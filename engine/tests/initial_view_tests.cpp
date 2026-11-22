#include <aibs/initial_view.hpp>
#include <aibs/warm_opening.hpp>
#include <aibs/scene.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {int checks=0;void check(bool v,const char* why){++checks;if(!v)throw std::runtime_error(why);}template<class F>void rejects(F f,const char* why){bool rejected=false;try{f();}catch(const std::invalid_argument&){rejected=true;}check(rejected,why);}Vec3 direction(const Camera& c){const float cp=std::cos(c.pitch);return {std::sin(c.yaw)*cp,std::sin(c.pitch),std::cos(c.yaw)*cp};}void settle(PlayerController& p){for(unsigned n=0;n<30;++n)p.update({},1./60);}}
int main(){try{
 CreatorSession source(first_boot_schema(),"initial-view-unit","new-branch");check(seed_first_boot(source).ok,"Seed failed");auto d=make_warm_opening_definition(source,{});d.hints.erase(std::string(first_boot_initial_view_key));const auto content=FirstBootContent::create(d);const auto baseline=first_boot_content_baseline(content);GameplayStoreRecovery state{{"initial-view-unit",d.world_id,"new-branch",new_uuid(),GameplayContext::temporary_play},0,0,baseline.components};const auto scene=first_boot_content_scene(state,content);
 const auto controller=std::find_if(d.fixtures.begin(),d.fixtures.end(),[](const auto& f){return f.object.name=="Controller and turning";});check(controller!=d.fixtures.end(),"Owned controller fixture missing");const auto target=controller->object.persistent_id;
 check(!first_boot_initial_view(d),"Old content without explicit initial view changed behavior");d.hints[std::string(first_boot_initial_view_key)]=target;const auto framing=first_boot_initial_view(d);check(framing&&framing->target_id==target&&framing->world_id==d.world_id,"Explicit scoped target missing");
 auto player=first_boot_content_player(state,content);settle(player);const auto before=player.state();const auto old_yaw=player.camera().yaw;check(frame_first_boot_initial_view(player,scene,*framing),"Actual controller target not visible from supported nook");check(player.state().feet==before.feet&&player.state().ticks==before.ticks,"Initial view moved/advanced BS");check(std::abs(player.camera().yaw-old_yaw)>1,"Initial facing still points at the south wall");
 auto all=scene;for(auto& object:all.objects)object.selectable=true;const auto hit=pick_scene(all,player.camera().position,direction(player.camera()),30);check(hit&&hit->persistent_id==target,"Framing does not actually aim at the owned visible fixture");
 auto blocked_scene=scene;blocked_scene.objects.push_back({new_uuid(),"Opaque non-selectable test wall",{-33.35f,1.5f,-27},{.8f,1.5f,.2f},{.3f,.3f,.3f},0,false});auto blocked=PlayerController(blocked_scene,d.jenison_returns.front());settle(blocked);const auto blocked_camera=blocked.camera();check(!frame_first_boot_initial_view(blocked,blocked_scene,*framing),"Framing ignored a non-selectable wall");check(blocked.camera().yaw==blocked_camera.yaw&&blocked.camera().pitch==blocked_camera.pitch,"Rejected framing mutated camera");
 auto other=scene;other.world_id=new_uuid();check(!frame_first_boot_initial_view(player,other,*framing),"Cross-world initial binding accepted");
 auto malformed=d;malformed.hints[std::string(first_boot_initial_view_key)]="";rejects([&]{first_boot_initial_view(malformed);},"Serialized empty key accepted instead of explicit erase");
 malformed=d;malformed.asset_profile=AssetContentProfile::legacy_v1;rejects([&]{first_boot_initial_view(malformed);},"Legacy content accepted new view contract");
 malformed=d;malformed.hints[std::string(first_boot_initial_view_key)]=new_uuid();rejects([&]{first_boot_initial_view(malformed);},"Foreign target accepted");
 malformed=d;malformed.hints[std::string(first_boot_initial_view_key)]=d.companions.front().entity_id;rejects([&]{first_boot_initial_view(malformed);},"Companion is not an owned inspection fixture");
 malformed=d;std::erase_if(malformed.fixtures,[&](const auto& f){return f.object.persistent_id==target;});std::erase_if(malformed.hints,[&](const auto& item){return item.first.starts_with("inspect."+target+".");});rejects([&]{first_boot_initial_view(malformed);},"Erased target silently cleared authored framing");malformed.hints.erase(std::string(first_boot_initial_view_key));check(!first_boot_initial_view(malformed),"Explicit same-group clear did not remove target binding");
 auto unframed=first_boot_content_player(state,content);settle(unframed);FirstBootInitialViewPolicy continuing(d,false);check(!continuing.apply(unframed,scene,{}),"Existing journey was reframed");
 FirstBootInitialViewPolicy fresh(d,true);WindowInput user;user.yaw_delta=.2f;unframed.update(user,0);const auto user_yaw=unframed.camera().yaw;check(!fresh.apply(unframed,scene,user)&&!fresh.pending()&&unframed.camera().yaw==user_yaw,"Framing overrode genuine user look");
 FirstBootInitialViewPolicy walking(d,true);user={};user.forward=1;check(!walking.apply(unframed,scene,user)&&!walking.pending(),"Framing ignored actual movement intent");
 FirstBootInitialViewPolicy quiet(d,true);check(quiet.apply(unframed,scene,{})&&quiet.applied()&&!quiet.pending(),"Fresh supported idle framing did not complete");
 const auto framed_camera=unframed.camera();check(!quiet.apply(unframed,scene,{})&&unframed.camera().yaw==framed_camera.yaw,"Completed framing kept overriding camera");
 auto resumed_state=state;resumed_state.revision=7;resumed_state.sequence=7;
 const auto resumed_scene=first_boot_content_scene(resumed_state,content);auto resumed_player=first_boot_content_player(resumed_state,content);settle(resumed_player);
 const auto resumed_before=resumed_player.state();FirstBootInitialViewPolicy resumed_policy(d,true);
 check(resumed_policy.apply(resumed_player,resumed_scene,{})&&resumed_policy.applied(),"Nonzero saved head at Jenison could not frame the owned target");
 check(resumed_player.state().feet==resumed_before.feet&&resumed_player.state().ticks==resumed_before.ticks&&resumed_state.revision==7&&resumed_state.sequence==7,"Resume framing changed body/time or saved heads");
 const auto resumed_hit=pick_scene(resumed_scene,resumed_player.camera().position,direction(resumed_player.camera()),30);check(resumed_hit&&resumed_hit->persistent_id==target,"Resume view does not face its visible owned target");
 FirstBootInitialViewPolicy reload_policy(d,true);WindowInput looking;looking.yaw_delta=.2f;const auto look_camera=resumed_player.camera();
 check(!reload_policy.apply(resumed_player,resumed_scene,looking)&&!reload_policy.pending()&&resumed_player.camera().yaw==look_camera.yaw,"Reload framing overrode genuine player look intent");
 std::cout<<checks<<" content-derived initial framing checks passed (CPU physics/LOS; native pixels pending)\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
