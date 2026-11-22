#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/asset_scene.hpp>
#include <aibs/asset_store.hpp>
#include <optional>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <set>
#include <stdexcept>
#include <string>
#include <thread>

namespace {
void require(bool condition,const char* message) { if(!condition) throw std::runtime_error(message); }
std::string quote(const std::string& text) {
 std::string result="\"";
 for(const unsigned char c:text) {
  if(c=='"'||c=='\\') result+='\\';
  if(c>=32) result+=static_cast<char>(c);
 }
 return result+'"';
}
std::string ascii(const std::wstring& text) {
 std::string result;
 for(const wchar_t c:text) { require(c>=32&&c<=126,"Asset ID must be ASCII");result+=static_cast<char>(c); }
 return result;
}
std::filesystem::path executable_directory() {
 std::wstring value(32768,L'\0');const auto length=GetModuleFileNameW(nullptr,value.data(),static_cast<DWORD>(value.size()));
 require(length>0&&length<value.size(),"Cannot locate native executable");value.resize(length);
 return std::filesystem::path(value).parent_path();
}
std::vector<char> bytes(const std::filesystem::path& path) {
 std::ifstream stream(path,std::ios::binary|std::ios::ate);require(stream.good(),"Cannot read GPU capture");
 const auto count=stream.tellg();require(count>0&&count<=32*1024*1024,"Invalid GPU capture length");
 std::vector<char> result(static_cast<std::size_t>(count));stream.seekg(0);stream.read(result.data(),count);
 require(stream.good(),"Incomplete GPU capture");return result;
}
std::uint64_t difference(const std::vector<char>& first,const std::vector<char>& second) {
 require(first.size()==second.size(),"GPU captures have different dimensions");
 std::uint64_t result=0;for(std::size_t i=54;i<first.size();++i) if(first[i]!=second[i]) ++result;
 return result;
}
void write_report(const std::filesystem::path& path,bool success,const std::string& error,const std::string& asset_id,
 const std::string& digest,std::size_t triangles,std::size_t materials,const aibs::RenderStats& stats,
 std::uint64_t pixels,std::uint64_t geometry_difference,std::uint64_t material_difference,bool input_verified) {
 if(path.empty()) return;
 if(!path.parent_path().empty()) std::filesystem::create_directories(path.parent_path());
 std::ofstream stream(path,std::ios::binary);
 stream<<"{\"schema_version\":1,\"status\":"<<quote(success?"passed":"failed")
  <<",\"error\":"<<quote(error)<<",\"asset_id\":"<<quote(asset_id)<<",\"asset_sha256\":"<<quote(digest)
  <<",\"triangles\":"<<triangles<<",\"materials\":"<<materials
  <<",\"source_fallback\":false,\"save_formats_changed\":false,\"presentation_only\":true"
  <<",\"adapter\":"<<quote(stats.adapter)<<",\"metrics\":{\"debug_errors\":"<<stats.debug_errors
  <<",\"debug_layer\":"<<(stats.debug_layer?"true":"false")<<",\"frames\":"<<stats.frames
  <<",\"nonbackground_pixels\":"<<pixels<<",\"asset_gpu_bytes_changed\":"<<geometry_difference
  <<",\"material_gpu_bytes_changed\":"<<material_difference<<",\"camera_input_verified\":"<<(input_verified?"true":"false")<<"}}\n";
 stream.close();
 require(stream.good(),"Cannot write asset showcase report");
}
}

int run_asset_showcase(int argc,wchar_t** argv) {
 std::filesystem::path root,capture,report;
 std::string asset_id,digest;
 bool self_test=false,input_verified=false;
 std::size_t triangles=0,materials=0;
 std::uint64_t pixels=0,geometry_difference=0,material_difference=0;
 aibs::RenderStats stats;
 try {
  std::set<std::wstring> seen;
  for(int i=1;i<argc;++i) {
   const std::wstring option(argv[i]);require(seen.insert(option).second,"Duplicate asset showcase option");
   if(option==L"--asset-showcase") continue;
   if(option==L"--self-test") { self_test=true;continue; }
   require(i+1<argc,"Missing asset showcase option value");
   if(option==L"--asset-root") root=argv[++i];
   else if(option==L"--asset-id") asset_id=ascii(argv[++i]);
   else if(option==L"--capture") capture=argv[++i];
   else if(option==L"--report") report=argv[++i];
   else throw std::invalid_argument("Unknown asset showcase option");
  }
  require(!root.empty()&&!asset_id.empty(),"Use --asset-showcase --asset-root COOKED_FOLDER --asset-id UUID");
  require(!self_test||(!capture.empty()&&!report.empty()),"Asset self-test requires capture and report");
  std::optional<aibs::SurfaceMeshAsset> surface;
  aibs::MeshAsset asset;
  std::array<char,9> catalog_header{};
  {std::ifstream declaration(root/"catalog.aibcat",std::ios::binary);declaration.read(catalog_header.data(),catalog_header.size());require(declaration.gcount()==9,"Missing bounded asset catalog header");}
  if(std::string_view(catalog_header.data(),catalog_header.size())=="AIBCAT 2\n"){
   auto pack=aibs::inspect_visual_asset_pack(root);require(pack.reference.asset_id==asset_id,"Selected asset differs from typed catalog identity");
   require(std::holds_alternative<aibs::SurfaceMeshAsset>(pack.asset.payload),"Expected typed surface payload");
   digest=pack.reference.asset_sha256;surface=std::move(std::get<aibs::SurfaceMeshAsset>(pack.asset.payload));asset=surface->geometry;
  }else{
   const aibs::AssetCatalog catalog(root);asset=catalog.load(asset_id);
   for(const auto& record:catalog.records())if(record.asset_id==asset_id)digest=record.sha256;
  }
  require(!digest.empty(),"Selected asset has no catalog identity");
  triangles=asset.indices.size()/3;materials=asset.materials.size();
  auto scene=aibs::make_motherboard_scene();
  const auto base=scene;
  aibs::TexturedScene textured;
  if(surface)textured=aibs::surface_scene(*surface,{-13,2.8f,-5});
  else aibs::append_asset_mesh(scene,asset,{-13,2.8f,-5});
  if(!capture.empty()&&!capture.parent_path().empty()) std::filesystem::create_directories(capture.parent_path());
  SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
  aibs::NativeWindow window(1200,800,L"AI-BS Motherboard Parts | WASD move | Right mouse look | Space/Ctrl rise/lower | Esc close",!self_test);
  aibs::Dx12Renderer renderer(window,base,executable_directory()/"shaders");
  aibs::Camera camera;camera.position={7,15,-25};camera.yaw=-.7853982f;camera.pitch=-.30f;
  const auto draw=[&] {
   for(unsigned frame=0;frame<4;++frame) { require(window.poll(),"Asset window closed during capture");renderer.render(camera); }
  };
  if(self_test) {
   const auto original=camera.position;
   const auto handle=static_cast<HWND>(window.native_handle());
   SendMessageW(handle,WM_KEYDOWN,'W',0);window.poll();camera.update(window.input(),1.f/60);
   SendMessageW(handle,WM_KEYUP,'W',0);window.poll();
   input_verified=camera.position!=original;require(input_verified,"Native camera movement input failed");camera.position=original;
   draw();auto baseline=capture;baseline+=L".baseline.bmp";renderer.capture(baseline);
   const auto baseline_bytes=bytes(baseline);
   renderer.set_scene(scene,textured);draw();pixels=renderer.capture(capture);const auto asset_bytes=bytes(capture);
   geometry_difference=difference(baseline_bytes,asset_bytes);require(geometry_difference>100,"Cooked mesh did not change GPU pixels");
   auto changed=asset;for(auto& material:changed.materials) {material.base_color={.95f,.05f,.65f};material.emission=1;}
   auto variant=base;aibs::TexturedScene changed_textures;
   if(surface){auto changed_surface=*surface;changed_surface.geometry=changed;changed_textures=aibs::surface_scene(changed_surface,{-13,2.8f,-5});}
   else aibs::append_asset_mesh(variant,changed,{-13,2.8f,-5});
   renderer.set_scene(variant,changed_textures);draw();
   auto variant_path=capture;variant_path+=L".material.bmp";renderer.capture(variant_path);
   material_difference=difference(asset_bytes,bytes(variant_path));require(material_difference>100,"Asset material did not affect GPU pixels");
   renderer.set_scene(scene,textured);draw();pixels=renderer.capture(capture);
   require(pixels>10000,"Asset GPU capture is blank");renderer.wait_idle();stats=renderer.stats();
   require(stats.debug_errors==0,"Asset rendering produced DX12 debug errors");
   write_report(report,true,"",asset_id,digest,triangles,materials,stats,pixels,geometry_difference,material_difference,input_verified);
   std::cout<<"PASS: cooked motherboard mesh/material GPU proof; triangles="<<triangles<<" materials="<<materials<<'\n';
  } else {
   renderer.set_scene(scene,textured);auto previous=std::chrono::steady_clock::now();
   while(window.poll()) {
    const auto now=std::chrono::steady_clock::now();const auto elapsed=std::chrono::duration<float>(now-previous).count();previous=now;
    if(window.minimized()) { std::this_thread::sleep_for(std::chrono::milliseconds(20));continue; }
    camera.update(window.input(),elapsed);renderer.render(camera);
   }
   renderer.wait_idle();stats=renderer.stats();require(stats.debug_errors==0,"Asset rendering produced DX12 debug errors");
  }
  return 0;
 } catch(const std::exception& error) {
  std::cerr<<"Asset showcase failed: "<<error.what()<<'\n';
  try {write_report(report,false,error.what(),asset_id,digest,triangles,materials,stats,pixels,geometry_difference,material_difference,input_verified);}
  catch(const std::exception& reporting) {std::cerr<<reporting.what()<<'\n';}
  return 1;
 }
}
