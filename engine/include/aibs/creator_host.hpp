#pragma once
#include <aibs/persistence.hpp>
#include <functional>
#include <memory>

namespace aibs {
struct CreatorScope {
 std::string project, branch, world_id;
 bool operator==(const CreatorScope&) const = default;
};
struct CreatorHostLimits {
 std::size_t maximum_live_entities = 10000;
 std::size_t maximum_fields_per_entity = 64;
 std::size_t maximum_string_bytes = 4096;
 std::size_t maximum_edits = 256;
 std::size_t maximum_request_bytes = 1024 * 1024;
 std::size_t maximum_session_bytes = 64 * 1024 * 1024;
 std::size_t maximum_prepared = 8;
 std::size_t maximum_prepared_bytes = 64 * 1024 * 1024;
 std::size_t maximum_history_receipts = 1024;
};
// References retain a private immutable session; publication never mutates it.
// Logical storage budgets do not bound RSS, temporary Core copies, or snapshots
// and Play contexts retained by a client after the host releases them.
class CreatorSnapshot {
 std::shared_ptr<const CreatorSession> owner_;
 friend class CreatorHost;
 explicit CreatorSnapshot(std::shared_ptr<const CreatorSession> owner, std::size_t reserved_checkpoint_bytes);
public:
 const CreatorScope scope;
 const std::uint64_t revision;
 const World& world;
 const std::vector<MemoryEvent>& history;
 const std::map<std::string, FieldSchema>& schemas;
 const std::string& checkpoint_id;
 const std::size_t undo_depth, redo_depth, receipt_count, charged_bytes;
 CreatorSnapshot(const CreatorSnapshot&) = delete;
 CreatorSnapshot& operator=(const CreatorSnapshot&) = delete;
};
struct CreatorDependencyPreview {
 bool valid = true;
 bool render_rebuild = false, collision_rebuild = false;
 bool navigation_validated = false;
 std::vector<std::string> changed_uuids, dependency_keys, notes;
 CheckpointAssessment save{false, 0, "Not assessed"};
 bool operator==(const CreatorDependencyPreview&) const = default;
};
using CreatorAssessor = std::function<CreatorDependencyPreview(const CreatorSnapshot&, const CreatorSnapshot&, const Transaction&)>;
namespace detail { struct CreatorEpoch; }
class CreatorPreparedChange {
 friend class CreatorHost;
 std::shared_ptr<const detail::CreatorEpoch> owner_;
 std::uint64_t generation_;
 Transaction request_;
 std::shared_ptr<const CreatorSnapshot> before_, after_;
 CreatorDependencyPreview dependencies_;
 CreatorAssessor assessor_;
 CreatorPreparedChange(std::shared_ptr<const detail::CreatorEpoch>, std::uint64_t,
  Transaction, std::shared_ptr<const CreatorSnapshot>, std::shared_ptr<const CreatorSnapshot>,
  CreatorDependencyPreview, CreatorAssessor);
public:
 std::shared_ptr<const CreatorSnapshot> snapshot() const noexcept { return after_; }
 const CreatorDependencyPreview& dependencies() const noexcept { return dependencies_; }
 CreatorPreparedChange(const CreatorPreparedChange&) = delete;
 CreatorPreparedChange& operator=(const CreatorPreparedChange&) = delete;
};
using CreatorPreparedPtr = std::shared_ptr<const CreatorPreparedChange>;
enum class CreatorHostStatus { prepared, applied, duplicate, undone, redone, saved, playing, stopped, rejected };
struct CreatorHostResult {
 CreatorHostStatus status;
 std::string message;
 std::uint64_t revision;
 CreatorPreparedPtr change{};
};
enum class CreatorHistoryDirection { undo, redo };
struct CreatorHistoryRequest {
 std::string id, host_epoch;
 CreatorScope scope;
 std::uint64_t expected_revision;
 CreatorHistoryDirection direction;
 bool operator==(const CreatorHistoryRequest&) const = default;
};
struct CreatorPlaySession {
 const std::string epoch;
 const CreatorScope scope;
 const std::uint64_t authored_revision;
 World world;
};
// Single-threaded owner; UI/SDK/proposals share these exact admission rules.
// Dependency callbacks are bounded observations; reentrant mutations reject.
// Chapter topology and navigation require a game-specific assessor, not guesses.
class CreatorHost {
 struct State;
 std::unique_ptr<State> state_;
 static std::shared_ptr<const CreatorSnapshot> describe(std::shared_ptr<const CreatorSession>, std::size_t reserved_checkpoint_bytes = 0);
 CreatorDependencyPreview assess(const std::shared_ptr<const CreatorSnapshot>&,
  const std::shared_ptr<const CreatorSnapshot>&, const Transaction&, const CreatorAssessor&) const;
public:
 explicit CreatorHost(CreatorSession&&, CreatorHostLimits = {});
 ~CreatorHost();
 CreatorHost(const CreatorHost&) = delete;
 CreatorHost& operator=(const CreatorHost&) = delete;
 static CreatorHost open(const std::filesystem::path&, SchemaRegistry, std::string project,
  std::string branch, CreatorHostLimits = {});
 std::shared_ptr<const CreatorSnapshot> snapshot() const noexcept;
 const std::string& epoch_id() const noexcept;
 CreatorHostResult preview(const CreatorScope&, const Transaction&, CreatorAssessor = {});
 CreatorHostResult apply(CreatorPreparedPtr);
 CreatorHostResult apply(const CreatorScope&, const Transaction&, CreatorAssessor = {});
 CreatorHostResult travel(const CreatorHistoryRequest&);
 CreatorHostResult save(const std::filesystem::path&);
 CreatorHostResult start_play(const CreatorScope&, std::uint64_t expected_revision);
 CreatorHostResult stop_play(const std::string& play_epoch);
 std::shared_ptr<CreatorPlaySession> play() const noexcept;
};
}
