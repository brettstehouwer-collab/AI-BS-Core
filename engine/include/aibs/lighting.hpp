#pragma once
#include <aibs/render.hpp>
#include <array>
#include <cstdint>
#include <optional>
#include <vector>

namespace aibs {
// direction follows light rays toward the world; Lambert uses its negative.
struct DirectionalLight {
 Vec3 direction{0,-1,0},color{1,1,1};float intensity=1;
 bool operator==(const DirectionalLight&)const=default;
};
struct PointLight {
 Vec3 position{},color{1,1,1};float intensity=1,radius=10;
 bool operator==(const PointLight&)const=default;
};
struct DirectionalShadow {
 bool enabled=false;Vec3 center{};
 float half_extent=64,near_plane=.1f,far_plane=256,bias=.001f;
 std::uint32_t resolution=1024;
 bool operator==(const DirectionalShadow&)const=default;
};
struct SceneLighting {
 bool enabled=false;Vec3 ambient{.05f,.05f,.05f};float exposure=1;
 std::optional<DirectionalLight> directional;
 std::vector<PointLight> points;
 DirectionalShadow shadow;
 bool operator==(const SceneLighting&)const=default;
};
inline constexpr std::size_t scene_lighting_maximum_points=32;
struct alignas(16) GpuPointLight {
 std::array<float,4> position_radius{},color_intensity{};
};
// Exact HLSL constant-buffer layout: 1168 bytes. Allocate a 256-byte-rounded
// upload buffer (1280 bytes); this CPU value does not own any GPU resource.
struct alignas(16) GpuLightingConstants {
 std::array<float,4> ambient_exposure{},direction_intensity{},directional_color{};
 std::array<std::uint32_t,4> controls{}; // enabled, point count, shadow enabled, resolution
 std::array<float,16> shadow_view_projection{}; // row-major, row-vector D3D LH
 std::array<float,4> shadow_parameters{}; // normalized depth bias, reciprocal resolution
 std::array<GpuPointLight,scene_lighting_maximum_points> points{};
};
void validate_scene_lighting(const SceneLighting&);
// The volume is centered on shadow.center with +/-half_extent along light X/Y
// and symmetric coverage about its center along the ray direction. D3D Z=0..1.
// Requires a directional light; it does not allocate or touch a renderer.
std::array<float,16> directional_shadow_matrix(const SceneLighting&);
GpuLightingConstants pack_scene_lighting(const SceneLighting&);
// Authored-lighting reference oracle only (enabled=true); legacy pipelines keep
// their own previous shading. Normal need not be unit but must be finite/nonzero.
// Ambient+Lambert+bounded quadratic point falloff, additive base*emission,
// exponential exposure (1-exp(-radiance*exposure)) and standard sRGB transfer.
// Shadow visibility is intentionally omitted; the GPU multiplies only the
// directional Lambert term by its measured directional-map visibility.
Vec3 evaluate_scene_lighting(const SceneLighting&,Vec3 position,Vec3 normal,
                            Vec3 base_color,float emission);
}
