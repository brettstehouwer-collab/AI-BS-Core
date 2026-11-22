#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/first_boot_content.hpp>
#include <aibs/initial_view.hpp>
#include <aibs/opening_inspections.hpp>
#include <aibs/creator_payload.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <tuple>

namespace aibs {
namespace {
using Writer=creator_payload::detail::Writer;using Reader=creator_payload::detail::Reader;
void need(bool value,const char* why){if(!value)throw std::invalid_argument(why);}
constexpr const char* binding_type="firstboot.ContentBinding";
constexpr const char* companion_type="firstboot.CompanionIntent";
GuideIntentRecord companion_intent(const ComponentRecord& r){
 need(r.type_id==companion_type&&r.version==1&&is_uuid(r.entity_id)&&r.fields.size()==4,"Invalid companion intent identity, version or field count");
 const auto follow=r.fields.find("follow");need(follow!=r.fields.end()&&std::holds_alternative<bool>(follow->second),"Companion follow intent must be boolean");
 const auto coordinate=[&](const char* key){const auto field=r.fields.find(key);need(field!=r.fields.end(),"Companion anchor coordinate is missing");const auto* value=std::get_if<double>(&field->second);need(value&&std::isfinite(*value)&&std::abs(*value)<=1000000,"Companion anchor must be a bounded finite number");const auto result=static_cast<float>(*value);need(static_cast<double>(result)==*value,"Companion anchor must retain canonical float precision");return result;};
 return {std::get<bool>(follow->second)?GuideIntent::follow:GuideIntent::wait,{coordinate("anchor_x"),coordinate("anchor_y"),coordinate("anchor_z")}};
}
bool inside(const FirstBootContentRegion& region,Vec3 p){return std::abs(p.x-region.center.x)<=region.half_extent.x&&std::abs(p.y-region.center.y)<=region.half_extent.y&&std::abs(p.z-region.center.z)<=region.half_extent.z;}
std::string digest(std::span<const unsigned char> bytes){
 struct Handles {BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;~Handles(){if(hash)BCryptDestroyHash(hash);if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);}} h;
 need(BCryptOpenAlgorithmProvider(&h.algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0,"SHA256 provider unavailable");
 need(BCryptCreateHash(h.algorithm,&h.hash,nullptr,0,nullptr,0,0)>=0,"SHA256 initialization failed");
 need(BCryptHashData(h.hash,const_cast<PUCHAR>(bytes.data()),static_cast<ULONG>(bytes.size()),0)>=0,"SHA256 input failed");
 std::array<unsigned char,32> hash{};need(BCryptFinishHash(h.hash,hash.data(),static_cast<ULONG>(hash.size()),0)>=0,"SHA256 result failed");
 std::ostringstream out;for(auto value:hash)out<<std::hex<<std::setfill('0')<<std::setw(2)<<static_cast<unsigned>(value);return out.str();
}
void point(Writer& w,Vec3 p){w.real(p.x);w.real(p.y);w.real(p.z);}
Vec3 point(Reader& r){auto scalar=[&]{const auto n=r.real();const auto f=static_cast<float>(n);need(std::isfinite(f)&&static_cast<double>(f)==n,"Non-canonical content float");return f;};return {scalar(),scalar(),scalar()};}
void raw(Writer& w,std::span<const unsigned char> bytes){w.number(bytes.size(),4);need(bytes.size()<=creator_payload::maximum_bytes-w.data.size(),"Content byte limit");w.data.insert(w.data.end(),bytes.begin(),bytes.end());}
std::span<const unsigned char> raw(Reader& r){const auto n=r.number(4);need(n<=r.data.size()-r.offset,"Truncated content record");const auto result=r.data.subspan(r.offset,static_cast<std::size_t>(n));r.offset+=static_cast<std::size_t>(n);return result;}
void reference(Writer& w,const AssetPackReference& a){w.text(a.asset_id,true);w.text(a.asset_sha256,true);w.text(a.pack_sha256,true);}
AssetPackReference reference(Reader& r){return {r.text(true),r.text(true),r.text(true)};}
void companion(Writer& w,const FirstBootCompanionBinding& a){
 w.text(a.entity_id,true);w.text(a.name,true);point(w,a.spawn);w.number(a.initial_follow,1);w.number(a.model.has_value(),1);if(a.model)reference(w,*a.model);
 w.number(a.routes.nodes.size(),4);for(const auto& n:a.routes.nodes){w.text(n.id,true);point(w,n.feet);}w.number(a.routes.edges.size(),4);for(const auto& e:a.routes.edges){w.text(e.from,true);w.text(e.to,true);w.text(e.door);w.number(e.bidirectional,1);}
}
void light(Writer& w,const FirstBootLightDefinition& l){w.text(l.entity_id,true);w.text(l.name,true);w.number(static_cast<unsigned>(l.kind),1);w.number(static_cast<unsigned>(l.power),1);point(w,l.position);point(w,l.direction);point(w,l.color);w.real(l.intensity);w.real(l.radius);}
void memory(Writer& w,const FirstBootMemoryBinding& m){w.text(m.entity_id,true);w.text(m.name,true);point(w,m.position);reference(w,m.audio);}
std::vector<unsigned char> encode(const FirstBootContentDefinition& d){
 Writer w;w.number(0x44424941,4);w.number(d.format_version,2);w.text(d.definition_id,true);w.text(d.world_id,true);w.text(d.binding_id,true);w.number(d.revision,8);
 w.number(d.hardware.size(),4);for(const auto& [alias,e]:d.hardware){w.text(alias,true);w.text(e.name);w.text(e.persistent_id,true);w.number(e.fields.size(),4);for(const auto& [key,value]:e.fields){w.text(key,true);w.real(value);}}
 w.number(d.initial_records.size(),4);for(const auto& r:d.initial_records)raw(w,gameplay_codec::encode_component(r));
 w.number(d.fixtures.size(),4);for(const auto& f:d.fixtures){const auto& o=f.object;w.text(o.persistent_id,true);w.text(o.name);point(w,o.center);point(w,o.half_extent);point(w,o.color);w.real(o.emission);w.number(f.role==FixtureRole::workshop?2u:static_cast<unsigned>(o.selectable),1);w.real(o.rotation.x);w.real(o.rotation.y);w.real(o.rotation.z);w.real(o.rotation.w);w.real(f.sheltered_emission);}
 for(const auto& zone:{d.hub,d.pencil}){point(w,zone.center);point(w,zone.half_extent);}
 for(const auto* list:{&d.jenison_returns,&d.hub_returns}){w.number(list->size(),4);for(auto p:*list)point(w,p);}
 point(w,d.isolation_switch);w.number(d.hints.size(),4);for(const auto& [key,text]:d.hints){w.text(key,true);w.text(text,true);}
 if(d.format_version>=2){w.number(d.placements.size(),4);for(const auto& p:d.placements){w.text(p.entity_id,true);w.text(p.name,true);w.text(p.asset_id,true);w.text(p.asset_sha256,true);w.text(p.pack_sha256,true);point(w,p.center);point(w,p.scale);w.real(p.rotation.x);w.real(p.rotation.y);w.real(p.rotation.z);w.real(p.rotation.w);w.number(p.selectable,1);}}
 if(d.format_version>=3){w.number(static_cast<unsigned>(d.asset_profile),1);w.real(d.exposure);w.number(d.companions.size(),4);for(const auto& a:d.companions)companion(w,a);w.number(d.lights.size(),4);for(const auto& l:d.lights)light(w,l);w.number(d.memories.size(),4);for(const auto& m:d.memories)memory(w,m);}
 return w.data;
}
GameplayStoreRecovery recovery(const FirstBootContent& c){const auto b=first_boot_content_baseline(c);return {{"content-validation",c.definition().world_id,"main",c.definition().definition_id,GameplayContext::temporary_play},0,0,b.components};}
const ComponentRecord& find(const FirstBootContentDefinition& d,const std::string& type,const std::string& role=""){
 for(const auto& r:d.initial_records)if(r.type_id==type&&(role.empty()||std::get<std::string>(r.fields.at("role"))==role))return r;throw std::invalid_argument("Content role missing");
}
void validate_defaults(const FirstBootContentDefinition& d){
 auto unique=std::set<std::string>{};auto id=[&](const std::string& value){need(is_uuid(value)&&unique.insert(value).second,"Duplicate/invalid content identity");};id(d.definition_id);id(d.binding_id);id(d.world_id);
 need(is_uuid(d.world_id)&&d.hardware.size()<=512&&d.initial_records.size()==6&&d.fixtures.size()<=512,"Content collection limit");
 (void)first_boot_scene(d.hardware,d.world_id,0);
 for(const auto& [alias,e]:d.hardware){need(alias==e.id,"Content hardware alias mismatch");id(e.persistent_id);}
 const auto schemas=first_boot_chapter_schemas();std::set<std::string> singleton,roles;
 for(const auto& r:d.initial_records){id(r.entity_id);const auto schema=std::find_if(schemas.begin(),schemas.end(),[&](const auto& s){return s.type_id==r.type_id&&r.version==1;});need(schema!=schemas.end()&&r.type_id!="firstboot.Node"&&r.fields.size()==schema->fields.size(),"Unsupported content record");
  for(const auto& f:schema->fields){const auto p=r.fields.find(f.id);need(p!=r.fields.end()&&p->second.index()==static_cast<std::size_t>(f.kind),"Content field schema mismatch");if(const auto* n=std::get_if<double>(&p->second))need(std::isfinite(*n)&&*n>=f.minimum&&*n<=f.maximum,"Content field outside schema bounds");}
  if(r.type_id=="firstboot.Door"){const auto role=std::get<std::string>(r.fields.at("role"));need((role=="main"||role=="service"||role=="pencil")&&roles.insert(role).second,"Content door role mismatch");need(!std::get<bool>(r.fields.at("open"))&&std::get<bool>(r.fields.at("unlocked"))==(role=="pencil"),"Authoring cannot pre-complete door outcomes");}
  else need(singleton.insert(r.type_id).second,"Duplicate content singleton");
  for(const auto& [key,value]:r.fields)if(first_boot_content_runtime_field(r.type_id,key)&&r.type_id!="firstboot.Door"){
   if(key=="state"){const auto state=r.type_id=="firstboot.ChapterProgress"?QuestState::active:QuestState::offered;need(value==GameplayValue{static_cast<std::int64_t>(state)},"Authoring cannot pre-complete quest state");}
   else if(key=="step"){need(value==GameplayValue{std::string(r.type_id=="firstboot.ChapterProgress"?"jenison":"lamp.awaiting_help")},"Authoring cannot pre-complete quest steps");}
   else if(key=="first_route")need(value==GameplayValue{std::string("none")},"Authoring cannot fabricate a route");
   else if(std::holds_alternative<bool>(value))need(!std::get<bool>(value),"Authoring cannot fabricate a boolean outcome");
   else if(std::holds_alternative<std::int64_t>(value))need(std::get<std::int64_t>(value)==0,"Authoring cannot fabricate a counter");
   else if(std::holds_alternative<double>(value))need(std::get<double>(value)==0,"Authoring cannot fabricate a repair");
   else need(std::get<std::string>(value).empty(),"Authoring cannot fabricate outcome evidence");
  }
 }
 need(roles.size()==3&&singleton.size()==3,"Content requires complete chapter roles");
 SceneSnapshot fixtures{d.world_id,0,{}};for(const auto& f:d.fixtures){id(f.object.persistent_id);need(std::isfinite(f.sheltered_emission)&&f.sheltered_emission>=-1&&f.sheltered_emission<=16,"Invalid authored illumination");fixtures.objects.push_back(f.object);}(void)mesh_from_snapshot(fixtures);
 need(d.format_version>=1&&d.format_version<=3&&(d.format_version>=2||d.placements.empty()),"Unsupported content version or placements in legacy content");
 need(d.placements.size()<=64,"Content asset placement limit");
 need(d.asset_profile==AssetContentProfile::legacy_v1||d.asset_profile==AssetContentProfile::warm_beginning,"Unknown content asset profile");
 need(d.format_version>=3||(d.asset_profile==AssetContentProfile::legacy_v1&&d.exposure==1&&d.companions.empty()&&d.lights.empty()&&d.memories.empty()),"Modern bindings/profile require AIBD3");
 need(std::isfinite(d.exposure)&&d.exposure>=.05f&&d.exposure<=16,"Exposure outside supported range");
 need(d.companions.size()<=1&&d.lights.size()<=32&&d.memories.size()<=8,"Modern content binding count exceeds profile");
 std::set<std::tuple<std::string,std::string,std::string>> references;
 std::set<std::string> asset_ids;
 const auto sha=[](const std::string& value){return value.size()==64&&std::all_of(value.begin(),value.end(),[](char c){return(c>='0'&&c<='9')||(c>='a'&&c<='f');});};
 for(const auto& p:d.placements){
  id(p.entity_id);need(is_uuid(p.asset_id)&&sha(p.asset_sha256)&&sha(p.pack_sha256),"Invalid placement asset UUID or immutable hash");
  Writer text;text.text(p.name,true);
  need(std::isfinite(p.center.x)&&std::isfinite(p.center.y)&&std::isfinite(p.center.z)&&std::isfinite(p.scale.x)&&std::isfinite(p.scale.y)&&std::isfinite(p.scale.z)&&p.scale.x>0&&p.scale.y>0&&p.scale.z>0,"Placement requires finite center and positive finite scale");
  const double x=p.rotation.x,y=p.rotation.y,z=p.rotation.z,w=p.rotation.w;const double norm=x*x+y*y+z*z+w*w;
  need(std::isfinite(norm)&&std::abs(norm-1)<=1e-4,"Placement requires a finite unit quaternion");
  references.emplace(p.asset_id,p.asset_sha256,p.pack_sha256);asset_ids.insert(p.asset_id);
 }
 const auto finite=[](Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z)&&std::max({std::abs(p.x),std::abs(p.y),std::abs(p.z)})<=1000000;};
 const auto asset_reference=[&](const AssetPackReference& a){validate_asset_pack_reference(a);references.emplace(a.asset_id,a.asset_sha256,a.pack_sha256);asset_ids.insert(a.asset_id);};
 std::set<std::string> gates{"main","service","pencil","bypass"};for(const auto& r:d.initial_records)if(r.type_id=="firstboot.Door")gates.insert(r.entity_id);for(const auto& f:d.fixtures)gates.insert(f.object.persistent_id);
 for(const auto& a:d.companions){
  id(a.entity_id);Writer name;name.text(a.name,true);need(finite(a.spawn),"Invalid companion spawn");if(a.model)asset_reference(*a.model);
  need(a.routes.nodes.size()<=256&&a.routes.edges.size()<=512,"Companion route graph exceeds profile");std::set<std::string> nodes;
  for(const auto& n:a.routes.nodes){Writer text;text.text(n.id,true);need(n.id.size()<=128&&finite(n.feet)&&nodes.insert(n.id).second,"Invalid/duplicate companion route node");}
  for(const auto& e:a.routes.edges){need(nodes.contains(e.from)&&nodes.contains(e.to)&&e.from!=e.to&&(e.door.empty()||gates.contains(e.door)),"Invalid companion route edge or gate");}
 }
 need(std::count_if(d.lights.begin(),d.lights.end(),[](const auto& l){return l.kind==FirstBootLightKind::directional;})<=1,"Content supports one authored directional light");
 for(const auto& l:d.lights){id(l.entity_id);Writer name;name.text(l.name,true);need(l.kind==FirstBootLightKind::directional||l.kind==FirstBootLightKind::point,"Unknown authored light kind");need(l.power==FirstBootLightPower::reserve||l.power==FirstBootLightPower::restored,"Unknown authored light power source");
  const auto length=static_cast<double>(l.direction.x)*l.direction.x+static_cast<double>(l.direction.y)*l.direction.y+static_cast<double>(l.direction.z)*l.direction.z;
  need(finite(l.position)&&finite(l.direction)&&std::abs(length-1)<=1e-4&&finite(l.color)&&l.color.x>=0&&l.color.x<=1&&l.color.y>=0&&l.color.y<=1&&l.color.z>=0&&l.color.z<=1&&std::isfinite(l.intensity)&&l.intensity>=0&&l.intensity<=100&&std::isfinite(l.radius)&&l.radius>.05f&&l.radius<=500,"Invalid authored light parameters");
 }
 for(const auto& m:d.memories){id(m.entity_id);Writer name;name.text(m.name,true);need(finite(m.position),"Invalid memory interaction position");asset_reference(m.audio);}
 need(references.size()<=32,"Content unique asset reference limit");
 need(d.placements.size()+d.memories.size()+std::count_if(d.companions.begin(),d.companions.end(),[](const auto& a){return a.model.has_value();})<=64,"Content total dependency reference limit");
 for(const auto& asset_id:asset_ids)need(!unique.contains(asset_id),"Asset definition UUID collides with a chapter or placement identity");
 for(const auto& region:{d.hub,d.pencil}){need(std::isfinite(region.center.x)&&std::isfinite(region.center.y)&&std::isfinite(region.center.z)&&region.half_extent.x>0&&region.half_extent.y>0&&region.half_extent.z>0&&region.half_extent.x<=500&&region.half_extent.y<=500&&region.half_extent.z<=500,"Invalid content region");}
 need(!d.jenison_returns.empty()&&d.jenison_returns.size()<=128&&!d.hub_returns.empty()&&d.hub_returns.size()<=128&&d.hints.size()<=32,"Content anchor/hint limit");
 const std::set<std::string> cues{"adam.danger","adam.bypass_open","adam.bypass_power","adam.pencil","adam.shelter","adam.repaired_isolated","adam.repaired_connected","adam.isolated","adam.live_fault"};
 for(const auto& [key,value]:d.hints){(void)value;need(cues.contains(key)||key.starts_with("inspect.")||key==first_boot_initial_view_key||key==opening_workshop_hint_key,"Unknown authored guidance cue");}
 // Pure projection only: ownership, complete triples and modern profile are
 // validated without calling FirstBootContent::create or creating a link cycle.
 const auto workshop=first_boot_content_workshop_binding(d);std::set<std::string> workshop_ids;
 if(workshop){need(d.format_version==3&&d.asset_profile==AssetContentProfile::warm_beginning,"Workshop requires AIBD3 warm_beginning");for(const auto& owned:workshop->fixtures){
  const auto f=std::find_if(d.fixtures.begin(),d.fixtures.end(),[&](const auto& item){return item.object.persistent_id==owned;});
  need(f!=d.fixtures.end()&&f->role==FixtureRole::workshop&&f->object.selectable,"Workshop binding requires five owned selectable workshop fixtures");
  need(!d.hints.contains("inspect."+owned+".text")&&!d.hints.contains("inspect."+owned+".source")&&!d.hints.contains("inspect."+owned+".action"),"Workshop mechanisms cannot also be read/seat panels");workshop_ids.insert(owned);
 }const auto bench=std::find_if(d.fixtures.begin(),d.fixtures.end(),[&](const auto& item){return item.object.persistent_id==workshop->fixtures[4];});const Vec3 bench_feet{bench->object.center.x,d.hub_returns.front().y,bench->object.center.z};need(inside(d.hub,bench_feet)&&!inside(d.pencil,bench_feet),"Workshop bench must belong to the shelter");}
 for(const auto& f:d.fixtures){need(f.role==FixtureRole::legacy||f.role==FixtureRole::workshop,"Unknown fixture role");need((f.role==FixtureRole::workshop)==workshop_ids.contains(f.object.persistent_id),"Workshop fixture role and binding must be changed atomically");}
 (void)OpeningInspectionCatalog(d);
 (void)first_boot_initial_view(d);
 for(auto p:d.hub_returns)need(inside(d.hub,p)&&!inside(d.pencil,p),"Shelter return must be in the hub");
 const auto& progress=find(d,"firstboot.ChapterProgress");
 need(Vec3{static_cast<float>(std::get<double>(progress.fields.at("spawn_x"))),static_cast<float>(std::get<double>(progress.fields.at("spawn_y"))),static_cast<float>(std::get<double>(progress.fields.at("spawn_z")))}==d.hub_returns.front(),"Primary shelter return must match its authored spawn witness");
 for(auto p:d.jenison_returns)need(!inside(d.hub,p)&&!inside(d.pencil,p),"Jenison return must remain outside refuge");
 const auto& npc=find(d,"firstboot.NPCQuest");const auto provenance=std::get<std::string>(npc.fields.at("source"));need(provenance.starts_with("fictional.")||provenance.starts_with("authored."),"Verified memoir attribution needs an explicit source adapter");
 (void)encode(d);
}
void validate_physical_dependencies(const FirstBootContent& content){
 auto state=recovery(content);const auto& d=content.definition();
 if(const auto initial=first_boot_initial_view(d)){
  const auto closed=first_boot_content_scene(state,content);PlayerController player(closed,d.jenison_returns.front());
  for(unsigned tick=0;tick<30;++tick)player.update({},1./60);
  need(player.state().grounded&&frame_first_boot_initial_view(player,closed,*initial),"Initial view target must be visible from the supported Jenison return with doors closed");
 }
 if(!d.companions.empty()){const auto closed=first_boot_content_scene(state,content);for(const auto& a:d.companions){const GuideController guide(closed,a.spawn,a.routes);(void)guide;}}
 for(auto& r:state.components)if(r.type_id=="firstboot.Door"){r.fields["open"]=true;r.fields["unlocked"]=true;}
 const auto scene=first_boot_content_scene(state,content);
 for(const auto& door:d.initial_records)if(door.type_id=="firstboot.Door"){
  const auto x=static_cast<float>(std::get<double>(door.fields.at("x"))),z=static_cast<float>(std::get<double>(door.fields.at("z")));
  const auto y=static_cast<float>(std::get<double>(door.fields.at("y"))-std::get<double>(door.fields.at("half_y"))+.2);
  const auto role=std::get<std::string>(door.fields.at("role"));const Vec3 front{x,y,z-1.6f},back{x,y,z+1.6f};
  need(first_boot_content_locate(content,front)==(role=="pencil"?"hub":"jenison")&&first_boot_content_locate(content,back)==(role=="pencil"?"pencil":"hub"),"Door aperture no longer connects its declared regions");
  for(const bool reverse:{false,true}){GroundedCharacter body(scene,reverse?back:front);CharacterInput input;input.move={0,0,reverse?-1.f:1.f};for(int i=0;i<32;++i)body.advance(input,1.0/60);const auto result=body.state();need(result.grounded&&(reverse?result.feet.z<z-.7f:result.feet.z>z+.7f),"Authored door route is blocked or unsupported");}
 }
 auto anchor=[&](Vec3 p,const char* region){need(first_boot_content_locate(content,{p.x,p.y+.2f,p.z})==region,"Interaction anchor is outside its declared region");
  bool reachable=false;for(const auto offset:{Vec3{2.5f,0,0},Vec3{-2.5f,0,0},Vec3{0,0,2.5f},Vec3{0,0,-2.5f}}){try{GroundedCharacter body(scene,{p.x+offset.x,p.y+.2f,p.z+offset.z});for(int i=0;i<24;++i)body.advance({},1.0/60);const auto s=body.state();if(s.grounded&&std::abs(s.feet.y-p.y)<.5f)reachable=true;}catch(const std::invalid_argument&) {}}
  need(reachable,"Interaction anchor has no supported local approach");};
 const auto& fault=find(d,"firstboot.PowerFault");const auto& npc=find(d,"firstboot.NPCQuest");
 auto p=[](const ComponentRecord& r,const std::string& prefix){return Vec3{static_cast<float>(std::get<double>(r.fields.at(prefix+"x"))),static_cast<float>(std::get<double>(r.fields.at(prefix+"y"))),static_cast<float>(std::get<double>(r.fields.at(prefix+"z")))};};
 anchor(p(fault,""),"jenison");anchor(d.isolation_switch,"jenison");anchor(p(fault,"socket_"),"jenison");anchor(p(npc,""),"hub");anchor(p(npc,"lamp_"),"hub");
 if(const auto workshop=first_boot_content_workshop_binding(d)){
  auto visible_scene=scene;for(auto& object:visible_scene.objects)object.selectable=true;
  for(std::size_t slot=0;slot<workshop->fixtures.size();++slot){const auto fixture=std::find_if(d.fixtures.begin(),d.fixtures.end(),[&](const auto& f){return f.object.persistent_id==workshop->fixtures[slot];});const auto target=fixture->object.center;bool reached=false;
   const auto floor=(slot==4?d.hub_returns.front():d.jenison_returns.front()).y;
   for(const auto offset:{Vec3{1.2f,0,0},Vec3{-1.2f,0,0},Vec3{0,0,1.2f},Vec3{0,0,-1.2f},Vec3{2.5f,0,0},Vec3{-2.5f,0,0},Vec3{0,0,2.5f},Vec3{0,0,-2.5f}}){try{
    GroundedCharacter body(scene,{target.x+offset.x,floor,target.z+offset.z});for(unsigned tick=0;tick<24;++tick)body.advance({},1./60);const auto standing=body.state();if(!standing.grounded||first_boot_content_locate(content,standing.feet)!=(slot==4?"hub":"jenison"))continue;
    const Vec3 eye{standing.feet.x,standing.feet.y+.9f,standing.feet.z};const auto hit=pick_scene(visible_scene,eye,{target.x-eye.x,target.y-eye.y,target.z-eye.z},3.2f);
    if(hit&&hit->persistent_id==fixture->object.persistent_id){reached=true;break;}
   }catch(const std::invalid_argument&) {}}
   need(reached,"Workshop station has no grounded visible local interaction approach");
  }
 }

}
}
struct FirstBootContent::Data {FirstBootContentDefinition definition;std::vector<unsigned char> bytes;std::string fingerprint;};
const FirstBootContentDefinition& FirstBootContent::definition()const noexcept{return data_->definition;}
const std::string& FirstBootContent::fingerprint()const noexcept{return data_->fingerprint;}
std::optional<OpeningWorkshopBinding> first_boot_content_workshop_binding(const FirstBootContentDefinition& d){const auto found=d.hints.find(std::string(opening_workshop_hint_key));if(found==d.hints.end())return {};return decode_opening_workshop_binding(found->second);}
OpeningWorkshopCircuit first_boot_content_workshop_circuit(const GameplayStoreRecovery& s,const FirstBootContent& c){
 const auto& authored=find(c.definition(),"firstboot.PowerFault");const auto fault=std::find_if(s.components.begin(),s.components.end(),[&](const auto& r){return r.entity_id==authored.entity_id&&r.type_id=="firstboot.PowerFault";});need(fault!=s.components.end(),"Workshop fault source missing");
 OpeningWorkshopCircuit value;value.fault_id=fault->entity_id;value.capacity=std::get<double>(fault->fields.at("capacity"));value.isolated=std::get<bool>(fault->fields.at("isolated"));value.bypass_connected=std::get<bool>(fault->fields.at("bypass_connected"));value.relay_id=std::get<std::string>(fault->fields.at("bypass_relay"));
 if(!value.relay_id.empty()){const auto relay=std::find_if(s.components.begin(),s.components.end(),[&](const auto& r){return r.entity_id==value.relay_id&&r.type_id=="firstboot.Node";});if(relay!=s.components.end()){need(std::get<double>(relay->fields.at("firstboot.kind"))==6,"Workshop relay source is not a relay");value.relay_alive=std::get<bool>(relay->fields.at("alive"));value.relay_capacity=std::get<double>(relay->fields.at("capacity"));}}
 (void)opening_workshop_signature(value);return value;
}
std::string first_boot_content_workshop_hint(const GameplayStoreRecovery& s,const FirstBootContent& c){
 const auto binding=first_boot_content_workshop_binding(c.definition());if(!binding)return {};
 const auto found=std::find_if(s.components.begin(),s.components.end(),[&](const auto& r){return r.entity_id==binding->fixtures[4]&&r.type_id==opening_workshop_component_type;});need(found!=s.components.end(),"Workshop progress missing");const auto source=first_boot_content_workshop_circuit(s,c);validate_opening_workshop_record(*found,*binding,source.fault_id);
 if(!std::get<bool>(found->fields.at("has_probe")))return "Authored Adam hint: The diagnostic probe is in the reserve nook. You choose when to pick it up.";
 if(std::get<std::string>(found->fields.at("supply_sample")).empty())return "Authored Adam hint: Sample the supply contact. The probe reports what is actually connected.";
 if(std::get<std::string>(found->fields.at("path_sample")).empty())return "Authored Adam hint: Now sample the path contact near the bypass bench. Both routes are still yours.";
 if(std::get<bool>(found->fields.at("bench_claimed")))return opening_workshop_online(*found,*binding,source)?"Authored Adam hint: Your claimed workbench is online. That connection holds.":"Authored Adam hint: The bench is still yours, but its present feed needs power and a current test.";
 if(std::get<std::string>(found->fields.at("tested_signature"))!=opening_workshop_signature(source))return "Authored Adam hint: Repair or build your chosen feed, then test its present connection at the tester.";
 return "Authored Adam hint: This feed passed its test. Commission the workbench inside the shelter.";
}
bool first_boot_content_runtime_field(const std::string& type,const std::string& id){
 if(type==opening_workshop_assembly_component_type)return id=="collected"||id=="available"||id=="legacy";
 if(type==opening_workshop_component_type)return id=="has_probe"||id=="supply_sample"||id=="path_sample"||id=="tested_signature"||id=="bench_claimed";
 if(type=="firstboot.Door")return id=="open"||id=="unlocked";
 if(type=="firstboot.PowerFault")return id=="diagnosed"||id=="isolated"||id=="capacity"||id=="bypass_connected"||id=="bypass_relay";
 if(type=="firstboot.ChapterProgress")return id=="state"||id=="step"||id=="shelter_secured"||id=="pencil_visited"||id=="repair_used"||id=="bypass_used"||id=="first_route"||id=="returns"||id=="departures"||id=="recoveries"||id=="last_recovery_activation"||id=="last_recovery_cycle";
 if(type=="firstboot.NPCQuest")return id=="state"||id=="step"||id=="lamp_connected"||id=="hint_seen";
 return false;
}
std::vector<ComponentSchema> first_boot_content_schemas(){auto result=first_boot_chapter_schemas();result.push_back({binding_type,1,{{"definition_id",GameplayValueKind::text},{"revision",GameplayValueKind::text},{"fingerprint",GameplayValueKind::text}}});return result;}
std::vector<ComponentSchema> first_boot_content_schemas(const FirstBootContent& c){auto result=first_boot_content_schemas();if(!c.definition().companions.empty())result.push_back({companion_type,1,{{"follow",GameplayValueKind::boolean},{"anchor_x",GameplayValueKind::number,true,-1000000,1000000},{"anchor_y",GameplayValueKind::number,true,-1000000,1000000},{"anchor_z",GameplayValueKind::number,true,-1000000,1000000}}});if(first_boot_content_workshop_binding(c.definition()))result.push_back(opening_workshop_schema());return result;}
std::vector<ComponentSchema> first_boot_content_relay_assembly_schemas(const FirstBootContent& c){auto result=first_boot_content_schemas(c);if(first_boot_content_workshop_binding(c.definition()))result.push_back(opening_workshop_assembly_schema());return result;}
FirstBootRelayAssemblyState first_boot_content_relay_assembly(const GameplayStoreRecovery& s,const FirstBootContent& c){
 first_boot_content_check_binding(s,c);FirstBootRelayAssemblyState result;
 const auto binding=first_boot_content_workshop_binding(c.definition());if(!binding)return result;
 const ComponentRecord* assembly=nullptr;const ComponentRecord* progress=nullptr;bool retained_relay=false;
 for(const auto& r:s.components){
  if(r.type_id==opening_workshop_assembly_component_type)assembly=&r;
  if(r.type_id==opening_workshop_component_type)progress=&r;
  if(r.type_id=="firstboot.Node"&&std::get<double>(r.fields.at("firstboot.kind"))==6){retained_relay=true;if(std::get<bool>(r.fields.at("alive")))++result.alive_relays;}
 }
 result.initialized=assembly!=nullptr;result.legacy=assembly?std::get<bool>(assembly->fields.at("legacy")):retained_relay;
 result.part_available=assembly&&std::get<bool>(assembly->fields.at("available"));
 result.pickup_available=!assembly&&result.alive_relays==0&&progress&&!std::get<std::string>(progress->fields.at("path_sample")).empty();
 return result;
}
ComponentRecord first_boot_content_companion_component(const FirstBootCompanionBinding& binding,const GuideIntentRecord& intent){
 need(intent.intent==GuideIntent::follow||intent.intent==GuideIntent::wait,"Unknown durable companion intent");
 ComponentRecord record{binding.entity_id,companion_type,1,{{"follow",intent.intent==GuideIntent::follow},{"anchor_x",static_cast<double>(intent.waiting_anchor.x)},{"anchor_y",static_cast<double>(intent.waiting_anchor.y)},{"anchor_z",static_cast<double>(intent.waiting_anchor.z)}}};
 (void)companion_intent(record);return record;
}
GameplayStoreBaseline first_boot_content_baseline(const FirstBootContent& c){GameplayStoreBaseline b;for(const auto& [alias,e]:c.definition().hardware){(void)alias;auto records=durable_first_boot_components(e);b.components.insert(b.components.end(),records.begin(),records.end());}b.components.insert(b.components.end(),c.definition().initial_records.begin(),c.definition().initial_records.end());b.components.push_back({c.definition().binding_id,binding_type,1,{{"definition_id",c.definition().definition_id},{"revision",std::to_string(c.definition().revision)},{"fingerprint",c.fingerprint()}}});for(const auto& a:c.definition().companions)b.components.push_back(first_boot_content_companion_component(a,{a.initial_follow?GuideIntent::follow:GuideIntent::wait,a.spawn}));if(const auto workshop=first_boot_content_workshop_binding(c.definition()))b.components.push_back(opening_workshop_initial(*workshop));return b;}
void first_boot_content_check_binding(const GameplayStoreRecovery& s,const FirstBootContent& c){
 need(s.scope.context==GameplayContext::player_world||s.scope.context==GameplayContext::temporary_play,"Content requires a runtime/isolated-Play context");
 need(s.scope.world_id==c.definition().world_id,"Content world binding mismatch");unsigned bindings=0;
 for(const auto& r:s.components)if(r.type_id==binding_type){++bindings;need(r.version==1&&r.entity_id==c.definition().binding_id&&r.fields==std::map<std::string,GameplayValue>{{"definition_id",c.definition().definition_id},{"revision",std::to_string(c.definition().revision)},{"fingerprint",c.fingerprint()}},"Content definition/revision/fingerprint mismatch");}
 need(bindings==1,"Exactly one immutable content binding is required");
 unsigned companions=0;for(const auto& r:s.components)if(r.type_id==companion_type){++companions;need(c.definition().format_version>=3&&c.definition().companions.size()==1&&r.entity_id==c.definition().companions.front().entity_id,"Undeclared or foreign companion intent");(void)companion_intent(r);}
 need(companions==c.definition().companions.size(),"Exactly the declared companion intent is required");
 const auto workshop=first_boot_content_workshop_binding(c.definition());unsigned workshops=0;
 for(const auto& r:s.components)if(r.type_id==opening_workshop_component_type){++workshops;need(workshop.has_value(),"Undeclared workshop runtime component");validate_opening_workshop_record(r,*workshop,first_boot_content_workshop_circuit(s,c).fault_id);}
 need(workshops==(workshop?1u:0u),"Exactly the declared workshop component is required");
 unsigned assemblies=0;const ComponentRecord* assembly=nullptr;
 for(const auto& r:s.components)if(r.type_id==opening_workshop_assembly_component_type){++assemblies;need(workshop.has_value(),"Undeclared Workshop relay assembly");validate_opening_workshop_assembly(r,*workshop);assembly=&r;}
 need(assemblies<=1,"Duplicate Workshop relay assembly");
 if(assembly){unsigned living=0;for(const auto& r:s.components)if(r.type_id=="firstboot.Node"&&std::get<double>(r.fields.at("firstboot.kind"))==6&&std::get<bool>(r.fields.at("alive")))++living;
  need(std::get<bool>(assembly->fields.at("available"))==(living==0),"Finite relay part contradicts existing living relay occupancy");}
 std::map<std::string,const ComponentRecord*> nodes;for(const auto& r:s.components)if(r.type_id=="firstboot.Node")need(nodes.emplace(r.entity_id,&r).second,"Duplicate content hardware UUID");
 for(const auto& [alias,e]:c.definition().hardware){(void)alias;const auto found=nodes.find(e.persistent_id);need(found!=nodes.end(),"Authored hardware identity was removed");const auto expected=durable_first_boot_components(e).front();for(const auto& [key,value]:expected.fields)if(key!="capacity"&&key!="alive")need(found->second->fields.at(key)==value,"Runtime cannot rewrite authored hardware");nodes.erase(found);}
 for(const auto& [id,r]:nodes){(void)id;need(std::get<double>(r->fields.at("firstboot.kind"))==6,"Runtime hardware must be an actual constructed relay");}
}
std::optional<GuideIntentRecord> first_boot_content_companion_intent(const GameplayStoreRecovery& s,const FirstBootContent& c){
 first_boot_content_check_binding(s,c);if(c.definition().companions.empty())return std::nullopt;
 for(const auto& r:s.components)if(r.type_id==companion_type)return companion_intent(r);
 throw std::invalid_argument("Declared companion intent is missing");
}
std::string first_boot_content_locate(const FirstBootContent& c,Vec3 p){need(std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z),"Invalid content region point");if(inside(c.definition().pencil,p))return "pencil";return inside(c.definition().hub,p)?"hub":"jenison";}
FirstBootContent FirstBootContent::from_template(const CreatorSession& source){
 durable_first_boot_validate_source(source);const auto baseline=first_boot_chapter_baseline(source);GameplayStoreRecovery s{{source.project_id(),source.world_id(),source.branch_id(),new_uuid(),GameplayContext::player_world},baseline.revision,baseline.sequence,baseline.components};
 const auto install=first_boot_chapter_install(s);need(install.has_value(),"Template installation unavailable");for(const auto& delta:install->deltas)s.components.push_back(delta.component);
 s.revision=install->revision;s.sequence=install->events.back().sequence;const auto ids=first_boot_chapter_ids(s);const auto scene=first_boot_chapter_scene(s);
 FirstBootContentDefinition d;d.definition_id=new_uuid();d.world_id=source.world_id();d.binding_id=new_uuid();d.hardware=source.world();for(const auto& delta:install->deltas)d.initial_records.push_back(delta.component);
 double x=0,y=0,z=0,hx=0,hz=0;for(const auto& [alias,e]:source.world()){(void)alias;if(e.fields.at("firstboot.kind")==1){x=e.fields.at("x");y=e.fields.at("y")+e.fields.at("half_y");z=e.fields.at("z");hx=e.fields.at("half_x")-.5;hz=e.fields.at("half_z")-.5;}}
 auto p=[&](double a,double b,double c){return Vec3{static_cast<float>(x+a),static_cast<float>(y+b),static_cast<float>(z+c)};};
 d.hub={p(-36.5,.325,8.5),{7.5f,.425f,4.5f}};d.pencil={p(-36.5,.325,16.75),{7.5f,.425f,3.75f}};
 d.jenison_returns={p(-32,.2,-25)};d.hub_returns={p(-36.5,.2,7)};d.isolation_switch=p(-35.5,0,-3);
 for(int row=0;row<5;++row)for(int column=0;column<7;++column)d.hub_returns.push_back(p(-43.2+column*2,.2,5.2+row*1.6));
 for(int row=0;row<9;++row)for(int column=0;column<9;++column){const auto candidate=p(-hx+2*hx*column/8,.2,-hz+2*hz*row/8);if(!inside(d.hub,candidate)&&!inside(d.pencil,candidate))d.jenison_returns.push_back(candidate);}
 for(const auto& o:scene.objects)if(o.persistent_id==ids.progress){auto fixture=o;fixture.persistent_id=new_uuid();d.fixtures.push_back({fixture,o.name=="Sheltered workshop floor"?.2f:o.name=="Pencil and blank page"?.4f:-1.f});}
 return create(std::move(d));
}
FirstBootContent FirstBootContent::create(FirstBootContentDefinition d){
 std::sort(d.initial_records.begin(),d.initial_records.end(),[](const auto& a,const auto& b){return a.entity_id<b.entity_id;});std::sort(d.fixtures.begin(),d.fixtures.end(),[](const auto& a,const auto& b){return a.object.persistent_id<b.object.persistent_id;});std::sort(d.placements.begin(),d.placements.end(),[](const auto& a,const auto& b){return a.entity_id<b.entity_id;});validate_defaults(d);
 // Modern bindings have stable identity order; route node/edge order remains
 // authored because deterministic BFS uses that order to resolve equal paths.
 std::sort(d.companions.begin(),d.companions.end(),[](const auto& a,const auto& b){return a.entity_id<b.entity_id;});std::sort(d.lights.begin(),d.lights.end(),[](const auto& a,const auto& b){return a.entity_id<b.entity_id;});std::sort(d.memories.begin(),d.memories.end(),[](const auto& a,const auto& b){return a.entity_id<b.entity_id;});
 auto data=std::make_shared<Data>();data->definition=std::move(d);data->bytes=encode(data->definition);data->fingerprint=digest(data->bytes);FirstBootContent result(data);
 auto state=recovery(result);first_boot_content_validate(state,result);
 for(auto& r:state.components)if(r.type_id=="firstboot.ChapterProgress"){r.fields["shelter_secured"]=true;r.fields["first_route"]=std::string("alternative");r.fields["step"]=std::string("hub");}
 first_boot_content_validate(state,result);validate_physical_dependencies(result);return result;
}
std::vector<unsigned char> first_boot_content_encode(const FirstBootContent& c){return c.data_->bytes;}
FirstBootContent first_boot_content_decode(std::span<const unsigned char> bytes){
 need(bytes.size()<=creator_payload::maximum_bytes,"Content byte limit");Reader r{bytes};need(r.number(4)==0x44424941,"Unsupported content definition");const auto version=r.number(2);need(version>=1&&version<=3,"Unsupported content definition version");FirstBootContentDefinition d;d.format_version=static_cast<std::uint16_t>(version);d.definition_id=r.text(true);d.world_id=r.text(true);d.binding_id=r.text(true);d.revision=r.number(8);
 auto count=r.number(4);need(count<=512,"Content hardware limit");for(std::uint64_t i=0;i<count;++i){Entity e;e.id=r.text(true);e.name=r.text();e.persistent_id=r.text(true);auto fields=r.number(4);need(fields<=64,"Content field limit");for(std::uint64_t j=0;j<fields;++j){auto key=r.text(true);auto value=r.real();need(e.fields.emplace(key,value).second,"Duplicate content field");}need(d.hardware.emplace(e.id,e).second,"Duplicate content hardware");}
 count=r.number(4);need(count==6,"Content role count");for(std::uint64_t i=0;i<count;++i)d.initial_records.push_back(gameplay_codec::decode_component(raw(r)));
 count=r.number(4);need(count<=512,"Content fixture limit");for(std::uint64_t i=0;i<count;++i){FirstBootContentFixture f;auto& o=f.object;o.persistent_id=r.text(true);o.name=r.text();o.center=point(r);o.half_extent=point(r);o.color=point(r);o.emission=static_cast<float>(r.real());const auto selected=r.number(1);need(selected<=2,"Invalid content selection flag");f.role=selected==2?FixtureRole::workshop:FixtureRole::legacy;o.selectable=selected!=0;o.rotation.x=static_cast<float>(r.real());o.rotation.y=static_cast<float>(r.real());o.rotation.z=static_cast<float>(r.real());o.rotation.w=static_cast<float>(r.real());f.sheltered_emission=static_cast<float>(r.real());d.fixtures.push_back(f);}
 d.hub={point(r),point(r)};d.pencil={point(r),point(r)};for(auto* list:{&d.jenison_returns,&d.hub_returns}){count=r.number(4);need(count>0&&count<=128,"Content return limit");for(std::uint64_t i=0;i<count;++i)list->push_back(point(r));}
 d.isolation_switch=point(r);count=r.number(4);need(count<=32,"Content hint limit");for(std::uint64_t i=0;i<count;++i){auto key=r.text(true);auto value=r.text(true);need(d.hints.emplace(key,value).second,"Duplicate content hint");}
 if(version>=2){count=r.number(4);need(count<=64,"Content asset placement limit");for(std::uint64_t i=0;i<count;++i){FirstBootAssetPlacement p;p.entity_id=r.text(true);p.name=r.text(true);p.asset_id=r.text(true);p.asset_sha256=r.text(true);p.pack_sha256=r.text(true);p.center=point(r);p.scale=point(r);p.rotation.x=static_cast<float>(r.real());p.rotation.y=static_cast<float>(r.real());p.rotation.z=static_cast<float>(r.real());p.rotation.w=static_cast<float>(r.real());const auto selected=r.number(1);need(selected<=1,"Invalid placement selection flag");p.selectable=selected==1;d.placements.push_back(std::move(p));}}
 if(version>=3){
  const auto profile=r.number(1);need(profile<=1,"Unknown content asset profile");d.asset_profile=static_cast<AssetContentProfile>(profile);d.exposure=static_cast<float>(r.real());
  const auto flag=[&](const char* why){const auto n=r.number(1);need(n<=1,why);return n==1;};
  count=r.number(4);need(count<=1,"Content companion limit");for(std::uint64_t i=0;i<count;++i){FirstBootCompanionBinding a;a.entity_id=r.text(true);a.name=r.text(true);a.spawn=point(r);a.initial_follow=flag("Invalid companion initial intent");if(flag("Invalid companion model flag"))a.model=reference(r);
   auto n=r.number(4);need(n<=256,"Companion route node limit");for(std::uint64_t j=0;j<n;++j)a.routes.nodes.push_back({r.text(true),point(r)});
   n=r.number(4);need(n<=512,"Companion route edge limit");for(std::uint64_t j=0;j<n;++j){GuideRouteEdge e;e.from=r.text(true);e.to=r.text(true);e.door=r.text();e.bidirectional=flag("Invalid companion route direction flag");a.routes.edges.push_back(std::move(e));}d.companions.push_back(std::move(a));
  }
  count=r.number(4);need(count<=32,"Authored light limit");for(std::uint64_t i=0;i<count;++i){FirstBootLightDefinition l;l.entity_id=r.text(true);l.name=r.text(true);l.kind=static_cast<FirstBootLightKind>(r.number(1));l.power=static_cast<FirstBootLightPower>(r.number(1));l.position=point(r);l.direction=point(r);l.color=point(r);l.intensity=static_cast<float>(r.real());l.radius=static_cast<float>(r.real());d.lights.push_back(std::move(l));}
  count=r.number(4);need(count<=8,"Memory binding limit");for(std::uint64_t i=0;i<count;++i){FirstBootMemoryBinding m;m.entity_id=r.text(true);m.name=r.text(true);m.position=point(r);m.audio=reference(r);d.memories.push_back(std::move(m));}
 }
 need(r.offset==bytes.size(),"Trailing content bytes");auto result=FirstBootContent::create(std::move(d));need(first_boot_content_encode(result)==std::vector<unsigned char>(bytes.begin(),bytes.end()),"Non-canonical content definition");return result;
}
FirstBootContentPreview first_boot_content_preview(const FirstBootContent& before,FirstBootContentDefinition proposed){
 FirstBootContentPreview p;try{
  need(proposed.format_version>=before.definition().format_version,"Content version cannot be downgraded by editing");
  auto next=FirstBootContent::create(std::move(proposed));need(next.definition().definition_id==before.definition().definition_id&&next.definition().world_id==before.definition().world_id,"Content identity requires an explicit new document");
  auto categories=[](const FirstBootContentDefinition& d){std::map<std::string,std::string> result;for(const auto& [alias,e]:d.hardware){(void)alias;result.emplace(e.persistent_id,"hardware");}for(const auto& r:d.initial_records)result.emplace(r.entity_id,r.type_id);for(const auto& f:d.fixtures)result.emplace(f.object.persistent_id,"fixture");for(const auto& p:d.placements)result.emplace(p.entity_id,"asset-placement");for(const auto& a:d.companions)result.emplace(a.entity_id,"companion");for(const auto& l:d.lights)result.emplace(l.entity_id,"light");for(const auto& m:d.memories)result.emplace(m.entity_id,"memory");return result;};
  const auto old_categories=categories(before.definition()),new_categories=categories(next.definition());for(const auto& [id,type]:new_categories){const auto old=old_categories.find(id);need(old==old_categories.end()||old->second==type,"Changed content cannot repurpose an existing UUID's category");}
  if(next.fingerprint()==before.fingerprint()){p.status=FirstBootContentPreviewStatus::compatible;p.save_compatible=true;p.message="Exact content identity/revision/fingerprint; existing bound save remains compatible";}
  else{need(next.definition().revision>before.definition().revision,"Changed content requires a newer retained revision");p.status=FirstBootContentPreviewStatus::new_play_branch;p.message="Changed content requires a new Play branch; old saves remain bound to their original definition and are not rewritten";
   const auto& a=before.definition();const auto& b=next.definition();std::set<std::string> affected;
   auto geometric=[](const std::string& key){return key=="x"||key=="y"||key=="z"||key=="firstboot.kind"||key.starts_with("half_")||key.starts_with("socket_")||key.starts_with("lamp_");};
   auto components=[&](const std::vector<ComponentRecord>& old,const std::vector<ComponentRecord>& current,bool hardware){
    std::map<std::string,const ComponentRecord*> left,right;for(const auto& r:old)left.emplace(r.entity_id,&r);for(const auto& r:current)right.emplace(r.entity_id,&r);std::set<std::string> ids;for(const auto& [id,r]:left){(void)r;ids.insert(id);}for(const auto& [id,r]:right){(void)r;ids.insert(id);}
    for(const auto& id:ids){const auto old_record=left.find(id),new_record=right.find(id);const bool missing=old_record==left.end()||new_record==right.end();if(!missing&&gameplay_codec::encode_component(*old_record->second)==gameplay_codec::encode_component(*new_record->second))continue;
     affected.insert(id);p.render_rebuild=true;if(missing)p.collision_rebuild=true;
     const auto& r=new_record!=right.end()?*new_record->second:*old_record->second;
     if(hardware||r.type_id=="firstboot.PowerFault"||r.type_id=="firstboot.Door")p.power_dependencies=true;
     if(r.type_id=="firstboot.NPCQuest"||r.type_id=="firstboot.ChapterProgress"||r.type_id=="firstboot.Door")p.quest_dependencies=true;
     if(!missing)for(const auto& [key,value]:r.fields)if(geometric(key)&&value!=old_record->second->fields.at(key))p.collision_rebuild=true;
    }
   };
   auto hardware=[](const World& world){std::vector<ComponentRecord> records;for(const auto& [alias,e]:world){(void)alias;records.push_back(durable_first_boot_components(e).front());}return records;};
   components(hardware(a.hardware),hardware(b.hardware),true);components(a.initial_records,b.initial_records,false);
   std::map<std::string,const FirstBootContentFixture*> left,right;for(const auto& f:a.fixtures)left.emplace(f.object.persistent_id,&f);for(const auto& f:b.fixtures)right.emplace(f.object.persistent_id,&f);std::set<std::string> ids;for(const auto& [id,f]:left){(void)f;ids.insert(id);}for(const auto& [id,f]:right){(void)f;ids.insert(id);}
   auto rotation=[](const Quaternion& q){return std::array{q.x,q.y,q.z,q.w};};
   for(const auto& id:ids){const auto old=left.find(id),current=right.find(id);if(old==left.end()||current==right.end()){affected.insert(id);p.render_rebuild=p.collision_rebuild=true;continue;}const auto& x=old->second->object;const auto& y=current->second->object;
    const bool geometry=x.center!=y.center||x.half_extent!=y.half_extent||rotation(x.rotation)!=rotation(y.rotation);
    if(geometry||x.name!=y.name||x.color!=y.color||x.emission!=y.emission||x.selectable!=y.selectable||old->second->role!=current->second->role||old->second->sheltered_emission!=current->second->sheltered_emission){affected.insert(id);p.render_rebuild=true;p.collision_rebuild=p.collision_rebuild||geometry;}}
   std::map<std::string,const FirstBootAssetPlacement*> old_placements,new_placements;
   for(const auto& item:a.placements)old_placements.emplace(item.entity_id,&item);for(const auto& item:b.placements)new_placements.emplace(item.entity_id,&item);
   std::set<std::string> placement_ids;for(const auto& [id,item]:old_placements){(void)item;placement_ids.insert(id);}for(const auto& [id,item]:new_placements){(void)item;placement_ids.insert(id);}
   for(const auto& id:placement_ids){const auto old=old_placements.find(id),current=new_placements.find(id);bool changed=old==old_placements.end()||current==new_placements.end();if(!changed){const auto& x=*old->second;const auto& y=*current->second;changed=x.name!=y.name||x.asset_id!=y.asset_id||x.asset_sha256!=y.asset_sha256||x.pack_sha256!=y.pack_sha256||x.center!=y.center||x.scale!=y.scale||rotation(x.rotation)!=rotation(y.rotation)||x.selectable!=y.selectable;}if(changed){affected.insert(id);p.render_rebuild=true;}}
   const auto modern_bindings=[&](const auto& old,const auto& current,auto write,bool quest){
    std::map<std::string,std::vector<unsigned char>> old_bytes,new_bytes;
    for(const auto& item:old){Writer w;write(w,item);old_bytes.emplace(item.entity_id,std::move(w.data));}for(const auto& item:current){Writer w;write(w,item);new_bytes.emplace(item.entity_id,std::move(w.data));}
    std::set<std::string> ids;for(const auto& [id,bytes]:old_bytes){(void)bytes;ids.insert(id);}for(const auto& [id,bytes]:new_bytes){(void)bytes;ids.insert(id);}
    for(const auto& id:ids){const auto x=old_bytes.find(id),y=new_bytes.find(id);if(x==old_bytes.end()||y==new_bytes.end()||x->second!=y->second){affected.insert(id);p.render_rebuild=true;p.quest_dependencies=p.quest_dependencies||quest;}}
   };
   modern_bindings(a.companions,b.companions,companion,true);modern_bindings(a.lights,b.lights,light,false);modern_bindings(a.memories,b.memories,memory,true);
   if(a.exposure!=b.exposure||a.asset_profile!=b.asset_profile||a.format_version!=b.format_version){p.render_rebuild=true;affected.insert(b.definition_id);}
   if(a.isolation_switch!=b.isolation_switch){p.render_rebuild=p.collision_rebuild=p.power_dependencies=true;affected.insert(find(b,"firstboot.PowerFault").entity_id);}
   auto same_region=[](const FirstBootContentRegion& x,const FirstBootContentRegion& y){return x.center==y.center&&x.half_extent==y.half_extent;};
   if(!same_region(a.hub,b.hub)||!same_region(a.pencil,b.pencil)||a.jenison_returns!=b.jenison_returns||a.hub_returns!=b.hub_returns){p.quest_dependencies=true;affected.insert(find(b,"firstboot.ChapterProgress").entity_id);}
   p.quest_dependencies=p.quest_dependencies||p.power_dependencies;if(a.hints!=b.hints||affected.empty())affected.insert(b.definition_id);p.affected_ids.assign(affected.begin(),affected.end());
   p.dependencies={"Both return states and all three actual bidirectional capsule door routes validated","Fault/switch/socket and NPC/lamp local supported approaches checked; no global pathfinding proof","Dirty flags identify affected subsystem dependencies; no automatic migration/navigation rebake"};}
  p.candidate=std::move(next);
 }catch(const std::exception& error){FirstBootContentPreview rejected;rejected.message=error.what();return rejected;}return p;
}
}
