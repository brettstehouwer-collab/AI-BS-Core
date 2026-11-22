#include <aibs/audio_playback.hpp>
#include "audio_device.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <span>
#include <stdexcept>
#include <thread>
#include <type_traits>
using namespace aibs;
namespace {
unsigned checks=0;
void check(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
AudioAsset asset(unsigned rate=44100,unsigned channels=2,std::uint64_t frames=44100){
 AudioAsset a;a.asset_id="a1b2c3d4-1234-4234-8234-123456789abc";a.name="Synthetic PCM fixture";a.source_sha256=std::string(64,'a');
 a.sample_rate=rate;a.channels=channels;a.frame_count=frames;a.pcm.resize(static_cast<std::size_t>(frames)*channels*2);
 for(std::size_t i=0;i<a.pcm.size();++i)a.pcm[i]=std::byte(i%251);return a;
}
struct Control {
 bool fail_create=false,fail_start=false,fail_pause=false,fail_resume=false,fail_volume=false;
 std::int32_t critical_error=0;
 std::uint64_t frames=0;std::uint32_t queued=1,rate=0,channels=0;
 unsigned creates=0,destroys=0,starts=0,pauses=0,resumes=0,volume_sets=0;
 std::span<const std::byte> submitted;
 std::vector<std::byte> expected;
 bool destruction_saw_valid_pcm=true;
 float volume=1;
};
struct FakeDevice final:detail::AudioDevice {
 Control& c;std::span<const std::byte> pcm;
 FakeDevice(Control& control,std::span<const std::byte> bytes):c(control),pcm(bytes){}
 ~FakeDevice()override{++c.destroys;if(c.expected.size()!=pcm.size()||!std::equal(c.expected.begin(),c.expected.end(),pcm.begin()))c.destruction_saw_valid_pcm=false;}
 AudioPlaybackResult start()noexcept override{++c.starts;return c.fail_start?AudioPlaybackResult{AudioPlaybackError::backend_failure,-2}:AudioPlaybackResult{};}
 AudioPlaybackResult pause()noexcept override{++c.pauses;return c.fail_pause?AudioPlaybackResult{AudioPlaybackError::backend_failure,-3}:AudioPlaybackResult{};}
 AudioPlaybackResult resume()noexcept override{++c.resumes;return c.fail_resume?AudioPlaybackResult{AudioPlaybackError::backend_failure,-4}:AudioPlaybackResult{};}
 AudioPlaybackResult set_volume(float volume)noexcept override{++c.volume_sets;if(c.fail_volume)return {AudioPlaybackError::backend_failure,-5};c.volume=volume;return {};}
 detail::AudioDeviceState state()noexcept override{return {c.frames,c.queued,c.critical_error};}
};
std::unique_ptr<detail::AudioDevice> create(void* context,unsigned rate,unsigned channels,
 std::span<const std::byte> pcm,float volume,AudioPlaybackResult& result)noexcept {
 auto& c=*static_cast<Control*>(context);++c.creates;c.rate=rate;c.channels=channels;c.volume=volume;c.submitted=pcm;
 if(c.fail_create){result={AudioPlaybackError::device_unavailable,-1};return {};}
 try{return std::make_unique<FakeDevice>(c,pcm);}catch(...){result={AudioPlaybackError::out_of_memory,0};return {};}
}
void no_device_contracts(){
 AudioPlayback player;auto s=player.snapshot();check(s.state==AudioPlaybackState::stopped&&!s.source_voice,"Construction is hardware-free stopped state");
 check(s.position_seconds()==0&&s.duration_seconds()==0&&s.owned_pcm_bytes==0,"Empty caption clock is defined");
 check(player.pause().error==AudioPlaybackError::invalid_state,"Cannot pause empty player");
 check(player.resume().error==AudioPlaybackError::invalid_state,"Cannot resume empty player");
 for(float volume:{-1.f,1.1f,std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity()})check(player.set_volume(volume).error==AudioPlaybackError::invalid_volume,"Volume must be finite unit interval");
 check(static_cast<bool>(player.set_volume(.3f))&&player.snapshot().volume==.3f,"Idle volume is retained");
 check(static_cast<bool>(player.stop())&&static_cast<bool>(player.stop()),"Stop idempotent");
 check(static_cast<bool>(player.close())&&static_cast<bool>(player.close()),"Close idempotent");
 check(player.snapshot().state==AudioPlaybackState::closed,"Close is terminal");
 auto a=asset();check(player.play(a).error==AudioPlaybackError::closed,"Closed player cannot reopen device");
}
void fake_contracts(){
 Control c;auto player=detail::AudioPlaybackTestAccess::make(create,&c);auto a=asset();c.expected=a.pcm;
 check(static_cast<bool>(player->play(a,.2f)),"Play staged PCM");auto s=player->snapshot();
 check(c.rate==44100&&c.channels==2&&c.volume==.2f,"Original 44.1k stereo sent unchanged");
 check(c.submitted.data()!=a.pcm.data()&&std::equal(a.pcm.begin(),a.pcm.end(),c.submitted.begin()),"Device receives complete independent PCM copy");
 a.pcm.clear();a.pcm.shrink_to_fit();check(std::equal(c.expected.begin(),c.expected.end(),c.submitted.begin()),"Caller PCM can be destroyed");
 check(s.source_voice&&s.state==AudioPlaybackState::playing&&s.owned_pcm_bytes>=c.expected.size()&&s.generation==1,"Playing owns charged PCM and generation");
 c.frames=22050;s=player->snapshot();check(s.played_frames==22050&&s.position_seconds()==.5&&s.duration_seconds()==1,"Caption clock uses source sample frames");
 check(static_cast<bool>(player->pause())&&player->snapshot().state==AudioPlaybackState::paused,"Pause state");
 c.frames=23000;check(player->snapshot().played_frames==22050,"Paused caption clock cannot advance");
 check(static_cast<bool>(player->pause()),"Repeated pause succeeds without consuming PCM");
 check(static_cast<bool>(player->resume()),"Resume from pause");check(player->snapshot().played_frames==23000,"Resumed native frame clock advances");
 check(static_cast<bool>(player->set_volume(0))&&c.volume==0,"Only source volume changed");
 auto malformed=asset();malformed.frame_count++;
 const auto before=player->snapshot();check(player->play(malformed).error==AudioPlaybackError::invalid_asset,"Bad frame/PCM correspondence rejected");
 check(player->snapshot().generation==before.generation&&c.destroys==0,"Bad asset preserves active voice");
 malformed=asset();const auto create_count=c.creates;check(player->play(malformed,2).error==AudioPlaybackError::invalid_volume&&c.creates==create_count,"Bad replacement volume rejected before device staging");
 c.fail_create=true;check(player->play(malformed).error==AudioPlaybackError::device_unavailable,"Missing default device returns bounded result");
 check(player->snapshot().state==AudioPlaybackState::playing&&c.destroys==0,"Device-creation failure retains old active clip");c.fail_create=false;
 c.fail_start=true;check(player->play(malformed).error==AudioPlaybackError::backend_failure,"Start failure is bounded");c.fail_start=false;
 check(player->snapshot().generation==before.generation&&c.resumes>=2,"Failed replacement resumes previous playing device");
 check(static_cast<bool>(player->play(malformed)),"Successful replacement");
 check(player->snapshot().generation==2&&player->snapshot().peak_owned_pcm_bytes>=2*c.expected.size(),"Replacement peak charges both PCM copies");
 check(c.destruction_saw_valid_pcm,"Replacement releases voice before PCM memory");
 c.frames=44100;c.queued=0;s=player->snapshot();check(s.state==AudioPlaybackState::completed&&s.played_frames==44100&&s.position_seconds()==1,"EOS retains final caption position even if backend resets counters");
 check(!s.source_voice&&s.owned_pcm_bytes==0,"EOS releases device and PCM");
 c.frames=0;c.queued=1;check(static_cast<bool>(player->play(malformed)),"New explicit Play after completion");
 c.critical_error=-123;s=player->snapshot();check(s.state==AudioPlaybackState::failed&&s.error==AudioPlaybackError::backend_failure&&s.native_code==-123,"Critical callback error becomes bounded failure");
 check(!s.source_voice&&s.owned_pcm_bytes==0,"Critical device error drains before PCM release");c.critical_error=0;
 check(static_cast<bool>(player->stop())&&player->snapshot().played_frames==0,"Explicit stop resets caption position");
 check(c.destruction_saw_valid_pcm,"Every fake device destruction read valid retained PCM");
}
void format_and_thread_contracts(){
 for(const auto [rate,channels]:{std::pair{8000u,1u},std::pair{192000u,2u},std::pair{48000u,1u}}){
  Control c;auto player=detail::AudioPlaybackTestAccess::make(create,&c);auto a=asset(rate,channels,rate);c.expected=a.pcm;
  check(static_cast<bool>(player->play(a))&&c.rate==rate&&c.channels==channels,"Playback preserves every supported source format");
  check(static_cast<bool>(player->close())&&c.destruction_saw_valid_pcm,"Close drains while PCM remains valid");
 }
 Control c;auto player=detail::AudioPlaybackTestAccess::make(create,&c);auto a=asset();c.expected=a.pcm;
 check(static_cast<bool>(player->play(a)),"Thread contract fixture plays");
 AudioPlaybackResult result;AudioPlaybackSnapshot snapshot;
 std::thread other([&]{result=player->stop();snapshot=player->snapshot();});other.join();
 check(result.error==AudioPlaybackError::wrong_thread&&snapshot.error==AudioPlaybackError::wrong_thread,"Wrong-thread operations return without touching owner resources");
 check(player->snapshot().source_voice&&c.destroys==0,"Foreign stop never releases owner audio");
 player.reset();check(c.destruction_saw_valid_pcm&&c.destroys==1,"Destructor closes voice before owned copy");
}
void failed_controls_preserve_state(){
 Control c;auto player=detail::AudioPlaybackTestAccess::make(create,&c);auto a=asset();c.expected=a.pcm;
 check(static_cast<bool>(player->play(a,.5f)),"Control failure fixture plays");
 c.fail_volume=true;check(player->set_volume(.1f).error==AudioPlaybackError::backend_failure&&player->snapshot().volume==.5f,"Failed volume change retains old source volume");c.fail_volume=false;
 c.fail_pause=true;check(player->pause().error==AudioPlaybackError::backend_failure&&player->snapshot().state==AudioPlaybackState::playing,"Failed pause retains playing intent");
 const auto before=player->snapshot();check(player->play(a).error==AudioPlaybackError::backend_failure&&player->snapshot().generation==before.generation,"Failed previous-device pause aborts replacement");c.fail_pause=false;
 check(static_cast<bool>(player->pause()),"Successful pause after failure");
 c.fail_resume=true;check(player->resume().error==AudioPlaybackError::backend_failure&&player->snapshot().state==AudioPlaybackState::paused,"Failed resume retains paused intent");c.fail_resume=false;
 c.fail_start=true;check(player->play(a).error==AudioPlaybackError::backend_failure&&player->snapshot().state==AudioPlaybackState::paused,"Failed replacement preserves previous paused clip");c.fail_start=false;
 check(static_cast<bool>(player->resume()),"Resume remains possible after rejected replacement");
 c.fail_start=true;c.fail_resume=true;check(player->play(a).error==AudioPlaybackError::backend_failure&&player->snapshot().state==AudioPlaybackState::failed,"Failed restoration reports failed state");
 check(!player->snapshot().source_voice&&player->snapshot().owned_pcm_bytes==0,"Unrecoverable control error drains voice before release");
 check(c.destruction_saw_valid_pcm,"Every failed control/replacement retains PCM through device destruction");
}
}
int main(){try{
 static_assert(!std::is_copy_constructible_v<AudioPlayback> && !std::is_move_constructible_v<AudioPlayback>);
 no_device_contracts();fake_contracts();format_and_thread_contracts();failed_controls_preserve_state();std::cout<<checks<<" audio playback contract checks passed\n";return 0;
}catch(const std::exception& error){std::cerr<<"Audio playback contract failure: "<<error.what()<<'\n';return 1;}}
