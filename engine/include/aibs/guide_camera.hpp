#pragma once
#include <aibs/render.hpp>
#include <cmath>

namespace aibs {
// Visual clearance for a human-sized memory guide. This never moves a guide,
// changes Follow/Wait/Recall, modifies animation, or writes gameplay history.
struct GuideCameraClearance {
 float body_bottom=-.1f,body_top=2.f;
 float hidden_distance=.35f,visible_distance=.9f;
};
// Smooth opacity multiplier around the rendered guide's vertical body segment.
// Full appearance is retained outside visible_distance; the draw is omitted
// inside hidden_distance. Invalid presentation inputs return zero visibility.
// The caller must not persist this camera-dependent value or rebuild geometry.
inline float guide_camera_visibility(Vec3 eye,Vec3 feet,GuideCameraClearance c={})noexcept{
 const auto finite=[](Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);};
 if(!finite(eye)||!finite(feet)||!std::isfinite(c.body_bottom)||!std::isfinite(c.body_top)||
    !std::isfinite(c.hidden_distance)||!std::isfinite(c.visible_distance)||
    c.body_top<=c.body_bottom||c.hidden_distance<0||c.visible_distance<=c.hidden_distance)return 0;
 const double low=static_cast<double>(feet.y)+c.body_bottom,high=static_cast<double>(feet.y)+c.body_top;
 const double dy=eye.y<low?low-eye.y:eye.y>high?eye.y-high:0;
 const double distance=std::hypot(static_cast<double>(eye.x)-feet.x,dy,static_cast<double>(eye.z)-feet.z);
 if(distance<=c.hidden_distance)return 0;if(distance>=c.visible_distance)return 1;
 const double t=(distance-c.hidden_distance)/(c.visible_distance-c.hidden_distance);
 return static_cast<float>(t*t*(3-2*t));
}
}
