#include <aibs/companion_runtime.hpp>
#include <aibs/warm_opening.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {
unsigned checks=0;
void need(bool ok,const char*why){++checks;if(!ok)throw std::runtime_error(why);}
template<class F>void rejects(F f,const char*why){bool rejected=false;try{f();}catch(const std::invalid_argument&){rejected=true;}need(rejected,why);}
float distance(Vec3 a,Vec3 b){return std::hypot(a.x-b.x,a.z-b.z);}
SceneObject box(Vec3 p,Vec3 h){return {new_uuid(),"Semantic scene fixture",p,h,{.4f,.5f,.6f}};}
void offgraph_revision(){
 SceneSnapshot s{new_uuid(),0,{box({0,-.5f,0},{20,.5f,20})}};GuideSettings settings;settings.walk_speed=7;settings.catchup_speed=13;
 GuideController guide(s,{0,.05f,0},{},settings);
 for(unsigned n=0;n<240;++n)(void)guide.advance({{std::min(8.f,static_cast<float>(n)*.05f),0,0},true,0},1./60);
 const auto before=guide.state();need(before.trail_points>10&&before.character.grounded,"Real offgraph walk records supported trail");
 auto revised=s;revised.revision=1;revised.objects[0].color={.7f,.3f,.2f};revised.objects[0].emission=.2f;revised.objects[0].name="Visual metadata only";revised.objects[0].selectable=false;
 guide.set_scene(revised);const auto adopted=guide.state();
 need(adopted.trail_points==before.trail_points,"Semantic-only revision must preserve actual walkable trail");
 need(adopted.character.feet==before.character.feet&&adopted.character.velocity==before.character.velocity&&adopted.character.ticks==before.character.ticks&&adopted.destination==before.destination&&adopted.activity==before.activity,"Semantic rebind preserves exact moving physics and route state");
 need(guide.scene_revision()==1,"Semantic rebind adopts authoritative new revision");
 for(unsigned n=0;n<240;++n)(void)guide.advance({{std::min(12.f,8.f+static_cast<float>(n)*.05f),0,0},true,1},1./60);
 need(guide.state().character.feet.x>10&&guide.state().activity==GuideActivity::near_player,"Offgraph Follow resumes after semantic station revision without Recall");
 const auto valid=guide.state();auto bad=revised;bad.revision=2;bad.objects[0].emission=std::numeric_limits<float>::quiet_NaN();
 rejects([&]{guide.set_scene(bad);},"Identical collision must still reject malformed visual scene");
 need(guide.scene_revision()==1&&guide.state().character.feet==valid.character.feet&&guide.state().trail_points==valid.trail_points,"Invalid scene validation preserves body/trail/revision");
 const auto feet=guide.state().character.feet;(void)guide.advance({{0,0,0},true,0},1./60);
 need(guide.state().activity==GuideActivity::blocked&&distance(feet,guide.state().character.feet)<.03f,"Old revision actor remains rejected despite preserved trail");
 auto geometry=revised;geometry.revision=2;geometry.objects.push_back(box({15,1,10},{.5f,1,.5f}));guide.set_scene(geometry);
 need(guide.scene_revision()==2&&guide.state().trail_points==0,"Actual changed collision invalidates trail as before");
 auto embedded=geometry;embedded.revision=3;embedded.objects.push_back(box({feet.x,1,feet.z},{1,1,1}));
 rejects([&]{guide.set_scene(embedded);},"Actual embedding edit retains strict supported replacement rejection");
 need(guide.scene_revision()==2,"Failed geometry replacement cannot adopt revision");
}
void fractional_clock(){
 SceneSnapshot s{new_uuid(),0,{box({0,-.5f,0},{20,.5f,20})}};GuideRouteGraph graph{{{"a",{-6,.05f,0}},{"b",{6,.05f,0}}},{{"a","b",""}}};GuideController a(s,{-6,.05f,0},graph),b(s,{-6,.05f,0},graph);
 (void)a.advance({{6,.05f,0},true,0},1./120);(void)b.advance({{6,.05f,0},true,0},1./120);auto revised=s;revised.revision=1;a.set_scene(revised);
 const auto aa=a.advance({{6,.05f,0},true,1},1./120),bb=b.advance({{6,.05f,0},true,0},1./120);
 need(aa.character.feet==bb.character.feet&&aa.character.velocity==bb.character.velocity&&aa.character.ticks==bb.character.ticks,"Semantic rebind retains fractional fixed-tick accumulator exactly");
}
struct WalkFixture {
 FirstBootContent content;GameplayStoreRecovery state;SceneSnapshot scene;GroundedCharacter bs;CompanionRuntime adam;FirstBootChapterClock clock;
 explicit WalkFixture(FirstBootContent c):content(std::move(c)),state{{"semantic-scene",content.definition().world_id,"warm",new_uuid(),GameplayContext::player_world},0,0,first_boot_content_baseline(content).components},scene(first_boot_content_scene(state,content)),bs(scene,content.definition().jenison_returns.front()),adam(state,content){for(unsigned n=0;n<30;++n)tick({});need(bs.state().grounded,"Warm initial BS has actual support");}
 void tick(CharacterInput input){const auto s=bs.advance(input,1./60);clock.advance(1./60);(void)adam.advance({s.feet,s.grounded,scene.revision},1./60);}
 void walk(float x,float z){for(unsigned n=0;n<800;++n){const auto p=bs.state().feet;const auto d=std::hypot(x-p.x,z-p.z);if(d<.14f){need(bs.state().grounded,"Contact route remains supported");return;}CharacterInput i;i.move={(x-p.x)/d,0,(z-p.z)/d};tick(i);}throw std::runtime_error("CPU physical contact route blocked");}
 void station(FirstBootChapterAction action,std::size_t slot){const auto binding=*first_boot_content_workshop_binding(content.definition());FirstBootChapterActor actor;actor.feet=actor.previous_feet=bs.state().feet;actor.grounded=bs.state().grounded;actor.hazard=clock.sample(state);FirstBootChapterCommand command;command.action=action;command.target_id=binding.fixtures[slot];command.operation_id="semantic."+new_uuid();const auto batch=first_boot_content_action(state,command,actor,content);need(batch.has_value(),"Actual owned station rule creates a semantic outcome");auto after=state;after.revision=batch->revision;after.sequence=batch->events.back().sequence;for(const auto&d:batch->deltas){const auto it=std::find_if(after.components.begin(),after.components.end(),[&](const auto&r){return r.entity_id==d.component.entity_id&&r.type_id==d.component.type_id;});need(it!=after.components.end()&&d.action==ComponentAction::upsert,"Workshop outcome only edits existing component");*it=d.component;}first_boot_content_rules(state,after,*batch,actor,content);state=std::move(after);const auto next=first_boot_content_scene(state,content);bs.set_scene(next);scene=next;adam.synchronize(state);}
};
void actual_path_sample(){
 CreatorSession source(first_boot_schema(),"semantic-scene","warm");need(seed_first_boot(source).ok,"Seed real warm source");WalkFixture f(FirstBootContent::create(make_warm_workshop_draft(source,{}).definition));
 f.walk(-33.5f,-25);f.walk(-34.25f,-28.25f);f.station(FirstBootChapterAction::collect_probe,0);need(!f.adam.state().recall_required,"Collect probe preserves live Adam");
 f.walk(-33.5f,-25);f.walk(-37,-25);f.walk(-37,-20);f.walk(-37,-15);f.walk(-37,-10);f.walk(-32.2f,-6.9f);f.station(FirstBootChapterAction::sample_supply,1);need(!f.adam.state().recall_required,"Supply sample preserves live Adam");
 f.walk(-37,-10);f.walk(-41.3f,-7);const auto before=f.adam.state();need(before.guide&&before.guide->character.grounded&&before.saved.intent==GuideIntent::follow,"Path sample starts with real moving supported guide");
 std::cout<<"Path sample live guide feet "<<before.guide->character.feet.x<<','<<before.guide->character.feet.y<<','<<before.guide->character.feet.z<<'\n';
 f.station(FirstBootChapterAction::sample_path,2);const auto after=f.adam.state();need(!after.recall_required&&after.guide,"Path sample must not require Recall for unchanged colliders at moving contact pose");
 need(after.guide->character.feet==before.guide->character.feet&&after.guide->character.velocity==before.guide->character.velocity&&after.guide->trail_points==before.guide->trail_points,"Actual semantic station outcome preserves Adam's exact physical pose/velocity/trail");
 const auto head=f.state.revision;f.walk(-37,-10);for(unsigned n=0;n<180;++n)f.tick({});need(f.adam.state().guide&&!f.adam.state().recall_required&&distance(f.adam.state().guide->character.feet,f.bs.state().feet)<3.5f,"Actual path sampler route continues Follow without Recall");need(f.state.revision==head,"Runtime following cannot fabricate durable footsteps");
}
void moving_contact_rebind(){
 CreatorSession source(first_boot_schema(),"semantic-moving","warm");need(seed_first_boot(source).ok,"Seed actual low-trace scene");const auto content=FirstBootContent::create(make_warm_workshop_draft(source,{}).definition);
 const GameplayStoreRecovery state{{"semantic-moving",content.definition().world_id,"warm",new_uuid(),GameplayContext::player_world},0,0,first_boot_content_baseline(content).components};const auto scene=first_boot_content_scene(state,content);GuideSettings settings;settings.walk_speed=7;settings.catchup_speed=13;settings.catchup_distance=30;
 const Vec3 start{-39.2f,.15f,-10},target{-44,.15f,-5};GuideController guide(scene,start,{{{"start",start},{"end",target}},{{"start","end",""}}},settings);
 for(unsigned n=0;n<90;++n){const auto before=guide.advance({target,true,0},1./60);if(!before.character.grounded||before.activity!=GuideActivity::following)continue;
  bool fails_support=false;try{GuideController stationary(scene,before.character.feet,{},settings);}catch(const std::invalid_argument& error){if(std::string(error.what())=="Guide anchor needs close stable ground support")fails_support=true;else throw;}
  if(!fails_support)continue;std::cout<<"Actual moving supported contact "<<before.character.feet.x<<','<<before.character.feet.y<<','<<before.character.feet.z<<'\n';auto revised=scene;revised.revision=1;bool rejected=false;try{guide.set_scene(revised);}catch(const std::invalid_argument&){rejected=true;}
  need(!rejected,"Semantic rebind must preserve valid moving contact that stationary reconstruction rejects");const auto after=guide.state();need(after.character.feet==before.character.feet&&after.character.velocity==before.character.velocity&&after.trail_points==before.trail_points,"Transient supported contact body/trail must remain exact");return;
 }
 throw std::runtime_error("Bounded diagonal trace route did not exercise transient stationary-support rejection");
}
}
int main(int argc,char**argv){try{if(argc==1){moving_contact_rebind();actual_path_sample();offgraph_revision();fractional_clock();}else{need(argc==2,"One bounded regression selector expected");const std::string mode=argv[1];if(mode=="--workshop")actual_path_sample();else if(mode=="--offgraph")offgraph_revision();else if(mode=="--moving-contact")moving_contact_rebind();else throw std::runtime_error("Unknown regression selector");}std::cout<<"PASS "<<checks<<" semantic-only scene, live Workshop path sample, trail and strict geometry contracts\n";return 0;}catch(const std::exception&e){std::cerr<<"FAIL "<<checks<<": "<<e.what()<<'\n';return 1;}}
