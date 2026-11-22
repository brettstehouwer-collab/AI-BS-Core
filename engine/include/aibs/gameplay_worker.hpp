#pragma once
#include <aibs/gameplay_store.hpp>

namespace aibs {
struct GameplayWorkerLimits {
 std::size_t items=8,bytes=1024*1024;
};
enum class WorkerSubmitStatus { accepted,retry,rejected,backpressure,closed };
struct WorkerSubmitResult {
 WorkerSubmitStatus status=WorkerSubmitStatus::rejected;
 std::string message;
};
struct GameplaySaveCompletion {
 GameplayScope scope;
 std::string operation_id;
 std::uint64_t revision=0,sequence=0;
 GameplayStoreCommit result;
};
struct GameplayWorkerState {
 std::size_t reserved=0,queued=0,in_flight=0,completed=0,charged_items=0,charged_bytes=0;
 bool blocked=false,closed=false,stopped=false;
};
// The worker exclusively owns its SQLite connection on a background thread.
// Constructor waits for successful open/recovery or joins and propagates the
// startup exception. No CreatorSession or mutable world crosses this boundary.
class GameplaySaveWorker {
public:
 GameplaySaveWorker(const std::filesystem::path& path,GameplayScope scope,std::vector<ComponentSchema> schemas,
                    GameplayWorkerLimits limits={},GameplayStoreObserver observer={});
 ~GameplaySaveWorker();
 GameplaySaveWorker(const GameplaySaveWorker&)=delete;
 GameplaySaveWorker& operator=(const GameplaySaveWorker&)=delete;
 // Bounded canonical preflight precedes capacity checks and defensive copying.
 // Queue charge includes queued, in-flight and undrained completion storage.
 // Retained exact requests retry without consuming another credit. After drain,
 // exact retries go through SQLite's durable receipts; no unlimited ID set grows.
 WorkerSubmitResult submit(std::shared_ptr<const GameplayChangeBatch> batch);
 // Reserve immutable storage/credits before live world publication. A reserved
 // entry cannot reach SQLite and blocks dispatch of all later entries.
 WorkerSubmitResult reserve(std::shared_ptr<const GameplayChangeBatch> batch);
 // After a prepared nonthrowing world swap, activate without allocating value
 // data. Repeats for retained active entries succeed without another dispatch.
 bool publish_reserved(const std::string& operation_id);
 // Only an unpublished reservation can be canceled/refunded. No committed or
 // already dispatched entry can be removed through this path.
 bool cancel_reserved(const std::string& operation_id);
 // Success releases credits. A failed attempt is delivered once but retains its
 // batch/credit and blocks later work. Poll before explicitly retrying that head.
 std::optional<GameplaySaveCompletion> poll();
 Result retry_failed();
 // Stop admission, flush in order until the first unpublished or failed entry,
 // then join. Uncommitted work reports failure; completions remain drainable.
 // Closing never publishes a reservation or skips its queued successors.
 Result close();
 GameplayWorkerState state() const;
 // Immutable startup snapshot, not a live view of subsequent commits. Recovery
 // has its own store limits; this bounded copy is outside pending queue credits.
 GameplayStoreRecovery initial_state() const;
private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
};
}
