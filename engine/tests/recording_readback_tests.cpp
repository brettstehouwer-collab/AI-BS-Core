#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/render.hpp>
#include "video_encoder.hpp"
#include "report_helper.hpp"
#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <thread>
#include <type_traits>
using namespace aibs;using Clock=std::chrono::steady_clock;
static_assert(CapturedFrame::maximum_bytes==32u*1024u*1024u);
static_assert(std::is_same_v<decltype(std::declval<Dx12Renderer&>().capture_frame(std::declval<CapturedFrame&>())),bool>);
unsigned checks=0;void require(bool value,const char* text){++checks;if(!value)throw std::runtime_error(text);}
WNDPROC native_proc=nullptr;
LRESULT CALLBACK unrestricted_test_size(HWND window,UINT message,WPARAM w,LPARAM l){
 const auto result=CallWindowProcW(native_proc,window,message,w,l);
 if(message==WM_GETMINMAXINFO){auto* limits=reinterpret_cast<MINMAXINFO*>(l);limits->ptMaxTrackSize={9000,9000};}
 return result;
}
LRESULT CALLBACK cover_proc(HWND window,UINT message,WPARAM w,LPARAM l){if(message==WM_PAINT){PAINTSTRUCT p{};auto dc=BeginPaint(window,&p);RECT rect{};GetClientRect(window,&rect);auto brush=CreateSolidBrush(RGB(255,0,255));FillRect(dc,&rect,brush);DeleteObject(brush);EndPaint(window,&p);return 0;}return DefWindowProcW(window,message,w,l);}
int wmain(int argc,wchar_t** argv){try{
 require(argc==4||argc==5,"Expected shaders, ffmpeg, output directory and optional encoder mode");const std::filesystem::path shaders=argv[1],ff=argv[2],out=argv[3];const auto mode=argc==5&&std::wstring(argv[4])==L"nvenc"?recording::EncoderMode::h264_nvenc:recording::EncoderMode::software;std::filesystem::create_directories(out);
 NativeWindow window(513,257,L"AI-BS bounded OWN renderer recording test",true);window.poll();native_proc=reinterpret_cast<WNDPROC>(SetWindowLongPtrW(static_cast<HWND>(window.native_handle()),GWLP_WNDPROC,reinterpret_cast<LONG_PTR>(unrestricted_test_size)));require(native_proc!=nullptr,"Test-only max-track override permits real 1080p/oversize dimensions");Dx12Renderer renderer(window,make_motherboard_scene(),shaders);Camera camera;
 CapturedFrame frame;frame.width=99;frame.present_id=123;frame.bgra={std::byte{8}};
 require(!renderer.capture_frame(frame)&&frame.width==99&&frame.present_id==123&&frame.bgra.size()==1,"No present preserves output");
 renderer.render(camera);require(renderer.capture_frame(frame),"Actual GPU capture available");require(frame.width==513&&frame.height==257,"Odd-width footprint compacted correctly");require(frame.bgra.size()==513u*257u*4&&frame.bgra.capacity()==CapturedFrame::maximum_bytes,"Producer slot exact bound");require(frame.present_id==renderer.stats().frames&&frame.nonbackground_pixels>1000,"Actual present identity and visible pixels");
 const auto* pointer=frame.bgra.data();{const auto first=frame.bgra;
 const auto pixels=renderer.capture(out/L"legacy-one.bmp");require(pixels==frame.nonbackground_pixels,"Legacy and owned pixel counts match");
 std::ifstream file(out/L"legacy-one.bmp",std::ios::binary|std::ios::ate);std::vector<char> bmp(static_cast<std::size_t>(file.tellg()));file.seekg(0);file.read(bmp.data(),static_cast<std::streamsize>(bmp.size()));require(bmp.size()==54+frame.bgra.size(),"BMP expected payload size");require(std::memcmp(bmp.data()+54,frame.bgra.data(),frame.bgra.size())==0,"Owned BGRA is byte-identical to existing BMP capture");
 WNDCLASSW type{};type.lpfnWndProc=cover_proc;type.hInstance=GetModuleHandleW(nullptr);type.lpszClassName=L"AIBS.Recorder.CoverProof";require(RegisterClassW(&type)!=0,"Cover test class");RECT rect{};GetWindowRect(static_cast<HWND>(window.native_handle()),&rect);
 const auto cover=CreateWindowExW(WS_EX_TOPMOST,type.lpszClassName,L"NOT THE GAME - magenta occlusion proof",WS_POPUP|WS_VISIBLE,rect.left,rect.top,rect.right-rect.left,rect.bottom-rect.top,nullptr,nullptr,type.hInstance,nullptr);require(cover!=nullptr,"Separate covering window created");UpdateWindow(cover);window.poll();require(renderer.capture_frame(frame),"GPU target captured while physically covered");require(frame.bgra==first,"Cover pixels never enter own-target capture");DestroyWindow(cover);window.poll();}
 for(unsigned n=0;n<8;++n){renderer.render(camera);require(renderer.capture_frame(frame),"Repeated captures available");require(frame.bgra.data()==pointer,"Producer allocation reused");}
 require(renderer.stats().capture_buffer_allocations==1&&renderer.stats().capture_active_readback_bytes==CapturedFrame::maximum_bytes,"One bounded GPU readback slot reused");
 window.set_size(640,360);window.poll();require(!renderer.capture_frame(frame),"Pending resize cannot return stale old frame");renderer.resize(640,360);require(!renderer.capture_frame(frame),"Resize invalidates old present");renderer.render(camera);require(renderer.capture_frame(frame)&&frame.width==640&&frame.height==360,"Resized capture renders new size");require(frame.bgra.data()==pointer&&renderer.stats().capture_buffer_allocations==1,"Resize reuses owned slots");
 window.minimize();window.poll();const auto present=frame.present_id;require(!renderer.capture_frame(frame)&&frame.present_id==present,"Minimize preserves last output and rejects capture");const auto count=renderer.stats().frames;renderer.render(camera);require(renderer.stats().frames==count,"No minimized present fabricated");window.restore();window.poll();renderer.render(camera);require(renderer.capture_frame(frame),"Restore resumes capture");
 window.set_size(4096,2160);window.poll();renderer.render(camera);bool oversized=false;try{renderer.capture_frame(frame);}catch(const std::invalid_argument&){oversized=true;}require(oversized,"Oversize capture rejects before any readback publication");require(renderer.stats().capture_buffer_allocations==1,"Oversize rejected without extra allocation");
 window.set_size(1920,1080);window.poll();renderer.render(camera);require(renderer.capture_frame(frame)&&frame.width==1920&&frame.height==1080,"1080p actual native capture");
 recording::VideoEncoder encoder;require(encoder.begin(ff,out/L"own-window-1080p.mp4",frame.width,frame.height,30,mode),"Actual window encoder starts");
 const auto started=Clock::now();auto next=started;bool paused=false;double maximum_capture=0,total_capture=0;std::uint64_t captured=0;
 while(Clock::now()-started<std::chrono::milliseconds(4200)){
  window.poll();const auto elapsed=std::chrono::duration<double>(Clock::now()-started).count();camera.yaw=-.67f+static_cast<float>(elapsed)*.045f;renderer.render(camera);
  if(Clock::now()>=next){const auto before=Clock::now();require(renderer.capture_frame(frame),"Video frame GPU readback");const auto capture_seconds=std::chrono::duration<double>(Clock::now()-before).count();total_capture+=capture_seconds;maximum_capture=std::max(maximum_capture,capture_seconds);++captured;encoder.submit(frame,Clock::now());require(encoder.active(),encoder.report().error.c_str());next+=std::chrono::microseconds(33333);if(next<Clock::now()-std::chrono::milliseconds(34))next=Clock::now();}
  if(!paused&&elapsed>1.6){std::this_thread::sleep_for(std::chrono::milliseconds(220));paused=true;}
 }
 require(encoder.finish(),encoder.report().error.c_str());require(encoder.report().frames_written>45,"Multiple actual animated camera frames encoded");require(encoder.report().missed_capture_slots>=5,"Capture pause explicitly accounted");require(encoder.report().encoder_frame_capacity+frame.bgra.capacity()<=2*CapturedFrame::maximum_bytes,"Complete two-frame CPU pool bounded");
 renderer.wait_idle();const auto stats=renderer.stats();require(stats.debug_errors==0&&stats.debug_warnings==0,"No GPU validation errors or warnings");require(stats.capture_buffer_allocations==1,"Whole proof uses one readback allocation");write_recording_report(out/L"own-window.json",encoder.report());
 std::ofstream report(out/L"readback.json");report<<std::setprecision(17)<<"{\"status\":\"passed\",\"checks\":"<<checks<<",\"legacy_byte_identical\":true,\"covered_window_identical\":true,\"resize_minimize_restore\":true,\"frames_captured_for_video\":"<<captured<<",\"total_capture_seconds\":"<<total_capture<<",\"mean_capture_seconds\":"<<total_capture/static_cast<double>(captured)<<",\"maximum_capture_seconds\":"<<maximum_capture<<",\"readback_allocations\":"<<stats.capture_buffer_allocations<<",\"gpu_readback_bytes\":"<<stats.capture_active_readback_bytes<<",\"producer_capacity\":"<<frame.bgra.capacity()<<",\"encoder_capacity\":"<<encoder.report().encoder_frame_capacity<<",\"debug_errors\":"<<stats.debug_errors<<",\"debug_warnings\":"<<stats.debug_warnings<<",\"frames_rendered\":"<<stats.frames<<"}";
 std::cout<<checks<<" checks passed\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}

