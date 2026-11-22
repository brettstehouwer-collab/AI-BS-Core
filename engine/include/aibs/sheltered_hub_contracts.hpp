#pragma once
#include <aibs/gameplay.hpp>
#include <aibs/render.hpp>
#include <string>
#include <string_view>
#include <vector>

namespace aibs {

inline constexpr std::string_view writing_desk_type = "firstboot.WritingDesk";
inline constexpr std::string_view memory_shelves_type = "firstboot.MemoryShelves";
inline constexpr std::string_view shared_play_type = "firstboot.SharedPlay";

enum class WritingPencilMode : std::uint8_t {
    record = 0, // Write and preserve memories
    trace = 1,  // Understand connections and lore
    sketch = 2  // Propose architectural builds
};

inline constexpr std::string_view writing_mode_name(WritingPencilMode mode) noexcept {
    switch (mode) {
        case WritingPencilMode::record: return "record";
        case WritingPencilMode::trace: return "trace";
        case WritingPencilMode::sketch: return "sketch";
    }
    return "record";
}

struct ShelteredStationIds {
    std::string desk_id;
    std::string shelves_id;
    std::string play_id;
};

// Component schemas for the Sheltered Hub & Pencil Room interactive stations
std::vector<ComponentSchema> sheltered_hub_station_schemas();

// Initial component records for the three Pencil Room stations
std::vector<ComponentRecord> create_sheltered_stations(
    const ShelteredStationIds& ids,
    Vec3 desk_pos = {-37.0f, 0.2f, 15.0f},
    Vec3 shelves_pos = {-34.0f, 0.2f, 16.5f},
    Vec3 play_pos = {-31.0f, 0.2f, 18.0f}
);

// State transition validators
bool can_write_note(const ComponentRecord& desk_record) noexcept;
bool can_switch_display(const ComponentRecord& play_record, bool shelter_has_power) noexcept;

// Plan actions
std::optional<ComponentRecord> plan_desk_action(
    const ComponentRecord& desk_before,
    bool claim_pencil,
    WritingPencilMode new_mode,
    bool increment_note
);

std::optional<ComponentRecord> plan_shelves_action(
    const ComponentRecord& shelves_before,
    bool place_object
);

std::optional<ComponentRecord> plan_play_action(
    const ComponentRecord& play_before,
    bool power_display,
    bool activate_session
);

} // namespace aibs

