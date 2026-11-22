#include <aibs/audio_playback.hpp>
#include "audio_device.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <thread>
using namespace aibs;
using Clock=std::chrono::steady_clock;
namespace {
unsigned checks=0;
void check(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
void require(AudioPlaybackResult result,const char* message){
 ++checks;if(!result)throw std::runtime_error(std::string(message)+": error="+std::to_string(static_cast<unsigned>(result.error))+" native="+std::to_string(result.native_code));
}
template<class Predicate>void until(Predicate predicate,const char* message){
 const auto deadline=Clock::now()+std::chrono::seconds(3);
 while(!predicate()&&Clock::now()<deadline)std::this_thread::sleep_for(std::chrono::milliseconds(4));
 check(predicate(),message);
}
AudioAsset silence(unsigned rate=44100,unsigned channels=2,std::uint64_t frames=88200){
 AudioAsset a;a.asset_id="12345678-1234-4234-8234-123456789abc";a.name="Synthetic zero PCM device proof";a.source_sha256=std::string(64,'0');
 a.sample_rate=rate;a.channels=channels;a.frame_count=frames;
 a.pcm.resize(static_cast<std::size_t>(frames)*channels*2,std::byte{0});return a;
}
}
int main(int argc,char** argv){
 std::filesystem::path report;
 if(argc>2){std::cerr<<"Expected an optional fresh report path\n";return 2;}
 if(argc==2){report=argv[1];if(std::filesystem::exists(report)){std::cerr<<"Preserve existing device proof\n";return 2;}}
 std::uint64_t first=0,paused=0,resumed=0,raw_paused=0,raw_resumed=0;
 const auto start=Clock::now();bool passed=false;std::string error;
 try{
  AudioPlayback player;auto a=silence();
  require(player.play(a,0),"Default-output XAudio2 silence must start or report device failure");
  a.pcm.clear();a.pcm.shrink_to_fit();
  until([&]{return player.snapshot().played_frames>=4410;},"Actual source sample clock did not advance");
  auto snapshot=player.snapshot();first=snapshot.played_frames;
  check(snapshot.sample_rate==44100&&snapshot.channels==2&&snapshot.total_frames==88200,"Original 44.1k stereo source format changed");
  check(snapshot.volume==0&&snapshot.owned_pcm_bytes==88200*4,"Muted source owns entire PCM after caller release");
  require(player.pause(),"Pause private XAudio2 engine");paused=player.snapshot().played_frames;
  std::this_thread::sleep_for(std::chrono::milliseconds(150));snapshot=player.snapshot();
  check(snapshot.state==AudioPlaybackState::paused&&snapshot.played_frames==paused,"Caption position moved while paused");
  require(player.resume(),"Resume private XAudio2 engine");
  until([&]{return player.snapshot().played_frames>paused;},"Caption source clock did not resume");resumed=player.snapshot().played_frames;
  require(player.stop(),"Stop and drain");snapshot=player.snapshot();
  check(snapshot.state==AudioPlaybackState::stopped&&!snapshot.source_voice&&snapshot.owned_pcm_bytes==0&&snapshot.played_frames==0,"Stop retained voice, PCM or caption position");

  auto short_clip=silence(44100,2,4410);require(player.play(short_clip,0),"Short natural-end fixture");
  until([&]{return player.snapshot().state==AudioPlaybackState::completed;},"Natural stream completion not observed");
  snapshot=player.snapshot();check(snapshot.played_frames==4410&&snapshot.position_seconds()==.1&&!snapshot.source_voice&&snapshot.owned_pcm_bytes==0,"Natural end lost final caption time or resources");
  auto stereo=silence();require(player.play(stereo,0),"Replacement initial stereo fixture");
  require(player.pause(),"Pause before replacement");auto mono=silence(48000,1,48000);
  require(player.play(mono,0),"Replace paused stereo with native 48k mono source");snapshot=player.snapshot();
  check(snapshot.sample_rate==48000&&snapshot.channels==1&&snapshot.generation==4,"Replacement failed to adopt unchanged source format");
  check(snapshot.peak_owned_pcm_bytes>=stereo.pcm.size()+mono.pcm.size(),"Replacement undercounted simultaneous PCM copies");
  require(player.close(),"Close active playback");snapshot=player.snapshot();
  check(snapshot.state==AudioPlaybackState::closed&&!snapshot.source_voice&&snapshot.owned_pcm_bytes==0,"Close retained PCM or source voice");

  // Independently inspect the actual adapter's SamplesPlayed while stopped.
  // The public paused caption cache alone cannot establish this hardware fact.
  auto raw_pcm=silence();AudioPlaybackResult created;
  auto device=detail::make_xaudio2_device(nullptr,raw_pcm.sample_rate,raw_pcm.channels,raw_pcm.pcm,0,created);
  require(created,"Create independent raw source cursor proof");check(static_cast<bool>(device),"No XAudio2 device returned after success");
  require(device->start(),"Start raw silence voice");
  until([&]{return device->state().played_frames>=2205;},"Raw SamplesPlayed did not advance");
  require(device->pause(),"Pause actual processing engine");raw_paused=device->state().played_frames;
  std::this_thread::sleep_for(std::chrono::milliseconds(150));
  check(device->state().played_frames==raw_paused,"Actual XAudio2 SamplesPlayed advanced during private-engine pause");
  require(device->resume(),"Resume actual processing engine");
  until([&]{return device->state().played_frames>raw_paused;},"Actual XAudio2 SamplesPlayed did not resume");raw_resumed=device->state().played_frames;
  const auto drain_start=Clock::now();device.reset();
  check(Clock::now()-drain_start<std::chrono::seconds(2),"Voice/engine drain exceeded bounded test deadline");
  // The PCM remains valid until the adapter is entirely destroyed.
  raw_pcm.pcm.clear();raw_pcm.pcm.shrink_to_fit();
  const auto destruction_start=Clock::now();
  {AudioPlayback active;require(active.play(silence(),0),"Destructor fixture active voice");}
  check(Clock::now()-destruction_start<std::chrono::seconds(2),"Owner destructor drain exceeded finite deadline");
  passed=true;
 }catch(const std::exception& failure){error=failure.what();}
 const auto elapsed=std::chrono::duration<double>(Clock::now()-start).count();
 std::ofstream file;if(!report.empty())file.open(report,std::ios::binary);
 auto& out=report.empty()?std::cout:file;
 out<<"{\"status\":\""<<(passed?"passed":"failed")<<"\",\"checks\":"<<checks
    <<",\"source_sample_rate\":44100,\"source_channels\":2,\"synthetic_silence\":true,\"source_volume\":0,\"family_references_used\":false"
    <<",\"first_frames\":"<<first<<",\"paused_frames\":"<<paused<<",\"resumed_frames\":"<<resumed
    <<",\"raw_paused_frames\":"<<raw_paused<<",\"raw_resumed_frames\":"<<raw_resumed<<",\"elapsed_seconds\":"<<elapsed<<"}\n";
 if(!error.empty())std::cerr<<error<<'\n';
 if(!report.empty()&&!file.good()){std::cerr<<"Cannot write owned report\n";return 2;}
 return passed?0:1;
}
