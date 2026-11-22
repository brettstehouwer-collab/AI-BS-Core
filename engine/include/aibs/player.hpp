#pragma once
#include <aibs/physics.hpp>

namespace aibs {
// Transient local player state. World edits still use CreatorSession; walking,
// looking and camera changes never grow the durable authoring journal.
class PlayerController {
public:
 PlayerController(const SceneSnapshot& scene, Vec3 spawn, CharacterSettings settings = {});
 void update(const WindowInput& input, double seconds);
 void set_scene(const SceneSnapshot& scene);
 void reset(Vec3 feet);
 const Camera& camera() const noexcept { return camera_; }
 CharacterState state() const;
 // Physical eye anchor derived from the configured body height. This remains
 // body-relative in orbit and inspection modes; querying it advances no state.
 Vec3 eye_anchor() const { const auto feet=state().feet; return {feet.x,feet.y+eye_height_,feet.z}; }
 bool third_person() const noexcept { return third_person_; }
 bool inspection_mode() const noexcept { return inspection_; }
 // The preferred camera mode can remain third person in a tight passage, but
 // its proxy is hidden when the camera retracts too close to the eye anchor
 // or inside conservative bounds around the configured body.
 bool avatar_visible() const noexcept { return third_person_ && !inspection_ && avatar_visible_; }
private:
 void follow();
 GroundedCharacter character_;
 Camera camera_;
 float yaw_ = 0, pitch_ = -0.12f;
 float eye_height_ = 1.62f;
 float body_radius_ = .35f, body_height_ = 1.8f;
 bool third_person_ = false, inspection_ = false;
 bool avatar_visible_ = false;
};
}
