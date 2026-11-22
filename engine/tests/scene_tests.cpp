#include <aibs/scene.hpp>
#include <aibs/engine.hpp>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace aibs;
void require(bool condition, const char* why) { if (!condition) throw std::runtime_error(why); }
template<class F> void rejects(F&& function, const char* why) {
 bool rejected = false;
 try { function(); } catch (const std::invalid_argument&) { rejected = true; }
 require(rejected, why);
}
int main() {
 try {
  const auto near_id = new_uuid(), far_id = new_uuid();
  SceneSnapshot scene{new_uuid(), 7, {
   {far_id, "Far machine", {0,0,12}, {1,1,1}, {0.2f,0.5f,0.7f}},
   {near_id, "Core", {0,0,4}, {1,1,1}, {0.9f,0.4f,0.1f}, 0.5f},
   {near_id, "Core part", {0,2,4}, {0.5f,0.5f,0.5f}, {0.9f,0.4f,0.1f}}
  }};
  const auto mesh = mesh_from_snapshot(scene);
  require(mesh.vertices.size() == 108, "each box emits twelve triangles");
  require(mesh.landmarks.size() == 2, "composite UUID named once");
  for (const auto& vertex : mesh.vertices) {
   require(std::isfinite(vertex.position.x) && std::isfinite(vertex.position.y) && std::isfinite(vertex.position.z), "finite extracted mesh");
  }
  const auto near = pick_scene(scene, {0,0,0}, {0,0,1});
  require(near && near->persistent_id == near_id && std::abs(near->distance - 3) < 0.0001f, "nearest stable identity");
  const auto scaled = pick_scene(scene, {0,0,0}, {0,0,500});
  require(scaled && std::abs(scaled->distance - near->distance) < 0.0001f, "direction length does not alter distance");
  require(!pick_scene(scene, {8,0,0}, {0,0,1}), "parallel ray miss");
  require(!pick_scene(scene, {0,0,0}, {0,0,1}, 2), "pick range limits selection");
  require(pick_scene(scene, {0,0,4}, {0,0,1})->distance == 0, "ray starting inside box");
  scene.objects[1].selectable = false;
  require(pick_scene(scene, {0,0,0}, {0,0,1})->persistent_id == far_id, "unselectable objects ignored");
  require(pick_scene(scene, {0,2,0}, {0,0,1})->persistent_id == near_id, "composite part returns owning UUID");
  SceneSnapshot empty{new_uuid(), 0, {}};
  require(mesh_from_snapshot(empty).vertices.empty() && !pick_scene(empty, {0,0,0}, {0,0,1}), "empty world supported");
  rejects([&] { (void)pick_scene(scene, {0,0,0}, {0,0,0}); }, "zero direction rejected");
  rejects([&] { (void)pick_scene(scene, {0,0,0}, {0,0,1}, -1); }, "negative distance rejected");
  rejects([&] { (void)pick_scene(scene, {0,0,0}, {0,0,1}, std::numeric_limits<float>::infinity()); }, "infinite distance rejected");
  auto invalid = scene;
  invalid.world_id = "not-a-uuid";
  rejects([&] { (void)mesh_from_snapshot(invalid); }, "world scope UUID required");
  invalid = scene; invalid.objects[0].persistent_id.clear();
  rejects([&] { (void)mesh_from_snapshot(invalid); }, "entity UUID required");
  invalid = scene; invalid.objects[0].half_extent.x = 0;
  rejects([&] { (void)mesh_from_snapshot(invalid); }, "positive extents required");
  invalid = scene; invalid.objects[0].color.z = 2;
  rejects([&] { (void)mesh_from_snapshot(invalid); }, "color range enforced");
  invalid = scene; invalid.objects[0].emission = std::numeric_limits<float>::quiet_NaN();
  rejects([&] { (void)mesh_from_snapshot(invalid); }, "finite emission required");
  invalid = scene; invalid.objects[0].center.y = std::numeric_limits<float>::infinity();
  rejects([&] { (void)pick_scene(invalid, {0,0,0}, {0,0,1}); }, "picking validates snapshot");
  invalid = empty; invalid.objects.assign(10001, scene.objects[0]);
  rejects([&] { (void)mesh_from_snapshot(invalid); }, "box budget enforced");
  const float pi = 3.14159265358979323846f;
  const float slope = -pi/6;
  SceneSnapshot ramp{new_uuid(), 1, {{new_uuid(), "Inclined surface", {0,1,5}, {2,.2f,4}, {.3f,.5f,.7f}}}};
  ramp.objects.front().rotation = Quaternion{std::sin(slope/2),0,0,std::cos(slope/2)};
  const auto ramp_mesh = mesh_from_snapshot(ramp);
  const auto& top = ramp_mesh.vertices.at(24);
  require(std::abs(top.normal.x)<.00001f && std::abs(top.normal.y-std::cos(slope))<.00001f &&
          std::abs(top.normal.z-std::sin(slope))<.00001f, "inclined top normal rotates with its rendered surface");
  const auto down = pick_scene(ramp,{0,8,5},{0,-7,0});
  const float expected_distance=8-(1+.2f/std::cos(slope));
  require(down && down->persistent_id==ramp.objects.front().persistent_id && std::abs(down->distance-expected_distance)<.0001f,
          "inclined picking returns the owning UUID and world distance to the actual rendered top");
  for(std::size_t index=24;index<30;++index) {
   const auto& vertex=ramp_mesh.vertices.at(index);
   const auto p=vertex.position;
   const float offset=top.normal.x*(p.x-top.position.x)+top.normal.y*(p.y-top.position.y)+top.normal.z*(p.z-top.position.z);
   require(std::abs(offset)<.00001f, "inclined top triangles share the rotated normal plane");
  }
  SceneSnapshot narrow{new_uuid(),1,{{new_uuid(),"Rotated thin panel",{0,0,5},{3,1,.2f},{.4f,.5f,.6f}}}};
  narrow.objects.front().rotation={0,std::sin(pi/8),0,std::cos(pi/8)};
  require(!pick_scene(narrow,{2,4,7},{0,-1,0}), "empty corner of rotated box AABB does not falsely select");
  const auto panel=pick_scene(narrow,{2,4,3},{0,-10,0});
  require(panel && std::abs(panel->distance-3)<.0001f, "rotated thin panel still picks at its real surface");
  for(const auto rotation: {Quaternion{0,0,0,0},Quaternion{0,0,0,2},
       Quaternion{0,std::numeric_limits<float>::quiet_NaN(),0,1},
       Quaternion{std::numeric_limits<float>::infinity(),0,0,1}}) {
   auto malformed=ramp; malformed.objects.front().rotation=rotation;
   rejects([&] { (void)mesh_from_snapshot(malformed); }, "mesh rejects nonunit/nonfinite rotation");
   rejects([&] { (void)pick_scene(malformed,{0,8,5},{0,-1,0}); }, "picking rejects nonunit/nonfinite rotation");
  }
  auto almost_identity=ramp; almost_identity.objects.front().rotation={0,0,0,1.00002f};
  const auto normalized_mesh=mesh_from_snapshot(almost_identity);
  require(std::abs(normalized_mesh.vertices.at(24).normal.y-1)<.00001f, "valid small quaternion rounding error is normalized");
  const float huge=std::numeric_limits<float>::max();
  SceneSnapshot overflow{new_uuid(),1,{{new_uuid(),"Huge rotated bounds",{0,0,0},{huge*.75f,huge*.75f,1},{.4f,.5f,.6f}}}};
  overflow.objects.front().rotation={0,0,std::sin(pi/8),std::cos(pi/8)};
  rejects([&] { (void)mesh_from_snapshot(overflow); }, "transformed corners overflowing float range are rejected");
  rejects([&] { (void)pick_scene(overflow,{0,0,0},{0,0,1}); }, "picking validates transformed bounds overflow");
  overflow.objects.front().half_extent={huge*.45f,huge*.45f,1};
  overflow.objects.front().center={huge*.1f,0,0};
  for(const auto& vertex:mesh_from_snapshot(overflow).vertices)
   require(std::isfinite(vertex.position.x) && std::isfinite(vertex.position.y), "large valid transformed corners use finite double intermediates");
  std::cout << "PASS: stable scene identity, oriented meshes/normals/picking, rotation bounds and empty world\n";
  return 0;
 } catch (const std::exception& error) { std::cerr << "FAIL: " << error.what() << '\n'; return 1; }
}
