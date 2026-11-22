#include <aibs/physics.hpp>
#include <Jolt/Jolt.h>
#include <Jolt/RegisterTypes.h>
#include <Jolt/Core/Factory.h>
#include <Jolt/Core/TempAllocator.h>
#include <Jolt/Physics/PhysicsSystem.h>
#include <Jolt/Physics/Body/BodyCreationSettings.h>
#include <Jolt/Physics/Character/CharacterVirtual.h>
#include <Jolt/Physics/Collision/CollisionCollectorImpl.h>
#include <Jolt/Physics/Collision/CollideShape.h>
#include <Jolt/Physics/Collision/CollidePointResult.h>
#include <Jolt/Physics/Collision/CastResult.h>
#include <Jolt/Physics/Collision/RayCast.h>
#include <Jolt/Physics/Collision/ShapeCast.h>
#include <Jolt/Physics/Collision/Shape/BoxShape.h>
#include <Jolt/Physics/Collision/Shape/CapsuleShape.h>
#include <Jolt/Physics/Collision/Shape/SphereShape.h>
#include <Jolt/Physics/Collision/Shape/RotatedTranslatedShape.h>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace aibs {
namespace {
constexpr double tick = 1.0 / 60.0;
bool finite(Vec3 p) { return std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z); }
JPH::Vec3 vec(Vec3 p) { return {p.x,p.y,p.z}; }
Vec3 vec(JPH::Vec3Arg p) { return {p.GetX(),p.GetY(),p.GetZ()}; }
struct Runtime {
 Runtime() { JPH::RegisterDefaultAllocator(); JPH::Factory::sInstance = new JPH::Factory(); JPH::RegisterTypes(); }
 ~Runtime() { JPH::UnregisterTypes(); delete JPH::Factory::sInstance; JPH::Factory::sInstance = nullptr; }
};
void initialize() { static Runtime runtime; }
class Layers final : public JPH::BroadPhaseLayerInterface {
public:
 JPH::uint GetNumBroadPhaseLayers() const override { return 1; }
 JPH::BroadPhaseLayer GetBroadPhaseLayer(JPH::ObjectLayer) const override { return JPH::BroadPhaseLayer(0); }
#if defined(JPH_EXTERNAL_PROFILE) || defined(JPH_PROFILE_ENABLED)
 const char* GetBroadPhaseLayerName(JPH::BroadPhaseLayer) const override { return "Static world"; }
#endif
};
class BroadFilter final : public JPH::ObjectVsBroadPhaseLayerFilter {
 bool ShouldCollide(JPH::ObjectLayer, JPH::BroadPhaseLayer) const override { return true; }
};
class PairFilter final : public JPH::ObjectLayerPairFilter {
 bool ShouldCollide(JPH::ObjectLayer, JPH::ObjectLayer) const override { return true; }
};
void validate(CharacterSettings s) {
 if (!std::isfinite(s.radius) || !std::isfinite(s.height) || !std::isfinite(s.walk_speed) || !std::isfinite(s.sprint_speed) ||
     !std::isfinite(s.jump_speed) || !std::isfinite(s.gravity) || !std::isfinite(s.step_height) || !std::isfinite(s.max_slope_degrees) ||
     s.radius < .05f || s.radius > 5 || s.height < 2*s.radius || s.height > 10 || s.walk_speed < 0 || s.walk_speed > 100 ||
     s.sprint_speed < s.walk_speed || s.sprint_speed > 100 || s.jump_speed < 0 || s.jump_speed > 30 || s.gravity <= 0 || s.gravity > 100 ||
     s.step_height < 0 || s.step_height > s.height*.5f || s.max_slope_degrees < 0 || s.max_slope_degrees >= 89)
  throw std::invalid_argument("Invalid capsule character settings");
}
}
struct GroundedCharacter::Impl {
 CharacterSettings settings;
 CharacterState state;
 double accumulator = 0;
 bool jump_pending = false, jump_held = false;
 Layers layers;
 BroadFilter broad;
 PairFilter pairs;
 JPH::PhysicsSystem system;
 JPH::TempAllocatorImpl allocator{4*1024*1024};
 JPH::Ref<JPH::CharacterVirtual> character;
 Impl(const SceneSnapshot& scene, CharacterSettings config, CharacterState initial) : settings(config), state(initial) {
  (void)mesh_from_snapshot(scene); // Reuse the bounded scene contract before any bodies publish.
  system.Init(10000,0,10000,10000,layers,broad,pairs);
  auto& bodies=system.GetBodyInterface();
  for (const auto& object:scene.objects) {
   JPH::RefConst<JPH::Shape> shape=new JPH::BoxShape(vec(object.half_extent),std::min({.02f,object.half_extent.x,object.half_extent.y,object.half_extent.z}));
   const auto q=object.rotation;
   const JPH::Quat rotation=JPH::Quat(q.x,q.y,q.z,q.w).Normalized();
   const JPH::BodyCreationSettings body(shape,vec(object.center),rotation,JPH::EMotionType::Static,0);
   if (bodies.CreateAndAddBody(body,JPH::EActivation::DontActivate).IsInvalid()) throw std::runtime_error("Physics collider budget exhausted");
  }
  system.OptimizeBroadPhase();
  JPH::Ref<JPH::CharacterVirtualSettings> config_jolt=new JPH::CharacterVirtualSettings();
  JPH::RefConst<JPH::Shape> capsule=new JPH::CapsuleShape(settings.height*.5f-settings.radius,settings.radius);
  config_jolt->mShape=new JPH::RotatedTranslatedShape({0,settings.height*.5f,0},JPH::Quat::sIdentity(),capsule);
  config_jolt->mMaxSlopeAngle=JPH::DegreesToRadians(settings.max_slope_degrees);
  config_jolt->mSupportingVolume=JPH::Plane(JPH::Vec3::sAxisY(),-settings.radius);
  character=new JPH::CharacterVirtual(config_jolt,vec(state.feet),JPH::Quat::sIdentity(),0,&system);
  character->SetLinearVelocity(vec(state.velocity));
  if (embedded()) throw std::invalid_argument("Collider update would overlap BS's capsule; choose another placement");
  refresh();
 }
 bool embedded() const {
  JPH::ClosestHitCollisionCollector<JPH::CollideShapeCollector> hits;
  system.GetNarrowPhaseQuery().CollideShape(character->GetShape(),JPH::Vec3::sOne(),character->GetCenterOfMassTransform(),{},JPH::RVec3::sZero(),hits);
  return hits.HadHit() && hits.mHit.mPenetrationDepth>.025f;
 }
 void refresh() {
  character->RefreshContacts(system.GetDefaultBroadPhaseLayerFilter(0),system.GetDefaultLayerFilter(0),{},{},allocator);
  state.feet=vec(character->GetPosition()); state.velocity=vec(character->GetLinearVelocity());
  state.grounded=character->GetGroundState()==JPH::CharacterBase::EGroundState::OnGround;
 }
 void step(CharacterInput input) {
  auto velocity=character->GetLinearVelocity();
  if (state.grounded && velocity.GetY()<.1f) velocity.SetY(jump_pending?settings.jump_speed:0);
  velocity.SetY(velocity.GetY()-settings.gravity*static_cast<float>(tick));
  const auto length=std::hypot(input.move.x,input.move.z);
  const auto scale=(input.sprint?settings.sprint_speed:settings.walk_speed)/std::max(1.0f,length);
  velocity.SetX(input.move.x*scale); velocity.SetZ(input.move.z*scale);
  jump_pending=false;
  character->SetLinearVelocity(velocity);
  JPH::CharacterVirtual::ExtendedUpdateSettings update;
  update.mWalkStairsStepUp={0,settings.step_height,0};
  update.mStickToFloorStepDown={0,-settings.step_height,0};
  character->ExtendedUpdate(static_cast<float>(tick),{0,-settings.gravity,0},update,
   system.GetDefaultBroadPhaseLayerFilter(0),system.GetDefaultLayerFilter(0),{},{},allocator);
  state.feet=vec(character->GetPosition()); state.velocity=vec(character->GetLinearVelocity());
  state.grounded=character->GetGroundState()==JPH::CharacterBase::EGroundState::OnGround;
  ++state.ticks;
 }
};
GroundedCharacter::GroundedCharacter(const SceneSnapshot& scene,Vec3 spawn,CharacterSettings settings) {
 validate(settings); if (!finite(spawn)) throw std::invalid_argument("Nonfinite character spawn");
 initialize(); impl_=std::make_unique<Impl>(scene,settings,CharacterState{spawn});
}
GroundedCharacter::~GroundedCharacter()=default;
GroundedCharacter::GroundedCharacter(GroundedCharacter&&) noexcept=default;
GroundedCharacter& GroundedCharacter::operator=(GroundedCharacter&&) noexcept=default;
CharacterState GroundedCharacter::advance(CharacterInput input,double elapsed) {
 if (!finite(input.move) || !std::isfinite(elapsed) || elapsed<0) throw std::invalid_argument("Invalid movement input or elapsed time");
 auto& p=*impl_;
 if (input.jump && !p.jump_held) p.jump_pending=true;
 p.jump_held=input.jump;
 const auto accepted=std::min(elapsed,8*tick);
 p.state.dropped_seconds+=elapsed-accepted;
 p.accumulator+=accepted;
 int steps=0;
 while (p.accumulator+1e-12>=tick && steps<8) { p.step(input); p.accumulator=std::max(0.0,p.accumulator-tick); ++steps; }
 return p.state;
}
CharacterState GroundedCharacter::state() const { return impl_->state; }
void GroundedCharacter::suspend() noexcept {
 impl_->accumulator=0; impl_->jump_pending=false; impl_->jump_held=false;
}
void GroundedCharacter::reset(Vec3 feet) {
 if (!finite(feet)) throw std::invalid_argument("Nonfinite character reset");
 const auto old=impl_->character->GetPosition();
 impl_->character->SetPosition(vec(feet));
 if (impl_->embedded()) { impl_->character->SetPosition(old); throw std::invalid_argument("Character reset overlaps solid geometry"); }
 impl_->character->SetLinearVelocity(JPH::Vec3::sZero());
 impl_->state.feet=feet; impl_->state.velocity={}; impl_->accumulator=0; impl_->jump_pending=false; impl_->jump_held=false;
 impl_->refresh();
}
void GroundedCharacter::set_scene(const SceneSnapshot& scene) {
 auto candidate=std::make_unique<Impl>(scene,impl_->settings,impl_->state);
 candidate->accumulator=impl_->accumulator; candidate->jump_pending=impl_->jump_pending; candidate->jump_held=impl_->jump_held;
 impl_.swap(candidate);
}
Vec3 GroundedCharacter::camera_position(Vec3 target,Vec3 desired,float padding) const {
 const auto bounded=[](Vec3 p) { return finite(p) && std::max({std::abs(p.x),std::abs(p.y),std::abs(p.z)})<=1000000; };
 if (!bounded(target) || !bounded(desired) || !std::isfinite(padding) || padding<0 || padding>10)
  throw std::invalid_argument("Camera coordinates or radius exceed finite query bounds");
 const auto& query=impl_->system.GetNarrowPhaseQuery();
 const auto direction=vec(desired)-vec(target);
 const auto distance=direction.Length();
 float hit_fraction=1;
 if (padding==0) {
  JPH::AnyHitCollisionCollector<JPH::CollidePointCollector> occupied;
  query.CollidePoint(vec(target),occupied);
  if (occupied.HadHit()) throw std::invalid_argument("Camera anchor point is inside solid geometry");
  if (distance<1e-6f) return target;
  JPH::RayCastResult hit;
  if (!query.CastRay(JPH::RRayCast(vec(target),direction),hit)) return desired;
  hit_fraction=hit.mFraction;
 } else {
  JPH::RefConst<JPH::Shape> sphere=new JPH::SphereShape(padding);
  const auto transform=JPH::RMat44::sTranslation(vec(target));
  JPH::ClosestHitCollisionCollector<JPH::CollideShapeCollector> occupied;
  query.CollideShape(sphere,JPH::Vec3::sOne(),transform,{},vec(target),occupied);
  if (occupied.HadHit() && occupied.mHit.mPenetrationDepth>1e-5f)
   throw std::invalid_argument("Camera anchor sphere overlaps solid geometry");
  if (distance<1e-6f) return target;
  JPH::ShapeCastSettings settings;
  settings.mBackFaceModeConvex=JPH::EBackFaceMode::CollideWithBackFaces;
  settings.mUseShrunkenShapeAndConvexRadius=true;
  JPH::ClosestHitCollisionCollector<JPH::CastShapeCollector> hit;
  query.CastShape(JPH::RShapeCast(sphere,JPH::Vec3::sOne(),transform,direction),settings,vec(target),hit);
  if (!hit.HadHit()) return desired;
  hit_fraction=hit.mHit.mFraction;
 }
 const auto fraction=std::max(0.0f,hit_fraction-.01f/distance);
 return vec(vec(target)+fraction*direction);
}
}
