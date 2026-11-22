#pragma once
#include <aibs/render.hpp>
#include <optional>

namespace aibs {
// Local-to-world unit quaternion. Small serialization rounding errors in the
// squared norm (<=1e-4) are normalized before use; other rotations are invalid.
struct Quaternion { float x = 0, y = 0, z = 0, w = 1; };
struct SceneObject {
 std::string persistent_id;
 std::string name;
 Vec3 center;
 Vec3 half_extent;
 Vec3 color;
 float emission = 0;
 bool selectable = true;
 Quaternion rotation{};
};
struct SceneSnapshot {
 std::string world_id;
 std::uint64_t revision = 0;
 std::vector<SceneObject> objects;
};
struct SceneHit { std::string persistent_id; float distance; };
// Boxes sharing a UUID are parts of the same persistent object. Snapshot and
// mesh extraction are value copies and cannot mutate the authoritative world.
SceneMesh mesh_from_snapshot(const SceneSnapshot& snapshot);
// Distance is measured in world units irrespective of the supplied ray length.
// Only selectable oriented boxes participate. Physics uses the same transform
// for collision/occlusion, independently of the selection flag.
std::optional<SceneHit> pick_scene(const SceneSnapshot& snapshot, Vec3 origin, Vec3 direction, float max_distance = 200);
}
