#pragma once
#include <aibs/first_boot_chapter.hpp>
#include <aibs/asset_store.hpp>
#include <aibs/guide_controller.hpp>
#include <aibs/opening_workshop.hpp>
#include <memory>
#include <span>

namespace aibs {
struct FirstBootContentRegion { Vec3 center,half_extent; };
enum class FixtureRole : std::uint8_t {legacy=0,workshop=2};
struct FirstBootContentFixture { SceneObject object;float sheltered_emission=-1;FixtureRole role=FixtureRole::legacy; };
struct FirstBootAssetPlacement {
 std::string entity_id,name,asset_id,asset_sha256,pack_sha256;
 Vec3 center{},scale{1,1,1};
 Quaternion rotation{};
 bool selectable=true;
};
// Authored declarations only. Runtime intent/media controls and animation state
// belong to compatible runtime schemas, not these immutable content bindings.
struct FirstBootCompanionBinding {
 std::string entity_id,name;
 Vec3 spawn;
 bool initial_follow=true;
 std::optional<AssetPackReference> model;
 GuideRouteGraph routes;
};
enum class FirstBootLightKind : std::uint8_t { directional,point };
enum class FirstBootLightPower : std::uint8_t { reserve,restored };
struct FirstBootLightDefinition {
 std::string entity_id,name;
 FirstBootLightKind kind=FirstBootLightKind::point;
 FirstBootLightPower power=FirstBootLightPower::reserve;
 Vec3 position{},direction{0,-1,0},color{1,1,1};
 float intensity=1,radius=10;
};
struct FirstBootMemoryBinding {
 std::string entity_id,name;
 Vec3 position;
 AssetPackReference audio;
};
// Authored initial defaults are validated, never a player-state editing surface.
struct FirstBootContentDefinition {
 std::string definition_id,world_id,binding_id;
 std::uint64_t revision=0;
 World hardware;
 std::vector<ComponentRecord> initial_records;
 std::vector<FirstBootContentFixture> fixtures;
 FirstBootContentRegion hub,pencil;
 std::vector<Vec3> jenison_returns,hub_returns;
 Vec3 isolation_switch;
 std::map<std::string,std::string> hints;
 std::vector<FirstBootAssetPlacement> placements;
 std::uint16_t format_version=1;
 AssetContentProfile asset_profile=AssetContentProfile::legacy_v1;
 float exposure=1;
 std::vector<FirstBootCompanionBinding> companions;
 std::vector<FirstBootLightDefinition> lights;
 std::vector<FirstBootMemoryBinding> memories;
};
std::optional<OpeningWorkshopBinding> first_boot_content_workshop_binding(const FirstBootContentDefinition&);
class FirstBootContent {
public:
 static FirstBootContent from_template(const CreatorSession& source);
 static FirstBootContent create(FirstBootContentDefinition definition);
 const FirstBootContentDefinition& definition() const noexcept;
 const std::string& fingerprint() const noexcept;
private:
 struct Data;
 std::shared_ptr<const Data> data_;
 explicit FirstBootContent(std::shared_ptr<const Data> data):data_(std::move(data)){}
 friend std::vector<unsigned char> first_boot_content_encode(const FirstBootContent&);
};
enum class FirstBootContentPreviewStatus { compatible,new_play_branch,rejected };
struct FirstBootContentPreview {
 FirstBootContentPreviewStatus status=FirstBootContentPreviewStatus::rejected;
 bool save_compatible=false,render_rebuild=false,collision_rebuild=false,power_dependencies=false,quest_dependencies=false;
 std::vector<std::string> affected_ids,dependencies;
 std::string message,navigation="Navigation rebake/automatic migration are not implemented";
 std::optional<FirstBootContent> candidate;
};
std::vector<unsigned char> first_boot_content_encode(const FirstBootContent& content);
FirstBootContent first_boot_content_decode(std::span<const unsigned char> bytes);
FirstBootContentPreview first_boot_content_preview(const FirstBootContent& before,FirstBootContentDefinition proposed);
std::vector<ComponentSchema> first_boot_content_schemas();
// Preserve the no-argument legacy registry. Only a content branch declaring a
// companion selects the additional durable-intent family.
std::vector<ComponentSchema> first_boot_content_schemas(const FirstBootContent& content);
// Legacy registry stays exact on reopen. Extend explicitly on an assembly
// action, preserving the prior durable head and original records.
std::vector<ComponentSchema> first_boot_content_relay_assembly_schemas(const FirstBootContent&);
struct FirstBootRelayAssemblyState {
 bool initialized=false,pickup_available=false,part_available=false,legacy=false;
 unsigned alive_relays=0;
};
FirstBootRelayAssemblyState first_boot_content_relay_assembly(const GameplayStoreRecovery&,const FirstBootContent&);
GameplayStoreBaseline first_boot_content_baseline(const FirstBootContent& content);
// Structural durable state only. A later BS edit may invalidate an old anchor
// physically; recovery preserves that anchor for an explicit validated Recall.
// These helpers never move a guide, repair hardware or change chapter progress.
std::optional<GuideIntentRecord> first_boot_content_companion_intent(const GameplayStoreRecovery&,const FirstBootContent&);
ComponentRecord first_boot_content_companion_component(const FirstBootCompanionBinding&,const GuideIntentRecord&);
// Shared chapter implementation explicitly takes immutable content. Legacy
// entry points keep their original fixed-template/save interpretation.
SceneSnapshot first_boot_content_scene(const GameplayStoreRecovery&,const FirstBootContent&);
Vec3 first_boot_content_safe_return(const GameplayStoreRecovery&,const FirstBootContent&);
PlayerController first_boot_content_player(const GameplayStoreRecovery&,const FirstBootContent&);
std::string first_boot_content_region(const GameplayStoreRecovery&,Vec3,const FirstBootContent&);
void first_boot_content_validate(const GameplayStoreRecovery&,const FirstBootContent&);
std::optional<GameplayChangeBatch> first_boot_content_action(const GameplayStoreRecovery&,const FirstBootChapterCommand&,const FirstBootChapterActor&,const FirstBootContent&);
std::optional<GameplayChangeBatch> first_boot_content_repair(const GameplayStoreRecovery&,const std::string&,const FirstBootChapterActor&,const FirstBootContent&,std::string operation_id={});
GameplayChangeBatch first_boot_content_build(const GameplayStoreRecovery&,Vec3,const FirstBootChapterActor&,const FirstBootContent&,std::string operation_id={});
std::optional<GameplayChangeBatch> first_boot_content_dismantle(const GameplayStoreRecovery&,const std::string&,const FirstBootChapterActor&,const FirstBootContent&,std::string operation_id={});
void first_boot_content_rules(const GameplayStoreRecovery&,const GameplayStoreRecovery&,const GameplayChangeBatch&,const FirstBootChapterActor&,const FirstBootContent&,const std::set<std::string>& historical_ids={});
std::string first_boot_content_hint(const GameplayStoreRecovery&,const FirstBootChapterActor&,const FirstBootContent&,std::string target_id={});
std::string first_boot_content_workshop_hint(const GameplayStoreRecovery&,const FirstBootContent&);
OpeningWorkshopCircuit first_boot_content_workshop_circuit(const GameplayStoreRecovery&,const FirstBootContent&);
struct FirstBootSupplyState { bool main=false,bypass=false; };
// Current physical supply state, shared with the actual chapter rules. This
// observation never repairs, reconnects or advances gameplay progress.
FirstBootSupplyState first_boot_content_supply(const GameplayStoreRecovery&,
                                              const FirstBootContent&);
// Adapter support: public for SDK validation; no mutation or automatic migration.
bool first_boot_content_runtime_field(const std::string& type,const std::string& field);
void first_boot_content_check_binding(const GameplayStoreRecovery&,const FirstBootContent&);
std::string first_boot_content_locate(const FirstBootContent&,Vec3);
}
