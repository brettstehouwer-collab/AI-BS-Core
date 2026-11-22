#include <aibs/placed_assets.hpp>
#include <aibs/asset_store.hpp>
#include <aibs/surface_codec.hpp>
#include <aibs/engine.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>

using namespace aibs;
namespace fs=std::filesystem;
namespace {
void need(bool b,const char* message){if(!b)throw std::runtime_error(message);}
template<class F>void reject(F f){bool bad=false;try{f();}catch(const std::invalid_argument&){bad=true;}need(bad,"Expected rejected surface placement");}
void write(const fs::path& p,std::span<const std::byte> b){std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char*>(b.data()),static_cast<std::streamsize>(b.size()));need(bool(f),"Write owned fixture");}
void write(const fs::path& p,const std::string& s){write(p,{reinterpret_cast<const std::byte*>(s.data()),s.size()});}
struct Scratch {
 fs::path parent=fs::canonical(fs::temp_directory_path()),path=parent/("aibs-surface-placement-"+new_uuid());
 Scratch(){fs::create_directory(path);}
 ~Scratch(){if(path.parent_path()==parent&&path.filename().string().starts_with("aibs-surface-placement-")){std::error_code ignored;fs::remove_all(path,ignored);}}
};
SurfaceMeshAsset triangle(std::string name,unsigned char value=160){
 auto a=import_surface_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n",std::vector<MeshMaterial>{{"pcb",{1,1,1},0}},new_uuid(),std::move(name),ObjUvOrigin::top_left);
 a.images={{ImageSemantic::srgb_color,{{1,1,{20,value,50,255}}}}};a.albedo_images={0};return a;
}
AssetPackReference publish(const fs::path& root,const fs::path& store,const SurfaceMeshAsset& a){
 const auto source=root/new_uuid();fs::create_directory(source);const auto encoded=encode_surface_asset(a);const auto sha=asset_sha256(encoded);
 write(source/(sha+".aibsurf"),encoded);write(source/"catalog.aibcat",std::string("AIBCAT 2\nsurface ")+a.geometry.asset_id+" "+sha+" "+sha+".aibsurf\n");
 write(source/"LICENSE.txt",std::string("Self-authored synthetic fixture\n"));write(source/"provenance.json",std::string("{\"origin\":\"test\"}\n"));return adopt_asset_pack(source,store);
}
void place(FirstBootContentDefinition& d,const AssetPackReference& ref,Vec3 center={}){d.placements.push_back({new_uuid(),"Surface instance",ref.asset_id,ref.asset_sha256,ref.pack_sha256,center,{1,1,1},{},true});}
SceneSnapshot scene_for(const FirstBootContent& c){const auto b=first_boot_content_baseline(c);return first_boot_content_scene({{"surface-placements",c.definition().world_id,"main",new_uuid()},b.revision,b.sequence,b.components},c);}
}
int main(int argc,char** argv){try{
 need(argc==2,"Reference legacy pack required");Scratch scratch;const auto store=scratch.path/"store";fs::create_directory(store);
 const auto surface=triangle("Textured PCB"),other_surface=triangle("Same pixels different asset");
 TexturedScene appended;append_surface_scene(appended,surface);append_surface_scene(appended,other_surface,{2,0,0});
 need(appended.images.size()==1&&appended.vertices.size()==6&&appended.draws.size()==2,"Shared surface composition deduplicates images");
 auto invalid=surface;invalid.albedo_images={20};reject([&]{append_surface_scene(appended,invalid);});need(appended.images.size()==1&&appended.vertices.size()==6&&appended.draws.size()==2,"Failed shared append preserves logical state");
 const auto ref=publish(scratch.path,store,surface),same=publish(scratch.path,store,other_surface),old=adopt_asset_pack(argv[1],store);
 const auto old_mesh=load_stored_asset(store,old);
 CreatorSession session(first_boot_schema(),"surface-placements","main");need(seed_first_boot(session).ok,"Seed template");
 auto d=FirstBootContent::from_template(session).definition();d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;
 place(d,ref,{-35,2,10});place(d,ref,{-32,2,10});d.placements.back().scale={2,3,1};place(d,same,{-29,2,10});place(d,old,{-25,2,10});
 auto c=FirstBootContent::create(d);auto scene=scene_for(c);const auto before=mesh_from_snapshot(scene);const PlacedAssetVisuals visuals(c,store);
 need(visuals.placement_count()==4,"All placements retained");need(visuals.mesh(scene).vertices.size()==before.vertices.size()+old_mesh.indices.size(),"Legacy geometry remains in base mesh and surfaces do not duplicate");
 const auto& layer=visuals.textured();need(layer.vertices.size()==9&&layer.draws.size()==3&&layer.images.size()==1,"Repeated instances and different assets share exact image resource");
 // Content canonicalization sorts instances by persistent UUID, so verify
 // transforms in the authoritative order instead of random insertion order.
 std::size_t offset=0;
 for(const auto& p:c.definition().placements)if(p.pack_sha256!=old.pack_sha256){
  need(layer.vertices[offset].position==p.center,"Instance origin preserves canonical placement transform");
  need(layer.vertices[offset+1].position==Vec3{p.center.x+p.scale.x,p.center.y,p.center.z}&&layer.vertices[offset+2].position==Vec3{p.center.x,p.center.y+p.scale.y,p.center.z},"Instance scale and translated corners remain distinct");
  offset+=3;
 }
 need(offset==layer.vertices.size(),"Every surface instance transform was checked");
 need(layer.draws[0].image==0&&layer.draws[1].image==0&&layer.draws[2].image==0,"Draw descriptors remapped");validate_textured_scene(layer);
 const auto picks=visuals.picking_scene(scene);need(picks.objects.size()==scene.objects.size()+4,"Geometry-derived selection proxies only");need(first_boot_content_scene({{"surface-placements",d.world_id,"main",new_uuid()},0,0,first_boot_content_baseline(c).components},c).objects.size()==scene.objects.size(),"Physics remains unchanged");
 need(!visuals.selection_mesh(d.placements[0].entity_id).vertices.empty(),"Surface can be selected");
 const auto staged=scratch.path/"private";stage_asset_packs(store,std::vector<AssetPackReference>{ref,same,old},staged,false,AssetContentProfile::warm_beginning);
 const auto reopened=first_boot_content_decode(first_boot_content_encode(c));const PlacedAssetVisuals replay(reopened,staged);need(replay.textured().images==layer.images&&replay.textured().vertices.size()==layer.vertices.size(),"Content/closure restart preserves owned textures");
 auto legacy=d;legacy.format_version=2;legacy.asset_profile=AssetContentProfile::legacy_v1;reject([&]{PlacedAssetVisuals ignored(FirstBootContent::create(legacy),store);});
 auto unsupported=d;unsupported.memories.push_back({new_uuid(),"Unimplemented media loader",{-10,2,10},ref});
 reject([&]{PlacedAssetVisuals ignored(FirstBootContent::create(unsupported),store);});
 GroundedCharacter anchor(scene,d.jenison_returns.front());
 for(unsigned tick=0;tick<32;++tick)anchor.advance({},1./60);
 need(anchor.state().grounded,"Fixture companion anchor must be physically settled");
 unsupported=d;unsupported.companions.push_back({new_uuid(),"Unimplemented character loader",anchor.state().feet,true,ref,{}});
 const auto unsupported_character=FirstBootContent::create(unsupported);
 reject([&]{PlacedAssetVisuals ignored(unsupported_character,store);});
 // The descriptor cap applies across the chapter, including distinct assets.
 auto wide=surface;wide.geometry.asset_id=new_uuid();for(unsigned n=1;n<32;++n)wide.images.push_back({ImageSemantic::srgb_color,{{1,1,{static_cast<unsigned char>(n),0,0,255}}}});
 const auto wide_ref=publish(scratch.path,store,wide),extra_ref=publish(scratch.path,store,triangle("Distinct pixel",170));auto over=d;over.placements.clear();place(over,wide_ref);place(over,extra_ref);reject([&]{PlacedAssetVisuals ignored(FirstBootContent::create(over),store);});
 // Validate composition against the base mesh, not each layer separately.
 auto large=surface;large.geometry.asset_id=new_uuid();large.geometry.indices.clear();large.geometry.triangle_materials.clear();large.corners.clear();
 for(unsigned t=0;t<100000;++t){large.geometry.indices.insert(large.geometry.indices.end(),surface.geometry.indices.begin(),surface.geometry.indices.end());large.geometry.triangle_materials.push_back(0);large.corners.insert(large.corners.end(),surface.corners.begin(),surface.corners.end());}
 const auto large_ref=publish(scratch.path,store,large);auto many=d;many.placements.clear();for(unsigned n=0;n<3;++n)place(many,large_ref,{static_cast<float>(n),0,0});const PlacedAssetVisuals many_visuals(FirstBootContent::create(many),store);
 auto crowded=scene;while(crowded.objects.size()<10000){auto box=crowded.objects.front();box.persistent_id=new_uuid();crowded.objects.push_back(std::move(box));}
 reject([&]{many_visuals.mesh(crowded);});
 // Corrupt stored content must not silently fall back to original source files.
 write(store/ref.pack_sha256/(ref.asset_sha256+".aibsurf"),std::string("bad"));reject([&]{PlacedAssetVisuals ignored(c,store);});need(layer.images.size()==1,"Existing immutable projection survives unrelated failed replacement");
 std::cout<<"PASS mixed surface placements, deduplicated images, transforms, bounds, private restart and unchanged collision\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
