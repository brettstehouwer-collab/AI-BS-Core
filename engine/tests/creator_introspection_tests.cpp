#include <aibs/persistence.hpp>
#include <bit>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace {
using namespace aibs;
unsigned checks = 0;
void require(bool condition, const char* message) {
 ++checks;
 if (!condition) throw std::runtime_error(message);
}
SchemaRegistry schemas() {
 SchemaRegistry result;
 require(result.add({"x", -100, 100}), "register x");
 require(result.add({"capacity", 0, 100}), "register capacity");
 return result;
}
CreatorSession empty() { return {schemas(), "introspection", "main"}; }

void read_only_schema_and_empty_state() {
 static_assert(std::is_same_v<decltype(std::declval<const SchemaRegistry&>().fields()),
                             const std::map<std::string, FieldSchema>&>);
 static_assert(std::is_same_v<decltype(std::declval<const CreatorSession&>().schemas()),
                             const SchemaRegistry&>);
 static_assert(std::is_same_v<decltype(std::declval<const CreatorSession&>().accepted_transaction("id")),
                             const Transaction*>);
 static_assert(noexcept(std::declval<const CreatorSession&>().charged_storage_bytes()));
 auto session = empty();
 require(session.schemas().fields().size() == 2, "schema enumeration");
 require(session.schemas().fields().at("x").minimum == -100, "schema bounds visible");
 require(session.undo_depth() == 0 && session.redo_depth() == 0 && session.receipt_count() == 0,
         "empty history and receipts");
 require(session.accepted_transaction("absent") == nullptr, "missing receipt pointer");
 require(session.charged_storage_bytes() >= sizeof(CreatorSession), "empty session charged");
 const auto initial = session.charged_storage_bytes();
 const auto revision = session.revision();
 (void)session.schemas().fields();
 (void)session.accepted_transaction("absent");
 require(session.charged_storage_bytes() == initial && session.revision() == revision,
         "introspection has no side effects");
 SchemaRegistry larger = schemas();
 require(larger.add({std::string(2000, 'f'), -1, 1}), "register long field");
 CreatorSession with_schema(std::move(larger), "introspection", "main");
 require(with_schema.charged_storage_bytes() >= initial + 4000,
         "registry keys and repeated schema IDs both charged");
 CreatorSession with_scope(schemas(), std::string(2000, 'p'), std::string(2000, 'b'));
 require(with_scope.charged_storage_bytes() > initial + 3900, "scope strings charged");
}

void original_requests_and_signed_zero_survive_restart(const std::filesystem::path& directory) {
 auto session = empty();
 const Transaction original{"create", 0, {Create{{"cube", "Authored cube", {{"x", 1}}, {}}}}, "Created cube"};
 require(session.apply(original).ok, "create with generated UUID");
 const auto* receipt = session.accepted_transaction("create");
 require(receipt != nullptr && *receipt == original, "original request retained");
 require(std::get<Create>(receipt->edits.front()).entity.persistent_id.empty(),
         "original request not replaced by realized UUID");
 require(!session.world().at("cube").persistent_id.empty(), "realized world UUID differs");
 const Transaction negative_zero{"negative-zero", 1, {SetField{"cube", "x", -0.0, {}}}, "Exact original number"};
 require(session.apply(negative_zero).ok, "write signed zero");
 receipt = session.accepted_transaction("negative-zero");
 require(receipt != nullptr && std::get<SetField>(receipt->edits.front()).persistent_id.empty(),
         "omitted original target UUID retained");
 require(std::bit_cast<std::uint64_t>(std::get<SetField>(receipt->edits.front()).value) == (std::uint64_t{1} << 63),
         "original request preserves negative zero bits");
 require(session.undo_depth() == 2 && session.redo_depth() == 0 && session.receipt_count() == 2,
         "applied counts");
 const auto before_observing = session.charged_storage_bytes();
 require(session.accepted_transaction("negative-zero") == receipt, "same read-only pointer without mutation");
 require(session.charged_storage_bytes() == before_observing, "receipt observation unchanged charge");
 const auto slot = directory / "original.aibs";
 require(CheckpointStore::save(slot, session).ok, "save original receipt");
 auto resumed = empty();
 require(CheckpointStore::load(slot, resumed).ok, "reopen original receipt");
 require(resumed.schemas().fields() == session.schemas().fields(), "schemas survive checkpoint");
 require(resumed.receipt_count() == 2 && resumed.undo_depth() == 2, "history counts survive checkpoint");
 receipt = resumed.accepted_transaction("create");
 require(receipt != nullptr && *receipt == original, "persisted original creation request");
 receipt = resumed.accepted_transaction("negative-zero");
 require(receipt != nullptr && std::bit_cast<std::uint64_t>(std::get<SetField>(receipt->edits.front()).value) == (std::uint64_t{1} << 63),
         "persisted original signed-zero bit pattern");
 require(resumed.apply(original).ok && resumed.revision() == 2 && resumed.receipt_count() == 2,
         "read-only API preserves existing durable retry behavior");
 require(resumed.undo().ok && resumed.undo_depth() == 1 && resumed.redo_depth() == 1,
         "undo exposes moved history depths");
 require(resumed.accepted_transaction("negative-zero") != nullptr && resumed.receipt_count() == 2,
         "undo retains original accepted receipt");
 require(resumed.redo().ok && resumed.undo_depth() == 2 && resumed.redo_depth() == 0,
         "redo exposes moved history depths");
}

std::size_t build_delete_charge(std::size_t name_size, std::size_t description_size) {
 auto session = empty();
 require(session.apply({"create", 0, {Create{{"cube", std::string(name_size, 'n'), {{"x", 1}}, new_uuid()}}},
                        std::string(description_size, 'd')}).ok, "create accounting entity");
 require(session.apply({"erase", 1, {Erase{"cube", session.world().at("cube").persistent_id}}, "Erase cube"}).ok,
         "erase accounting entity");
 require(session.world().empty() && session.known_entity_ids().size() == 1, "retired identity retained");
 require(session.undo_depth() == 2 && session.redo_depth() == 0 && session.receipt_count() == 2,
         "empty world keeps history and receipts");
 return session.charged_storage_bytes();
}

void retained_storage_and_both_history_stacks() {
 const auto short_charge = build_delete_charge(1, 1);
 const auto long_charge = build_delete_charge(3000, 1);
 // The same retired name is owned by the original receipt, applied journal,
 // and two history Worlds even though the live world is empty.
 require(long_charge >= short_charge + 4 * 2999, "all retained name copies charged after deletion");
 const auto long_description = build_delete_charge(1, 3000);
 require(long_description >= short_charge + 2 * 2999, "receipt and journal descriptions both charged");
 auto session = empty();
 const auto before = session.charged_storage_bytes();
 require(session.apply({"create", 0, {Create{{"cube", std::string(3000, 'n'), {{"x", 1}}, new_uuid()}}}, "Create"}).ok,
         "create for redo retention");
 require(session.undo().ok && session.world().empty(), "undo to empty world");
 require(session.undo_depth() == 0 && session.redo_depth() == 1 && session.receipt_count() == 1,
         "redo stores complete history while live empty");
 require(session.charged_storage_bytes() >= before + 9000, "redo world plus receipt and journal charged");
 const auto after_undo = session.charged_storage_bytes();
 require(session.redo().ok && session.redo_depth() == 0 && session.undo_depth() == 1, "restore redo world");
 require(session.charged_storage_bytes() > after_undo, "restored live world and additional journal charged");
 const auto accepted = session.receipt_count();
 const auto charged = session.charged_storage_bytes();
 require(!session.apply({"rejected", session.revision(), {SetField{"absent", "x", 1, new_uuid()}}, "Rejected"}).ok,
         "reject invalid transaction");
 require(session.receipt_count() == accepted && session.charged_storage_bytes() == charged,
         "rejection adds no retained storage or receipt");
}
}

int main() {
 const auto directory = std::filesystem::temp_directory_path() / ("aibs-introspection-" + aibs::new_uuid());
 std::filesystem::create_directories(directory);
 try {
  read_only_schema_and_empty_state();
  original_requests_and_signed_zero_survive_restart(directory);
  retained_storage_and_both_history_stacks();
  std::filesystem::remove_all(directory);
  std::cout << "PASS: " << checks << " creator introspection checks\n";
  return 0;
 } catch (const std::exception& error) {
  std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n';
  std::filesystem::remove_all(directory);
  return 1;
 }
}
