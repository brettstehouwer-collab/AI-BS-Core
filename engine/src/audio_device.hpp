#pragma once
// Private implementation/test seam; not installed as an SDK header.
#include <aibs/audio_playback.hpp>
#include <memory>
#include <span>
namespace aibs::detail {
struct AudioDeviceState {std::uint64_t played_frames=0;std::uint32_t queued_buffers=0;std::int32_t error=0;};
class AudioDevice {
 public:
 virtual ~AudioDevice()=default;
 virtual AudioPlaybackResult start()noexcept=0;
 virtual AudioPlaybackResult pause()noexcept=0;
 virtual AudioPlaybackResult resume()noexcept=0;
 virtual AudioPlaybackResult set_volume(float)noexcept=0;
 virtual AudioDeviceState state()noexcept=0;
};
using AudioDeviceFactory=std::unique_ptr<AudioDevice>(*)(void*,std::uint32_t,std::uint32_t,
 std::span<const std::byte>,float,AudioPlaybackResult&)noexcept;
std::unique_ptr<AudioDevice> make_xaudio2_device(void*,std::uint32_t,std::uint32_t,
 std::span<const std::byte>,float,AudioPlaybackResult&)noexcept;
struct AudioPlaybackTestAccess {
 static std::unique_ptr<AudioPlayback> make(AudioDeviceFactory,void* context);
};
}
