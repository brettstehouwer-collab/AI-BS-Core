#include <aibs/durable_first_boot.hpp>
#include <aibs/gameplay_codec.hpp>
#include <aibs/legacy_import.hpp>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <thread>
using namespace aibs;
namespace {
void require(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
template<class F> void rejects(F action,const char* message) { bool rejected=false;try{action();}catch(const std::exception&){rejected=true;}require(rejected,message); }
GameplayScope scope(const CreatorSession& source) { return {source.project_id(),source.world_id(),source.branch_id(),source.world_id(),GameplayContext::player_world}; }
const ComponentRecord& record(const GameplayStoreRecovery& state,const std::string& id) {
 const auto found=std::find_if(state.components.begin(),state.components.end(),[&](const auto& value){return value.entity_id==id;});require(found!=state.components.end(),"node record exists");return *found;
}
void rules(const GameplayStoreRecovery& before,const GameplayStoreRecovery& after,const GameplayChangeBatch& batch) { durable_first_boot_rules(before,after,batch); }
GameplaySaveCompletion committed(GameplayWorld& world) {
 std::optional<GameplaySaveCompletion> result;const auto until=std::chrono::steady_clock::now()+std::chrono::seconds(10);
 while(!(result=world.poll())) { require(std::chrono::steady_clock::now()<until,"actual facade save timed out");std::this_thread::sleep_for(std::chrono::milliseconds(2)); }
 require(result->result.status==GameplayStoreStatus::committed||result->result.status==GameplayStoreStatus::retry,"facade batch really committed to SQLite");return std::move(*result);
}
template<class Predicate> void await(Predicate predicate,const char* message) {
 const auto until=std::chrono::steady_clock::now()+std::chrono::seconds(10);
 while(!predicate()){require(std::chrono::steady_clock::now()<until,message);std::this_thread::sleep_for(std::chrono::milliseconds(2));}
}
void publish(GameplayWorld& world,const GameplayChangeBatch& batch,GameplayRuleValidator validator=rules) {
 const auto ready=world.prepare(batch,std::move(validator));require(ready.status==GameplayPrepareStatus::prepared,ready.message.c_str());
 require(world.publish(ready.change).ok,"publish prepared facade batch");(void)committed(world);require(world.state().saved,"world is durably acknowledged");
}
bool equal_mesh(const SceneMesh& left,const SceneMesh& right) {
 if(left.landmarks!=right.landmarks||left.vertices.size()!=right.vertices.size())return false;
 for(std::size_t i=0;i<left.vertices.size();++i) {
  const auto& a=left.vertices[i];const auto& b=right.vertices[i];
  if(a.position!=b.position||a.normal!=b.normal||a.color!=b.color||a.emission!=b.emission)return false;
 }return true;
}
std::vector<std::uint8_t> bytes(const std::filesystem::path& path) { std::ifstream file(path,std::ios::binary);return {std::istreambuf_iterator<char>(file),{}}; }
void lifecycle(const std::filesystem::path& directory) {
 CreatorSession source(first_boot_schema(),"typed-first-boot","main");require(seed_first_boot(source).ok,"original first boot seed");
 const auto baseline=durable_first_boot_baseline(source);const auto original_world=source.world();const auto original_memory=source.memory().events();
 require(baseline.components.size()==source.world().size()&&baseline.revision==0&&baseline.sequence==0&&baseline.legacy_checkpoint.empty(),"foundation projection fabricates no gameplay seed event or original archive");
 const auto owner=scope(source);const auto database=directory/"typed.sqlite";const auto core=source.world().at("core-01").persistent_id;
 {GameplayStore seed(database,owner,durable_first_boot_schemas());require(seed.seed(baseline).status==GameplayStoreStatus::committed,"typed foundation seeded");}
 GameplayWorld world(database,owner,durable_first_boot_schemas());
 require(durable_first_boot_world(*world.snapshot())==original_world,"alive node projection exactly preserves source entities and UUIDs");
 require(equal_mesh(mesh_from_snapshot(first_boot_scene(source)),mesh_from_snapshot(durable_first_boot_scene(*world.snapshot()))),"typed projection preserves actual motherboard mesh");
 auto old_player=first_boot_player(source);auto new_player=durable_first_boot_player(*world.snapshot());
 require(old_player.state().feet==new_player.state().feet,"typed projection uses identical safe spawn");
 const auto repair=durable_first_boot_repair(*world.snapshot(),core,"repair-once");require(repair.has_value(),"unpowered core yields a repair request");
 const auto& outcome=std::get<RepairOutcome>(repair->events[0].payload);require(outcome.before==0&&outcome.after==100,"repair payload reflects actual old capacity");
 const auto ready=world.prepare(*repair,rules);require(ready.status==GameplayPrepareStatus::prepared&&world.publish(ready.change).ok,"publish repair before acknowledgement");
 await([&]{return world.state().worker.completed==1;},"repair did not reach actual COMMIT");
 {
  GameplayStore committed_before_ack(database,owner,durable_first_boot_schemas());
  const auto waiting=durable_first_boot_guidance(world,committed_before_ack);
  require(committed_before_ack.read_batches(0).size()==1&&world.state().durable_revision==0&&waiting.authored_hint.find("is restored")!=std::string::npos&&waiting.committed_facts.empty(),
          "visible hint updates while real committed rows remain outside recall until owner acknowledgement");
 }
 (void)committed(world);require(world.state().saved&&!durable_first_boot_repair(*world.snapshot(),core),"healthy repair is an event-free no-op");
 require(world.prepare(*repair,rules).status==GameplayPrepareStatus::retry,"exact repair retry uses durable receipt without reapplying current-state rules");
 const auto built=durable_first_boot_build(*world.snapshot(),{30,1.2f,-20},"build-once");const auto relay=std::get<ConstructionOutcome>(built.events[0].payload).entity_id;
 publish(world,built);require(durable_first_boot_world(*world.snapshot()).size()==original_world.size()+1,"built relay enters actual scene world");
 const auto dismantled=durable_first_boot_dismantle(*world.snapshot(),relay,"dismantle-once");require(dismantled.has_value(),"living relay dismantles");publish(world,*dismantled);
 require(world.snapshot()->components.size()==baseline.components.size()+1&&!std::get<bool>(record(*world.snapshot(),relay).fields.at("alive"))&&
         durable_first_boot_world(*world.snapshot()).size()==original_world.size(),"dismantled relay retains identity tombstone outside render/collision world");
 require(!durable_first_boot_dismantle(*world.snapshot(),relay),"already dismantled relay is an event-free no-op");
 auto revive=built;revive.operation_id="illegal-revival";revive.expected_revision=world.snapshot()->revision;revive.revision=revive.expected_revision+1;
 revive.events[0].event_id=new_uuid();revive.events[0].operation_id=revive.operation_id;revive.events[0].sequence=world.snapshot()->sequence+1;revive.events[0].source_revision=revive.revision;
 require(world.prepare(revive,rules).status==GameplayPrepareStatus::rejected,"existing tombstone UUID cannot be revived or recycled");
 auto alias=durable_first_boot_build(*world.snapshot(),{32,1.2f,-20},"recycled-alias");alias.deltas[0].component.fields["alias"]=std::get<std::string>(record(*world.snapshot(),relay).fields.at("alias"));
 require(world.prepare(alias,rules).status==GameplayPrepareStatus::rejected,"tombstone alias cannot be recycled by a new typed node");
 require(world.close().ok,"typed lifecycle closes");
 GameplayWorld reopened(database,owner,durable_first_boot_schemas());durable_first_boot_validate(*reopened.snapshot());
 require(reopened.snapshot()->revision==3&&reopened.snapshot()->sequence==3&&!std::get<bool>(record(*reopened.snapshot(),relay).fields.at("alive")),"SQLite worker restart preserves repaired world, event head and tombstone");
 GameplayStore archive(database,owner,durable_first_boot_schemas());const auto guidance=durable_first_boot_guidance(reopened,archive);
 require(guidance.authored_hint.starts_with("Authored hint:")&&guidance.committed_facts.size()==3&&
         guidance.committed_facts[0].starts_with("Committed gameplay:")&&guidance.committed_facts[0].find("dismantled relay")!=std::string::npos&&
         guidance.original_evidence.find("authored foundation")!=std::string::npos,
         "authored hint, actual committed facts and original-baseline evidence are separate");
 require(archive.read_batches(0).size()==3&&source.world()==original_world&&source.memory().events()==original_memory,"typed progress never rewrites original authoring history");
 require(reopened.close().ok,"reopened lifecycle closes");
}
void false_outcomes_and_base_protection(const std::filesystem::path& directory) {
 CreatorSession source(first_boot_schema(),"false-outcome","main");require(seed_first_boot(source).ok,"rejection fixture seed");
 const auto owner=scope(source);const auto database=directory/"rules.sqlite";
 {GameplayStore seeded(database,owner,durable_first_boot_schemas());require(seeded.seed(durable_first_boot_baseline(source)).status==GameplayStoreStatus::committed,"rule baseline");}
 GameplayWorld world(database,owner,durable_first_boot_schemas());const auto core=source.world().at("core-01").persistent_id;
 const auto valid=*durable_first_boot_repair(*world.snapshot(),core,"repair-candidate");const auto original=world.snapshot();
 auto invalid=valid;invalid.deltas[0].component.fields["capacity"]=50.0;
 require(world.prepare(invalid,rules).status==GameplayPrepareStatus::rejected,"repair delta cannot claim a different semantic result");
 invalid=valid;invalid.deltas[0].component.fields["x"]=source.world().at("core-01").fields.at("x")+1;
 require(world.prepare(invalid,rules).status==GameplayPrepareStatus::rejected,"repair cannot secretly move immutable base geometry");
 invalid=valid;std::get<RepairOutcome>(invalid.events[0].payload).before=1;
 require(world.prepare(invalid,rules).status==GameplayPrepareStatus::rejected,"repair cannot falsify historical before capacity");
 invalid=valid;invalid.deltas[0].component.fields["name"]=std::string("Rewritten architecture");
 require(world.prepare(invalid,rules).status==GameplayPrepareStatus::rejected,"repair cannot rewrite original architecture names");
 const auto board=source.world().at("board").persistent_id;invalid=valid;invalid.deltas[0].component=record(*world.snapshot(),board);invalid.deltas[0].component.fields["alive"]=false;
 invalid.events[0].subject_ids={board};invalid.events[0].payload=ConstructionOutcome{board,false};invalid.events[0].provenance.source_id="firstboot.dismantle.v1";
 require(world.prepare(invalid,rules).status==GameplayPrepareStatus::rejected,"non-relay base cannot be dismantled");
 invalid=valid;invalid.deltas[0].component.type_id="foreign.Node";
 require(world.prepare(invalid,rules).status==GameplayPrepareStatus::rejected,"foreign registry type cannot enter game world");
 auto foreign=*original;foreign.scope.branch_id="foreign";
 rejects([&]{durable_first_boot_rules(*original,foreign,valid);},"foreign facade scope rejects");
 auto malformed=*original;malformed.components[0].type_id="foreign.Node";
 rejects([&]{(void)durable_first_boot_world(malformed);},"projection never ignores foreign components");
 auto duplicate=*original;duplicate.components.push_back(duplicate.components[0]);
 rejects([&]{(void)durable_first_boot_world(duplicate);},"projection rejects duplicate entity identities");
 require(world.snapshot()==original&&world.read_batches(0).empty()&&world.state().saved,"all rejected outcomes preserve live world and durable history");
 require(world.close().ok,"rule owner closes");
}
void imported_retired_identity(const std::filesystem::path& directory) {
 CreatorSession source(first_boot_schema(),"imported-first-boot","main");require(seed_first_boot(source).ok,"import source seed");
 require(build_first_boot_relay(source,{30,1.2f,-20}).ok,"original relay built");std::string retired;
 for(const auto& [unused,entity]:source.world()){(void)unused;if(entity.fields.at("firstboot.kind")==6)retired=entity.persistent_id;}
 require(!retired.empty()&&dismantle_first_boot(source,retired).ok,"original relay retired before migration");
 const auto file=directory/"original.aibs",database=directory/"imported.sqlite";require(CheckpointStore::save(file,source).ok,"original source checkpoint published");
 const auto source_bytes=bytes(file);const auto source_memory=source.memory().events();
 const auto imported=import_format1_checkpoint(file,database,first_boot_schema(),source.project_id(),source.branch_id(),durable_first_boot_schemas(),durable_first_boot_components,{},durable_first_boot_validate_source);
 require(imported.ok&&imported.source_revision==source.revision(),"original typed import preserves actual source revision");
 GameplayStore archive(database,imported.scope,durable_first_boot_schemas());const auto known=durable_first_boot_imported_ids(archive);
 require(known==source.known_entity_ids()&&known.contains(retired),"imported known UUID cache includes source-retired identities");
 GameplayWorld world(database,imported.scope,durable_first_boot_schemas());
 auto guarded=[&](const auto& before,const auto& after,const auto& batch){durable_first_boot_rules(before,after,batch,known);};
 auto bad=durable_first_boot_build(*world.snapshot(),{30,1.2f,-20},"reuse-retired-source");bad.deltas[0].component.entity_id=retired;bad.deltas[0].component.fields["alias"]="relay-"+retired;
 bad.events[0].subject_ids={retired};std::get<ConstructionOutcome>(bad.events[0].payload).entity_id=retired;
 require(world.prepare(bad,guarded).status==GameplayPrepareStatus::rejected,"SDK proposals cannot reuse a UUID retired before import");
 const auto repair=*durable_first_boot_repair(*world.snapshot(),source.world().at("core-01").persistent_id,"imported-core-repair");publish(world,repair,guarded);
 const auto guidance=durable_first_boot_guidance(world,archive);require(guidance.original_evidence.find("format-1")!=std::string::npos&&guidance.committed_facts.size()==1,"original raw evidence is separate from newly committed gameplay recall");
 require(guidance.original_evidence.find("Imported edit record")!=std::string::npos&&guidance.original_evidence.find(source_memory.back().description)!=std::string::npos&&
         guidance.original_evidence.find(source_memory.back().operation)!=std::string::npos,"original recall includes the actual last validated edit description and operation");
 CreatorSession original(first_boot_schema(),source.project_id(),source.branch_id());
 require(restore_imported_checkpoint(archive,original).ok&&original.world()==source.world()&&original.memory().events()==source_memory&&bytes(file)==source_bytes,
         "new typed repairs never rewrite archived original state, receipts or source bytes");
 require(world.close().ok,"imported gameplay closes");
}
void failed_save_hint(const std::filesystem::path& directory) {
 CreatorSession source(first_boot_schema(),"failed-save-hint","main");require(seed_first_boot(source).ok,"failed hint source");
 const auto owner=scope(source);const auto database=directory/"failed-hint.sqlite";
 {GameplayStore initial(database,owner,durable_first_boot_schemas());require(initial.seed(durable_first_boot_baseline(source)).status==GameplayStoreStatus::committed,"failed hint baseline");}
 std::atomic<bool> fail=true;GameplayWorld world(database,owner,durable_first_boot_schemas(),{},[&](GameplayStoreStage stage){if(stage==GameplayStoreStage::before_commit&&fail.exchange(false))throw std::runtime_error("actual save rollback");});
 const auto repair=*durable_first_boot_repair(*world.snapshot(),source.world().at("core-01").persistent_id);
 const auto ready=world.prepare(repair,rules);require(ready.status==GameplayPrepareStatus::prepared&&world.publish(ready.change).ok,"failed hint publication");
 std::optional<GameplaySaveCompletion> failed;await([&]{failed=world.poll();return failed.has_value();},"failed hint completion");
 require(failed->result.status==GameplayStoreStatus::failed&&world.state().failed&&!world.state().saved,"actual save failure acknowledged honestly");
 GameplayStore archive(database,owner,durable_first_boot_schemas());const auto current=durable_first_boot_guidance(world,archive);
 require(current.authored_hint.find("is restored")!=std::string::npos&&current.committed_facts.empty(),"failed save keeps visible authored hint without inventing committed memory");
 require(world.retry_pending().ok,"failed facade save can retry");(void)committed(world);
 require(durable_first_boot_guidance(world,archive).committed_facts.size()==1&&world.close().ok,"only successful retry creates committed recall");
}
void blocked_candidate_is_recoverable(const std::filesystem::path& directory) {
 CreatorSession source(first_boot_schema(),"blocked-candidate","main");require(seed_first_boot(source).ok,"blocked candidate source");
 const auto id=source.world().at("board").persistent_id;
 require(source.apply({"small-clear-board",source.revision(),{SetField{"board","x",30,id},SetField{"board","z",-20,id},
   SetField{"board","half_x",1,id},SetField{"board","half_z",1,id}}}).ok,"small clear board source");
 const auto owner=scope(source);const auto database=directory/"blocked-candidate.sqlite";
 {GameplayStore initial(database,owner,durable_first_boot_schemas());require(initial.seed(durable_first_boot_baseline(source)).status==GameplayStoreStatus::committed,"small board baseline");}
 GameplayWorld world(database,owner,durable_first_boot_schemas());const auto before=world.snapshot();const auto original_player=durable_first_boot_player(*before);
 bool rejected=false;try{(void)durable_first_boot_build(*before,{30,1.2f,-20});}catch(const std::invalid_argument&){rejected=true;}
 require(rejected&&world.snapshot()==before&&world.state().saved&&world.read_batches(0).empty(),"fully blocking construction is a recoverable rejection, not an app-ending runtime error");
 const auto still_usable=durable_first_boot_player(*world.snapshot());require(still_usable.state().feet==original_player.state().feet,"failed construction leaves old scene and safe spawn usable");
 require(world.close().ok,"blocked candidate owner closes");
}
void board_placement() {
 CreatorSession source(first_boot_schema(),"placement","main");require(seed_first_boot(source).ok,"placement source");
 const auto baseline=durable_first_boot_baseline(source);GameplayStoreRecovery snapshot{scope(source),0,0,baseline.components};const auto original=snapshot.components;
 const auto normal=durable_first_boot_placement(snapshot,{0,11,0},{0,-2,0});
 require(normal&&normal->x==0&&normal->z==0&&normal->y==1.2f,"default board placement preserves current offsets and normalizes the ray");
 auto elevated=snapshot;
 for(auto& value:elevated.components)if(std::get<double>(value.fields.at("firstboot.kind"))==1){value.fields["x"]=15.0;value.fields["z"]=-5.0;value.fields["y"]=4.0;value.fields["half_y"]=2.0;}
 const auto hit=durable_first_boot_placement(elevated,{100,17,-100},{0,-3,0});
 require(hit&&hit->x==100&&hit->z==-100&&hit->y==7.2f,"elevated shifted boards use actual top and retain construction expansion outside board extents");
 const auto diagonal=durable_first_boot_placement(elevated,{0,17,0},{1,-1,0});require(diagonal&&std::abs(diagonal->x-10)<.0001f,"normalized diagonal placement uses world distance");
 require(!durable_first_boot_placement(elevated,{0,17,0},{0,1,0})&&!durable_first_boot_placement(elevated,{0,17,0},{1,0,0})&&
         !durable_first_boot_placement(elevated,{0,17,0},{0,0,0}),"upward, parallel and zero rays have no placement");
 require(!durable_first_boot_placement(elevated,{0,207,0},{0,-1,0})&&!durable_first_boot_placement(elevated,{0,208,0},{0,-1,0})&&
         !durable_first_boot_placement(elevated,{0,7,0},{0,-1,0}),"zero and at/beyond 200 world-unit distances reject");
 require(!durable_first_boot_placement(elevated,{std::numeric_limits<float>::quiet_NaN(),17,0},{0,-1,0})&&
         !durable_first_boot_placement(elevated,{0,17,0},{0,-std::numeric_limits<float>::infinity(),0})&&
         !durable_first_boot_placement(elevated,{201,17,0},{0,-1,0}),"nonfinite rays and out-of-world node positions reject");
 require(snapshot.components==original&&source.world()==durable_first_boot_world(snapshot),"placement is a pure read of original nodes");
}
void empty_original_recall(const std::filesystem::path& directory) {
 CreatorSession original(first_boot_schema(),"empty-original","main");const auto file=directory/"empty-original.aibs";
 require(CheckpointStore::save(file,original).ok,"valid empty original checkpoint");
 CreatorSession authored(first_boot_schema(),"empty-original","main");require(seed_first_boot(authored).ok,"authored projection for empty source fallback");
 auto baseline=durable_first_boot_baseline(authored);baseline.legacy_checkpoint=bytes(file);const auto database=directory/"empty-original.sqlite";
 {GameplayStore seeded(database,scope(original),durable_first_boot_schemas());require(seeded.seed(baseline).status==GameplayStoreStatus::committed,"empty source evidence retained");}
 GameplayWorld world(database,scope(original),durable_first_boot_schemas());GameplayStore archive(database,scope(original),durable_first_boot_schemas());
 const auto recalled=durable_first_boot_guidance(world,archive);
 require(recalled.original_evidence.find("no edit records")!=std::string::npos&&recalled.committed_facts.empty(),"empty original journal is labeled without inventing a memory");
 require(world.close().ok,"empty original owner closes");
}
}
int main() {
 try {
  const auto directory=std::filesystem::temp_directory_path()/("aibs-durable-first-boot-"+new_uuid());std::filesystem::create_directories(directory);
  lifecycle(directory);false_outcomes_and_base_protection(directory);imported_retired_identity(directory);failed_save_hint(directory);blocked_candidate_is_recoverable(directory);board_placement();empty_original_recall(directory);
  std::cout<<"PASS: durable First Boot projection, true outcomes, protected architecture, tombstones, actual commits/restart and source evidence\n";return 0;
 }catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}
}
