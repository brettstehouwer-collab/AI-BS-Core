#include <aibs/first_boot.hpp>
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace aibs {
namespace {
constexpr const char* kind_field = "firstboot.kind";
double required(const Entity& entity, const std::string& field) {
 const auto found = entity.fields.find(field);
 if (found == entity.fields.end() || !std::isfinite(found->second))
  throw std::invalid_argument("First Boot entity " + entity.id + " has a missing/nonfinite field: " + field);
 return found->second;
}
FirstBootKind kind(const Entity& entity) {
 const auto value = required(entity, kind_field);
 if (value < 1 || value > 9 || std::floor(value) != value) throw std::invalid_argument("Unsupported First Boot entity kind");
 return static_cast<FirstBootKind>(static_cast<unsigned>(value));
}
Vec3 position(const Entity& entity) {
 return {static_cast<float>(required(entity, "x")), static_cast<float>(required(entity, "y")), static_cast<float>(required(entity, "z"))};
}
Vec3 half_extent(const Entity& entity) {
 return {static_cast<float>(required(entity, "half_x")), static_cast<float>(required(entity, "half_y")), static_cast<float>(required(entity, "half_z"))};
}
void validate_entity(const Entity& entity) {
 if (entity.id.empty() || entity.name.empty() || !is_uuid(entity.persistent_id)) throw std::invalid_argument("First Boot entity identity/name is invalid");
 (void)kind(entity);
 const auto p = position(entity), h = half_extent(entity);
 const auto capacity = required(entity, "capacity");
 if (p.x < -200 || p.x > 200 || p.z < -200 || p.z > 200 || p.y < -50 || p.y > 100 ||
     h.x < 0.01f || h.x > 100 || h.y < 0.01f || h.y > 100 || h.z < 0.01f || h.z > 100 || capacity < 0 || capacity > 100)
  throw std::invalid_argument("First Boot entity fields are outside supported bounds");
}
const Entity& core_entity(const World& world) {
 if (world.empty()) throw std::invalid_argument("First Boot world is not initialized");
 const Entity* core = nullptr;
 unsigned boards = 0, gpus = 0;
 for (const auto& [alias, entity] : world) {
  if (alias != entity.id) throw std::invalid_argument("First Boot entity alias mismatch");
  validate_entity(entity);
  switch (kind(entity)) {
  case FirstBootKind::core:
   if (core) throw std::invalid_argument("First Boot world has multiple core nodes");
   core = &entity; break;
  case FirstBootKind::board: ++boards; break;
  case FirstBootKind::gpu: ++gpus; break;
  default: break;
  }
 }
 if (!core || boards != 1 || gpus != 1) throw std::invalid_argument("First Boot world requires one board, core and GPU landmark");
 return *core;
}
Entity entity(std::string alias, std::string name, FirstBootKind type, Vec3 center, Vec3 half, double capacity = 100) {
 return {std::move(alias), std::move(name), {{kind_field, static_cast<double>(type)}, {"x", center.x}, {"y", center.y}, {"z", center.z},
  {"half_x", half.x}, {"half_y", half.y}, {"half_z", half.z}, {"capacity", capacity}}};
}
Vec3 mix(Vec3 dark, Vec3 lit, float power) {
 return {dark.x + (lit.x-dark.x)*power, dark.y + (lit.y-dark.y)*power, dark.z + (lit.z-dark.z)*power};
}
void box(SceneSnapshot& snapshot, const Entity& source, Vec3 center, Vec3 half, Vec3 color, float emission = 0, bool selectable = true) {
 snapshot.objects.push_back({source.persistent_id, source.name, center, half, color, emission, selectable});
}
Result rejected(const CreatorSession& session, std::string message) { return {false, std::move(message), session.revision()}; }
}

SchemaRegistry first_boot_schema() {
 SchemaRegistry schema;
 for (const auto& field : std::vector<FieldSchema>{{kind_field,1,9},{"x",-200,200},{"y",-50,100},{"z",-200,200},
     {"half_x",0.01,100},{"half_y",0.01,100},{"half_z",0.01,100},{"capacity",0,100}}) {
  if (!schema.add(field)) throw std::logic_error("First Boot schema registration failed");
 }
 return schema;
}

Result seed_first_boot(CreatorSession& session) {
 if (!session.world().empty()) {
  try { (void)core_entity(session.world()); }
  catch (const std::invalid_argument& error) { return rejected(session, error.what()); }
  return {true, "First Boot world already initialized; no changes applied", session.revision()};
 }
 std::vector<Edit> edits;
 edits.push_back(Create{entity("board", "Motherboard foundation", FirstBootKind::board, {0,-1,0}, {47,1,36})});
 edits.push_back(Create{entity("core-01", "Core Node 01", FirstBootKind::core, {-13,1.1f,-5}, {9,1.1f,9}, 0)});
 edits.push_back(Create{entity("gpu-01", "RTX execution core", FirstBootKind::gpu, {0,10,24}, {23,10,3.5f})});
 edits.push_back(Create{entity("archive-01", "M.2 archive", FirstBootKind::archive, {21,1.1f,-27}, {13,1.1f,3})});
 for (int i = 0; i < 4; ++i) {
  const float x = 8 + static_cast<float>(i) * 4;
  edits.push_back(Create{entity("ram-" + std::to_string(i+1), "DDR5 memory tower " + std::to_string(i+1), FirstBootKind::ram, {x,5.5f,-7}, {0.6f,4.5f,10.5f})});
  edits.push_back(Create{entity("slot-" + std::to_string(i+1), "PCIe corridor " + std::to_string(i+1), FirstBootKind::slot, {27,0.6f,3+static_cast<float>(i)*4}, {15,0.6f,0.5f})});
 }
 for (int i = -8; i <= 8; ++i) {
  const float offset = static_cast<float>(i) * 5;
  const auto index = std::to_string(i+8);
  edits.push_back(Create{entity("trace-z-"+index, "Power trace", FirstBootKind::trace, {offset,0.07f,0}, {0.10f,0.06f,33})});
  edits.push_back(Create{entity("trace-x-"+index, "Data trace", FirstBootKind::trace, {0,0.06f,offset*0.75f}, {44,0.04f,0.06f})});
 }
 for (int i = 0; i < 10; ++i)
  edits.push_back(Create{entity("power-"+std::to_string(i), "Core power stage", FirstBootKind::power, {-24,1.4f,-14+static_cast<float>(i)*2}, {1.1f,1.4f,0.65f})});
 return session.apply({"first-boot.seed." + new_uuid(), session.revision(), std::move(edits), "Established the motherboard world with an unpowered Core Node 01"});
}

SceneSnapshot first_boot_scene(const CreatorSession& session) {
 return first_boot_scene(session.world(),session.world_id(),session.revision());
}
SceneSnapshot first_boot_scene(const World& world,const std::string& world_id,std::uint64_t revision) {
 const auto& core = core_entity(world);
 if(!is_uuid(world_id)) throw std::invalid_argument("First Boot scene requires a persistent world UUID");
 const float power = static_cast<float>(required(core, "capacity") / 100);
 SceneSnapshot snapshot{world_id, revision, {}};
 for (const auto& [alias, e] : world) {
  (void)alias;
  const auto p = position(e), h = half_extent(e);
  switch (kind(e)) {
  case FirstBootKind::board:
   box(snapshot,e,p,h,mix({0.025f,0.07f,0.055f},{0.035f,0.15f,0.12f},power),0,false);
   box(snapshot,e,{p.x,p.y-h.y-0.3f,p.z},{h.x+1,0.3f,h.z+1},{0.08f,0.09f,0.12f},0,false);
   break;
  case FirstBootKind::core:
   box(snapshot,e,p,h,{0.12f,0.13f,0.17f});
   box(snapshot,e,{p.x,p.y+h.y+0.15f,p.z},{h.x*0.7f,0.3f,h.z*0.7f},mix({0.24f,0.27f,0.29f},{0.58f,0.62f,0.69f},power));
   box(snapshot,e,{p.x,p.y+h.y+0.52f,p.z},{h.x*0.52f,0.06f,h.z*0.52f},mix({0.12f,0.15f,0.18f},{0.92f,0.48f,0.10f},power),power);
   break;
  case FirstBootKind::ram:
   box(snapshot,e,p,h,{0.12f,0.29f,0.22f});
   box(snapshot,e,{p.x,p.y+h.y+0.1f,p.z},{h.x*1.5f,0.2f,h.z*1.02f},mix({0.12f,0.10f,0.06f},{0.70f,0.32f,0.08f},power),power*0.65f);
   for (int chip = 0; chip < 6; ++chip)
    box(snapshot,e,{p.x-h.x-0.15f,p.y,p.z-h.z*0.76f+static_cast<float>(chip)*h.z*0.30f},{0.24f,h.y*0.44f,h.z*0.11f},{0.07f,0.08f,0.11f});
   break;
  case FirstBootKind::gpu: {
   box(snapshot,e,p,h,{0.09f,0.10f,0.13f});
   const auto light = mix({0.10f,0.07f,0.035f},{0.95f,0.48f,0.10f},power);
   for (int step = 0; step < 20; ++step) {
    const float x = -h.x + (static_cast<float>(step)+0.5f)*(h.x*2/20);
    const float rise = x * (h.y*0.82f/h.x);
    for (float sign : {-1.0f,1.0f})
     box(snapshot,e,{p.x+x,p.y+rise*sign,p.z-h.z-0.3f},{h.x/20+0.05f,h.y*0.055f,0.2f},light,power);
   }
   for (float side : {-1.0f,1.0f}) for (int segment = 0; segment < 20; ++segment) {
    const float angle = static_cast<float>(segment)*6.28318530718f/20;
    box(snapshot,e,{p.x+side*h.x*0.56f+std::cos(angle)*h.y*0.55f,p.y+std::sin(angle)*h.y*0.55f,p.z-h.z-0.6f},
     {h.y*0.055f,h.y*0.055f,0.25f},{0.31f,0.34f,0.39f});
   }
   break;
  }
  case FirstBootKind::archive:
   box(snapshot,e,p,h,{0.12f,0.13f,0.16f});
   for (int fin = 0; fin < 11; ++fin)
    box(snapshot,e,{p.x-h.x*0.9f+static_cast<float>(fin)*h.x*0.18f,p.y+h.y+0.3f,p.z},{0.25f,0.3f,h.z},{0.32f,0.36f,0.42f});
   break;
  case FirstBootKind::relay: {
   const float relay_power = power * static_cast<float>(required(e,"capacity")/100);
   box(snapshot,e,p,h,{0.12f,0.16f,0.21f});
   box(snapshot,e,{p.x,p.y+h.y+0.16f,p.z},{h.x*0.75f,0.16f,h.z*0.75f},mix({0.11f,0.09f,0.04f},{0.95f,0.52f,0.12f},relay_power),relay_power);
   break;
  }
  case FirstBootKind::trace:
   box(snapshot,e,p,h,mix({0.10f,0.075f,0.035f},{0.85f,0.46f,0.12f},power),power*0.7f,false); break;
  case FirstBootKind::slot:
   box(snapshot,e,p,h,{0.10f,0.11f,0.14f}); break;
  case FirstBootKind::power:
   box(snapshot,e,p,h,{0.18f,0.20f,0.24f}); break;
  }
 }
 return snapshot;
}

PlayerController first_boot_player(const CreatorSession& session) {
 return first_boot_player(session.world(),session.world_id(),session.revision());
}
PlayerController first_boot_player(const World& world,const std::string& world_id,std::uint64_t revision) {
 const auto scene = first_boot_scene(world,world_id,revision);
 const Entity* board = nullptr;
 for (const auto& [alias, source] : world) {
  (void)alias;
  if (kind(source) == FirstBootKind::board) { board = &source; break; }
 }
 // first_boot_scene already validates that exactly one board exists.
 if (!board) throw std::logic_error("First Boot board disappeared while selecting a spawn");
 const auto p = position(*board), h = half_extent(*board);
 const float margin = CharacterSettings{}.radius + .05f;
 const float min_x = p.x - h.x + margin, max_x = p.x + h.x - margin;
 const float min_z = p.z - h.z + margin, max_z = p.z + h.z - margin;
 std::vector<Vec3> candidates;
 candidates.reserve(82);
 if (min_x <= max_x && min_z <= max_z) {
  const float top = p.y + h.y + .2f;
  if (-32 >= min_x && -32 <= max_x && -25 >= min_z && -25 <= max_z)
   candidates.push_back({-32, top, -25});
  // Fixed row-major grid: bounded work and deterministic fallback selection.
  // It deliberately does not promise to find every narrow free space.
  for (int z = 0; z < 9; ++z) for (int x = 0; x < 9; ++x)
   candidates.push_back({min_x + (max_x - min_x) * static_cast<float>(x) / 8, top,
    min_z + (max_z - min_z) * static_cast<float>(z) / 8});
 }
 for (const auto& feet : candidates) {
  try { return PlayerController(scene, feet); }
  catch (const std::invalid_argument&) { /* Occupied capsule: try the next supported point. */ }
 }
 throw std::runtime_error("No safe BS spawn was found on the motherboard. Restore an earlier checkpoint or use the authoring SDK to clear an entrance.");
}

const Entity* first_boot_entity(const CreatorSession& session, const std::string& persistent_id) {
 return first_boot_entity(session.world(),persistent_id);
}
const Entity* first_boot_entity(const World& world,const std::string& persistent_id) {
 if (!is_uuid(persistent_id)) return nullptr;
 for (const auto& [alias, entity] : world) { (void)alias; if (entity.persistent_id == persistent_id) return &entity; }
 return nullptr;
}

Result repair_first_boot(CreatorSession& session, const std::string& persistent_id) {
 try { (void)core_entity(session.world()); }
 catch (const std::invalid_argument& error) { return rejected(session,error.what()); }
 const auto* target = first_boot_entity(session,persistent_id);
 if (!target) return rejected(session,"The selected entity no longer exists");
 if (kind(*target) != FirstBootKind::core && kind(*target) != FirstBootKind::relay) return rejected(session,"This object is not a repairable core or relay");
 if (required(*target,"capacity") == 100) return {true,"Already restored; no new change or memory recorded",session.revision()};
 return session.apply({"first-boot.repair."+new_uuid(),session.revision(),{SetField{target->id,"capacity",100,persistent_id}},"Restored "+target->name+" capacity"});
}

Result build_first_boot_relay(CreatorSession& session, Vec3 p) {
 try { (void)core_entity(session.world()); }
 catch (const std::invalid_argument& error) { return rejected(session,error.what()); }
 if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z) || p.x < -200 || p.x > 200 || p.z < -200 || p.z > 200 || p.y < -50 || p.y > 100)
  return rejected(session,"Relay placement must be finite and within the current world bounds");
 const auto id = "relay-"+new_uuid();
 return session.apply({"first-boot.build."+new_uuid(),session.revision(),{Create{entity(id,"Built power relay",FirstBootKind::relay,p,{0.9f,1.2f,0.9f})}},"Built a power relay in the motherboard world"});
}

Result dismantle_first_boot(CreatorSession& session, const std::string& persistent_id) {
 try { (void)core_entity(session.world()); }
 catch (const std::invalid_argument& error) { return rejected(session,error.what()); }
 const auto* target = first_boot_entity(session,persistent_id);
 if (!target) return rejected(session,"The selected entity no longer exists");
 if (kind(*target) != FirstBootKind::relay) return rejected(session,"Only player-built relays can be dismantled in this slice");
 return session.apply({"first-boot.dismantle."+new_uuid(),session.revision(),{Erase{target->id,persistent_id}},"Dismantled a built power relay"});
}

std::string first_boot_guidance(const CreatorSession& session) {
 if (session.world().empty()) return "First Boot world is not initialized yet.";
 const auto& core = core_entity(session.world());
 std::string guidance = required(core,"capacity") == 100
  ? "Core Node 01 is restored. Its connection powers the traces and execution-core landmark."
  : "Core Node 01 still needs repair. Start with what still responds.";
 if (!session.memory().events().empty()) guidance += " Last recorded change: " + session.memory().events().back().description + ".";
 return guidance;
}
}
