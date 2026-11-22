#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/character_assets.hpp>
#include <aibs/engine.hpp>
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace aibs {namespace {
void need(bool value,const char* message){if(!value)throw std::invalid_argument(message);}
std::size_t add(std::size_t a,std::size_t b){need(b<=std::numeric_limits<std::size_t>::max()-a,"Character asset byte count overflow");return a+b;}
std::size_t multiply(std::size_t a,std::size_t b){need(!a||b<=std::numeric_limits<std::size_t>::max()/a,"Character asset byte count overflow");return a*b;}
void counts(const CharacterAsset& a){need(a.images.size()<=character_asset_maximum_images&&a.materials.size()<=character_asset_maximum_materials&&a.draws.size()<=character_asset_maximum_draws,"Character image/material/draw count exceeds profile");}
bool unit(float v){return std::isfinite(v)&&v>=0&&v<=1;}
bool digest(std::string_view s){return s.size()==64&&std::all_of(s.begin(),s.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');});}
void label(std::string_view name,std::size_t maximum){
 need(!name.empty()&&name.size()<=maximum&&std::none_of(name.begin(),name.end(),[](unsigned char c){return c<32||c==127;}),"Invalid character asset label");
 need(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,name.data(),static_cast<int>(name.size()),nullptr,0)>0,"Character asset label must be UTF-8");
}
void identity(const CharacterAsset& a){
 need(is_uuid(a.asset_id)&&digest(a.source_sha256),"Invalid character asset UUID/source digest");
 label(a.name,128);
}
}
std::uint32_t character_asset_payload_version(const CharacterAsset& a)noexcept{
 return std::any_of(a.materials.begin(),a.materials.end(),[](const auto& m){return m.roughness!=1;})?3u:2u;
}
CharacterAssetCost character_asset_cost(const CharacterAsset& a){
 counts(a);const auto mesh=character_mesh_cost(a.mesh);CharacterAssetCost cost;
 cost.gpu_vertex_bytes=mesh.gpu_vertex_bytes;cost.gpu_index_bytes=mesh.gpu_index_bytes;cost.animation_bytes=mesh.animation_bytes;
 cost.payload_bytes=48+32+12;for(const auto* s:{&a.asset_id,&a.name,&a.source_sha256})cost.payload_bytes=add(cost.payload_bytes,s->size());
 cost.payload_bytes=add(cost.payload_bytes,add(mesh.gpu_vertex_bytes,add(mesh.gpu_index_bytes,multiply(a.mesh.joints.size(),108))));
 for(const auto& clip:a.mesh.clips)cost.payload_bytes=add(cost.payload_bytes,add(add(20,clip.name.size()),multiply(clip.samples.size(),40)));
 cost.payload_bytes=add(cost.payload_bytes,add(multiply(a.materials.size(),character_asset_payload_version(a)==3?28u:24u),multiply(a.draws.size(),12)));
 cost.decoded_bytes=add(sizeof(CharacterAsset)-sizeof(CharacterMesh),mesh.decoded_bytes);
 for(const auto* s:{&a.asset_id,&a.name,&a.source_sha256})cost.decoded_bytes=add(cost.decoded_bytes,add(s->capacity(),1));
 cost.decoded_bytes=add(cost.decoded_bytes,add(multiply(a.materials.capacity(),sizeof(CharacterMaterial)),add(multiply(a.draws.capacity(),sizeof(CharacterDraw)),multiply(a.images.capacity(),sizeof(ImageAsset)))));
 for(const auto& image:a.images){
  need(image.levels.size()<=13,"Character image mip count exceeds profile");cost.payload_bytes=add(cost.payload_bytes,12);cost.decoded_bytes=add(cost.decoded_bytes,multiply(image.levels.capacity(),sizeof(ImageMip)));
  for(const auto& mip:image.levels){cost.image_bytes=add(cost.image_bytes,mip.rgba.size());cost.payload_bytes=add(cost.payload_bytes,add(16,mip.rgba.size()));cost.decoded_bytes=add(cost.decoded_bytes,mip.rgba.capacity());}
 }
 return cost;
}
void validate_character_asset(const CharacterAsset& a){
 counts(a);identity(a);need(!a.materials.empty()&&!a.draws.empty(),"Character asset requires materials and draws");
 const auto cost=character_asset_cost(a);need(cost.payload_bytes<=character_maximum_payload_bytes&&cost.decoded_bytes<=character_maximum_decoded_bytes,"Complete character asset payload/decoded storage exceeds profile");
 validate_character_mesh(a.mesh);
 for(const auto& clip:a.mesh.clips)label(clip.name,64);
 for(const auto& image:a.images){validate_image_asset(image);for(const auto& mip:image.levels)for(std::size_t i=3;i<mip.rgba.size();i+=4)need(mip.rgba[i]==255,"Opaque character images require canonical alpha255");}
 for(const auto& material:a.materials){need(unit(material.base_color.x)&&unit(material.base_color.y)&&unit(material.base_color.z)&&std::isfinite(material.emission)&&material.emission>=0&&material.emission<=16,"Invalid character material color/emission");need(std::isfinite(material.roughness)&&material.roughness>=.04f&&material.roughness<=1,"Character roughness outside0.04..1");if(material.albedo_image!=character_no_image){need(material.albedo_image<a.images.size(),"Character albedo index outside owned images");need(a.images[material.albedo_image].semantic==ImageSemantic::srgb_color,"Character albedo must use sRGB color semantics");}}
 std::size_t cursor=0;for(const auto& draw:a.draws){need(draw.material<a.materials.size()&&draw.first_index==cursor&&draw.index_count>0&&draw.index_count%3==0&&draw.index_count<=a.mesh.indices.size()-cursor,"Character draws must cover contiguous index triangles exactly once");cursor+=draw.index_count;}
 need(cursor==a.mesh.indices.size(),"Character draws omit indexed geometry");
}
}
