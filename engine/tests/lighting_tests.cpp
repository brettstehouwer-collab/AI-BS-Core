#include <aibs/lighting.hpp>
#include <cmath>
#include <cstddef>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {
unsigned checks=0;
void need(bool b,const char* text){++checks;if(!b)throw std::runtime_error(text);}
void close(float a,float b,float tolerance=2e-5f){need(std::abs(a-b)<=tolerance,"Lighting numeric reference mismatch");}
void close(Vec3 a,Vec3 b,float tolerance=2e-5f){close(a.x,b.x,tolerance);close(a.y,b.y,tolerance);close(a.z,b.z,tolerance);}
template<class F>void reject(F f){bool failed=false;try{f();}catch(const std::invalid_argument&){failed=true;}need(failed,"Expected lighting rejection");}
std::array<float,4> project(const std::array<float,16>& m,Vec3 p){std::array<float,4> r{};for(unsigned c=0;c<4;++c)r[c]=p.x*m[c]+p.y*m[4+c]+p.z*m[8+c]+m[12+c];return r;}
}
int main(){try{
 static_assert(sizeof(GpuPointLight)==32&&alignof(GpuPointLight)==16);
 static_assert(sizeof(GpuLightingConstants)==1168&&alignof(GpuLightingConstants)==16);
 static_assert(offsetof(GpuLightingConstants,points)==144);
 SceneLighting s;validate_scene_lighting(s);need(!s.enabled,"Legacy authored lighting is opt-in");
 auto packed=pack_scene_lighting(s);need(packed.controls[0]==0&&packed.controls[1]==0&&packed.controls[2]==0,"Disabled GPU controls remain explicit");
 need(packed.shadow_view_projection[0]==1&&packed.shadow_view_projection[15]==1,"Disabled shadow matrix is identity");
 reject([&]{evaluate_scene_lighting(s,{},{0,1,0},{1,1,1},0);});
 s.enabled=true;s.ambient={1,1,1};
 close(evaluate_scene_lighting(s,{},{0,1,0},{1,1,1},0),{.816469966f,.816469966f,.816469966f});
 s.exposure=2;close(evaluate_scene_lighting(s,{},{0,1,0},{1,1,1},0),{.937976606f,.937976606f,.937976606f});
 s.exposure=1;s.ambient={};s.directional=DirectionalLight{};
 close(evaluate_scene_lighting(s,{},{0,1,0},{1,1,1},0),{.816469966f,.816469966f,.816469966f});
 close(evaluate_scene_lighting(s,{},{0,-1,0},{1,1,1},0),{});
 close(evaluate_scene_lighting(s,{},{0,7,0},{1,1,1},0),{.816469966f,.816469966f,.816469966f});
 s.directional.reset();s.points={PointLight{{0,2,0},{1,1,1},4,4}};
 close(evaluate_scene_lighting(s,{},{0,1,0},{1,1,1},0),{.816469966f,.816469966f,.816469966f});
 close(evaluate_scene_lighting(s,{0,-2,0},{0,1,0},{1,1,1},0),{});
 close(evaluate_scene_lighting(s,{0,-3,0},{0,1,0},{1,1,1},0),{});
 s.points={{PointLight{{0,0,0},{1,1,1},1,4}}};
 close(evaluate_scene_lighting(s,{},{0,1,0},{1,1,1},0),{.816469966f,.816469966f,.816469966f});
 s.points.clear();close(evaluate_scene_lighting(s,{},{0,1,0},{1,1,1},1),{.816469966f,.816469966f,.816469966f});
 s.ambient={1,1,1};close(evaluate_scene_lighting(s,{},{0,1,0},{.25f,.5f,1},0),{.507659454f,.660262298f,.816469966f});
 s.directional=DirectionalLight{{0,0,1},{1,.5f,.25f},2};s.points={{PointLight{{2,3,4},{.5f,.2f,1},3,8}}};s.shadow.enabled=true;s.shadow.center={10,20,30};s.shadow.half_extent=10;s.shadow.near_plane=1;s.shadow.far_plane=21;
 const auto matrix=directional_shadow_matrix(s);auto p=project(matrix,{10,20,30});close(p[0],0);close(p[1],0);close(p[2],.5f);close(p[3],1);
 p=project(matrix,{20,30,40});close(p[0],1);close(p[1],1);close(p[2],1);
 p=project(matrix,{0,10,20});close(p[0],-1);close(p[1],-1);close(p[2],0);
 packed=pack_scene_lighting(s);need(packed.controls==std::array<std::uint32_t,4>{1,1,1,1024},"Packed counts and feature flags");
 need(packed.direction_intensity==std::array<float,4>{0,0,1,2},"Directional ray direction/intensity packing");
 need(packed.points[0].position_radius==std::array<float,4>{2,3,4,8}&&packed.points[0].color_intensity==std::array<float,4>{.5f,.2f,1,3},"Point constant layout");
 need(packed.points[1].position_radius==std::array<float,4>{}&&packed.points[31].color_intensity==std::array<float,4>{},"Unused GPU constants zero initialized");
 need(packed.shadow_view_projection==matrix,"Packed shadow transform is unchanged");
 close(packed.shadow_parameters[0],s.shadow.bias);close(packed.shadow_parameters[1],1.f/1024);
 s.directional->direction={0,-1,0};const auto vertical=directional_shadow_matrix(s);for(float v:vertical)need(std::isfinite(v),"Vertical shadow light cannot form NaNs");
 p=project(vertical,s.shadow.center);close(p[0],0);close(p[1],0);close(p[2],.5f);
 s.directional->direction={.26726124f,.53452248f,.80178373f};const auto diagonal=directional_shadow_matrix(s);p=project(diagonal,s.shadow.center);close(p[0],0);close(p[1],0);close(p[2],.5f);
 const Vec3 near_center{s.shadow.center.x-s.directional->direction.x*10,s.shadow.center.y-s.directional->direction.y*10,s.shadow.center.z-s.directional->direction.z*10};
 const Vec3 far_center{s.shadow.center.x+s.directional->direction.x*10,s.shadow.center.y+s.directional->direction.y*10,s.shadow.center.z+s.directional->direction.z*10};
 p=project(diagonal,near_center);close(p[0],0);close(p[1],0);close(p[2],0);
 p=project(diagonal,far_center);close(p[0],0);close(p[1],0);close(p[2],1);
 auto translated=s;translated.shadow.center={110,70,-20};const Vec3 translated_point{110,70,-20};p=project(directional_shadow_matrix(translated),translated_point);close(p[0],0);close(p[1],0);close(p[2],.5f);
 const auto valid=s;
 auto bad=valid;bad.exposure=0;reject([&]{validate_scene_lighting(bad);});bad=valid;bad.exposure=17;reject([&]{pack_scene_lighting(bad);});
 bad=valid;bad.directional->direction={};reject([&]{validate_scene_lighting(bad);});bad=valid;bad.directional->direction={1,1,1};reject([&]{validate_scene_lighting(bad);});
 bad=valid;bad.directional->intensity=101;reject([&]{validate_scene_lighting(bad);});bad=valid;bad.points[0].radius=.05f;reject([&]{validate_scene_lighting(bad);});
 bad=valid;bad.points.resize(33);reject([&]{validate_scene_lighting(bad);});
 bad=valid;bad.points[0].position.x=std::numeric_limits<float>::quiet_NaN();reject([&]{pack_scene_lighting(bad);});
 bad=valid;bad.points[0].position.z=1000001;reject([&]{validate_scene_lighting(bad);});
 bad=valid;bad.points[0].intensity=-1;reject([&]{validate_scene_lighting(bad);});bad=valid;bad.points[0].radius=std::numeric_limits<float>::infinity();reject([&]{validate_scene_lighting(bad);});
 bad=valid;bad.points[0].color.x=-1;reject([&]{validate_scene_lighting(bad);});bad=valid;bad.ambient.z=2;reject([&]{validate_scene_lighting(bad);});
 bad=valid;bad.shadow.resolution=4096;reject([&]{validate_scene_lighting(bad);});bad=valid;bad.shadow.half_extent=0;reject([&]{directional_shadow_matrix(bad);});
 bad=valid;bad.shadow.far_plane=bad.shadow.near_plane;reject([&]{validate_scene_lighting(bad);});bad=valid;bad.shadow.bias=-.01f;reject([&]{validate_scene_lighting(bad);});
 bad=valid;bad.shadow.far_plane=bad.shadow.near_plane+.01f;reject([&]{validate_scene_lighting(bad);});bad=valid;bad.shadow.center.x=std::numeric_limits<float>::infinity();reject([&]{validate_scene_lighting(bad);});
 bad=valid;bad.directional.reset();reject([&]{validate_scene_lighting(bad);});bad=valid;bad.enabled=false;reject([&]{validate_scene_lighting(bad);});
 reject([&]{evaluate_scene_lighting(valid,{},{},{1,1,1},0);});reject([&]{evaluate_scene_lighting(valid,{},{0,1,0},{2,1,1},0);});reject([&]{evaluate_scene_lighting(valid,{},{0,1,0},{1,1,1},-1);});
 s=valid;s.points.resize(32);s.shadow.resolution=2048;validate_scene_lighting(s);need(pack_scene_lighting(s).controls[1]==32,"Maximum point count admitted");
 s.exposure=16;s.ambient={1,1,1};s.directional=DirectionalLight{{0,-1,0},{1,1,1},100};for(auto& light:s.points)light={{0,0,0},{1,1,1},100,500};
 close(evaluate_scene_lighting(s,{},{0,1,0},{1,1,1},16),{1,1,1});
 s=valid;s.shadow.enabled=false;s.directional.reset();s.ambient={};s.points={PointLight{{0,0,0},{1,1,1},1,4}};
 const auto almost_edge=evaluate_scene_lighting(s,{0,-3.9f,0},{0,1,0},{1,1,1},0);
 const auto nearer=evaluate_scene_lighting(s,{0,-3.8f,0},{0,1,0},{1,1,1},0);
 need(almost_edge.x>0&&almost_edge.x<nearer.x&&nearer.x<1,"Point falloff fades continuously near its finite radius");
 close(evaluate_scene_lighting(s,{0,-4,0},{0,1,0},{1,1,1},0),{});
 need(valid==valid,"Lighting snapshots are values");
 std::cout<<"PASS "<<checks<<" CPU lighting, exposure, attenuation, shadow projection, packing and malformed-data contracts\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
