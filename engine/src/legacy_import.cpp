#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/legacy_import.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <fstream>
#include <set>
#include <stdexcept>
#include <type_traits>

namespace aibs {
namespace {
void require(bool ok,const char* why) { if(!ok) throw std::invalid_argument(why); }
using Bytes=std::vector<std::uint8_t>;
Bytes captured_bytes(const std::filesystem::path& file) {
 const auto size=std::filesystem::file_size(file);
 require(size>=24 && size<=CheckpointStore::maximum_file_bytes,"Original checkpoint size is outside format-1 bounds");
 std::ifstream input(file,std::ios::binary);require(input.good(),"Cannot read original checkpoint");
 Bytes data(static_cast<std::size_t>(size));
 input.read(reinterpret_cast<char*>(data.data()),static_cast<std::streamsize>(data.size()));
 require(input.gcount()==static_cast<std::streamsize>(data.size()) && input.peek()==std::char_traits<char>::eof(),"Original checkpoint changed or could not be captured completely");
 return data;
}
class StagedCheckpoint {
 std::filesystem::path path_;
public:
 explicit StagedCheckpoint(const Bytes& data) {
  require(data.size()>=24 && data.size()<=CheckpointStore::maximum_file_bytes,"Invalid preserved checkpoint size");
  const auto base=std::filesystem::temp_directory_path()/"AI-BS/LegacyImport";
  std::filesystem::create_directories(base);path_=base/(new_uuid()+".aibs");
  HANDLE handle=CreateFileW(path_.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_TEMPORARY,nullptr);
  if(handle==INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot stage captured checkpoint for validation");
  try {
   DWORD written=0;
   if(!WriteFile(handle,data.data(),static_cast<DWORD>(data.size()),&written,nullptr) || written!=data.size() || !FlushFileBuffers(handle))
    throw std::runtime_error("Cannot finish staging captured checkpoint");
  } catch(...) {
   CloseHandle(handle);std::error_code ignored;std::filesystem::remove(path_,ignored);throw;
  }
  CloseHandle(handle);
 }
 ~StagedCheckpoint() {
  std::error_code ignored;std::filesystem::remove(path_,ignored);
  auto lock=path_;lock+=L".lock";std::filesystem::remove(lock,ignored);
 }
 StagedCheckpoint(const StagedCheckpoint&)=delete;
 StagedCheckpoint& operator=(const StagedCheckpoint&)=delete;
 const std::filesystem::path& path() const noexcept { return path_; }
};
bool same_file(const std::filesystem::path& source,const std::filesystem::path& database) {
 if(std::filesystem::weakly_canonical(source)==std::filesystem::weakly_canonical(database)) return true;
 std::error_code error;return std::filesystem::equivalent(source,database,error);
}
void validate_projection(const ComponentRecord& record,const std::vector<ComponentSchema>& schemas) {
 const auto definition=std::find_if(schemas.begin(),schemas.end(),[&](const auto& schema) {
  return schema.type_id==record.type_id && schema.version==record.version;
 });
 require(definition!=schemas.end(),"Legacy projection has an unregistered component type/version");
 for(const auto& rule:definition->fields)
  require(!rule.required || record.fields.contains(rule.id),"Legacy projection is missing a required component field");
 for(const auto& [id,value]:record.fields) {
  const auto rule=std::find_if(definition->fields.begin(),definition->fields.end(),[&](const auto& field) { return field.id==id; });
  require(rule!=definition->fields.end() && !value.valueless_by_exception() && value.index()==static_cast<std::size_t>(rule->kind),
          "Legacy projection contains an unknown field or mismatched field type");
  if(const auto* number=std::get_if<double>(&value))
   require(*number>=rule->minimum && *number<=rule->maximum,"Legacy projection number is outside its registered bounds");
 }
}
}
LegacyImportResult import_format1_checkpoint(const std::filesystem::path& source,
 const std::filesystem::path& database,const SchemaRegistry& original_schema,
 const std::string& project,const std::string& branch,const std::vector<ComponentSchema>& component_schemas,
 const LegacyComponentAdapter& adapter,std::string timeline_id,CheckpointValidator original_validator) {
 LegacyImportResult result;
 try {
  require(!source.empty()&&!database.empty()&&!same_file(source,database),"Original checkpoint and SQLite database must be different files");
  require(static_cast<bool>(adapter),"An explicit original-to-component adapter is required");
  // Freeze a bounded, canonical registry before invoking caller adapter code.
  const auto registered=gameplay_codec::decode_schemas(gameplay_codec::encode_schemas(component_schemas));
  const auto data=captured_bytes(source);StagedCheckpoint staged(data);
  CreatorSession original(original_schema,project,branch);
  const auto loaded=CheckpointStore::load(staged.path(),original,original_validator);require(loaded.ok,loaded.message.c_str());
  if(timeline_id.empty()) timeline_id=original.world_id();
  result.scope={project,original.world_id(),branch,std::move(timeline_id),GameplayContext::player_world};
  result.checkpoint_id=original.checkpoint_id();result.source_revision=original.revision();
  result.entities=original.world().size();result.memory_events=original.memory().events().size();
  GameplayStoreBaseline baseline;baseline.revision=original.revision();baseline.legacy_checkpoint=data;
  std::set<std::pair<std::string,std::string>> keys;std::size_t total_bytes=data.size();
  for(const auto& [alias,entity]:original.world()) {
   (void)alias;const auto source_id=entity.persistent_id;
   auto adapter_input=entity;auto records=adapter(adapter_input);
   require(!records.empty()&&records.size()<=128,"Original entity requires a bounded explicit component projection");
   for(auto& record:records) {
    require(record.entity_id==source_id,"Legacy projection cannot rewrite original entity identity");
    const auto encoded=gameplay_codec::encode_component(record);
    validate_projection(record,registered);
    require(encoded.size()<=64*1024*1024-total_bytes,"Legacy projection exceeds bounded baseline size");total_bytes+=encoded.size();
    require(baseline.components.size()<10000,"Legacy projection exceeds 10000 components");
    require(keys.emplace(record.entity_id,record.type_id).second,"Duplicate projected component");
    baseline.components.push_back(std::move(record));
   }
  }
  // All source capture, old-schema replay and projection happen before the new
  // database is opened. The source path is never passed to a writer.
  GameplayStore store(database,result.scope,registered);
  const auto saved=store.seed(baseline);result.message=saved.message;
  result.ok=saved.status==GameplayStoreStatus::committed||saved.status==GameplayStoreStatus::retry;
  result.retry=saved.status==GameplayStoreStatus::retry;
  return result;
 } catch(const std::exception& e) { result.message=e.what();return result; }
}
CheckpointResult restore_imported_checkpoint(const GameplayStore& store,CreatorSession& destination) {
 static_assert(std::is_nothrow_move_assignable_v<CreatorSession>);
 try {
  const auto baseline=store.baseline();
  require(baseline.has_value()&&!baseline->legacy_checkpoint.empty(),"No imported original checkpoint exists");
  StagedCheckpoint staged(baseline->legacy_checkpoint);auto candidate=destination;
  const auto loaded=CheckpointStore::load(staged.path(),candidate);require(loaded.ok,loaded.message.c_str());
  const auto scope=store.recover().scope;
  require(candidate.project_id()==scope.project_id && candidate.branch_id()==scope.branch_id &&
          candidate.world_id()==scope.world_id && candidate.revision()==baseline->revision,
          "Preserved checkpoint scope/identity/revision does not match its imported baseline");
  CheckpointResult ready{true,"Preserved original checkpoint restored",candidate.revision(),candidate.checkpoint_id()};
  destination=std::move(candidate);return ready;
 } catch(const std::exception& e) { return {false,e.what(),destination.revision(),destination.checkpoint_id()}; }
}
}
