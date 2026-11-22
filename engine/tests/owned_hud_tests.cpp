#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/render.hpp>
#include "owned_hud.hpp"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
unsigned checks=0;
void need(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
template<class F>void rejects(F action){bool failed=false;try{action();}catch(const std::invalid_argument&){failed=true;}need(failed,"Malformed/foreign HUD rejected");}
bool inside(const owned_hud::Snapshot& hud,UINT x,UINT y){for(std::size_t n=0;n<hud.count();++n){const auto& r=hud.region(n);if(x>=r.x&&y>=r.y&&x-r.x<r.width&&y-r.y<r.height)return true;}return false;}
bool covered_later(const owned_hud::Snapshot& hud,std::size_t current,UINT x,UINT y){
 for(std::size_t n=current+1;n<hud.count();++n){const auto& r=hud.region(n);if(x>=r.x&&y>=r.y&&x-r.x<r.width&&y-r.y<r.height)return true;}return false;
}
std::uint64_t expected_pixels(const CapturedFrame& frame,const owned_hud::Snapshot& hud,bool match){
 std::uint64_t glyphs=0,matched=0;
 for(std::size_t n=0;n<hud.count();++n){const auto& r=hud.region(n);for(UINT y=0;y<r.height;++y)for(UINT x=0;x<r.width;++x){
  // Long status panels overlap the centre crosshair. The renderer composes
  // regions in order; validate each final pixel against its last opaque owner.
  if(covered_later(hud,n,r.x+x,r.y+y))continue;
  const auto from=static_cast<std::size_t>(r.offset)+static_cast<std::size_t>(y)*r.pitch+x*4u;
  const auto to=((static_cast<std::size_t>(r.y)+y)*frame.width+r.x+x)*4;
  if(match){need(frame.bgra[to]==hud.bytes()[from+2]&&frame.bgra[to+1]==hud.bytes()[from+1]&&frame.bgra[to+2]==hud.bytes()[from]&&frame.bgra[to+3]==std::byte{255},"GPU target contains exact opaque HUD raster");}
  if(std::to_integer<unsigned>(hud.bytes()[from])>100&&std::to_integer<unsigned>(hud.bytes()[from+1])>100){++glyphs;if(frame.bgra[to]==hud.bytes()[from+2]&&frame.bgra[to+1]==hud.bytes()[from+1]&&frame.bgra[to+2]==hud.bytes()[from])++matched;}
 }}
 need(glyphs>100,"Actual private status/crosshair raster has glyphs");return matched;
}
WNDPROC prior=nullptr;
LRESULT CALLBACK test_proc(HWND window,UINT message,WPARAM w,LPARAM l){const auto result=CallWindowProcW(prior,window,message,w,l);if(message==WM_GETMINMAXINFO){auto* limits=reinterpret_cast<MINMAXINFO*>(l);limits->ptMaxTrackSize={9000,9000};}return result;}
const std::wstring retained_chapter=
 L"WASD walk | Right-drag look | Space jump | V camera | F2 inspect | F5 retry | F9 reload\n"
 L"E (centre): Move closer to read: Controller and turning | B relay | Delete dismantle | Ctrl+Y help / Ctrl+Z decline\n"
 L"Find isolation switch: 23 m, behind-right (direction only; use a clear path).\n"
 L"I'm here. This nook has reserve light, but we are still inside Jenison. Start with what still responds. "
 L"Follow the west signal path to the supply, or look around before we go.\n"
 L"F6 Follow | F7 Wait | F8 Recall: Adam is following. F7: Wait | F8: Recall.\n"
 L"Authored Adam hint: The diagnostic probe is in the reserve nook. You choose when to pick it up.\n"
 L"Recorded (acknowledged): No acknowledged chapter outcomes yet.\n"
 L"SAVED | visible 0 | durable 0\n"
 L"Jenison is not home. Follow what still responds.";
HFONT verify_full_status(HWND owner,const std::wstring& expected){
 const auto status=FindWindowExW(owner,nullptr,L"STATIC",nullptr);need(status!=nullptr,"Actual owned status control");
 const int length=GetWindowTextLengthW(status);std::wstring value(static_cast<std::size_t>(length)+1,L'\0');
 GetWindowTextW(status,value.data(),length+1);value.resize(static_cast<std::size_t>(length));need(value==expected,"Full retained chapter text survives font fitting");
 const auto font=reinterpret_cast<HFONT>(SendMessageW(status,WM_GETFONT,0,0));need(font!=nullptr,"Actual status font remains accessible");
 RECT panel{},client{};need(GetWindowRect(status,&panel)&&GetClientRect(owner,&client),"Actual fitted status/client bounds");
 MapWindowPoints(nullptr,owner,reinterpret_cast<POINT*>(&panel),2);
 need(panel.left>=0&&panel.top>=0&&panel.right<=client.right&&panel.bottom<=client.bottom,"Fitted status is completely inside client");
 HDC dc=GetDC(status);need(dc!=nullptr,"Actual fitted-font measurement DC");const auto previous=SelectObject(dc,font);
 RECT measured{0,0,panel.right-panel.left,0};DrawTextW(dc,value.c_str(),-1,&measured,DT_CALCRECT|DT_WORDBREAK|DT_EXPANDTABS);
 SelectObject(dc,previous);ReleaseDC(status,dc);
 need(measured.bottom-measured.top<=panel.bottom-panel.top,"Full actual selected-font text fits visible HUD");
 LOGFONTW description{};need(GetObjectW(font,sizeof(description),&description)==sizeof(description),"Actual selected font identity is inspectable");
 need(font==GetStockObject(DEFAULT_GUI_FONT)||std::abs(description.lfHeight)>=12,"Fitted HUD retains twelve-pixel floor");
 return font;
}
int wmain(int argc,wchar_t** argv){try{
 SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
 need(argc==3||argc==4,"Expected shader directory, new evidence directory, optional baseline-missing");
 const bool baseline=argc==4&&std::wstring_view(argv[3])==L"baseline-missing";
 const std::filesystem::path out=argv[2];need(!std::filesystem::exists(out),"Evidence scope must be new");std::filesystem::create_directories(out);
 SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
 NativeWindow window(1280,720,L"AI-BS actual GPU HUD visibility diagnostic",true);window.poll();
 const auto hwnd=static_cast<HWND>(window.native_handle());prior=reinterpret_cast<WNDPROC>(SetWindowLongPtrW(hwnd,GWLP_WNDPROC,reinterpret_cast<LONG_PTR>(test_proc)));need(prior!=nullptr,"Test-only window sizing override");
 rejects([]{owned_hud::Snapshot rejected(GetDesktopWindow());});
 Dx12Renderer renderer(window,make_motherboard_scene(),argv[1]);Camera camera;renderer.render(camera);
 CapturedFrame before,frame;need(renderer.capture_frame(before),"Baseline GPU frame captured");renderer.capture(out/L"scene-before.bmp");
 window.set_status(L"ACTUAL HUD VISIBILITY\nFind isolation switch: 37 m, ahead-left.\nSAVED | visible 6 | durable 6");window.poll();
 owned_hud::Snapshot hud(hwnd);need(hud.refresh(window.width(),window.height())&&hud.count()==2,"Two actual native STATIC controls rasterized");
 const auto version=hud.version();const auto* stable=hud.bytes().data();const auto rasters=owned_hud::rasterizations.load();
 need(!hud.refresh(window.width(),window.height())&&hud.version()==version&&hud.bytes().data()==stable&&owned_hud::rasterizations==rasters,"Unchanged descriptors reuse CPU raster without allocation");
 renderer.render(camera);need(renderer.capture_frame(frame),"GPU frame after HUD publication");renderer.capture(out/L"hud-in-gpu-target.bmp");
 const auto matches=expected_pixels(frame,hud,!baseline);
 if(baseline){need(matches<10,"Old renderer target lacks actual private HUD glyphs");std::ofstream report(out/L"result.json");report<<"{\"status\":\"baseline_missing_confirmed\",\"checks\":"<<checks<<",\"matching_glyph_pixels\":"<<matches<<"}";std::cout<<"BASELINE missing confirmed, checks="<<checks<<'\n';return 0;}
 std::uint64_t outside=0;for(UINT y=0;y<frame.height;++y)for(UINT x=0;x<frame.width;++x)if(!inside(hud,x,y)){const auto at=(static_cast<std::size_t>(y)*frame.width+x)*4;need(std::equal(frame.bgra.begin()+at,frame.bgra.begin()+at+4,before.bgra.begin()+at),"Pixels outside overlay remain the actual scene");++outside;}
 const auto& cross=hud.region(1);need(cross.width==16&&cross.height==16&&cross.x==window.width()/2-8&&cross.y==window.height()/2-8,"Actual centre crosshair rectangle");
 for(unsigned n=0;n<6;++n)renderer.render(camera);
 const auto allocations=owned_hud::upload_allocations.load(),steady_rasters=owned_hud::rasterizations.load(),idle=renderer.stats().full_idle_calls;
 for(unsigned n=0;n<12;++n)renderer.render(camera);
 need(owned_hud::upload_allocations==allocations&&owned_hud::rasterizations==steady_rasters&&renderer.stats().full_idle_calls==idle,"Unchanged frames reuse both upload slots with no raster/allocation/full idle");
 need(renderer.capture_frame(frame),"Stable slots GPU readback");expected_pixels(frame,hud,true);
 window.set_status(L"SAVED 6");window.poll();need(hud.refresh(window.width(),window.height()),"Changed text produces new raster");
 for(unsigned n=0;n<5;++n){renderer.render(camera);need(renderer.capture_frame(frame),"Changed text slot GPU frame");expected_pixels(frame,hud,true);}
 for(UINT y=0;y<frame.height;++y)for(UINT x=0;x<frame.width;++x)if(!inside(hud,x,y)){
  const auto at=(static_cast<std::size_t>(y)*frame.width+x)*4;
  need(std::equal(frame.bgra.begin()+at,frame.bgra.begin()+at+4,before.bgra.begin()+at),"Shorter HUD removes all former panel/glyph pixels outside its new rectangle");
 }
 renderer.capture(out/L"changed-text.bmp");
 for(const auto dimensions:{std::pair{1920u,1080u},std::pair{1280u,720u}}){window.set_size(dimensions.first,dimensions.second);window.poll();
  renderer.render(camera);need(hud.refresh(window.width(),window.height()),"Resize updates HUD snapshot");need(renderer.capture_frame(frame)&&frame.width==dimensions.first&&frame.height==dimensions.second,"Resized completed target dimensions");expected_pixels(frame,hud,true);}
 // Regression: the actual chapter's 629-pixel HUD was clipped to616 at960x640.
 // At640x480 it needs the bounded fitted font; a larger resize restores stock.
 window.set_status(retained_chapter);window.set_size(640,480);window.poll();
 const auto fitted=verify_full_status(hwnd,retained_chapter);
 need(fitted!=GetStockObject(DEFAULT_GUI_FONT),"Small retained-chapter fixture exercises actual font change");
 need(hud.refresh(window.width(),window.height()),"Fitted font/geometry publishes a new actual HUD raster");
 const auto fitted_version=hud.version();
 for(unsigned n=0;n<5;++n){renderer.render(camera);need(renderer.capture_frame(frame)&&frame.width==640&&frame.height==480,"Fitted HUD actual GPU target640x480");expected_pixels(frame,hud,true);}
 const auto& fitted_cross=hud.region(1);need(fitted_cross.x==312&&fitted_cross.y==232&&fitted_cross.width==16&&fitted_cross.height==16,"Fitted HUD keeps actual centre crosshair");
 renderer.capture(out/L"retained-chapter-fitted640.bmp");
 window.set_size(1440,900);window.poll();need(verify_full_status(hwnd,retained_chapter)==GetStockObject(DEFAULT_GUI_FONT),"Large resize restores original stock font without losing text");
 need(hud.refresh(window.width(),window.height())&&hud.version()>fitted_version,"Restored actual font/geometry invalidates cached raster");
 for(unsigned n=0;n<5;++n){renderer.render(camera);need(renderer.capture_frame(frame)&&frame.width==1440&&frame.height==900,"Restored HUD actual GPU target1440x900");expected_pixels(frame,hud,true);}
 const auto& restored_cross=hud.region(1);need(restored_cross.x==712&&restored_cross.y==442&&restored_cross.width==16&&restored_cross.height==16,"Restored font keeps actual centre crosshair");
 renderer.capture(out/L"retained-chapter-restored1440.bmp");
 window.set_size(1280,720);window.set_status(L"SAVED 6");window.poll();hud.refresh(window.width(),window.height());renderer.render(camera);
 window.minimize();window.poll();const auto frames=renderer.stats().frames;renderer.render(camera);need(renderer.stats().frames==frames&&!renderer.capture_frame(frame),"Minimized window fabricates no present/readback");
 window.restore();window.poll();renderer.render(camera);need(renderer.capture_frame(frame),"Restored GPU target available");hud.refresh(window.width(),window.height());expected_pixels(frame,hud,true);
 // Clip a partly off-client owned crosshair safely; no copy can escape target.
 HWND child=FindWindowExW(hwnd,nullptr,L"STATIC",nullptr);child=FindWindowExW(hwnd,child,L"STATIC",nullptr);need(child!=nullptr,"Owned crosshair located");
 SetWindowPos(child,nullptr,-8,-8,16,16,SWP_NOZORDER|SWP_NOACTIVATE);need(hud.refresh(window.width(),window.height()),"Clipped control updates snapshot");renderer.render(camera);need(renderer.capture_frame(frame),"Clipped HUD GPU frame");expected_pixels(frame,hud,true);
 need(hud.region(1).x==0&&hud.region(1).y==0&&hud.region(1).width==8&&hud.region(1).height==8,"Partly off-client control clips source and destination");
 const auto unchanged_version=hud.version();const auto* unchanged_pixels=hud.bytes().data();
 const auto extra=CreateWindowExW(0,L"STATIC",L"Third control rejected",WS_CHILD|WS_VISIBLE,0,0,20,20,hwnd,nullptr,GetModuleHandleW(nullptr),nullptr);
 need(extra!=nullptr,"Extra owned control fixture");rejects([&]{hud.refresh(window.width(),window.height());});
 const auto rejected_presents=renderer.stats().frames;rejects([&]{renderer.render(camera);});
 need(renderer.stats().frames==rejected_presents,"Actual renderer rejects excess controls before submission/Present");DestroyWindow(extra);
 need(hud.version()==unchanged_version&&hud.bytes().data()==unchanged_pixels,"Rejected excess controls preserve accepted raster");
 HWND status=FindWindowExW(hwnd,nullptr,L"STATIC",nullptr);
 const std::wstring excessive(owned_hud::maximum_text+1,L'W');SetWindowTextW(status,excessive.c_str());
 rejects([&]{hud.refresh(window.width(),window.height());});need(hud.version()==unchanged_version,"Rejected overlong text cannot publish");
 rejects([&]{renderer.render(camera);});need(renderer.stats().frames==rejected_presents,"Actual renderer rejects overlong text before submission/Present");
 window.set_status(L"Bound check");SetWindowPos(status,nullptr,0,0,4096,1080,SWP_NOZORDER|SWP_NOACTIVATE);
 const auto rejected_rasters=owned_hud::rasterizations.load();rejects([&]{hud.refresh(8192,8192);});
 need(owned_hud::rasterizations==rejected_rasters&&hud.version()==unchanged_version,"Oversize aligned upload rejects before DIB allocation/raster publication");
 window.set_status(L"Recovered bounded HUD");window.poll();hud.refresh(window.width(),window.height());renderer.render(camera);need(renderer.capture_frame(frame),"Renderer continues after pre-submit diagnostic rejection");expected_pixels(frame,hud,true);
 renderer.wait_idle();const auto stats=renderer.stats();need(stats.debug_layer&&stats.debug_errors==0&&stats.debug_warnings==0,"Actual DX12 debug layer reports zero errors/warnings");
 std::ofstream report(out/L"result.json");report<<"{\"status\":\"passed\",\"checks\":"<<checks<<",\"outside_scene_pixels_verified\":"<<outside<<",\"upload_allocations\":"<<owned_hud::upload_allocations.load()<<",\"rasterizations\":"<<owned_hud::rasterizations.load()<<",\"presents\":"<<stats.frames<<",\"debug_errors\":"<<stats.debug_errors<<",\"debug_warnings\":"<<stats.debug_warnings<<"}";
 std::cout<<checks<<" checks passed\n";return 0;
 }catch(const std::exception& error){std::cerr<<"FAIL after "<<checks<<": "<<error.what()<<'\n';return 1;}}
