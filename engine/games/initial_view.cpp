#include <aibs/initial_view.hpp>
#include <aibs/opening_inspections.hpp>
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace aibs {namespace {
bool intended(const WindowInput& input){return input.forward!=0||input.right!=0||input.up!=0||input.yaw_delta!=0||input.pitch_delta!=0||input.jump||input.sprint||input.interact||input.build||input.dismantle||input.undo||input.redo||input.save||input.reload||input.cycle_camera||input.toggle_flight||input.companion_follow||input.companion_wait||input.companion_recall;}
}}
namespace aibs {
std::optional<FirstBootInitialView> first_boot_initial_view(const FirstBootContentDefinition& d){
 const auto field=d.hints.find(std::string(first_boot_initial_view_key));if(field==d.hints.end())return {};
 if(d.format_version!=3||d.asset_profile!=AssetContentProfile::warm_beginning||!is_uuid(d.world_id)||!is_uuid(field->second))throw std::invalid_argument("Initial view requires a modern chapter and canonical owned inspection UUID; clear by erasing its key");
 const OpeningInspectionCatalog inspections(d);const auto* target=inspections.find(field->second);if(!target)throw std::invalid_argument("Initial view target must remain an owned selectable inspection fixture; explicitly clear it in the same group before unbinding/erasing");
 return FirstBootInitialView{d.world_id,target->fixture_id,target->center};
}
bool frame_first_boot_initial_view(PlayerController& player,const SceneSnapshot& scene,const FirstBootInitialView& target){
 if(scene.world_id!=target.world_id||player.third_person()||player.inspection_mode())return false;
 if(std::count_if(scene.objects.begin(),scene.objects.end(),[&](const auto& object){return object.persistent_id==target.target_id&&object.center==target.center;})!=1)return false;
 const auto camera=player.camera();const Vec3 ray{target.center.x-camera.position.x,target.center.y-camera.position.y,target.center.z-camera.position.z};
 const auto horizontal=std::hypot(ray.x,ray.z),distance=std::hypot(ray.x,ray.y,ray.z);
 if(!std::isfinite(distance)||horizontal<.05f||distance>30.f||distance<.1f)return false;
 const auto pitch=std::atan2(ray.y,horizontal);if(std::abs(pitch)>1.4f)return false;
 auto occluders=scene;for(auto& object:occluders.objects)object.selectable=true;
 const auto hit=pick_scene(occluders,camera.position,ray,distance+.01f);if(!hit||hit->persistent_id!=target.target_id)return false;
 WindowInput framing;framing.yaw_delta=std::remainder(std::atan2(ray.x,ray.z)-camera.yaw,6.28318530718f);framing.pitch_delta=pitch-camera.pitch;player.update(framing,0);return true;
}
FirstBootInitialViewPolicy::FirstBootInitialViewPolicy(const FirstBootContentDefinition& d,bool fresh):binding_(first_boot_initial_view(d)),pending_(fresh&&binding_.has_value()){}
bool FirstBootInitialViewPolicy::apply(PlayerController& player,const SceneSnapshot& scene,const WindowInput& actual){
 if(!pending_)return false;if(intended(actual)){pending_=false;return false;}if(!actual.active)return false;
 const bool framed=frame_first_boot_initial_view(player,scene,*binding_);applied_=applied_||framed;
 if(!framed||player.state().grounded||++attempts_>=32)pending_=false;return framed;
}
}
