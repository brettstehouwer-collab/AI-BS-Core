#include <aibs/opening_inspections.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <set>
#include <limits>
#include <stdexcept>

namespace aibs {namespace {
void need(bool condition,const char* message){if(!condition)throw std::invalid_argument(message);}
bool uuid(std::string_view value){
 if(value.size()!=36||value[14]!='4'||(value[19]!='8'&&value[19]!='9'&&value[19]!='a'&&value[19]!='b'))return false;
 for(std::size_t i=0;i<value.size();++i){const char c=value[i];if(i==8||i==13||i==18||i==23){if(c!='-')return false;}else if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;}
 return true;
}
void text(const std::string& value,std::size_t maximum){
 need(!value.empty()&&value.size()<=maximum,"Inspection text is empty or exceeds its byte limit");
 const auto* bytes=reinterpret_cast<const unsigned char*>(value.data());
 for(std::size_t i=0;i<value.size();){const auto c=bytes[i++];
  if(c<0x80){need((c>=0x20&&c!=0x7f)||c=='\n'||c=='\r'||c=='\t',"Inspection text contains a forbidden control");continue;}
  std::uint32_t scalar=0;unsigned following=0;std::uint32_t minimum=0;
  if(c>=0xc2&&c<=0xdf){scalar=c&0x1f;following=1;minimum=0x80;}
  else if(c>=0xe0&&c<=0xef){scalar=c&0x0f;following=2;minimum=0x800;}
  else if(c>=0xf0&&c<=0xf4){scalar=c&7;following=3;minimum=0x10000;}
  else throw std::invalid_argument("Inspection text is not canonical UTF8");
  need(following<=value.size()-i,"Inspection text has truncated UTF8");
  for(unsigned n=0;n<following;++n){const auto next=bytes[i++];need((next&0xc0)==0x80,"Inspection text has invalid UTF8 continuation");scalar=(scalar<<6)|(next&0x3f);}
  need(scalar>=minimum&&scalar<=0x10ffff&&!(scalar>=0xd800&&scalar<=0xdfff),"Inspection text has invalid UTF8 scalar");
 }
}
bool finite(Vec3 v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z);}
std::size_t resident_add(std::size_t left,std::size_t right)noexcept{return right>std::numeric_limits<std::size_t>::max()-left?std::numeric_limits<std::size_t>::max():left+right;}
std::size_t inspection_strings(const OpeningInspection& value)noexcept{
 std::size_t bytes=0;for(const auto* text:{&value.fixture_id,&value.title,&value.text,&value.source})bytes=resident_add(bytes,resident_add(text->capacity(),1));return bytes;
}
}}
namespace aibs {
OpeningInspectionCatalog::OpeningInspectionCatalog(const FirstBootContentDefinition& d){
 struct Fields {std::array<const std::string*,3> values{};};std::map<std::string,Fields> groups;
 for(const auto& [key,value]:d.hints){if(!key.starts_with("inspect."))continue;
  need(d.format_version==3&&d.asset_profile==AssetContentProfile::warm_beginning,"Authored inspections require AIBD3 warm_beginning");
  need(key.size()>44&&key[44]=='.',"Malformed inspection key");const auto id=key.substr(8,36);need(uuid(id),"Inspection requires a canonical owned UUID");const auto field=key.substr(45);
  const std::size_t slot=field=="text"?0:field=="source"?1:field=="action"?2:3;need(slot<3,"Unknown inspection field");groups[id].values[slot]=&value;
 }
 need(groups.size()<=10,"Inspection count exceeds bounded content map profile");
 std::size_t total=0;
 for(const auto& [id,fields]:groups){
  need(std::all_of(fields.values.begin(),fields.values.end(),[](const auto* v){return v!=nullptr;}),"Inspection requires complete text/source/action fields");
  const auto owner=std::find_if(d.fixtures.begin(),d.fixtures.end(),[&](const auto& f){return f.object.persistent_id==id;});need(owner!=d.fixtures.end(),"Inspection targets an unowned fixture");
  need(std::count_if(d.fixtures.begin(),d.fixtures.end(),[&](const auto& f){return f.object.persistent_id==id;})==1,"Inspection owner UUID is not unique");
  need(owner->object.selectable&&finite(owner->object.center),"Inspection fixture must be selectable with finite coordinates");
  const auto& body=*fields.values[0];const auto& source=*fields.values[1];const auto& action=*fields.values[2];text(owner->object.name,256);text(body,2048);text(source,512);
  need(action=="read"||action=="seat","Inspection action must be read or seat");total+=owner->object.name.size()+body.size()+source.size()+action.size();need(total<=32u*1024u,"Inspection text closure exceeds byte budget");
  entries_.push_back({id,owner->object.name,body,source,owner->object.center,action=="seat"?OpeningInspectionAction::seat:OpeningInspectionAction::read});
 }
}
const OpeningInspection* OpeningInspectionCatalog::find(std::string_view id)const noexcept{
 const auto found=std::find_if(entries_.begin(),entries_.end(),[&](const auto& item){return item.fixture_id==id;});return found==entries_.end()?nullptr:&*found;
}
std::size_t OpeningInspectionCatalog::resident_bytes()const noexcept{
 if(entries_.capacity()>std::numeric_limits<std::size_t>::max()/sizeof(OpeningInspection))return std::numeric_limits<std::size_t>::max();
 std::size_t bytes=entries_.capacity()*sizeof(OpeningInspection);for(const auto& entry:entries_)bytes=resident_add(bytes,inspection_strings(entry));return bytes;
}
std::size_t OpeningInspectionSession::resident_bytes()const noexcept{
 auto bytes=catalog_.resident_bytes();if(current_)bytes=resident_add(bytes,resident_add(sizeof(OpeningInspection),inspection_strings(*current_)));return bytes;
}
bool OpeningInspectionSession::select(std::string_view id,Vec3 feet,bool visible){
 const auto* item=catalog_.find(id);if(!item||!visible||!finite(feet))return false;
 if(std::hypot(static_cast<double>(feet.x)-item->center.x,static_cast<double>(feet.y)-item->center.y,static_cast<double>(feet.z)-item->center.z)>3.2)return false;
 current_=*item;return true;
}
}
