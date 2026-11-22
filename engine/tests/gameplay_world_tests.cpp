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
namespace {
void require(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
GameplayScope scope() { return {"runtime-world",new_uuid(),"main",new_uuid(),GameplayContext::player_world}; }
std::vector<ComponentSchema> schemas() { return {{"runtime.Power",1,{{"capacity",GameplayValueKind::number,true,0,100}}}}; }
GameplayChangeBatch change(const GameplayScope& owner,const std::string& entity,std::uint64_t previous=0,double capacity=100) {
 GameplayChangeBatch result;result.scope=owner;result.operation_id="repair-"+std::to_string(previous+1);
 result.expected_revision=previous;result.revision=previous+1;
 result.deltas.push_back({ComponentAction::upsert,{entity,"runtime.Power",1,{{"capacity",capacity}}}});
 SemanticEvent event;event.event_id=new_uuid();event.scope=owner;event.sequence=previous+1;event.operation_id=result.operation_id;
 event.subject_ids={entity};event.source_revision=result.revision;event.provenance.source_id="runtime.repair.v1";
 event.payload=RepairOutcome{entity,0,capacity};result.events.push_back(std::move(event));return result;
}
template<class Predicate> void await(Predicate predicate,const char* message) {
 const auto until=std::chrono::steady_clock::now()+std::chrono::seconds(10);
 while(!predicate()) { require(std::chrono::steady_clock::now()<until,message);std::this_thread::sleep_for(std::chrono::milliseconds(2)); }
}
GameplaySaveCompletion completion(GameplayWorld& world) {
 std::optional<GameplaySaveCompletion> result;await([&]{result=world.poll();return result.has_value();},"world completion timed out");return std::move(*result);
}
bool committed(const GameplaySaveCompletion& value) { return value.result.status==GameplayStoreStatus::committed || value.result.status==GameplayStoreStatus::retry; }
void prepare_publish_restart(const std::filesystem::path& folder) {
 const auto owner=scope(),other_scope=scope();const auto entity=new_uuid();const auto database=folder/"world.sqlite";
 const auto first=change(owner,entity);
 {
  GameplayWorld world(database,owner,schemas());require(world.state().saved && world.snapshot()->revision==0,"empty actual store is saved baseline");
  const auto prepared=world.prepare(first);
  require(prepared.status==GameplayPrepareStatus::prepared && prepared.change && world.snapshot()->revision==0 && world.state().pending_batches==0,
          "prepare does not publish or reserve a save queue credit");
  require(world.read_batches(0).empty(),"unpublished semantic proposal is absent from durable runtime history");
  { GameplayStore read(database,owner,schemas());require(read.recover().revision==0 && read.read_batches(0).empty(),"unpublished preparation has no durable world or Adam event"); }
  auto alternate=first;alternate.operation_id="alternate";alternate.events[0].operation_id="alternate";alternate.events[0].event_id=new_uuid();
  const auto stale=world.prepare(alternate);require(stale.status==GameplayPrepareStatus::prepared,"second same-head candidate prepared");
  GameplayWorld foreign(folder/"other.sqlite",other_scope,schemas());
  require(!foreign.publish(prepared.change).ok,"prepared token is bound to its owning runtime");
  require(world.publish(prepared.change).ok && world.snapshot()->revision==1 && world.state().visible_revision==1 && world.state().durable_revision==0,
          "visible publication precedes durable completion polling");
  require(!world.publish(stale.change).ok && world.snapshot()->revision==1,"stale prepared token cannot overwrite a newer live head");
  require(world.prepare(first).status==GameplayPrepareStatus::retry && world.state().pending_batches==1,"pending exact retry adds no queue item");
  auto conflict=first;conflict.deltas[0].component.fields["capacity"]=99.0;
  require(world.prepare(conflict).status==GameplayPrepareStatus::rejected,"pending conflicting request cannot reuse an operation ID");
  require(committed(completion(world)) && world.state().saved && world.state().durable_revision==1,"real SQLite completion marks current visible head saved");
  require(world.read_batches(0)==std::vector<GameplayChangeBatch>{first},"runtime exposes actual bounded durable semantic history");
  require(world.publish(prepared.change).ok && world.state().pending_batches==0,"late exact publication retry does not resave the world");
  require(world.close().ok,"saved world closes cleanly");
 }
 GameplayWorld restored(database,owner,schemas());
 require(restored.snapshot()->revision==1 && restored.snapshot()->components==std::vector<ComponentRecord>{first.deltas[0].component} && restored.state().saved,
         "restart restores actual typed world and durable head");
 require(restored.prepare(first).status==GameplayPrepareStatus::retry,"durable exact retry is found before stale revision validation");
 { GameplayStore read(database,owner,schemas());require(read.read_batches(0).size()==1 && read.read_batches(0)[0].events==first.events,"original semantic memory survives restart without duplicates"); }
 require(restored.close().ok,"restored owner closes");
}
void visibility_and_backpressure(const std::filesystem::path& folder) {
 const auto owner=scope();const auto entity=new_uuid();std::mutex mutex;std::condition_variable condition;bool entered=false,released=false;
 std::atomic<bool> observed_visible=false;GameplayWorld* active=nullptr;
 GameplayWorkerLimits limits;limits.items=1;
 GameplayWorld world(folder/"bounded.sqlite",owner,schemas(),limits,[&](GameplayStoreStage stage) {
  if(stage!=GameplayStoreStage::before_commit) return;
  observed_visible=active->snapshot()->revision>=1;
  std::unique_lock lock(mutex);entered=true;condition.notify_all();
  require(condition.wait_for(lock,std::chrono::seconds(10),[&]{return released;}),"precommit fixture gate timed out");
 });active=&world;
 const auto first=world.prepare(change(owner,entity));require(world.publish(first.change).ok,"bounded world first publication");
 { std::unique_lock lock(mutex);require(condition.wait_for(lock,std::chrono::seconds(10),[&]{return entered;}),"actual worker did not reach precommit"); }
 require(observed_visible && world.state().visible_revision==1 && world.state().durable_revision==0 && !world.state().saved,
         "SQLite observer sees already published world while durable acknowledgement is pending");
 const auto second=world.prepare(change(owner,entity,1,80));require(second.status==GameplayPrepareStatus::prepared,"next visible revision can be prepared");
 const auto before=world.snapshot();require(!world.publish(second.change).ok && world.snapshot()==before && world.state().pending_batches==1,
         "worker backpressure leaves live snapshot and pending records unchanged");
 { std::lock_guard lock(mutex);released=true; }condition.notify_all();
 require(committed(completion(world)) && world.state().saved,"drain current actual commit");
 require(world.publish(second.change).ok && world.snapshot()->revision==2 && world.state().durable_revision==1 && !world.state().saved,
         "same prepared token publishes after capacity drains without treating old acknowledgement as newer saved state");
 require(committed(completion(world)) && world.state().saved && world.close().ok,"second actual commit drains and closes");
}
void rule_isolation_and_targets(const std::filesystem::path& folder) {
 const auto owner=scope();const auto entity=new_uuid();GameplayWorld world(folder/"rules.sqlite",owner,schemas());
 auto invalid=change(owner,entity);invalid.deltas[0].component.fields["capacity"]=101.0;bool called=false;
 require(world.prepare(invalid,[&](const auto&,const auto&,const auto&){called=true;}).status==GameplayPrepareStatus::rejected &&
         !called && world.snapshot()->revision==0 && world.state().pending_batches==0,"invalid registered components reject before rule callbacks or queue admission");
 auto caller=change(owner,entity);
 const auto prepared=world.prepare(caller,[&](const auto& before,const auto& after,const auto& immutable) {
  caller.deltas[0].component.fields["capacity"]=10.0;
  require(before.revision==0 && after.revision==1 && std::get<double>(immutable.deltas[0].component.fields.at("capacity"))==100,
          "rule receives owned immutable candidate input");
  require(world.prepare(immutable).status==GameplayPrepareStatus::rejected,"rule cannot reenter runtime preparation");
  require(!world.close().ok,"rule cannot close owner during preparation");
  require(!world.poll(),"rule cannot consume save completions during preparation");
 });
 require(prepared.status==GameplayPrepareStatus::prepared && std::get<double>(prepared.change->snapshot()->components[0].fields.at("capacity"))==100,
         "external mutable alias cannot alter prepared candidate");
 const auto rejected=world.prepare(change(owner,entity),[](const auto&,const auto&,const auto&){throw std::invalid_argument("power dependency blocked");});
 require(rejected.status==GameplayPrepareStatus::rejected && world.snapshot()->revision==0,"game rule failure leaves visible and durable state unchanged");
 require(world.prepare(change(owner,entity),[](const auto&,const auto&,const auto&){throw 1;}).status==GameplayPrepareStatus::rejected &&
         world.snapshot()->revision==0,"nonstandard rule exceptions also leave the world unchanged");
 require(world.publish(prepared.change).ok && committed(completion(world)),"isolated canonical input publishes and commits");
 auto unknown=change(owner,new_uuid(),1);unknown.deltas.clear();unknown.events[0].payload=RouteOutcome{unknown.events[0].subject_ids[0],true};
 require(world.prepare(unknown).status==GameplayPrepareStatus::rejected,"event-only target must exist in current world or staged creations");
 require(world.close().ok,"rules owner closes");
}
void failures_and_long_lived_receipts(const std::filesystem::path& folder) {
 const auto owner=scope();const auto entity=new_uuid();std::atomic<bool> fail=true;
 GameplayWorld world(folder/"failure.sqlite",owner,schemas(),{},[&](GameplayStoreStage stage) {
  if(stage==GameplayStoreStage::before_commit && fail.exchange(false)) throw std::runtime_error("real save failure");
 });
 const auto first=change(owner,entity);require(world.publish(world.prepare(first).change).ok,"failure fixture visible");
 require(!committed(completion(world)) && world.state().failed && world.state().visible_revision==1 && world.state().durable_revision==0 && !world.state().saved,
         "actual save failure preserves visible state and never fabricates a durable head");
 require(world.retry_pending().ok && committed(completion(world)) && world.state().saved,"explicit failed-head retry produces a real saved acknowledgement");
 require(world.close().ok,"recovered failure closes");
 const auto many_scope=scope();GameplayWorld many(folder/"many.sqlite",many_scope,schemas());
 const auto oldest=change(many_scope,entity);
 for(std::uint64_t n=0;n<140;++n) {
  const auto request=n==0?oldest:change(many_scope,entity,n);
  const auto ready=many.prepare(request);require(ready.status==GameplayPrepareStatus::prepared && many.publish(ready.change).ok,"runtime must not hit admission lifetime receipt cap");
  require(committed(completion(many)) && many.state().pending_batches==0,"completed batches release bounded pending records");
 }
 require(many.state().durable_revision==140 && many.prepare(oldest).status==GameplayPrepareStatus::retry && many.state().pending_batches==0,
         "old exact request uses durable database receipt after more than 128 operations without RAM receipt growth");
 require(many.close().ok,"long-lived runtime closes");
 const auto zero_scope=scope();GameplayWorld zeros(folder/"zero.sqlite",zero_scope,schemas());auto negative=change(zero_scope,entity,0,-0.0);
 require(zeros.publish(zeros.prepare(negative).change).ok && committed(completion(zeros)),"negative-zero request is durable");
 auto positive=negative;positive.deltas[0].component.fields["capacity"]=0.0;
 require(zeros.prepare(positive).status==GameplayPrepareStatus::rejected && zeros.prepare(negative).status==GameplayPrepareStatus::retry,
         "runtime exact retries preserve signed-zero distinctions across codec and database");
 require(zeros.close().ok,"signed-zero owner closes");
}
void event_identity_preflight(const std::filesystem::path& folder) {
 const auto owner=scope();const auto entity=new_uuid();GameplayWorld world(folder/"event-identities.sqlite",owner,schemas());
 const auto first=change(owner,entity);require(world.publish(world.prepare(first).change).ok,"event identity first publication");
 auto duplicate=change(owner,entity,1);duplicate.events[0].event_id=first.events[0].event_id;
 unsigned failures=0;
 if(world.prepare(duplicate).status!=GameplayPrepareStatus::rejected) { ++failures;std::cerr<<"REGRESSION: duplicate pending event identity was prepared\n"; }
 require(committed(completion(world)),"event identity first durable commit");
 if(world.prepare(duplicate).status!=GameplayPrepareStatus::rejected) { ++failures;std::cerr<<"REGRESSION: duplicate durable event identity was prepared\n"; }
 require(world.prepare(first).status==GameplayPrepareStatus::retry,"exact operation retry precedes event identity checks");
 require(world.close().ok,"event identity owner closes");
 const auto race_scope=scope();const auto path=folder/"event-identity-winner.sqlite";GameplayWorld racing(path,race_scope,schemas());
 auto candidate=change(race_scope,entity);const auto prepared=racing.prepare(candidate);
 auto winner=candidate;winner.operation_id="other-owner-winner";winner.events[0].operation_id=winner.operation_id;
 { GameplayStore external(path,race_scope,schemas());require(external.commit(winner).status==GameplayStoreStatus::committed,"another owner commits the proposed event first"); }
 const auto before=racing.snapshot();
 if(racing.publish(prepared.change).ok || racing.snapshot()!=before) { ++failures;std::cerr<<"REGRESSION: event identity was not rechecked before visible publication\n"; }
 (void)racing.close();
 require(failures==0,"event identity preflight regressions failed");
}
void aggregate_replacement_budget(const std::filesystem::path& folder) {
 constexpr std::size_t maximum=64*1024*1024;
 const auto owner=scope();std::vector<ComponentSchema> definitions={{"large.Component",1,{}}};
 ComponentRecord large{new_uuid(),"large.Component",1,{}};
 for(unsigned i=0;i<64;++i) {
  const auto name="field-"+std::to_string(i);definitions[0].fields.push_back({name,GameplayValueKind::text,false});large.fields.emplace(name,std::string(4096,'x'));
 }
 const auto big_size=gameplay_codec::encode_component(large).size();
 ComponentRecord tiny{new_uuid(),"large.Component",1,{}};const auto small_size=gameplay_codec::encode_component(tiny).size();
 const auto count=(maximum-small_size)/big_size;
 require(count>1 && maximum-(count*big_size+small_size)<big_size-small_size,"boundary fixture has less free space than the first replacement growth");
 GameplayStoreBaseline baseline;
 for(std::size_t i=0;i<count;++i) { auto record=large;record.entity_id=new_uuid();baseline.components.push_back(std::move(record)); }
 const auto shrink_id=baseline.components[0].entity_id;baseline.components.push_back(tiny);
 const auto path=folder/"aggregate-budget.sqlite";
 { GameplayStore seeded(path,owner,definitions);require(seeded.seed(baseline).status==GameplayStoreStatus::committed,"near-limit component baseline seeded"); }
 GameplayWorld world(path,owner,definitions);GameplayChangeBatch proposal;proposal.scope=owner;proposal.operation_id="atomic-size-swap";proposal.revision=1;
 auto grow=large;grow.entity_id=tiny.entity_id;auto shrink=tiny;shrink.entity_id=shrink_id;
 proposal.deltas={{ComponentAction::upsert,grow},{ComponentAction::upsert,shrink}};
 SemanticEvent event;event.event_id=new_uuid();event.scope=owner;event.sequence=1;event.operation_id=proposal.operation_id;
 event.subject_ids={tiny.entity_id};event.source_revision=1;event.provenance.source_id="atomic.swap.v1";event.payload=RouteOutcome{tiny.entity_id,true};proposal.events.push_back(event);
 const auto prepared=world.prepare(proposal);
 require(prepared.status==GameplayPrepareStatus::prepared && prepared.change->snapshot()->components.size()==baseline.components.size() && world.snapshot()->revision==0,
         "atomic grow/shrink replacements must use final aggregate bytes rather than request order");
 require(world.close().ok,"unpublished boundary preparation leaves baseline saved");
}
}
int main(int argc,char** argv) {
 try {
  const auto directory=std::filesystem::temp_directory_path()/("aibs-gameplay-world-"+new_uuid());std::filesystem::create_directories(directory);
  if(argc>1 && std::string(argv[1])=="--event-identity") { event_identity_preflight(directory);return 0; }
  if(argc>1 && std::string(argv[1])=="--aggregate-budget") { aggregate_replacement_budget(directory);return 0; }
  prepare_publish_restart(directory);visibility_and_backpressure(directory);rule_isolation_and_targets(directory);failures_and_long_lived_receipts(directory);
  event_identity_preflight(directory);aggregate_replacement_budget(directory);
  std::cout<<"PASS: authoritative prepared/published gameplay world, real durable acknowledgements, bounds, failures and restart\n";return 0;
 }catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}
}
