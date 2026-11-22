#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <xaudio2.h>
#include "audio_device.hpp"
#include <atomic>
#include <limits>
#include <new>
#include <thread>

namespace aibs::detail {
namespace {
AudioPlaybackResult failure(HRESULT code,AudioPlaybackError error=AudioPlaybackError::backend_failure)noexcept{
 return {error,static_cast<std::int32_t>(code)};
}
class XAudioDevice final:public AudioDevice,private IXAudio2EngineCallback {
 IXAudio2* engine_=nullptr;
 IXAudio2MasteringVoice* master_=nullptr;
 IXAudio2SourceVoice* source_=nullptr;
 const std::thread::id owner_=std::this_thread::get_id();
 bool com_owned_=false,callback_registered_=false;
 std::atomic<HRESULT> critical_{S_OK};
 void STDMETHODCALLTYPE OnProcessingPassStart()noexcept override{}
 void STDMETHODCALLTYPE OnProcessingPassEnd()noexcept override{}
 void STDMETHODCALLTYPE OnCriticalError(HRESULT error)noexcept override{critical_.store(error,std::memory_order_release);}
 public:
 ~XAudioDevice()override {
  if(engine_)engine_->StopEngine();
  // DestroyVoice is the API's completion fence: it returns after this voice
  // cannot read submitted PCM or invoke voice callbacks. The parent Clip still
  // owns PCM until this whole destructor has finished.
  if(source_){source_->DestroyVoice();source_=nullptr;}
  if(master_){master_->DestroyVoice();master_=nullptr;}
  if(engine_){
   if(callback_registered_)engine_->UnregisterForCallbacks(this);
   engine_->Release();engine_=nullptr;
  }
  // All operations, including destruction, have an explicit owner-thread
  // contract. Never uninitialize another thread's COM apartment on misuse.
  if(com_owned_&&std::this_thread::get_id()==owner_)CoUninitialize();
 }
 AudioPlaybackResult initialize(unsigned rate,unsigned channels,std::span<const std::byte> pcm,float volume)noexcept {
  const auto initialized=CoInitializeEx(nullptr,COINIT_MULTITHREADED);
  if(SUCCEEDED(initialized))com_owned_=true;
  else if(initialized!=RPC_E_CHANGED_MODE)return failure(initialized,AudioPlaybackError::device_unavailable);
  // RPC_E_CHANGED_MODE means the owner already has a valid STA apartment.
  // Reuse that apartment without changing it or balancing somebody else's init.
  auto code=XAudio2Create(&engine_,0,XAUDIO2_DEFAULT_PROCESSOR);
  if(FAILED(code))return failure(code,AudioPlaybackError::device_unavailable);
  code=engine_->RegisterForCallbacks(this);if(FAILED(code))return failure(code);
  callback_registered_=true;
  code=engine_->CreateMasteringVoice(&master_,XAUDIO2_DEFAULT_CHANNELS,XAUDIO2_DEFAULT_SAMPLERATE,
   0,nullptr,nullptr,AudioCategory_GameMedia);
  if(FAILED(code))return failure(code,AudioPlaybackError::device_unavailable);
  engine_->StopEngine();
  WAVEFORMATEX format{};format.wFormatTag=WAVE_FORMAT_PCM;
  format.nChannels=static_cast<WORD>(channels);format.nSamplesPerSec=rate;format.wBitsPerSample=16;
  format.nBlockAlign=static_cast<WORD>(channels*2);format.nAvgBytesPerSec=rate*format.nBlockAlign;
  code=engine_->CreateSourceVoice(&source_,&format,XAUDIO2_VOICE_NOPITCH,1,nullptr,nullptr,nullptr);
  if(FAILED(code))return failure(code);
  XAUDIO2_VOICE_DETAILS details{};source_->GetVoiceDetails(&details);
  if(details.InputSampleRate!=rate||details.InputChannels!=channels)return failure(E_UNEXPECTED);
  code=source_->SetVolume(volume);if(FAILED(code))return failure(code);
  if(pcm.empty()||pcm.size()>std::numeric_limits<UINT32>::max())return failure(E_INVALIDARG);
  XAUDIO2_BUFFER buffer{};buffer.Flags=XAUDIO2_END_OF_STREAM;
  buffer.AudioBytes=static_cast<UINT32>(pcm.size());buffer.pAudioData=reinterpret_cast<const BYTE*>(pcm.data());
  code=source_->SubmitSourceBuffer(&buffer);return FAILED(code)?failure(code):AudioPlaybackResult{};
 }
 AudioPlaybackResult start()noexcept override {
  auto code=source_->Start();if(FAILED(code))return failure(code);
  code=engine_->StartEngine();return FAILED(code)?failure(code):AudioPlaybackResult{};
 }
 AudioPlaybackResult pause()noexcept override {
  engine_->StopEngine();const auto code=critical_.load(std::memory_order_acquire);
  return FAILED(code)?failure(code):AudioPlaybackResult{};
 }
 AudioPlaybackResult resume()noexcept override {
  const auto code=engine_->StartEngine();return FAILED(code)?failure(code):AudioPlaybackResult{};
 }
 AudioPlaybackResult set_volume(float volume)noexcept override {
  const auto code=source_->SetVolume(volume);return FAILED(code)?failure(code):AudioPlaybackResult{};
 }
 AudioDeviceState state()noexcept override {
  const auto error=critical_.load(std::memory_order_acquire);
  if(FAILED(error))return {0,0,static_cast<std::int32_t>(error)};
  XAUDIO2_VOICE_STATE state{};source_->GetState(&state,0);
  return {state.SamplesPlayed,state.BuffersQueued,0};
 }
};
}
std::unique_ptr<AudioDevice> make_xaudio2_device(void*,unsigned rate,unsigned channels,
 std::span<const std::byte> pcm,float volume,AudioPlaybackResult& result)noexcept {
 try{
  auto device=std::make_unique<XAudioDevice>();result=device->initialize(rate,channels,pcm,volume);
  if(!result)return {};
  return device;
 }catch(...){result={AudioPlaybackError::out_of_memory,0};return {};}
}
}
