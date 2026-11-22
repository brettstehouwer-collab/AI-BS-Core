#pragma once
#include <aibs/render.hpp>
#include <aibs/image_assets.hpp>
namespace aibs {
struct TexturedVertex {Vec3 position,normal;float u=0,v=0;};
struct TexturedDraw {std::uint32_t first=0,count=0,image=0;Vec3 tint{1,1,1};float emission=0;};
// Immutable CPU resource snapshot. Textures are owned; no borrowed source paths.
struct TexturedScene {std::vector<TexturedVertex> vertices;std::vector<ImageAsset> images;std::vector<TexturedDraw> draws;};
void validate_textured_scene(const TexturedScene&);
}
