#include <aibs/content_authoring.hpp>
#include <aibs/content_dependencies.hpp>
#include <aibs/creator_payload.hpp>
#include <array>
#include <bit>
#include <filesystem>
#include <iostream>
#include <map>
#include <new>
#include <string_view>
#include <fcntl.h>
#include <io.h>

namespace {
using namespace aibs;
namespace wire=creator_wire;
namespace payload=creator_payload;
using Reader=payload::detail::Reader;
using Writer=payload::detail::Writer;
using payload::detail::ensure;
constexpr std::size_t maximum_body_bytes=500*1024;
// Cursor text length prefix + canonical UUID + more flag + row count.
constexpr std::size_t page_header_bytes=4+36+1+4;
enum class Status:std::uint16_t {ok=0,prepared=1,applied=2,duplicate=3,undone=4,redone=5,saved=6,rejected=100};
struct Reply {
 Status status=Status::ok;
 std::string message="Command completed";
 std::uint64_t operation_revision=0;
 std::string token;
 bool compatible=false;
 std::uint64_t save_bytes=0;
 std::string save_message="Not assessed";
 std::vector<unsigned char> body;
};
Status status(ContentAuthoringStatus value){
 switch(value){
 case ContentAuthoringStatus::prepared:return Status::prepared;
 case ContentAuthoringStatus::applied:return Status::applied;
 case ContentAuthoringStatus::duplicate:return Status::duplicate;
 case ContentAuthoringStatus::undone:return Status::undone;
 case ContentAuthoringStatus::redone:return Status::redone;
 case ContentAuthoringStatus::saved:return Status::saved;
 case ContentAuthoringStatus::rejected:case ContentAuthoringStatus::failed:return Status::rejected;
 }
 throw std::runtime_error("Unknown typed owner result");
}
std::string bounded_message(std::string message){
 if(!payload::detail::utf8(message))return "Typed creator diagnostic is not valid UTF-8";
 if(message.size()>4096){message.resize(4096);while(!payload::detail::utf8(message))message.pop_back();}
 return message;
}
std::array<unsigned char,16> epoch_bytes(){
 std::array<unsigned char,16> bytes{};const auto id=new_uuid();unsigned nibble=0;
 for(const char c:id){if(c=='-')continue;const auto value=static_cast<unsigned>(c<='9'?c-'0':c-'a'+10);auto& b=bytes[nibble/2];b=static_cast<unsigned char>((b<<4)|value);++nibble;}
 return bytes;
}
void end(const Reader& r){ensure(r.offset==r.data.size(),"Trailing command bytes");}
Reader reader(const wire::Frame& frame){ensure(frame.payload.size()<=payload::maximum_bytes,"Request exceeds 1 MiB");Reader r{frame.payload};ensure(r.number(2)==1,"Unsupported command version");return r;}
struct ScopeRequest {CreatorScope scope;std::string host_epoch;};
ScopeRequest scope(Reader& r){ScopeRequest result;result.scope.project=r.text(true);result.scope.branch=r.text(true);result.scope.world_id=r.text(true);result.host_epoch=r.text(true);payload::detail::uuid(result.scope.world_id);payload::detail::uuid(result.host_epoch);return result;}
void field_value(Writer& w,const GameplayValue& value){
 ensure(!value.valueless_by_exception(),"Unsupported typed observation value");w.number(value.index(),1);
 std::visit([&](const auto& v){using T=std::decay_t<decltype(v)>;if constexpr(std::is_same_v<T,bool>)w.number(v?1:0,1);else if constexpr(std::is_same_v<T,std::int64_t>)w.number(std::bit_cast<std::uint64_t>(v),8);else if constexpr(std::is_same_v<T,double>)w.real(v);else w.text(v);},value);
}
void row(Writer& w,const ContentAuthoringRow& value){
 payload::detail::uuid(value.entity_id);w.text(value.entity_id,true);w.text(value.type_id,true);w.text(value.name);ensure(value.fields.size()<=1024,"Typed observation field limit");w.number(value.fields.size(),4);
 for(const auto& [key,v]:value.fields){w.text(key,true);field_value(w,v);}
}
std::vector<ContentAuthoringRow> rows(const ContentAuthoringSnapshot& snapshot){
 auto result=content_authoring_rows(snapshot.content);ensure(result.size()<=10000,"Typed observation row limit");
 std::sort(result.begin(),result.end(),[](const auto& a,const auto& b){return a.entity_id<b.entity_id;});return result;
}
class Owner {
 std::filesystem::path root_;
 AssetContentProfile asset_profile_=AssetContentProfile::legacy_v1;
 bool negotiated_=false;
 std::unique_ptr<ContentAuthoringHost> host_;
 std::map<std::string,ContentPreparedPtr> tokens_;
 void check_scope(const ScopeRequest& q)const{ensure(host_!=nullptr,"No chapter document open");ensure(q.scope==host_->snapshot()->scope&&q.host_epoch==host_->epoch_id(),"Document scope or host epoch mismatch");}
 void check_head(const wire::Frame& f)const{ensure(host_&&f.revision==host_->snapshot()->revision,"Chapter authoring revision conflict");}
 std::filesystem::path slot()const{
  const auto path=root_/L"chapter.aiba";ensure(std::filesystem::weakly_canonical(path)==path,"Chapter slot redirects outside selected workspace");auto lock=path;lock+=L".lock";ensure(!std::filesystem::is_symlink(lock),"Chapter lock redirects");return path;
 }
 Reply result(ContentAuthoringResult value){
  Reply reply;reply.status=status(value.status);reply.message=std::move(value.message);reply.operation_revision=value.revision;
  if(value.status==ContentAuthoringStatus::prepared){
   ensure(tokens_.size()<8&&value.change,"Prepared chapter handle budget exhausted");const auto& p=value.change->dependencies();
   reply.token=new_uuid();reply.compatible=true;reply.save_bytes=value.change->encoded_document_bytes();reply.save_message="Authoring journal encoding assessed; changed gameplay content requires a new Play branch";
   Writer body;body.number(p.save_compatible,1);body.number(p.render_rebuild,1);body.number(p.collision_rebuild,1);body.number(p.power_dependencies,1);body.number(p.quest_dependencies,1);
   ensure(p.affected_ids.size()<=10000&&p.dependencies.size()<=1024,"Dependency preview collection limit");body.number(p.affected_ids.size(),4);for(const auto& id:p.affected_ids){payload::detail::uuid(id);body.text(id,true);}body.number(p.dependencies.size(),4);for(const auto& dependency:p.dependencies)body.text(dependency,true);body.text(p.navigation);ensure(body.data.size()<=maximum_body_bytes,"Typed preview body exceeds budget");reply.body=std::move(body.data);tokens_.emplace(reply.token,std::move(value.change));
  }
  if(value.status==ContentAuthoringStatus::applied||value.status==ContentAuthoringStatus::undone||value.status==ContentAuthoringStatus::redone||value.status==ContentAuthoringStatus::saved)tokens_.clear();
  return reply;
 }
public:
 const std::array<unsigned char,16> epoch=epoch_bytes();
 bool shutdown=false;
 explicit Owner(std::filesystem::path root,AssetContentProfile profile):root_(std::filesystem::canonical(root)),asset_profile_(profile){ensure(std::filesystem::is_directory(root_),"Workspace must be an existing directory");}
 Reply dispatch(const wire::Frame& frame){
  try{
   ensure(!frame.response,"Request must not set response flag");
   if(frame.opcode==wire::Opcode::hello){
    ensure(!negotiated_&&frame.epoch==std::array<unsigned char,16>{}&&frame.revision==wire::unscoped_revision&&frame.payload.empty(),"Invalid Hello negotiation");
    Writer body;body.text("chapter-authoring-v1;typed-observation-rows;chapter-content-export-v1;chapter-content-export-v2;chapter-character-assets-v1;chapter-memory-audio-v1;chapter-authored-inspections-v1;chapter-initial-view-v1;chapter-workshop-commissioning-v1;chapter-assets-v1;chapter-assets-v2;chapter-content-v3;no-native-play");body.number(payload::maximum_bytes,4);body.number(8,4);Reply reply;reply.body=std::move(body.data);negotiated_=true;return reply;
   }
   ensure(negotiated_&&frame.epoch==epoch,"Process epoch mismatch or Hello required");
   if(frame.opcode==wire::Opcode::shutdown){ensure(frame.revision==wire::unscoped_revision&&frame.payload.empty(),"Invalid Shutdown request");shutdown=true;return Reply{};}
   if(frame.opcode==wire::Opcode::open){
    ensure(!host_&&frame.revision==wire::unscoped_revision,"Open requires an unopened typed owner");auto r=reader(frame);const auto project=r.text(true),branch=r.text(true);const auto create=r.number(1);end(r);ensure(create<=1,"Invalid chapter create mode");const auto path=slot();
    std::unique_ptr<ContentAuthoringHost> owner;
    if(std::filesystem::exists(path))owner=std::make_unique<ContentAuthoringHost>(ContentAuthoringHost::open(path,project,branch));
    else{ensure(create==1,"Chapter document is absent; explicit create required");CreatorSession source(first_boot_schema(),project,branch);const auto seeded=seed_first_boot(source);ensure(seeded.ok,seeded.message.c_str());auto definition=FirstBootContent::from_template(source).definition();if(asset_profile_==AssetContentProfile::warm_beginning){definition.format_version=3;definition.asset_profile=asset_profile_;}owner=std::make_unique<ContentAuthoringHost>(FirstBootContent::create(std::move(definition)),project,branch,source.known_entity_ids());}
    ensure(owner->snapshot()->content.definition().asset_profile==asset_profile_,"Project metadata asset profile differs from saved chapter content");
    owner->bind_asset_store(root_/"assets"/"packs");host_.swap(owner);return Reply{};
   }
   auto r=reader(frame);const auto q=scope(r);check_scope(q);
   if(frame.opcode==wire::Opcode::preview||frame.opcode==wire::Opcode::apply_transaction){
    const auto size=r.number(4);ensure(size<=r.data.size()-r.offset,"Truncated scoped typed edit");const auto packet=decode_scoped_content_edit(r.data.subspan(r.offset,static_cast<std::size_t>(size)));r.offset+=static_cast<std::size_t>(size);end(r);
    ensure(packet.scope==q.scope&&packet.request.expected_revision==frame.revision,"Scoped packet/frame identity or head differs");
    if(frame.opcode==wire::Opcode::preview)ensure(tokens_.size()<8,"Prepared chapter handle budget exhausted");
    // Durable original receipts resolve before current-head conflict checks.
    return result(frame.opcode==wire::Opcode::preview?host_->preview(packet):host_->apply(packet));
   }
   if(frame.opcode==wire::Opcode::history){const auto id=r.text(true);const auto redo=r.number(1);const auto fingerprint=r.text(true);end(r);ensure(redo<=1,"Invalid typed history direction");return result(host_->travel(q.scope,{id,frame.revision,fingerprint,redo==1}));}
   check_head(frame);
   if(frame.opcode==wire::Opcode::describe){
    const auto view=host_->snapshot();Writer body;
    if(r.offset!=r.data.size()){
     const auto mode=r.number(1);ensure(mode==1||mode==2,"Unsupported chapter export command");const auto offset=r.number(4),limit=r.number(4);const auto fingerprint=r.text(true);end(r);
     ensure(limit>0&&limit<=256*1024,"Chapter export chunk limit must be1..256 KiB");ensure(fingerprint==view->content.fingerprint(),"Chapter export fingerprint is stale");
     const auto content=first_boot_content_encode(view->content);ensure(content.size()<=payload::maximum_bytes&&offset<=content.size(),"Chapter export content/offset bound");const auto count=(std::min)(limit,content.size()-static_cast<std::size_t>(offset));
     body.number(mode==2?2:1,2);body.text(view->content.definition().definition_id,true);body.text(view->content.fingerprint(),true);body.number(view->content.definition().revision,8);body.number(content.size(),4);body.number(offset,4);body.number(count,4);
     if(mode==2){
      const auto dependencies=first_boot_content_dependencies(view->content);body.number(dependencies.size(),4);
      for(const auto& dependency:dependencies){body.number(static_cast<unsigned>(dependency.kind),1);body.text(dependency.reference.asset_id,true);body.text(dependency.reference.asset_sha256,true);body.text(dependency.reference.pack_sha256,true);}
     }
     body.data.insert(body.data.end(),content.begin()+static_cast<std::ptrdiff_t>(offset),content.begin()+static_cast<std::ptrdiff_t>(offset+count));ensure(body.data.size()<=maximum_body_bytes,"Chapter export reply byte bound");
    }else{body.text(view->content.definition().definition_id,true);body.number(view->content.definition().revision,8);body.text(view->content.fingerprint(),true);body.number(view->dirty,1);body.number(view->known_ids.size(),4);}
    Reply reply;reply.body=std::move(body.data);return reply;
   }
   if(frame.opcode==wire::Opcode::snapshot_page){
    const auto checkpoint=r.text(),after=r.text();const auto limit=r.number(4);end(r);const auto view=host_->snapshot();ensure(checkpoint==view->checkpoint_id,"Chapter snapshot checkpoint cursor is stale");ensure(after.empty()||is_uuid(after),"Typed cursor must be a canonical UUID");ensure(limit>0&&limit<=32,"Typed snapshot page count limit");
    const auto all=rows(*view);auto it=std::upper_bound(all.begin(),all.end(),after,[](const auto& id,const auto& value){return id<value.entity_id;});Writer encoded;std::size_t count=0;std::string cursor=after;
    while(it!=all.end()&&count<limit){Writer next;row(next,*it);if(encoded.data.size()+next.data.size()>maximum_body_bytes-page_header_bytes){ensure(count!=0,"Typed row exceeds page byte budget");break;}encoded.data.insert(encoded.data.end(),next.data.begin(),next.data.end());cursor=it->entity_id;++count;++it;}
    Writer body;body.text(cursor);body.number(it!=all.end(),1);body.number(count,4);body.data.insert(body.data.end(),encoded.data.begin(),encoded.data.end());Reply reply;reply.body=std::move(body.data);return reply;
   }
   if(frame.opcode==wire::Opcode::apply_prepared||frame.opcode==wire::Opcode::release_prepared){
    const auto handle=r.text(true);payload::detail::uuid(handle);end(r);const auto found=tokens_.find(handle);ensure(found!=tokens_.end(),"Prepared chapter handle expired/unknown");if(frame.opcode==wire::Opcode::release_prepared){tokens_.erase(found);return Reply{};}return result(host_->apply(found->second));
   }
   if(frame.opcode==wire::Opcode::save){end(r);return result(host_->save(slot()));}
   if(frame.opcode==wire::Opcode::start_play){end(r);throw payload::PayloadError("Native chapter Play/Stop is not implemented; no gameplay process started");}
   if(frame.opcode==wire::Opcode::stop_play){const auto handle=r.text(true);payload::detail::uuid(handle);end(r);throw payload::PayloadError("No native chapter Play process is owned");}
   throw payload::PayloadError("Typed command is not implemented");
  }catch(const std::bad_alloc&){throw;}
   catch(const std::exception& error){Reply reply;reply.status=Status::rejected;reply.message=bounded_message(error.what());return reply;}
 }
 wire::Frame response(const wire::Frame& request,const Reply& reply)const{
  Writer w;w.number(1,2);w.number(static_cast<std::uint16_t>(reply.status),2);w.text(bounded_message(reply.message));const auto view=host_?host_->snapshot():nullptr;
  w.text(host_?host_->epoch_id():"");w.text(view?view->scope.project:"");w.text(view?view->scope.branch:"");w.text(view?view->scope.world_id:"");w.number(view?view->revision:0,8);w.text(view?view->checkpoint_id:"");w.number(reply.operation_revision,8);w.text(reply.token);w.text("");w.number(reply.compatible,1);w.number(reply.save_bytes,8);w.text(bounded_message(reply.save_message));
  w.number(view?rows(*view).size():0,4);w.number(view?view->undo_depth:0,8);w.number(view?view->redo_depth:0,8);ensure(reply.body.size()<=maximum_body_bytes,"Typed response body exceeds budget");w.number(reply.body.size(),4);w.data.insert(w.data.end(),reply.body.begin(),reply.body.end());
  return {request.opcode,request.request_id,negotiated_?epoch:std::array<unsigned char,16>{},view?view->revision:0,std::move(w.data),true};
 }
};
}
int wmain(int argc,wchar_t** argv){
 _setmode(_fileno(stdin),_O_BINARY);_setmode(_fileno(stdout),_O_BINARY);
 if((argc!=3&&argc!=5)||std::wstring_view(argv[1])!=L"--workspace"||(argc==5&&(std::wstring_view(argv[3])!=L"--asset-profile"||std::wstring_view(argv[4])!=L"warm-beginning"))){std::cerr<<"Usage: aibs_content_host --workspace EXISTING_DIRECTORY [--asset-profile warm-beginning]\n";return 64;}
 try{
  Owner owner{std::filesystem::path(argv[2]),argc==5?AssetContentProfile::warm_beginning:AssetContentProfile::legacy_v1};wire::Parser parser;
  while(!owner.shutdown){
   std::array<unsigned char,48> header{};std::cin.read(reinterpret_cast<char*>(header.data()),header.size());const auto got=std::cin.gcount();if(got==0&&std::cin.eof()){parser.finish();break;}
   ensure(got==static_cast<std::streamsize>(header.size()),"Truncated typed pipe header");auto frames=parser.feed(header);const auto length=wire::detail::number(header,12,4);ensure(length<=payload::maximum_bytes&&wire::detail::number(header,10,2)==0,"Invalid typed request size/response flag");
   std::size_t left=static_cast<std::size_t>(length);std::array<unsigned char,65536> chunk{};while(left){const auto take=(std::min)(left,chunk.size());std::cin.read(reinterpret_cast<char*>(chunk.data()),static_cast<std::streamsize>(take));ensure(std::cin.gcount()==static_cast<std::streamsize>(take),"Truncated typed pipe payload");auto next=parser.feed({chunk.data(),take});frames.insert(frames.end(),std::make_move_iterator(next.begin()),std::make_move_iterator(next.end()));left-=take;}
   ensure(frames.size()==1,"Expected one complete typed request");const auto reply=owner.dispatch(frames.front());const auto bytes=wire::encode(owner.response(frames.front(),reply));std::cout.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));std::cout.flush();ensure(std::cout.good(),"Typed creator response pipe closed");
  }return 0;
 }catch(const std::exception& error){std::cerr<<bounded_message(error.what())<<'\n';return 2;}
}
