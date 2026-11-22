#include <aibs/content_authoring.hpp>
#include <aibs/asset_store.hpp>
#include <aibs/creator_payload.hpp>
#include <aibs/gameplay_codec.hpp>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>

using namespace aibs;
namespace {
unsigned checks=0;
void need(bool value,const char* why){if(!value)throw std::runtime_error(why);++checks;}
template<class F>void rejects(F&& action,const char* why){bool rejected=false;try{action();}catch(const std::exception&){rejected=true;}need(rejected,why);}
using Bytes=std::vector<unsigned char>;
Bytes read(const std::filesystem::path& path){std::ifstream in(path,std::ios::binary|std::ios::ate);need(in.good(),"Read saved test document");const auto size=in.tellg();Bytes bytes(static_cast<std::size_t>(size));in.seekg(0);in.read(reinterpret_cast<char*>(bytes.data()),size);need(in.good(),"Read complete test document");return bytes;}
struct Directory{std::filesystem::path path=std::filesystem::temp_directory_path()/("aibs-placement-"+new_uuid());Directory(){std::filesystem::create_directory(path);}~Directory(){std::error_code ignored;std::filesystem::remove_all(path,ignored);}};
FirstBootContent content(){CreatorSession source(first_boot_schema(),"placement-proof","main");need(seed_first_boot(source).ok,"Seed independent content");return FirstBootContent::from_template(source);}
FirstBootAssetPlacement placement(const AssetPackReference& reference){return {new_uuid(),"Persistent part",reference.asset_id,reference.asset_sha256,reference.pack_sha256,{-20,2,-20},{1,1,1},{},true};}
// Frozen AIBD1 field order. This compatibility oracle deliberately has no
// placement/version dispatch and must remain byte-identical for legacy input.
Bytes legacy_bytes(const FirstBootContentDefinition& d){
 creator_payload::detail::Writer w;w.number(0x44424941,4);w.number(1,2);w.text(d.definition_id,true);w.text(d.world_id,true);w.text(d.binding_id,true);w.number(d.revision,8);
 auto point=[&](Vec3 p){w.real(p.x);w.real(p.y);w.real(p.z);};
 w.number(d.hardware.size(),4);for(const auto& [alias,e]:d.hardware){w.text(alias,true);w.text(e.name);w.text(e.persistent_id,true);w.number(e.fields.size(),4);for(const auto& [key,value]:e.fields){w.text(key,true);w.real(value);}}
 w.number(d.initial_records.size(),4);for(const auto& r:d.initial_records){const auto bytes=gameplay_codec::encode_component(r);w.number(bytes.size(),4);w.data.insert(w.data.end(),bytes.begin(),bytes.end());}
 w.number(d.fixtures.size(),4);for(const auto& f:d.fixtures){const auto& o=f.object;w.text(o.persistent_id,true);w.text(o.name);point(o.center);point(o.half_extent);point(o.color);w.real(o.emission);w.number(o.selectable,1);w.real(o.rotation.x);w.real(o.rotation.y);w.real(o.rotation.z);w.real(o.rotation.w);w.real(f.sheltered_emission);}
 for(const auto& zone:{d.hub,d.pencil}){point(zone.center);point(zone.half_extent);}for(const auto* list:{&d.jenison_returns,&d.hub_returns}){w.number(list->size(),4);for(auto p:*list)point(p);}point(d.isolation_switch);w.number(d.hints.size(),4);for(const auto& [key,value]:d.hints){w.text(key,true);w.text(value,true);}return w.data;
}
ContentEditRequest request(const ContentAuthoringHost& host,std::vector<ContentEdit> edits){const auto head=host.snapshot();return {new_uuid(),head->revision,head->content.fingerprint(),"Placement test",std::move(edits)};}
ContentAuthoringResult apply(ContentAuthoringHost& host,std::vector<ContentEdit> edits){return host.apply(host.snapshot()->scope,request(host,std::move(edits)));}
void dependency_budget_tests(){
 Directory directory;const auto store=directory.path/"packs";std::filesystem::create_directory(store);
 const std::vector<MeshMaterial> materials{{"owned",{.5f,.5f,.5f},0}};
 auto mesh=import_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl owned\nf 1 2 3\n",materials,new_uuid(),"Owned admission budget fixture");
 mesh.vertices.resize(mesh_asset_max_vertices,mesh.vertices.front());
 const auto encoded=encode_mesh_asset(mesh);const auto digest=asset_sha256(encoded);
 const auto bytes=[](const std::string& text){return std::vector<std::byte>(reinterpret_cast<const std::byte*>(text.data()),reinterpret_cast<const std::byte*>(text.data()+text.size()));};
 const auto catalog=bytes("AIBCAT 1\n"+mesh.asset_id+" "+digest+" "+digest+".aibmesh\n");
 std::vector<AssetPackReference> references;std::size_t total=0;
 for(unsigned index=0;index<27;++index){
  auto license=std::string("Self-authored admission fixture ")+std::to_string(index)+"\n";license.resize(64u*1024u,' ');
  auto provenance=std::string("{\"origin\":\"self-authored admission fixture\"}\n");provenance.resize(64u*1024u,' ');
  const std::map<std::string,std::vector<std::byte>> files{{digest+".aibmesh",encoded},{"catalog.aibcat",catalog},{"LICENSE.txt",bytes(license)},{"provenance.json",bytes(provenance)}};
  std::string manifest="AIBPACK 1\n";for(const auto& [name,data]:files){manifest+=name+" "+std::to_string(data.size())+" "+asset_sha256(data)+"\n";total+=data.size();}
  const auto pack_sha=asset_sha256(bytes(manifest));const auto pack=store/pack_sha;std::filesystem::create_directory(pack);
  for(const auto& [name,data]:files){std::ofstream out(pack/name,std::ios::binary);out.write(reinterpret_cast<const char*>(data.data()),static_cast<std::streamsize>(data.size()));out.close();need(out.good(),"Write complete owned four-file admission fixture");}
  references.push_back({mesh.asset_id,digest,pack_sha});
 }
 const auto decoded=mesh.vertices.size()*sizeof(AssetVertex)+mesh.indices.size()*sizeof(std::uint32_t)+mesh.triangle_materials.size()*sizeof(std::uint32_t)+mesh.materials.size()*sizeof(MeshMaterial)+mesh.name.size()+mesh.asset_id.size()+mesh.source_sha256.size()+mesh.materials.front().name.size();
 need(decoded*references.size()<asset_store_maximum_staged_bytes&&total>asset_store_maximum_staged_bytes&&total/27*26<asset_store_maximum_staged_bytes,"Regression isolates full-pack budget: decoded geometry fits,26 packs fit,27 four-file packs exceed64MiB");
 ContentAuthoringHost host(content(),"placement-proof","main");host.bind_asset_store(store);
 std::vector<ContentEdit> edits;for(const auto& reference:references)edits.push_back(ContentCreateAssetPlacement{placement(reference)});
 const auto before=host.snapshot();const auto rejected=host.preview(before->scope,request(host,edits));
 need(rejected.status==ContentAuthoringStatus::rejected&&host.snapshot()==before,"Preview rejects full four-file dependency budget even when decoded geometry and rendered triangles fit");
 edits.pop_back();edits.push_back(ContentCreateAssetPlacement{placement(references.front())});
 const auto accepted=host.preview(before->scope,request(host,std::move(edits)));
 need(accepted.status==ContentAuthoringStatus::prepared&&host.apply(accepted.change).status==ContentAuthoringStatus::applied,"Admission charges each unique full pack once and permits26 packs plus duplicate placement");
 auto invalid=content().definition();invalid.format_version=2;for(const auto& reference:references)invalid.placements.push_back(placement(reference));
 ContentAuthoringHost save_host(FirstBootContent::create(std::move(invalid)),"placement-proof","main");save_host.bind_asset_store(store);
 const auto save=directory.path/"oversized.aiba";
 need(save_host.save(save).status==ContentAuthoringStatus::rejected&&!std::filesystem::exists(save),"Save rejects an oversized dependency closure without publishing a document");
 rejects([&]{host.bind_asset_store(store/".."/"packs");},"Raw parent traversal in explicit store binding rejects before path normalization");
 need(host.preview(host.snapshot()->scope,request(host,{ContentCreateAssetPlacement{placement(references.front())}})).status==ContentAuthoringStatus::prepared,"Rejected store binding preserves the prior valid binding");
}
void codec_tests(const AssetPackReference& reference){
 const auto original=content();const auto v1=legacy_bytes(original.definition());
 need(original.definition().format_version==1&&first_boot_content_encode(original)==v1,"AIBD1 bytes remain exactly the frozen legacy layout");
 need(first_boot_content_encode(first_boot_content_decode(v1))==v1,"Legacy decode/reencode is byte preserving");
 auto d=original.definition();auto item=placement(reference);d.placements.push_back(item);
 rejects([&]{(void)FirstBootContent::create(d);},"AIBD1 cannot silently discard placements");
 d.format_version=2;const auto edited=FirstBootContent::create(d);const auto bytes=first_boot_content_encode(edited);
 need(bytes[4]==2&&bytes[5]==0&&first_boot_content_encode(first_boot_content_decode(bytes))==bytes,"AIBD2 canonical roundtrip retains reference/TRS/selection");
 need(edited.fingerprint()!=original.fingerprint(),"Placement content has a distinct immutable binding");
 auto empty=d;empty.placements.clear();const auto empty_bytes=first_boot_content_encode(FirstBootContent::create(empty));
 need(empty_bytes[4]==2&&first_boot_content_decode(empty_bytes).definition().format_version==2,"Empty AIBD2 does not silently downgrade");
 auto malformed=bytes;malformed[4]=3;rejects([&]{(void)first_boot_content_decode(malformed);},"Unknown content version rejected");
 malformed=bytes;malformed.push_back(0);rejects([&]{(void)first_boot_content_decode(malformed);},"Trailing AIBD2 bytes rejected");
 auto invalid=[&](const FirstBootAssetPlacement& bad){auto next=d;next.placements={bad};rejects([&]{(void)FirstBootContent::create(next);},"Invalid placement rejected by pure codec");};
 auto bad=item;bad.entity_id=reference.asset_id;invalid(bad);bad=item;bad.entity_id=d.world_id;invalid(bad);
 bad=item;bad.asset_sha256[0]='G';invalid(bad);bad=item;bad.pack_sha256="short";invalid(bad);
 bad=item;bad.asset_id="not-a-uuid";invalid(bad);bad=item;bad.name.clear();invalid(bad);
 bad=item;bad.center.x=std::numeric_limits<float>::infinity();invalid(bad);
 bad=item;bad.scale.y=0;invalid(bad);bad=item;bad.scale.z=-1;invalid(bad);
 bad=item;bad.rotation.w=2;invalid(bad);bad=item;bad.rotation={0,0,0,0};invalid(bad);
 auto duplicates=d;duplicates.placements.push_back(item);rejects([&]{(void)FirstBootContent::create(duplicates);},"Duplicate placement identities rejected");
 auto many=d;many.placements.clear();for(unsigned i=0;i<65;++i)many.placements.push_back(placement(reference));
 rejects([&]{(void)FirstBootContent::create(many);},"64 placement limit enforced");
 auto refs=d;refs.placements.clear();for(unsigned i=0;i<33;++i){auto p=placement(reference);p.asset_id=new_uuid();refs.placements.push_back(p);}
 rejects([&]{(void)FirstBootContent::create(refs);},"32 unique reference tuple limit enforced");
 auto sorted=d;auto second=item;second.entity_id=new_uuid();sorted.placements.push_back(second);std::reverse(sorted.placements.begin(),sorted.placements.end());
 const auto stable=FirstBootContent::create(sorted);need(std::is_sorted(stable.definition().placements.begin(),stable.definition().placements.end(),[](const auto& a,const auto& b){return a.entity_id<b.entity_id;}),"Placement rows serialize in stable UUID order");
 auto proposed=d;proposed.revision=original.definition().revision+1;const auto preview=first_boot_content_preview(original,proposed);
 need(preview.status==FirstBootContentPreviewStatus::new_play_branch&&preview.render_rebuild&&!preview.collision_rebuild&&!preview.power_dependencies&&!preview.quest_dependencies,"Placement-only Preview changes rendering and requests a fresh Play branch only");
}
void host_tests(const AssetPackReference& reference,const std::filesystem::path& store){
 Directory directory;const auto file=directory.path/"chapter.aiba";
 ContentAuthoringHost host(content(),"placement-proof","main");host.bind_asset_store(store);
 need(host.save(file).status==ContentAuthoringStatus::saved,"Save legacy baseline without asset dependencies");
 const auto saved=read(file);const auto before=host.snapshot();const auto item=placement(reference);
 const auto create=request(host,{ContentCreateAssetPlacement{item}});const auto encoded=encode_content_edit(create);
 need(encoded[0]==2&&encoded[1]==0&&encode_content_edit(decode_content_edit(encoded))==encoded,"New create operation uses canonical typed request2 tag5");
 auto wrong=encoded;wrong[0]=1;rejects([&]{(void)decode_content_edit(wrong);},"Placement tags cannot masquerade as typed request1");
 const auto old=request(host,{ContentSetField{before->content.definition().definition_id,"hint.adam.danger",std::string("Authored cue")}});
 need(encode_content_edit(old)[0]==1,"Existing typed field request keeps version1 bytes");
 const auto preview=host.preview(before->scope,create);
 need(preview.status==ContentAuthoringStatus::prepared&&host.snapshot()==before&&read(file)==saved,"Native placement Preview is private and preserves saved bytes");
 need(host.apply(preview.change).status==ContentAuthoringStatus::applied,"Explicit placement Apply publishes");
 need(host.snapshot()->content.definition().format_version==2&&host.snapshot()->content.definition().placements.size()==1,"First placement edit explicitly upgrades content to AIBD2");
 const auto rows=content_authoring_rows(host.snapshot()->content);const auto row=std::find_if(rows.begin(),rows.end(),[&](const auto& r){return r.entity_id==item.entity_id;});
 need(row!=rows.end()&&row->type_id=="authoring.AssetPlacement"&&row->fields.size()==15,"Placement exposes exact typed inspector row");
 for(const auto* field:{"asset_id","asset_sha256","pack_sha256"})need(apply(host,{ContentSetField{item.entity_id,field,std::string("immutable")}}).status==ContentAuthoringStatus::rejected,"Asset references are immutable through generic SetField");
 need(apply(host,{ContentSetField{item.entity_id,"x",-19.5}}).status==ContentAuthoringStatus::applied,"Placement transform remains typed authorable");
 const auto changed=host.snapshot();
 need(host.travel(changed->scope,{new_uuid(),changed->revision,changed->content.fingerprint(),false}).status==ContentAuthoringStatus::undone,"Placement transform Undo succeeds");
 const auto undone=host.snapshot();need(host.travel(undone->scope,{new_uuid(),undone->revision,undone->content.fingerprint(),true}).status==ContentAuthoringStatus::redone,"Placement transform Redo succeeds");
 need(host.save(file).status==ContentAuthoringStatus::saved,"Save resolves all referenced immutable packs");
 const auto saved_head=host.snapshot();auto restored=ContentAuthoringHost::open(file,"placement-proof","main");
 need(restored.snapshot()->content.fingerprint()==saved_head->content.fingerprint(),"Saved placement journal reopens without requiring asset I/O during replay");
 // An unavailable store cannot hide the rows or prevent explicit recovery erase.
 restored.bind_asset_store(directory.path/"missing-store");
 need(!content_authoring_rows(restored.snapshot()->content).empty(),"Missing dependencies preserve Describe/recovery visibility");
 need(restored.save(file).status!=ContentAuthoringStatus::saved,"Save with missing dependencies is rejected");
 const auto erase=request(restored,{ContentEraseAssetPlacement{item.entity_id}});need(encode_content_edit(erase)[0]==2,"Erase operation uses typed request2 tag6");
 need(restored.apply(restored.snapshot()->scope,erase).status==ContentAuthoringStatus::applied,"Explicit erase can recover a document with missing asset packs");
 need(restored.snapshot()->content.definition().placements.empty()&&restored.snapshot()->content.definition().format_version==2,"Erasing final placement retains AIBD2");
 restored.bind_asset_store(store);
 need(apply(restored,{ContentCreateAssetPlacement{item}}).status==ContentAuthoringStatus::rejected,"Erased placement UUID cannot be reused");
 // Dependency disappearance between Preview and Apply cannot publish anything.
 ContentAuthoringHost race(content(),"placement-proof","main");race.bind_asset_store(store);
 const auto accepted=race.preview(race.snapshot()->scope,request(race,{ContentCreateAssetPlacement{placement(reference)}}));
 need(accepted.status==ContentAuthoringStatus::prepared,"Dependency race starts from a valid private preview");
 const auto head=race.snapshot();race.bind_asset_store(directory.path/"missing-store");
 need(race.apply(accepted.change).status==ContentAuthoringStatus::rejected&&race.snapshot()==head,"Apply revalidates dependencies and preserves head on failure");
}
}
int main(int argc,char** argv){try{need(argc==2,"Pass self-authored cooked fixture root");Directory directory;const auto store=directory.path/"assets";std::filesystem::create_directory(store);const auto reference=adopt_asset_pack(std::filesystem::path(argv[1]),store);codec_tests(reference);host_tests(reference,store);dependency_budget_tests();std::cout<<"PASS: "<<checks<<" AIBD1/2 placement codec, private authoring, immutable reference, history and missing-dependency recovery checks\n";return 0;}catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}}
