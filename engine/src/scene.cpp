#include <aibs/scene.hpp>
#include <aibs/engine.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <set>
#include <stdexcept>

namespace aibs {
namespace {
bool finite(Vec3 value) { return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z); }
bool unit(float value) { return std::isfinite(value) && value >= 0 && value <= 1; }
using Coordinates = std::array<double, 3>;
using Rotation = std::array<Coordinates, 3>;
constexpr Vec3 corners[] = {{-1,-1,-1},{1,-1,-1},{1,1,-1},{-1,1,-1},{-1,-1,1},{1,-1,1},{1,1,1},{-1,1,1}};
Rotation rotation_matrix(Quaternion quaternion) {
 const double x=quaternion.x, y=quaternion.y, z=quaternion.z, w=quaternion.w;
 const double squared=x*x+y*y+z*z+w*w;
 if (!std::isfinite(squared) || std::abs(squared-1)>1e-4)
  throw std::invalid_argument("Scene rotation requires a finite unit quaternion");
 // Normalize accepted serialization/rounding error, rather than introducing
 // scale into render geometry, inverse picking or the matching physics shape.
 const double scale=2/squared;
 return {{{1-scale*(y*y+z*z),scale*(x*y-z*w),scale*(x*z+y*w)},
          {scale*(x*y+z*w),1-scale*(x*x+z*z),scale*(y*z-x*w)},
          {scale*(x*z-y*w),scale*(y*z+x*w),1-scale*(x*x+y*y)}}};
}
Coordinates rotate(const Rotation& rotation, Coordinates value) {
 Coordinates result{};
 for(std::size_t row=0;row<3;++row)
  for(std::size_t column=0;column<3;++column) result[row]+=rotation[row][column]*value[column];
 return result;
}
Coordinates inverse_rotate(const Rotation& rotation, Coordinates value) {
 Coordinates result{};
 for(std::size_t row=0;row<3;++row)
  for(std::size_t column=0;column<3;++column) result[row]+=rotation[column][row]*value[column];
 return result;
}
void validate(const SceneSnapshot& snapshot) {
 if (!is_uuid(snapshot.world_id)) throw std::invalid_argument("Scene requires a persistent world UUID");
 if (snapshot.objects.size() > 10000) throw std::invalid_argument("Scene exceeds 10000 boxes");
 for (const auto& object : snapshot.objects) {
  if (!is_uuid(object.persistent_id) || object.name.size() > 4096) throw std::invalid_argument("Invalid scene object identity/name");
  if (!finite(object.center) || !finite(object.half_extent) || object.half_extent.x <= 0 || object.half_extent.y <= 0 || object.half_extent.z <= 0)
   throw std::invalid_argument("Scene object requires finite positive bounds");
  if (!unit(object.color.x) || !unit(object.color.y) || !unit(object.color.z) || !unit(object.emission))
   throw std::invalid_argument("Scene color/emission must be finite and normalized");
  const auto rotation=rotation_matrix(object.rotation);
  const Coordinates center{object.center.x,object.center.y,object.center.z};
  for(const auto corner:corners) {
   const auto offset=rotate(rotation,{static_cast<double>(corner.x)*object.half_extent.x,
                                    static_cast<double>(corner.y)*object.half_extent.y,
                                    static_cast<double>(corner.z)*object.half_extent.z});
   for(std::size_t axis=0;axis<3;++axis) {
    if(std::abs(center[axis]+offset[axis])>std::numeric_limits<float>::max())
     throw std::invalid_argument("Transformed scene bounds overflow float coordinates");
   }
  }
 }
}
void append_box(SceneMesh& mesh, const SceneObject& object) {
 constexpr unsigned faces[6][4] = {{0,3,2,1},{4,5,6,7},{0,4,7,3},{1,2,6,5},{3,7,6,2},{0,1,5,4}};
 constexpr Vec3 normals[] = {{0,0,-1},{0,0,1},{-1,0,0},{1,0,0},{0,1,0},{0,-1,0}};
 constexpr unsigned triangles[] = {0,1,2,0,2,3};
 const auto rotation=rotation_matrix(object.rotation);
 for (unsigned face = 0; face < 6; ++face) {
  const auto normal=rotate(rotation,{normals[face].x,normals[face].y,normals[face].z});
  for (const auto triangle : triangles) {
   const auto unit_corner = corners[faces[face][triangle]];
   const auto offset=rotate(rotation,{static_cast<double>(unit_corner.x)*object.half_extent.x,
                                    static_cast<double>(unit_corner.y)*object.half_extent.y,
                                    static_cast<double>(unit_corner.z)*object.half_extent.z});
   const Vec3 point{static_cast<float>(object.center.x+offset[0]),
                    static_cast<float>(object.center.y+offset[1]),
                    static_cast<float>(object.center.z+offset[2])};
   mesh.vertices.push_back({point, {static_cast<float>(normal[0]),static_cast<float>(normal[1]),static_cast<float>(normal[2])}, object.color, object.emission});
  }
 }
}
}

SceneMesh mesh_from_snapshot(const SceneSnapshot& snapshot) {
 validate(snapshot);
 SceneMesh mesh;
 mesh.vertices.reserve(snapshot.objects.size() * 36);
 std::set<std::string> named;
 for (const auto& object : snapshot.objects) {
  append_box(mesh, object);
  if (named.insert(object.persistent_id).second) mesh.landmarks.push_back(object.name.empty() ? object.persistent_id : object.name);
 }
 return mesh;
}

std::optional<SceneHit> pick_scene(const SceneSnapshot& snapshot, Vec3 origin, Vec3 direction, float max_distance) {
 validate(snapshot);
 if (!finite(origin) || !finite(direction) || !std::isfinite(max_distance) || max_distance < 0)
  throw std::invalid_argument("Pick ray and range must be finite with nonnegative range");
 const double length = std::sqrt(static_cast<double>(direction.x) * direction.x + static_cast<double>(direction.y) * direction.y + static_cast<double>(direction.z) * direction.z);
 if (length == 0) throw std::invalid_argument("Pick direction cannot be zero");
 const Coordinates direction_unit{direction.x/length,direction.y/length,direction.z/length};
 std::optional<SceneHit> hit;
 double closest = max_distance;
 for (const auto& object : snapshot.objects) {
  if (!object.selectable) continue;
  const auto rotation=rotation_matrix(object.rotation);
  const auto start=inverse_rotate(rotation,{static_cast<double>(origin.x)-object.center.x,
                                            static_cast<double>(origin.y)-object.center.y,
                                            static_cast<double>(origin.z)-object.center.z});
  const auto ray=inverse_rotate(rotation,direction_unit);
  const std::array<double, 3> extent{object.half_extent.x, object.half_extent.y, object.half_extent.z};
  double entering = 0, leaving = closest;
  bool intersects = true;
  for (std::size_t axis = 0; axis < 3; ++axis) {
   const double minimum = -extent[axis], maximum = extent[axis];
   if (ray[axis] == 0) {
    if (start[axis] < minimum || start[axis] > maximum) { intersects = false; break; }
   } else {
    double first = (minimum - start[axis]) / ray[axis], second = (maximum - start[axis]) / ray[axis];
    if (first > second) std::swap(first, second);
    entering = std::max(entering, first); leaving = std::min(leaving, second);
    if (entering > leaving) { intersects = false; break; }
   }
  }
  if (intersects && (!hit || entering < closest)) {
   closest = entering;
   hit = SceneHit{object.persistent_id, static_cast<float>(entering)};
  }
 }
 return hit;
}
}
