#pragma once
#include <aibs/character_scene.hpp>
#include <aibs/image_assets.hpp>
#include <limits>
namespace aibs {
inline constexpr std::uint32_t character_no_image=std::numeric_limits<std::uint32_t>::max();
inline constexpr std::size_t character_asset_maximum_images=32;
inline constexpr std::size_t character_asset_maximum_materials=64;
inline constexpr std::size_t character_asset_maximum_draws=64;
struct CharacterMaterial {
 std::uint32_t albedo_image=character_no_image;Vec3 base_color{1,1,1};float emission=0;bool double_sided=true;
 // Opt-in surface factor. The default retains the legacy diffuse wire form.
 float roughness=1;
 bool operator==(const CharacterMaterial&)const=default;
};
struct CharacterDraw {
 std::uint32_t first_index=0,index_count=0,material=0;
 bool operator==(const CharacterDraw&)const=default;
};
struct CharacterAsset {
 std::string asset_id,name,source_sha256;CharacterMesh mesh;
 std::vector<ImageAsset> images;std::vector<CharacterMaterial> materials;std::vector<CharacterDraw> draws;
 bool operator==(const CharacterAsset&)const=default;
};
struct CharacterAssetCost {
 std::size_t payload_bytes=0,decoded_bytes=0,animation_bytes=0,image_bytes=0,gpu_vertex_bytes=0,gpu_index_bytes=0;
};
// Complete canonical payload charge, including48-byte header; actual decoder
// input and encoder output have the same independent32MiB bound. Decoded cost
// includes all owned container/string capacities, images and baked samples.
CharacterAssetCost character_asset_cost(const CharacterAsset&);
std::uint32_t character_asset_payload_version(const CharacterAsset&)noexcept;
void validate_character_asset(const CharacterAsset&);
}
