#pragma once
#include <aibs/scene.hpp>
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace aibs {
inline constexpr std::size_t character_maximum_payload_bytes=32u*1024u*1024u;
inline constexpr std::size_t character_maximum_decoded_bytes=64u*1024u*1024u;
inline constexpr std::size_t character_maximum_vertices=262144;
inline constexpr std::size_t character_maximum_indices=1572864;
inline constexpr std::size_t character_maximum_joints=64;
inline constexpr std::size_t character_maximum_clips=8;
inline constexpr std::size_t character_maximum_clip_frames=4096;
using CharacterMatrix=std::array<float,16>;
inline constexpr CharacterMatrix character_identity_matrix{1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};

// Local-to-parent TRS. Positive scales prevent reflected/singular skin normals.
// Quaternion order and tolerance match the engine's existing Quaternion.
struct CharacterJointTransform {
 Vec3 translation{};Quaternion rotation{};Vec3 scale{1,1,1};
 bool operator==(const CharacterJointTransform& r)const{return translation==r.translation&&rotation.x==r.rotation.x&&rotation.y==r.rotation.y&&rotation.z==r.rotation.z&&rotation.w==r.rotation.w&&scale==r.scale;}
};
struct CharacterVertex {
 // Normal is unit length (squared-norm tolerance1e-4); color is linear albedo.
 Vec3 position{},normal{0,1,0},color{1,1,1};float emission=0;
 float u=0,v=0;
 std::array<std::uint16_t,4> joints{};
 std::array<float,4> weights{1,0,0,0};
 bool operator==(const CharacterVertex&)const=default;
};
struct CharacterJoint {
 std::int32_t parent=-1;
 CharacterJointTransform bind_local;
 CharacterMatrix inverse_bind=character_identity_matrix;
 bool operator==(const CharacterJoint&)const=default;
};
struct CharacterClip {
 std::string name;
 float duration_seconds=1;
 std::uint32_t frame_count=1;
 bool looping=true;
 // Uniformly spaced samples, frame-major, exactly frame_count*joint_count.
 // Root translation stays at bind translation: navigation owns locomotion.
 std::vector<CharacterJointTransform> samples;
 bool operator==(const CharacterClip&)const=default;
};
// Owned persistent resource; no source paths, borrowed arrays or transient mesh.
struct CharacterMesh {
 std::vector<CharacterVertex> vertices;
 std::vector<std::uint32_t> indices;
 std::vector<CharacterJoint> joints;
 std::vector<CharacterClip> clips;
 bool operator==(const CharacterMesh&)const=default;
};
// Per-frame data is independent of the resource and needs no dynamic storage.
struct CharacterPose {
 std::uint32_t joint_count=0;
 std::array<CharacterJointTransform,character_maximum_joints> local{};
};
struct CharacterInstance {
 CharacterPose pose;
 CharacterMatrix world=character_identity_matrix;
 Vec3 tint{1,1,1};float emission=0,opacity=1;
};
struct CharacterSkinPalette {
 // CPU value layout; a renderer must pack its own explicit GPU constant layout.
 std::uint32_t joint_count=0;
 std::array<CharacterMatrix,character_maximum_joints> skin{},normal{};
};
struct CharacterSkinnedVertex {Vec3 position,normal;};
struct CharacterMeshCost {
 // Conservative canonical data charge, not an implemented file encoder.
 // A future codec must also bound the actual complete input/output file.
 std::size_t payload_bytes=0,decoded_bytes=0,animation_bytes=0;
 std::size_t gpu_vertex_bytes=0,gpu_index_bytes=0;
};
CharacterMeshCost character_mesh_cost(const CharacterMesh&);
// Single root at joint0; every other parent precedes its child. Inverse binds
// must invert global bind transforms in mesh coordinates. No GPU is touched.
void validate_character_mesh(const CharacterMesh&);
CharacterMatrix character_transform_matrix(const CharacterJointTransform&);
CharacterPose character_bind_pose(const CharacterMesh&);
// Resource adoption validates every sample first. This bounded runtime helper
// checks structure and the two accessed frames; it does not rescan the mesh.
CharacterPose sample_character_clip(const CharacterMesh&,std::size_t clip,double seconds);
// Row-vector conventions: global=local*parent_global; skin=inverse_bind*global.
// Normal palette is inverse-transpose of each skin matrix's linear 3x3 block.
CharacterSkinPalette character_skin_palette(const CharacterMesh&,const CharacterPose&);
// Spherically and linearly blend two poses of equal joint count. Factor in [0, 1].
// Zero dynamic memory allocations. Preserves unit quaternions and scale validity.
CharacterPose blend_character_poses(const CharacterPose& a,const CharacterPose& b,float factor);
void validate_character_instance(const CharacterMesh&,const CharacterInstance&);
// CPU oracle: weighted skin positions and per-bone inverse-transpose normals,
// then world/inverse-transpose-world. Normalize after blending/world transform.
// If squared blended normal <=1e-12*(sum weighted normal lengths)^2, use the
// original bind normal before world. This relative test preserves large scales.
CharacterSkinnedVertex character_skin_vertex(const CharacterVertex&,const CharacterSkinPalette&,
                                            const CharacterMatrix& world=character_identity_matrix);
}
