#pragma once
#include <aibs/physics.hpp>
#include <algorithm>
#include <cmath>
#include <optional>
#include <stdexcept>
#include <vector>
namespace workshop_tour_path {
using ::aibs::SceneSnapshot;using ::aibs::Vec3;using ::aibs::GroundedCharacter;using ::aibs::CharacterInput;
// Diagnostic collision queries only. No runtime actor, controller, save or
// journal is modified; the caller must walk every accepted segment normally.
// A cold controller may slide/step around a grazing corner differently from
// the live actor. Admit only a conservative straight capsule corridor as well
// as the physical dry run. This changes diagnostic plans, not BS's colliders.
inline bool corridor_clear(const SceneSnapshot& scene,Vec3 from,Vec3 to){
 const ::aibs::CharacterSettings settings;constexpr float margin=.10f,step_tolerance=.0001f;
 if(std::hypot(to.x-from.x,to.z-from.z)<1e-6f)return true;
 const float segment_half=settings.height*.5f-settings.radius;
 SceneSnapshot obstacles{scene.world_id,scene.revision,{}};obstacles.objects.reserve(scene.objects.size());
 for(const auto& original:scene.objects){
  const auto q=original.rotation;const double inv=1/std::sqrt(double(q.x)*q.x+double(q.y)*q.y+double(q.z)*q.z+double(q.w)*q.w);
  const double x=q.x*inv,y=q.y*inv,z=q.z*inv,w=q.w*inv;
  // World-Y components of the normalized OBB's three local axes.
  const double ax=2*(x*y+z*w),ay=1-2*(x*x+z*z),az=2*(y*z-x*w);
  const double top=original.center.y+std::abs(ax)*original.half_extent.x+std::abs(ay)*original.half_extent.y+std::abs(az)*original.half_extent.z;
  // Low support and step surfaces still go through the actual physics query.
  if(top<=std::min(from.y,to.y)+settings.step_height+step_tolerance)continue;
  auto proxy=original;proxy.selectable=true;
  proxy.half_extent.x+=settings.radius+margin+segment_half*static_cast<float>(std::abs(ax));
  proxy.half_extent.y+=settings.radius+margin+segment_half*static_cast<float>(std::abs(ay));
  proxy.half_extent.z+=settings.radius+margin+segment_half*static_cast<float>(std::abs(az));
  obstacles.objects.push_back(std::move(proxy));
 }
 const Vec3 a{from.x,from.y+settings.height*.5f,from.z},b{to.x,to.y+settings.height*.5f,to.z};
 const Vec3 direction{b.x-a.x,b.y-a.y,b.z-a.z};const float length=std::hypot(direction.x,direction.y,direction.z);
 return !::aibs::pick_scene(obstacles,a,direction,length).has_value();
}

inline bool clear(const SceneSnapshot& scene,Vec3 from,const std::vector<Vec3>& points,float minimum_y,Vec3* standing=nullptr){
 if(points.empty()||points.size()>3)return false;
 try{
  GroundedCharacter query(scene,from);for(unsigned n=0;n<12;++n)(void)query.advance({},1./60);
  for(const auto target:points){const auto actual_start=query.state().feet;
   if(std::hypot(query.state().feet.x-target.x,query.state().feet.z-target.z)>16)return false;bool reached=false;
   for(unsigned n=0;n<600;++n){const auto feet=query.state().feet;const auto length=std::hypot(feet.x-target.x,feet.z-target.z);
    if(length<.14f){reached=true;break;}CharacterInput input;input.move={(target.x-feet.x)/length,0,(target.z-feet.z)/length};
    if(query.advance(input,1./60).feet.y<minimum_y)return false;
   }
   if(!reached||!query.state().grounded)return false;
   if(!corridor_clear(scene,actual_start,query.state().feet))return false;
  }
  if(standing)*standing=query.state().feet;return true;
 }catch(const std::invalid_argument&){return false;}
}
inline std::vector<Vec3> return_plan(const SceneSnapshot& scene,Vec3 from,Vec3 anchor,float minimum_y){
 if(clear(scene,from,{anchor},minimum_y))return {anchor};
 // At most24 dogleg queries, each with at most3 segments/600 steps per
 // segment. Approach tolerance or a resumed idle step can move BS away from
 // an ideal outward waypoint; never assume its reverse remains walkable.
 for(const float margin:{0.f,.5f,1.f,1.5f,2.f,3.f}){
  for(const float z:{std::min(from.z,anchor.z)-margin,std::max(from.z,anchor.z)+margin}){
   std::vector<Vec3> plan{{from.x,from.y,z},{anchor.x,anchor.y,z},anchor};if(clear(scene,from,plan,minimum_y))return plan;
  }
  for(const float x:{std::min(from.x,anchor.x)-margin,std::max(from.x,anchor.x)+margin}){
   std::vector<Vec3> plan{{x,from.y,from.z},{x,anchor.y,anchor.z},anchor};if(clear(scene,from,plan,minimum_y))return plan;
  }
 }
 return {};
}
// Stations retain their tight authored interaction approach. Validate its
// physical landing and modeled reverse, then check the observed live pose at
// runtime before sending the action and again after its actual outcome.
inline bool reversible_station(const SceneSnapshot& scene,Vec3 from,const std::vector<Vec3>& outward,
 Vec3 anchor,float minimum_y,Vec3* standing=nullptr,std::vector<Vec3>* returning=nullptr){
 Vec3 landing;if(!clear(scene,from,outward,minimum_y,&landing))return false;
 std::vector<Vec3> back;for(std::size_t n=outward.size();n>1;--n)back.push_back(outward[n-2]);back.push_back(anchor);
 if(!clear(scene,landing,back,minimum_y))back=return_plan(scene,landing,anchor,minimum_y);if(back.empty())return false;
 if(standing)*standing=landing;if(returning)*returning=back;return true;
}
// Reading panels: validate the outward landing AND a common return from nine samples
// in the square around the live controller's .35m arrival tolerance. A cold query
// stopping .14m short of a fixture is not evidence that a closer live landing
// can leave it. Samples are a candidate filter, not continuous coverage or a
// wider BS capsule; the observed live pose must be checked independently.
inline bool reversible(const SceneSnapshot& scene,Vec3 from,const std::vector<Vec3>& outward,
 Vec3 anchor,float minimum_y,Vec3* standing=nullptr,std::vector<Vec3>* returning=nullptr){
 Vec3 landing;std::vector<Vec3> back;if(!reversible_station(scene,from,outward,anchor,minimum_y,&landing,&back))return false;
 constexpr float tolerance=.35f;
 const auto requested=outward.back();
 for(const float dx:{-tolerance,0.f,tolerance})for(const float dz:{-tolerance,0.f,tolerance}){
  const Vec3 pose{requested.x+dx,landing.y,requested.z+dz};
  if(!corridor_clear(scene,pose,back.front())||!clear(scene,pose,back,minimum_y))return false;
 }
 if(standing)*standing=landing;if(returning)*returning=back;return true;
}
struct BlockerDiagnostic {std::string id,name;Vec3 center{},half_extent{};double clearance=0;};
// Evidence only: nearest capsule-envelope clearance at the observed pose.
// The actual corridor/physics predicates still decide whether a route passes.
inline std::optional<BlockerDiagnostic> nearest_blocker(const SceneSnapshot& scene,Vec3 feet){
 const ::aibs::CharacterSettings settings;constexpr double margin=.10,step_tolerance=.0001;
 const double segment_half=settings.height*.5-settings.radius;
 std::optional<BlockerDiagnostic> closest;
 for(const auto& object:scene.objects){
  const auto q=object.rotation;const double norm=std::sqrt(double(q.x)*q.x+double(q.y)*q.y+double(q.z)*q.z+double(q.w)*q.w);
  if(!std::isfinite(norm)||norm<=0)continue;
  const double x=q.x/norm,y=q.y/norm,z=q.z/norm,w=q.w/norm;
  const double ax=2*(x*y+z*w),ay=1-2*(x*x+z*z),az=2*(y*z-x*w);
  const double top=object.center.y+std::abs(ax)*object.half_extent.x+std::abs(ay)*object.half_extent.y+std::abs(az)*object.half_extent.z;
  if(top<=feet.y+settings.step_height+step_tolerance)continue;
  const double px=double(feet.x)-object.center.x,py=double(feet.y)+settings.height*.5-object.center.y,pz=double(feet.z)-object.center.z;
  // Conjugate normalized quaternion: world body centre into collider-local axes.
  const double tx=2*(-y*pz+z*py),ty=2*(-z*px+x*pz),tz=2*(-x*py+y*px);
  const double lx=px+w*tx-y*tz+z*ty,ly=py+w*ty-z*tx+x*tz,lz=pz+w*tz-x*ty+y*tx;
  const double dx=std::abs(lx)-object.half_extent.x-settings.radius-margin-segment_half*std::abs(ax);
  const double dy=std::abs(ly)-object.half_extent.y-settings.radius-margin-segment_half*std::abs(ay);
  const double dz=std::abs(lz)-object.half_extent.z-settings.radius-margin-segment_half*std::abs(az);
  const double clearance=dx<=0&&dy<=0&&dz<=0?std::max({dx,dy,dz}):std::hypot(std::max(0.,dx),std::max(0.,dy),std::max(0.,dz));
  if(!closest||clearance<closest->clearance)closest=BlockerDiagnostic{object.persistent_id,object.name,object.center,object.half_extent,clearance};
 }
 return closest;
}
}
