#pragma once
#include <aibs/scene.hpp>

namespace aibs {
struct CharacterSettings {
 float radius = .35f, height = 1.8f;
 float walk_speed = 7, sprint_speed = 12, jump_speed = 6, gravity = 18;
 float step_height = .4f, max_slope_degrees = 45;
};
struct CharacterInput {
 Vec3 move; // World X/Z direction; length is clamped to one. Y is ignored.
 bool sprint = false, jump = false;
};
struct CharacterState {
 Vec3 feet, velocity;
 bool grounded = false;
 std::uint64_t ticks = 0;
 double dropped_seconds = 0;
};
// Single-owner static-box world and capsule controller. Jolt types remain private.
// SI units, +Y up. All scene boxes collide, independently of selection flags.
// Static box orientation matches the normalized SceneObject quaternion. This
// slice has no dynamic rigid bodies, animated collision shapes or vehicles.
class GroundedCharacter {
public:
 GroundedCharacter(const SceneSnapshot& scene, Vec3 spawn, CharacterSettings settings = {});
 ~GroundedCharacter();
 GroundedCharacter(const GroundedCharacter&) = delete;
 GroundedCharacter& operator=(const GroundedCharacter&) = delete;
 GroundedCharacter(GroundedCharacter&&) noexcept;
 GroundedCharacter& operator=(GroundedCharacter&&) noexcept;
 // Internal 60Hz ticks; at most eight per call. Excess time is explicitly counted.
 // Jump is edge-triggered and retained until the next tick. Inactive windows
 // should skip this call and discard their frame elapsed time.
 CharacterState advance(CharacterInput input, double elapsed);
 CharacterState state() const;
 // Focus loss clears partial tick time and pending controls, retaining pose and
 // velocity so resuming mid-jump continues from the same physical state.
 void suspend() noexcept;
 // Clears velocity and clock backlog; embedded/nonfinite positions are rejected.
 void reset(Vec3 feet);
 // Stage a complete replacement; reject overlap with the occupied capsule.
 // Failure preserves collision geometry, pose, velocity, clock and jump state.
 void set_scene(const SceneSnapshot& scene);
 // Sweep a camera sphere from target to desired, with padding as its radius.
 // Zero radius uses a solid ray. Stops 1cm before the nearest collision.
 // An occupied target is rejected; desired may be occupied. This includes zero
 // length booms. Radius is limited to 10m, coordinates to +/-1,000,000m.
 Vec3 camera_position(Vec3 target, Vec3 desired, float padding = .2f) const;
private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
};
}
