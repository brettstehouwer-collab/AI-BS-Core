#pragma once
#include <aibs/player.hpp>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <ostream>
#include <stdexcept>
namespace aibs::controlled_motion {
// Rejected diagnostic inputs must stay rejected without making the failure
// report itself malformed JSON (C++ streams spell nonfinite values nan/inf).
inline void write_diagnostic_real(std::ostream& stream,double value){if(std::isfinite(value))stream<<value;else stream<<"null";}
// Private opt-in hardware diagnostic policy, never ordinary/human input.
inline bool allowed(bool performance,bool gameplay,bool managed,bool fresh,
 bool proof,bool tour,bool recording,bool offscreen) noexcept {
 return performance&&!gameplay&&managed&&fresh&&!proof&&!tour&&!recording&&!offscreen;
}
class Shuttle {
 Vec3 first_,second_;bool toward_second_=true;std::uint64_t arrivals_=0;
public:
 Shuttle(Vec3 first,Vec3 second):first_(first),second_(second){
  const auto length=std::hypot(first.x-second.x,first.z-second.z);
  if(!std::isfinite(length)||!std::isfinite(first.y)||!std::isfinite(second.y)||length<3||length>8||std::abs(first.y-second.y)>.1f)
   throw std::invalid_argument("Controlled motion requires a bounded level3..8m collision-checked shuttle");
 }
 WindowInput input(Vec3 feet,float yaw){
  auto target=toward_second_?second_:first_;
  if(std::hypot(feet.x-target.x,feet.z-target.z)<.25f){toward_second_=!toward_second_;++arrivals_;target=toward_second_?second_:first_;}
  WindowInput command;command.forward=1;
  command.yaw_delta=std::remainder(std::atan2(target.x-feet.x,target.z-feet.z)-yaw,6.28318530718f);
  return command;
 }
 std::uint64_t arrivals()const noexcept{return arrivals_;}
 Vec3 first()const noexcept{return first_;}Vec3 second()const noexcept{return second_;}
};
struct Coverage {
 enum class Invalid {none,bad_elapsed,bad_position,tick_regressed,tick_burst,dropped_physics,impossible_displacement};
 static constexpr const char* reason(Invalid value)noexcept{
  switch(value){case Invalid::none:return "none";case Invalid::bad_elapsed:return "bad_elapsed";case Invalid::bad_position:return "bad_position";case Invalid::tick_regressed:return "tick_regressed";case Invalid::tick_burst:return "tick_burst";case Invalid::dropped_physics:return "dropped_physics";case Invalid::impossible_displacement:return "impossible_displacement";}return "unknown";
 }
 double physical_seconds=0,moving_physical_seconds=0,horizontal_metres=0,commanded_wall_seconds=0;
 std::uint64_t physical_steps=0,moving_steps=0,observations=0;
 bool invalid=false;
 Invalid first_invalid=Invalid::none;std::uint64_t invalid_observations=0,first_invalid_observation=0;
 double first_invalid_elapsed=0,first_invalid_distance=0,first_dropped_before=0,first_dropped_after=0,rejected_elapsed_seconds=0;
 std::uint64_t first_ticks_before=0,first_ticks_after=0;
 void reject(Invalid why,const CharacterState& before,const CharacterState& after,double wall,double distance)noexcept{
  invalid=true;++invalid_observations;if(std::isfinite(wall)&&wall>=0)rejected_elapsed_seconds+=wall;
  if(first_invalid!=Invalid::none)return;
  first_invalid=why;first_invalid_observation=observations;first_invalid_elapsed=wall;first_invalid_distance=distance;
  first_ticks_before=before.ticks;first_ticks_after=after.ticks;first_dropped_before=before.dropped_seconds;first_dropped_after=after.dropped_seconds;
 }
 // Physics runs60Hz while Present may run much faster. Count actual tick
 // deltas, not render frames that happen to contain a displacement.
 void observe(const CharacterState& before,const CharacterState& after,double wall,bool commanded)noexcept{
  ++observations;
  const auto distance=std::hypot(double(after.feet.x)-before.feet.x,double(after.feet.z)-before.feet.z);
  if(!std::isfinite(wall)||wall<0){reject(Invalid::bad_elapsed,before,after,wall,distance);return;}
  // Declared held-command time includes rejected intervals; it is never
  // substituted for actual physical movement time or used to qualify motion.
  if(commanded)commanded_wall_seconds+=wall;
  if(!std::isfinite(distance)){reject(Invalid::bad_position,before,after,wall,distance);return;}
  if(after.ticks<before.ticks){reject(Invalid::tick_regressed,before,after,wall,distance);return;}
  if(after.ticks-before.ticks>8){reject(Invalid::tick_burst,before,after,wall,distance);return;}
  if(after.dropped_seconds>before.dropped_seconds+1e-9){reject(Invalid::dropped_physics,before,after,wall,distance);return;}
  const auto ticks=after.ticks-before.ticks;
  if(distance>double(ticks)*12./60+.03){reject(Invalid::impossible_displacement,before,after,wall,distance);return;} // Reject reset/teleport, including zero-tick motion.
  physical_steps+=ticks;physical_seconds+=double(ticks)/60.;
  if(ticks&&commanded&&before.grounded&&after.grounded&&distance>1e-5){
   moving_steps+=ticks;moving_physical_seconds+=double(ticks)/60.;horizontal_metres+=distance;
  }
 }
 bool qualifies(double wall,std::uint64_t arrivals)const noexcept{
  // This explicit coverage policy qualifies only controlled movement. Idle,
  // blocked input, a short run and elapsed wall time alone never pass.
  return !invalid&&std::isfinite(wall)&&wall>=15&&arrivals>=2&&
   physical_seconds>=wall*.95&&moving_physical_seconds>=wall*.90&&horizontal_metres>=wall*3.5;
 }
};
}
