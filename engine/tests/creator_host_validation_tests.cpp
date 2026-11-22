#include <aibs/creator_host.hpp>
#include <bit>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <type_traits>

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
 require(result.add({"half_x", .1, 10}), "register extent");
 return result;
}
CreatorSession authored() {
 CreatorSession session(schemas(), "generic-tools", "main");
 require(session.apply({"seed", 0, {Create{{"cube", "Cube", {{"x", 0}, {"half_x", 1}}, new_uuid()}}}, "Seed cube"}).ok,
         "seed authored document");
 return session;
}
Transaction set(const CreatorHost& host, std::string id, double value = 3) {
 const auto snapshot = host.snapshot();
 return {std::move(id), snapshot->revision,
         {SetField{"cube", "x", value, snapshot->world.at("cube").persistent_id}}, "Move cube"};
}
CreatorHistoryRequest history(const CreatorHost& host, std::string id, CreatorHistoryDirection direction) {
 const auto snapshot = host.snapshot();
 return {std::move(id), host.epoch_id(), snapshot->scope, snapshot->revision, direction};
}
void rejected_unchanged(CreatorHost& host, const CreatorScope& scope, const Transaction& transaction, const char* message) {
 const auto before = host.snapshot();
 require(host.apply(scope, transaction).status == CreatorHostStatus::rejected, message);
 require(host.snapshot() == before, "rejected command preserves snapshot identity");
}

void grouped_and_strict_identity() {
 CreatorHost host(authored());
 const auto initial = host.snapshot();
 const auto added_uuid = new_uuid();
 const Transaction create_set{"create-set", initial->revision,
  {Create{{"added", "Added", {{"x", 1}}, added_uuid}}, SetField{"added", "x", 7, added_uuid}}, "Create then set"};
 auto preview = host.preview(initial->scope, create_set);
 require(preview.status == CreatorHostStatus::prepared && preview.change, "grouped Create then Set prepares");
 require(host.snapshot() == initial && !initial->world.contains("added"), "group preview never publishes");
 require(preview.change->snapshot()->world.at("added").fields.at("x") == 7, "sequential created target available");
 require(host.apply(preview.change).status == CreatorHostStatus::applied, "grouped Create then Set applies");
 require(host.snapshot()->revision == initial->revision + 1 && host.snapshot()->undo_depth == initial->undo_depth + 1,
         "one group creates one revision and undo item");
 const auto old_uuid = host.snapshot()->world.at("cube").persistent_id;
 const auto replacement_uuid = new_uuid();
 const Transaction replace{"replace", host.snapshot()->revision,
  {Erase{"cube", old_uuid}, Create{{"cube", "Replacement", {{"x", 0}}, replacement_uuid}},
   SetField{"cube", "x", 9, replacement_uuid}}, "Erase, replace, then set"};
 require(host.apply(host.snapshot()->scope, replace).status == CreatorHostStatus::applied, "sequential alias replacement applies");
 require(host.snapshot()->world.at("cube").persistent_id == replacement_uuid && host.snapshot()->world.at("cube").fields.at("x") == 9,
         "replacement resolves new UUID");
 rejected_unchanged(host, host.snapshot()->scope,
  {"stale-uuid", host.snapshot()->revision, {SetField{"cube", "x", 1, old_uuid}}, "Old UUID"}, "stale UUID rejected");
 rejected_unchanged(host, host.snapshot()->scope,
  {"missing-uuid", host.snapshot()->revision, {SetField{"cube", "x", 1, {}}}, "No UUID"}, "missing target UUID rejected");
 rejected_unchanged(host, host.snapshot()->scope,
  {"erase-no-uuid", host.snapshot()->revision, {Erase{"cube", {}}}, "No UUID"}, "erase requires target UUID");
 rejected_unchanged(host, host.snapshot()->scope,
  {"create-no-uuid", host.snapshot()->revision, {Create{{"other", "Other", {{"x", 0}}, {}}}}, "No UUID"}, "create requires explicit UUID");
 rejected_unchanged(host, host.snapshot()->scope,
  {"recycle", host.snapshot()->revision, {Create{{"retired", "Retired", {{"x", 0}}, old_uuid}}}, "Recycle"}, "retired UUID cannot be recycled");
 const auto current = host.snapshot();
 rejected_unchanged(host, current->scope,
  {"partial", current->revision,
   {SetField{"cube", "x", 2, replacement_uuid}, SetField{"cube", "half_x", -1, replacement_uuid}}, "Invalid group"},
  "invalid final edit rolls back whole group");
 auto foreign_scope = current->scope;
 foreign_scope.project = "different-project";
 rejected_unchanged(host, foreign_scope, set(host, "foreign-project"), "project scope rejected");
 foreign_scope = current->scope; foreign_scope.branch = "different-branch";
 rejected_unchanged(host, foreign_scope, set(host, "foreign-branch"), "branch scope rejected");
 foreign_scope = current->scope; foreign_scope.world_id = new_uuid();
 rejected_unchanged(host, foreign_scope, set(host, "foreign-world"), "world scope rejected");
 auto stale = set(host, "stale-revision"); stale.expected_revision = 0;
 rejected_unchanged(host, current->scope, stale, "stale revision rejected");
}

void immutable_tokens_and_dependency_reassessment() {
 static_assert(!std::is_default_constructible_v<CreatorPreparedChange>);
 static_assert(!std::is_copy_constructible_v<CreatorPreparedChange>);
 CreatorHost host(authored());
 const auto original = host.snapshot();
 require(host.apply(CreatorPreparedPtr{}).status == CreatorHostStatus::rejected, "null token rejected");
 auto prepared = host.preview(original->scope, set(host, "prepared"));
 require(prepared.status == CreatorHostStatus::prepared, "prepare token");
 CreatorHost foreign(authored());
 const auto foreign_before = foreign.snapshot();
 require(foreign.apply(prepared.change).status == CreatorHostStatus::rejected && foreign.snapshot() == foreign_before,
         "foreign owner cannot publish token");
 require(host.apply(original->scope, set(host, "intervening", 4)).status == CreatorHostStatus::applied,
         "intervening mutation");
 require(host.apply(prepared.change).status == CreatorHostStatus::rejected, "stale token rejected");
 require(original->world.at("cube").fields.at("x") == 0 && original->revision == 1,
         "retained snapshot immutable after publication");
 require(prepared.change->snapshot()->world.at("cube").fields.at("x") == 3,
         "retained rejected candidate remains immutable");
 unsigned dependency_version = 1;
 unsigned calls = 0;
 auto assessor = [&](const CreatorSnapshot& before, const CreatorSnapshot& after, const Transaction&) {
  ++calls;
  require(before.world.at("cube").fields.at("x") == 4 && after.world.at("cube").fields.at("x") == 8,
          "assessor receives true before and after");
  CreatorDependencyPreview result;
  result.render_rebuild = true; result.collision_rebuild = true;
  result.dependency_keys = {"power-graph:" + std::to_string(dependency_version)};
  result.changed_uuids = {after.world.at("cube").persistent_id};
  return result;
 };
 prepared = host.preview(host.snapshot()->scope, set(host, "dependency", 8), assessor);
 require(prepared.status == CreatorHostStatus::prepared && calls == 1, "dependencies assessed before preview");
 require(prepared.change->dependencies().save.compatible && prepared.change->dependencies().save.encoded_bytes > 0,
         "host supplies exact checkpoint assessment");
 require(!prepared.change->dependencies().navigation_validated, "generic host claims no navigation proof");
 dependency_version = 2;
 const auto before_apply = host.snapshot();
 require(host.apply(prepared.change).status == CreatorHostStatus::rejected && calls == 2,
         "external dependency drift rejected after reassessment");
 require(host.snapshot() == before_apply, "dependency rejection never publishes");
 auto invalid = host.preview(host.snapshot()->scope, set(host, "invalid-dependency"),
  [](const auto&, const auto&, const auto&) { CreatorDependencyPreview result; result.valid = false; return result; });
 require(invalid.status == CreatorHostStatus::rejected && host.snapshot() == before_apply, "invalid dependency preview rejected");
 auto thrown = host.preview(host.snapshot()->scope, set(host, "throwing"),
  [](const auto&, const auto&, const auto&) -> CreatorDependencyPreview { throw std::runtime_error("Assessor failure"); });
 require(thrown.status == CreatorHostStatus::rejected && host.snapshot() == before_apply, "throwing assessor rejected unchanged");
 bool rejected_reentrant = false;
 prepared = host.preview(host.snapshot()->scope, set(host, "outer"), [&](const auto&, const auto&, const auto&) {
  const auto nested = host.apply(host.snapshot()->scope, set(host, "nested", 10));
  rejected_reentrant = nested.status == CreatorHostStatus::rejected;
  return CreatorDependencyPreview{};
 });
 require(rejected_reentrant && prepared.status == CreatorHostStatus::prepared && host.snapshot() == before_apply,
         "reentrant mutation rejected while outer observation prepares");
 require(host.apply(prepared.change).status == CreatorHostStatus::applied && rejected_reentrant,
         "reentrancy guard also holds during apply reassessment");
 require(host.snapshot()->world.at("cube").fields.at("x") == 3, "only outer candidate published");
 bool throw_during_apply = false;
 prepared = host.preview(host.snapshot()->scope, set(host, "throw-at-publication", 6),
  [&](const auto&, const auto&, const auto&) {
   if (throw_during_apply) throw std::runtime_error("Late assessor failure");
   return CreatorDependencyPreview{};
  });
 require(prepared.status == CreatorHostStatus::prepared, "prepare before late assessor exception");
 throw_during_apply = true;
 const auto before_throw = host.snapshot();
 require(host.apply(prepared.change).status == CreatorHostStatus::rejected && host.snapshot() == before_throw,
         "apply-time assessor throw preserves live snapshot");
}

void original_retry_and_restart(const std::filesystem::path& directory) {
 CreatorHost host(authored());
 const auto scope = host.snapshot()->scope;
 const auto original = set(host, "negative-zero", -0.0);
 require(host.apply(scope, original).status == CreatorHostStatus::applied, "signed-zero request applied");
 auto positive = original; std::get<SetField>(positive.edits.front()).value = 0.0;
 rejected_unchanged(host, scope, positive, "bit-different signed-zero reused ID rejected");
 const auto accepted_snapshot = host.snapshot();
 require(host.apply(scope, original).status == CreatorHostStatus::duplicate && host.snapshot() == accepted_snapshot,
         "exact retry duplicate without republishing");
 auto wrong_scope = scope; wrong_scope.branch = "other";
 rejected_unchanged(host, wrong_scope, original, "accepted ID never bypasses document scope");
 const auto erase = Transaction{"delete-target", host.snapshot()->revision,
  {Erase{"cube", host.snapshot()->world.at("cube").persistent_id}}, "Delete original target"};
 require(host.apply(scope, erase).status == CreatorHostStatus::applied, "delete original target");
 const auto deleted = host.snapshot();
 require(host.apply(scope, original).status == CreatorHostStatus::duplicate && host.snapshot() == deleted,
         "exact retry resolves before missing target or stale head");
 const auto undo = history(host, "undo-delete", CreatorHistoryDirection::undo);
 require(host.travel(undo).status == CreatorHostStatus::undone, "undo deletion");
 const auto undo_value = history(host, "undo-value", CreatorHistoryDirection::undo);
 require(host.travel(undo_value).status == CreatorHostStatus::undone, "undo original numeric operation");
 require(!std::signbit(host.snapshot()->world.at("cube").fields.at("x")), "undo restored positive zero");
 const auto undone = host.snapshot();
 require(host.apply(scope, original).status == CreatorHostStatus::duplicate && host.snapshot() == undone,
         "retry of undone operation never reapplies it");
 const auto slot = directory / "retry.aibs";
 require(host.save(slot).status == CreatorHostStatus::saved, "save retry history");
 auto resumed = CreatorHost::open(slot, schemas(), "generic-tools", "main");
 const auto reopened = resumed.snapshot();
 require(resumed.epoch_id() != host.epoch_id() && reopened->scope == scope, "restart retains document scope and changes host epoch");
 require(resumed.apply(scope, original).status == CreatorHostStatus::duplicate && resumed.snapshot() == reopened,
         "persisted original request resolves after reopen");
 rejected_unchanged(resumed, scope, positive, "signed-zero conflict survives restart");
 CreatorSession legacy(schemas(), "generic-tools", "main");
 const Transaction legacy_create{"legacy-auto-id", 0, {Create{{"legacy", "Legacy", {{"x", -0.0}}, {}}}}, "Legacy generated UUID"};
 require(legacy.apply(legacy_create).ok, "legacy original generated UUID request");
 CreatorHost legacy_host(std::move(legacy));
 const auto legacy_before = legacy_host.snapshot();
 require(legacy_host.apply(legacy_before->scope, legacy_create).status == CreatorHostStatus::duplicate && legacy_host.snapshot() == legacy_before,
         "accepted legacy retry resolves before new strict UUID admission");
 auto legacy_positive = legacy_create;
 std::get<Create>(legacy_positive.edits.front()).entity.fields.at("x") = 0.0;
 rejected_unchanged(legacy_host, legacy_before->scope, legacy_positive, "Create receipt also compares signed-zero bits");
}

void save_and_epoch_bound_history(const std::filesystem::path& directory) {
 CreatorHost host(authored());
 auto prepared = host.preview(host.snapshot()->scope, set(host, "after-failed-save"));
 require(prepared.status == CreatorHostStatus::prepared, "prepare before failing save");
 const auto before_failure = host.snapshot();
 require(host.save(directory / "nonexistent" / "failed.aibs").status == CreatorHostStatus::rejected,
         "unavailable directory save rejects");
 require(host.snapshot() == before_failure && host.apply(prepared.change).status == CreatorHostStatus::applied,
         "failed save preserves valid preview generation");
 prepared = host.preview(host.snapshot()->scope, set(host, "invalidated-by-save", 5));
 const auto before_save = host.snapshot();
 const auto slot = directory / "history.aibs";
 require(host.save(slot).status == CreatorHostStatus::saved, "successful save");
 require(host.snapshot()->revision == before_save->revision && host.snapshot()->checkpoint_id != before_save->checkpoint_id,
         "save changes checkpoint ID without authored revision");
 auto charge_reopened = CreatorHost::open(slot, schemas(), "generic-tools", "main");
 require(host.snapshot()->charged_bytes == charge_reopened.snapshot()->charged_bytes,
         "published save snapshot charge includes newly allocated checkpoint ID");
 require(host.apply(prepared.change).status == CreatorHostStatus::rejected, "successful save invalidates prior token");
 const auto undo = history(host, "history-operation", CreatorHistoryDirection::undo);
 require(host.travel(undo).status == CreatorHostStatus::undone, "history undo applies");
 const auto after_undo = host.snapshot();
 require(host.travel(undo).status == CreatorHostStatus::duplicate && host.snapshot() == after_undo,
         "same epoch history retry deduplicates before revision check");
 auto conflicting = undo; conflicting.direction = CreatorHistoryDirection::redo;
 require(host.travel(conflicting).status == CreatorHostStatus::rejected && host.snapshot() == after_undo,
         "same history ID with changed content rejects");
 conflicting = undo; conflicting.scope.branch = "other";
 require(host.travel(conflicting).status == CreatorHostStatus::rejected, "history scope conflict rejects");
 const auto redo = history(host, "redo-operation", CreatorHistoryDirection::redo);
 require(host.travel(redo).status == CreatorHostStatus::redone, "fresh redo applies");
 require(host.save(slot).status == CreatorHostStatus::saved, "save retained authored history");
 auto reopened = CreatorHost::open(slot, schemas(), "generic-tools", "main");
 const auto reopened_before = reopened.snapshot();
 require(reopened.travel(undo).status == CreatorHostStatus::rejected && reopened.snapshot() == reopened_before,
         "old host epoch history request rejects after restart");
 auto new_undo = history(reopened, "history-operation", CreatorHistoryDirection::undo);
 require(reopened.travel(new_undo).status == CreatorHostStatus::undone, "new epoch may reuse local history ID explicitly");
 CreatorHostLimits receipt_limit; receipt_limit.maximum_history_receipts = 1;
 CreatorHost one_receipt(authored(), receipt_limit);
 const auto only_undo = history(one_receipt, "only-history-receipt", CreatorHistoryDirection::undo);
 require(one_receipt.travel(only_undo).status == CreatorHostStatus::undone, "one local history receipt admitted");
 const auto limited_before = one_receipt.snapshot();
 require(one_receipt.travel(only_undo).status == CreatorHostStatus::duplicate, "bounded history retains duplicate resolution");
 require(one_receipt.travel(history(one_receipt, "another-history-receipt", CreatorHistoryDirection::redo)).status == CreatorHostStatus::rejected &&
         one_receipt.snapshot() == limited_before, "history receipt bound rejects new mutation unchanged");
}

void play_isolation_and_retained_clients(const std::filesystem::path& directory) {
 static_assert(std::is_const_v<decltype(CreatorPlaySession::epoch)>);
 static_assert(std::is_const_v<decltype(CreatorPlaySession::scope)>);
 static_assert(std::is_const_v<decltype(CreatorPlaySession::authored_revision)>);
 CreatorHost host(authored());
 const auto authored_snapshot = host.snapshot();
 require(!host.play(), "no play before start");
 auto wrong_scope = authored_snapshot->scope; wrong_scope.world_id = new_uuid();
 require(host.start_play(wrong_scope, authored_snapshot->revision).status == CreatorHostStatus::rejected, "foreign Play scope rejected");
 require(host.start_play(authored_snapshot->scope, 0).status == CreatorHostStatus::rejected, "stale Play revision rejected");
 require(host.start_play(authored_snapshot->scope, authored_snapshot->revision).status == CreatorHostStatus::playing,
         "start isolated Play");
 auto client = host.play();
 require(client && client->scope == authored_snapshot->scope && client->authored_revision == authored_snapshot->revision,
         "Play binds authored scope and revision");
 const auto old_epoch = client->epoch;
 client->world.at("cube").fields.at("x") = 44;
 require(host.snapshot() == authored_snapshot && authored_snapshot->world.at("cube").fields.at("x") == 0,
         "Play mutation never edits authored snapshot");
 require(host.stop_play("foreign-epoch").status == CreatorHostStatus::rejected && host.play() == client,
         "foreign Stop cannot stop current Play");
 const auto slot = directory / "play.aibs";
 require(host.save(slot).status == CreatorHostStatus::saved, "save while Play changes exist");
 require(host.stop_play(old_epoch).status == CreatorHostStatus::stopped && !host.play(), "Stop releases host Play ownership");
 require(host.stop_play(old_epoch).status == CreatorHostStatus::rejected, "old Stop epoch cannot address released context");
 require(client->world.at("cube").fields.at("x") == 44, "client retained Play survives Stop independently");
 require(host.start_play(host.snapshot()->scope, host.snapshot()->revision).status == CreatorHostStatus::playing,
         "start next Play");
 require(host.play()->epoch != old_epoch && host.play()->world.at("cube").fields.at("x") == 0,
         "next Play fresh epoch and authored baseline");
 client->world.at("cube").fields.at("x") = 88;
 require(host.play()->world.at("cube").fields.at("x") == 0 && host.snapshot()->world.at("cube").fields.at("x") == 0,
         "old retained Play cannot affect new Play or authoring");
 auto reopened = CreatorHost::open(slot, schemas(), "generic-tools", "main");
 require(!reopened.play() && reopened.snapshot()->world.at("cube").fields.at("x") == 0,
         "restart reopens authored state without retained Play edits");
}

void limits_and_invalid_numbers() {
 CreatorHostLimits limits;
 limits.maximum_string_bytes = 64;
 CreatorHost host(authored(), limits);
 auto transaction = set(host, "long-description"); transaction.description.assign(65, 'd');
 rejected_unchanged(host, host.snapshot()->scope, transaction, "description string limit");
 transaction = set(host, std::string(65, 'i'));
 rejected_unchanged(host, host.snapshot()->scope, transaction, "request ID string limit");
 transaction = set(host, "long-field"); std::get<SetField>(transaction.edits.front()).field.assign(65, 'f');
 rejected_unchanged(host, host.snapshot()->scope, transaction, "field string limit");
 transaction = {"long-name", host.snapshot()->revision,
  {Create{{"new", std::string(65, 'n'), {{"x", 0}}, new_uuid()}}}, "Long name"};
 rejected_unchanged(host, host.snapshot()->scope, transaction, "entity name string limit");
 for (const auto invalid : {std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::infinity(),
                            -std::numeric_limits<double>::infinity(), 101.0}) {
  rejected_unchanged(host, host.snapshot()->scope, set(host, "invalid-number", invalid), "non-finite or out-of-schema number rejected");
 }
 limits = {}; limits.maximum_edits = 1;
 CreatorHost one_edit(authored(), limits);
 transaction = set(one_edit, "two-edits"); transaction.edits.push_back(transaction.edits.front());
 rejected_unchanged(one_edit, one_edit.snapshot()->scope, transaction, "group edit-count limit");
 limits = {}; limits.maximum_request_bytes = 64;
 CreatorHost small_request(authored(), limits);
 rejected_unchanged(small_request, small_request.snapshot()->scope, set(small_request, "oversized-request"), "request logical byte limit");
 limits = {}; limits.maximum_live_entities = 1;
 CreatorHost one_entity(authored(), limits);
 transaction = {"second-entity", one_entity.snapshot()->revision, {Create{{"second", "Second", {{"x", 1}}, new_uuid()}}}, "Second"};
 rejected_unchanged(one_entity, one_entity.snapshot()->scope, transaction, "live entity count limit");
 limits = {}; limits.maximum_fields_per_entity = 1;
 CreatorSession one_field_source(schemas(), "generic-tools", "main");
 require(one_field_source.apply({"seed", 0, {Create{{"cube", "Cube", {{"x", 0}}, new_uuid()}}}, "One field"}).ok,
         "seed one-field document");
 CreatorHost one_field(std::move(one_field_source), limits);
 transaction = set(one_field, "add-second-field", 1);
 std::get<SetField>(transaction.edits.front()).field = "half_x";
 rejected_unchanged(one_field, one_field.snapshot()->scope, transaction, "Set cannot exceed resulting entity field limit");
 limits = {}; limits.maximum_prepared = 1;
 CreatorHost one_prepared(authored(), limits);
 auto retained = one_prepared.preview(one_prepared.snapshot()->scope, set(one_prepared, "prepared-one"));
 require(retained.status == CreatorHostStatus::prepared, "first token fits prepared count");
 const auto original = one_prepared.snapshot();
 require(one_prepared.preview(original->scope, set(one_prepared, "prepared-two")).status == CreatorHostStatus::rejected &&
         one_prepared.snapshot() == original, "prepared count limit rejects without mutation");
 require(one_prepared.apply(retained.change).status == CreatorHostStatus::applied, "bounded prepared token remains usable");
 require(one_prepared.preview(one_prepared.snapshot()->scope, set(one_prepared, "new-generation")).status == CreatorHostStatus::prepared,
         "successful mutation releases old generation admission budget");
 require(one_prepared.preview(one_prepared.snapshot()->scope, set(one_prepared, "expired-client-token")).status == CreatorHostStatus::prepared,
         "discarded client token releases admission on pruning");
 limits = {}; limits.maximum_prepared_bytes = 1;
 CreatorHost tiny_prepared(authored(), limits);
 require(tiny_prepared.preview(tiny_prepared.snapshot()->scope, set(tiny_prepared, "too-large-preview")).status == CreatorHostStatus::rejected,
         "aggregate prepared byte limit");
 auto source = authored();
 limits = {}; limits.maximum_session_bytes = source.charged_storage_bytes();
 CreatorHost full_session(std::move(source), limits);
 rejected_unchanged(full_session, full_session.snapshot()->scope, set(full_session, "exceeds-session"),
                    "full session charge includes growing history and receipts");
 source = authored(); limits.maximum_session_bytes = source.charged_storage_bytes() - 1;
 bool rejected_initial = false;
 try { CreatorHost oversized(std::move(source), limits); }
 catch (const std::exception&) { rejected_initial = true; }
 require(rejected_initial, "oversized initial session rejected before ownership copies");
}

void save_growth_obeys_session_budget(const std::filesystem::path& directory) {
 auto source = authored();
 CreatorHostLimits limits; limits.maximum_session_bytes = source.charged_storage_bytes();
 CreatorHost host(std::move(source), limits);
 const auto before = host.snapshot();
 const auto slot = directory / "save-budget.aibs";
 require(host.save(slot).status == CreatorHostStatus::rejected && host.snapshot() == before && !std::filesystem::exists(slot),
         "first save checkpoint-ID growth rejected before durable publication when session budget full");
}

void callback_request_freeze_and_small_string_limit() {
 CreatorHost host(authored());
 auto caller_request = set(host, "freeze-callback-request", 1);
 const auto original_request = caller_request;
 bool observer_always_saw_original = true;
 const auto prepared = host.preview(host.snapshot()->scope, caller_request,
  [&](const auto&, const auto&, const Transaction& observed) {
   observer_always_saw_original = observer_always_saw_original && std::get<SetField>(observed.edits.front()).value == 1;
   // The caller still owns its request and may retain it in a callback capture.
   // Its mutation must not alter the validated request observed here or the
   // request subsequently retained in the private prepared token.
   std::get<SetField>(caller_request.edits.front()).value = 2;
   observer_always_saw_original = observer_always_saw_original && std::get<SetField>(observed.edits.front()).value == 1;
   return CreatorDependencyPreview{};
  });
 require(prepared.status == CreatorHostStatus::prepared && prepared.change, "callback-mutated caller request still prepares original candidate");
 require(prepared.change->snapshot()->world.at("cube").fields.at("x") == 1, "candidate uses admitted original numeric value");
 require(host.apply(prepared.change).status == CreatorHostStatus::applied, "frozen original candidate applies");
 require(host.snapshot()->world.at("cube").fields.at("x") == 1, "publication retains original candidate value");
 const auto published = host.snapshot();
 require(host.apply(published->scope, original_request).status == CreatorHostStatus::duplicate && host.snapshot() == published,
         "original frozen request resolves as exact duplicate");
 require(host.apply(published->scope, caller_request).status == CreatorHostStatus::rejected && host.snapshot() == published,
         "callback-mutated caller request conflicts with original receipt");
 CreatorHostLimits limits; limits.maximum_string_bytes = 64;
 CreatorHost small_strings(authored(), limits);
 const auto small_preview = small_strings.preview(small_strings.snapshot()->scope, set(small_strings, "valid-short-request", 1));
 const bool valid_short_request = small_preview.status == CreatorHostStatus::prepared && small_preview.change;
 if (!observer_always_saw_original || !valid_short_request) {
  std::cerr << "Regression observations: callback request frozen=" << observer_always_saw_original
            << ", valid 64-byte string limit preview=" << valid_short_request
            << "; preview response=" << small_preview.message << '\n';
 }
 require(observer_always_saw_original, "callback observes frozen request independent of caller lvalue mutation during preview and apply");
 require(valid_short_request, "built-in diagnostic strings permit valid request under 64-byte string limit");
}
}

int main() {
 const auto directory = std::filesystem::temp_directory_path() / ("aibs-host-contract-" + aibs::new_uuid());
 std::filesystem::create_directories(directory);
 try {
  grouped_and_strict_identity();
  immutable_tokens_and_dependency_reassessment();
  original_retry_and_restart(directory);
  save_and_epoch_bound_history(directory);
  play_isolation_and_retained_clients(directory);
  limits_and_invalid_numbers();
  save_growth_obeys_session_budget(directory);
  callback_request_freeze_and_small_string_limit();
  std::filesystem::remove_all(directory);
  std::cout << "PASS: " << checks << " creator host contract checks\n";
  return 0;
 } catch (const std::exception& error) {
  std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n';
  std::filesystem::remove_all(directory);
  return 1;
 }
}
