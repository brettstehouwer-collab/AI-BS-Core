#include <aibs/asset_store.hpp>
#include <aibs/character_codec.hpp>
#include <aibs/guide_presentation.hpp>
#include <aibs/content_authoring.hpp>
#include <aibs/content_dependencies.hpp>
#include <aibs/placed_assets.hpp>
#include <aibs/engine.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <algorithm>
using namespace aibs;
namespace {
std::size_t checks=0;
void need(bool b,const char* m){++checks;if(!b)throw std::runtime_error(m);}
template<class F>void reject(F f,const char* message){bool rejected=false;try{f();}catch(const std::invalid_argument&){rejected=true;}need(rejected,message);}
std::vector<std::byte> bytes(std::string_view v){return {reinterpret_cast<const std::byte*>(v.data()),reinterpret_cast<const std::byte*>(v.data()+v.size())};}
void write(const std::filesystem::path& p,std::span<const std::byte> value){std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char*>(value.data()),static_cast<std::streamsize>(value.size()));need(f.good(),"Cannot write owned test fixture");}
void text(const std::filesystem::path& p,std::string_view value){write(p,bytes(value));}
CharacterAsset asset(){CharacterAsset a;a.asset_id=new_uuid();a.name="Synthetic textured guide";a.source_sha256=std::string(64,'1');a.mesh=make_guide_placeholder();a.images={{ImageSemantic::srgb_color,{{2,2,{255,0,0,255,0,255,0,255,0,0,255,255,255,255,255,255}}}}};generate_image_mips(a.images[0]);a.materials={{0,{1,1,1},0,true},{character_no_image,{.2f,.5f,.8f},.1f,false}};const auto half=static_cast<std::uint32_t>(a.mesh.indices.size()/2);a.draws={{0,half,0},{half,half,1}};validate_character_asset(a);return a;}
void pack(const std::filesystem::path& folder,const CharacterAsset& a,std::string kind="character",std::string suffix=".aibchar"){
 std::filesystem::create_directory(folder);const auto payload=encode_character_asset(a);const auto digest=asset_sha256(payload);
 write(folder/(digest+suffix),payload);text(folder/"catalog.aibcat","AIBCAT 2\n"+kind+" "+a.asset_id+" "+digest+" "+digest+suffix+"\n");
 text(folder/"LICENSE.txt","Synthetic test asset owned by AI-BS. No family references.\n");text(folder/"provenance.json","{\"source\":\"generated-synthetic-character\"}\n");
}
AssetPackReference scenery_pack(const std::filesystem::path& folder,const std::filesystem::path& store){
 const std::array materials{MeshMaterial{"plain",{.3f,.6f,.2f},0}};
 const auto mesh=import_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",materials,new_uuid(),"Synthetic placement");
 const auto payload=encode_mesh_asset(mesh);const auto digest=asset_sha256(payload);std::filesystem::create_directory(folder);
 write(folder/(digest+".aibmesh"),payload);text(folder/"catalog.aibcat","AIBCAT 1\n"+mesh.asset_id+" "+digest+" "+digest+".aibmesh\n");
 text(folder/"LICENSE.txt","Self-authored synthetic scenery.\n");text(folder/"provenance.json","{\"source\":\"synthetic-placement\"}\n");return adopt_asset_pack(folder,store);
}
std::size_t files(const std::filesystem::path& folder){return static_cast<std::size_t>(std::distance(std::filesystem::directory_iterator(folder),std::filesystem::directory_iterator{}));}
}
int main(int argc,char**argv){try{
 need(argc==2,"Pass private evidence parent");std::filesystem::create_directories(argv[1]);const auto root=std::filesystem::path(argv[1])/new_uuid();std::filesystem::create_directory(root);const auto store=root/"store";std::filesystem::create_directory(store);
 const auto original=asset();pack(root/"source",original);const auto inspected=inspect_asset_pack(root/"source");
 need(inspected.kind==StoredAssetKind::character_v2&&std::holds_alternative<CharacterAsset>(inspected.asset.payload),"Typed inspection loses character kind");
 need(encode_character_asset(std::get<CharacterAsset>(inspected.asset.payload))==encode_character_asset(original),"Typed inspection changed character bytes");
 need(inspected.asset.decoded_bytes==character_asset_cost(std::get<CharacterAsset>(inspected.asset.payload)).decoded_bytes&&inspected.asset.encoded_bytes>encode_character_asset(original).size(),"Complete pack/decoded charges missing");
 reject([&]{(void)inspect_visual_asset_pack(root/"source");},"Character accepted as scenery during visual inspection");
 const auto reference=adopt_asset_pack(root/"source",store);need(reference==inspected.reference&&files(store)==1,"Immutable character adoption differs from inspection");
 need(adopt_asset_pack(root/"source",store)==reference&&files(store)==1,"Identical character adoption is not exact reuse");
 std::size_t charged=0;const auto loaded=load_stored_character_asset(store,reference,&charged);
 need(charged==inspected.asset.encoded_bytes&&loaded.encoded_bytes==charged&&loaded.decoded_bytes==character_asset_cost(loaded.payload).decoded_bytes,"Typed load byte accounting differs");
 need(encode_character_asset(loaded.payload)==encode_character_asset(original),"Stored character differs from complete source");
 reject([&]{(void)load_stored_asset(store,reference);},"Legacy mesh loader accepted character");
 reject([&]{(void)load_stored_visual_asset(store,reference);},"Static visual loader accepted character");
 auto wrong=reference;wrong.asset_id=new_uuid();reject([&]{(void)load_stored_character_asset(store,wrong);},"Foreign UUID accepted");
 wrong=reference;wrong.asset_sha256=std::string(64,'2');reject([&]{(void)load_stored_character_asset(store,wrong);},"Foreign asset digest accepted");
 reject([&]{(void)load_stored_character_asset(store,reference,nullptr,charged-1);},"Read budget checked after oversized read");
 reject([&]{stage_asset_packs(store,std::span(&reference,1),root/"legacy-stage");},"Character staged under legacy64MiB profile");
 need(!std::filesystem::exists(root/"legacy-stage"),"Failed legacy staging published a directory");
 const std::array refs{reference,reference};stage_asset_packs(store,refs,root/"modern-stage",false,AssetContentProfile::warm_beginning);
 need(files(root/"modern-stage")==1,"Repeated character dependencies were not deduplicated");
 need(encode_character_asset(load_stored_character_asset(root/"modern-stage",reference).payload)==encode_character_asset(original),"Private staging changed owned images/animation");
 CreatorSession source(first_boot_schema(),"character-authoring","main");need(seed_first_boot(source).ok,"Could not seed companion authoring fixture");
 auto definition=FirstBootContent::from_template(source).definition();definition.format_version=3;definition.asset_profile=AssetContentProfile::warm_beginning;
 FirstBootCompanionBinding binding;binding.entity_id=new_uuid();binding.name="Adam memory";binding.spawn=definition.jenison_returns.front();binding.spawn.x+=2;definition.companions={binding};
 ContentAuthoringHost editor(FirstBootContent::create(definition),"character-authoring","main");editor.bind_asset_store(store);
 const auto rows=content_authoring_rows(editor.snapshot()->content);need(std::any_of(rows.begin(),rows.end(),[&](const auto& r){return r.entity_id==binding.entity_id&&r.type_id=="authoring.CompanionBinding";}),"Companion binding is not exposed to native authoring");
 const auto before=editor.snapshot();ContentEditRequest assign{"assign-adam-model",before->revision,before->content.fingerprint(),"Assign verified character",{
  ContentSetField{binding.entity_id,"model_bound",true},ContentSetField{binding.entity_id,"model_asset_id",reference.asset_id},ContentSetField{binding.entity_id,"model_asset_sha256",reference.asset_sha256},ContentSetField{binding.entity_id,"model_pack_sha256",reference.pack_sha256}}};
 auto prepared=editor.preview(before->scope,assign);need(prepared.status==ContentAuthoringStatus::prepared&&editor.snapshot()==before,"Character assignment did not produce an isolated valid preview");
 need(editor.apply(prepared.change).status==ContentAuthoringStatus::applied,"Character assignment failed native Apply");
 need(editor.snapshot()->content.definition().companions.front().model==reference,"Applied companion reference differs");
 const auto closure=first_boot_content_dependencies(editor.snapshot()->content);need(closure.size()==1&&closure.front().kind==FirstBootDependencyKind::character&&closure.front().reference==reference,"Native export closure omitted companion model");
 PlacedAssetVisuals projection(editor.snapshot()->content,store);need(projection.placement_count()==0&&projection.companion_model()&&encode_character_asset(*projection.companion_model())==encode_character_asset(original),"Native projection lost typed model or counted it as a placement");
 const auto scenery=scenery_pack(root/"scenery",store);FirstBootAssetPlacement placement;placement.entity_id=new_uuid();placement.name="Persistent motherboard part";placement.asset_id=scenery.asset_id;placement.asset_sha256=scenery.asset_sha256;placement.pack_sha256=scenery.pack_sha256;placement.center={-35,1,10};
 auto head=editor.snapshot();need(editor.apply(head->scope,{"place-part",head->revision,head->content.fingerprint(),"Place scenery beside Adam",{ContentCreateAssetPlacement{placement}}}).status==ContentAuthoringStatus::applied,"Placement with a companion model failed");
 const auto placed_fingerprint=editor.snapshot()->content.fingerprint();head=editor.snapshot();need(editor.apply(head->scope,{"move-part",head->revision,head->content.fingerprint(),"Move placed part",{ContentSetField{placement.entity_id,"x",-34.0}}}).status==ContentAuthoringStatus::applied,"Placement edit with a companion model failed");
 const auto moved_fingerprint=editor.snapshot()->content.fingerprint();
 const auto model_and_placement=[&](const ContentAuthoringHost& owner,float x){const auto& d=owner.snapshot()->content.definition();return d.format_version==3&&d.companions.front().model==reference&&d.placements.size()==1&&d.placements.front().entity_id==placement.entity_id&&d.placements.front().center.x==x;};
 need(model_and_placement(editor,-34),"Placement edit downgraded v3 or lost companion model");head=editor.snapshot();need(editor.travel(head->scope,{"undo-part",head->revision,head->content.fingerprint(),false}).status==ContentAuthoringStatus::undone&&editor.snapshot()->content.fingerprint()==placed_fingerprint&&model_and_placement(editor,-35),"Placement Undo changed companion binding");
 head=editor.snapshot();need(editor.travel(head->scope,{"redo-part",head->revision,head->content.fingerprint(),true}).status==ContentAuthoringStatus::redone&&editor.snapshot()->content.fingerprint()==moved_fingerprint&&model_and_placement(editor,-34),"Placement Redo changed companion binding");
 const auto authoring_file=root/"chapter.aiba";need(editor.save(authoring_file).status==ContentAuthoringStatus::saved,"Cannot save placement and companion journal");
 auto reopened=ContentAuthoringHost::open(authoring_file,"character-authoring","main");reopened.bind_asset_store(store);need(reopened.snapshot()->content.fingerprint()==moved_fingerprint&&model_and_placement(reopened,-34)&&reopened.snapshot()->undo_depth==editor.snapshot()->undo_depth,"Reopen lost model, placement or Undo history");
 head=reopened.snapshot();need(reopened.travel(head->scope,{"undo-reopened-part",head->revision,head->content.fingerprint(),false}).status==ContentAuthoringStatus::undone&&model_and_placement(reopened,-35),"Reopened placement Undo lost companion model");head=reopened.snapshot();need(reopened.travel(head->scope,{"redo-reopened-part",head->revision,head->content.fingerprint(),true}).status==ContentAuthoringStatus::redone&&model_and_placement(reopened,-34),"Reopened placement Redo lost companion model");need(reopened.save(authoring_file).status==ContentAuthoringStatus::saved,"Cannot save reopened model and placement history");
 const auto complete=load_first_boot_content_assets(reopened.snapshot()->content,store);need(complete.assets.size()==2&&std::holds_alternative<CharacterAsset>(complete.require(reference,FirstBootDependencyKind::character).payload)&&std::holds_alternative<MeshAsset>(complete.require(scenery,FirstBootDependencyKind::visual).payload),"Reopened complete dependency closure lost scenery or model");
 const auto replace_model=[&](const AssetPackReference& replacement,const std::string& id){const auto old=reopened.snapshot();const ContentEditRequest request{id,old->revision,old->content.fingerprint(),"Reject invalid exact companion replacement",{ContentSetField{binding.entity_id,"model_asset_id",replacement.asset_id},ContentSetField{binding.entity_id,"model_asset_sha256",replacement.asset_sha256},ContentSetField{binding.entity_id,"model_pack_sha256",replacement.pack_sha256}}};need(reopened.apply(old->scope,request).status==ContentAuthoringStatus::rejected&&reopened.snapshot()==old&&model_and_placement(reopened,-34),"Invalid exact model replacement changed logical head");};
 replace_model(scenery,"reject-scenery-as-companion");
 auto absent=reference;absent.pack_sha256=std::string(64,'f');replace_model(absent,"reject-absent-companion-pack");
 auto wrong_clips=asset();wrong_clips.mesh.clips.front().name="unbound-idle";pack(root/"wrong-clips",wrong_clips);replace_model(adopt_asset_pack(root/"wrong-clips",store),"reject-incompatible-guide-clips");
 stage_asset_packs(store,refs,root/"modern-stage",true,AssetContentProfile::warm_beginning);need(files(root/"modern-stage")==1,"Merge changed exact existing pack");
 pack(root/"wrong-kind",original,"surface");reject([&]{(void)inspect_asset_pack(root/"wrong-kind");},"Wrong catalog kind admitted");
 pack(root/"wrong-suffix",original,"character",".aibsurf");reject([&]{(void)inspect_asset_pack(root/"wrong-suffix");},"Character catalog/suffix mismatch admitted");
 auto second=asset();pack(root/"second",second);const auto second_ref=adopt_asset_pack(root/"second",store);
 const auto corrupt_file=store/second_ref.pack_sha256/(second_ref.asset_sha256+".aibchar");auto corrupt=encode_character_asset(second);corrupt[corrupt.size()/2]^=std::byte{1};write(corrupt_file,corrupt);
 replace_model(second_ref,"reject-corrupt-companion");
 const std::array bad_refs{reference,second_ref};reject([&]{stage_asset_packs(store,bad_refs,root/"failed-stage",false,AssetContentProfile::warm_beginning);},"Corrupt typed dependency staged");
 need(!std::filesystem::exists(root/"failed-stage"),"Corrupt closure published partial final store");
 need(encode_character_asset(load_stored_character_asset(root/"modern-stage",reference).payload)==encode_character_asset(original),"Failed replacement corrupted previous private store");
 // Destroy the import source pack; the independent immutable store still owns
 // complete mip/animation bytes. Only exact test-owned files are removed.
 for(const auto& e:std::filesystem::directory_iterator(root/"source"))std::filesystem::remove(e.path());std::filesystem::remove(root/"source");
 need(encode_character_asset(load_stored_character_asset(store,reference).payload)==encode_character_asset(original),"Stored character falls back to removed source");
 std::ofstream report(root/"verification.json");report<<"{\"status\":\"passed\",\"checks\":"<<checks<<",\"character_pack_bytes\":"<<charged<<",\"source_removed\":true,\"private_closure_exact\":true,\"legacy_profile_rejected\":true}\n";
 need(report.good(),"Cannot write typed store evidence");std::cout<<"PASS "<<checks<<" typed character store contracts "<<root.string()<<'\n';return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
