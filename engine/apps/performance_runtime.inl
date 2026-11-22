// Optional managed diagnostic. All times below are actual steady_clock
// observations around normal frame()/Present work, never chapter proof dt.
#include "workshop_tour_path.hpp"
struct ChapterPerformanceOutcome {
 std::optional<FrameMeasurementSummary> measured;
 std::string error;
 double setup_wall_seconds=0;
 Vec3 start_feet{},end_feet{};
 double dropped_simulation_seconds=0;
 std::uint64_t setup_observations=0,foreground_observations=0,memory_valid_observations=0;
 bool last_foreground=false,last_minimized=false,last_reading=false,last_inspection=false,last_pending_save=false,last_exit_requested=false,last_memory_valid=false;
 unsigned long last_memory_error=0;
 std::uint64_t measured_reading_frames=0,measured_inspection_frames=0,measured_saving_frames=0;
 bool normal_player_close=false;
 controlled_motion::Coverage motion;
 Vec3 motion_first{},motion_second{};
 std::uint64_t motion_arrivals=0,motion_revision_before=0,motion_revision_after=0;
 performance_phases::Collector phases;
};
FrameObservation performance_observation(const ChapterLive& live,unsigned long& memory_error){
 FrameObservation out;const auto stats=live.renderer.stats();out.presented_frames=stats.frames;
 const auto hwnd=static_cast<HWND>(live.window.native_handle());RECT client{};
 if(GetClientRect(hwnd,&client)&&client.right>0&&client.bottom>0){out.width=static_cast<std::uint32_t>(client.right);out.height=static_cast<std::uint32_t>(client.bottom);}
 const auto foreground=GetForegroundWindow();
 // Gameplay includes the game's own reading/inspection UI and normal saves.
 // It still rejects foreign focus, minimization, resizing and failed memory.
 out.active=performance::context_ready(hwnd,foreground,live.config.performance_gameplay,live.window.minimized(),live.reading(),live.player.inspection_mode(),live.critical.has_value(),live.exit_requested);
 PROCESS_MEMORY_COUNTERS_EX memory{};memory.cb=static_cast<DWORD>(sizeof(memory));
 out.memory_valid=GetProcessMemoryInfo(GetCurrentProcess(),reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&memory),static_cast<DWORD>(sizeof(memory)))!=FALSE;
 memory_error=out.memory_valid?ERROR_SUCCESS:GetLastError();
 if(out.memory_valid){out.private_bytes=memory.PrivateUsage;out.working_set_bytes=memory.WorkingSetSize;out.working_set_peak_lifetime=memory.PeakWorkingSetSize;}
 out.gpu_content_bytes=stats.scene_active_gpu_bytes;return out;
}
ChapterPerformanceOutcome measure_chapter_window(ChapterLive& live){
 ChapterPerformanceOutcome out;out.start_feet=live.player.state().feet;const auto started=Clock::now();auto previous=started;
 // Observe genuine activation; diagnostics must never take desktop focus.
 std::unique_ptr<FrameMeasurement> measurement;
 constexpr double activation_grace_seconds=30;
 const auto& o=live.config;const bool controlled=o.performance_controlled_motion;
 if(controlled)require(live.owner->snapshot()->revision==0,"Controlled motion cannot use an existing progressed world");
 out.motion_revision_before=live.owner->snapshot()->revision;
 std::optional<controlled_motion::Shuttle> motion;std::uint64_t arrivals_before=0,phase_frame_index=0;bool motion_measuring=false;
 const FrameMeasurementConfig config{o.width,o.height,o.performance_warmup,o.performance_seconds,(o.performance_gameplay||controlled)?480000u:120000u,(o.performance_gameplay||controlled)?FrameMeasurementProfile::gameplay:FrameMeasurementProfile::stationary};
 for(;;){
  const auto now=Clock::now();const auto elapsed=std::chrono::duration<double>(now-previous).count();previous=now;
  const bool measuring_motion=controlled&&measurement&&measurement->state()==FrameMeasurementState::measuring;
  performance_phases::Sample phase;phase.frame_index=++phase_frame_index;phase.measuring=measuring_motion;
  if(controlled){phase.loop_started_seconds=std::chrono::duration<double>(now-started).count();phase.seconds[performance_phases::at(performance_phases::Phase::loop_gap)]=elapsed;}
  performance_phases::ScopedSample retained{controlled?&out.phases:nullptr,phase};
  const auto command_started=controlled?Clock::now():Clock::time_point{};
  if(measuring_motion&&!motion_measuring){arrivals_before=motion->arrivals();motion_measuring=true;}
  const auto before_motion=live.player.state();
  if(controlled){
   WindowInput command;command.active=performance::context_ready(static_cast<HWND>(live.window.native_handle()),GetForegroundWindow(),false,live.window.minimized(),live.reading(),live.player.inspection_mode(),live.critical.has_value(),live.exit_requested);
   if(command.active&&motion)command=motion->input(before_motion.feet,live.player.camera().yaw);
   live.controlled_performance_input=command;
  }
  const auto frame_started=controlled?Clock::now():Clock::time_point{};
  const bool frame_open=live.frame(elapsed);
  if(controlled){
   phase.frame_completed=true;phase.frame_started_seconds=std::chrono::duration<double>(live.controlled_frame_stages.started-started).count();
   phase.frame_finished_seconds=std::chrono::duration<double>(Clock::now()-started).count();
   phase.seconds[performance_phases::at(performance_phases::Phase::command)]=std::chrono::duration<double>(frame_started-command_started).count();
   for(std::size_t n=0;n<performance_phases::count;++n){
    phase.seconds[n]+=live.controlled_frame_stages.seconds[n];
    if(live.controlled_frame_stages.ends[n]!=Clock::time_point{})phase.phase_ended_seconds[n]=std::chrono::duration<double>(live.controlled_frame_stages.ends[n]-started).count();
   }
  }
  if(!frame_open){
   if(o.performance_gameplay&&measurement&&!std::filesystem::exists(o.stop_file)&&measurement->finish_gameplay()){
    out.measured=measurement->summary();out.normal_player_close=true;
   }else out.error="window_closed_before_measurement_complete";
   break;
  }
  if(measuring_motion){const bool invalid_before=out.motion.invalid;out.motion.observe(before_motion,live.player.state(),elapsed,live.controlled_performance_input.active&&live.controlled_performance_input.forward==1);retained.first_motion_fault=!invalid_before&&out.motion.invalid;}
  const auto queries_started=controlled?Clock::now():Clock::time_point{};
  unsigned long memory_error=0;const auto observation=performance_observation(live,memory_error);const auto observed=Clock::now();
  if(controlled){phase.observation_completed=true;phase.foreground_active=observation.active;phase.memory_valid=observation.memory_valid;
   phase.observation_finished_seconds=std::chrono::duration<double>(observed-started).count();phase.seconds[performance_phases::at(performance_phases::Phase::stats_memory)]=std::chrono::duration<double>(observed-queries_started).count();}
  if(observation.width!=o.width||observation.height!=o.height){out.error="physical_client_dimensions_differ_from_request";break;}
  if(!measurement){
   ++out.setup_observations;
   out.last_foreground=performance::context_ready(static_cast<HWND>(live.window.native_handle()),GetForegroundWindow(),o.performance_gameplay,false,false,false,false,false);
   out.foreground_observations+=out.last_foreground?1:0;
   out.memory_valid_observations+=observation.memory_valid?1:0;
   out.last_minimized=live.window.minimized();out.last_reading=live.reading();out.last_inspection=live.player.inspection_mode();
   out.last_pending_save=static_cast<bool>(live.critical);out.last_exit_requested=live.exit_requested;out.last_memory_valid=observation.memory_valid;
   out.last_memory_error=memory_error;
   if(observation.active&&observation.memory_valid&&(!controlled||live.player.state().grounded)){
    if(controlled){
     const auto from=live.player.state().feet;
     constexpr std::array<Vec3,4> offsets{{{-5,0,0},{5,0,0},{0,0,-5},{0,0,5}}};
     for(const auto delta:offsets){const Vec3 to{from.x+delta.x,from.y,from.z+delta.z};
      if(workshop_tour_path::clear(live.scene,from,{to,from},from.y-.2f)){motion.emplace(from,to);out.motion_first=from;out.motion_second=to;break;}}
     if(!motion){out.error="controlled_motion_has_no_collision_checked_shuttle";break;}
    }
    // Planning/physics queries are setup work, not a fabricated frame interval.
    const auto ready=controlled?Clock::now():observed;if(controlled)previous=ready;measurement=std::make_unique<FrameMeasurement>(config,ready,observation);out.setup_wall_seconds=std::chrono::duration<double>(ready-started).count();
   }
   else if(std::chrono::duration<double>(observed-started).count()>activation_grace_seconds){
    out.setup_wall_seconds=std::chrono::duration<double>(observed-started).count();
    out.error=!out.last_memory_valid?"process_memory_setup_unavailable":!out.last_foreground?"foreground_setup_unavailable":out.last_minimized?"window_minimized_during_setup":out.last_reading?"memory_panel_open_during_setup":out.last_inspection?"inspection_mode_during_setup":out.last_pending_save?"pending_save_during_setup":out.last_exit_requested?"exit_requested_during_setup":"readiness_changed_during_setup";break;}
  }else{
   if(measurement->state()==FrameMeasurementState::measuring){
    out.measured_reading_frames+=live.reading()?1:0;
    out.measured_inspection_frames+=live.player.inspection_mode()?1:0;
    out.measured_saving_frames+=(live.critical||!live.owner->state().saved)?1:0;
   }
   const auto sampler_started=controlled?Clock::now():Clock::time_point{};
   measurement->observe(observed,observation);
   if(controlled){const auto sampled=Clock::now();phase.sampler_finished_seconds=std::chrono::duration<double>(sampled-started).count();phase.seconds[performance_phases::at(performance_phases::Phase::sampler)]=std::chrono::duration<double>(sampled-sampler_started).count();}
   if(measurement->state()==FrameMeasurementState::failed){out.error=std::string(frame_measurement_error_name(measurement->error()));break;}
   if(measurement->state()==FrameMeasurementState::complete){out.measured=measurement->summary();break;}
  }
  if(std::chrono::duration<double>(observed-started).count()>activation_grace_seconds+o.performance_warmup+o.performance_seconds+12){out.error="bounded_measurement_deadline";break;}
 }
 out.end_feet=live.player.state().feet;out.dropped_simulation_seconds=live.player.state().dropped_seconds;
 if(controlled){
  out.motion_arrivals=motion?motion->arrivals()-arrivals_before:0;
  out.motion_revision_after=live.owner->snapshot()->revision;
  if(out.measured&&out.error.empty()&&!out.motion.qualifies(out.measured->wall_seconds,out.motion_arrivals))out.error="controlled_motion_coverage_incomplete";
  if(out.error.empty()&&out.motion_revision_after!=out.motion_revision_before)out.error="controlled_motion_changed_saved_outcomes";
  live.controlled_performance_input={};live.controlled_performance_input.active=false;
 }
 // This finite diagnostic closes through the normal durable close path. It
 // never credits a route or clears a pending outcome to satisfy a timer.
 if(!live.exit_requested){live.exit_requested=true;const auto close_deadline=Clock::now()+std::chrono::seconds(15);while(live.frame(0)){if(Clock::now()>close_deadline){out.error="saved_close_deadline";break;}std::this_thread::sleep_for(std::chrono::milliseconds(1));}}
 return out;
}
void write_performance_phase_sample(std::ostream& text,const performance_phases::Sample& sample){
 text<<"{\"frame_index\":"<<sample.frame_index<<",\"measuring\":"<<(sample.measuring?"true":"false")<<",\"frame_completed\":"<<(sample.frame_completed?"true":"false")<<",\"observation_completed\":"<<(sample.observation_completed?"true":"false")
  <<",\"foreground_active_observed\":"<<(sample.foreground_active?"true":"false")<<",\"memory_valid_observed\":"<<(sample.memory_valid?"true":"false")<<",\"loop_started_seconds\":"<<sample.loop_started_seconds<<",\"frame_started_seconds\":"<<sample.frame_started_seconds
  <<",\"frame_finished_seconds\":"<<sample.frame_finished_seconds<<",\"observation_finished_seconds\":"<<sample.observation_finished_seconds<<",\"sampler_finished_seconds\":"<<sample.sampler_finished_seconds<<",\"durations\":{";
 for(std::size_t n=0;n<performance_phases::count;++n){if(n)text<<',';text<<quoted(std::string(performance_phases::names[n]))<<':'<<sample.seconds[n];}
 text<<"},\"phase_ended_seconds\":{";for(std::size_t n=0;n<performance_phases::count;++n){if(n)text<<',';text<<quoted(std::string(performance_phases::names[n]))<<':'<<sample.phase_ended_seconds[n];}text<<"}}";
}
void write_performance_phase_context(std::ostream& text,const performance_phases::Context& context){
 text<<"{\"current\":";write_performance_phase_sample(text,context.current);text<<",\"preceding\":";if(context.have_preceding)write_performance_phase_sample(text,context.preceding);else text<<"null";text<<'}';
}
void write_chapter_performance(const ChapterLive& live,const ChapterPerformanceOutcome& outcome,std::uint64_t nonbackground){
 const auto& o=live.config;const auto stats=live.renderer.stats();const auto snapshot=live.owner->snapshot();
 std::ostringstream text;text<<std::setprecision(17)<<"{\"version\":1,\"status\":"<<quoted(outcome.measured&&outcome.error.empty()?"measured":"failed")<<",\"error\":"<<quoted(outcome.error)<<",\"completed_at\":"<<quoted(utc())
 <<",\"clock\":\"std::chrono::steady_clock / actual completed Present intervals\",\"synthetic_chapter_ticks_used_for_fps\":false,\"engine_requested_inference\":false,\"background_gpu_users\":\"unknown_not_enumerated_not_isolated\",\"recording_enabled\":false"
 <<",\"measurement_profile\":"<<quoted(o.performance_controlled_motion?"controlled-motion":o.performance_gameplay?"gameplay":"stationary")<<",\"normal_player_close\":"<<(outcome.normal_player_close?"true":"false")<<",\"saved_close_complete\":"<<(live.saved_close_complete?"true":"false")
 <<",\"gameplay_includes_reading_inspection_and_saving\":"<<(o.performance_gameplay?"true":"false")<<",\"measured_reading_frames\":"<<outcome.measured_reading_frames<<",\"measured_inspection_frames\":"<<outcome.measured_inspection_frames<<",\"measured_saving_frames\":"<<outcome.measured_saving_frames
 <<",\"scope\":{\"world_id\":"<<quoted(live.scope.world_id)<<",\"timeline_id\":"<<quoted(live.scope.timeline_id)<<"},\"content_fingerprint\":"<<quoted(live.content->fingerprint())<<",\"visible_revision\":"<<snapshot->revision<<",\"durable_revision\":"<<live.owner->state().durable_revision
 <<",\"requested_width\":"<<o.width<<",\"requested_height\":"<<o.height<<",\"warmup_min_seconds\":"<<o.performance_warmup<<",\"requested_measure_seconds\":"<<o.performance_seconds<<",\"setup_wall_seconds\":"<<outcome.setup_wall_seconds<<",\"hud_text_publications_lifetime\":"<<live.hud_text_publications
 <<",\"adapter\":"<<quoted(stats.adapter)<<",\"present_policy\":\"DX12 Present(1,0)\",\"gpu_debug_layer_observed\":"<<(stats.debug_layer?"true":"false")<<",\"gpu_debug_errors\":"<<stats.debug_errors<<",\"gpu_debug_warnings\":"<<stats.debug_warnings
 <<",\"setup_readiness\":{\"observations\":"<<outcome.setup_observations<<",\"foreground_observations\":"<<outcome.foreground_observations<<",\"memory_valid_observations\":"<<outcome.memory_valid_observations
 <<",\"last_foreground\":"<<(outcome.last_foreground?"true":"false")<<",\"last_minimized\":"<<(outcome.last_minimized?"true":"false")<<",\"last_reading\":"<<(outcome.last_reading?"true":"false")<<",\"last_inspection\":"<<(outcome.last_inspection?"true":"false")<<",\"last_pending_save\":"<<(outcome.last_pending_save?"true":"false")<<",\"last_exit_requested\":"<<(outcome.last_exit_requested?"true":"false")<<",\"last_memory_valid\":"<<(outcome.last_memory_valid?"true":"false")<<",\"memory_error\":"<<outcome.last_memory_error<<'}'
 <<",\"capture_nonbackground_pixels\":"<<nonbackground<<",\"capture_is_after_measurement\":true,\"cpu_asset_projection_bytes\":"<<(live.placed_assets?live.placed_assets->resident_bytes():0)
 <<",\"scene_gpu_accounting_excludes\":[\"swapchain\",\"depth buffers\",\"descriptors\",\"driver heaps\",\"temporary replacement uploads\"],\"process_memory_includes_instrumentation\":true"
 <<",\"sampling_note\":\"Per-frame memory queries and stats observation overhead are included. Private/working-set sampled maxima are not unsampled peaks. Peak working set is lifetime-wide.\""
 <<",\"player_feet_start\":["<<outcome.start_feet.x<<','<<outcome.start_feet.y<<','<<outcome.start_feet.z<<"],\"player_feet_end\":["<<outcome.end_feet.x<<','<<outcome.end_feet.y<<','<<outcome.end_feet.z<<"],\"dropped_simulation_seconds\":"<<outcome.dropped_simulation_seconds;
 if(o.performance_controlled_motion){const auto& c=outcome.motion;
  text<<",\"controlled_input\":true,\"os_focus_input_verified\":false,\"human_pacing_measured\":false,\"motion\":{\"policy\":\"full-requested-time;90-percent-moving-physics;95-percent-physics-coverage;3.5m-per-wall-second;two-arrivals\",\"physical_steps\":"<<c.physical_steps<<",\"moving_steps\":"<<c.moving_steps
   <<",\"physical_seconds\":"<<c.physical_seconds<<",\"moving_physical_seconds\":"<<c.moving_physical_seconds<<",\"horizontal_metres\":"<<c.horizontal_metres<<",\"commanded_wall_seconds\":"<<c.commanded_wall_seconds<<",\"invalid\":"<<(c.invalid?"true":"false")<<",\"arrivals\":"<<outcome.motion_arrivals
   <<",\"revision_before\":"<<outcome.motion_revision_before<<",\"revision_after\":"<<outcome.motion_revision_after<<",\"first\":["<<outcome.motion_first.x<<','<<outcome.motion_first.y<<','<<outcome.motion_first.z<<"],\"second\":["<<outcome.motion_second.x<<','<<outcome.motion_second.y<<','<<outcome.motion_second.z<<"]"
   <<",\"invalid_reason\":"<<quoted(controlled_motion::Coverage::reason(c.first_invalid))<<",\"invalid_observations\":"<<c.invalid_observations<<",\"first_invalid_observation\":"<<c.first_invalid_observation
   <<",\"first_invalid_elapsed\":";controlled_motion::write_diagnostic_real(text,c.first_invalid_elapsed);
  text<<",\"first_invalid_distance\":";controlled_motion::write_diagnostic_real(text,c.first_invalid_distance);
  text<<",\"first_ticks_before\":"<<c.first_ticks_before<<",\"first_ticks_after\":"<<c.first_ticks_after<<",\"first_dropped_before\":";controlled_motion::write_diagnostic_real(text,c.first_dropped_before);
  text<<",\"first_dropped_after\":";controlled_motion::write_diagnostic_real(text,c.first_dropped_after);
  text<<",\"rejected_elapsed_seconds\":";controlled_motion::write_diagnostic_real(text,c.rejected_elapsed_seconds);
  text<<",\"movement_counters_exclude_invalid_samples\":true,\"commanded_wall_includes_rejected_intervals\":true}";
  const auto& p=outcome.phases;
  text<<",\"phase_timings\":{\"clock\":\"steady_clock seconds relative to performance loop start\",\"causality\":\"loop_gap sampled at iteration start; frame N stall may cause frame N+1 dropped physics\",\"fixed_storage_bytes\":"<<sizeof(performance_phases::Collector)
   <<",\"outlier_capacity\":"<<performance_phases::Collector::capacity<<",\"outlier_threshold_seconds\":"<<performance_phases::Collector::outlier_seconds<<",\"observations\":"<<p.observations<<",\"invalid_samples\":"<<p.invalid_samples<<",\"outlier_count\":"<<p.outlier_count<<",\"maxima\":{";
  for(std::size_t n=0;n<performance_phases::count;++n){if(n)text<<',';text<<quoted(std::string(performance_phases::names[n]))<<':'<<p.maxima[n];}
  text<<"},\"outliers\":[";for(std::size_t n=0;n<p.retained;++n){if(n)text<<',';write_performance_phase_context(text,p.outliers[n]);}
  text<<"],\"first_motion_fault_context\":";if(p.have_motion_fault)write_performance_phase_context(text,p.first_motion_fault);else text<<"null";text<<'}';
 }
 if(outcome.measured){const auto& m=*outcome.measured;text<<",\"actual_client_width\":"<<m.width<<",\"actual_client_height\":"<<m.height<<",\"measured_wall_seconds\":"<<m.wall_seconds<<",\"frame_count\":"<<m.frame_count<<",\"actual_present_delta\":"<<m.presented_frame_delta<<",\"fps\":"<<m.frames_per_second
 <<",\"frame_ms\":{\"mean\":"<<m.mean_ms<<",\"p50\":"<<m.p50_ms<<",\"p95\":"<<m.p95_ms<<",\"p99\":"<<m.p99_ms<<"},\"private_bytes\":{\"start\":"<<m.private_start<<",\"end\":"<<m.private_end<<",\"maximum_sampled\":"<<m.private_peak_sampled<<"},\"working_set_bytes\":{\"start\":"<<m.working_set_start<<",\"end\":"<<m.working_set_end<<",\"maximum_sampled\":"<<m.working_set_peak_sampled<<",\"lifetime_peak\":"<<m.working_set_peak_lifetime<<"},\"scene_content_gpu_bytes\":{\"start\":"<<m.gpu_content_start<<",\"end\":"<<m.gpu_content_end<<",\"maximum_sampled\":"<<m.gpu_content_peak_sampled<<"},\"instrumentation_owned_bytes\":"<<m.instrumentation_bytes;}
 if(outcome.measured){const auto& m=*outcome.measured;text<<",\"long_frames\":{\"over16_67ms\":"<<m.frames_over_16_67ms<<",\"over33_33ms\":"<<m.frames_over_33_33ms<<",\"over50ms\":"<<m.frames_over_50ms<<'}';}
 const auto ids=live.ids();const auto& progress=chapter_record(*snapshot,ids.progress);
 text<<",\"opening_outcomes\":{\"first_route\":"<<quoted(chapter_text(progress,"first_route"))<<",\"shelter_secured\":"<<(chapter_flag(progress,"shelter_secured")?"true":"false")<<",\"pencil_visited\":"<<(chapter_flag(progress,"pencil_visited")?"true":"false")<<'}';
 text<<"}\n";const auto payload=text.str();auto temporary=o.performance_report;temporary+=L".creating-"+wide(new_uuid());{std::ofstream file(temporary,std::ios::binary);file.write(payload.data(),static_cast<std::streamsize>(payload.size()));file.close();require(file.good(),"Cannot write bounded performance report");}
 require(MoveFileExW(temporary.c_str(),o.performance_report.c_str(),MOVEFILE_WRITE_THROUGH)!=FALSE,"Cannot publish a new performance report without replacing an existing file");
}
