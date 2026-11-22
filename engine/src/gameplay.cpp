#include <aibs/gameplay.hpp>
#include <algorithm>
#include <bit>
#include <cmath>
#include <set>
#include <stdexcept>
#include <type_traits>

namespace aibs {
namespace {
void require(bool value, const char* message) { if (!value) throw std::invalid_argument(message); }
bool text(const std::string& value, std::size_t maximum=256) {
 return !value.empty() && value.size()<=maximum && value.find('\0')==std::string::npos;
}
std::uint32_t family_version(std::size_t index) { return index==6?3u:index>=4?2u:1u; }
bool valid_companion_intent(const CompanionIntentValue& value) {
 return std::isfinite(value.anchor_x)&&std::abs(value.anchor_x)<=1e6&&
        std::isfinite(value.anchor_y)&&std::abs(value.anchor_y)<=1e6&&
        std::isfinite(value.anchor_z)&&std::abs(value.anchor_z)<=1e6;
}
void valid_scope(const GameplayScope& scope) {
 require(text(scope.project_id) && text(scope.branch_id) && is_uuid(scope.world_id) && is_uuid(scope.timeline_id), "Invalid gameplay scope");
 require(scope.context>=GameplayContext::authoring && scope.context<=GameplayContext::published_historical_lore,"Unsupported gameplay context");
}
const std::string& payload_target(const SemanticPayload& payload) {
 return std::visit([](const auto& value) -> const std::string& {
  using T=std::decay_t<decltype(value)>;
  if constexpr(std::is_same_v<T,RouteOutcome>) return value.route_id;
  else if constexpr(std::is_same_v<T,HazardOutcome>) return value.hazard_id;
  else if constexpr(std::is_same_v<T,QuestOutcome>) return value.quest_id;
  else return value.entity_id;
 },payload);
}
}
const char* semantic_event_type(const SemanticEvent& event) noexcept {
 switch(event.payload.index()) {
 case 0: return "repair.outcome";
 case 1: return "construction.outcome";
 case 2: return "route.outcome";
 case 3: return "hazard.outcome";
 case 4: return "mechanism.outcome";
 case 5: return "quest.outcome";
 case 6: return "companion.outcome";
 default: return "unsupported";
 }
}
bool gameplay_batch_exact(const GameplayChangeBatch& left,const GameplayChangeBatch& right) {
 if(!(left==right)) return false;
 const auto same_bits=[](double a,double b) { return std::bit_cast<std::uint64_t>(a)==std::bit_cast<std::uint64_t>(b); };
 for(std::size_t i=0;i<left.deltas.size();++i) {
  const auto& fields=right.deltas[i].component.fields;
  for(const auto& [key,value]:left.deltas[i].component.fields)
   if(const auto* number=std::get_if<double>(&value)) if(!same_bits(*number,std::get<double>(fields.at(key)))) return false;
 }
 for(std::size_t i=0;i<left.events.size();++i) {
  if(const auto* repair=std::get_if<RepairOutcome>(&left.events[i].payload)) {
   const auto& other=std::get<RepairOutcome>(right.events[i].payload);
   if(!same_bits(repair->before,other.before)||!same_bits(repair->after,other.after)) return false;
  }
  if(const auto* companion=std::get_if<CompanionOutcome>(&left.events[i].payload)) {
   const auto& other=std::get<CompanionOutcome>(right.events[i].payload);
   for(const auto& pair:{std::pair{&companion->before,&other.before},std::pair{&companion->after,&other.after}})
    if(!same_bits(pair.first->anchor_x,pair.second->anchor_x)||!same_bits(pair.first->anchor_y,pair.second->anchor_y)||
       !same_bits(pair.first->anchor_z,pair.second->anchor_z)) return false;
  }
 }
 return true;
}
struct GameplayAdmission::Impl {
 struct Receipt { std::shared_ptr<const GameplayChangeBatch> batch; std::size_t bytes=0; bool visible=false,durable=false; };
 GameplayScope scope;
 GameplayLimits limits;
 GameplayAdmissionState state;
 std::map<std::pair<std::string,std::uint32_t>,ComponentSchema> schemas;
 std::map<std::string,Receipt> receipts;
 std::vector<std::string> order;
 std::set<std::string> event_ids;
 bool reserving = false;
 Impl(GameplayScope owner,std::vector<ComponentSchema> definitions,GameplayLimits budgets,std::uint64_t revision,std::uint64_t sequence)
  : scope(std::move(owner)),limits(budgets) {
  valid_scope(scope);
  require(limits.pending_batches>0 && limits.pending_batches<=256 && limits.receipts>0 && limits.receipts<=4096 &&
          limits.pending_bytes>0 && limits.pending_bytes<=64*1024*1024 && limits.receipt_bytes>0 && limits.receipt_bytes<=64*1024*1024,
          "Gameplay limits must be positive and within hard bounds");
  require(!definitions.empty() && definitions.size()<=128,"Gameplay requires a bounded component schema registry");
  for(auto& definition:definitions) {
   require(text(definition.type_id) && definition.version>0 && !definition.fields.empty() && definition.fields.size()<=64,"Invalid component schema");
   std::set<std::string> fields;
   for(const auto& field:definition.fields) {
    require(text(field.id) && fields.insert(field.id).second && field.kind>=GameplayValueKind::boolean && field.kind<=GameplayValueKind::text,
            "Invalid or duplicate component field rule");
    require(std::isfinite(field.minimum) && std::isfinite(field.maximum) && field.minimum<=field.maximum,"Invalid component numeric range");
   }
   const auto key=std::make_pair(definition.type_id,definition.version);
   require(schemas.emplace(key,std::move(definition)).second,"Duplicate component type/version");
  }
  state.accepted_revision=state.visible_revision=state.durable_revision=revision;
  state.accepted_sequence=state.visible_sequence=state.durable_sequence=sequence;
 }
 std::size_t validate(const GameplayChangeBatch& batch,const GameplayTargetValidator& targets) const {
  std::uint32_t version=1;for(const auto& event:batch.events)version=std::max(version,family_version(event.payload.index()));
  require(batch.schema_version==version && batch.scope==scope && text(batch.operation_id),"Unsupported or noncanonical batch version, scope or operation ID");
  require(state.accepted_revision<std::numeric_limits<std::uint64_t>::max() && batch.expected_revision==state.accepted_revision &&
          batch.revision==state.accepted_revision+1,"Gameplay revision conflict");
  require(batch.deltas.size()<=256 && !batch.events.empty() && batch.events.size()<=64,"Batch requires 1..64 events and at most 256 component deltas");
  require(static_cast<bool>(targets),"Caller UUID target validator is required");
  std::size_t bytes=512+batch.operation_id.size()+scope.project_id.size()+scope.branch_id.size()+scope.world_id.size()+scope.timeline_id.size();
  std::set<std::string> checked_targets,delta_entities,ids;
  auto target=[&](const std::string& id) {
   require(is_uuid(id),"Gameplay target requires a persistent UUID");
   if(checked_targets.insert(id).second) require(targets(id),"Caller rejected gameplay UUID target");
  };
  std::set<std::pair<std::string,std::string>> components;
  for(const auto& delta:batch.deltas) {
   const auto& value=delta.component;
   target(value.entity_id); delta_entities.insert(value.entity_id);
   require(text(value.type_id) && value.version>0 && value.fields.size()<=64,"Invalid component record");
   require(components.emplace(value.entity_id,value.type_id).second,"Duplicate component delta");
   const auto schema=schemas.find({value.type_id,value.version});
   require(schema!=schemas.end(),"Unknown component type/version requires migration");
   require(delta.action==ComponentAction::upsert || delta.action==ComponentAction::erase,"Unsupported component delta action");
   bytes+=256+value.entity_id.size()+value.type_id.size();
   if(delta.action==ComponentAction::erase) { require(value.fields.empty(),"Erased component must not carry replacement fields"); continue; }
   for(const auto& rule:schema->second.fields) require(!rule.required || value.fields.contains(rule.id),"Missing required component field");
   for(const auto& [id,field]:value.fields) {
    const auto rule=std::find_if(schema->second.fields.begin(),schema->second.fields.end(),[&](const auto& candidate){return candidate.id==id;});
    require(rule!=schema->second.fields.end() && !field.valueless_by_exception() && field.index()==static_cast<std::size_t>(rule->kind),
            "Unknown component field or mismatched value type");
    bytes+=128+id.size();
    if(const auto* number=std::get_if<double>(&field)) require(std::isfinite(*number) && *number>=rule->minimum && *number<=rule->maximum,"Component number outside finite bounds");
    if(const auto* string=std::get_if<std::string>(&field)) { require(string->size()<=4096,"Component text exceeds byte bound"); bytes+=string->size(); }
   }
  }
  auto sequence=state.accepted_sequence;
  for(const auto& event:batch.events) {
   require(is_uuid(event.event_id) && ids.insert(event.event_id).second && !event_ids.contains(event.event_id),"Invalid or duplicate semantic event identity");
   require(event.payload_version==family_version(event.payload.index()) && event.scope==scope && event.operation_id==batch.operation_id && event.source_revision==batch.revision,
           "Semantic event version, scope, operation or source revision mismatch");
   require(sequence<std::numeric_limits<std::uint64_t>::max() && event.sequence==sequence+1,"Semantic sequence gap or overflow"); ++sequence;
   require(event.result_phase==GameplayPhase::accepted,"Only the owner acknowledgements can claim visible or durable results");
   require(event.provenance.kind>=GameplayProvenance::gameplay_rule && event.provenance.kind<=GameplayProvenance::authored_source &&
           text(event.provenance.source_id,4096),"Semantic provenance requires a known kind and source reference");
   require(!event.subject_ids.empty() && event.subject_ids.size()<=64 && !event.payload.valueless_by_exception(),"Invalid semantic subjects or payload");
   std::set<std::string> subjects;
   for(const auto& subject:event.subject_ids) { target(subject); require(subjects.insert(subject).second,"Duplicate semantic subject"); }
   const auto& primary=payload_target(event.payload);
   require(subjects.contains(primary),"Semantic payload target is not a validated subject");
   if(const auto* repair=std::get_if<RepairOutcome>(&event.payload)) {
    require(std::isfinite(repair->before) && std::isfinite(repair->after) && repair->before>=0 && repair->after>=repair->before && repair->after<=100,
            "Repair outcome must contain finite nondecreasing capacity within 0..100");
   }
   if(const auto* mechanism=std::get_if<MechanismOutcome>(&event.payload)) {
    require(text(mechanism->attribute_id) && mechanism->before!=mechanism->after,"Mechanism outcome requires a bounded attribute and changed state");
    bytes+=mechanism->attribute_id.size();
   }
   if(const auto* quest=std::get_if<QuestOutcome>(&event.payload)) {
    const auto valid_state=[](QuestState value){return value>=QuestState::unavailable && value<=QuestState::completed;};
    const auto valid_step=[](const std::string& value){return value.size()<=256 && value.find('\0')==std::string::npos;};
    require(valid_state(quest->before) && valid_state(quest->after) && valid_step(quest->before_step) && valid_step(quest->after_step) &&
            (quest->before!=quest->after || quest->before_step!=quest->after_step),"Quest outcome requires known states, bounded steps and a real transition");
    bytes+=quest->before_step.size()+quest->after_step.size();
   }
   if(const auto* companion=std::get_if<CompanionOutcome>(&event.payload)) {
    require(companion->action>=CompanionAction::follow&&companion->action<=CompanionAction::recall&&
            valid_companion_intent(companion->before)&&valid_companion_intent(companion->after),
            "Companion outcome requires a known action and finite anchors within world bounds");
    require((companion->action!=CompanionAction::follow||companion->after.follow)&&
            (companion->action!=CompanionAction::wait||!companion->after.follow)&&
            (companion->action!=CompanionAction::recall||companion->before.follow==companion->after.follow),
            "Companion action does not match its explicit saved intent");
   }
   if(std::holds_alternative<RepairOutcome>(event.payload) || std::holds_alternative<ConstructionOutcome>(event.payload) || event.payload.index()>=4)
    require(delta_entities.contains(primary),"Repair, construction, mechanism, quest or companion outcome requires a matching world delta in the same batch");
   bytes+=512+event.event_id.size()+event.operation_id.size()+event.provenance.source_id.size()+primary.size()+
          event.scope.project_id.size()+event.scope.branch_id.size()+event.scope.world_id.size()+event.scope.timeline_id.size();
   for(const auto& subject:event.subject_ids) bytes+=64+subject.size();
  }
  return bytes;
 }
 std::shared_ptr<const GameplayChangeBatch> next(bool durability) const {
  for(const auto& id:order) {
   const auto& receipt=receipts.at(id);
   if(durability && !receipt.durable) return receipt.visible?receipt.batch:nullptr;
   if(!durability && !receipt.visible) return receipt.batch;
  }
  return {};
 }
};
GameplayAdmission::GameplayAdmission(GameplayScope scope,std::vector<ComponentSchema> schemas,GameplayLimits limits,
                                     std::uint64_t revision,std::uint64_t sequence)
 : impl_(std::make_unique<Impl>(std::move(scope),std::move(schemas),limits,revision,sequence)) {}
GameplayAdmission::~GameplayAdmission()=default;
AdmissionResult GameplayAdmission::reserve(const GameplayChangeBatch& batch,const GameplayTargetValidator& targets) {
 auto& p=*impl_;
 if(p.reserving) return {AdmissionStatus::rejected,"Reentrant gameplay mutation is not allowed",{}};
 struct MutationGuard { bool& value; ~MutationGuard() { value=false; } } guard{p.reserving};
 p.reserving=true;
 try {
  require(text(batch.operation_id),"Invalid gameplay operation ID");
  if(const auto found=p.receipts.find(batch.operation_id);found!=p.receipts.end()) {
   if(gameplay_batch_exact(*found->second.batch,batch)) return {AdmissionStatus::retry,"Exact previously admitted request",found->second.batch};
   return {AdmissionStatus::rejected,"Operation ID was already used for different content",{}};
  }
  require(static_cast<bool>(targets),"Caller UUID target validator is required");
  // Validate shape and charged budgets without calling user code. Copy only
  // bounded data, then resolve targets against that immutable snapshot.
  const auto bytes=p.validate(batch,[](const std::string&) { return true; });
  if(p.state.pending_batches>=p.limits.pending_batches || bytes>p.limits.pending_bytes-p.state.pending_bytes)
   return {AdmissionStatus::backpressure,"Pending item/byte budget exhausted; publish and commit queued batches first",{}};
  if(p.state.receipt_count>=p.limits.receipts || bytes>p.limits.receipt_bytes-p.state.receipt_bytes)
   return {AdmissionStatus::backpressure,"Retained receipt budget exhausted; no deduplication records were evicted",{}};
  auto immutable=std::make_shared<const GameplayChangeBatch>(batch);
  const auto& prepared=*immutable;
  require(p.validate(prepared,targets)==bytes,"Prepared gameplay byte accounting changed");
  auto receipts=p.receipts; auto order=p.order; auto event_ids=p.event_ids;
  receipts.emplace(prepared.operation_id,Impl::Receipt{immutable,bytes}); order.push_back(prepared.operation_id);
  for(const auto& event:prepared.events) event_ids.insert(event.event_id);
  AdmissionResult result{AdmissionStatus::accepted,"Reserved immutable delta/event batch; not yet visible or durable",immutable};
  p.receipts.swap(receipts); p.order.swap(order); p.event_ids.swap(event_ids);
  p.state.accepted_revision=prepared.revision; p.state.accepted_sequence=prepared.events.back().sequence;
  ++p.state.pending_batches; p.state.pending_bytes+=bytes; ++p.state.receipt_count; p.state.receipt_bytes+=bytes;
  return result;
 } catch(const std::exception& error) { return {AdmissionStatus::rejected,error.what(),{}}; }
}
Result GameplayAdmission::acknowledge(const GameplayAcknowledgement& acknowledgement) {
 auto& p=*impl_;
 if(p.reserving) return {false,"Reentrant gameplay mutation is not allowed",p.state.durable_revision};
 if(acknowledgement.scope!=p.scope || !text(acknowledgement.operation_id)) return {false,"Foreign gameplay acknowledgement",p.state.durable_revision};
 const auto found=p.receipts.find(acknowledgement.operation_id);
 if(found==p.receipts.end() || found->second.batch->revision!=acknowledgement.revision)
  return {false,"Unknown acknowledgement operation/revision",p.state.durable_revision};
 auto& receipt=found->second;
 if(acknowledgement.phase==GameplayPhase::world_or_document_applied) {
  if(receipt.visible) return {true,"Visibility already acknowledged",acknowledgement.revision};
  if(p.next(false)!=receipt.batch) return {false,"Visibility acknowledgement is out of order",p.state.visible_revision};
  Result result{true,"World publication acknowledged; not a storage acknowledgement",acknowledgement.revision};
  receipt.visible=true; p.state.visible_revision=acknowledgement.revision; p.state.visible_sequence=receipt.batch->events.back().sequence;
  return result;
 }
 if(acknowledgement.phase==GameplayPhase::durably_committed) {
  if(receipt.durable) return {true,"Durability already acknowledged",acknowledgement.revision};
  if(!receipt.visible || p.next(true)!=receipt.batch) return {false,"Durability requires ordered visible batches",p.state.durable_revision};
  Result result{true,"External storage completion acknowledged",acknowledgement.revision};
  receipt.durable=true; p.state.durable_revision=acknowledgement.revision; p.state.durable_sequence=receipt.batch->events.back().sequence;
  --p.state.pending_batches; p.state.pending_bytes-=receipt.bytes;
  return result;
 }
 return {false,"Unsupported acknowledgement phase",p.state.durable_revision};
}
GameplayAdmissionState GameplayAdmission::state() const noexcept { return impl_->state; }
std::shared_ptr<const GameplayChangeBatch> GameplayAdmission::next_visible() const { return impl_->next(false); }
std::shared_ptr<const GameplayChangeBatch> GameplayAdmission::next_durable() const { return impl_->next(true); }
}
