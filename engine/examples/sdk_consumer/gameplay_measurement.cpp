#include <aibs/frame_measurement.hpp>
#include <chrono>
#include <iostream>
#include <stdexcept>
namespace {int checks=0;void check(bool v,const char* why){++checks;if(!v)throw std::runtime_error(why);}}
int main(){try{
 using namespace aibs;
 FrameMeasurementConfig config{1920,1080,2,900,64,FrameMeasurementProfile::gameplay};
 FrameObservation view{0,1920,1080,true,true,1000,2000,2500,3000};
 FrameMeasurement sampled(config,{},view);
 check(!sampled.finish_gameplay()&&!sampled.summary(),"Installed SDK accepted warmup as gameplay");
 for(unsigned i=1;i<=17;++i){view.presented_frames=i;sampled.observe(FrameMeasurement::Clock::time_point{}+std::chrono::seconds(i),view);}
 check(sampled.finish_gameplay(),"Installed gameplay finish entry point failed");
 const auto summary=sampled.summary();check(summary.has_value(),"Installed SDK lost completed session");
 check(summary->frame_count==15&&summary->presented_frame_delta==15,"Installed ABI lost actual Present accounting");
 check(summary->wall_seconds==15&&summary->frames_per_second==1,"Installed timing ABI is inconsistent");
 check(summary->frames_over_50ms==15&&summary->frames_over_33_33ms==15&&summary->frames_over_16_67ms==15,"Installed summary omitted long-frame counters");
 FrameMeasurementConfig legacy{1920,1080,2,15,64};
 view.presented_frames=0;FrameMeasurement stationary(legacy,{},view);
 check(!stationary.finish_gameplay(),"Legacy aggregate constructor silently enabled gameplay");
 for(unsigned i=1;i<=17;++i){view.presented_frames=i;stationary.observe(FrameMeasurement::Clock::time_point{}+std::chrono::seconds(i),view);}
 check(stationary.summary()&&stationary.summary()->frame_count==15,"Legacy installed capture changed");
 std::cout<<checks<<" installed SDK gameplay ABI and legacy compatibility checks passed; algorithm fixtures, not hardware FPS\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
