#include <aibs/companion_runtime.hpp>
#include <aibs/content_authoring.hpp>
#include <aibs/audio_codec.hpp>
#include <aibs/assets.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace fs=std::filesystem;
int wmain(int argc,wchar_t** argv){try{
 if(argc!=2)throw std::invalid_argument("Expected a new owned synthetic output directory");const fs::path output=fs::absolute(argv[1]);if(fs::exists(output)||!fs::is_directory(output.parent_path()))throw std::invalid_argument("Fixture output must be a new child of an existing directory");fs::create_directory(output);fs::create_directory(output/"empty-packs");
 CreatorSession source(first_boot_schema(),"memory-native-proof","main");if(!seed_first_boot(source).ok)throw std::runtime_error("Cannot seed native companion fixture");auto d=FirstBootContent::from_template(source).definition();d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;
 const auto spawn=d.jenison_returns.front();const Vec3 origin{spawn.x+32,spawn.y-.2f,spawn.z+25};auto point=[&](float x,float z,float height=.05f){return Vec3{origin.x+x,origin.y+height,origin.z+z};};
 FirstBootCompanionBinding adam;adam.entity_id=new_uuid();adam.name="Adam's memory";adam.spawn=spawn;adam.spawn.x+=2;
 AudioAsset recording;recording.asset_id=new_uuid();recording.name="Synthetic optional memory proof - no family speech";recording.sample_rate=44100;recording.channels=2;recording.frame_count=88200;recording.pcm.resize(352800,std::byte{0});recording.source_sha256=asset_sha256(recording.pcm);recording.captions={{0,44100,"Synthetic caption one: this is a generated silent test recording."},{44100,88200,"Synthetic caption two: no original family audio is used by this proof."}};recording.caption_review=AudioCaptionReview::checked;
 const auto encoded=encode_audio_asset(recording);const auto digest=asset_sha256(encoded);const auto pack=output/"synthetic-audio-pack";fs::create_directory(pack);
 const auto write=[&](const fs::path& path,std::string_view text){std::ofstream file(path,std::ios::binary);file.write(text.data(),static_cast<std::streamsize>(text.size()));file.close();if(!file.good())throw std::runtime_error("Cannot write synthetic memory fixture pack");};
 {std::ofstream file(pack/(digest+".aibaud"),std::ios::binary);file.write(reinterpret_cast<const char*>(encoded.data()),static_cast<std::streamsize>(encoded.size()));file.close();if(!file.good())throw std::runtime_error("Cannot write synthetic audio payload");}
 write(pack/"catalog.aibcat","AIBCAT 2\naudio "+recording.asset_id+" "+digest+" "+digest+".aibaud\n");write(pack/"LICENSE.txt","Self-authored synthetic silence and captions. No family originals.\n");write(pack/"provenance.json","{\"source\":\"generated-muted-native-memory-proof\",\"family_references_used\":false}\n");
 const auto audio_ref=adopt_asset_pack(pack,output/"empty-packs");FirstBootMemoryBinding memory;memory.entity_id=new_uuid();memory.name="Synthetic nook memory station";memory.position={spawn.x-1.5f,spawn.y,spawn.z};memory.audio=audio_ref;d.memories.push_back(memory);
 adam.routes.nodes={{"nook",adam.spawn},{"nook-turn",point(-33.5f,-25)},{"west",point(-37,-25)},{"west20",point(-37,-20)},{"west15",point(-37,-15)},{"west10",point(-37,-10)},{"fault",point(-37,-5.2f)},{"approach",point(-37,-1.5f)},{"junction",point(-37,1.9f)},{"main-front",point(-33,1.9f)},{"main-back",point(-33,6,.25f)},{"service-front",point(-41,1.9f)},{"service-back",point(-41,6,.25f)},{"hub",point(-37,8,.25f)},{"pencil-front",point(-37,10.7f,.25f)},{"pencil-back",point(-37,15,.25f)}};
 auto edge=[&](const char* from,const char* to,std::string gate=""){adam.routes.edges.push_back({from,to,std::move(gate),true});};edge("nook","nook-turn");edge("nook-turn","west");edge("west","west20");edge("west20","west15");edge("west15","west10");edge("west10","fault");edge("fault","approach");edge("approach","junction");edge("junction","main-front");edge("junction","service-front");edge("main-back","hub");edge("service-back","hub");edge("hub","pencil-front");
 for(const auto& r:d.initial_records)if(r.type_id=="firstboot.Door"){const auto role=std::get<std::string>(r.fields.at("role"));if(role=="main")edge("main-front","main-back",r.entity_id);else if(role=="service")edge("service-front","service-back",r.entity_id);else edge("pencil-front","pencil-back",r.entity_id);}
 d.companions.push_back(adam);FirstBootLightDefinition reserve;reserve.entity_id=new_uuid();reserve.name="Nook reserve fixture";reserve.position={spawn.x,spawn.y+3,spawn.z};reserve.color={1,.5f,.2f};reserve.intensity=3;reserve.radius=18;d.lights.push_back(reserve);
 const auto content=FirstBootContent::create(d);const auto bytes=first_boot_content_encode(content);std::ofstream f(output/"memory.aibd",std::ios::binary);f.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));f.close();if(!f.good())throw std::runtime_error("Cannot write companion fixture");
 fs::create_directories(output/"assets/packs");
 stage_asset_packs(output/"empty-packs",std::span(&audio_ref,1),output/"assets/packs",true,AssetContentProfile::warm_beginning);
 ContentAuthoringHost authoring(content,"memory-native-proof","main");authoring.bind_asset_store(output/"assets/packs");
 if(authoring.save(output/"chapter.aiba").status!=ContentAuthoringStatus::saved)throw std::runtime_error("Cannot save native authoring fixture");
 std::ofstream metadata(output/".aibs-chapter-project.json");metadata<<"{\"version\":2,\"project\":\"memory-native-proof\",\"branch\":\"main\",\"asset_profile\":\"warm-beginning\"}\n";metadata.close();if(!metadata.good())throw std::runtime_error("Cannot write native project metadata");
 std::ofstream expected(output/"expected.json");expected<<"{\"world_id\":\""<<d.world_id<<"\",\"fingerprint\":\""<<content.fingerprint()<<"\",\"companion_id\":\""<<adam.entity_id<<"\",\"memory_id\":\""<<memory.entity_id<<"\",\"family_references_used\":false,\"synthetic_silence\":true,\"asset_id\":\""<<audio_ref.asset_id<<"\",\"asset_sha256\":\""<<audio_ref.asset_sha256<<"\",\"pack_sha256\":\""<<audio_ref.pack_sha256<<"\"}\n";expected.close();if(!expected.good())throw std::runtime_error("Cannot write expected memory identity");std::cout<<"Prepared private synthetic native memory fixture\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
