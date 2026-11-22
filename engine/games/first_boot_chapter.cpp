#include <aibs/first_boot_chapter.hpp>
#include <aibs/first_boot_content.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <charconv>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace aibs {
SceneSnapshot chapter_content_scene(const GameplayStoreRecovery&,const FirstBootContent*);
Vec3 chapter_content_return(const GameplayStoreRecovery&,const FirstBootContent*);
void chapter_content_validate(const GameplayStoreRecovery&,const FirstBootContent*);
namespace {
constexpr const char* door_type="firstboot.Door";
constexpr const char* fault_type="firstboot.PowerFault";
constexpr const char* progress_type="firstboot.ChapterProgress";
constexpr const char* quest_type="firstboot.NPCQuest";
void need(bool value,const char* message){if(!value)throw std::invalid_argument(message);}
template<class T> const T& get(const ComponentRecord& record,const std::string& id){
 const auto found=record.fields.find(id);need(found!=record.fields.end(),"Chapter field is missing");const auto* value=std::get_if<T>(&found->second);need(value!=nullptr,"Chapter field type mismatch");return *value;
}
double number(const ComponentRecord& r,const std::string& id){return get<double>(r,id);}
bool flag(const ComponentRecord& r,const std::string& id){return get<bool>(r,id);}
const std::string& text(const ComponentRecord& r,const std::string& id){return get<std::string>(r,id);}
std::int64_t integer(const ComponentRecord& r,const std::string& id){return get<std::int64_t>(r,id);}
std::uint64_t cycle_number(const std::string& value){std::uint64_t result=0;const auto parsed=std::from_chars(value.data(),value.data()+value.size(),result);need(parsed.ec==std::errc{}&&parsed.ptr==value.data()+value.size()&&std::to_string(result)==value,"Invalid recovery cycle identity");return result;}
bool finite(Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
Vec3 point(const ComponentRecord& r,const std::string& prefix=""){return {static_cast<float>(number(r,prefix+"x")),static_cast<float>(number(r,prefix+"y")),static_cast<float>(number(r,prefix+"z"))};}
bool exact(const ComponentRecord& a,const ComponentRecord& b){return gameplay_codec::encode_component(a)==gameplay_codec::encode_component(b);}
GameplayStoreRecovery node_view(const GameplayStoreRecovery& source){
 auto result=source;result.components.clear();for(const auto& r:source.components)if(r.type_id=="firstboot.Node")result.components.push_back(r);return result;
}
struct Layout{double x=0,y=0,z=0;};
Layout layout(const GameplayStoreRecovery& state,const FirstBootContent* content=nullptr){
 const auto world=durable_first_boot_world(node_view(state),content?state.scope.context:GameplayContext::player_world);
 for(const auto& [unused,e]:world){(void)unused;if(e.fields.at("firstboot.kind")==1)return {e.fields.at("x"),e.fields.at("y")+e.fields.at("half_y"),e.fields.at("z")};}
 throw std::invalid_argument("Chapter requires its original motherboard");
}
ComponentSchema schema(std::string id,std::vector<GameplayFieldRule> fields){return {std::move(id),1,std::move(fields)};}
GameplayFieldRule boolean(std::string id){return {std::move(id),GameplayValueKind::boolean};}
GameplayFieldRule string(std::string id){return {std::move(id),GameplayValueKind::text};}
GameplayFieldRule count(std::string id){return {std::move(id),GameplayValueKind::integer};}
GameplayFieldRule real(std::string id,double lo=-500,double hi=500){return {std::move(id),GameplayValueKind::number,true,lo,hi};}
std::vector<ComponentRecord> initial_records(const Layout& p,const FirstBootChapterIds& ids){
 auto door=[&](std::string id,std::string role,double x,double z,bool unlocked){return ComponentRecord{std::move(id),door_type,1,
  {{"role",role},{"name",role=="main"?std::string("Main feed door"):role=="service"?std::string("Service bypass door"):std::string("Pencil Room door")},
   {"open",false},{"unlocked",unlocked},{"x",p.x+x},{"y",p.y+1.7},{"z",p.z+z},{"half_x",1.5},{"half_y",1.7},{"half_z",.18}}};};
 return {door(ids.main_door,"main",-33,4,false),door(ids.service_door,"service",-41,4,false),door(ids.pencil_door,"pencil",-37,13,true),
  {ids.fault,fault_type,1,{{"diagnosed",false},{"isolated",false},{"capacity",0.0},{"bypass_connected",false},{"bypass_relay",std::string{}},
   {"x",p.x-33},{"y",p.y},{"z",p.z-3},{"half_x",2.0},{"half_z",2.5},{"socket_x",p.x-42},{"socket_y",p.y},{"socket_z",p.z-3}}},
  {ids.progress,progress_type,1,{{"state",static_cast<std::int64_t>(QuestState::active)},{"step",std::string("jenison")},{"shelter_secured",false},{"pencil_visited",false},
   {"repair_used",false},{"bypass_used",false},{"first_route",std::string("none")},{"returns",std::int64_t{0}},{"departures",std::int64_t{0}},{"recoveries",std::int64_t{0}},
   {"last_recovery_activation",std::string{}},{"last_recovery_cycle",std::string{}},{"spawn_x",p.x-36.5},{"spawn_y",p.y+.2},{"spawn_z",p.z+7}}},
  {ids.npc_quest,quest_type,1,{{"state",static_cast<std::int64_t>(QuestState::offered)},{"step",std::string("lamp.awaiting_help")},{"lamp_connected",false},{"hint_seen",false},
   {"name",std::string("The Caretaker")},{"source",std::string("fictional.gameplay.v1")},{"x",p.x-40},{"y",p.y},{"z",p.z+6.5},
   {"lamp_x",p.x-40},{"lamp_y",p.y},{"lamp_z",p.z+10}}}};
}
bool chapter_type(const std::string& type){return type==door_type||type==fault_type||type==progress_type||type==quest_type;}
void validate_record(const ComponentRecord& r){
 (void)gameplay_codec::encode_component(r);need(r.version==1,"Unsupported chapter component version");const auto schemas=first_boot_chapter_schemas();
 const auto definition=std::find_if(schemas.begin(),schemas.end(),[&](const auto& s){return s.type_id==r.type_id;});need(definition!=schemas.end(),"Foreign chapter component registry");
 need(r.fields.size()==definition->fields.size(),"Chapter fields cannot be silently added or removed");
 for(const auto& f:definition->fields){const auto found=r.fields.find(f.id);need(found!=r.fields.end()&&found->second.index()==static_cast<std::size_t>(f.kind),"Chapter schema field mismatch");
  if(const auto* n=std::get_if<double>(&found->second))need(std::isfinite(*n)&&*n>=f.minimum&&*n<=f.maximum,"Chapter number outside supported bounds");}
}
struct View{
 const GameplayStoreRecovery& state;
 GameplayStoreRecovery nodes;
 Layout place;
 FirstBootChapterIds ids;
 std::map<std::string,const ComponentRecord*> records;
 bool installed=false;
 const FirstBootContent* content=nullptr;
 explicit View(const GameplayStoreRecovery& s,const FirstBootContent* definition=nullptr):state(s),nodes(node_view(s)),place(layout(s,definition)),content(definition){
  if(content)first_boot_content_check_binding(s,*content);
  need(s.components.size()<=10000,"Chapter component budget exceeded");std::set<std::string> identities;unsigned chapter=0;
  for(const auto& r:s.components){need(identities.insert(r.entity_id).second,"Chapter UUID is shared by multiple records");
   // The immutable binding check above validates this exact optional family.
   // Retain it for node-action isolation without counting a seventh singleton.
   if(content&&(r.type_id=="firstboot.CompanionIntent"||r.type_id==opening_workshop_component_type||r.type_id==opening_workshop_assembly_component_type)){records.emplace(r.entity_id,&r);continue;}
   if(r.type_id=="firstboot.Node"||(content&&r.type_id=="firstboot.ContentBinding"))continue;need(chapter_type(r.type_id),"Foreign chapter component");validate_record(r);records.emplace(r.entity_id,&r);++chapter;
   if(r.type_id==door_type){const auto& role=text(r,"role");auto* id=role=="main"?&ids.main_door:role=="service"?&ids.service_door:role=="pencil"?&ids.pencil_door:nullptr;need(id&&id->empty(),"Duplicate or unknown chapter door role");*id=r.entity_id;need(!flag(r,"open")||flag(r,"unlocked"),"A locked chapter door cannot be open");}
   else {auto* id=r.type_id==fault_type?&ids.fault:r.type_id==progress_type?&ids.progress:&ids.npc_quest;need(id->empty(),"Duplicate chapter singleton");*id=r.entity_id;}
  }
  if(chapter==0)return;
  need(chapter==6&&!ids.main_door.empty()&&!ids.service_door.empty()&&!ids.pencil_door.empty()&&!ids.fault.empty()&&!ids.progress.empty()&&!ids.npc_quest.empty(),"Partial chapter initialization is not playable");installed=true;
  const auto authored=content?content->definition().initial_records:initial_records(place,ids);
  for(const auto& original:authored){const auto& actual=*records.at(original.entity_id);
   for(const auto& [id,value]:original.fields){
    const bool mutable_field=first_boot_content_runtime_field(actual.type_id,id);
    if(!mutable_field)need(actual.fields.at(id)==value,"Chapter content geometry/provenance requires explicit migration");
   }
  }
  need(flag(at(ids.pencil_door),"unlocked"),"Pencil Room is not conditional on optional help");
  const auto& progress=at(ids.progress);const auto& region=text(progress,"step");need(region=="jenison"||region=="hub"||region=="pencil","Unknown chapter region");
  const bool secured=flag(progress,"shelter_secured"),pencil=flag(progress,"pencil_visited");
  need(integer(progress,"state")==static_cast<std::int64_t>(pencil?QuestState::completed:QuestState::active),"Chapter completion contradicts actual Pencil Room discovery");
  need(secured||(region=="jenison"&&!pencil&&text(progress,"first_route")=="none"),"Unsecured chapter cannot claim shelter or Pencil Room");
  const auto& first=text(progress,"first_route");need(first=="none"||first=="repair"||first=="bypass"||first=="alternative","Unknown first route");
  need(!secured||first!="none","Secured shelter must preserve the actual first approach");
  need(region!="pencil"||pencil,"Current Pencil Room presence must retain its actual discovery");
  need(first!="repair"||flag(progress,"repair_used"),"First repair route requires the actual aperture crossing");
  need(first!="bypass"||flag(progress,"bypass_used"),"First bypass route requires the actual aperture crossing");
  for(const auto* id:{"returns","departures","recoveries"})need(integer(progress,id)>=0,"Chapter counters cannot be negative");
  const auto& last=text(progress,"last_recovery_activation");need((integer(progress,"recoveries")==0)==last.empty(),"Recovery count must retain its activation identity");
  if(last.empty())need(text(progress,"last_recovery_cycle").empty(),"Empty recovery activation cannot retain a cycle");
  else{need(is_uuid(last),"Invalid recovery activation identity");(void)cycle_number(text(progress,"last_recovery_cycle"));}
  const auto& fault=at(ids.fault);const auto& relay=text(fault,"bypass_relay");
  if(!relay.empty()){const auto found=std::find_if(nodes.components.begin(),nodes.components.end(),[&](const auto& r){return r.entity_id==relay;});need(found!=nodes.components.end()&&number(*found,"firstboot.kind")==6,"Bypass reference must retain a real relay identity");}
  need(!flag(fault,"bypass_connected")||!relay.empty(),"Connected bypass requires its actual relay");
  const auto& quest=at(ids.npc_quest);const auto q=integer(quest,"state");need(q>=static_cast<std::int64_t>(QuestState::offered)&&q<=static_cast<std::int64_t>(QuestState::completed),"Unknown Caretaker quest state");
  need(flag(quest,"lamp_connected")== (q==static_cast<std::int64_t>(QuestState::completed)),"Completed help must retain the lamp connection");
  const auto expected_step=q==static_cast<std::int64_t>(QuestState::offered)?"lamp.awaiting_help":q==static_cast<std::int64_t>(QuestState::active)?"lamp.accepted":q==static_cast<std::int64_t>(QuestState::declined)?"lamp.deferred":"lamp.connected";
  need(text(quest,"step")==expected_step,"Caretaker step contradicts its actual state");
 }
 const ComponentRecord& at(const std::string& id)const{const auto found=records.find(id);need(found!=records.end(),"Chapter target not found");return *found->second;}
};
bool main_power(const View& v){return number(v.at(v.ids.fault),"capacity")==100&&!flag(v.at(v.ids.fault),"isolated");}
bool bypass_power(const View& v){
 const auto& fault=v.at(v.ids.fault);if(!flag(fault,"isolated")||!flag(fault,"bypass_connected"))return false;
 for(const auto& r:v.nodes.components)if(r.entity_id==text(fault,"bypass_relay"))return flag(r,"alive")&&number(r,"capacity")==100;return false;
}
bool arc_active(const ComponentRecord& f){return !flag(f,"isolated")&&number(f,"capacity")<100;}
bool hint_near(const FirstBootChapterActor& actor,Vec3 point,double distance){
 if(!finite(actor.feet)||!std::isfinite(actor.height)||actor.height<=0||actor.height>10)return false;
 const double x=static_cast<double>(actor.feet.x)-point.x,y=static_cast<double>(actor.feet.y)+actor.height*.5-point.y,z=static_cast<double>(actor.feet.z)-point.z;
 return x*x+y*y+z*z<=distance*distance;
}
bool nearby_active_fault(const ComponentRecord& fault,const FirstBootChapterActor& actor){
 if(!arc_active(fault)||!finite(actor.feet)||!std::isfinite(actor.height)||actor.height<=0||actor.height>10)return false;
 const auto x=std::max(0.0,std::abs(static_cast<double>(actor.feet.x)-number(fault,"x"))-number(fault,"half_x"));
 const auto y=std::max(0.0,std::abs(static_cast<double>(actor.feet.y)+actor.height*.5-number(fault,"y")-1.25)-1.25);
 const auto z=std::max(0.0,std::abs(static_cast<double>(actor.feet.z)-number(fault,"z"))-number(fault,"half_z"));
 return x*x+y*y+z*z<=9;
}
void actor_valid(const FirstBootChapterActor& actor){need(finite(actor.feet)&&finite(actor.previous_feet)&&std::isfinite(actor.radius)&&std::isfinite(actor.height)&&actor.radius>=.05f&&actor.radius<=5&&actor.height>=2*actor.radius&&actor.height<=10,"Invalid chapter actor");need(!actor.inspection_mode,"Inspection camera cannot create chapter progress");}
void reach(const FirstBootChapterActor& actor,Vec3 p,double distance=3){
 actor_valid(actor);const auto dx=static_cast<double>(actor.feet.x)-p.x,dz=static_cast<double>(actor.feet.z)-p.z,dy=static_cast<double>(actor.feet.y)+actor.height*.5-p.y;
 need(dx*dx+dy*dy+dz*dz<=distance*distance,"Move within the interaction's physical reach");
}
void node_reach(const View& view,const FirstBootChapterActor& actor,const std::string& target){
 actor_valid(actor);const auto scene=durable_first_boot_scene(view.nodes,view.content?view.state.scope.context:GameplayContext::player_world);(void)mesh_from_snapshot(scene);
 for(const auto& object:scene.objects){
  if(object.persistent_id!=target)continue;
  const double x=static_cast<double>(actor.feet.x)-object.center.x,y=static_cast<double>(actor.feet.y)+actor.height*.5-object.center.y,z=static_cast<double>(actor.feet.z)-object.center.z;
  // Compare the body centre with each actual collision part, including parts
  // that are not pickable. Conjugate rotation maps into the box's local space.
  const auto rotation=object.rotation;const double norm=std::sqrt(static_cast<double>(rotation.x)*rotation.x+static_cast<double>(rotation.y)*rotation.y+static_cast<double>(rotation.z)*rotation.z+static_cast<double>(rotation.w)*rotation.w);
  const double qx=-rotation.x/norm,qy=-rotation.y/norm,qz=-rotation.z/norm,qw=rotation.w/norm;
  const double tx=2*(qy*z-qz*y),ty=2*(qz*x-qx*z),tz=2*(qx*y-qy*x);
  const double local_x=x+qw*tx+qy*tz-qz*ty,local_y=y+qw*ty+qz*tx-qx*tz,local_z=z+qw*tz+qx*ty-qy*tx;
  const auto dx=std::max(0.0,std::abs(local_x)-object.half_extent.x),dy=std::max(0.0,std::abs(local_y)-object.half_extent.y),dz=std::max(0.0,std::abs(local_z)-object.half_extent.z);
  if(dx*dx+dy*dy+dz*dz<=9.0+1e-6)return;
 }
 throw std::invalid_argument("Move within three metres of the component to repair or dismantle it");
}
std::string region(const Layout& p,Vec3 feet){
 if(feet.x<p.x-44||feet.x>p.x-29||feet.z<p.z+4||feet.z>p.z+20.5||feet.y<p.y-.1||feet.y>p.y+.75)return "jenison";
 return feet.z>=p.z+13?"pencil":"hub";
}
bool crossed(const ComponentRecord& door,const FirstBootChapterActor& a){
 if(!flag(door,"open"))return false;const auto dz=static_cast<double>(a.feet.z)-a.previous_feet.z;if(std::abs(dz)<1e-7)return false;
 const auto t=(number(door,"z")-a.previous_feet.z)/dz;if(t<0||t>1)return false;
 const auto x=a.previous_feet.x+t*(a.feet.x-a.previous_feet.x),y=a.previous_feet.y+t*(a.feet.y-a.previous_feet.y);
 return std::abs(x-number(door,"x"))<=number(door,"half_x")-a.radius&&y>=number(door,"y")-number(door,"half_y")-.1&&y+a.height<=number(door,"y")+number(door,"half_y")+.1;
}
std::string action_name(FirstBootChapterAction action){
 switch(action){case FirstBootChapterAction::inspect_fault:return "inspect_fault";case FirstBootChapterAction::set_isolation:return "set_isolation";
 case FirstBootChapterAction::repair_fault:return "repair_fault";case FirstBootChapterAction::connect_bypass:return "connect_bypass";case FirstBootChapterAction::disconnect_bypass:return "disconnect_bypass";
 case FirstBootChapterAction::open_door:return "open_door";case FirstBootChapterAction::close_door:return "close_door";case FirstBootChapterAction::arrive_hub:return "arrive_hub";
 case FirstBootChapterAction::enter_pencil:return "enter_pencil";case FirstBootChapterAction::depart_hub:return "depart_hub";case FirstBootChapterAction::help_caretaker:return "help_caretaker";
 case FirstBootChapterAction::decline_caretaker:return "decline_caretaker";case FirstBootChapterAction::connect_lamp:return "connect_lamp";case FirstBootChapterAction::recover_arc:return "recover_arc";
 case FirstBootChapterAction::collect_probe:return "collect_probe";case FirstBootChapterAction::sample_supply:return "sample_supply";case FirstBootChapterAction::sample_path:return "sample_path";case FirstBootChapterAction::test_feed:return "test_feed";case FirstBootChapterAction::commission_bench:return "commission_bench";case FirstBootChapterAction::collect_relay_part:return "collect_relay_part";}
 throw std::invalid_argument("Unknown chapter action");
}
struct PlannedEvent{SemanticPayload payload;std::vector<std::string> subjects;};
struct Plan{std::vector<ComponentRecord> changed;std::vector<PlannedEvent> events;};
void mechanism(Plan& p,const ComponentRecord& before,ComponentRecord& after,const std::string& id,bool value){const auto old=flag(before,id);if(old==value)return;after.fields[id]=value;p.events.push_back({MechanismOutcome{before.entity_id,id,old,value},{before.entity_id}});}
void quest(Plan& p,const ComponentRecord& before,const ComponentRecord& after){
 const auto a=static_cast<QuestState>(integer(before,"state")),b=static_cast<QuestState>(integer(after,"state"));
 if(a!=b||text(before,"step")!=text(after,"step"))p.events.push_back({QuestOutcome{before.entity_id,a,b,text(before,"step"),text(after,"step")},{before.entity_id}});
}
void increment(ComponentRecord& record,const std::string& field){const auto value=integer(record,field);need(value<std::numeric_limits<std::int64_t>::max(),"Chapter counter exhausted");record.fields[field]=value+1;}
Plan plan(const View& v,const FirstBootChapterCommand& c,const FirstBootChapterActor& a){
 need(v.installed,"Chapter must be installed before taking chapter actions");actor_valid(a);Plan p;
 const auto& fault=v.at(v.ids.fault);const auto& progress=v.at(v.ids.progress);const auto& npc=v.at(v.ids.npc_quest);
 auto f=fault,pr=progress,q=npc;
 switch(c.action){
 case FirstBootChapterAction::inspect_fault:reach(a,{static_cast<float>(number(fault,"x")),static_cast<float>(number(fault,"y")+1),static_cast<float>(number(fault,"z"))},8);mechanism(p,fault,f,"diagnosed",true);if(!p.events.empty())p.changed.push_back(std::move(f));break;
 case FirstBootChapterAction::set_isolation:{auto position=v.content?v.content->definition().isolation_switch:Vec3{static_cast<float>(number(fault,"x")-2.5),static_cast<float>(number(fault,"y")),static_cast<float>(number(fault,"z"))};position.y+=1;reach(a,position);mechanism(p,fault,f,"isolated",c.enabled);if(!p.events.empty())p.changed.push_back(std::move(f));break;}
 case FirstBootChapterAction::repair_fault:{reach(a,{static_cast<float>(number(fault,"x")),static_cast<float>(number(fault,"y")+1),static_cast<float>(number(fault,"z"))});need(flag(fault,"isolated"),"Isolate the damaged feed before repair");const auto old=number(fault,"capacity");if(old==100)break;f.fields["capacity"]=100.0;p.changed.push_back(std::move(f));p.events.push_back({RepairOutcome{v.ids.fault,old,100},{v.ids.fault}});break;}
 case FirstBootChapterAction::connect_bypass:{reach(a,{static_cast<float>(number(fault,"socket_x")),static_cast<float>(number(fault,"socket_y")+1),static_cast<float>(number(fault,"socket_z"))});need(flag(fault,"isolated"),"Isolate the main fault before using its independent relay feed");need(!flag(fault,"bypass_connected"),"Disconnect the old bypass feed before selecting another relay");
  const auto found=std::find_if(v.nodes.components.begin(),v.nodes.components.end(),[&](const auto& r){return r.entity_id==c.relay_id;});need(found!=v.nodes.components.end()&&flag(*found,"alive")&&number(*found,"firstboot.kind")==6&&number(*found,"capacity")==100,"Bypass needs an actual healthy living relay");
  need(std::hypot(number(*found,"x")-number(fault,"socket_x"),number(*found,"z")-number(fault,"socket_z"))<=2.0&&std::abs(number(*found,"y")-(number(fault,"socket_y")+1.2))<=.25,"Place the relay in the service socket");f.fields["bypass_relay"]=c.relay_id;mechanism(p,fault,f,"bypass_connected",true);p.changed.push_back(std::move(f));break;}
 case FirstBootChapterAction::disconnect_bypass:reach(a,{static_cast<float>(number(fault,"socket_x")),static_cast<float>(number(fault,"socket_y")+1),static_cast<float>(number(fault,"socket_z"))});mechanism(p,fault,f,"bypass_connected",false);if(!p.events.empty())p.changed.push_back(std::move(f));break;
 case FirstBootChapterAction::open_door:case FirstBootChapterAction::close_door:{const auto& door=v.at(c.target_id);need(door.type_id==door_type,"Selected target is not a chapter door");reach(a,point(door));auto changed=door;
  const bool opening=c.action==FirstBootChapterAction::open_door;
  if(opening&&!flag(door,"unlocked")){const auto& role=text(door,"role");need((role=="main"&&main_power(v))||(role=="service"&&bypass_power(v))||role=="pencil","This first opening needs its repaired or isolated relay supply");mechanism(p,door,changed,"unlocked",true);}
  mechanism(p,door,changed,"open",opening);if(!p.events.empty())p.changed.push_back(std::move(changed));break;}
 case FirstBootChapterAction::arrive_hub:case FirstBootChapterAction::enter_pencil:case FirstBootChapterAction::depart_hub:{need(a.grounded,"Grounded physical arrival is required");const auto actual=v.content?first_boot_content_locate(*v.content,a.feet):region(v.place,a.feet),previous=text(progress,"step");
  need(actual==(c.action==FirstBootChapterAction::enter_pencil?"pencil":c.action==FirstBootChapterAction::depart_hub?"jenison":"hub"),"Actor has not reached the selected region");if(actual==previous)break;
  if(actual!="jenison"){const bool first=!flag(progress,"shelter_secured");mechanism(p,progress,pr,"shelter_secured",true);
   const bool main=crossed(v.at(v.ids.main_door),a),service=crossed(v.at(v.ids.service_door),a);
   if(main)mechanism(p,progress,pr,"repair_used",true);if(service)mechanism(p,progress,pr,"bypass_used",true);
   if(first)pr.fields["first_route"]=std::string(main?"repair":service?"bypass":"alternative");else if(previous=="jenison")increment(pr,"returns");
  }else if(previous!="jenison")increment(pr,"departures");
  if(actual=="pencil"){mechanism(p,progress,pr,"pencil_visited",true);pr.fields["state"]=static_cast<std::int64_t>(QuestState::completed);}
  pr.fields["step"]=actual;quest(p,progress,pr);p.changed.push_back(std::move(pr));break;}
 case FirstBootChapterAction::help_caretaker:case FirstBootChapterAction::decline_caretaker:{reach(a,{static_cast<float>(number(npc,"x")),static_cast<float>(number(npc,"y")+1),static_cast<float>(number(npc,"z"))});if(integer(npc,"state")==static_cast<std::int64_t>(QuestState::completed))break;
  const bool help=c.action==FirstBootChapterAction::help_caretaker;q.fields["state"]=static_cast<std::int64_t>(help?QuestState::active:QuestState::declined);q.fields["step"]=std::string(help?"lamp.accepted":"lamp.deferred");mechanism(p,npc,q,"hint_seen",true);quest(p,npc,q);if(!p.events.empty())p.changed.push_back(std::move(q));break;}
 case FirstBootChapterAction::connect_lamp:{reach(a,{static_cast<float>(number(npc,"lamp_x")),static_cast<float>(number(npc,"lamp_y")+1),static_cast<float>(number(npc,"lamp_z"))});if(flag(npc,"lamp_connected"))break;need(main_power(v)||bypass_power(v),"The table lamp needs repaired main power or the isolated relay feed");
  mechanism(p,npc,q,"lamp_connected",true);q.fields["state"]=static_cast<std::int64_t>(QuestState::completed);q.fields["step"]=std::string("lamp.connected");quest(p,npc,q);p.changed.push_back(std::move(q));break;}
 case FirstBootChapterAction::collect_probe:case FirstBootChapterAction::sample_supply:case FirstBootChapterAction::sample_path:case FirstBootChapterAction::test_feed:case FirstBootChapterAction::commission_bench:case FirstBootChapterAction::collect_relay_part:{
  need(v.content!=nullptr,"Workshop actions require explicitly bound content");const auto binding=first_boot_content_workshop_binding(v.content->definition());need(binding.has_value(),"This chapter has no workshop workflow");
  const bool salvage=c.action==FirstBootChapterAction::collect_relay_part;
  const auto slot=salvage?2u:static_cast<unsigned>(c.action)-static_cast<unsigned>(FirstBootChapterAction::collect_probe);need(slot<5,"Unknown workshop action");
  const auto fixture=std::find_if(v.content->definition().fixtures.begin(),v.content->definition().fixtures.end(),[&](const auto& f){return f.object.persistent_id==binding->fixtures[slot];});need(fixture!=v.content->definition().fixtures.end(),"Owned workshop target disappeared");
  const Vec3 eye{a.feet.x,a.feet.y+a.height*.5f,a.feet.z};const auto target=fixture->object.center;auto visibility=first_boot_content_scene(v.state,*v.content);for(auto& object:visibility.objects)object.selectable=true;
  const auto hit=pick_scene(visibility,eye,{target.x-eye.x,target.y-eye.y,target.z-eye.z},3.2f);
  OpeningWorkshopActor actor;actor.target_id=c.target_id;actor.distance=std::hypot(static_cast<double>(eye.x)-target.x,static_cast<double>(eye.y)-target.y,static_cast<double>(eye.z)-target.z);actor.grounded=a.grounded;actor.inspection_mode=a.inspection_mode;actor.visible=hit&&hit->persistent_id==fixture->object.persistent_id;actor.in_shelter=first_boot_content_locate(*v.content,a.feet)=="hub";
  if(salvage){
   need(actor.target_id==binding->fixtures[2]&&actor.grounded&&!actor.inspection_mode&&actor.visible&&actor.distance<=3.2,"Move within visible grounded reach of the path-contact salvage tray");
   const auto assembly=first_boot_content_relay_assembly(v.state,*v.content);if(assembly.initialized)break;
   need(assembly.pickup_available,"Sample the path contact first; an existing living relay already holds the finite part");
   p.changed.push_back(opening_workshop_assembly_record(*binding,true,assembly.legacy));
   p.events.push_back({MechanismOutcome{binding->fixtures[2],"relay_part_available",false,true},{binding->fixtures[2]}});break;
  }
  const auto result=plan_opening_workshop(v.at(binding->fixtures[4]),*binding,first_boot_content_workshop_circuit(v.state,*v.content),static_cast<OpeningWorkshopAction>(slot),actor);
  if(result){p.changed.push_back(result->component);p.events.push_back({result->outcome,{binding->fixtures[4]}});}break;
 }
 case FirstBootChapterAction::recover_arc:{need(first_boot_chapter_hazard_contact(v.state,a)&&a.hazard.recovery_available,"No unacknowledged physical arc contact exists");
  const auto& last=text(progress,"last_recovery_activation");need(last!=a.hazard.activation_id||a.hazard.cycle>cycle_number(text(progress,"last_recovery_cycle")),"This activation cycle already produced a recovery");
  increment(pr,"recoveries");pr.fields["last_recovery_activation"]=a.hazard.activation_id;pr.fields["last_recovery_cycle"]=std::to_string(a.hazard.cycle);
  const auto destination=flag(progress,"shelter_secured")?"hub":"jenison";pr.fields["step"]=std::string(destination);quest(p,progress,pr);p.changed.push_back(std::move(pr));p.events.push_back({HazardOutcome{v.ids.fault,false},{v.ids.fault,v.ids.progress}});break;}
 }
 return p;
}
GameplayChangeBatch batch_from(const GameplayStoreRecovery& before,const Plan& p,const std::string& source,std::string operation,const FirstBootChapterActor* actor,const GameplayChangeBatch* identity=nullptr){
 need(!p.events.empty()&&before.revision<std::numeric_limits<std::uint64_t>::max()&&before.sequence<=std::numeric_limits<std::uint64_t>::max()-p.events.size(),"Chapter event head exhausted");
 GameplayChangeBatch batch;batch.scope=before.scope;batch.operation_id=operation.empty()?source+"."+new_uuid():std::move(operation);batch.expected_revision=before.revision;batch.revision=before.revision+1;
 for(const auto& changed:p.changed)batch.deltas.push_back({ComponentAction::upsert,changed});
 for(std::size_t i=0;i<p.events.size();++i){const auto& planned=p.events[i];SemanticEvent event;event.event_id=identity?identity->events.at(i).event_id:new_uuid();event.scope=before.scope;event.sequence=before.sequence+i+1;event.operation_id=batch.operation_id;event.subject_ids=planned.subjects;event.source_revision=batch.revision;
  if(actor)event.logical_tick=actor->active_tick;event.provenance.source_id=source;event.payload=planned.payload;event.payload_version=event.payload.index()>=4?2:1;if(event.payload_version==2)batch.schema_version=2;batch.events.push_back(std::move(event));}
 return batch;
}
GameplayStoreRecovery apply_plan(const GameplayStoreRecovery& before,const GameplayChangeBatch& batch){auto after=before;after.revision=batch.revision;after.sequence=batch.events.back().sequence;for(const auto& delta:batch.deltas){auto found=std::find_if(after.components.begin(),after.components.end(),[&](const auto& r){return r.entity_id==delta.component.entity_id&&r.type_id==delta.component.type_id;});if(found==after.components.end())after.components.push_back(delta.component);else *found=delta.component;}return after;}
bool exact_state(const GameplayStoreRecovery& a,const GameplayStoreRecovery& b){if(a.scope!=b.scope||a.revision!=b.revision||a.sequence!=b.sequence||a.components.size()!=b.components.size())return false;std::map<std::string,const ComponentRecord*> records;for(const auto& r:a.components)need(records.emplace(r.entity_id,&r).second,"Duplicate expected chapter entity");for(const auto& r:b.components){const auto found=records.find(r.entity_id);if(found==records.end()||!exact(*found->second,r))return false;}return true;}
void box(SceneSnapshot& scene,const std::string& id,std::string name,Vec3 center,Vec3 half,Vec3 color,float emission=0,bool selectable=false,Quaternion rotation={}){scene.objects.push_back({id,std::move(name),center,half,color,emission,selectable,rotation});}
void door_clear(const GameplayStoreRecovery& after,const FirstBootChapterActor& actor,const FirstBootContent* content=nullptr){CharacterSettings settings;settings.radius=actor.radius;settings.height=actor.height;PlayerController candidate(chapter_content_scene(after,content),actor.feet,settings);}
unsigned living_relays(const GameplayStoreRecovery& state){unsigned count=0;for(const auto& r:state.components)if(r.type_id=="firstboot.Node"&&number(r,"firstboot.kind")==6&&flag(r,"alive"))++count;return count;}
ComponentRecord assembly_after_node(const GameplayStoreRecovery& before,const GameplayStoreRecovery& after,bool built,const FirstBootContent& content){
 const auto binding=first_boot_content_workshop_binding(content.definition());need(binding.has_value(),"Relay assembly requires Workshop content");
 const auto assembly=first_boot_content_relay_assembly(before,content);
 if(built)need(assembly.initialized&&assembly.part_available,"Collect the one relay part from the sampled path-contact tray before building");
 return opening_workshop_assembly_record(*binding,built?false:living_relays(after)==0,assembly.legacy);
}
std::optional<MechanismOutcome> assembly_transition(const GameplayStoreRecovery& before,const ComponentRecord& after,const FirstBootContent& content){
 const auto assembly=first_boot_content_relay_assembly(before,content);const bool available=flag(after,"available");
 if(assembly.part_available!=available)return MechanismOutcome{after.entity_id,"relay_part_available",assembly.part_available,available};
 if(!assembly.initialized)return MechanismOutcome{after.entity_id,"relay_part_collected",false,true};
 return {};
}
void socket_build_position(const View& view,Vec3 position){
 const auto& fault=view.at(view.ids.fault);need(finite(position)&&std::hypot(static_cast<double>(position.x)-number(fault,"socket_x"),static_cast<double>(position.z)-number(fault,"socket_z"))<=2.0&&std::abs(static_cast<double>(position.y)-(number(fault,"socket_y")+1.2))<=.25,"Assemble the finite relay part in the actual service socket");
}
void append_assembly(const GameplayStoreRecovery& before,GameplayChangeBatch& batch,const FirstBootChapterActor& actor,const FirstBootContent& content){
 if(!first_boot_content_workshop_binding(content.definition()))return;
 need(batch.events.size()==1,"Relay assembly requires one actual node transition");const auto* construction=std::get_if<ConstructionOutcome>(&batch.events.front().payload);need(construction!=nullptr,"Relay assembly needs its real construction outcome");
 const auto after=apply_plan(before,batch);const auto record=assembly_after_node(before,after,construction->built,content);const auto transition=assembly_transition(before,record,content);if(!transition)return;
 Plan plan;plan.changed.push_back(record);plan.events.push_back({*transition,{record.entity_id}});
 auto extra=batch_from(before,plan,"firstboot.workshop.assembly.v1",batch.operation_id,&actor);
 need(batch.events.back().sequence<std::numeric_limits<std::uint64_t>::max(),"Relay assembly sequence exhausted");extra.events.front().sequence=batch.events.back().sequence+1;
 batch.deltas.push_back(extra.deltas.front());batch.events.push_back(extra.events.front());batch.schema_version=2;
}
void assembly_node_rules(const View& old,const View& next,const GameplayChangeBatch& batch,const FirstBootChapterActor& actor,const FirstBootContent& content,const std::set<std::string>& historical){
 need(batch.deltas.size()==2&&batch.events.size()==2,"Finite assembly must atomically publish one node and one part transition");
 const auto* construction=std::get_if<ConstructionOutcome>(&batch.events.front().payload);need(construction!=nullptr,"Assembly must retain its actual construction outcome first");
 auto nodes=batch;std::erase_if(nodes.deltas,[](const auto& d){return d.component.type_id==opening_workshop_assembly_component_type;});nodes.events.resize(1);nodes.schema_version=1;
 need(nodes.deltas.size()==1&&nodes.deltas.front().component.type_id=="firstboot.Node","Assembly cannot alter other chapter state");
 auto after_nodes=next.nodes;after_nodes.sequence=old.nodes.sequence+1;
 durable_first_boot_rules(old.nodes,after_nodes,nodes,historical,old.state.scope.context);actor_valid(actor);
 if(construction->built)socket_build_position(old,point(nodes.deltas.front().component));else node_reach(old,actor,construction->entity_id);
 const auto expected=assembly_after_node(old.state,next.state,construction->built,content);
 const auto outcome=assembly_transition(old.state,expected,content);need(outcome.has_value(),"Assembly batch invents an unchanged part outcome");
 const auto found=std::find_if(batch.deltas.begin(),batch.deltas.end(),[](const auto& d){return d.component.type_id==opening_workshop_assembly_component_type;});
 need(found!=batch.deltas.end()&&found->action==ComponentAction::upsert&&exact(found->component,expected),"Assembly part transition contradicts actual before/after inventory");
 const auto& event=batch.events.back();need(event.payload==SemanticPayload{*outcome}&&event.subject_ids==std::vector<std::string>{expected.entity_id}&&event.provenance.kind==GameplayProvenance::gameplay_rule&&event.provenance.source_id=="firstboot.workshop.assembly.v1"&&event.logical_tick==actor.active_tick,"Assembly event does not describe the exact part transition");
 for(const auto& [id,r]:old.records)if(r->type_id!=opening_workshop_assembly_component_type)need(exact(*r,next.at(id)),"Assembly cannot rewrite other chapter history");
}
}

std::vector<ComponentSchema> first_boot_chapter_schemas(){
 auto result=durable_first_boot_schemas();result.push_back(schema(door_type,{string("role"),string("name"),boolean("open"),boolean("unlocked"),real("x"),real("y"),real("z"),real("half_x",.01,20),real("half_y",.01,20),real("half_z",.01,20)}));
 result.push_back(schema(fault_type,{boolean("diagnosed"),boolean("isolated"),real("capacity",0,100),boolean("bypass_connected"),string("bypass_relay"),real("x"),real("y"),real("z"),real("half_x",.01,20),real("half_z",.01,20),real("socket_x"),real("socket_y"),real("socket_z")}));
 result.push_back(schema(progress_type,{count("state"),string("step"),boolean("shelter_secured"),boolean("pencil_visited"),boolean("repair_used"),boolean("bypass_used"),string("first_route"),count("returns"),count("departures"),count("recoveries"),string("last_recovery_activation"),string("last_recovery_cycle"),real("spawn_x"),real("spawn_y"),real("spawn_z")}));
 result.push_back(schema(quest_type,{count("state"),string("step"),boolean("lamp_connected"),boolean("hint_seen"),string("name"),string("source"),real("x"),real("y"),real("z"),real("lamp_x"),real("lamp_y"),real("lamp_z")}));return result;
}
void first_boot_chapter_preflight(const GameplayStoreRecovery& before){
 const auto slice=node_view(before);durable_first_boot_validate(slice);const auto world=durable_first_boot_world(slice);const Entity* board=nullptr;
 for(const auto& [unused,e]:world){(void)unused;if(e.fields.at("firstboot.kind")==1)board=&e;}need(board!=nullptr,"Chapter needs its board");
 need(board->fields.at("half_x")>=44.5&&board->fields.at("half_z")>=21,"This board footprint cannot support the authored chapter; original save remains compatible with the construction yard");
 const auto p=layout(before);need(p.x-42>=-200&&p.x-42<=200&&p.z-3>=-200&&p.z-3<=200&&p.y+1.2>=-50&&p.y+1.2<=100,"Chapter relay socket exceeds existing construction bounds");
 for(const auto& [unused,e]:world){(void)unused;const auto kind=e.fields.at("firstboot.kind");if(kind==1||kind==6||(kind==7&&e.fields.at("y")+e.fields.at("half_y")<=p.y+.15))continue;
  const auto x=e.fields.at("x"),z=e.fields.at("z");need(x+e.fields.at("half_x")<=p.x-44||x-e.fields.at("half_x")>=p.x-29||z+e.fields.at("half_z")<=p.z+4||z-e.fields.at("half_z")>=p.z+20.5,"Chapter refuge footprint overlaps existing hardware; explicit content placement is required");}
 // Registry migration must not strand a valid M2 world in an unplayable new
 // schema. Stage the complete authored geometry and its actual supported return
 // policy before the external caller is allowed to extend that registry.
 View content(before);auto candidate=before;
 if(!content.installed){const FirstBootChapterIds ids{new_uuid(),new_uuid(),new_uuid(),new_uuid(),new_uuid(),new_uuid()};const auto additions=initial_records(p,ids);candidate.components.insert(candidate.components.end(),additions.begin(),additions.end());}
 first_boot_chapter_validate(candidate);
}
GameplayStoreBaseline first_boot_chapter_baseline(const CreatorSession& source){return durable_first_boot_baseline(source);}
std::vector<ComponentRecord> first_boot_chapter_additions(const GameplayStoreRecovery& before){View v(before);if(v.installed)return {};first_boot_chapter_preflight(before);FirstBootChapterIds ids{new_uuid(),new_uuid(),new_uuid(),new_uuid(),new_uuid(),new_uuid()};return initial_records(v.place,ids);}
std::optional<GameplayChangeBatch> first_boot_chapter_install(const GameplayStoreRecovery& before,std::string operation){
 const auto additions=first_boot_chapter_additions(before);if(additions.empty())return {};Plan p;p.changed=additions;
 for(const auto& r:additions)if(r.type_id==progress_type||r.type_id==quest_type)p.events.push_back({QuestOutcome{r.entity_id,QuestState::unavailable,static_cast<QuestState>(integer(r,"state")),"",text(r,"step")},{r.entity_id}});
 return batch_from(before,p,"firstboot.chapter.install.v1",std::move(operation),nullptr);
}
FirstBootChapterIds first_boot_chapter_ids(const GameplayStoreRecovery& snapshot){View v(snapshot);need(v.installed,"Chapter has not been installed");return v.ids;}
SceneSnapshot chapter_content_scene(const GameplayStoreRecovery& snapshot,const FirstBootContent* content){
 View v(snapshot,content);auto scene=durable_first_boot_scene(v.nodes,content?snapshot.scope.context:GameplayContext::player_world);if(!v.installed)return scene;const auto p=v.place;const auto& id=v.ids.progress;
 if(!content){
 auto wall=[&](double x,double z,double hx,double hz){box(scene,id,"Refuge boundary",{static_cast<float>(p.x+x),static_cast<float>(p.y+2.5),static_cast<float>(p.z+z)},{static_cast<float>(hx),2.5f,static_cast<float>(hz)},{.15f,.18f,.20f});};
 wall(-44,12.25,.22,8.25);wall(-29,12.25,.22,8.25);wall(-36.5,20.5,7.5,.22);
 wall(-43.25,4,.75,.22);wall(-37,4,2.5,.22);wall(-30.25,4,1.25,.22);
 wall(-41.25,13,2.75,.18);wall(-32.25,13,3.25,.18);
 const bool secured=flag(v.at(v.ids.progress),"shelter_secured");box(scene,id,"Sheltered workshop floor",{static_cast<float>(p.x-36.5),static_cast<float>(p.y+.015),static_cast<float>(p.z+12.25)},{7.25f,.015f,8.0f},{.18f,.12f,.08f},secured?.2f:0);
 }else{const bool secured=flag(v.at(v.ids.progress),"shelter_secured");for(const auto& f:content->definition().fixtures){auto object=f.object;if(secured&&f.sheltered_emission>=0)object.emission=f.sheltered_emission;
  if(f.role==FixtureRole::workshop){const auto binding=first_boot_content_workshop_binding(content->definition());if(binding&&f.object.persistent_id==binding->fixtures[4])object.emission=opening_workshop_online(v.at(binding->fixtures[4]),*binding,first_boot_content_workshop_circuit(snapshot,*content))?.65f:.015f;}
  scene.objects.push_back(object);}}
 for(const auto* door_id:{&v.ids.main_door,&v.ids.service_door,&v.ids.pencil_door}){const auto& d=v.at(*door_id);auto center=point(d);const auto half=point(d,"half_");Quaternion rotation{};
  if(flag(d,"open")){center.x-=half.x;center.z+=half.x;rotation={0,.70710678f,0,.70710678f};}
  box(scene,*door_id,text(d,"name"),center,half,flag(d,"unlocked")?Vec3{.3f,.4f,.35f}:Vec3{.36f,.16f,.12f},0,true,rotation);
 }
 const auto& fault=v.at(v.ids.fault);box(scene,v.ids.fault,"Downstream power fault",{static_cast<float>(number(fault,"x")),static_cast<float>(number(fault,"y")+.6),static_cast<float>(number(fault,"z"))},{.7f,.6f,.6f},{.25f,.13f,.12f},arc_active(fault)?.15f:0,true);
 auto isolation=content?content->definition().isolation_switch:Vec3{static_cast<float>(number(fault,"x")-2.5),static_cast<float>(p.y),static_cast<float>(number(fault,"z"))};isolation.y+=.8f;
 box(scene,v.ids.fault,"Isolation switch",isolation,{.25f,.8f,.35f},{.2f,.3f,.32f},0,true);
 box(scene,v.ids.fault,"Service relay socket",{static_cast<float>(number(fault,"socket_x")),static_cast<float>(number(fault,"socket_y")+.12),static_cast<float>(number(fault,"socket_z"))},{1.2f,.12f,1.2f},bypass_power(v)?Vec3{.1f,.65f,.4f}:Vec3{.3f,.28f,.12f},bypass_power(v)?.5f:0,true);
 const auto& npc=v.at(v.ids.npc_quest);box(scene,v.ids.npc_quest,content?text(npc,"name"):"The Caretaker (fictional)",{static_cast<float>(number(npc,"x")),static_cast<float>(number(npc,"y")+.9),static_cast<float>(number(npc,"z"))},{.3f,.9f,.3f},{.26f,.42f,.4f},0,true);
 box(scene,v.ids.npc_quest,"Table and lamp",{static_cast<float>(number(npc,"lamp_x")),static_cast<float>(number(npc,"lamp_y")+.6),static_cast<float>(number(npc,"lamp_z"))},{1.0f,.6f,.6f},{.28f,.18f,.1f},0,true);
 const bool lamp=flag(npc,"lamp_connected")&&(main_power(v)||bypass_power(v));box(scene,v.ids.npc_quest,"Table lamp",{static_cast<float>(number(npc,"lamp_x")),static_cast<float>(number(npc,"lamp_y")+1.6),static_cast<float>(number(npc,"lamp_z"))},{.25f,.25f,.25f},{.9f,.54f,.2f},lamp?1.0f:.03f,true);
 if(!content){const bool secured=flag(v.at(v.ids.progress),"shelter_secured");
 box(scene,id,"Pencil Room writing desk",{static_cast<float>(p.x-40),static_cast<float>(p.y+.6),static_cast<float>(p.z+17)},{1.2f,.6f,.7f},{.3f,.18f,.09f});
 box(scene,id,"Pencil and blank page",{static_cast<float>(p.x-40),static_cast<float>(p.y+1.25),static_cast<float>(p.z+17)},{.55f,.025f,.35f},{.85f,.75f,.5f},secured?.4f:0);
 }(void)mesh_from_snapshot(scene);return scene;
}
std::string first_boot_chapter_region(const GameplayStoreRecovery& snapshot,Vec3 feet){need(finite(feet),"Invalid region position");return region(layout(snapshot),feet);}
Vec3 chapter_content_return(const GameplayStoreRecovery& snapshot,const FirstBootContent* content){
 View v(snapshot,content);const auto scene=chapter_content_scene(snapshot,content);const bool secured=v.installed&&flag(v.at(v.ids.progress),"shelter_secured");std::vector<Vec3> candidates;
 const auto world=durable_first_boot_world(v.nodes,content?snapshot.scope.context:GameplayContext::player_world);const auto& board=*std::find_if(world.begin(),world.end(),[](const auto& entry){return entry.second.fields.at("firstboot.kind")==1;});
 const auto half_x=board.second.fields.at("half_x"),half_z=board.second.fields.at("half_z");
 if(content)candidates=secured?content->definition().hub_returns:content->definition().jenison_returns;
 else if(secured){candidates.push_back(point(v.at(v.ids.progress),"spawn_"));for(int z=0;z<5;++z)for(int x=0;x<7;++x)candidates.push_back({static_cast<float>(v.place.x-43.2+x*2),static_cast<float>(v.place.y+.2),static_cast<float>(v.place.z+5.2+z*1.6)});}
 else{
  candidates.push_back({static_cast<float>(v.place.x-32),static_cast<float>(v.place.y+.2),static_cast<float>(v.place.z-25)});
  const auto hx=board.second.fields.at("half_x")-.5,hz=board.second.fields.at("half_z")-.5;for(int z=0;z<9;++z)for(int x=0;x<9;++x)candidates.push_back({static_cast<float>(v.place.x-hx+2*hx*x/8),static_cast<float>(v.place.y+.2),static_cast<float>(v.place.z-hz+2*hz*z/8)});
 }
 for(const auto feet:candidates){const auto location=content?first_boot_content_locate(*content,feet):region(v.place,feet);if(std::abs(feet.x-v.place.x)+.35>half_x||std::abs(feet.z-v.place.z)+.35>half_z||(!secured&&location!="jenison")||(content&&secured&&location!="hub"))continue;try{
  if(content){GroundedCharacter body(scene,feet);for(int i=0;i<60;++i)body.advance({},1.0/60);if(!body.state().grounded||std::abs(body.state().feet.y-feet.y)>.5f)continue;}
  PlayerController test(scene,feet);return feet;}catch(const std::invalid_argument&) {}}
 throw std::invalid_argument("No supported clear chapter return point remains; choose another construction placement");
}
PlayerController first_boot_chapter_player(const GameplayStoreRecovery& snapshot){return PlayerController(first_boot_chapter_scene(snapshot),first_boot_chapter_safe_return(snapshot));}
void chapter_content_validate(const GameplayStoreRecovery& snapshot,const FirstBootContent* content){View view(snapshot,content);need(view.installed,"Chapter has not been installed");(void)chapter_content_scene(snapshot,content);(void)chapter_content_return(snapshot,content);}
std::optional<GameplayChangeBatch> chapter_content_action(const GameplayStoreRecovery& before,const FirstBootChapterCommand& command,const FirstBootChapterActor& actor,const FirstBootContent* content){
 View view(before,content);const auto result=plan(view,command,actor);if(result.events.empty())return {};auto batch=batch_from(before,result,"firstboot.chapter."+action_name(command.action)+".v1",command.operation_id,&actor);
 const auto after=apply_plan(before,batch);chapter_content_validate(after,content);if(command.action==FirstBootChapterAction::open_door||command.action==FirstBootChapterAction::close_door)door_clear(after,actor,content);return batch;
}
void chapter_content_rules(const GameplayStoreRecovery& before,const GameplayStoreRecovery& after,const GameplayChangeBatch& batch,const FirstBootChapterActor& actor,const std::set<std::string>& historical,const FirstBootContent* content){
 (void)gameplay_codec::encode_batch(batch);need(before.scope==after.scope&&before.scope==batch.scope&&batch.expected_revision==before.revision,"Foreign chapter scope or head");View old(before,content),next(after,content);
 if(!old.installed){
  first_boot_chapter_preflight(before);need(next.installed&&batch.deltas.size()==6,"Chapter installation must publish all authored records atomically");
  for(const auto& [id,unused]:next.records){(void)unused;need(!historical.contains(id),"Chapter initialization cannot reuse a retired imported identity");}
  Plan p;p.changed=initial_records(old.place,next.ids);for(const auto& r:p.changed)if(r.type_id==progress_type||r.type_id==quest_type)p.events.push_back({QuestOutcome{r.entity_id,QuestState::unavailable,static_cast<QuestState>(integer(r,"state")),"",text(r,"step")},{r.entity_id}});
  need(batch.events.size()==p.events.size(),"Chapter installation availability records mismatch");const auto expected=batch_from(before,p,"firstboot.chapter.install.v1",batch.operation_id,nullptr,&batch);
  need(gameplay_batch_exact(expected,batch)&&exact_state(apply_plan(before,expected),after),"Chapter initialization cannot fabricate discoveries or rewrite hardware");
 }else{
  need(next.installed,"Chapter state cannot be removed");
  const bool nodes_only=std::all_of(batch.deltas.begin(),batch.deltas.end(),[](const auto& d){return d.component.type_id=="firstboot.Node";});
  const bool assembly_nodes=std::any_of(batch.deltas.begin(),batch.deltas.end(),[](const auto& d){return d.component.type_id==opening_workshop_assembly_component_type;})&&std::any_of(batch.events.begin(),batch.events.end(),[](const auto& e){return std::holds_alternative<ConstructionOutcome>(e.payload);});
  if(assembly_nodes){need(content!=nullptr,"Assembly requires explicit Workshop content");assembly_node_rules(old,next,batch,actor,*content,historical);}
  else if(nodes_only){
   if(content&&first_boot_content_workshop_binding(content->definition()))for(const auto& event:batch.events)if(const auto* construction=std::get_if<ConstructionOutcome>(&event.payload)){
    need(!construction->built,"Workshop relay construction must atomically consume its finite part");
    const auto expected=assembly_after_node(before,after,false,*content);need(!assembly_transition(before,expected,*content).has_value(),"Relay dismantle must atomically reclaim or adopt its finite part");
   }
   durable_first_boot_rules(old.nodes,next.nodes,batch,historical,content?before.scope.context:GameplayContext::player_world);actor_valid(actor);
   for(const auto& event:batch.events){if(const auto* repair=std::get_if<RepairOutcome>(&event.payload))node_reach(old,actor,repair->entity_id);
    else if(const auto* construction=std::get_if<ConstructionOutcome>(&event.payload);construction&&!construction->built)node_reach(old,actor,construction->entity_id);}
   for(const auto& [id,r]:old.records)need(exact(*r,next.at(id)),"Node construction cannot rewrite chapter history");
  }
  else{
   need(!batch.events.empty(),"Chapter action requires true outcomes");const auto source=batch.events.front().provenance.source_id;std::optional<FirstBootChapterAction> action;
   for(unsigned n=0;n<=static_cast<unsigned>(FirstBootChapterAction::collect_relay_part);++n){const auto candidate=static_cast<FirstBootChapterAction>(n);if(source=="firstboot.chapter."+action_name(candidate)+".v1")action=candidate;}need(action.has_value(),"Unknown chapter action provenance");
   FirstBootChapterCommand command;command.action=*action;command.operation_id=batch.operation_id;
   if(*action==FirstBootChapterAction::open_door||*action==FirstBootChapterAction::close_door)command.target_id=batch.events.front().subject_ids.front();
   if(*action==FirstBootChapterAction::set_isolation)command.enabled=flag(next.at(next.ids.fault),"isolated");
   if(*action==FirstBootChapterAction::connect_bypass)command.relay_id=text(next.at(next.ids.fault),"bypass_relay");
   if(*action>=FirstBootChapterAction::collect_probe&&*action<=FirstBootChapterAction::commission_bench){need(content!=nullptr,"Workshop provenance requires content");const auto binding=first_boot_content_workshop_binding(content->definition());need(binding.has_value(),"Workshop provenance has no binding");command.target_id=binding->fixtures[static_cast<unsigned>(*action)-static_cast<unsigned>(FirstBootChapterAction::collect_probe)];}
   if(*action==FirstBootChapterAction::collect_relay_part){need(content!=nullptr,"Salvage provenance requires content");const auto binding=first_boot_content_workshop_binding(content->definition());need(binding.has_value(),"Salvage requires Workshop binding");command.target_id=binding->fixtures[2];}
   const auto expected_plan=plan(old,command,actor);need(expected_plan.events.size()==batch.events.size(),"Chapter outcome count contradicts actual changes");
   const auto expected=batch_from(before,expected_plan,source,batch.operation_id,&actor,&batch);
   need(gameplay_batch_exact(expected,batch)&&exact_state(apply_plan(before,expected),after),"Chapter outcome contradicts actual before/after state or actor evidence");
   if(*action==FirstBootChapterAction::open_door||*action==FirstBootChapterAction::close_door)door_clear(after,actor,content);
  }
 }
 chapter_content_validate(after,content);
}
std::string chapter_content_hint(const GameplayStoreRecovery& snapshot,const FirstBootChapterActor& actor,std::string target_id,const FirstBootContent* content){
 View v(snapshot,content);if(!v.installed)return "Authored Adam hint: Jenison is not home. Start with what still responds.";
 auto cue=[&](const char* key,std::string fallback){if(content){const auto found=content->definition().hints.find(key);if(found!=content->definition().hints.end())return found->second;}return fallback;};
 const auto& fault=v.at(v.ids.fault);const auto& progress=v.at(v.ids.progress);const auto& npc=v.at(v.ids.npc_quest);
 if(nearby_active_fault(fault,actor))return cue("adam.danger","Authored Adam hint: Watch the arc. This feed is still live and damaged. Step clear, then isolate it from the safe edge.");
 const bool main=main_power(v),bypass=bypass_power(v),offline=flag(fault,"bypass_connected")&&!bypass&&!main;
 std::string recovery;
 if(offline){
  recovery="The relay feed is offline. ";
  if(flag(v.at(v.ids.service_door),"unlocked"))recovery+="Your latched service door is still available. ";
  if(number(fault,"capacity")==100)recovery+="Reconnect the repaired main line, or disconnect the old feed and connect a healthy relay.";
  else if(!flag(fault,"isolated"))recovery+="Isolate the damaged feed before connecting a healthy relay, or isolate and repair the main line.";
  else recovery+="Disconnect the old feed, connect a healthy relay, or repair the main line.";
 }
 const Vec3 npc_anchor{static_cast<float>(number(npc,"x")),static_cast<float>(number(npc,"y")+1),static_cast<float>(number(npc,"z"))};
 const std::string speaker=content?text(npc,"name")+": ":"Fictional Caretaker: ";
 if(target_id==v.ids.npc_quest&&hint_near(actor,npc_anchor,3)){
  if(integer(npc,"state")==static_cast<std::int64_t>(QuestState::completed))return speaker+"You connected the table lamp. That help is remembered. "+(offline?recovery:"The current feed can still be maintained.");
  if(integer(npc,"state")==static_cast<std::int64_t>(QuestState::declined))return speaker+"The Pencil Room is still open to you. The lamp is optional. "+(offline?recovery:"You can return to it whenever you choose.");
  if(offline)return speaker+"A Light for the Table is optional. "+recovery;
  return speaker+(main||bypass?"There is supply for the table now. You may connect its lamp, or leave it for later.":"A Light for the Table is optional. Repair the main feed or build a relay at the isolated service socket.");
 }
 if(offline)return "Authored Adam hint: "+recovery+" We can work from here.";
 if(bypass&&!flag(progress,"shelter_secured"))return flag(v.at(v.ids.service_door),"open")?
  cue("adam.bypass_open","Authored Adam hint: That relay feed holds. The service door is open. Step through when you are ready."):
  cue("adam.bypass_power","Authored Adam hint: That relay feed holds. The service door has power. You can open it when you are ready.");
 if(flag(progress,"pencil_visited"))return cue("adam.pencil","Authored Adam hint: The Pencil Room is here when you need it. We can keep building from this place.");
 if(flag(progress,"shelter_secured"))return cue("adam.shelter",content?"Authored Adam hint: This foothold is secured. "+text(npc,"name")+"'s task is optional; the writing room is yours to enter.":"Authored Adam hint: This foothold is secured. The Caretaker's task is optional; the writing room is yours to enter.");
 if(number(fault,"capacity")==100)return flag(fault,"isolated")?cue("adam.repaired_isolated","Authored Adam hint: The downstream repair holds. Reconnect the main feed when ready."):cue("adam.repaired_connected","Authored Adam hint: The main feed is restored. Open the main door, or make your own physical way into shelter.");
 return flag(fault,"isolated")?cue("adam.isolated","Authored Adam hint: The damaged feed is isolated. Repair it, or place and connect a healthy relay at the service socket."):cue("adam.live_fault","Authored Adam hint: Watch the warning before each arc. Scan the downstream fault, then isolate it from a safe edge.");
}
unsigned FirstBootChapterClock::advance(double seconds,bool active){if(!active){accumulator_=0;return 0;}if(!std::isfinite(seconds)||seconds<0)return 0;constexpr double dt=1.0/60;accumulator_+=std::min(seconds,8*dt);unsigned steps=0;while(accumulator_+1e-12>=dt&&steps<8){need(tick_<std::numeric_limits<std::uint64_t>::max(),"Chapter clock exhausted");++tick_;++steps;accumulator_=std::max(0.0,accumulator_-dt);}return steps;}
SceneSnapshot first_boot_chapter_scene(const GameplayStoreRecovery& s){return chapter_content_scene(s,nullptr);}
Vec3 first_boot_chapter_safe_return(const GameplayStoreRecovery& s){return chapter_content_return(s,nullptr);}
void first_boot_chapter_validate(const GameplayStoreRecovery& s){chapter_content_validate(s,nullptr);}
std::optional<GameplayChangeBatch> first_boot_chapter_action(const GameplayStoreRecovery& s,const FirstBootChapterCommand& c,const FirstBootChapterActor& a){return chapter_content_action(s,c,a,nullptr);}
void first_boot_chapter_rules(const GameplayStoreRecovery& b,const GameplayStoreRecovery& a,const GameplayChangeBatch& change,const FirstBootChapterActor& actor,const std::set<std::string>& ids){chapter_content_rules(b,a,change,actor,ids,nullptr);}
std::string first_boot_chapter_hint(const GameplayStoreRecovery& s,const FirstBootChapterActor& a,std::string target){return chapter_content_hint(s,a,std::move(target),nullptr);}
SceneSnapshot first_boot_content_scene(const GameplayStoreRecovery& s,const FirstBootContent& c){return chapter_content_scene(s,&c);}
Vec3 first_boot_content_safe_return(const GameplayStoreRecovery& s,const FirstBootContent& c){return chapter_content_return(s,&c);}
PlayerController first_boot_content_player(const GameplayStoreRecovery& s,const FirstBootContent& c){return PlayerController(chapter_content_scene(s,&c),chapter_content_return(s,&c));}
std::string first_boot_content_region(const GameplayStoreRecovery& s,Vec3 feet,const FirstBootContent& c){View check(s,&c);return first_boot_content_locate(c,feet);}
void first_boot_content_validate(const GameplayStoreRecovery& s,const FirstBootContent& c){chapter_content_validate(s,&c);}
std::optional<GameplayChangeBatch> first_boot_content_action(const GameplayStoreRecovery& s,const FirstBootChapterCommand& command,const FirstBootChapterActor& actor,const FirstBootContent& c){return chapter_content_action(s,command,actor,&c);}
std::optional<GameplayChangeBatch> first_boot_content_repair(const GameplayStoreRecovery& s,const std::string& id,const FirstBootChapterActor& actor,const FirstBootContent& c,std::string operation){View v(s,&c);auto b=durable_first_boot_repair(v.nodes,id,std::move(operation),s.scope.context);if(b)first_boot_content_rules(s,apply_plan(s,*b),*b,actor,c);return b;}
GameplayChangeBatch first_boot_content_build(const GameplayStoreRecovery& s,Vec3 point,const FirstBootChapterActor& actor,const FirstBootContent& c,std::string operation){
 View v(s,&c);if(first_boot_content_workshop_binding(c.definition())){const auto assembly=first_boot_content_relay_assembly(s,c);need(assembly.initialized&&assembly.part_available,"Collect the one relay part from the sampled path-contact tray before building");socket_build_position(v,point);}
 auto b=durable_first_boot_build(v.nodes,point,std::move(operation),s.scope.context);append_assembly(s,b,actor,c);first_boot_content_rules(s,apply_plan(s,b),b,actor,c);return b;
}
std::optional<GameplayChangeBatch> first_boot_content_dismantle(const GameplayStoreRecovery& s,const std::string& id,const FirstBootChapterActor& actor,const FirstBootContent& c,std::string operation){View v(s,&c);auto b=durable_first_boot_dismantle(v.nodes,id,std::move(operation),s.scope.context);if(b){append_assembly(s,*b,actor,c);first_boot_content_rules(s,apply_plan(s,*b),*b,actor,c);}return b;}
void first_boot_content_rules(const GameplayStoreRecovery& b,const GameplayStoreRecovery& a,const GameplayChangeBatch& change,const FirstBootChapterActor& actor,const FirstBootContent& c,const std::set<std::string>& ids){chapter_content_rules(b,a,change,actor,ids,&c);}
std::string first_boot_content_hint(const GameplayStoreRecovery& s,const FirstBootChapterActor& a,const FirstBootContent& c,std::string target){return chapter_content_hint(s,a,std::move(target),&c);}
FirstBootSupplyState first_boot_content_supply(const GameplayStoreRecovery& s,const FirstBootContent& c){
 View v(s,&c);need(v.installed,"Chapter supply requires complete installed chapter state");
 return {main_power(v),bypass_power(v)};
}
FirstBootChapterHazardSample FirstBootChapterClock::sample(const GameplayStoreRecovery& snapshot){
 const ComponentRecord* fault=nullptr;need(snapshot.components.size()<=10000,"Hazard snapshot exceeds bounds");for(const auto& r:snapshot.components)if(r.type_id==fault_type){need(!fault,"Duplicate chapter fault");fault=&r;}
 need(fault!=nullptr,"Chapter hazard requires its fault");const bool enabled=arc_active(*fault);
 if(!scope_||*scope_!=snapshot.scope){scope_=snapshot.scope;observed_active_=false;recovered_.reset();}if(enabled&&!observed_active_){activation_tick_=tick_;activation_id_=new_uuid();recovered_.reset();}observed_active_=enabled;
 FirstBootChapterHazardSample result;result.activation_id=activation_id_;result.active_tick=tick_;result.activation_tick=activation_tick_;const auto elapsed=tick_-activation_tick_;result.cycle=elapsed/240;
 if(enabled){const auto phase=elapsed%240;result.phase=phase<90?FirstBootArcPhase::telegraph:phase<120?FirstBootArcPhase::arc:FirstBootArcPhase::cooldown;result.recovery_available=!recovered_||*recovered_!=std::pair{activation_tick_,result.cycle};}return result;
}
void FirstBootChapterClock::acknowledge_recovery(const FirstBootChapterHazardSample& sample)noexcept{if(sample.phase==FirstBootArcPhase::arc&&sample.activation_id==activation_id_&&sample.activation_tick==activation_tick_&&(!recovered_||sample.cycle>recovered_->second))recovered_=std::pair{sample.activation_tick,sample.cycle};}
bool first_boot_chapter_hazard_contact(const GameplayStoreRecovery& snapshot,const FirstBootChapterActor& actor){
 actor_valid(actor);const auto found=std::find_if(snapshot.components.begin(),snapshot.components.end(),[](const auto& r){return r.type_id==fault_type;});need(found!=snapshot.components.end(),"Hazard fault missing");
 if(!arc_active(*found)||!is_uuid(actor.hazard.activation_id)||actor.hazard.phase!=FirstBootArcPhase::arc||actor.hazard.active_tick!=actor.active_tick||actor.hazard.activation_tick>actor.active_tick)return false;
 const auto elapsed=actor.active_tick-actor.hazard.activation_tick;if(elapsed%240<90||elapsed%240>=120||elapsed/240!=actor.hazard.cycle)return false;
 return std::abs(actor.feet.x-number(*found,"x"))<number(*found,"half_x")+actor.radius&&std::abs(actor.feet.z-number(*found,"z"))<number(*found,"half_z")+actor.radius&&actor.feet.y<number(*found,"y")+2.5&&actor.feet.y+actor.height>number(*found,"y");
}
SceneMesh first_boot_chapter_hazard_mesh(const GameplayStoreRecovery& snapshot,const FirstBootChapterHazardSample& sample){
 if(sample.phase==FirstBootArcPhase::dormant||sample.phase==FirstBootArcPhase::cooldown)return {};const auto found=std::find_if(snapshot.components.begin(),snapshot.components.end(),[](const auto& r){return r.type_id==fault_type;});need(found!=snapshot.components.end(),"Hazard visual fault missing");
 SceneSnapshot scene{snapshot.scope.world_id,snapshot.revision,{}};const auto color=sample.phase==FirstBootArcPhase::arc?Vec3{.65f,.85f,1}:Vec3{.95f,.4f,.08f};
 box(scene,found->entity_id,"Arc warning",{static_cast<float>(number(*found,"x")),static_cast<float>(number(*found,"y")+.025),static_cast<float>(number(*found,"z"))},{static_cast<float>(number(*found,"half_x")),.025f,static_cast<float>(number(*found,"half_z"))},color,.8f);
 if(sample.phase==FirstBootArcPhase::arc)for(int i=-1;i<=1;++i)box(scene,found->entity_id,"Power arc",{static_cast<float>(number(*found,"x")+i*number(*found,"half_x")*.5),static_cast<float>(number(*found,"y")+1.3),static_cast<float>(number(*found,"z"))},{.07f,1.3f,.07f},color,1);
 return mesh_from_snapshot(scene);
}
}
