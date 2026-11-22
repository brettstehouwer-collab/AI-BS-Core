#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/legacy_import.hpp>
#include <aibs/gameplay_codec.hpp>
#include <sqlite3.h>
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <thread>

using namespace aibs;
namespace {
void require(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
std::string ascii(const wchar_t* value) { std::string out;for(;*value;++value) { require(*value>0 && *value<128,"Probe value must be ASCII");out+=static_cast<char>(*value); }return out; }
struct Options { std::string step,world,timeline,entity,event;std::filesystem::path database,source,report; };
std::vector<ComponentSchema> old_registry() { return {{"old.Power",1,{{"capacity",GameplayValueKind::number,true,-0.0,100}}}}; }
std::vector<ComponentSchema> new_registry() {
 auto result=old_registry();result.push_back({"m3.Door",1,{{"open",GameplayValueKind::boolean}}});
 result.push_back({"m3.Power",1,{{"energy",GameplayValueKind::integer}}});result.push_back({"m3.Quest",1,{{"stage",GameplayValueKind::text}}});return result;
}
SchemaRegistry source_schema() { SchemaRegistry result;require(result.add({"capacity",0,100}),"Original schema registration failed");return result; }
std::vector<ComponentRecord> project(const Entity& entity) { return {{entity.persistent_id,"old.Power",1,{{"capacity",entity.fields.at("capacity")}}}}; }
GameplayChangeBatch old_batch(const Options& options,const GameplayScope& owner,bool stale=false) {
 GameplayChangeBatch batch;batch.scope=owner;batch.operation_id=stale?"stale.repair":"v1.repair";batch.expected_revision=stale?3:2;batch.revision=batch.expected_revision+1;
 batch.deltas.push_back({ComponentAction::upsert,{options.entity,"old.Power",1,{{"capacity",50.0}}}});
 SemanticEvent event;event.event_id=stale?new_uuid():options.event;event.scope=owner;event.sequence=stale?2:1;event.operation_id=batch.operation_id;
 event.subject_ids={options.entity};event.source_revision=batch.revision;event.logical_tick=23;
 event.provenance.source_id="registry.process.repair.v1";event.payload=RepairOutcome{options.entity,20,50};batch.events.push_back(std::move(event));return batch;
}
std::string hex(const gameplay_codec::Bytes& bytes) { constexpr char digits[]="0123456789abcdef";std::string result;result.reserve(2*bytes.size());for(const auto value:bytes) { result+=digits[value>>4];result+=digits[value&15]; }return result; }
gameplay_codec::Bytes read_source(const std::filesystem::path& path) {
 const auto count=std::filesystem::file_size(path);require(count>=24 && count<=CheckpointStore::maximum_file_bytes,"Source proof checkpoint exceeds bounds");
 std::ifstream input(path,std::ios::binary);gameplay_codec::Bytes bytes(static_cast<std::size_t>(count));input.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
 require(input.gcount()==static_cast<std::streamsize>(bytes.size()) && input.peek()==std::char_traits<char>::eof(),"Cannot capture exact source proof bytes");return bytes;
}
int format(const std::filesystem::path& path) {
 const auto encoded=path.u8string();const std::string name(reinterpret_cast<const char*>(encoded.data()),encoded.size());sqlite3* db=nullptr;
 require(sqlite3_open_v2(name.c_str(),&db,SQLITE_OPEN_READONLY,nullptr)==SQLITE_OK,"Cannot inspect database format");sqlite3_stmt* statement=nullptr;
 require(sqlite3_prepare_v2(db,"PRAGMA user_version",-1,&statement,nullptr)==SQLITE_OK && sqlite3_step(statement)==SQLITE_ROW,"Cannot read database format");
 const auto result=sqlite3_column_int(statement,0);sqlite3_finalize(statement);sqlite3_close(db);return result;
}
const char* status(GameplayStoreStatus value) {
 switch(value) { case GameplayStoreStatus::committed:return "committed";case GameplayStoreStatus::retry:return "retry";case GameplayStoreStatus::rejected:return "rejected";default:return "failed"; }
}
void report(const Options& options,const GameplayScope& owner,const char* migration="none") {
 const auto registry=GameplayStore::inspect_registry(options.database,owner);GameplayStore store(options.database,owner,registry);
 require(store.verify().ok,"Full registry and gameplay replay did not verify");const auto state=store.recover();const auto baseline=store.baseline();
 require(baseline && baseline->legacy_checkpoint==read_source(options.source),"Original source raw bytes were not preserved");
 const auto request=old_batch(options,owner);const auto receipt=store.lookup_batch("v1.repair");
 require(receipt && gameplay_codec::encode_batch(*receipt)==gameplay_codec::encode_batch(request),"Original exact gameplay receipt changed");
 const auto retry=store.commit(request);require(retry.status==GameplayStoreStatus::retry,"Original gameplay request is no longer idempotent");
 CreatorSession restored(source_schema(),"registry-process-proof","main");require(restore_imported_checkpoint(store,restored).ok,"Cannot restore retained original evidence");
 const auto checkpoint=restored.checkpoint_id();const auto original_revision=restored.revision();const auto original_events=restored.memory().events().size();
 const Transaction created{"source.create",0,{Create{{"core","Original core",{{"capacity",0}},options.entity}}}};
 require(restored.apply(created).ok && restored.memory().events().size()==original_events,"Original authoring receipt was lost");
 require(restored.undo().ok && restored.world().at("core").fields.at("capacity")==0 && restored.redo().ok &&
  restored.world().at("core").fields.at("capacity")==20 && restored.world().at("core").persistent_id==options.entity,"Original undo/redo or entity UUID was lost");
 std::ofstream out(options.report,std::ios::binary);
 out<<"{\"schema_version\":1,\"status\":\"passed\",\"format\":"<<format(options.database)<<",\"registry_hex\":\""<<hex(gameplay_codec::encode_schemas(registry))
  <<"\",\"expected_old_registry_hex\":\""<<hex(gameplay_codec::encode_schemas(old_registry()))<<"\",\"expected_target_registry_hex\":\""<<hex(gameplay_codec::encode_schemas(new_registry()))
  <<"\",\"migration_status\":\""<<migration<<"\",\"old_retry_status\":\""<<status(retry.status)<<"\",\"scope\":{\"project_id\":\"registry-process-proof\",\"world_id\":\""<<owner.world_id
  <<"\",\"branch_id\":\"main\",\"timeline_id\":\""<<owner.timeline_id<<"\",\"context\":\"player_world\"},\"revision\":"<<state.revision<<",\"sequence\":"<<state.sequence
  <<",\"original_checkpoint_id\":\""<<checkpoint<<"\",\"original_revision\":"<<original_revision<<",\"original_events\":"<<original_events
  <<",\"original_receipt_preserved\":true,\"original_undo_redo_preserved\":true,\"baseline_revision\":"<<baseline->revision<<",\"baseline_sequence\":"<<baseline->sequence
  <<",\"legacy_hex\":\""<<hex(baseline->legacy_checkpoint)<<"\",\"old_receipt_hex\":\""<<hex(gameplay_codec::encode_batch(*receipt))<<"\",\"baseline_components\":[";
 bool first=true;for(const auto& component:baseline->components) { if(!first) out<<',';first=false;out<<'"'<<hex(gameplay_codec::encode_component(component))<<'"'; }
 out<<"],\"components\":[";first=true;for(const auto& component:state.components) { if(!first) out<<',';first=false;out<<'"'<<hex(gameplay_codec::encode_component(component))<<'"'; }
 out<<"],\"batches\":[";first=true;for(const auto& batch:store.read_batches(0)) { if(!first) out<<',';first=false;out<<'"'<<hex(gameplay_codec::encode_batch(batch))<<'"'; }
 out<<"]}";out.close();require(out.good(),"Could not publish registry process proof result");
}
}
int wmain(int argc,wchar_t** argv) {
 try {
  Options options;
  for(int n=1;n<argc;++n) {
   const std::wstring flag(argv[n]);require(n+1<argc,"Probe option requires a value");const auto* value=argv[++n];
   if(flag==L"--step") options.step=ascii(value);else if(flag==L"--database") options.database=value;else if(flag==L"--source") options.source=value;
   else if(flag==L"--report") options.report=value;else if(flag==L"--world") options.world=ascii(value);else if(flag==L"--timeline") options.timeline=ascii(value);
   else if(flag==L"--entity") options.entity=ascii(value);else if(flag==L"--event") options.event=ascii(value);else throw std::invalid_argument("Unknown registry probe option");
  }
  require(!options.database.empty() && !options.source.empty() && !options.report.empty() && is_uuid(options.timeline) && is_uuid(options.entity) && is_uuid(options.event),"Incomplete registry process scope/paths");
  if(options.step=="seed") {
   require(!std::filesystem::exists(options.database) && !std::filesystem::exists(options.source),"Seed must use fresh synthetic proof files");
   CreatorSession source(source_schema(),"registry-process-proof","main");
   require(source.apply({"source.create",0,{Create{{"core","Original core",{{"capacity",0}},options.entity}}}}).ok &&
    source.apply({"source.set",1,{SetField{"core","capacity",20,options.entity}}}).ok,"Could not prepare genuine original authoring history");
   require(CheckpointStore::save(options.source,source).ok,"Could not save genuine format1 source");
   const auto imported=import_format1_checkpoint(options.source,options.database,source_schema(),"registry-process-proof","main",old_registry(),project,options.timeline);
   require(imported.ok && !imported.retry,"Original format1 import failed");options.world=imported.scope.world_id;
   GameplayStore store(options.database,imported.scope,old_registry());require(store.commit(old_batch(options,imported.scope)).status==GameplayStoreStatus::committed,"Original v1 gameplay batch failed");
   report(options,imported.scope);return 0;
  }
  require(is_uuid(options.world),"Registry probe requires the seeded persistent world UUID");const GameplayScope owner{"registry-process-proof",options.world,"main",options.timeline};
  if(options.step=="inspect") { report(options,owner);return 0; }
  if(options.step=="stale") {
   GameplayStore stale(options.database,owner,old_registry());require(stale.recover().revision==3 && format(options.database)==1,"Stale connection did not open original registry/head");
   auto ready=options.report;ready+=L".ready";{ std::ofstream signal(ready);signal<<"opened original registry and head";require(signal.good(),"Cannot signal stale registry readiness"); }
   auto go=options.report;go+=L".go";const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(15);
   while(!std::filesystem::exists(go) && std::chrono::steady_clock::now()<deadline) std::this_thread::sleep_for(std::chrono::milliseconds(10));
   require(std::filesystem::exists(go),"Stale registry connection did not receive bounded resume signal");
   const auto attempted=stale.commit(old_batch(options,owner,true));require(attempted.status==GameplayStoreStatus::rejected,"Stale registry connection committed after migration");
   report(options,owner,"stale_rejected");return 0;
  }
  require(options.step=="before" || options.step=="after" || options.step=="retry" || options.step=="conflict","Unknown registry proof step");
  auto target=new_registry();if(options.step=="conflict") target.push_back({"m3.Conflicting",1,{{"enabled",GameplayValueKind::boolean}}});
  GameplayStoreObserver observer;if(options.step=="before" || options.step=="after") observer=[&](GameplayStoreStage stage) {
   if(options.step=="before" && stage==GameplayStoreStage::before_commit) ExitProcess(73);
   if(options.step=="after" && stage==GameplayStoreStage::after_commit) ExitProcess(74);
  };
  const auto migrated=GameplayStore::extend_registry(options.database,owner,old_registry(),target,"m3.registry.process.v1",3,1,observer);
  if(options.step=="before" || options.step=="after") throw std::runtime_error("Requested migration interruption did not happen");
  require(migrated.status==(options.step=="retry"?GameplayStoreStatus::retry:GameplayStoreStatus::rejected),"Migration retry/conflict status was incorrect");
  report(options,owner,status(migrated.status));return 0;
 } catch(const std::exception& error) { std::cerr<<"Registry process proof failed: "<<error.what()<<'\n';return 1; }
}
