#pragma once
#include <aibs/asset_scene.hpp>
#include <aibs/textured_scene.hpp>
#include <limits>
namespace aibs {
enum class ObjUvOrigin {top_left,bottom_left};
struct SurfaceCorner {float u=0,v=0;Vec3 tangent{1,0,0};float tangent_sign=1;bool tangent_valid=true;};
inline constexpr std::uint32_t surface_no_image=std::numeric_limits<std::uint32_t>::max();
// Corner attributes retain UV seams independently of v1's geometric deduplication.
struct SurfaceMeshAsset {MeshAsset geometry;std::vector<SurfaceCorner> corners;std::vector<ImageAsset> images;std::vector<std::uint32_t> albedo_images;};
SurfaceMeshAsset import_surface_obj(std::string_view,std::span<const MeshMaterial>,std::string asset_id,std::string name,ObjUvOrigin);
void validate_surface_asset(const SurfaceMeshAsset&);
TexturedScene surface_scene(const SurfaceMeshAsset&,Vec3 center={},Vec3 scale={1,1,1},Quaternion rotation={});
// Compose one transformed surface with exact image/semantic deduplication.
// Aggregate image/draw/vertex limits apply before logical publication. Failed
// validation/allocation preserves all destination elements (capacity may grow).
void append_surface_scene(TexturedScene&,const SurfaceMeshAsset&,Vec3 center={},Vec3 scale={1,1,1},Quaternion rotation={});
}
