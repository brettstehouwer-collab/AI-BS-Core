#include <aibs/textured_scene.hpp>
#include <aibs/surface_assets.hpp>
#include <aibs/engine.hpp>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
void need(bool b,const char*m){if(!b)throw std::runtime_error(m);}
template<class F>void reject(F f){bool r=false;try{f();}catch(const std::invalid_argument&){r=true;}need(r,"Invalid scene accepted");}
std::vector<char> read(const std::filesystem::path&p){std::ifstream f(p,std::ios::binary);return {(std::istreambuf_iterator<char>(f)),{}};}
int main(int argc,char**argv){try{
 need(argc==4,"Pass shader, evidence and original OBJ paths");const std::filesystem::path output=argv[2];std::filesystem::create_directories(output);
 TexturedScene s;s.images.push_back({ImageSemantic::srgb_color,{{2,2,{255,30,20,255,20,255,30,255,20,30,255,255,255,230,20,255}}}});generate_image_mips(s.images[0]);
 s.vertices={{{-1,-1,3},{0,0,-1},0,1},{{-1,1,3},{0,0,-1},0,0},{{1,1,3},{0,0,-1},1,0},{{-1,-1,3},{0,0,-1},0,1},{{1,1,3},{0,0,-1},1,0},{{1,-1,3},{0,0,-1},1,1}};
 s.draws.push_back({0,6,0,{1,1,1},1});validate_textured_scene(s);
 const auto original_image=s.images[0];
 auto bad=s;bad.vertices[0].u=std::numeric_limits<float>::quiet_NaN();reject([&]{validate_textured_scene(bad);});bad=s;bad.draws[0].image=1;reject([&]{validate_textured_scene(bad);});
 NativeWindow window(256,256,L"AI-BS actual texture proof",false);Dx12Renderer renderer(window,{},argv[1]);Camera camera;camera.position={0,0,0};camera.yaw=camera.pitch=0;
 renderer.render(camera);renderer.capture(output/"empty.bmp");const auto empty=read(output/"empty.bmp");
 renderer.set_textured_scene(s);renderer.render(camera);need(renderer.capture(output/"textured.bmp")>10000,"Textured quad absent from GPU readback");const auto textured=read(output/"textured.bmp");need(textured!=empty,"Texture produced no pixels");
 for(auto& level:s.images[0].levels)for(std::size_t p=0;p<level.rgba.size();p+=4){level.rgba[p]=10;level.rgba[p+1]=20;level.rgba[p+2]=250;}
 renderer.set_textured_scene(s);renderer.render(camera);renderer.capture(output/"changed.bmp");const auto changed=read(output/"changed.bmp");std::size_t differences=0;for(std::size_t n=54;n<changed.size();++n)differences+=changed[n]!=textured[n];need(differences>10000,"Changing actual texture bytes did not affect GPU pixels");
 reject([&]{renderer.set_textured_scene(bad);});renderer.render(camera);renderer.capture(output/"rejected.bmp");need(read(output/"rejected.bmp")==changed,"Rejected texture replacement changed visible pixels");
 for(unsigned n=0;n<12;++n){renderer.set_textured_scene(s);renderer.render(camera);}
 window.set_size(320,240);window.poll();renderer.render(camera);window.minimize();window.poll();const auto frames=renderer.stats().frames;renderer.render(camera);need(renderer.stats().frames==frames,"Minimized rendering did not suspend");window.restore(false);window.set_size(256,256);window.poll();renderer.render(camera);
 renderer.set_textured_scene({});renderer.render(camera);renderer.capture(output/"cleared.bmp");need(read(output/"cleared.bmp")==empty,"Clearing textures did not restore prior base scene");
 const auto obj_bytes=read(argv[3]);const std::vector<MeshMaterial> materials{{"capacitor_body",{1,1,1},.3f},{"metal_contacts",{.7f,.7f,.7f},0}};
 auto asset=import_surface_obj(std::string_view(obj_bytes.data(),obj_bytes.size()),materials,new_uuid(),"Original Blender capacitor",ObjUvOrigin::bottom_left);asset.images={original_image};asset.albedo_images={0,0};
 renderer.set_scene(make_motherboard_scene());Camera board_camera;renderer.render(board_camera);renderer.capture(output/"board-base.bmp");const auto board=read(output/"board-base.bmp");
 renderer.set_textured_scene(surface_scene(asset,{-13,3,-5},{10,10,10}));renderer.render(board_camera);renderer.capture(output/"board-capacitor.bmp");const auto imported=read(output/"board-capacitor.bmp");std::size_t imported_difference=0;for(std::size_t n=54;n<board.size();++n)imported_difference+=board[n]!=imported[n];need(imported_difference>100,"Imported Blender UV geometry absent from motherboard readback");
 auto over_budget=s;over_budget.vertices.resize(999999,s.vertices[0]);over_budget.draws[0].count=999999;reject([&]{renderer.set_textured_scene(over_budget);});renderer.render(board_camera);renderer.capture(output/"budget-rejected.bmp");need(read(output/"budget-rejected.bmp")==imported,"Aggregate budget failure changed the published scene");
 reject([&]{renderer.set_scene(SceneMesh{},bad);});renderer.render(board_camera);renderer.capture(output/"joint-rejected.bmp");need(read(output/"joint-rejected.bmp")==imported,"Failed joint publication changed base geometry or texture layer");
 renderer.set_scene(SceneMesh{},TexturedScene{});renderer.render(camera);renderer.capture(output/"joint-cleared.bmp");need(read(output/"joint-cleared.bmp")==empty,"Joint empty scene publication failed");
 renderer.wait_idle();const auto stats=renderer.stats();need(stats.debug_layer&&stats.debug_errors==0,"D3D12 debug validation failed/unavailable");
 std::ofstream report(output/"verification.json");report<<"{\"status\":\"passed\",\"changed_pixel_bytes\":"<<differences<<",\"imported_geometry_pixel_bytes\":"<<imported_difference<<",\"debug_errors\":"<<stats.debug_errors<<",\"debug_warnings\":"<<stats.debug_warnings<<",\"frames\":"<<stats.frames<<"}\n";
 std::cout<<"PASS native textured GPU pixels, material replacement, rejection rollback, resize/minimize and clear\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
