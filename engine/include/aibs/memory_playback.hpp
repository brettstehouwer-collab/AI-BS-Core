#pragma once
#include <aibs/audio_playback.hpp>
#include <array>
#include <memory>
#include <optional>
#include <string_view>
namespace aibs {
inline constexpr std::size_t memory_playback_maximum_resident_bytes=128u*1024u*1024u;
enum class MemoryPlaybackError:std::uint8_t {none,wrong_thread,invalid_station,invalid_asset,
 out_of_memory,budget_exceeded,unbound,game_paused,playback_failure,closed};
struct MemoryPlaybackResult {
 MemoryPlaybackError error=MemoryPlaybackError::none;
 AudioPlaybackResult audio;
 explicit operator bool()const noexcept{return error==MemoryPlaybackError::none;}
};
// Pure source-frame lookup on an already validated immutable asset. Draft cues
// are withheld unless explicitly requested. This does not approve captions.
std::optional<std::size_t> memory_caption_index(const AudioAsset&,std::uint64_t source_frame,
 bool allow_draft_preview=false)noexcept;
struct MemoryPlaybackSnapshot {
 std::shared_ptr<const AudioAsset> asset;
 std::array<char,37> station_uuid{};
 AudioPlaybackSnapshot playback;
 MemoryPlaybackError error=MemoryPlaybackError::none;
 AudioPlaybackResult audio_error;
 std::optional<std::size_t> caption_index;
 bool game_paused=false,resume_on_game_resume=false,review_pending=false,allow_draft_preview=false;
 std::size_t source_decoded_bytes=0,other_chapter_residency_bytes=0,resident_bytes=0,reserved_peak_bytes=0;
 std::string_view station_id()const noexcept{return {station_uuid.data(),station_uuid[0]?36u:0u};}
};
namespace detail {struct MemoryPlaybackTestAccess;}
class MemoryPlaybackSession {
 public:
 MemoryPlaybackSession();
 ~MemoryPlaybackSession();
 MemoryPlaybackSession(const MemoryPlaybackSession&)=delete;
 MemoryPlaybackSession& operator=(const MemoryPlaybackSession&)=delete;
 MemoryPlaybackSession(MemoryPlaybackSession&&)=delete;
 MemoryPlaybackSession& operator=(MemoryPlaybackSession&&)=delete;
 // During bind, other excludes BOTH current/candidate AudioAssets and this
 // session's PCM. Before Play/Resume it excludes the selected asset and PCM.
 MemoryPlaybackResult bind(std::string_view station_uuid,std::shared_ptr<const AudioAsset>,
  std::size_t other_chapter_residency_bytes,bool allow_draft_preview=false)noexcept;
 MemoryPlaybackResult play_or_resume(std::size_t other_chapter_residency_bytes)noexcept;
 MemoryPlaybackResult pause()noexcept;
 MemoryPlaybackResult stop()noexcept;
 MemoryPlaybackResult set_game_paused(bool,std::size_t other_chapter_residency_bytes)noexcept;
 MemoryPlaybackResult set_volume(float)noexcept;
 MemoryPlaybackResult close()noexcept;
 MemoryPlaybackSnapshot snapshot()noexcept;
 private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
 friend struct detail::MemoryPlaybackTestAccess;
};
}
