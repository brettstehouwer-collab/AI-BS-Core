#pragma once
#include <aibs/gameplay.hpp>
#include <filesystem>

namespace aibs {
enum class GameplayStoreStatus { committed, retry, rejected, failed };
enum class GameplayStoreStage { before_commit, after_commit };
// Fault/termination instrumentation runs on the connection owner. An exception
// after COMMIT cannot revoke the durable result and is reported in its message.
using GameplayStoreObserver = std::function<void(GameplayStoreStage)>;
struct GameplayStoreCommit {
 GameplayStoreStatus status = GameplayStoreStatus::failed;
 std::string message;
 GameplayAcknowledgement acknowledgement;
};
struct GameplayStoreRecovery {
 GameplayScope scope;
 std::uint64_t revision = 0, sequence = 0;
 std::vector<ComponentRecord> components;
};
struct GameplayStoreBaseline {
 std::uint64_t revision = 0, sequence = 0;
 std::vector<ComponentRecord> components;
 std::vector<std::uint8_t> legacy_checkpoint;
};
struct GameplayRegistryExtensionResult {
 GameplayStoreStatus status = GameplayStoreStatus::failed;
 std::string message;
};
// Synchronous, single-owner durable boundary. The save worker owns this object
// and its SQLite connection; simulation code only sends immutable batches.
// Complete scope keys isolate branches/contexts in a shared database. Registry
// changes and unknown database formats require explicit migration. Recovery is
// bounded (10000 components / 64 MiB encoded state). Receipt lifetime is not
// capped; callers page through history with explicit item/byte bounds.
class GameplayStore {
public:
 // Read-only bounded restart discovery. Unknown/foreign/corrupt databases and
 // exhausted limits throw; missing paths are never created. This checks scope
 // metadata only; open the selected scope with its known registry to validate
 // the complete durable stream. maximum must be within 1..4096.
 static std::vector<GameplayScope> list_scopes(const std::filesystem::path& path,
                                             std::size_t maximum = 128);
 // Inspect only canonical metadata without creating/upgrading a database.
 static std::vector<ComponentSchema> inspect_registry(const std::filesystem::path& path,
                                                     const GameplayScope& scope);
 // Existing-file, quiescent single-scope read-only admission. Denies concurrent
 // writers and validates exact registry, canonical full
 // stream, bounded state and heads in ONE read transaction; never creates a DB,
 // configures WAL, seeds metadata or upgrades its format. A caller can validate
 // this immutable recovery against content before opening a writable owner.
 static GameplayStoreRecovery inspect_recovery(const std::filesystem::path& path,
    const GameplayScope& scope,const std::vector<ComponentSchema>& expected_schemas);
 // Explicit format1->2 additive registry transaction. Existing definitions,
 // gameplay heads, components, events, retry receipts and baseline stay intact.
 // This result intentionally carries no gameplay acknowledgement or revision.
 static GameplayRegistryExtensionResult extend_registry(const std::filesystem::path& path,
    const GameplayScope& scope,const std::vector<ComponentSchema>& expected_schemas,
    const std::vector<ComponentSchema>& target_schemas,const std::string& migration_id,
    std::uint64_t expected_revision,std::uint64_t expected_sequence,GameplayStoreObserver observer = {});
 GameplayStore(const std::filesystem::path& path, GameplayScope scope,
               std::vector<ComponentSchema> schemas, GameplayStoreObserver observer = {});
 ~GameplayStore();
 GameplayStore(const GameplayStore&) = delete;
 GameplayStore& operator=(const GameplayStore&) = delete;
 GameplayStoreCommit commit(const GameplayChangeBatch& batch);
 GameplayStoreRecovery recover() const;
 std::optional<GameplayChangeBatch> lookup_batch(const std::string& operation_id) const;
 // Exact read-only lookup in this store's full scope. Invalid UUIDs throw.
 bool contains_event(const std::string& event_id) const;
 std::vector<GameplayChangeBatch> read_batches(std::uint64_t after_revision,
    std::size_t max_batches = 128, std::size_t max_bytes = 4 * 1024 * 1024) const;
 GameplayStoreCommit seed(const GameplayStoreBaseline& baseline);
 std::optional<GameplayStoreBaseline> baseline() const;
 Result verify() const;
private:
 struct Impl;
 std::unique_ptr<Impl> impl_;
};
}
