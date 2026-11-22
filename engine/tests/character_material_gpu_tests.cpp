#include <aibs/render.hpp>
#include <aibs/character_assets.hpp>
#include <aibs/lighting.hpp>
#include <aibs/textured_scene.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {
std::size_t checks=0;
void need(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
template<class F>void reject(F&& f,const char* message){bool caught=false;try{f();}catch(const std::invalid_argument&){caught=true;}need(caught,message);}
using Bytes=std::vector<unsigned char>;
Bytes read(const std::filesystem::path& path){std::ifstream file(path,std::ios::binary);need(static_cast<bool>(file),"Capture absent");return {(std::istreambuf_iterator<char>(file)),{}};}
std::size_t difference(const Bytes& a,const Bytes& b){need(a.size()==b.size(),"Capture dimensions differ");std::size_t n=0;for(std::size_t i=54;i<a.size();++i)n+=a[i]!=b[i];return n;}
ImageAsset solid(unsigned char r,unsigned char g,unsigned char b,unsigned width=1){ImageAsset image;image.levels={{width,width,std::vector<unsigned char>(static_cast<std::size_t>(width)*width*4)}};for(std::size_t i=0;i<image.levels[0].rgba.size();i+=4){image.levels[0].rgba[i]=r;image.levels[0].rgba[i+1]=g;image.levels[0].rgba[i+2]=b;image.levels[0].rgba[i+3]=255;}generate_image_mips(image);return image;}
void quad(CharacterMesh& mesh,float x,float X,float y,float Y,float z,float u,float v,bool reverse=false){
 const auto first=static_cast<std::uint32_t>(mesh.vertices.size());
 for(const auto p:{Vec3{x,y,z},Vec3{x,Y,z},Vec3{X,Y,z},Vec3{X,y,z}}){CharacterVertex vertex;vertex.position=p;vertex.normal={0,0,-1};vertex.u=u;vertex.v=v;mesh.vertices.push_back(vertex);}
 for(auto index:reverse?std::array{0u,2u,1u,0u,3u,2u}:std::array{0u,1u,2u,0u,2u,3u})mesh.indices.push_back(first+index);
}
CharacterAsset base(){CharacterAsset a;a.asset_id="11111111-1111-4111-8111-111111111111";a.name="Synthetic indexed material proof";a.source_sha256=std::string(64,'0');a.mesh.joints.resize(1);return a;}
CharacterAsset panel(){auto a=base();quad(a.mesh,-1,1,-1,1,3,.25f,.25f);a.images={solid(128,128,128)};a.materials={{0,{1,1,1},0,false}};a.draws={{0,6,0}};validate_character_asset(a);return a;}
Bytes snap(Dx12Renderer& renderer,NativeWindow& window,const Camera& camera,const std::filesystem::path& path,const CharacterInstance* instance=nullptr){need(window.poll(),"Test window closed");if(instance)renderer.render(camera,{},*instance);else renderer.render(camera);renderer.capture(path);return read(path);}
void pixel(const Bytes& bytes,unsigned x,unsigned y,Vec3 expected,const char* message){const std::size_t at=54+(static_cast<std::size_t>(y)*256+x)*4;for(const auto [channel,value]:{std::pair{2,expected.x},std::pair{1,expected.y},std::pair{0,expected.z}})need(std::abs(static_cast<int>(bytes.at(at+channel))-static_cast<int>(std::lround(value*255)))<=3,message);}
float linear(unsigned char v){const float f=static_cast<float>(v)/255;return f<=.04045f?f/12.92f:std::pow((f+.055f)/1.055f,2.4f);}
float transfer(float v){return v<=.0031308f?12.92f*v:1.055f*std::pow(v,1.f/2.4f)-.055f;}
void scene_quad(SceneMesh& mesh,Vec3 a,Vec3 b,Vec3 c,Vec3 d,Vec3 normal,Vec3 color){for(const auto position:{a,b,c,a,c,d})mesh.vertices.push_back({position,normal,color,0});}
struct FloorSample {unsigned x,y;Vec3 world;};
FloorSample floor_sample(const Camera& camera,Vec3 target){
 const auto matrix=camera.view_projection(1);std::array<float,4> clip{};for(unsigned c=0;c<4;++c)clip[c]=target.x*matrix[c]+target.y*matrix[4+c]+target.z*matrix[8+c]+matrix[12+c];need(clip[3]>0,"Typed receiver sample behind camera");
 const int x=static_cast<int>(std::floor((clip[0]/clip[3]*.5f+.5f)*256)),y=static_cast<int>(std::floor((.5f-clip[1]/clip[3]*.5f)*256));need(x>=0&&x<256&&y>=0&&y<256,"Typed receiver sample outside image");
 const float sx=(2*(static_cast<float>(x)+.5f)/256-1)*std::tan(3.14159265358979323846f/8),sy=(1-2*(static_cast<float>(y)+.5f)/256)*std::tan(3.14159265358979323846f/8);
 const float cy=std::cos(camera.yaw),yaw=std::sin(camera.yaw),cp=std::cos(camera.pitch),sp=std::sin(camera.pitch);const Vec3 ray{yaw*cp+sx*cy-sy*yaw*sp,sp+sy*cp,cy*cp-sx*yaw-sy*cy*sp};need(ray.y<0,"Typed receiver sample ray needs downward direction");const float time=-camera.position.y/ray.y;
 return {static_cast<unsigned>(x),static_cast<unsigned>(y),{camera.position.x+time*ray.x,0,camera.position.z+time*ray.z}};
}
// Independent double-precision oracle for a gray dielectric plane at Z=3,
// directional incidence along -Z and diffuse-normalized engine light units.
Vec3 surface_reference(const Camera& camera,float roughness){
 const double sx=(2*128.5/256-1)*std::tan(3.14159265358979323846/8),sy=-sx;
 const double yaw=camera.yaw,rx=std::sin(yaw)+sx*std::cos(yaw),rz=std::cos(yaw)-sx*std::sin(yaw),t=(3-camera.position.z)/rz;
 const double px=camera.position.x+t*rx,py=camera.position.y+t*sy;
 const double vx=camera.position.x-px,vy=camera.position.y-py,vz=camera.position.z-3,len=std::sqrt(vx*vx+vy*vy+vz*vz);
 const double Vx=vx/len,Vy=vy/len,Vz=vz/len,hz=Vz-1,hl=std::sqrt(Vx*Vx+Vy*Vy+hz*hz),nh=-hz/hl,nv=-Vz,vh=(Vx*Vx+Vy*Vy+Vz*hz)/hl;
 const double r=roughness,a=r*r,a2=a*a,den=nh*nh*(a2-1)+1,D=a2/(3.14159265358979323846*den*den),k=(r+1)*(r+1)/8,G=nv/(nv*(1-k)+k),F=.04+.96*std::pow(1-vh,5);
 const double radiance=linear(128)* (1-F)+3.14159265358979323846*D*G*F/(4*nv);
 const float encoded=transfer(static_cast<float>(1-std::exp(-radiance)));return {encoded,encoded,encoded};
}
void stable(const RenderStats& a,const RenderStats& b){need(a.character_replacements==b.character_replacements&&a.character_buffer_allocations==b.character_buffer_allocations&&a.character_texture_allocations==b.character_texture_allocations&&a.scene_replacements==b.scene_replacements&&a.full_idle_calls==b.full_idle_calls&&a.character_active_gpu_bytes==b.character_active_gpu_bytes&&a.character_replacement_peak_gpu_bytes==b.character_replacement_peak_gpu_bytes,"Ordinary pose/rejected adoption replaced or allocated GPU resources");}
}
int main(int argc,char** argv){try{
 need(argc==3,"Pass shader and evidence directories");const std::filesystem::path output=argv[2];std::filesystem::create_directories(output);
 NativeWindow window(256,256,L"AI-BS owned character material proof",false);Dx12Renderer renderer(window,{},argv[1]);Camera camera;camera.position={};camera.yaw=camera.pitch=0;
 SceneLighting light;light.enabled=true;light.ambient={1,1,1};renderer.set_lighting(light);const auto empty=snap(renderer,window,camera,output/"empty.bmp");
 auto asset=panel();CharacterInstance instance;instance.pose=character_bind_pose(asset.mesh);renderer.set_character_asset(asset);
 SceneLighting surface_light;surface_light.enabled=true;surface_light.ambient={0,0,0};surface_light.directional=DirectionalLight{{0,0,1},{1,1,1},1};
 auto surface_candidate=asset;surface_candidate.materials[0].roughness=.6f;renderer.set_scene_character_asset({},TexturedScene{},surface_light,&surface_candidate);
 const auto satin=snap(renderer,window,camera,output/"surface-roughness06.bmp",&instance);pixel(satin,128,128,surface_reference(camera,.6f),"Roughness06 differs from independent dielectric oracle");
 surface_candidate.materials[0].roughness=.9f;renderer.set_character_asset(surface_candidate);const auto cloth=snap(renderer,window,camera,output/"surface-roughness09.bmp",&instance);pixel(cloth,128,128,surface_reference(camera,.9f),"Roughness09 differs from independent dielectric oracle");need(difference(satin,cloth)>1000,"Roughness does not change actual GPU pixels");
 surface_candidate.materials[0].roughness=.6f;renderer.set_character_asset(surface_candidate);camera.position={.9f,0,0};camera.yaw=std::atan2(-.9f,3.f);const auto oblique=snap(renderer,window,camera,output/"surface-oblique.bmp",&instance);pixel(oblique,128,128,surface_reference(camera,.6f),"Surface highlight ignores actual camera position");
 const auto stable_surface=renderer.stats();renderer.render(camera,{},instance);stable(stable_surface,renderer.stats());
 auto invalid_surface=surface_candidate;invalid_surface.materials[0].roughness=0;reject([&]{renderer.set_character_asset(invalid_surface);},"Invalid roughness accepted");stable(stable_surface,renderer.stats());
 camera.position={};camera.yaw=0;renderer.set_scene_character_asset({},TexturedScene{},light,&asset);
 const auto gray=snap(renderer,window,camera,output/"srgb-gray.bmp",&instance);const auto value=linear(128);pixel(gray,128,128,evaluate_scene_lighting(light,{0,0,3},{0,0,-1},{value,value,value},0),"sRGB albedo sampled without linear decoding");need(difference(empty,gray)>10000,"Owned character material produces no visible pixels");
 // The owned image heap must carry the *current* directional shadow SRV,
 // including a new allocation published by a later set_lighting operation.
 auto receiver=base();for(const auto position:{Vec3{-4,0,0},Vec3{-4,0,8},Vec3{4,0,8},Vec3{4,0,0}}){CharacterVertex vertex;vertex.position=position;vertex.normal={0,1,0};vertex.u=vertex.v=.25f;receiver.mesh.vertices.push_back(vertex);}receiver.mesh.indices={0,1,2,0,2,3};receiver.images={solid(128,128,128)};receiver.materials={{0,{1,1,1},0,false}};receiver.draws={{0,6,0}};validate_character_asset(receiver);CharacterInstance receiver_instance;receiver_instance.pose=character_bind_pose(receiver.mesh);
 SceneMesh caster;scene_quad(caster,{-.5f,1.5f,3.5f},{-.5f,1.5f,4.5f},{.5f,1.5f,4.5f},{.5f,1.5f,3.5f},{0,1,0},{.4f,.4f,.4f});SceneLighting receiver_light;receiver_light.enabled=true;receiver_light.ambient={.04f,.04f,.04f};receiver_light.directional=DirectionalLight{{.6f,-.8f,0},{1,1,1},1};receiver_light.shadow.center={0,0,4};receiver_light.shadow.half_extent=6;receiver_light.shadow.near_plane=.1f;receiver_light.shadow.far_plane=30;receiver_light.shadow.bias=.001f;receiver_light.shadow.resolution=2048;
 camera.position={0,5,-3};camera.pitch=-.55f;renderer.set_scene_character_asset(caster,{},receiver_light,&receiver);const auto receiver_at=floor_sample(camera,{1.125f,0,4});const Vec3 gray_linear{value,value,value};const auto lit_receiver=snap(renderer,window,camera,output/"typed-receiver-unshadowed.bmp",&receiver_instance);pixel(lit_receiver,receiver_at.x,receiver_at.y,evaluate_scene_lighting(receiver_light,receiver_at.world,{0,1,0},gray_linear,0),"Unshadowed typed material receiver differs from CPU oracle");
 receiver_light.shadow.enabled=true;renderer.set_lighting(receiver_light);const auto shadow_receiver=snap(renderer,window,camera,output/"typed-receiver-shadowed.bmp",&receiver_instance);auto receiver_expected=receiver_light;receiver_expected.shadow.enabled=false;receiver_expected.directional.reset();pixel(shadow_receiver,receiver_at.x,receiver_at.y,evaluate_scene_lighting(receiver_expected,receiver_at.world,{0,1,0},gray_linear,0),"Typed material heap uses missing/stale directional shadow SRV");need(difference(shadow_receiver,lit_receiver)>150,"Actual static caster does not shadow typed character pixels");
 receiver_light.points={{{1.125f,2,4},{.1f,.3f,1},.7f,4}};renderer.set_lighting(receiver_light);const auto point_receiver=snap(renderer,window,camera,output/"typed-receiver-point-in-shadow.bmp",&receiver_instance);receiver_expected=receiver_light;receiver_expected.shadow.enabled=false;receiver_expected.directional.reset();pixel(point_receiver,receiver_at.x,receiver_at.y,evaluate_scene_lighting(receiver_expected,receiver_at.world,{0,1,0},gray_linear,0),"Typed character directional shadow erased point-light contribution");need(difference(point_receiver,shadow_receiver)>150,"Typed character point light produced no GPU pixels");
 // With authored lighting disabled, emissive typed albedo remains linear
 // through factor composition and transfers once to presentation sRGB.
 camera.position={};camera.pitch=0;auto disabled_asset=asset;disabled_asset.materials[0].base_color={.5f,.7f,.9f};for(auto& vertex:disabled_asset.mesh.vertices){vertex.color={.8f,.6f,.4f};vertex.emission=1;}instance={};instance.pose=character_bind_pose(disabled_asset.mesh);instance.tint={.9f,.8f,.7f};renderer.set_scene_character_asset({},TexturedScene{},SceneLighting{},&disabled_asset);const auto disabled=snap(renderer,window,camera,output/"typed-disabled-linear-transfer.bmp",&instance);pixel(disabled,128,128,{transfer(value*.5f*.8f*.9f),transfer(value*.7f*.6f*.8f),transfer(value*.9f*.4f*.7f)},"Disabled-light typed linear material missing/surplus sRGB transfer");
 instance={};instance.pose=character_bind_pose(asset.mesh);renderer.set_scene_character_asset({},TexturedScene{},light,&asset);
 // Constant UVs sample exact texel centers. Adjacent patches duplicate seam
 // positions while retaining distinct UVs, exposing any position-only merging.
 auto checker=base();quad(checker.mesh,-1,0,0,1,3,.25f,.25f);quad(checker.mesh,0,1,0,1,3,.75f,.25f);quad(checker.mesh,-1,0,-1,0,3,.25f,.75f);quad(checker.mesh,0,1,-1,0,3,.75f,.75f);
 checker.images={{ImageSemantic::srgb_color,{{2,2,{255,0,0,255,0,255,0,255,0,0,255,255,255,255,0,255}}}}};generate_image_mips(checker.images[0]);checker.materials={{0,{1,1,1},0,false}};checker.draws={{0,24,0}};validate_character_asset(checker);instance.pose=character_bind_pose(checker.mesh);renderer.set_character_asset(checker);const auto corners=snap(renderer,window,camera,output/"uv-seams.bmp",&instance);
 for(const auto& sample:std::array<std::pair<std::array<unsigned,2>,Vec3>,4>{{{{76,76},{1,0,0}},{{180,76},{0,1,0}},{{76,180},{0,0,1}},{{180,180},{1,1,0}}}})pixel(corners,sample.first[0],sample.first[1],evaluate_scene_lighting(light,{0,0,3},{0,0,-1},sample.second,0),"UV seam or upper-left image origin mismatch");
 auto wrapped=checker;for(auto& vertex:wrapped.mesh.vertices){vertex.u-=3;vertex.v+=2;}renderer.set_character_asset(wrapped);need(snap(renderer,window,camera,output/"repeat.bmp",&instance)==corners,"Character sampler does not repeat signed UVs");
 // Complete mip ownership: deliberately distinct valid mip levels and strong
 // minification force the blue1x1 level, independently of mip generation tests.
 auto minified=panel();minified.images={solid(255,0,0,4)};minified.images[0].levels[1]=solid(0,255,0,2).levels[0];minified.images[0].levels[2]=solid(0,0,255).levels[0];
 const std::array<std::array<float,2>,4> uv{{{0,4096},{0,0},{4096,0},{4096,4096}}};for(std::size_t i=0;i<4;++i){minified.mesh.vertices[i].u=uv[i][0];minified.mesh.vertices[i].v=uv[i][1];}renderer.set_character_asset(minified);instance.pose=character_bind_pose(minified.mesh);pixel(snap(renderer,window,camera,output/"owned-mip.bmp",&instance),128,128,evaluate_scene_lighting(light,{0,0,3},{0,0,-1},{0,0,1},0),"Character shader does not sample retained mip chain");
 auto material=panel();material.materials[0].base_color={.5f,.7f,.9f};material.materials[0].emission=.1f;for(auto& v:material.mesh.vertices){v.color={.8f,.6f,.4f};v.emission=.05f;}instance.pose=character_bind_pose(material.mesh);instance.tint={.9f,.8f,.7f};instance.emission=.05f;renderer.set_character_asset(material);
 const Vec3 product{value*.5f*.8f*.9f,value*.7f*.6f*.8f,value*.9f*.4f*.7f};const auto composed=snap(renderer,window,camera,output/"material-factors.bmp",&instance);pixel(composed,128,128,evaluate_scene_lighting(light,{0,0,3},{0,0,-1},product,.2f),"Material/vertex/instance color-emission composition mismatch");
 // Source memory is not a runtime dependency. Mutation/destruction after upload
 // must not change the palette, materials, texture resources or pixels.
 for(auto& mip:material.images[0].levels)std::fill(mip.rgba.begin(),mip.rgba.end(),0);material.images.clear();material.materials.clear();material.draws.clear();material.mesh={};need(snap(renderer,window,camera,output/"source-destroyed.bmp",&instance)==composed,"Renderer borrows character source material/image bytes");
 const auto resources=renderer.stats();for(unsigned frame=0;frame<16;++frame)renderer.render(camera,{},instance);stable(resources,renderer.stats());need(renderer.stats().character_frames==resources.character_frames+16,"Pose frames bypass character draw");
 auto bad=asset;bad.draws[0].index_count=3;reject([&]{renderer.set_character_asset(bad);},"Incomplete material index coverage accepted");bad=asset;bad.images[0].levels[0].rgba.pop_back();reject([&]{renderer.set_character_asset(bad);},"Malformed character image accepted");bad=asset;bad.materials[0].albedo_image=9;reject([&]{renderer.set_character_asset(bad);},"Out-of-range character image accepted");const auto before_rejected=renderer.stats();auto altered=light;altered.exposure=2;reject([&]{renderer.set_scene_character_asset({},TexturedScene{},altered,&bad);},"Invalid whole-scene character transaction accepted");stable(before_rejected,renderer.stats());need(snap(renderer,window,camera,output/"rejected.bmp",&instance)==composed,"Rejected material adoption changed active pixels");
 // Encoded/decoded limits do not substitute for actual aligned GPU costs.
 // This legal~30.67MiB payload fits CPU limits, but native VB/IB/CB plus all
 // owned image allocations and fallback exceed the32MiB character profile.
 auto gpu_budget=asset;gpu_budget.mesh.vertices.resize(character_maximum_vertices,gpu_budget.mesh.vertices.front());gpu_budget.mesh.indices.resize(character_maximum_indices);for(std::size_t i=0;i<gpu_budget.mesh.indices.size();++i)gpu_budget.mesh.indices[i]=static_cast<std::uint32_t>(i%4);gpu_budget.draws[0].index_count=static_cast<std::uint32_t>(gpu_budget.mesh.indices.size());gpu_budget.images={solid(255,255,255,1024),solid(255,255,255,512)};for(unsigned i=0;i<30;++i)gpu_budget.images.push_back(solid(255,255,255));validate_character_asset(gpu_budget);const auto before_budget=renderer.stats();reject([&]{renderer.set_character_asset(gpu_budget);},"Valid encoded payload exceeded actual GPU32MiB profile without rejection");stable(before_budget,renderer.stats());need(snap(renderer,window,camera,output/"gpu-budget-rejected.bmp",&instance)==composed,"GPU allocation budget rejection changed published image");
 // Independent material draws and faithful single/double-sided behavior.
 auto layered=base();quad(layered.mesh,-1,1,-1,1,3,0,0);quad(layered.mesh,-1,1,-1,1,2,0,0,true);layered.materials={{character_no_image,{0,1,0},0,false},{character_no_image,{1,0,0},0,false}};layered.draws={{0,6,0},{6,6,1}};validate_character_asset(layered);instance={};instance.pose=character_bind_pose(layered.mesh);renderer.set_character_asset(layered);const auto culled=snap(renderer,window,camera,output/"single-sided-depth.bmp",&instance);pixel(culled,128,128,evaluate_scene_lighting(light,{0,0,3},{0,0,-1},{0,1,0},0),"Culled near back-face incorrectly writes depth before visible far material");
 layered.materials[1].double_sided=true;renderer.set_character_asset(layered);const auto double_sided=snap(renderer,window,camera,output/"double-sided.bmp",&instance);pixel(double_sided,128,128,evaluate_scene_lighting(light,{0,0,2},{0,0,1},{1,0,0},0),"Second material/double-sided backface not rendered");
 auto directional=light;directional.ambient={.03f,.03f,.03f};directional.directional=DirectionalLight{{0,0,1},{1,1,1},1};renderer.set_lighting(directional);pixel(snap(renderer,window,camera,output/"backface-normal.bmp",&instance),128,128,evaluate_scene_lighting(directional,{0,0,2},{0,0,1},{1,0,0},0),"Double-sided backface normal was not reversed for lighting");
 // Old resource setters retain a material character; all-layer publication may
 // explicitly clear it. Legacy mesh calls remain a separate compatible path.
 renderer.set_scene({},TexturedScene{},light);pixel(snap(renderer,window,camera,output/"old-setter-preserves.bmp",&instance),128,128,evaluate_scene_lighting(light,{0,0,2},{0,0,1},{1,0,0},0),"Legacy three-layer setter lost material character");renderer.set_scene_character_asset({},TexturedScene{},light,nullptr);need(snap(renderer,window,camera,output/"explicit-clear.bmp")==empty,"Explicit character asset clear changed unrelated scene");
 renderer.set_character(asset.mesh);instance.pose=character_bind_pose(asset.mesh);need(difference(snap(renderer,window,camera,output/"legacy-mesh.bmp",&instance),empty)>10000,"Legacy CharacterMesh route failed after material assets");
 renderer.set_scene_character_asset({},TexturedScene{},light,&asset);instance.pose=character_bind_pose(asset.mesh);const auto republished=snap(renderer,window,camera,output/"joint-republished.bmp",&instance);need(republished==gray,"Whole-scene typed character publication changed owned source material");
 window.minimize();window.poll();const auto paused=renderer.stats().frames;renderer.render(camera,{},instance);need(renderer.stats().frames==paused,"Minimized textured character submitted work");window.restore(false);window.set_size(320,192);window.poll();renderer.render(camera,{},instance);renderer.capture(output/"resized.bmp");window.set_size(256,256);window.poll();need(snap(renderer,window,camera,output/"restored.bmp",&instance)==gray,"Owned material resources lost across resize/minimize");
 renderer.wait_idle();const auto stats=renderer.stats();if(stats.debug_errors||stats.debug_warnings)for(const auto& message:stats.debug_messages)std::cerr<<message<<'\n';need(stats.debug_layer&&stats.debug_errors==0&&stats.debug_warnings==0,"Textured character DX12 diagnostics");need(stats.character_active_gpu_bytes>0&&stats.character_active_gpu_bytes<=32u*1024u*1024u,"Character texture GPU allocation not included in active budget");need(stats.character_texture_allocations>0,"Character image allocation counters absent");
 std::ofstream report(output/"verification.json");report<<"{\"status\":\"passed\",\"checks\":"<<checks<<",\"frames\":"<<stats.frames<<",\"character_frames\":"<<stats.character_frames<<",\"character_material_draws\":"<<stats.character_material_draws<<",\"character_texture_allocations\":"<<stats.character_texture_allocations<<",\"active_gpu_bytes\":"<<stats.character_active_gpu_bytes<<",\"replacement_peak_gpu_bytes\":"<<stats.character_replacement_peak_gpu_bytes<<",\"debug_errors\":"<<stats.debug_errors<<",\"debug_warnings\":"<<stats.debug_warnings<<",\"uv_seams_and_srgb_and_mips\":true,\"source_ownership\":true,\"culling_and_backface_normals\":true,\"typed_shadow_point_oracles\":true,\"typed_disabled_linear_transfer_oracle\":true,\"likeness_claim\":false}\n";need(static_cast<bool>(report),"Could not write GPU proof report");std::cout<<"PASS "<<checks<<" character material GPU checks\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL character material GPU: "<<e.what()<<'\n';return 1;}}
