#include <aibs/engine.hpp>
#include <cmath>

namespace aibs {
unsigned FixedStep::advance(double seconds) {
 if (paused_ || !std::isfinite(seconds) || seconds < 0) return 0;
 const double incoming = accumulator_ + seconds;
 // Bound before converting to an integer; huge finite input cannot overflow.
 if (incoming >= tick_seconds * 5) {
  ++overloads_;
  accumulator_ = std::fmod(incoming, tick_seconds);
  return 4;
 }
 accumulator_ = incoming;
 unsigned ticks = 0;
 while (accumulator_ + 1e-12 >= tick_seconds && ticks < 4) {
  accumulator_ -= tick_seconds;
  ++ticks;
 }
 if (accumulator_ < 0) accumulator_ = 0;
 return ticks;
}
}
