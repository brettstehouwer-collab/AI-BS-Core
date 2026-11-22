#include <aibs/content_dependencies.hpp>
#include <aibs/guide_presentation.hpp>
#include <map>
#include <stdexcept>
namespace aibs {
std::vector<FirstBootDependency> first_boot_content_dependencies(const FirstBootContent& content){
 std::map<std::string,FirstBootDependency> unique;std::size_t count=0;
 const auto add=[&](AssetPackReference reference,FirstBootDependencyKind kind){
  if(++count>asset_store_maximum_references)throw std::invalid_argument("Content dependency reference count exceeds64");
  validate_asset_pack_reference(reference);FirstBootDependency dependency{std::move(reference),kind};
  const auto [it,inserted]=unique.emplace(dependency.reference.pack_sha256,dependency);
  if(!inserted&&it->second!=dependency)throw std::invalid_argument("Content pack has conflicting kind or identity");
  if(unique.size()>asset_store_maximum_unique_packs)throw std::invalid_argument("Content dependency closure exceeds32 unique packs");
 };
 const auto& d=content.definition();
 for(const auto& placement:d.placements)add({placement.asset_id,placement.asset_sha256,placement.pack_sha256},FirstBootDependencyKind::visual);
 for(const auto& companion:d.companions)if(companion.model)add(*companion.model,FirstBootDependencyKind::character);
 for(const auto& memory:d.memories)add(memory.audio,FirstBootDependencyKind::audio);
 std::vector<FirstBootDependency> result;result.reserve(unique.size());for(const auto& [digest,dependency]:unique){(void)digest;result.push_back(dependency);}return result;
}
const StoredTypedAsset& FirstBootAssetClosure::require(const AssetPackReference& reference,FirstBootDependencyKind kind)const{
 for(const auto& entry:assets)if(entry.dependency.reference==reference&&entry.dependency.kind==kind)return entry.asset;
 throw std::invalid_argument("Dependency absent from complete typed content closure");
}
FirstBootAssetClosure load_first_boot_content_assets(const FirstBootContent& content,const std::filesystem::path& store){
 if(content.definition().format_version<3||content.definition().asset_profile!=AssetContentProfile::warm_beginning)throw std::invalid_argument("Typed content closure requires warm-beginning AIBD3");
 const auto dependencies=first_boot_content_dependencies(content);FirstBootAssetClosure result;result.assets.reserve(dependencies.size());
 for(const auto& dependency:dependencies){
  if(store.empty())throw std::invalid_argument("An explicit project asset store is required");
  auto inspected=inspect_asset_pack(store/dependency.reference.pack_sha256,asset_store_modern_staged_bytes-result.encoded_bytes);
  if(inspected.reference!=dependency.reference)throw std::invalid_argument("Complete content dependency reference mismatch");
  const bool character=inspected.kind==StoredAssetKind::character_v2;
  const bool visual=inspected.kind==StoredAssetKind::mesh_v1||inspected.kind==StoredAssetKind::surface_v2;
  const bool audio=inspected.kind==StoredAssetKind::audio_v2;
  const bool role_matches=(dependency.kind==FirstBootDependencyKind::visual&&visual)||
   (dependency.kind==FirstBootDependencyKind::character&&character)||
   (dependency.kind==FirstBootDependencyKind::audio&&audio);
  if(!role_matches)throw std::invalid_argument("Content dependency catalog kind differs from binding role");
  if(character){const GuidePresentation clip_contract(std::get<CharacterAsset>(inspected.asset.payload).mesh);(void)clip_contract;}
  if(inspected.asset.decoded_bytes>asset_store_modern_staged_bytes-result.decoded_bytes)throw std::invalid_argument("Complete decoded dependency residency exceeds128MiB");
  result.encoded_bytes+=inspected.asset.encoded_bytes;result.decoded_bytes+=inspected.asset.decoded_bytes;
  result.assets.push_back({dependency,std::move(inspected.asset)});
 }
 return result;
}
}
