#pragma once
#include <aibs/first_boot_content.hpp>
#include <aibs/creator_host.hpp>
#include <filesystem>

namespace aibs {
struct ContentSetField {std::string entity_id,field;GameplayValue value;};
struct ContentCreateFixture {FirstBootContentFixture fixture;};
struct ContentEraseFixture {std::string entity_id;};
struct ContentCreateHardware {Entity entity;};
struct ContentEraseHardware {std::string entity_id;};
struct ContentCreateAssetPlacement {FirstBootAssetPlacement placement;};
struct ContentEraseAssetPlacement {std::string entity_id;};
struct ContentCreateMemoryBinding {FirstBootMemoryBinding memory;};
struct ContentEraseMemoryBinding {std::string entity_id;};
using ContentEdit=std::variant<ContentSetField,ContentCreateFixture,ContentEraseFixture,ContentCreateHardware,ContentEraseHardware,ContentCreateAssetPlacement,ContentEraseAssetPlacement,ContentCreateMemoryBinding,ContentEraseMemoryBinding>;
struct ContentEditRequest {std::string id;std::uint64_t expected_revision;std::string expected_fingerprint,label;std::vector<ContentEdit> edits;};
struct ContentHistoryRequest {std::string id;std::uint64_t expected_revision;std::string expected_fingerprint;bool redo=false;};
struct ScopedContentEditRequest {CreatorScope scope;std::string definition_id;ContentEditRequest request;};
// Authorable fields only. Runtime progress/repair/door-state flags never appear.
// Observation rows are not gameplay components or their persistence envelopes.
struct ContentAuthoringRow {
 std::string entity_id,type_id,name;
 std::map<std::string,GameplayValue> fields;
 ContentAuthoringRow(ComponentRecord record):entity_id(std::move(record.entity_id)),type_id(std::move(record.type_id)),fields(std::move(record.fields)){
  const auto found=fields.find("name");name=found!=fields.end()&&std::holds_alternative<std::string>(found->second)?std::get<std::string>(found->second):type_id;
 }
};
std::vector<ContentAuthoringRow> content_authoring_rows(const FirstBootContent&);
std::vector<unsigned char> encode_content_edit(const ContentEditRequest&);
ContentEditRequest decode_content_edit(std::span<const unsigned char>);
std::vector<unsigned char> encode_scoped_content_edit(const ScopedContentEditRequest&);
ScopedContentEditRequest decode_scoped_content_edit(std::span<const unsigned char>);
namespace detail {struct ContentAuthoringData;}
class ContentAuthoringSnapshot {
 std::shared_ptr<const detail::ContentAuthoringData> owner_;
 friend class ContentAuthoringHost;
 explicit ContentAuthoringSnapshot(std::shared_ptr<const detail::ContentAuthoringData>);
public:
 const CreatorScope scope;
 const std::uint64_t revision;
 const FirstBootContent content;
 const std::string checkpoint_id;
 const std::set<std::string>& known_ids;
 const std::size_t undo_depth,redo_depth,receipt_count;
 const bool dirty;
};
class ContentPreparedChange {
 friend class ContentAuthoringHost;
 std::string owner_;
 std::uint64_t generation_;
 std::shared_ptr<const detail::ContentAuthoringData> after_;
 std::shared_ptr<const ContentAuthoringSnapshot> snapshot_;
 FirstBootContentPreview dependencies_;
 std::size_t charged_bytes_,encoded_bytes_;
 ContentPreparedChange(std::string,std::uint64_t,std::shared_ptr<const detail::ContentAuthoringData>,std::shared_ptr<const ContentAuthoringSnapshot>,FirstBootContentPreview,std::size_t,std::size_t);
public:
 const FirstBootContentPreview& dependencies()const noexcept{return dependencies_;}
 std::shared_ptr<const ContentAuthoringSnapshot> snapshot()const noexcept{return snapshot_;}
 std::size_t encoded_document_bytes()const noexcept{return encoded_bytes_;}
};
using ContentPreparedPtr=std::shared_ptr<const ContentPreparedChange>;
enum class ContentAuthoringStatus {prepared,applied,duplicate,undone,redone,saved,rejected,failed};
struct ContentAuthoringResult {ContentAuthoringStatus status;std::string message;std::uint64_t revision;ContentPreparedPtr change{};};
class ContentAuthoringHost {
 struct State;std::unique_ptr<State> state_;
 static std::shared_ptr<const ContentAuthoringSnapshot> describe(std::shared_ptr<const detail::ContentAuthoringData>);
public:
 static constexpr std::size_t maximum_operations=256,maximum_file_bytes=1024*1024,maximum_state_bytes=16*1024*1024;
 ContentAuthoringHost(FirstBootContent,std::string project,std::string branch,std::set<std::string> reserved_ids={});
 ~ContentAuthoringHost();
 ContentAuthoringHost(const ContentAuthoringHost&)=delete;
 ContentAuthoringHost& operator=(const ContentAuthoringHost&)=delete;
 ContentAuthoringHost(ContentAuthoringHost&&) noexcept;
 static ContentAuthoringHost open(const std::filesystem::path&,const std::string& project,const std::string& branch);
 std::shared_ptr<const ContentAuthoringSnapshot> snapshot()const noexcept;
 const std::string& epoch_id()const noexcept;
 // Runtime dependency context, never serialized into content or journals.
 // Binding itself does not read/create files; recovery can inspect/erase
 // missing dependencies. Normal publication/save validates the current store.
 void bind_asset_store(const std::filesystem::path&);
 ContentAuthoringResult preview(const CreatorScope&,const ContentEditRequest&);
 ContentAuthoringResult preview(const ScopedContentEditRequest&);
 ContentAuthoringResult apply(ContentPreparedPtr);
 ContentAuthoringResult apply(const CreatorScope&,const ContentEditRequest&);
 ContentAuthoringResult apply(const ScopedContentEditRequest&);
 ContentAuthoringResult travel(const CreatorScope&,const ContentHistoryRequest&);
 ContentAuthoringResult save(const std::filesystem::path&);
};
}
