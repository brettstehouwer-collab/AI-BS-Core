#pragma once
#include <aibs/engine.hpp>
#include <aibs/scene.hpp>
#include <aibs/player.hpp>

namespace aibs {
enum class FirstBootKind : unsigned { board = 1, core = 2, ram = 3, gpu = 4, archive = 5, relay = 6, trace = 7, slot = 8, power = 9 };
// Numeric source fields are firstboot.kind, x/y/z, half_x/half_y/half_z,
// and capacity. Every First Boot entity supplies all fields explicitly.
SchemaRegistry first_boot_schema();
Result seed_first_boot(CreatorSession& session);
SceneSnapshot first_boot_scene(const CreatorSession& session);
// Pure projection of authoritative entities; no session/history is synthesized.
SceneSnapshot first_boot_scene(const World& world,const std::string& world_id,std::uint64_t revision);
// Transient spawn only: preferred entrance, then at most 81 board-top points.
// Preserves every saved entity/event; a fully blocked board is an explicit error.
PlayerController first_boot_player(const CreatorSession& session);
PlayerController first_boot_player(const World& world,const std::string& world_id,std::uint64_t revision);
const Entity* first_boot_entity(const CreatorSession& session, const std::string& persistent_id);
const Entity* first_boot_entity(const World& world,const std::string& persistent_id);
Result repair_first_boot(CreatorSession& session, const std::string& persistent_id);
Result build_first_boot_relay(CreatorSession& session, Vec3 position);
Result dismantle_first_boot(CreatorSession& session, const std::string& persistent_id);
std::string first_boot_guidance(const CreatorSession& session);
}
