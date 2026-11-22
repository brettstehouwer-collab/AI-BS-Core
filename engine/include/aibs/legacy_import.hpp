#pragma once
#include <aibs/gameplay_store.hpp>
#include <aibs/persistence.hpp>

namespace aibs {
using LegacyComponentAdapter=std::function<std::vector<ComponentRecord>(const Entity&)>;
struct LegacyImportResult {
 bool ok=false,retry=false;
 std::string message;
 GameplayScope scope;
 std::string checkpoint_id;
 std::uint64_t source_revision=0;
 std::size_t entities=0,memory_events=0;
};
// Capture/read/validate the original format-1 snapshot using its original schema.
// The database receives a typed baseline and the exact original bytes together.
// Adapter projection must retain each source entity's UUID; original evidence
// also preserves retired IDs, receipts and complete undo/redo independently.
// Default root timeline ID is the source world ID, giving stable import retries.
// Optional game validation receives the replayed captured original before any
// component adapter runs or the destination database is opened.
LegacyImportResult import_format1_checkpoint(const std::filesystem::path& source,
 const std::filesystem::path& database,const SchemaRegistry& original_schema,
 const std::string& project,const std::string& branch,
 const std::vector<ComponentSchema>& component_schemas,const LegacyComponentAdapter& adapter,
 std::string timeline_id={},CheckpointValidator original_validator=nullptr);
// Restores the preserved ORIGINAL authoring snapshot, not later typed gameplay
// deltas. The latter are recovered with GameplayStore::recover(). Failure leaves
// the destination unchanged, including schema/project mismatch or corrupt bytes.
CheckpointResult restore_imported_checkpoint(const GameplayStore& store,CreatorSession& destination);
}
