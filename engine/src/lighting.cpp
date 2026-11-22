#include <aibs/lighting.hpp>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace aibs {namespace {
void need(bool value,const char* message){if(!value)throw std::invalid_argument(message);}
bool finite(Vec3 v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z);}
bool bounded(Vec3 v){return finite(v)&&std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<=1000000;}
bool unit(float x){return std::isfinite(x)&&x>=0&&x<=1;}
bool color(Vec3 v){return unit(v.x)&&unit(v.y)&&unit(v.z);}
double length_squared(Vec3 v){return static_cast<double>(v.x)*v.x+static_cast<double>(v.y)*v.y+static_cast<double>(v.z)*v.z;}
using V=std::array<double,3>;
V vector(Vec3 v){return {v.x,v.y,v.z};}
double dot(V a,V b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
V cross(V a,V b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
V normalized(V value){const auto length=std::sqrt(dot(value,value));need(std::isfinite(length)&&length>0,"Lighting requires a finite nonzero normal/direction");for(auto& n:value)n/=length;return value;}
std::array<float,4> values(Vec3 v,float w){return {v.x,v.y,v.z,w};}
constexpr std::array<float,16> identity{1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
float transfer(double linear){return static_cast<float>(linear<=.0031308?12.92*linear:1.055*std::pow(linear,1./2.4)-.055);}
}
void validate_scene_lighting(const SceneLighting& s){
 need(color(s.ambient),"Lighting ambient requires normalized finite RGB");
 need(std::isfinite(s.exposure)&&s.exposure>=.05f&&s.exposure<=16,"Lighting exposure outside .05..16");
 need(s.points.size()<=scene_lighting_maximum_points,"Lighting exceeds32 point lights");
 if(s.directional){const auto& d=*s.directional;
  need(finite(d.direction)&&std::abs(length_squared(d.direction)-1)<=1e-4,"Directional light requires finite unit ray direction");
  need(color(d.color)&&std::isfinite(d.intensity)&&d.intensity>=0&&d.intensity<=100,"Directional light color/intensity outside profile");
 }
 for(const auto& p:s.points){
  need(bounded(p.position)&&color(p.color)&&std::isfinite(p.intensity)&&p.intensity>=0&&p.intensity<=100,"Point light position/color/intensity outside profile");
  need(std::isfinite(p.radius)&&p.radius>.05f&&p.radius<=500,"Point light radius outside .05..500");
 }
 const auto& shadow=s.shadow;
 need(bounded(shadow.center)&&std::isfinite(shadow.half_extent)&&shadow.half_extent>=.25f&&shadow.half_extent<=4096,"Directional shadow bounds outside profile");
 need(std::isfinite(shadow.near_plane)&&std::isfinite(shadow.far_plane)&&shadow.near_plane>=.01f&&shadow.near_plane<=4096&&shadow.far_plane<=100000&&static_cast<double>(shadow.far_plane)-shadow.near_plane>=.1,"Directional shadow depth outside profile");
 need((shadow.resolution==1024||shadow.resolution==2048)&&std::isfinite(shadow.bias)&&shadow.bias>=0&&shadow.bias<=.05f,"Directional shadow resolution/bias outside profile");
 need(!shadow.enabled||(s.enabled&&s.directional.has_value()),"Directional shadows require enabled authored directional light");
}
std::array<float,16> directional_shadow_matrix(const SceneLighting& s){
 validate_scene_lighting(s);need(s.directional.has_value(),"Directional shadow transform requires directional light");
 const auto forward=normalized(vector(s.directional->direction));V up{0,1,0};
 if(std::abs(dot(up,forward))>.98)up={0,0,1};
 const auto right=normalized(cross(up,forward));up=cross(forward,right);
 const auto& shadow=s.shadow;auto eye=vector(shadow.center);
 const double middle=(static_cast<double>(shadow.near_plane)+shadow.far_plane)*.5;
 for(unsigned c=0;c<3;++c)eye[c]-=forward[c]*middle;
 const double inverse_extent=1./shadow.half_extent,inverse_depth=1./(static_cast<double>(shadow.far_plane)-shadow.near_plane);
 std::array<float,16> matrix{};
 for(unsigned row=0;row<3;++row){matrix[row*4]=static_cast<float>(right[row]*inverse_extent);matrix[row*4+1]=static_cast<float>(up[row]*inverse_extent);matrix[row*4+2]=static_cast<float>(forward[row]*inverse_depth);}
 matrix[12]=static_cast<float>(-dot(eye,right)*inverse_extent);
 matrix[13]=static_cast<float>(-dot(eye,up)*inverse_extent);
 matrix[14]=static_cast<float>((-dot(eye,forward)-shadow.near_plane)*inverse_depth);matrix[15]=1;
 for(const auto n:matrix)need(std::isfinite(n),"Directional shadow transform overflow");return matrix;
}
GpuLightingConstants pack_scene_lighting(const SceneLighting& s){
 validate_scene_lighting(s);GpuLightingConstants result;
 result.ambient_exposure=values(s.ambient,s.exposure);
 if(s.directional){result.direction_intensity=values(s.directional->direction,s.directional->intensity);result.directional_color=values(s.directional->color,0);}
 result.controls={s.enabled?1u:0u,static_cast<std::uint32_t>(s.points.size()),s.shadow.enabled?1u:0u,s.shadow.resolution};
 result.shadow_view_projection=s.shadow.enabled?directional_shadow_matrix(s):identity;
 result.shadow_parameters={s.shadow.bias,1.f/static_cast<float>(s.shadow.resolution),0,0};
 for(std::size_t i=0;i<s.points.size();++i){const auto& p=s.points[i];result.points[i].position_radius=values(p.position,p.radius);result.points[i].color_intensity=values(p.color,p.intensity);}
 return result;
}
Vec3 evaluate_scene_lighting(const SceneLighting& s,Vec3 position,Vec3 normal,Vec3 base_color,float emission){
 validate_scene_lighting(s);need(s.enabled,"CPU authored lighting oracle requires enabled scene");
 need(bounded(position)&&bounded(normal)&&length_squared(normal)>0&&color(base_color),"Lighting evaluation requires bounded position/normal and normalized base color");
 need(std::isfinite(emission)&&emission>=0&&emission<=16,"Lighting emission outside0..16");
 const auto n=normalized(vector(normal));V irradiance=vector(s.ambient);
 if(s.directional){const auto& d=*s.directional;const auto direction=normalized(vector(d.direction));const auto lambert=std::max(0.,-dot(n,direction))*d.intensity;const auto c=vector(d.color);for(unsigned k=0;k<3;++k)irradiance[k]+=c[k]*lambert;}
 for(const auto& p:s.points){V delta{static_cast<double>(p.position.x)-position.x,static_cast<double>(p.position.y)-position.y,static_cast<double>(p.position.z)-position.z};const auto distance=std::sqrt(dot(delta,delta));if(distance>=p.radius)continue;
  const auto direction=distance<=1e-6?n:normalized(delta);const double falloff=1-distance/p.radius;const auto strength=std::max(0.,dot(n,direction))*p.intensity*falloff*falloff;const auto c=vector(p.color);for(unsigned k=0;k<3;++k)irradiance[k]+=c[k]*strength;
 }
 const auto base=vector(base_color);std::array<float,3> output{};
 for(unsigned k=0;k<3;++k){const auto radiance=base[k]*(irradiance[k]+emission);const auto mapped=-std::expm1(-radiance*s.exposure);output[k]=transfer(std::clamp(mapped,0.,1.));}
 return {output[0],output[1],output[2]};
}
}
