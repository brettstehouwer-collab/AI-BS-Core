#include <aibs/sheltered_hub_contracts.hpp>
#include <cmath>
#include <stdexcept>

namespace aibs {

namespace {

ComponentSchema make_schema(std::string id, std::vector<GameplayFieldRule> fields) {
    return {std::move(id), 1, std::move(fields)};
}

GameplayFieldRule make_bool(std::string id) {
    return {std::move(id), GameplayValueKind::boolean};
}

GameplayFieldRule make_string(std::string id) {
    return {std::move(id), GameplayValueKind::text};
}

GameplayFieldRule make_count(std::string id) {
    return {std::move(id), GameplayValueKind::integer};
}

GameplayFieldRule make_real(std::string id, double min_v = -500.0, double max_v = 500.0) {
    return {std::move(id), GameplayValueKind::number, true, min_v, max_v};
}

} // namespace

std::vector<ComponentSchema> sheltered_hub_station_schemas() {
    std::vector<ComponentSchema> result;
    result.reserve(3);

    // 1. Writing Desk
    result.push_back(make_schema(std::string(writing_desk_type), {
        make_bool("pencil_claimed"),
        make_string("mode"),
        make_count("notes_written"),
        make_real("x"),
        make_real("y"),
        make_real("z")
    }));

    // 2. Memory Shelves
    result.push_back(make_schema(std::string(memory_shelves_type), {
        make_count("items_placed"),
        make_count("capacity"),
        make_bool("secret_revealed"),
        make_real("x"),
        make_real("y"),
        make_real("z")
    }));

    // 3. Shared Play Corner
    result.push_back(make_schema(std::string(shared_play_type), {
        make_bool("display_powered"),
        make_bool("session_active"),
        make_real("x"),
        make_real("y"),
        make_real("z")
    }));

    return result;
}

std::vector<ComponentRecord> create_sheltered_stations(
    const ShelteredStationIds& ids,
    Vec3 desk_pos,
    Vec3 shelves_pos,
    Vec3 play_pos
) {
    std::vector<ComponentRecord> records;
    records.reserve(3);

    // Desk record
    ComponentRecord desk;
    desk.entity_id = ids.desk_id;
    desk.type_id = std::string(writing_desk_type);
    desk.version = 1;
    desk.fields["pencil_claimed"] = false;
    desk.fields["mode"] = std::string("record");
    desk.fields["notes_written"] = std::int64_t(0);
    desk.fields["x"] = static_cast<double>(desk_pos.x);
    desk.fields["y"] = static_cast<double>(desk_pos.y);
    desk.fields["z"] = static_cast<double>(desk_pos.z);
    records.push_back(std::move(desk));

    // Shelves record
    ComponentRecord shelves;
    shelves.entity_id = ids.shelves_id;
    shelves.type_id = std::string(memory_shelves_type);
    shelves.version = 1;
    shelves.fields["items_placed"] = std::int64_t(0);
    shelves.fields["capacity"] = std::int64_t(12);
    shelves.fields["secret_revealed"] = false;
    shelves.fields["x"] = static_cast<double>(shelves_pos.x);
    shelves.fields["y"] = static_cast<double>(shelves_pos.y);
    shelves.fields["z"] = static_cast<double>(shelves_pos.z);
    records.push_back(std::move(shelves));

    // Shared Play record
    ComponentRecord play;
    play.entity_id = ids.play_id;
    play.type_id = std::string(shared_play_type);
    play.version = 1;
    play.fields["display_powered"] = false;
    play.fields["session_active"] = false;
    play.fields["x"] = static_cast<double>(play_pos.x);
    play.fields["y"] = static_cast<double>(play_pos.y);
    play.fields["z"] = static_cast<double>(play_pos.z);
    records.push_back(std::move(play));

    return records;
}

bool can_write_note(const ComponentRecord& desk_record) noexcept {
    const auto it = desk_record.fields.find("pencil_claimed");
    if (it == desk_record.fields.end()) return false;
    const auto* claimed = std::get_if<bool>(&it->second);
    return claimed && *claimed;
}

bool can_switch_display(const ComponentRecord& /*play_record*/, bool shelter_has_power) noexcept {
    return shelter_has_power;
}

std::optional<ComponentRecord> plan_desk_action(
    const ComponentRecord& desk_before,
    bool claim_pencil,
    WritingPencilMode new_mode,
    bool increment_note
) {
    if (desk_before.type_id != writing_desk_type) return std::nullopt;

    ComponentRecord after = desk_before;
    if (claim_pencil) {
        after.fields["pencil_claimed"] = true;
    }

    after.fields["mode"] = std::string(writing_mode_name(new_mode));

    if (increment_note) {
        if (!can_write_note(after)) {
            // Cannot write without claiming pencil first
            return std::nullopt;
        }
        auto& notes = std::get<std::int64_t>(after.fields.at("notes_written"));
        notes += 1;
    }

    return after;
}

std::optional<ComponentRecord> plan_shelves_action(
    const ComponentRecord& shelves_before,
    bool place_object
) {
    if (shelves_before.type_id != memory_shelves_type) return std::nullopt;

    ComponentRecord after = shelves_before;
    if (place_object) {
        auto& placed = std::get<std::int64_t>(after.fields.at("items_placed"));
        const auto capacity = std::get<std::int64_t>(after.fields.at("capacity"));
        if (placed >= capacity) {
            return std::nullopt; // Over capacity
        }
        placed += 1;
        if (placed >= 3) {
            after.fields["secret_revealed"] = true; // Reveal secret compartment
        }
    }

    return after;
}

std::optional<ComponentRecord> plan_play_action(
    const ComponentRecord& play_before,
    bool power_display,
    bool activate_session
) {
    if (play_before.type_id != shared_play_type) return std::nullopt;

    ComponentRecord after = play_before;
    after.fields["display_powered"] = power_display;

    if (activate_session) {
        if (!power_display) {
            return std::nullopt; // Cannot run session without display power
        }
        after.fields["session_active"] = true;
    } else {
        after.fields["session_active"] = false;
    }

    return after;
}

} // namespace aibs

