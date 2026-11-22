#include <aibs/guide_camera.hpp>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {unsigned checks=0;void check(bool value,const char* why){++checks;if(!value)throw std::runtime_error(why);}}
int main(){try{
 const Vec3 feet{};check(guide_camera_visibility({0,1.62f,0},feet)==0,"Camera inside guide must hide the figure");
 check(guide_camera_visibility({.35f,1.62f,0},feet)==0,"Inner clearance boundary must hide");
 check(guide_camera_visibility({.9f,1.62f,0},feet)==1,"Comfortable viewing distance must retain full appearance");
 check(std::abs(guide_camera_visibility({.625f,1.62f,0},feet)-.5f)<1e-5f,"Mid-clearance hologram must fade smoothly");
 float previous=0;for(unsigned n=0;n<=200;++n){const auto v=guide_camera_visibility({n*.01f,1.62f,0},feet);check(v>=previous&&v>=0&&v<=1,"Clearance opacity must be bounded and monotonic");previous=v;}
 check(guide_camera_visibility({0,4,0},feet)==1,"A camera above another floor must not hide a distant figure");
 check(guide_camera_visibility({0,-2,0},feet)==1,"Vertical distance must count below the guide too");
 check(std::abs(guide_camera_visibility({10.625f,21.62f,-30},{10,20,-30})-.5f)<1e-5f,"Translation changed visual clearance");
 check(guide_camera_visibility({std::numeric_limits<float>::max(),0,0},{-std::numeric_limits<float>::max(),0,0})==1,"Finite large offsets overflowed visibility");
 check(guide_camera_visibility({std::numeric_limits<float>::quiet_NaN(),0,0},feet)==0,"Invalid camera must not draw");
 check(guide_camera_visibility({}, {0,std::numeric_limits<float>::infinity(),0})==0,"Invalid guide position must not draw");
 GuideCameraClearance invalid;invalid.visible_distance=invalid.hidden_distance;check(guide_camera_visibility({1,1,0},feet,invalid)==0,"Degenerate fade interval accepted");
 invalid={};invalid.body_top=invalid.body_bottom;check(guide_camera_visibility({1,1,0},feet,invalid)==0,"Degenerate body interval accepted");
 invalid={};invalid.hidden_distance=-1;check(guide_camera_visibility({1,1,0},feet,invalid)==0,"Negative hidden radius accepted");
 std::cout<<checks<<" guide-camera clearance checks passed\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
