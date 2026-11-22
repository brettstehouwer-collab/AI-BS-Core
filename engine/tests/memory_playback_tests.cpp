#include <aibs/memory_playback.hpp>
#include "memory_detail.hpp"
#include "audio_device.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>
#include <thread>
using namespace aibs;
namespace {
unsigned checks=0;
void check(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
constexpr auto station="12345678-1234-4234-8234-123456789abc";
std::shared_ptr<AudioAsset> asset(){
 auto a=std::make_shared<AudioAsset>();a->asset_id="87654321-1234-4234-8234-123456789abc";a->name="Synthetic caption fixture";a->source_sha256=std::string(64,'a');
 a->sample_rate=44100;a->channels=2;a->frame_count=22050;a->pcm.resize(88200);
 a->captions={{0,4410,"First cue"},{6615,11025,"Second cue"},{13230,22050,"Final cue"}};
 a->caption_review=AudioCaptionReview::checked;return a;
}
struct Control {std::uint64_t frames=0;std::uint32_t queued=1;unsigned starts=0,pauses=0,resumes=0,destroys=0;bool fail_pause=false,fail_resume=false;};
struct Device:detail::AudioDevice {
 Control& c;explicit Device(Control& control):c(control){}
 ~Device()override{++c.destroys;}
 AudioPlaybackResult start()noexcept override{++c.starts;return {};}
 AudioPlaybackResult pause()noexcept override{++c.pauses;return c.fail_pause?AudioPlaybackResult{AudioPlaybackError::backend_failure,-1}:AudioPlaybackResult{};}
 AudioPlaybackResult resume()noexcept override{++c.resumes;return c.fail_resume?AudioPlaybackResult{AudioPlaybackError::backend_failure,-2}:AudioPlaybackResult{};}
 AudioPlaybackResult set_volume(float)noexcept override{return {};}
 detail::AudioDeviceState state()noexcept override{return {c.frames,c.queued,0};}
};
std::unique_ptr<detail::AudioDevice> create(void* ptr,unsigned,unsigned,std::span<const std::byte>,float,AudioPlaybackResult& result)noexcept{
 try{return std::make_unique<Device>(*static_cast<Control*>(ptr));}catch(...){result={AudioPlaybackError::out_of_memory,0};return {};}
}
std::unique_ptr<MemoryPlaybackSession> session(Control& c){return detail::MemoryPlaybackTestAccess::make(detail::AudioPlaybackTestAccess::make(create,&c));}
void lookup(){
 auto a=asset();
 for(const auto [frame,index]:{std::pair{0ull,0u},std::pair{4409ull,0u},std::pair{6615ull,1u},std::pair{11024ull,1u},std::pair{13230ull,2u},std::pair{22049ull,2u}})
  check(memory_caption_index(*a,frame)==index,"Cue interval is start-inclusive/end-exclusive");
 for(auto frame:{4410ull,6614ull,11025ull,13229ull,22050ull,std::numeric_limits<unsigned long long>::max()})check(!memory_caption_index(*a,frame),"Cue gaps/end/out-of-range are empty");
 a->caption_review=AudioCaptionReview::draft;check(!memory_caption_index(*a,0),"Draft cue withheld by default");
 check(memory_caption_index(*a,0,true)==0,"Explicit draft preview permits lookup without approval");
 a->captions.clear();check(!memory_caption_index(*a,0,true),"Empty captions have no cue");
}
void controls(){
 Control c;auto m=session(c);auto a=asset();
 check(!m->snapshot().asset&&m->play_or_resume(0).error==MemoryPlaybackError::unbound,"Unbound session cannot play");
 check(static_cast<bool>(m->bind(station,a,0)),"Bind validates station and source");auto snap=m->snapshot();
 check(snap.asset.get()==a.get()&&snap.station_id()==station&&snap.playback.state==AudioPlaybackState::stopped&&c.starts==0,"Bind owns source and never auto-plays");
 check(!snap.caption_index&&!snap.review_pending&&snap.source_decoded_bytes==audio_asset_cost(*a).decoded_bytes,"Stopped binding hides captions and charges source");
 check(static_cast<bool>(m->play_or_resume(0))&&c.starts==1,"Explicit Play starts memory");
 c.frames=1000;check(m->snapshot().caption_index==0,"Playing current cue from actual source frames");
 check(static_cast<bool>(m->set_game_paused(true,0)),"Game pause pauses active memory");snap=m->snapshot();
 check(snap.game_paused&&snap.resume_on_game_resume&&snap.playback.state==AudioPlaybackState::paused,"Game pause records only active-play intent");
 c.frames=2000;check(m->snapshot().playback.played_frames==1000&&m->snapshot().caption_index==0,"Game pause holds current cue");
 check(static_cast<bool>(m->set_game_paused(false,0))&&c.resumes==1,"Unpause resumes remembered active memory");
 c.frames=5000;check(!m->snapshot().caption_index,"Playing cue gap is empty");c.frames=7000;check(m->snapshot().caption_index==1,"Later cue is selected");
 check(static_cast<bool>(m->pause()),"Manual pause");
 check(static_cast<bool>(m->set_game_paused(true,0))&&!m->snapshot().resume_on_game_resume,"Game pause cannot invent resume intent for manual pause");
 check(static_cast<bool>(m->set_game_paused(false,0))&&m->snapshot().playback.state==AudioPlaybackState::paused,"Unpause preserves manual pause");
 check(static_cast<bool>(m->play_or_resume(0)),"Explicit Play resumes manual pause");
 check(static_cast<bool>(m->set_game_paused(true,0)),"Autopause before manual stop");
 check(static_cast<bool>(m->stop())&&!m->snapshot().resume_on_game_resume,"Manual Stop clears remembered resume intent");
 check(static_cast<bool>(m->set_game_paused(false,0))&&m->snapshot().playback.state==AudioPlaybackState::stopped,"Unpause never restarts a manually stopped recording");
 auto draft=asset();draft->caption_review=AudioCaptionReview::draft;c.frames=0;
 check(static_cast<bool>(m->bind(station,draft,0))&&static_cast<bool>(m->play_or_resume(0)),"Draft recording can play as optional audio without claimed caption review");
 check(m->snapshot().review_pending&&!m->snapshot().caption_index,"Draft captions remain withheld during playback");
 check(static_cast<bool>(m->set_game_paused(true,0)),"Autopause before rebind");
 check(static_cast<bool>(m->bind(station,a,0)),"Explicit rebind stops old memory");
 check(!m->snapshot().resume_on_game_resume&&m->snapshot().playback.state==AudioPlaybackState::stopped,"Rebind clears resume intent and does not play");
 check(static_cast<bool>(m->set_game_paused(false,0))&&m->snapshot().playback.state==AudioPlaybackState::stopped,"Unpause cannot start newly bound recording");
 check(static_cast<bool>(m->bind(station,draft,0,true))&&static_cast<bool>(m->play_or_resume(0)),"Explicit draft preview bind");
 check(m->snapshot().review_pending&&m->snapshot().caption_index==0,"Draft preview remains visibly pending review");
 c.frames=22050;c.queued=0;snap=m->snapshot();check(snap.playback.state==AudioPlaybackState::completed&&!snap.caption_index,"Completed memory hides captions");
 auto held=m->snapshot();snap.asset.reset();std::weak_ptr<const AudioAsset> lifetime=draft;draft.reset();
 check(static_cast<bool>(m->close())&&!m->snapshot().asset,"Close releases binding");
 check(!lifetime.expired()&&held.asset->captions[*memory_caption_index(*held.asset,0,true)].text=="First cue","Returned snapshot retains caption asset ownership after session close");
 held.asset.reset();check(lifetime.expired(),"No hidden session source ownership after close");
 check(m->bind(station,a,0).error==MemoryPlaybackError::closed,"Closed session is terminal");
}
void budgets_and_failures(){
 Control c;auto m=session(c);auto a=asset();check(static_cast<bool>(m->bind(station,a,0)),"Budget fixture binds");
 const auto baseline=m->snapshot();
 check(m->bind("invalid",a,0).error==MemoryPlaybackError::invalid_station&&m->snapshot().asset==baseline.asset,"Invalid station leaves old binding unchanged");
 auto malformed=asset();++malformed->frame_count;
 check(m->bind(station,malformed,0).error==MemoryPlaybackError::invalid_asset&&m->snapshot().asset==baseline.asset,"Invalid replacement validated before old mutation");
 check(m->bind(station,{},0).error==MemoryPlaybackError::invalid_asset,"Null source rejected");
 check(m->bind(station,a,std::numeric_limits<std::size_t>::max()).error==MemoryPlaybackError::budget_exceeded,"Bind arithmetic overflow rejects");
 const auto source=audio_asset_cost(*a).decoded_bytes;
 const auto boundary=memory_playback_maximum_resident_bytes-source-audio_playback_maximum_pcm_bytes;
 check(m->play_or_resume(boundary+1).error==MemoryPlaybackError::budget_exceeded&&c.starts==0,"Over-budget Play rejects before device creation");
 check(static_cast<bool>(m->play_or_resume(boundary)),"Exact conservative 128MiB boundary admitted");
 auto snap=m->snapshot();check(snap.reserved_peak_bytes==memory_playback_maximum_resident_bytes,"Source plus PCM reserve plus other charged exactly once");
 check(static_cast<bool>(m->set_game_paused(true,0)),"Budget fixture autopause");
 check(m->set_game_paused(false,std::numeric_limits<std::size_t>::max()).error==MemoryPlaybackError::budget_exceeded&&m->snapshot().game_paused&&m->snapshot().resume_on_game_resume,"Over-budget game resume preserves paused intent before mutation");
 const auto same_bound=memory_playback_maximum_resident_bytes-source-snap.playback.owned_pcm_bytes;
 check(static_cast<bool>(m->bind(station,a,same_bound)),"Same shared asset is deduplicated during rebind admission");
 auto b=asset();
 check(m->bind(station,b,memory_playback_maximum_resident_bytes-source).error==MemoryPlaybackError::budget_exceeded&&m->snapshot().asset==a,"Distinct old/new sources both charged during replacement");
 check(static_cast<bool>(m->set_game_paused(false,0))&&static_cast<bool>(m->play_or_resume(0)),"Failure fixture plays");
 c.fail_pause=true;check(m->set_game_paused(true,0).error==MemoryPlaybackError::playback_failure&&!m->snapshot().game_paused,"Failed auto-pause does not invent paused state");c.fail_pause=false;
 check(static_cast<bool>(m->set_game_paused(true,0)),"Pause before failed resume");c.fail_resume=true;
 check(m->set_game_paused(false,0).error==MemoryPlaybackError::playback_failure&&m->snapshot().game_paused&&m->snapshot().resume_on_game_resume,"Failed resume keeps retry intent");c.fail_resume=false;
 MemoryPlaybackResult wrong;MemoryPlaybackSnapshot foreign;std::thread other([&]{wrong=m->stop();foreign=m->snapshot();});other.join();
 check(wrong.error==MemoryPlaybackError::wrong_thread&&foreign.error==MemoryPlaybackError::wrong_thread,"Wrong-thread session call cannot release owner audio");
 check(m->snapshot().asset==a,"Wrong-thread call preserves binding");
}
}
int main(){try{lookup();controls();budgets_and_failures();std::cout<<checks<<" memory playback checks passed\n";return 0;}
catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
