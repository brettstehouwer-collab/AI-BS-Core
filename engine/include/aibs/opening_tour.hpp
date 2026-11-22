#pragma once
#include <aibs/first_boot_content.hpp>
#include <array>
#include <string_view>
namespace aibs {
inline constexpr std::size_t opening_tour_stop_count=7;
enum class OpeningTourRole :std::uint8_t {controller,truck,diagnostic,bypass,seats,shelter,pencil};
struct OpeningTourTargets {std::array<std::string,opening_tour_stop_count> ids;};
std::string_view opening_tour_role_name(OpeningTourRole)noexcept;
// Explicit optional diagnostic sidecar, never required by normal Play or
// serialized into gameplay history. Canonical ASCII is also canonical UTF8.
// It binds version/definition/world/fingerprint and exactly seven typed roles
// to unique currently owned inspection UUIDs; no fixture-name interpretation.
std::vector<unsigned char> encode_opening_tour(const FirstBootContent&,const OpeningTourTargets&);
OpeningTourTargets decode_opening_tour(std::span<const unsigned char>,const FirstBootContent&);
}
