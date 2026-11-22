#pragma once
#include <aibs/character_scene.hpp>
#include <aibs/guide_controller.hpp>
#include <optional>

namespace aibs {
// Temporary articulated figure. This is neither Adam's likeness nor a family
// reference asset; it proves the indexed character and authored motion route.
CharacterMesh make_guide_placeholder();
enum class GuidePresentationClip { idle,walk,catchup,guidance };

// The immutable resource must outlive its presenter. Movement remains owned by
// CompanionRuntime. This object only samples fixed-storage visual pose data.
class GuidePresentation {
public:
 explicit GuidePresentation(const CharacterMesh&);
 GuidePresentation(CharacterMesh&&)=delete;
 // Missing/invalid/Recall-required motion hides the figure. Anchor validity
 // belongs to CompanionRuntime; a transient live-body grounded flag does not
 // control visibility. Pausing freezes the last visible valid instance;
 // no pose, clock or bones are persisted.
 std::optional<CharacterInstance> sample(const std::optional<GuideState>&,
  double elapsed,bool paused=false,bool recall_required=false,bool guidance=false);
 void reset()noexcept;
 double animation_seconds()const noexcept{return seconds_;}
 float yaw()const noexcept{return yaw_;}
 GuidePresentationClip clip()const noexcept{return clip_;}
 double transition_progress()const noexcept{return transition_duration_>0?std::min(1.0,transition_elapsed_/transition_duration_):1.0;}
 bool is_transitioning()const noexcept{return transition_elapsed_<transition_duration_;}
private:
 const CharacterMesh* mesh_;
 std::optional<CharacterInstance> previous_;
 GuidePresentationClip clip_=GuidePresentationClip::idle;
 GuidePresentationClip previous_clip_=GuidePresentationClip::idle;
 double seconds_=0;
 double previous_seconds_=0;
 double transition_elapsed_=1.0;
 double transition_duration_=0.20;
 float yaw_=0;
 bool facing_initialized_=false;
};
}
