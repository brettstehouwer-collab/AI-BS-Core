
#include <aibs/asset_store.hpp>
#include <aibs/character_assets.hpp>
#include <aibs/lighting.hpp>
#include <aibs/textured_scene.hpp>
#include <aibs/render.hpp>
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
int main(int argc,char** argv){try{
 need(argc==4,"Expected pack,shaders,new output root");std::filesystem::path out=argv[3];need(!std::filesystem::exists(out),"Retain old evidence");std::filesystem::create_directories(out);
 auto inspected=inspect_asset_pack(argv[1]);need(inspected.kind==StoredAssetKind::character_v2,"Expected actual typed character");const auto& asset=std::get<CharacterAsset>(inspected.asset.payload);const auto cost=character_asset_cost(asset);
 NativeWindow window(768,768,L"AI-BS private Adam native review",false);Dx12Renderer renderer(window,{},argv[2]);SceneLighting lights;lights.enabled=true;lights.ambient={.15f,.15f,.15f};lights.exposure=1.2f;lights.directional=DirectionalLight{{-.2182179f,-.4364358f,-.8728716f},{1,.93f,.85f},1.3f};
 renderer.set_scene_character_asset_bounded({},TexturedScene{},lights,&asset,128u*1024u*1024u-cost.decoded_bytes);
 CharacterInstance instance;instance.pose=sample_character_clip(asset.mesh,0,0);Camera camera;camera.position={0,1.67f,.52f};camera.yaw=3.14159265f;camera.pitch=0;
 const auto capture=[&](const char* name,bool character){need(window.poll(),"Window closed");if(character){renderer.render(camera,{},instance);renderer.render(camera,{},instance);renderer.render(camera,{},instance);}else renderer.render(camera);CapturedFrame frame;need(renderer.capture_frame(frame),"Missing GPU frame");need(frame.width==768&&frame.height==768,"Wrong capture size");renderer.capture(out/(std::string(name)+".bmp"));return frame;};
 const auto empty=capture("without",false);const auto front=capture("front",true);std::size_t visible=0;for(std::size_t i=0;i<front.bgra.size();i+=4)if(front.bgra[i]!=empty.bgra[i]||front.bgra[i+1]!=empty.bgra[i+1]||front.bgra[i+2]!=empty.bgra[i+2])++visible;need(visible>1000,"Actual imported character invisible");
 camera.position={.32f,1.7f,.55f};camera.yaw=std::atan2(-.32f,-.55f);camera.pitch=-.04f;capture("quarter",true);
 camera.position={.65f,1.68f,0};camera.yaw=-1.57079633f;camera.pitch=0;capture("profile",true);

 Vec3 band_center{};std::size_t band_count=0;const auto palette=character_skin_palette(asset.mesh,instance.pose);
 for(const auto& draw:asset.draws)if(draw.material==12){for(std::uint32_t k=0;k<draw.index_count;++k){const auto skinned=character_skin_vertex(asset.mesh.vertices[asset.mesh.indices[draw.first_index+k]],palette);band_center.x+=skinned.position.x;band_center.y+=skinned.position.y;band_center.z+=skinned.position.z;++band_count;}}
 need(band_count>0,"Band draw is missing");const auto divisor=static_cast<float>(band_count);band_center.x/=divisor;band_center.y/=divisor;band_center.z/=divisor;
 camera.position={band_center.x,band_center.y,band_center.z+.30f};camera.yaw=3.14159265f;camera.pitch=0;
 const auto band_frame=capture("right-wrist",true);need(asset.materials.size()==14,"Expected14materials with band and inscription");
 auto marked=asset;marked.materials[12].base_color={1,0,0};
 renderer.set_scene_character_asset_bounded({},TexturedScene{},lights,&marked,128u*1024u*1024u-character_asset_cost(marked).decoded_bytes);
 const auto band_marked=capture("band-material-red",true);std::size_t band_pixels=0;
 for(std::size_t i=0;i<band_frame.bgra.size();i+=4)if(band_frame.bgra[i]!=band_marked.bgra[i]||band_frame.bgra[i+1]!=band_marked.bgra[i+1]||band_frame.bgra[i+2]!=band_marked.bgra[i+2])++band_pixels;
 need(band_pixels>500,"Band material did not affect actual wrist GPU pixels");
 renderer.set_scene_character_asset_bounded({},TexturedScene{},lights,&asset,128u*1024u*1024u-cost.decoded_bytes);
 camera.position={0,1.1f,3.0f};camera.yaw=3.14159265f;camera.pitch=-.07f;capture("full",true);
 instance.pose=sample_character_clip(asset.mesh,1,0);const auto first=capture("walk-start",true);instance.pose=sample_character_clip(asset.mesh,1,.25);const auto later=capture("walk-quarter",true);std::size_t animated=0;for(std::size_t i=0;i<first.bgra.size();i+=4)if(first.bgra[i]!=later.bgra[i]||first.bgra[i+1]!=later.bgra[i+1]||first.bgra[i+2]!=later.bgra[i+2])++animated;need(animated>100,"Actual imported animation does not change GPU pixels");
 const auto before=renderer.stats();for(int i=0;i<24;++i){instance.pose=sample_character_clip(asset.mesh,1,i/60.);renderer.render(camera,{},instance);}const auto after=renderer.stats();need(after.character_buffer_allocations==before.character_buffer_allocations&&after.scene_replacements==before.scene_replacements,"Ordinary animation reallocates immutable resources");need(after.debug_errors==0&&after.debug_warnings==0,"Actual GPU diagnostics failed");
 std::ofstream report(out/"verification.json");report<<"{\"status\":\"passed_actual_native_band_material_and_animation\",\"vertices\":"<<asset.mesh.vertices.size()<<",\"indices\":"<<asset.mesh.indices.size()<<",\"joints\":"<<asset.mesh.joints.size()<<",\"clips\":"<<asset.mesh.clips.size()<<",\"decoded_bytes\":"<<cost.decoded_bytes<<",\"content_gpu_bytes\":"<<after.scene_active_gpu_bytes<<",\"visible_pixel_difference\":"<<visible<<",\"animated_pixel_difference\":"<<animated<<",\"band_material_changed_pixels\":"<<band_pixels<<",\"debug_errors\":"<<after.debug_errors<<",\"debug_warnings\":"<<after.debug_warnings<<",\"likeness_approved\":false,\"installed_model_replaced\":false}\n";report.close();need(report.good(),"Cannot retain report");std::cout<<"Actual typed v15 native portrait/animation passed\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
