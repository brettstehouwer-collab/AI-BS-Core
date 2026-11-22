#include <aibs/gameplay_worker.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <condition_variable>
#include <future>
#include <list>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <type_traits>

namespace aibs {
static_assert(std::is_nothrow_move_constructible_v<GameplaySaveCompletion>);
namespace {
bool committed(GameplayStoreStatus status) { return status==GameplayStoreStatus::committed || status==GameplayStoreStatus::retry; }
std::size_t charge(const GameplayChangeBatch& batch,const gameplay_codec::Bytes& encoded) {
 // Includes encoded retry identity, decoded value data, map/vector allocations
 // and bounded completion/error metadata. This is conservative charged storage,
 // rather than an allocator/RSS promise. Encoder already enforces hard bounds.
 std::size_t bytes=8192+encoded.capacity()+2*encoded.size();
 for(const auto& delta:batch.deltas) bytes+=256+128*delta.component.fields.size();
 for(const auto& event:batch.events) bytes+=512+64*event.subject_ids.size();
 return bytes;
}
}
struct GameplaySaveWorker::Impl {
 enum class Phase { reserved,queued,in_flight,completed,failed };
 struct Entry {
  std::shared_ptr<const GameplayChangeBatch> batch;
  gameplay_codec::Bytes encoded;
  std::size_t bytes=0;
  Phase phase=Phase::reserved;
  bool completion_pending=false;
  GameplaySaveCompletion completion;
 };
 GameplayScope scope;
 GameplayWorkerLimits limits;
 mutable std::mutex mutex;
 std::mutex close_mutex;
 std::condition_variable changed;
 std::list<std::unique_ptr<Entry>> entries;
 std::size_t charged_bytes=0;
 bool closing=false,stopped=false;
 std::uint64_t committed_revision=0;
 std::shared_ptr<const GameplayStoreRecovery> initial;
 std::promise<void> startup;
 // Set before startup publication and immutable afterward. Reading std::thread
 // itself here would race another owner call joining and replacing its handle.
 std::thread::id worker_id;
 std::thread thread;

 Impl(GameplayScope owner,GameplayWorkerLimits budgets):scope(std::move(owner)),limits(budgets) {
  if(limits.items==0 || limits.items>256 || limits.bytes==0 || limits.bytes>64*1024*1024)
   throw std::invalid_argument("Save worker limits must be positive and within 256 items / 64 MiB");
 }
 ~Impl() {
  { std::lock_guard lock(mutex); closing=true; }
  changed.notify_all();
  if(thread.joinable()) thread.join();
 }
 Entry* ready() const {
  for(const auto& item:entries) {
   if(item->phase==Phase::reserved || item->phase==Phase::failed) return nullptr;
   if(item->phase==Phase::queued) return item.get();
  }
  return nullptr;
 }
 bool blocked() const {
  return std::any_of(entries.begin(),entries.end(),[](const auto& item){return item->phase==Phase::failed;});
 }
 GameplayWorkerState snapshot() const {
  GameplayWorkerState result;
  result.charged_items=entries.size(); result.charged_bytes=charged_bytes;
  result.closed=closing; result.stopped=stopped;
  for(const auto& item:entries) {
   if(item->phase==Phase::reserved) ++result.reserved;
   if(item->phase==Phase::queued) ++result.queued;
   if(item->phase==Phase::in_flight) ++result.in_flight;
   if(item->completion_pending) ++result.completed;
   if(item->phase==Phase::failed) result.blocked=true;
  }
  return result;
 }
 WorkerSubmitResult admit(const std::shared_ptr<const GameplayChangeBatch>& batch,Phase phase) {
  if(closing) return {WorkerSubmitStatus::closed,"Save worker is closed"};
  if(!batch) return {WorkerSubmitStatus::rejected,"Save worker requires a batch"};
  try {
   if(batch->scope!=scope) return {WorkerSubmitStatus::rejected,"Foreign save worker scope"};
   auto encoded=gameplay_codec::encode_batch(*batch);
   for(const auto& retained:entries) if(retained->batch->operation_id==batch->operation_id) {
    if(retained->encoded!=encoded) return {WorkerSubmitStatus::rejected,"Save operation ID already has different content"};
    WorkerSubmitResult result{WorkerSubmitStatus::retry,"Exact retained save request"};
    if(phase==Phase::queued && retained->phase==Phase::reserved) {
     retained->phase=Phase::queued; changed.notify_all();
    }
    return result;
   }
   const auto bytes=charge(*batch,encoded);
   if(entries.size()>=limits.items || bytes>limits.bytes-charged_bytes)
    return {WorkerSubmitStatus::backpressure,"Save queue item/byte budget exhausted; drain completions or cancel unpublished reservations"};
   auto item=std::make_unique<Entry>();
   item->batch=std::make_shared<const GameplayChangeBatch>(gameplay_codec::decode_batch(encoded));
   item->bytes=bytes; item->encoded=std::move(encoded); item->phase=phase;
   item->completion.scope=item->batch->scope; item->completion.operation_id=item->batch->operation_id;
   item->completion.revision=item->batch->revision; item->completion.sequence=item->batch->events.back().sequence;
   item->completion.result={GameplayStoreStatus::failed,"Save worker did not confirm a commit",{}};
   WorkerSubmitResult result{WorkerSubmitStatus::accepted,phase==Phase::reserved?
    "Save storage reserved; world publication and commit have not occurred":"Save batch queued; not yet durable"};
   entries.push_back(std::move(item)); charged_bytes+=bytes; changed.notify_all();
   return result;
  } catch(const std::exception& error) { return {WorkerSubmitStatus::rejected,error.what()}; }
 }
 void run(const std::filesystem::path& path,std::vector<ComponentSchema> schemas,GameplayStoreObserver observer) noexcept {
  bool opened=false;
  try {
   GameplayStore store(path,scope,std::move(schemas),std::move(observer));
   auto recovered=std::make_shared<const GameplayStoreRecovery>(store.recover());
   {
    std::lock_guard lock(mutex); initial=std::move(recovered); committed_revision=initial->revision;
    worker_id=std::this_thread::get_id();
   }
   startup.set_value(); opened=true;
   std::unique_lock lock(mutex);
   for(;;) {
    changed.wait(lock,[&]{return closing || ready()!=nullptr;});
    Entry* item=ready();
    if(!item) {
     if(closing) break;
     continue;
    }
    item->phase=Phase::in_flight;
    lock.unlock();
    // The preallocated failure result survives allocation errors while forming
    // diagnostics. Commit owns the actual SQLite transaction and durable proof.
    GameplayStoreCommit result;
    bool returned=false;
    try { result=store.commit(*item->batch); returned=true; }
    catch(const std::exception& error) {
     try {
      const char* message=error.what(); std::size_t size=0;
      while(size<4096 && message[size]!='\0') ++size;
      result.message.assign(message,size);
     } catch(...) {}
    } catch(...) {}
    lock.lock();
    if(returned || !result.message.empty()) {
     if(result.message.size()>4096) result.message.resize(4096);
     item->completion.result=std::move(result);
    }
    item->phase=committed(item->completion.result.status)?Phase::completed:Phase::failed;
    item->completion_pending=true;
    if(item->phase==Phase::completed) committed_revision=std::max(committed_revision,item->completion.revision);
    changed.notify_all();
   }
   stopped=true;
  } catch(...) {
   if(!opened) {
    try { startup.set_exception(std::current_exception()); } catch(...) {}
   }
   std::lock_guard lock(mutex);
   closing=true; stopped=true;
   for(auto& item:entries) if(item->phase==Phase::in_flight) {
    item->phase=Phase::failed; item->completion_pending=true;
   }
   changed.notify_all();
  }
 }
};
GameplaySaveWorker::GameplaySaveWorker(const std::filesystem::path& path,GameplayScope scope,std::vector<ComponentSchema> schemas,
                                     GameplayWorkerLimits limits,GameplayStoreObserver observer)
 :impl_(std::make_unique<Impl>(std::move(scope),limits)) {
 auto startup=impl_->startup.get_future();
 impl_->thread=std::thread([owner=impl_.get(),path,definitions=std::move(schemas),hook=std::move(observer)]() mutable {
  owner->run(path,std::move(definitions),std::move(hook));
 });
 try { startup.get(); }
 catch(...) { if(impl_->thread.joinable()) impl_->thread.join(); throw; }
}
GameplaySaveWorker::~GameplaySaveWorker()=default;
WorkerSubmitResult GameplaySaveWorker::submit(std::shared_ptr<const GameplayChangeBatch> batch) {
 auto& p=*impl_;
 std::lock_guard lock(p.mutex);
 return p.admit(batch,Impl::Phase::queued);
}
WorkerSubmitResult GameplaySaveWorker::reserve(std::shared_ptr<const GameplayChangeBatch> batch) {
 auto& p=*impl_; std::lock_guard lock(p.mutex);
 return p.admit(batch,Impl::Phase::reserved);
}
bool GameplaySaveWorker::publish_reserved(const std::string& operation_id) {
 auto& p=*impl_; std::lock_guard lock(p.mutex);
 if(p.closing) return false;
 for(const auto& item:p.entries) if(item->batch->operation_id==operation_id) {
  if(item->phase==Impl::Phase::reserved) { item->phase=Impl::Phase::queued; p.changed.notify_all(); }
  return true;
 }
 return false;
}
bool GameplaySaveWorker::cancel_reserved(const std::string& operation_id) {
 auto& p=*impl_; std::lock_guard lock(p.mutex);
 for(auto iterator=p.entries.begin();iterator!=p.entries.end();++iterator) {
  const auto& item=**iterator;
  if(item.batch->operation_id==operation_id && item.phase==Impl::Phase::reserved) {
   p.charged_bytes-=item.bytes; p.entries.erase(iterator); p.changed.notify_all();
   return true;
  }
 }
 return false;
}
std::optional<GameplaySaveCompletion> GameplaySaveWorker::poll() {
 auto& p=*impl_; std::lock_guard lock(p.mutex);
 for(auto iterator=p.entries.begin();iterator!=p.entries.end();++iterator) {
  auto& item=**iterator;
  if(!item.completion_pending) continue;
  if(item.phase==Impl::Phase::failed) {
   GameplaySaveCompletion result=item.completion;
   item.completion_pending=false;
   return std::optional<GameplaySaveCompletion>(std::move(result));
  }
  GameplaySaveCompletion result=std::move(item.completion);
  p.charged_bytes-=item.bytes; p.entries.erase(iterator);
  return std::optional<GameplaySaveCompletion>(std::move(result));
 }
 return {};
}
Result GameplaySaveWorker::retry_failed() {
 auto& p=*impl_; std::lock_guard lock(p.mutex);
 if(p.closing) return {false,"Cannot retry a closed save worker",p.committed_revision};
 for(auto& item:p.entries) if(item->phase==Impl::Phase::failed) {
  if(item->completion_pending) return {false,"Drain the failed completion before retrying",p.committed_revision};
  Result result{true,"Failed head queued for exact retry",p.committed_revision};
  item->phase=Impl::Phase::queued; p.changed.notify_all();
  return result;
 }
 return {false,"No blocked save batch to retry",p.committed_revision};
}
Result GameplaySaveWorker::close() {
 auto& p=*impl_;
 // Reject from the connection thread before the join lock. The owner may hold
 // that lock while waiting for this very observer/commit callback to return.
 if(p.worker_id==std::this_thread::get_id())
  return {false,"Save worker cannot join itself",0};
 std::lock_guard close_lock(p.close_mutex);
 { std::lock_guard lock(p.mutex); p.closing=true; }
 p.changed.notify_all();
 if(p.thread.joinable()) p.thread.join();
 std::lock_guard lock(p.mutex);
 const bool incomplete=std::any_of(p.entries.begin(),p.entries.end(),[](const auto& item){return item->phase!=Impl::Phase::completed;});
 return { !incomplete,incomplete?"Save worker joined with uncommitted work at an unpublished or failed head":"All submitted batches committed; save worker joined",p.committed_revision };
}
GameplayWorkerState GameplaySaveWorker::state() const { std::lock_guard lock(impl_->mutex); return impl_->snapshot(); }
GameplayStoreRecovery GameplaySaveWorker::initial_state() const {
 std::shared_ptr<const GameplayStoreRecovery> initial;
 { std::lock_guard lock(impl_->mutex); initial=impl_->initial; }
 return *initial;
}
}
