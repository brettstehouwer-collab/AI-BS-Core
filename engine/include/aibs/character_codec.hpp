#pragma once
#include <aibs/character_assets.hpp>
#include <span>
namespace aibs {
inline constexpr std::size_t character_asset_max_input_bytes=character_maximum_payload_bytes;
// AIBChar2 family: version2 retains legacy diffuse bytes; version3 appends an
// opt-in roughness scalar per material. Default-only assets still encode v2.
// Both versions are canonical little-endian owned data plus SHA-256 checksum.
// No source paths or external image/animation references survive decoding.
std::vector<std::byte> encode_character_asset(const CharacterAsset&);
CharacterAsset decode_character_asset(std::span<const std::byte>);
}
