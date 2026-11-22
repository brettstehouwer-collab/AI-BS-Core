#include <aibs/creator_host.hpp>
#include <algorithm>
#include <bit>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace aibs {
namespace detail { struct CreatorEpoch { const std::string id = new_uuid(); }; }
namespace {
std::size_t add(std::size_t a, std::size_t b) noexcept {
 return b > (std::numeric_limits<std::size_t>::max)() - a ? (std::numeric_limits<std::size_t>::max)() : a + b;
}
void ensure(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
bool exact_entity(const Entity& a, const Entity& b) {
 if (a.id != b.id || a.name != b.name || a.persistent_id != b.persistent_id || a.fields.size() != b.fields.size()) return false;
 auto it = b.fields.begin();
 for (const auto& [key, value] : a.fields) {
  if (key != it->first || std::bit_cast<std::uint64_t>(value) != std::bit_cast<std::uint64_t>(it->second)) return false;
  ++it;
 }
 return true;
}
bool exact_request(const Transaction& a, const Transaction& b) {
 if (a.id != b.id || a.expected_revision != b.expected_revision || a.description != b.description || a.edits.size() != b.edits.size()) return false;
 for (std::size_t i = 0; i < a.edits.size(); ++i) {
  const auto& lhs = a.edits[i]; const auto& rhs = b.edits[i];
  if (lhs.index() != rhs.index()) return false;
  if (const auto* create = std::get_if<Create>(&lhs)) { if (!exact_entity(create->entity, std::get<Create>(rhs).entity)) return false; }
  else if (const auto* erase = std::get_if<Erase>(&lhs)) { if (*erase != std::get<Erase>(rhs)) return false; }
  else {
   const auto& x = std::get<SetField>(lhs); const auto& y = std::get<SetField>(rhs);
   if (x.entity != y.entity || x.field != y.field || x.persistent_id != y.persistent_id || std::bit_cast<std::uint64_t>(x.value) != std::bit_cast<std::uint64_t>(y.value)) return false;
  }
 }
 return true;
}
void text_bound(const std::string& value, const CreatorHostLimits& limits) {
 ensure(value.size() <= limits.maximum_string_bytes, "Creator string limit exceeded");
}
void document_bound(const CreatorSession& session, const CreatorHostLimits& limits) {
 ensure(session.charged_storage_bytes() <= limits.maximum_session_bytes, "Creator logical session storage limit exceeded");
 ensure(session.world().size() <= limits.maximum_live_entities, "Creator live entity limit exceeded");
 text_bound(session.project_id(), limits); text_bound(session.branch_id(), limits);
 text_bound(session.world_id(), limits); text_bound(session.checkpoint_id(), limits);
 for (const auto& [id, field] : session.schemas().fields()) { text_bound(id, limits); text_bound(field.id, limits); }
 for (const auto& [id, entity] : session.world()) {
  text_bound(id, limits); text_bound(entity.id, limits); text_bound(entity.name, limits); text_bound(entity.persistent_id, limits);
  ensure(entity.fields.size() <= limits.maximum_fields_per_entity, "Creator entity field limit exceeded");
  for (const auto& [field, value] : entity.fields) { (void)value; text_bound(field, limits); }
 }
}
std::size_t request_bound(const Transaction& request, const CreatorHostLimits& limits) {
 ensure(!request.id.empty(), "Operation ID required"); text_bound(request.id, limits); text_bound(request.description, limits);
 ensure(!request.edits.empty() && request.edits.size() <= limits.maximum_edits, "Creator request edit limit exceeded");
 auto charge = add(sizeof(Transaction), add(request.id.size(), request.description.size()));
 for (const auto& edit : request.edits) {
  charge = add(charge, sizeof(Edit) + 64);
  std::visit([&](const auto& op) {
   using T = std::decay_t<decltype(op)>;
   if constexpr (std::is_same_v<T, Create>) {
    text_bound(op.entity.id, limits); text_bound(op.entity.name, limits); text_bound(op.entity.persistent_id, limits);
    ensure(is_uuid(op.entity.persistent_id), "Every creation needs an explicit persistent UUID");
    ensure(op.entity.fields.size() <= limits.maximum_fields_per_entity, "Creator entity field limit exceeded");
    charge = add(charge, add(op.entity.id.size(), add(op.entity.name.size(), op.entity.persistent_id.size())));
    for (const auto& [field, value] : op.entity.fields) { (void)value; text_bound(field, limits); charge = add(charge, add(128, field.size())); }
   } else {
    text_bound(op.entity, limits); text_bound(op.persistent_id, limits);
    ensure(is_uuid(op.persistent_id), "Every target needs an explicit persistent UUID");
    charge = add(charge, add(op.entity.size(), op.persistent_id.size()));
    if constexpr (std::is_same_v<T, SetField>) { text_bound(op.field, limits); charge = add(charge, op.field.size()); }
   }
  }, edit);
 }
 ensure(charge <= limits.maximum_request_bytes, "Creator logical request storage limit exceeded"); return charge;
}
void sequential_targets(const CreatorSession& session, const Transaction& request, const CreatorHostLimits& limits) {
 std::map<std::string, std::string> targets;
 for (const auto& [id, entity] : session.world()) targets.emplace(id, entity.persistent_id);
 for (const auto& edit : request.edits) {
  if (const auto* create = std::get_if<Create>(&edit)) {
   ensure(!create->entity.id.empty() && targets.emplace(create->entity.id, create->entity.persistent_id).second, "Empty or duplicate entity alias");
   ensure(targets.size() <= limits.maximum_live_entities, "Creator live entity limit exceeded");
  } else {
   const auto& alias = std::holds_alternative<Erase>(edit) ? std::get<Erase>(edit).entity : std::get<SetField>(edit).entity;
   const auto& uuid = std::holds_alternative<Erase>(edit) ? std::get<Erase>(edit).persistent_id : std::get<SetField>(edit).persistent_id;
   const auto it = targets.find(alias);
   ensure(it != targets.end() && it->second == uuid, "Missing target or stale entity UUID");
   if (std::holds_alternative<Erase>(edit)) targets.erase(it);
  }
 }
}
std::size_t dependency_bound(const CreatorDependencyPreview& value, const CreatorHostLimits& limits) {
 std::size_t charge = sizeof(value);
 for (const auto* values : {&value.changed_uuids, &value.dependency_keys, &value.notes}) {
  ensure(values->size() <= limits.maximum_live_entities, "Creator dependency count limit exceeded");
  for (const auto& text : *values) { text_bound(text, limits); charge = add(charge, add(sizeof(std::string), text.size())); }
 }
 ensure(charge <= limits.maximum_request_bytes, "Creator dependency storage limit exceeded"); return charge;
}
struct BusyGuard {
 bool& flag;
 explicit BusyGuard(bool& value) : flag(value) { flag = true; }
 ~BusyGuard() { flag = false; }
};
CreatorSession load_session(const std::filesystem::path& path, SchemaRegistry schemas, std::string project, std::string branch) {
 CreatorSession session(std::move(schemas), std::move(project), std::move(branch));
 const auto loaded = CheckpointStore::load(path, session);
 if (!loaded.ok) throw std::runtime_error(loaded.message);
 return session;
}
}
CreatorSnapshot::CreatorSnapshot(std::shared_ptr<const CreatorSession> owner, std::size_t reserved_checkpoint_bytes)
 : owner_(std::move(owner)), scope{owner_->project_id(), owner_->branch_id(), owner_->world_id()},
 revision(owner_->revision()), world(owner_->world()), history(owner_->memory().events()), schemas(owner_->schemas().fields()),
 checkpoint_id(owner_->checkpoint_id()), undo_depth(owner_->undo_depth()), redo_depth(owner_->redo_depth()),
 receipt_count(owner_->receipt_count()), charged_bytes(add(owner_->charged_storage_bytes(), reserved_checkpoint_bytes)) {}
CreatorPreparedChange::CreatorPreparedChange(std::shared_ptr<const detail::CreatorEpoch> owner, std::uint64_t generation,
 Transaction request, std::shared_ptr<const CreatorSnapshot> before, std::shared_ptr<const CreatorSnapshot> after,
 CreatorDependencyPreview dependencies, CreatorAssessor assessor)
 : owner_(std::move(owner)), generation_(generation), request_(std::move(request)), before_(std::move(before)), after_(std::move(after)),
 dependencies_(std::move(dependencies)), assessor_(std::move(assessor)) {}
struct CreatorHost::State {
 struct Slot { std::weak_ptr<const CreatorPreparedChange> token; std::size_t charge; };
 struct HistoryReceipt { CreatorHistoryRequest request; CreatorHostResult result; };
 CreatorHostLimits limits;
 std::shared_ptr<const detail::CreatorEpoch> epoch = std::make_shared<detail::CreatorEpoch>();
 std::shared_ptr<const CreatorSession> session;
 std::shared_ptr<const CreatorSnapshot> head;
 std::vector<Slot> prepared;
 std::map<std::string, HistoryReceipt> history_receipts;
 std::shared_ptr<CreatorPlaySession> play;
 std::uint64_t generation = 0;
 bool busy = false;
 CreatorHostResult result(CreatorHostStatus status, std::string message) const { return {status, std::move(message), head->revision}; }
 CreatorHostResult reject(std::string message) const { return result(CreatorHostStatus::rejected, std::move(message)); }
 void publish(std::shared_ptr<const CreatorSession> next, std::shared_ptr<const CreatorSnapshot> view) noexcept {
  session.swap(next); head.swap(view); ++generation; prepared.clear();
 }
 void check_generation() const { ensure(generation < (std::numeric_limits<std::uint64_t>::max)(), "Creator generation exhausted"); }
 std::size_t prepared_charge() {
  std::erase_if(prepared, [](const Slot& item) { return item.token.expired(); });
  std::size_t total = 0; for (const auto& slot : prepared) total = add(total, slot.charge); return total;
 }
};
std::shared_ptr<const CreatorSnapshot> CreatorHost::describe(std::shared_ptr<const CreatorSession> session, std::size_t reserved_checkpoint_bytes) {
 return std::shared_ptr<const CreatorSnapshot>(new CreatorSnapshot(std::move(session), reserved_checkpoint_bytes));
}
CreatorHost::CreatorHost(CreatorSession&& session, CreatorHostLimits limits) : state_(std::make_unique<State>()) {
 document_bound(session, limits); state_->limits = limits;
 state_->session = std::make_shared<const CreatorSession>(std::move(session)); state_->head = describe(state_->session);
}
CreatorHost::~CreatorHost() = default;
CreatorHost CreatorHost::open(const std::filesystem::path& path, SchemaRegistry schemas, std::string project, std::string branch, CreatorHostLimits limits) {
 return CreatorHost(load_session(path, std::move(schemas), std::move(project), std::move(branch)), limits);
}
std::shared_ptr<const CreatorSnapshot> CreatorHost::snapshot() const noexcept { return state_->head; }
const std::string& CreatorHost::epoch_id() const noexcept { return state_->epoch->id; }
CreatorDependencyPreview CreatorHost::assess(const std::shared_ptr<const CreatorSnapshot>& before,
 const std::shared_ptr<const CreatorSnapshot>& after, const Transaction& request, const CreatorAssessor& assessor) const {
 auto result = assessor ? assessor(*before, *after, request) : CreatorDependencyPreview{};
 dependency_bound(result, state_->limits);
 result.changed_uuids.clear();
 for (const auto& edit : request.edits) {
  result.changed_uuids.push_back(std::visit([](const auto& op) {
   if constexpr (std::is_same_v<std::decay_t<decltype(op)>, Create>) return op.entity.persistent_id;
   else return op.persistent_id;
  }, edit));
 }
 std::sort(result.changed_uuids.begin(), result.changed_uuids.end());
 result.changed_uuids.erase(std::unique(result.changed_uuids.begin(), result.changed_uuids.end()), result.changed_uuids.end());
 result.navigation_validated = false;
 result.notes.push_back("Navigation: unimplemented.");
 result.save = CheckpointStore::assess(*after->owner_);
 dependency_bound(result, state_->limits); return result;
}
CreatorHostResult CreatorHost::preview(const CreatorScope& scope, const Transaction& request, CreatorAssessor assessor) {
 auto& s = *state_; if (s.busy) return s.reject("Creator owner is busy in an observation callback"); BusyGuard guard(s.busy);
 try {
  ensure(scope == s.head->scope, "Creator project/branch/world scope mismatch");
  // Original request identity precedes live revision/target validation. Core's
  // default double equality remains unchanged; this boundary compares bits.
  if (const auto* original = s.session->accepted_transaction(request.id)) {
   ensure(exact_request(*original, request), "Operation ID already used for different request bits");
   return {CreatorHostStatus::duplicate, "Previously accepted request; no effect repeated", original->expected_revision + 1};
  }
  ensure(request.expected_revision == s.head->revision, "Creator authored revision conflict");
  const auto request_charge = request_bound(request, s.limits); s.check_generation();
  const auto held = s.prepared_charge();
  ensure(s.prepared.size() < s.limits.maximum_prepared, "Creator prepared token count limit exceeded");
  ensure(s.session->charged_storage_bytes() <= s.limits.maximum_session_bytes, "Creator session exceeds copy budget");
  sequential_targets(*s.session, request, s.limits);
  // The caller may own a mutable alias captured by an observation callback.
  // Freeze accepted request bits before invoking any caller-provided code.
  Transaction frozen = request;
  auto candidate = std::make_shared<CreatorSession>(*s.session);
  const auto applied = candidate->apply(frozen); ensure(applied.ok, applied.message.c_str());
  document_bound(*candidate, s.limits);
  const auto after = describe(candidate); auto dependencies = assess(s.head, after, frozen, assessor);
  ensure(dependencies.valid, "Creator dependency assessor rejected candidate");
  const auto snapshot_overhead = add(sizeof(CreatorPreparedChange) + sizeof(CreatorSnapshot),
   add(after->scope.project.size(), add(after->scope.branch.size(), after->scope.world_id.size())));
  const auto charge = add(snapshot_overhead, add(candidate->charged_storage_bytes(), add(request_charge, dependency_bound(dependencies, s.limits))));
  ensure(add(held, charge) <= s.limits.maximum_prepared_bytes, "Creator prepared logical storage limit exceeded");
  CreatorPreparedPtr token(new CreatorPreparedChange(s.epoch, s.generation, std::move(frozen), s.head, after, std::move(dependencies), std::move(assessor)));
  s.prepared.push_back({token, charge}); return {CreatorHostStatus::prepared, "Prepared in memory; not published or saved", s.head->revision, token};
 } catch (const std::exception& error) { return s.reject(error.what()); }
}
CreatorHostResult CreatorHost::apply(CreatorPreparedPtr token) {
 auto& s = *state_; if (s.busy) return s.reject("Creator owner is busy in an observation callback"); BusyGuard guard(s.busy);
 try {
  ensure(token && token->owner_ == s.epoch, "Missing or foreign creator preparation");
  ensure(token->before_->scope == s.head->scope, "Creator scope mismatch");
  if (const auto* original = s.session->accepted_transaction(token->request_.id)) {
   ensure(exact_request(*original, token->request_), "Operation ID already used for different request bits");
   return {CreatorHostStatus::duplicate, "Previously accepted request; no effect repeated", original->expected_revision + 1};
  }
  ensure(token->generation_ == s.generation && token->before_ == s.head, "Creator preparation is stale");
  ensure(std::any_of(s.prepared.begin(), s.prepared.end(), [&](const State::Slot& slot) { return slot.token.lock() == token; }), "Creator preparation no longer admitted");
  s.check_generation();
  const auto refreshed = assess(s.head, token->after_, token->request_, token->assessor_);
  ensure(refreshed.valid && refreshed == token->dependencies_, "Creator dependencies changed; prepare again");
  CreatorHostResult result{CreatorHostStatus::applied, "Applied in memory; not durably saved", token->after_->revision};
  s.publish(token->after_->owner_, token->after_); return result;
 } catch (const std::exception& error) { return s.reject(error.what()); }
}
CreatorHostResult CreatorHost::apply(const CreatorScope& scope, const Transaction& request, CreatorAssessor assessor) {
 auto prepared = preview(scope, request, std::move(assessor));
 return prepared.status == CreatorHostStatus::prepared ? apply(std::move(prepared.change)) : prepared;
}
CreatorHostResult CreatorHost::travel(const CreatorHistoryRequest& request) {
 auto& s = *state_; if (s.busy) return s.reject("Creator owner is busy in an observation callback"); BusyGuard guard(s.busy);
 try {
  ensure(request.host_epoch == s.epoch->id && request.scope == s.head->scope, "History request belongs to another host epoch or document");
  if (const auto found = s.history_receipts.find(request.id); found != s.history_receipts.end()) {
   ensure(found->second.request == request, "History request ID already used for different content");
   auto result = found->second.result; result.status = CreatorHostStatus::duplicate; return result;
  }
  ensure(!request.id.empty(), "History request ID required"); text_bound(request.id, s.limits);
  ensure(request.expected_revision == s.head->revision, "Creator authored revision conflict"); s.check_generation();
  ensure(s.history_receipts.size() < s.limits.maximum_history_receipts, "Creator history receipt limit exceeded");
  ensure(request.direction == CreatorHistoryDirection::undo || request.direction == CreatorHistoryDirection::redo, "Unknown history direction");
  auto candidate = std::make_shared<CreatorSession>(*s.session);
  const auto moved = request.direction == CreatorHistoryDirection::undo ? candidate->undo() : candidate->redo();
  ensure(moved.ok, moved.message.c_str()); document_bound(*candidate, s.limits);
  const auto view = describe(candidate);
  CreatorHostResult result{request.direction == CreatorHistoryDirection::undo ? CreatorHostStatus::undone : CreatorHostStatus::redone, "History applied in memory; receipt is valid only in this host epoch", view->revision};
  // Allocate the receipt before no-throw document publication.
  s.history_receipts.emplace(request.id, State::HistoryReceipt{request, result});
  s.publish(candidate, view); return result;
 } catch (const std::exception& error) { return s.reject(error.what()); }
}
CreatorHostResult CreatorHost::save(const std::filesystem::path& path) {
 auto& s = *state_; if (s.busy) return s.reject("Creator owner is busy in an observation callback"); BusyGuard guard(s.busy);
 try {
  s.check_generation(); document_bound(*s.session, s.limits);
  // Format 1 always publishes a 36-character checkpoint UUID. Reserve its
  // first-save charge before filesystem work and snapshot allocation.
  const std::size_t checkpoint_growth = s.session->checkpoint_id().empty() ? 36 : 0;
  ensure(s.limits.maximum_string_bytes >= 36, "Creator checkpoint UUID exceeds string limit");
  ensure(add(s.session->charged_storage_bytes(), checkpoint_growth) <= s.limits.maximum_session_bytes,
   "Creator first checkpoint exceeds logical session storage limit");
  auto candidate = std::make_shared<CreatorSession>(*s.session);
  const auto view = describe(candidate, checkpoint_growth); // Allocate before durable publication.
  auto saved = CheckpointStore::save(path, *candidate);
  if (!saved.ok) return s.reject(std::move(saved.message));
  s.publish(candidate, view); return s.result(CreatorHostStatus::saved, std::move(saved.message));
 } catch (const std::exception& error) { return s.reject(error.what()); }
}
CreatorHostResult CreatorHost::start_play(const CreatorScope& scope, std::uint64_t revision) {
 auto& s = *state_; if (s.busy) return s.reject("Creator owner is busy in an observation callback"); BusyGuard guard(s.busy);
 try {
  ensure(scope == s.head->scope && revision == s.head->revision, "Play document scope/revision conflict");
  ensure(!s.play, "A Play context is already active"); document_bound(*s.session, s.limits);
  auto play = std::make_shared<CreatorPlaySession>(CreatorPlaySession{new_uuid(), scope, revision, s.session->start_play()});
  auto result = s.result(CreatorHostStatus::playing, "Isolated in-process World; no authored apply-back or child process");
  s.play.swap(play); return result;
 } catch (const std::exception& error) { return s.reject(error.what()); }
}
CreatorHostResult CreatorHost::stop_play(const std::string& epoch) {
 auto& s = *state_; if (s.busy) return s.reject("Creator owner is busy in an observation callback"); BusyGuard guard(s.busy);
 if (!s.play || s.play->epoch != epoch) return s.reject("Play epoch mismatch");
 auto result = s.result(CreatorHostStatus::stopped, "Host released Play context; client-retained copies remain isolated");
 s.play.reset(); return result;
}
std::shared_ptr<CreatorPlaySession> CreatorHost::play() const noexcept { return state_->play; }
}
