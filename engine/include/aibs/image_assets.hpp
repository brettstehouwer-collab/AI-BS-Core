#pragma once
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>
namespace aibs {
enum class ImageSemantic : std::uint32_t { srgb_color,linear_data,normal_map };
struct ImageMip {std::uint32_t width=0,height=0;std::vector<unsigned char> rgba;bool operator==(const ImageMip&)const=default;};
struct ImageAsset {ImageSemantic semantic=ImageSemantic::srgb_color;std::vector<ImageMip> levels;bool operator==(const ImageAsset&)const=default;};
inline constexpr std::size_t image_asset_maximum_bytes=32u*1024u*1024u;
std::size_t image_resident_bytes(const ImageAsset&);
void validate_image_asset(const ImageAsset&);
// Strong exception guarantee. Color filtering is linear-light/premultiplied;
// data stays linear and normal-map vectors are renormalized after filtering.
void generate_image_mips(ImageAsset&,std::size_t budget=image_asset_maximum_bytes);
// Native WIC PNG decoder; metadata/dimensions/budget checked before pixel allocation.
ImageAsset decode_png_image(std::span<const unsigned char>,ImageSemantic,std::size_t budget=image_asset_maximum_bytes);
}
