#pragma once

#include <cstddef>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <variant>
#include <vector>

namespace aibs {
std::string new_uuid();
bool is_uuid(const std::string& value) noexcept;
struct FieldSchema { std::string id; double minimum; double maximum; bool operator==(const FieldSchema&) const = default; };
class SchemaRegistry {
public:
 bool add(FieldSchema schema);
 bool accepts(const std::string& field, double value) const;
 const std::map<std::string, FieldSchema>& fields() const noexcept { return fields_; }
private:
 friend struct SnapshotCodec;
 std::map<std::string, FieldSchema> fields_;
};
struct Entity {
 std::string id;
 std::string name;
 std::map<std::string, double> fields;
 std::string persistent_id;
 bool operator==(const Entity&) const = default;
};
using World = std::map<std::string, Entity>;
struct Create { Entity entity; bool operator==(const Create&) const = default; };
struct Erase { std::string entity; std::string persistent_id; bool operator==(const Erase&) const = default; };
struct SetField { std::string entity; std::string field; double value; std::string persistent_id; bool operator==(const SetField&) const = default; };
using Edit = std::variant<Create, Erase, SetField>;
struct Transaction {
 std::string id;
 std::uint64_t expected_revision;
 std::vector<Edit> edits;
 std::string description;
 bool operator==(const Transaction&) const = default;
};
struct Result { bool ok; std::string message; std::uint64_t revision; };
struct MemoryEvent {
 std::string project;
 std::string branch;
 std::string operation;
 std::string kind;
 std::uint64_t revision;
 std::string world_id;
 std::vector<Edit> edits;
 std::string description;
 bool operator==(const MemoryEvent&) const = default;
};
class AdamMemory {
public:
 const std::vector<MemoryEvent>& events() const noexcept { return events_; }
private:
 friend class CreatorSession;
 friend struct SnapshotCodec;
 std::vector<MemoryEvent> events_;
};
// One authoritative owner; UI, code and future AI adapters submit Transaction.
// Edits publish in memory. CheckpointStore explicitly publishes durable snapshots.
class CreatorSession {
public:
 CreatorSession(SchemaRegistry schemas, std::string project, std::string branch);
 Result apply(const Transaction& transaction);
 Result undo();
 Result redo();
 std::uint64_t revision() const noexcept { return revision_; }
 const std::string& project_id() const noexcept { return project_; }
 const std::string& branch_id() const noexcept { return branch_; }
 const std::string& world_id() const noexcept { return world_id_; }
 const std::string& checkpoint_id() const noexcept { return checkpoint_id_; }
 const World& world() const noexcept { return world_; }
 // Read-only owner view of every entity UUID used in this restored history,
 // including alive entities and identities retired by deletion or undo.
 const std::set<std::string>& known_entity_ids() const noexcept { return used_entity_ids_; }
 const AdamMemory& memory() const noexcept { return memory_; }
 const SchemaRegistry& schemas() const noexcept { return schemas_; }
 std::size_t undo_depth() const noexcept { return undo_.size(); }
 std::size_t redo_depth() const noexcept { return redo_.size(); }
 std::size_t receipt_count() const noexcept { return receipts_.size(); }
 // Original accepted request, before UUID realization; invalidated by mutation.
 const Transaction* accepted_transaction(const std::string& id) const noexcept;
 // Saturating logical storage charge for owned content, including retained
 // history/receipts. Not measured RSS, spare capacity, or transient copy memory.
 std::size_t charged_storage_bytes() const noexcept;
 World start_play() const { return world_; }
private:
 friend struct SnapshotCodec;
 friend class CheckpointStore;
 struct History { World before; World after; };
 struct Receipt { Transaction transaction; Result result; };
 SchemaRegistry schemas_;
 std::string project_, branch_;
 std::string world_id_, checkpoint_id_;
 std::set<std::string> used_entity_ids_;
 World world_;
 std::uint64_t revision_ = 0;
 AdamMemory memory_;
 std::vector<History> undo_, redo_;
 std::map<std::string, Receipt> receipts_;
 Result fail(std::string message) const;
 Result travel(bool backwards);
 void swap_state(CreatorSession& other) noexcept;
};
class FixedStep {
public:
 unsigned advance(double seconds);
 void pause(bool paused) noexcept { paused_ = paused; accumulator_ = 0; }
 std::uint64_t overloads() const noexcept { return overloads_; }
 static constexpr double tick_seconds = 1.0 / 60.0;
private:
 double accumulator_ = 0;
 bool paused_ = false;
 std::uint64_t overloads_ = 0;
};
}
