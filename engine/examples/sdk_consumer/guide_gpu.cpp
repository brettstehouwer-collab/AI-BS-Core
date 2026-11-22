#include <aibs/guide_presentation.hpp>
#include <aibs/character_codec.hpp>
#include <aibs/engine.hpp>
#include <aibs/textured_scene.hpp>
#include <aibs/lighting.hpp>
#include <aibs/render.hpp>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

// This executable consumes only installed public headers/libraries/shaders.
// It does not read source assets, family references or a canonical project tree.
using namespace aibs;
namespace {
void need(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void quad(SceneMesh& mesh,Vec3 a,Vec3 b,Vec3 c,Vec3 d,Vec3 normal,Vec3 color){
 for(const auto point:{a,b,c,a,c,d})mesh.vertices.push_back({point,normal,color,0});
}
SceneMesh background(){
 SceneMesh mesh;
 quad(mesh,{-5,-.025f,-3},{-5,-.025f,6},{5,-.025f,6},{5,-.025f,-3},{0,1,0},{.06f,.10f,.075f});
 quad(mesh,{-5,0,3},{-5,4,3},{5,4,3},{5,0,3},{0,0,-1},{.025f,.045f,.065f});
 return mesh;
}
std::vector<unsigned char> read(const std::filesystem::path& path){
 std::ifstream file(path,std::ios::binary);need(static_cast<bool>(file),"Cannot read installed SDK GPU evidence");
 std::vector<unsigned char> bytes{std::istreambuf_iterator<char>(file),{}};
 need(bytes.size()==54+256*256*4&&bytes[0]=='B'&&bytes[1]=='M',"Unexpected installed SDK GPU readback size/format");return bytes;
}
std::size_t difference(const std::vector<unsigned char>& a,const std::vector<unsigned char>& b){
 need(a.size()==b.size(),"Installed SDK captures differ in size");std::size_t total=0;
 for(std::size_t i=54;i<a.size();++i)total+=a[i]!=b[i];return total;
}
std::vector<unsigned char> capture(Dx12Renderer& renderer,NativeWindow& window,
 const Camera& camera,const CharacterInstance* instance,const std::filesystem::path& path){
 need(window.poll(),"Installed SDK GPU test window closed");
 if(instance)renderer.render(camera,{},*instance);else renderer.render(camera);
 renderer.capture(path);return read(path);
}
}
int main(int argc,char** argv){try{
 need(argc==3,"Pass installed shader directory and evidence directory");
 const std::filesystem::path shaders=argv[1],output=argv[2];std::filesystem::create_directories(output);
 need(std::filesystem::is_regular_file(shaders/"character.vs.cso")&&std::filesystem::is_regular_file(shaders/"character.ps.cso"),"Installed SDK character shaders missing");
 const auto figure=make_guide_placeholder();GuidePresentation presentation(figure);
 NativeWindow window(256,256,L"AI-BS installed SDK articulated guide proof",false);
 Dx12Renderer renderer(window,background(),shaders);
 SceneLighting lights;lights.enabled=true;lights.ambient={.12f,.15f,.18f};lights.exposure=1;
 const float ray_length=std::sqrt(.35f*.35f+.8f*.8f+.5f*.5f);
 lights.directional=DirectionalLight{{.35f/ray_length,-.8f/ray_length,.5f/ray_length},{1,.72f,.45f},.65f};renderer.set_lighting(lights);
 Camera camera;camera.position={2.2f,1.2f,-3.7f};camera.yaw=std::atan2(-2.2f,3.7f);camera.pitch=-.0696f;
 const auto empty=capture(renderer,window,camera,nullptr,output/"without-guide.bmp");
 renderer.set_scene_character_bounded(background(),TexturedScene{},lights,&figure,128u*1024u*1024u);
 GuideState guide;guide.character.feet={};guide.character.grounded=true;guide.destination={0,0,3};
 guide.intent=GuideIntent::wait;guide.activity=GuideActivity::waiting;
 const auto idle=presentation.sample(guide,0);need(idle.has_value(),"Installed SDK presentation rejected grounded guide");
 const auto idle_bytes=capture(renderer,window,camera,&*idle,output/"idle.bmp");
 const auto visible_difference=difference(empty,idle_bytes);need(visible_difference>1000,"Installed SDK indexed guide produces no visible GPU figure");
 guide.intent=GuideIntent::follow;guide.activity=GuideActivity::following;guide.character.velocity={0,0,7};
 const auto walk_start=presentation.sample(guide,0);need(walk_start&&presentation.clip()==GuidePresentationClip::walk,"Installed SDK presentation did not select walk");
 const auto first=capture(renderer,window,camera,&*walk_start,output/"walk-start.bmp");
 std::optional<CharacterInstance> walk_later;
 for(unsigned frame=0;frame<15;++frame)walk_later=presentation.sample(guide,1./60);
 need(walk_later&&std::abs(presentation.animation_seconds()-.25)<1e-8,"Installed SDK walk sample time differs from quarter-cycle");
 const auto later=capture(renderer,window,camera,&*walk_later,output/"walk-quarter.bmp");
 const auto animated_difference=difference(first,later),idle_walk_difference=difference(idle_bytes,later);
 need(animated_difference>300&&idle_walk_difference>300,"Installed SDK sampled bones do not change actual GPU pixels");
 const auto before=renderer.stats();
 for(unsigned frame=0;frame<30;++frame){
  need(window.poll(),"Installed SDK GPU window closed during animation");const auto instance=presentation.sample(guide,1./60);
  need(instance.has_value(),"Installed SDK animation lost grounded guide");renderer.render(camera,{},*instance);
 }
 const auto after=renderer.stats();
 need(after.character_replacements==before.character_replacements&&after.character_buffer_allocations==before.character_buffer_allocations&&
  after.scene_replacements==before.scene_replacements&&after.transient_buffer_allocations==before.transient_buffer_allocations&&
  after.full_idle_calls==before.full_idle_calls,"Installed SDK ordinary pose frames replace/allocate/drain GPU resources");
 need(after.character_frames==before.character_frames+30,"Installed SDK pose frames bypass indexed character draw");
 need(after.character_active_gpu_bytes>0&&after.character_active_gpu_bytes<=32u*1024u*1024u,"Installed SDK character allocation charge outside bounded profile");
 // The installed codec and typed renderer must own complete material/image
 // resources, rather than silently drawing the old vertex-colored fallback.
 const auto same_pose=presentation.sample(guide,0);need(same_pose.has_value(),"Installed SDK guide pose unavailable for typed asset proof");
 const auto plain=capture(renderer,window,camera,&*same_pose,output/"plain-before-typed.bmp");
 CharacterAsset typed;typed.asset_id=new_uuid();typed.name="Installed SDK textured character";typed.source_sha256=std::string(64,'a');typed.mesh=figure;
 typed.images={{ImageSemantic::srgb_color,{{2,2,{255,40,10,255,20,240,30,255,10,30,255,255,255,255,255,255}}}}};generate_image_mips(typed.images.front());typed.materials={{0,{1,1,1},0,true}};typed.draws={{0,static_cast<std::uint32_t>(figure.indices.size()),0}};
 const auto packed=encode_character_asset(typed);auto cooked=decode_character_asset(packed);need(encode_character_asset(cooked)==packed,"Installed SDK typed character codec changed complete bytes");
 renderer.set_scene_character_asset_bounded(background(),TexturedScene{},lights,&cooked,128u*1024u*1024u);
 renderer.set_scene_bounded(background(),TexturedScene{},lights,128u*1024u*1024u);
 const auto textured=capture(renderer,window,camera,&*same_pose,output/"typed-textured.bmp");const auto textured_difference=difference(plain,textured);need(textured_difference>300,"Installed SDK typed renderer silently used the untextured character path");
 auto updated=cooked;for(auto& level:updated.images.front().levels)for(std::size_t pixel=0;pixel<level.rgba.size();pixel+=4){level.rgba[pixel]=255;level.rgba[pixel+1]=180;level.rgba[pixel+2]=10;}
 renderer.set_character_asset(updated);const auto changed=capture(renderer,window,camera,&*same_pose,output/"typed-updated.bmp");const auto updated_difference=difference(textured,changed);need(updated_difference>300,"Installed SDK typed image replacement produced no GPU change");
 const auto accepted=renderer.stats();auto invalid=updated;invalid.images.front().levels.front().rgba.pop_back();bool rejected=false;try{renderer.set_scene_character_asset({},TexturedScene{},lights,&invalid);}catch(const std::invalid_argument&){rejected=true;}need(rejected,"Installed SDK malformed typed replacement accepted");const auto rejected_stats=renderer.stats();
 need(rejected_stats.scene_replacements==accepted.scene_replacements&&rejected_stats.character_replacements==accepted.character_replacements&&rejected_stats.character_buffer_allocations==accepted.character_buffer_allocations&&rejected_stats.full_idle_calls==accepted.full_idle_calls,"Installed SDK rejected typed replacement changed resources");
 need(capture(renderer,window,camera,&*same_pose,output/"typed-rejection-preserved.bmp")==changed,"Installed SDK rejected typed replacement changed published pixels");
 const auto typed_before=renderer.stats();for(unsigned frame=0;frame<8;++frame)renderer.render(camera,{},*same_pose);const auto typed_after=renderer.stats();need(typed_after.scene_replacements==typed_before.scene_replacements&&typed_after.character_replacements==typed_before.character_replacements&&typed_after.character_buffer_allocations==typed_before.character_buffer_allocations&&typed_after.full_idle_calls==typed_before.full_idle_calls&&typed_after.character_frames==typed_before.character_frames+8,"Installed SDK typed pose frames allocate/rebuild/drain resources");
 renderer.clear_character();const auto cleared=capture(renderer,window,camera,nullptr,output/"cleared.bmp");
 need(cleared==empty,"Installed SDK clearing character changes independently owned scenery");
 renderer.wait_idle();const auto final=renderer.stats();
 need(final.debug_layer&&final.debug_errors==0&&final.debug_warnings==0,"Installed SDK character DX12 debug diagnostics");
 std::ofstream report(output/"verification.json");need(static_cast<bool>(report),"Cannot create installed SDK GPU report");
 report<<"{\"status\":\"passed\",\"scope\":\"installed SDK temporary articulated and typed textured guide; not Adam likeness or full opening\","
  <<"\"visible_changed_channel_bytes\":"<<visible_difference<<",\"animated_changed_channel_bytes\":"<<animated_difference
  <<",\"idle_walk_changed_channel_bytes\":"<<idle_walk_difference<<",\"ordinary_pose_frames\":30,\"sample_seconds\":[0,0.25],"
  <<"\"frames\":"<<final.frames<<",\"character_frames\":"<<final.character_frames<<",\"active_character_gpu_bytes_before_clear\":"<<typed_after.character_active_gpu_bytes
  <<",\"typed_textured_changed_channel_bytes\":"<<textured_difference<<",\"typed_updated_changed_channel_bytes\":"<<updated_difference<<",\"typed_codec_exact\":true,\"typed_rejection_pixels_exact\":true,\"typed_ordinary_pose_frames\":8"
  <<",\"debug_errors\":"<<final.debug_errors<<",\"debug_warnings\":"<<final.debug_warnings<<",\"cleared_background_exact\":true}\n";
 need(static_cast<bool>(report),"Cannot write installed SDK GPU report");
 std::cout<<"PASS installed SDK indexed guide, actual sampled animation GPU readback and stable resource reuse\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
