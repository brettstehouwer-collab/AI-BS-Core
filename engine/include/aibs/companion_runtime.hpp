#pragma once
#include <aibs/first_boot_content.hpp>

namespace aibs {
struct CompanionActor {
 GuideTarget target;
 bool inspection_mode=false,paused=false;
 std::uint64_t active_tick=0;
};
struct CompanionRuntimeState {
 GuideIntentRecord saved;
 std::optional<GuideState> guide;
 bool recall_required=false;
 std::uint64_t scene_revision=0;
};
class CompanionRuntime;
class PreparedCompanionChoice {
public:
 ~PreparedCompanionChoice();
 PreparedCompanionChoice(const PreparedCompanionChoice&)=delete;
 PreparedCompanionChoice& operator=(const PreparedCompanionChoice&)=delete;
 const GameplayChangeBatch& batch()const noexcept;
private:
 friend class CompanionRuntime;
 struct Data;
 std::unique_ptr<Data> data_;
 explicit PreparedCompanionChoice(std::unique_ptr<Data>);
};
// Single native owner. Motion is ephemeral; only explicit choices create a
// companion batch. Adam never enters BS's collision scene or edits BS's state.
class CompanionRuntime {
public:
 CompanionRuntime(const GameplayStoreRecovery&,const FirstBootContent&);
 ~CompanionRuntime();
 CompanionRuntime(const CompanionRuntime&)=delete;
 CompanionRuntime& operator=(const CompanionRuntime&)=delete;
 CompanionRuntimeState state()const;
 GuideState advance(GuideTarget,double elapsed);
 void suspend()noexcept;
 // Call after accepted BS changes. An embedded/unsupported guide suspends and
 // requires explicit Recall; it never rejects or reverts the BS edit/save.
 void synchronize(const GameplayStoreRecovery&);
 // Null means a repeated Follow/Wait choice with no new outcome. Invalid or
 // unavailable choices throw without changing motion, intent or the world.
 std::unique_ptr<PreparedCompanionChoice> prepare_choice(const GameplayStoreRecovery&,
  CompanionAction,const CompanionActor&,std::span<const Vec3> recall_candidates={},
  std::string operation_id={})const;
 void validate_choice(const PreparedCompanionChoice&,const GameplayStoreRecovery& before,
  const GameplayStoreRecovery& after,const GameplayChangeBatch&,const CompanionActor&)const;
 bool ready(const PreparedCompanionChoice&)const noexcept;
 // Check ready, validate/prepare and admit to GameplayWorld first. No movement
 // or synchronization may intervene. This final activation allocates nothing.
 // A stale choice returns false and preserves the runtime.
 bool publish(std::unique_ptr<PreparedCompanionChoice>)noexcept;
 std::string hint()const;
private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
};
}
