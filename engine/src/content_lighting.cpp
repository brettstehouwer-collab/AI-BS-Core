#include <aibs/content_lighting.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace aibs {namespace {
void need(bool value,const char* message){if(!value)throw std::invalid_argument(message);}
void shadow_bounds(SceneLighting& lighting,const SceneSnapshot& scene){
 need(!scene.objects.empty(),"Authored directional shadow requires chapter geometry");
 std::array<double,3> low{std::numeric_limits<double>::infinity(),std::numeric_limits<double>::infinity(),std::numeric_limits<double>::infinity()};
 std::array<double,3> high{-low[0],-low[1],-low[2]};
 for(const auto& object:scene.objects){
  // A sphere around each oriented collision box bounds all rotations. Imported
  // visuals retain their own explicit proxies; they never enlarge this world.
  const auto h=object.half_extent;
  const double radius=std::sqrt(static_cast<double>(h.x)*h.x+static_cast<double>(h.y)*h.y+static_cast<double>(h.z)*h.z);
  need(std::isfinite(radius)&&radius>0,"Invalid static geometry shadow bounds");
  const std::array<double,3> center{object.center.x,object.center.y,object.center.z};
  for(unsigned axis=0;axis<3;++axis){low[axis]=std::min(low[axis],center[axis]-radius);high[axis]=std::max(high[axis],center[axis]+radius);}
 }
 std::array<double,3> center{},half{};
 for(unsigned axis=0;axis<3;++axis){center[axis]=(low[axis]+high[axis])*.5;half[axis]=(high[axis]-low[axis])*.5;}
 const double radius=std::sqrt(half[0]*half[0]+half[1]*half[1]+half[2]*half[2])+2;
 need(std::isfinite(radius)&&radius>=.25&&radius<=4096,"Chapter exceeds bounded directional shadow coverage");
 auto& shadow=lighting.shadow;shadow.enabled=true;shadow.resolution=1024;
 shadow.center={static_cast<float>(center[0]),static_cast<float>(center[1]),static_cast<float>(center[2])};
 shadow.half_extent=static_cast<float>(radius);shadow.near_plane=.1f;shadow.far_plane=static_cast<float>(2*radius+.1);shadow.bias=.001f;
}
}
SceneLighting first_boot_content_lighting(const GameplayStoreRecovery& state,const FirstBootContent& content){
 // This read validates the immutable binding and current chapter records, and
 // deliberately calls the chapter's shared live-supply predicates.
 const auto supply=first_boot_content_supply(state,content);
 const auto& definition=content.definition();SceneLighting result;result.exposure=definition.exposure;
 if(definition.lights.empty()){validate_scene_lighting(result);return result;}
 result.enabled=true;result.ambient={.02f,.02f,.02f};
 for(const auto& light:definition.lights){
  if(light.power==FirstBootLightPower::restored&&!supply.main&&!supply.bypass)continue;
  if(light.kind==FirstBootLightKind::directional){
   need(!result.directional,"Chapter supports one active directional light");
   result.directional=DirectionalLight{light.direction,light.color,light.intensity};
  }else result.points.push_back({light.position,light.color,light.intensity,light.radius});
 }
 if(result.directional&&result.directional->intensity>0)shadow_bounds(result,first_boot_content_scene(state,content));
 validate_scene_lighting(result);return result;
}
}
