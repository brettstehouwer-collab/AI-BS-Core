#include <aibs/companion_runtime.hpp>
#include <aibs/content_authoring.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace fs=std::filesystem;
int wmain(int argc,wchar_t** argv){try{
 if(argc!=2&&argc!=3)throw std::invalid_argument("Expected a new owned output directory and optional model pack");const fs::path output=fs::absolute(argv[1]);if(fs::exists(output)||!fs::is_directory(output.parent_path()))throw std::invalid_argument("Fixture output must be a new child of an existing directory");fs::create_directory(output);fs::create_directory(output/"empty-packs");
 CreatorSession source(first_boot_schema(),"companion-native-proof","main");if(!seed_first_boot(source).ok)throw std::runtime_error("Cannot seed native companion fixture");auto d=FirstBootContent::from_template(source).definition();d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;
 const auto spawn=d.jenison_returns.front();const Vec3 origin{spawn.x+32,spawn.y-.2f,spawn.z+25};auto point=[&](float x,float z,float height=.05f){return Vec3{origin.x+x,origin.y+height,origin.z+z};};
 FirstBootCompanionBinding adam;adam.entity_id=new_uuid();adam.name="Adam's memory";adam.spawn=spawn;adam.spawn.x+=2;
 if(argc==3)adam.model=adopt_asset_pack(argv[2],output/"empty-packs");
 adam.routes.nodes={{"nook",adam.spawn},{"nook-turn",point(-33.5f,-25)},{"west",point(-37,-25)},{"west20",point(-37,-20)},{"west15",point(-37,-15)},{"west10",point(-37,-10)},{"fault",point(-37,-5.2f)},{"approach",point(-37,-1.5f)},{"junction",point(-37,1.9f)},{"main-front",point(-33,1.9f)},{"main-back",point(-33,6,.25f)},{"service-front",point(-41,1.9f)},{"service-back",point(-41,6,.25f)},{"hub",point(-37,8,.25f)},{"pencil-front",point(-37,10.7f,.25f)},{"pencil-back",point(-37,15,.25f)}};
 auto edge=[&](const char* from,const char* to,std::string gate=""){adam.routes.edges.push_back({from,to,std::move(gate),true});};edge("nook","nook-turn");edge("nook-turn","west");edge("west","west20");edge("west20","west15");edge("west15","west10");edge("west10","fault");edge("fault","approach");edge("approach","junction");edge("junction","main-front");edge("junction","service-front");edge("main-back","hub");edge("service-back","hub");edge("hub","pencil-front");
 for(const auto& r:d.initial_records)if(r.type_id=="firstboot.Door"){const auto role=std::get<std::string>(r.fields.at("role"));if(role=="main")edge("main-front","main-back",r.entity_id);else if(role=="service")edge("service-front","service-back",r.entity_id);else edge("pencil-front","pencil-back",r.entity_id);}
 d.companions.push_back(adam);FirstBootLightDefinition reserve;reserve.entity_id=new_uuid();reserve.name="Nook reserve fixture";reserve.position={spawn.x,spawn.y+3,spawn.z};reserve.color={1,.5f,.2f};reserve.intensity=3;reserve.radius=18;d.lights.push_back(reserve);
 const auto content=FirstBootContent::create(d);const auto bytes=first_boot_content_encode(content);std::ofstream f(output/"companion.aibd",std::ios::binary);f.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));f.close();if(!f.good())throw std::runtime_error("Cannot write companion fixture");
 fs::create_directories(output/"assets/packs");
 if(adam.model)stage_asset_packs(output/"empty-packs",std::span(&*adam.model,1),output/"assets/packs",true,AssetContentProfile::warm_beginning);
 ContentAuthoringHost authoring(content,"companion-native-proof","main");authoring.bind_asset_store(output/"assets/packs");
 if(authoring.save(output/"chapter.aiba").status!=ContentAuthoringStatus::saved)throw std::runtime_error("Cannot save native authoring fixture");
 std::ofstream metadata(output/".aibs-chapter-project.json");metadata<<"{\"version\":2,\"project\":\"companion-native-proof\",\"branch\":\"main\",\"asset_profile\":\"warm-beginning\"}\n";metadata.close();if(!metadata.good())throw std::runtime_error("Cannot write native project metadata");
 std::ofstream expected(output/"expected.json");expected<<"{\"world_id\":\""<<d.world_id<<"\",\"fingerprint\":\""<<content.fingerprint()<<"\",\"companion_id\":\""<<adam.entity_id<<"\",\"family_references_used\":false,\"model_reference\":";if(adam.model)expected<<"{\"asset_id\":\""<<adam.model->asset_id<<"\",\"asset_sha256\":\""<<adam.model->asset_sha256<<"\",\"pack_sha256\":\""<<adam.model->pack_sha256<<"\"}";else expected<<"null";expected<<"}\n";expected.close();if(!expected.good())throw std::runtime_error("Cannot write expected fixture identity");std::cout<<"Prepared private native companion fixture\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
