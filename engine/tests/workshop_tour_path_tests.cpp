#include <aibs/warm_opening.hpp>
#include <aibs/gameplay_store.hpp>
#include <aibs/player.hpp>
#include <aibs/gameplay_codec.hpp>
#include "workshop_tour_path.hpp"
#include <fstream>
#include <iostream>
using namespace aibs;
namespace {
unsigned checks=0;
void check(bool v,const char* why){++checks;if(!v)throw std::runtime_error(why);}
void reproduce(const SceneSnapshot& scene){
 // Exact actual feet/anchor retained by the failed wall-clock bypass-note
 // return. A reverse of the ideal outward line clips a real fixture here.
 const Vec3 from{-43.118042f,0,-6.681632f},anchor{-36.9599f,.0699999f,-9.97161f};
 const auto original=scene.objects;
 check(!workshop_tour_path::clear(scene,from,{anchor},-.2f),"Recorded blocked direct return unexpectedly passed");
 const auto plan=workshop_tour_path::return_plan(scene,from,anchor,-.2f);
 check(!plan.empty()&&plan.size()<=3,"No bounded physical return from recorded feet");
 Vec3 standing;check(workshop_tour_path::clear(scene,from,plan,-.2f,&standing),"Planned return is not walkable");
 check(std::hypot(standing.x-anchor.x,standing.z-anchor.z)<.14f,"Query did not reach the actual corridor anchor");
 check(!workshop_tour_path::clear(scene,from,{},-.2f),"Empty path accepted");
 check(!workshop_tour_path::clear(scene,from,{anchor,anchor,anchor,anchor},-.2f),"Unbounded waypoint list accepted");
 check(!workshop_tour_path::clear(scene,from,{{1000,0,1000}},-.2f),"Remote planning segment accepted");
 auto walled=scene;walled.objects.push_back({new_uuid(),"Closed test partition",{-40,2,-8},{.3f,2,30},{.4f,.4f,.4f},0,false});
 check(workshop_tour_path::return_plan(walled,from,anchor,-.2f).empty(),"Closed wall bypassed or invented arrival");
 check(scene.objects.size()==original.size(),"Read-only planning mutated scene ownership");
}
void walk_player(const SceneSnapshot& scene,Vec3 from,const std::vector<Vec3>& plan){
 PlayerController player(scene,from);for(unsigned i=0;i<12;++i)player.update({},1./60);
 for(const auto target:plan){bool reached=false;
  for(unsigned i=0;i<600;++i){const auto p=player.state().feet;if(std::hypot(p.x-target.x,p.z-target.z)<.14f){reached=true;break;}
   const auto c=player.camera();WindowInput look;look.yaw_delta=std::atan2(target.x-c.position.x,target.z-c.position.z)-c.yaw;look.pitch_delta=-c.pitch;player.update(look,0);WindowInput input;input.forward=1;player.update(input,1./60);
   check(player.state().feet.y>=-.2f,"Actual return walk lost supported floor");
  }
  check(reached&&player.state().grounded,"Actual yaw/W return walk failed grounded arrival");
 }
}
void shelter_return(const SceneSnapshot& scene){
 const auto original=scene.objects;const Vec3 f{-42.3987f,.03f,9.92842f},a{-36.991734f,.03f,8.034330f};
 check(!workshop_tour_path::clear(scene,f,{a},-.2f),"Recorded shelter direct return must reject a grazing corridor");
 for(const Vec3 offset:std::initializer_list<Vec3>{{0,0,0},{.05f,0,0},{-.05f,0,0},{0,0,.05f},{0,0,-.05f}}){
  const Vec3 from{f.x+offset.x,f.y,f.z+offset.z},anchor{a.x-offset.x,a.y,a.z-offset.z};
  const auto plan=workshop_tour_path::return_plan(scene,from,anchor,-.2f);
  check(!plan.empty()&&plan.size()<=3,"No bounded clearance return under endpoint perturbation");
  check(workshop_tour_path::clear(scene,from,plan,-.2f),"Chosen shelter detour fails actual physics query");walk_player(scene,from,plan);
 }
 check(scene.objects.size()==original.size(),"Return planner altered scene size");
 for(std::size_t i=0;i<original.size();++i){const auto& x=scene.objects[i];const auto& y=original[i];check(x.persistent_id==y.persistent_id&&x.name==y.name&&x.center==y.center&&x.half_extent==y.half_extent&&x.color==y.color&&x.emission==y.emission&&x.selectable==y.selectable&&x.rotation.x==y.rotation.x&&x.rotation.y==y.rotation.y&&x.rotation.z==y.rotation.z&&x.rotation.w==y.rotation.w,"Return planner altered an original collider");}
}
auto walk_live(PlayerController& player,Vec3 target,double dt){
 for(unsigned n=0;n<600;++n){const auto feet=player.state().feet;if(std::hypot(feet.x-target.x,feet.z-target.z)<.28f)break;
  const auto camera=player.camera();WindowInput look;look.yaw_delta=std::atan2(target.x-camera.position.x,target.z-camera.position.z)-camera.yaw;look.pitch_delta=-camera.pitch;player.update(look,0);WindowInput input;input.forward=1;player.update(input,dt);
 }
 player.update({},dt);return player.state();
}
void diagnostic_reversible(const SceneSnapshot& scene){
 const Vec3 anchor{-37.1815f,.0699999f,-9.92792f},old_target{-35.6f,.2f,-7.8f};
 check(workshop_tour_path::clear(scene,anchor,{old_target},-.2f),"Recorded diagnostic outward cold query no longer reproduces");
 PlayerController bad(scene,anchor);for(unsigned n=0;n<12;++n)bad.update({},1./60);const auto failed=walk_live(bad,old_target,4./60);
 check(failed.grounded&&std::hypot(failed.feet.x-old_target.x,failed.feet.z-old_target.z)<.35f,"Real-time normal controller failed to reproduce accepted outward arrival");
 check(workshop_tour_path::return_plan(scene,failed.feet,anchor,-.2f).empty(),"Recorded diagnostic grounded landing no longer reproduces blocked return");
 check(!workshop_tour_path::reversible(scene,anchor,{old_target},anchor,-.2f),"Diagnostic approach admitted cold forward success with unsafe live return envelope");
 const Vec3 alternative{-36.9f,.2f,-7.8f};Vec3 standing;std::vector<Vec3> returning;
 check(workshop_tour_path::reversible(scene,anchor,{alternative},anchor,-.2f,&standing,&returning)&&!returning.empty(),"Existing farther-west diagnostic candidate is not physically reversible");
 for(const double dt:{1./60,1./30,1./20,4./60}){
  PlayerController good(scene,anchor);for(unsigned n=0;n<12;++n)good.update({},1./60);(void)walk_live(good,alternative,dt);
  for(unsigned n=0;n<60&&!good.state().grounded&&good.state().feet.y>=-.2f;++n)good.update({},1./60);
  const auto actual=good.state();check(actual.grounded&&actual.feet.y>=-.2f&&std::hypot(actual.feet.x-alternative.x,actual.feet.z-alternative.z)<.35f,"Viable diagnostic alternative failed bounded actual live arrival");
  const auto plan=workshop_tour_path::return_plan(scene,actual.feet,anchor,-.2f);check(!plan.empty()&&plan.size()<=3,"Actual accepted alternative has no finite return");walk_player(scene,actual.feet,plan);
 }
 auto walled=scene;walled.objects.push_back({new_uuid(),"True diagnostic partition",{-37,2,-8.8f},{30,2,.3f},{.4f,.4f,.4f},0,false});
 check(!workshop_tour_path::reversible(walled,anchor,{alternative},anchor,-.2f),"Genuinely impassable diagnostic partition accepted");
}
void diagnostic_settle(const SceneSnapshot& scene){
 // Exact actual trace record-0a04749fe7 final diagnostic leg. Replay consumed
 // physics ticks through the real controller, not synthetic standing state.
 PlayerController player(scene,{-37.160919189453125f,4.22200230332237e-09f,-6.64404821395874f});for(unsigned n=0;n<12;++n)player.update({},1./60);
 struct Step{unsigned ticks;float forward;double yaw;};
 const Step steps[]={{1,1,1.5548436641693115},{3,1,1.5548436641693115},{2,1,1.5548436641693115},{1,1,1.5548436641693115},{3,1,1.5548436641693115},{2,1,1.5548436641693115},{2,1,1.5548436641693115},{2,1,1.5548436641693115},{2,1,1.554843783378601},{2,1,1.5559349060058594},{2,1,1.5559349060058594},{2,0,1.5559349060058594}};
 for(const auto& step:steps){const auto camera=player.camera();WindowInput look;look.yaw_delta=static_cast<float>(step.yaw)-camera.yaw;look.pitch_delta=-camera.pitch;player.update(look,0);WindowInput input;input.forward=step.forward;player.update(input,step.ticks/60.);}
 const auto released=player.state();const Vec3 target{-34.4f,.2f,-6.6f};
 check(!released.grounded&&released.velocity.y<0&&released.feet.y>=-.2f&&std::hypot(released.feet.x-target.x,released.feet.z-target.z)<.35f,"Actual short-step release did not reproduce transient ungrounded landing");
 unsigned settles=0;while(!player.state().grounded&&player.state().feet.y>=-.2f&&settles<60){player.update({},1./60);++settles;}
 const auto settled=player.state();check(settles>0&&settles<=60&&settled.grounded&&settled.feet.y>=-.2f&&std::hypot(settled.feet.x-target.x,settled.feet.z-target.z)<.35f,"Supported short-step landing did not settle in bounded zero-input time");
 PlayerController fallen(scene,{-37,.2f,-34});for(unsigned n=0;n<24;++n)fallen.update({},1./60);check(fallen.state().grounded,"Actual board-edge negative did not start supported");
 WindowInput look;look.yaw_delta=3.14159265358979323846f-fallen.camera().yaw;look.pitch_delta=-fallen.camera().pitch;fallen.update(look,0);
 for(unsigned n=0;n<240&&fallen.state().feet.y>=-.2f;++n){WindowInput input;input.forward=1;fallen.update(input,1./60);}
 check(!fallen.state().grounded&&fallen.state().feet.y<-.2f,"Actual board-edge walk failed to lose floor support");
 for(unsigned n=0;n<60;++n)fallen.update({},1./60);
 check(!fallen.state().grounded&&fallen.state().feet.y<-.2f,"Zero-input settle fabricated support after a genuine fall");
}
std::vector<ComponentSchema> admitted_registry(const std::filesystem::path& db,const GameplayScope& scope,const FirstBootContent& content){
 const auto actual=GameplayStore::inspect_registry(db,scope);const auto bytes=gameplay_codec::encode_schemas(actual);
 check(bytes==gameplay_codec::encode_schemas(first_boot_content_schemas(content))||bytes==gameplay_codec::encode_schemas(first_boot_content_relay_assembly_schemas(content)),"Actual fixture registry is neither exact legacy nor explicit finite-assembly registry");return actual;
}
void clearance_geometry(){
 auto box=[](const char* name,Vec3 p,Vec3 h){return SceneObject{new_uuid(),name,p,h,{.4f,.5f,.6f},0,false};};
 SceneSnapshot scene{new_uuid(),0,{box("floor",{0,-.5f,0},{20,.5f,20})}};
 scene.objects.push_back(box("nonselectable table",{0,.6f,0},{1,.6f,.6f}));
 check(!workshop_tour_path::clear(scene,{-3,.03f,1.02f},{{3,.25f,1.02f}},-.2f),"Extra corridor clearance was not enforced on a nonselectable collider");
 check(workshop_tour_path::clear(scene,{-3,.03f,2},{{3,.25f,2}},-.2f),"Clear supported corridor incorrectly rejected");
 scene.objects.pop_back();scene.objects.push_back(box("raised floor",{0,.015f,0},{8,.015f,8}));scene.objects.push_back(box("low trace",{0,.06f,0},{4,.04f,.06f}));
 check(workshop_tour_path::clear(scene,{-3,.03f,-1},{{3,.25f,1}},-.2f),"Raised floor and low trace rejected instead of physical stepping");
 scene.objects.resize(1);auto rail=box("yaw rail",{0,1,0},{3,1,.1f});rail.rotation={0,.3826834324f,0,.9238795325f};scene.objects.push_back(rail);
 check(workshop_tour_path::clear(scene,{-2,.03f,3},{{3,.25f,-2}},-.2f),"OBB-local clearance rejected a clear parallel rotated corridor");
 check(!workshop_tour_path::clear(scene,{-3,.03f,-3},{{3,.25f,3}},-.2f),"Rotated obstacle crossing accepted");
 scene.objects.back().rotation={0,0,.2588190451f,.9659258263f};scene.objects.back().half_extent={.2f,1.5f,.2f};
 check(!workshop_tour_path::clear(scene,{-3,.03f,0},{{3,.25f,0}},-.2f),"Tilted obstacle crossing accepted");
 check(workshop_tour_path::clear(scene,{-3,.03f,3},{{-3,500,3}},-.2f),"Zero horizontal leg incorrectly treated authored Y as flight");
 // Isolate the capsule-envelope math from the nominal Jolt walking query.
 // At x=.5 the tilted box is outside a mere radius-expanded ray in local X,
 // but intersects the upright capsule's projected vertical segment.
 scene.objects.resize(1);auto tilted=box("off-center tilted envelope",{0,.4f,0},{.1f,.5f,.1f});
 tilted.rotation={0,0,.2588190451f,.9659258263f};scene.objects.push_back(tilted);
 check(!workshop_tour_path::corridor_clear(scene,{.5f,.03f,-2},{.5f,.03f,2}),"Tilted capsule projection missed an off-center collision");
 check(workshop_tour_path::corridor_clear(scene,{.9f,.03f,-2},{.9f,.03f,2}),"Tilted capsule projection rejected the clear parallel corridor");
 // Marker lower edge1.4m lies above a .45m chest sphere centered at .93m,
 // while the full capsule reaches1.83m and must still reject this crossing.
 scene.objects.resize(1);scene.objects.push_back(box("high capsule marker",{0,1.65f,0},{.25f,.25f,.2f}));
 check(!workshop_tour_path::corridor_clear(scene,{.5f,.03f,-2},{.5f,.03f,2}),"Full capsule envelope missed a high marker");

}

}
int main(int argc,char** argv){try{
 CreatorSession source(first_boot_schema(),"tour-path-tests","fresh");check(seed_first_boot(source).ok,"Seed test hardware");
 const auto content=FirstBootContent::create(make_warm_workshop_draft(source,{}).definition);const auto baseline=first_boot_content_baseline(content);
 GameplayStoreRecovery state{{"tour-path-tests",content.definition().world_id,"fresh",new_uuid(),GameplayContext::temporary_play},baseline.revision,baseline.sequence,baseline.components};
 reproduce(first_boot_content_scene(state,content));
 diagnostic_reversible(first_boot_content_scene(state,content));
 diagnostic_settle(first_boot_content_scene(state,content));
 clearance_geometry();
 shelter_return(first_boot_content_scene(state,content));
 if(argc==3||argc==4){
  check(std::filesystem::file_size(argv[1])<=1024u*1024u,"Content input exceeds bound");std::ifstream file(argv[1],std::ios::binary);check(file.good(),"Content input missing");std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(file)),{});check(!bytes.empty(),"Empty content input");
  const auto actual=first_boot_content_decode(bytes);const auto scopes=GameplayStore::list_scopes(argv[2],2);check(scopes.size()==1,"Expected one actual failed timeline");
  const auto recovered=GameplayStore::inspect_recovery(argv[2],scopes.front(),admitted_registry(argv[2],scopes.front(),actual));const auto head=recovered.revision;
  shelter_return(first_boot_content_scene(recovered,actual));
  reproduce(first_boot_content_scene(recovered,actual));
  diagnostic_reversible(first_boot_content_scene(recovered,actual));
  diagnostic_settle(first_boot_content_scene(recovered,actual));
  const auto again=GameplayStore::inspect_recovery(argv[2],scopes.front(),admitted_registry(argv[2],scopes.front(),actual));check(again.revision==recovered.revision&&again.sequence==recovered.sequence&&again.components==recovered.components,"Read-only planning changed recovered history");check(recovered.revision==head,"Planning changed recovered head");
  if(argc==4){
   const auto open_scopes=GameplayStore::list_scopes(argv[3],2);check(open_scopes.size()==1,"Expected one actual post-door timeline");
   const auto postdoor=GameplayStore::inspect_recovery(argv[3],open_scopes.front(),admitted_registry(argv[3],open_scopes.front(),actual));const auto scene=first_boot_content_scene(postdoor,actual);
   const Vec3 from{-33.0022f,.0299999f,5.81255f},target{-33,.25f,8};
   check(workshop_tour_path::clear(scene,from,{target},-.2f),"Actual post-door shelter corridor physically blocked");
   PlayerController player(scene,from);for(unsigned n=0;n<24;++n)player.update({},1./60);bool arrived=false;
   for(unsigned n=0;n<600;++n){const auto feet=player.state().feet;if(std::hypot(feet.x-target.x,feet.z-target.z)<.28f){arrived=true;break;}
    const auto camera=player.camera();WindowInput look;look.yaw_delta=std::atan2(target.x-camera.position.x,target.z-camera.position.z)-camera.yaw;look.pitch_delta=-camera.pitch;player.update(look,0);WindowInput input;input.forward=1;player.update(input,1./60);
   }
   check(arrived&&player.state().grounded,"Actual player controller cannot walk the post-door corridor with active W input");
  }
 }else check(argc==1,"Expected zero args or exact content/database paths");
 std::cout<<checks<<" collision-return checks passed; no GPU or runtime actor changes\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
