#include <aibs/character_assets.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {
std::size_t checks=0;
void need(bool value,const char* text){++checks;if(!value)throw std::runtime_error(text);}
template<class F>void bad(F f){bool rejected=false;try{f();}catch(const std::invalid_argument&){rejected=true;}need(rejected,"Invalid owned character asset accepted");}
CharacterAsset fixture(){
 CharacterAsset a;a.asset_id="12345678-1234-4234-8234-123456789abc";a.name="Owned character";a.source_sha256=std::string(64,'a');a.mesh.joints.resize(2);
 a.mesh.joints[0].bind_local.translation={.1f,0,0};a.mesh.joints[0].inverse_bind[12]=-.1f;
 a.mesh.joints[1].parent=0;a.mesh.joints[1].bind_local.translation={0,1,0};a.mesh.joints[1].inverse_bind[12]=-.1f;a.mesh.joints[1].inverse_bind[13]=-1;
 for(auto p:{Vec3{0,0,0},Vec3{1,0,0},Vec3{0,1,0}}){CharacterVertex v;v.position=p;v.joints={0,1,0,0};v.weights={.25f,.75f,0,0};a.mesh.vertices.push_back(v);}a.mesh.indices={0,1,2,2,1,0};
 CharacterClip clip;clip.name="wave";clip.frame_count=2;for(unsigned frame=0;frame<2;++frame)for(const auto&j:a.mesh.joints)clip.samples.push_back(j.bind_local);clip.samples[3].rotation={0,0,std::sin(.1f),std::cos(.1f)};a.mesh.clips.push_back(clip);
 ImageAsset image{ImageSemantic::srgb_color,{{2,2,{255,0,0,255,0,255,0,255,0,0,255,255,255,255,255,255}}}};generate_image_mips(image);a.images.push_back(image);
 a.materials={{0,{1,1,1},0},{character_no_image,{.7f,.5f,.2f},.4f}};a.draws={{0,3,0},{3,3,1}};return a;
}
}
int main(){try{
 const auto base=fixture();validate_character_asset(base);const auto cost=character_asset_cost(base);
 need(cost.payload_bytes>character_mesh_cost(base.mesh).gpu_vertex_bytes,"Missing complete payload cost");need(cost.decoded_bytes>=character_mesh_cost(base.mesh).decoded_bytes,"Missing mesh decoded charge");need(cost.animation_bytes==160&&cost.image_bytes==20,"Missing image/animation charge");need(cost.gpu_vertex_bytes==216&&cost.gpu_index_bytes==24,"Incorrect indexed GPU bytes");
 auto a=base;a.asset_id[14]='1';bad([&]{validate_character_asset(a);});a=base;a.asset_id[19]='7';bad([&]{validate_character_asset(a);});a=base;a.asset_id[0]='A';bad([&]{validate_character_asset(a);});a=base;a.name="";bad([&]{validate_character_asset(a);});a=base;a.name=std::string(129,'a');bad([&]{validate_character_asset(a);});a=base;a.name="bad\nname";bad([&]{validate_character_asset(a);});a=base;a.name=std::string("\xc0\xaf",2);bad([&]{validate_character_asset(a);});a=base;a.source_sha256[0]='A';bad([&]{validate_character_asset(a);});a=base;a.source_sha256.pop_back();bad([&]{validate_character_asset(a);});
 a=base;a.materials.clear();bad([&]{validate_character_asset(a);});a=base;a.materials.resize(65);bad([&]{validate_character_asset(a);});a=base;a.images.resize(33);bad([&]{validate_character_asset(a);});a=base;a.draws.resize(65);bad([&]{validate_character_asset(a);});a=base;a.draws.clear();bad([&]{validate_character_asset(a);});
 for(unsigned channel=0;channel<4;++channel)for(const float value:{-.1f,1.1f,std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity()}){
  a=base;if(channel==0)a.materials[0].base_color.x=value;else if(channel==1)a.materials[0].base_color.y=value;else if(channel==2)a.materials[0].base_color.z=value;else a.materials[0].emission=value<0?value:std::numeric_limits<float>::infinity();bad([&]{validate_character_asset(a);});
 }
 a=base;a.materials[0].emission=16;validate_character_asset(a);++checks;a.materials[0].emission=16.01f;bad([&]{validate_character_asset(a);});
 a=base;a.materials[0].albedo_image=1;bad([&]{validate_character_asset(a);});a=base;a.images[0].semantic=ImageSemantic::linear_data;bad([&]{validate_character_asset(a);});a=base;a.images[0].semantic=ImageSemantic::normal_map;bad([&]{validate_character_asset(a);});
 a=base;a.images[0].levels.pop_back();bad([&]{validate_character_asset(a);});a=base;a.images[0].levels[0].rgba[3]=0;bad([&]{validate_character_asset(a);});a=base;a.images[0].levels[1].rgba[3]=254;bad([&]{validate_character_asset(a);});a=base;a.images[0].levels[0].rgba.pop_back();bad([&]{validate_character_asset(a);});
 a=base;a.draws[0].first_index=3;bad([&]{validate_character_asset(a);});a=base;a.draws[0].index_count=0;bad([&]{validate_character_asset(a);});a=base;a.draws[0].index_count=4;bad([&]{validate_character_asset(a);});a=base;a.draws[0].index_count=std::numeric_limits<std::uint32_t>::max();bad([&]{validate_character_asset(a);});a=base;a.draws[1].first_index=0;bad([&]{validate_character_asset(a);});a=base;a.draws.pop_back();bad([&]{validate_character_asset(a);});a=base;a.draws[0].material=2;bad([&]{validate_character_asset(a);});
 a=base;a.mesh.indices[0]=3;bad([&]{validate_character_asset(a);});a=base;a.mesh.vertices[0].joints[0]=2;bad([&]{validate_character_asset(a);});a=base;a.mesh.vertices[0].weights[0]=.5f;bad([&]{validate_character_asset(a);});a=base;a.mesh.clips[0].samples[2].translation.x+=1;bad([&]{validate_character_asset(a);});
 a=base;a.mesh.clips[0].name=std::string("\xc0\xaf",2);bad([&]{validate_character_asset(a);});a=base;a.materials[0].double_sided=false;validate_character_asset(a);++checks;
 a=base;a.name.reserve(character_maximum_decoded_bytes);need(character_asset_cost(a).decoded_bytes>character_maximum_decoded_bytes,"String capacity not charged");bad([&]{validate_character_asset(a);});a=base;a.images[0].levels[0].rgba.reserve(character_maximum_decoded_bytes);need(character_asset_cost(a).decoded_bytes>character_maximum_decoded_bytes,"Image capacity not charged");bad([&]{validate_character_asset(a);});
 a=base;a.mesh.vertices.reserve(character_maximum_decoded_bytes/sizeof(CharacterVertex)+1);bad([&]{validate_character_asset(a);});
 a=base;a.images.resize(2,a.images[0]);a.images[1].levels[0].rgba.reserve(1024);need(character_asset_cost(a).decoded_bytes>cost.decoded_bytes+1024,"Independent image storage not charged");
 auto payload_boundary=base;payload_boundary.images.clear();ImageAsset large{ImageSemantic::srgb_color,{{2048,1024,std::vector<unsigned char>(2048u*1024u*4u,255)}}};generate_image_mips(large);payload_boundary.images={large,large,large};need(character_asset_cost(payload_boundary).payload_bytes>character_maximum_payload_bytes&&character_asset_cost(payload_boundary).decoded_bytes<character_maximum_decoded_bytes,"Complete payload boundary fixture did not isolate encoded budget");bad([&]{validate_character_asset(payload_boundary);});
 validate_character_asset(base);need(base.images[0].levels[0].rgba[0]==255,"Validation mutated owned source");
 std::cout<<"PASS "<<checks<<" owned character asset checks\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
