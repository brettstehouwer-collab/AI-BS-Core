#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <winioctl.h>
#include <aibs/asset_scene.hpp>
#include <aibs/engine.hpp>
#include <aibs/physics.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>

using namespace aibs;
namespace {
unsigned checks = 0;
void require(bool ok, const char* why) {
 if (!ok) throw std::runtime_error(why);
 ++checks;
}
template<class F> void rejects(F&& function, const char* why, std::string_view message = {}) {
 bool rejected = false;
 try { function(); }
 catch (const std::exception& error) {
  rejected = message.empty() || std::string_view(error.what()).find(message) != std::string_view::npos;
 }
 require(rejected, why);
}
bool close(float a, float b) { return std::abs(a-b) < .00001f; }
bool equal_mesh(const SceneMesh& a, const SceneMesh& b) {
 if (a.landmarks != b.landmarks || a.vertices.size() != b.vertices.size()) return false;
 for (std::size_t i=0;i<a.vertices.size();++i) {
  const auto& x=a.vertices[i];const auto& y=b.vertices[i];
  if (x.position!=y.position || x.normal!=y.normal || x.color!=y.color || x.emission!=y.emission) return false;
 }
 return true;
}
void write(const std::filesystem::path& path, std::span<const std::byte> bytes) {
 std::ofstream stream(path,std::ios::binary|std::ios::trunc);
 stream.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
 if (!stream) throw std::runtime_error("Test fixture write failed");
}
void text(const std::filesystem::path& path, const std::string& value) {
 write(path,std::as_bytes(std::span(value.data(),value.size())));
}
std::vector<std::byte> read(const std::filesystem::path& path) {
 const auto size=std::filesystem::file_size(path);
 std::vector<std::byte> bytes(static_cast<std::size_t>(size));
 std::ifstream stream(path,std::ios::binary);
 stream.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
 if (!stream) throw std::runtime_error("Test fixture read failed");
 return bytes;
}
struct Directory {
 std::filesystem::path path=std::filesystem::temp_directory_path()/("aibs-asset-scene-"+new_uuid());
 Directory() { std::filesystem::create_directory(path); }
 ~Directory() { std::error_code ignored;std::filesystem::remove_all(path,ignored); }
};
MeshAsset triangle() {
 MeshAsset asset;
 asset.asset_id="11111111-1111-4111-8111-111111111111";
 asset.name="Self-authored part";
 const std::string source="self-authored asset scene triangle";
 asset.source_sha256=asset_sha256(std::as_bytes(std::span(source.data(),source.size())));
 const float normal=std::sqrt(.5f);
 asset.vertices={{{0,0,0},{normal,normal,0}},{{0,0,1},{normal,normal,0}},{{1,-1,0},{normal,normal,0}}};
 asset.indices={0,1,2};asset.triangle_materials={0};
 asset.materials={{"Copper",{.8f,.4f,.1f},.3f}};
 return asset;
}
std::string record(const MeshAsset& asset, const std::string& digest) {
 return asset.asset_id+" "+digest+" "+digest+".aibmesh\n";
}
std::string publish(const std::filesystem::path& root, const MeshAsset& asset) {
 const auto bytes=encode_mesh_asset(asset);const auto digest=asset_sha256(bytes);
 write(root/(digest+".aibmesh"),bytes);
 text(root/"catalog.aibcat","AIBCAT 1\n"+record(asset,digest));
 return digest;
}
std::vector<std::string> inventory(const std::filesystem::path& directory) {
 std::vector<std::string> paths;
 for (const auto& entry:std::filesystem::directory_iterator(directory)) paths.push_back(entry.path().filename().string());
 std::sort(paths.begin(),paths.end());return paths;
}
// Junctions exercise the same reparse attribute as symlinks without requiring
// Windows Developer Mode or the symbolic-link privilege on the test account.
void junction(const std::filesystem::path& link, const std::filesystem::path& target) {
 if (!CreateDirectoryW(link.c_str(),nullptr)) throw std::runtime_error("Test junction directory failed");
 const HANDLE handle=CreateFileW(link.c_str(),GENERIC_WRITE,0,nullptr,OPEN_EXISTING,
  FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_BACKUP_SEMANTICS,nullptr);
 if (handle==INVALID_HANDLE_VALUE) throw std::runtime_error("Test junction handle failed");
 struct Header { DWORD tag;WORD length,reserved,substitute_offset,substitute_length,print_offset,print_length; };
 const std::wstring substitute=L"\\??\\"+std::filesystem::absolute(target).native();
 const auto printable=std::filesystem::absolute(target).native();
 const auto substitute_bytes=substitute.size()*sizeof(wchar_t),print_bytes=printable.size()*sizeof(wchar_t);
 const std::size_t payload_bytes=substitute_bytes+print_bytes+2*sizeof(wchar_t);
 std::vector<std::byte> bytes(sizeof(Header)+payload_bytes);
 const Header header{IO_REPARSE_TAG_MOUNT_POINT,static_cast<WORD>(8+payload_bytes),0,0,
  static_cast<WORD>(substitute_bytes),static_cast<WORD>(substitute_bytes+sizeof(wchar_t)),static_cast<WORD>(print_bytes)};
 std::memcpy(bytes.data(),&header,sizeof(header));
 std::memcpy(bytes.data()+sizeof(Header),substitute.c_str(),substitute_bytes+sizeof(wchar_t));
 std::memcpy(bytes.data()+sizeof(Header)+substitute_bytes+sizeof(wchar_t),printable.c_str(),print_bytes+sizeof(wchar_t));
 DWORD returned=0;
 const auto ok=DeviceIoControl(handle,FSCTL_SET_REPARSE_POINT,bytes.data(),static_cast<DWORD>(bytes.size()),nullptr,0,&returned,nullptr);
 CloseHandle(handle);
 if (!ok) throw std::runtime_error("Test junction reparse setup failed");
}
void catalog_tests() {
 Directory directory;
 const auto root=directory.path/"package";std::filesystem::create_directory(root);
 auto asset=triangle();const auto digest=publish(root,asset);
 text(directory.path/"chapter.aiba","Retained authored chapter");
 text(directory.path/"player.sqlite","Retained player save");
 const auto document=read(directory.path/"chapter.aiba"),save=read(directory.path/"player.sqlite");
 const auto before=inventory(root);const auto catalog_bytes=read(root/"catalog.aibcat");
 AssetCatalog catalog(root);
 require(catalog.records().size()==1,"one exact catalog record");
 const auto& row=catalog.records().front();
 require(row.asset_id==asset.asset_id&&row.sha256==digest&&row.file==digest+".aibmesh","catalog record identity/hash/basename retained");
 require(inventory(root)==before&&read(root/"catalog.aibcat")==catalog_bytes,"catalog constructor never creates or modifies files");
 require(encode_mesh_asset(catalog.load(asset.asset_id))==encode_mesh_asset(asset),"standalone asset root resolves canonical cooked bytes");
 rejects([&]{(void)catalog.load(new_uuid());},"unknown asset never falls back to a source tree");
 require(read(directory.path/"chapter.aiba")==document&&read(directory.path/"player.sqlite")==save,"asset loading preserves authored documents and player saves");
 auto corrupt=read(root/(digest+".aibmesh"));corrupt[0]^=std::byte{1};write(root/(digest+".aibmesh"),corrupt);
 rejects([&]{(void)catalog.load(asset.asset_id);},"tampering is rejected before decoding","digest");
 const auto malformed_digest=asset_sha256(corrupt);
 write(root/(malformed_digest+".aibmesh"),corrupt);
 text(root/"catalog.aibcat","AIBCAT 1\n"+record(asset,malformed_digest));
 AssetCatalog malformed(root);
 rejects([&]{(void)malformed.load(asset.asset_id);},"matching outer SHA still requires valid cooked payload");
 publish(root,asset);
 text(root/"catalog.aibcat","AIBCAT 1\n"+new_uuid()+" "+digest+" "+digest+".aibmesh\n");
 AssetCatalog foreign(root);
 rejects([&]{(void)foreign.load(foreign.records().front().asset_id);},"decoded asset UUID must match catalog UUID");
 publish(root,asset);
 AssetCatalog absent(root);
 std::filesystem::remove(root/(digest+".aibmesh"));
 rejects([&]{(void)absent.load(asset.asset_id);},"missing cooked file never falls back");
 // An oversized placeholder is rejected before attempting an allocation/read.
 text(root/(digest+".aibmesh"),"x");
 std::filesystem::resize_file(root/(digest+".aibmesh"),mesh_asset_max_input_bytes+1);
 rejects([&]{(void)absent.load(asset.asset_id);},"catalog asset read enforces 32 MiB bound");
 std::filesystem::resize_file(root/(digest+".aibmesh"),0);
 rejects([&]{(void)absent.load(asset.asset_id);},"empty cooked file is rejected");
 std::filesystem::remove(root/(digest+".aibmesh"));
 std::filesystem::create_directory(root/(digest+".aibmesh"));
 rejects([&]{(void)absent.load(asset.asset_id);},"directory cannot masquerade as a cooked asset");
}
void catalog_validation_tests() {
 Directory directory;const auto root=directory.path/"package";std::filesystem::create_directory(root);
 const auto asset=triangle();const auto digest=asset_sha256(encode_mesh_asset(asset));
 const auto valid=record(asset,digest);
 std::string upper=digest;upper[0]='A';
 const std::vector<std::string> malformed={"","AIBCAT 2\n","AIBCAT 1\r\n","AIBCAT 1",
  "AIBCAT 1\n\n","AIBCAT 1\n# comment\n","AIBCAT 1\n"+valid+valid,
  "AIBCAT 1\n"+asset.asset_id+" "+digest+" ../"+digest+".aibmesh\n",
  "AIBCAT 1\n"+asset.asset_id+" "+digest+" nested/"+digest+".aibmesh\n",
  "AIBCAT 1\n"+asset.asset_id+" "+digest+" C:\\escape.aibmesh\n",
  "AIBCAT 1\n"+asset.asset_id+" "+digest+" "+digest+".aibmesh:stream\n",
  "AIBCAT 1\n"+asset.asset_id+" "+digest+" wrong.aibmesh\n",
  "AIBCAT 1\n"+asset.asset_id+" "+upper+" "+upper+".aibmesh\n",
  "AIBCAT 1\n"+asset.asset_id+" "+digest.substr(1)+" "+digest+".aibmesh\n",
  "AIBCAT 1\nnot-a-uuid "+digest+" "+digest+".aibmesh\n",
  "AIBCAT 1\n"+asset.asset_id+"  "+digest+" "+digest+".aibmesh\n",
  "AIBCAT 1\n"+asset.asset_id+"\t"+digest+" "+digest+".aibmesh\n",
  "AIBCAT 1\n"+asset.asset_id+" "+digest+" "+digest+".aibmesh extra\n",
  "AIBCAT 1\n"+valid.substr(0,valid.size()-1),
  "AIBCAT 1\n"+valid+new_uuid()+" "+digest+" "+digest+".aibmesh\n"};
 for(const auto& value:malformed){text(root/"catalog.aibcat",value);rejects([&]{AssetCatalog catalog(root);},"malformed/duplicate/traversal catalog rejected");}
 auto second=asset;second.name="Different bytes";const auto other=asset_sha256(encode_mesh_asset(second));
 text(root/"catalog.aibcat","AIBCAT 1\n"+valid+record(second,other));
 rejects([&]{AssetCatalog catalog(root);},"duplicate UUID with distinct digest rejected");
 text(root/"catalog.aibcat",std::string(1024u*1024u+1,'x'));
 rejects([&]{AssetCatalog catalog(root);},"catalog enforces 1 MiB read bound");
 std::string many="AIBCAT 1\n";
 for(unsigned i=0;i<1001;++i) {
  auto unique=asset;unique.asset_id=new_uuid();
  const std::string source=std::to_string(i);const auto hash=asset_sha256(std::as_bytes(std::span(source.data(),source.size())));
  many+=record(unique,hash);
 }
 text(root/"catalog.aibcat",many);
 rejects([&]{AssetCatalog catalog(root);},"catalog enforces 1000-record budget");
 text(root/"catalog.aibcat","AIBCAT 1\n");
 require(AssetCatalog(root).records().empty(),"versioned empty catalog is supported");
 std::filesystem::remove(root/"catalog.aibcat");
 rejects([&]{AssetCatalog catalog(root);},"missing catalog rejected without creating it");
 require(!std::filesystem::exists(root/"catalog.aibcat"),"missing catalog constructor remains read only");
 rejects([&]{AssetCatalog catalog(root/"missing");},"missing root rejected without creating it");
}
void reparse_tests() {
 Directory directory;const auto actual=directory.path/"actual";std::filesystem::create_directory(actual);
 const auto asset=triangle();publish(actual,asset);
 junction(directory.path/"redirect",actual);
 rejects([&]{AssetCatalog catalog(directory.path/"redirect");},"reparse package root rejected");
 const auto child=actual/"nested";std::filesystem::create_directory(child);publish(child,asset);
 rejects([&]{AssetCatalog catalog(directory.path/"redirect"/"nested");},"ancestor reparse component rejected before canonicalization");
 AssetCatalog catalog(actual);
 const auto moved=directory.path/"moved";std::filesystem::rename(actual,moved);junction(actual,moved);
 rejects([&]{(void)catalog.load(asset.asset_id);},"load rechecks root replaced by a junction after construction");
}
void composition_tests() {
 auto asset=triangle();SceneMesh output;
 const float q=std::sqrt(.5f);
 append_asset_mesh(output,asset,{5,7,11},{2,1,3},{0,0,q,q});
 require(output.vertices.size()==3&&output.landmarks==std::vector<std::string>{asset.name},"indexed triangle is flattened once with one landmark");
 require(output.vertices[0].position==Vec3{5,7,11}&&output.vertices[1].position==Vec3{5,7,14},"local vertices scale/rotate/translate into world coordinates");
 require(close(output.vertices[2].position.x,6)&&close(output.vertices[2].position.y,9)&&close(output.vertices[2].position.z,11),"rotation applies after nonuniform scale");
 const auto& normal=output.vertices[0].normal;
 require(close(normal.x,-2/std::sqrt(5.f))&&close(normal.y,1/std::sqrt(5.f))&&close(normal.z,0),"normals use inverse transpose scale then normalized quaternion rotation");
 require(output.vertices[0].color==asset.materials[0].base_color&&output.vertices[0].emission==asset.materials[0].emission,"triangle material becomes existing per-vertex color/emission");
 auto two=asset;two.indices={0,1,2,0,2,1};two.triangle_materials={0,1};two.materials.push_back({"Ceramic",{.1f,.2f,.3f},.8f});
 SceneMesh colored;append_asset_mesh(colored,two,{});
 require(colored.vertices.size()==6&&colored.vertices[3].color==two.materials[1].base_color&&colored.vertices[3].emission==.8f,"triangle material indices control each flattened triangle");
 const auto before=output;
 auto failed=[&](const MeshAsset& invalid,Vec3 center={},Vec3 scale={1,1,1},Quaternion rotation={}) {
  rejects([&]{append_asset_mesh(output,invalid,center,scale,rotation);},"invalid composition rejected");
  require(equal_mesh(output,before),"composition failure preserves all existing vertices and landmarks");
 };
 auto invalid=asset;invalid.indices[0]=999;failed(invalid);
 invalid=asset;invalid.triangle_materials[0]=1;failed(invalid);
 invalid=asset;invalid.materials[0].base_color.x=2;failed(invalid);
 invalid=asset;invalid.materials[0].emission=std::numeric_limits<float>::quiet_NaN();failed(invalid);
 invalid=asset;invalid.vertices[0].position.x=std::numeric_limits<float>::infinity();failed(invalid);
 invalid=asset;invalid.vertices[0].normal={};failed(invalid);
 invalid=asset;invalid.indices.pop_back();failed(invalid);
 failed(asset,{}, {0,1,1});failed(asset,{}, {-1,1,1});
 failed(asset,{}, {std::numeric_limits<float>::infinity(),1,1});
 failed(asset,{std::numeric_limits<float>::quiet_NaN(),0,0});
 failed(asset,{}, {1,1,1},{0,0,0,0});failed(asset,{}, {1,1,1},{0,0,0,2});
 failed(asset,{}, {1,1,1},{0,std::numeric_limits<float>::infinity(),0,1});
 const float huge=std::numeric_limits<float>::max();
 failed(asset,{huge,0,0},{huge,1,1});
 SceneMesh rounded;append_asset_mesh(rounded,asset,{}, {1,1,1},{0,0,0,1.00002f});
 require(rounded.vertices[2].position==asset.vertices[2].position,"small quaternion serialization error is normalized without scale");
 // The renderer's one-million-vertex limit is enforced before publication.
 SceneMesh bounded;bounded.vertices.assign(999996,output.vertices.front());
 append_asset_mesh(bounded,asset,{});
 require(bounded.vertices.size()==999999,"largest representable under-budget triangle count accepted");
 const auto count=bounded.vertices.size();const auto landmarks=bounded.landmarks;
 rejects([&]{append_asset_mesh(bounded,asset,{});},"combined renderer vertex budget rejected");
 require(bounded.vertices.size()==count&&bounded.landmarks==landmarks,"budget failure preserves previous composed scene");
}
void presentation_only_test() {
 SceneSnapshot scene{new_uuid(),7,{{new_uuid(),"Floor",{0,-1,0},{10,1,10},{.2f,.3f,.4f}},
  {new_uuid(),"Collider",{0,1,5},{1,1,1},{.3f,.2f,.1f}}}};
 const auto original=mesh_from_snapshot(scene);const auto picked=pick_scene(scene,{0,1,0},{0,0,1});
 GroundedCharacter character(scene,{0,.1f,0});
 const auto collision=character.camera_position({0,1,0},{0,1,10},.2f);
 auto render=original;append_asset_mesh(render,triangle(),{0,1,2});
 require(render.vertices.size()==original.vertices.size()+3,"visual detail exists only in render mesh");
 const auto after=pick_scene(scene,{0,1,0},{0,0,1});
 require(scene.revision==7&&scene.objects.size()==2&&equal_mesh(mesh_from_snapshot(scene),original),"visual append does not alter authoritative world geometry or revision");
 require(after&&picked&&after->persistent_id==picked->persistent_id&&after->distance==picked->distance,"existing object picking is unchanged");
 require(character.camera_position({0,1,0},{0,1,10},.2f)==collision,"real native collision remains unchanged by visual-only asset composition");
}
}
int main() {
 try {
  catalog_tests();catalog_validation_tests();reparse_tests();composition_tests();presentation_only_test();
  std::cout<<"PASS: "<<checks<<" cooked catalog, path/hash/reparse, atomic transform/material and collision checks\n";
  return 0;
 } catch(const std::exception& error) {std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}
}
