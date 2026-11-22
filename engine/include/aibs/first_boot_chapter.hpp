#pragma once
#include <aibs/durable_first_boot.hpp>

namespace aibs {
enum class FirstBootChapterAction {
 inspect_fault,set_isolation,repair_fault,connect_bypass,disconnect_bypass,
 open_door,close_door,arrive_hub,enter_pencil,depart_hub,help_caretaker,decline_caretaker,connect_lamp,recover_arc,collect_probe,sample_supply,sample_path,test_feed,commission_bench,collect_relay_part
};
enum class FirstBootArcPhase { dormant,telegraph,arc,cooldown };
struct FirstBootChapterHazardSample {
 FirstBootArcPhase phase=FirstBootArcPhase::dormant;
 std::string activation_id;
 std::uint64_t active_tick=0,activation_tick=0,cycle=0;
 bool recovery_available=false;
};
// Evidence supplied by the authoritative native controller/clock, never by an
// untrusted SDK/AI batch proposal. Retained contacts are valid only in their
// current activation; discard them when that activation changes or is disabled.
struct FirstBootChapterActor {
 Vec3 previous_feet{},feet{};
 bool grounded=true,inspection_mode=false;
 float radius=.35f,height=1.8f;
 std::uint64_t active_tick=0;
 FirstBootChapterHazardSample hazard{};
};
struct FirstBootChapterCommand {
 FirstBootChapterAction action=FirstBootChapterAction::inspect_fault;
 std::string target_id,relay_id,operation_id;
 bool enabled=true; // set_isolation's requested switch state.
};
struct FirstBootChapterIds { std::string fault,main_door,service_door,pencil_door,progress,npc_quest; };
std::vector<ComponentSchema> first_boot_chapter_schemas(); // Node v1 + four explicit chapter types.
// Stage full chapter geometry and a supported clear return before an explicit
// registry extension; never edits hardware, heads or history and emits no events.
// New authored baseline remains Node-only until the actual install is published.
void first_boot_chapter_preflight(const GameplayStoreRecovery& before);
GameplayStoreBaseline first_boot_chapter_baseline(const CreatorSession& source);
std::vector<ComponentRecord> first_boot_chapter_additions(const GameplayStoreRecovery& before);
std::optional<GameplayChangeBatch> first_boot_chapter_install(const GameplayStoreRecovery& before,std::string operation_id={});
FirstBootChapterIds first_boot_chapter_ids(const GameplayStoreRecovery& snapshot);
SceneSnapshot first_boot_chapter_scene(const GameplayStoreRecovery& snapshot);
PlayerController first_boot_chapter_player(const GameplayStoreRecovery& snapshot);
void first_boot_chapter_validate(const GameplayStoreRecovery& snapshot);
Vec3 first_boot_chapter_safe_return(const GameplayStoreRecovery& snapshot);
std::string first_boot_chapter_region(const GameplayStoreRecovery& snapshot,Vec3 feet);
std::optional<GameplayChangeBatch> first_boot_chapter_action(const GameplayStoreRecovery& before,
 const FirstBootChapterCommand& command,const FirstBootChapterActor& actor);
void first_boot_chapter_rules(const GameplayStoreRecovery& before,const GameplayStoreRecovery& after,
 const GameplayChangeBatch& batch,const FirstBootChapterActor& actor,const std::set<std::string>& historical_ids={});
// Chapter Node repair/dismantle requires body-centre distance <=3m from an
// actual collision part. Inspector actions reject; relay placement keeps its
// existing sandbox range. The original Node-only M2 rules remain unchanged.
// Current local danger outranks optional conversation/room reminders. A cached
// NPC target is contextual only within interaction reach of the actual body.
// These authored cues do not create or rewrite committed/source memory.
std::string first_boot_chapter_hint(const GameplayStoreRecovery& snapshot,const FirstBootChapterActor& actor,std::string target_id={});
// Independent fixed-60-Hz active-play clock; pause discards catch-up. New fault
// activation/reload starts a full warning. Acknowledge only after publishing an
// actual recovery outcome, so waiting/retrying never writes per-frame records.
class FirstBootChapterClock {
public:
 unsigned advance(double seconds,bool active=true);
 std::uint64_t tick() const noexcept { return tick_; }
 FirstBootChapterHazardSample sample(const GameplayStoreRecovery& snapshot);
 void acknowledge_recovery(const FirstBootChapterHazardSample& sample) noexcept;
private:
 double accumulator_=0;
 std::uint64_t tick_=0,activation_tick_=0;
 bool observed_active_=false;
 std::optional<GameplayScope> scope_;
 std::string activation_id_;
 std::optional<std::pair<std::uint64_t,std::uint64_t>> recovered_;
};
bool first_boot_chapter_hazard_contact(const GameplayStoreRecovery& snapshot,const FirstBootChapterActor& actor);
SceneMesh first_boot_chapter_hazard_mesh(const GameplayStoreRecovery& snapshot,const FirstBootChapterHazardSample& sample);
}
