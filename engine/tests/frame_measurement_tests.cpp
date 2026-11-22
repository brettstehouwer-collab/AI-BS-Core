#include <aibs/frame_measurement.hpp>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {
int checks=0;
void check(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
template<class F>void rejects(F action,const char* message){bool failed=false;try{action();}catch(const std::invalid_argument&){failed=true;}check(failed,message);}
using Clock=FrameMeasurement::Clock;
const auto epoch=Clock::time_point{};
Clock::time_point seconds(double n){return epoch+std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(n));}
FrameObservation observation(std::uint64_t frames){return {frames,1920,1080,true,true,1000,2000,2500,3000};}
}
int main(){try{
 FrameMeasurementConfig config;FrameMeasurement measured(config,epoch,observation(0));
 check(measured.state()==FrameMeasurementState::warmup,"New capture did not warm up");
 check(!measured.summary(),"Warmup produced fake measured statistics");
 measured.observe(seconds(2),observation(1));check(measured.state()==FrameMeasurementState::measuring,"Actual warmup boundary did not start sample window");
 for(std::uint64_t i=1;i<=15;++i){auto o=observation(i+1);if(i==5)o.private_bytes=5000;measured.observe(seconds(2+static_cast<double>(i)),o);}
 check(measured.state()==FrameMeasurementState::complete,"Fifteen actual wall seconds did not complete");
 const auto result=measured.summary();check(result.has_value(),"Completed capture lost statistics");
 check(result->frame_count==15&&result->presented_frame_delta==15,"Measured frame count differs from actual present counter");
 check(result->wall_seconds==15&&result->mean_ms==1000&&result->p50_ms==1000&&result->p95_ms==1000&&result->p99_ms==1000,"Clock-derived statistics wrong");
 check(result->frames_per_second==1,"FPS must use measured wall duration");
 check(result->private_start==1000&&result->private_end==1000&&result->private_peak_sampled==5000,"Private commit sampling wrong");
 check(result->working_set_peak_sampled==2000&&result->working_set_peak_lifetime==2500,"Working set peak semantics wrong");
 check(result->gpu_content_peak_sampled==3000&&result->width==1920&&result->height==1080,"Actual client/GPU content observation wrong");
 check(result->instrumentation_bytes>=2*config.maximum_samples*sizeof(double),"Owned bounded sample buffers were not charged");
 measured.observe(seconds(100),observation(100));check(measured.summary()->frame_count==15,"Completion kept collecting unbounded frames");
 FrameMeasurement sixty(config,epoch,observation(0));sixty.observe(seconds(2),observation(1));
 const auto step=std::chrono::nanoseconds(16666667);
 for(std::uint64_t i=1;i<=900;++i)sixty.observe(seconds(2)+step*i,observation(i+1));
 const auto fps=sixty.summary();check(fps&&fps->frame_count==900&&fps->wall_seconds>=15,"Real sixty-Hz interval test did not use >=15secs");
 check(std::abs(fps->frames_per_second-60)<.001&&std::abs(fps->p99_ms-16.666667)<.0001,"Submillisecond percentile precision lost");
 for(const double duration:{14.9,120.1,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}){auto c=config;c.measure_seconds=duration;rejects([&]{FrameMeasurement x(c,epoch,observation(0));},"Invalid duration accepted");}
 for(const double warmup:{1.9,30.1,std::numeric_limits<double>::infinity()}){auto c=config;c.warmup_seconds=warmup;rejects([&]{FrameMeasurement x(c,epoch,observation(0));},"Invalid warmup accepted");}
 for(const auto capacity:{std::size_t{0},std::size_t{120001}}){auto c=config;c.maximum_samples=capacity;rejects([&]{FrameMeasurement x(c,epoch,observation(0));},"Unbounded/empty sample capacity accepted");}
 auto invalid=config;invalid.width=0;rejects([&]{FrameMeasurement x(invalid,epoch,observation(0));},"Zero client width accepted");
 invalid=config;invalid.height=4321;rejects([&]{FrameMeasurement x(invalid,epoch,observation(0));},"Unsupported client height accepted");
 auto dimensions=observation(0);dimensions.width=1280;rejects([&]{FrameMeasurement x(config,epoch,dimensions);},"Requested dimensions substituted for actual client dimensions");
 FrameMeasurement stalled(config,epoch,observation(0));stalled.observe(epoch,observation(1));check(stalled.error()==FrameMeasurementError::clock_not_advanced&&!stalled.summary(),"Nonadvancing clock generated fake FPS");
 FrameMeasurement skipped(config,epoch,observation(0));skipped.observe(seconds(1),observation(2));check(skipped.error()==FrameMeasurementError::present_counter_mismatch&&!skipped.summary(),"Skipped present counter silently counted a frame");
 FrameMeasurement resized(config,epoch,observation(0));auto change=observation(1);change.height=720;resized.observe(seconds(1),change);check(resized.error()==FrameMeasurementError::client_dimensions_changed,"Resize did not invalidate fixed-resolution capture");
 FrameMeasurement inactive(config,epoch,observation(0));change=observation(1);change.active=false;inactive.observe(seconds(1),change);check(inactive.error()==FrameMeasurementError::inactive,"Paused/minimized/focus-lost frames were claimed as game performance");
 FrameMeasurement unavailable(config,epoch,observation(0));change=observation(1);change.memory_valid=false;unavailable.observe(seconds(1),change);check(unavailable.error()==FrameMeasurementError::memory_unavailable,"Failed memory query silently became zero usage");
 auto tiny_config=config;tiny_config.maximum_samples=2;FrameMeasurement tiny(tiny_config,epoch,observation(0));tiny.observe(seconds(2),observation(1));tiny.observe(seconds(3),observation(2));tiny.observe(seconds(4),observation(3));tiny.observe(seconds(5),observation(4));check(tiny.error()==FrameMeasurementError::sample_capacity&&!tiny.summary(),"Sample overflow published truncated statistics");
 check(frame_measurement_error_name(FrameMeasurementError::sample_capacity)==std::string("sample_capacity"),"Bounded diagnostic reason missing");
 check(!measured.finish_gameplay(),"Stationary completion was relabelled gameplay");
 check(result->frames_over_16_67ms==15&&result->frames_over_33_33ms==15&&result->frames_over_50ms==15,"Long-frame counters omitted actual measured intervals");
 check(fps->frames_over_16_67ms==0&&fps->frames_over_33_33ms==0&&fps->frames_over_50ms==0,"Sixty-Hz frames falsely counted as long");
 auto game_config=config;game_config.profile=FrameMeasurementProfile::gameplay;game_config.measure_seconds=900;game_config.maximum_samples=480000;
 FrameMeasurement game(game_config,epoch,observation(0));check(!game.finish_gameplay()&&!game.summary(),"Gameplay warmup was accepted as a session");
 game.observe(seconds(2),observation(1));
 for(std::uint64_t i=1;i<=14;++i)game.observe(seconds(2+static_cast<double>(i)),observation(i+1));
 check(!game.finish_gameplay()&&!game.summary(),"Short gameplay session was accepted");
 game.observe(seconds(17),observation(16));check(game.finish_gameplay(),"Normal gameplay finish rejected valid Present endpoints");
 const auto finished=game.summary();check(finished&&finished->wall_seconds==15&&finished->frame_count==15&&finished->presented_frame_delta==15,"Gameplay finish fabricated duration or frame count");
 check(game.finish_gameplay()&&game.summary()->frame_count==15,"Repeated finish changed measured history");
 FrameMeasurement failed_game(game_config,epoch,observation(0));failed_game.observe(epoch,observation(1));
 check(!failed_game.finish_gameplay()&&!failed_game.summary(),"Failed gameplay was promoted by normal close");
 auto long_config=game_config;long_config.maximum_samples=8;FrameMeasurement long_game(long_config,epoch,observation(0));long_game.observe(seconds(2),observation(1));long_game.observe(seconds(901),observation(2));
 check(long_game.state()==FrameMeasurementState::measuring,"Gameplay completed before its900second limit");long_game.observe(seconds(902),observation(3));
 check(long_game.summary()&&long_game.summary()->wall_seconds==900,"Gameplay finite maximum did not terminate");
 for(auto bad:{901.,std::numeric_limits<double>::quiet_NaN()}){auto c=game_config;c.measure_seconds=bad;rejects([&]{FrameMeasurement x(c,epoch,observation(0));},"Invalid gameplay duration accepted");}
 auto bad_game=game_config;bad_game.maximum_samples=480001;rejects([&]{FrameMeasurement x(bad_game,epoch,observation(0));},"Unbounded gameplay sample storage accepted");
 bad_game=config;bad_game.profile=static_cast<FrameMeasurementProfile>(2);rejects([&]{FrameMeasurement x(bad_game,epoch,observation(0));},"Unknown measurement profile accepted");
 std::cout<<checks<<" bounded wall-clock measurement checks passed (synthetic algorithm fixtures; not a hardware benchmark)\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
