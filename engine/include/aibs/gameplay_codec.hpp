#pragma once
#include <aibs/gameplay.hpp>
#include <cstddef>
#include <cstdint>
#include <span>
#include <stdexcept>

namespace aibs::gameplay_codec {
using Bytes = std::vector<std::uint8_t>;
inline constexpr std::size_t maximum_bytes = 4 * 1024 * 1024;
// Canonical typed little-endian envelopes. Every decoder rejects
// trailing/truncated/noncanonical input. Invalid input throws invalid_argument.
// Registered component versions remain explicit positive values; envelope,
// scope/component/registry envelopes stay at 1. Old-only batches retain exact
// version-1 bytes. Batches containing Mechanism/Quest use envelope/schema 2;
// those families use payload 2 while original families retain payload 1.
Bytes encode_batch(const GameplayChangeBatch& batch);
GameplayChangeBatch decode_batch(std::span<const std::uint8_t> bytes);
Bytes encode_component(const ComponentRecord& component);
ComponentRecord decode_component(std::span<const std::uint8_t> bytes);
// Registry and field order are canonicalized by type/version and field ID.
Bytes encode_schemas(const std::vector<ComponentSchema>& schemas);
std::vector<ComponentSchema> decode_schemas(std::span<const std::uint8_t> bytes);
Bytes encode_scope(const GameplayScope& scope);
GameplayScope decode_scope(std::span<const std::uint8_t> bytes);
}
