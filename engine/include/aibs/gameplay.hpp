#pragma once
#include <aibs/engine.hpp>
#include <functional>
#include <limits>
#include <memory>
#include <optional>

namespace aibs {
enum class GameplayContext { authoring, temporary_play, player_world, published_historical_lore };
enum class GameplayPhase { accepted, world_or_document_applied, durably_committed };
enum class GameplayProvenance { gameplay_rule, player_input, authored_source };
struct GameplayScope {
 std::string project_id, world_id, branch_id, timeline_id;
 GameplayContext context = GameplayContext::player_world;
 bool operator==(const GameplayScope&) const = default;
};
using GameplayValue = std::variant<bool, std::int64_t, double, std::string>;
enum class GameplayValueKind { boolean, integer, number, text };
struct GameplayFieldRule {
 std::string id;
 GameplayValueKind kind;
 bool required = true;
 // Inclusive finite bounds for number fields. Integer fields retain int64 exactly.
 double minimum = -std::numeric_limits<double>::max(), maximum = std::numeric_limits<double>::max();
};
struct ComponentSchema { std::string type_id; std::uint32_t version = 1; std::vector<GameplayFieldRule> fields; };
struct ComponentRecord {
 std::string entity_id, type_id;
 std::uint32_t version = 1;
 std::map<std::string, GameplayValue> fields;
 bool operator==(const ComponentRecord&) const = default;
};
enum class ComponentAction { upsert, erase };
struct ComponentDelta {
 ComponentAction action = ComponentAction::upsert;
 ComponentRecord component;
 bool operator==(const ComponentDelta&) const = default;
};
struct RepairOutcome { std::string entity_id; double before = 0, after = 0; bool operator==(const RepairOutcome&) const = default; };
struct ConstructionOutcome { std::string entity_id; bool built = false; bool operator==(const ConstructionOutcome&) const = default; };
struct RouteOutcome { std::string route_id; bool traversed = false; bool operator==(const RouteOutcome&) const = default; };
struct HazardOutcome { std::string hazard_id; bool survived = false; bool operator==(const HazardOutcome&) const = default; };
// Mechanism/quest families use payload version 2. The four original alternatives
// retain their indices and payload version 1 so old durable receipts remain exact.
struct MechanismOutcome {
 std::string entity_id, attribute_id;
 bool before = false, after = false;
 bool operator==(const MechanismOutcome&) const = default;
};
enum class QuestState { unavailable, offered, active, declined, completed };
struct QuestOutcome {
 std::string quest_id;
 QuestState before = QuestState::unavailable, after = QuestState::unavailable;
 std::string before_step, after_step;
 bool operator==(const QuestOutcome&) const = default;
};
enum class CompanionAction { follow, wait, recall };
// Only explicit durable choices belong here. Movement trails, animation frames
// and the guide's current walking pose are reconstructed runtime state.
struct CompanionIntentValue {
 bool follow = true;
 double anchor_x = 0, anchor_y = 0, anchor_z = 0;
 bool operator==(const CompanionIntentValue&) const = default;
};
struct CompanionOutcome {
 std::string entity_id;
 CompanionAction action = CompanionAction::follow;
 CompanionIntentValue before, after;
 bool operator==(const CompanionOutcome&) const = default;
};
// Companion is appended at index 6 and requires payload version 3. Existing
// family indices, envelope versions and their encoded bytes are unchanged.
using SemanticPayload = std::variant<RepairOutcome, ConstructionOutcome, RouteOutcome, HazardOutcome, MechanismOutcome, QuestOutcome, CompanionOutcome>;
struct EventProvenance {
 GameplayProvenance kind = GameplayProvenance::gameplay_rule;
 std::string source_id;
 bool operator==(const EventProvenance&) const = default;
};
struct SemanticEvent {
 std::string event_id;
 std::uint32_t payload_version = 1;
 GameplayScope scope;
 std::uint64_t sequence = 0;
 std::string operation_id;
 std::vector<std::string> subject_ids;
 std::uint64_t source_revision = 0;
 std::optional<std::uint64_t> logical_tick;
 EventProvenance provenance;
 GameplayPhase result_phase = GameplayPhase::accepted;
 SemanticPayload payload;
 bool operator==(const SemanticEvent&) const = default;
};
const char* semantic_event_type(const SemanticEvent& event) noexcept;
struct GameplayChangeBatch {
 std::uint32_t schema_version = 1;
 GameplayScope scope;
 std::string operation_id;
 std::uint64_t expected_revision = 0, revision = 0;
 std::vector<ComponentDelta> deltas;
 std::vector<SemanticEvent> events;
 bool operator==(const GameplayChangeBatch&) const = default;
};
// Request identity agrees with the lossless durable codec, including +/-zero.
// Ordinary value equality remains available through operator==.
bool gameplay_batch_exact(const GameplayChangeBatch& left,const GameplayChangeBatch& right);
struct GameplayLimits {
 std::size_t pending_batches = 8, pending_bytes = 1024 * 1024;
 std::size_t receipts = 128, receipt_bytes = 4 * 1024 * 1024;
};
struct GameplayAdmissionState {
 std::uint64_t accepted_revision = 0, visible_revision = 0, durable_revision = 0;
 std::uint64_t accepted_sequence = 0, visible_sequence = 0, durable_sequence = 0;
 std::size_t pending_batches = 0, pending_bytes = 0, receipt_count = 0, receipt_bytes = 0;
};
enum class AdmissionStatus { accepted, retry, rejected, backpressure };
struct AdmissionResult {
 AdmissionStatus status = AdmissionStatus::rejected;
 std::string message;
 std::shared_ptr<const GameplayChangeBatch> batch;
};
struct GameplayAcknowledgement {
 GameplayScope scope;
 std::string operation_id;
 std::uint64_t revision = 0;
 GameplayPhase phase = GameplayPhase::accepted;
};
using GameplayTargetValidator = std::function<bool(const std::string&)>;
// Single simulation-owner admission ledger, not a worker or storage adapter.
// Reserve before a prepared, nonthrowing world publication. Only explicit
// owner acknowledgements advance visible/durable heads. Immutable batch handles
// may be passed to a future worker; the ledger itself is not thread-safe.
class GameplayAdmission {
public:
 GameplayAdmission(GameplayScope scope, std::vector<ComponentSchema> schemas, GameplayLimits limits = {},
                   std::uint64_t base_revision = 0, std::uint64_t base_sequence = 0);
 ~GameplayAdmission();
 GameplayAdmission(const GameplayAdmission&) = delete;
 GameplayAdmission& operator=(const GameplayAdmission&) = delete;
 AdmissionResult reserve(const GameplayChangeBatch& batch, const GameplayTargetValidator& targets);
 Result acknowledge(const GameplayAcknowledgement& acknowledgement);
 GameplayAdmissionState state() const noexcept;
 std::shared_ptr<const GameplayChangeBatch> next_visible() const;
 std::shared_ptr<const GameplayChangeBatch> next_durable() const;
private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
};
}
