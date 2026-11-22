#pragma once
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string_view>
namespace aibs {
enum class FrameMeasurementProfile {stationary,gameplay};
struct FrameMeasurementConfig {
 std::uint32_t width=1920,height=1080;
 double warmup_seconds=2,measure_seconds=15;
 std::size_t maximum_samples=120000;
 FrameMeasurementProfile profile=FrameMeasurementProfile::stationary;
};
struct FrameObservation {
 std::uint64_t presented_frames=0;
 std::uint32_t width=0,height=0;
 bool active=false,memory_valid=false;
 std::uint64_t private_bytes=0,working_set_bytes=0,working_set_peak_lifetime=0,gpu_content_bytes=0;
};
enum class FrameMeasurementState {warmup,measuring,complete,failed};
enum class FrameMeasurementError {none,clock_not_advanced,present_counter_mismatch,client_dimensions_changed,inactive,memory_unavailable,sample_capacity};
std::string_view frame_measurement_error_name(FrameMeasurementError)noexcept;
struct FrameMeasurementSummary {
 std::uint64_t frame_count=0,presented_frame_delta=0;
 std::uint32_t width=0,height=0;
 double wall_seconds=0,frames_per_second=0,mean_ms=0,p50_ms=0,p95_ms=0,p99_ms=0;
 std::uint64_t private_start=0,private_end=0,private_peak_sampled=0;
 std::uint64_t working_set_start=0,working_set_end=0,working_set_peak_sampled=0,working_set_peak_lifetime=0;
 std::uint64_t gpu_content_start=0,gpu_content_end=0,gpu_content_peak_sampled=0;
 std::size_t instrumentation_bytes=0;
 std::uint64_t frames_over_16_67ms=0,frames_over_33_33ms=0,frames_over_50ms=0;
};
// Single-owner optional diagnostics. The app supplies actual steady_clock
// endpoints and successful renderer Present counters, never simulation ticks.
// Quantiles use nearest rank. Two fixed-capacity owned buffers are allocated
// once; observe() does not allocate. Caller reports this instrumentation apart
// from active game content, and reports scene-GPU accounting exclusions.
class FrameMeasurement {
public:
 using Clock=std::chrono::steady_clock;
 FrameMeasurement(FrameMeasurementConfig,Clock::time_point,const FrameObservation&);
 void observe(Clock::time_point,const FrameObservation&)noexcept;
 // Gameplay may end on normal player close after >=15 measured seconds.
 // Uses the last observed Present endpoint; never fabricates a terminal frame.
 // Stationary captures and failed/incomplete captures cannot be promoted here.
 bool finish_gameplay()noexcept;
 FrameMeasurementState state()const noexcept{return state_;}
 FrameMeasurementError error()const noexcept{return error_;}
 std::optional<FrameMeasurementSummary> summary()const;
 std::size_t instrumentation_bytes()const noexcept;
private:
 FrameMeasurementConfig config_;
 std::unique_ptr<double[]> samples_,sorted_;
 Clock::time_point beginning_,previous_,measurement_start_;
 FrameObservation previous_observation_,start_observation_;
 std::size_t count_=0;
 std::uint64_t private_peak_=0,working_peak_=0,gpu_peak_=0;
 FrameMeasurementState state_=FrameMeasurementState::warmup;
 FrameMeasurementError error_=FrameMeasurementError::none;
 void fail(FrameMeasurementError)noexcept;
};
}
