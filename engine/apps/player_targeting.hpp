#pragma once
#include <aibs/player.hpp>
#include <cmath>

namespace aibs::app_input {
// Native app diagnostic targeting. Physical cameras orbit the configured body
// eye, so derive their look direction from that anchor before follow() relocates
// the boom. Inspection retains its detached camera origin. Existing pitch bounds,
// camera clearance, player mode and zero-dt physics semantics remain in force.
inline void aim(PlayerController& player, Vec3 target) {
 const auto camera=player.camera();
 const auto origin=player.inspection_mode()?camera.position:player.eye_anchor();
 const Vec3 offset{target.x-origin.x,target.y-origin.y,target.z-origin.z};
 WindowInput look;
 look.yaw_delta=std::atan2(offset.x,offset.z)-camera.yaw;
 look.pitch_delta=std::atan2(offset.y,std::sqrt(offset.x*offset.x+offset.z*offset.z))-camera.pitch;
 player.update(look,0);
}
}
