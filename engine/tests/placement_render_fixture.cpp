#include <aibs/asset_store.hpp>
#include <aibs/chapter_viewport.hpp>
#include <aibs/content_authoring.hpp>
#include <aibs/persistence.hpp>
#include <aibs/placed_assets.hpp>
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>

using namespace aibs;
namespace {
using Bytes=std::vector<unsigned char>;
constexpr const char* project_name="placement-render-proof";
void need(bool value,const char* message){if(!value)throw std::runtime_error(message);}
std::string quote(const std::string& value){std::string result="\"";constexpr char hex[]="0123456789abcdef";for(const unsigned char c:value){if(c=='"'||c=='\\'){result+='\\';result+=static_cast<char>(c);}else if(c<32){result+="\\u00";result+=hex[c>>4];result+=hex[c&15];}else result+=static_cast<char>(c);}return result+'"';}
void write(const std::filesystem::path& path,const Bytes& bytes){std::ofstream stream(path,std::ios::binary);stream.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));need(stream.good(),"Cannot write owned placement proof fixture");}
void text(const std::filesystem::path& path,const std::string& value){write(path,Bytes(value.begin(),value.end()));}
Bytes read(const std::filesystem::path& path){const auto size=std::filesystem::file_size(path);need(size>0&&size<=1024*1024,"Invalid placement fixture read bound");Bytes bytes(static_cast<std::size_t>(size));std::ifstream stream(path,std::ios::binary);stream.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));need(stream.good(),"Cannot read complete placement fixture");return bytes;}
std::array<float,6> bounds(const SceneSnapshot& scene){need(!scene.objects.empty(),"Fixture requires visible legacy chapter geometry");const auto& first=scene.objects.front();std::array<float,6> result{first.center.x-first.half_extent.x,first.center.y-first.half_extent.y,first.center.z-first.half_extent.z,first.center.x+first.half_extent.x,first.center.y+first.half_extent.y,first.center.z+first.half_extent.z};for(const auto& object:scene.objects){result[0]=std::min(result[0],object.center.x-object.half_extent.x);result[1]=std::min(result[1],object.center.y-object.half_extent.y);result[2]=std::min(result[2],object.center.z-object.half_extent.z);result[3]=std::max(result[3],object.center.x+object.half_extent.x);result[4]=std::max(result[4],object.center.y+object.half_extent.y);result[5]=std::max(result[5],object.center.z+object.half_extent.z);}return result;}
struct Export {std::string fingerprint,snapshot_id,pick_snapshot_id;std::uint64_t head=0,content_revision=0;};
std::string state_json(const Export& value){std::ostringstream out;out<<"{\"fingerprint\":"<<quote(value.fingerprint)<<",\"snapshot_id\":"<<quote(value.snapshot_id)<<",\"pick_snapshot_id\":"<<quote(value.pick_snapshot_id)<<",\"head\":"<<value.head<<",\"content_revision\":"<<value.content_revision<<'}';return out.str();}
void snapshot(const std::filesystem::path& file,const ContentAuthoringSnapshot& head,const std::string& snapshot_id,const std::string& selected){
 const auto bytes=first_boot_content_encode(head.content);creator_payload::detail::Writer writer;writer.number(0x56424941,4);writer.number(1,2);writer.number(2,1);
 for(const auto& value:{snapshot_id,head.scope.project,head.scope.branch,head.scope.world_id})writer.text(value,true);
 writer.text(head.checkpoint_id);writer.number(head.revision,8);writer.text(selected);writer.number(bytes.size(),4);writer.data.insert(writer.data.end(),bytes.begin(),bytes.end());
 need(writer.data.size()<=chapter_viewport_maximum_bytes,"Fixture exceeds typed viewport envelope bound");
 (void)decode_chapter_viewport_snapshot(writer.data);write(file,writer.data);
}
Export export_stage(ContentAuthoringHost& host,const std::filesystem::path& output,const std::string& label,const std::filesystem::path& store,const std::array<float,6>& base_bounds){
 const auto head=host.snapshot();const auto bytes=first_boot_content_encode(head->content);write(output/(label+".aibd"),bytes);
 const auto id=new_uuid();snapshot(output/(label+".aibv"),*head,id,"");
 Export result{head->content.fingerprint(),id,"",head->revision,head->content.definition().revision};
 const ChapterViewportSnapshot projection{new_uuid(),head->scope,head->checkpoint_id,"",head->revision,head->content};
 const auto base=chapter_viewport_scene(projection);PlacedAssetVisuals visual(head->content,store);
 need(bounds(base)==base_bounds&&bounds(visual.picking_scene(base))==base_bounds,"Placement would change the overview framing; pixel proof must use identical camera bounds");
 const auto mesh=visual.mesh(base);need(!mesh.vertices.empty(),"Fixture composition has no geometry");
 if(!head->content.definition().placements.empty()){result.pick_snapshot_id=new_uuid();snapshot(output/(label+"-pick.aibv"),*head,result.pick_snapshot_id,head->content.definition().placements.front().entity_id);}
 return result;
}
ContentEditRequest request(const ContentAuthoringHost& host,std::vector<ContentEdit> edits,const std::string& label){const auto head=host.snapshot();return {new_uuid(),head->revision,head->content.fingerprint(),label,std::move(edits)};}
void preview_apply(ContentAuthoringHost& host,std::vector<ContentEdit> edits,const std::string& label){const auto before=host.snapshot();const auto result=host.preview(before->scope,request(host,std::move(edits),label));need(result.status==ContentAuthoringStatus::prepared&&host.snapshot()==before,"Fixture native Preview must remain private");need(host.apply(result.change).status==ContentAuthoringStatus::applied,"Fixture explicit Apply failed");}
void save(ContentAuthoringHost& host,const std::filesystem::path& file){const auto result=host.save(file);need(result.status==ContentAuthoringStatus::saved,result.message.c_str());}
void travel(ContentAuthoringHost& host,bool redo){const auto head=host.snapshot();const auto result=host.travel(head->scope,{new_uuid(),head->revision,head->content.fingerprint(),redo});need(result.status==(redo?ContentAuthoringStatus::redone:ContentAuthoringStatus::undone),"Fixture placement history failed");}
void create(const std::filesystem::path& source_pack,const std::filesystem::path& output){
 need(!std::filesystem::exists(output),"Placement render fixture requires a fresh output directory");
 const auto project=output/"project",store=project/"assets/packs",journal=project/"chapter.aiba";
 std::filesystem::create_directories(store);std::filesystem::create_directory(output/"protected");
 text(output/"protected/retained-player.sqlite","Retained player-save sentinel; never selected by a proof process\n");
 text(output/"protected/retained-chapter.aiba","Retained authoring sentinel; never selected by a proof process\n");
 const auto inspection=inspect_visual_asset_pack(source_pack);
 const bool surface=std::holds_alternative<SurfaceMeshAsset>(inspection.asset.payload);
 const auto expected_version=surface?3u:2u;
 const auto reference=adopt_asset_pack(source_pack,store);
 need(reference==inspection.reference,"Inspected and adopted source pack identity differ");
 CreatorSession source(first_boot_schema(),project_name,"main");need(seed_first_boot(source).ok,"Cannot seed independent legacy template");
 need(CheckpointStore::save(output/"legacy-world.aibs",source).ok,"Cannot save retained native legacy checkpoint");
 const auto original=FirstBootContent::from_template(source);const auto original_bytes=first_boot_content_encode(original);
 need(original.definition().format_version==1,"Fresh legacy template must retain AIBD1");write(output/"legacy-template.aibd",original_bytes);
 auto starting_definition=original.definition();
 if(surface){starting_definition.format_version=3;starting_definition.asset_profile=AssetContentProfile::warm_beginning;}
 ContentAuthoringHost host(FirstBootContent::create(std::move(starting_definition)),project_name,"main");host.bind_asset_store(store);save(host,journal);
 const ChapterViewportSnapshot base_projection{new_uuid(),host.snapshot()->scope,host.snapshot()->checkpoint_id,"",0,host.snapshot()->content};const auto framing=bounds(chapter_viewport_scene(base_projection));
 std::map<std::string,Export> states;states.emplace("baseline",export_stage(host,output,"baseline",store,framing));
 FirstBootAssetPlacement item{new_uuid(),"Persistent motherboard reference",reference.asset_id,reference.asset_sha256,reference.pack_sha256,{-13,2.8f,-5},{1,1,1},{},true};
 // The workshop capacitor is under1.2m tall; use the creator's explicit scale
 // so it is legible in the whole-board overview while keeping framing fixed.
 if(surface)item.scale={4,4,4};
 const auto saved_baseline=read(journal);const auto initial_head=host.snapshot();
 const auto prepared=host.preview(initial_head->scope,request(host,{ContentCreateAssetPlacement{item}},"Create persistent reference part"));
 need(prepared.status==ContentAuthoringStatus::prepared&&host.snapshot()==initial_head&&read(journal)==saved_baseline,"Native placement Preview changed a published head or saved journal");
 need(prepared.change->dependencies().render_rebuild&&!prepared.change->dependencies().collision_rebuild&&!prepared.change->dependencies().power_dependencies&&!prepared.change->dependencies().quest_dependencies,"Visual placement preview changed physics/gameplay dependencies");
 need(host.apply(prepared.change).status==ContentAuthoringStatus::applied&&read(journal)==saved_baseline,"Explicit Apply must preserve separate Save");save(host,journal);
 states.emplace("placed",export_stage(host,output,"placed",store,framing));
 preview_apply(host,{ContentSetField{item.entity_id,"x",-5.0}},"Move persistent reference part");save(host,journal);
 states.emplace("moved",export_stage(host,output,"moved",store,framing));
 preview_apply(host,{ContentEraseAssetPlacement{item.entity_id}},"Erase persistent reference part");save(host,journal);
 need(host.snapshot()->content.definition().format_version==expected_version&&host.snapshot()->content.definition().placements.empty(),"Erasing final placement must retain its selected content version");
 states.emplace("erased",export_stage(host,output,"erased",store,framing));
 travel(host,false);travel(host,true);travel(host,false);save(host,journal);
 need(host.snapshot()->content.definition().placements.size()==1&&host.snapshot()->content.definition().placements.front().entity_id==item.entity_id,"History restore lost the persistent placement identity");
 states.emplace("restored",export_stage(host,output,"restored",store,framing));
 need(states.at("moved").fingerprint==states.at("restored").fingerprint,"History restore changed authored placement bytes");
 need(read(output/"legacy-template.aibd")==original_bytes,"Placement fixture changed its original legacy template");
 const PlacedAssetVisuals actual(host.snapshot()->content,store);
 if(surface)need(actual.textured().vertices.size()==std::get<SurfaceMeshAsset>(inspection.asset.payload).geometry.indices.size()&&!actual.textured().images.empty(),"Typed fixture did not resolve owned textured geometry");
 else need(actual.textured().vertices.empty(),"Legacy fixture unexpectedly entered the textured path");
 std::ostringstream info;info<<"{\"schema_version\":1,\"world_id\":"<<quote(host.snapshot()->scope.world_id)<<",\"placement_id\":"<<quote(item.entity_id)<<",\"asset_id\":"<<quote(reference.asset_id)<<",\"asset_sha256\":"<<quote(reference.asset_sha256)<<",\"pack_sha256\":"<<quote(reference.pack_sha256)<<",\"preview_private\":true,\"legacy_v1_preserved\":true,\"overview_framing_unchanged\":true,\"asset_kind\":"<<quote(surface?"surface":"mesh")<<",\"payload_extension\":"<<quote(surface?".aibsurf":".aibmesh")<<",\"placement_content_version\":"<<expected_version<<",\"textured_vertices\":"<<actual.textured().vertices.size()<<",\"texture_count\":"<<actual.textured().images.size();
 for(const auto& [label,value]:states)info<<','<<quote(label)<<':'<<state_json(value);info<<"}\n";text(output/"expected.json",info.str());
 std::cout<<"Prepared independent AIBD1/"<<expected_version<<" placement stages and saved authoring journal\n";
}
void reopen(const std::filesystem::path& output){
 const auto journal=output/"project/chapter.aiba",store=output/"project/assets/packs";const auto saved=read(journal);
 auto host=ContentAuthoringHost::open(journal,project_name,"main");host.bind_asset_store(store);
 const auto expected=first_boot_content_decode(read(output/"restored.aibd"));const auto head=host.snapshot();
 need(head->content.fingerprint()==expected.fingerprint()&&head->scope.world_id==expected.definition().world_id,"Separate native owner reopen lost the saved content/world identity");
 need(head->content.definition().placements.size()==1&&head->content.definition().placements.front().entity_id==expected.definition().placements.front().entity_id,"Separate native owner reopen lost placement UUID");
 const ChapterViewportSnapshot projection{new_uuid(),head->scope,head->checkpoint_id,"",head->revision,head->content};const auto base_bounds=bounds(chapter_viewport_scene(projection));
 const auto state=export_stage(host,output,"reopened",store,base_bounds);need(read(journal)==saved,"Native reopen rewrote the authored journal");
 std::ostringstream info;info<<"{\"fingerprint\":"<<quote(state.fingerprint)<<",\"world_id\":"<<quote(head->scope.world_id)<<",\"placement_id\":"<<quote(head->content.definition().placements.front().entity_id)<<",\"head\":"<<head->revision<<"}\n";text(output/"reopened.json",info.str());
 std::cout<<"Reopened saved native placement identity in a separate process\n";
}
}
int wmain(int argc,wchar_t** argv){try{need(argc==3,"Usage: aibs_placement_render_fixture SOURCE_PACK NEW_OUTPUT or --reopen OUTPUT");if(std::wstring(argv[1])==L"--reopen")reopen(std::filesystem::path(argv[2]));else create(std::filesystem::path(argv[1]),std::filesystem::path(argv[2]));return 0;}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
