#include <aibs/gameplay_store.hpp>
#include <aibs/gameplay_codec.hpp>
#include <sqlite3.h>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace aibs;
namespace {
void require(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
GameplayScope scope() { return {"sqlite-contract",new_uuid(),"main",new_uuid(),GameplayContext::player_world}; }
std::vector<ComponentSchema> schemas() {
 return {{"test.Power",1,{{"capacity",GameplayValueKind::number,true,0,100},
  {"counter",GameplayValueKind::integer,false},{"label",GameplayValueKind::text,false},
  {"enabled",GameplayValueKind::boolean,false}}}};
}
GameplayChangeBatch repair(const GameplayScope& owner,const std::string& entity,std::uint64_t revision=1,
                           std::uint64_t sequence=1,std::string operation="repair-1") {
 GameplayChangeBatch value;
 value.scope=owner; value.operation_id=std::move(operation);value.expected_revision=revision-1;value.revision=revision;
 value.deltas.push_back({ComponentAction::upsert,{entity,"test.Power",1,{{"capacity",100.0},
  {"counter",std::numeric_limits<std::int64_t>::max()},{"label",std::string("x\0y",3)},{"enabled",true}}}});
 SemanticEvent event;
 event.event_id=new_uuid();event.scope=owner;event.operation_id=value.operation_id;event.sequence=sequence;
 event.source_revision=revision;event.subject_ids={entity};event.logical_tick=std::numeric_limits<std::uint64_t>::max();
 event.provenance={GameplayProvenance::gameplay_rule,"test.repair.v1"};event.payload=RepairOutcome{entity,0,100};
 value.events.push_back(std::move(event));return value;
}
struct RawDatabase {
 sqlite3* db=nullptr;
 explicit RawDatabase(const std::filesystem::path& path) {
  require(sqlite3_open(path.string().c_str(),&db)==SQLITE_OK,"open raw corruption fixture");
 }
 ~RawDatabase() { sqlite3_close(db); }
 void execute(const char* sql) { require(sqlite3_exec(db,sql,nullptr,nullptr,nullptr)==SQLITE_OK,"execute raw corruption fixture"); }
};
struct RawStatement {
 sqlite3_stmt* value=nullptr;
 RawStatement(sqlite3* db,const char* sql) { require(sqlite3_prepare_v2(db,sql,-1,&value,nullptr)==SQLITE_OK,"prepare raw corruption fixture"); }
 ~RawStatement() { sqlite3_finalize(value); }
 void blob(int index,const gameplay_codec::Bytes& bytes) { require(sqlite3_bind_blob64(value,index,bytes.data(),bytes.size(),SQLITE_TRANSIENT)==SQLITE_OK,"bind raw corruption bytes"); }
 void text(int index,const std::string& text) { require(sqlite3_bind_text64(value,index,text.data(),text.size(),SQLITE_TRANSIENT,SQLITE_UTF8)==SQLITE_OK,"bind raw corruption text"); }
 void write() { require(sqlite3_step(value)==SQLITE_DONE,"write raw corruption fixture");sqlite3_reset(value);sqlite3_clear_bindings(value); }
};
gameplay_codec::Bytes unsigned_bytes(std::uint64_t value) {
 gameplay_codec::Bytes result(8);for(std::size_t n=0;n<8;++n) result[n]=static_cast<std::uint8_t>(value>>(56-8*n));return result;
}
void hostile_intermediate_state(const std::filesystem::path& path,const GameplayScope& owner,const std::vector<ComponentSchema>& registry) {
 { GameplayStore empty(path,owner,registry); }
 RawDatabase raw(path);raw.execute("BEGIN IMMEDIATE");const auto key=gameplay_codec::encode_scope(owner);
 RawStatement receipt(raw.db,"INSERT INTO aibs_gameplay_batches VALUES(?1,?2,?3,?4)");
 RawStatement event(raw.db,"INSERT INTO aibs_gameplay_events VALUES(?1,?2,?3,?4)");
 std::vector<std::string> entities;std::uint64_t revision=0;
 auto append=[&](GameplayChangeBatch& batch) {
  batch.scope=owner;batch.expected_revision=revision;batch.revision=++revision;batch.operation_id="hostile-"+std::to_string(revision);
  SemanticEvent outcome;outcome.event_id=new_uuid();outcome.scope=owner;outcome.sequence=revision;outcome.operation_id=batch.operation_id;
  outcome.source_revision=revision;outcome.subject_ids={batch.deltas[0].component.entity_id};outcome.provenance.source_id="fixture";
  outcome.payload=RouteOutcome{outcome.subject_ids[0],true};batch.events.push_back(outcome);
  receipt.blob(1,key);receipt.text(2,batch.operation_id);receipt.blob(3,unsigned_bytes(revision));receipt.blob(4,gameplay_codec::encode_batch(batch));receipt.write();
  event.blob(1,key);event.text(2,outcome.event_id);event.blob(3,unsigned_bytes(revision));event.text(4,batch.operation_id);event.write();
 };
 for(int page=0;page<18;++page) {
  GameplayChangeBatch batch;
  for(int item=0;item<15;++item) {
   ComponentRecord record{new_uuid(),"large.State",1,{}};entities.push_back(record.entity_id);
   for(const auto& field:registry[0].fields) record.fields.emplace(field.id,std::string(4096,'x'));
   batch.deltas.push_back({ComponentAction::upsert,std::move(record)});
  }
  append(batch);
 }
 for(std::size_t start=0;start<entities.size();start+=256) {
  GameplayChangeBatch batch;
  for(auto n=start;n<std::min(start+256,entities.size());++n) batch.deltas.push_back({ComponentAction::erase,{entities[n],"large.State",1,{}}});
  append(batch);
 }
 RawStatement head(raw.db,"UPDATE aibs_gameplay_meta SET revision=?2,sequence=?2 WHERE scope=?1");head.blob(1,key);head.blob(2,unsigned_bytes(revision));head.write();
 raw.execute("COMMIT");
}
}
int main() {
 try {
  const auto owner=scope();const auto entity=new_uuid();const auto batch=repair(owner,entity);
  const auto folder=std::filesystem::temp_directory_path()/std::filesystem::path("aibs-gameplay-store-"+new_uuid());
  std::filesystem::create_directories(folder);const auto path=folder/"world.sqlite";
  {
   GameplayStore store(path,owner,schemas());
   auto fresh=store.recover();require(fresh.revision==0 && fresh.sequence==0 && fresh.components.empty() && store.read_batches(0).empty(),"new store is empty");
   const auto saved=store.commit(batch);
   require(saved.status==GameplayStoreStatus::committed && saved.acknowledgement.scope==owner &&
    saved.acknowledgement.operation_id==batch.operation_id && saved.acknowledgement.revision==1 &&
    saved.acknowledgement.phase==GameplayPhase::durably_committed,"COMMIT returns matching durable receipt");
   require(store.commit(batch).status==GameplayStoreStatus::retry,"exact retry does not duplicate data");
   require(store.contains_event(batch.events[0].event_id) && !store.contains_event(new_uuid()),"scoped event index distinguishes present and missing UUIDs");
   bool invalid_event=false;try { store.contains_event("not-a-uuid"); } catch(const std::invalid_argument&) { invalid_event=true; }
   require(invalid_event,"event identity lookup rejects an invalid UUID before SQL binding");
   auto conflict=batch;conflict.deltas[0].component.fields["capacity"]=90.0;
   require(store.commit(conflict).status==GameplayStoreStatus::rejected,"operation ID conflict rejects");
   auto gap=repair(owner,entity,3,3,"gap");require(store.commit(gap).status==GameplayStoreStatus::rejected,"revision gap rejects");
   auto duplicate=repair(owner,entity,2,2,"duplicate-event");duplicate.events[0].event_id=batch.events[0].event_id;
   require(store.commit(duplicate).status==GameplayStoreStatus::rejected,"historical event identity is unique");
   auto foreign=batch;foreign.scope.branch_id="foreign";require(store.commit(foreign).status==GameplayStoreStatus::rejected,"foreign scope rejects");
   auto recovered=store.recover();
   require(recovered.scope==owner && recovered.revision==1 && recovered.sequence==1 && recovered.components.size()==1 &&
    recovered.components[0]==batch.deltas[0].component && store.read_batches(0)==std::vector<GameplayChangeBatch>{batch} && store.lookup_batch(batch.operation_id)==batch,
    "components, semantic event and exact retry bytes persist atomically without numeric loss");
   require(store.verify().ok,"integrity and relational recovery verification");
  }
  {
   GameplayStore reopened(path,owner,schemas());require(reopened.commit(batch).status==GameplayStoreStatus::retry,"exact retry survives reopen");
   auto erase=repair(owner,entity,2,2,"erase");erase.deltas[0].action=ComponentAction::erase;erase.deltas[0].component.fields.clear();
   erase.events[0].payload=RouteOutcome{entity,true};require(reopened.commit(erase).status==GameplayStoreStatus::committed,"erase and semantic outcome commit together");
   const auto recovered=reopened.recover();require(recovered.components.empty() && recovered.revision==2 && recovered.sequence==2 && reopened.read_batches(0).size()==2 && reopened.read_batches(1).size()==1,"erase survives durable recovery");
  }
  bool incompatible=false;try { auto changed=schemas();changed[0].fields[0].maximum=99;GameplayStore rejected(path,owner,changed); } catch(const std::exception&) { incompatible=true; }
  require(incompatible,"changed component schema requires an explicit migration");
  {
   auto other=owner;other.branch_id="isolated";GameplayStore isolated(path,other,schemas());
   require(isolated.recover().revision==0,"scope has independent head");const auto isolated_batch=repair(other,new_uuid());
   require(isolated.commit(isolated_batch).status==GameplayStoreStatus::committed,"same operation ID is isolated by complete scope");
   require(isolated.contains_event(isolated_batch.events[0].event_id) && !isolated.contains_event(batch.events[0].event_id),"event identity lookup cannot observe another scope's UUIDs");
   GameplayStore original(path,owner,schemas());require(original.recover().revision==2,"other scope cannot mutate original head");
  }
  {
   bool fail=true;GameplayStore rollback(folder/"rollback.sqlite",owner,schemas(),[&](GameplayStoreStage stage) {
    if(fail && stage==GameplayStoreStage::before_commit) { fail=false;throw std::runtime_error("injected before COMMIT"); }
   });
   require(rollback.commit(batch).status==GameplayStoreStatus::failed,"precommit fault reports failure");
   const auto empty=rollback.recover();require(empty.revision==0 && empty.components.empty() && rollback.read_batches(0).empty(),"precommit fault rolls back every table");
   require(rollback.commit(batch).status==GameplayStoreStatus::committed,"retry following rollback commits once");
  }
  {
   bool fail=true;GameplayStore uncertain(folder/"uncertain.sqlite",owner,schemas(),[&](GameplayStoreStage stage) {
    if(fail && stage==GameplayStoreStage::after_commit) { fail=false;throw std::runtime_error("lost completion after COMMIT"); }
   });
   require(uncertain.commit(batch).status==GameplayStoreStatus::committed,"after-commit observer cannot revoke an actual durable commit");
   require(uncertain.commit(batch).status==GameplayStoreStatus::retry && uncertain.recover().revision==1,"retry reconciles the committed transaction without duplication");
  }
  {
   GameplayStore seeded(folder/"seeded.sqlite",owner,schemas());GameplayStoreBaseline value;
   value.revision=70;value.sequence=11;value.components={batch.deltas[0].component};value.legacy_checkpoint={0,1,2,255};
   require(seeded.seed(value).status==GameplayStoreStatus::committed,"baseline and original legacy bytes commit together");
   require(seeded.seed(value).status==GameplayStoreStatus::retry,"identical baseline seed is idempotent");
   auto changed=value;changed.legacy_checkpoint.push_back(4);
   require(seeded.seed(changed).status==GameplayStoreStatus::rejected,"different baseline cannot replace original evidence");
   auto loaded=seeded.baseline();require(loaded && loaded->revision==70 && loaded->sequence==11 && loaded->components==value.components &&
    loaded->legacy_checkpoint==value.legacy_checkpoint,"baseline preserves typed components and raw original checkpoint");
   const auto continued=repair(owner,entity,71,12,"continued");
   require(seeded.commit(continued).status==GameplayStoreStatus::committed && seeded.recover().revision==71,"live gameplay continues from imported revision and sequence");
   require(seeded.read_batches(0).size()==1 && seeded.read_batches(70,1).size()==1,"bounded history begins after imported baseline");
   require(seeded.verify().ok,"baseline and continued stream validate together");
   GameplayStore unseeded(path,owner,schemas());require(unseeded.seed(value).status==GameplayStoreStatus::rejected,"cannot import over existing gameplay");
  }
  {
   GameplayStore exact(folder/"exact-baseline.sqlite",owner,schemas());GameplayStoreBaseline value;
   value.components={batch.deltas[0].component};value.components[0].fields["capacity"]=-0.0;
   require(exact.seed(value).status==GameplayStoreStatus::committed,"negative-zero baseline is valid");
   value.components[0].fields["capacity"]=0.0;
   require(exact.seed(value).status==GameplayStoreStatus::rejected,"baseline exact retry compares canonical typed bytes including negative zero");
  }
  {
   GameplayStore edge(folder/"uint64.sqlite",owner,schemas());GameplayStoreBaseline value;
   value.revision=std::numeric_limits<std::uint64_t>::max()-1;value.sequence=value.revision;
   require(edge.seed(value).status==GameplayStoreStatus::committed,"full-width unsigned baseline is stored without signed conversion");
   const auto last=repair(owner,entity,std::numeric_limits<std::uint64_t>::max(),std::numeric_limits<std::uint64_t>::max(),"last");
   require(edge.commit(last).status==GameplayStoreStatus::committed && edge.recover().revision==std::numeric_limits<std::uint64_t>::max() &&
    edge.read_batches(value.revision).size()==1 && edge.verify().ok,"unsigned head and sequence survive commit, ordered paging and integrity replay");
  }
  {
   GameplayStore* active=nullptr;bool nested_rejected=false;auto mutable_batch=batch;
   GameplayStore guarded(folder/"guarded.sqlite",owner,schemas(),[&](GameplayStoreStage stage) {
    if(stage==GameplayStoreStage::before_commit) {
     mutable_batch.operation_id="mutated-after-snapshot";nested_rejected=active->commit(batch).status==GameplayStoreStatus::rejected;
    }
   });active=&guarded;
   require(guarded.commit(mutable_batch).status==GameplayStoreStatus::committed && nested_rejected && guarded.lookup_batch(batch.operation_id)==batch &&
    !guarded.lookup_batch("mutated-after-snapshot"),"observer cannot mutate store recursively or alter the already prepared batch");
   bool page_rejected=false;try { guarded.read_batches(0,1,1); } catch(const std::invalid_argument&) { page_rejected=true; }
   require(page_rejected,"history explicitly rejects a page too small for its first durable receipt");
  }
  {
   const auto invalid=folder/"unsupported.sqlite";std::filesystem::copy_file(path,invalid);
   { std::fstream file(invalid,std::ios::in|std::ios::out|std::ios::binary);file.seekp(60);const char version[4]={0,0,0,2};file.write(version,4); }
   bool rejected=false;try { GameplayStore unsupported(invalid,owner,schemas()); } catch(const std::exception&) { rejected=true; }
   require(rejected,"unsupported database format fails closed without migration");
   const auto corrupt=folder/"corrupt.sqlite";{ std::ofstream file(corrupt,std::ios::binary);file<<"not a SQLite database"; }
   rejected=false;try { GameplayStore damaged(corrupt,owner,schemas()); } catch(const std::exception&) { rejected=true; }
   require(rejected,"corrupted database fails startup validation");
  }
  {
   ComponentSchema large{"large.State",1,{}};
   for(int n=0;n<64;++n) large.fields.push_back({"field-"+std::to_string(n),GameplayValueKind::text});
   const auto hostile=folder/"intermediate-overflow.sqlite";const std::vector<ComponentSchema> registry{large};
   hostile_intermediate_state(hostile,owner,registry);
   bool rejected=false;try { GameplayStore loaded(hostile,owner,registry); } catch(const std::invalid_argument& error) {
    rejected=std::string(error.what()).find("replay byte budget")!=std::string::npos;
   }
   require(rejected,"startup rejects history whose intermediate component state exceeds 64 MiB even when its final state is empty");
  }
  {
   const auto oversized=folder/"oversized-wire.sqlite";std::filesystem::copy_file(path,oversized);
   { RawDatabase raw(oversized);raw.execute("UPDATE aibs_gameplay_batches SET batch=zeroblob(4194305) WHERE operation='repair-1'"); }
   bool rejected=false;try { GameplayStore loaded(oversized,owner,schemas()); } catch(const std::invalid_argument& error) {
    rejected=std::string(error.what()).find("domain byte bound")!=std::string::npos;
   }
   require(rejected,"oversized persisted wire is rejected by its domain bound before vector copying");
   const auto oversized_legacy=folder/"oversized-legacy.sqlite";
   { GameplayStore seeded(oversized_legacy,owner,schemas());require(seeded.seed({}).status==GameplayStoreStatus::committed,"prepare empty baseline corruption fixture"); }
   { RawDatabase raw(oversized_legacy);raw.execute("UPDATE aibs_gameplay_baselines SET legacy=zeroblob(16777217)"); }
   rejected=false;try { GameplayStore loaded(oversized_legacy,owner,schemas()); } catch(const std::invalid_argument& error) {
    rejected=std::string(error.what()).find("domain byte bound")!=std::string::npos;
   }
   require(rejected,"oversized preserved checkpoint is rejected before vector copying");
   GameplayStore bounded(folder/"bounded-seed.sqlite",owner,schemas());GameplayStoreBaseline invalid;
   invalid.components={batch.deltas[0].component};invalid.components[0].fields["label"]=std::string(1024*1024,'x');
   require(bounded.seed(invalid).status==GameplayStoreStatus::rejected && !bounded.baseline() && bounded.recover().revision==0,
    "seed preflights invalid field bounds before copying or publishing its baseline");
  }
  {
   const auto missing=folder/"never-created.sqlite";bool rejected=false;
   try { GameplayStore::list_scopes(missing); } catch(const std::exception&) { rejected=true; }
   require(rejected && !std::filesystem::exists(missing),"read-only scope discovery never creates a missing database");
   const auto discovery=folder/"scope-discovery.sqlite";std::vector<GameplayScope> expected;
   for(int n=0;n<20;++n) {
    auto value=owner;value.world_id=new_uuid();value.timeline_id=new_uuid();value.branch_id="branch-"+std::to_string(n);
    value.context=static_cast<GameplayContext>(n%4);expected.push_back(value);GameplayStore created(discovery,value,schemas());
   }
   const auto size=std::filesystem::file_size(discovery);const auto modified=std::filesystem::last_write_time(discovery);
   auto read_bytes=[](const std::filesystem::path& file) { std::ifstream input(file,std::ios::binary);return std::vector<char>(std::istreambuf_iterator<char>(input),{}); };
   const auto original_bytes=read_bytes(discovery);
   const auto found=GameplayStore::list_scopes(discovery,20);
   require(found.size()==expected.size() && std::all_of(expected.begin(),expected.end(),[&](const auto& value) { return std::find(found.begin(),found.end(),value)!=found.end(); }),
    "read-only discovery returns every exact project/world/branch/timeline/context scope");
   require(std::filesystem::file_size(discovery)==size && std::filesystem::last_write_time(discovery)==modified && read_bytes(discovery)==original_bytes,"scope discovery does not modify database bytes or publication time");
   rejected=false;try { GameplayStore::list_scopes(discovery,19); } catch(const std::invalid_argument&) { rejected=true; }
   require(rejected,"scope limit exhaustion is explicit and cannot hide extra restart candidates");
   const auto oversized=folder/"oversized-scope.sqlite";std::filesystem::copy_file(discovery,oversized);
   { RawDatabase raw(oversized);raw.execute("UPDATE aibs_gameplay_meta SET scope=zeroblob(618) WHERE scope=(SELECT scope FROM aibs_gameplay_meta LIMIT 1)"); }
   rejected=false;try { GameplayStore::list_scopes(oversized); } catch(const std::invalid_argument& error) { rejected=std::string(error.what()).find("domain byte bound")!=std::string::npos; }
   require(rejected,"persisted scope size is checked before allocating its byte vector");
   const auto malformed=folder/"malformed-scope.sqlite";std::filesystem::copy_file(discovery,malformed);
   { auto invalid=gameplay_codec::encode_scope(expected[0]);invalid[16]=1;invalid[17]=1;invalid[18]=0;invalid[19]=0;
    RawDatabase raw(malformed);RawStatement update(raw.db,"UPDATE aibs_gameplay_meta SET scope=?1 WHERE scope=(SELECT scope FROM aibs_gameplay_meta LIMIT 1)");update.blob(1,invalid);update.write(); }
   rejected=false;try { GameplayStore::list_scopes(malformed); } catch(const std::invalid_argument&) { rejected=true; }
   require(rejected,"malformed scope field length is rejected before allocating its decoded string");
   const auto foreign=folder/"foreign-application.sqlite";std::filesystem::copy_file(discovery,foreign);
   { RawDatabase raw(foreign);raw.execute("PRAGMA application_id=7"); }
   rejected=false;try { GameplayStore::list_scopes(foreign); } catch(const std::invalid_argument&) { rejected=true; }
   require(rejected,"foreign application ID is not a gameplay database");
   const auto future=folder/"future-discovery.sqlite";std::filesystem::copy_file(discovery,future);
   { RawDatabase raw(future);raw.execute("PRAGMA user_version=2"); }
   rejected=false;try { GameplayStore::list_scopes(future); } catch(const std::invalid_argument&) { rejected=true; }
   require(rejected,"future database versions cannot be discovered implicitly");
   const auto unknown=folder/"unknown.sqlite";{ RawDatabase raw(unknown);raw.execute("CREATE TABLE unrelated(value TEXT)"); }
   rejected=false;try { GameplayStore::list_scopes(unknown); } catch(const std::invalid_argument&) { rejected=true; }
   require(rejected,"unrecognized SQLite database rejects metadata discovery");
   rejected=false;try { GameplayStore::list_scopes(folder/"corrupt.sqlite"); } catch(const std::exception&) { rejected=true; }
   require(rejected,"corrupt database rejects read-only discovery");
  }
  std::cout<<"gameplay SQLite store contracts passed\n";return 0;
 } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
