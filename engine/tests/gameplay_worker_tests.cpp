#include <aibs/gameplay_worker.hpp>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>

using namespace aibs;
namespace {
void require(bool condition,const char* message) { if(!condition) throw std::runtime_error(message); }
struct Workspace {
 std::filesystem::path path=std::filesystem::temp_directory_path()/("aibs-worker-test-"+new_uuid());
 Workspace() { std::filesystem::create_directories(path); }
 ~Workspace() {
  std::error_code error;
  if(path.parent_path()==std::filesystem::temp_directory_path() && path.filename().wstring().starts_with(L"aibs-worker-test-"))
   std::filesystem::remove_all(path,error);
 }
};
GameplayScope scope() { return {"first-boot",new_uuid(),"main",new_uuid(),GameplayContext::player_world}; }
std::vector<ComponentSchema> schemas() {
 return {{"firstboot.Power",1,{{"capacity",GameplayValueKind::number,true,0,100},{"note",GameplayValueKind::text,false}}}};
}
std::shared_ptr<GameplayChangeBatch> batch(const GameplayScope& owner,const std::string& entity,std::uint64_t before=0) {
 auto result=std::make_shared<GameplayChangeBatch>();
 result->scope=owner; result->operation_id="repair-"+std::to_string(before+1); result->expected_revision=before; result->revision=before+1;
 result->deltas.push_back({ComponentAction::upsert,{entity,"firstboot.Power",1,{{"capacity",100.0}}}});
 SemanticEvent event;
 event.event_id=new_uuid(); event.scope=owner; event.sequence=before+1; event.operation_id=result->operation_id;
 event.subject_ids={entity}; event.source_revision=result->revision; event.payload=RepairOutcome{entity,0,100};
 event.provenance={GameplayProvenance::gameplay_rule,"worker-fixture.v1"}; result->events.push_back(std::move(event));
 return result;
}
template<class Predicate> void await(Predicate predicate,const char* message) {
 const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);
 while(!predicate()) {
  if(std::chrono::steady_clock::now()>deadline) throw std::runtime_error(message);
  std::this_thread::sleep_for(std::chrono::milliseconds(2));
 }
}
GameplaySaveCompletion completion(GameplaySaveWorker& worker) {
 std::optional<GameplaySaveCompletion> item;
 await([&]{item=worker.poll();return item.has_value();},"worker completion timeout");
 return std::move(*item);
}
bool success(const GameplaySaveCompletion& result) {
 return result.result.status==GameplayStoreStatus::committed || result.result.status==GameplayStoreStatus::retry;
}
void basic_and_immutability(const Workspace& files) {
 const auto owner=scope(); const auto entity=new_uuid(); const auto path=files.path/"basic.sqlite";
 GameplaySaveWorker worker(path,owner,schemas());
 require(worker.initial_state().revision==0 && worker.initial_state().components.empty(),"worker opens and recovers before accepting work");
 auto first=batch(owner,entity);
 require(worker.submit(first).status==WorkerSubmitStatus::accepted,"immutable save batch accepted");
 first->deltas[0].component.fields["capacity"]=50.0; // Mutable alias must not affect the worker snapshot.
 const auto saved=completion(worker);
 require(success(saved) && saved.scope==owner && saved.operation_id=="repair-1" && saved.revision==1 && saved.sequence==1,
  "completion carries actual committed scope operation revision and sequence");
 require(saved.result.acknowledgement.phase==GameplayPhase::durably_committed,"only actual store commit emits durable acknowledgement");
 require(worker.state().charged_items==0 && worker.state().charged_bytes==0,"draining completion releases its queue credits");
 require(worker.close().ok,"explicit close joins after successful ordered flush");
 GameplayStore store(path,owner,schemas()); const auto recovered=store.recover();
 require(recovered.revision==1 && recovered.components.size()==1 && std::get<double>(recovered.components[0].fields.at("capacity"))==100,
  "worker deep copy survives caller mutable alias and actual SQLite restart");
 GameplaySaveWorker restarted(path,owner,schemas());
 require(restarted.initial_state().revision==1 && restarted.initial_state().components==recovered.components,"worker startup exposes recovered immutable baseline");
 require(restarted.close().ok,"restarted worker closes cleanly");
}
void bounded_inflight_and_completions(const Workspace& files) {
 const auto owner=scope(); const auto entity=new_uuid(); const auto path=files.path/"bounded.sqlite";
 const auto owner_thread=std::this_thread::get_id();
 std::mutex mutex; std::condition_variable condition; bool entered=false,released=false;
 const auto observer=[&](GameplayStoreStage stage) {
  if(stage!=GameplayStoreStage::before_commit) return;
  require(std::this_thread::get_id()!=owner_thread,"actual SQLite commit runs on its dedicated worker thread");
  std::unique_lock lock(mutex); entered=true; condition.notify_all();
  if(!condition.wait_for(lock,std::chrono::seconds(10),[&]{return released;})) throw std::runtime_error("fixture gate timeout");
 };
 GameplayWorkerLimits limits; limits.items=2;
 GameplaySaveWorker worker(path,owner,schemas(),limits,observer);
 const auto first=batch(owner,entity),second=batch(owner,entity,1),third=batch(owner,entity,2);
 require(worker.submit(first).status==WorkerSubmitStatus::accepted,"first queue slot accepted");
 {
  std::unique_lock lock(mutex);
  require(condition.wait_for(lock,std::chrono::seconds(10),[&]{return entered;}),"actual SQLite precommit gate reached on worker thread");
 }
 require(worker.state().in_flight==1 && worker.state().charged_items==1,"inflight entry retains queue credit");
 require(worker.submit(first).status==WorkerSubmitStatus::retry,"retained exact request retry does not allocate another queue slot");
 auto conflicting=std::make_shared<GameplayChangeBatch>(*first); conflicting->deltas[0].component.fields["capacity"]=50.0;
 require(worker.submit(conflicting).status==WorkerSubmitStatus::rejected,"conflicting retained operation reuse rejected");
 require(worker.submit(second).status==WorkerSubmitStatus::accepted && worker.submit(third).status==WorkerSubmitStatus::backpressure,
  "queued plus inflight items share bounded capacity");
 const auto full=worker.state();
 require(full.charged_items==2 && full.charged_bytes>0,"all admitted value and completion storage is byte charged");
 {
  std::lock_guard lock(mutex); released=true;
 }
 condition.notify_all();
 await([&]{return worker.state().completed==2;},"completed queue did not fill");
 require(worker.state().charged_items==2 && worker.state().charged_bytes==full.charged_bytes && worker.submit(third).status==WorkerSubmitStatus::backpressure,
  "undrained completions retain both item and byte credits");
 require(completion(worker).revision==1 && worker.state().charged_items==1 && worker.state().charged_bytes>0 && worker.state().charged_bytes<full.charged_bytes,
  "first completion drains its item and byte credits in admission order");
 require(completion(worker).revision==2 && worker.state().charged_items==0 && worker.state().charged_bytes==0,"second completion drains remaining credits in order");
 require(worker.submit(third).status==WorkerSubmitStatus::accepted,"draining bounded completions enables later submission");
 require(worker.close().ok,"close flushes pending third batch and joins");
 require(success(completion(worker)) && worker.state().charged_items==0,"completion remains drainable after close");
 require(worker.submit(batch(owner,entity,3)).status==WorkerSubmitStatus::closed,"closed worker rejects new work");
 GameplayStore store(path,owner,schemas()); require(store.recover().revision==3,"actual SQLite transactions committed all ordered batches");
}
void failure_retry_and_close(const Workspace& files) {
 const auto owner=scope(); const auto entity=new_uuid(); const auto path=files.path/"retry.sqlite";
 std::atomic<int> attempts=0;
 GameplaySaveWorker worker(path,owner,schemas(),{},[&](GameplayStoreStage stage) {
  if(stage==GameplayStoreStage::before_commit && attempts.fetch_add(1)==0) throw std::runtime_error("injected real transaction rollback");
 });
 const auto first=batch(owner,entity),second=batch(owner,entity,1);
 require(worker.submit(first).status==WorkerSubmitStatus::accepted && worker.submit(second).status==WorkerSubmitStatus::accepted,"failure fixture queues ordered batches");
 await([&]{return worker.state().blocked;},"save failure did not block queue");
 require(!worker.retry_failed().ok,"failure completion must be drained before retry");
 const auto failed=completion(worker);
 require(!success(failed) && failed.revision==1 && worker.state().charged_items==2 && worker.state().queued==1,
  "failed head remains charged and later batch cannot skip it");
 require(!worker.poll() && worker.retry_failed().ok,"explicit retry requeues the exact failed head");
 require(success(completion(worker)) && success(completion(worker)),"retry commits failed head then later batch in order");
 require(worker.close().ok && worker.state().charged_items==0,"successful retries fully drain and close");
 GameplayStore store(path,owner,schemas()); require(store.recover().revision==2,"SQLite recovery proves rollback then ordered retry");
 const auto blocked_path=files.path/"blocked.sqlite"; const auto other=scope();
 GameplaySaveWorker blocked(blocked_path,other,schemas(),{},[](GameplayStoreStage stage) {
  if(stage==GameplayStoreStage::before_commit) throw std::runtime_error("persistent commit failure");
 });
 require(blocked.submit(batch(other,entity)).status==WorkerSubmitStatus::accepted &&
         blocked.submit(batch(other,entity,1)).status==WorkerSubmitStatus::accepted,"persistent failure queue accepted");
 require(!blocked.close().ok && blocked.state().stopped && blocked.state().blocked,"close joins and reports first failure instead of skipping or retrying forever");
 require(!success(completion(blocked)) && !blocked.retry_failed().ok,"failed completion survives close and closed retry is explicit failure");
 GameplayStore untouched(blocked_path,other,schemas()); require(untouched.recover().revision==0,"failed close never publishes the later SQLite batch");
}
void startup_limits_and_destructor(const Workspace& files) {
 const auto owner=scope(); const auto entity=new_uuid();
 const auto directory=files.path/"not-a-database"; std::filesystem::create_directory(directory);
 bool rejected=false;
 try { GameplaySaveWorker bad(directory,owner,schemas()); } catch(const std::exception&) { rejected=true; }
 require(rejected,"worker constructor propagates SQLite open failure and joins startup thread");
 GameplayWorkerLimits tiny; tiny.bytes=1;
 GameplaySaveWorker bounded(files.path/"tiny.sqlite",owner,schemas(),tiny);
 require(bounded.submit(batch(owner,entity)).status==WorkerSubmitStatus::backpressure && bounded.state().charged_items==0,
  "byte budget applies before defensive batch copy or retained completion");
 require(bounded.reserve(batch(owner,entity)).status==WorkerSubmitStatus::backpressure && bounded.state().reserved==0,
  "unpublished reservations require capacity before live world publication");
 auto large=batch(owner,entity); large->deltas[0].component.fields["note"]=std::string(5*1024*1024,'x');
 require(bounded.submit(large).status==WorkerSubmitStatus::rejected && bounded.state().charged_items==0,"untrusted oversized caller batch rejects before defensive copy");
 require(bounded.submit({}).status==WorkerSubmitStatus::rejected && bounded.close().ok,"null batch rejects without poisoning worker");
 const auto path=files.path/"destructor.sqlite";
 {
  GameplaySaveWorker worker(path,owner,schemas());
  require(worker.submit(batch(owner,entity)).status==WorkerSubmitStatus::accepted,"destructor flush fixture admitted");
 }
 GameplayStore store(path,owner,schemas()); require(store.recover().revision==1,"destructor joins worker and best-effort flush commits queued batch");
}
void actual_after_commit_and_database_retry(const Workspace& files) {
 const auto owner=scope(); const auto entity=new_uuid(); const auto path=files.path/"after-commit.sqlite";
 GameplaySaveWorker worker(path,owner,schemas(),{},[](GameplayStoreStage stage) {
  if(stage==GameplayStoreStage::after_commit) throw std::runtime_error("observer failed after actual durable COMMIT");
 });
 const auto first=batch(owner,entity);
 require(worker.submit(first).status==WorkerSubmitStatus::accepted,"after commit fixture accepted");
 require(success(completion(worker)),"postcommit observer failure cannot undo actual commit acknowledgement");
 require(worker.submit(first).status==WorkerSubmitStatus::accepted,"drained operation can use database dedup without unbounded worker receipts");
 const auto retried=completion(worker);
 require(retried.result.status==GameplayStoreStatus::retry,"SQLite exact retry returns prior committed acknowledgement");
 require(worker.close().ok,"postcommit instrumentation does not block clean shutdown");
 GameplayStore store(path,owner,schemas()); require(store.recover().revision==1,"database dedup commits no duplicate semantic history");
}
void observer_close_during_owner_join(const Workspace& files) {
 const auto owner=scope(); const auto entity=new_uuid(); const auto path=files.path/"observer-close.sqlite";
 GameplaySaveWorker* self=nullptr;
 std::atomic<bool> self_rejected=false;
 GameplaySaveWorker worker(path,owner,schemas(),{},[&](GameplayStoreStage stage) {
  if(stage!=GameplayStoreStage::before_commit) return;
  await([&]{return self->state().closed;},"owner close did not publish shutdown before joining");
  std::cout<<"PROBE: owner close published; observer attempting self-close\n"<<std::flush;
  self_rejected=!self->close().ok;
 });
 self=&worker;
 require(worker.submit(batch(owner,entity)).status==WorkerSubmitStatus::accepted,"observer-close fixture accepted");
 require(worker.close().ok && self_rejected,"observer self-close rejects without deadlocking owner join");
 require(success(completion(worker)),"observer self-close rejection preserves actual SQLite commit completion");
 GameplayStore store(path,owner,schemas()); require(store.recover().revision==1,"owner close flush commits despite observer self-close attempt");
}
void reserved_publication_and_cancel(const Workspace& files) {
 const auto owner=scope(); const auto entity=new_uuid(); const auto path=files.path/"reserved.sqlite";
 std::atomic<int> transactions=0;
 GameplaySaveWorker worker(path,owner,schemas(),{},[&](GameplayStoreStage stage) {
  if(stage==GameplayStoreStage::before_commit) ++transactions;
 });
 auto first=batch(owner,entity);
 const auto exact=std::make_shared<GameplayChangeBatch>(*first);
 require(worker.reserve(first).status==WorkerSubmitStatus::accepted,"storage credits reserve before visible world publication");
 first->deltas[0].component.fields["capacity"]=50.0;
 const auto held=worker.state();
 require(held.reserved==1 && held.queued==0 && held.charged_items==1 && held.charged_bytes>0,"reservation is immutable charged storage with no dispatch");
 require(worker.reserve(exact).status==WorkerSubmitStatus::retry && worker.state().reserved==1,"exact reservation retry cannot publish or duplicate its entry");
 require(!worker.publish_reserved("foreign-operation") && !worker.cancel_reserved("foreign-operation") &&
         worker.state().charged_bytes==held.charged_bytes,"unknown publication/cancellation leaves reservation credits intact");
 auto foreign=std::make_shared<GameplayChangeBatch>(*exact); foreign->scope.timeline_id=new_uuid();
 require(worker.reserve(foreign).status==WorkerSubmitStatus::rejected && worker.state().charged_bytes==held.charged_bytes,
  "foreign scope reservation cannot alter the retained owner entry");
 {
  GameplayStore reader(path,owner,schemas());
  require(reader.recover().revision==0 && transactions==0,"actual SQLite head remains unchanged before world publication");
 }
 require(worker.publish_reserved(exact->operation_id) && worker.publish_reserved(exact->operation_id),"publication is idempotent for a retained reservation or active entry");
 await([&]{return worker.state().completed==1;},"published reservation did not commit");
 require(worker.state().reserved==0 && worker.state().charged_bytes==held.charged_bytes,"published completion retains all reservation credits until drained");
 require(!worker.cancel_reserved(exact->operation_id),"published reservation cannot be canceled after dispatch");
 require(success(completion(worker)) && transactions==1 && worker.state().charged_items==0,"one activation yields exactly one actual transaction and refundable completion");
 const auto second=batch(owner,entity,1);
 require(worker.reserve(second).status==WorkerSubmitStatus::accepted && worker.cancel_reserved(second->operation_id),"unpublished reservation can be canceled before world changes");
 require(worker.state().charged_items==0 && worker.state().charged_bytes==0 && !worker.cancel_reserved(second->operation_id),"cancellation refunds once without creating history");
 require(worker.reserve(second).status==WorkerSubmitStatus::accepted && worker.submit(second).status==WorkerSubmitStatus::retry,
  "combined submit can publish an exact existing reservation");
 require(worker.close().ok && success(completion(worker)) && transactions==2,"combined publication flushes exactly once");
 GameplayStore store(path,owner,schemas());
 const auto recovered=store.recover();
 require(recovered.revision==2 && std::get<double>(recovered.components[0].fields.at("capacity"))==100,
  "published immutable reservation survives SQLite restart; cancellation adds no revision");
}
void reservation_order_and_shutdown(const Workspace& files) {
 const auto owner=scope(); const auto entity=new_uuid(); const auto path=files.path/"reserved-close.sqlite";
 GameplaySaveWorker worker(path,owner,schemas());
 require(worker.reserve(batch(owner,entity)).status==WorkerSubmitStatus::accepted &&
         worker.submit(batch(owner,entity,1)).status==WorkerSubmitStatus::accepted,"later visible work queues behind an unpublished reservation");
 require(worker.state().reserved==1 && worker.state().queued==1,"earlier reservation is a dispatch barrier");
 require(!worker.close().ok && worker.state().stopped && worker.state().reserved==1 && worker.state().queued==1 && !worker.poll(),
  "close joins at reserved barrier without dispatching unpublished or later batches");
 require(!worker.publish_reserved("repair-1"),"closed worker cannot activate an unpublished world change");
 GameplayStore store(path,owner,schemas()); require(store.recover().revision==0,"reserved close preserves actual empty durable SQLite head");
 const auto destructor_path=files.path/"reserved-destructor.sqlite";
 {
  GameplaySaveWorker unsubmitted(destructor_path,owner,schemas());
  require(unsubmitted.reserve(batch(owner,entity)).status==WorkerSubmitStatus::accepted &&
          unsubmitted.submit(batch(owner,entity,1)).status==WorkerSubmitStatus::accepted,"reserved destructor fixture accepted");
 }
 GameplayStore unsubmitted_store(destructor_path,owner,schemas());
 require(unsubmitted_store.recover().revision==0,"destructor joins without publishing reservations or queued successors");
 const auto published_path=files.path/"reserved-ordered.sqlite";
 GameplaySaveWorker published(published_path,owner,schemas());
 require(published.reserve(batch(owner,entity)).status==WorkerSubmitStatus::accepted &&
         published.submit(batch(owner,entity,1)).status==WorkerSubmitStatus::accepted && published.publish_reserved("repair-1"),
  "publishing head unlocks later queued work");
 require(published.close().ok && completion(published).revision==1 && completion(published).revision==2,"reserved then queued work commits in order after explicit publication");
 const auto partial_path=files.path/"reserved-partial.sqlite";
 GameplaySaveWorker partial(partial_path,owner,schemas());
 require(partial.submit(batch(owner,entity)).status==WorkerSubmitStatus::accepted &&
         partial.reserve(batch(owner,entity,1)).status==WorkerSubmitStatus::accepted &&
         partial.submit(batch(owner,entity,2)).status==WorkerSubmitStatus::accepted,"partial close fixture accepted");
 require(!partial.close().ok && completion(partial).revision==1 && partial.state().reserved==1 && partial.state().queued==1,
  "close flushes earlier published work and stops precisely at unpublished barrier");
 GameplayStore partial_store(partial_path,owner,schemas()); require(partial_store.recover().revision==1,"later queued revision never overtakes reserved predecessor during shutdown");
}
}
int main(int argc,char** argv) {
 try {
  const Workspace files;
  if(argc>1 && std::string(argv[1])=="--close-reentrancy-probe") { observer_close_during_owner_join(files); return 0; }
  basic_and_immutability(files); bounded_inflight_and_completions(files); failure_retry_and_close(files);
  startup_limits_and_destructor(files); actual_after_commit_and_database_retry(files);
  observer_close_during_owner_join(files);
  reserved_publication_and_cancel(files); reservation_order_and_shutdown(files);
  std::cout<<"PASS: actual SQLite async commits, immutable bounded worker, reserve/publish/cancel barriers, ordered failure retry, completion credits, startup and shutdown\n";
  return 0;
 } catch(const std::exception& error) { std::cerr<<"FAIL: "<<error.what()<<'\n'; return 1; }
}
