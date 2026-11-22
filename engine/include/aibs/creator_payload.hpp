#pragma once
#include <aibs/creator_host.hpp>
#include <aibs/creator_wire.hpp>
#include <bit>
#include <cmath>
#include <string_view>

namespace aibs::creator_payload {
inline constexpr std::size_t maximum_bytes=1024*1024;
struct EditRequest { CreatorScope scope; std::string host_epoch; Transaction transaction; };
class PayloadError : public std::runtime_error { public: using std::runtime_error::runtime_error; };
namespace detail {
inline void ensure(bool value,const char* reason) { if(!value) throw PayloadError(reason); }
inline bool utf8(std::string_view text) noexcept {
 std::size_t i=0;
 while(i<text.size()) {
  const auto first=static_cast<unsigned char>(text[i++]);
  if(first==0) return false;
  if(first<0x80) continue;
  unsigned count=0; std::uint32_t code=0, minimum=0;
  if(first>=0xc2&&first<=0xdf) {count=1;code=first&0x1f;minimum=0x80;}
  else if(first>=0xe0&&first<=0xef) {count=2;code=first&0xf;minimum=0x800;}
  else if(first>=0xf0&&first<=0xf4) {count=3;code=first&7;minimum=0x10000;}
  else return false;
  if(count>text.size()-i) return false;
  for(unsigned j=0;j<count;++j) {
   const auto next=static_cast<unsigned char>(text[i++]);
   if(next<0x80||next>0xbf) return false;
   code=(code<<6)|(next&0x3f);
  }
  if(code<minimum||code>0x10ffff||(code>=0xd800&&code<=0xdfff)) return false;
 }
 return true;
}
inline void uuid(const std::string& value,bool optional=false) {ensure((optional&&value.empty())||is_uuid(value),"Invalid canonical UUID");}
struct Writer {
 std::vector<unsigned char> data;
 void number(std::uint64_t value,unsigned width) {
  ensure(width<=maximum_bytes-data.size(),"Payload size limit");
  creator_wire::detail::append(data,value,width);
 }
 void text(const std::string& value,bool required=false) {
  ensure(value.size()<=4096&&utf8(value)&&(!required||!value.empty()),"Invalid bounded UTF-8 text");
  number(value.size(),4);ensure(value.size()<=maximum_bytes-data.size(),"Payload size limit");
  data.insert(data.end(),value.begin(),value.end());
 }
 void real(double value) {ensure(std::isfinite(value),"Non-finite number");number(std::bit_cast<std::uint64_t>(value),8);}
};
struct Reader {
 std::span<const unsigned char> data;std::size_t offset=0;
 std::uint64_t number(unsigned width) {
  ensure(width<=data.size()-offset,"Truncated payload");
  const auto value=creator_wire::detail::number(data,offset,width);offset+=width;return value;
 }
 std::string text(bool required=false) {
  const auto size=number(4);ensure(size<=4096&&size<=data.size()-offset,"Invalid text length");
  const auto view=std::string_view(reinterpret_cast<const char*>(data.data()+offset),static_cast<std::size_t>(size));
  ensure(utf8(view)&&(!required||!view.empty()),"Invalid bounded UTF-8 text");offset+=static_cast<std::size_t>(size);return std::string(view);
 }
 double real() {const auto value=std::bit_cast<double>(number(8));ensure(std::isfinite(value),"Non-finite number");return value;}
};
}
inline std::vector<unsigned char> encode_edit(const EditRequest& request) {
 detail::Writer w;w.number(1,2);
 detail::uuid(request.scope.world_id);detail::uuid(request.host_epoch);
 w.text(request.scope.project,true);w.text(request.scope.branch,true);w.text(request.scope.world_id,true);w.text(request.host_epoch,true);
 const auto& t=request.transaction;w.text(t.id,true);w.number(t.expected_revision,8);w.text(t.description);
 detail::ensure(!t.edits.empty()&&t.edits.size()<=256,"Edit count limit");w.number(t.edits.size(),4);
 for(const auto& edit:t.edits) {
  w.number(edit.index(),1);
  if(const auto* c=std::get_if<Create>(&edit)) {
   const auto& e=c->entity;w.text(e.id,true);w.text(e.name);detail::uuid(e.persistent_id,true);w.text(e.persistent_id);
   detail::ensure(e.fields.size()<=64,"Field count limit");w.number(e.fields.size(),4);
   for(const auto& [field,value]:e.fields) {w.text(field,true);w.real(value);}
  } else if(const auto* e=std::get_if<Erase>(&edit)) {w.text(e->entity,true);detail::uuid(e->persistent_id,true);w.text(e->persistent_id);}
  else {
   const auto& s=std::get<SetField>(edit);w.text(s.entity,true);w.text(s.field,true);w.real(s.value);
   detail::uuid(s.persistent_id,true);w.text(s.persistent_id);
  }
 }
 return w.data;
}
inline EditRequest decode_edit(std::span<const unsigned char> bytes) {
 detail::ensure(bytes.size()<=maximum_bytes,"Payload size limit");detail::Reader r{bytes};
 detail::ensure(r.number(2)==1,"Unsupported payload version");EditRequest request;
 request.scope.project=r.text(true);request.scope.branch=r.text(true);request.scope.world_id=r.text(true);request.host_epoch=r.text(true);
 detail::uuid(request.scope.world_id);detail::uuid(request.host_epoch);
 auto& t=request.transaction;t.id=r.text(true);t.expected_revision=r.number(8);t.description=r.text();
 const auto count=r.number(4);detail::ensure(count>0&&count<=256,"Edit count limit");
 for(std::uint64_t i=0;i<count;++i) {
  const auto tag=r.number(1);detail::ensure(tag<=2,"Unknown edit tag");auto alias=r.text(true);
  if(tag==0) {
   Entity entity;entity.id=std::move(alias);entity.name=r.text();entity.persistent_id=r.text();detail::uuid(entity.persistent_id,true);
   const auto fields=r.number(4);detail::ensure(fields<=64,"Field count limit");
   for(std::uint64_t j=0;j<fields;++j) {
    auto key=r.text(true);const auto value=r.real();
    detail::ensure(entity.fields.emplace(std::move(key),value).second,"Duplicate field key");
   }
   t.edits.push_back(Create{std::move(entity)});
  } else if(tag==1) {
   auto uuid=r.text();detail::uuid(uuid,true);t.edits.push_back(Erase{std::move(alias),std::move(uuid)});
  } else {
   auto field=r.text(true);const auto value=r.real();auto uuid=r.text();detail::uuid(uuid,true);
   t.edits.push_back(SetField{std::move(alias),std::move(field),value,std::move(uuid)});
  }
 }
 detail::ensure(r.offset==bytes.size(),"Trailing payload bytes");return request;
}
}
