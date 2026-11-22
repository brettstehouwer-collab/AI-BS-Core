#include <aibs/placed_assets.hpp>
#include <aibs/asset_store.hpp>
#include <aibs/engine.hpp>
#include <aibs/gameplay.hpp>
#include <filesystem>
#include <iostream>
#include <stdexcept>

namespace {
void need(bool result,const char* message){if(!result)throw std::runtime_error(message);}
struct Scratch {std::filesystem::path path=std::filesystem::temp_directory_path()/("aibs-placed-"+aibs::new_uuid());Scratch(){std::filesystem::create_directory(path);}~Scratch(){std::error_code ignored;std::filesystem::remove_all(path,ignored);}};
}
int main(int argc,char** argv){
 try {
  need(argc==2,"Explicit native reference pack required");Scratch scratch;
  const auto store=scratch.path/"packs";std::filesystem::create_directory(store);
  const auto ref=aibs::adopt_asset_pack(argv[1],store);
  const auto mesh=aibs::load_stored_asset(store,ref);
  aibs::CreatorSession source(aibs::first_boot_schema(),"placed-visuals","main");need(aibs::seed_first_boot(source).ok,"Seed independent chapter");
  auto definition=aibs::FirstBootContent::from_template(source).definition();definition.format_version=2;
  const auto id=aibs::new_uuid();definition.placements.push_back({id,"Placed cooling assembly",ref.asset_id,ref.asset_sha256,ref.pack_sha256,{-35,2,10},{1,1,1},{},true});
  const auto content=aibs::FirstBootContent::create(definition);
  const aibs::GameplayScope scope{"placed-visuals",definition.world_id,"main",aibs::new_uuid()};
  const auto baseline=aibs::first_boot_content_baseline(content);const aibs::GameplayStoreRecovery state{scope,baseline.revision,baseline.sequence,baseline.components};
  const auto scene=aibs::first_boot_content_scene(state,content);const auto before=aibs::mesh_from_snapshot(scene);
  const aibs::PlacedAssetVisuals visuals(content,store);
  const auto rendered=visuals.mesh(scene);need(rendered.vertices.size()==before.vertices.size()+mesh.indices.size(),"Actual indexed mesh triangles enter the chapter render geometry");
  need(visuals.placement_count()==1,"One placement resolves once");
  const auto picks=visuals.picking_scene(scene);need(picks.objects.size()==scene.objects.size()+1,"Pick-only proxy is additive");
  const auto& proxy=picks.objects.back();need(proxy.persistent_id==id&&proxy.selectable,"Pick proxy preserves placement UUID");
  const auto hit=aibs::pick_scene(picks,{proxy.center.x,proxy.center.y+proxy.half_extent.y+5,proxy.center.z},{0,-1,0},10);
  need(hit&&hit->persistent_id==id,"Picking selects the placed part identity");
  need(!visuals.selection_mesh(id).vertices.empty(),"Selected placement gets a bounded edge highlight");
  need(visuals.selection_mesh(aibs::new_uuid()).vertices.empty(),"Foreign selection adds no visual geometry");
  need(aibs::mesh_from_snapshot(scene).vertices.size()==before.vertices.size(),"Composition leaves physics/source boxes unchanged");
  need(aibs::first_boot_content_scene(state,content).objects.size()==scene.objects.size(),"Game collision projection does not acquire pick-only proxies");
  const auto staged=scratch.path/"private-packs";aibs::stage_asset_packs(store,std::span<const aibs::AssetPackReference>(&ref,1),staged);
  const aibs::PlacedAssetVisuals reopened(content,staged);need(reopened.mesh(scene).vertices.size()==rendered.vertices.size(),"Private Play closure renders identically");
  bool rejected=false;try{(void)aibs::PlacedAssetVisuals(content,scratch.path/"missing");}catch(const std::exception&){rejected=true;}need(rejected,"Missing dependency rejects before publication");
  auto empty=definition;empty.placements.clear();const aibs::PlacedAssetVisuals none(aibs::FirstBootContent::create(empty),{});
  need(none.mesh(scene).vertices.size()==before.vertices.size(),"Empty/legacy visuals do not require an asset store");
  std::cout<<"PASS: placed visual geometry, persistent picking, isolated dependencies and unchanged collision\n";return 0;
 }catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}
}
