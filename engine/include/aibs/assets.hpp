#pragma once
#include <aibs/render.hpp>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace aibs {
inline constexpr std::size_t mesh_asset_max_input_bytes = 32u * 1024u * 1024u;
inline constexpr std::size_t mesh_asset_max_vertices = 100000;
inline constexpr std::size_t mesh_asset_max_triangles = 100000;
inline constexpr std::size_t mesh_asset_max_materials = 64;

// v1 supports opaque base color/emission. OBJ texture coordinates are checked
// when supplied but are not retained; materials are supplied by the engine.
struct MeshMaterial { std::string name; Vec3 base_color{1,1,1}; float emission = 0; };
struct AssetVertex { Vec3 position; Vec3 normal; };
struct MeshAsset {
 std::string asset_id;
 std::string name;
 std::string source_sha256;
 std::vector<AssetVertex> vertices;
 std::vector<std::uint32_t> indices;
 std::vector<std::uint32_t> triangle_materials;
 std::vector<MeshMaterial> materials;
};

MeshAsset import_obj(std::string_view obj, std::span<const MeshMaterial> materials,
                     std::string asset_id, std::string name);
void validate_mesh_asset(const MeshAsset& asset);
// AIBMesh1: little-endian versioned payload plus SHA-256 checksum. Encoding
// canonicalizes signed zero; decoding rejects noncanonical negative zero.
std::vector<std::byte> encode_mesh_asset(const MeshAsset& asset);
MeshAsset decode_mesh_asset(std::span<const std::byte> bytes);
std::string asset_sha256(std::span<const std::byte> bytes);
MeshAsset load_mesh_asset(const std::filesystem::path& path);
// Publish atomically to a new path. Existing files are never replaced.
void save_mesh_asset(const std::filesystem::path& path, const MeshAsset& asset);
}
