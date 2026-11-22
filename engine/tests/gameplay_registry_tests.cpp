#include <aibs/gameplay_store.hpp>
#include <aibs/gameplay_codec.hpp>
#include <sqlite3.h>
#include <algorithm>
#include <filesystem>
#include <iostream>
#include <stdexcept>

using namespace aibs;
namespace {
void require(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
GameplayScope scope() { return {"registry-proof",new_uuid(),"main",new_uuid(),GameplayContext::player_world}; }
std::vector<ComponentSchema> original() { return {{"old.Power",1,{{"capacity",GameplayValueKind::number,true,-0.0,100}}}}; }
std::vector<ComponentSchema> additions() {
 auto values=original();values.push_back({"m3.Door",1,{{"open",GameplayValueKind::boolean}}});
 values.push_back({"m3.Power",1,{{"energy",GameplayValueKind::integer}}});
 values.push_back({"m3.Quest",1,{{"stage",GameplayValueKind::text}}});return values;
}
GameplayChangeBatch repair(const GameplayScope& owner,const std::string& entity,std::uint64_t revision,std::uint64_t sequence,std::string operation) {
 GameplayChangeBatch batch;batch.scope=owner;batch.operation_id=std::move(operation);batch.expected_revision=revision-1;batch.revision=revision;
 batch.deltas.push_back({ComponentAction::upsert,{entity,"old.Power",1,{{"capacity",50.0}}}});
 SemanticEvent event;event.event_id=new_uuid();event.scope=owner;event.sequence=sequence;event.operation_id=batch.operation_id;
 event.subject_ids={entity};event.source_revision=revision;event.provenance.source_id="registry.repair.v1";event.payload=RepairOutcome{entity,0,50};
 batch.events.push_back(std::move(event));return batch;
}
int database_version(const std::filesystem::path& path) {
 sqlite3* db=nullptr;require(sqlite3_open_v2(path.string().c_str(),&db,SQLITE_OPEN_READONLY,nullptr)==SQLITE_OK,"read format fixture");
 sqlite3_stmt* statement=nullptr;const auto prepared=sqlite3_prepare_v2(db,"PRAGMA user_version",-1,&statement,nullptr);
 require(prepared==SQLITE_OK && sqlite3_step(statement)==SQLITE_ROW,"read database format");const auto value=sqlite3_column_int(statement,0);
 sqlite3_finalize(statement);sqlite3_close(db);return value;
}
void corrupt(const std::filesystem::path& path,const char* sql) {
 sqlite3* db=nullptr;require(sqlite3_open(path.string().c_str(),&db)==SQLITE_OK,"open corruption fixture");
 const auto result=sqlite3_exec(db,sql,nullptr,nullptr,nullptr);sqlite3_close(db);require(result==SQLITE_OK,"write corruption fixture");
}
bool same(const std::vector<ComponentSchema>& a,const std::vector<ComponentSchema>& b) { return gameplay_codec::encode_schemas(a)==gameplay_codec::encode_schemas(b); }
}
int main() {
 try {
  const auto folder=std::filesystem::temp_directory_path()/("aibs-registry-"+new_uuid());std::filesystem::create_directories(folder);
  const auto owner=scope();const auto entity=new_uuid();const auto path=folder/"old-world.sqlite";
  GameplayStore old_connection(path,owner,original());GameplayStoreBaseline baseline;
  baseline.revision=70;baseline.sequence=11;baseline.components={{entity,"old.Power",1,{{"capacity",10.0}}}};baseline.legacy_checkpoint={0,255,42,1};
  require(old_connection.seed(baseline).status==GameplayStoreStatus::committed,"original evidence seeded");
  const auto first=repair(owner,entity,71,12,"old-repair");require(old_connection.commit(first).status==GameplayStoreStatus::committed,"old event committed");
  auto other=owner;other.branch_id="untouched";GameplayStore foreign(path,other,original());
  require(database_version(path)==1 && same(GameplayStore::inspect_registry(path,owner),original()),"old world remains format1 until explicit registry extension");
  const auto extended=GameplayStore::extend_registry(path,owner,original(),additions(),"m3.add-core-types",71,12);
  require(extended.status==GameplayStoreStatus::committed && database_version(path)==2,"explicit registry transaction upgrades format2");
  require(same(GameplayStore::inspect_registry(path,owner),additions()) && same(GameplayStore::inspect_registry(path,other),original()),"registry extension is fully scoped");
  const auto discovered=GameplayStore::list_scopes(path);require(discovered.size()==2 && std::find(discovered.begin(),discovered.end(),owner)!=discovered.end(),"format2 supports read-only scope discovery");
  require(old_connection.commit(repair(owner,entity,72,13,"stale-connection")).status==GameplayStoreStatus::rejected,"stale old-registry connection cannot commit");
  bool rejected=false;try { GameplayStore stale(path,owner,original()); } catch(const std::exception&) { rejected=true; }
  require(rejected,"old registry must not silently reopen evolved scope");
  GameplayStore evolved(path,owner,additions());const auto recovered=evolved.recover();const auto preserved=evolved.baseline();
  require(recovered.components==std::vector<ComponentRecord>{first.deltas[0].component} && preserved && preserved->revision==baseline.revision &&
   preserved->sequence==baseline.sequence && preserved->components==baseline.components && preserved->legacy_checkpoint==baseline.legacy_checkpoint &&
   evolved.lookup_batch(first.operation_id)==first && evolved.read_batches(0)==std::vector<GameplayChangeBatch>{first} && evolved.contains_event(first.events[0].event_id),
   "additive registry preserves exact components, UUIDs, baseline/raw evidence, original event and retry receipt");
  require(recovered.revision==71 && recovered.sequence==12 && evolved.verify().ok && foreign.recover().revision==0 && foreign.verify().ok,"registry migration fabricates no gameplay head or event and leaves other scope intact");
  require(evolved.commit(first).status==GameplayStoreStatus::retry,"original gameplay exact retry remains valid");
  auto reordered=additions();std::reverse(reordered.begin(),reordered.end());
  require(GameplayStore::extend_registry(path,owner,original(),reordered,"m3.add-core-types",71,12).status==GameplayStoreStatus::retry,"canonical exact migration retry is idempotent");
  auto conflict=additions();conflict.push_back({"m3.Other",1,{{"active",GameplayValueKind::boolean}}});
  require(GameplayStore::extend_registry(path,owner,original(),conflict,"m3.add-core-types",71,12).status==GameplayStoreStatus::rejected,"migration ID conflicting target rejects");
  require(GameplayStore::extend_registry(path,owner,additions(),conflict,"wrong-head",70,12).status==GameplayStoreStatus::rejected,"migration revision precondition is exact");
  require(GameplayStore::extend_registry(path,owner,additions(),conflict,"wrong-sequence",71,11).status==GameplayStoreStatus::rejected,"migration sequence precondition is exact");
  require(GameplayStore::extend_registry(path,owner,original(),conflict,"stale-registry",71,12).status==GameplayStoreStatus::rejected,"migration registry precondition is exact");
  require(GameplayStore::extend_registry(path,owner,additions(),additions(),"no-addition",71,12).status==GameplayStoreStatus::rejected,"unchanged unrecorded migration rejects");
  auto removed=additions();removed.erase(removed.begin());
  require(GameplayStore::extend_registry(path,owner,additions(),removed,"remove-old",71,12).status==GameplayStoreStatus::rejected,"existing definitions cannot be removed");
  auto changed=conflict;changed[0].fields[0].minimum=0.0;
  require(GameplayStore::extend_registry(path,owner,additions(),changed,"change-zero-bits",71,12).status==GameplayStoreStatus::rejected,"existing numeric bound bits including negative zero cannot change");
  require(evolved.commit(repair(owner,entity,72,13,"after-extension")).status==GameplayStoreStatus::committed,"old component and payload versions continue after migration");
  auto new_types=repair(owner,new_uuid(),73,14,"new-component-types");const auto door=new_types.deltas[0].component.entity_id;
  new_types.deltas={{ComponentAction::upsert,{door,"m3.Door",1,{{"open",false}}}},
   {ComponentAction::upsert,{new_uuid(),"m3.Power",1,{{"energy",std::int64_t{42}}}}},
   {ComponentAction::upsert,{new_uuid(),"m3.Quest",1,{{"stage",std::string("started")}}}}};
  new_types.events[0].payload=ConstructionOutcome{door,true};
  require(evolved.commit(new_types).status==GameplayStoreStatus::committed,"new Door, Power and Quest component definitions can commit after explicit registration");
  require(GameplayStore::extend_registry(path,owner,additions(),conflict,"m3.add-other",73,14).status==GameplayStoreStatus::committed,"second additive step extends canonical receipt chain");
  require(GameplayStore::extend_registry(path,owner,original(),additions(),"m3.add-core-types",71,12).status==GameplayStoreStatus::retry,"old exact migration retry survives later extension and gameplay");
  GameplayStore latest(path,owner,conflict);require(latest.verify().ok && latest.recover().revision==73 && latest.recover().components.size()==4 && latest.read_batches(0).size()==3,"registry receipt chain and prefix heads verify with unchanged game history");
  {
   const auto rollback_path=folder/"rollback.sqlite";{ GameplayStore empty(rollback_path,owner,original()); }
   auto result=GameplayStore::extend_registry(rollback_path,owner,original(),additions(),"rollback",0,0,[](GameplayStoreStage stage) { if(stage==GameplayStoreStage::before_commit) throw std::runtime_error("injected migration rollback"); });
   require(result.status==GameplayStoreStatus::failed && database_version(rollback_path)==1 && same(GameplayStore::inspect_registry(rollback_path,owner),original()),"precommit failure rolls back format, registry and migration receipt together");
   result=GameplayStore::extend_registry(rollback_path,owner,original(),additions(),"rollback",0,0,[](GameplayStoreStage stage) { if(stage==GameplayStoreStage::after_commit) throw std::runtime_error("postcommit observer"); });
   require(result.status==GameplayStoreStatus::committed && database_version(rollback_path)==2,"postcommit observer cannot revoke actual migration commit");
  }
  {
   const auto guarded_path=folder/"guarded.sqlite";{ GameplayStore empty(guarded_path,owner,original()); }
   auto expected=original(),target=additions();auto mutable_scope=owner;std::string identifier="immutable-request";bool nested=false;
   const auto result=GameplayStore::extend_registry(guarded_path,mutable_scope,expected,target,identifier,0,0,[&](GameplayStoreStage stage) {
    if(stage!=GameplayStoreStage::before_commit) return;
    expected.clear();target.clear();mutable_scope.branch_id="mutated";identifier="changed";
    nested=GameplayStore::extend_registry(guarded_path,owner,original(),additions(),"nested",0,0).status==GameplayStoreStatus::rejected;
   });
   require(result.status==GameplayStoreStatus::committed && nested && same(GameplayStore::inspect_registry(guarded_path,owner),additions()),"migration snapshots caller aliases and rejects recursive registry mutation");
   require(GameplayStore::extend_registry(guarded_path,owner,original(),additions(),"immutable-request",0,0).status==GameplayStoreStatus::retry,"immutable original migration identity was retained");
  }
  {
   const auto missing=folder/"missing.sqlite";
   require(GameplayStore::extend_registry(missing,owner,original(),additions(),"missing",0,0).status==GameplayStoreStatus::failed && !std::filesystem::exists(missing),"migration must not create a missing database");
   rejected=false;try { GameplayStore::inspect_registry(missing,owner); } catch(const std::exception&) { rejected=true; }
   require(rejected && !std::filesystem::exists(missing),"registry inspection is read-only and never creates missing databases");
  }
  {
   const auto unchanged=folder/"precondition.sqlite";{ GameplayStore empty(unchanged,owner,original()); }
   require(GameplayStore::extend_registry(unchanged,owner,original(),additions(),"bad-head",1,0).status==GameplayStoreStatus::rejected && database_version(unchanged)==1,
    "failed preconditions cannot upgrade the old database format");
   corrupt(unchanged,"PRAGMA user_version=3");rejected=false;
   try { GameplayStore::inspect_registry(unchanged,owner); } catch(const std::exception&) { rejected=true; }require(rejected,"future format rejects registry inspection");
   rejected=false;try { GameplayStore::list_scopes(unchanged); } catch(const std::exception&) { rejected=true; }require(rejected,"future format rejects scope discovery");
   rejected=false;try { GameplayStore future(unchanged,owner,original()); } catch(const std::exception&) { rejected=true; }require(rejected,"future format rejects store reopen");
  }
  corrupt(path,"UPDATE aibs_gameplay_registry_migrations SET ordinal=ordinal+10 WHERE migration_id='m3.add-other'");
  rejected=false;try { GameplayStore invalid(path,owner,conflict); } catch(const std::exception&) { rejected=true; }
  require(rejected,"corrupt migration ordinal chain fails full startup validation");
  {
   const auto historical=folder/"historical-definition.sqlite";
   { GameplayStore old(historical,owner,original());require(old.seed(baseline).status==GameplayStoreStatus::committed,"historical registry fixture seeded"); }
   require(GameplayStore::extend_registry(historical,owner,original(),additions(),"historical",70,11).status==GameplayStoreStatus::committed,"historical registry fixture extended");
   sqlite3* db=nullptr;require(sqlite3_open(historical.string().c_str(),&db)==SQLITE_OK,"open historical receipt fixture");sqlite3_stmt* update=nullptr;
   require(sqlite3_prepare_v2(db,"UPDATE aibs_gameplay_registry_migrations SET expected_registry=?1",-1,&update,nullptr)==SQLITE_OK,"prepare historical receipt fixture");
   const auto forged=gameplay_codec::encode_schemas({additions()[1]});
   require(sqlite3_bind_blob64(update,1,forged.data(),forged.size(),SQLITE_TRANSIENT)==SQLITE_OK && sqlite3_step(update)==SQLITE_DONE,"forge historical receipt definition");
   sqlite3_finalize(update);sqlite3_close(db);rejected=false;
   try { GameplayStore invalid(historical,owner,additions()); } catch(const std::exception&) { rejected=true; }
   require(rejected,"receipt chain cannot introduce a component type after it already existed in the immutable baseline");
  }
  std::cout<<"PASS: explicit additive registry evolution, exact scoped receipts, preserved M2 evidence and atomic format2\n";return 0;
 } catch(const std::exception& error) { std::cerr<<"FAIL: "<<error.what()<<'\n';return 1; }
}
