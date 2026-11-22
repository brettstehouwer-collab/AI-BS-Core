#pragma once
#include <aibs/audio_assets.hpp>
#include <cstddef>
#include <cstdint>
#include <memory>

namespace aibs {
inline constexpr std::size_t audio_playback_maximum_pcm_bytes=48u*1024u*1024u;
inline constexpr std::size_t audio_playback_maximum_replacement_pcm_bytes=96u*1024u*1024u;
enum class AudioPlaybackState : std::uint8_t {stopped,playing,paused,completed,failed,closed};
enum class AudioPlaybackError : std::uint8_t {
 none,wrong_thread,invalid_asset,invalid_volume,invalid_state,out_of_memory,
 device_unavailable,backend_failure,closed
};
struct AudioPlaybackResult {
 AudioPlaybackError error=AudioPlaybackError::none;
 std::int32_t native_code=0;
 explicit operator bool()const noexcept{return error==AudioPlaybackError::none;}
};
struct AudioPlaybackSnapshot {
 AudioPlaybackState state=AudioPlaybackState::stopped;
 AudioPlaybackError error=AudioPlaybackError::none;
 std::int32_t native_code=0;
 std::uint64_t played_frames=0,total_frames=0,generation=0;
 std::uint32_t sample_rate=0,channels=0;
 float volume=1;
 std::size_t owned_pcm_bytes=0,peak_owned_pcm_bytes=0;
 bool source_voice=false;
 double position_seconds()const noexcept{return sample_rate?static_cast<double>(played_frames)/sample_rate:0;}
 double duration_seconds()const noexcept{return sample_rate?static_cast<double>(total_frames)/sample_rate:0;}
};
namespace detail {struct AudioPlaybackTestAccess;}

// Windows PC default-output playback. Construct, operate and destroy on one
// owner thread. No hardware is opened until play. Every operation after
// construction returns bounded data rather than throwing on input/device errors.
// Source-rate interleaved PCM16LE is copied and charged independently from the
// immutable asset; caller data can be destroyed immediately after play returns.
class AudioPlayback {
 public:
 AudioPlayback();
 ~AudioPlayback();
 AudioPlayback(const AudioPlayback&)=delete;
 AudioPlayback& operator=(const AudioPlayback&)=delete;
 AudioPlayback(AudioPlayback&&)=delete;
 AudioPlayback& operator=(AudioPlayback&&)=delete;
 AudioPlaybackResult play(const AudioAsset&)noexcept;
 AudioPlaybackResult play(const AudioAsset&,float volume)noexcept;
 AudioPlaybackResult pause()noexcept;
 AudioPlaybackResult resume()noexcept;
 AudioPlaybackResult stop()noexcept;
 AudioPlaybackResult close()noexcept;
 AudioPlaybackResult set_volume(float)noexcept;
 AudioPlaybackSnapshot snapshot()noexcept;
 private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
 friend struct detail::AudioPlaybackTestAccess;
};
}
