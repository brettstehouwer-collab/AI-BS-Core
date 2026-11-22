#include <aibs/persistence.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace {
using namespace aibs;
void require(bool condition, const char* message) {
 if (!condition) throw std::runtime_error(message);
}
SchemaRegistry schemas() {
 SchemaRegistry result;
 require(result.add({"x", -100, 100}), "register schema");
 return result;
}
void same_source(const CreatorSession& before, const CreatorSession& after) {
 require(before.world() == after.world(), "assessment preserves live entities");
 require(before.memory().events() == after.memory().events(), "assessment preserves original journal");
 require(before.known_entity_ids() == after.known_entity_ids(), "assessment preserves retired identities");
 require(before.revision() == after.revision() && before.world_id() == after.world_id(), "assessment preserves revision/world");
 require(before.checkpoint_id() == after.checkpoint_id(), "assessment never sets original checkpoint ID");
 require(before.project_id() == after.project_id() && before.branch_id() == after.branch_id(), "assessment preserves scope");
}
CreatorSession small_session() {
 CreatorSession session(schemas(), "assessment-project", "main");
 require(session.apply({"seed", 0, {Create{{"cube", "Cube", {{"x", 1}}, new_uuid()}}}, "Authored cube"}).ok, "seed");
 return session;
}
void assessment_without_publication(const std::filesystem::path& directory) {
 auto source = small_session();
 const auto original = source;
 const auto assessment = CheckpointStore::assess(source);
 require(assessment.compatible && assessment.encoded_bytes >= 24, "unsaved session has an exact encoding assessment");
 require(source.checkpoint_id().empty(), "unsaved source stays unsaved");
 same_source(original, source);
 require(std::filesystem::is_empty(directory), "assessment writes no files/lock/temp files");
 const auto slot = directory / "checkpoint.aibs";
 require(CheckpointStore::save(slot, source).ok, "publish independent actual save");
 require(assessment.encoded_bytes == std::filesystem::file_size(slot), "assessed bytes equal real format-1 output bytes");
 const auto saved = source;
 const auto saved_assessment = CheckpointStore::assess(source);
 require(saved_assessment.compatible && saved_assessment.encoded_bytes == assessment.encoded_bytes, "saved session remains exactly compatible");
 same_source(saved, source);
 require(std::filesystem::file_size(slot) == saved_assessment.encoded_bytes, "assessment leaves existing output unchanged");
 auto expected_history = saved;
 auto assessed_history = source;
 require(expected_history.undo().ok && assessed_history.undo().ok, "history remains operational after assessment");
 same_source(expected_history, assessed_history);
 require(expected_history.redo().ok && assessed_history.redo().ok, "redo remains operational after assessment");
 same_source(expected_history, assessed_history);
}
void oversized_string() {
 auto source = small_session();
 require(source.apply({"long-description", source.revision(), {SetField{"cube", "x", 2, source.world().at("cube").persistent_id}}, std::string(4097, 'd')}).ok, "Core accepts in-memory oversized description");
 const auto before = source;
 const auto assessment = CheckpointStore::assess(source);
 require(!assessment.compatible && assessment.encoded_bytes == 0, "oversized description is incompatible");
 require(assessment.message.find("string/size limit") != std::string::npos, "exact encoder identifies oversized string");
 same_source(before, source);
}
void undo_collection_limit() {
 CreatorSession source(schemas(), "assessment-project", "main");
 constexpr std::size_t count = 5001;
 for (std::size_t begin = 0; begin < count; begin += 1024) {
  Transaction transaction{"batch-" + std::to_string(begin), source.revision(), {}, "Batch authored nodes"};
  for (std::size_t index = begin; index < count && index < begin + 1024; ++index) {
   transaction.edits.push_back(Create{{"node-" + std::to_string(index), "N", {{"x", 0}}, new_uuid()}});
  }
  require(source.apply(transaction).ok, "batch create under existing 1024-edit limit");
 }
 require(source.apply({"adjust", source.revision(), {SetField{"node-0", "x", 1, source.world().at("node-0").persistent_id}}, "Adjust one field"}).ok, "small update to a large world");
 require(source.undo().ok, "undo realizes 5001 erase plus 5001 create edits");
 require(source.world().size() == count && source.memory().events().back().edits.size() == 10002, "fixture crosses exact format-1 collection limit");
 const auto before = source;
 const auto assessment = CheckpointStore::assess(source);
 require(!assessment.compatible && assessment.message.find("collection limit") != std::string::npos, "exact format-1 assessment catches oversize undo event");
 same_source(before, source);
}
void replay_byte_limit() {
 CreatorSession source(schemas(), "assessment-project", "main");
 Transaction seed{"seed", 0, {}, "Dense-history fixture"};
 for (unsigned index = 0; index < 64; ++index) seed.edits.push_back(Create{{"node-" + std::to_string(index), std::string(4096, 'n'), {{"x", 0}}, new_uuid()}});
 require(source.apply(seed).ok, "seed long-name world with legal strings");
 const auto uuid = source.world().at("node-0").persistent_id;
 for (unsigned index = 0; index < 80; ++index) {
  require(source.apply({"update-" + std::to_string(index), source.revision(), {SetField{"node-0", "x", static_cast<double>(index % 2), uuid}}, "Change one field"}).ok, "accumulate existing Core history");
 }
 const auto before = source;
 const auto assessment = CheckpointStore::assess(source);
 require(!assessment.compatible && assessment.message.find("replay byte budget") != std::string::npos, "exact validation catches replay byte expansion before publication");
 same_source(before, source);
}
}
int main() {
 const auto directory = std::filesystem::temp_directory_path() / ("aibs-assessment-" + aibs::new_uuid());
 std::filesystem::create_directories(directory);
 try {
  assessment_without_publication(directory);
  oversized_string();
  undo_collection_limit();
  replay_byte_limit();
  std::filesystem::remove_all(directory);
  std::cout << "PASS: read-only exact encoding assessment, actual-size parity, original state/history, string/undo/replay bounds\n";
  return 0;
 } catch (const std::exception& error) {
  std::cerr << "FAIL: " << error.what() << '\n';
  std::filesystem::remove_all(directory);
  return 1;
 }
}
