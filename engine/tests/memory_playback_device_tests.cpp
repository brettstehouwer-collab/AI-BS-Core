#include <aibs/memory_playback.hpp>
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
void require(MemoryPlaybackResult value,const char* message){++checks;if(!value)throw std::runtime_error(std::string(message)+": memory="+std::to_string(static_cast<unsigned>(value.error))+" audio="+std::to_string(static_cast<unsigned>(value.audio.error)));}
template<class Predicate>void until(Predicate predicate,const char* message){const auto end=Clock::now()+std::chrono::seconds(3);while(!predicate()&&Clock::now()<end)std::this_thread::sleep_for(std::chrono::milliseconds(3));check(predicate(),message);}
std::shared_ptr<AudioAsset> silence(){
 auto asset=std::make_shared<AudioAsset>();asset->asset_id="12345678-1234-4234-8234-123456789abc";asset->name="Synthetic zero PCM caption proof";asset->source_sha256=std::string(64,'0');
 asset->sample_rate=44100;asset->channels=2;asset->frame_count=22050;asset->pcm.resize(88200,std::byte{0});
 asset->captions={{0,4410,"Synthetic first cue"},{6615,11025,"Synthetic second cue"},{13230,22050,"Synthetic final cue"}};asset->caption_review=AudioCaptionReview::checked;return asset;
}
}
int main(int argc,char** argv){
 std::filesystem::path report;if(argc>2)return 2;if(argc==2){report=argv[1];if(std::filesystem::exists(report))return 2;}
 const auto start=Clock::now();bool passed=false;std::uint64_t paused=0,resumed=0;std::string error;
 try{
  MemoryPlaybackSession session;auto original=silence();constexpr auto station="87654321-1234-4234-8234-123456789abc";
  require(session.set_volume(0),"Source-only mute");require(session.bind(station,original,0),"Bind synthetic original");
  check(session.snapshot().playback.generation==0&&!session.snapshot().caption_index,"Binding must not start hardware or show cue");
  require(session.play_or_resume(0),"Explicit memory Play");
  until([&]{return session.snapshot().playback.played_frames>=1000;},"Source clock did not reach first caption");
  auto snapshot=session.snapshot();check(snapshot.caption_index==0&&snapshot.asset->captions[*snapshot.caption_index].text=="Synthetic first cue","First caption selected from actual source frame");
  require(session.set_game_paused(true,0),"Game pause active recording");snapshot=session.snapshot();paused=snapshot.playback.played_frames;
  check(snapshot.resume_on_game_resume&&snapshot.game_paused,"Game pause remembers active source only");
  std::this_thread::sleep_for(std::chrono::milliseconds(150));snapshot=session.snapshot();
  check(snapshot.playback.played_frames==paused&&snapshot.caption_index==0,"Paused caption and source frame must hold");
  require(session.set_game_paused(false,0),"Game unpause");
  until([&]{return session.snapshot().playback.played_frames>paused;},"Game unpause failed to resume source");resumed=session.snapshot().playback.played_frames;
  until([&]{return session.snapshot().playback.played_frames>=7000;},"Source did not reach second caption");
  snapshot=session.snapshot();check(snapshot.caption_index==1,"Second cue follows actual XAudio2 sample clock");
  require(session.pause(),"Manual pause");require(session.set_game_paused(true,0),"Game pause manually paused source");
  check(!session.snapshot().resume_on_game_resume,"Manual pause must not acquire game resume intent");
  require(session.set_game_paused(false,0),"Unpause after manual pause");check(session.snapshot().playback.state==AudioPlaybackState::paused,"Game unpause must retain manual pause");
  require(session.play_or_resume(0),"Explicit resume");require(session.set_game_paused(true,0),"Autopause before Stop");require(session.stop(),"Manual Stop while game paused");
  require(session.set_game_paused(false,0),"Unpause after Stop");snapshot=session.snapshot();
  check(snapshot.playback.state==AudioPlaybackState::stopped&&!snapshot.resume_on_game_resume&&!snapshot.caption_index,"Manual Stop blocks later game resume and hides cue");
  require(session.play_or_resume(0),"Explicit replay");require(session.set_game_paused(true,0),"Autopause before rebind");
  auto draft=silence();draft->caption_review=AudioCaptionReview::draft;require(session.bind(station,draft,0),"Rebind another synthetic recording");
  require(session.set_game_paused(false,0),"Unpause newly bound recording");check(session.snapshot().playback.state==AudioPlaybackState::stopped,"Rebind cannot auto-play on game resume");
  require(session.play_or_resume(0),"Explicit draft playback");snapshot=session.snapshot();
  check(snapshot.review_pending&&!snapshot.caption_index,"Draft captions withheld despite explicit audio playback");
  require(session.bind(station,draft,0,true),"Explicit draft cue preview");require(session.play_or_resume(0),"Play draft preview");snapshot=session.snapshot();
  check(snapshot.review_pending&&snapshot.caption_index==0,"Draft preview remains pending review");
  until([&]{return session.snapshot().playback.state==AudioPlaybackState::completed;},"Memory did not complete naturally");snapshot=session.snapshot();
  check(!snapshot.caption_index&&snapshot.playback.played_frames==22050,"Completion hides cue and retains exact final frame");
  require(session.close(),"Close memory session");snapshot=session.snapshot();
  check(!snapshot.asset&&!snapshot.caption_index&&!snapshot.playback.source_voice&&snapshot.playback.owned_pcm_bytes==0,"Close releases binding, voice and PCM");
  passed=true;
 }catch(const std::exception& failure){error=failure.what();}
 std::ofstream file;if(!report.empty())file.open(report,std::ios::binary);auto& out=report.empty()?std::cout:file;
 out<<"{\"status\":\""<<(passed?"passed":"failed")<<"\",\"checks\":"<<checks<<",\"source_sample_rate\":44100,\"source_channels\":2,\"synthetic_silence\":true,\"source_volume\":0,\"family_references_used\":false,\"paused_frame\":"<<paused<<",\"resumed_frame\":"<<resumed<<",\"caption_indices_verified\":[0,1],\"elapsed_seconds\":"<<std::chrono::duration<double>(Clock::now()-start).count()<<"}\n";
 if(!error.empty())std::cerr<<error<<'\n';if(!report.empty()&&!file.good())return 2;return passed?0:1;
}
