// Private native UI projection. No commands, identities, storage or rendering.
// Include the public content/inspection headers and standard algorithm/math first.
namespace chapter_aim {
using namespace aibs;
struct Pick {
 std::optional<SceneHit> selected,solid;
 Vec3 point{};
 bool visible()const noexcept {
  return selected&&solid&&selected->persistent_id==solid->persistent_id&&selected->distance==solid->distance;
 }
};
class SolidCache {
 SceneSnapshot solid_;
 bool initialized_=false;
 std::size_t refreshes_=0;
public:
 const SceneSnapshot& sync(const SceneSnapshot& scene){
  if(!initialized_||solid_.world_id!=scene.world_id||solid_.revision!=scene.revision){
   auto next=scene;for(auto& object:next.objects)object.selectable=true;
   // Validate before publication using the actual picker, never a render mesh.
   (void)pick_scene(next,{},Vec3{0,0,1},0);solid_=std::move(next);initialized_=true;++refreshes_;
  }
  return solid_;
 }
 std::size_t refreshes()const noexcept{return refreshes_;}
 Pick pick(const SceneSnapshot& scene,Vec3 origin,Vec3 direction){
  Pick result;result.selected=pick_scene(scene,origin,direction);result.solid=pick_scene(sync(scene),origin,direction);
  if(result.selected){const auto length=std::hypot(direction.x,direction.y,direction.z);
   result.point={origin.x+direction.x/length*result.selected->distance,origin.y+direction.y/length*result.selected->distance,origin.z+direction.z/length*result.selected->distance};}
  return result;
 }
};
enum class FaultPart {socket,isolation,downstream};
inline FaultPart fault_part(Vec3 point,Vec3 socket,Vec3 isolation)noexcept{
 if(std::hypot(point.x-socket.x,point.z-socket.z)<1.7f)return FaultPart::socket;
 if(std::hypot(point.x-isolation.x,point.z-isolation.z)<.9f)return FaultPart::isolation;
 return FaultPart::downstream;
}
inline bool lamp_part(Vec3 point,Vec3 lamp)noexcept{return std::hypot(point.x-lamp.x,point.z-lamp.z)<1.7f;}
struct Prompt {std::string text;bool ready=false;std::string detail{};};
// Navigation only. Never projects an E admission or calls an action planner.
// Whole metres and eight bearing sectors keep small movements from republishing
// the native HUD on every rendered frame. Picking/reach remain authoritative.
inline std::string isolation_guidance(Vec3 feet,float camera_yaw,Vec3 target,double capacity,bool isolated,bool active){
 const auto finite=[](Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);};
 if(!active||!finite(feet)||!finite(target)||!std::isfinite(camera_yaw)||!std::isfinite(capacity)||capacity<0||capacity>100)return {};
 const bool find=capacity<100&&!isolated,reconnect=capacity==100&&isolated;
 if(!find&&!reconnect)return {};
 const std::string action=find?"Find isolation switch":"Reconnect at isolation switch";
 const double dx=static_cast<double>(target.x)-feet.x,dz=static_cast<double>(target.z)-feet.z;
 const double distance=std::hypot(dx,dz);
 if(distance<=3)return action+" nearby; aim until the E prompt names it.";
 constexpr double pi=3.14159265358979323846;
 const double bearing=std::remainder(std::atan2(dx,dz)-static_cast<double>(camera_yaw),2*pi);
 const int sector=static_cast<int>(std::floor((bearing+pi/8)/(pi/4)));
 constexpr std::array<const char*,8> directions{"ahead","ahead-right","right","behind-right","behind","behind-left","left","ahead-left"};
 const auto metres=static_cast<unsigned>(std::ceil(std::min(distance,99999.0)));
 return action+": "+std::to_string(metres)+(distance>99999?"+":"")+" m, "+directions[static_cast<std::size_t>((sector+8)%8)]+" (direction only; use a clear path).";
}
inline std::string bounded(std::string_view value,std::size_t maximum=48){
 std::string result;result.reserve(std::min(value.size(),maximum));
 for(std::size_t i=0;i<value.size();){
  const auto c=static_cast<unsigned char>(value[i]);const std::size_t count=c<0x80?1:c<0xe0?2:c<0xf0?3:4;
  if(i+count>value.size()||result.size()+count>maximum)break;
  if(c<32||c==127)result+=' ';else result.append(value.substr(i,count));i+=count;
 }
 if(result.size()<value.size()&&result.size()+3<=maximum)result+="...";return result;
}
inline const ComponentRecord* record(const GameplayStoreRecovery& state,std::string_view id,std::string_view type={}){
 const auto found=std::find_if(state.components.begin(),state.components.end(),[&](const auto& r){return r.entity_id==id&&(type.empty()||r.type_id==type);});
 return found==state.components.end()?nullptr:&*found;
}
inline bool flag(const ComponentRecord& r,const char* name){return std::get<bool>(r.fields.at(name));}
inline double number(const ComponentRecord& r,const char* name){return std::get<double>(r.fields.at(name));}
inline Vec3 point(const ComponentRecord& r,const std::string& prefix={}){return {static_cast<float>(number(r,(prefix+"x").c_str())),static_cast<float>(number(r,(prefix+"y").c_str())),static_cast<float>(number(r,(prefix+"z").c_str()))};}
// Current-objective navigation only. The actual centre pick and action planner
// retain authority over visibility, grounding, reach and E admission.
inline std::string workshop_guidance(const GameplayStoreRecovery& state,const FirstBootContent* content,
 Vec3 feet,Vec3 eye,float camera_yaw,float camera_pitch,bool active,const Prompt& focus,bool* current_objective=nullptr){
 if(current_objective)*current_objective=false;
 const auto finite=[](Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);};
 if(!active||!content||!finite(feet)||!finite(eye)||!std::isfinite(camera_yaw)||!std::isfinite(camera_pitch))return {};
 if(state.scope.world_id!=content->definition().world_id)return {};
 const auto binding=first_boot_content_workshop_binding(content->definition());if(!binding)return {};
 const auto* progress=record(state,binding->fixtures[4],opening_workshop_component_type);if(!progress||progress->version!=1)return {};
 const auto probe=progress->fields.find("has_probe"),supply=progress->fields.find("supply_sample"),path=progress->fields.find("path_sample");
 if(probe==progress->fields.end()||supply==progress->fields.end()||path==progress->fields.end())return {};
 const auto* has_probe=std::get_if<bool>(&probe->second);const auto* supply_sample=std::get_if<std::string>(&supply->second);const auto* path_sample=std::get_if<std::string>(&path->second);
 if(!has_probe||!supply_sample||!path_sample)return {};
 const std::size_t slot=!*has_probe?0:supply_sample->empty()?1:path_sample->empty()?2:3;if(slot==3)return {};
 constexpr std::array<const char*,3> names{"Diagnostic probe","Supply contact","Path contact"};
 constexpr std::array<std::string_view,3> actions{"Collect diagnostic probe","Sample supply contact","Sample path contact"};
 const auto& fixtures=content->definition().fixtures;
 const auto target=std::find_if(fixtures.begin(),fixtures.end(),[&](const auto& f){return f.object.persistent_id==binding->fixtures[slot];});
 if(target==fixtures.end()||!finite(target->object.center))return {};
 if(current_objective)*current_objective=true;
 // Once the actual centre prompt offers this action it already gives the
 // useful instruction. A different ready target must not hide this objective.
 if(focus.ready&&focus.text==actions[slot])return {};
 const auto center=target->object.center;
 const double dx=static_cast<double>(center.x)-eye.x,dy=static_cast<double>(center.y)-eye.y,dz=static_cast<double>(center.z)-eye.z;
 const double horizontal=std::hypot(dx,dz),distance=std::hypot(static_cast<double>(center.x)-feet.x,static_cast<double>(center.z)-feet.z);
 constexpr double pi=3.14159265358979323846;
 const double turn=std::remainder(std::atan2(dx,dz)-static_cast<double>(camera_yaw),2*pi);
 const double tilt=std::atan2(dy,horizontal)-static_cast<double>(camera_pitch);
 const auto metres=static_cast<unsigned>(std::ceil(std::min(distance,99999.0)));
 std::string line="Workshop: "+std::string(names[slot])+", "+std::to_string(metres)+(distance>99999?"+":"")+" m";
 const auto degrees=[](double radians){return static_cast<unsigned>(std::ceil(std::min(std::abs(radians)*180/pi,360.0)));};
 if(horizontal>.05&&std::abs(turn)>.008)line+="; turn "+std::string(turn>0?"right ":"left ")+std::to_string(degrees(turn))+" deg";
 if(std::abs(tilt)>.008)line+="; look "+std::string(tilt>0?"up ":"down ")+std::to_string(degrees(tilt))+" deg";
 if(distance>3.2)line+="; use a clear path.";
 else line+="; aim until centre prompt names it.";
 return line;
}
inline Prompt workshop(const ComponentRecord& progress,const OpeningWorkshopBinding& binding,const OpeningWorkshopCircuit& circuit,OpeningWorkshopAction action,const OpeningWorkshopActor& actor){
 const auto slot=static_cast<std::size_t>(action);
 constexpr std::array<std::string_view,5> names{"Probe","Supply contact","Path contact","Feed tester","Workbench"};
 constexpr std::array<std::string_view,5> actions{"Collect diagnostic probe","Sample supply contact","Sample path contact","Test present feed","Commission workbench"};
 constexpr std::array<std::string_view,5> done{"Diagnostic probe collected","Supply sample recorded","Path sample recorded","Present feed already verified","Workbench online"};
 if(slot>=names.size())return {"Unknown workshop station",false};
 try {
  const auto change=plan_opening_workshop(progress,binding,circuit,action,actor);
  if(change)return {std::string(actions[slot]),true};
  if(const auto saved=opening_workshop_saved_reading(progress,binding,action,circuit.fault_id))return {"Saved: "+*saved,false};
  if(slot==4&&!opening_workshop_online(progress,binding,circuit))return {"Workbench claimed; restore a healthy feed",false};
  return {std::string(done[slot]),false};
 }catch(const std::invalid_argument& error){
  const std::string_view why=error.what();std::string_view short_reason="unavailable";
  if(why=="Move within visible grounded reach of that workshop fixture")short_reason="move closer on solid ground";
  else if(why=="Collect the diagnostic probe in the reserve nook first")short_reason="collect probe first";
  else if(why=="Sample both actual contacts before verifying a feed")short_reason="sample both contacts first";
  else if(why=="No healthy repaired main or connected isolated bypass is available")short_reason="restore a healthy feed first";
  else if(why=="Commission the workbench from inside the actual shelter")short_reason="enter the shelter first";
  else if(why=="The current feed differs from its successful test; test the present source again")short_reason="test present feed again";
  return {std::string(names[slot])+": "+std::string(short_reason),false};
 }
}
// This projection intentionally does not call a chapter action planner: those
// planners mint operation/event UUIDs. Only Workshop's pure local query may run.
inline Prompt describe(const Pick& aim,const SceneSnapshot& solid,const GameplayStoreRecovery& state,
 const FirstBootChapterIds& ids,const FirstBootContent* content,const FirstBootChapterActor& actor,const OpeningInspection* inspection=nullptr,
 const FirstBootRelayAssemblyState* assembly=nullptr){
 if(!aim.selected)return {"Aim at a visible mechanism",false};
 if(!aim.visible())return {"View blocked; find a clear approach",false};
 const auto& id=aim.selected->persistent_id;
 if(inspection&&aim.solid->distance<=10){
  const bool reached=std::hypot(static_cast<double>(actor.feet.x)-inspection->center.x,static_cast<double>(actor.feet.y)-inspection->center.y,static_cast<double>(actor.feet.z)-inspection->center.z)<=3.2;
  return {(reached?(inspection->action==OpeningInspectionAction::seat?"Quiet reading: ":"Read: "):"Move closer to read: ")+bounded(inspection->title,38),reached};
 }
 if(content){if(const auto binding=first_boot_content_workshop_binding(content->definition())){
  const auto fixture=std::find(binding->fixtures.begin(),binding->fixtures.end(),id);
  if(fixture!=binding->fixtures.end()){
   if(state.scope.world_id!=content->definition().world_id)return {"Workshop station unavailable",false};
   const auto index=static_cast<std::size_t>(std::distance(binding->fixtures.begin(),fixture));
   const auto source=std::find_if(content->definition().fixtures.begin(),content->definition().fixtures.end(),[&](const auto& f){return f.object.persistent_id==id;});
   const auto* progress=record(state,binding->fixtures[4],opening_workshop_component_type);
   if(source==content->definition().fixtures.end()||!progress)return {"Workshop station unavailable",false};
   const auto target=source->object.center;const Vec3 eye{actor.feet.x,actor.feet.y+actor.height*.5f,actor.feet.z};
   const auto hit=pick_scene(solid,eye,{target.x-eye.x,target.y-eye.y,target.z-eye.z},3.2f);
   OpeningWorkshopActor evidence{id,std::hypot(static_cast<double>(eye.x)-target.x,static_cast<double>(eye.y)-target.y,static_cast<double>(eye.z)-target.z),actor.grounded,actor.inspection_mode,hit&&hit->persistent_id==id,first_boot_content_locate(*content,actor.feet)=="hub"};
   auto prompt=workshop(*progress,*binding,first_boot_content_workshop_circuit(state,*content),static_cast<OpeningWorkshopAction>(index),evidence);
   if(index==2&&prompt.text.starts_with("Saved: ")&&(assembly?*assembly:first_boot_content_relay_assembly(state,*content)).pickup_available)
    return {"Collect relay assembly",true,prompt.text};
   return prompt;
  }
 }}
 const auto* selected=record(state,id);if(!selected)return {"Authored world fixture",false};
 const auto* fault=record(state,ids.fault);if(!fault)return {"Mechanism unavailable",false};
 if(selected->type_id=="firstboot.Node"){
  if(std::hypot(aim.point.x-actor.feet.x,aim.point.y-(actor.feet.y+actor.height*.5f),aim.point.z-actor.feet.z)>3)return {"Component: move within reach",false};
  const auto socket=point(*fault,"socket_");
  if(number(*selected,"firstboot.kind")==6){
   if(!flag(*selected,"alive"))return {"Relay unavailable",false};
   if(number(*selected,"capacity")<100)return {"Repair selected relay",false};
   if(std::hypot(number(*selected,"x")-socket.x,number(*selected,"z")-socket.z)<=2){
    if(flag(*fault,"bypass_connected"))return {"Relay: disconnect old feed",false};
    if(std::abs(number(*selected,"y")-(socket.y+1.2))>.25)return {"Relay: place at service socket height",false};
    return {flag(*fault,"isolated")?"Relay: connect bypass feed":"Relay: isolate main before connecting",false};
   }
  }
  return {number(*selected,"capacity")==100?"Component restored; Delete dismantles relay":"Repair selected component",false};
 }
 if(selected->type_id=="firstboot.Door"){
  const auto& role=std::get<std::string>(selected->fields.at("role"));const std::string name=role=="main"?"Main door":role=="service"?"Service door":"Pencil Room door";
  return {name+(flag(*selected,"open")?": close":flag(*selected,"unlocked")||role=="pencil"?": open":": try powered latch"),false};
 }
 if(id==ids.fault){
  const auto socket=point(*selected,"socket_");const auto location=point(*selected);
  const auto isolation=content?content->definition().isolation_switch:Vec3{location.x-2.5f,location.y,location.z};
  switch(fault_part(aim.point,socket,isolation)){
   case FaultPart::socket:{
    if(flag(*selected,"bypass_connected"))return {"Service socket: disconnect old feed",false};
    bool healthy=false;
    for(const auto& node:state.components)if(node.type_id=="firstboot.Node"&&flag(node,"alive")&&number(node,"firstboot.kind")==6&&number(node,"capacity")==100&&
       std::hypot(number(node,"x")-socket.x,number(node,"z")-socket.z)<=2&&std::abs(number(node,"y")-(socket.y+1.2))<=.25){healthy=true;break;}
    if(!healthy)return {"Service socket: needs a healthy relay",false};
    return {flag(*selected,"isolated")?"Service socket: connect built relay":"Service socket: isolate main before connecting",false};
   }
   case FaultPart::isolation:return {flag(*selected,"isolated")?(number(*selected,"capacity")==100?"Isolation switch: reconnect repaired main":"Isolation switch: restore DAMAGED live feed"):"Isolation switch: isolate main feed",false};
   case FaultPart::downstream:return {!flag(*selected,"diagnosed")?"Inspect downstream power fault":!flag(*selected,"isolated")?"Power fault: isolate feed before repair":number(*selected,"capacity")==100?"Power fault already repaired":"Repair isolated power fault",false};
  }
 }
 if(id==ids.npc_quest){
  if(lamp_part(aim.point,point(*selected,"lamp_")))return {flag(*selected,"lamp_connected")?"Table lamp already connected":"Table lamp: connect (power required)",false};
  return {"Caretaker: ask about the optional lamp",false};
 }
 return {"Authored chapter mechanism",false};
}
// Nearby Workshop option, not action admission. Placement is the existing
// native centre-ray board projection; this query never builds a candidate or
// mints an operation/entity UUID.
inline std::string workshop_bypass_guidance(const GameplayStoreRecovery& state,const FirstBootContent* content,
 const FirstBootChapterActor& actor,std::optional<Vec3> current_build_placement,float camera_yaw,bool active,
 const FirstBootRelayAssemblyState* cached_assembly=nullptr){
 const auto finite=[](Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);};
 if(!active||!content||actor.inspection_mode||!finite(actor.feet)||!std::isfinite(camera_yaw)||state.scope.world_id!=content->definition().world_id)return {};
 const auto binding=first_boot_content_workshop_binding(content->definition());
 if(!binding||!record(state,binding->fixtures[4],opening_workshop_component_type))return {};
 const ComponentRecord* fault=nullptr;
 for(const auto& component:state.components)if(component.type_id=="firstboot.PowerFault"){
  if(fault)return {};fault=&component;
 }
 if(!fault)return {};
 const auto real=[](const ComponentRecord& r,const char* key)->std::optional<double>{
  const auto field=r.fields.find(key);if(field==r.fields.end())return {};
  const auto* value=std::get_if<double>(&field->second);return value&&std::isfinite(*value)?std::optional<double>{*value}:std::nullopt;
 };
 const auto boolean=[](const ComponentRecord& r,const char* key)->std::optional<bool>{
  const auto field=r.fields.find(key);if(field==r.fields.end())return {};
  const auto* value=std::get_if<bool>(&field->second);return value?std::optional<bool>{*value}:std::nullopt;
 };
 const auto sx=real(*fault,"socket_x"),sy=real(*fault,"socket_y"),sz=real(*fault,"socket_z"),capacity=real(*fault,"capacity");
 const auto connected=boolean(*fault,"bypass_connected"),isolated=boolean(*fault,"isolated");
 const auto reference=fault->fields.find("bypass_relay");
 const auto* relay_id=reference==fault->fields.end()?nullptr:std::get_if<std::string>(&reference->second);
 if(!sx||!sy||!sz||!capacity||*capacity<0||*capacity>100||!connected||!isolated||!relay_id)return {};
 if(std::hypot(static_cast<double>(actor.feet.x)-*sx,static_cast<double>(actor.feet.z)-*sz)>8||std::abs(static_cast<double>(actor.feet.y)-*sy)>4)return {};
 bool healthy_at_socket=false,damaged_at_socket=false,referenced_alive=false,referenced_healthy=false;
 for(const auto& node:state.components){
  if(node.type_id!="firstboot.Node")continue;
  const auto kind=real(node,"firstboot.kind"),level=real(node,"capacity");const auto alive=boolean(node,"alive");
  if(!kind||*kind!=6||!alive||!level||*level<0||*level>100)continue;
  if(node.entity_id==*relay_id){referenced_alive=*alive;referenced_healthy=*alive&&*level==100;}
  if(!*alive)continue;
  const auto x=real(node,"x"),y=real(node,"y"),z=real(node,"z");if(!x||!y||!z)continue;
  if(std::hypot(*x-*sx,*z-*sz)<=2.0&&std::abs(*y-(*sy+1.2))<=.25){
   healthy_at_socket=healthy_at_socket||*level==100;damaged_at_socket=damaged_at_socket||*level<100;
  }
 }
 if(*connected){
  if(*isolated&&referenced_healthy)return "Bypass: Relay feed live.";
  if(*capacity==100&&!*isolated)return "Bypass: Main feed live; relay feed inactive.";
  if(referenced_healthy)return "Bypass: Relay connected, feed inactive. Isolate main to use bypass.";
  if(referenced_alive)return "Bypass: Relay feed lost. Repair the relay, or disconnect old feed before replacement.";
  return "Bypass: Relay feed lost. Disconnect old feed before connecting a replacement.";
 }
 // A working main feed needs no unsolicited alternative construction prompt.
 if(*capacity==100&&!*isolated)return {};
 if(healthy_at_socket)return *isolated?
  "Bypass: Relay built, not connected. Aim at relay/socket; E connects when in reach.":
  "Bypass: Relay built, not connected. Isolate main before connecting.";
 if(damaged_at_socket)return "Bypass: Relay at socket needs repair; aim at it for E.";
 const auto parts=cached_assembly?*cached_assembly:first_boot_content_relay_assembly(state,*content);
 if(parts.alive_relays)return "Bypass: Find your earlier relay and use Delete to reclaim its assembly.";
 if(!parts.part_available)return parts.pickup_available?
  "Bypass: Collect one relay assembly with E at the sampled path contact.":
  "Bypass: Sample the path contact with the probe, then press E there to collect the relay assembly.";
 const auto find_socket=[&](){
  constexpr double pi=3.14159265358979323846;
  const double dx=*sx-actor.feet.x,dz=*sz-actor.feet.z;
  const auto metres=static_cast<unsigned>(std::ceil(std::hypot(dx,dz)));
  if(!*isolated||metres<=2)return std::string("Bypass: 1 assembly carried. Aim down at the service socket.");
  const auto bearing=std::remainder(std::atan2(dx,dz)-static_cast<double>(camera_yaw),2*pi);
  const int sector=static_cast<int>(std::floor((bearing+pi/8)/(pi/4)));
  constexpr std::array<const char*,8> directions{"ahead","ahead-right","right","behind-right","behind","behind-left","left","ahead-left"};
  return "Bypass: 1 assembly carried. Service socket "+std::to_string(metres)+" m, "+directions[static_cast<std::size_t>((sector+8)%8)]+"; aim down.";
 };
 if(!current_build_placement||!finite(*current_build_placement))return find_socket();
 const auto position=*current_build_placement;
 if(std::hypot(static_cast<double>(position.x)-*sx,static_cast<double>(position.z)-*sz)>2.0||std::abs(static_cast<double>(position.y)-(*sy+1.2))>.25)
  return *isolated?find_socket():"Bypass: 1 assembly carried. Placement misses service socket; adjust aim before B.";
 return "Bypass: 1 assembly carried. Press B to install it at the service socket.";
}
inline std::string line(const Prompt& prompt,bool active){
 if(!active)return "E (centre): paused / waiting for saves";
 auto result="E (centre): "+bounded(prompt.text,61);
 if(!prompt.detail.empty())result+="\n"+bounded(prompt.detail,96);
 return result;
}
}
