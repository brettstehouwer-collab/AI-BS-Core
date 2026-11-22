#include <aibs/persistence.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace aibs;
void require(bool ok, const char* reason) { if (!ok) throw std::runtime_error(reason); }
SchemaRegistry schemas() { SchemaRegistry s; s.add({"capacity", 0, 100}); s.add({"open", 0, 1}); return s; }
Transaction place(std::string op, std::uint64_t rev, std::string alias) {
 return {std::move(op), rev, {Create{{std::move(alias), "Node", {{"capacity", 0}}}}}, "Built a core node"};
}
int main() {
 const auto directory = std::filesystem::temp_directory_path() / ("aibs-save-test-" + new_uuid());
 std::filesystem::create_directories(directory);
 try {
  require(is_uuid(new_uuid()) && new_uuid() != new_uuid(), "UUID v4 allocation");
  CreatorSession session(schemas(), "first-boot", "main");
  require(session.apply(place("build", 0, "core")).ok, "create");
  const auto entity_id = session.world().at("core").persistent_id;
  require(is_uuid(entity_id) && is_uuid(session.world_id()), "world and entity stable UUIDs");
  require(session.apply({"repair", 1, {SetField{"core", "capacity", 75}}, "Restored Core Node 01"}).ok, "repair");
  require(session.memory().events().back().description == "Restored Core Node 01", "meaning retained");
  const auto slot = directory / "world.aibs";
  require(CheckpointStore::save(slot, session).ok, "save");
  CreatorSession resumed(schemas(), "first-boot", "main");
  require(CheckpointStore::load(slot, resumed).ok, "load");
  const auto before_validation = resumed.world();
  require(!CheckpointStore::load(slot, resumed, [](const CreatorSession&) { throw std::runtime_error("Game rejects this scene"); }).ok,
          "game-specific load validation rejects candidate");
  require(resumed.world() == before_validation, "game validation preserves live world");
  require(resumed.world() == session.world() && resumed.world_id() == session.world_id(), "world identity/state roundtrip");
  require(resumed.memory().events() == session.memory().events(), "Adam journal roundtrip");
  require(resumed.apply(place("build", 0, "core")).ok && resumed.revision() == 2, "durable request dedup");
  require(resumed.undo().ok && resumed.world().at("core").fields.at("capacity") == 0, "undo survives restart");
  require(CheckpointStore::save(slot, resumed).ok, "save undo");
  require(CheckpointStore::load(slot, session).ok && session.redo().ok, "redo survives restart");
  require(session.world().at("core").persistent_id == entity_id, "history preserves UUID");
  require(session.apply({"delete", session.revision(), {Erase{"core"}}}).ok, "delete");
  require(session.apply(place("replacement", session.revision(), "core")).ok, "alias reuse");
  require(session.world().at("core").persistent_id != entity_id, "alias reuse gets new identity");
  require(!session.apply({"stale-target", session.revision(), {SetField{"core", "capacity", 2, entity_id}}}).ok, "stale UUID target rejected");
  Entity reused{"other", "Other", {{"capacity", 1}}, entity_id};
  require(!session.apply({"recycle", session.revision(), {Create{reused}}}).ok, "tombstone rejects UUID recycling");
  require(CheckpointStore::save(slot, session).ok, "save replacement");
  CreatorSession stale(schemas(), "first-boot", "main");
  require(CheckpointStore::load(slot, stale).ok, "second reader");
  require(session.apply({"newer", session.revision(), {SetField{"core", "capacity", 80}}}).ok, "advance owner");
  require(CheckpointStore::save(slot, session).ok, "newer head");
  require(!CheckpointStore::save(slot, stale).ok, "stale writer cannot overwrite head");
  CreatorSession different(schemas(), "first-boot", "main");
  require(!CheckpointStore::save(slot, different).ok, "different world cannot overwrite slot");
  CreatorSession wrong_branch(schemas(), "first-boot", "experiment");
  require(!CheckpointStore::load(slot, wrong_branch).ok && wrong_branch.world().empty(), "branch isolation");
  SchemaRegistry changed; changed.add({"capacity", 0, 50});
  CreatorSession incompatible(changed, "first-boot", "main");
  require(!CheckpointStore::load(slot, incompatible).ok, "schema compatibility");
  std::ifstream in(slot, std::ios::binary);
  std::string bytes((std::istreambuf_iterator<char>(in)), {});
  in.close();
  const auto prior = session.world();
  const auto prior_memory = session.memory().events();
  const auto prior_head = session.checkpoint_id();
  for (int mode = 0; mode < 4; ++mode) {
   auto broken = bytes;
   if (mode == 0) broken.resize(12);
   if (mode == 1) broken.back() ^= 1;
   if (mode == 2) broken[8] = 99;
   if (mode == 3) broken += 'x';
   const auto corrupt = directory / ("corrupt" + std::to_string(mode) + ".aibs");
   std::ofstream out(corrupt, std::ios::binary); out.write(broken.data(), static_cast<std::streamsize>(broken.size())); out.close();
   require(!CheckpointStore::load(corrupt, session).ok && session.world() == prior, "invalid load leaves session intact");
   require(session.memory().events() == prior_memory && session.checkpoint_id() == prior_head, "invalid load leaves memory/head intact");
  }
  require(!CheckpointStore::load(directory / "missing.aibs", session).ok, "missing save surfaced");
  std::filesystem::remove_all(directory);
  std::cout << "PASS: identity, checkpoints, memory, restart history, stale writers, corrupt files\n";
  return 0;
 } catch (const std::exception& e) {
  std::cerr << "FAIL: " << e.what() << '\n';
  std::filesystem::remove_all(directory);
  return 1;
 }
}
