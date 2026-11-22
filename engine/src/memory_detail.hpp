#pragma once
#include <aibs/memory_playback.hpp>
namespace aibs::detail {
// Private seam for deterministic controller tests, not an installed SDK API.
struct MemoryPlaybackTestAccess {
 static std::unique_ptr<MemoryPlaybackSession> make(std::unique_ptr<AudioPlayback>);
};
}
