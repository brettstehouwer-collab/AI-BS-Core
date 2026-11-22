// Actual native window/input/control acceptance for authored reading stops.
// No gameplay changes, teleports or synthetic outcome records originate here.
void chapter_opening_controls(ChapterLive& live){
 const auto check=[&](bool value,const char* why){++live.proof_opening_checks;require(value,why);};
 check(live.content&&live.opening&&live.opening->count()==7,"Opening proof requires all seven authored inspection stops");
 const auto initial=live.owner->snapshot();const auto saved=live.owner->state();const auto chapter_ids=live.ids();
 check(!chapter_flag(chapter_record(*initial,chapter_ids.progress),"shelter_secured"),"Reserve nook must not complete the shelter objective");
 const auto found=std::find_if(live.scene.objects.begin(),live.scene.objects.end(),[](const auto& o){return o.name=="Controller and turning";});
 check(found!=live.scene.objects.end(),"Opening controller fixture is missing");const auto target=*found;
 check(live.opening->find(target.persistent_id)!=nullptr,"Controller must own its bounded inspection triple");
 check(live.opening->resident_bytes()<=512u*1024u,"Opening owned capacities must fit charged panel reserve");
 const auto game=static_cast<HWND>(live.window.native_handle());
 const auto tick=[&](double elapsed=0.){require(live.frame(elapsed),"Opening proof window unexpectedly closed");};
 const auto open=[&]{aim(live.player,target.center);key(live.window,'E');tick();check(live.reading(),"Actual E must open the nearby owned reading panel");};
 chapter_walk(live,-37,-25);chapter_walk(live,-37,-29);
 aim(live.player,target.center);key(live.window,'E');tick();
 check(!live.reading(),"An unselectable physical nook wall must block inspection through it");
 check(live.owner->snapshot()->components==initial->components,"Occluded reading must not invent quest credit");
 chapter_walk(live,-37,-25);chapter_walk(live,-34.7f,-25);chapter_walk(live,-34.7f,-27);
 aim(live.player,target.center);SendMessageW(game,WM_KEYDOWN,'W',0);key(live.window,'E');tick();
 check(live.reading(),"Aimed E must open inspection through the real native frame dispatch");
 const auto body=live.opening->panel().body_handle();
 check(IsWindow(body)&&IsWindowVisible(live.opening->panel().native_handle()),"Actual native reading edit/window must exist and be visible");
 const auto text=live.opening->panel().body_text();
 check(text.find(L"Adam")!=std::wstring::npos&&text.find(L"Echos Within")!=std::wstring::npos,"Native reading must show personal text and explicit memoir attribution");
 auto capture=live.config.capture;capture+=L".opening-panel.bmp";
 check(live.opening->panel().capture_body(capture),"Native read-only inspection glyphs must actually render");
 check(text.find(L"XML paragraph")==std::wstring::npos&&!live.opening->panel().source_visible(),"Default story view must keep technical provenance behind Memory source");
 SendMessageW(live.opening->panel().source_handle(),BM_CLICK,0,0);tick();
 check(live.reading()&&live.opening->panel().source_visible(),"Actual Memory source button must remain inside paused reading");
 const auto provenance=live.opening->panel().body_text();
 check(provenance.find(live.opening->panel().source_attribution())!=std::wstring::npos&&provenance.find(L"Echos Within")!=std::wstring::npos,"Actual source disclosure must render exact retained memoir attribution");
 auto source_capture=capture;source_capture+=L".source.bmp";
 check(live.opening->panel().capture_body(source_capture),"Actual provenance glyphs must render on the owned reading surface");
 const auto feet=live.player.state().feet;const auto hazard_tick=live.clock.tick();
 const auto animation=live.guide_presentation?live.guide_presentation->animation_seconds():0;
 const auto guide_feet=live.companion->state().guide->character.feet;
 const auto intent=live.companion->state().saved;
 for(const auto code:std::array<WPARAM,7>{VK_F6,VK_F7,VK_F8,'B',VK_DELETE,VK_F2,'V'}){key(live.window,code);tick(.25);}
 SendMessageW(game,WM_KEYDOWN,VK_CONTROL,0);key(live.window,'Y');key(live.window,'Z');SendMessageW(game,WM_KEYUP,VK_CONTROL,0);tick(.25);
 check(live.reading()&&live.player.state().feet==feet,"Reading must pause BS even while W is held and gameplay keys arrive");
 check(live.clock.tick()==hazard_tick,"Reading must freeze the actual hazard clock");
 check(live.companion->state().guide->character.feet==guide_feet,"Reading must suspend Adam's physical movement");
 check(!live.guide_presentation||live.guide_presentation->animation_seconds()==animation,"Reading must freeze the actual articulated pose clock");
 check(live.companion->state().saved.intent==intent.intent&&live.companion->state().saved.waiting_anchor==intent.waiting_anchor,"Reading must reject Follow/Wait/Recall changes");
 check(live.owner->snapshot()->revision==initial->revision&&live.owner->snapshot()->sequence==initial->sequence&&live.owner->snapshot()->components==initial->components,"Reading/build/choice keys must never change chapter history");
 check(live.owner->state().durable_revision==saved.durable_revision,"Optional reading must never add durable writes");
 check(!live.original_memory||!live.original_memory->snapshot().asset,"Reading must never select or autoplay the original recording");
 // Release the actually held W in the focused edit, then use its real button.
 SendMessageW(live.opening->panel().source_handle(),WM_KEYUP,'W',0);tick(.25);SendMessageW(live.opening->panel().continue_handle(),BM_CLICK,0,0);tick(.05);
 check(!live.reading(),"Actual Continue button must close only the optional panel");
 const auto after=live.player.state().feet;
 check(std::hypot(after.x-feet.x,after.z-feet.z)<.001f,"W released inside the edit must not remain held after Continue");
 check(live.clock.tick()>hazard_tick,"Leaving reading must resume active hazard time without catch-up");
 open();const auto read_head=live.owner->snapshot()->revision;
 SendMessageW(live.opening->panel().body_handle(),WM_KEYDOWN,VK_ESCAPE,0);tick();
 check(!live.reading()&&IsWindow(game),"Actual Escape in reading must close the panel without closing the game");
 check(live.owner->snapshot()->revision==read_head,"Escape must not create gameplay history");
 open();const auto expected_reload=live.reloads+1;
 // Route the actual focused edit F9; do not call the reload implementation.
 SendMessageW(live.opening->panel().source_handle(),BM_CLICK,0,0);tick();
 const auto focused=live.opening->panel().source_handle();SendMessageW(focused,WM_KEYDOWN,VK_F9,0);SendMessageW(focused,WM_KEYUP,VK_F9,0);tick();
 check(live.reloads==expected_reload&&!live.reading(),"Focused-edit F9 must reload the chapter and discard its ephemeral reading selection");
 check(live.owner->snapshot()->revision==initial->revision&&live.owner->snapshot()->components==initial->components,"Reload must preserve actual recorded state without persisting reading/animation frames");
 check(live.companion->state().saved.intent==intent.intent&&live.companion->state().saved.waiting_anchor==intent.waiting_anchor,"Reload after reading must preserve Adam's saved intent and anchor");
 check(live.opening->count()==7&&live.opening->resident_bytes()<=512u*1024u,"Reload must reconstruct a valid bounded owned inspection catalog");
 check(!live.original_memory||live.original_memory->snapshot().playback.owned_pcm_bytes==0,"Reading/reload must leave optional PCM unplayed and unallocated");
 check(live.guidance_gestures>0,"Actual native companion must schedule authored situational guidance gestures");
 check(live.renderer.stats().debug_errors==0&&live.renderer.stats().debug_warnings==0,"Opening native proof must keep DX12 diagnostics clean");
 live.proof_opening_controls=true;
}
