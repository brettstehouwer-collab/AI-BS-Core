#include <aibs/physics.hpp>
#include <aibs/engine.hpp>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using namespace aibs;
namespace {
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
template<class F> void rejects(F&& operation, const char* message) {
 bool threw = false;
 try { operation(); } catch (const std::invalid_argument&) { threw = true; }
 require(threw, message);
}
SceneObject box(Vec3 center, Vec3 half, bool selectable = true) {
 return {new_uuid(), "Collision fixture", center, half, {.3f,.5f,.7f}, 0, selectable};
}
SceneSnapshot course() {
 return {new_uuid(), 1, {box({0,-.5f,0}, {20,.5f,20}), box({0,2,5}, {3,2,1}, false)}};
}
void ticks(GroundedCharacter& player, CharacterInput input, int count) {
 for (int tick=0;tick<count;++tick) (void)player.advance(input, 1.0/60.0);
}
struct Incline {
 SceneSnapshot scene;
 float low_z, high_z, high_y;
};
Incline incline(float degrees) {
 const float radians=degrees*3.14159265358979323846f/180;
 const float sine=std::sin(radians), cosine=std::cos(radians);
 auto ramp=box({0,6*sine-.1f*cosine,0},{4,.1f,6});
 ramp.rotation={-std::sin(radians*.5f),0,0,std::cos(radians*.5f)};
 const float low_z=-6*cosine-.1f*sine, high_z=6*cosine-.1f*sine, high_y=12*sine;
 SceneSnapshot result{new_uuid(),0,{box({0,-.5f,0},{40,.5f,40}),ramp,
  box({0,high_y-.5f,high_z+3},{4,.5f,3})}};
 return {result,low_z,high_z,high_y};
}
void slope_contracts() {
 for(const float degrees:{20.0f,30.0f}) {
  const auto ramp=incline(degrees);
  GroundedCharacter walker(ramp.scene,{0,.05f,ramp.low_z-2});
  ticks(walker,{},30);
  bool touched_incline=false;
  for(int frame=0;frame<180;++frame) {
   const auto state=walker.advance({{0,0,1}},1.0/60.0);
   if(state.feet.z>ramp.low_z+1 && state.feet.z<ramp.high_z-1) {
    touched_incline=true;
    require(state.grounded && state.feet.y>.2f,"walkable incline retains capsule support during ascent");
   }
  }
  const auto summit=walker.state();
  std::cout << "Incline "<<degrees<<" ascent feet="<<summit.feet.x<<','<<summit.feet.y<<','<<summit.feet.z<<" grounded="<<summit.grounded<<'\n';
  require(touched_incline && summit.grounded && summit.feet.z>ramp.high_z+.5f && std::abs(summit.feet.y-ramp.high_y)<.08f,
   "walkable incline reaches elevated platform through floor-ramp-platform transitions");
  bool descended_incline=false;
  for(int frame=0;frame<180;++frame) {
   const auto state=walker.advance({{0,0,-1}},1.0/60.0);
   if(state.feet.z>ramp.low_z+1 && state.feet.z<ramp.high_z-1) {
    descended_incline=true;
    require(state.grounded,"walkable incline retains capsule support during descent");
   }
  }
  const auto base=walker.state();
  std::cout << "Incline "<<degrees<<" descent feet="<<base.feet.x<<','<<base.feet.y<<','<<base.feet.z<<" grounded="<<base.grounded<<'\n';
  require(descended_incline && base.grounded && base.feet.z<ramp.low_z-.5f && std::abs(base.feet.y)<.08f,
   "descending ramp returns smoothly to lower floor");
 }
 const auto steep=incline(60);
 GroundedCharacter climber(steep.scene,{0,.05f,steep.low_z-2});
 ticks(climber,{},30); ticks(climber,{{0,0,1}},180);
 const auto blocked=climber.state();
 std::cout << "Steep60 blocked feet="<<blocked.feet.x<<','<<blocked.feet.y<<','<<blocked.feet.z<<'\n';
 require(blocked.feet.z<steep.low_z+.5f && blocked.feet.y<.6f,
  "above-limit incline rejects forced ascent instead of stair climbing its face");
 GroundedCharacter slider(steep.scene,{0,8,0});
 ticks(slider,{},45);
 const auto sliding=slider.state();
 std::cout << "Steep60 gravity feet="<<sliding.feet.x<<','<<sliding.feet.y<<','<<sliding.feet.z<<" grounded="<<sliding.grounded<<'\n';
 require(sliding.feet.z<-.3f && sliding.feet.y<6 && !sliding.grounded,
  "gravity drives an unsupported capsule down a too-steep surface");
 ticks(slider,{},90);
 require(slider.state().grounded && slider.state().feet.z<steep.low_z && std::abs(slider.state().feet.y)<.08f,
  "steep slide reaches lower floor and restores grounded movement");
 auto tall_step=course(); tall_step.objects.push_back(box({-8,.65f,-2},{2,.65f,1}));
 GroundedCharacter stopped(tall_step,{-8,.05f,-5}); ticks(stopped,{},30); ticks(stopped,{{0,0,1}},90);
 require(stopped.state().feet.z<-3.3f && stopped.state().feet.y<.08f,"above-limit step blocks instead of auto mounting");
}
void camera_contracts() {
 SceneSnapshot near_edge{new_uuid(),0,{box({0,-.5f,0},{20,.5f,20}),box({.4f,2,5},{.2f,2,1},false)}};
 GroundedCharacter camera_world(near_edge,{-5,.05f,0});
 const auto center_ray=camera_world.camera_position({0,1,0},{0,1,10},0);
 require(center_ray.z==10,"camera center ray misses off-axis wall");
 const auto volume=camera_world.camera_position({0,1,0},{0,1,10},.3f);
 std::cout << "Camera edge sweep center="<<volume.x<<','<<volume.y<<','<<volume.z<<'\n';
 require(volume.z>3.5f && volume.z<3.9f,"camera volume blocks near-edge clipping missed by center ray");
 const auto inside_destination=camera_world.camera_position({.4f,1,0},{.4f,1,5},.3f);
 require(inside_destination.z<3.71f && inside_destination.z>3.5f,"occupied desired endpoint is clipped to free camera volume");
 rejects([&]{(void)camera_world.camera_position({.4f,1,5},{0,1,0},.3f);},"embedded camera anchor rejected instead of returning solid camera position");
 rejects([&]{(void)camera_world.camera_position({.4f,1,5},{.4f,1,5},.3f);},"both occupied endpoints rejected even on zero length boom");
 rejects([&]{(void)camera_world.camera_position({.4f,1,5},{0,1,0},0);},"embedded zero-radius ray anchor rejected");
 const Vec3 free{0,1,0};
 require(camera_world.camera_position(free,free,.3f)==free,"free zero-length boom remains valid");
 rejects([&]{(void)camera_world.camera_position(free,{0,1,10},100);},"camera radius budget enforced");
 rejects([&]{(void)camera_world.camera_position(free,{1e30f,1,10},.3f);},"camera coordinate budget rejects overflowing casts");
}
}
int main(int argc,char** argv) {
 try {
  if(argc>1 && std::string(argv[1])=="--camera-only") { camera_contracts(); return 0; }
  const auto scene=course();
  GroundedCharacter player(scene, {0,2,0});
  ticks(player, {}, 120);
  require(player.state().grounded && std::abs(player.state().feet.y)<.07f, "gravity lands the capsule on floor");
  ticks(player, {{0,0,1}}, 120);
  require(player.state().feet.z>3.4f && player.state().feet.z<3.7f, "unselectable wall blocks capsule instead of tunneling");
  ticks(player, {{1,0,1}}, 15);
  require(player.state().feet.x>.7f && player.state().feet.z<3.7f, "capsule slides along walls");
  player.reset({-10,.05f,0}); ticks(player, {}, 30);
  (void)player.advance({{}, false, true},1.0/60.0);
  ticks(player, {{}, false, true}, 20);
  require(player.state().feet.y>.5f, "grounded jump rises");
  ticks(player, {{}, false, true}, 120);
  require(player.state().grounded, "holding jump cannot cause repeated jumps");
  (void)player.advance({},0);
  (void)player.advance({{},false,true},0);
  const auto before_suspend=player.state();
  player.suspend();
  (void)player.advance({},1.0/60.0);
  require(player.state().grounded && std::abs(player.state().feet.y-before_suspend.feet.y)<.02f,
   "focus suspension cancels queued sub-tick jump without moving or resetting BS");
  GroundedCharacter sixty(scene, {-10,.05f,0}), thirty(scene, {-10,.05f,0});
  ticks(sixty, {{1,0,0}}, 60);
  for(int frame=0;frame<30;++frame) (void)thirty.advance({{1,0,0}},1.0/30.0);
  require(sixty.state().ticks==60 && thirty.state().ticks==60 && std::abs(sixty.state().feet.x-thirty.state().feet.x)<.0001f, "fixed ticks ignore render cadence");
  const auto before_pause=sixty.state();
  (void)sixty.advance({},5);
  require(sixty.state().ticks-before_pause.ticks<=8 && sixty.state().dropped_seconds>4.8, "long pause has bounded catchup and reports dropped time");
  player.reset({0,.05f,0}); ticks(player, {},30);
  const auto preserved=player.state();
  auto occupied=scene;
  occupied.objects.push_back(box({0,1,0},{1,1,1}));
  rejects([&]{player.set_scene(occupied);}, "building over character rejected");
  require(player.state().feet==preserved.feet, "rejected collider update preserves pose");
  const auto camera=player.camera_position({0,1,0},{0,1,10});
  require(camera.z>3.5f && camera.z<4, "camera cannot pass through unselectable wall");
  auto removed=scene; removed.objects.pop_back(); player.set_scene(removed);
  require(player.camera_position({0,1,0},{0,1,10}).z==10, "removed collider no longer blocks camera");
  ticks(player, {{0,0,1},true}, 180);
  require(player.state().feet.z>25 && player.state().feet.y<-1 && !player.state().grounded, "walking off platform falls instead of hovering");
  player.reset({0,.05f,0}); ticks(player,{},30);
  require(player.state().grounded, "fall recovery reset restores grounded play");
  auto stairs=course(); stairs.objects.push_back(box({-8,.15f,-2},{2,.15f,1}));
  GroundedCharacter stepper(stairs,{-8,.05f,-5}); ticks(stepper,{},30);
  ticks(stepper,{{0,0,1}},25);
  require(stepper.state().feet.z>-2.5f && stepper.state().feet.y>.25f, "short step is climbable");
  rejects([&]{(void)player.advance({},-1);}, "negative elapsed rejected");
  rejects([&]{(void)player.advance({{std::numeric_limits<float>::quiet_NaN(),0,0}},.016);}, "nonfinite input rejected");
  rejects([&]{player.reset({0,std::numeric_limits<float>::infinity(),0});}, "nonfinite reset rejected");
  rejects([&]{(void)player.camera_position({0,1,0},{0,1,10},-1);}, "negative camera clearance rejected");
  auto bad=scene; bad.world_id="bad";
  rejects([&]{player.set_scene(bad);}, "invalid scene rejected transactionally");
  slope_contracts(); camera_contracts();
  std::cout << "PASS: Jolt capsule gravity/walls/sliding/jump/steps/falls/slopes, fixed ticks, live colliders and swept camera volume\n";
  return 0;
 } catch(const std::exception& error) { std::cerr << "FAIL: " << error.what() << '\n'; return 1; }
}
