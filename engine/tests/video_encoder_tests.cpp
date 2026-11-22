#include "video_encoder.hpp"
#include "report_helper.hpp"
#include <iostream>
#include <thread>
#include <fstream>
using namespace aibs;using namespace aibs::recording;using Clock=std::chrono::steady_clock;
unsigned checks=0;void require(bool value,const char* text){++checks;if(!value)throw std::runtime_error(text);}
CapturedFrame frame(unsigned w,unsigned h){CapturedFrame f;f.width=w;f.height=h;f.present_id=1;f.bgra.resize(static_cast<std::size_t>(w)*h*4);for(std::size_t i=0;i<f.bgra.size();i+=4){f.bgra[i]=std::byte{70};f.bgra[i+1]=std::byte{90};f.bgra[i+2]=std::byte{180};f.bgra[i+3]=std::byte{255};}return f;}
int wmain(int argc,wchar_t** argv){try{
 require(argc==4,"Expected ffmpeg, mock ffmpeg, output directory");const std::filesystem::path ff=argv[1],mock=argv[2],out=argv[3];std::filesystem::create_directories(out);
 {VideoEncoder r;require(!r.active(),"New recorder is inactive");require(r.finish(),"Unstarted stop");require(r.finish(),"Stop is idempotent");}
 for(const auto dims:{std::pair{0u,72u},std::pair{127u,72u},std::pair{8192u,8192u},std::pair{0x80000000u,0x80000000u}}){VideoEncoder r;require(!r.begin(ff,out/L"invalid.mp4",dims.first,dims.second),"Bad dimensions reject");require(!r.active(),"Bad begin has no child");}
 {std::ofstream f(out/L"keep.mp4");f<<"KEEP";f.close();VideoEncoder r;require(!r.begin(ff,out/L"keep.mp4",128,72),"Existing output rejects");std::ifstream in(out/L"keep.mp4");std::string text;in>>text;require(text=="KEEP","Existing bytes unchanged");}
 {VideoEncoder r;require(!r.begin(ff,L"relative.mp4",128,72),"Relative path rejects");}
 {VideoEncoder r;require(!r.begin(ff,out/L"bad-rate.mp4",128,72,61),"Excess rate rejects");}
 {VideoEncoder r;require(!r.begin(ff.parent_path()/L"missing.exe",out/L"bad-exe.mp4",128,72),"Unknown executable rejects");}
 {VideoEncoder r;require(!r.begin(mock,out/L"explicit-hardware.mp4",128,72,30,EncoderMode::h264_nvenc),"Explicit unavailable hardware rejects");require(r.report().hardware_probe_attempted&&!r.report().hardware_probe_passed,"Hardware rejection is based on actual child exit");}
 {VideoEncoder r;require(r.begin(mock,out/L"auto-fallback.mp4",128,72,30,EncoderMode::automatic),"Auto selection permits software fallback");require(r.report().encoder=="libx264"&&!r.report().fallback_reason.empty(),"Software fallback explicitly reported");require(!r.finish(std::chrono::milliseconds(20)),"Mock fallback stops boundedly");}
 auto f=frame(128,72);
 {VideoEncoder r;require(r.begin(ff,out/L"synthetic space & apostrophe's.mp4",128,72),"Trusted ffmpeg starts");VideoEncoder second;require(!second.begin(ff,out/L"concurrent.mp4",128,72),"Single recording bounds pool");
  require(r.submit(f,Clock::now()),"First frame delivered");const auto capacity=r.report().encoder_frame_capacity;
  require(!r.submit(f,Clock::now())&&r.active(),"Rate/duplicate drop preserves recorder");
  for(unsigned n=2;n<=35;++n){std::this_thread::sleep_for(std::chrono::milliseconds(n==9||n==23?220:35));f.present_id=n;f.bgra[0]=static_cast<std::byte>(n*3);require(r.submit(f,Clock::now()),"Synthetic frame delivered");require(r.report().encoder_frame_capacity==capacity,"Encoder slot reused");}
  std::this_thread::sleep_for(std::chrono::milliseconds(120));require(r.finish(),r.report().error.c_str());require(!r.active()&&r.report().finished&&!r.report().failed,"Stopped child drained");
  require(r.report().encoder_frame_capacity<=CapturedFrame::maximum_bytes,"Encoder slot bounded");require(r.report().encoder_frame_capacity+r.report().producer_frame_capacity_peak<=2*CapturedFrame::maximum_bytes,"Two frame pool bounded");
  require(r.report().missed_capture_slots>=8&&r.report().dropped_for_rate==1,"Honest rate and missed slots");require(r.report().repeated_at_stop==1,"Stop holds image until stop time");require(r.finish(),"Successful stop repeats safely");require(r.report().encoder_frame_capacity_active==0,"Finished recorder releases full pixel slot while report remains inspectable");write_recording_report(out/L"synthetic.json",r.report());}
 {VideoEncoder r;require(r.begin(ff,out/L"malformed.mp4",128,72),"Malformed fixture child starts");auto bad=f;bad.width=126;require(!r.submit(bad,Clock::now())&&!r.active(),"Changed size stops recording only");require(!r.finish(),"Malformed record reports failure");require(!r.report().quarantined,"Ordinary error joins I/O");}
 {VideoEncoder r;require(r.begin(ff,out/L"stale.mp4",128,72),"Stale fixture starts");require(!r.submit(f,Clock::now()-std::chrono::seconds(2)),"Stale timestamp rejects");require(!r.finish(),"Stale error joins child");}
 {VideoEncoder r;require(r.begin(mock,out/L"stall.mp4",1920,1080),"Mock stalled child starts");const auto big=frame(1920,1080);const auto start=Clock::now();require(!r.submit(big,Clock::now()),"No-read child hits backpressure deadline");require(std::chrono::duration<double>(Clock::now()-start).count()<1.0,"Backpressure cannot block game forever");require(r.report().backpressure_events==1&&!r.active(),"Backpressure is fatal to recorder only");require(!r.finish(),"Failed recorder stop is honest");require(!r.report().quarantined,"Cancellation completed normally");write_recording_report(out/L"stall.json",r.report());}
 {VideoEncoder r;require(r.begin(mock,out/L"early-exit.mp4",128,72),"Early exit child starts");std::this_thread::sleep_for(std::chrono::milliseconds(50));require(!r.submit(f,Clock::now()),"Dead child rejected without blocking");require(!r.finish(),"Dead child reports failure");}
 {VideoEncoder r;require(r.begin(mock,out/L"stop-deadline.mp4",128,72),"Stop deadline child starts");const auto start=Clock::now();require(!r.finish(std::chrono::milliseconds(20)),"Nonexiting child reports stop failure");require(std::chrono::duration<double>(Clock::now()-start).count()<.5,"Stop deadline bounded");}
 std::ofstream report(out/L"checks.json");report<<"{\"status\":\"passed\",\"checks\":"<<checks<<"}";std::cout<<checks<<" checks passed\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}

