#include <aibs/gameplay_store.hpp>
#include <aibs/gameplay_codec.hpp>
#include <sqlite3.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

using namespace aibs;
namespace fs = std::filesystem;
namespace {
using Bytes = gameplay_codec::Bytes;
using Tree = std::map<fs::path,std::optional<std::vector<char>>>;
void require(bool condition,const char* message) {
 if(!condition) throw std::runtime_error(message);
}
std::vector<ComponentSchema> schemas() {
 return {{"test.Power",1,{{"capacity",GameplayValueKind::number,true,0,100},
  {"reserve",GameplayValueKind::number},{"counter",GameplayValueKind::integer},
  {"enabled",GameplayValueKind::boolean},{"label",GameplayValueKind::text}}}};
}
Tree snapshot(const fs::path& root) {
 Tree result;
 for(const auto& entry:fs::recursive_directory_iterator(root)) {
  require(!entry.is_symlink(),"Unexpected redirected evidence member");
  const auto relative=entry.path().lexically_relative(root);
  if(entry.is_directory()) { result.emplace(relative,std::nullopt);continue; }
  require(entry.is_regular_file(),"Unexpected non-file evidence member");
  std::ifstream file(entry.path(),std::ios::binary);
  require(file.good(),"Cannot read evidence bytes");
  std::vector<char> bytes{std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>()};
  require(!file.bad(),"Incomplete evidence byte snapshot");
  result.emplace(relative,std::move(bytes));
 }
 return result;
}
template<class Operation>
void inspect_unchanged(const fs::path& root,Operation&& operation,bool should_reject,const char* label) {
 const auto before=snapshot(root);bool rejected=false;
 try { operation(); } catch(const std::exception&) { rejected=true; }
 require(snapshot(root)==before,"Inspection changed file bytes or directory members");
 require(rejected==should_reject,label);
 std::cout<<"PASS "<<label<<'\n';
}
bool exact(const GameplayStoreRecovery& a,const GameplayStoreRecovery& b) {
 if(a.scope!=b.scope||a.revision!=b.revision||a.sequence!=b.sequence||a.components.size()!=b.components.size()) return false;
 for(std::size_t n=0;n<a.components.size();++n)
  if(gameplay_codec::encode_component(a.components[n])!=gameplay_codec::encode_component(b.components[n])) return false;
 return true;
}
class RawDatabase {
public:
 sqlite3* db=nullptr;
 explicit RawDatabase(const fs::path& path) {
  const auto encoded=path.u8string();const std::string name(reinterpret_cast<const char*>(encoded.data()),encoded.size());
  const auto opened=sqlite3_open_v2(name.c_str(),&db,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE,nullptr);
  if(opened!=SQLITE_OK) { if(db) sqlite3_close_v2(db);db=nullptr;throw std::runtime_error("Cannot open raw fixture"); }
 }
 ~RawDatabase() { if(db) sqlite3_close_v2(db); }
 RawDatabase(const RawDatabase&)=delete;
 RawDatabase& operator=(const RawDatabase&)=delete;
 void execute(const char* sql) {
  require(sqlite3_exec(db,sql,nullptr,nullptr,nullptr)==SQLITE_OK,"Cannot alter corruption fixture");
 }
 void replace_blob(const char* sql,const Bytes& bytes) {
  sqlite3_stmt* raw=nullptr;
  require(sqlite3_prepare_v2(db,sql,-1,&raw,nullptr)==SQLITE_OK,"Cannot prepare fixture blob update");
  const std::unique_ptr<sqlite3_stmt,decltype(&sqlite3_finalize)> statement(raw,&sqlite3_finalize);
  require(sqlite3_bind_blob64(statement.get(),1,bytes.data(),bytes.size(),SQLITE_TRANSIENT)==SQLITE_OK,"Cannot bind fixture blob");
  require(sqlite3_step(statement.get())==SQLITE_DONE,"Cannot write fixture blob");
 }
};
GameplayStoreRecovery make_valid(const fs::path& path,const GameplayScope& owner,const std::string& entity) {
 GameplayStore store(path,owner,schemas());
 ComponentRecord initial{entity,"test.Power",1,{{"capacity",10.0},{"reserve",-0.0},
  {"counter",std::numeric_limits<std::int64_t>::max()},{"enabled",false},{"label",std::string("x\0y",3)}}};
 GameplayStoreBaseline baseline;baseline.revision=7;baseline.sequence=11;
 baseline.components={initial};baseline.legacy_checkpoint={0,255,42,1};
 require(store.seed(baseline).status==GameplayStoreStatus::committed,"Cannot seed valid immutable baseline");
 GameplayChangeBatch batch;batch.scope=owner;batch.operation_id="readonly.repair";
 batch.expected_revision=7;batch.revision=8;
 auto repaired=initial;repaired.fields["capacity"]=100.0;repaired.fields["enabled"]=true;
 batch.deltas.push_back({ComponentAction::upsert,std::move(repaired)});
 SemanticEvent event;event.event_id=new_uuid();event.scope=owner;event.sequence=12;
 event.operation_id=batch.operation_id;event.source_revision=8;event.subject_ids={entity};
 event.provenance={GameplayProvenance::gameplay_rule,"readonly.repair.v1"};event.payload=RepairOutcome{entity,10,100};
 batch.events.push_back(std::move(event));
 require(store.commit(batch).status==GameplayStoreStatus::committed,"Cannot commit valid semantic receipt");
 require(store.verify().ok,"Ordinary recovery fixture does not verify");
 return store.recover();
}
#ifdef _WIN32
class DenyFileWrites {
 HANDLE handle=INVALID_HANDLE_VALUE;
public:
 explicit DenyFileWrites(const fs::path& path) {
  handle=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
  require(handle!=INVALID_HANDLE_VALUE,"Cannot acquire fixture write-denial handle");
 }
 ~DenyFileWrites() { if(handle!=INVALID_HANDLE_VALUE) CloseHandle(handle); }
 DenyFileWrites(const DenyFileWrites&)=delete;
 DenyFileWrites& operator=(const DenyFileWrites&)=delete;
};
#endif
}

int main(int argc,char** argv) {
 fs::path output;
 try {
  require(argc==2,"Usage: gameplay_readonly_tests NEWOUTPUTDIR");
  require(argv[1][0]!='\0',"An explicit new output directory is required");
  output=fs::absolute(fs::path(argv[1])).lexically_normal();
  require(!fs::exists(output),"Refusing an existing output directory");
  require(fs::create_directories(output),"Cannot create new evidence directory");
  const GameplayScope owner{"readonly-contract",new_uuid(),"main",new_uuid(),GameplayContext::player_world};
  const auto registry=schemas();const auto entity=new_uuid();
  const auto missing=output/"missing.sqlite";
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(missing,owner,registry); },true,
   "Missing database rejects without creating a file or sidecar");
  require(!fs::exists(missing),"Inspection created the missing database");

  const auto empty=output/"empty.sqlite";
  { std::ofstream file(empty,std::ios::binary);require(file.good(),"Cannot create empty fixture"); }
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(empty,owner,registry); },true,
   "Existing empty database rejects without initialization");
  const auto foreign=output/"foreign.sqlite";
  { RawDatabase db(foreign);db.execute("CREATE TABLE foreign_data(value TEXT);INSERT INTO foreign_data VALUES('retain me')"); }
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(foreign,owner,registry); },true,
   "Foreign SQLite database rejects without schema or journal changes");

  const auto valid=output/"valid.sqlite";const auto ordinary=make_valid(valid,owner,entity);
  require(ordinary.revision==8&&ordinary.sequence==12&&ordinary.components.size()==1,"Unexpected valid fixture head");
  inspect_unchanged(output,[&] {
   require(exact(GameplayStore::inspect_recovery(valid,owner,registry),ordinary),"Recovery differs from ordinary recovery");
   require(exact(GameplayStore::inspect_recovery(valid,owner,registry),ordinary),"Repeated inspection differs");
  },false,"Baseline plus committed receipt recover exact typed bytes without WAL or metadata writes");

  auto other=owner;other.timeline_id=new_uuid();
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(valid,other,registry); },true,
   "Wrong timeline rejects without inserting a scope");
  auto changed=registry;changed[0].fields[0].maximum=99;
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(valid,owner,changed); },true,
   "Wrong expected registry rejects without migration");

  const auto component=output/"corrupt-component.sqlite";fs::copy_file(valid,component);
  auto altered=ordinary.components.front();altered.fields["capacity"]=75.0;
  { RawDatabase db(component);db.replace_blob("UPDATE aibs_gameplay_components SET record=?1",gameplay_codec::encode_component(altered)); }
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(component,owner,registry); },true,
   "Canonical component inconsistent with durable replay rejects unchanged");
  const auto head=output/"corrupt-head.sqlite";fs::copy_file(valid,head);
  { RawDatabase db(head);db.execute("UPDATE aibs_gameplay_meta SET revision=X'0000000000000009'"); }
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(head,owner,registry); },true,
   "Head inconsistent with durable receipt rejects unchanged");
  const auto receipt=output/"corrupt-semantic-index.sqlite";fs::copy_file(valid,receipt);
  { RawDatabase db(receipt);db.execute("DELETE FROM aibs_gameplay_events"); }
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(receipt,owner,registry); },true,
   "Missing semantic index receipt rejects unchanged");
  const auto wire=output/"corrupt-receipt-wire.sqlite";fs::copy_file(valid,wire);
  { RawDatabase db(wire);db.execute("UPDATE aibs_gameplay_batches SET batch=CAST(batch||X'00' AS BLOB)"); }
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(wire,owner,registry); },true,
   "Noncanonical durable receipt bytes reject unchanged");

  const auto hot=output/"hot-wal.sqlite";const auto old_head=make_valid(hot,owner,entity);
  const auto old_main=snapshot(output).at(hot.filename()).value();
  GameplayStoreRecovery wal_head;
  {
   // This real reader pins the old snapshot while the public store commits.
   // Its final close deliberately retains WAL/SHM instead of checkpointing.
   RawDatabase keeper(hot);
   require(sqlite3_db_config(keeper.db,SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,1,nullptr)==SQLITE_OK,
    "Cannot disable fixture checkpoint on close");
   require(sqlite3_wal_autocheckpoint(keeper.db,0)==SQLITE_OK,"Cannot disable fixture auto-checkpoint");
   int persist=1;
   require(sqlite3_file_control(keeper.db,"main",SQLITE_FCNTL_PERSIST_WAL,&persist)==SQLITE_OK,
    "Cannot retain fixture WAL sidecars");
   keeper.execute("BEGIN;SELECT count(*) FROM aibs_gameplay_meta");
   {
    GameplayStore writer(hot,owner,registry);
    GameplayChangeBatch batch;batch.scope=owner;batch.operation_id="readonly.hot-wal";
    batch.expected_revision=old_head.revision;batch.revision=old_head.revision+1;
    auto record=old_head.components.front();record.fields["capacity"]=35.0;
    batch.deltas.push_back({ComponentAction::upsert,std::move(record)});
    SemanticEvent event;event.event_id=new_uuid();event.scope=owner;event.operation_id=batch.operation_id;
    event.sequence=old_head.sequence+1;event.source_revision=batch.revision;event.subject_ids={entity};
    event.provenance={GameplayProvenance::gameplay_rule,"readonly.hot-wal.v1"};event.payload=RouteOutcome{entity,true};
    batch.events.push_back(std::move(event));
    const auto committed=writer.commit(batch);
    if(committed.status!=GameplayStoreStatus::committed)
     throw std::runtime_error("Cannot commit synthetic hot-WAL fixture: "+committed.message);
    wal_head=writer.recover();
   }
   keeper.execute("ROLLBACK");
  }
  const auto wal=fs::path(hot.wstring()+L"-wal"),shm=fs::path(hot.wstring()+L"-shm");
  require(fs::exists(wal)&&fs::file_size(wal)>32&&fs::exists(shm)&&fs::file_size(shm)>=32768,
   "Hot-WAL fixture did not retain actual frames and shared memory");
  require(snapshot(output).at(hot.filename()).value()==old_main,"Fixture unexpectedly checkpointed its old main file");
  require(wal_head.revision==9&&wal_head.sequence==13&&!exact(wal_head,old_head),"Hot-WAL fixture lacks a newer committed head");
  const auto main_only=output/"hot-wal-main-only.sqlite";fs::copy_file(hot,main_only);
  inspect_unchanged(output,[&] {
   require(exact(GameplayStore::inspect_recovery(main_only,owner,registry),old_head),"Old main file did not retain old head");
  },false,"Main-file-only control recovers the older head without an immutable URI");
  inspect_unchanged(output,[&] {
   require(exact(GameplayStore::inspect_recovery(hot,owner,registry),wal_head),"Inspection ignored committed WAL frames");
  },false,"Hot WAL recovers the newer exact head without changing main, WAL, SHM, or directory members");

  const auto active=output/"active-writer.sqlite";fs::copy_file(valid,active);
  {
   RawDatabase writer(active);writer.execute("BEGIN IMMEDIATE");
   inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(active,owner,registry); },true,
    "An actual SQLite write transaction excludes inspection without source changes");
   writer.execute("ROLLBACK");
  }
  inspect_unchanged(output,[&] {
   require(exact(GameplayStore::inspect_recovery(active,owner,registry),ordinary),"Writer exclusion poisoned recovery");
  },false,"Inspection succeeds unchanged after the legitimate writer releases ownership");

  const auto journal_work=output/"journal-working.sqlite",journal_hot=output/"hot-journal.sqlite";
  const auto work_journal=fs::path(journal_work.wstring()+L"-journal");
  const auto hot_journal=fs::path(journal_hot.wstring()+L"-journal");
  fs::copy_file(valid,journal_work);
  {
   RawDatabase writer(journal_work);
   writer.execute("PRAGMA journal_mode=DELETE;PRAGMA synchronous=FULL;BEGIN IMMEDIATE;"
    "UPDATE aibs_gameplay_components SET record=zeroblob(length(record))");
   // Flush uncommitted pages to make an authentic recoverable hot journal,
   // then copy the paused pair instead of terminating a fixture process.
   require(sqlite3_db_cacheflush(writer.db)==SQLITE_OK,"Cannot flush pending rollback-journal fixture");
   require(fs::exists(work_journal),"Pending rollback fixture has no actual journal");
   fs::copy_file(journal_work,journal_hot);fs::copy_file(work_journal,hot_journal);
   writer.execute("ROLLBACK");
  }
  const auto journal_bytes=snapshot(output).at(hot_journal.filename()).value();
  require(journal_bytes.size()>512&&std::string(journal_bytes.data(),8)==std::string("\xd9\xd5\x05\xf9\x20\xa1\x63\xd7",8),
   "Rollback fixture lacks the synced SQLite journal header");
  const auto journal_control=output/"journal-recovery-control.sqlite";
  fs::copy_file(journal_hot,journal_control);
  fs::copy_file(hot_journal,fs::path(journal_control.wstring()+L"-journal"));
  {
   GameplayStore recovered(journal_control,owner,registry);
   require(exact(recovered.recover(),ordinary),"Real rollback recovery control failed to restore the old committed state");
  }
  inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(journal_hot,owner,registry); },true,
   "Authentic hot rollback journal rejects without replay, deletion, or source writes");

#ifdef _WIN32
  {
   const auto writer=CreateFileW(wal.c_str(),GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,
    nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
   require(writer!=INVALID_HANDLE_VALUE,"Cannot acquire actual WAL-only writer handle");
   struct CloseHandleOnExit { HANDLE value;~CloseHandleOnExit() { CloseHandle(value); } } owner_handle{writer};
   inspect_unchanged(output,[&] { (void)GameplayStore::inspect_recovery(hot,owner,registry); },true,
    "A WAL-only writer handle excludes inspection without changing existing sidecars");
  }
  inspect_unchanged(output,[&] {
   require(exact(GameplayStore::inspect_recovery(hot,owner,registry),wal_head),"Rejected WAL writer leaked a source guard");
  },false,"WAL writer rejection releases partially acquired main-file ownership");
  {
   // An open read handle denies file writes without changing attributes or ACLs.
   DenyFileWrites protected_file(valid);
   const auto writer=CreateFileW(valid.c_str(),GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,
    nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
   if(writer!=INVALID_HANDLE_VALUE) CloseHandle(writer);
   require(writer==INVALID_HANDLE_VALUE,"Fixture does not actually deny file writes");
   inspect_unchanged(output,[&] {
    require(exact(GameplayStore::inspect_recovery(valid,owner,registry),ordinary),"Protected recovery differs");
   },false,"Recovery succeeds while the OS denies writes to the database file");
  }
#endif
  std::cout<<"All read-only recovery checks passed; fixtures retained at "<<output.string()<<'\n';
  return 0;
 } catch(const std::exception& error) {
  std::cerr<<"FAILED: "<<error.what()<<"\nFixtures retained at "<<output.string()<<'\n';return 1;
 }
}
