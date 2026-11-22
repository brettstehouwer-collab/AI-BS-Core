#pragma once
#include <aibs/character_assets.hpp>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace aibs {
struct GltfInputResource {std::string_view uri;std::span<const std::byte> bytes;};
struct CharacterClipSelection {std::uint32_t source_animation=0;std::string name;bool looping=false;};
struct CharacterImportOptions {
 std::string asset_id,name;
 std::vector<CharacterClipSelection> clips;
 std::uint32_t bake_rate=30;
};
struct CharacterImportDiagnostics {
 std::size_t parser_peak_bytes=0;
 // Conservative engine-owned source/parser/output/scratch accounting; this is
 // not a measurement or cap on opaque WIC/driver/whole-process allocations.
 std::size_t engine_owned_live_upper_bound_bytes=0;
 std::vector<std::uint16_t> source_skin_to_cooked;
 std::vector<double> baked_intervals_seconds;
 bool operator==(const CharacterImportDiagnostics&)const=default;
};
// Actual aggregate bytes currently owned by the private cgltf allocators,
// including allocation headers. Safe to observe while other imports run.
std::size_t character_import_live_parser_bytes()noexcept;
// Synchronous, memory-only bounded GLB2/glTF2 opaque dielectric/skinned profile.
// Scalar roughness0.04..1 is owned; normal/roughness textures remain unsupported.
// Every
// retained byte is owned by the returned asset. External relative resources
// must be supplied explicitly; no filesystem, data URI or network fallback.
CharacterAsset import_character_gltf(std::span<const std::byte> source,
 std::span<const GltfInputResource> resources,const CharacterImportOptions&,
 CharacterImportDiagnostics* diagnostics=nullptr);
}
