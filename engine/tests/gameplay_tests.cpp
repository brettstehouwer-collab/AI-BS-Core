#include <aibs/gameplay.hpp>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace aibs;
namespace {
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
GameplayScope scope() { return {"first-boot", new_uuid(), "main", new_uuid(), GameplayContext::player_world}; }
std::vector<ComponentSchema> schemas() {
 return {{"firstboot.Power",1,{{"capacity",GameplayValueKind::number,true,0,100},
                              {"isolated",GameplayValueKind::boolean,false}}}};
}
GameplayChangeBatch repair(const GameplayScope& owner, const std::string& entity, std::uint64_t before=0,
                           std::uint64_t sequence=1, std::string operation="repair-1") {
 GameplayChangeBatch batch;
 batch.scope=owner; batch.operation_id=std::move(operation); batch.expected_revision=before; batch.revision=before+1;
 batch.deltas.push_back({ComponentAction::upsert,{entity,"firstboot.Power",1,{{"capacity",100.0}}}});
 SemanticEvent event;
 event.event_id=new_uuid(); event.scope=owner; event.sequence=sequence; event.operation_id=batch.operation_id;
 event.subject_ids={entity}; event.source_revision=batch.revision;
 event.provenance={GameplayProvenance::gameplay_rule,"firstboot.repair.v1"};
 event.payload=RepairOutcome{entity,0,100};
 batch.events.push_back(std::move(event));
 return batch;
}
}
int main() {
 try {
  const auto owner=scope(); const auto entity=new_uuid();
  auto accepts=[&](const std::string& id){return id==entity;};
  GameplayAdmission admission(owner,schemas());
  const auto batch=repair(owner,entity);
  auto accepted=admission.reserve(batch,accepts);
  require(accepted.status==AdmissionStatus::accepted && accepted.batch, "validated world delta and semantic event reserve together");
  require(admission.state().accepted_revision==1 && admission.state().visible_revision==0 && admission.state().durable_revision==0,
          "acceptance does not claim visibility or durability");
  auto changed=batch; std::get<double>(changed.deltas[0].component.fields.at("capacity"))=50;
  require(admission.reserve(changed,accepts).status==AdmissionStatus::rejected, "conflicting operation retry rejected");
  require(admission.reserve(batch,[](const std::string&){return false;}).status==AdmissionStatus::retry,
          "exact retry uses retained admission receipt even after caller world changed");
  auto immutable=batch; immutable.events[0].subject_ids.clear();
  require(accepted.batch->events[0].subject_ids.size()==1, "batch ownership is immutable and independent of caller buffers");
  require(!admission.acknowledge({owner,"repair-1",1,GameplayPhase::durably_committed}).ok,
          "durable acknowledgement cannot precede world publication");
  auto foreign=owner; foreign.branch_id="other";
  require(!admission.acknowledge({foreign,"repair-1",1,GameplayPhase::world_or_document_applied}).ok,
          "foreign visibility acknowledgement rejected");
  require(admission.next_visible()==accepted.batch && !admission.next_durable(),
          "worker cannot receive unpublished world changes");
  require(admission.acknowledge({owner,"repair-1",1,GameplayPhase::world_or_document_applied}).ok, "visible acknowledgement accepted");
  require(admission.state().visible_revision==1 && admission.state().durable_revision==0, "visible is not saved");
  require(admission.next_durable()==accepted.batch, "same immutable visible delta and events reach durable boundary");
  require(admission.acknowledge({owner,"repair-1",1,GameplayPhase::durably_committed}).ok, "external durability acknowledgement advances saved head");
  require(admission.state().durable_revision==1 && admission.state().pending_batches==0, "durable batch releases pending credits");
  require(admission.acknowledge({owner,"repair-1",1,GameplayPhase::durably_committed}).ok, "identical completion is idempotent");
  require(admission.reserve(batch,accepts).status==AdmissionStatus::retry && admission.state().receipt_count==1,
          "durable request retry does not duplicate history");
  GameplayAdmission zero_identity(owner,schemas());
  auto negative_zero=repair(owner,entity,0,1,"signed-zero");
  negative_zero.deltas[0].component.fields["capacity"]=-0.0;
  negative_zero.events[0].payload=RepairOutcome{entity,-0.0,0};
  require(zero_identity.reserve(negative_zero,accepts).status==AdmissionStatus::accepted,"preserve finite signed-zero input");
  auto positive_zero=negative_zero;positive_zero.deltas[0].component.fields["capacity"]=0.0;
  require(zero_identity.reserve(positive_zero,accepts).status==AdmissionStatus::rejected,"exact retry identity matches lossless wire signed-zero bits");

  GameplayAdmission reentrant(owner,schemas());
  auto outer=repair(owner,entity,0,1,"reentrant-outer");
  outer.deltas.clear();outer.events[0].payload=RouteOutcome{entity,true};
  const auto inner=repair(owner,entity,0,1,"reentrant-inner");
  bool entered=false;auto inner_status=AdmissionStatus::accepted;
  const auto outer_result=reentrant.reserve(outer,[&](const std::string& id) {
   if(!entered) { entered=true;inner_status=reentrant.reserve(inner,accepts).status; }
   return accepts(id);
  });
  const bool reentrant_safe=entered && inner_status==AdmissionStatus::rejected && outer_result.status==AdmissionStatus::accepted &&
   reentrant.state().accepted_revision==1 && reentrant.state().accepted_sequence==1 && reentrant.state().pending_batches==1 &&
   reentrant.state().receipt_count==1 && reentrant.next_visible()==outer_result.batch;
  GameplayAdmission immutable_input(owner,schemas());
  auto mutable_batch=repair(owner,entity,0,1,"mutated-input");bool mutated=false;
  const auto snapshot_result=immutable_input.reserve(mutable_batch,[&](const std::string& id) {
   if(!mutated) {
    mutated=true;mutable_batch.revision=50;mutable_batch.events[0].source_revision=50;
    mutable_batch.deltas[0].component.fields["capacity"]=99.0;
   }
   return accepts(id);
  });
  const bool immutable_safe=snapshot_result.status==AdmissionStatus::accepted && snapshot_result.batch->revision==1 &&
   snapshot_result.batch->events[0].source_revision==1 && immutable_input.state().accepted_revision==1 &&
   std::get<double>(snapshot_result.batch->deltas[0].component.fields.at("capacity"))==100;
  GameplayAdmission guarded_ack(owner,schemas());
  require(guarded_ack.reserve(batch,accepts).status==AdmissionStatus::accepted,"prepare callback acknowledgement fixture");
  auto route=repair(owner,entity,1,2,"callback-ack");route.deltas.clear();route.events[0].payload=RouteOutcome{entity,true};
  bool nested_ack=true;
  const auto rejected_callback=guarded_ack.reserve(route,[&](const std::string&) -> bool {
   nested_ack=guarded_ack.acknowledge({owner,"repair-1",1,GameplayPhase::world_or_document_applied}).ok;
   throw std::runtime_error("target lookup failed");
  });
  const bool ack_safe=!nested_ack && rejected_callback.status==AdmissionStatus::rejected && guarded_ack.state().visible_revision==0 &&
   guarded_ack.state().accepted_revision==1 && guarded_ack.reserve(route,accepts).status==AdmissionStatus::accepted;
  std::cout<<"resolver safety: recursive="<<reentrant_safe<<" immutable="<<immutable_safe<<" acknowledgement="<<ack_safe<<'\n';
  require(reentrant_safe && immutable_safe && ack_safe,"resolver cannot mutate admission state or the immutable prepared batch");
  GameplayAdmission semantic_families(owner,schemas());
  auto construction=repair(owner,entity,0,1,"constructed");construction.events[0].payload=ConstructionOutcome{entity,true};
  require(semantic_families.reserve(construction,accepts).status==AdmissionStatus::accepted &&
   std::string(semantic_event_type(construction.events[0]))=="construction.outcome","construction component delta and typed result reserve as one unit");
  auto route_only=repair(owner,entity,1,2,"route-choice");route_only.deltas.clear();route_only.events[0].payload=RouteOutcome{entity,true};
  require(semantic_families.reserve(route_only,accepts).status==AdmissionStatus::accepted &&
   std::string(semantic_event_type(route_only.events[0]))=="route.outcome","event-only route outcome remains separate from authoring edits");
  auto hazard_only=repair(owner,entity,2,3,"hazard-choice");hazard_only.deltas.clear();hazard_only.events[0].payload=HazardOutcome{entity,true};
  require(semantic_families.reserve(hazard_only,accepts).status==AdmissionStatus::accepted &&
   std::string(semantic_event_type(hazard_only.events[0]))=="hazard.outcome","typed hazard evidence preserves ordered semantic sequence");
  GameplayAdmission allocation_failure(owner,schemas());
  const auto failed_allocation=allocation_failure.reserve(batch,[](const std::string&) -> bool { throw std::bad_alloc(); });
  require(failed_allocation.status==AdmissionStatus::rejected && allocation_failure.state().receipt_count==0 &&
   allocation_failure.state().pending_bytes==0 && allocation_failure.state().accepted_revision==0 &&
   allocation_failure.reserve(batch,accepts).status==AdmissionStatus::accepted,"resolver allocation failure preserves heads/budgets and releases mutation guard");

  GameplayLimits limits; limits.pending_batches=1;
  GameplayAdmission bounded(owner,schemas(),limits);
  require(bounded.reserve(batch,accepts).status==AdmissionStatus::accepted, "first bounded batch accepted");
  const auto second=repair(owner,entity,1,2,"repair-2");
  require(bounded.reserve(second,accepts).status==AdmissionStatus::backpressure, "queue capacity reports backpressure");
  require(bounded.state().accepted_revision==1 && bounded.state().accepted_sequence==1, "backpressure publishes neither delta nor event head");
  require(bounded.acknowledge({owner,"repair-1",1,GameplayPhase::world_or_document_applied}).ok, "bounded visible");
  require(bounded.acknowledge({owner,"repair-1",1,GameplayPhase::durably_committed}).ok, "bounded durable");
  require(bounded.reserve(second,accepts).status==AdmissionStatus::accepted, "draining permits exact previously blocked operation");

  GameplayAdmission ordered(owner,schemas());
  require(ordered.reserve(batch,accepts).status==AdmissionStatus::accepted && ordered.reserve(second,accepts).status==AdmissionStatus::accepted,
          "two sequential batches admitted");
  require(!ordered.acknowledge({owner,"repair-2",2,GameplayPhase::world_or_document_applied}).ok, "out-of-order visible acknowledgement rejected");
  require(ordered.acknowledge({owner,"repair-1",1,GameplayPhase::world_or_document_applied}).ok &&
          ordered.acknowledge({owner,"repair-2",2,GameplayPhase::world_or_document_applied}).ok, "ordered visibility");
  require(!ordered.acknowledge({owner,"repair-2",2,GameplayPhase::durably_committed}).ok, "out-of-order durable acknowledgement rejected");
  require(ordered.acknowledge({owner,"repair-1",1,GameplayPhase::durably_committed}).ok &&
          ordered.acknowledge({owner,"repair-2",2,GameplayPhase::durably_committed}).ok, "ordered durability");
  require(ordered.acknowledge({owner,"repair-1",1,GameplayPhase::durably_committed}).ok && ordered.state().durable_revision==2,
          "late duplicate cannot regress newer durable head");

  auto rejects=[&](GameplayChangeBatch invalid, const char* message) {
   GameplayAdmission fresh(owner,schemas());
   require(fresh.reserve(invalid,accepts).status==AdmissionStatus::rejected,message);
   require(fresh.state().accepted_revision==0 && fresh.state().receipt_count==0,"rejection preserves all admission state");
  };
  auto invalid=batch; invalid.scope.world_id=new_uuid(); rejects(invalid,"cross-world batch rejected");
  invalid=batch; invalid.events[0].scope.timeline_id=new_uuid(); rejects(invalid,"cross-timeline semantic event rejected");
  invalid=batch; invalid.deltas[0].component.version=2; rejects(invalid,"unknown component version rejected");
  invalid=batch; invalid.deltas[0].component.fields["capacity"]=true; rejects(invalid,"component field type cannot change silently");
  invalid=batch; invalid.deltas[0].component.fields["capacity"]=101.0; rejects(invalid,"component numeric constraints enforced");
  invalid=batch; invalid.deltas[0].component.fields["capacity"]=std::numeric_limits<double>::quiet_NaN(); rejects(invalid,"nonfinite component value rejected");
  invalid=batch; invalid.deltas[0].component.fields["unexpected"]=1.0; rejects(invalid,"unknown field rejected");
  invalid=batch; invalid.events[0].payload_version=2; rejects(invalid,"unsupported semantic payload version rejected");
  invalid=batch; invalid.events[0].source_revision=0; rejects(invalid,"semantic event must describe admitted revision");
  invalid=batch; invalid.events[0].sequence=2; rejects(invalid,"semantic event sequence gap rejected");
  invalid=batch; invalid.events[0].subject_ids={new_uuid()}; rejects(invalid,"caller resolver validates semantic UUID targets");
  invalid=batch; invalid.events[0].payload=RepairOutcome{new_uuid(),0,100}; rejects(invalid,"payload target must match scoped subject");
  invalid=batch; invalid.events[0].result_phase=GameplayPhase::durably_committed; rejects(invalid,"caller cannot reserve a forged durable event");
  invalid=batch; invalid.events.clear(); rejects(invalid,"world deltas without semantic evidence rejected");
  invalid=batch; invalid.events.push_back(invalid.events.front()); rejects(invalid,"duplicate event identity rejected atomically");
  GameplayAdmission bad_targets(owner,schemas());
  require(bad_targets.reserve(batch,{}).status==AdmissionStatus::rejected, "caller UUID resolver required");

  GameplayLimits tiny; tiny.pending_bytes=1;
  GameplayAdmission no_bytes(owner,schemas(),tiny);
  require(no_bytes.reserve(batch,accepts).status==AdmissionStatus::backpressure && no_bytes.state().receipt_count==0,
          "byte budget rejects complete batch before admission");
  GameplayLimits receipts; receipts.receipts=1;
  GameplayAdmission no_eviction(owner,schemas(),receipts);
  require(no_eviction.reserve(batch,accepts).status==AdmissionStatus::accepted, "single receipt accepted");
  require(no_eviction.acknowledge({owner,"repair-1",1,GameplayPhase::world_or_document_applied}).ok &&
          no_eviction.acknowledge({owner,"repair-1",1,GameplayPhase::durably_committed}).ok, "single receipt completed");
  require(no_eviction.reserve(second,accepts).status==AdmissionStatus::backpressure &&
          no_eviction.reserve(batch,accepts).status==AdmissionStatus::retry,"receipt capacity never casually evicts deduplication");
  std::cout << "PASS: versioned semantic/component contracts, immutable atomic batches, scope/UUID validation, bounded admission and ordered acknowledgements\n";
  return 0;
 } catch(const std::exception& error) { std::cerr << "FAIL: " << error.what() << '\n'; return 1; }
}
