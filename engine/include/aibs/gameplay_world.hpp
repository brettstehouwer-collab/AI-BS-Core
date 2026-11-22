#pragma once
#include <aibs/gameplay_worker.hpp>
#include <utility>

namespace aibs {
class GameplayWorld;
class PreparedGameplayChange {
public:
 std::shared_ptr<const GameplayStoreRecovery> snapshot() const noexcept { return after_; }
 std::shared_ptr<const GameplayChangeBatch> batch() const noexcept { return batch_; }
private:
 friend class GameplayWorld;
 PreparedGameplayChange(std::string owner,std::shared_ptr<const GameplayStoreRecovery> before,
   std::shared_ptr<const GameplayStoreRecovery> after,std::shared_ptr<const GameplayChangeBatch> batch)
  :owner_(std::move(owner)),before_(std::move(before)),after_(std::move(after)),batch_(std::move(batch)) {}
 std::string owner_;
 std::shared_ptr<const GameplayStoreRecovery> before_,after_;
 std::shared_ptr<const GameplayChangeBatch> batch_;
};
enum class GameplayPrepareStatus { prepared,retry,rejected };
struct GameplayPrepareResult {
 GameplayPrepareStatus status=GameplayPrepareStatus::rejected;
 std::string message;
 std::shared_ptr<const PreparedGameplayChange> change;
};
using GameplayRuleValidator=std::function<void(const GameplayStoreRecovery& before,
 const GameplayStoreRecovery& after,const GameplayChangeBatch& batch)>;
struct GameplayWorldState {
 std::uint64_t visible_revision=0,visible_sequence=0,durable_revision=0,durable_sequence=0;
 std::size_t pending_batches=0,pending_bytes=0;
 bool saved=false,failed=false,closed=false;
 std::string error;
 GameplayWorkerState worker;
};
// Authoritative single-owner alpha world. prepare builds immutable candidates;
// publish reserves save credits before a nonallocating visible snapshot swap.
// Worker storage cannot dispatch until that publication is activated.
// Mutators/state are owner-thread-only; snapshot() is safe for concurrent readers.
// Whole-component-world copies remain bounded prototype work, not streamed ECS.
class GameplayWorld {
public:
 GameplayWorld(const std::filesystem::path& path,GameplayScope scope,std::vector<ComponentSchema> schemas,
               GameplayWorkerLimits limits={},GameplayStoreObserver observer={});
 ~GameplayWorld();
 GameplayWorld(const GameplayWorld&)=delete;
 GameplayWorld& operator=(const GameplayWorld&)=delete;
 std::shared_ptr<const GameplayStoreRecovery> snapshot() const noexcept;
 GameplayPrepareResult prepare(const GameplayChangeBatch& batch,GameplayRuleValidator validator={});
 Result publish(std::shared_ptr<const PreparedGameplayChange> change);
 std::optional<GameplaySaveCompletion> poll();
 GameplayWorldState state() const;
 // Bounded storage history; uncommitted visible changes are not included.
 std::vector<GameplayChangeBatch> read_batches(std::uint64_t after_revision,
   std::size_t max_batches=128,std::size_t max_bytes=4*1024*1024) const;
 Result retry_pending();
 // Stops admission, flushes until a failure, drains actual completions, joins.
 // Failed close leaves visible unsaved state explicit; reopen/recover uses only
 // committed state. Retry a failed live head before closing this owner.
 Result close();
private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
};
}
