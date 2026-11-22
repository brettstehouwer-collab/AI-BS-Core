#pragma once
#include <aibs/assets.hpp>
#include <aibs/scene.hpp>

namespace aibs {
struct AssetRecord {
 std::string asset_id;
 std::string sha256;
 std::string file;
};

// Read-only standalone catalog. Exact ASCII/LF syntax:
// AIBCAT 1\n<UUID> <lowercase SHA256> <same SHA256>.aibmesh\n...
// No comments, duplicate identities/digests/paths, relative directories or
// redirected filesystem components are accepted. No source fallback exists.
class AssetCatalog {
public:
 explicit AssetCatalog(const std::filesystem::path& root);
 const std::vector<AssetRecord>& records() const noexcept { return records_; }
 // Each load rechecks paths, bounds, file SHA before decoding, and asset UUID.
 // It returns a value without changing or importing any world/save document.
 MeshAsset load(const std::string& asset_id) const;
private:
 std::filesystem::path root_;
 std::vector<AssetRecord> records_;
};

// Presentation only: expands indexed triangles into the existing colored
// vertex format. It does not alter SceneSnapshot, picking, collision or saves.
// Positive finite scale; finite unit quaternion (1e-4 squared-norm tolerance).
// Normals use inverse transpose scale and normalized rotation. Validation,
// overflow or allocation failure leaves the entire destination mesh unchanged.
void append_asset_mesh(SceneMesh& scene, const MeshAsset& asset, Vec3 center,
                       Vec3 scale = {1,1,1}, Quaternion rotation = {});
}
