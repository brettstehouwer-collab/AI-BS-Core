#pragma once
#include <aibs/render.hpp>
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>
#include <vector>

namespace aibs {

struct SpatialZoneBounds {
    Vec3 min{};
    Vec3 max{};

    [[nodiscard]] constexpr bool contains(Vec3 pt) const noexcept {
        return pt.x >= min.x && pt.x <= max.x &&
               pt.y >= min.y && pt.y <= max.y &&
               pt.z >= min.z && pt.z <= max.z;
    }
};

struct PodiumCaptionTrigger {
    std::size_t segment_index = 0;
    std::uint64_t start_sample = 0;
    std::uint64_t end_sample = 0;
    std::string_view text;
    std::string_view zone_name;
    SpatialZoneBounds bounds;

    [[nodiscard]] constexpr bool contains(Vec3 pt) const noexcept {
        return bounds.contains(pt);
    }
};

class PodiumCaptionsSpatialMap {
public:
    static constexpr std::size_t SEGMENT_COUNT = 62;
    static constexpr std::uint32_t SAMPLE_RATE = 44100;
    static constexpr std::uint32_t CHANNELS = 2;
    static constexpr std::uint64_t TOTAL_FRAMES = 8684544;
    static constexpr std::string_view SOURCE_SHA256 = "1464299dbe1280b979384f12fc34db1f6626b52ed3d1fb699541cf74082c2a08";

    // All 62 statically mapped triggers
    [[nodiscard]] static std::span<const PodiumCaptionTrigger, SEGMENT_COUNT> all_triggers() noexcept;

    // Get trigger by index (0..61)
    [[nodiscard]] static const PodiumCaptionTrigger& trigger(std::size_t index) noexcept;

    // Find the next eligible segment given player's feet position and last triggered segment index
    [[nodiscard]] static std::optional<std::size_t> query_next_eligible_segment(
        Vec3 player_feet,
        std::size_t last_triggered_index
    ) noexcept;

    // Direct spatial query returning all segments whose zone contains player_feet
    [[nodiscard]] static std::vector<std::size_t> query_zones_at(Vec3 player_feet);
};

} // namespace aibs
