#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/gameplay_store.hpp>
#include <aibs/gameplay_codec.hpp>
#include <sqlite3.h>
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstring>
#include <limits>
#include <set>
#include <stdexcept>
#include <utility>

namespace aibs {
namespace {
using Bytes=gameplay_codec::Bytes;
constexpr std::size_t state_limit=64*1024*1024, component_limit=10000, legacy_limit=16*1024*1024;
constexpr std::size_t scope_limit=16+4*4+256*2+36*2+1;
constexpr std::uint64_t application_id=0x41494253; // AIBS
struct SqlError : std::runtime_error { int code; SqlError(sqlite3* db,int value) : std::runtime_error(sqlite3_errmsg(db)),code(value) {} };
void check(sqlite3* db,int code) { if(code!=SQLITE_OK) throw SqlError(db,code); }
void execute(sqlite3* db,const char* sql) { check(db,sqlite3_exec(db,sql,nullptr,nullptr,nullptr)); }
void require(bool value,const char* message) { if(!value) throw std::invalid_argument(message); }
struct Statement {
 sqlite3* db; sqlite3_stmt* value=nullptr;
 Statement(sqlite3* connection,const char* sql) : db(connection) { check(db,sqlite3_prepare_v2(db,sql,-1,&value,nullptr)); }
 ~Statement() { sqlite3_finalize(value); }
 Statement(const Statement&)=delete;Statement& operator=(const Statement&)=delete;
 void bytes(int index,const Bytes& data) { check(db,sqlite3_bind_blob64(value,index,data.empty()?static_cast<const void*>(""):static_cast<const void*>(data.data()),data.size(),SQLITE_TRANSIENT)); }
 void text(int index,const std::string& data) { check(db,sqlite3_bind_text64(value,index,data.data(),data.size(),SQLITE_TRANSIENT,SQLITE_UTF8)); }
 bool row() { const auto result=sqlite3_step(value);if(result==SQLITE_ROW) return true;if(result!=SQLITE_DONE) throw SqlError(db,result);return false; }
 void done() { require(!row(),"Unexpected SQLite result row"); }
 Bytes blob(int index,std::size_t maximum=gameplay_codec::maximum_bytes) const {
  require(sqlite3_column_type(value,index)==SQLITE_BLOB,"Invalid SQLite blob type");
  const auto size=sqlite3_column_bytes(value,index);require(size>=0 && static_cast<std::size_t>(size)<=maximum,"SQLite blob exceeds its domain byte bound");
  const auto* data=static_cast<const std::uint8_t*>(sqlite3_column_blob(value,index));
  if(size==0) return {};require(data!=nullptr,"Invalid SQLite blob");return {data,data+size};
 }
 std::string string(int index,std::size_t maximum=4096) const {
  require(sqlite3_column_type(value,index)==SQLITE_TEXT,"Invalid SQLite text type");
  require(static_cast<std::size_t>(sqlite3_column_bytes(value,index))<=maximum,"SQLite text exceeds its domain byte bound");
  const auto* data=reinterpret_cast<const char*>(sqlite3_column_text(value,index));return {data,static_cast<std::size_t>(sqlite3_column_bytes(value,index))};
 }
 std::uint64_t natural(int index) const {
  require(sqlite3_column_type(value,index)==SQLITE_INTEGER && sqlite3_column_int64(value,index)>=0,"Invalid SQLite count");
  return static_cast<std::uint64_t>(sqlite3_column_int64(value,index));
 }
};
Bytes number(std::uint64_t value) { Bytes bytes(8);for(std::size_t n=0;n<8;++n) bytes[n]=static_cast<std::uint8_t>(value>>(56-8*n));return bytes; }
std::uint64_t number(const Bytes& bytes) { require(bytes.size()==8,"Invalid persisted unsigned integer");std::uint64_t value=0;for(const auto byte:bytes) value=(value<<8)|byte;return value; }
struct SqlTransaction {
 sqlite3* db;bool active=true;
 explicit SqlTransaction(sqlite3* connection,bool write=true) : db(connection) { execute(db,write?"BEGIN IMMEDIATE":"BEGIN"); }
 ~SqlTransaction() { if(active) sqlite3_exec(db,"ROLLBACK",nullptr,nullptr,nullptr); }
 void finish() { execute(db,"COMMIT");active=false; }
};
using ComponentKey=std::pair<std::string,std::string>;
using Components=std::map<ComponentKey,ComponentRecord>;
bool exact_components(const Components& left,const Components& right) {
 if(left.size()!=right.size()) return false;
 auto a=left.begin();auto b=right.begin();
 for(;a!=left.end();++a,++b)
  if(a->first!=b->first || gameplay_codec::encode_component(a->second)!=gameplay_codec::encode_component(b->second)) return false;
 return true;
}
struct BusyGuard {
 bool& active;
 explicit BusyGuard(bool& flag) : active(flag) { require(!active,"Reentrant gameplay store operation");active=true; }
 ~BusyGuard() { active=false; }
};
GameplayLimits validation_limits() { GameplayLimits value;value.pending_bytes=state_limit;value.receipt_bytes=state_limit;return value; }
using Connection=std::unique_ptr<sqlite3,decltype(&sqlite3_close_v2)>;
// Windows SQLite READONLY can still create/write WAL bookkeeping files. This
// inspection-only VFS reads an existing WAL, substitutes a zero-length in-memory
// WAL when absent, and requests SQLite's supported heap WAL-index recovery.
// Real deny-write/delete handles on BOTH source files make the no-op SHM locks
// safe: no SQLite writer/checkpointer can be open while this inspection runs.
class InspectionSourceGuard {
 std::array<HANDLE,2> handles_{INVALID_HANDLE_VALUE,INVALID_HANDLE_VALUE};
 void close()noexcept{for(auto& h:handles_)if(h!=INVALID_HANDLE_VALUE){CloseHandle(h);h=INVALID_HANDLE_VALUE;}}
public:
 explicit InspectionSourceGuard(const std::filesystem::path& path){
  try{
   for(std::size_t n=0;n<handles_.size();++n){
    auto source=path;if(n)source+=L"-wal";
    handles_[n]=CreateFileW(source.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
    if(handles_[n]==INVALID_HANDLE_VALUE){const auto error=GetLastError();if(n&&(error==ERROR_FILE_NOT_FOUND||error==ERROR_PATH_NOT_FOUND))continue;throw std::invalid_argument("Read-only recovery requires existing quiescent source files");}
    BY_HANDLE_FILE_INFORMATION info{};
    require(GetFileInformationByHandle(handles_[n],&info)&&!(info.dwFileAttributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY))&&GetFileType(handles_[n])==FILE_TYPE_DISK,"Read-only recovery source must be a nonredirected regular file");
   }
  }catch(...){close();throw;}
 }
 ~InspectionSourceGuard(){close();}
 InspectionSourceGuard(const InspectionSourceGuard&)=delete;InspectionSourceGuard& operator=(const InspectionSourceGuard&)=delete;
};
sqlite3_vfs*& inspection_parent(){static sqlite3_vfs* value=nullptr;return value;}
int inspect_shm_map(sqlite3_file*,int,int,int,void volatile** page){*page=nullptr;return SQLITE_READONLY_CANTINIT;}
int inspect_shm_lock(sqlite3_file*,int,int,int){return SQLITE_OK;}
void inspect_shm_barrier(sqlite3_file*){}
int inspect_shm_unmap(sqlite3_file*,int){return SQLITE_OK;}
int inspect_write(sqlite3_file*,const void*,int,sqlite3_int64){return SQLITE_READONLY;}
int inspect_truncate(sqlite3_file*,sqlite3_int64){return SQLITE_READONLY;}
const sqlite3_io_methods empty_inspection_wal={
 1,[](sqlite3_file*){return SQLITE_OK;},
 [](sqlite3_file*,void* data,int size,sqlite3_int64){std::memset(data,0,static_cast<std::size_t>(size));return SQLITE_IOERR_SHORT_READ;},
 inspect_write,inspect_truncate,[](sqlite3_file*,int){return SQLITE_OK;},
 [](sqlite3_file*,sqlite3_int64* size){*size=0;return SQLITE_OK;},
 [](sqlite3_file*,int){return SQLITE_OK;},[](sqlite3_file*,int){return SQLITE_OK;},
 [](sqlite3_file*,int* reserved){*reserved=0;return SQLITE_OK;},
 [](sqlite3_file*,int,void*){return SQLITE_NOTFOUND;},
 [](sqlite3_file*){return 512;},[](sqlite3_file*){return SQLITE_IOCAP_IMMUTABLE;},
 nullptr,nullptr,nullptr,nullptr,nullptr,nullptr
};
std::size_t inspection_method_offset(){const auto size=static_cast<std::size_t>(inspection_parent()->szOsFile);return (size+alignof(sqlite3_io_methods)-1)&~(alignof(sqlite3_io_methods)-1);}
int inspection_open(sqlite3_vfs*,const char* path,sqlite3_file* file,int flags,int* actual){
 const auto* parent=inspection_parent();
 if(!(flags&(SQLITE_OPEN_MAIN_DB|SQLITE_OPEN_WAL)))return SQLITE_READONLY;
 if(flags&SQLITE_OPEN_WAL){
  int exists=0;const auto rc=parent->xAccess(inspection_parent(),path,SQLITE_ACCESS_EXISTS,&exists);if(rc!=SQLITE_OK)return rc;
  if(!exists){file->pMethods=&empty_inspection_wal;if(actual)*actual=SQLITE_OPEN_READONLY|SQLITE_OPEN_WAL;return SQLITE_OK;}
 }
 flags=(flags&~(SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE|SQLITE_OPEN_DELETEONCLOSE))|SQLITE_OPEN_READONLY;
 const auto rc=parent->xOpen(inspection_parent(),path,file,flags,actual);if(rc!=SQLITE_OK)return rc;
 auto* methods=reinterpret_cast<sqlite3_io_methods*>(reinterpret_cast<unsigned char*>(file)+inspection_method_offset());
 *methods=*file->pMethods;methods->xWrite=inspect_write;methods->xTruncate=inspect_truncate;
 methods->xShmMap=inspect_shm_map;methods->xShmLock=inspect_shm_lock;methods->xShmBarrier=inspect_shm_barrier;methods->xShmUnmap=inspect_shm_unmap;
 file->pMethods=methods;return SQLITE_OK;
}
const char* inspection_vfs(){
 static constexpr char name[]="aibs-quiescent-readonly-v1";
 static const bool registered=[](){
  auto* parent=sqlite3_vfs_find(nullptr);require(parent!=nullptr,"SQLite base VFS is unavailable");inspection_parent()=parent;
  static sqlite3_vfs vfs=*parent;vfs.zName=name;vfs.pNext=nullptr;
  vfs.szOsFile=static_cast<int>(inspection_method_offset()+sizeof(sqlite3_io_methods));vfs.xOpen=inspection_open;
  vfs.xDelete=[](sqlite3_vfs*,const char*,int){return SQLITE_READONLY;};
  require(sqlite3_vfs_register(&vfs,0)==SQLITE_OK,"Cannot register read-only admission VFS");return true;
 }();(void)registered;return name;
}
Connection inspection_connection(const std::filesystem::path& path){
 const auto encoded=path.u8string();const std::string filename(reinterpret_cast<const char*>(encoded.data()),encoded.size());sqlite3* raw=nullptr;
 const auto opened=sqlite3_open_v2(filename.c_str(),&raw,SQLITE_OPEN_READONLY|SQLITE_OPEN_FULLMUTEX,inspection_vfs());
 Connection result(raw,&sqlite3_close_v2);check(raw,opened);require(sqlite3_db_readonly(raw,"main")==1,"Read-only gameplay inspection required");
 check(raw,sqlite3_extended_result_codes(raw,1));check(raw,sqlite3_busy_timeout(raw,250));
 sqlite3_limit(raw,SQLITE_LIMIT_LENGTH,20*1024*1024);sqlite3_limit(raw,SQLITE_LIMIT_SQL_LENGTH,64*1024);
 check(raw,sqlite3_db_config(raw,SQLITE_DBCONFIG_DEFENSIVE,1,nullptr));
 check(raw,sqlite3_db_config(raw,SQLITE_DBCONFIG_TRUSTED_SCHEMA,0,nullptr));
 check(raw,sqlite3_db_config(raw,SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,1,nullptr));return result;
}
Connection readonly_connection(const std::filesystem::path& path) {
 require(!path.empty(),"SQLite gameplay path cannot be empty");const auto encoded=path.u8string();
 const std::string filename(reinterpret_cast<const char*>(encoded.data()),encoded.size());sqlite3* raw=nullptr;
 const auto opened=sqlite3_open_v2(filename.c_str(),&raw,SQLITE_OPEN_READONLY|SQLITE_OPEN_FULLMUTEX,nullptr);
 Connection result(raw,&sqlite3_close_v2);check(raw,opened);require(sqlite3_db_readonly(raw,"main")==1,"Read-only gameplay inspection required");
 check(raw,sqlite3_busy_timeout(raw,250));sqlite3_limit(raw,SQLITE_LIMIT_LENGTH,20*1024*1024);
 check(raw,sqlite3_db_config(raw,SQLITE_DBCONFIG_TRUSTED_SCHEMA,0,nullptr));return result;
}
std::uint64_t database_format(sqlite3* db) {
 Statement version(db,"PRAGMA user_version");require(version.row(),"Missing SQLite format version");return version.natural(0);
}
void known_database(sqlite3* db) {
 const auto version=database_format(db);require(version==1 || version==2,"Unsupported gameplay database format requires migration");
 Statement identity(db,"PRAGMA application_id");require(identity.row() && identity.natural(0)==application_id,"Foreign or untagged gameplay database application ID");
 if(version==2) {
  Statement table(db,"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='aibs_gameplay_registry_migrations'");
  require(table.row() && table.natural(0)==1,"Format2 registry migration table is missing");
  Statement columns(db,"SELECT scope,migration_id,ordinal,expected_registry,target_registry,expected_revision,expected_sequence FROM aibs_gameplay_registry_migrations LIMIT 0");columns.done();
 }
}
std::vector<ComponentSchema> canonical_registry(const Bytes& bytes) {
 auto values=gameplay_codec::decode_schemas(bytes);require(gameplay_codec::encode_schemas(values)==bytes,"Noncanonical gameplay component registry");return values;
}
bool identifier(const std::string& value) { return !value.empty() && value.size()<=256 && value.find('\0')==std::string::npos; }
void additive_registry(const std::vector<ComponentSchema>& expected,const std::vector<ComponentSchema>& target) {
 require(target.size()>expected.size(),"Registry extension must add at least one definition");
 for(const auto& original:expected) {
  const auto found=std::find_if(target.begin(),target.end(),[&](const auto& candidate) { return candidate.type_id==original.type_id && candidate.version==original.version; });
  require(found!=target.end() && gameplay_codec::encode_schemas({original})==gameplay_codec::encode_schemas({*found}),"Registry extension cannot remove or change an existing definition");
 }
}
thread_local bool registry_extension_active=false;
}
struct GameplayStore::Impl {
 sqlite3* db=nullptr;
 GameplayScope scope;
 std::vector<ComponentSchema> schemas;
 Bytes key,registry;
 GameplayStoreObserver observer;
 mutable bool busy=false;
 Impl(const std::filesystem::path& path,GameplayScope owner,std::vector<ComponentSchema> definitions,GameplayStoreObserver hook,bool read_only=false)
  : scope(std::move(owner)),schemas(std::move(definitions)),observer(std::move(hook)) {
  GameplayAdmission validation(scope,schemas);key=gameplay_codec::encode_scope(scope);registry=gameplay_codec::encode_schemas(schemas);
  require(!path.empty(),"SQLite gameplay path cannot be empty");
  const auto encoded=path.u8string();const std::string filename(reinterpret_cast<const char*>(encoded.data()),encoded.size());
  try {
   if(read_only) {
    auto connection=inspection_connection(path);db=connection.release();known_database(db);return;
   }
   check(db,sqlite3_open_v2(filename.c_str(),&db,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE|SQLITE_OPEN_FULLMUTEX,nullptr));
   check(db,sqlite3_extended_result_codes(db,1));check(db,sqlite3_busy_timeout(db,250));
   sqlite3_limit(db,SQLITE_LIMIT_LENGTH,20*1024*1024);sqlite3_limit(db,SQLITE_LIMIT_SQL_LENGTH,64*1024);
   check(db,sqlite3_db_config(db,SQLITE_DBCONFIG_DEFENSIVE,1,nullptr));
   check(db,sqlite3_db_config(db,SQLITE_DBCONFIG_TRUSTED_SCHEMA,0,nullptr));
   std::uint64_t format=0;
   { Statement version(db,"PRAGMA user_version");require(version.row(),"Missing SQLite format version");format=version.natural(0); }
   require(format<=2,"Unsupported gameplay database format requires migration");
   { Statement identity(db,"PRAGMA application_id");require(identity.row(),"Missing SQLite application ID");
    require(identity.natural(0)==(format==0?0:application_id),"Foreign or untagged gameplay database application ID"); }
   if(format==2) known_database(db);
   if(format==0) { Statement tables(db,"SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'");require(tables.row() && tables.natural(0)==0,"Unrecognized nonempty database"); }
   physical_integrity();
   { Statement mode(db,"PRAGMA journal_mode=WAL");require(mode.row() && mode.string(0)=="wal","SQLite WAL mode is required"); }
   execute(db,"PRAGMA synchronous=FULL");
   { Statement synchronous(db,"PRAGMA synchronous");require(synchronous.row() && synchronous.natural(0)==2,"SQLite FULL durability is required"); }
   execute(db,"PRAGMA foreign_keys=ON");
   { Statement foreign_keys(db,"PRAGMA foreign_keys");require(foreign_keys.row() && foreign_keys.natural(0)==1,"SQLite foreign keys are required"); }
   {
    SqlTransaction transaction(db);
    if(format==0) {
     execute(db,"CREATE TABLE aibs_gameplay_meta(scope BLOB PRIMARY KEY,registry BLOB NOT NULL,revision BLOB NOT NULL CHECK(length(revision)=8),sequence BLOB NOT NULL CHECK(length(sequence)=8)) WITHOUT ROWID;"
      "CREATE TABLE aibs_gameplay_components(scope BLOB NOT NULL,entity TEXT NOT NULL,type TEXT NOT NULL,record BLOB NOT NULL,PRIMARY KEY(scope,entity,type),FOREIGN KEY(scope) REFERENCES aibs_gameplay_meta(scope)) WITHOUT ROWID;"
      "CREATE TABLE aibs_gameplay_batches(scope BLOB NOT NULL,operation TEXT NOT NULL,revision BLOB NOT NULL CHECK(length(revision)=8),batch BLOB NOT NULL,PRIMARY KEY(scope,operation),UNIQUE(scope,revision),FOREIGN KEY(scope) REFERENCES aibs_gameplay_meta(scope)) WITHOUT ROWID;"
      "CREATE TABLE aibs_gameplay_events(scope BLOB NOT NULL,event_id TEXT NOT NULL,sequence BLOB NOT NULL CHECK(length(sequence)=8),operation TEXT NOT NULL,PRIMARY KEY(scope,event_id),UNIQUE(scope,sequence),FOREIGN KEY(scope,operation) REFERENCES aibs_gameplay_batches(scope,operation)) WITHOUT ROWID;"
      "CREATE TABLE aibs_gameplay_baselines(scope BLOB PRIMARY KEY,revision BLOB NOT NULL CHECK(length(revision)=8),sequence BLOB NOT NULL CHECK(length(sequence)=8),legacy BLOB NOT NULL,FOREIGN KEY(scope) REFERENCES aibs_gameplay_meta(scope)) WITHOUT ROWID;"
      "CREATE TABLE aibs_gameplay_baseline_components(scope BLOB NOT NULL,entity TEXT NOT NULL,type TEXT NOT NULL,record BLOB NOT NULL,PRIMARY KEY(scope,entity,type),FOREIGN KEY(scope) REFERENCES aibs_gameplay_baselines(scope)) WITHOUT ROWID;PRAGMA user_version=1;PRAGMA application_id=1095320147");
    }
    Statement existing(db,"SELECT registry FROM aibs_gameplay_meta WHERE scope=?1");existing.bytes(1,key);
    if(existing.row()) require(existing.blob(0)==registry,"Component registry changed; explicit migration required");
    else { Statement insert(db,"INSERT INTO aibs_gameplay_meta VALUES(?1,?2,?3,?4)");insert.bytes(1,key);insert.bytes(2,registry);insert.bytes(3,number(0));insert.bytes(4,number(0));insert.done(); }
    transaction.finish();
   }
   validate_stream();
  } catch(...) { if(db) sqlite3_close_v2(db);db=nullptr;throw; }
 }
 ~Impl() { if(db) sqlite3_close_v2(db); }
 void physical_integrity() const {
  Statement integrity(db,"PRAGMA integrity_check");require(integrity.row() && integrity.string(0)=="ok" && !integrity.row(),"SQLite integrity check failed");
 }
 std::pair<std::uint64_t,std::uint64_t> heads() const {
  Statement query(db,"SELECT revision,sequence,registry FROM aibs_gameplay_meta WHERE scope=?1");query.bytes(1,key);
  require(query.row() && query.blob(2)==registry,"Gameplay scope metadata missing or incompatible");return {number(query.blob(0,8)),number(query.blob(1,8))};
 }
 Components components(bool original=false) const {
  const char* sql=original?"SELECT entity,type,record FROM aibs_gameplay_baseline_components WHERE scope=?1 ORDER BY entity,type":"SELECT entity,type,record FROM aibs_gameplay_components WHERE scope=?1 ORDER BY entity,type";
  Statement query(db,sql);query.bytes(1,key);Components result;std::size_t charged=0;
  while(query.row()) {
   auto encoded=query.blob(2);require(encoded.size()<=state_limit-charged && result.size()<component_limit,"Gameplay component recovery exceeds bounded state budget");charged+=encoded.size();
   auto record=gameplay_codec::decode_component(encoded);require(record.entity_id==query.string(0) && record.type_id==query.string(1),"Component row identity mismatch");
   require(result.emplace(ComponentKey{record.entity_id,record.type_id},std::move(record)).second,"Duplicate component row");
  }
  return result;
 }
 void validate_batch(const GameplayChangeBatch& batch,std::uint64_t revision,std::uint64_t sequence) const {
  GameplayAdmission validation(scope,schemas,validation_limits(),revision,sequence);
  const auto admitted=validation.reserve(batch,[](const std::string&) { return true; });
  if(admitted.status!=AdmissionStatus::accepted) throw std::invalid_argument(admitted.message);
 }
 std::size_t validate_component_set(const Components& values) const {
  require(values.size()<=component_limit,"Gameplay component count exceeds alpha recovery budget");std::size_t charged=0;
  for(const auto& [unused,record]:values) {
   (void)unused;const auto encoded=gameplay_codec::encode_component(record);require(encoded.size()<=state_limit-charged,"Gameplay component bytes exceed alpha recovery budget");charged+=encoded.size();
   GameplayChangeBatch batch;batch.scope=scope;batch.operation_id="baseline.validation";batch.revision=1;
   batch.deltas.push_back({ComponentAction::upsert,record});SemanticEvent event;
   event.event_id="11111111-1111-4111-8111-111111111111";event.scope=scope;event.sequence=1;event.operation_id=batch.operation_id;
   event.source_revision=1;event.subject_ids={record.entity_id};event.provenance.source_id="baseline.validation";event.payload=RouteOutcome{record.entity_id,true};
   batch.events.push_back(std::move(event));validate_batch(batch,0,0);
  }
  return charged;
 }
 std::optional<GameplayStoreBaseline> original() const {
  Statement query(db,"SELECT revision,sequence,legacy FROM aibs_gameplay_baselines WHERE scope=?1");query.bytes(1,key);if(!query.row()) return {};
  GameplayStoreBaseline result;result.revision=number(query.blob(0,8));result.sequence=number(query.blob(1,8));result.legacy_checkpoint=query.blob(2,legacy_limit);
  require(result.legacy_checkpoint.size()<=legacy_limit,"Original checkpoint exceeds import bound");
  auto values=components(true);for(auto& [unused,record]:values) { (void)unused;result.components.push_back(std::move(record)); }return result;
 }
 static Components mapped(const std::vector<ComponentRecord>& records) {
  require(records.size()<=component_limit,"Gameplay component count exceeds alpha recovery budget");Components result;
  for(const auto& record:records) require(result.emplace(ComponentKey{record.entity_id,record.type_id},record).second,"Duplicate baseline component identity");return result;
 }
 void apply(Components& values,const GameplayChangeBatch& batch,std::size_t& charged) const {
  // Preflight the resulting transaction state before copying any component.
  // Erase/replacement rows are removed before insertions so a bounded atomic
  // swap does not transiently retain both old and new state during replay.
  std::uint64_t next_bytes=charged,next_count=values.size();
  for(const auto& delta:batch.deltas) {
   const auto& record=delta.component;const ComponentKey identity{record.entity_id,record.type_id};const auto found=values.find(identity);
   if(found!=values.end()) { next_bytes-=gameplay_codec::encode_component(found->second).size();--next_count; }
   if(delta.action==ComponentAction::upsert) { next_bytes+=gameplay_codec::encode_component(record).size();++next_count; }
  }
  require(next_bytes<=state_limit,"Gameplay replay byte budget exceeded");
  require(next_count<=component_limit,"Gameplay replay component count budget exceeded");
  for(const auto& delta:batch.deltas) values.erase({delta.component.entity_id,delta.component.type_id});
  for(const auto& delta:batch.deltas) if(delta.action==ComponentAction::upsert)
   values.emplace(ComponentKey{delta.component.entity_id,delta.component.type_id},delta.component);
  charged=static_cast<std::size_t>(next_bytes);
 }
 void write_component(const ComponentRecord& record,bool original=false) {
  Statement insert(db,original?"INSERT INTO aibs_gameplay_baseline_components VALUES(?1,?2,?3,?4)":"INSERT INTO aibs_gameplay_components VALUES(?1,?2,?3,?4) ON CONFLICT(scope,entity,type) DO UPDATE SET record=excluded.record");
  insert.bytes(1,key);insert.text(2,record.entity_id);insert.text(3,record.type_id);insert.bytes(4,gameplay_codec::encode_component(record));insert.done();
 }
 void update_heads(std::uint64_t revision,std::uint64_t sequence) {
  Statement update(db,"UPDATE aibs_gameplay_meta SET revision=?2,sequence=?3 WHERE scope=?1");update.bytes(1,key);update.bytes(2,number(revision));update.bytes(3,number(sequence));update.done();
 }
 GameplayStoreCommit completed(GameplayStoreStatus status,const std::string& operation,std::uint64_t revision,const char* message) const {
  return {status,message,{scope,operation,revision,GameplayPhase::durably_committed}};
 }
 void after_commit(GameplayStoreCommit& result) const noexcept {
  if(!observer) return;try { observer(GameplayStoreStage::after_commit); } catch(const std::exception& error) { try { result.message+="; after-commit observer failed: ";result.message+=error.what(); } catch(...) {} } catch(...) { try { result.message+="; after-commit observer failed"; } catch(...) {} }
 }
 using Definition=std::pair<std::string,std::uint32_t>;
 using IntroductionHeads=std::map<Definition,std::pair<std::uint64_t,std::uint64_t>>;
 std::vector<std::pair<std::uint64_t,std::uint64_t>> registry_chain(IntroductionHeads* introduced=nullptr) const {
  std::vector<std::pair<std::uint64_t,std::uint64_t>> anchors;if(database_format(db)==1) return anchors;
  known_database(db);Statement query(db,"SELECT migration_id,ordinal,expected_registry,target_registry,expected_revision,expected_sequence FROM aibs_gameplay_registry_migrations WHERE scope=?1 ORDER BY ordinal");query.bytes(1,key);
  Bytes previous;std::uint64_t ordinal=0;
  while(query.row()) {
   require(ordinal<127 && query.natural(1)==ordinal+1 && identifier(query.string(0,256)),"Invalid registry migration ordinal/identity");
   const auto expected=query.blob(2),target=query.blob(3);const auto old=canonical_registry(expected),next=canonical_registry(target);additive_registry(old,next);
   if(ordinal>0) require(previous==expected,"Registry migration receipt chain is discontinuous");
   const auto anchor=std::pair{number(query.blob(4,8)),number(query.blob(5,8))};
   if(introduced) {
    if(ordinal==0) for(const auto& schema:old) introduced->emplace(Definition{schema.type_id,schema.version},std::pair<std::uint64_t,std::uint64_t>{0,0});
    for(const auto& schema:next) introduced->try_emplace(Definition{schema.type_id,schema.version},anchor);
   }
   if(!anchors.empty()) require(anchor.first>=anchors.back().first && anchor.second>=anchors.back().second,"Registry migration heads regress");
   anchors.push_back(anchor);previous=target;++ordinal;
  }
  require(previous.empty() || previous==registry,"Registry migration chain does not end at current registry");return anchors;
 }
 void validate_stream(bool own_transaction=true) const {
  std::unique_ptr<SqlTransaction> transaction;if(own_transaction) transaction=std::make_unique<SqlTransaction>(db,false);
  IntroductionHeads introduced;const auto anchors=registry_chain(&introduced);std::size_t migration=0;
  while(migration<anchors.size() && anchors[migration]==std::pair<std::uint64_t,std::uint64_t>{0,0}) ++migration;
  auto validate_anchors=[&](std::uint64_t revision,std::uint64_t sequence) {
   while(migration<anchors.size() && anchors[migration].first<=revision) {
    require(anchors[migration]==std::pair{revision,sequence},"Registry migration head is not a durable stream prefix");++migration;
   }
  };
  const auto head=heads();auto initial=original();Components replay;std::uint64_t revision=0,sequence=0,events=0;std::size_t replay_bytes=0;
  if(initial) { revision=initial->revision;sequence=initial->sequence;replay=mapped(initial->components);replay_bytes=validate_component_set(replay); }
  if(!introduced.empty()) for(const auto& [unused,record]:replay) {
   (void)unused;const auto found=introduced.find({record.type_id,record.version});
   require(found!=introduced.end() && found->second==std::pair<std::uint64_t,std::uint64_t>{0,0},"Registry receipt introduces a component after the immutable baseline");
  }
  validate_anchors(revision,sequence);
  Statement batches(db,"SELECT operation,revision,batch FROM aibs_gameplay_batches WHERE scope=?1 ORDER BY revision");batches.bytes(1,key);
  while(batches.row()) {
   const auto batch=gameplay_codec::decode_batch(batches.blob(2));require(batch.operation_id==batches.string(0) && batch.revision==number(batches.blob(1,8)),"Persisted batch row identity mismatch");
   if(!introduced.empty()) for(const auto& delta:batch.deltas) {
    const auto found=introduced.find({delta.component.type_id,delta.component.version});
    require(found!=introduced.end() && found->second.first<=revision && found->second.second<=sequence,"Registry receipt introduces a component after its historical gameplay use");
   }
   validate_batch(batch,revision,sequence);apply(replay,batch,replay_bytes);
   Statement stored(db,"SELECT event_id,sequence FROM aibs_gameplay_events WHERE scope=?1 AND operation=?2 ORDER BY sequence");stored.bytes(1,key);stored.text(2,batch.operation_id);
   for(const auto& event:batch.events) { require(stored.row() && stored.string(0)==event.event_id && number(stored.blob(1,8))==event.sequence,"Semantic index differs from exact durable receipt");++events; }
   require(!stored.row(),"Unexpected semantic index row");revision=batch.revision;sequence=batch.events.back().sequence;
   validate_anchors(revision,sequence);
  }
  Statement count(db,"SELECT count(*) FROM aibs_gameplay_events WHERE scope=?1");count.bytes(1,key);require(count.row() && count.natural(0)==events,"Orphan semantic event row");
  const auto current=components();validate_component_set(current);require(exact_components(current,replay) && head==std::pair{revision,sequence},"Gameplay state and durable event stream disagree");
  require(migration==anchors.size(),"Registry migration head exceeds current durable stream");
  if(transaction) transaction->finish();
 }
};
std::vector<GameplayScope> GameplayStore::list_scopes(const std::filesystem::path& path,std::size_t maximum) {
 require(!path.empty(),"SQLite gameplay path cannot be empty");require(maximum>0 && maximum<=4096,"Invalid gameplay scope discovery limit");
 const auto encoded=path.u8string();const std::string filename(reinterpret_cast<const char*>(encoded.data()),encoded.size());
 sqlite3* raw=nullptr;const auto opened=sqlite3_open_v2(filename.c_str(),&raw,SQLITE_OPEN_READONLY|SQLITE_OPEN_FULLMUTEX,nullptr);
 const std::unique_ptr<sqlite3,decltype(&sqlite3_close_v2)> connection(raw,&sqlite3_close_v2);check(raw,opened);
 require(sqlite3_db_readonly(raw,"main")==1,"Scope discovery requires a read-only database connection");
 check(raw,sqlite3_extended_result_codes(raw,1));check(raw,sqlite3_busy_timeout(raw,250));
 sqlite3_limit(raw,SQLITE_LIMIT_LENGTH,20*1024*1024);sqlite3_limit(raw,SQLITE_LIMIT_SQL_LENGTH,64*1024);
 check(raw,sqlite3_db_config(raw,SQLITE_DBCONFIG_DEFENSIVE,1,nullptr));
 check(raw,sqlite3_db_config(raw,SQLITE_DBCONFIG_TRUSTED_SCHEMA,0,nullptr));
 SqlTransaction transaction(raw,false);
 known_database(raw);
 { Statement integrity(raw,"PRAGMA quick_check");require(integrity.row() && integrity.string(0)=="ok" && !integrity.row(),"SQLite scope discovery integrity check failed"); }
 Statement scopes(raw,"SELECT scope FROM aibs_gameplay_meta ORDER BY scope");std::vector<GameplayScope> result;
 while(scopes.row()) {
  require(result.size()<maximum,"Gameplay scope discovery limit exhausted; explicit selection requires a larger bound");
  const auto bytes=scopes.blob(0,scope_limit);auto scope=gameplay_codec::decode_scope(bytes);
  require(gameplay_codec::encode_scope(scope)==bytes,"Noncanonical persisted gameplay scope");result.push_back(std::move(scope));
 }
 transaction.finish();return result;
}
std::vector<ComponentSchema> GameplayStore::inspect_registry(const std::filesystem::path& path,const GameplayScope& scope) {
 const auto key=gameplay_codec::encode_scope(scope);auto connection=readonly_connection(path);known_database(connection.get());
 SqlTransaction transaction(connection.get(),false);Statement query(connection.get(),"SELECT registry FROM aibs_gameplay_meta WHERE scope=?1");query.bytes(1,key);
 require(query.row(),"Gameplay scope has no registered component schemas");auto result=canonical_registry(query.blob(0));
 GameplayAdmission validation(scope,result);transaction.finish();return result;
}
GameplayStoreRecovery GameplayStore::inspect_recovery(const std::filesystem::path& path,const GameplayScope& scope,
 const std::vector<ComponentSchema>& expected_schemas) {
 require(!path.empty(),"SQLite gameplay path cannot be empty");InspectionSourceGuard protected_source(path);
 Impl reader(path,scope,expected_schemas,{},true);SqlTransaction transaction(reader.db,false);
 Statement scopes(reader.db,"SELECT scope FROM aibs_gameplay_meta ORDER BY scope LIMIT 2");
 require(scopes.row()&&scopes.blob(0,scope_limit)==reader.key&&!scopes.row(),"Read-only recovery requires exactly its selected gameplay scope");
 reader.physical_integrity();reader.validate_stream(false);
 const auto [revision,sequence]=reader.heads();GameplayStoreRecovery result{scope,revision,sequence,{}};
 auto values=reader.components();result.components.reserve(values.size());
 for(auto& [unused,record]:values){(void)unused;result.components.push_back(std::move(record));}
 transaction.finish();return result;
}
GameplayRegistryExtensionResult GameplayStore::extend_registry(const std::filesystem::path& path,const GameplayScope& scope,
 const std::vector<ComponentSchema>& expected_schemas,const std::vector<ComponentSchema>& target_schemas,const std::string& migration_id,
 std::uint64_t expected_revision,std::uint64_t expected_sequence,GameplayStoreObserver observer) {
 try {
  BusyGuard extension_guard(registry_extension_active);
  // Bounded canonical encoding precedes all value copies and caller hooks.
  const auto key=gameplay_codec::encode_scope(scope);const auto owner=gameplay_codec::decode_scope(key);
  const auto expected_bytes=gameplay_codec::encode_schemas(expected_schemas),target_bytes=gameplay_codec::encode_schemas(target_schemas);
  const auto expected=canonical_registry(expected_bytes),target=canonical_registry(target_bytes);
  GameplayAdmission expected_validation(owner,expected),target_validation(owner,target);additive_registry(expected,target);
  require(identifier(migration_id),"Registry migration ID must be a bounded identifier");const auto id=migration_id;
  // Inspect without CREATE before choosing the current-schema validator. This
  // also permits a retained exact retry after later additive registry changes.
  auto current=inspect_registry(path,owner);Impl store(path,owner,std::move(current),{});
  BusyGuard mutation_guard(store.busy);SqlTransaction transaction(store.db);store.validate_stream(false);
  auto format=database_format(store.db);
  if(format==2) {
   Statement receipt(store.db,"SELECT expected_registry,target_registry,expected_revision,expected_sequence FROM aibs_gameplay_registry_migrations WHERE scope=?1 AND migration_id=?2");
   receipt.bytes(1,key);receipt.text(2,id);
   if(receipt.row()) {
    require(receipt.blob(0)==expected_bytes && receipt.blob(1)==target_bytes && number(receipt.blob(2,8))==expected_revision &&
            number(receipt.blob(3,8))==expected_sequence,"Registry migration ID was already used for different content");
    return {GameplayStoreStatus::retry,"Exact previously committed additive registry migration"};
   }
  }
  require(store.registry==expected_bytes,"Registry migration expected registry is stale");
  require(store.heads()==std::pair{expected_revision,expected_sequence},"Registry migration durable head precondition failed");
  const auto ordinal=store.registry_chain().size()+1;require(ordinal<=127,"Registry migration chain exceeds its hard definition bound");
  if(format==1) {
   execute(store.db,"CREATE TABLE aibs_gameplay_registry_migrations(scope BLOB NOT NULL,migration_id TEXT NOT NULL,ordinal INTEGER NOT NULL CHECK(ordinal>=1 AND ordinal<=127),expected_registry BLOB NOT NULL,target_registry BLOB NOT NULL,expected_revision BLOB NOT NULL CHECK(length(expected_revision)=8),expected_sequence BLOB NOT NULL CHECK(length(expected_sequence)=8),PRIMARY KEY(scope,migration_id),UNIQUE(scope,ordinal),FOREIGN KEY(scope) REFERENCES aibs_gameplay_meta(scope)) WITHOUT ROWID;PRAGMA user_version=2");
  }
  { Statement update(store.db,"UPDATE aibs_gameplay_meta SET registry=?2 WHERE scope=?1");update.bytes(1,key);update.bytes(2,target_bytes);update.done(); }
  { Statement insert(store.db,"INSERT INTO aibs_gameplay_registry_migrations VALUES(?1,?2,?3,?4,?5,?6,?7)");
   insert.bytes(1,key);insert.text(2,id);check(store.db,sqlite3_bind_int64(insert.value,3,static_cast<sqlite3_int64>(ordinal)));
   insert.bytes(4,expected_bytes);insert.bytes(5,target_bytes);insert.bytes(6,number(expected_revision));insert.bytes(7,number(expected_sequence));insert.done(); }
  store.schemas=target;store.registry=target_bytes;store.validate_stream(false);
  GameplayRegistryExtensionResult result{GameplayStoreStatus::committed,"Additive registry and exact migration receipt committed; gameplay heads unchanged"};
  if(observer) observer(GameplayStoreStage::before_commit);transaction.finish();
  if(observer) {
   try { observer(GameplayStoreStage::after_commit); }
   catch(...) { try { result.message+="; after-commit observer failed"; } catch(...) {} }
  }
  return result;
 } catch(const std::invalid_argument& error) { return {GameplayStoreStatus::rejected,error.what()}; }
 catch(const std::exception& error) { return {GameplayStoreStatus::failed,error.what()}; }
 catch(...) { return {GameplayStoreStatus::failed,"Unknown additive registry migration failure"}; }
}
GameplayStore::GameplayStore(const std::filesystem::path& path,GameplayScope scope,std::vector<ComponentSchema> schemas,GameplayStoreObserver observer)
 : impl_(std::make_unique<Impl>(path,std::move(scope),std::move(schemas),std::move(observer))) {}
GameplayStore::~GameplayStore()=default;
GameplayStoreCommit GameplayStore::commit(const GameplayChangeBatch& batch) {
 auto& p=*impl_;
 try {
  BusyGuard guard(p.busy);const auto encoded=gameplay_codec::encode_batch(batch);const auto snapshot=gameplay_codec::decode_batch(encoded);
  require(snapshot.scope==p.scope,"Foreign gameplay scope");SqlTransaction transaction(p.db);
  { Statement receipt(p.db,"SELECT batch FROM aibs_gameplay_batches WHERE scope=?1 AND operation=?2");receipt.bytes(1,p.key);receipt.text(2,snapshot.operation_id);
   if(receipt.row()) { require(receipt.blob(0)==encoded,"Gameplay operation ID conflicts with a durable receipt");return p.completed(GameplayStoreStatus::retry,snapshot.operation_id,snapshot.revision,"Exact durable retry"); }
  }
  const auto [revision,sequence]=p.heads();p.validate_batch(snapshot,revision,sequence);
  auto projected=p.components();auto projected_bytes=p.validate_component_set(projected);p.apply(projected,snapshot,projected_bytes);p.validate_component_set(projected);
  { Statement insert(p.db,"INSERT INTO aibs_gameplay_batches VALUES(?1,?2,?3,?4)");insert.bytes(1,p.key);insert.text(2,snapshot.operation_id);insert.bytes(3,number(snapshot.revision));insert.bytes(4,encoded);insert.done(); }
  for(const auto& delta:snapshot.deltas) {
   if(delta.action==ComponentAction::upsert) p.write_component(delta.component);
   else { Statement erase(p.db,"DELETE FROM aibs_gameplay_components WHERE scope=?1 AND entity=?2 AND type=?3");erase.bytes(1,p.key);erase.text(2,delta.component.entity_id);erase.text(3,delta.component.type_id);erase.done(); }
  }
  for(const auto& event:snapshot.events) { Statement insert(p.db,"INSERT INTO aibs_gameplay_events VALUES(?1,?2,?3,?4)");insert.bytes(1,p.key);insert.text(2,event.event_id);insert.bytes(3,number(event.sequence));insert.text(4,snapshot.operation_id);insert.done(); }
  p.update_heads(snapshot.revision,snapshot.events.back().sequence);
  auto result=p.completed(GameplayStoreStatus::committed,snapshot.operation_id,snapshot.revision,"SQLite WAL FULL transaction committed");
  if(p.observer) p.observer(GameplayStoreStage::before_commit);transaction.finish();p.after_commit(result);return result;
 } catch(const std::invalid_argument& error) { return {GameplayStoreStatus::rejected,error.what(),{}}; }
 catch(const SqlError& error) { return {(error.code&0xff)==SQLITE_CONSTRAINT?GameplayStoreStatus::rejected:GameplayStoreStatus::failed,error.what(),{}}; }
 catch(const std::exception& error) { return {GameplayStoreStatus::failed,error.what(),{}}; }
 catch(...) { return {GameplayStoreStatus::failed,"Unknown gameplay store failure",{}}; }
}
GameplayStoreRecovery GameplayStore::recover() const {
 auto& p=*impl_;BusyGuard guard(p.busy);SqlTransaction transaction(p.db,false);const auto [revision,sequence]=p.heads();
 GameplayStoreRecovery result{p.scope,revision,sequence,{}};auto values=p.components();p.validate_component_set(values);
 for(auto& [unused,record]:values) { (void)unused;result.components.push_back(std::move(record)); }transaction.finish();return result;
}
std::optional<GameplayChangeBatch> GameplayStore::lookup_batch(const std::string& operation_id) const {
 auto& p=*impl_;BusyGuard guard(p.busy);require(!operation_id.empty() && operation_id.size()<=256,"Invalid gameplay operation ID");
 Statement query(p.db,"SELECT batch FROM aibs_gameplay_batches WHERE scope=?1 AND operation=?2");query.bytes(1,p.key);query.text(2,operation_id);
 if(!query.row()) return {};auto result=gameplay_codec::decode_batch(query.blob(0));require(result.scope==p.scope && result.operation_id==operation_id,"Durable receipt identity mismatch");return result;
}
bool GameplayStore::contains_event(const std::string& event_id) const {
 require(is_uuid(event_id),"Event identity lookup requires a persistent UUID");auto& p=*impl_;BusyGuard guard(p.busy);
 Statement query(p.db,"SELECT 1 FROM aibs_gameplay_events WHERE scope=?1 AND event_id=?2");query.bytes(1,p.key);query.text(2,event_id);return query.row();
}
std::vector<GameplayChangeBatch> GameplayStore::read_batches(std::uint64_t after_revision,std::size_t max_batches,std::size_t max_bytes) const {
 auto& p=*impl_;BusyGuard guard(p.busy);require(max_batches>0 && max_batches<=1024 && max_bytes>0 && max_bytes<=state_limit,"Invalid durable history page bounds");
 Statement query(p.db,"SELECT batch FROM aibs_gameplay_batches WHERE scope=?1 AND revision>?2 ORDER BY revision");query.bytes(1,p.key);query.bytes(2,number(after_revision));
 std::vector<GameplayChangeBatch> result;std::size_t charged=0;
 while(result.size()<max_batches && query.row()) { auto bytes=query.blob(0);if(bytes.size()>max_bytes-charged) { require(!result.empty(),"First durable receipt exceeds history page byte budget");break; }
  auto batch=gameplay_codec::decode_batch(bytes);require(batch.scope==p.scope && batch.revision>after_revision,"Invalid durable history scope/revision");charged+=bytes.size();result.push_back(std::move(batch)); }
 return result;
}
GameplayStoreCommit GameplayStore::seed(const GameplayStoreBaseline& baseline) {
 auto& p=*impl_;
 try {
  BusyGuard guard(p.busy);require(baseline.legacy_checkpoint.size()<=legacy_limit,"Legacy checkpoint exceeds import byte budget");
  require(baseline.components.size()<=component_limit,"Gameplay component count exceeds alpha recovery budget");
  std::size_t preflight_bytes=0;
  for(const auto& record:baseline.components) {
   const auto encoded=gameplay_codec::encode_component(record);
   require(encoded.size()<=state_limit-preflight_bytes,"Gameplay component bytes exceed alpha recovery budget");preflight_bytes+=encoded.size();
  }
  auto values=Impl::mapped(baseline.components);p.validate_component_set(values);GameplayStoreBaseline snapshot{baseline.revision,baseline.sequence,{},baseline.legacy_checkpoint};
  for(const auto& [unused,record]:values) { (void)unused;snapshot.components.push_back(record); }
  SqlTransaction transaction(p.db);
  if(auto existing=p.original()) { require(existing->revision==snapshot.revision && existing->sequence==snapshot.sequence && exact_components(Impl::mapped(existing->components),values) && existing->legacy_checkpoint==snapshot.legacy_checkpoint,"A different immutable baseline is already seeded");return p.completed(GameplayStoreStatus::retry,"",snapshot.revision,"Exact baseline retry"); }
  const auto [revision,sequence]=p.heads();require(revision==0 && sequence==0 && p.components().empty(),"Baseline requires an empty unseeded store");
  { Statement count(p.db,"SELECT count(*) FROM aibs_gameplay_batches WHERE scope=?1");count.bytes(1,p.key);require(count.row() && count.natural(0)==0,"Cannot seed over durable gameplay history"); }
  { Statement insert(p.db,"INSERT INTO aibs_gameplay_baselines VALUES(?1,?2,?3,?4)");insert.bytes(1,p.key);insert.bytes(2,number(snapshot.revision));insert.bytes(3,number(snapshot.sequence));insert.bytes(4,snapshot.legacy_checkpoint);insert.done(); }
  for(const auto& record:snapshot.components) { p.write_component(record,true);p.write_component(record); }
  p.update_heads(snapshot.revision,snapshot.sequence);auto result=p.completed(GameplayStoreStatus::committed,"",snapshot.revision,"Immutable baseline and original legacy evidence committed");
  if(p.observer) p.observer(GameplayStoreStage::before_commit);transaction.finish();p.after_commit(result);return result;
 } catch(const std::invalid_argument& error) { return {GameplayStoreStatus::rejected,error.what(),{}}; }
 catch(const std::exception& error) { return {GameplayStoreStatus::failed,error.what(),{}}; }
 catch(...) { return {GameplayStoreStatus::failed,"Unknown baseline import failure",{}}; }
}
std::optional<GameplayStoreBaseline> GameplayStore::baseline() const { auto& p=*impl_;BusyGuard guard(p.busy);SqlTransaction transaction(p.db,false);auto result=p.original();transaction.finish();return result; }
Result GameplayStore::verify() const {
 auto& p=*impl_;
 try { BusyGuard guard(p.busy);p.physical_integrity();p.validate_stream();return {true,"SQLite integrity and exact durable stream verified",p.heads().first}; }
 catch(const std::exception& error) { return {false,error.what(),0}; }
}
}
