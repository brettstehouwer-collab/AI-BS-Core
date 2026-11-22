#include <aibs/guide_presentation.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <numbers>
#include <stdexcept>

namespace aibs {
namespace {
constexpr std::size_t joint_count=18;
constexpr std::array<const char*,4> clip_names{"idle","walk","catchup","guidance"};
constexpr float pi=std::numbers::pi_v<float>;
enum Joint :std::uint16_t {
 root,hips,spine,chest,neck,head,
 left_shoulder,left_elbow,left_wrist,right_shoulder,right_elbow,right_wrist,
 left_hip,left_knee,left_ankle,right_hip,right_knee,right_ankle
};
Quaternion rotation_x(float radians){return {std::sin(radians*.5f),0,0,std::cos(radians*.5f)};}
Quaternion rotation_z(float radians){return {0,0,std::sin(radians*.5f),std::cos(radians*.5f)};}
bool valid(Vec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z)&&std::abs(p.x)<=1e6f&&std::abs(p.y)<=1e6f&&std::abs(p.z)<=1e6f;}
bool valid(const GuideState& state){
 return valid(state.character.feet)&&valid(state.character.velocity)&&valid(state.destination)&&
  (state.intent==GuideIntent::follow||state.intent==GuideIntent::wait)&&
  (state.activity==GuideActivity::following||state.activity==GuideActivity::near_player||state.activity==GuideActivity::waiting||state.activity==GuideActivity::blocked);
}
void joint(CharacterMesh& mesh,std::int32_t parent,Vec3 translation){
 CharacterJoint value;value.parent=parent;value.bind_local.translation=translation;
 Vec3 global=translation;
 if(parent>=0){const auto& p=mesh.joints[static_cast<std::size_t>(parent)].inverse_bind;global.x-=p[12];global.y-=p[13];global.z-=p[14];}
 value.inverse_bind[12]=-global.x;value.inverse_bind[13]=-global.y;value.inverse_bind[14]=-global.z;
 mesh.joints.push_back(value);
}
void face(CharacterMesh& mesh,std::array<Vec3,4> positions,Vec3 normal,Vec3 color,std::uint16_t bone){
 const auto start=static_cast<std::uint32_t>(mesh.vertices.size());
 constexpr std::array<std::array<float,2>,4> uv{{{0,1},{1,1},{1,0},{0,0}}};
 for(std::size_t i=0;i<positions.size();++i){CharacterVertex vertex;vertex.position=positions[i];vertex.normal=normal;vertex.color=color;vertex.u=uv[i][0];vertex.v=uv[i][1];vertex.joints={bone,0,0,0};mesh.vertices.push_back(vertex);}
 for(auto index:{0u,1u,2u,0u,2u,3u})mesh.indices.push_back(start+index);
}
void box(CharacterMesh& mesh,Vec3 center,Vec3 half,Vec3 color,std::uint16_t bone){
 const float x=center.x-half.x,X=center.x+half.x,y=center.y-half.y,Y=center.y+half.y,z=center.z-half.z,Z=center.z+half.z;
 face(mesh,{{{x,y,Z},{X,y,Z},{X,Y,Z},{x,Y,Z}}},{0,0,1},color,bone);
 face(mesh,{{{X,y,z},{x,y,z},{x,Y,z},{X,Y,z}}},{0,0,-1},color,bone);
 face(mesh,{{{X,y,Z},{X,y,z},{X,Y,z},{X,Y,Z}}},{1,0,0},color,bone);
 face(mesh,{{{x,y,z},{x,y,Z},{x,Y,Z},{x,Y,z}}},{-1,0,0},color,bone);
 face(mesh,{{{x,Y,Z},{X,Y,Z},{X,Y,z},{x,Y,z}}},{0,1,0},color,bone);
 face(mesh,{{{x,y,z},{X,y,z},{X,y,Z},{x,y,Z}}},{0,-1,0},color,bone);
}
CharacterClip authored_clip(const CharacterMesh& mesh,std::size_t index){
 CharacterClip clip;clip.name=clip_names[index];clip.frame_count=33;clip.duration_seconds=index==0?3.2f:index==1?1.f:index==2?.6f:2.4f;clip.looping=index!=3;
 clip.samples.reserve(clip.frame_count*mesh.joints.size());
 for(std::uint32_t frame=0;frame<clip.frame_count;++frame){
  const float fraction=static_cast<float>(frame)/static_cast<float>(clip.frame_count-1);
  const float wave=std::sin(2*pi*fraction);
  std::array<CharacterJointTransform,joint_count> pose{};for(std::size_t j=0;j<mesh.joints.size();++j)pose[j]=mesh.joints[j].bind_local;
  if(index==0){
   pose[chest].rotation=rotation_z(.018f*wave);pose[neck].rotation=rotation_x(.012f*wave);
   pose[left_shoulder].rotation=rotation_z(.025f+.008f*wave);pose[right_shoulder].rotation=rotation_z(-.025f-.008f*wave);
   pose[spine].translation.y+=.004f*wave;
  }else if(index==1||index==2){
   const float amplitude=index==1?.40f:.58f;
   pose[left_hip].rotation=rotation_x(amplitude*wave);pose[right_hip].rotation=rotation_x(-amplitude*wave);
   pose[left_knee].rotation=rotation_x(std::max(0.f,-wave)*(index==1?.55f:.85f));
   pose[right_knee].rotation=rotation_x(std::max(0.f,wave)*(index==1?.55f:.85f));
   pose[left_shoulder].rotation=rotation_x(-.8f*amplitude*wave);pose[right_shoulder].rotation=rotation_x(.8f*amplitude*wave);
   pose[left_elbow].rotation=rotation_x(index==1?-.10f:-.28f);pose[right_elbow].rotation=rotation_x(index==1?-.10f:-.28f);
   pose[chest].rotation=rotation_z(.025f*wave);
  }else{
   // A small open-hand invitation, not a repair or gameplay interaction.
   const float raised=std::sin(pi*fraction);
   pose[left_shoulder].rotation=rotation_x(-.32f*raised);pose[left_elbow].rotation=rotation_x(-.62f*raised);
   pose[left_wrist].rotation=rotation_z(.18f*raised);pose[head].rotation=rotation_x(-.045f*raised);
  }
  clip.samples.insert(clip.samples.end(),pose.begin(),pose.end());
 }
 return clip;
}
}
CharacterMesh make_guide_placeholder(){
 CharacterMesh mesh;mesh.joints.reserve(joint_count);mesh.vertices.reserve(18*24);mesh.indices.reserve(18*36);mesh.clips.reserve(4);
 joint(mesh,-1,{});joint(mesh,root,{0,.91f,0});joint(mesh,hips,{0,.24f,0});joint(mesh,spine,{0,.25f,0});
 joint(mesh,chest,{0,.13f,0});joint(mesh,neck,{0,.13f,0});
 joint(mesh,chest,{-.24f,0,0});joint(mesh,left_shoulder,{0,-.27f,0});joint(mesh,left_elbow,{0,-.25f,0});
 joint(mesh,chest,{.24f,0,0});joint(mesh,right_shoulder,{0,-.27f,0});joint(mesh,right_elbow,{0,-.25f,0});
 joint(mesh,hips,{-.11f,0,0});joint(mesh,left_hip,{0,-.42f,0});joint(mesh,left_knee,{0,-.40f,0});
 joint(mesh,hips,{.11f,0,0});joint(mesh,right_hip,{0,-.42f,0});joint(mesh,right_knee,{0,-.40f,0});
 const Vec3 shirt{.21f,.35f,.43f},trousers{.085f,.13f,.19f},skin{.48f,.60f,.62f},shoes{.045f,.07f,.09f};
 box(mesh,{0,.95f,0},{.18f,.10f,.105f},trousers,hips);
 box(mesh,{0,1.10f,0},{.16f,.12f,.10f},shirt,spine);
 box(mesh,{0,1.30f,0},{.20f,.10f,.115f},shirt,chest);
 box(mesh,{0,1.51f,0},{.06f,.06f,.06f},skin,neck);
 box(mesh,{0,1.66f,0},{.10f,.14f,.10f},skin,head);
 for(const bool left:{true,false}){
  const float x=left?-.255f:.255f;
  box(mesh,{x,1.265f,0},{.055f,.135f,.055f},shirt,left?left_shoulder:right_shoulder);
  box(mesh,{x,1.005f,0},{.05f,.125f,.05f},shirt,left?left_elbow:right_elbow);
  box(mesh,{x,.835f,.015f},{.055f,.065f,.045f},skin,left?left_wrist:right_wrist);
  const float leg=left?-.11f:.11f;
  box(mesh,{leg,.70f,0},{.085f,.20f,.085f},trousers,left?left_hip:right_hip);
  box(mesh,{leg,.29f,0},{.07f,.19f,.07f},trousers,left?left_knee:right_knee);
  box(mesh,{leg,.045f,.06f},{.08f,.045f,.13f},shoes,left?left_ankle:right_ankle);
 }
 for(std::size_t i=0;i<clip_names.size();++i)mesh.clips.push_back(authored_clip(mesh,i));
 validate_character_mesh(mesh);return mesh;
}
GuidePresentation::GuidePresentation(const CharacterMesh& mesh):mesh_(&mesh){
 validate_character_mesh(mesh);
 if(mesh.clips.size()!=clip_names.size())throw std::invalid_argument("Guide presentation requires four named clips");
 for(std::size_t i=0;i<clip_names.size();++i)if(mesh.clips[i].name!=clip_names[i])throw std::invalid_argument("Guide presentation clip order mismatch");
}
std::optional<CharacterInstance> GuidePresentation::sample(const std::optional<GuideState>& guide,double elapsed,bool paused,bool recall_required,bool guidance){
 if(!std::isfinite(elapsed)||elapsed<0)throw std::invalid_argument("Guide presentation elapsed must be finite/nonnegative");
 if(!guide||recall_required||!valid(*guide)){previous_.reset();return {};}
 if(paused)return previous_;
 const auto speed=std::hypot(guide->character.velocity.x,guide->character.velocity.z);
 auto clip=GuidePresentationClip::idle;
 if(guide->intent==GuideIntent::follow&&guide->activity==GuideActivity::following&&speed>.12f)
  clip=speed>9.f?GuidePresentationClip::catchup:GuidePresentationClip::walk;
 else if(guidance)clip=GuidePresentationClip::guidance;
 float yaw=yaw_;
 if(speed>.12f)yaw=std::atan2(guide->character.velocity.x,guide->character.velocity.z);
 else if(!facing_initialized_){const auto dx=guide->destination.x-guide->character.feet.x,dz=guide->destination.z-guide->character.feet.z;if(std::hypot(dx,dz)>.01f)yaw=std::atan2(dx,dz);}
 const auto dt=std::min(elapsed,4./60);
 if(clip!=clip_){
  previous_clip_=clip_;
  previous_seconds_=seconds_;
  transition_elapsed_=0;
  clip_=clip;
  seconds_=0;
 }
 const auto clip_index=static_cast<std::size_t>(clip_);
 const double seconds=seconds_+dt;
 const double duration=mesh_->clips[clip_index].duration_seconds;
 const double phase=mesh_->clips[clip_index].looping?std::fmod(seconds,duration):std::min(seconds,duration);
 auto target_pose=sample_character_clip(*mesh_,clip_index,phase);
 if(transition_elapsed_<transition_duration_){
  transition_elapsed_+=dt;
  const auto prev_index=static_cast<std::size_t>(previous_clip_);
  previous_seconds_+=dt;
  const double prev_dur=mesh_->clips[prev_index].duration_seconds;
  const double prev_phase=mesh_->clips[prev_index].looping?std::fmod(previous_seconds_,prev_dur):std::min(previous_seconds_,prev_dur);
  const auto prev_pose=sample_character_clip(*mesh_,prev_index,prev_phase);
  const double u=std::clamp(transition_elapsed_/transition_duration_,0.0,1.0);
  const double w=u*u*(3.0-2.0*u);
  target_pose=blend_character_poses(prev_pose,target_pose,static_cast<float>(w));
 }
 CharacterInstance instance;instance.pose=target_pose;
 CharacterJointTransform world;world.translation=guide->character.feet;world.rotation={0,std::sin(yaw*.5f),0,std::cos(yaw*.5f)};
 instance.world=character_transform_matrix(world);instance.tint={.55f,.85f,1};instance.emission=.85f;instance.opacity=.78f;
 validate_character_instance(*mesh_,instance);
 // Publish presentation state only after complete bounded sampling succeeds.
 seconds_=phase;yaw_=yaw;facing_initialized_=true;previous_=instance;return instance;
}
void GuidePresentation::reset()noexcept{previous_.reset();clip_=GuidePresentationClip::idle;previous_clip_=GuidePresentationClip::idle;seconds_=0;previous_seconds_=0;transition_elapsed_=1.0;yaw_=0;facing_initialized_=false;}
}
