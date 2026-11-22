#pragma once
#include <aibs/first_boot_content.hpp>
namespace aibs {
enum class FirstBootDependencyKind : std::uint8_t {visual=0,character=1,audio=2};
struct FirstBootDependency {
 AssetPackReference reference;
 FirstBootDependencyKind kind=FirstBootDependencyKind::visual;
 bool operator==(const FirstBootDependency&)const=default;
};
// Canonical complete closure from immutable content, not a projection of the
// creator's visible rows. Structural collection never claims a loader exists.
// Conflicting kinds/identities for one pack digest reject before publication.
std::vector<FirstBootDependency> first_boot_content_dependencies(const FirstBootContent&);
struct FirstBootResolvedAsset {FirstBootDependency dependency;StoredTypedAsset asset;};
struct FirstBootAssetClosure {
 std::vector<FirstBootResolvedAsset> assets;
 std::size_t encoded_bytes=0,decoded_bytes=0;
 const StoredTypedAsset& require(const AssetPackReference&,FirstBootDependencyKind)const;
};
// Modern CPU admission validates the complete deduplicated closure and its
// typed role before publication. Native DX12 additionally admits GPU resources.
FirstBootAssetClosure load_first_boot_content_assets(const FirstBootContent&,
 const std::filesystem::path& store);
}
