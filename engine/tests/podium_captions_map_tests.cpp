#include <aibs/podium_captions_map.hpp>
#include <iostream>
#include <stdexcept>
#include <string>

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

        // 1. Array bounds & counts
        const auto triggers = PodiumCaptionsSpatialMap::all_triggers();
        require(triggers.size() == 62, "Must contain exactly 62 triggers");
        require(PodiumCaptionsSpatialMap::SEGMENT_COUNT == 62, "Constant count matches 62");
        require(PodiumCaptionsSpatialMap::SAMPLE_RATE == 44100, "Sample rate matches 44.1kHz");
        require(PodiumCaptionsSpatialMap::CHANNELS == 2, "Stereo 2-channel audio");
        require(PodiumCaptionsSpatialMap::TOTAL_FRAMES == 8684544ULL, "Total frames matches draft");

        // 2. Validate ordering and non-overlapping samples
        std::uint64_t last_sample = 0;
        for (std::size_t i = 0; i < triggers.size(); ++i) {
            const auto& t = triggers[i];
            require(t.segment_index == i, "Segment index must match array position");
            require(t.start_sample >= last_sample, "Sample start must be monotonically increasing");
            require(t.end_sample > t.start_sample, "Sample end must exceed start");
            require(!t.text.empty(), "Cue text must be non-empty");
            require(!t.zone_name.empty(), "Zone name must be non-empty");
            require(t.bounds.min.x <= t.bounds.max.x, "Bounds min.x <= max.x");
            require(t.bounds.min.y <= t.bounds.max.y, "Bounds min.y <= max.y");
            require(t.bounds.min.z <= t.bounds.max.z, "Bounds min.z <= max.z");
            last_sample = t.start_sample;
        }
        require(last_sample < PodiumCaptionsSpatialMap::TOTAL_FRAMES, "Last sample bounded by total frames");

        // 3. Test key spatial points along physical route
        // Point in Nook: (-37, 0.2, -25)
        const Vec3 nook_spawn{-37.0f, 0.2f, -25.0f};
        const auto nook_cue = PodiumCaptionsSpatialMap::query_next_eligible_segment(nook_spawn, 0);
        require(nook_cue.has_value(), "Nook spawn must hit a trigger");
        require(*nook_cue <= 7, "Nook spawn must trigger one of segments 0..7");

        // Point at Fault Trench: (-33, 0.2, -5.2)
        const Vec3 fault_pos{-33.0f, 0.2f, -5.2f};
        const auto fault_cue = PodiumCaptionsSpatialMap::query_next_eligible_segment(fault_pos, 8);
        require(fault_cue.has_value(), "Fault trench position must hit a trigger");
        require(*fault_cue >= 16 && *fault_cue <= 24, "Fault position must map to fault_trench zone");

        // Point at Relay Bypass Socket: (-42, 0.2, -5.2)
        const Vec3 socket_pos{-42.0f, 0.2f, -5.2f};
        const auto socket_cue = PodiumCaptionsSpatialMap::query_next_eligible_segment(socket_pos, 16);
        require(socket_cue.has_value(), "Bypass socket position must hit a trigger");
        require(*socket_cue >= 25 && *socket_cue <= 31, "Socket position must map to relay_bypass_socket zone");

        // Point at Door Threshold / Aperture: (-33, 0.2, 5.0)
        const Vec3 aperture_pos{-33.0f, 0.2f, 5.0f};
        const auto aperture_cue = PodiumCaptionsSpatialMap::query_next_eligible_segment(aperture_pos, 25);
        require(aperture_cue.has_value(), "Aperture position must hit a trigger");
        require(*aperture_cue >= 32 && *aperture_cue <= 43, "Aperture position must map to threshold_aperture zone");

        // Point in Sheltered Hub: (-37, 0.2, 8.0)
        const Vec3 hub_pos{-37.0f, 0.2f, 8.0f};
        const auto hub_cue = PodiumCaptionsSpatialMap::query_next_eligible_segment(hub_pos, 35);
        require(hub_cue.has_value(), "Hub interior position must hit a trigger");
        require(*hub_cue >= 44 && *hub_cue <= 55, "Hub interior position must map to sheltered_hub zone");

        // Point in Pencil Room: (-37, 0.2, 15.0)
        const Vec3 pencil_pos{-37.0f, 0.2f, 15.0f};
        const auto pencil_cue = PodiumCaptionsSpatialMap::query_next_eligible_segment(pencil_pos, 45);
        require(pencil_cue.has_value(), "Pencil room position must hit a trigger");
        require(*pencil_cue >= 56 && *pencil_cue <= 61, "Pencil room position must map to pencil_room zone");

        // Point far outside world: (100, 0, 100)
        const Vec3 void_pos{100.0f, 0.0f, 100.0f};
        const auto void_cue = PodiumCaptionsSpatialMap::query_next_eligible_segment(void_pos, 0);
        require(!void_cue.has_value(), "Void coordinates outside all zones must return nullopt");

        // 4. Safe out-of-bounds trigger lookup
        const auto& fallback = PodiumCaptionsSpatialMap::trigger(999);
        require(fallback.segment_index == 61, "Out of bounds trigger index safely returns last cue");

        std::cout << "PASS: all " << checks << " podium spatial captions map checks passed successfully.\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL: " << e.what() << "\n";
        return 1;
    }
}

