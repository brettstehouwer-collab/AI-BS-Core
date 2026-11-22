#include <aibs/audio_playback.hpp>
#include "audio_device.hpp"
#include <algorithm>
#include <cmath>
#include <new>
#include <thread>
#include <utility>

namespace aibs {
struct AudioPlayback::Impl {
 struct Clip {
  // Destruction is reverse declaration order: device first, PCM last.
  std::vector<std::byte> pcm;
  std::unique_ptr<detail::AudioDevice> device;
 };
 const std::thread::id owner=std::this_thread::get_id();
 AudioPlaybackSnapshot view;
 std::unique_ptr<Clip> clip;
 detail::AudioDeviceFactory factory=detail::make_xaudio2_device;
 void* factory_context=nullptr;
 bool on_owner()const noexcept{return owner==std::this_thread::get_id();}
 AudioPlaybackResult remember(AudioPlaybackResult result)noexcept{
  view.error=result.error;view.native_code=result.native_code;return result;
 }
 AudioPlaybackResult admissible()const noexcept{
  if(!on_owner())return {AudioPlaybackError::wrong_thread,0};
  if(view.state==AudioPlaybackState::closed)return {AudioPlaybackError::closed,0};
  return {};
 }
 void release_clip()noexcept{
  clip.reset();view.owned_pcm_bytes=0;view.source_voice=false;
 }
 void poll()noexcept{
  if(!clip)return;
  const auto state=clip->device->state();
  if(state.error!=0){
   view.state=AudioPlaybackState::failed;remember({AudioPlaybackError::backend_failure,state.error});release_clip();return;
  }
  if(view.state==AudioPlaybackState::playing){
   if(state.queued_buffers==0){
    view.played_frames=view.total_frames;view.state=AudioPlaybackState::completed;release_clip();
   }else view.played_frames=std::max(view.played_frames,std::min(view.total_frames,state.played_frames));
  }
 }
};
AudioPlayback::AudioPlayback():impl_(std::make_unique<Impl>()){}
AudioPlayback::~AudioPlayback()=default;

AudioPlaybackResult AudioPlayback::play(const AudioAsset& asset)noexcept {
 if(!impl_->on_owner())return {AudioPlaybackError::wrong_thread,0};
 return play(asset,impl_->view.volume);
}
AudioPlaybackResult AudioPlayback::play(const AudioAsset& asset,float volume)noexcept {
 auto& p=*impl_;if(const auto admitted=p.admissible();!admitted)return admitted;
 if(!std::isfinite(volume)||volume<0||volume>1)return p.remember({AudioPlaybackError::invalid_volume,0});
 try{validate_audio_asset(asset);}catch(const std::bad_alloc&){return p.remember({AudioPlaybackError::out_of_memory,0});}
 catch(...){return p.remember({AudioPlaybackError::invalid_asset,0});}
 p.poll();
 if(asset.pcm.size()>audio_playback_maximum_pcm_bytes||
    p.view.owned_pcm_bytes>audio_playback_maximum_replacement_pcm_bytes-asset.pcm.size())
  return p.remember({AudioPlaybackError::out_of_memory,0});
 std::unique_ptr<Impl::Clip> candidate;
 try{
  candidate=std::make_unique<Impl::Clip>();
  candidate->pcm=std::vector<std::byte>(asset.pcm.begin(),asset.pcm.end());
 }catch(...){return p.remember({AudioPlaybackError::out_of_memory,0});}
 const auto cost=candidate->pcm.capacity();
 if(cost>audio_playback_maximum_pcm_bytes||p.view.owned_pcm_bytes>audio_playback_maximum_replacement_pcm_bytes-cost)
  return p.remember({AudioPlaybackError::out_of_memory,0});
 p.view.peak_owned_pcm_bytes=std::max(p.view.peak_owned_pcm_bytes,p.view.owned_pcm_bytes+cost);
 AudioPlaybackResult prepared;
 candidate->device=p.factory(p.factory_context,asset.sample_rate,asset.channels,candidate->pcm,volume,prepared);
 if(!candidate->device)return p.remember(prepared?AudioPlaybackResult{AudioPlaybackError::backend_failure,0}:prepared);
 const bool resume_previous=p.clip&&p.view.state==AudioPlaybackState::playing;
 if(resume_previous){
  const auto paused=p.clip->device->pause();
  if(!paused)return p.remember(paused);
 }
 const auto started=candidate->device->start();
 if(!started){
  candidate.reset();
  if(resume_previous){
   const auto restored=p.clip->device->resume();
   if(!restored){p.view.state=AudioPlaybackState::failed;p.release_clip();return p.remember(restored);}
  }
  return p.remember(started);
 }
 p.clip=std::move(candidate);++p.view.generation;
 p.view.state=AudioPlaybackState::playing;p.view.volume=volume;
 p.view.sample_rate=asset.sample_rate;p.view.channels=asset.channels;
 p.view.total_frames=asset.frame_count;p.view.played_frames=0;
 p.view.source_voice=true;p.view.owned_pcm_bytes=cost;
 return p.remember({});
}
AudioPlaybackResult AudioPlayback::pause()noexcept {
 auto& p=*impl_;if(const auto admitted=p.admissible();!admitted)return admitted;p.poll();
 if(p.view.state==AudioPlaybackState::paused)return p.remember({});
 if(!p.clip||p.view.state!=AudioPlaybackState::playing)return p.remember({AudioPlaybackError::invalid_state,0});
 const auto stopped=p.clip->device->pause();if(!stopped)return p.remember(stopped);
 // StopEngine is synchronous; sample after it has stopped the private engine.
 const auto state=p.clip->device->state();
 if(state.error){p.view.state=AudioPlaybackState::failed;p.release_clip();return p.remember({AudioPlaybackError::backend_failure,state.error});}
 p.view.played_frames=state.queued_buffers?std::max(p.view.played_frames,std::min(p.view.total_frames,state.played_frames)):p.view.total_frames;
 p.view.state=AudioPlaybackState::paused;return p.remember({});
}
AudioPlaybackResult AudioPlayback::resume()noexcept {
 auto& p=*impl_;if(const auto admitted=p.admissible();!admitted)return admitted;p.poll();
 if(p.view.state==AudioPlaybackState::playing)return p.remember({});
 if(!p.clip||p.view.state!=AudioPlaybackState::paused)return p.remember({AudioPlaybackError::invalid_state,0});
 const auto result=p.clip->device->resume();if(!result)return p.remember(result);
 p.view.state=AudioPlaybackState::playing;return p.remember({});
}
AudioPlaybackResult AudioPlayback::stop()noexcept {
 auto& p=*impl_;if(const auto admitted=p.admissible();!admitted)return admitted;
 p.release_clip();p.view.state=AudioPlaybackState::stopped;p.view.played_frames=p.view.total_frames=0;
 p.view.sample_rate=p.view.channels=0;return p.remember({});
}
AudioPlaybackResult AudioPlayback::close()noexcept {
 auto& p=*impl_;if(!p.on_owner())return {AudioPlaybackError::wrong_thread,0};
 if(p.view.state==AudioPlaybackState::closed)return {};
 p.release_clip();p.view.state=AudioPlaybackState::closed;p.view.played_frames=p.view.total_frames=0;
 p.view.sample_rate=p.view.channels=0;return p.remember({});
}
AudioPlaybackResult AudioPlayback::set_volume(float volume)noexcept {
 auto& p=*impl_;if(const auto admitted=p.admissible();!admitted)return admitted;
 if(!std::isfinite(volume)||volume<0||volume>1)return p.remember({AudioPlaybackError::invalid_volume,0});
 if(p.clip){const auto changed=p.clip->device->set_volume(volume);if(!changed)return p.remember(changed);}
 p.view.volume=volume;return p.remember({});
}
AudioPlaybackSnapshot AudioPlayback::snapshot()noexcept {
 auto& p=*impl_;if(!p.on_owner()){AudioPlaybackSnapshot rejected;rejected.state=AudioPlaybackState::failed;rejected.error=AudioPlaybackError::wrong_thread;return rejected;}
 p.poll();return p.view;
}
std::unique_ptr<AudioPlayback> detail::AudioPlaybackTestAccess::make(AudioDeviceFactory factory,void* context){
 auto player=std::make_unique<AudioPlayback>();player->impl_->factory=factory;player->impl_->factory_context=context;return player;
}
}
