#pragma once
#include <aibs/assets.hpp>
#include <aibs/surface_assets.hpp>
#include <aibs/character_assets.hpp>
#include <aibs/audio_assets.hpp>
#include <filesystem>
#include <span>
#include <string>
#include <vector>
#include <variant>

namespace aibs {
// Project metadata contains only these persistent identities/digests. The
// explicit store root is supplied by the owner, never serialized as a host path.
struct AssetPackReference {
 std::string asset_id;
 std::string asset_sha256;
 std::string pack_sha256;
 bool operator==(const AssetPackReference&) const = default;
};
inline constexpr std::size_t asset_store_maximum_references = 64;
inline constexpr std::size_t asset_store_maximum_unique_packs = 32;
inline constexpr std::size_t asset_store_maximum_staged_bytes = 64u * 1024u * 1024u;
enum class AssetContentProfile { legacy_v1, warm_beginning };
inline constexpr std::size_t asset_store_modern_staged_bytes = 128u * 1024u * 1024u;
// Audio alone has a48MiB cooked envelope plus bounded catalog/rights/provenance.
// Existing mesh/surface/character33MiB read defaults and32MiB payload caps stay.
inline constexpr std::size_t asset_store_maximum_audio_pack_bytes = 50u * 1024u * 1024u;
struct StoredVisualAsset {
 std::variant<MeshAsset,SurfaceMeshAsset> payload;
 std::size_t encoded_bytes=0,decoded_bytes=0;
};
struct AssetPackInspection { AssetPackReference reference;StoredVisualAsset asset; };
enum class StoredAssetKind { mesh_v1,surface_v2,character_v2,audio_v2 };
struct StoredTypedAsset {
 std::variant<MeshAsset,SurfaceMeshAsset,CharacterAsset,AudioAsset> payload;
 std::size_t encoded_bytes=0,decoded_bytes=0;
};
struct TypedAssetPackInspection {AssetPackReference reference;StoredAssetKind kind;StoredTypedAsset asset;};
struct StoredCharacterAsset {CharacterAsset payload;std::size_t encoded_bytes=0,decoded_bytes=0;};
struct StoredAudioAsset {AudioAsset payload;std::size_t encoded_bytes=0,decoded_bytes=0;};
// Typed inspection includes character/audio packs. Its historical33MiB default
// remains; pass50MiB explicitly for large audio, or use the audio loader below.
// Visual-only loaders reject characters/audio rather than treating them as scenery.
TypedAssetPackInspection inspect_asset_pack(const std::filesystem::path& source_pack,
 std::size_t maximum_read_bytes=33u*1024u*1024u);
StoredCharacterAsset load_stored_character_asset(const std::filesystem::path& store,
 const AssetPackReference&,std::size_t* verified_pack_bytes=nullptr,
 std::size_t maximum_read_bytes=33u*1024u*1024u);
StoredAudioAsset load_stored_audio_asset(const std::filesystem::path& store,
 const AssetPackReference&,std::size_t* verified_pack_bytes=nullptr,
 std::size_t maximum_read_bytes=asset_store_maximum_audio_pack_bytes);
AssetPackInspection inspect_visual_asset_pack(const std::filesystem::path& source_pack,
 std::size_t maximum_read_bytes=33u*1024u*1024u);
// Catalog and payload kind must agree. The returned charge includes all four
// pack files, with a separate decoded charge for dependency residency budgets.
StoredVisualAsset load_stored_visual_asset(const std::filesystem::path& store,
 const AssetPackReference&,std::size_t* verified_pack_bytes=nullptr,
 std::size_t maximum_read_bytes=33u*1024u*1024u);

void validate_asset_pack_reference(const AssetPackReference& reference);
// Source is one exact four-file v1 mesh or typed v2 surface/character/audio pack. Store must be an existing
// plain directory. Fresh immutable child publication; exact existing pack reuse.
AssetPackReference adopt_asset_pack(const std::filesystem::path& source_pack,
                                  const std::filesystem::path& store);
// Rechecks all four file lengths/digests and the canonical manifest-derived pack
// identity, catalog, decoded asset UUID and mesh SHA. No source fallback exists.
MeshAsset load_stored_asset(const std::filesystem::path& store,
                           const AssetPackReference& reference);
// Same verified read, with the complete four-file byte charge returned only on
// success. File lengths are checked against maximum_read_bytes before content
// reads, so callers can enforce a deduplicated aggregate dependency budget.
MeshAsset load_stored_asset(const std::filesystem::path& store,
                           const AssetPackReference& reference,
                           std::size_t* verified_pack_bytes,
                           std::size_t maximum_read_bytes = 33u * 1024u * 1024u);
// Copies the deduplicated requested closure to one NEW private store directory.
// Parent exists; destination itself must not exist. At most64 input references,
// 32 unique packs and64MiB aggregate pack bytes in the legacy profile. Explicit
// warm_beginning supports mixed v1/v2 with128MiB encoded/decoded charges.
// No partial final publication.
// merge_existing validates an existing private store (<=128MiB/256 packs), then
// adds/reuses immutable pack children. Failure may retain unused verified new
// packs, but existing packs are never changed. Publish a new snapshot only after
// this call succeeds. No garbage collection or save-document writes occur.
void stage_asset_packs(const std::filesystem::path& source_store,
                       std::span<const AssetPackReference> references,
                       const std::filesystem::path& destination_store,
                       bool merge_existing = false,
                       AssetContentProfile profile = AssetContentProfile::legacy_v1);
}
