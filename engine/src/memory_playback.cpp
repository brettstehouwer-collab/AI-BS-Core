#include <aibs/memory_playback.hpp>
#include <aibs/engine.hpp>
#include "memory_detail.hpp"
#include <algorithm>
#include <limits>
#include <new>
#include <string>
#include <thread>
namespace aibs {
std::optional<std::size_t> memory_caption_index(const AudioAsset& asset,std::uint64_t frame,bool draft)noexcept{
 if(frame>=asset.frame_count||(!draft&&asset.caption_review!=AudioCaptionReview::checked))return {};
 const auto next=std::upper_bound(asset.captions.begin(),asset.captions.end(),frame,
  [](std::uint64_t value,const AudioCaption& cue){return value<cue.start_frame;});
 if(next==asset.captions.begin())return {};
 const auto cue=std::prev(next);
 if(frame>=cue->end_frame)return {};
 return static_cast<std::size_t>(cue-asset.captions.begin());
}
namespace {
std::optional<std::size_t> charge(std::initializer_list<std::size_t> pieces)noexcept{
 std::size_t total=0;
 for(auto item:pieces){if(item>memory_playback_maximum_resident_bytes-total)return {};total+=item;}
 return total;
}
bool same_shared_asset(const std::shared_ptr<const AudioAsset>& a,const std::shared_ptr<const AudioAsset>& b)noexcept{
 // Do not collapse different aliased objects merely because their control
 // block is shared. Registry entries normally own exactly one AudioAsset.
 return a&&b&&a.get()==b.get()&&!a.owner_before(b)&&!b.owner_before(a);
}
}
struct MemoryPlaybackSession::Impl {
 const std::thread::id owner=std::this_thread::get_id();
 std::shared_ptr<const AudioAsset> asset;
 std::unique_ptr<AudioPlayback> player=std::make_unique<AudioPlayback>();
 std::array<char,37> station{};
 AudioPlaybackSnapshot audio;
 MemoryPlaybackError error=MemoryPlaybackError::none;
 AudioPlaybackResult audio_error;
 std::size_t source=0,other=0,peak=0;
 bool game_paused=false,resume_intent=false,allow_draft=false,closed=false;
 bool on_owner()const noexcept{return owner==std::this_thread::get_id();}
 MemoryPlaybackResult admit()const noexcept{
  if(!on_owner())return {MemoryPlaybackError::wrong_thread,{}};
  if(closed)return {MemoryPlaybackError::closed,{}};
  return {};
 }
 MemoryPlaybackResult remember(MemoryPlaybackResult value)noexcept{error=value.error;audio_error=value.audio;return value;}
 MemoryPlaybackResult from_audio(AudioPlaybackResult value)noexcept{
  audio=player->snapshot();return remember(value?MemoryPlaybackResult{}:MemoryPlaybackResult{MemoryPlaybackError::playback_failure,value});
 }
 void sync()noexcept{audio=player->snapshot();if(audio.state==AudioPlaybackState::failed){error=MemoryPlaybackError::playback_failure;audio_error={audio.error,audio.native_code};resume_intent=false;}}
 bool reserve(std::size_t observed_other,std::size_t candidate_pcm=0)noexcept{
  const auto total=charge({observed_other,source,audio.owned_pcm_bytes,candidate_pcm});
  if(!total)return false;
  peak=std::max(peak,*total);return true;
 }
};
MemoryPlaybackSession::MemoryPlaybackSession():impl_(std::make_unique<Impl>()){}
MemoryPlaybackSession::~MemoryPlaybackSession()=default;
MemoryPlaybackResult MemoryPlaybackSession::bind(std::string_view station,std::shared_ptr<const AudioAsset> asset,
 std::size_t other,bool allow_draft)noexcept{
 auto& p=*impl_;if(const auto admission=p.admit();!admission)return admission;
 if(station.size()!=36)return p.remember({MemoryPlaybackError::invalid_station,{}});
 std::size_t decoded=0;
 try{
  if(!is_uuid(std::string(station)))return p.remember({MemoryPlaybackError::invalid_station,{}});
  if(!asset)return p.remember({MemoryPlaybackError::invalid_asset,{}});
  validate_audio_asset(*asset);decoded=audio_asset_cost(*asset).decoded_bytes;
 }catch(const std::bad_alloc&){return p.remember({MemoryPlaybackError::out_of_memory,{}});}
 catch(...){return p.remember({MemoryPlaybackError::invalid_asset,{}});}
 const auto previous_source=same_shared_asset(p.asset,asset)?0:p.source;
 const auto peak=charge({other,decoded,previous_source,p.audio.owned_pcm_bytes});
 if(!peak)return p.remember({MemoryPlaybackError::budget_exceeded,{}});
 const auto stopped=p.player->stop();if(!stopped)return p.from_audio(stopped);
 p.asset=std::move(asset);p.source=decoded;p.other=other;p.allow_draft=allow_draft;p.resume_intent=false;
 p.station.fill(0);std::copy(station.begin(),station.end(),p.station.begin());p.peak=std::max(p.peak,*peak);
 return p.from_audio({});
}
MemoryPlaybackResult MemoryPlaybackSession::play_or_resume(std::size_t other)noexcept{
 auto& p=*impl_;if(const auto admission=p.admit();!admission)return admission;
 if(!p.asset)return p.remember({MemoryPlaybackError::unbound,{}});
 if(p.game_paused)return p.remember({MemoryPlaybackError::game_paused,{}});
 p.sync();
 const bool start=p.audio.state!=AudioPlaybackState::playing&&p.audio.state!=AudioPlaybackState::paused;
 if(!p.reserve(other,start?audio_playback_maximum_pcm_bytes:0))return p.remember({MemoryPlaybackError::budget_exceeded,{}});
 AudioPlaybackResult result;
 if(start)result=p.player->play(*p.asset);
 else if(p.audio.state==AudioPlaybackState::paused)result=p.player->resume();
 if(result){p.other=other;p.resume_intent=false;}
 return p.from_audio(result);
}
MemoryPlaybackResult MemoryPlaybackSession::pause()noexcept{
 auto& p=*impl_;if(const auto admission=p.admit();!admission)return admission;
 const auto result=p.player->pause();if(result)p.resume_intent=false;return p.from_audio(result);
}
MemoryPlaybackResult MemoryPlaybackSession::stop()noexcept{
 auto& p=*impl_;if(const auto admission=p.admit();!admission)return admission;
 const auto result=p.player->stop();if(result)p.resume_intent=false;return p.from_audio(result);
}
MemoryPlaybackResult MemoryPlaybackSession::set_game_paused(bool paused,std::size_t other)noexcept{
 auto& p=*impl_;if(const auto admission=p.admit();!admission)return admission;p.sync();
 if(paused==p.game_paused)return p.remember({});
 if(!p.reserve(other))return p.remember({MemoryPlaybackError::budget_exceeded,{}});
 if(paused){
  const bool was_playing=p.audio.state==AudioPlaybackState::playing;
  if(was_playing){const auto result=p.player->pause();if(!result)return p.from_audio(result);}
  p.resume_intent=was_playing;p.game_paused=true;p.other=other;return p.from_audio({});
 }
 if(p.resume_intent&&p.audio.state==AudioPlaybackState::paused){
  const auto result=p.player->resume();if(!result)return p.from_audio(result);
 }
 p.game_paused=false;p.resume_intent=false;p.other=other;return p.from_audio({});
}
MemoryPlaybackResult MemoryPlaybackSession::set_volume(float volume)noexcept{
 auto& p=*impl_;if(const auto admission=p.admit();!admission)return admission;return p.from_audio(p.player->set_volume(volume));
}
MemoryPlaybackResult MemoryPlaybackSession::close()noexcept{
 auto& p=*impl_;if(!p.on_owner())return {MemoryPlaybackError::wrong_thread,{}};
 if(p.closed)return {};
 const auto result=p.player->close();if(!result)return p.from_audio(result);
 p.asset.reset();p.source=p.other=0;p.station.fill(0);p.game_paused=p.resume_intent=p.allow_draft=false;p.closed=true;return p.from_audio({});
}
MemoryPlaybackSnapshot MemoryPlaybackSession::snapshot()noexcept{
 auto& p=*impl_;MemoryPlaybackSnapshot result;
 if(!p.on_owner()){result.error=MemoryPlaybackError::wrong_thread;return result;}
 p.sync();result.asset=p.asset;result.station_uuid=p.station;result.playback=p.audio;result.error=p.error;result.audio_error=p.audio_error;
 result.game_paused=p.game_paused;result.resume_on_game_resume=p.resume_intent;result.allow_draft_preview=p.allow_draft;
 result.review_pending=p.asset&&p.asset->caption_review!=AudioCaptionReview::checked;
 result.source_decoded_bytes=p.source;result.other_chapter_residency_bytes=p.other;result.reserved_peak_bytes=p.peak;
 const auto total=charge({p.source,p.other,p.audio.owned_pcm_bytes});
 result.resident_bytes=total.value_or(std::numeric_limits<std::size_t>::max());
 if(p.asset&&(p.audio.state==AudioPlaybackState::playing||p.audio.state==AudioPlaybackState::paused))
  result.caption_index=memory_caption_index(*p.asset,p.audio.played_frames,p.allow_draft);
 return result;
}
std::unique_ptr<MemoryPlaybackSession> detail::MemoryPlaybackTestAccess::make(std::unique_ptr<AudioPlayback> player){
 auto session=std::make_unique<MemoryPlaybackSession>();session->impl_->player=std::move(player);return session;
}
}
