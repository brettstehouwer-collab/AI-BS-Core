#include <aibs/player.hpp>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace aibs {
PlayerController::PlayerController(const SceneSnapshot& scene, Vec3 spawn, CharacterSettings settings)
 : character_(scene, spawn, settings), eye_height_(settings.height * 0.9f),
   body_radius_(settings.radius), body_height_(settings.height) { follow(); }
CharacterState PlayerController::state() const { return character_.state(); }
void PlayerController::set_scene(const SceneSnapshot& scene) {
 character_.set_scene(scene);
 if (!inspection_) follow();
}
void PlayerController::reset(Vec3 feet) {
 character_.reset(feet);
 if (!inspection_) follow();
}
void PlayerController::follow() {
 const auto feet = character_.state().feet;
 const Vec3 target{feet.x, feet.y + eye_height_, feet.z};
 camera_.yaw = yaw_; camera_.pitch = pitch_;
 avatar_visible_ = false;
 if (!third_person_) { camera_.position = target; return; }
 const float cp = std::cos(pitch_);
 const Vec3 desired{target.x-std::sin(yaw_)*cp*5, target.y-std::sin(pitch_)*5, target.z-std::cos(yaw_)*cp*5};
 try { camera_.position = character_.camera_position(target, desired, 0.25f); }
 catch (const std::invalid_argument&) {
  // A tight ceiling can fit the capsule/eye while overlapping the camera
  // sphere at its anchor. Keep a valid first-person eye in that case.
  camera_.position = character_.camera_position(target, target, 0);
 }
 const auto offset=Vec3{camera_.position.x-target.x,camera_.position.y-target.y,camera_.position.z-target.z};
 const bool inside_body=std::abs(camera_.position.x-feet.x)<=body_radius_+.1f &&
  std::abs(camera_.position.z-feet.z)<=body_radius_+.1f &&
  camera_.position.y>=feet.y-.1f && camera_.position.y<=feet.y+body_height_+.1f;
 avatar_visible_=offset.x*offset.x+offset.y*offset.y+offset.z*offset.z>.6f*.6f && !inside_body;
}
void PlayerController::update(const WindowInput& input, double seconds) {
 if (!input.active) { character_.suspend(); return; }
 if (!std::isfinite(seconds) || seconds < 0) return;
 if (input.toggle_flight) inspection_ = !inspection_;
 if (input.cycle_camera) third_person_ = !third_person_;
 if (inspection_) {
  camera_.update(input, static_cast<float>(std::min(seconds, 0.25)));
  return;
 }
 if (std::isfinite(input.yaw_delta)) yaw_ = std::remainder(yaw_ + input.yaw_delta, 6.28318530718f);
 if (std::isfinite(input.pitch_delta)) pitch_ = std::clamp(pitch_ + input.pitch_delta, -1.4f, 1.4f);
 const float sy = std::sin(yaw_), cy = std::cos(yaw_);
 CharacterInput command;
 command.move = {sy*input.forward+cy*input.right, 0, cy*input.forward-sy*input.right};
 command.sprint = input.sprint; command.jump = input.jump;
 character_.advance(command, seconds);
 follow();
}
}
