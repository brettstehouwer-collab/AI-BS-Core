#pragma once
#include <aibs/surface_assets.hpp>
#include <cstddef>
#include <span>
#include <vector>
namespace aibs {
inline constexpr std::size_t surface_asset_max_input_bytes=32u*1024u*1024u;
// AIBSurf2: little-endian version2 payload with SHA-256, embedded AIBMesh1,
// per-corner UV/tangent attributes and complete owned RGBA8 mip chains.
// No external paths or executable content. Signed zero is canonicalized on
// encode and rejected on decode. Legacy geometry bytes remain unchanged.
std::vector<std::byte> encode_surface_asset(const SurfaceMeshAsset&);
SurfaceMeshAsset decode_surface_asset(std::span<const std::byte>);
}
