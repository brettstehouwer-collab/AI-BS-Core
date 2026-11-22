#pragma once
#include <aibs/gameplay.hpp>
#include <limits>

inline aibs::GameplayChangeBatch semantic_v1_fixture() {
 using namespace aibs;
 GameplayChangeBatch value;
 value.scope={"semantic-compatibility","11111111-1111-4111-8111-111111111111","main","22222222-2222-4222-8222-222222222222",GameplayContext::player_world};
 value.operation_id="fixture.v1";value.revision=1;
 const std::string entity="33333333-3333-4333-8333-333333333333";
 value.deltas.push_back({ComponentAction::upsert,{entity,"fixture.State",1,{{"capacity",100.0},{"count",std::numeric_limits<std::int64_t>::min()},{"open",false},{"stage",std::string("closed")},{"zero",-0.0}}}});
 SemanticEvent event;event.scope=value.scope;event.operation_id=value.operation_id;event.subject_ids={entity};event.source_revision=1;
 event.provenance={GameplayProvenance::gameplay_rule,"fixture.semantic.v1"};event.logical_tick=std::numeric_limits<std::uint64_t>::max();
 event.event_id="44444444-4444-4444-8444-444444444444";event.sequence=1;event.payload=RepairOutcome{entity,0,100};value.events.push_back(event);
 event.event_id="55555555-5555-4555-8555-555555555555";event.sequence=2;event.payload=ConstructionOutcome{entity,true};value.events.push_back(event);
 event.event_id="66666666-6666-4666-8666-666666666666";event.sequence=3;event.payload=RouteOutcome{entity,true};value.events.push_back(event);
 event.event_id="77777777-7777-4777-8777-777777777777";event.sequence=4;event.payload=HazardOutcome{entity,false};value.events.push_back(event);
 return value;
}
