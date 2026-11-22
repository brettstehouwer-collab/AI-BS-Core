#include <aibs/first_boot_chapter.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using namespace aibs;
namespace {
void require(bool value,const std::string& message) { if(!value)throw std::runtime_error(message); }
const ComponentRecord& record(const GameplayStoreRecovery& s,const std::string& id) {
 const auto found=std::find_if(s.components.begin(),s.components.end(),[&](const auto& r){return r.entity_id==id;});
 require(found!=s.components.end(),"Missing traversal record");return *found;
}
double number(const ComponentRecord& r,const char* field) {return std::get<double>(r.fields.at(field));}
bool flag(const GameplayStoreRecovery& s,const std::string& id,const char* field) {return std::get<bool>(record(s,id).fields.at(field));}
std::string text(const GameplayStoreRecovery& s,const std::string& id,const char* field) {return std::get<std::string>(record(s,id).fields.at(field));}
std::int64_t count(const GameplayStoreRecovery& s,const std::string& id,const char* field) {return std::get<std::int64_t>(record(s,id).fields.at(field));}
GameplayStoreRecovery apply(GameplayStoreRecovery s,const GameplayChangeBatch& batch) {
 s.revision=batch.revision;s.sequence=batch.events.back().sequence;
 for(const auto& delta:batch.deltas) {
  require(delta.action==ComponentAction::upsert,"Traversal retains tombstones");
  auto found=std::find_if(s.components.begin(),s.components.end(),[&](const auto& r){return r.entity_id==delta.component.entity_id;});
  if(found==s.components.end())s.components.push_back(delta.component);else *found=delta.component;
 }
 return s;
}
GameplayStoreRecovery installed() {
 CreatorSession source(first_boot_schema(),"chapter-body-traversal","main");require(seed_first_boot(source).ok,"Seed chapter world");
 const auto baseline=first_boot_chapter_baseline(source);
 GameplayStoreRecovery before{{source.project_id(),source.world_id(),source.branch_id(),source.world_id(),GameplayContext::player_world},baseline.revision,baseline.sequence,baseline.components};
 const auto batch=first_boot_chapter_install(before,"physical-traversal-install");require(batch.has_value(),"Install physical chapter");
 auto after=apply(before,*batch);first_boot_chapter_rules(before,after,*batch,{});return after;
}
FirstBootChapterCommand command(FirstBootChapterAction action,std::string target={}) {
 FirstBootChapterCommand result;result.action=action;result.target_id=std::move(target);return result;
}
class Walk {
public:
 GameplayStoreRecovery world=installed();
 FirstBootChapterIds ids=first_boot_chapter_ids(world);
 PlayerController player=first_boot_chapter_player(world);
 FirstBootChapterClock clock;
 Vec3 previous=player.state().feet;
 float x=0,z=0,top=0;
 unsigned ticks=0,regions=0;
 float minimum_ground_y=std::numeric_limits<float>::max(),maximum_ground_y=std::numeric_limits<float>::lowest();
 explicit Walk() {
  const auto board=std::find_if(world.components.begin(),world.components.end(),[](const auto& r){return r.type_id=="firstboot.Node"&&number(r,"firstboot.kind")==1;});
  require(board!=world.components.end(),"World board");x=static_cast<float>(number(*board,"x"));z=static_cast<float>(number(*board,"z"));top=static_cast<float>(number(*board,"y")+number(*board,"half_y"));
  (void)clock.sample(world);for(unsigned i=0;i<30;++i)step({});
  require(player.state().grounded,"Initial capsule settles on board");
 }
 FirstBootChapterActor actor() {
  FirstBootChapterActor a;a.previous_feet=previous;a.feet=player.state().feet;a.grounded=player.state().grounded;
  a.inspection_mode=player.inspection_mode();a.active_tick=clock.tick();a.hazard=clock.sample(world);return a;
 }
 void publish(const GameplayChangeBatch& batch,const FirstBootChapterActor& a) {
  auto after=apply(world,batch);first_boot_chapter_rules(world,after,batch,a);
  player.set_scene(first_boot_chapter_scene(after));world=std::move(after);
 }
 void action(FirstBootChapterCommand c) {
  const auto a=actor();const auto batch=first_boot_chapter_action(world,c,a);require(batch.has_value(),"Expected physical action");publish(*batch,a);
 }
 void step(WindowInput input) {
  previous=player.state().feet;player.update(input,1.0/60);clock.advance(1.0/60);++ticks;
  const auto state=player.state();require(std::isfinite(state.feet.y)&&state.feet.y>=top-.2f,"Continuous capsule retains board support");
  if(!state.grounded)return;
  minimum_ground_y=std::min(minimum_ground_y,state.feet.y-top);maximum_ground_y=std::max(maximum_ground_y,state.feet.y-top);
  const auto actual=first_boot_chapter_region(world,state.feet);
  if(actual==text(world,ids.progress,"step"))return;
  const auto kind=actual=="pencil"?FirstBootChapterAction::enter_pencil:actual=="hub"?FirstBootChapterAction::arrive_hub:FirstBootChapterAction::depart_hub;
  action(command(kind));++regions;
 }
 void toward(float relative_x,float relative_z,unsigned maximum) {
  const auto destination_x=x+relative_x,destination_z=z+relative_z;
  for(unsigned i=0;i<maximum;++i) {
   const auto p=player.state().feet;const float dx=destination_x-p.x,dz=destination_z-p.z,d=std::hypot(dx,dz);
   if(d<.14f)return;
   WindowInput input;input.right=dx/d;input.forward=dz/d;step(input);
  }
 }
 void to(float relative_x,float relative_z) {
  toward(relative_x,relative_z,800);const auto p=player.state().feet;
  require(std::hypot(p.x-(x+relative_x),p.z-(z+relative_z))<.2f,
          "Walk blocked toward ("+std::to_string(relative_x)+","+std::to_string(relative_z)+") at ("+std::to_string(p.x-x)+","+std::to_string(p.y-top)+","+std::to_string(p.z-z)+")");
  require(player.state().grounded,"Waypoint reached with grounded capsule");
 }
 void closed_door(float relative_x) {
  to(relative_x,1.9f);toward(relative_x,6,100);const auto p=player.state().feet;
  require(p.z-z>3.1f&&p.z-z<3.6f,"Closed door must physically stop actual capsule before aperture");
  require(!flag(world,ids.progress,"shelter_secured"),"Blocked movement cannot discover shelter");
  std::cout<<"  closed door stop z="<<p.z-z<<" grounded="<<player.state().grounded<<'\n';to(relative_x,1.9f);
 }
 void isolation(bool enabled) {auto c=command(FirstBootChapterAction::set_isolation);c.enabled=enabled;action(c);}
 GameplayStoreRecovery nodes() const {auto result=world;std::erase_if(result.components,[](const auto& r){return r.type_id!="firstboot.Node";});return result;}
};
void repair_traversal() {
 Walk w;
 // The west approach avoids the downstream fault and original core/power stages.
 w.to(-37,-25);w.to(-37,1.9f);w.to(-33,1.9f);w.closed_door(-33);
 w.to(-37,1.9f);w.to(-37,-5.2f);w.to(-35.5f,-5.2f);w.isolation(true);
 w.to(-33,-5.2f);w.action(command(FirstBootChapterAction::repair_fault));
 w.to(-35.5f,-5.2f);w.isolation(false);w.to(-37,-5.2f);w.to(-37,1.9f);w.to(-33,1.9f);
 w.action(command(FirstBootChapterAction::open_door,w.ids.main_door));w.to(-33,6);
 require(text(w.world,w.ids.progress,"first_route")=="repair"&&flag(w.world,w.ids.progress,"repair_used"),"Actual main aperture earns repair route");
 w.to(-33,8);w.to(-37,8);w.to(-37,10.7f);w.action(command(FirstBootChapterAction::open_door,w.ids.pencil_door));w.to(-37,15);
 require(flag(w.world,w.ids.progress,"pencil_visited")&&first_boot_chapter_region(w.world,w.player.state().feet)=="pencil","Actual capsule enters Pencil Room");
 // Walk clear room space, then return through both physical apertures.
 w.to(-34,16.5f);w.to(-31,18);w.to(-34,15);w.to(-37,15);w.to(-37,10.7f);w.to(-33,8);w.to(-33,1.9f);w.to(-33,6);
 require(count(w.world,w.ids.progress,"departures")==1&&count(w.world,w.ids.progress,"returns")==1,"Continuous leave/return produces one actual loop");
 require(w.regions>=5&&w.player.state().ticks==w.ticks,"All route segments use actual fixed-step capsule ticks");
 require(w.maximum_ground_y-w.minimum_ground_y>.04f,"Real route steps across raised motherboard traces and workshop floor");
 std::cout<<"PASS: continuous repair/Pencil/return ticks="<<w.ticks<<" regions="<<w.regions<<" ground_y="<<w.minimum_ground_y<<".."<<w.maximum_ground_y<<" final=("<<w.player.state().feet.x<<','<<w.player.state().feet.y<<','<<w.player.state().feet.z<<")\n";
}
void bypass_traversal() {
 Walk w;w.to(-37,-25);w.to(-37,-5.2f);w.to(-35.5f,-5.2f);w.isolation(true);w.to(-42,-5.2f);
 const auto& fault=record(w.world,w.ids.fault);
 const Vec3 socket{static_cast<float>(number(fault,"socket_x")),static_cast<float>(number(fault,"socket_y")+1.2),static_cast<float>(number(fault,"socket_z"))};
 const auto build=durable_first_boot_build(w.nodes(),socket,"physical-relay-build");const auto relay=std::get<ConstructionOutcome>(build.events.front().payload).entity_id;w.publish(build,w.actor());
 auto connect=command(FirstBootChapterAction::connect_bypass);connect.relay_id=relay;w.action(connect);
 w.to(-39.5f,-5.2f);w.to(-39.5f,1.9f);w.to(-41,1.9f);w.closed_door(-41);w.action(command(FirstBootChapterAction::open_door,w.ids.service_door));w.to(-41,6);
 require(text(w.world,w.ids.progress,"first_route")=="bypass"&&flag(w.world,w.ids.progress,"bypass_used")&&!flag(w.world,w.ids.progress,"repair_used"),"Actual service aperture earns separate bypass route");
 // Return to the real relay before removing supply. Its identity stays tombstoned.
 w.to(-41,1.9f);w.to(-39.5f,1.9f);w.to(-39.5f,-5.2f);w.to(-42,-5.2f);
 const auto dismantle=durable_first_boot_dismantle(w.nodes(),relay,"physical-relay-remove");require(dismantle.has_value(),"Living relay can be removed");w.publish(*dismantle,w.actor());
 w.to(-39.5f,-5.2f);w.to(-39.5f,1.9f);w.to(-41,1.9f);w.action(command(FirstBootChapterAction::close_door,w.ids.service_door));w.action(command(FirstBootChapterAction::open_door,w.ids.service_door));w.to(-41,6);
 require(!flag(w.world,relay,"alive")&&flag(w.world,w.ids.service_door,"unlocked")&&count(w.world,w.ids.progress,"returns")==1,"Actual unpowered latched service door permits return after relay removal");
 require(w.player.state().grounded&&w.player.state().ticks==w.ticks,"Bypass uses continuous supported fixed-step body");
 require(w.maximum_ground_y-w.minimum_ground_y>.04f,"Service route steps across real board details");
 std::cout<<"PASS: continuous bypass/dismantle/unpowered-return ticks="<<w.ticks<<" regions="<<w.regions<<" ground_y="<<w.minimum_ground_y<<".."<<w.maximum_ground_y<<" final=("<<w.player.state().feet.x<<','<<w.player.state().feet.y<<','<<w.player.state().feet.z<<")\n";
}
}
int main() {
 unsigned failures=0;
 for(const auto& [name,test]:{std::pair{"repair",repair_traversal},std::pair{"bypass",bypass_traversal}}) {
  try{test();}catch(const std::exception& error){++failures;std::cerr<<"FAIL: "<<name<<": "<<error.what()<<'\n';}
 }
 return failures?1:0;
}
