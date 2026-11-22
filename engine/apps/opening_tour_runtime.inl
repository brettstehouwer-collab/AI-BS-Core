// Actual native W/E/Build/button route. Proof dt and real walkthrough time are
// explicitly separate; neither is represented as an8–12minute human playtest.
OpeningTourTargets load_opening_tour(const ChapterLive& live){
 require(live.content&&live.opening,"Tour requires authored inspection content");std::ifstream input(live.config.tour_bindings,std::ios::binary);require(input.good(),"Cannot open explicit tour sidecar");
 std::array<unsigned char,4097> bytes{};input.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));require(!input.bad()&&input.gcount()>0&&input.gcount()<=4096,"Tour sidecar exceeds its bounded canonical input");return decode_opening_tour(std::span(bytes.data(),static_cast<std::size_t>(input.gcount())),*live.content);
}
void opening_tour_read(ChapterLive& live,const OpeningTourTargets& targets,OpeningTourRole role,Vec3 approach){
 const auto index=static_cast<std::size_t>(role);const auto& id=targets.ids.at(index);const auto* entry_ptr=live.opening->find(id);require(entry_ptr!=nullptr,"Tour lost its owned inspection fixture; regenerate bindings");OpeningTourReadGuard guard(*entry_ptr,live.reloads);const auto& entry=guard.expected();
 const auto board=chapter_board(live);chapter_walk(live,approach.x-board.x,approach.z-board.z);guard.after_walk(live.reloads);
 OpeningTourReadProof proof;proof.role=role;proof.id=id;proof.title=entry.title;proof.text=entry.text;proof.source=entry.source;
 const auto before=live.owner->snapshot();proof.revision_before=before->revision;proof.sequence_before=before->sequence;
 const bool pressed=chapter_press(live,entry.center);
 if(!pressed||!live.reading()){
  const auto feet=live.player.state().feet;const auto camera=live.player.camera();
  std::ostringstream failure;
  failure<<std::setprecision(9)<<"Actual E did not open the targeted tour panel: "<<opening_tour_role_name(role)
   <<" notice="<<quoted(chapter_aim::bounded(live.notice,192))
   <<" feet=("<<feet.x<<','<<feet.y<<','<<feet.z<<") camera=("<<camera.position.x<<','<<camera.position.y<<','<<camera.position.z
   <<") yaw="<<camera.yaw<<" pitch="<<camera.pitch<<" third_person="<<(live.player.third_person()?"true":"false")
   <<" inspection="<<(live.player.inspection_mode()?"true":"false")<<" pressed="<<(pressed?"true":"false")<<" reading="<<(live.reading()?"true":"false");
  throw std::runtime_error(failure.str());
 }
 guard.reading(live.reloads,live.opening->selection(),live.reading());const auto actual=live.opening->panel().body_text();require(actual.find(wide(entry.text))!=std::wstring::npos&&live.opening->panel().source_attribution()==wide(entry.source),"Actual native panel lost target text or owned source attribution");
 proof.glyph=live.config.capture;proof.glyph+=L".tour-"+wide(std::string(opening_tour_role_name(role)))+L".bmp";require(live.opening->panel().capture_body(proof.glyph),"Actual tour glyph readback is blank");
 const auto feet=live.player.state().feet;const auto tick=live.clock.tick();
 if(live.config.walkthrough){const auto until=Clock::now()+std::chrono::duration<double>(live.config.walkthrough_read_seconds);while(Clock::now()<until){require(live.tour_frame(0),"Walkthrough closed while reading");require(live.opening!=nullptr,"Tour opening adapter disappeared");guard.reading(live.reloads,live.opening->selection(),live.reading());}}
 else for(unsigned frame=0;frame<8;++frame){require(live.tour_frame(1./60,frame==7),"Tour proof closed while reading");require(live.opening!=nullptr,"Tour opening adapter disappeared");guard.reading(live.reloads,live.opening->selection(),live.reading());}
 require(live.player.state().feet==feet&&live.clock.tick()==tick,"Reading advanced body/hazard rather than pausing");
 guard.reading(live.reloads,live.opening->selection(),live.reading());SendMessageW(live.opening->panel().continue_handle(),BM_CLICK,0,0);require(live.tour_frame(0)&&!live.reading(),"Actual Continue failed to return to BS");guard.after_walk(live.reloads);
 const auto after=live.owner->snapshot();proof.revision_after=after->revision;proof.sequence_after=after->sequence;
 require(proof.revision_before==proof.revision_after&&proof.sequence_before==proof.sequence_after,"Inspection fabricated durable quest credit");
 require(live.tour_reads.size()<opening_tour_stop_count,"Tour proof array exceeded seven stops");live.tour_reads.push_back(std::move(proof));
}
#include "workshop_tour_runtime.inl"
void chapter_opening_tour(ChapterLive& live){
 require(live.owner->snapshot()->revision==0&&live.observed_region=="jenison","Tour requires a fresh isolated chapter timeline; existing saves are never reset");
 const auto targets=load_opening_tour(live);const auto board=chapter_board(live);
 if(first_boot_content_workshop_binding(live.content->definition())){workshop_tour::run(live,targets);return;}
 const auto target=[&](OpeningTourRole role)->const OpeningInspection&{const auto* entry=live.opening->find(targets.ids.at(static_cast<std::size_t>(role)));require(entry!=nullptr,"Tour role is no longer owned");return *entry;};
 const auto approach=[&](OpeningTourRole role,float x,float z){const auto center=target(role).center;return Vec3{center.x+x,board.y+.2f,center.z+z};};
 opening_tour_read(live,targets,OpeningTourRole::controller,approach(OpeningTourRole::controller,0,2));
 chapter_walk(live,-32,-26);opening_tour_read(live,targets,OpeningTourRole::truck,approach(OpeningTourRole::truck,0,1.8f));
 chapter_walk(live,-32,-25);chapter_walk(live,-37,-25);chapter_walk(live,-37,-10);
 chapter_walk(live,target(OpeningTourRole::diagnostic).center.x-board.x,-10);opening_tour_read(live,targets,OpeningTourRole::diagnostic,approach(OpeningTourRole::diagnostic,0,-2));
 chapter_walk(live,-37,-10);opening_tour_read(live,targets,OpeningTourRole::bypass,approach(OpeningTourRole::bypass,0,-2));
 chapter_walk(live,-37,-10);chapter_walk(live,-37,-6.5f);chapter_walk(live,-35.5f,-6.5f);
 const auto ids=live.ids();require(chapter_press(live,chapter_target(live,ids.fault,"Downstream power fault")),"Tour fault diagnosis failed");chapter_walk(live,-35.5f,-5.2f);require(chapter_press(live,chapter_target(live,ids.fault,"Isolation switch")),"Tour isolation failed");
 if(live.config.tour_route=="repair"){
  chapter_walk(live,-33,-5.2f);require(chapter_press(live,chapter_target(live,ids.fault,"Downstream power fault")),"Tour repair failed");chapter_walk(live,-35.5f,-5.2f);require(chapter_press(live,chapter_target(live,ids.fault,"Isolation switch")),"Tour feed reconnection failed");chapter_walk(live,-37,-5.2f);chapter_walk(live,-37,1.9f);chapter_walk(live,-33,1.9f);require(chapter_press(live,chapter_target(live,ids.main_door)),"Tour main door failed");chapter_walk(live,-33,6);
 }else{
  chapter_walk(live,-42,-5.2f);const auto socket=chapter_point(chapter_record(*live.owner->snapshot(),ids.fault),"socket_");require(chapter_press(live,{socket.x,socket.y+1,socket.z},'B'),"Tour real relay build failed");std::string relay;
  for(const auto& node:chapter_nodes(*live.owner->snapshot()).components)if(chapter_flag(node,"alive")&&chapter_number(node,"firstboot.kind")==6&&std::hypot(chapter_number(node,"x")-socket.x,chapter_number(node,"z")-socket.z)<.1)relay=node.entity_id;
  require(!relay.empty()&&chapter_press(live,chapter_target(live,relay)),"Tour relay connection failed");chapter_walk(live,-39.5f,-5.2f);chapter_walk(live,-39.5f,1.9f);chapter_walk(live,-41,1.9f);require(chapter_press(live,chapter_target(live,ids.service_door)),"Tour service door failed");chapter_walk(live,-41,6);chapter_walk(live,-41,8);chapter_walk(live,-37,8);chapter_walk(live,-33,8);
 }
 require(chapter_text(chapter_record(*live.owner->snapshot(),ids.progress),"first_route")==live.config.tour_route,"Tour did not earn its declared actual doorway route");
 opening_tour_read(live,targets,OpeningTourRole::seats,approach(OpeningTourRole::seats,-2,0));
 chapter_walk(live,-37,8);opening_tour_read(live,targets,OpeningTourRole::shelter,approach(OpeningTourRole::shelter,0,-1.6f));
 chapter_walk(live,-37,8);chapter_walk(live,-37,10.7f);require(chapter_press(live,chapter_target(live,ids.pencil_door)),"Tour Pencil door failed");chapter_walk(live,-37,15);chapter_walk(live,-37,17);
 opening_tour_read(live,targets,OpeningTourRole::pencil,approach(OpeningTourRole::pencil,2.2f,0));
 chapter_walk(live,-37,15);require(chapter_flag(chapter_record(*live.owner->snapshot(),ids.progress),"pencil_visited"),"Tour never physically reached Pencil Room");
 require(live.tour_reads.size()==opening_tour_stop_count,"Tour did not read all seven owned stops");
 if(live.companion){const auto deadline=Clock::now()+std::chrono::seconds(20);bool arrived=false;for(unsigned step=0;step<(live.config.walkthrough?12000u:1200u);++step){const auto guide=live.companion->state();if(guide.guide&&!guide.recall_required&&std::hypot(guide.guide->character.feet.x-live.player.state().feet.x,guide.guide->character.feet.z-live.player.state().feet.z)<3.5f){arrived=true;break;}require(!live.config.walkthrough||Clock::now()<deadline,"Adam could not follow the real-time route; no automatic Recall substituted");require(live.tour_frame(1./60,step%16==0),"Tour companion catch-up closed");}require(arrived,"Adam did not physically catch up through the tour doors");}
 live.proof_opening_tour=true;if(live.companion)live.proof_companion_route=true;
}
