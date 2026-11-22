#include <aibs/gameplay_world.hpp>
#include <aibs/gameplay_codec.hpp>
#include <atomic>
#include <list>
#include <set>
#include <stdexcept>
#include <thread>

namespace aibs {
namespace {
constexpr std::size_t state_bytes=64*1024*1024,component_count=10000;
using ComponentKey=std::pair<std::string,std::string>;
void require(bool value,const char* message) { if(!value) throw std::invalid_argument(message); }
struct BusyGuard {
 bool& busy;
 explicit BusyGuard(bool& flag):busy(flag) { require(!busy,"Reentrant gameplay world operation");busy=true; }
 ~BusyGuard() { busy=false; }
};
bool success(GameplayStoreStatus status) { return status==GameplayStoreStatus::committed || status==GameplayStoreStatus::retry; }
std::string diagnostic(const std::exception& error) {
 const auto* message=error.what();std::size_t size=0;
 if(message) while(size<4096 && message[size]!='\0') ++size;
 return message?std::string(message,size):std::string("Gameplay operation failed");
}
bool exact_state(const GameplayStoreRecovery& left,const GameplayStoreRecovery& right) {
 if(left.scope!=right.scope || left.revision!=right.revision || left.sequence!=right.sequence || left.components.size()!=right.components.size()) return false;
 for(std::size_t i=0;i<left.components.size();++i)
  if(gameplay_codec::encode_component(left.components[i])!=gameplay_codec::encode_component(right.components[i])) return false;
 return true;
}
std::shared_ptr<const GameplayStoreRecovery> apply(const GameplayStoreRecovery& before,const GameplayChangeBatch& batch) {
 std::map<ComponentKey,ComponentRecord> values;std::map<ComponentKey,std::size_t> charges;std::size_t bytes=0;
 for(const auto& record:before.components) {
  const auto encoded=gameplay_codec::encode_component(record);
  require(values.size()<component_count && encoded.size()<=state_bytes-bytes,"Initial gameplay world exceeds component/byte bounds");
  const ComponentKey key{record.entity_id,record.type_id};
  require(values.emplace(key,record).second,"Duplicate component identity in gameplay world");charges.emplace(key,encoded.size());bytes+=encoded.size();
 }
 // Remove every replaced or erased record first. Unique atomic deltas commute;
 // the insertion budget then depends on final state, never request order.
 for(const auto& delta:batch.deltas) {
  const ComponentKey key{delta.component.entity_id,delta.component.type_id};
  if(const auto found=charges.find(key);found!=charges.end()) { bytes-=found->second;charges.erase(found);values.erase(key); }
 }
 for(const auto& delta:batch.deltas) if(delta.action==ComponentAction::upsert) {
  const auto& record=delta.component;const ComponentKey key{record.entity_id,record.type_id};
  const auto encoded=gameplay_codec::encode_component(record);const auto found=charges.find(key);
  const auto previous=found==charges.end()?0:found->second;
  require((found!=charges.end() || values.size()<component_count) && encoded.size()<=state_bytes-(bytes-previous),
          "Projected gameplay world exceeds 10000 components or 64 MiB encoded state");
  values[key]=record;charges[key]=encoded.size();bytes=bytes-previous+encoded.size();
 }
 GameplayStoreRecovery result{before.scope,batch.revision,batch.events.back().sequence,{}};result.components.reserve(values.size());
 for(auto& [unused,record]:values) { (void)unused;result.components.push_back(std::move(record)); }
 return std::make_shared<const GameplayStoreRecovery>(std::move(result));
}
}
struct GameplayWorld::Impl {
 struct Pending { std::shared_ptr<const GameplayChangeBatch> batch; };
 const std::thread::id owner_thread=std::this_thread::get_id();
 const std::string owner_id=new_uuid();
 GameplayScope scope;
 std::vector<ComponentSchema> schemas;
 std::unique_ptr<GameplaySaveWorker> worker;
 std::unique_ptr<GameplayStore> reader;
 std::atomic<std::shared_ptr<const GameplayStoreRecovery>> visible;
 std::list<Pending> pending;
 std::uint64_t durable_revision=0,durable_sequence=0;
 bool busy=false,closed=false,failed=false,fatal=false;
 std::string error;
 Impl(const std::filesystem::path& path,GameplayScope owner,std::vector<ComponentSchema> definitions,
      GameplayWorkerLimits limits,GameplayStoreObserver observer):scope(std::move(owner)) {
  schemas=gameplay_codec::decode_schemas(gameplay_codec::encode_schemas(definitions));
  GameplayAdmission validation(scope,schemas);
  worker=std::make_unique<GameplaySaveWorker>(path,scope,schemas,limits,std::move(observer));
  auto initial=worker->initial_state();require(initial.scope==scope,"Worker restored a foreign gameplay scope");
  reader=std::make_unique<GameplayStore>(path,scope,schemas);
  require(exact_state(initial,reader->recover()),"Gameplay database changed during runtime startup; reopen before continuing");
  durable_revision=initial.revision;durable_sequence=initial.sequence;
  visible.store(std::make_shared<const GameplayStoreRecovery>(std::move(initial)),std::memory_order_release);
 }
 bool owner() const noexcept { return std::this_thread::get_id()==owner_thread; }
 std::shared_ptr<const GameplayStoreRecovery> snapshot() const noexcept { return visible.load(std::memory_order_acquire); }
 enum class Existing { none,exact,conflict };
 Existing existing(const GameplayChangeBatch& batch) const {
  for(const auto& item:pending) if(item.batch->operation_id==batch.operation_id)
   return gameplay_batch_exact(*item.batch,batch)?Existing::exact:Existing::conflict;
  if(const auto durable=reader->lookup_batch(batch.operation_id))
   return gameplay_batch_exact(*durable,batch)?Existing::exact:Existing::conflict;
  return Existing::none;
 }
 void new_events(const GameplayChangeBatch& batch) const {
  for(const auto& event:batch.events) {
   for(const auto& item:pending)
    for(const auto& accepted:item.batch->events)
     require(event.event_id!=accepted.event_id,"Semantic event UUID already belongs to a pending gameplay operation");
   require(!reader->contains_event(event.event_id),"Semantic event UUID already belongs to durable gameplay history");
  }
 }
 void consume(const GameplaySaveCompletion& completion) {
  auto bad=[&](const char* message) { fatal=failed=true;error=message; };
  if(pending.empty()) { bad("Unexpected save completion without a published gameplay batch");return; }
  const auto& expected=*pending.front().batch;
  if(completion.scope!=scope || completion.operation_id!=expected.operation_id || completion.revision!=expected.revision ||
     completion.sequence!=expected.events.back().sequence) { bad("Save completion scope, operation, revision or sequence is out of order");return; }
  if(!success(completion.result.status)) { failed=true;error=completion.result.message.substr(0,4096);return; }
  const auto& acknowledged=completion.result.acknowledgement;
  if(acknowledged.scope!=scope || acknowledged.operation_id!=expected.operation_id || acknowledged.revision!=expected.revision ||
     acknowledged.phase!=GameplayPhase::durably_committed || expected.expected_revision!=durable_revision ||
     durable_sequence==std::numeric_limits<std::uint64_t>::max() || expected.events.front().sequence!=durable_sequence+1) {
   bad("Save completion does not prove the next ordered durable gameplay head");return;
  }
  if(fatal) return;
  durable_revision=expected.revision;durable_sequence=expected.events.back().sequence;pending.pop_front();failed=false;error.clear();
 }
};
GameplayWorld::GameplayWorld(const std::filesystem::path& path,GameplayScope scope,std::vector<ComponentSchema> schemas,
                             GameplayWorkerLimits limits,GameplayStoreObserver observer)
 :impl_(std::make_unique<Impl>(path,std::move(scope),std::move(schemas),limits,std::move(observer))) {}
GameplayWorld::~GameplayWorld() { try { if(impl_ && impl_->worker) impl_->worker->close(); }catch(...) {} }
std::shared_ptr<const GameplayStoreRecovery> GameplayWorld::snapshot() const noexcept { return impl_->snapshot(); }
GameplayPrepareResult GameplayWorld::prepare(const GameplayChangeBatch& batch,GameplayRuleValidator validator) {
 auto& p=*impl_;
 if(!p.owner()) return {GameplayPrepareStatus::rejected,"Gameplay preparation requires the simulation owner thread",{}};
 try {
  BusyGuard guard(p.busy);require(!p.closed,"Gameplay world is closed");
  // Canonical snapshot severs every mutable caller alias before a rule callback.
  const auto encoded=gameplay_codec::encode_batch(batch);
  auto immutable=std::make_shared<const GameplayChangeBatch>(gameplay_codec::decode_batch(encoded));
  require(immutable->scope==p.scope,"Foreign gameplay world scope");
  const auto existing=p.existing(*immutable);
  if(existing==Impl::Existing::exact) return {GameplayPrepareStatus::retry,"Exact published or durably committed request; no world change",{}};
  require(existing!=Impl::Existing::conflict,"Operation ID was already used for different content");
  require(!p.failed && !p.fatal,"Resolve the failed save head before publishing more gameplay");
  p.new_events(*immutable);
  const auto before=p.snapshot();std::set<std::string> targets;
  for(const auto& record:before->components) targets.insert(record.entity_id);
  for(const auto& delta:immutable->deltas) if(delta.action==ComponentAction::upsert) targets.insert(delta.component.entity_id);
  GameplayLimits limits;limits.pending_batches=limits.receipts=1;limits.pending_bytes=limits.receipt_bytes=state_bytes;
  GameplayAdmission validation(p.scope,p.schemas,limits,before->revision,before->sequence);
  const auto admitted=validation.reserve(*immutable,[&](const auto& id){return targets.contains(id);});
  require(admitted.status==AdmissionStatus::accepted,admitted.message.c_str());
  const auto after=apply(*before,*immutable);
  if(validator) validator(*before,*after,*immutable);
  std::shared_ptr<const PreparedGameplayChange> prepared(new PreparedGameplayChange(p.owner_id,before,after,std::move(immutable)));
  return {GameplayPrepareStatus::prepared,"Prepared immutable gameplay change; not published or saved",std::move(prepared)};
 }catch(const std::exception& error) { return {GameplayPrepareStatus::rejected,diagnostic(error),{}}; }
 catch(...) { return {GameplayPrepareStatus::rejected,"Unknown gameplay preparation or rule failure",{}}; }
}
Result GameplayWorld::publish(std::shared_ptr<const PreparedGameplayChange> change) {
 auto& p=*impl_;
 if(!p.owner()) return {false,"Gameplay publication requires the simulation owner thread",snapshot()->revision};
 try {
  BusyGuard guard(p.busy);require(!p.closed,"Gameplay world is closed");
  require(change && change->owner_==p.owner_id && change->batch_ && change->after_,"Prepared token belongs to another gameplay owner");
  const auto existing=p.existing(*change->batch_);
  if(existing==Impl::Existing::exact) return {true,"Exact prior publication; no additional world or save change",change->batch_->revision};
  require(existing!=Impl::Existing::conflict,"Operation ID was already used for different content");
  require(!p.failed && !p.fatal,"Resolve the failed save head before publication");
  require(p.snapshot()==change->before_,"Prepared gameplay token is stale; prepare against the current world");
  p.new_events(*change->batch_);
  std::list<Impl::Pending> staged;staged.push_back({change->batch_});
  Result result{true,"Gameplay visible; waiting for a real durable save completion",change->batch_->revision};
  const auto reserved=p.worker->reserve(change->batch_);
  require(reserved.status==WorkerSubmitStatus::accepted,reserved.message.c_str());
  // These operations allocate no value storage. The reserved worker entry
  // cannot reach SQLite until the visible world and pending order are installed.
  p.pending.splice(p.pending.end(),staged);
  p.visible.store(change->after_,std::memory_order_release);
  bool activated=false;
  try { activated=p.worker->publish_reserved(change->batch_->operation_id); }
  catch(...) {
   p.visible.store(change->before_,std::memory_order_release);p.pending.pop_back();p.worker->cancel_reserved(change->batch_->operation_id);throw;
  }
  if(!activated) {
   p.visible.store(change->before_,std::memory_order_release);p.pending.pop_back();p.worker->cancel_reserved(change->batch_->operation_id);
   return {false,"Save reservation could not activate; visible publication was rolled back",change->before_->revision};
  }
  return result;
 }catch(const std::exception& error) { return {false,diagnostic(error),snapshot()->revision}; }
 catch(...) { return {false,"Unknown gameplay publication failure",snapshot()->revision}; }
}
std::optional<GameplaySaveCompletion> GameplayWorld::poll() {
 auto& p=*impl_;if(!p.owner() || p.busy) return {};
 try { BusyGuard guard(p.busy);auto result=p.worker->poll();if(result) p.consume(*result);return result; }
 catch(const std::exception& error) { p.failed=true;p.error=diagnostic(error);return {}; }
 catch(...) { p.failed=true;p.error="Unknown gameplay save completion failure";return {}; }
}
GameplayWorldState GameplayWorld::state() const {
 const auto& p=*impl_;require(p.owner(),"Gameplay status requires the simulation owner thread");
 const auto visible=p.snapshot();GameplayWorldState state;
 state.visible_revision=visible->revision;state.visible_sequence=visible->sequence;
 state.durable_revision=p.durable_revision;state.durable_sequence=p.durable_sequence;state.pending_batches=p.pending.size();
 state.worker=p.worker->state();state.pending_bytes=state.worker.charged_bytes;
 state.failed=p.failed;state.closed=p.closed;state.error=p.error;
 state.saved=!state.failed && p.pending.empty() && state.visible_revision==state.durable_revision && state.visible_sequence==state.durable_sequence;
 return state;
}
std::vector<GameplayChangeBatch> GameplayWorld::read_batches(std::uint64_t after_revision,std::size_t max_batches,std::size_t max_bytes) const {
 auto& p=*impl_;require(p.owner(),"Gameplay history requires the simulation owner thread");BusyGuard guard(p.busy);
 return p.reader->read_batches(after_revision,max_batches,max_bytes);
}
Result GameplayWorld::retry_pending() {
 auto& p=*impl_;if(!p.owner()) return {false,"Gameplay retry requires the simulation owner thread",snapshot()->revision};
 try {
  BusyGuard guard(p.busy);require(!p.closed && !p.fatal,"Closed or inconsistent gameplay owner requires recovery");
  require(p.failed && !p.pending.empty(),"No failed gameplay save head is pending");
  const auto retried=p.worker->retry_failed();if(retried.ok) { p.failed=false;p.error.clear(); }return retried;
 }catch(const std::exception& error) { return {false,diagnostic(error),p.durable_revision}; }
 catch(...) { return {false,"Unknown gameplay retry failure",p.durable_revision}; }
}
Result GameplayWorld::close() {
 auto& p=*impl_;if(!p.owner()) return {false,"Gameplay close requires the simulation owner thread",snapshot()->revision};
 try {
  BusyGuard guard(p.busy);const auto flushed=p.worker->close();p.closed=true;
  while(const auto completed=p.worker->poll()) p.consume(*completed);
  const bool complete=flushed.ok && p.pending.empty() && !p.failed && !p.fatal;
  return {complete,complete?"Published gameplay and semantic events committed; owner closed":"Gameplay owner closed with unsaved work: "+(p.error.empty()?flushed.message:p.error),p.durable_revision};
 }catch(const std::exception& error) { return {false,diagnostic(error),p.durable_revision}; }
 catch(...) { return {false,"Unknown gameplay close failure",p.durable_revision}; }
}
}
