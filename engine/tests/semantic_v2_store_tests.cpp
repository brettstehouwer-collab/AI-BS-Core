#include <aibs/gameplay_world.hpp>
#include <aibs/gameplay_codec.hpp>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>

using namespace aibs;
namespace gc=aibs::gameplay_codec;
namespace {
void require(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
struct Ids { GameplayScope scope{"semantic-store",new_uuid(),"main",new_uuid(),GameplayContext::player_world};std::string old=new_uuid(),door=new_uuid(),power=new_uuid(),quest=new_uuid(); };
std::vector<ComponentSchema> old_registry() { return {{"old.Power",1,{{"capacity",GameplayValueKind::number,true,0,100}}}}; }
std::vector<ComponentSchema> new_registry() {
 auto result=old_registry();result.push_back({"game.Door",1,{{"open",GameplayValueKind::boolean}}});
 result.push_back({"game.Power",1,{{"energy",GameplayValueKind::integer}}});
 result.push_back({"game.Quest",1,{{"state",GameplayValueKind::integer},{"step",GameplayValueKind::text}}});return result;
}
GameplayChangeBatch batch(const Ids& ids,std::string operation,std::uint64_t revision,std::uint32_t version=1) {
 GameplayChangeBatch result;result.scope=ids.scope;result.operation_id=std::move(operation);result.expected_revision=revision-1;result.revision=revision;result.schema_version=version;return result;
}
SemanticEvent event(const GameplayChangeBatch& batch,std::uint64_t sequence,std::string subject,SemanticPayload payload) {
 SemanticEvent result;result.event_id=new_uuid();result.scope=batch.scope;result.sequence=sequence;result.operation_id=batch.operation_id;
 result.source_revision=batch.revision;result.subject_ids={std::move(subject)};result.payload_version=payload.index()>=4?2:1;
 result.provenance.source_id="semantic.integration.rules.v1";result.payload=std::move(payload);return result;
}
const ComponentRecord& component(const GameplayStoreRecovery& state,const std::string& entity,const std::string& type) {
 for(const auto& value:state.components) if(value.entity_id==entity && value.type_id==type) return value;
 throw std::runtime_error("Missing actual component in rule snapshot");
}
bool has(const GameplayStoreRecovery& state,const std::string& entity) {
 for(const auto& value:state.components) if(value.entity_id==entity) return true;return false;
}
GameplayChangeBatch repair(const Ids& ids) {
 auto value=batch(ids,"legacy-repair",41);value.deltas={{ComponentAction::upsert,{ids.old,"old.Power",1,{{"capacity",50.0}}}}};
 value.events={event(value,8,ids.old,RepairOutcome{ids.old,25,50})};return value;
}
GameplayChangeBatch setup(const Ids& ids) {
 auto value=batch(ids,"construct-mechanism-and-quest",42);
 value.deltas={{ComponentAction::upsert,{ids.door,"game.Door",1,{{"open",false}}}},
  {ComponentAction::upsert,{ids.power,"game.Power",1,{{"energy",std::int64_t{10}}}}},
  {ComponentAction::upsert,{ids.quest,"game.Quest",1,{{"state",std::int64_t{1}},{"step",std::string("offer")}}}}};
 value.events={event(value,9,ids.door,ConstructionOutcome{ids.door,true})};return value;
}
GameplayChangeBatch activate(const Ids& ids) {
 auto value=batch(ids,"powered-door-and-quest",43,2);
 value.deltas={{ComponentAction::upsert,{ids.door,"game.Door",1,{{"open",true}}}},
  {ComponentAction::upsert,{ids.power,"game.Power",1,{{"energy",std::int64_t{7}}}}},
  {ComponentAction::upsert,{ids.quest,"game.Quest",1,{{"state",std::int64_t{2}},{"step",std::string("enter")}}}}};
 value.events={event(value,10,ids.door,MechanismOutcome{ids.door,"open",false,true}),
  event(value,11,ids.quest,QuestOutcome{ids.quest,QuestState::offered,QuestState::active,"offer","enter"}),
  event(value,12,ids.door,RouteOutcome{ids.door,true})};return value;
}
GameplayChangeBatch finish(const Ids& ids) {
 auto value=batch(ids,"finish-quest",44,2);value.deltas={{ComponentAction::upsert,{ids.quest,"game.Quest",1,{{"state",std::int64_t{4}},{"step",std::string("done")}}}}};
 value.events={event(value,13,ids.quest,QuestOutcome{ids.quest,QuestState::active,QuestState::completed,"enter","done"})};return value;
}
void validate_activation(const Ids& ids,const GameplayStoreRecovery& before,const GameplayStoreRecovery& after,const GameplayChangeBatch& request) {
 const auto& before_door=component(before,ids.door,"game.Door");const auto& after_door=component(after,ids.door,"game.Door");
 const auto& before_power=component(before,ids.power,"game.Power");const auto& after_power=component(after,ids.power,"game.Power");
 const auto& before_quest=component(before,ids.quest,"game.Quest");const auto& after_quest=component(after,ids.quest,"game.Quest");
 const auto& mechanism=std::get<MechanismOutcome>(request.events.at(0).payload);const auto& quest=std::get<QuestOutcome>(request.events.at(1).payload);
 require(mechanism.entity_id==ids.door && mechanism.attribute_id=="open" && mechanism.before==std::get<bool>(before_door.fields.at("open")) &&
  mechanism.after==std::get<bool>(after_door.fields.at("open")) && !mechanism.before && mechanism.after,"mechanism event must prove the actual closed-to-open component transition");
 require(std::get<std::int64_t>(before_power.fields.at("energy"))>=3 &&
  std::get<std::int64_t>(after_power.fields.at("energy"))==std::get<std::int64_t>(before_power.fields.at("energy"))-3,"opening the door must consume exactly three actual power units");
 require(quest.quest_id==ids.quest && quest.before==QuestState::offered && quest.after==QuestState::active &&
  std::get<std::int64_t>(before_quest.fields.at("state"))==static_cast<std::int64_t>(quest.before) &&
  std::get<std::int64_t>(after_quest.fields.at("state"))==static_cast<std::int64_t>(quest.after) &&
  std::get<std::string>(before_quest.fields.at("step"))==quest.before_step && std::get<std::string>(after_quest.fields.at("step"))==quest.after_step &&
  quest.before_step=="offer" && quest.after_step=="enter","quest event must prove actual offered-to-active state and step changes");
 require(std::get<RouteOutcome>(request.events.at(2).payload).traversed && std::get<bool>(after_door.fields.at("open")),"legacy traversal outcome requires the newly opened door");
 require(gc::encode_component(component(before,ids.old,"old.Power"))==gc::encode_component(component(after,ids.old,"old.Power")),"new mechanics cannot rewrite the legacy component");
}
bool success(const GameplaySaveCompletion& value) { return value.result.status==GameplayStoreStatus::committed || value.result.status==GameplayStoreStatus::retry; }
GameplaySaveCompletion completion(GameplayWorld& world) {
 const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);
 for(;;) { if(auto value=world.poll()) return std::move(*value);require(std::chrono::steady_clock::now()<deadline,"Actual v2 save completion timed out");std::this_thread::sleep_for(std::chrono::milliseconds(2)); }
}
void exact_history(const std::vector<GameplayChangeBatch>& actual,const std::vector<GameplayChangeBatch>& expected) {
 require(actual.size()==expected.size(),"Durable history count changed");
 for(std::size_t n=0;n<actual.size();++n) require(gc::encode_batch(actual[n])==gc::encode_batch(expected[n]),"Durable v1/v2 request/event bytes changed");
}
}
int main() {
 try {
  const Ids ids;const auto directory=std::filesystem::temp_directory_path()/("aibs-semantic-v2-store-"+new_uuid());std::filesystem::create_directories(directory);const auto path=directory/"world.sqlite";
  // This test checks the store's opaque legacy-byte preservation. Genuine
  // format1 import/undo evidence is exercised by registry process acceptance.
  GameplayStoreBaseline baseline;baseline.revision=40;baseline.sequence=7;baseline.legacy_checkpoint={0,255,0,1,42};
  baseline.components={{ids.old,"old.Power",1,{{"capacity",25.0}}}};const auto old=repair(ids);const auto old_wire=gc::encode_batch(old);
  { GameplayStore original(path,ids.scope,old_registry());require(original.seed(baseline).status==GameplayStoreStatus::committed && original.commit(old).status==GameplayStoreStatus::committed,"prepare original baseline and v1 durable receipt"); }
  require(GameplayStore::extend_registry(path,ids.scope,old_registry(),new_registry(),"semantic.v2.types",41,8).status==GameplayStoreStatus::committed,"explicit additive format2 registry evolution");
  const auto constructed=setup(ids),activated=activate(ids),finished=finish(ids);const std::vector<GameplayChangeBatch> history{old,constructed,activated,finished};
  std::mutex mutex;std::condition_variable changed;bool entered=false,released=false;std::atomic<bool> gate=false,fail_once=false;
  {
   GameplayWorld world(path,ids.scope,new_registry(),{},[&](GameplayStoreStage stage) {
    if(stage!=GameplayStoreStage::before_commit) return;
    if(fail_once.exchange(false)) throw std::runtime_error("injected v2 quest commit failure");
    if(gate.exchange(false)) { std::unique_lock lock(mutex);entered=true;changed.notify_all();require(changed.wait_for(lock,std::chrono::seconds(10),[&]{return released;}),"v2 transaction gate timed out"); }
   });
   GameplayStore durable_reader(path,ids.scope,new_registry());
   const auto prepared=world.prepare(constructed,[&](const auto& before,const auto& after,const auto&) {
    require(!has(before,ids.door) && !has(before,ids.power) && !has(before,ids.quest) &&
     !std::get<bool>(component(after,ids.door,"game.Door").fields.at("open")) &&
     std::get<std::int64_t>(component(after,ids.power,"game.Power").fields.at("energy"))==10 &&
     std::get<std::int64_t>(component(after,ids.quest,"game.Quest").fields.at("state"))==1,"setup rule must create actual closed door, power reserve and offered quest");
   });
   require(prepared.status==GameplayPrepareStatus::prepared && world.publish(prepared.change).ok && success(completion(world)),"new registered components commit through actual worker");
   const auto validator=[&](const auto& before,const auto& after,const auto& request) { validate_activation(ids,before,after,request); };
   for(int lie=0;lie<3;++lie) {
    auto invalid=activated;
    if(lie==0) invalid.deltas[0].component.fields["open"]=false;
    if(lie==1) invalid.deltas[1].component.fields["energy"]=std::int64_t{9};
    if(lie==2) invalid.deltas[2].component.fields["step"]=std::string("fabricated");
    require(world.prepare(invalid,validator).status==GameplayPrepareStatus::rejected && world.snapshot()->revision==42 && world.state().saved,
     "valid event labels cannot publish false mechanism/power/quest component outcomes");
   }
   auto proposal=world.prepare(activated,validator);require(proposal.status==GameplayPrepareStatus::prepared,"truthful v2 mechanism and quest prepare");
   gate=true;require(world.publish(proposal.change).ok,"truthful mixed v1/v2 batch publishes atomically");
   { std::unique_lock lock(mutex);require(changed.wait_for(lock,std::chrono::seconds(10),[&]{return entered;}),"actual v2 transaction did not reach gate"); }
   require(world.snapshot()->revision==43 && world.state().durable_revision==42 && !world.state().saved &&
    std::get<bool>(component(*world.snapshot(),ids.door,"game.Door").fields.at("open")),"visible v2 world is not prematurely acknowledged saved");
   { require(durable_reader.recover().revision==42 && !std::get<bool>(component(durable_reader.recover(),ids.door,"game.Door").fields.at("open")),"uncommitted v2 transaction leaves old durable components");exact_history(durable_reader.read_batches(0),{old,constructed}); }
   { std::lock_guard lock(mutex);released=true; }changed.notify_all();
   require(success(completion(world)) && world.state().saved && world.state().durable_revision==43 && world.state().durable_sequence==12,"real COMMIT acknowledges complete mixed-family batch once");
   fail_once=true;auto ready=world.prepare(finished,[&](const auto& before,const auto& after,const auto& request) {
    const auto& outcome=std::get<QuestOutcome>(request.events.front().payload);
    require(std::get<bool>(component(before,ids.door,"game.Door").fields.at("open")) && outcome.before==QuestState::active && outcome.after==QuestState::completed &&
     std::get<std::int64_t>(component(before,ids.quest,"game.Quest").fields.at("state"))==2 &&
     std::get<std::int64_t>(component(after,ids.quest,"game.Quest").fields.at("state"))==4 &&
     outcome.before_step==std::get<std::string>(component(before,ids.quest,"game.Quest").fields.at("step")) &&
     outcome.after_step==std::get<std::string>(component(after,ids.quest,"game.Quest").fields.at("step")),"completion rule proves actual active quest and exact terminal step");
   });
   require(ready.status==GameplayPrepareStatus::prepared && world.publish(ready.change).ok && !success(completion(world)) && world.state().failed &&
    world.state().visible_revision==44 && world.state().durable_revision==43,"failed v2 quest save stays visibly unsaved");
   { require(durable_reader.recover().revision==43 && std::get<std::int64_t>(component(durable_reader.recover(),ids.quest,"game.Quest").fields.at("state"))==2,"failed quest transaction rolls back state and semantic evidence");exact_history(durable_reader.read_batches(0),{old,constructed,activated}); }
   require(world.retry_pending().ok && success(completion(world)) && world.state().saved && world.close().ok,"exact live retry of v2 quest commits once before close");
  }
  {
   GameplayWorld reopened(path,ids.scope,new_registry());require(reopened.state().saved && reopened.snapshot()->revision==44 && reopened.state().durable_sequence==13,"restart restores the complete v2 durable head");
   exact_history(reopened.read_batches(0),history);bool callback=false;
   require(reopened.prepare(activated,[&](const auto&,const auto&,const auto&){callback=true;}).status==GameplayPrepareStatus::retry && !callback,"v2 exact retry survives restart without replaying rules or paying twice");
   auto conflict=activated;conflict.deltas[1].component.fields["energy"]=std::int64_t{6};
   require(reopened.prepare(conflict).status==GameplayPrepareStatus::rejected && reopened.snapshot()->revision==44,"conflicting v2 operation retry cannot rewrite the committed cost");
   require(reopened.prepare(old).status==GameplayPrepareStatus::retry && reopened.close().ok,"old v1 retry remains idempotent after v2 events");
  }
  GameplayStore verified(path,ids.scope,new_registry());const auto preserved=verified.baseline();const auto receipt=verified.lookup_batch(old.operation_id);
  require(preserved && preserved->revision==baseline.revision && preserved->sequence==baseline.sequence && preserved->components==baseline.components &&
   preserved->legacy_checkpoint==baseline.legacy_checkpoint && receipt && gc::encode_batch(*receipt)==old_wire && verified.verify().ok,"v2 replay leaves original raw baseline/components and exact v1 receipt unchanged");
  const auto batches=verified.read_batches(0);for(std::size_t n=0;n<batches.size();++n) require(gc::encode_batch(batches[n])[8]==(n<2?1:2),"stored envelopes retain actual old/new family versions");
  require(std::get<MechanismOutcome>(batches[2].events[0].payload).after && std::get<QuestOutcome>(batches[2].events[1].payload).after==QuestState::active &&
   std::get<QuestOutcome>(batches[3].events[0].payload).after==QuestState::completed,"typed mechanism and quest payloads replay exactly");
  std::cout<<"PASS: migrated registry, mixed v1/v2 actual store/worker/world, truthful rules, rollback/retry and exact restart evidence\n";return 0;
 } catch(const std::exception& error) { std::cerr<<"FAIL: "<<error.what()<<'\n';return 1; }
}
