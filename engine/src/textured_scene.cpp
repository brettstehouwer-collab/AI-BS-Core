#include <aibs/textured_scene.hpp>
#include <cmath>
#include <stdexcept>
namespace aibs {
void validate_textured_scene(const TexturedScene&s){
 const auto need=[](bool b){if(!b)throw std::invalid_argument("Invalid/budget-exceeding textured scene");};
 const auto finite=[](Vec3 v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z);};
 const auto unit=[](float f){return std::isfinite(f)&&f>=0&&f<=1;};
 need(s.vertices.size()<=1000000&&s.vertices.size()%3==0&&s.images.size()<=32&&s.draws.size()<=256);
 if(s.vertices.empty()){need(s.images.empty()&&s.draws.empty());return;}
 need(!s.images.empty()&&!s.draws.empty());std::size_t bytes=0;
 for(const auto&i:s.images){validate_image_asset(i);const auto n=image_resident_bytes(i);need(n<=128u*1024u*1024u-bytes);bytes+=n;}
 for(const auto&v:s.vertices)need(finite(v.position)&&finite(v.normal)&&(v.normal.x!=0||v.normal.y!=0||v.normal.z!=0)&&std::isfinite(v.u)&&std::isfinite(v.v));
 std::size_t offset=0;
 for(const auto&d:s.draws){need(d.first==offset&&d.count>0&&d.count%3==0&&d.count<=s.vertices.size()-offset&&d.image<s.images.size()&&s.images[d.image].semantic!=ImageSemantic::normal_map&&unit(d.tint.x)&&unit(d.tint.y)&&unit(d.tint.z)&&unit(d.emission));offset+=d.count;}
 need(offset==s.vertices.size());
}
}
