#include <aibs/engine.hpp>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace aibs {
namespace {
// Fixed node overhead is a logical allocation allowance, independent of the
// standard library's node layout. Object bodies and every owned string payload
// are charged separately, including duplicated keys and history Worlds.
constexpr std::size_t node_charge = 64;
struct StorageCharge {
 std::size_t bytes = 0;
 void add(std::size_t value) noexcept {
  const auto maximum = (std::numeric_limits<std::size_t>::max)();
  bytes = value > maximum - bytes ? maximum : bytes + value;
 }
 void text(const std::string& value) noexcept { add(value.size()); add(1); }
 void entity(const Entity& value) noexcept {
  text(value.id); text(value.name); text(value.persistent_id);
  for (const auto& [key, number] : value.fields) {
   (void)number;
   add(node_charge); add(sizeof(std::map<std::string, double>::value_type)); text(key);
  }
 }
 void world(const World& value) noexcept {
  for (const auto& [key, item] : value) {
   add(node_charge); add(sizeof(World::value_type)); text(key); entity(item);
  }
 }
 void edits(const std::vector<Edit>& values) noexcept {
  for (const auto& edit : values) {
   add(sizeof(Edit));
   std::visit([&](const auto& operation) {
    using T = std::decay_t<decltype(operation)>;
    if constexpr (std::is_same_v<T, Create>) entity(operation.entity);
    else if constexpr (std::is_same_v<T, Erase>) {
     text(operation.entity); text(operation.persistent_id);
    } else {
     text(operation.entity); text(operation.field); text(operation.persistent_id);
    }
   }, edit);
  }
 }
 void transaction(const Transaction& value) noexcept {
  text(value.id); text(value.description); edits(value.edits);
 }
};
}
CreatorSession::CreatorSession(SchemaRegistry schemas, std::string project, std::string branch)
 : schemas_(std::move(schemas)), project_(std::move(project)), branch_(std::move(branch)), world_id_(new_uuid()) {
 if (project_.empty() || branch_.empty()) throw std::invalid_argument("Project and branch must be specified");
}
Result CreatorSession::fail(std::string message) const { return {false, std::move(message), revision_}; }
const Transaction* CreatorSession::accepted_transaction(const std::string& id) const noexcept {
 const auto found = receipts_.find(id);
 return found == receipts_.end() ? nullptr : &found->second.transaction;
}
std::size_t CreatorSession::charged_storage_bytes() const noexcept {
 StorageCharge charge;
 charge.add(sizeof(CreatorSession));
 charge.text(project_); charge.text(branch_); charge.text(world_id_); charge.text(checkpoint_id_);
 for (const auto& [key, field] : schemas_.fields()) {
  charge.add(node_charge); charge.add(sizeof(std::map<std::string, FieldSchema>::value_type));
  charge.text(key); charge.text(field.id);
 }
 for (const auto& id : used_entity_ids_) {
  charge.add(node_charge); charge.add(sizeof(std::string)); charge.text(id);
 }
 charge.world(world_);
 for (const auto& event : memory_.events_) {
  charge.add(sizeof(MemoryEvent));
  charge.text(event.project); charge.text(event.branch); charge.text(event.operation);
  charge.text(event.kind); charge.text(event.world_id); charge.text(event.description);
  charge.edits(event.edits);
 }
 for (const auto& [key, receipt] : receipts_) {
  charge.add(node_charge); charge.add(sizeof(decltype(receipts_)::value_type));
  charge.text(key); charge.transaction(receipt.transaction); charge.text(receipt.result.message);
 }
 for (const auto* stack : {&undo_, &redo_}) {
  for (const auto& history : *stack) {
   charge.add(sizeof(History)); charge.world(history.before); charge.world(history.after);
  }
 }
 return charge.bytes;
}
Result CreatorSession::apply(const Transaction& transaction) {
 if (transaction.id.empty()) return fail("Operation ID is required");
 if (auto it = receipts_.find(transaction.id); it != receipts_.end()) {
  return it->second.transaction == transaction ? it->second.result : fail("Operation ID was already used for different content");
 }
 if (transaction.expected_revision != revision_) return fail("Scene revision conflict");
 if (transaction.edits.empty()) return fail("Empty transaction");
 if (transaction.edits.size() > 1024) return fail("Transaction exceeds 1024 edits");
 auto candidate = world_;
 auto used_ids = used_entity_ids_;
 auto realized = transaction.edits;
 std::string error;
 for (auto& edit : realized) {
  std::visit([&](auto& op) {
   using T = std::decay_t<decltype(op)>;
   if constexpr (std::is_same_v<T, Create>) {
    if (op.entity.id.empty() || candidate.contains(op.entity.id)) { error = "Empty or duplicate entity ID"; return; }
    for (const auto& [field, value] : op.entity.fields) {
     if (!schemas_.accepts(field, value)) { error = "Unknown or invalid field: " + field; return; }
    }
    if (op.entity.persistent_id.empty()) op.entity.persistent_id = new_uuid();
    if (!is_uuid(op.entity.persistent_id) || !used_ids.insert(op.entity.persistent_id).second) { error = "Invalid or previously used persistent entity UUID"; return; }
    candidate.emplace(op.entity.id, op.entity);
   } else if constexpr (std::is_same_v<T, Erase>) {
    const auto target = candidate.find(op.entity);
    if (target == candidate.end()) { error = "Entity does not exist: " + op.entity; return; }
    if (!op.persistent_id.empty() && op.persistent_id != target->second.persistent_id) { error = "Stale entity UUID"; return; }
    op.persistent_id = target->second.persistent_id;
    if (!candidate.erase(op.entity)) error = "Entity does not exist: " + op.entity;
   } else {
    auto it = candidate.find(op.entity);
    if (it == candidate.end()) { error = "Entity does not exist: " + op.entity; return; }
    if (!op.persistent_id.empty() && op.persistent_id != it->second.persistent_id) { error = "Stale entity UUID"; return; }
    op.persistent_id = it->second.persistent_id;
    if (!schemas_.accepts(op.field, op.value)) { error = "Unknown or invalid field: " + op.field; return; }
    it->second.fields[op.field] = op.value;
   }
  }, edit);
  if (!error.empty()) return fail(std::move(error));
 }
 // Stage allocations before publishing state, memory and receipt together.
 auto undo = undo_;
 undo.push_back({world_, candidate});
 auto events = memory_.events_;
 events.push_back({project_, branch_, transaction.id, "authoring.applied", revision_ + 1, world_id_, realized, transaction.description});
 Result result{true, "Applied in memory; not durably saved", revision_ + 1};
 auto receipts = receipts_;
 receipts.emplace(transaction.id, Receipt{transaction, result});
 world_.swap(candidate);
 used_entity_ids_.swap(used_ids);
 undo_.swap(undo);
 memory_.events_.swap(events);
 receipts_.swap(receipts);
 redo_.clear();
 ++revision_;
 return result;
}
Result CreatorSession::travel(bool backwards) {
 const auto& source = backwards ? undo_ : redo_;
 if (source.empty()) return fail(backwards ? "Nothing to undo" : "Nothing to redo");
 auto undo = undo_;
 auto redo = redo_;
 auto& from = backwards ? undo : redo;
 auto& to = backwards ? redo : undo;
 auto entry = from.back();
 World candidate = backwards ? entry.before : entry.after;
 to.push_back(entry);
 from.pop_back();
 auto events = memory_.events_;
 // History events contain the resulting world as realized Create records and
 // erase records for the previous world, so targets stay unambiguous by UUID.
 std::vector<Edit> changes;
 for (const auto& [id, entity] : world_) changes.push_back(Erase{id, entity.persistent_id});
 for (const auto& [id, entity] : candidate) { (void)id; changes.push_back(Create{entity}); }
 events.push_back({project_, branch_, "history:" + std::to_string(revision_ + 1), backwards ? "authoring.undone" : "authoring.redone", revision_ + 1, world_id_, std::move(changes), backwards ? "Undid an authored change" : "Redid an authored change"});
 Result result{true, "History applied in memory; not durably saved", revision_ + 1};
 world_.swap(candidate);
 undo_.swap(undo);
 redo_.swap(redo);
 memory_.events_.swap(events);
 ++revision_;
 return result;
}
Result CreatorSession::undo() { return travel(true); }
Result CreatorSession::redo() { return travel(false); }
void CreatorSession::swap_state(CreatorSession& other) noexcept {
 world_.swap(other.world_);
 world_id_.swap(other.world_id_);
 checkpoint_id_.swap(other.checkpoint_id_);
 used_entity_ids_.swap(other.used_entity_ids_);
 std::swap(revision_, other.revision_);
 memory_.events_.swap(other.memory_.events_);
 undo_.swap(other.undo_);
 redo_.swap(other.redo_);
 receipts_.swap(other.receipts_);
}
}
