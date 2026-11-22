#include <aibs/content_lighting.hpp>
#include <aibs/gameplay_codec.hpp>
#include <aibs/engine.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {
unsigned checks=0;
void need(bool value,const char* message){if(!value)throw std::runtime_error(message);++checks;}
template<class F>void reject(F f){bool bad=false;try{f();}catch(const std::invalid_argument&){bad=true;}need(bad,"Expected chapter lighting rejection");}
const ComponentRecord& record(const GameplayStoreRecovery& s,const char* type,const char* role=""){
 for(const auto& r:s.components)if(r.type_id==type&&(!*role||std::get<std::string>(r.fields.at("role"))==role))return r;
 throw std::runtime_error("Test component absent");
}
float number(const ComponentRecord& r,const char* key){return static_cast<float>(std::get<double>(r.fields.at(key)));}
GameplayStoreRecovery state(const FirstBootContent& c){const auto b=first_boot_content_baseline(c);return {{"chapter-lighting",c.definition().world_id,"main",new_uuid(),GameplayContext::temporary_play},b.revision,b.sequence,b.components};}
GameplayStoreRecovery apply(GameplayStoreRecovery s,const GameplayChangeBatch& b){
 for(const auto& d:b.deltas){auto p=std::find_if(s.components.begin(),s.components.end(),[&](const auto& r){return r.entity_id==d.component.entity_id;});
  if(d.action==ComponentAction::erase){if(p!=s.components.end())s.components.erase(p);}else if(p==s.components.end())s.components.push_back(d.component);else *p=d.component;}
 s.revision=b.revision;s.sequence=b.events.back().sequence;return s;
}
FirstBootChapterActor actor(Vec3 p){FirstBootChapterActor a;a.previous_feet=a.feet=p;return a;}
void accept(GameplayStoreRecovery& s,const GameplayChangeBatch& b,const FirstBootChapterActor& a,const FirstBootContent& c){const auto next=apply(s,b);first_boot_content_rules(s,next,b,a,c);s=next;}
void command(GameplayStoreRecovery& s,const FirstBootContent& c,FirstBootChapterAction action,FirstBootChapterActor a,bool enabled=true,std::string target="",std::string relay=""){
 FirstBootChapterCommand q;q.action=action;q.enabled=enabled;q.target_id=std::move(target);q.relay_id=std::move(relay);q.operation_id=new_uuid();const auto b=first_boot_content_action(s,q,a,c);need(b.has_value(),"Actual chapter command produces transition");accept(s,*b,a,c);
}
void no_progress(const GameplayStoreRecovery& s){const auto& r=record(s,"firstboot.ChapterProgress");need(!std::get<bool>(r.fields.at("shelter_secured"))&&std::get<std::string>(r.fields.at("first_route"))=="none","Light evaluation must not grant shelter or a route");}
}
int main(){try{
 CreatorSession source(first_boot_schema(),"chapter-lighting","main");need(seed_first_boot(source).ok,"Seed chapter");
 const auto original=FirstBootContent::from_template(source);auto legacy=state(original);const auto disabled=first_boot_content_lighting(legacy,original);need(!disabled.enabled&&!disabled.directional&&disabled.points.empty(),"Legacy content retains prior rendering");
 auto d=original.definition();d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;d.exposure=1.75f;
 FirstBootLightDefinition reserve;reserve.entity_id=new_uuid();reserve.name="Nook reserve";reserve.position={-32,3,-25};reserve.color={1,.45f,.1f};reserve.intensity=2;reserve.radius=7;
 FirstBootLightDefinition circuit=reserve;circuit.entity_id=new_uuid();circuit.name="Restored work area";circuit.power=FirstBootLightPower::restored;circuit.position={-33,3,-3};circuit.color={.2f,.6f,1};circuit.intensity=4;circuit.radius=16;
 FirstBootLightDefinition key=circuit;key.entity_id=new_uuid();key.name="Restored directional key";key.kind=FirstBootLightKind::directional;key.direction={0,-1,0};key.color={.8f,.85f,1};key.intensity=.7f;
 d.lights={reserve,circuit,key};const auto c=FirstBootContent::create(d);auto s=state(c);const auto original_components=s.components;const auto original_revision=s.revision,original_sequence=s.sequence;
 const auto dark=first_boot_content_lighting(s,c);need(dark.enabled&&dark.points.size()==1&&!dark.directional&&!dark.shadow.enabled,"Before repair only reserve illumination is active");need(dark.exposure==d.exposure&&dark.ambient==Vec3{.02f,.02f,.02f},"Authored exposure and bounded ambient copied");need(dark.points.front().position==reserve.position&&dark.points.front().color==reserve.color&&dark.points.front().intensity==reserve.intensity,"Reserve light keeps exact authored parameters");
 const auto supply0=first_boot_content_supply(s,c);need(!supply0.main&&!supply0.bypass,"Faulted supply reports actual current state");
 need(s.components==original_components&&s.revision==original_revision&&s.sequence==original_sequence,"Lighting projection leaves components and history unchanged");no_progress(s);
 const auto& fault=record(s,"firstboot.PowerFault");const auto isolation=actor({d.isolation_switch.x,d.isolation_switch.y+.2f,d.isolation_switch.z});const auto repair_actor=actor({number(fault,"x"),number(fault,"y")+.2f,number(fault,"z")});const auto socket_actor=actor({number(fault,"socket_x"),number(fault,"socket_y")+.2f,number(fault,"socket_z")-2});const Vec3 socket{number(fault,"socket_x"),number(fault,"socket_y")+1.2f,number(fault,"socket_z")};
 command(s,c,FirstBootChapterAction::set_isolation,isolation);
 command(s,c,FirstBootChapterAction::repair_fault,repair_actor);
 need(!first_boot_content_supply(s,c).main&&first_boot_content_lighting(s,c)==dark,"Repair while isolated does not invent a live connection");
 command(s,c,FirstBootChapterAction::set_isolation,isolation,false);
 const auto repaired=first_boot_content_lighting(s,c);const auto supply1=first_boot_content_supply(s,c);need(supply1.main&&!supply1.bypass,"Reconnected repaired main is authoritative");need(repaired.points.size()==2&&repaired.directional.has_value()&&repaired.shadow.enabled&&repaired.shadow.resolution==1024,"Main supply enables restored point/key and one bounded shadow");need(repaired.directional->color==key.color&&repaired.directional->direction==key.direction,"Directional semantics retained");validate_scene_lighting(repaired);no_progress(s);
 const auto shadow_matrix=directional_shadow_matrix(repaired);
 for(const auto& object:first_boot_content_scene(s,c).objects)for(float x:{-1.f,1.f})for(float y:{-1.f,1.f})for(float z:{-1.f,1.f}){
  const Vec3 p{object.center.x+x*object.half_extent.x,object.center.y+y*object.half_extent.y,object.center.z+z*object.half_extent.z};
  std::array<float,4> clip{};for(unsigned column=0;column<4;++column)clip[column]=p.x*shadow_matrix[column]+p.y*shadow_matrix[4+column]+p.z*shadow_matrix[8+column]+shadow_matrix[12+column];
  need(std::abs(clip[0])<=1.00001f&&std::abs(clip[1])<=1.00001f&&clip[2]>=-.00001f&&clip[2]<=1.00001f&&clip[3]==1,"Authored shadow volume covers actual static chapter geometry");
 }
 need(std::find(repaired.points.begin(),repaired.points.end(),dark.points.front())!=repaired.points.end(),"Repair does not extinguish warm reserve");
 const auto door=record(s,"firstboot.Door","main");const auto doorway=actor({number(door,"x"),.2f,number(door,"z")-2});command(s,c,FirstBootChapterAction::open_door,doorway,true,door.entity_id);need(first_boot_content_lighting(s,c).points==repaired.points,"Opening a door does not fabricate a power change");command(s,c,FirstBootChapterAction::close_door,doorway,true,door.entity_id);need(first_boot_content_lighting(s,c).points==repaired.points,"Closing a door leaves circuit selection coherent");no_progress(s);
 command(s,c,FirstBootChapterAction::set_isolation,isolation,true);need(first_boot_content_lighting(s,c)==dark,"Isolation removes restored lights, retaining reserve");
 const auto built=first_boot_content_build(s,socket,socket_actor,c,new_uuid());accept(s,built,socket_actor,c);const auto relay=std::get<ConstructionOutcome>(built.events.front().payload).entity_id;
 need(!first_boot_content_supply(s,c).bypass&&first_boot_content_lighting(s,c)==dark,"A merely built relay is not a connected supply");
 command(s,c,FirstBootChapterAction::connect_bypass,socket_actor,true,"",relay);const auto bypass=first_boot_content_lighting(s,c);const auto supply2=first_boot_content_supply(s,c);need(!supply2.main&&supply2.bypass&&bypass.points==repaired.points&&bypass.directional==repaired.directional,"Actual connected live bypass lights the same authored circuits");no_progress(s);
 command(s,c,FirstBootChapterAction::disconnect_bypass,socket_actor);need(first_boot_content_lighting(s,c)==dark,"Disconnected relay cannot continue illuminating restored circuits");
 const auto dismantled=first_boot_content_dismantle(s,relay,socket_actor,c,new_uuid());need(dismantled.has_value(),"Dismantle actual owned relay");accept(s,*dismantled,socket_actor,c);need(!first_boot_content_supply(s,c).bypass&&first_boot_content_lighting(s,c)==dark,"Dismantled relay does not leave stale light state");no_progress(s);
 auto foreign=s;foreign.scope.world_id=new_uuid();reject([&]{first_boot_content_lighting(foreign,c);});
 const auto decoded=first_boot_content_decode(first_boot_content_encode(c));need(first_boot_content_lighting(s,decoded)==first_boot_content_lighting(s,c),"Codec restart preserves exact light projection");
 auto invalid=d;auto extra=key;extra.entity_id=new_uuid();invalid.lights.push_back(extra);reject([&]{FirstBootContent::create(invalid);});
 std::cout<<"PASS "<<checks<<" authored reserve/restored lighting, real repair/bypass actions, shadow bounds and read-only progression checks\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
