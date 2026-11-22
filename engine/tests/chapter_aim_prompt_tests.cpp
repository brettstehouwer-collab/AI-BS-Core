#include <aibs/warm_opening.hpp>
#include <aibs/opening_inspections.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#ifndef AIBS_AIM_HELPER
#define AIBS_AIM_HELPER "../apps/chapter_aim_prompt.inl"
#endif
#include AIBS_AIM_HELPER
using namespace aibs;
namespace {
unsigned checks=0;
void check(bool yes,const char* why){++checks;if(!yes)throw std::runtime_error(why);}
constexpr const char* world="11111111-1111-4111-8111-111111111111";
constexpr const char* other="22222222-2222-4222-8222-222222222222";
constexpr const char* target="33333333-3333-4333-8333-333333333333";
SceneObject box(std::string id,float z,bool selectable=true){return {std::move(id),"test",{0,0,z},{.4f,.4f,.4f},{.5f,.5f,.5f},0,selectable,{}};}
void isolation_navigation(){
 const auto guide=[](Vec3 feet,float yaw,Vec3 point,double capacity=0,bool isolated=false,bool active=true){return chapter_aim::isolation_guidance(feet,yaw,point,capacity,isolated,active);};
 const Vec3 origin{},ahead{0,0,10};
 check(guide(origin,0,ahead)=="Find isolation switch: 10 m, ahead (direction only; use a clear path).","Damaged live feed lacks named navigation");
 check(guide(origin,0,ahead,100,true)=="Reconnect at isolation switch: 10 m, ahead (direction only; use a clear path).","Repaired isolated feed lacks reconnect navigation");
 check(guide(origin,0,ahead,0,true).empty(),"Isolated damaged feed hides repair/bypass choice");
 check(guide(origin,0,ahead,100,false).empty(),"Connected healthy feed advertises unnecessary switch action");
 check(guide(origin,0,ahead,0,false,false).empty(),"Paused controls retain active navigation");
 check(guide(origin,0,ahead,-1).empty()&&guide(origin,0,ahead,101).empty(),"Invalid capacity produces plausible guidance");
 constexpr std::array<Vec3,8> points{{{0,0,10},{10,0,10},{10,0,0},{10,0,-10},{0,0,-10},{-10,0,-10},{-10,0,0},{-10,0,10}}};
 constexpr std::array<const char*,8> names{"ahead","ahead-right","right","behind-right","behind","behind-left","left","ahead-left"};
 for(std::size_t n=0;n<points.size();++n){
  const auto result=guide(origin,0,points[n]);
  check(result.find(std::string(", ")+names[n]+" (direction only;")!=std::string::npos,"Navigation bearing sector incorrect");
 }
 constexpr float pi=3.14159265358979323846f;
 check(guide(origin,pi-.01f,{0,0,-10})==guide(origin,-pi+.01f,{0,0,-10}),"Bearing wraparound changes equivalent ahead cue");
 check(guide(origin,pi/2,{10,0,0})==guide(origin,0,ahead),"Camera-relative bearing ignored");
 check(guide({21,4,-14},0,{21,17,-4})==guide(origin,0,ahead),"Translated world or vertical offset changes horizontal navigation");
 check(guide(origin,0,{0,0,10.1f})==guide(origin,0,{0,0,10.8f}),"Small movement republishes within one metre bucket");
 check(guide(origin,.01f,ahead)==guide(origin,-.01f,ahead),"Small turn republishes within one bearing sector");
 const auto near=guide(origin,0,{1,0,1});
 check(near=="Find isolation switch nearby; aim until the E prompt names it.","Nearby navigation claims or omits actual E prompt");
 check(guide(origin,0,origin,100,true)=="Reconnect at isolation switch nearby; aim until the E prompt names it.","Coincident reconnect lacks actual E prompt requirement");
 const float nan=std::numeric_limits<float>::quiet_NaN(),inf=std::numeric_limits<float>::infinity();
 for(const auto bad:{nan,inf,-inf}){
  check(guide({bad,0,0},0,ahead).empty()&&guide({0,bad,0},0,ahead).empty()&&guide({0,0,bad},0,ahead).empty(),"Nonfinite feet admitted to guidance");
  check(guide(origin,0,{bad,0,10}).empty()&&guide(origin,0,{0,bad,10}).empty()&&guide(origin,0,{0,0,bad}).empty(),"Nonfinite target admitted to guidance");
  check(guide(origin,bad,ahead).empty()&&guide(origin,0,ahead,bad).empty(),"Nonfinite yaw/capacity admitted to guidance");
 }
 const auto far=guide({-std::numeric_limits<float>::max(),0,0},0,{std::numeric_limits<float>::max(),0,0});
 check(far.find("99999+ m, right")!=std::string::npos&&far.size()<=128,"Large finite navigation overflows or becomes unbounded");
}
void geometry(){
 SceneSnapshot scene{world,0,{box(target,4)}};chapter_aim::SolidCache cache;
 auto hit=cache.pick(scene,{},Vec3{0,0,1});check(hit.visible()&&hit.point.z==hit.selected->distance,"Clear actual surface was rejected");
 for(int n=0;n<100;++n)(void)cache.pick(scene,{},Vec3{0,0,1});check(cache.refreshes()==1,"Unchanged scene rebuilt solid cache");
 scene.revision=1;scene.objects.insert(scene.objects.begin(),box(other,2,false));hit=cache.pick(scene,{},Vec3{0,0,1});
 check(hit.selected&&hit.selected->persistent_id==target&&!hit.visible(),"Nonselectable nearer wall did not block aimed mechanism");
 scene.revision=2;scene.objects.front().persistent_id=target;hit=cache.pick(scene,{},Vec3{0,0,1});
 check(hit.solid->persistent_id==hit.selected->persistent_id&&hit.solid->distance<hit.selected->distance&&!hit.visible(),"Nearer same-UUID part was incorrectly accepted");
 scene.revision=3;scene.objects.erase(scene.objects.begin());check(cache.pick(scene,{},Vec3{0,0,1}).visible(),"Door removal/dismantle revision left stale blocker");
 scene.world_id=other;scene.objects.insert(scene.objects.begin(),box(world,2,false));check(!cache.pick(scene,{},Vec3{0,0,1}).visible(),"Changed world at same revision reused stale cache");
 check(cache.refreshes()==5,"Unexpected revision cache refresh count");
 scene.revision=4;scene.objects.front().center.x=4;check(cache.pick(scene,{},Vec3{0,0,1}).visible(),"Opened blocker revision remained opaque");
 const auto& solids=cache.sync(scene);check(solids.objects.front().selectable&&!scene.objects.front().selectable,"Solid projection mutated source selectable flags");
 scene.revision=5;scene.objects.front().half_extent.x=0;bool rejected=false;try{(void)cache.sync(scene);}catch(const std::invalid_argument&){rejected=true;}check(rejected,"Malformed replacement scene admitted to cache");
 check(cache.refreshes()==6,"Failed cache replacement was published");
 const Vec3 socket{0,0,0},isolation{8,0,0};
 check(chapter_aim::fault_part({std::nextafter(1.7f,0.f),5,0},socket,isolation)==chapter_aim::FaultPart::socket,"Socket strict inside threshold changed");
 check(chapter_aim::fault_part({1.7f,0,0},socket,isolation)==chapter_aim::FaultPart::downstream,"Socket boundary became inclusive");
 check(chapter_aim::fault_part({0,0,std::nextafter(.9f,0.f)},Vec3{8,0,0},{})==chapter_aim::FaultPart::isolation,"Isolation strict inside threshold changed");
 check(chapter_aim::fault_part({0,0,.9f},Vec3{8,0,0},{})==chapter_aim::FaultPart::downstream,"Isolation boundary became inclusive");
 check(chapter_aim::fault_part({},socket,{})==chapter_aim::FaultPart::socket,"Overlapping socket/isolation precedence changed");
 check(chapter_aim::lamp_part({1.6f,50,0},{})&&!chapter_aim::lamp_part({1.7f,0,0},{}),"Lamp XZ threshold changed");
 check(chapter_aim::line({"Repair isolated power fault",true},false).find("paused")!=std::string::npos,"Paused state advertised active E action");
 check(chapter_aim::bounded(std::string(500,'x')).size()<=48,"Unbounded target text");
 check(chapter_aim::bounded("abc\nxyz")=="abc xyz","HUD target could inject rows");
 check(chapter_aim::bounded("\xc3\xa9\xc3\xa9",3)=="\xc3\xa9","UTF8 target truncated in codepoint");
}
OpeningWorkshopBinding binding(){return {{{"44444444-4444-4444-8444-444444444444","55555555-5555-4555-8555-555555555555","66666666-6666-4666-8666-666666666666","77777777-7777-4777-8777-777777777777","88888888-8888-4888-8888-888888888888"}}};}
void workshop(){
 const auto b=binding();auto r=opening_workshop_initial(b);OpeningWorkshopCircuit c{target,"",20,0,false,false,false};const auto original=r;
 auto query=[&](unsigned slot,bool grounded=true,bool visible=true,bool shelter=false){return chapter_aim::workshop(r,b,c,static_cast<OpeningWorkshopAction>(slot),{b.fixtures[slot],2,grounded,false,visible,shelter});};
 auto p=query(0);check(p.ready&&p.text=="Collect diagnostic probe","Probe action unclear");
 check(!query(0,false).ready&&!query(0,true,false).ready,"Blocked actor was advertised ready");
 check(!query(1).ready&&query(1).text.find("collect probe")!=std::string::npos,"Supply dependency missing");
 for(int n=0;n<1000;++n){(void)query(static_cast<unsigned>(n)%5);}check(r==original,"Pure repeated prompt mutated progress");
 r.fields["has_probe"]=true;check(query(1).ready&&query(2).ready,"Contacts not ready after probe");
 check(!query(3).ready&&query(3).text.find("both contacts")!=std::string::npos,"Tester skipped contacts");
 const auto sample=opening_workshop_signature(c);r.fields["supply_sample"]=sample;r.fields["path_sample"]=sample;
 check(!query(3).ready&&query(3).text.find("healthy feed")!=std::string::npos,"Dead feed advertised test ready");
 for(bool bypass:{false,true}){
  c.capacity=bypass?20:100;c.isolated=bypass;c.bypass_connected=bypass;c.relay_id=bypass?other:"";c.relay_alive=bypass;c.relay_capacity=bypass?100:0;
  check(query(3).ready,"Healthy main/bypass feed not ready");r.fields["tested_signature"]=opening_workshop_signature(c);
  check(!query(3).ready&&query(3).text.find("already verified")!=std::string::npos,"No-op test advertised a new result");
  check(!query(4).ready&&query(4).text.find("shelter")!=std::string::npos,"Bench accepted outside shelter");
  check(query(4,true,true,true).ready,"Verified source not commissionable inside shelter");
  c.capacity=bypass?19:99;check(!query(4,true,true,true).ready,"Changed source incorrectly retained test readiness");
  r.fields["tested_signature"]=std::string{};
 }
 c={target,"",100,0,false,false,false};r.fields["tested_signature"]=opening_workshop_signature(c);r.fields["bench_claimed"]=true;
 check(query(4,true,true,true).text=="Workbench online","Claimed healthy bench wording changed");
 c.capacity=20;check(query(4,true,true,true).text.find("restore a healthy feed")!=std::string::npos,"Claimed bench falsely online after loss");
 c.capacity=100;c.relay_capacity=7;check(query(4,true,true,true).text=="Workbench online","Claimed bench incorrectly requires historical signature match");
}
void workshop_saved_readings(){
 const auto b=binding();auto r=opening_workshop_initial(b);r.fields["has_probe"]=true;
 const OpeningWorkshopCircuit supply{target,"",0,0,false,false,false},path{target,"",100,0,false,false,false};
 const OpeningWorkshopCircuit present{target,other,25,100,true,true,true};
 const auto actor=[&](unsigned slot){return OpeningWorkshopActor{b.fixtures[slot],2,true,false,true,false};};
 const auto prompt=[&](const ComponentRecord& record,unsigned slot,OpeningWorkshopActor evidence){return chapter_aim::workshop(record,b,present,static_cast<OpeningWorkshopAction>(slot),evidence);};
 check(prompt(r,1,actor(1)).ready&&!opening_workshop_saved_reading(r,b,OpeningWorkshopAction::sample_supply,target),"Unsampled contact lost E action or gained an invented reading");
 r.fields["supply_sample"]=opening_workshop_signature(supply);r.fields["path_sample"]=opening_workshop_signature(path);const auto original=r;
 const auto a=prompt(r,1,actor(1)),p=prompt(r,2,actor(2));
 check(!a.ready&&a.text=="Saved: "+opening_workshop_reading(supply),"Supply prompt does not display its own stored observation");
 check(!p.ready&&p.text=="Saved: "+opening_workshop_reading(path),"Path prompt substituted supply or present circuit");
 check(a.text!=p.text&&a.text.find(opening_workshop_reading(present))==std::string::npos,"Changed current feed overwrote a saved contact reading");
 const auto restored=gameplay_codec::decode_component(gameplay_codec::encode_component(r));
 check(prompt(restored,1,actor(1)).text==a.text&&prompt(restored,2,actor(2)).text==p.text,"Existing component wire roundtrip lost readable observations");
 auto blocked=actor(1);blocked.visible=false;
 check(prompt(r,1,blocked).text.find("move closer")!=std::string::npos&&prompt(r,1,blocked).text.find("Saved:")==std::string::npos,"Blocked contact bypassed existing error feedback");
 auto distant=actor(1);distant.distance=3.3;
 check(prompt(r,1,distant).text.find("move closer")!=std::string::npos,"Saved reading bypassed existing contact reach");
 auto inspecting=actor(1);inspecting.inspection_mode=true;
 check(prompt(r,1,inspecting).text.find("Saved:")==std::string::npos,"Inspection unexpectedly advertised a contact reading");
 const auto rejects=[&](const ComponentRecord& record,const std::string& fault){try{(void)opening_workshop_saved_reading(record,b,OpeningWorkshopAction::sample_supply,fault);return false;}catch(const std::invalid_argument&){return true;}};
 auto malformed=r;malformed.fields["supply_sample"]=std::string("W1|bad");
 check(rejects(malformed,target)&&prompt(malformed,1,actor(1)).text=="Supply contact: unavailable","Malformed saved stamp became a plausible reading");
 check(rejects(r,other),"Foreign fault observation was displayed");
 auto wrong_owner=r;wrong_owner.entity_id=other;
 check(rejects(wrong_owner,target),"Wrong owned Workshop record was displayed");
 auto wrong_type=r;wrong_type.fields["supply_sample"]=true;
 check(rejects(wrong_type,target),"Wrongly typed saved stamp was coerced to a reading");
 check(!opening_workshop_saved_reading(r,b,OpeningWorkshopAction::test_feed,target),"Noncontact acquired an unrelated saved reading");
 auto extreme=r;auto tiny=supply;tiny.capacity=std::numeric_limits<double>::denorm_min();extreme.fields["supply_sample"]=opening_workshop_signature(tiny);
 const auto compact=prompt(extreme,1,actor(1));
 check(compact.text.size()<=61&&chapter_aim::line(compact,true)=="E (centre): "+compact.text&&compact.text.ends_with("feed none"),"Saved reading was clipped or exceeded compact prompt bound");
 for(int n=0;n<1000;++n)(void)prompt(r,1,actor(1));
 check(r==original,"Repeated saved-read projection mutated observations");
}
FirstBootChapterIds ids(const FirstBootContent& content){FirstBootChapterIds out;for(const auto& r:content.definition().initial_records){if(r.type_id=="firstboot.PowerFault")out.fault=r.entity_id;else if(r.type_id=="firstboot.NPCQuest")out.npc_quest=r.entity_id;else if(r.type_id=="firstboot.ChapterProgress")out.progress=r.entity_id;else if(r.type_id=="firstboot.Door"){const auto role=std::get<std::string>(r.fields.at("role"));(role=="main"?out.main_door:role=="service"?out.service_door:out.pencil_door)=r.entity_id;}}return out;}
void workshop_navigation(const FirstBootContent& content,const GameplayStoreRecovery& initial){
 const auto b=*first_boot_content_workshop_binding(content.definition());
 const auto fixture=std::find_if(content.definition().fixtures.begin(),content.definition().fixtures.end(),[&](const auto& f){return f.object.persistent_id==b.fixtures[0];});
 if(fixture==content.definition().fixtures.end())throw std::runtime_error("Navigation probe fixture missing");
 const auto target_point=fixture->object.center;
 const Vec3 feet{target_point.x,target_point.y-1.62f,target_point.z-10},eye{feet.x,feet.y+1.62f,feet.z};
 auto state=initial;const auto original=state.components;const auto encoded=first_boot_content_encode(content);
 const auto cue=[&](Vec3 from,Vec3 camera,float yaw=0,float pitch=0,bool active=true,chapter_aim::Prompt focus={}){
  return chapter_aim::workshop_guidance(state,&content,from,camera,yaw,pitch,active,focus);
 };
 const auto far=cue(feet,eye);
 check(far.find("Diagnostic probe")!=std::string::npos&&far.find("use a clear path")!=std::string::npos,"Workshop navigation omits probe objective or path caveat");
 constexpr float pi=3.14159265358979323846f;
 check(cue(feet,eye,pi/2).find("turn left")!=std::string::npos,"Workshop bearing ignores camera yaw");
 const Vec3 west_feet{target_point.x-10,feet.y,target_point.z},west_eye{west_feet.x,eye.y,west_feet.z};
 check(cue(west_feet,west_eye).find("turn right")!=std::string::npos,"Workshop east target gives incorrect turn direction");
 check(cue(feet,eye,0,.5f).find("look down")!=std::string::npos,"Workshop pitch ignores an upward-looking camera");
 check(cue(feet,eye,0,-.5f).find("look up")!=std::string::npos,"Workshop pitch ignores a downward-looking camera");
 const Vec3 near_feet{target_point.x,target_point.y-1.62f,target_point.z-1},near_eye{near_feet.x,target_point.y,near_feet.z};
 const auto near=cue(near_feet,near_eye);
 check(near.find("aim until centre prompt names it")!=std::string::npos&&near.find("E ready")==std::string::npos,"Nearby cue bypasses actual aimed prompt");
 check(cue(near_feet,near_eye,0,0,true,{"Sample supply contact",true})==near,"Wrong aimed station suppresses needed probe navigation");
 check(cue(near_feet,near_eye,0,0,true,{"View blocked; find a clear approach",false})==near,"Occluded aim becomes a ready interaction or suppresses navigation");
 check(cue(near_feet,near_eye,0,0,true,{"Collect diagnostic probe",true}).empty(),"Matching actual ready prompt is duplicated by navigation");
 check(cue(feet,eye,0,0,false).empty(),"Paused controls retain Workshop navigation");
 auto no_workshop=state;std::erase_if(no_workshop.components,[&](const auto& r){return r.type_id==opening_workshop_component_type;});
 check(chapter_aim::workshop_guidance(state,nullptr,feet,eye,0,0,true,{}).empty()&&chapter_aim::workshop_guidance(no_workshop,&content,feet,eye,0,0,true,{}).empty(),"Non-Workshop state acquired Workshop navigation");
 const auto nan=std::numeric_limits<float>::quiet_NaN();
 check(cue(feet,eye,nan).empty()&&cue(feet,{nan,eye.y,eye.z}).empty(),"Invalid camera produces plausible Workshop navigation");
 auto progress=std::find_if(state.components.begin(),state.components.end(),[&](const auto& r){return r.entity_id==b.fixtures[4]&&r.type_id==opening_workshop_component_type;});
 if(progress==state.components.end())throw std::runtime_error("Navigation workshop progress missing");
 const auto sample=opening_workshop_signature(first_boot_content_workshop_circuit(state,content));
 progress->fields["has_probe"]=true;
 const auto supply=cue(feet,eye);progress->fields["supply_sample"]=sample;const auto path=cue(feet,eye);
 check(supply.find("Supply contact")!=std::string::npos&&path.find("Path contact")!=std::string::npos,"Navigation objective failed probe/supply/path transitions");
 progress->fields["path_sample"]=sample;
 check(cue(feet,eye).empty(),"Completed contact guidance persists or selects an invented objective");
 state=initial;for(int n=0;n<1000;++n)(void)cue(feet,eye);
 check(state.components==original&&state.revision==initial.revision&&state.sequence==initial.sequence&&first_boot_content_encode(content)==encoded,"Workshop navigation mutated state, revision or authored content");
}
void workshop_bypass_projection(const FirstBootContent& content,const GameplayStoreRecovery& original){
 auto state=original;state.components.reserve(state.components.size()+2);
 auto fault=std::find_if(state.components.begin(),state.components.end(),[](const auto& r){return r.type_id=="firstboot.PowerFault";});
 if(fault==state.components.end())throw std::runtime_error("Relay projection needs actual fault");
 const Vec3 socket=chapter_aim::point(*fault,"socket_");
 FirstBootChapterActor actor;actor.feet=actor.previous_feet={socket.x,socket.y,socket.z+4};
 auto nodes=state;std::erase_if(nodes.components,[](const auto& r){return r.type_id!="firstboot.Node";});
 const auto placement=durable_first_boot_placement(nodes,{socket.x,socket.y+3,socket.z},{0,-1,0});
 check(placement&&std::hypot(placement->x-socket.x,placement->z-socket.z)<.001&&std::abs(placement->y-(socket.y+1.2f))<.001,"Authoritative socket placement disagrees with relay projection fixture");
 const auto cue=[&](std::optional<Vec3> point=std::nullopt,float yaw=0,bool active=true){return chapter_aim::workshop_bypass_guidance(state,&content,actor,point,yaw,active);};
 const auto before=state.components;const auto encoded=first_boot_content_encode(content);
 const auto names=ids(content);SceneSnapshot solid{content.definition().world_id,0,{}};
 auto reach_actor=actor;reach_actor.feet=reach_actor.previous_feet={socket.x,socket.y,socket.z+1};
 chapter_aim::Pick socket_aim{{SceneHit{names.fault,1}},{SceneHit{names.fault,1}},socket};
 const auto socket_prompt=[&](){return chapter_aim::describe(socket_aim,solid,state,names,&content,reach_actor);};
 check(socket_prompt().text=="Service socket: needs a healthy relay"&&!socket_prompt().ready,"Actual empty socket describe promises connection or arbitrary B placement");
 check(cue(placement).find("Sample the path contact")!=std::string::npos&&cue(placement).find("Press B")==std::string::npos,"Empty hands offered a free build");
 const auto binding=*first_boot_content_workshop_binding(content.definition());
 state.components.push_back(opening_workshop_assembly_record(binding,true,false));
 check(cue(placement).find("1 assembly carried")!=std::string::npos&&cue(placement).find("Press B to install")!=std::string::npos,"Carried part did not admit the socket placement cue");
 check(cue().find("Aim down at the service socket")!=std::string::npos&&cue().find("behind")==std::string::npos,"Live damaged feed advertised a direction into its fault");
 check(cue(Vec3{socket.x+3,placement->y,socket.z}).find("misses service socket")!=std::string::npos,"Outside-socket placement advertised a socket Build");
 fault->fields["isolated"]=true;
 check(cue().find("4 m, behind; aim down")!=std::string::npos,"Isolated socket actual distance/bearing absent");
 constexpr float pi=3.14159265358979323846f;
 check(cue({},pi/2).find(", right; aim down")!=std::string::npos,"Socket bearing ignored actual camera yaw");
 auto far_actor=actor;far_actor.feet.z+=9;
 check(chapter_aim::workshop_bypass_guidance(state,&content,far_actor,placement,0,true).empty(),"Distant socket adds unsolicited relay HUD");
 check(cue(placement,0,false).empty()&&chapter_aim::workshop_bypass_guidance(state,nullptr,actor,placement,0,true).empty(),"Inactive or nonWorkshop view gained relay command");
 auto inspecting=actor;inspecting.inspection_mode=true;
 check(chapter_aim::workshop_bypass_guidance(state,&content,inspecting,placement,0,true).empty(),"Inspection gained relay action cue");
 state.components.pop_back(); // Remaining checks exercise the earlier saved-relay layout.
 auto relay=*std::find_if(state.components.begin(),state.components.end(),[](const auto& r){return r.type_id=="firstboot.Node";});
 relay.entity_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";relay.fields["firstboot.kind"]=6.;relay.fields["alive"]=true;relay.fields["capacity"]=100.;
 relay.fields["x"]=static_cast<double>(placement->x);relay.fields["y"]=static_cast<double>(placement->y);relay.fields["z"]=static_cast<double>(placement->z);
 const auto fault_index=static_cast<std::size_t>(std::distance(state.components.begin(),fault));
 state.components.push_back(relay);
 check(socket_prompt().text=="Service socket: connect built relay","Actual isolated socket with healthy relay omits connection");
 chapter_aim::Pick relay_aim{{SceneHit{relay.entity_id,1}},{SceneHit{relay.entity_id,1}},Vec3{socket.x,socket.y+1,socket.z}};
 check(cue(placement).find("built, not connected")!=std::string::npos&&cue(placement).find("E connects when in reach")!=std::string::npos,"Living built relay incorrectly reported powered or still needs Build");
 auto& current_fault=state.components[fault_index];current_fault.fields["isolated"]=false;
 check(socket_prompt().text=="Service socket: isolate main before connecting"&&chapter_aim::describe(relay_aim,solid,state,names,&content,reach_actor).text=="Relay: isolate main before connecting","Actual socket/selected relay omit isolation prerequisite");
 check(cue(placement).find("Isolate main before connecting")!=std::string::npos,"Connection isolation prerequisite missing");
 current_fault.fields["isolated"]=true;current_fault.fields["bypass_connected"]=true;current_fault.fields["bypass_relay"]=relay.entity_id;
 check(socket_prompt().text=="Service socket: disconnect old feed"&&chapter_aim::describe(relay_aim,solid,state,names,&content,reach_actor).text=="Relay: disconnect old feed","Actual connected socket/relay lost disconnect command");
 check(cue(placement)=="Bypass: Relay feed live.","Actual isolated healthy connected relay not live");
 state.components.back().fields["capacity"]=25.;
 current_fault.fields["bypass_connected"]=false;
 check(socket_prompt().text=="Service socket: needs a healthy relay"&&chapter_aim::describe(relay_aim,solid,state,names,&content,reach_actor).text=="Repair selected relay","Actual damaged relay falsely advertises connecting feed");
 current_fault.fields["bypass_connected"]=true;
 check(cue(placement).find("feed lost")!=std::string::npos&&cue(placement).find("Repair the relay")!=std::string::npos,"Damaged referenced relay falsely live or requires unnecessary rebuild");
 state.components.back().fields["alive"]=false;
 check(cue(placement).find("Disconnect old feed before connecting a replacement")!=std::string::npos,"Lost relay omits existing disconnect requirement");
 state.components.back().fields["alive"]=true;state.components.back().fields["capacity"]=100.;current_fault.fields["isolated"]=false;current_fault.fields["capacity"]=100.;
 check(cue(placement)=="Bypass: Main feed live; relay feed inactive.","Main supply incorrectly reported as live bypass");
 current_fault.fields["bypass_connected"]=false;
 check(cue(placement).empty(),"Working main feed gained unsolicited alternative build guidance");
 auto foreign=original;foreign.scope.world_id=other;
 check(chapter_aim::workshop_bypass_guidance(foreign,&content,actor,placement,0,true).empty(),"Foreign world gained relay guidance");
 state=original;
 for(unsigned i=0;i<1000;++i)(void)cue(placement);
 check(state.components==before&&state.revision==original.revision&&state.sequence==original.sequence&&first_boot_content_encode(content)==encoded,"Relay HUD mutated records/history/content");
}
void actual_content(const char* file){
 std::ifstream input(file,std::ios::binary);check(static_cast<bool>(input),"Current content input missing");const std::vector<unsigned char> bytes{std::istreambuf_iterator<char>(input),{}};
 const auto content=first_boot_content_decode(bytes);const auto content_before=first_boot_content_encode(content);const auto names=ids(content);
 GameplayStoreRecovery state{{"aim-prompt",content.definition().world_id,"test",world,GameplayContext::player_world},0,0,first_boot_content_baseline(content).components};const auto before=state.components;
 auto scene=first_boot_content_scene(state,content);chapter_aim::SolidCache cache;
 // Actual current-v02 reverse-side occluded fault ray from independent RED.
 GroundedCharacter body(scene,{-33,content.definition().jenison_returns[0].y,-.5f});for(int n=0;n<24;++n)body.advance({},1./60);
 const auto feet=body.state().feet;const Vec3 eye{feet.x,feet.y+1.62f,feet.z};const auto fault=chapter_aim::point(*chapter_aim::record(state,names.fault));
 auto pick=cache.pick(scene,eye,{fault.x-eye.x,fault.y+1-eye.y,fault.z-eye.z});
 check(pick.selected&&pick.selected->persistent_id==names.fault&&pick.solid&&pick.solid->distance<pick.selected->distance,"Concrete current fault occluder fixture changed");
#ifdef AIBS_AIM_LEGACY_RED
 check(!pick.selected.has_value(),"RED: old core E selectable-only ray reaches the fault through actual rear chassis");
#endif
 check(!pick.visible(),"Current actual chassis occlusion not blocked");
 FirstBootChapterActor actor;actor.feet=actor.previous_feet=feet;actor.grounded=body.state().grounded;
 check(chapter_aim::describe(pick,cache.sync(scene),state,names,&content,actor).text.find("blocked")!=std::string::npos,"Occluded target leaked ready prompt");
 OpeningInspectionCatalog catalog(content.definition());
 const auto workshop_binding=*first_boot_content_workshop_binding(content.definition());
 for(std::size_t slot=0;slot<workshop_binding.fixtures.size();++slot){
  const auto& id=workshop_binding.fixtures[slot];const auto source=std::find_if(content.definition().fixtures.begin(),content.definition().fixtures.end(),[&](const auto& f){return f.object.persistent_id==id;});
  check(source!=content.definition().fixtures.end(),"Actual Workshop fixture missing");const auto target_point=source->object.center;bool observed=false;
  for(const auto offset:{Vec3{1.2f,0,0},Vec3{-1.2f,0,0},Vec3{0,0,1.2f},Vec3{0,0,-1.2f},Vec3{2.5f,0,0},Vec3{-2.5f,0,0},Vec3{0,0,2.5f},Vec3{0,0,-2.5f}}){
   try{
    GroundedCharacter approach(scene,{target_point.x+offset.x,content.definition().jenison_returns[0].y,target_point.z+offset.z});for(unsigned tick=0;tick<24;++tick)approach.advance({},1./60);
    if(!approach.state().grounded)continue;const auto standing=approach.state().feet;const Vec3 camera{standing.x,standing.y+1.62f,standing.z};
    const auto aimed=cache.pick(scene,camera,{target_point.x-camera.x,target_point.y-camera.y,target_point.z-camera.z});if(!aimed.visible()||aimed.selected->persistent_id!=id)continue;
    FirstBootChapterActor evidence;evidence.feet=evidence.previous_feet=standing;evidence.grounded=true;
    const auto prompt=chapter_aim::describe(aimed,cache.sync(scene),state,names,&content,evidence);
    if(prompt.text.find("move closer")!=std::string::npos)continue;
    check(prompt.ready==(slot==0),"Actual initial station readiness differs from authoritative probe dependency");
    check(!prompt.text.empty()&&prompt.text.size()<=61,"Actual station prompt missing/unbounded");observed=true;break;
   }catch(const std::invalid_argument&){}
  }
  check(observed,"Actual station has no grounded camera/body-visible prompt approach");
 }
 for(const auto& read:catalog.entries()){
  chapter_aim::Pick aimed{{SceneHit{read.fixture_id,1}},{SceneHit{read.fixture_id,1}},read.center};actor.feet=read.center;
  const auto prompt=chapter_aim::describe(aimed,cache.sync(scene),state,names,&content,actor,&read);
  check(prompt.ready&&prompt.text.size()<=61,"Inspection cue missing or unbounded");actor.feet.x+=10;
  check(!chapter_aim::describe(aimed,cache.sync(scene),state,names,&content,actor,&read).ready,"Out-of-reach reading advertised ready");
 }
 const auto* f=chapter_aim::record(state,names.fault);const auto socket=chapter_aim::point(*f,"socket_");
 for(const auto& item:std::array<std::pair<Vec3,std::string_view>,3>{{{socket,"Service socket"},{content.definition().isolation_switch,"Isolation switch"},{fault,"power fault"}}}){
  chapter_aim::Pick aimed{{SceneHit{names.fault,1}},{SceneHit{names.fault,1}},item.first};
  check(chapter_aim::describe(aimed,cache.sync(scene),state,names,&content,actor).text.find(item.second)!=std::string::npos,"Shared UUID subtarget name incorrect");
 }
 for(const auto& id:{names.main_door,names.service_door,names.pencil_door}){chapter_aim::Pick aimed{{SceneHit{id,1}},{SceneHit{id,1}},{}};check(chapter_aim::describe(aimed,cache.sync(scene),state,names,&content,actor).text.find("door")!=std::string::npos,"Door focus name absent");}
 auto offline_latch=state;auto door=std::find_if(offline_latch.components.begin(),offline_latch.components.end(),[&](const auto& r){return r.entity_id==names.main_door;});door->fields["unlocked"]=true;
 chapter_aim::Pick door_aim{{SceneHit{names.main_door,1}},{SceneHit{names.main_door,1}},{}};
 check(chapter_aim::describe(door_aim,cache.sync(scene),offline_latch,names,&content,actor).text=="Main door: open","Earned offline latch incorrectly advertises a supply requirement");
 door_aim.selected->persistent_id=door_aim.solid->persistent_id=names.pencil_door;
 check(chapter_aim::describe(door_aim,cache.sync(scene),state,names,&content,actor).text=="Pencil Room door: open","Pencil door incorrectly advertises a supply requirement");
 auto isolated=state;auto fault_record=std::find_if(isolated.components.begin(),isolated.components.end(),[&](const auto& r){return r.entity_id==names.fault;});fault_record->fields["isolated"]=true;
 chapter_aim::Pick switch_aim{{SceneHit{names.fault,1}},{SceneHit{names.fault,1}},content.definition().isolation_switch};
 check(chapter_aim::describe(switch_aim,cache.sync(scene),isolated,names,&content,actor).text.find("DAMAGED live feed")!=std::string::npos,"Damaged feed reconnection lacks warning");
 fault_record->fields["capacity"]=100.;check(chapter_aim::describe(switch_aim,cache.sync(scene),isolated,names,&content,actor).text.find("repaired main")!=std::string::npos,"Repaired feed reconnection incorrectly warns of damage");
 const auto* npc=chapter_aim::record(state,names.npc_quest);chapter_aim::Pick lamp_aim{{SceneHit{names.npc_quest,1}},{SceneHit{names.npc_quest,1}},chapter_aim::point(*npc,"lamp_")};
 check(chapter_aim::describe(lamp_aim,cache.sync(scene),state,names,&content,actor).text.find("power required")!=std::string::npos,"Lamp cue promises unavailable power");
 for(int n=0;n<1000;++n){
  (void)chapter_aim::describe(pick,cache.sync(scene),state,names,&content,actor);
  (void)chapter_aim::isolation_guidance(actor.feet,0,content.definition().isolation_switch,chapter_aim::number(*f,"capacity"),chapter_aim::flag(*f,"isolated"),true);
 }
 check(state.components==before&&state.revision==0&&state.sequence==0&&first_boot_content_encode(content)==content_before,"HUD projection changed history or content");
 workshop_navigation(content,state);
 workshop_bypass_projection(content,state);
 auto foreign_state=state;foreign_state.scope.world_id=other;
 chapter_aim::Pick contact_aim{{SceneHit{workshop_binding.fixtures[1],1}},{SceneHit{workshop_binding.fixtures[1],1}},{}};
 const auto foreign_prompt=chapter_aim::describe(contact_aim,cache.sync(scene),foreign_state,names,&content,actor);
 check(!foreign_prompt.ready&&foreign_prompt.text=="Workshop station unavailable","Wrong world scope leaked a contact observation");
}
}
int main(int argc,char** argv){try{geometry();isolation_navigation();workshop();workshop_saved_readings();if(argc==2)actual_content(argv[1]);std::cout<<"PASS "<<checks<<" aim prompt CPU checks\n";return 0;}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
