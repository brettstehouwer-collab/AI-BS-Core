#include <aibs/render.hpp>
#include <aibs/lighting.hpp>
#include <aibs/textured_scene.hpp>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {
void need(bool b,const char* message){if(!b)throw std::runtime_error(message);}
template<class F>void reject(F f){bool bad=false;try{f();}catch(const std::invalid_argument&){bad=true;}need(bad,"Invalid authored lighting accepted");}
std::vector<unsigned char> read(const std::filesystem::path&p){std::ifstream f(p,std::ios::binary);return {(std::istreambuf_iterator<char>(f)),{}};}
std::size_t difference(const std::vector<unsigned char>&a,const std::vector<unsigned char>&b){need(a.size()==b.size(),"Capture dimensions changed");std::size_t n=0;for(std::size_t i=54;i<a.size();++i)n+=a[i]!=b[i];return n;}
void quad(SceneMesh& mesh,Vec3 a,Vec3 b,Vec3 c,Vec3 d,Vec3 n,Vec3 color){for(const auto p:{a,b,c,a,c,d})mesh.vertices.push_back({p,n,color,0});}
SceneMesh front(){SceneMesh m;quad(m,{-2,-2,3},{-2,2,3},{2,2,3},{2,-2,3},{0,0,-1},{.25f,.4f,.6f});return m;}
std::vector<unsigned char> snap(Dx12Renderer&r,NativeWindow&w,const Camera&c,const std::filesystem::path&p){need(w.poll(),"Test window closed");r.render(c);r.capture(p);return read(p);}
void center_matches(const std::vector<unsigned char>& b,Vec3 color){
 need(b.size()>=54+256*256*4,"Unexpected GPU capture bound");
 const std::size_t at=54+(128*256+128)*4;
 for(const auto [channel,expected]:{std::pair{2,color.x},std::pair{1,color.y},std::pair{0,color.z}})
  need(std::abs(static_cast<int>(b[at+channel])-static_cast<int>(std::lround(expected*255)))<=2,"GPU linear lighting/exposure/transfer differs from CPU oracle");
}
struct FloorSample {std::size_t byte;Vec3 world;};
FloorSample floor_sample(const Camera& camera,Vec3 target){
 const auto m=camera.view_projection(1);std::array<float,4> clip{};
 for(unsigned c=0;c<4;++c)clip[c]=target.x*m[c]+target.y*m[4+c]+target.z*m[8+c]+m[12+c];
 need(clip[3]>0,"Floor sample is behind the camera");
 const auto x=static_cast<int>(std::floor((clip[0]/clip[3]*.5f+.5f)*256));
 const auto y=static_cast<int>(std::floor((.5f-clip[1]/clip[3]*.5f)*256));
 need(x>=0&&x<256&&y>=0&&y<256,"Floor sample outside GPU image");
 // Recover the exact world location of this pixel's center on Y=0, rather
 // than comparing an approximate target location against a point-light oracle.
 const float sx=(2*(static_cast<float>(x)+.5f)/256-1)*std::tan(3.14159265358979323846f/8);
 const float sy=(1-2*(static_cast<float>(y)+.5f)/256)*std::tan(3.14159265358979323846f/8);
 const float cy=std::cos(camera.yaw),syaw=std::sin(camera.yaw),cp=std::cos(camera.pitch),sp=std::sin(camera.pitch);
 const Vec3 ray{syaw*cp+sx*cy-sy*syaw*sp,sp+sy*cp,cy*cp-sx*syaw-sy*cy*sp};
 need(ray.y<0,"Floor sample ray needs downward direction");const float t=-camera.position.y/ray.y;
 return {54+(static_cast<std::size_t>(y)*256+static_cast<std::size_t>(x))*4,{camera.position.x+t*ray.x,0,camera.position.z+t*ray.z}};
}
void floor_matches(const std::vector<unsigned char>& bytes,FloorSample at,Vec3 expected){
 for(const auto [channel,value]:{std::pair{2,expected.x},std::pair{1,expected.y},std::pair{0,expected.z}})
  need(std::abs(static_cast<int>(bytes.at(at.byte+channel))-static_cast<int>(std::lround(value*255)))<=2,"GPU shadow receiver differs from its unshadowed-term CPU oracle");
}
}
int main(int argc,char**argv){try{
 need(argc==3,"Pass shader directory and evidence directory");const std::filesystem::path output=argv[2];std::filesystem::create_directories(output);
 NativeWindow window(256,256,L"AI-BS authored lighting proof",false);const auto base=front();Dx12Renderer renderer(window,base,argv[1]);Camera camera;camera.position={};camera.yaw=camera.pitch=0;
 const auto legacy=snap(renderer,window,camera,output/"legacy.bmp");
 SceneLighting light;light.enabled=true;light.ambient={1,1,1};light.exposure=1;
 renderer.set_lighting(light);const auto ambient=snap(renderer,window,camera,output/"ambient.bmp");
 center_matches(ambient,evaluate_scene_lighting(light,{0,0,3},{0,0,-1},{.25f,.4f,.6f},0));need(difference(legacy,ambient)>10000,"Authored base lighting produced no pixels");
 light.ambient={.02f,.02f,.02f};light.directional=DirectionalLight{{0,0,1},{1,.6f,.3f},.8f};
 renderer.set_lighting(light);const auto directional=snap(renderer,window,camera,output/"directional.bmp");need(difference(ambient,directional)>10000,"Directional light did not change base pixels");
 light.directional.reset();light.points={{{0,0,1},{.3f,.7f,1},1,8}};
 renderer.set_lighting(light);const auto point=snap(renderer,window,camera,output/"point.bmp");need(difference(directional,point)>10000,"Point light did not change base pixels");
 center_matches(point,evaluate_scene_lighting(light,{0,0,3},{0,0,-1},{.25f,.4f,.6f},0));
 light.exposure=3;renderer.set_lighting(light);const auto bright=snap(renderer,window,camera,output/"exposure.bmp");need(difference(point,bright)>10000,"Exposure did not affect rendered pixels");
 auto invalid=light;invalid.points[0].radius=0;reject([&]{renderer.set_lighting(invalid);});need(snap(renderer,window,camera,output/"rejected.bmp")==bright,"Invalid light update changed active pixels");
 reject([&]{renderer.set_scene(SceneMesh{},TexturedScene{},invalid);});need(snap(renderer,window,camera,output/"joint-rejected.bmp")==bright,"Invalid joint publication changed active base/lights");
 TexturedScene textured;textured.images={{ImageSemantic::linear_data,{{1,1,{64,102,153,255}}}}};
 for(const auto&v:base.vertices)textured.vertices.push_back({v.position,v.normal,0,0});textured.draws={{0,6,0,{1,1,1},0}};
 renderer.set_scene({},textured,light);const auto textured_point=snap(renderer,window,camera,output/"textured-point.bmp");center_matches(textured_point,evaluate_scene_lighting(light,{0,0,3},{0,0,-1},{64.f/255,102.f/255,153.f/255},0));
 SceneMesh shadow_scene;quad(shadow_scene,{-4,0,0},{-4,0,8},{4,0,8},{4,0,0},{0,1,0},{.8f,.8f,.8f});quad(shadow_scene,{-.5f,1.5f,3.5f},{-.5f,1.5f,4.5f},{.5f,1.5f,4.5f},{.5f,1.5f,3.5f},{0,1,0},{.4f,.4f,.4f});
 camera.position={0,5,-3};camera.pitch=-.55f;
 light.points.clear();light.exposure=1;light.ambient={.04f,.04f,.04f};light.directional=DirectionalLight{{.6f,-.8f,0},{1,1,1},1};light.shadow.center={0,0,4};light.shadow.half_extent=6;light.shadow.near_plane=.1f;light.shadow.far_plane=30;light.shadow.bias=.001f;
 renderer.set_scene(shadow_scene,{},light);const auto unshadowed=snap(renderer,window,camera,output/"unshadowed.bmp");
 light.shadow.enabled=true;renderer.set_lighting(light);const auto shadowed=snap(renderer,window,camera,output/"shadowed.bmp");const auto shadow_difference=difference(unshadowed,shadowed);need(shadow_difference>150,"Directional occluder did not cast a GPU-readback shadow");
 light.shadow.resolution=2048;renderer.set_lighting(light);const auto large_shadow=snap(renderer,window,camera,output/"shadowed-2048.bmp");need(difference(unshadowed,large_shadow)>150,"Resized directional shadow map produced no shadow");
 invalid=light;invalid.shadow.resolution=512;reject([&]{renderer.set_lighting(invalid);});need(snap(renderer,window,camera,output/"shadow-rejected.bmp")==large_shadow,"Rejected shadow allocation/config changed published pixels");
 const auto receiver=floor_sample(camera,{1.125f,0,4});
 auto ambient_only=light;ambient_only.shadow.enabled=false;ambient_only.directional.reset();
 floor_matches(large_shadow,receiver,evaluate_scene_lighting(ambient_only,receiver.world,{0,1,0},{.8f,.8f,.8f},0));
 // A directional shadow must leave the blue point light intact. The receiver
 // is well inside the cast patch, so its expected radiance excludes only the
 // directional term; its exact pixel-center floor position is used above.
 light.points={{{1.125f,2,4},{.1f,.3f,1},.7f,4}};renderer.set_lighting(light);
 const auto point_in_shadow=snap(renderer,window,camera,output/"point-in-shadow.bmp");
 auto point_only=light;point_only.shadow.enabled=false;point_only.directional.reset();
 floor_matches(point_in_shadow,receiver,evaluate_scene_lighting(point_only,receiver.world,{0,1,0},{.8f,.8f,.8f},0));
 need(difference(point_in_shadow,large_shadow)>150,"Directional shadow incorrectly erased the point-light contribution");
 light.points.clear();
 // Move the same floor onto the owned texture draw path while keeping the
 // caster in the base mesh. This also exercises the single combined SRV heap.
 SceneMesh occluder;occluder.vertices.assign(shadow_scene.vertices.begin()+6,shadow_scene.vertices.end());
 TexturedScene floor_textures;floor_textures.images={{ImageSemantic::linear_data,{{1,1,{204,204,204,255}}}}};
 for(std::size_t i=0;i<6;++i){const auto&v=shadow_scene.vertices[i];floor_textures.vertices.push_back({v.position,v.normal,0,0});}floor_textures.draws={{0,6,0,{1,1,1},0}};
 auto no_shadow=light;no_shadow.shadow.enabled=false;renderer.set_scene(occluder,floor_textures,no_shadow);
 const auto textured_unshadowed=snap(renderer,window,camera,output/"textured-unshadowed.bmp");
 renderer.set_lighting(light);const auto textured_shadowed=snap(renderer,window,camera,output/"textured-shadowed.bmp");
 const auto textured_shadow_difference=difference(textured_unshadowed,textured_shadowed);need(textured_shadow_difference>150,"Textured receiver did not sample the directional shadow");
 floor_matches(textured_shadowed,receiver,evaluate_scene_lighting(ambient_only,receiver.world,{0,1,0},{.8f,.8f,.8f},0));
 // The caster can instead be transient geometry. It never enters a persistent
 // scene buffer, but must participate in the same depth-only shadow pass.
 renderer.set_scene({},floor_textures,light);const auto without_caster=snap(renderer,window,camera,output/"no-caster.bmp");
 renderer.render(camera,occluder);renderer.capture(output/"transient-caster.bmp");const auto transient_shadowed=read(output/"transient-caster.bmp");
 const auto transient_shadow_difference=difference(without_caster,transient_shadowed);need(transient_shadow_difference>150,"Transient occluder did not cast onto textured receiver");
 floor_matches(transient_shadowed,receiver,evaluate_scene_lighting(ambient_only,receiver.world,{0,1,0},{.8f,.8f,.8f},0));
 auto malformed=base;malformed.vertices[0].normal={};auto valid_new_light=light;valid_new_light.exposure=2;
 reject([&]{renderer.set_scene(malformed,floor_textures,valid_new_light);});
 need(snap(renderer,window,camera,output/"geometry-rejected.bmp")==without_caster,"Malformed geometry after valid lights changed joint published state");
 const auto stats_before=renderer.stats();for(unsigned frame=0;frame<8;++frame)renderer.render(camera);const auto stats_after=renderer.stats();need(stats_after.scene_replacements==stats_before.scene_replacements&&stats_after.full_idle_calls==stats_before.full_idle_calls,"Ordinary lighting frames rebuild/idle static resources");
 renderer.set_scene(base,{},SceneLighting{});camera.position={};camera.pitch=0;need(snap(renderer,window,camera,output/"disabled.bmp")==legacy,"Disabled authored lighting changed legacy shader bytes");
 renderer.wait_idle();const auto stats=renderer.stats();need(stats.debug_layer&&stats.debug_errors==0&&stats.debug_warnings==0,"Authored lighting/shadow DX12 debug diagnostics");
 std::ofstream report(output/"verification.json");report<<"{\"status\":\"passed\",\"frames\":"<<stats.frames<<",\"debug_errors\":"<<stats.debug_errors<<",\"debug_warnings\":"<<stats.debug_warnings<<",\"shadow_changed_channel_bytes\":"<<shadow_difference<<",\"textured_shadow_changed_channel_bytes\":"<<textured_shadow_difference<<",\"transient_shadow_changed_channel_bytes\":"<<transient_shadow_difference<<",\"point_in_shadow_sample_verified\":true}\n";
 std::cout<<"PASS GPU authored directional/point/exposure/texture shading, directional shadow, rollback and legacy disable\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
