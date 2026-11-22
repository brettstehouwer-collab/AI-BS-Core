#include <aibs/guide_presentation.hpp>
#include <aibs/warm_opening.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {
unsigned checks=0;
void need(bool value,const char*why){++checks;if(!value)throw std::runtime_error(why);}
void actual_trace_step(){
 CreatorSession source(first_boot_schema(),"presentation-continuity","warm");need(seed_first_boot(source).ok,"Seed actual motherboard trace scene");const auto content=FirstBootContent::create(make_warm_workshop_draft(source,{}).definition);
 const GameplayStoreRecovery state{{"presentation-continuity",content.definition().world_id,"warm",new_uuid(),GameplayContext::player_world},0,0,first_boot_content_baseline(content).components};const auto scene=first_boot_content_scene(state,content);
 GuideSettings settings;settings.walk_speed=7;settings.catchup_speed=13;GuideController guide(scene,{-37,.05f,-2.5f},content.definition().companions.front().routes,settings);std::map<std::string,bool> gates;for(const auto&e:content.definition().companions.front().routes.edges)if(!e.door.empty())gates[e.door]=true;guide.set_doors(gates);
 const auto mesh=make_guide_placeholder();GuidePresentation presenter(mesh);bool grounded=false,airborne=false,regrounded=false,all_visible=true;unsigned missing_frames=0;Vec3 first_air{};
 for(unsigned n=0;n<120;++n){const auto live=guide.advance({{-41,.03f,5.88374f},true,scene.revision},1./60);grounded|=live.character.grounded;
  if(grounded&&!live.character.grounded){if(!airborne)first_air=live.character.feet;airborne=true;}else if(airborne&&live.character.grounded)regrounded=true;
  const auto instance=presenter.sample(live,1./60,false,false);if(!instance){all_visible=false;++missing_frames;continue;}
  need(instance->world[12]==live.character.feet.x&&instance->world[13]==live.character.feet.y&&instance->world[14]==live.character.feet.z,"Visual root follows exact actual controller feet");
  need(instance->opacity>.5f&&instance->opacity<1&&instance->emission>0,"Live hologram retains stable luminous material");
 }
 std::cout<<"Real controller trace grounded="<<grounded<<" airborne="<<airborne<<" regrounded="<<regrounded<<" missing="<<missing_frames<<" first_air="<<first_air.x<<','<<first_air.y<<','<<first_air.z<<'\n';
 need(grounded&&airborne&&regrounded,"Actual controller must exercise grounded-airborne-grounded trace contact");
 need(all_visible,"Steady hologram must remain visible through brief live-controller airborne contact");
 need(state.revision==0&&state.sequence==0,"Visual sampling creates no gameplay history");
}
void explicit_live_state_and_guards(){
 const auto mesh=make_guide_placeholder();GuidePresentation presenter(mesh);GuideState live;live.character.feet={-37,.1535f,.035f};live.character.velocity={0,-.3f,13};live.character.grounded=true;live.destination={-37,.2f,1.9f};live.activity=GuideActivity::following;
 const auto grounded=presenter.sample(live,1./60);need(grounded.has_value(),"Live grounded initial pose renders");const auto before_time=presenter.animation_seconds();
 live.character.feet={-37,.00809088f,.251802f};live.character.grounded=false;const auto step=presenter.sample(live,1./60);
 need(step.has_value()&&step->world[13]==live.character.feet.y,"Finite live airborne pose remains visible at its actual height");need(presenter.clip()==GuidePresentationClip::catchup&&presenter.animation_seconds()>before_time,"Live airborne motion retains velocity-driven animation");
 const auto frozen_time=presenter.animation_seconds();const auto frozen=step;live.character.feet.z+=1;const auto paused=presenter.sample(live,1,true);
 need(paused&&paused->world==frozen->world&&presenter.animation_seconds()==frozen_time,"Pause freezes prior live airborne visual transform and clock");
 need(!presenter.sample(live,0,true,true),"Recall-required state hides even during pause");need(!presenter.sample({},0,true),"Missing motion hides even during pause");
 need(!presenter.sample(live,0,true),"Pause without a previous visible instance invents no pose");
 live.character.grounded=true;const auto landed=presenter.sample(live,1./60);need(landed.has_value(),"Actual regrounded live state resumes normally");
 auto bad=live;bad.intent=static_cast<GuideIntent>(99);need(!presenter.sample(bad,.01),"Invalid intent still hides");bad=live;bad.activity=static_cast<GuideActivity>(99);need(!presenter.sample(bad,.01),"Invalid activity still hides");bad=live;bad.character.feet.x=1000001;need(!presenter.sample(bad,.01),"Out-of-bounds live feet still hide");
}
}
int main(){try{actual_trace_step();explicit_live_state_and_guards();std::cout<<"PASS "<<checks<<" steady live-controller hologram continuity checks\n";return 0;}catch(const std::exception&e){std::cerr<<"FAIL "<<checks<<": "<<e.what()<<'\n';return 1;}}
