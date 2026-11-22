#include <aibs/player.hpp>
#include <aibs/engine.hpp>
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
SceneSnapshot room() {
 return {new_uuid(), 0, {
  {new_uuid(), "floor", {0,-1,0}, {20,1,20}, {0.2f,0.3f,0.2f}},
  {new_uuid(), "wall", {0,3,5}, {20,3,0.5f}, {0.4f,0.4f,0.4f}}
 }};
}
float distance(Vec3 a, Vec3 b) {
 return std::sqrt((a.x-b.x)*(a.x-b.x)+(a.y-b.y)*(a.y-b.y)+(a.z-b.z)*(a.z-b.z));
}
}
int main() {
 try {
  PlayerController player(room(), {0,0.1f,0});
  WindowInput idle;
  for (int i=0; i<120; ++i) player.update(idle, 1.0/60);
  require(player.state().grounded, "capsule settles on floor");
  require(player.camera().position.y > player.state().feet.y+1.4f, "first-person eye above feet");
  WindowInput queued; queued.jump=true;
  player.update(queued,0);
  WindowInput suspended; suspended.active=false;
  player.update(suspended,10);
  for(int i=0;i<8;++i) player.update(idle,1.0/60);
  require(player.state().grounded && player.state().feet.y<0.1f, "focus loss discards a queued sub-tick jump");
  WindowInput forward; forward.forward=1;
  for (int i=0; i<120; ++i) player.update(forward, 1.0/60);
  require(player.state().feet.z>1 && player.state().feet.z<4.3f, "walking collides with wall");
  auto stopped=player.state(); WindowInput inactive=forward; inactive.active=false;
  inactive.yaw_delta=1; inactive.jump=true;
  player.update(inactive, 10);
  require(player.state().feet==stopped.feet && player.state().ticks==stopped.ticks, "focus loss pauses movement without catch-up");
  player.update(idle, 0);
  require(player.state().ticks==stopped.ticks, "reactivation does not replay focus-lost time");
  WindowInput jump; jump.jump=true;
  player.update(jump,1.0/60);
  for (int i=0; i<8; ++i) player.update(idle,1.0/60);
  require(player.state().feet.y>stopped.feet.y+0.2f, "space edge jumps from ground");
  WindowInput third; third.cycle_camera=true;
  player.update(third,0);
  require(player.third_person(), "camera mode switches");
  require(distance(player.camera().position, player.state().feet)>1, "third-person boom follows capsule");
  require(player.avatar_visible(), "clear third-person boom displays BS");
  const auto physics_feet=player.state().feet;
  WindowInput fly; fly.toggle_flight=true;
  player.update(fly,0);
  require(player.inspection_mode(), "developer free flight is explicit");
  require(!player.avatar_visible(), "inspection hides BS proxy independently of camera-mode preference");
  WindowInput rise; rise.up=1;
  player.update(rise,0.1);
  require(player.state().feet==physics_feet, "inspection camera does not move BS");
  player.update(fly,0);
  require(!player.inspection_mode() && player.state().feet==physics_feet, "leaving inspection returns to BS");
  auto before=player.state().feet;
  player.update(idle,-1);
  require(player.state().feet==before, "negative frame duration does not move capsule");
  auto low_room=room();
  low_room.objects.push_back({new_uuid(), "Low ceiling", {0,2.34f,0}, {20,.5f,20}, {.3f,.3f,.4f}});
  PlayerController beneath_ceiling(low_room,{0,.02f,0});
  for(int i=0;i<120;++i) beneath_ceiling.update(idle,1.0/60);
  require(beneath_ceiling.state().grounded, "capsule fits beneath low ceiling");
  beneath_ceiling.update(third,0);
  const auto low_feet=beneath_ceiling.state().feet;
  const Vec3 low_eye{low_feet.x,low_feet.y+1.62f,low_feet.z};
  require(beneath_ceiling.third_person() && !beneath_ceiling.avatar_visible() && distance(beneath_ceiling.camera().position,low_eye)<.00001f,
          "overlapping camera anchor sphere falls back to valid eye and hides BS without throwing");
  beneath_ceiling.update(third,0);
  require(!beneath_ceiling.third_person() && !beneath_ceiling.avatar_visible(), "first-person mode keeps BS proxy hidden");
  auto back_wall=room();
  back_wall.objects.push_back({new_uuid(), "Close rear wall", {0,2,-.65f}, {3,2,.1f}, {.3f,.3f,.4f}});
  PlayerController against_wall(back_wall,{0,.02f,0});
  for(int i=0;i<120;++i) against_wall.update(idle,1.0/60);
  against_wall.update(third,0);
  const auto wall_feet=against_wall.state().feet;
  const Vec3 wall_eye{wall_feet.x,wall_feet.y+1.62f,wall_feet.z};
  require(distance(against_wall.camera().position,wall_eye)<.6f && !against_wall.avatar_visible(),
          "short obstruction-limited boom hides BS so the camera does not render inside its proxy");
  against_wall.set_scene(room());
  require(against_wall.avatar_visible() && distance(against_wall.camera().position,wall_eye)>4,
          "removing the rear obstruction restores the visible third-person proxy");
  PlayerController steep_view(room(),{0,.02f,0});
  for(int i=0;i<120;++i) steep_view.update(idle,1.0/60);
  WindowInput look_up; look_up.cycle_camera=true; look_up.pitch_delta=1.52f;
  steep_view.update(look_up,0);
  const auto steep_feet=steep_view.state().feet;
  const Vec3 steep_eye{steep_feet.x,steep_feet.y+1.62f,steep_feet.z};
  require(distance(steep_view.camera().position,steep_eye)>.6f && !steep_view.avatar_visible(),
          "steep upward view hides BS when the floor retracts camera into body despite a long eye distance");
  WindowInput look_down; look_down.pitch_delta=-2.8f;
  steep_view.update(look_down,0);
  require(steep_view.camera().position.y>steep_feet.y+1.9f && steep_view.avatar_visible(),
          "camera clearly above the body restores the visible proxy even at a steep angle");
  CharacterSettings larger; larger.radius=.8f; larger.height=4;
  PlayerController large_body(room(),{0,.02f,0},larger);
  for(int i=0;i<120;++i) large_body.update(idle,1.0/60);
  large_body.update(look_up,0);
  require(!large_body.avatar_visible(), "camera visibility uses configured body radius and height rather than default dimensions");
  std::cout << "PASS: grounded player, jump, cameras, focus and inspection contracts\n";
  return 0;
 } catch (const std::exception& error) { std::cerr << "FAIL: " << error.what() << '\n'; return 1; }
}
