#include <aibs/character_import.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
using namespace aibs;
namespace {
std::size_t checks=0;using Bytes=std::vector<std::byte>;
void need(bool b,const std::string&m){++checks;if(!b)throw std::runtime_error(m);}
template<class F>void reject(F&&f,const std::string&m){bool rejected=false;try{f();}catch(const std::invalid_argument&){rejected=true;}need(rejected,m);need(character_import_live_parser_bytes()==0,"Parser allocations leaked after rejection: "+m);}
Bytes read(const std::filesystem::path&p){std::ifstream f(p,std::ios::binary|std::ios::ate);need(static_cast<bool>(f),"Missing fixture: "+p.string());const auto size=f.tellg();need(size>0&&size<=32*1024*1024,"Fixture size bound");Bytes b(static_cast<std::size_t>(size));f.seekg(0);f.read(reinterpret_cast<char*>(b.data()),size);need(f.good(),"Read fixture");return b;}
std::string text(const Bytes&b){return {reinterpret_cast<const char*>(b.data()),b.size()};}
std::span<const std::byte> bytes(const std::string&s){return {reinterpret_cast<const std::byte*>(s.data()),s.size()};}
CharacterImportOptions options(){return {"12345678-1234-4567-89ab-123456789abc","Synthetic character",{},30};}
void word(Bytes&b,std::size_t at,std::uint32_t n){for(unsigned i=0;i<4;++i)b[at+i]=static_cast<std::byte>((n>>(8*i))&255);}
void replace(std::string&s,const std::string&a,const std::string&b){const auto at=s.find(a);need(at!=s.npos,"Fixture replacement missing");s.replace(at,a.size(),b);}
void run(const std::filesystem::path&folder){
 auto source=read(folder/"basic.glb");const auto a=import_character_gltf(source,{},options());
 need(a.mesh.vertices.size()==4&&a.mesh.indices==std::vector<std::uint32_t>({0,2,1,0,3,2})&&a.mesh.joints.size()==1,"GLB indexed geometry/winding/joints");
 need(a.mesh.vertices[0].position==Vec3{.7f,-.7f,3}&&a.mesh.vertices[0].normal==Vec3{0,0,-1},"LH conversion");
 need(a.draws.size()==1&&a.draws[0].index_count==6&&a.materials[0].double_sided,"Draw/material ownership");need(a.source_sha256.size()==64&&a.name==options().name,"Owned source identity");
 auto document=read(folder/"external.gltf"),buffer=read(folder/"buffer.bin");const std::array<GltfInputResource,1> resources{{{"buffer.bin",buffer}}};const auto external=import_character_gltf(document,resources,options());
 for(const auto& sample:std::array<std::pair<const char*,float>,4>{{{"0.04",.04f},{"0.6",.6f},{"0.999",.999f},{"1",1.f}}}){
  auto surface=text(document);replace(surface,"\"roughnessFactor\":1",std::string("\"roughnessFactor\":")+sample.first);
  const auto imported=import_character_gltf(bytes(surface),resources,options());
  need(imported.materials[0].roughness==sample.second,"Source roughness factor not retained");
  need(imported.mesh==external.mesh&&imported.images==external.images&&imported.draws==external.draws,"Surface factor changed geometry/animation/images/draws");
  need(character_asset_payload_version(imported)==(sample.second==1?2u:3u),"Surface payload promotion differs from source roughness");
 }
 for(const char* bad_factor:{"0","0.039","1.01","1e400"}){
  auto surface=text(document);replace(surface,"\"roughnessFactor\":1",std::string("\"roughnessFactor\":")+bad_factor);
  reject([&]{(void)import_character_gltf(bytes(surface),resources,options());},"Invalid roughness accepted");
 }
need(external.mesh==a.mesh&&external.materials==a.materials&&external.source_sha256!=a.source_sha256,"Explicit external source closure");need(import_character_gltf(document,resources,options())==external,"Deterministic source digest and owned output");source.clear();buffer.clear();need(a.mesh.vertices[0].position.x==.7f&&external.mesh.vertices[0].position.x==.7f,"Output survives original storage destruction");
 need(!import_character_gltf(read(folder/"one-sided.glb"),{},options()).materials[0].double_sided,"Single-sided glTF material is retained");
 need(import_character_gltf(read(folder/"interleaved.glb"),{},options()).mesh==a.mesh,"Dense interleaved attributes preserve owned geometry");
 const auto reflected=import_character_gltf(read(folder/"reflected-bind-shape.glb"),{},options());need(reflected.mesh.indices==std::vector<std::uint32_t>({0,1,2,0,2,3})&&reflected.mesh.vertices[0].position.x==-.7f,"Winding derives from complete reflected bind basis");
 auto o=options();o.clips={{0,"motion",false}};const auto asym=import_character_gltf(read(folder/"asymmetric.glb"),{},o);
 need(asym.mesh.joints.size()==64&&asym.mesh.vertices[0].joints==std::array<std::uint16_t,4>{63,32,1,0},"Shuffled skin indices remapped through joint63");need(asym.mesh.clips.size()==1&&asym.mesh.clips[0].frame_count==31,"Uniform30Hz bake includes both endpoints");need(import_character_gltf(read(folder/"ignored-mesh-transform.glb"),{},o).mesh==asym.mesh,"Nonancestor mesh transform is ignored by skinning");
 auto world=character_identity_matrix;world[0]=1.2f;world[5]=.8f;world[10]=1.1f;world[12]=2;world[13]=.2f;world[14]=1;
 std::ifstream oracle(folder/"source-oracle.txt");unsigned frame=0,vertex=0;std::array<double,6> expected{};unsigned rows=0;
 while(oracle>>frame>>vertex>>expected[0]>>expected[1]>>expected[2]>>expected[3]>>expected[4]>>expected[5]){
  CharacterPose pose;pose.joint_count=64;for(unsigned j=0;j<64;++j)pose.local[j]=asym.mesh.clips[0].samples[frame*64+j];const auto actual=character_skin_vertex(asym.mesh.vertices[vertex],character_skin_palette(asym.mesh,pose),world);
  need(std::abs(actual.position.x-expected[0])<5e-4&&std::abs(actual.position.y-expected[1])<5e-4&&std::abs(actual.position.z-expected[2])<5e-4,"Independent source J(t)*IBM position oracle");
  need(std::abs(actual.normal.x-expected[3])<5e-4&&std::abs(actual.normal.y-expected[4])<5e-4&&std::abs(actual.normal.z-expected[5])<5e-4,"Independent source inverse-transpose normal oracle");++rows;
 }need(rows==16,"All independent source oracle samples evaluated");
 auto late_options=options();late_options.bake_rate=4;late_options.clips={{0,"late",false}};const auto late_source=read(folder/"late-key.glb");const auto late=import_character_gltf(late_source,{},late_options);const auto&clip=late.mesh.clips[0];need(clip.duration_seconds==2&&clip.frame_count==9,"Late first key does not shift timeline tozero");need(clip.samples[0]==clip.samples[4]&&clip.samples[8]!=clip.samples[4],"Before-first key clamps while endpoint changes");need(std::abs(clip.samples[8].rotation.z+std::sin(.25))<5e-5,"Exact final sample and handedness");late_options.clips[0].looping=true;reject([&]{import_character_gltf(late_source,{},late_options);},"Incompatible looping pose seam rejected");
 need(import_character_gltf(read(folder/"antipodal-loop.glb"),{},late_options).mesh.clips[0].looping,"Quaternion-sign-equivalent looping seam accepted");
 reject([&]{import_character_gltf(read(folder/"small-loop-seam.glb"),{},late_options);},"Visible small looping seam rejected");
 auto boundary_options=options();boundary_options.clips={{0,"boundary",true}};need(import_character_gltf(read(folder/"frame-boundary.glb"),{},boundary_options).mesh.clips[0].frame_count==4096,"Exact4096 uniform frame boundary");
 const auto textured=import_character_gltf(read(folder/"textured-seams.glb"),{},options());need(textured.mesh.vertices.size()==8&&textured.draws.size()==2&&textured.materials.size()==2,"Distinct primitive material ranges");need(textured.mesh.vertices[0].position==textured.mesh.vertices[4].position&&textured.mesh.vertices[0].u!=textured.mesh.vertices[4].u,"UV seam survives coincident positions");need(textured.images.size()==1&&textured.images[0].semantic==ImageSemantic::srgb_color&&textured.images[0].levels.size()==2,"Owned sRGB image and complete mip chain");const auto&mip=textured.images[0].levels[1];need(std::abs(static_cast<int>(mip.rgba[0])-188)<=1&&std::abs(static_cast<int>(mip.rgba[2])-188)<=1,"OPAQUE ignores source alpha before linear-light mip filtering");for(const auto&level:textured.images[0].levels)for(std::size_t p=3;p<level.rgba.size();p+=4)need(level.rgba[p]==255,"Opaque image canonical alpha");need(textured.mesh.vertices[0].color==Vec3{1,1,1}&&textured.materials[0].base_color==Vec3{.8f,.9f,1},"Vertex and material RGB retained, OPAQUE alpha ignored");
 const auto quantized=import_character_gltf(read(folder/"quantized-weights.glb"),{},options());need(quantized.mesh.vertices[0].weights==std::array<float,4>{.25f,.25f,.25f,.25f},"UNORM8 weights normalize only within quantization envelope");
 for(const auto&entry:std::filesystem::directory_iterator(folder))if(entry.path().filename().string().starts_with("bad-")&&entry.path().extension()==".glb"){
  auto selected=options();if(entry.path().filename().string().find("animation")!=std::string::npos||entry.path().filename().string().find("channel")!=std::string::npos||entry.path().filename().string().find("time")!=std::string::npos||entry.path().filename().string().find("duration")!=std::string::npos||entry.path().filename().string().find("root-motion")!=std::string::npos)selected.clips={{0,"bad",false}};
  const auto bad=read(entry.path());reject([&]{import_character_gltf(bad,{},selected);},"Malformed fixture accepted: "+entry.path().filename().string());
 }
 source=read(folder/"basic.glb");reject([&]{import_character_gltf({}, {}, options());},"Empty input rejected");for(std::size_t size:{1u,11u,19u})reject([&]{import_character_gltf(std::span(source).first(size),{},options());},"Truncated GLB rejected");auto bad=source;bad.push_back(std::byte{});reject([&]{import_character_gltf(bad,{},options());},"Trailing GLB rejected");bad=source;word(bad,4,1);reject([&]{import_character_gltf(bad,{},options());},"Old GLB rejected");bad=source;word(bad,16,0);reject([&]{import_character_gltf(bad,{},options());},"Unknown first chunk rejected");bad=source;word(bad,12,0xfffffffcu);reject([&]{import_character_gltf(bad,{},options());},"GLB chunk overflow rejected");
 document=read(folder/"external.gltf");buffer=read(folder/"buffer.bin");const std::array<GltfInputResource,1> current{{{"buffer.bin",buffer}}};reject([&]{import_character_gltf(document,{},options());},"No implicit filesystem fallback");for(const auto uri:{"../buffer.bin","C:/buffer.bin","https://example.invalid/x","buffer%2ebin","a\\\\buffer.bin","data:application/octet-stream;base64,AAAA","a//buffer.bin"}){auto s=text(document);replace(s,"buffer.bin",uri);reject([&]{import_character_gltf(bytes(s),current,options());},"Unsafe URI rejected");}const std::array<GltfInputResource,2> duplicate{{current[0],current[0]}};reject([&]{import_character_gltf(document,duplicate,options());},"Duplicate resource rejected");const std::array<GltfInputResource,2> extra{{current[0],{"unused.bin",buffer}}};reject([&]{import_character_gltf(document,extra,options());},"Undeclared resource rejected");reject([&]{import_character_gltf(source,current,options());},"GLB requires embedded resource closure");auto s=text(document);s+="{}";reject([&]{import_character_gltf(bytes(s),current,options());},"Trailing JSON rejected");s=text(document);replace(s,"\"2.0\"","NaN");reject([&]{import_character_gltf(bytes(s),current,options());},"Malformed JSON number rejected");
 auto invalid=options();invalid.asset_id="bad";reject([&]{import_character_gltf(source,{},invalid);},"UUID validation");invalid=options();invalid.bake_rate=61;reject([&]{import_character_gltf(source,{},invalid);},"Bake rate bound");invalid=options();invalid.clips={{999,"missing",false}};reject([&]{import_character_gltf(source,{},invalid);},"Selection index bound");
 CharacterImportDiagnostics diagnostics;diagnostics.parser_peak_bytes=123;diagnostics.engine_owned_live_upper_bound_bytes=456;diagnostics.source_skin_to_cooked={7};diagnostics.baked_intervals_seconds={3.14};const auto before=diagnostics;
 reject([&]{import_character_gltf({}, {}, options(),&diagnostics);},"Diagnostics rejection");need(diagnostics==before,"Failed import preserves caller diagnostics");
 (void)import_character_gltf(read(folder/"asymmetric.glb"),{},o,&diagnostics);need(diagnostics.parser_peak_bytes>0&&diagnostics.parser_peak_bytes<=64u*1024u*1024u&&diagnostics.engine_owned_live_upper_bound_bytes<=256u*1024u*1024u,"Tracked parser and engine-owned live accounting");need(diagnostics.source_skin_to_cooked.size()==64&&diagnostics.source_skin_to_cooked.front()==63&&diagnostics.source_skin_to_cooked.back()==0&&diagnostics.baked_intervals_seconds.size()==1&&std::abs(diagnostics.baked_intervals_seconds[0]-1./30)<1e-12,"Owned joint map and actual baked intervals");need(character_import_live_parser_bytes()==0,"Successful import releases private parser allocations");
 s=text(document);s.insert(s.size()-1,",\"asset\":{\"version\":\"2.0\"}");reject([&]{import_character_gltf(bytes(s),current,options());},"Duplicate JSON property rejected before parser allocation");
 s=text(document);replace(s,"buffer.bin","buffer.bin\\u0000evil");reject([&]{import_character_gltf(bytes(s),current,options());},"Escaped NUL URI alias rejected");
 std::string exhausted="{\"asset\":{\"version\":\"2.0\"},\"nodes\":[";for(unsigned n=0;n<400000;++n){if(n)exhausted+=',';exhausted+="{}";}exhausted+="]}";bool bounded=false;const auto diagnostic_before_failure=diagnostics;try{(void)import_character_gltf(bytes(exhausted),{},options(),&diagnostics);}catch(const std::invalid_argument&e){bounded=std::string(e.what()).find("allocator")!=std::string::npos;}need(bounded,"Actual tracked cgltf allocator exhaustion was diagnosed");need(character_import_live_parser_bytes()==0&&diagnostics==diagnostic_before_failure,"OOM frees actual parser allocations and preserves diagnostics");
 Bytes over(32u*1024u*1024u+1);reject([&]{import_character_gltf(over,{},options());},"Source byte budget before parsing");
}
}
int main(int argc,char**argv){try{const auto folder=argc>1?std::filesystem::path(argv[1]):std::filesystem::path(__FILE__).parent_path()/"fixtures/character_import";run(folder);std::cout<<"PASS "<<checks<<" character import checks\n";return 0;}catch(const std::exception&e){std::cerr<<"FAIL character import: "<<e.what()<<" after "<<checks<<" checks\n";return 1;}}
