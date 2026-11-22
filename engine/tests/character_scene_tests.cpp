#include <aibs/character_scene.hpp>
#include <cmath>
#include <cstddef>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace aibs;
namespace {
unsigned checks=0;
void need(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
void close(float actual,float expected,float epsilon=4e-5f){need(std::abs(actual-expected)<=epsilon,"Character numeric reference mismatch");}
void close(Vec3 actual,Vec3 expected,float epsilon=4e-5f){close(actual.x,expected.x,epsilon);close(actual.y,expected.y,epsilon);close(actual.z,expected.z,epsilon);}
template<class F>void reject(F&& action){bool rejected=false;try{action();}catch(const std::invalid_argument&){rejected=true;}need(rejected,"Expected malformed character rejection");}
CharacterMatrix root_inverse(){return {0,-1,0,0,1,0,0,0,0,0,1,0,0,2,0,1};}
CharacterMatrix child_inverse(){return {0,-1,0,0,1,0,0,0,0,0,1,0,0,-1,0,1};}
CharacterMesh fixture(){
 CharacterMesh mesh;
 CharacterJoint root;root.bind_local.translation={2,0,0};root.bind_local.rotation={0,0,.7071067812f,.7071067812f};root.inverse_bind=root_inverse();
 CharacterJoint child;child.parent=0;child.bind_local.translation={0,3,0};child.inverse_bind=child_inverse();mesh.joints={root,child};
 for(const Vec3 p:{Vec3{-1,0,0},Vec3{-1,1,0},Vec3{-2,0,1}}){CharacterVertex vertex;vertex.position=p;vertex.normal={0,1,0};vertex.color={.2f,.5f,.9f};vertex.joints={1,0,0,0};vertex.weights={1,0,0,0};mesh.vertices.push_back(vertex);}
 mesh.vertices[1].u=1;mesh.vertices[2].v=1;mesh.indices={0,1,2};return mesh;
}
CharacterClip clip(const CharacterMesh& mesh){
 CharacterClip result;result.name="idle-gesture";result.duration_seconds=2;result.frame_count=3;
 for(unsigned i=0;i<3;++i){result.samples.push_back(mesh.joints[0].bind_local);auto child=mesh.joints[1].bind_local;if(i==1){child.translation.y=5;child.rotation={0,0,-.7071067812f,-.7071067812f};}result.samples.push_back(child);}
 return result;
}
}
int main(){try{
 static_assert(sizeof(CharacterVertex)==72);
 static_assert(offsetof(CharacterVertex,joints)==48&&offsetof(CharacterVertex,weights)==56);
 static_assert(sizeof(CharacterJointTransform)==40);
 static_assert(character_maximum_joints==64&&character_maximum_clips==8);
 auto mesh=fixture();validate_character_mesh(mesh);const auto original=mesh;
 const auto cost=character_mesh_cost(mesh);need(cost.payload_bytes<character_maximum_payload_bytes,"Small mesh fits explicit payload charge");
 need(cost.gpu_vertex_bytes==3*sizeof(CharacterVertex)&&cost.gpu_index_bytes==3*sizeof(std::uint32_t),"GPU geometry bytes charge indexed storage, not expanded triangles");
 need(cost.animation_bytes==0&&cost.decoded_bytes>=cost.gpu_vertex_bytes+cost.gpu_index_bytes,"Decoded storage and animation costs are independent");
 auto pose=character_bind_pose(mesh);need(pose.joint_count==2,"Bind pose records only the actual skeleton size");
 auto palette=character_skin_palette(mesh,pose);need(palette.joint_count==2,"Skin palette retains skeleton size");
 for(const auto& vertex:mesh.vertices){const auto skinned=character_skin_vertex(vertex,palette);close(skinned.position,vertex.position);close(skinned.normal,vertex.normal);}
 need(mesh==original,"Pose/skin evaluation does not mutate immutable resource data");
 // Nonidentity parent rotation, translation and inverse binds expose order errors.
 pose.local[1].translation.y=4;palette=character_skin_palette(mesh,pose);
 close(character_skin_vertex(mesh.vertices[0],palette).position,{-2,0,0});
 close(character_skin_vertex(mesh.vertices[1],palette).position,{-2,1,0});
 pose=character_bind_pose(mesh);pose.local[1].rotation={0,0,.7071067812f,.7071067812f};palette=character_skin_palette(mesh,pose);
 close(character_skin_vertex(mesh.vertices[0],palette).position,{-1,0,0});
 close(character_skin_vertex(mesh.vertices[1],palette).position,{-2,0,0});
 close(character_skin_vertex(mesh.vertices[1],palette).normal,{-1,0,0});
 auto blended=mesh.vertices[1];blended.joints={0,1,0,0};blended.weights={.25f,.75f,0,0};
 close(character_skin_vertex(blended,palette).position,{-1.75f,.25f,0});
 close(character_skin_vertex(blended,palette).normal,{-.948683298f,.316227766f,0});
 pose=character_bind_pose(mesh);pose.local[1].rotation={0,0,1,0};palette=character_skin_palette(mesh,pose);blended.weights={.5f,.5f,0,0};
 close(character_skin_vertex(blended,palette).position,{-1,0,0});close(character_skin_vertex(blended,palette).normal,{0,1,0});
 // Skin normal transforms use inverse transpose, including nonuniform bone scale.
 pose=character_bind_pose(mesh);pose.local[1].scale={2,1,1};palette=character_skin_palette(mesh,pose);
 auto diagonal=mesh.vertices[0];diagonal.normal={.7071067812f,.7071067812f,0};
 close(character_skin_vertex(diagonal,palette).normal,{.894427191f,.447213595f,0});
 CharacterJointTransform world;world.translation={10,20,30};world.rotation={0,0,.7071067812f,.7071067812f};world.scale={2,1,3};
 palette=character_skin_palette(mesh,character_bind_pose(mesh));
 const auto placed=character_skin_vertex(diagonal,palette,character_transform_matrix(world));
 close(placed.position,{10,18,30});close(placed.normal,{-.894427191f,.447213595f,0});
 pose=character_bind_pose(mesh);for(unsigned j=0;j<pose.joint_count;++j)pose.local[j].scale={1000,1000,1000};palette=character_skin_palette(mesh,pose);
 close(character_skin_vertex(mesh.vertices[0],palette).normal,{0,1,0});
 CharacterInstance instance;instance.pose=character_bind_pose(mesh);instance.world=character_transform_matrix(world);instance.opacity=.65f;validate_character_instance(mesh,instance);
 need(mesh==original,"Per-frame pose and instance placement leave resource bytes unchanged");
 mesh.clips.push_back(clip(mesh));validate_character_mesh(mesh);const auto animated_cost=character_mesh_cost(mesh);
 need(animated_cost.animation_bytes==6*sizeof(CharacterJointTransform)&&animated_cost.payload_bytes>cost.payload_bytes&&animated_cost.decoded_bytes>cost.decoded_bytes,"Baked samples are charged before publication");
 auto sampled=sample_character_clip(mesh,0,.5);close(sampled.local[1].translation,{0,4,0});
 close(sampled.local[1].rotation.z,.382683432f);close(sampled.local[1].rotation.w,.923879533f);
 palette=character_skin_palette(mesh,sampled);close(character_skin_vertex(mesh.vertices[0],palette).position,{-2,0,0});
 close(character_skin_vertex(mesh.vertices[1],palette).position,{-2.707106781f,.707106781f,0});
 auto looped=sample_character_clip(mesh,0,2);close(looped.local[1].translation,{0,3,0});
 mesh.clips[0].looping=false;auto ended=sample_character_clip(mesh,0,300);close(ended.local[1].translation,{0,3,0});
 mesh.clips[0].frame_count=1;mesh.clips[0].samples.resize(2);validate_character_mesh(mesh);close(sample_character_clip(mesh,0,.9).local[1].translation,{0,3,0});
 mesh=fixture();mesh.clips.push_back(clip(mesh));
 reject([&]{sample_character_clip(mesh,1,0);});reject([&]{sample_character_clip(mesh,0,-.1);});reject([&]{sample_character_clip(mesh,0,std::numeric_limits<double>::infinity());});
 auto bad=mesh;bad.vertices.clear();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.indices.clear();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.indices.push_back(0);reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.indices[0]=3;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints.clear();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[0].parent=1;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[1].parent=1;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[1].parent=63;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[1].parent=-1;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[0].parent=1;bad.joints[1].parent=0;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints.resize(65);reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[1].inverse_bind=character_identity_matrix;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[1].inverse_bind[15]=0;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[1].inverse_bind[0]=std::numeric_limits<float>::infinity();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[1].bind_local.rotation={0,0,0,0};reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[1].bind_local.scale.x=0;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.joints[1].bind_local.scale.y=-1;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].position.x=std::numeric_limits<float>::quiet_NaN();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].normal={};reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].normal={.1f,0,0};reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].u=std::numeric_limits<float>::infinity();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].color.z=2;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].emission=-1;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].weights={.4f,.4f,0,0};reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].weights={1.1f,-.1f,0,0};reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].weights[2]=std::numeric_limits<float>::quiet_NaN();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.vertices[0].joints[3]=64;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips.resize(9,mesh.clips[0]);reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips.push_back(bad.clips[0]);reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].name.clear();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].name=std::string(65,'x');reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].duration_seconds=0;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].duration_seconds=std::numeric_limits<float>::quiet_NaN();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].duration_seconds=3601;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].frame_count=0;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].frame_count=4097;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].samples.pop_back();reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].samples[2].translation.x+=.01f;reject([&]{validate_character_mesh(bad);});
 bad=mesh;bad.clips[0].samples[3].scale.z=0;reject([&]{validate_character_mesh(bad);});
 auto invalid_pose=character_bind_pose(mesh);invalid_pose.joint_count=1;reject([&]{character_skin_palette(mesh,invalid_pose);});
 invalid_pose=character_bind_pose(mesh);invalid_pose.local[0].scale.x=0;reject([&]{character_skin_palette(mesh,invalid_pose);});
 auto invalid_instance=instance;invalid_instance.world[3]=1;reject([&]{validate_character_instance(mesh,invalid_instance);});
 invalid_instance=instance;invalid_instance.world[0]=0;invalid_instance.world[1]=0;invalid_instance.world[2]=0;reject([&]{validate_character_instance(mesh,invalid_instance);});
 invalid_instance=instance;invalid_instance.opacity=1.01f;reject([&]{validate_character_instance(mesh,invalid_instance);});
 invalid_instance=instance;invalid_instance.tint.x=-1;reject([&]{validate_character_instance(mesh,invalid_instance);});
 invalid_instance=instance;invalid_instance.emission=17;reject([&]{validate_character_instance(mesh,invalid_instance);});
 auto many=fixture();many.joints.clear();for(int i=0;i<64;++i){CharacterJoint joint;joint.parent=i-1;many.joints.push_back(joint);}for(auto& vertex:many.vertices)vertex.joints={63,0,0,0};validate_character_mesh(many);need(character_bind_pose(many).joint_count==64,"64-joint boundary is usable");
 auto scaled=many;scaled.joints.resize(3);for(auto& vertex:scaled.vertices)vertex.joints={2,0,0,0};auto scaled_pose=character_bind_pose(scaled);for(unsigned i=0;i<3;++i)scaled_pose.local[i].scale={1000,1000,1000};scaled_pose.local[2].scale.y=500;
 auto scaled_vertex=scaled.vertices[0];scaled_vertex.normal={.7071067812f,.7071067812f,0};close(character_skin_vertex(scaled_vertex,character_skin_palette(scaled,scaled_pose)).normal,{.447213595f,.894427191f,0});
 CharacterInstance overflowing;overflowing.pose=character_bind_pose(many);for(auto& joint:overflowing.pose.local)joint.scale={1000,1000,1000};reject([&]{validate_character_instance(many,overflowing);});
 auto large=many;large.vertices.resize(character_maximum_vertices,large.vertices.front());large.indices.resize(character_maximum_indices,0);
 CharacterClip bulk;bulk.name="budget-test";bulk.frame_count=4096;bulk.samples.resize(4096*64);large.clips={bulk};
 need(character_mesh_cost(large).payload_bytes>character_maximum_payload_bytes,"Actual bounded geometry+animation storage exceeds the payload budget in this fixture");reject([&]{validate_character_mesh(large);});
 auto reserved=fixture();reserved.vertices.reserve(1000000);need(character_mesh_cost(reserved).decoded_bytes>character_maximum_decoded_bytes,"Unused owned capacity is charged before publication");reject([&]{validate_character_mesh(reserved);});
 need(character_mesh_cost(mesh).decoded_bytes<character_maximum_decoded_bytes,"Rejected replacement does not alter original usable resource");validate_character_mesh(mesh);
 std::cout<<"PASS "<<checks<<" indexed character, bind/pose, animation, normal and resource-budget contracts\n";
 auto pose_a=character_bind_pose(mesh);auto pose_b=pose_a;
 pose_b.local[1].translation={0,6,0};
 pose_b.local[1].rotation={0,0,1,0};
 const auto blend_zero=blend_character_poses(pose_a,pose_b,0.f);
 close(blend_zero.local[1].translation,pose_a.local[1].translation);
 const auto blend_one=blend_character_poses(pose_a,pose_b,1.f);
 close(blend_one.local[1].translation,pose_b.local[1].translation);
 const auto blend_half=blend_character_poses(pose_a,pose_b,0.5f);
 close(blend_half.local[1].translation,{0,4.5f,0});
 reject([&]{blend_character_poses(pose_a,pose_b,-0.1f);});
 reject([&]{blend_character_poses(pose_a,pose_b,1.1f);});
 reject([&]{blend_character_poses(pose_a,pose_b,std::numeric_limits<float>::quiet_NaN());});
 auto pose_c=pose_a;pose_c.joint_count=1;
 reject([&]{blend_character_poses(pose_a,pose_c,0.5f);});
 std::cout<<"PASS "<<checks<<" indexed character, bind/pose, animation, normal, blend and resource-budget contracts\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
