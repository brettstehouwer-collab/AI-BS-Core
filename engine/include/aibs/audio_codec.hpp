#pragma once
#include <aibs/audio_assets.hpp>
namespace aibs {
// AIBAudio2: exact LE version2 envelope, SHA256 body, no external dependencies.
// Decode preflights all lengths/metadata/budgets before owned PCM allocation.
std::vector<std::byte> encode_audio_asset(const AudioAsset&);
AudioAsset decode_audio_asset(std::span<const std::byte>);
}
