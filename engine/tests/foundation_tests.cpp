#include <aibs/engine.hpp>
#include <aibs/persistence.hpp>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <type_traits>
#include <utility>

using namespace aibs;
static_assert(std::is_same_v<decltype(std::declval<const CreatorSession&>().known_entity_ids()),const std::set<std::string>&>);
static_assert(noexcept(std::declval<const CreatorSession&>().known_entity_ids()));
void check(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
Entity node(std::string id) { return {std::move(id), "Core Node 01", {{"capacity", 0.0}}}; }
int main() {
 try {
  SchemaRegistry schemas;
  check(schemas.add({"capacity", 0, 100}), "register field");
  check(!schemas.add({"capacity", 0, 100}), "duplicate schema rejected");
  CreatorSession creator(schemas, "first-boot", "main");
  const auto& known_ids=creator.known_entity_ids();
  check(known_ids.empty(),"new owner has no used entity identities");
  auto created = creator.apply({"create-1", 0, {Create{node("core-01")}}});
  check(created.ok && creator.revision() == 1, "create transaction");
  const auto core_uuid=creator.world().at("core-01").persistent_id;
  check(known_ids.contains(core_uuid),"read-only known UUID view includes alive entities");
  check(creator.apply({"create-1", 0, {Create{node("core-01")}}}).ok, "retry idempotent");
  check(creator.revision() == 1, "retry no revision increment");
  check(!creator.apply({"create-1", 1, {Erase{"core-01"}}}).ok, "id reuse rejected");
  check(!creator.apply({"stale", 0, {Erase{"core-01"}}}).ok, "stale revision rejected");
  check(!creator.apply({"atomic", 1, {SetField{"core-01", "capacity", 50}, SetField{"missing", "capacity", 5}}}).ok, "invalid group rejected");
  check(creator.world().at("core-01").fields.at("capacity") == 0, "rollback all edits");
  check(!creator.apply({"range", 1, {SetField{"core-01", "capacity", 101}}}).ok, "field limits");
  check(!creator.apply({"unknown", 1, {SetField{"core-01", "typo", 1}}}).ok, "unknown fields");
  check(creator.apply({"repair", 1, {SetField{"core-01", "capacity", 75}}}).ok, "repair");
  check(creator.memory().events().size() == 2, "only accepted edits become memory");
  check(creator.memory().events().back().project == "first-boot", "scoped memory");
  check(creator.undo().ok && creator.world().at("core-01").fields.at("capacity") == 0, "undo");
  check(creator.redo().ok && creator.world().at("core-01").fields.at("capacity") == 75, "redo");
  auto play = creator.start_play();
  play.at("core-01").fields["capacity"] = 10;
  check(creator.world().at("core-01").fields.at("capacity") == 75, "play isolation");
  check(creator.apply({"delete", creator.revision(), {Erase{"core-01"}}}).ok, "delete");
  check(known_ids.contains(core_uuid),"deleting an entity preserves its known UUID");
  check(creator.undo().ok && creator.world().contains("core-01"), "undo deletion");
  check(creator.redo().ok && !creator.world().contains("core-01") && known_ids.contains(core_uuid),"redo deletion cannot forget its UUID");
  check(creator.undo().ok && creator.world().at("core-01").persistent_id==core_uuid && known_ids.contains(core_uuid),"undo restores the same known identity");
  check(creator.apply({"branch", creator.revision(), {SetField{"core-01", "capacity", 30}}}).ok, "new history branch");
  check(!creator.redo().ok, "new edit invalidates redo");
  auto temporary=node("temporary"); temporary.persistent_id=new_uuid();
  const auto retired_uuid=temporary.persistent_id;
  check(creator.apply({"temporary-create",creator.revision(),{Create{temporary}}}).ok && known_ids.contains(retired_uuid),"new identity enters the lifetime set");
  check(creator.undo().ok && !creator.world().contains("temporary") && known_ids.contains(retired_uuid),"undoing creation retains retired identity");
  check(creator.redo().ok && creator.world().at("temporary").persistent_id==retired_uuid && known_ids.contains(retired_uuid),"redo creation restores its original known identity");
  check(creator.apply({"temporary-delete",creator.revision(),{Erase{"temporary",retired_uuid}}}).ok && known_ids.contains(retired_uuid),"retirement preserves identity after redo");
  auto reused=node("replacement"); reused.persistent_id=retired_uuid;
  check(!creator.apply({"reuse-retired",creator.revision(),{Create{reused}}}).ok && known_ids.size()==2,"known retired UUID cannot be reused by another entity");
  const auto slot=std::filesystem::temp_directory_path()/("aibs-known-ids-"+new_uuid()+".aibs");
  struct SlotCleanup {
   std::filesystem::path file;
   ~SlotCleanup() { std::error_code error; std::filesystem::remove(file,error); auto lock=file;lock+=L".lock";std::filesystem::remove(lock,error); }
  } cleanup{slot};
  check(CheckpointStore::save(slot,creator).ok,"save original format with lifetime identity evidence");
  CreatorSession restored(schemas,"first-boot","main");
  check(CheckpointStore::load(slot,restored).ok && restored.known_entity_ids()==known_ids &&
        restored.world()==creator.world() && restored.memory().events()==creator.memory().events(),"unchanged format restores alive and retired UUID set alongside original world/history");
  FixedStep clock;
  check(clock.advance(1.0 / 30) == 2, "fixed ticks");
  clock.pause(true);
  check(clock.advance(10) == 0, "paused simulation");
  clock.pause(false);
  check(clock.advance(2) == 4 && clock.overloads() == 1, "bounded catchup");
  check(clock.advance(-1) == 0, "negative delta rejected");
  std::cout << "PASS: transactional authoring, revision conflicts, memory, history, Play isolation, fixed step\n";
  return 0;
 } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
