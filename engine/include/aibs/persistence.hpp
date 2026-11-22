#pragma once
#include <aibs/engine.hpp>
#include <filesystem>

namespace aibs {
enum class SaveStage { before_publish, after_publish };
// Optional observation seam used by the process-interruption harness. Must not
// throw or mutate the session. Called synchronously on the checkpoint owner.
using SaveObserver = void(*)(SaveStage) noexcept;
using CheckpointValidator = void(*)(const CreatorSession&);
struct CheckpointResult {
 bool ok;
 std::string message;
 std::uint64_t revision;
 std::string checkpoint_id;
};
struct CheckpointAssessment {
 bool compatible;
 std::size_t encoded_bytes;
 std::string message;
 bool operator==(const CheckpointAssessment&) const = default;
};
class CheckpointStore {
public:
 static constexpr unsigned format_version = 1;
 static constexpr std::size_t maximum_file_bytes = 16 * 1024 * 1024;
 // Exact format-1 validation/encoding without filesystem access or publication.
 // Copies the complete session: callers must bound its logical storage first.
 // Compatibility promises neither durable publication nor available disk space.
 static CheckpointAssessment assess(const CreatorSession& session);
 static CheckpointResult save(const std::filesystem::path& path, CreatorSession& session, SaveObserver observer = nullptr);
 static CheckpointResult load(const std::filesystem::path& path, CreatorSession& session, CheckpointValidator validator = nullptr);
};
}
