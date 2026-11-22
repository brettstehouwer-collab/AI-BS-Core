// Application-owned diagnostic recorder. Capture is renderer-only BGRA and
// current-process STATIC/EDIT glyph composition; never the user's desktop.
class ChapterRecorder {
 aibs::recording::VideoEncoder encoder_;CapturedFrame frame_;aibs::recording::OwnedHudComposer hud_;HWND owner_=nullptr;
 Clock::time_point started_=Clock::now(),next_=started_;std::string error_;std::uint64_t captures_=0,nonbackground_=0,owned_hud_=0;
 std::size_t frame_peak_=0,overlay_peak_=0;std::uint64_t gpu_readback_peak_=0;bool finished_=false;double capture_seconds_=0;
public:
 ChapterRecorder(const Options& config,NativeWindow& window):hud_(static_cast<HWND>(window.native_handle())),owner_(static_cast<HWND>(window.native_handle())){
  using namespace aibs::recording;const auto mode=config.record_encoder=="software"?EncoderMode::software:config.record_encoder=="nvenc"?EncoderMode::h264_nvenc:EncoderMode::automatic;
  RECT client{};if(!GetClientRect(owner_,&client)||client.right!=static_cast<LONG>(config.width)||client.bottom!=static_cast<LONG>(config.height)){error_="Recording client dimensions differ from requested physical target";return;}
  if(!encoder_.begin(config.record_ffmpeg,config.record_mp4,config.width,config.height,30,mode))error_=encoder_.report().error;
  started_=next_=Clock::now();
 }
 ~ChapterRecorder(){finish();}
 const std::string& failure()const noexcept{return error_;}
 void tick(Dx12Renderer& renderer,HWND body)noexcept{
  if(finished_||!error_.empty()||!encoder_.active())return;const auto now=Clock::now();if(now<next_)return;
  // Absolute slots advance from the preceding deadline; capture/write cost is
  // not added as another33ms delay. At most ONE live frame, no catch-up queue.
  constexpr auto period=std::chrono::nanoseconds(1000000000/30);do{next_+=period;}while(next_<=now);
  try{const auto capture_start=Clock::now();if(!renderer.capture_frame(frame_)){error_="Renderer has no presented frame during recording";finish();return;}capture_seconds_+=std::chrono::duration<double>(Clock::now()-capture_start).count();++captures_;gpu_readback_peak_=std::max(gpu_readback_peak_,renderer.stats().capture_active_readback_bytes);nonbackground_=std::max(nonbackground_,frame_.nonbackground_pixels);frame_peak_=std::max(frame_peak_,frame_.bgra.capacity());
   // capture_frame already includes the live main HUD/crosshair composed by
   // Dx12Renderer. Only the separate owned reading popup needs another layer;
   // preserve its actual full-text body without inventing a recorder layout.
   if(body){RECT bounds{};if(!GetClientRect(body,&bounds))throw std::runtime_error("Owned reading control has no rectangle");
    const int x=(static_cast<int>(frame_.width)-bounds.right)/2,y=(static_cast<int>(frame_.height)-bounds.bottom)/2;
    hud_.composite(frame_,body,x,y);++owned_hud_;overlay_peak_=std::max(overlay_peak_,hud_.resident_bytes());}
   (void)encoder_.submit(frame_,Clock::now());if(!encoder_.active()&&!encoder_.report().finished){error_=encoder_.report().error;finish();}
  }catch(const std::exception& failure){error_=failure.what();finish();}catch(...){error_="Unknown recorder failure";finish();}
 }
 void finish()noexcept{if(finished_)return;finished_=true;if(!encoder_.finish(std::chrono::milliseconds(5000))&&error_.empty())error_=encoder_.report().error;std::vector<std::byte>().swap(frame_.bgra);hud_.release();}
 void write_report(std::ostream& out)const{
  out<<",\"recording_main_hud_source\":\"already-composited-dx12-frame\",\"recording_additional_overlay\":\"owned-reading-body-only\"";
  const auto& r=encoder_.report();out<<",\"recording\":{\"requested\":true,\"finished\":"<<(r.finished?"true":"false")<<",\"failed\":"<<(!error_.empty()||r.failed?"true":"false")<<",\"error\":"<<quoted(error_.empty()?r.error:error_)<<",\"source\":\"owned-renderer-bgra-and-current-process-controls\",\"desktop_capture\":false,\"audio_capture\":false,\"original_audio_autoplay\":false,\"width\":"<<r.width<<",\"height\":"<<r.height<<",\"target_fps\":"<<r.target_fps<<",\"requested_encoder\":"<<quoted(r.requested_encoder)<<",\"selected_encoder\":"<<quoted(r.encoder)<<",\"hardware_probe_attempted\":"<<(r.hardware_probe_attempted?"true":"false")<<",\"hardware_probe_passed\":"<<(r.hardware_probe_passed?"true":"false")<<",\"fallback_reason\":"<<quoted(r.fallback_reason)<<",\"encoder_exit_code\":"<<r.encoder_exit_code<<",\"wall_seconds\":"<<r.wall_seconds<<",\"captures\":"<<captures_<<",\"frames_received\":"<<r.frames_received<<",\"frames_written\":"<<r.frames_written<<",\"dropped_for_rate\":"<<r.dropped_for_rate<<",\"missed_capture_slots\":"<<r.missed_capture_slots<<",\"maximum_write_seconds\":"<<r.maximum_write_seconds<<",\"capture_seconds\":"<<capture_seconds_<<",\"nonbackground_pixels_peak\":"<<nonbackground_<<",\"owned_hud_frames\":"<<owned_hud_<<",\"producer_frame_capacity_peak\":"<<frame_peak_<<",\"encoder_frame_capacity_peak\":"<<r.encoder_frame_capacity<<",\"encoder_frame_capacity_active\":"<<r.encoder_frame_capacity_active<<",\"overlay_instrumentation_capacity_peak\":"<<overlay_peak_<<",\"gpu_readback_instrumentation_peak\":"<<gpu_readback_peak_<<",\"encoder_sampled_private_bytes_peak\":"<<r.encoder_sampled_private_bytes_peak<<",\"encoder_peak_working_set_bytes\":"<<r.encoder_peak_working_set_bytes<<",\"timing\":"<<quoted(r.timing)<<",\"encoder_stderr\":"<<quoted(r.encoder_stderr)<<",\"timestamps\":[";
  bool first=true;for(const auto& timestamp:r.timestamps){if(!first)out<<',';first=false;out<<"{\"present_id\":"<<timestamp.present_id<<",\"capture_seconds\":"<<timestamp.capture_seconds<<",\"write_complete_seconds\":"<<timestamp.write_complete_seconds<<",\"stop_repeat\":"<<(timestamp.stop_repeat?"true":"false")<<'}';}out<<"]}";
 }
};
