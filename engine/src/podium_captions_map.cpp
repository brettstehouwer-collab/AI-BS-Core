#include <aibs/podium_captions_map.hpp>
#include <algorithm>
#include <stdexcept>

namespace aibs {

namespace {

constexpr std::array<PodiumCaptionTrigger, PodiumCaptionsSpatialMap::SEGMENT_COUNT> s_triggers = {
    PodiumCaptionTrigger{
        0u,
        0ULL,
        88200ULL,
        "I think that's like the first step.",
        "nook_awakening",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -27.0f},
            Vec3{-35.0f, 3.0f, -12.0f}
        }
    },    PodiumCaptionTrigger{
        1u,
        88200ULL,
        264600ULL,
        "Just listen, you don't even have to listen.",
        "nook_awakening",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -27.0f},
            Vec3{-35.0f, 3.0f, -12.0f}
        }
    },    PodiumCaptionTrigger{
        2u,
        264600ULL,
        352800ULL,
        "You just sit there and write.",
        "nook_awakening",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -27.0f},
            Vec3{-35.0f, 3.0f, -12.0f}
        }
    },    PodiumCaptionTrigger{
        3u,
        352800ULL,
        396900ULL,
        "You need to start listening.",
        "nook_awakening",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -27.0f},
            Vec3{-35.0f, 3.0f, -12.0f}
        }
    },    PodiumCaptionTrigger{
        4u,
        396900ULL,
        485100ULL,
        "It's almost like you're trying to blow.",
        "nook_awakening",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -27.0f},
            Vec3{-35.0f, 3.0f, -12.0f}
        }
    },    PodiumCaptionTrigger{
        5u,
        485100ULL,
        617400ULL,
        "It's like, oh, you have to fight with your girlfriend?",
        "nook_awakening",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -27.0f},
            Vec3{-35.0f, 3.0f, -12.0f}
        }
    },    PodiumCaptionTrigger{
        6u,
        617400ULL,
        705600ULL,
        "It's like, the next thing you know,",
        "nook_awakening",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -27.0f},
            Vec3{-35.0f, 3.0f, -12.0f}
        }
    },    PodiumCaptionTrigger{
        7u,
        705600ULL,
        793800ULL,
        "he's up here reading there and talking about something",
        "nook_awakening",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -27.0f},
            Vec3{-35.0f, 3.0f, -12.0f}
        }
    },    PodiumCaptionTrigger{
        8u,
        793800ULL,
        970200ULL,
        "that has to do with like, it applies to fighting with your girlfriend.",
        "corridor_approach",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -12.0f},
            Vec3{-35.0f, 3.0f, 2.5f}
        }
    },    PodiumCaptionTrigger{
        9u,
        970200ULL,
        1102500ULL,
        "It applies to make people's bad decisions.",
        "corridor_approach",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -12.0f},
            Vec3{-35.0f, 3.0f, 2.5f}
        }
    },    PodiumCaptionTrigger{
        10u,
        1102500ULL,
        1278900ULL,
        "But it's a story and like, this is a huge book.",
        "corridor_approach",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -12.0f},
            Vec3{-35.0f, 3.0f, 2.5f}
        }
    },    PodiumCaptionTrigger{
        11u,
        1278900ULL,
        1455300ULL,
        "There's many, many stories in here.",
        "corridor_approach",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -12.0f},
            Vec3{-35.0f, 3.0f, 2.5f}
        }
    },    PodiumCaptionTrigger{
        12u,
        1455300ULL,
        1631700ULL,
        "And it's just like, they all sound the same.",
        "corridor_approach",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -12.0f},
            Vec3{-35.0f, 3.0f, 2.5f}
        }
    },    PodiumCaptionTrigger{
        13u,
        1631700ULL,
        1852200ULL,
        "They all, so for me, it means you're dumb.",
        "corridor_approach",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -12.0f},
            Vec3{-35.0f, 3.0f, 2.5f}
        }
    },    PodiumCaptionTrigger{
        14u,
        1852200ULL,
        2072700ULL,
        "But if it works for you or anybody else like that, you know, it has that.",
        "corridor_approach",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -12.0f},
            Vec3{-35.0f, 3.0f, 2.5f}
        }
    },    PodiumCaptionTrigger{
        15u,
        2072700ULL,
        2205000ULL,
        "It works, it helps you out first for sure.",
        "corridor_approach",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, -12.0f},
            Vec3{-35.0f, 3.0f, 2.5f}
        }
    },    PodiumCaptionTrigger{
        16u,
        2205000ULL,
        2293200ULL,
        "Like, you know, right off the bat.",
        "fault_trench",
        SpatialZoneBounds{
            Vec3{-37.5f, -1.0f, -7.0f},
            Vec3{-31.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        17u,
        2293200ULL,
        2381400ULL,
        "I mean, it sucks at first, but...",
        "fault_trench",
        SpatialZoneBounds{
            Vec3{-37.5f, -1.0f, -7.0f},
            Vec3{-31.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        18u,
        2381400ULL,
        2469600ULL,
        "I never liked it.",
        "fault_trench",
        SpatialZoneBounds{
            Vec3{-37.5f, -1.0f, -7.0f},
            Vec3{-31.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        19u,
        2513700ULL,
        2646000ULL,
        "But, I haven't. But I mean, if it works for you, you can use to it.",
        "fault_trench",
        SpatialZoneBounds{
            Vec3{-37.5f, -1.0f, -7.0f},
            Vec3{-31.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        20u,
        2646000ULL,
        2734200ULL,
        "No, you don't get used to it.",
        "fault_trench",
        SpatialZoneBounds{
            Vec3{-37.5f, -1.0f, -7.0f},
            Vec3{-31.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        21u,
        2734200ULL,
        2822400ULL,
        "I don't get used to it.",
        "fault_trench",
        SpatialZoneBounds{
            Vec3{-37.5f, -1.0f, -7.0f},
            Vec3{-31.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        22u,
        2822400ULL,
        2998800ULL,
        "I've been doing, it made me go to meetings for like, three and a half months.",
        "fault_trench",
        SpatialZoneBounds{
            Vec3{-37.5f, -1.0f, -7.0f},
            Vec3{-31.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        23u,
        2998800ULL,
        3087000ULL,
        "I hated it from day one.",
        "fault_trench",
        SpatialZoneBounds{
            Vec3{-37.5f, -1.0f, -7.0f},
            Vec3{-31.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        24u,
        3087000ULL,
        3219300ULL,
        "I don't hate it. I just like it's probably.",
        "fault_trench",
        SpatialZoneBounds{
            Vec3{-37.5f, -1.0f, -7.0f},
            Vec3{-31.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        25u,
        3219300ULL,
        3483900ULL,
        "You know, so, I don't like to go, but I'll go to church every Sunday.",
        "relay_bypass_socket",
        SpatialZoneBounds{
            Vec3{-44.0f, -1.0f, -7.0f},
            Vec3{-38.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        26u,
        3483900ULL,
        3528000ULL,
        "I don't just fight.",
        "relay_bypass_socket",
        SpatialZoneBounds{
            Vec3{-44.0f, -1.0f, -7.0f},
            Vec3{-38.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        27u,
        3528000ULL,
        3616200ULL,
        "I'll walk there if I have to.",
        "relay_bypass_socket",
        SpatialZoneBounds{
            Vec3{-44.0f, -1.0f, -7.0f},
            Vec3{-38.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        28u,
        3616200ULL,
        3880800ULL,
        "They're like, you know, you can either walk 45 minutes to church or come in less to the 2RA meeting.",
        "relay_bypass_socket",
        SpatialZoneBounds{
            Vec3{-44.0f, -1.0f, -7.0f},
            Vec3{-38.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        29u,
        3880800ULL,
        4013100ULL,
        "Trust me, I'm gone. I left 50 minutes ago.",
        "relay_bypass_socket",
        SpatialZoneBounds{
            Vec3{-44.0f, -1.0f, -7.0f},
            Vec3{-38.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        30u,
        4013100ULL,
        4101300ULL,
        "You know, I'll be here.",
        "relay_bypass_socket",
        SpatialZoneBounds{
            Vec3{-44.0f, -1.0f, -7.0f},
            Vec3{-38.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        31u,
        4101300ULL,
        4277700ULL,
        "So where do you find the strength to stay?",
        "relay_bypass_socket",
        SpatialZoneBounds{
            Vec3{-44.0f, -1.0f, -7.0f},
            Vec3{-38.0f, 3.0f, -3.0f}
        }
    },    PodiumCaptionTrigger{
        32u,
        4277700ULL,
        4630500ULL,
        "Uh, I guess it's, it always comes down to what they call the old five.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        33u,
        4630500ULL,
        4851000ULL,
        "And you can leave your car, you can leave everything.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        34u,
        4851000ULL,
        4939200ULL,
        "You can leave everything twice.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        35u,
        4939200ULL,
        5027400ULL,
        "But if they look, they get through the spot.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        36u,
        5027400ULL,
        5203800ULL,
        "They're usually literally like,",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        37u,
        5203800ULL,
        5380200ULL,
        "for me it was, I lost my girlfriend.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        38u,
        5380200ULL,
        5512500ULL,
        "We've only got it for like, almost six years.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        39u,
        5512500ULL,
        5644800ULL,
        "And she's just like, I really, cause she was always there for me.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        40u,
        5644800ULL,
        5777100ULL,
        "I mean, she never did drugs or anything like that.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        41u,
        5777100ULL,
        5953500ULL,
        "She just, she just kind of kept trying to pull me out of it.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        42u,
        5953500ULL,
        6085800ULL,
        "You can't pull anybody out of it unless they're ready.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        43u,
        6085800ULL,
        6174000ULL,
        "And I don't know, I lost her.",
        "threshold_aperture",
        SpatialZoneBounds{
            Vec3{-43.0f, -1.0f, 1.5f},
            Vec3{-31.0f, 3.0f, 6.5f}
        }
    },    PodiumCaptionTrigger{
        44u,
        6174000ULL,
        6306300ULL,
        "And then I lost her, I was pretty much, I was pretty good.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        45u,
        6306300ULL,
        6526800ULL,
        "And they took like two or three months to really fully resonate.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        46u,
        6526800ULL,
        6791400ULL,
        "But, cause I, I mean, I kept trying to do the right thing and it's really pretty.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        47u,
        6791400ULL,
        6967800ULL,
        "And finally it was a, you can buy another car.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        48u,
        6967800ULL,
        7100100ULL,
        "And that can get better. It can bounce back by another car.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        49u,
        7100100ULL,
        7188300ULL,
        "By a new house.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        50u,
        7188300ULL,
        7276500ULL,
        "You know, fill up the savings account.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        51u,
        7276500ULL,
        7364700ULL,
        "Everything I did.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        52u,
        7364700ULL,
        7452900ULL,
        "But when it comes to her, you can't.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        53u,
        7452900ULL,
        7541100ULL,
        "There's no monetary value that will get her back.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        54u,
        7541100ULL,
        7629300ULL,
        "No deed, no nothing.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        55u,
        7629300ULL,
        7805700ULL,
        "You know, except for time, change and change.",
        "sheltered_hub",
        SpatialZoneBounds{
            Vec3{-41.0f, -1.0f, 6.5f},
            Vec3{-31.0f, 3.0f, 12.0f}
        }
    },    PodiumCaptionTrigger{
        56u,
        7805700ULL,
        7982100ULL,
        "And patience. And, like, I tried for like three months to do it.",
        "pencil_room",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, 12.0f},
            Vec3{-29.0f, 3.0f, 22.0f}
        }
    },    PodiumCaptionTrigger{
        57u,
        7982100ULL,
        8158500ULL,
        "And finally hit me one day and like, what are you doing that's any difficult",
        "pencil_room",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, 12.0f},
            Vec3{-29.0f, 3.0f, 22.0f}
        }
    },    PodiumCaptionTrigger{
        58u,
        8158500ULL,
        8246700ULL,
        "when you're doing it before?",
        "pencil_room",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, 12.0f},
            Vec3{-29.0f, 3.0f, 22.0f}
        }
    },    PodiumCaptionTrigger{
        59u,
        8246700ULL,
        8423100ULL,
        "What makes it, what makes you worthy enough to be with her again?",
        "pencil_room",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, 12.0f},
            Vec3{-29.0f, 3.0f, 22.0f}
        }
    },    PodiumCaptionTrigger{
        60u,
        8423100ULL,
        8599500ULL,
        "What, what really makes you stand out again?",
        "pencil_room",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, 12.0f},
            Vec3{-29.0f, 3.0f, 22.0f}
        }
    },    PodiumCaptionTrigger{
        61u,
        8599500ULL,
        8684544ULL,
        "Nothing.",
        "pencil_room",
        SpatialZoneBounds{
            Vec3{-39.0f, -1.0f, 12.0f},
            Vec3{-29.0f, 3.0f, 22.0f}
        }
    }
};

} // namespace

std::span<const PodiumCaptionTrigger, PodiumCaptionsSpatialMap::SEGMENT_COUNT> PodiumCaptionsSpatialMap::all_triggers() noexcept {
    return std::span<const PodiumCaptionTrigger, SEGMENT_COUNT>(s_triggers);
}

const PodiumCaptionTrigger& PodiumCaptionsSpatialMap::trigger(std::size_t index) noexcept {
    if (index >= SEGMENT_COUNT) {
        return s_triggers[SEGMENT_COUNT - 1];
    }
    return s_triggers[index];
}

std::optional<std::size_t> PodiumCaptionsSpatialMap::query_next_eligible_segment(
    Vec3 player_feet,
    std::size_t last_triggered_index
) noexcept {
    // Search forward from last_triggered_index for narrative progression
    for (std::size_t i = last_triggered_index; i < SEGMENT_COUNT; ++i) {
        if (s_triggers[i].contains(player_feet)) {
            return i;
        }
    }
    // If not found forward, search entire array in case player re-entered a zone
    for (std::size_t i = 0; i < SEGMENT_COUNT; ++i) {
        if (s_triggers[i].contains(player_feet)) {
            return i;
        }
    }
    return std::nullopt;
}

std::vector<std::size_t> PodiumCaptionsSpatialMap::query_zones_at(Vec3 player_feet) {
    std::vector<std::size_t> results;
    results.reserve(8);
    for (std::size_t i = 0; i < SEGMENT_COUNT; ++i) {
        if (s_triggers[i].contains(player_feet)) {
            results.push_back(i);
        }
    }
    return results;
}

} // namespace aibs
