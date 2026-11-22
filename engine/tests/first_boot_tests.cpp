#include <aibs/first_boot.hpp>
#include <aibs/persistence.hpp>
#include <aibs/player.hpp>
#include <cmath>
#include <bit>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace aibs;
void require(bool ok, const char* why) { if (!ok) throw std::runtime_error(why); }
std::uint64_t geometry_fingerprint(const SceneSnapshot& scene) {
 auto hash=UINT64_C(14695981039346656037);
 for(const auto& vertex:mesh_from_snapshot(scene).vertices) {
  for(const auto number:{vertex.position.x,vertex.position.y,vertex.position.z,vertex.normal.x,vertex.normal.y,vertex.normal.z,
                        vertex.color.x,vertex.color.y,vertex.color.z,vertex.emission}) {
   const auto bits=std::bit_cast<std::uint32_t>(number);
   for(unsigned byte=0;byte<4;++byte) { hash^=(bits>>(byte*8))&255; hash*=UINT64_C(1099511628211); }
  }
 }
 return hash;
}
void pure_projection_matches(const CreatorSession& session,const SceneSnapshot& reference) {
 const World detached=session.world();
 const auto projected=first_boot_scene(detached,session.world_id(),session.revision());
 require(projected.world_id==reference.world_id && projected.revision==reference.revision && projected.objects.size()==reference.objects.size(),
  "pure projection preserves explicit scope revision and object order");
 require(geometry_fingerprint(projected)==geometry_fingerprint(reference),"pure projection preserves all rendered float bits");
 for(std::size_t index=0;index<projected.objects.size();++index) {
  const auto& actual=projected.objects[index]; const auto& expected=reference.objects[index];
  require(actual.persistent_id==expected.persistent_id && actual.name==expected.name && actual.center==expected.center &&
          actual.half_extent==expected.half_extent && actual.color==expected.color && actual.emission==expected.emission &&
          actual.selectable==expected.selectable && actual.rotation.x==expected.rotation.x && actual.rotation.y==expected.rotation.y &&
          actual.rotation.z==expected.rotation.z && actual.rotation.w==expected.rotation.w,"pure projection preserves every scene object field");
 }
 const auto other_world=new_uuid();
 const auto explicit_metadata=first_boot_scene(detached,other_world,777);
 require(explicit_metadata.world_id==other_world && explicit_metadata.revision==777 &&
         geometry_fingerprint(explicit_metadata)==geometry_fingerprint(reference),"projection uses supplied metadata without manufacturing session state");
 require(detached==session.world(),"pure projection leaves its authoritative input untouched");
}
void pure_rejects(const World& world,const std::string& world_id,const char* why) {
 bool rejected=false;
 try { (void)first_boot_scene(world,world_id,42); } catch(const std::invalid_argument&) { rejected=true; }
 require(rejected,why);
}
int main() {
 const auto directory = std::filesystem::temp_directory_path() / ("aibs-first-boot-" + new_uuid());
 std::filesystem::create_directories(directory);
 try {
  CreatorSession session(first_boot_schema(), "first-boot-visible", "main");
  bool unseeded = false;
  try { (void)first_boot_scene(session); } catch (const std::invalid_argument&) { unseeded = true; }
  require(unseeded, "uninitialized world is explicit");
  require(seed_first_boot(session).ok, "seed world");
  const auto seeded_revision = session.revision();
  require(seed_first_boot(session).ok && session.revision() == seeded_revision, "seed retry is not duplicated");
  const auto dark = first_boot_scene(session);
  require(dark.objects.size() > session.world().size() && dark.world_id == session.world_id() && dark.revision == session.revision(), "render snapshot contains scoped composite objects");
  const auto dark_mesh = mesh_from_snapshot(dark);
  pure_projection_matches(session,dark);
  pure_rejects({},session.world_id(),"pure projection rejects an uninitialized world");
  pure_rejects(session.world(),"invalid-world-id","pure projection rejects invalid explicit world identity");
  require(dark_mesh.vertices.size() == dark.objects.size() * 36, "all saved game objects produce validated box geometry");
  const auto core = session.world().at("core-01").persistent_id;
  require(first_boot_entity(session, core) == &session.world().at("core-01"), "UUID resolution");
  const World detached=session.world();
  require(first_boot_entity(detached,core)==&detached.at("core-01") && !first_boot_entity(detached,"invalid") && !first_boot_entity(detached,new_uuid()),
   "pure UUID resolution borrows the supplied world and rejects unknown identities");
  auto invalid_world=detached; invalid_world.begin()->second.id="alias-mismatch";
  pure_rejects(invalid_world,session.world_id(),"pure projection preserves alias validation");
  invalid_world=detached; invalid_world.at("core-01").fields.erase("capacity");
  pure_rejects(invalid_world,session.world_id(),"pure projection preserves required field validation");
  invalid_world=detached; invalid_world.at("ram-1").fields["firstboot.kind"]=2.5;
  pure_rejects(invalid_world,session.world_id(),"pure projection preserves integral kind validation");
  require(repair_first_boot(session, core).ok, "repair core");
  const auto lit = first_boot_scene(session);
  std::cout<<"Projection geometry baseline dark="<<geometry_fingerprint(dark)<<" lit="<<geometry_fingerprint(lit)<<'\n';
  require(geometry_fingerprint(dark)==UINT64_C(1501321206742680957) && geometry_fingerprint(lit)==UINT64_C(1388916305200067637),
   "pure refactor retains captured original Debug and Release scene bytes");
  pure_projection_matches(session,lit);
  bool illumination_changed = false;
  for (std::size_t i = 0; i < dark.objects.size(); ++i)
   if (dark.objects[i].emission < lit.objects[i].emission || dark.objects[i].color != lit.objects[i].color) illumination_changed = true;
  require(illumination_changed, "real repair changes visible light state");
  const auto repaired_revision = session.revision();
  require(repair_first_boot(session, core).ok && session.revision() == repaired_revision, "healthy repair is no-op");
  require(!repair_first_boot(session, new_uuid()).ok && session.revision() == repaired_revision, "unknown target rejected without memory");
  require(!dismantle_first_boot(session, core).ok, "core is protected");
  const auto before_build = session.world().size();
  require(build_first_boot_relay(session, {2, 2, -21}).ok, "build relay");
  require(session.world().size() == before_build + 1, "relay persists as entity");
  const auto relay = session.memory().events().back().edits.front();
  const auto relay_uuid = std::get<Create>(relay).entity.persistent_id;
  require(first_boot_entity(session, relay_uuid) != nullptr, "built relay UUID resolves");
  pure_projection_matches(session,first_boot_scene(session));
  const auto slot = directory / "visible-world.aibs";
  require(CheckpointStore::save(slot, session).ok, "save visible world");
  CreatorSession resumed(first_boot_schema(), "first-boot-visible", "main");
  require(CheckpointStore::load(slot, resumed).ok, "reload visible world");
  require(resumed.world() == session.world() && resumed.memory().events() == session.memory().events(), "saved world and Adam history match");
  require(first_boot_scene(resumed).objects.size() == first_boot_scene(session).objects.size(), "visible objects survive reload");
  pure_projection_matches(resumed,first_boot_scene(session));
  require(first_boot_guidance(resumed).find("restored") != std::string::npos, "guidance agrees with actual restoration");
  require(dismantle_first_boot(resumed, relay_uuid).ok && first_boot_entity(resumed, relay_uuid) == nullptr, "dismantle relay");
  require(resumed.undo().ok && first_boot_entity(resumed, relay_uuid) != nullptr, "undo restores original relay UUID");
  require(resumed.redo().ok && first_boot_entity(resumed, relay_uuid) == nullptr, "redo removes it again");
  const auto revision = resumed.revision();
  require(!build_first_boot_relay(resumed, {std::numeric_limits<float>::quiet_NaN(), 0, 0}).ok && resumed.revision() == revision, "nonfinite placement rejected");
  require(!build_first_boot_relay(resumed, {201, 0, 0}).ok && resumed.revision() == revision, "out of bounds placement rejected");
  CreatorSession malformed(first_boot_schema(), "bad", "main");
  require(malformed.apply({"bad", 0, {Create{{"core-01", "Incomplete", {{"firstboot.kind", 2}}}}}}).ok, "partial authoring record admitted by generic schema");
  bool rejected = false;
  try { (void)first_boot_scene(malformed); } catch (const std::invalid_argument&) { rejected = true; }
  require(rejected, "incomplete saved game entity is not silently defaulted");
  CreatorSession unsupported(first_boot_schema(), "bad-kind", "main");
  require(seed_first_boot(unsupported).ok, "seed malformed-kind fixture");
  const auto existing = unsupported.world().at("ram-1").persistent_id;
  require(unsupported.apply({"fractional-kind", unsupported.revision(), {SetField{"ram-1", "firstboot.kind", 2.5, existing}}}).ok, "numeric base schema admits fractional field");
  rejected = false;
  try { (void)first_boot_scene(unsupported); } catch (const std::invalid_argument&) { rejected = true; }
  require(rejected, "unsupported fractional kind is rejected by game projection");
  CreatorSession entrance(first_boot_schema(), "entrance-blocked", "main");
  require(seed_first_boot(entrance).ok, "seed safe-spawn fixture");
  auto walking = first_boot_player(entrance);
  auto pure_walking=first_boot_player(entrance.world(),entrance.world_id(),entrance.revision());
  require(pure_walking.state().feet==walking.state().feet,"pure player preserves preferred spawn");
  WindowInput walk; walk.right = 1;
  for (int tick = 0; tick < 90; ++tick) walking.update(walk, 1.0 / 60);
  require(walking.state().feet.x > -25, "BS walks away from the entrance before building");
  require(build_first_boot_relay(entrance, {-32, 1.2f, -25}).ok, "build a relay over the old entrance");
  walking.set_scene(first_boot_scene(entrance));
  const auto blocked_slot = directory / "blocked-entrance.aibs";
  require(CheckpointStore::save(blocked_slot, entrance).ok, "save valid blocked entrance");
  CreatorSession blocked(first_boot_schema(), "entrance-blocked", "main");
  require(CheckpointStore::load(blocked_slot, blocked).ok, "load blocked-entrance world");
  const auto blocked_world = blocked.world();
  const auto blocked_events = blocked.memory().events();
  const auto blocked_world_id = blocked.world_id();
  auto safe_player = first_boot_player(blocked);
  const auto safe_feet = safe_player.state().feet;
  auto pure_safe=first_boot_player(blocked_world,blocked_world_id,blocked.revision());
  require(pure_safe.state().feet==safe_feet,"pure player preserves deterministic blocked-entrance fallback");
  require(std::abs(safe_feet.x + 32) > .1f || std::abs(safe_feet.z + 25) > .1f, "blocked entrance selects another safe spawn");
  for (int tick = 0; tick < 60; ++tick) safe_player.update({}, 1.0 / 60);
  require(safe_player.state().grounded, "fallback spawn settles on the board");
  require(blocked.world_id() == blocked_world_id && blocked.world() == blocked_world && blocked.memory().events() == blocked_events,
   "safe spawn preserves saved identities, built entities and Adam events");
  CreatorSession shifted(first_boot_schema(), "shifted-board", "main");
  require(seed_first_boot(shifted).ok, "seed shifted-board fixture");
  const auto board_id = shifted.world().at("board").persistent_id;
  require(shifted.apply({"move-board", shifted.revision(), {SetField{"board", "x", 90, board_id}, SetField{"board", "z", 90, board_id},
   SetField{"board", "y", 4, board_id}}}).ok, "author a different board position");
  auto shifted_player = first_boot_player(shifted);
  const auto shifted_feet = shifted_player.state().feet;
  auto pure_shifted=first_boot_player(shifted.world(),shifted.world_id(),shifted.revision());
  require(pure_shifted.state().feet==shifted_feet,"pure player derives the same shifted-board spawn");
  require(shifted_feet.x > 43 && shifted_feet.x < 137 && shifted_feet.z > 54 && shifted_feet.z < 126 && shifted_feet.y > 5,
   "spawn derives bounds and top from the actual board");
  for (int tick = 0; tick < 60; ++tick) shifted_player.update({}, 1.0 / 60);
  require(shifted_player.state().grounded && shifted_player.state().feet.y > 4.9f, "shifted-board spawn remains supported");
  CreatorSession full(first_boot_schema(), "blocked-board", "main");
  require(seed_first_boot(full).ok, "seed fully obstructed board fixture");
  const auto small_board_id = full.world().at("board").persistent_id;
  require(full.apply({"small-board", full.revision(), {SetField{"board", "x", -32, small_board_id}, SetField{"board", "z", -25, small_board_id},
   SetField{"board", "half_x", .45, small_board_id}, SetField{"board", "half_z", .45, small_board_id}}}).ok, "author a bounded small board");
  require(build_first_boot_relay(full, {-32, 1.2f, -25}).ok, "obstruct all supported spawn positions");
  rejected = false;
  try { (void)first_boot_player(full); }
  catch (const std::runtime_error& error) { rejected = std::string(error.what()).find("safe") != std::string::npos; }
  require(rejected, "fully obstructed board fails with a helpful bounded-spawn error");
  rejected=false;
  try { (void)first_boot_player(full.world(),full.world_id(),full.revision()); } catch(const std::runtime_error&) { rejected=true; }
  require(rejected,"pure player preserves fully obstructed board failure");
  std::filesystem::remove_all(directory);
  std::cout << "PASS: saved First Boot entities drive visible state and safe actions\n";
  return 0;
 } catch (const std::exception& error) {
  std::cerr << "FAIL: " << error.what() << '\n';
  std::filesystem::remove_all(directory);
  return 1;
 }
}
