#pragma once
#include <aibs/first_boot_content.hpp>
#include <aibs/textured_scene.hpp>
#include <filesystem>

namespace aibs {
struct FirstBootAssetClosure;
// Immutable render projection. Assets are resolved and hashed once at creation;
// physics keeps the original chapter SceneSnapshot. Picking uses a separate view.
class PlacedAssetVisuals {
 std::shared_ptr<const FirstBootAssetClosure> closure_;
 std::size_t resident_bytes_=0;
 SceneMesh geometry_;
 TexturedScene textured_;
 std::vector<SceneObject> proxies_;
 std::shared_ptr<const CharacterAsset> companion_;
 std::optional<SceneObject> companion_proxy_;
public:
 PlacedAssetVisuals(const FirstBootContent&,const std::filesystem::path& asset_store);
 // Retained immutable complete closure; aliases share PCM and character ownership.
 const std::shared_ptr<const FirstBootAssetClosure>& asset_closure()const noexcept{return closure_;}
 // Owned CPU content/projection storage; add renderer content GPU bytes separately.
 std::size_t resident_bytes()const noexcept{return resident_bytes_;}
 std::size_t placement_count()const noexcept{return proxies_.size();}
 SceneMesh mesh(const SceneSnapshot& physics_scene)const;
 const TexturedScene& textured()const noexcept{return textured_;}
 const CharacterAsset* companion_model()const noexcept{return companion_.get();}
 SceneSnapshot picking_scene(const SceneSnapshot& physics_scene)const;
 SceneMesh selection_mesh(const std::string& placement_id)const;
};
}
