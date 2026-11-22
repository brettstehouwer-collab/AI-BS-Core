// CPU-only admission of the ACTUAL native option/lock/initialization functions.
// Including this translation unit exercises the same implementation; no window,
// renderer, run_chapter, synthetic walkthrough or family-media code is invoked.
#ifndef AIBS_DURABLE_WORLD_SOURCE
#define AIBS_DURABLE_WORLD_SOURCE "../apps/durable_world.cpp"
#endif
#include AIBS_DURABLE_WORLD_SOURCE
#include <aibs/warm_opening.hpp>
#include <iterator>

namespace {
unsigned assertions=0;
void check(bool value,const char* why){++assertions;if(!value)throw std::runtime_error(why);}
template<class F>void rejects(F&& call,const char* why){bool failed=false;try{call();}catch(const std::exception&){failed=true;}check(failed,why);}
std::vector<char> bytes(const std::filesystem::path& path){std::ifstream f(path,std::ios::binary);check(f.good(),"Cannot read evidence bytes");return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};}
using Tree=std::map<std::filesystem::path,std::vector<char>>;
Tree tree(const std::filesystem::path& root){Tree r;for(const auto& p:std::filesystem::recursive_directory_iterator(root))if(p.is_regular_file())r.emplace(p.path().lexically_relative(root),bytes(p.path()));return r;}
void write(const std::filesystem::path& path,const std::vector<unsigned char>& data){std::ofstream f(path,std::ios::binary);f.write(reinterpret_cast<const char*>(data.data()),static_cast<std::streamsize>(data.size()));f.close();check(f.good(),"Cannot write synthetic content");}
Options parsed(std::vector<std::wstring> args){std::vector<wchar_t*> pointers;for(auto& a:args)pointers.push_back(a.data());return options(static_cast<int>(pointers.size()),pointers.data());}
std::vector<std::wstring> arguments(const Options& o){return {L"fixture",L"--durable-world",L"--persistent-play",L"--content-definition",o.content_definition.wstring(),L"--database",o.database.wstring(),L"--project",wide(o.project),L"--branch",wide(o.branch),L"--play-session",wide(o.play_session),L"--timeline-id",wide(o.timeline_id),L"--stop-file",o.stop_file.wstring()};}
Options fresh(const std::filesystem::path& root,const std::filesystem::path& content,std::string timeline={}){
 std::filesystem::create_directory(root);Options o;o.database=root/L"world.sqlite";o.content_definition=content;
 o.project="persistent-native-contract";o.branch="main";o.play_session=new_uuid();o.timeline_id=timeline.empty()?new_uuid():std::move(timeline);
 o.stop_file=root/std::filesystem::path("stop."+o.play_session+".request");return parsed(arguments(o));
}
bool same(const GameplayStoreRecovery& a,const GameplayStoreRecovery& b){if(a.scope!=b.scope||a.revision!=b.revision||a.sequence!=b.sequence||a.components.size()!=b.components.size())return false;for(std::size_t n=0;n<a.components.size();++n)if(gameplay_codec::encode_component(a.components[n])!=gameplay_codec::encode_component(b.components[n]))return false;return true;}
Vec3 grounded(const GameplayStoreRecovery& s,const FirstBootContent& c){GroundedCharacter bs(first_boot_content_scene(s,c),first_boot_content_safe_return(s,c));for(unsigned n=0;n<32;++n)bs.advance({},1./60);check(bs.state().grounded,"Supported actual CPU player return");return bs.state().feet;}
void companion_choice(GameplayWorld& world,CompanionRuntime& guide,const FirstBootContent& c,CompanionAction action){
 const auto s=world.snapshot();CompanionActor actor;actor.target={grounded(*s,c),true,s->revision};
 auto choice=guide.prepare_choice(*s,action,actor);check(choice!=nullptr,"Explicit companion choice creates a real batch");
 const auto prepared=world.prepare(choice->batch(),[&](const auto& before,const auto& after,const auto& batch){guide.validate_choice(*choice,before,after,batch,actor);});
 check(prepared.status==GameplayPrepareStatus::prepared,"Actual world validates companion batch");check(world.publish(prepared.change).ok,"Actual worker admission publishes companion choice");check(guide.publish(std::move(choice)),"Accepted choice activates companion");
 const auto deadline=Clock::now()+std::chrono::seconds(5);
 while(!world.state().saved){if(auto done=world.poll();done)check(done->result.status==GameplayStoreStatus::committed,"Companion commit succeeds");check(!world.state().failed&&Clock::now()<deadline,"Bounded companion commit drains without failure");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
}
}

int wmain(int argc,wchar_t** argv){
 try{
  if(argc==5&&std::wstring_view(argv[1])==L"--hold-lock"){
   Options o;o.persistent_play=true;o.database=std::filesystem::absolute(argv[2]);PersistentSlotLock held(o);
   {std::ofstream ready(argv[3]);ready<<"held\n";check(ready.good(),"Cannot signal actual held kernel lock");}
   const auto until=Clock::now()+std::chrono::seconds(30);while(!std::filesystem::exists(argv[4])){check(Clock::now()<until,"Lock test release timed out");std::this_thread::sleep_for(std::chrono::milliseconds(10));}return 0;
  }
  if(argc==3&&std::wstring_view(argv[1])==L"--try-lock"){
   Options o;o.persistent_play=true;o.database=std::filesystem::absolute(argv[2]);PersistentSlotLock held(o);return 0;
  }
  check(argc==2,"Usage: native_saved_play_tests NEWOUTPUTDIR");const auto root=std::filesystem::absolute(argv[1]).lexically_normal();
  check(!std::filesystem::exists(root)&&std::filesystem::is_directory(root.parent_path()),"Refuse existing evidence output");std::filesystem::create_directory(root);
  CreatorSession source(first_boot_schema(),"persistent-native-contract","main");check(seed_first_boot(source).ok,"Synthetic source authored");
  const auto content=FirstBootContent::create(make_warm_workshop_draft(source,{}).definition);const auto definition=root/L"chapter.aibd";write(definition,first_boot_content_encode(content));
  auto o=fresh(root/L"saved",definition);const auto base_args=arguments(o);
  for(const auto& extra:std::vector<std::vector<std::wstring>>{{L"--durable-step",L"seed"},{L"--import-checkpoint",L"unused"},{L"--upgrade-chapter"},{L"--request-file",L"unused"},{L"--proof-gate",L"unused"}}){auto a=base_args;a.insert(a.end(),extra.begin(),extra.end());rejects([&]{(void)parsed(a);},"Destructive/migration option rejects before database admission");}
  auto bad=base_args;bad.erase(bad.begin()+13,bad.begin()+15);rejects([&]{(void)parsed(bad);},"Persistent mode requires explicit stable timeline");
  bad=base_args;bad[16]=(o.database.parent_path()/L"stop.request").wstring();rejects([&]{(void)parsed(bad);},"Retained fixed marker cannot masquerade as invocation control");
  bad=base_args;bad.push_back(L"--persistent-play");rejects([&]{(void)parsed(bad);},"Duplicate persistent option rejects");
  check(!std::filesystem::exists(o.database)&&!std::filesystem::exists(saved_world_claim_path(o)),"Rejected CLI creates no database or initialization claim");
  const auto tour=root/L"tour.aibtour";write(tour,{1});auto recording=base_args;
  const std::vector<std::wstring> record_args{L"--record-mp4",(o.database.parent_path()/L"walkthrough.mp4").wstring(),L"--record-ffmpeg",std::filesystem::absolute(argv[0]).wstring(),L"--width",L"1280",L"--height",L"720",L"--capture",(root/L"capture.bmp").wstring(),L"--durable-report",(root/L"capture.json").wstring(),L"--opening-tour-bindings",tour.wstring()};
  recording.insert(recording.end(),record_args.begin(),record_args.end());const auto recorder_options=parsed(recording);
  check(recorder_options.persistent_play&&recorder_options.recording()&&recorder_options.walkthrough&&!recorder_options.proof(),"Ordinary explicit recording options remain admitted without running encoder or GPU");
  check(!std::filesystem::exists(recorder_options.record_mp4),"CLI recording admission alone creates no media file");
  GameplayScope scope;GameplayStoreRecovery progressed;
  {
   PersistentSlotLock held(o);rejects([&]{PersistentSlotLock duplicate(o);},"Kernel lock rejects a duplicate live slot owner");
   scope=initialize_content(o,content);check(scope.context==GameplayContext::player_world&&scope.timeline_id==o.timeline_id&&scope.timeline_id!=o.play_session,"Stable player timeline differs from fresh invocation");
   check(std::filesystem::is_regular_file(saved_world_claim_path(o)),"Flushed initialization claim precedes first seed");
   GameplayWorld world(o.database,scope,first_boot_content_schemas(content));CompanionRuntime guide(*world.snapshot(),content);
   companion_choice(world,guide,content,CompanionAction::wait);check(guide.state().saved.intent==GuideIntent::wait,"Wait is actual acknowledged state");
   companion_choice(world,guide,content,CompanionAction::follow);check(guide.state().saved.intent==GuideIntent::follow,"Follow is actual acknowledged state");
   check(world.close().ok,"Actual save worker drains and joins");progressed=*world.snapshot();check(progressed.revision==2&&progressed.sequence==2,"Only two explicit choices persisted");
   GameplayWorldState status;status.saved=true;status.durable_revision=progressed.revision;status.durable_sequence=progressed.sequence;
   const auto ready=saved_play_lifecycle(o,scope,content,status,true,false),stopped=saved_play_lifecycle(o,scope,content,status,false,false);
   std::ofstream events(root/L"lifecycle.jsonl");events<<ready<<stopped;events.close();check(events.good(),"Exact lifecycle samples retained");
   check(ready.find("aibs.saved_play.ready")!=std::string::npos&&stopped.find("aibs.saved_play.stopped")!=std::string::npos,"Saved mode has distinct lifecycle events");
   check(saved_play_lifecycle(o,scope,content,status,false,true).find("\"saved\":false")!=std::string::npos,"Critical unpublished outcome cannot claim saved");
  }
  auto resumed=o;resumed.play_session=new_uuid();resumed.stop_file=o.database.parent_path()/std::filesystem::path("stop."+resumed.play_session+".request");resumed=parsed(arguments(resumed));
  const auto retained=tree(o.database.parent_path());
  {PersistentSlotLock held(resumed);check(initialize_content(resumed,content)==scope,"New invocation resumes stable scope");}
  check(tree(o.database.parent_path())==retained,"Resume preflight changes no source/sidecar bytes");
  const auto recovered=GameplayStore::inspect_recovery(o.database,scope,first_boot_content_schemas(content));check(same(recovered,progressed),"Recovery preserves exact committed components and heads");
  CompanionRuntime restored(recovered,content);check(restored.state().saved.intent==GuideIntent::follow,"Companion intent reconstructed after owner restart");
  auto wrong=resumed;wrong.timeline_id=new_uuid();const auto before=tree(o.database.parent_path());rejects([&]{PersistentSlotLock held(wrong);(void)initialize_content(wrong,content);},"Wrong stable timeline rejects");check(tree(o.database.parent_path())==before,"Wrong timeline preserves every slot byte");
  auto altered=content.definition();altered.hints["adam.shelter"]="Synthetic changed revision";++altered.revision;const auto changed=FirstBootContent::create(altered);
  rejects([&]{PersistentSlotLock held(resumed);(void)initialize_content(resumed,changed);},"Changed immutable content rejects existing slot");check(tree(o.database.parent_path())==before,"Changed content preserves original slot");
  const auto bound=fresh(root/L"binding-mismatch",definition);GameplayScope bound_scope;
  {PersistentSlotLock held(bound);bound_scope=initialize_content(bound,content);}
  const auto forged_claim=saved_world_claim(bound_scope,changed);write(saved_world_claim_path(bound),std::vector<unsigned char>(forged_claim.begin(),forged_claim.end()));const auto bound_before=tree(bound.database.parent_path());
  bool binding_rejected=false;try{PersistentSlotLock held(bound);(void)initialize_content(bound,changed);}catch(const std::exception& error){binding_rejected=std::string(error.what()).find("fingerprint mismatch")!=std::string::npos;}
  check(binding_rejected,"Read-only native recovery validates actual DB binding even when the adjacent claim matches wrong content");check(tree(bound.database.parent_path())==bound_before,"Rejected actual DB binding preserves all source and sidecar bytes");
  const auto empty=fresh(root/L"empty",definition);{std::ofstream file(empty.database);file.close();}rejects([&]{PersistentSlotLock held(empty);(void)initialize_content(empty,content);},"Existing unclaimed empty DB never reseeds");check(bytes(empty.database).empty()&&!std::filesystem::exists(saved_world_claim_path(empty)),"Empty DB remains empty and unclaimed");
  const auto partial=fresh(root/L"interrupted",definition);{PersistentSlotLock held(partial);validate_saved_world_claim(partial,{partial.project,content.definition().world_id,partial.branch,partial.timeline_id,GameplayContext::player_world},content,false);}rejects([&]{PersistentSlotLock held(partial);(void)initialize_content(partial,content);},"Interrupted claim without DB never silently starts over");check(!std::filesystem::exists(partial.database),"Incomplete slot remains explicit");
  const auto db_preimage=bytes(o.database);write(root/L"retained-database-preimage.bin",std::vector<unsigned char>(db_preimage.begin(),db_preimage.end()));
  check(std::filesystem::remove(o.database),"Synthetic lost DB fixture removed intentionally");const auto claim_before=bytes(saved_world_claim_path(o));rejects([&]{PersistentSlotLock held(resumed);(void)initialize_content(resumed,content);},"Lost established database is never reseeded");check(!std::filesystem::exists(o.database)&&bytes(saved_world_claim_path(o))==claim_before,"Lost DB/retained claim remain unchanged");
  const auto isolated=fresh(root/L"isolated",definition);auto isolated_args=arguments(isolated);isolated_args.erase(isolated_args.begin()+13,isolated_args.begin()+15);isolated_args.erase(isolated_args.begin()+2);const auto legacy=parsed(isolated_args);const auto isolated_scope=initialize_content(legacy,content);check(isolated_scope.context==GameplayContext::temporary_play&&isolated_scope.timeline_id==legacy.play_session,"Legacy isolated managed context/timeline unchanged");check(!std::filesystem::exists(saved_world_claim_path(legacy)),"Isolated Play never creates retained initialization claim");
  std::cout<<"PASS "<<assertions<<" native saved-player admission/recovery/lock/claim checks; no window or GPU created\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAILED: "<<e.what()<<'\n';return 1;}
}
