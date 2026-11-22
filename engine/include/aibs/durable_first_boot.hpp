#pragma once
#include <aibs/first_boot.hpp>
#include <aibs/gameplay_world.hpp>

namespace aibs {
std::vector<ComponentSchema> durable_first_boot_schemas();
// Original-save adapter: copies UUID, alias/name and all eight numeric fields.
std::vector<ComponentRecord> durable_first_boot_components(const Entity& source);
void durable_first_boot_validate_source(const CreatorSession& source);
// A new authored foundation has revision/sequence zero and no invented player
// events. The explicit format-1 importer instead preserves its original head/raw.
GameplayStoreBaseline durable_first_boot_baseline(const CreatorSession& source);
// Tombstones remain in recovery. Only alive nodes enter scene/collision views.
World durable_first_boot_world(const GameplayStoreRecovery& snapshot);
// Explicit runtime/isolated-Play admission; the content adapter separately checks
// its immutable binding. Legacy overloads still require player_world, while
// authoring/published-lore contexts always reject.
World durable_first_boot_world(const GameplayStoreRecovery&,GameplayContext expected);
SceneSnapshot durable_first_boot_scene(const GameplayStoreRecovery&,GameplayContext expected);
void durable_first_boot_validate(const GameplayStoreRecovery&,GameplayContext expected);
void durable_first_boot_rules(const GameplayStoreRecovery&,const GameplayStoreRecovery&,
 const GameplayChangeBatch&,const std::set<std::string>&,GameplayContext expected);
std::optional<GameplayChangeBatch> durable_first_boot_repair(const GameplayStoreRecovery&,const std::string&,std::string,GameplayContext);
GameplayChangeBatch durable_first_boot_build(const GameplayStoreRecovery&,Vec3,std::string,GameplayContext);
std::optional<GameplayChangeBatch> durable_first_boot_dismantle(const GameplayStoreRecovery&,const std::string&,std::string,GameplayContext);
SceneSnapshot durable_first_boot_scene(const GameplayStoreRecovery& snapshot);
PlayerController durable_first_boot_player(const GameplayStoreRecovery& snapshot);
void durable_first_boot_validate(const GameplayStoreRecovery& snapshot);
std::set<std::string> durable_first_boot_imported_ids(const GameplayStore& original_archive);
void durable_first_boot_rules(const GameplayStoreRecovery& before,const GameplayStoreRecovery& after,
                             const GameplayChangeBatch& batch,const std::set<std::string>& historical_ids={});
// Normalizes finite ray direction. A downward intersection must be within
// (0,200) world units. Placement follows board top, without an extent restriction.
std::optional<Vec3> durable_first_boot_placement(const GameplayStoreRecovery& snapshot,Vec3 origin,Vec3 direction);
// Reuse the resulting immutable request for exact retries. Rebuilding an action
// creates a new event identity. Healthy repairs/dead dismantles are no-ops.
std::optional<GameplayChangeBatch> durable_first_boot_repair(const GameplayStoreRecovery& before,
 const std::string& entity_id,std::string operation_id={});
GameplayChangeBatch durable_first_boot_build(const GameplayStoreRecovery& before,Vec3 position,std::string operation_id={});
std::optional<GameplayChangeBatch> durable_first_boot_dismantle(const GameplayStoreRecovery& before,
 const std::string& entity_id,std::string operation_id={});
struct DurableFirstBootGuidance {
 std::string authored_hint;
 std::vector<std::string> committed_facts;
 std::string original_evidence;
};
// Query on startup or a visible/acknowledged durable-head change; cache for HUD.
// The archive must be the same scoped store; no pending proposal is recalled as
// committed history, and source memoir quotations are never manufactured.
DurableFirstBootGuidance durable_first_boot_guidance(const GameplayWorld& world,const GameplayStore& original_archive,
                                                    std::size_t max_facts=4);
}
