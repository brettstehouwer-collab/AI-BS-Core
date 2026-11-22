#include <aibs/frame_measurement.hpp>
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace aibs {namespace {
FrameMeasurementConfig checked(FrameMeasurementConfig c){
 const bool gameplay=c.profile==FrameMeasurementProfile::gameplay;
 if(c.width<320||c.width>7680||c.height<200||c.height>4320||
    !std::isfinite(c.warmup_seconds)||c.warmup_seconds<2||c.warmup_seconds>30||
    !std::isfinite(c.measure_seconds)||c.measure_seconds<15||c.measure_seconds>(gameplay?900:120)||
    c.maximum_samples==0||c.maximum_samples>(gameplay?480000u:120000u)||
    (c.profile!=FrameMeasurementProfile::stationary&&!gameplay))
  throw std::invalid_argument("Frame measurement configuration exceeds bounded diagnostic limits");
 return c;
}
}}
namespace aibs {
std::string_view frame_measurement_error_name(FrameMeasurementError error)noexcept{
 switch(error){case FrameMeasurementError::none:return "none";case FrameMeasurementError::clock_not_advanced:return "clock_not_advanced";case FrameMeasurementError::present_counter_mismatch:return "present_counter_mismatch";case FrameMeasurementError::client_dimensions_changed:return "client_dimensions_changed";case FrameMeasurementError::inactive:return "inactive";case FrameMeasurementError::memory_unavailable:return "memory_unavailable";case FrameMeasurementError::sample_capacity:return "sample_capacity";}return "unknown";
}
FrameMeasurement::FrameMeasurement(FrameMeasurementConfig c,Clock::time_point now,const FrameObservation& observation)
 :config_(checked(c)),samples_(std::make_unique<double[]>(config_.maximum_samples)),sorted_(std::make_unique<double[]>(config_.maximum_samples)),
 beginning_(now),previous_(now),measurement_start_(now),previous_observation_(observation),start_observation_(observation){
 if(observation.width!=config_.width||observation.height!=config_.height||!observation.active||!observation.memory_valid)
  throw std::invalid_argument("Frame measurement requires actual requested client dimensions, active rendering and valid process memory sample");
}
void FrameMeasurement::fail(FrameMeasurementError error)noexcept{state_=FrameMeasurementState::failed;error_=error;}
std::size_t FrameMeasurement::instrumentation_bytes()const noexcept{return sizeof(*this)+2*config_.maximum_samples*sizeof(double);}
bool FrameMeasurement::finish_gameplay()noexcept{
 if(config_.profile!=FrameMeasurementProfile::gameplay)return false;
 if(state_==FrameMeasurementState::complete)return true;
 if(state_!=FrameMeasurementState::measuring||count_==0||std::chrono::duration<double>(previous_-measurement_start_).count()<15)return false;
 state_=FrameMeasurementState::complete;return true;
}
void FrameMeasurement::observe(Clock::time_point now,const FrameObservation& observation)noexcept{
 if(state_==FrameMeasurementState::failed||state_==FrameMeasurementState::complete)return;
 if(now<=previous_){fail(FrameMeasurementError::clock_not_advanced);return;}
 if(observation.width!=config_.width||observation.height!=config_.height){fail(FrameMeasurementError::client_dimensions_changed);return;}
 if(!observation.active){fail(FrameMeasurementError::inactive);return;}
 if(!observation.memory_valid){fail(FrameMeasurementError::memory_unavailable);return;}
 if(previous_observation_.presented_frames==std::numeric_limits<std::uint64_t>::max()||observation.presented_frames!=previous_observation_.presented_frames+1){fail(FrameMeasurementError::present_counter_mismatch);return;}
 if(state_==FrameMeasurementState::warmup){
  if(std::chrono::duration<double>(now-beginning_).count()>=config_.warmup_seconds){
   state_=FrameMeasurementState::measuring;measurement_start_=now;start_observation_=observation;
   private_peak_=observation.private_bytes;working_peak_=observation.working_set_bytes;gpu_peak_=observation.gpu_content_bytes;
  }
 }else{
  if(count_>=config_.maximum_samples){fail(FrameMeasurementError::sample_capacity);return;}
  samples_[count_++]=std::chrono::duration<double,std::milli>(now-previous_).count();
  private_peak_=std::max(private_peak_,observation.private_bytes);working_peak_=std::max(working_peak_,observation.working_set_bytes);gpu_peak_=std::max(gpu_peak_,observation.gpu_content_bytes);
  if(std::chrono::duration<double>(now-measurement_start_).count()>=config_.measure_seconds)state_=FrameMeasurementState::complete;
 }
 previous_=now;previous_observation_=observation;
}
std::optional<FrameMeasurementSummary> FrameMeasurement::summary()const{
 if(state_!=FrameMeasurementState::complete||count_==0)return {};
 std::copy_n(samples_.get(),count_,sorted_.get());std::sort(sorted_.get(),sorted_.get()+count_);
 const auto quantile=[&](double percentile){const auto rank=static_cast<std::size_t>(std::ceil(percentile*static_cast<double>(count_)));return sorted_[std::max(std::size_t{1},rank)-1];};
 FrameMeasurementSummary out;out.frame_count=count_;out.presented_frame_delta=previous_observation_.presented_frames-start_observation_.presented_frames;
 out.width=previous_observation_.width;out.height=previous_observation_.height;out.wall_seconds=std::chrono::duration<double>(previous_-measurement_start_).count();
 out.frames_per_second=static_cast<double>(count_)/out.wall_seconds;out.mean_ms=out.wall_seconds*1000/static_cast<double>(count_);out.p50_ms=quantile(.5);out.p95_ms=quantile(.95);out.p99_ms=quantile(.99);
 out.private_start=start_observation_.private_bytes;out.private_end=previous_observation_.private_bytes;out.private_peak_sampled=private_peak_;
 out.working_set_start=start_observation_.working_set_bytes;out.working_set_end=previous_observation_.working_set_bytes;out.working_set_peak_sampled=working_peak_;out.working_set_peak_lifetime=previous_observation_.working_set_peak_lifetime;
 out.gpu_content_start=start_observation_.gpu_content_bytes;out.gpu_content_end=previous_observation_.gpu_content_bytes;out.gpu_content_peak_sampled=gpu_peak_;out.instrumentation_bytes=instrumentation_bytes();
 for(std::size_t i=0;i<count_;++i){out.frames_over_16_67ms+=samples_[i]>16.67?1:0;out.frames_over_33_33ms+=samples_[i]>33.33?1:0;out.frames_over_50ms+=samples_[i]>50?1:0;}
 return out;
}
}
