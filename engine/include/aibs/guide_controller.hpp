#pragma once
#include <aibs/physics.hpp>
#include <initializer_list>
#include <map>
#include <span>

namespace aibs {
enum class GuideIntent { follow,wait };
enum class GuideActivity { following,near_player,waiting,blocked };
struct GuideRouteNode {std::string id;Vec3 feet;};
struct GuideRouteEdge {std::string from,to,door;bool bidirectional=true;};
struct GuideRouteGraph {std::vector<GuideRouteNode> nodes;std::vector<GuideRouteEdge> edges;};
// Durable intent only: no bone poses, footsteps, trail, tick or animation state.
struct GuideIntentRecord {GuideIntent intent=GuideIntent::follow;Vec3 waiting_anchor;};
// Supply from the authoritative BS controller, not an AI/SDK proposal.
struct GuideTarget {Vec3 feet;bool grounded=true;std::uint64_t scene_revision=0;};
struct GuideSettings {
 float radius=.25f,height=1.8f,walk_speed=3,catchup_speed=5;
 float follow_distance=1.8f,catchup_distance=6,graph_attach_distance=3;
 float recall_min_distance=.9f,recall_max_distance=4;
};
struct GuideState {
 CharacterState character;
 GuideIntent intent=GuideIntent::follow;
 GuideActivity activity=GuideActivity::blocked;
 Vec3 destination;
 std::size_t trail_points=0;
 double dropped_seconds=0;
};
// Single-owner, noncombat companion. Its GroundedCharacter is a separate
// collision/query world and never adds a body to BS's physics world. This class
// has no gameplay/store access and cannot repair, build or advance objectives.
class GuideController {
public:
 GuideController(const SceneSnapshot&,Vec3 spawn,GuideRouteGraph,GuideSettings={});
 ~GuideController();
 GuideController(const GuideController&)=delete;
 GuideController& operator=(const GuideController&)=delete;
 GuideController(GuideController&&) noexcept;
 GuideController& operator=(GuideController&&) noexcept;
 // Missing gate IDs are closed. Doors must also be reflected in collision
 // geometry; physical checks prevent stale open metadata crossing a solid door.
 void set_doors(std::map<std::string,bool>);
 // Atomic collision replacement. Invalid geometry/support preserves all state.
 // Changed collision geometry discards the runtime trail. Identical ordered
 // collider transforms adopt the validated scene revision while preserving the
 // live body, contacts, velocity, route, fractional tick and walkable trail.
 void set_scene(const SceneSnapshot&);
 std::uint64_t scene_revision() const noexcept;
 void set_intent(GuideIntent);
 GuideIntentRecord saved_intent() const;
 void restore_intent(const GuideIntentRecord&);
 // Explicit rematerialization only: test at most sixteen supplied nearby
 // candidates for support, clearance and personal space; failure changes nothing.
 bool recall(Vec3 player_feet,std::span<const Vec3> candidates);
 bool recall(Vec3 player_feet,std::initializer_list<Vec3> candidates){return recall(player_feet,std::span<const Vec3>(candidates.begin(),candidates.size()));}
 // If a BS edit embeds the old guide pose, do not veto that edit or teleport
 // automatically. Stop stepping the stale guide; explicit Recall can atomically
 // adopt the latest collision snapshot and a validated new pose here.
 bool recall(const SceneSnapshot&,Vec3 player_feet,std::span<const Vec3> candidates);
 bool recall(const SceneSnapshot& scene,Vec3 player_feet,std::initializer_list<Vec3> candidates){return recall(scene,player_feet,std::span<const Vec3>(candidates.begin(),candidates.size()));}
 // Fixed 60Hz, max four ticks per call, excess reported in dropped_seconds.
 // Actual grounded BS samples supplement authored routes. Discontinuities,
 // ungrounded samples and changed collision geometry break the trail, never
 // bridge a fall. Semantic-only scene revisions preserve validated walkability.
 GuideState advance(GuideTarget,double elapsed);
 GuideState state() const;
 void suspend() noexcept;
private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
};
}
