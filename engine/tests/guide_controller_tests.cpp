#include <aibs/guide_controller.hpp>
#include <aibs/engine.hpp>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {
void require(bool b,const char* message){if(!b)throw std::runtime_error(message);}
template<class F> void rejects(F f,const char* message){bool failed=false;try{f();}catch(const std::invalid_argument&){failed=true;}require(failed,message);}
float distance(Vec3 a,Vec3 b){return std::hypot(a.x-b.x,a.z-b.z);}
SceneObject box(Vec3 p,Vec3 half){return {new_uuid(),"Guide fixture",p,half,{.4f,.5f,.6f}};}
SceneSnapshot floor(){return {new_uuid(),4,{box({0,-.5f,0},{20,.5f,20})}};}
GuideRouteGraph main_route(){return {{{"west",{-6,.05f,0}},{"east",{6,.05f,0}}},{{"west","east","main"}}};}
GuideState run(GuideController& guide,GuideTarget player,int count){for(int i=0;i<count;++i)(void)guide.advance(player,1.0/60);return guide.state();}
void main_contracts(){
 auto scene=floor();const auto original=scene.objects.size();
 GuideController guide(scene,{-6,.05f,0},main_route());
 const GuideTarget player{{6,.05f,0},true,scene.revision};
 guide.set_doors({{"main",false}});auto blocked=run(guide,player,90);
 require(blocked.activity==GuideActivity::blocked && blocked.character.feet.x<-5.8f,"closed authored door waits without teleporting");
 guide.set_doors({{"main",true}});auto followed=run(guide,player,240);
 require(followed.character.feet.x>3.5f && followed.character.feet.x<5.2f,"open authored route follows and leaves personal space");
 require(scene.objects.size()==original,"Adam adds no colliders to BS scene");
 guide.set_intent(GuideIntent::wait);const auto saved=guide.saved_intent();const auto waited=run(guide,{{-10,.05f,0},true,4},90);
 require(waited.activity==GuideActivity::waiting && distance(waited.character.feet,saved.waiting_anchor)<.03f,"Wait retains supported anchor");
 GuideController restarted(scene,{-10,.05f,0},main_route());restarted.restore_intent(saved);
 require(restarted.state().intent==GuideIntent::wait && distance(restarted.state().character.feet,saved.waiting_anchor)<.03f,"restart reconstructs Wait anchor");
 guide.set_intent(GuideIntent::follow);const auto before=guide.state().character.feet;
 require(!guide.recall(player.feet,{{6,.05f,0},{6,10,2},{16,.05f,0}}),"Recall rejects player overlap, unsupported and distant positions");
 require(distance(guide.state().character.feet,before)<.001f,"failed Recall preserves current pose");
 require(!guide.recall({6,0,0},{{6.889f,.15f,0}}),"Recall checks personal space after ground settling, not only the requested point");
 require(guide.recall(player.feet,{{6,.05f,2}}),"Recall accepts supported nearby free position");
 require(distance(guide.state().character.feet,{6,0,2})<.03f,"Recall uses validated candidate");
 guide.set_intent(GuideIntent::wait);require(guide.recall(player.feet,{{6,.05f,-2}}),"Recall can reposition an explicitly waiting guide");
 require(guide.saved_intent().intent==GuideIntent::wait&&distance(guide.saved_intent().waiting_anchor,{6,0,-2})<.03f,"Recall preserves Wait and updates valid anchor");
 guide.set_intent(GuideIntent::follow);require(guide.recall(player.feet,{{6,.05f,2}}),"Follow Recall remains explicit");
 auto bad=saved;bad.waiting_anchor={0,30,0};rejects([&]{guide.restore_intent(bad);},"unsupported saved anchor rejects");
 require(distance(guide.state().character.feet,{6,0,2})<.03f,"bad saved state preserves pose");
 guide.suspend();auto resumed=guide.advance(player,0);require(distance(resumed.character.feet,{6,0,2})<.03f,"pause consumes no catch-up");
 rejects([&]{(void)guide.advance(player,std::numeric_limits<double>::quiet_NaN());},"invalid elapsed rejects");
 rejects([&]{guide.set_intent(static_cast<GuideIntent>(99));},"unknown intent rejects");
}
void geometry_and_bypass(){
 auto scene=floor();scene.objects.push_back(box({0,1,0},{.3f,1,2}));
 GuideController guide(scene,{-6,.05f,0},main_route());guide.set_doors({{"main",true}});
 auto blocked=run(guide,{{6,.05f,0},true,4},240);
 require(blocked.character.feet.x<-.55f,"physical closed door prevents stale open metadata crossing");
 require(blocked.activity==GuideActivity::blocked,"physical blockage reports waiting for route");
 auto graph=main_route();graph.nodes.push_back({"southwest",{-6,.05f,4}});graph.nodes.push_back({"southeast",{6,.05f,4}});
 graph.edges.push_back({"west","southwest",""});graph.edges.push_back({"southwest","southeast","bypass"});graph.edges.push_back({"southeast","east",""});
 GuideController bypass(scene,{-6,.05f,0},graph);bypass.set_doors({{"main",false},{"bypass",true}});
 auto arrived=run(bypass,{{6,.05f,0},true,4},500);
 require(arrived.character.feet.x>3.5f && std::abs(arrived.character.feet.z)<2.1f,"alternate gated path navigates around closed main door");
 const auto before=bypass.state().character.feet;require(!bypass.recall({0,.05f,0},{{0,.05f,1}}),"Recall rejects embedded wall candidate");
 require(distance(before,bypass.state().character.feet)<.001f,"embedded Recall rollback");
 auto invalid=graph;invalid.edges.push_back({"missing","east",""});rejects([&]{GuideController bad(scene,{-6,.05f,0},invalid);},"unknown graph endpoint rejects");
 GuideController missing(scene,{-6,.05f,0},main_route());require(run(missing,{{6,.05f,0},true,4},30).activity==GuideActivity::blocked,"missing gate is closed");
 auto malformed=graph;malformed.nodes.push_back(malformed.nodes.front());rejects([&]{GuideController bad(scene,{-6,.05f,0},malformed);},"duplicate graph IDs reject");
 auto settings=GuideSettings{};settings.walk_speed=std::numeric_limits<float>::infinity();rejects([&]{GuideController bad(scene,{-6,.05f,0},graph,settings);},"nonfinite settings reject");
}
void trail_and_scene(){
 auto scene=floor();GuideController guide(scene,{-6,.05f,0},{});
 for(int i=0;i<300;++i){const float x=std::min(6.0f,-6.0f+i*.06f);(void)guide.advance({{x,.05f,0},true,4},1.0/60);}
 auto followed=guide.state();require(followed.character.feet.x>3,"validated grounded BS trail supplements graph");
 require(followed.trail_points>10,"runtime trail recorded");
 auto revised=scene;revised.revision=5;guide.set_scene(revised);
 require(guide.state().trail_points==followed.trail_points,"semantic-only revision preserves still-walkable trail");
 auto geometry_changed=revised;geometry_changed.revision=6;geometry_changed.objects.push_back(box({15,1,15},{.5f,1,.5f}));guide.set_scene(geometry_changed);
 require(guide.state().trail_points==0,"actual changed collision invalidates old walkable trail");
 const auto start=guide.state().character.feet;auto stale=run(guide,{{-6,.05f,0},true,4},90);
 require(stale.activity==GuideActivity::blocked && distance(start,stale.character.feet)<.03f,"stale player samples cannot navigate revised geometry");
 GuideController discontinuity(scene,{-6,.05f,0},{});(void)discontinuity.advance({{-6,.05f,0},true,4},1.0/60);
 auto jumped=run(discontinuity,{{6,.05f,0},true,4},120);require(jumped.character.feet.x<-5.8f,"teleported player sample never creates straight walkable shortcut");
 auto changed=scene;changed.revision=6;changed.objects.push_back(box({-6,1,0},{1,1,1}));
 rejects([&]{discontinuity.set_scene(changed);},"scene replacement overlapping Adam rejects");
 require(discontinuity.scene_revision()==4,"failed scene replacement preserves revision");
 auto oversized=discontinuity.advance({{6,.05f,0},true,4},10);
 require(oversized.dropped_seconds>9.9,"bounded fixed stepping reports dropped time");
 require(discontinuity.recall(changed,{0,.05f,0},{{0,.05f,2}}),"explicit Recall can adopt latest scene after old guide pose became embedded");
 require(discontinuity.scene_revision()==6&&distance(discontinuity.state().character.feet,{0,0,2})<.03f,"latest-scene Recall publishes validated geometry and pose together");
}
void deterministic_steps_and_cliffs(){
 auto scene=floor();GuideController a(scene,{-6,.05f,0},main_route()),b(scene,{-6,.05f,0},main_route());a.set_doors({{"main",true}});b.set_doors({{"main",true}});
 const GuideTarget player{{6,.05f,0},true,4};
 for(int i=0;i<80;++i){(void)a.advance(player,1.0/60);(void)b.advance(player,1.0/120);(void)b.advance(player,1.0/120);}
 require(distance(a.state().character.feet,b.state().character.feet)<.001f,"fixed companion ticks match across render cadence");
 auto gap=scene;gap.objects.clear();gap.objects.push_back(box({-5,-.5f,0},{3,.5f,4}));gap.objects.push_back(box({5,-.5f,0},{3,.5f,4}));
 GuideController cliff(gap,{-6,.05f,0},main_route());cliff.set_doors({{"main",true}});const auto held=run(cliff,player,300);
 require(held.activity==GuideActivity::blocked&&held.character.grounded&&held.character.feet.x<-2,"stale graph cannot walk off unsupported bridge gap");
}
}
int main(){try{main_contracts();geometry_and_bypass();trail_and_scene();deterministic_steps_and_cliffs();std::cout<<"PASS guide Follow/Wait/Recall, doors, bypass, revision trails, cliff support, render cadence and restart intent\n";return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
