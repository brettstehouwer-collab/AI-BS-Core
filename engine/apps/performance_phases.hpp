#pragma once
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <string_view>
namespace aibs::performance_phases {
using Clock=std::chrono::steady_clock;
enum class Phase:std::size_t {loop_gap,command,window_poll,owner_input,physics_gameplay,guide_memory,hud,render,tail_close,stats_memory,sampler,count};
constexpr auto count=static_cast<std::size_t>(Phase::count);
constexpr std::array<std::string_view,count> names{{"loop_gap","command","window_poll","owner_input","physics_gameplay","guide_memory","hud","render","tail_close","stats_memory","sampler"}};
using Durations=std::array<double,count>;
constexpr std::size_t at(Phase p)noexcept{return static_cast<std::size_t>(p);}
struct FrameStages {Clock::time_point started{};std::array<Clock::time_point,count> ends{};Durations seconds{};};
class Marks {
 bool enabled_;Clock::time_point previous_{};FrameStages stages_;
public:
 explicit Marks(bool enabled):enabled_(enabled){if(enabled_){stages_.started=Clock::now();previous_=stages_.started;}}
 void mark(Phase phase)noexcept{if(!enabled_)return;const auto now=Clock::now();const auto index=at(phase);stages_.seconds[index]+=std::chrono::duration<double>(now-previous_).count();stages_.ends[index]=now;previous_=now;}
 const FrameStages& stages()const noexcept{return stages_;}
};
struct Sample {
 std::uint64_t frame_index=0;bool measuring=false;
 bool frame_completed=false,observation_completed=false,foreground_active=false,memory_valid=false;
 double loop_started_seconds=0,frame_started_seconds=0,frame_finished_seconds=0,observation_finished_seconds=0,sampler_finished_seconds=0;
 Durations seconds{},phase_ended_seconds{};
 double maximum()const noexcept{return *std::max_element(seconds.begin(),seconds.end());}
 bool valid()const noexcept{
  for(const auto value:seconds)if(!std::isfinite(value)||value<0)return false;
  for(const auto value:phase_ended_seconds)if(!std::isfinite(value)||value<0)return false;
  return std::isfinite(loop_started_seconds)&&std::isfinite(frame_started_seconds)&&std::isfinite(frame_finished_seconds)&&std::isfinite(observation_finished_seconds)&&std::isfinite(sampler_finished_seconds);
 }
};
struct Context {Sample current{},preceding{};bool have_preceding=false;};
// All storage is fixed. No allocation, output or renderer/stat query occurs
// in observe(). Preserve both sides of a stall: elapsed is sampled at frame
// START, while the Present observation follows frame/queries. Frame N's stall
// can therefore produce frame N+1's dropped physics interval.
class Collector {
public:
 static constexpr std::size_t capacity=16;static constexpr double outlier_seconds=.05;
 std::array<Context,capacity> outliers{};std::size_t retained=0;
 Durations maxima{};std::uint64_t observations=0,outlier_count=0,invalid_samples=0;
 Context first_motion_fault{};bool have_motion_fault=false;
private:
 Sample previous_{};bool have_previous_=false;
public:
 void observe(const Sample& sample,bool first_motion_fault_now=false)noexcept{
  ++observations;if(!sample.valid()){++invalid_samples;return;}
  const Context context{sample,previous_,have_previous_};
  if(first_motion_fault_now&&!have_motion_fault){first_motion_fault=context;have_motion_fault=true;}
  for(std::size_t n=0;n<count;++n)maxima[n]=std::max(maxima[n],sample.seconds[n]);
  if(sample.maximum()>=outlier_seconds){
   ++outlier_count;
   if(retained<capacity)outliers[retained++]=context;
   else {std::size_t smallest=0;for(std::size_t n=1;n<capacity;++n)if(outliers[n].current.maximum()<outliers[smallest].current.maximum())smallest=n;
    if(sample.maximum()>outliers[smallest].current.maximum())outliers[smallest]=context;}
  }
  previous_=sample;have_previous_=true;
 }
};
struct ScopedSample {
 Collector* collector;Sample& sample;bool first_motion_fault=false;
 ~ScopedSample(){if(collector)collector->observe(sample,first_motion_fault);}
};
}
