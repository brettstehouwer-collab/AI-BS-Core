// Headless regression using the same targeting helper as the native app.
// Uses actual PlayerController/Jolt behavior and independent final-ray geometry.
// No renderer, window, private header overlay or copied aiming implementation.
#include "player_targeting.hpp"
#include <array>
#include <cmath>
#include <cstddef>
#include <iostream>
#include <initializer_list>
#include <stdexcept>
#include <string>

using namespace aibs;
namespace {
std::size_t assertions = 0, aiming_cases = 0;
constexpr const char* target_id = "00000000-0000-4000-8000-000000000003";
void require(bool condition, const char* message) {
 ++assertions;
 if (!condition) throw std::runtime_error(message);
}
double length(Vec3 p) {
 return std::sqrt(double(p.x)*p.x+double(p.y)*p.y+double(p.z)*p.z);
}
Vec3 subtract(Vec3 a, Vec3 b) { return {a.x-b.x,a.y-b.y,a.z-b.z}; }
double distance(Vec3 a, Vec3 b) { return length(subtract(a,b)); }
SceneSnapshot scene(Vec3 target, bool rear_wall=false, bool low_ceiling=false) {
 SceneSnapshot result{"00000000-0000-4000-8000-000000000001",0,{
  {"00000000-0000-4000-8000-000000000002","floor",{0,-.5f,0},{100,.5f,100},{.2f,.3f,.2f}},
  {target_id,"small interaction target",target,{.025f,.025f,.025f},{.8f,.4f,.2f}}
 }};
 if (rear_wall) result.objects.push_back({
  "00000000-0000-4000-8000-000000000004","rear boom obstruction",{0,2,-.65f},{3,2,.1f},{.3f,.3f,.4f}});
 if (low_ceiling) result.objects.push_back({
  "00000000-0000-4000-8000-000000000005","low ceiling",{0,2.34f,0},{20,.5f,20},{.3f,.3f,.4f}});
 return result;
}
void settle(PlayerController& p) {
 WindowInput idle;
 for (unsigned i=0;i<120;++i) p.update(idle,1./60);
 require(p.state().grounded,"fixture capsule did not settle");
}
void unchanged_body(const CharacterState& before, const CharacterState& after) {
 require(before.feet==after.feet,"zero-dt aim moved physical feet");
 require(before.velocity==after.velocity,"zero-dt aim changed physical velocity");
 require(before.grounded==after.grounded,"zero-dt aim changed grounding");
 require(before.ticks==after.ticks,"zero-dt aim advanced physics ticks");
 require(before.dropped_seconds==after.dropped_seconds,"zero-dt aim changed dropped-time accounting");
}

using aibs::app_input::aim;

void checked_aim(PlayerController& p, const SceneSnapshot& world, Vec3 target) {
 const auto body=p.state();
 const bool preferred_third=p.third_person(),inspection=p.inspection_mode();
 aim(p,target);
 unchanged_body(body,p.state());
 require(p.third_person()==preferred_third,"aim changed preferred camera mode");
 require(p.inspection_mode()==inspection,"aim toggled inspection");
 const auto& c=p.camera();
 const Vec3 forward{std::sin(c.yaw)*std::cos(c.pitch),std::sin(c.pitch),std::cos(c.yaw)*std::cos(c.pitch)};
 const auto offset=subtract(target,c.position);
 const double norm=length(forward);
 const double projection=(double(offset.x)*forward.x+double(offset.y)*forward.y+double(offset.z)*forward.z)/norm;
 const double cx=double(offset.y)*forward.z-double(offset.z)*forward.y;
 const double cy=double(offset.z)*forward.x-double(offset.x)*forward.z;
 const double cz=double(offset.x)*forward.y-double(offset.y)*forward.x;
 const double perpendicular=std::sqrt(cx*cx+cy*cy+cz*cz)/norm;
 require(std::isfinite(projection)&&projection>0,"target is not ahead of final camera");
 require(std::isfinite(perpendicular)&&perpendicular<1e-3,"final camera center ray misses target after orbit repositioning");
 require(std::abs(c.pitch)<=(inspection?1.45f:1.4f)+1e-5f,"aim exceeded existing pitch bound");
 const auto hit=pick_scene(world,c.position,forward,100);
 require(hit.has_value()&&hit->persistent_id==target_id,"actual scene picker did not select the small visible target");
 ++aiming_cases;
}
void first_and_third_person() {
 const std::array<float,3> heights{{1.4f,1.8f,2.4f}};
 const std::array<Vec3,4> targets{{{3,1,4},{-4,2.7f,1.5f},{.3f,.6f,-3},{-.5f,3.2f,-2}}};
 const std::array<float,4> starting_yaws{{2.4f,-2.2f,.7f,-.8f}};
 const std::array<float,4> starting_pitches{{.4f,-.5f,.6f,-.3f}};
 for (float height:heights) for (std::size_t i=0;i<targets.size();++i) for (bool third:{false,true}) {
  const auto world=scene(targets[i]);CharacterSettings settings;settings.height=height;
  PlayerController p(world,{0,.02f,0},settings);settle(p);
  // Observe the real first-person camera rather than reproducing eye_height's
  // implementation or using the accessor under test as the expected result.
  // The independent final ray and actual scene picker validate shared targeting.
  const auto observed_eye=p.camera().position;
  require(observed_eye.y>p.state().feet.y&&observed_eye.x==p.state().feet.x&&observed_eye.z==p.state().feet.z,
          "first-person fixture camera is not directly above physical feet");
  WindowInput orient;orient.yaw_delta=starting_yaws[i];orient.pitch_delta=starting_pitches[i];orient.cycle_camera=third;
  p.update(orient,0);
  checked_aim(p,world,targets[i]);
  const auto once=p.camera();checked_aim(p,world,targets[i]);
  require(distance(once.position,p.camera().position)<1e-4,"repeating target aim drifted camera position");
 }
}
void obstructed_boom_and_fallback() {
 {
  const Vec3 target{0,1.6f,4};const auto world=scene(target,true);
  PlayerController p(world,{0,.02f,0});settle(p);const auto observed_eye=p.camera().position;
  WindowInput third;third.cycle_camera=true;third.yaw_delta=.7f;p.update(third,0);
  checked_aim(p,world,target);
  require(distance(p.camera().position,observed_eye)<.6,"rear wall did not retract actual physics camera boom");
  require(p.third_person()&&!p.avatar_visible(),"retracted boom changed preference or exposed the body proxy");
 }
 {
  const Vec3 target{0,1.55f,3};const auto world=scene(target,false,true);
  PlayerController p(world,{0,.02f,0});settle(p);const auto observed_eye=p.camera().position;
  WindowInput third;third.cycle_camera=true;p.update(third,0);
  checked_aim(p,world,target);
  require(distance(p.camera().position,observed_eye)<1e-4,"overlapping sphere did not use the actual eye fallback");
  require(p.third_person()&&!p.avatar_visible(),"eye fallback changed preference or showed the body proxy");
 }
}
void inspection_camera() {
 const Vec3 target{-3,1.2f,5};const auto world=scene(target);
 for (bool preferred_third:{false,true}) {
  PlayerController p(world,{0,.02f,0});settle(p);
  const auto observed_body_eye=p.camera().position;
  WindowInput mode;mode.cycle_camera=preferred_third;p.update(mode,0);
  WindowInput inspection;inspection.toggle_flight=true;p.update(inspection,0);
  require(p.inspection_mode(),"inspection fixture did not enter free camera");
  WindowInput move;move.up=1;move.right=.4f;move.forward=.3f;p.update(move,.1);
  const auto camera_position=p.camera().position;
  require(distance(camera_position,observed_body_eye)>1,"inspection fixture did not detach from body eye");
  checked_aim(p,world,target);
  require(distance(camera_position,p.camera().position)<1e-6,"inspection aim incorrectly moved the free camera");
  require(p.third_person()==preferred_third,"inspection aim lost stored third-person preference");
 }
}
void partial_tick_and_pending_jump() {
 const Vec3 target{3,1,4};const auto world=scene(target);
 {
  PlayerController aimed(world,{0,.02f,0}),control(world,{0,.02f,0});settle(aimed);settle(control);
  WindowInput idle;aimed.update(idle,1./120);control.update(idle,1./120);const auto before=aimed.state();
  checked_aim(aimed,world,target);
  aimed.update(idle,1./120);control.update(idle,1./120);
  require(aimed.state().ticks==before.ticks+1,"aim dropped a pending partial physics tick");
  unchanged_body(control.state(),aimed.state());
 }
 {
  PlayerController aimed(world,{0,.02f,0}),control(world,{0,.02f,0});settle(aimed);settle(control);
  WindowInput queued_jump;queued_jump.jump=true;aimed.update(queued_jump,0);control.update(queued_jump,0);
  const auto before=aimed.state();checked_aim(aimed,world,target);
  WindowInput idle;aimed.update(idle,1./60);control.update(idle,1./60);
  require(aimed.state().feet.y>before.feet.y,"zero-dt aim discarded the queued jump");
  unchanged_body(control.state(),aimed.state());
 }
}
}
int main() {
 try {
  first_and_third_person();obstructed_boom_and_fallback();inspection_camera();partial_tick_and_pending_jump();
  std::cout<<"PASS: "<<aiming_cases<<" actual-player aim checks, "<<assertions<<" assertions; camera-ray selection, orbit/retraction, custom heights, inspection and zero-dt physics contracts\n";
  return 0;
 } catch (const std::exception& error) {
  std::cerr<<"FAIL after "<<aiming_cases<<" completed aim checks / "<<assertions<<" assertions: "<<error.what()<<'\n';
  return 1;
 }
}
