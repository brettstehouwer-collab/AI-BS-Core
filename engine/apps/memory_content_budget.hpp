#pragma once
#include <aibs/render.hpp>
#include <cstddef>
#include <stdexcept>
namespace aibs {
// Private native-app accounting: the composed upload source is separate from
// PlacedAssetVisuals' retained immutable closure and placement projection.
inline constexpr std::size_t memory_content_resident_limit=128u*1024u*1024u;
inline std::size_t memory_scene_mesh_bytes(const SceneMesh& mesh){
 std::size_t total=0;
 const auto add=[&](std::size_t bytes){if(bytes>memory_content_resident_limit-total)throw std::invalid_argument("Composed scene CPU storage exceeds128MiB");total+=bytes;};
 const auto items=[&](std::size_t count,std::size_t stride){if(count>memory_content_resident_limit/stride)throw std::invalid_argument("Composed scene CPU capacity exceeds128MiB");add(count*stride);};
 items(mesh.vertices.capacity(),sizeof(SceneVertex));items(mesh.landmarks.capacity(),sizeof(std::string));
 for(const auto& name:mesh.landmarks){add(name.capacity());add(1);}
 return total;
}
inline std::size_t memory_scene_gpu_remainder(std::size_t other_cpu,const SceneMesh& composed){
 if(other_cpu>memory_content_resident_limit)throw std::invalid_argument("Retained chapter CPU storage exceeds128MiB");
 const auto mesh=memory_scene_mesh_bytes(composed);
 if(mesh>memory_content_resident_limit-other_cpu)throw std::invalid_argument("Composed scene and retained chapter CPU storage exceed128MiB");
 return memory_content_resident_limit-other_cpu-mesh;
}
}
