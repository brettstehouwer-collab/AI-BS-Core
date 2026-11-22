// Opt-in managed-Play proof. It refuses every nonzero source PCM byte before
// an explicit key/button starts a muted synthetic recording.
void chapter_memory_controls(ChapterLive& live){
 require(live.content&&live.original_memory,"Memory controls proof requires authored memory stations");
 auto& media=*live.original_memory;const auto& definition=live.content->definition();
 require(!definition.memories.empty(),"Synthetic memory fixture has no station");
 const auto check=[&](bool value,const char* message){++live.proof_memory_checks;require(value,message);};
 const auto& binding=definition.memories.front();const auto& closure=live.placed_assets->asset_closure();
 const auto* source=std::get_if<AudioAsset>(&closure->require(binding.audio,FirstBootDependencyKind::audio).payload);
 check(source&&source->sample_rate==44100&&source->channels==2,"Proof requires unchanged44.1kHz stereo source");
 check(source->caption_review==AudioCaptionReview::checked&&source->captions.size()>=2&&source->captions.front().start_frame==0&&source->captions.front().end_frame>=22050,"Proof requires checked synthetic captions with a half-second first interval");
 check(std::all_of(source->pcm.begin(),source->pcm.end(),[](std::byte value){return value==std::byte{0};}),"Memory proof refuses original or non-silent PCM");
 const auto initial=live.owner->snapshot();const auto durable=live.owner->state();
 check(live.region(*initial,binding.position)=="jenison","Synthetic no-quest-credit proof requires a nook station inside Jenison");
 check(!media.snapshot().asset&&media.snapshot().playback.generation==0,"Binding content must never start optional audio");
 const auto board=chapter_board(live);const auto position=binding.position;bool clear=false;
 for(const auto offset:std::array<Vec3,8>{{{0,0,-2},{-2,0,0},{2,0,0},{0,0,2},{-1.5f,0,-1.5f},{1.5f,0,-1.5f},{-1.5f,0,1.5f},{1.5f,0,1.5f}}}){
  try{live.player.reset({position.x+offset.x,board.y+.05f,position.z+offset.z});clear=true;break;}catch(const std::invalid_argument&){}
 }
 check(clear,"Synthetic memory station needs a collision-checked reachable approach");
 live.observed_region=live.region(*live.owner->snapshot(),live.player.state().feet);live.entry_previous.reset();chapter_settle(live);
 const Vec3 target{position.x,position.y+.45f,position.z};aim(live.player,target);
 check(chapter_press(live,target),"E selection must be a real station interaction");
 auto state=media.snapshot();check(state.asset&&state.station_id()==binding.entity_id&&state.playback.state==AudioPlaybackState::stopped,"Actual E selects an exact audio station without playing");
 check(state.asset.get()==source&&state.playback.volume==0,"Runtime must alias admitted PCM and mute synthetic proof");
 check(state.resident_bytes<=memory_playback_maximum_resident_bytes,"Current source plus GPU content budget exceeds profile");
 const auto tick=[&]{require(live.frame(0,false),"Memory proof window closed");};
 const auto wait=[&](auto predicate,const char* message){const auto end=Clock::now()+std::chrono::seconds(4);while(!predicate()&&Clock::now()<end){tick();std::this_thread::sleep_for(std::chrono::milliseconds(3));}check(predicate(),message);};
 key(live.window,'P');tick();wait([&]{return media.snapshot().playback.played_frames>=441;},"Actual P must start XAudio2 source frames");state=media.snapshot();
 check(state.caption_index==0&&state.playback.sample_rate==44100&&state.playback.channels==2,"Checked caption must follow actual original-rate source frames");
 check(media.panel().caption_text().find(wide(source->captions.front().text))!=std::wstring::npos,"Checked caption must exist in the actual native read-only transcript");
 check(has_status(live.window,L"P Play/Resume"),"Native HUD must explain explicit PC audio controls");
 key(live.window,'O');tick();state=media.snapshot();const auto manually_paused=state.playback.played_frames;
 check(state.playback.state==AudioPlaybackState::paused,"Actual O pauses the selected recording");
 auto caption_capture=live.config.capture;caption_capture+=L".memory-caption.bmp";check(media.panel().capture_caption(caption_capture),"Actual native checked-caption glyph readback must render");
 std::this_thread::sleep_for(std::chrono::milliseconds(130));tick();check(media.snapshot().playback.played_frames==manually_paused&&media.snapshot().caption_index==0,"Manual pause holds source clock and caption");
 key(live.window,VK_F2);tick();key(live.window,VK_F2);tick();check(media.snapshot().playback.state==AudioPlaybackState::paused,"Inspection must not restart a manually paused recording");
 SendMessageW(media.panel().play_handle(),BM_CLICK,0,0);tick();
 wait([&]{return media.snapshot().playback.played_frames>manually_paused;},"Native Play button must resume source frames");
 key(live.window,VK_F2);tick();state=media.snapshot();live.proof_memory_paused_frame=state.playback.played_frames;
 check(state.game_paused&&state.resume_on_game_resume&&state.playback.state==AudioPlaybackState::paused,"Inspection automatically pauses only a playing recording");
 std::this_thread::sleep_for(std::chrono::milliseconds(130));tick();check(media.snapshot().playback.played_frames==live.proof_memory_paused_frame,"Game pause must hold the real recording clock");
 key(live.window,VK_F2);tick();wait([&]{return media.snapshot().playback.played_frames>live.proof_memory_paused_frame;},"Leaving inspection resumes only remembered active playback");live.proof_memory_resumed_frame=media.snapshot().playback.played_frames;
 key(live.window,VK_F2);tick();key(live.window,'K');tick();key(live.window,VK_F2);tick();
 check(media.snapshot().playback.state==AudioPlaybackState::stopped&&!media.snapshot().resume_on_game_resume&&!media.snapshot().caption_index,"Manual K during game pause prevents later automatic replay");
 // Focus suspension must clear queued presses; the normal platform input is
 // deliberately used rather than a controller-only fake.
 SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_ACTIVATEAPP,FALSE,0);key(live.window,'P');tick();
 SendMessageW(static_cast<HWND>(live.window.native_handle()),WM_ACTIVATEAPP,TRUE,0);tick();
 check(media.snapshot().playback.state==AudioPlaybackState::stopped,"Inactive window must discard attempted Play");
 key(live.window,'P');tick();wait([&]{return media.snapshot().playback.played_frames>=441;},"Restart explicit Play before reload");
 key(live.window,VK_F9);tick();check(live.reloads==1&&media.snapshot().playback.state==AudioPlaybackState::stopped&&media.snapshot().playback.played_frames==0,"F9 reload stops audio and never restores a saved playback cursor");
 check(live.owner->snapshot()->revision==initial->revision&&live.owner->snapshot()->sequence==initial->sequence&&live.owner->snapshot()->components==initial->components,"Memory controls must never invent quest credit, frame history or gameplay outcomes");
 check(live.owner->state().durable_revision==durable.durable_revision,"Memory controls must not add durable writes");
 for(const auto code:{VK_F6,VK_F7,VK_F8}){key(live.window,static_cast<WPARAM>(code));const auto input=live.window.input();check(code==VK_F6?input.companion_follow:code==VK_F7?input.companion_wait:input.companion_recall,"Owned audio routing must preserve Follow/Wait/Recall key edges");}
 check(media.snapshot().playback.owned_pcm_bytes==0&&!media.snapshot().playback.source_voice,"Stopped/reloaded playback must release its PCM and voices");
 live.proof_memory_controls=true;
}
