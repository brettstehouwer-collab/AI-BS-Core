#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/warm_opening.hpp>
#include <aibs/opening_inspections.hpp>
#include <aibs/content_authoring.hpp>
#include <aibs/content_dependencies.hpp>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <set>
using namespace aibs;
namespace fs=std::filesystem;
namespace {
fs::path native_path(const fs::path& path){
 const auto value=path.native();
 if(value.starts_with(L"\\\\?\\"))return path;
 if(value.starts_with(L"\\\\"))return fs::path(L"\\\\?\\UNC\\"+value.substr(2));
 return fs::path(L"\\\\?\\"+value);
}
std::string path_utf8(const fs::path& path){const auto value=path.u8string();return std::string(reinterpret_cast<const char*>(value.data()),value.size());}
void publish_project(const fs::path& staging,const fs::path& output){
 const auto from=native_path(staging),to=native_path(output);
 unsigned attempts=1;
 if(MoveFileExW(from.c_str(),to.c_str(),MOVEFILE_WRITE_THROUGH)!=0)return;
 DWORD error=GetLastError();
 if(error==ERROR_ACCESS_DENIED||error==ERROR_SHARING_VIOLATION){
  const auto attributes=GetFileAttributesW(to.c_str());
  const DWORD probe_error=attributes==INVALID_FILE_ATTRIBUTES?GetLastError():ERROR_SUCCESS;
  if(attributes==INVALID_FILE_ATTRIBUTES&&probe_error==ERROR_FILE_NOT_FOUND){
   Sleep(150);
   attempts=2;
   if(MoveFileExW(from.c_str(),to.c_str(),MOVEFILE_WRITE_THROUGH)!=0)return;
   error=GetLastError();
  }
 }
 throw std::runtime_error("MoveFileExW project publication failed; Win32="+std::to_string(error)+"; attempts="+std::to_string(attempts)+"; source="+path_utf8(staging)+"; destination="+path_utf8(output));
}
std::string json(std::string_view value){std::string out="\"";for(const unsigned char c:value){if(c=='\"'||c=='\\'){out+='\\';out+=static_cast<char>(c);}else if(c=='\n')out+="\\n";else if(c=='\r')out+="\\r";else if(c=='\t')out+="\\t";else if(c<32)throw std::invalid_argument("Unsupported manifest control byte");else out+=static_cast<char>(c);}return out+'\"';}
void write(const fs::path& path,std::span<const unsigned char> bytes){std::ofstream file(path,std::ios::binary);file.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));file.close();if(!file.good())throw std::runtime_error("Cannot write owned opening output");}
void write(const fs::path& path,const std::string& value){write(path,std::span(reinterpret_cast<const unsigned char*>(value.data()),value.size()));}
AssetPackReference adopt(const fs::path& input,const fs::path& store,FirstBootDependencyKind role,bool capacitor_contract=false){
 AssetPackReference inspected_reference;
 {const auto inspected=inspect_asset_pack(input,role==FirstBootDependencyKind::audio?asset_store_maximum_audio_pack_bytes:33u*1024u*1024u);
  inspected_reference=inspected.reference;
  if(role==FirstBootDependencyKind::character){if(inspected.kind!=StoredAssetKind::character_v2)throw std::invalid_argument("Adam requires a typed character pack");}
  else if(role==FirstBootDependencyKind::audio){if(inspected.kind!=StoredAssetKind::audio_v2)throw std::invalid_argument("Recording requires a typed audio pack");const auto& a=std::get<AudioAsset>(inspected.asset.payload);if(a.sample_rate!=44100||a.channels!=2)throw std::invalid_argument("Original podium recording must retain 44.1kHz stereo");}
  else {const MeshAsset* mesh=nullptr;if(const auto* legacy=std::get_if<MeshAsset>(&inspected.asset.payload))mesh=legacy;else if(const auto* surface=std::get_if<SurfaceMeshAsset>(&inspected.asset.payload))mesh=&surface->geometry;else throw std::invalid_argument("Scenery requires a visual mesh/surface pack");
   if(capacitor_contract){Vec3 low{1,2,1},high{-1,-1,-1};for(const auto& v:mesh->vertices){if(std::hypot(v.position.x,v.position.z)>.35f||v.position.y<-.04f||v.position.y>1.3f)throw std::invalid_argument("Capacitor exceeds its explicit .35m radius/1.3m height, Y-up board-mount proxy contract (pins may extend .04m below the board)");low.x=std::min(low.x,v.position.x);low.y=std::min(low.y,v.position.y);low.z=std::min(low.z,v.position.z);high.x=std::max(high.x,v.position.x);high.y=std::max(high.y,v.position.y);high.z=std::max(high.z,v.position.z);}
   if(low.x>-.29f||low.z>-.29f||low.y>.28f||high.x<.29f||high.z<.29f||high.y<1.12f)throw std::invalid_argument("Capacitor does not match the owned shell dimensions required by its explicit inner collision core");}
  }
 }
 const auto adopted=adopt_asset_pack(input,store);if(adopted!=inspected_reference)throw std::invalid_argument("Pack changed after typed role/dimension inspection; private project publication rejected");return adopted;
}
}
int wmain(int argc,wchar_t** argv){try{
 fs::path output,capacitor,adam,audio,nook,fault,bypass,shelter;std::set<std::wstring> seen;bool workshop=false;for(int i=1;i<argc;){const std::wstring key=argv[i++];if(!seen.insert(key).second)throw std::invalid_argument("Duplicate opening factory option");if(key==L"--workshop"){if(workshop)throw std::invalid_argument("Duplicate --workshop flag");workshop=true;continue;}if(i>=argc)throw std::invalid_argument("Expected option/value pairs");const auto* value=argv[i++];if(key==L"--output")output=value;else if(key==L"--capacitor-pack")capacitor=value;else if(key==L"--adam-pack")adam=value;else if(key==L"--audio-pack")audio=value;else if(key==L"--nook-pack")nook=value;else if(key==L"--fault-pack")fault=value;else if(key==L"--bypass-pack")bypass=value;else if(key==L"--shelter-pack")shelter=value;else throw std::invalid_argument("Unknown opening factory option");}
 if(output.empty())throw std::invalid_argument("Required: --output NEW_DIRECTORY; optional --capacitor-pack, --adam-pack, --audio-pack, --nook-pack, --fault-pack, --bypass-pack, --shelter-pack, --workshop");output=fs::absolute(output).lexically_normal();
 if(fs::exists(output)||!fs::is_directory(output.parent_path())||output.filename().empty())throw std::invalid_argument("Opening output must be a new child of an existing directory");
 const auto token=new_uuid();const fs::path temporary=output.parent_path()/(output.filename().wstring()+L".staging-"+std::wstring(token.begin(),token.end()));if(fs::exists(temporary))throw std::invalid_argument("Owned staging directory unexpectedly exists");fs::create_directory(temporary);const auto store=temporary/"assets/packs";fs::create_directories(store);
 WarmOpeningAssetRefs references;if(!capacitor.empty())references.capacitor=adopt(capacitor,store,FirstBootDependencyKind::visual,true);if(!adam.empty())references.adam=adopt(adam,store,FirstBootDependencyKind::character);if(!audio.empty())references.original_recording=adopt(audio,store,FirstBootDependencyKind::audio);
 if(!nook.empty())references.nook=adopt(nook,store,FirstBootDependencyKind::visual);if(!fault.empty())references.fault=adopt(fault,store,FirstBootDependencyKind::visual);if(!bypass.empty())references.bypass=adopt(bypass,store,FirstBootDependencyKind::visual);if(!shelter.empty())references.shelter=adopt(shelter,store,FirstBootDependencyKind::visual);
 CreatorSession source(first_boot_schema(),"first-boot-warm-opening","warm-beginning-opening-v1");if(!seed_first_boot(source).ok)throw std::runtime_error("Cannot seed new opening branch");
 const auto draft=workshop?make_warm_workshop_draft(source,references):make_warm_opening_draft(source,references);const auto& definition=draft.definition;const auto content=FirstBootContent::create(definition);
 // Complete typed CPU closure admission and authoring save happen before the
 // directory becomes visible as a usable project. Native GPU admission is a
 // separate runtime contract, never claimed by this offline generator.
 {const auto closure=load_first_boot_content_assets(content,store);(void)closure;}
 ContentAuthoringHost host(content,"first-boot-warm-opening","warm-beginning-opening-v1");host.bind_asset_store(store);if(host.save(temporary/"chapter.aiba").status!=ContentAuthoringStatus::saved)throw std::runtime_error("Native chapter authoring save failed");write(temporary/"opening.aibd",first_boot_content_encode(content));write(temporary/"opening-tour.aibtour",encode_opening_tour(content,draft.tour));
 write(temporary/".aibs-chapter-project.json",workshop?std::string("{\"version\":3,\"project\":\"first-boot-warm-opening\",\"branch\":\"warm-beginning-opening-v1\",\"asset_profile\":\"warm-beginning\",\"opening_workshop\":true}\n"):std::string("{\"version\":2,\"project\":\"first-boot-warm-opening\",\"branch\":\"warm-beginning-opening-v1\",\"asset_profile\":\"warm-beginning\"}\n"));
 std::string report="{\n  \"version\":1,\n  \"definition_id\":"+json(definition.definition_id)+",\n  \"world_id\":"+json(definition.world_id)+",\n  \"fingerprint\":"+json(content.fingerprint())+",\n  \"required_capability\":\"chapter-authored-inspections-v1\",\n  \"required_capabilities\":[\"chapter-authored-inspections-v1\",\"chapter-initial-view-v1\"],\n  \"tour_bindings_file\":\"opening-tour.aibtour\",\n  \"pacing_target_minutes\":[8,12],\n  \"pacing_measured\":false,\n  \"timer_gates\":false,\n  \"guidance_is_authored\":true,\n  \"family_source_files_copied\":false,\n  \"audio_played\":false,\n  \"recording_bound\":"+std::string(references.original_recording?"true":"false")+",\n  \"stops\":[";
 const OpeningInspectionCatalog inspection_catalog(definition);bool comma=false;for(const auto& stop:inspection_catalog.entries()){if(comma)report+=",";comma=true;report+="\n    {\"id\":"+json(stop.fixture_id)+",\"title\":"+json(stop.title)+",\"source\":"+json(stop.source)+",\"action\":"+json(stop.action==OpeningInspectionAction::seat?"seat":"read")+"}";}report+="\n  ],\n  \"dependencies\":[";
 comma=false;for(const auto& dependency:first_boot_content_dependencies(content)){if(comma)report+=",";comma=true;const auto& r=dependency.reference;report+="\n    {\"kind\":"+std::to_string(static_cast<unsigned>(dependency.kind))+",\"asset_id\":"+json(r.asset_id)+",\"asset_sha256\":"+json(r.asset_sha256)+",\"pack_sha256\":"+json(r.pack_sha256)+"}";}report+="\n  ]\n}\n";if(workshop){
  const std::string old_required="\"required_capability\":\"chapter-authored-inspections-v1\"",new_required="\"required_capability\":\"chapter-workshop-commissioning-v1\"";
  const auto required=report.find(old_required);if(required==std::string::npos)throw std::logic_error("Missing opening capability manifest field");report.replace(required,old_required.size(),new_required);
  const std::string end_capabilities="\"chapter-initial-view-v1\"]";const auto capabilities=report.find(end_capabilities);if(capabilities==std::string::npos)throw std::logic_error("Missing opening capabilities list");report.replace(capabilities,end_capabilities.size(),"\"chapter-initial-view-v1\",\"chapter-workshop-commissioning-v1\"]");
  report.insert(report.find("\n")+1,"  \"opening_workshop\":true,\n");
 }write(temporary/"opening-manifest.json",report);
 // Exact folder publication only. Existing projects are never overwritten.
 publish_project(temporary,output);std::cout<<"Created separate creator-compatible Warm Beginning opening. No audio played.\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\nA failed private .staging directory may be retained for diagnostics; existing projects remain untouched.\n";return 1;}}
