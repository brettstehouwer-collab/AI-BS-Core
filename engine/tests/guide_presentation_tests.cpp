#include <aibs/guide_presentation.hpp>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <malloc.h>
#include <new>
#include <stdexcept>

namespace {bool track_allocations=false;std::size_t allocations=0;}
void* operator new(std::size_t size){if(track_allocations)++allocations;if(void* p=std::malloc(size?size:1))return p;throw std::bad_alloc();}
void* operator new[](std::size_t size){return ::operator new(size);}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete[](void* p)noexcept{std::free(p);}
void operator delete(void* p,std::size_t)noexcept{std::free(p);}
void operator delete[](void* p,std::size_t)noexcept{std::free(p);}
void* operator new(std::size_t size,std::align_val_t alignment){if(track_allocations)++allocations;if(void* p=_aligned_malloc(size?size:1,static_cast<std::size_t>(alignment)))return p;throw std::bad_alloc();}
void* operator new[](std::size_t size,std::align_val_t alignment){return ::operator new(size,alignment);}
void operator delete(void* p,std::align_val_t)noexcept{_aligned_free(p);}
void operator delete[](void* p,std::align_val_t)noexcept{_aligned_free(p);}
void operator delete(void* p,std::size_t,std::align_val_t)noexcept{_aligned_free(p);}
void operator delete[](void* p,std::size_t,std::align_val_t)noexcept{_aligned_free(p);}

using namespace aibs;
namespace {
unsigned checks=0;
void need(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
bool near(float a,float b,float epsilon=1e-4f){return std::abs(a-b)<=epsilon;}
template<class F>void reject(F f,const char* message){bool rejected=false;try{f();}catch(const std::invalid_argument&){rejected=true;}need(rejected,message);}
GuideState guide(Vec3 feet={2,0,3},Vec3 velocity={}){
 GuideState g;g.character.feet=feet;g.character.velocity=velocity;g.character.grounded=true;
 g.destination={feet.x,feet.y,feet.z+3};g.activity=GuideActivity::near_player;return g;
}
float moved(const CharacterMesh& m,const CharacterPose& a,const CharacterPose& b){
 const auto first=character_skin_palette(m,a),second=character_skin_palette(m,b);float total=0;
 for(const auto& vertex:m.vertices){const auto p=character_skin_vertex(vertex,first),q=character_skin_vertex(vertex,second);total+=std::abs(p.position.x-q.position.x)+std::abs(p.position.y-q.position.y)+std::abs(p.position.z-q.position.z);}
 return total;
}
}
int main(){try{
 const auto mesh=make_guide_placeholder();validate_character_mesh(mesh);
 need(mesh.joints.size()>=15&&mesh.joints.size()<=64,"Placeholder requires articulated limbs");
 need(mesh.clips.size()==4,"Four authored animation clips required");
 need(mesh.vertices.size()>100&&mesh.indices.size()>500,"Indexed articulated body geometry required");
 float bottom=100,top=-100;for(const auto& v:mesh.vertices){bottom=std::min(bottom,v.position.y);top=std::max(top,v.position.y);}
 need(near(bottom,0)&&near(top,1.8f),"Placeholder must use feet origin and1.8m height");
 const auto bind=character_bind_pose(mesh);const auto palette=character_skin_palette(mesh,bind);
 for(const auto& v:mesh.vertices){const auto p=character_skin_vertex(v,palette);need(near(p.position.x,v.position.x)&&near(p.position.y,v.position.y)&&near(p.position.z,v.position.z),"Inverse binds alter rest geometry");}
 for(std::size_t clip=0;clip<mesh.clips.size();++clip){
  need(mesh.clips[clip].frame_count>=17,"Authored motion requires baked samples");
  const auto first=sample_character_clip(mesh,clip,0),later=sample_character_clip(mesh,clip,mesh.clips[clip].duration_seconds*.25);
  need(moved(mesh,first,later)>.01f,"Clip changes no actual skinned geometry");
  for(const auto& pose:mesh.clips[clip].samples){need(std::isfinite(pose.translation.x)&&std::isfinite(pose.translation.y)&&std::isfinite(pose.translation.z),"Nonfinite authored pose");}
  for(std::size_t frame=0;frame<mesh.clips[clip].frame_count;++frame)need(mesh.clips[clip].samples[frame*mesh.joints.size()].translation==mesh.joints[0].bind_local.translation,"Animation owns navigation movement");
 }
 const auto asymmetric=character_skin_palette(mesh,sample_character_clip(mesh,1,.25));
 const auto left=character_skin_vertex(mesh.vertices[12*24],asymmetric),right=character_skin_vertex(mesh.vertices[15*24],asymmetric);
 need(std::abs(left.position.z-right.position.z)>.05f,"Walk limbs do not use asymmetric articulated motion");
 GuidePresentation presenter(mesh);
 need(!presenter.sample({},.01),"Missing guide creates world-origin character");
 auto g=guide();const auto initial=presenter.sample(g,0);need(initial.has_value(),"Valid grounded guide is hidden");
 need(near(initial->world[12],2)&&near(initial->world[13],0)&&near(initial->world[14],3),"Guide world transform does not use actual feet");
 need(presenter.clip()==GuidePresentationClip::idle,"Stationary guide is not idle");
 need(initial->opacity>.5f&&initial->opacity<1&&initial->emission>0,"Placeholder must be a steady luminous silhouette");
 const auto before=presenter.animation_seconds();presenter.sample(g,.02);need(presenter.animation_seconds()>before,"Live animation clock did not advance");
 const auto frozen=presenter.sample(g,0);const auto frozen_time=presenter.animation_seconds();g.character.feet={80,2,40};
 const auto paused=presenter.sample(g,.03,true);need(paused&&paused->world==frozen->world&&moved(mesh,paused->pose,frozen->pose)<1e-6f&&presenter.animation_seconds()==frozen_time,"Pause changes presentation pose/time");
 g=guide({2,0,3},{3,0,0});g.activity=GuideActivity::following;
 auto walk=presenter.sample(g,.02);need(walk&&presenter.clip()==GuidePresentationClip::walk,"Moving guide did not use walk clip");
 need(near(presenter.yaw(),1.57079632679f)&&near(walk->world[8],1)&&near(walk->world[10],0),"Visual facing does not follow actual motion");
 auto stopped=g;stopped.character.velocity={};stopped.activity=GuideActivity::near_player;presenter.sample(stopped,.01);
 need(near(presenter.yaw(),1.57079632679f),"Idle guide loses facing");
 g.character.velocity={0,0,13};presenter.sample(g,.02);need(presenter.clip()==GuidePresentationClip::catchup,"Catch-up velocity did not use catch-up clip");
 g.character.velocity={};g.activity=GuideActivity::waiting;g.intent=GuideIntent::wait;presenter.sample(g,.02,false,false,true);
 need(presenter.clip()==GuidePresentationClip::guidance,"Explicit restrained guidance clip missing");
 need(!presenter.sample(g,.01,false,true),"Recall-required guide remains visible");
 g.character.grounded=false;need(presenter.sample(g,.01).has_value(),"Finite live guide must remain visible through a transient support flag");
 g=guide();g.character.feet.x=std::numeric_limits<float>::infinity();need(!presenter.sample(g,.01),"Nonfinite guide remains visible");
 g=guide();g.destination.z=1000001;need(!presenter.sample(g,.01),"Out-of-bounds destination remains visible");
 g=guide();g.character.velocity.y=std::numeric_limits<float>::quiet_NaN();need(!presenter.sample(g,.01),"Nonfinite velocity remains visible");
 g=guide();g.activity=static_cast<GuideActivity>(100);need(!presenter.sample(g,.01),"Unknown guide activity remains visible");
 g=guide();presenter.sample(g,.02);const auto prior=presenter.animation_seconds();
 reject([&]{presenter.sample(g,-1);},"Negative elapsed accepted");need(presenter.animation_seconds()==prior,"Bad elapsed changes animation state");
 reject([&]{presenter.sample(g,std::numeric_limits<double>::infinity());},"Infinite elapsed accepted");
 auto bad=mesh;bad.clips[1].name="unrelated";reject([&]{GuidePresentation ignored(bad);},"Unrelated clip contract accepted");
 presenter.reset();need(presenter.animation_seconds()==0&&presenter.yaw()==0,"Reset retained ephemeral state");
 presenter.sample(g,100);need(presenter.animation_seconds()<=4./60+1e-8,"Dropped frame advanced unbounded animation time");
 const auto vertex_pointer=mesh.vertices.data();const auto sample_pointer=mesh.clips[1].samples.data();
 const auto index_pointer=mesh.indices.data();g=guide({2,0,3},{3,0,0});g.activity=GuideActivity::following;
 const auto allocation_start=allocations;track_allocations=true;
 for(unsigned frame=0;frame<1000;++frame){g.character.grounded=frame%2==0;need(presenter.sample(g,1./120).has_value(),"Ground-contact transitions hide a valid live figure");}
 track_allocations=false;
 need(allocations==allocation_start,"Ordinary presentation frames allocate dynamic storage");
 need(mesh.vertices.data()==vertex_pointer&&mesh.indices.data()==index_pointer&&mesh.clips[1].samples.data()==sample_pointer,"Presentation replaced owned character resources");
 const auto cost=character_mesh_cost(mesh);need(cost.payload_bytes<256*1024&&cost.gpu_vertex_bytes+cost.gpu_index_bytes<128*1024,"Temporary figure exceeds small resource budget");
 std::cout<<"PASS "<<checks<<" articulated guide presentation checks\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
