#include <aibs/sheltered_hub_contracts.hpp>
#include <aibs/gameplay_codec.hpp>
#include <aibs/engine.hpp>
#include <iostream>
#include <stdexcept>

namespace {

unsigned checks = 0;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
    ++checks;
}

} // namespace

int main() {
    try {
        using namespace aibs;

        // 1. Schemas check
        const auto schemas = sheltered_hub_station_schemas();
        require(schemas.size() == 3, "Exactly 3 station schemas defined");
        require(schemas[0].type_id == writing_desk_type, "WritingDesk schema present");
        require(schemas[1].type_id == memory_shelves_type, "MemoryShelves schema present");
        require(schemas[2].type_id == shared_play_type, "SharedPlay schema present");

        // 2. Creation of stations
        ShelteredStationIds ids{new_uuid(), new_uuid(), new_uuid()};
        const auto records = create_sheltered_stations(ids);
        require(records.size() == 3, "3 initial records created");

        // Check encode/decode compatibility via gameplay_codec
        for (const auto& r : records) {
            const auto encoded = gameplay_codec::encode_component(r);
            require(!encoded.empty(), "Component must encode to non-empty bytes");
            const auto decoded = gameplay_codec::decode_component(encoded);
            require(decoded.entity_id == r.entity_id, "Decoded entity_id matches");
            require(decoded.type_id == r.type_id, "Decoded type_id matches");
        }

        // 3. Desk State transitions & Invariants
        const auto& desk = records[0];
        require(!can_write_note(desk), "Cannot write note initially before claiming pencil");

        // Try writing without pencil -> must fail
        const auto bad_write = plan_desk_action(desk, false, WritingPencilMode::record, true);
        require(!bad_write.has_value(), "Must reject writing note if pencil is not claimed");

        // Claim pencil and switch mode to trace
        const auto desk_claimed = plan_desk_action(desk, true, WritingPencilMode::trace, false);
        require(desk_claimed.has_value(), "Claiming pencil succeeds");
        require(can_write_note(*desk_claimed), "Now eligible to write notes");
        require(std::get<std::string>(desk_claimed->fields.at("mode")) == "trace", "Mode switched to trace");

        // Write a note
        const auto desk_written = plan_desk_action(*desk_claimed, false, WritingPencilMode::sketch, true);
        require(desk_written.has_value(), "Writing note succeeds");
        require(std::get<std::int64_t>(desk_written->fields.at("notes_written")) == 1, "Notes count incremented to 1");
        require(std::get<std::string>(desk_written->fields.at("mode")) == "sketch", "Mode switched to sketch");

        // 4. Memory Shelves Placement & Secret Compartment
        auto shelves = records[1];
        require(!std::get<bool>(shelves.fields.at("secret_revealed")), "Secret initially locked");

        // Place 3 items
        for (int i = 0; i < 3; ++i) {
            auto next = plan_shelves_action(shelves, true);
            require(next.has_value(), "Placing item succeeds");
            shelves = *next;
        }
        require(std::get<std::int64_t>(shelves.fields.at("items_placed")) == 3, "Placed 3 items");
        require(std::get<bool>(shelves.fields.at("secret_revealed")), "Secret revealed after 3 items placed");

        // 5. Shared Play Corner & Power Dependency
        const auto& play = records[2];
        require(!can_switch_display(play, false), "Cannot switch display without shelter power");
        require(can_switch_display(play, true), "Can switch display when shelter has power");

        // Try activating session without display power -> must fail
        const auto bad_session = plan_play_action(play, false, true);
        require(!bad_session.has_value(), "Must reject session activation if display is not powered");

        // Power display and activate session
        const auto play_active = plan_play_action(play, true, true);
        require(play_active.has_value(), "Powering and activating session succeeds");
        require(std::get<bool>(play_active->fields.at("display_powered")), "Display is powered");
        require(std::get<bool>(play_active->fields.at("session_active")), "Session is active");

        std::cout << "PASS: all " << checks << " sheltered hub station contract checks passed successfully.\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL: " << e.what() << "\n";
        return 1;
    }
}
