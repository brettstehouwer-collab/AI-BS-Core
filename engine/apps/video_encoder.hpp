#pragma once
#include <aibs/render.hpp>
#include <chrono>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>
namespace aibs::recording {
enum class EncoderMode { software,h264_nvenc,automatic };
struct FrameTimestamp {
 std::uint64_t present_id=0;
 double capture_seconds=0,write_complete_seconds=0;
 bool stop_repeat=false;
};
struct RecordingReport {
 bool started=false,finished=false,failed=false,quarantined=false;
 bool hardware_probe_attempted=false,hardware_probe_passed=false;
 std::uint32_t hardware_probe_exit_code=0;
 std::uint32_t width=0,height=0,target_fps=30,encoder_exit_code=0;
 std::uint64_t frames_received=0,frames_written=0,dropped_for_rate=0,missed_capture_slots=0,backpressure_events=0,repeated_at_stop=0;
 // Historical peak and current retained capacity are distinguished at Stop.
 std::size_t encoder_frame_capacity=0,encoder_frame_capacity_active=0,producer_frame_capacity_peak=0,timestamp_capacity_bytes=0;
 // External ffmpeg process overhead is separate from the owned frame pool.
 std::uint64_t encoder_peak_working_set_bytes=0,encoder_sampled_private_bytes_peak=0;
 double wall_seconds=0,first_frame_seconds=0,last_frame_seconds=0,maximum_write_seconds=0,total_write_seconds=0,hardware_probe_seconds=0;
 // VFR media duration follows elapsed pipe-consumption time. No audio input.
 std::string requested_encoder="software",fallback_reason,hardware_probe_stderr;
 std::string encoder="libx264",timing="ffmpeg-wallclock-vfr-1ms",error,encoder_stderr;
 std::vector<FrameTimestamp> timestamps;
};
class VideoEncoder {
public:
 VideoEncoder();~VideoEncoder();
 VideoEncoder(const VideoEncoder&)=delete;VideoEncoder& operator=(const VideoEncoder&)=delete;
 // Explicit trusted local executable; absolute new .mp4 in existing local folder.
 // Opaque BGRA, even dimensions, <=32MiB. Existing output is never overwritten.
 // Auto uses a real one-frame NVENC preflight (<=3.2s), otherwise reports a
 // software fallback. Explicit hardware mode fails if that preflight fails.
 bool begin(const std::filesystem::path& executable,const std::filesystem::path& new_mp4,
            std::uint32_t width,std::uint32_t height,std::uint32_t fps=30,
            EncoderMode mode=EncoderMode::software) noexcept;
 // False can mean a deliberate rate drop (active remains true) or failure.
 // Only one internal reusable BGRA slot; caller retains the other. No queue.
 bool submit(const CapturedFrame&,std::chrono::steady_clock::time_point) noexcept;
 // EOF/exit bounded by deadline (1..10000ms), plus <=200ms cancellation. Idempotent; failed
 // encoders preserve gameplay. Destructor uses a bounded 250ms emergency stop.
 bool finish(std::chrono::milliseconds deadline=std::chrono::milliseconds(5000)) noexcept;
 bool active() const noexcept;
 const RecordingReport& report() const noexcept;
private:struct Impl;std::unique_ptr<Impl> impl_;
};
}

