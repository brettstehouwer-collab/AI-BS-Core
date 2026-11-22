#include <aibs/first_boot_content.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {
void require(bool value,const char* why){if(!value)throw std::runtime_error(why);}
template<class F> void rejects(F action,const char* why){bool caught=false;try{action();}catch(const std::exception&){caught=true;}require(caught,why);}
ComponentRecord& record(FirstBootContentDefinition& d,const char* type,const char* role=""){
 for(auto& r:d.initial_records)if(r.type_id==type&&(!*role||std::get<std::string>(r.fields.at("role"))==role))return r;throw std::runtime_error("Definition record missing");
}
GameplayStoreRecovery state(const FirstBootContent& content){const auto b=first_boot_content_baseline(content);return {{"content-test",content.definition().world_id,"main",new_uuid(),GameplayContext::temporary_play},b.revision,b.sequence,b.components};}
GameplayStoreRecovery apply(GameplayStoreRecovery s,const GameplayChangeBatch& b){for(const auto& d:b.deltas){auto p=std::find_if(s.components.begin(),s.components.end(),[&](const auto& r){return r.entity_id==d.component.entity_id;});if(p==s.components.end())s.components.push_back(d.component);else *p=d.component;}s.revision=b.revision;s.sequence=b.events.back().sequence;return s;}
FirstBootChapterActor actor(float x,float z){FirstBootChapterActor a;a.previous_feet=a.feet={x,.2f,z};return a;}
}
int wmain(int argc,wchar_t** argv){
 try {
  CreatorSession source(first_boot_schema(),"content-test","main");require(seed_first_boot(source).ok,"Seed native hardware");
  const auto original=FirstBootContent::from_template(source);auto edited=original.definition();++edited.revision;
  auto& door=record(edited,"firstboot.Door","main");door.fields["x"]=std::get<double>(door.fields.at("x"))+.5;
  auto& fault=record(edited,"firstboot.PowerFault");fault.fields["socket_x"]=-41.5;
  auto& npc=record(edited,"firstboot.NPCQuest");npc.fields["x"]=-39.5;
  edited.hints["adam.danger"]="Authored Adam hint: Step clear. We can work from what still responds.";
  const auto preview=first_boot_content_preview(original,edited);require(preview.status==FirstBootContentPreviewStatus::new_play_branch&&preview.render_rebuild&&preview.collision_rebuild&&preview.power_dependencies&&preview.quest_dependencies,"Preview reports actual dependencies and branch requirement");
  require(!preview.save_compatible&&preview.candidate.has_value(),"Changed content cannot silently reuse old save");
  const auto content=*preview.candidate;auto before=state(content);first_boot_content_validate(before,content);
  require(first_boot_content_hint(before,actor(-33,-3),content)==edited.hints.at("adam.danger"),"Authored Adam cue comes from immutable content");
  const auto scene=first_boot_content_scene(before,content);
  require(std::any_of(scene.objects.begin(),scene.objects.end(),[&](const auto& o){return o.persistent_id==door.entity_id&&o.center.x==-32.5f;}),"Moved authored door reaches actual scene");
  rejects([&]{first_boot_chapter_validate(before);},"Legacy adapter must not accept content-bound save");
  rejects([&]{first_boot_content_validate(before,original);},"Wrong content version cannot reinterpret save");
  auto a=actor(-35.5f,-3);FirstBootChapterCommand isolate;isolate.action=FirstBootChapterAction::set_isolation;isolate.operation_id="content-isolate";
  const auto batch=first_boot_content_action(before,isolate,a,content);require(batch.has_value(),"Content-aware isolation action");
  auto after=apply(before,*batch);first_boot_content_rules(before,after,*batch,a,content);
  std::vector<GameplayChangeBatch> batches{*batch};
  auto accept=[&](const GameplayChangeBatch& b,const FirstBootChapterActor& body){auto next=apply(after,b);first_boot_content_rules(after,next,b,body,content);after=std::move(next);batches.push_back(b);};
  auto act=[&](FirstBootChapterAction action,FirstBootChapterActor body,std::string target="",std::string relay="",bool enabled=true){FirstBootChapterCommand c;c.action=action;c.target_id=std::move(target);c.relay_id=std::move(relay);c.enabled=enabled;const auto b=first_boot_content_action(after,c,body,content);require(b.has_value(),"Expected real content action");accept(*b,body);};
  auto socket_actor=actor(-41.5f,-5);const auto built=first_boot_content_build(after,{-41.5f,1.2f,-3},socket_actor,content,"content-build");accept(built,socket_actor);const auto relay=std::get<ConstructionOutcome>(built.events.front().payload).entity_id;
  act(FirstBootChapterAction::connect_bypass,socket_actor,"",relay);
  act(FirstBootChapterAction::decline_caretaker,actor(-39.5f,6.5f));
  act(FirstBootChapterAction::disconnect_bypass,socket_actor);
  const auto removed=first_boot_content_dismantle(after,relay,socket_actor,content,"content-dismantle");require(removed.has_value(),"Content relay dismantle");accept(*removed,socket_actor);
  act(FirstBootChapterAction::repair_fault,actor(-33,-3));
  act(FirstBootChapterAction::set_isolation,actor(-35.5f,-3),"","",false);
  act(FirstBootChapterAction::open_door,actor(-32.5f,2),door.entity_id);
  GroundedCharacter body(first_boot_content_scene(after,content),{-32.5f,.2f,2});bool arrived=false;
  for(int i=0;i<36;++i){const auto previous=body.state().feet;CharacterInput input;input.move={0,0,1};const auto next=body.advance(input,1.0/60);
   if(!arrived&&first_boot_content_region(after,next.feet,content)=="hub"){FirstBootChapterActor evidence;evidence.previous_feet=previous;evidence.feet=next.feet;evidence.grounded=next.grounded;evidence.active_tick=next.ticks;act(FirstBootChapterAction::arrive_hub,evidence);arrived=true;}}
  require(arrived,"Actual capsule traverses moved main aperture");
  auto progress=std::find_if(after.components.begin(),after.components.end(),[](const auto& r){return r.type_id=="firstboot.ChapterProgress";});require(std::get<std::string>(progress->fields.at("first_route"))=="repair","Moved aperture retains genuine first-route evidence");
  auto directory=argc==2?std::filesystem::path(argv[1]):std::filesystem::temp_directory_path()/("aibs-content-"+new_uuid());require(!std::filesystem::exists(directory),"Proof directory must be new");std::filesystem::create_directories(directory);
  {GameplayStore store(directory/"play.sqlite",before.scope,first_boot_content_schemas());require(store.seed(first_boot_content_baseline(content)).status==GameplayStoreStatus::committed,"Bound baseline durable");for(const auto& b:batches)require(store.commit(b).status==GameplayStoreStatus::committed,"Actual content action durable");}
  {GameplayStore store(directory/"play.sqlite",before.scope,first_boot_content_schemas());const auto reloaded=store.recover();first_boot_content_validate(reloaded,content);require(reloaded.revision==after.revision&&store.lookup_batch("content-isolate").has_value()&&store.lookup_batch("content-build").has_value(),"Reload retains bound content and genuine receipts");require(reloaded.sequence==after.sequence,"Reload retains complete semantic head");}
  const auto bytes=first_boot_content_encode(content);const auto restored=first_boot_content_decode(bytes);require(restored.fingerprint()==content.fingerprint()&&first_boot_content_encode(restored)==bytes,"Exact definition codec/fingerprint roundtrip");
  {std::ofstream file(directory/"definition.aibd",std::ios::binary);file.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));require(file.good(),"Definition proof write");}
  auto changed=bytes;changed.pop_back();rejects([&]{(void)first_boot_content_decode(changed);},"Truncated definition rejected");
  auto fabricated=edited;record(fabricated,"firstboot.ChapterProgress").fields["shelter_secured"]=true;rejects([&]{(void)FirstBootContent::create(fabricated);},"Authoring cannot fabricate completed player progress");
  auto stranded=edited;stranded.hub_returns={{0,.2f,0}};rejects([&]{(void)FirstBootContent::create(stranded);},"Return anchor outside shelter rejected");
  auto blocked=edited;SceneObject wall{new_uuid(),"Blocked authored ingress",{-32.5f,2.5f,4},{2,2.5f,.4f},{.2f,.2f,.2f}};blocked.fixtures.push_back({wall,-1});rejects([&]{(void)FirstBootContent::create(blocked);},"Blocked physical main route rejected");
  require(content.fingerprint()!=original.fingerprint()&&content.fingerprint().size()==64,"Actual content change has distinct SHA256 identity");
  auto words=content.definition();++words.revision;words.hints["adam.danger"]="Authored Adam hint: Take the safe edge.";
  const auto words_preview=first_boot_content_preview(content,words);require(words_preview.status==FirstBootContentPreviewStatus::new_play_branch&&!words_preview.render_rebuild&&!words_preview.collision_rebuild&&!words_preview.power_dependencies&&!words_preview.quest_dependencies,"Dialogue-only revision does not pretend to rebuild geometry or change quest state");
  require(first_boot_content_preview(content,content.definition()).save_compatible,"Exact immutable content remains save compatible");
  auto repurposed=content.definition();++repurposed.revision;std::swap(record(repurposed,"firstboot.PowerFault").entity_id,record(repurposed,"firstboot.NPCQuest").entity_id);
  const auto refused=first_boot_content_preview(content,repurposed);require(refused.status==FirstBootContentPreviewStatus::rejected&&!refused.candidate,"Rejected identity-category change cannot return a publishable candidate");
  rejects([&]{(void)durable_first_boot_world(before);},"Legacy durable entry still rejects temporary context");
  auto foreign=before;foreign.scope.context=GameplayContext::authoring;rejects([&]{first_boot_content_validate(foreign,content);},"Runtime definition cannot admit authoring context");
  {std::ofstream file(directory/"content-proof.json");file<<"{\"status\":\"passed\",\"definition_sha256\":\""<<content.fingerprint()<<"\",\"world_id\":\""<<content.definition().world_id<<"\",\"revision\":"<<after.revision<<",\"semantic_sequence\":"<<after.sequence<<",\"batches\":"<<batches.size()<<",\"moved_door_physical_route\":true,\"sqlite_restart\":true,\"blocked_route_rejected\":true}";require(file.good(),"Content proof report write");}
  std::cout<<"Content definitions, actual moved geometry/actions, dependency preview, bound SQLite restart and exact codec passed\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
