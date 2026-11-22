#include <aibs/render.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
using namespace aibs;
int main(int argc,char** argv){try{
 if(argc!=4)throw std::runtime_error("Expected mode, shaders, new evidence directory");
 const std::string mode=argv[1];const std::filesystem::path root=argv[3];
 if(std::filesystem::exists(root))throw std::runtime_error("Preserve existing evidence; use a fresh output directory");
 std::filesystem::create_directories(root);
 NativeWindow window(640,480,L"AI-BS owned renderer validation proof",false);
 const auto scene=make_motherboard_scene();
 bool inherited=false;std::unique_ptr<Dx12Renderer> renderer;
 if(mode=="legacy")renderer=std::make_unique<Dx12Renderer>(window,scene,argv[2]);
 else if(mode=="enabled")renderer=std::make_unique<Dx12Renderer>(window,scene,argv[2],RenderValidationMode::enable_if_available);
 else if(mode=="skip")renderer=std::make_unique<Dx12Renderer>(window,scene,argv[2],RenderValidationMode::do_not_enable);
 else if(mode=="inherited"){
  {Dx12Renderer prior(window,scene,argv[2]);inherited=prior.stats().debug_layer;}
  renderer=std::make_unique<Dx12Renderer>(window,scene,argv[2],RenderValidationMode::do_not_enable);
  if(renderer->stats().debug_layer!=inherited)throw std::runtime_error("Existing validation was disabled or misreported");
 }else if(mode=="invalid"){
  bool rejected=false;try{Dx12Renderer invalid(window,scene,argv[2],static_cast<RenderValidationMode>(999));}catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("Invalid validation mode accepted");
  std::cout<<"{\"status\":\"passed\",\"invalid_mode_rejected\":true}\n";return 0;
 }else throw std::runtime_error("Unknown fixture mode");
 Camera camera;for(int n=0;n<4;++n)renderer->render(camera);
 const auto pixels=renderer->capture(root/"frame.bmp");renderer->wait_idle();const auto stats=renderer->stats();
 if(pixels<100||stats.frames!=4||stats.debug_errors||stats.debug_warnings)throw std::runtime_error("Actual native render or GPU diagnostics failed");
 std::ofstream report(root/"result.json");report<<"{\"status\":\"passed\",\"mode\":\""<<mode<<"\",\"debug_layer_observed\":"<<(stats.debug_layer?"true":"false")<<",\"frames\":"<<stats.frames<<",\"nonbackground_pixels\":"<<pixels<<",\"debug_errors\":"<<stats.debug_errors<<",\"debug_warnings\":"<<stats.debug_warnings<<"}\n";
 report.close();if(!report.good())throw std::runtime_error("Cannot retain proof report");
 std::cout<<mode<<" actual DX12 render and validation observation passed\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
