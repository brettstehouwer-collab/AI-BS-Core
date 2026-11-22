#include <aibs/content_lighting.hpp>
#include <aibs/engine.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>

using namespace aibs;
namespace fs=std::filesystem;
namespace {
void need(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void write(const fs::path& path,const std::vector<unsigned char>& bytes){std::ofstream f(path,std::ios::binary);f.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));f.close();need(f.good(),"Cannot write owned chapter lighting fixture");}
GameplayStoreRecovery state(const FirstBootContent& content){const auto b=first_boot_content_baseline(content);return {{"chapter-lighting-proof",content.definition().world_id,"main",new_uuid(),GameplayContext::temporary_play},b.revision,b.sequence,b.components};}
const ComponentRecord& fault(const FirstBootContentDefinition& d){for(const auto& r:d.initial_records)if(r.type_id=="firstboot.PowerFault")return r;throw std::runtime_error("Fixture requires actual chapter fault");}
float number(const ComponentRecord& r,const char* name){return static_cast<float>(std::get<double>(r.fields.at(name)));}
}
int wmain(int argc,wchar_t** argv){try{
 need(argc==2,"Usage: aibs_chapter_lighting_fixture NEW_OUTPUT_DIRECTORY");const auto output=fs::absolute(fs::path(argv[1])).lexically_normal();need(!fs::exists(output)&&fs::is_directory(output.parent_path()),"Fixture output must be a new child of an existing owned directory");fs::create_directory(output);
 CreatorSession source(first_boot_schema(),"chapter-lighting-proof","main");need(seed_first_boot(source).ok,"Cannot seed original test chapter");
 auto d=FirstBootContent::from_template(source).definition();d.format_version=3;d.asset_profile=AssetContentProfile::warm_beginning;d.exposure=1;
 const auto& f=fault(d);const auto spawn=d.jenison_returns.front();
 FirstBootLightDefinition reserve;reserve.entity_id=new_uuid();reserve.name="Warm reserve test point";reserve.position={spawn.x,spawn.y+3,spawn.z};reserve.color={1,.5f,.2f};reserve.intensity=3;reserve.radius=18;
 FirstBootLightDefinition restored;restored.entity_id=new_uuid();restored.name="Restored cool test point";restored.power=FirstBootLightPower::restored;restored.position={number(f,"x"),number(f,"y")+4,number(f,"z")};restored.color={.25f,.6f,1};restored.intensity=2;restored.radius=30;
 FirstBootLightDefinition directional=restored;directional.entity_id=new_uuid();directional.name="Restored directional test key";directional.kind=FirstBootLightKind::directional;directional.direction={.6f,-.8f,0};directional.color={.8f,.9f,1};directional.intensity=1;
 d.lights={reserve,restored,directional};const auto lit=FirstBootContent::create(d);auto control_definition=d;control_definition.lights.clear();const auto control=FirstBootContent::create(control_definition);
 const auto lit_state=state(lit),control_state=state(control);const auto lit_scene=first_boot_content_scene(lit_state,lit),control_scene=first_boot_content_scene(control_state,control);
 const auto a=mesh_from_snapshot(lit_scene),b=mesh_from_snapshot(control_scene);need(a.vertices.size()==b.vertices.size()&&a.landmarks==b.landmarks,"Control geometry collections differ");
 for(std::size_t i=0;i<a.vertices.size();++i){const auto& x=a.vertices[i];const auto& y=b.vertices[i];need(x.position==y.position&&x.normal==y.normal&&x.color==y.color&&x.emission==y.emission,"Light declarations changed the underlying scene geometry/materials");}
 const auto initial=first_boot_content_lighting(lit_state,lit);need(initial.enabled&&initial.points.size()==1&&!initial.directional,"Fixture must begin with actual reserve-only light");need(!first_boot_content_lighting(control_state,control).enabled,"Control must retain disabled legacy rendering");
 write(output/"withlights.aibd",first_boot_content_encode(lit));write(output/"withoutlights.aibd",first_boot_content_encode(control));fs::create_directory(output/"empty-packs");
 std::ofstream report(output/"expected.json");report<<"{\"schema_version\":1,\"world_id\":\""<<d.world_id<<"\",\"withlights_fingerprint\":\""<<lit.fingerprint()<<"\",\"withoutlights_fingerprint\":\""<<control.fingerprint()<<"\",\"geometry_identical\":true,\"vertices\":"<<a.vertices.size()<<",\"initial_points\":1,\"powered_points\":2,\"shadow_resolution\":1024,\"family_references_used\":false}\n";report.close();need(report.good(),"Cannot write expected chapter lighting data");
 std::cout<<"Prepared source-owned AIBD3 lighting/control fixtures with identical geometry\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
