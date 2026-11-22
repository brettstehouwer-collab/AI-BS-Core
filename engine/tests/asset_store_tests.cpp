#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <winioctl.h>
#include <aibs/asset_store.hpp>
#include <aibs/engine.hpp>
#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string_view>

namespace {
namespace fs = std::filesystem;
using Bytes = std::vector<std::byte>;
unsigned checks = 0;
void check(bool condition, const char* message) {
 if (!condition) throw std::runtime_error(message);
 ++checks;
}
template<class F> void rejects(F&& action, const char* message) {
 bool rejected = false;
 try { action(); } catch (const std::exception&) { rejected = true; }
 check(rejected, message);
}
Bytes bytes(std::string_view value) {
 return {reinterpret_cast<const std::byte*>(value.data()), reinterpret_cast<const std::byte*>(value.data()+value.size())};
}
void write(const fs::path& path, const Bytes& data) {
 std::ofstream file(path, std::ios::binary | std::ios::trunc);
 file.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
 file.close();
 check(file.good(), "Owned test input write succeeded");
}
Bytes read(const fs::path& path) {
 Bytes data(static_cast<std::size_t>(fs::file_size(path)));
 std::ifstream file(path, std::ios::binary);
 file.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(data.size()));
 if (!file) throw std::runtime_error("Owned test input read failed");
 return data;
}
std::vector<std::string> inventory(const fs::path& directory) {
 std::vector<std::string> result;
 for (const auto& item : fs::directory_iterator(directory)) result.push_back(item.path().filename().string());
 std::sort(result.begin(), result.end()); return result;
}
struct Scratch {
 fs::path parent = fs::canonical(fs::temp_directory_path());
 fs::path path = parent / ("aibs-asset-store-" + aibs::new_uuid());
 Scratch() { fs::create_directory(path); }
 ~Scratch() {
  // This is one uniquely owned scratch subtree, checked before recursive cleanup.
  std::error_code ignored;
  if (path.parent_path() == parent && path.filename().string().starts_with("aibs-asset-store-"))
   fs::remove_all(fs::path(L"\\\\?\\"+path.native()), ignored);
 }
};
struct Pack {
 fs::path path;
 aibs::MeshAsset asset;
 std::string mesh_sha;
};
Pack pack(const fs::path& path, std::string license = "Self-authored synthetic asset; permission declared for this test.\n") {
 fs::create_directory(path);
 const std::vector<aibs::MeshMaterial> materials{{"copper", {.8f,.3f,.1f}, .1f}};
 auto asset = aibs::import_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl copper\nf 1 2 3\n", materials,
     "8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264", "Owned store triangle");
 const auto encoded = aibs::encode_mesh_asset(asset);
 const auto digest = aibs::asset_sha256(encoded);
 write(path/(digest+".aibmesh"), encoded);
 write(path/"catalog.aibcat", bytes("AIBCAT 1\n"+asset.asset_id+" "+digest+" "+digest+".aibmesh\n"));
 write(path/"LICENSE.txt", bytes(license));
 write(path/"provenance.json", bytes("{\"schema_version\":1,\"origin\":\"self-authored synthetic fixture\"}\n"));
 return {path, std::move(asset), digest};
}
std::string expected_pack_sha(const fs::path& directory) {
 std::string manifest = "AIBPACK 1\n";
 for (const auto& name : inventory(directory)) {
  const auto data = read(directory/name);
  manifest += name+" "+std::to_string(data.size())+" "+aibs::asset_sha256(data)+"\n";
 }
 return aibs::asset_sha256(bytes(manifest));
}
void junction(const fs::path& link, const fs::path& target) {
 if (!CreateDirectoryW(link.c_str(), nullptr)) throw std::runtime_error("Cannot create owned test junction");
 const auto handle = CreateFileW(link.c_str(), GENERIC_WRITE, 0, nullptr, OPEN_EXISTING,
     FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS, nullptr);
 if (handle == INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot open owned test junction");
 struct Header { DWORD tag; WORD length,reserved,substitute_offset,substitute_length,print_offset,print_length; };
 const std::wstring substitute = L"\\??\\"+fs::absolute(target).native(), printable=fs::absolute(target).native();
 const auto left=substitute.size()*sizeof(wchar_t),right=printable.size()*sizeof(wchar_t),payload=left+right+2*sizeof(wchar_t);
 Bytes data(sizeof(Header)+payload);
 const Header header{IO_REPARSE_TAG_MOUNT_POINT,static_cast<WORD>(8+payload),0,0,static_cast<WORD>(left),
     static_cast<WORD>(left+sizeof(wchar_t)),static_cast<WORD>(right)};
 std::memcpy(data.data(),&header,sizeof(header));
 std::memcpy(data.data()+sizeof(Header),substitute.c_str(),left+sizeof(wchar_t));
 std::memcpy(data.data()+sizeof(Header)+left+sizeof(wchar_t),printable.c_str(),right+sizeof(wchar_t));
 DWORD returned=0;const auto ok=DeviceIoControl(handle,FSCTL_SET_REPARSE_POINT,data.data(),static_cast<DWORD>(data.size()),nullptr,0,&returned,nullptr);
 CloseHandle(handle);
 if (!ok) throw std::runtime_error("Cannot initialize owned test junction");
}
void tests() {
 Scratch scratch;
 const auto source = pack(scratch.path/"source");
 const auto store = scratch.path/"store";fs::create_directory(store);
 const auto source_before=inventory(source.path);
 const auto document=scratch.path/"chapter.aiba",save=scratch.path/"world.sqlite";
 write(document,bytes("Retained authored document"));write(save,bytes("Retained gameplay data"));
 const auto ref = aibs::adopt_asset_pack(source.path,store);
 check(ref.asset_id==source.asset.asset_id&&ref.asset_sha256==source.mesh_sha,"Adoption pins asset UUID and cooked mesh digest");
 check(ref.pack_sha256==expected_pack_sha(source.path),"Pack digest covers canonical sorted manifest of all four files");
 check(inventory(store)==std::vector<std::string>{ref.pack_sha256},"Adoption publishes one immutable pack child");
 check(inventory(store/ref.pack_sha256)==source_before,"Stored pack contains exactly its four original files");
 for(const auto& name:source_before) check(read(source.path/name)==read(store/ref.pack_sha256/name),"Adoption copies exact original bytes");
 check(aibs::encode_mesh_asset(aibs::load_stored_asset(store,ref))==aibs::encode_mesh_asset(source.asset),"Stored load resolves native mesh without source fallback");
 std::size_t exact_pack_bytes=0;for(const auto& name:source_before)exact_pack_bytes+=static_cast<std::size_t>(fs::file_size(source.path/name));
 std::size_t verified_pack_bytes=0;
 check(aibs::load_stored_asset(store,ref,&verified_pack_bytes,exact_pack_bytes).asset_id==ref.asset_id&&verified_pack_bytes==exact_pack_bytes,
     "Verified load returns exact full mesh/catalog/license/provenance byte charge and permits exact budget");
 verified_pack_bytes=777;
 rejects([&]{(void)aibs::load_stored_asset(store,ref,&verified_pack_bytes,exact_pack_bytes-1);},"Verified load rejects one-byte-short aggregate read budget");
 check(verified_pack_bytes==777,"Rejected load does not publish an unverified byte charge");
 check(aibs::adopt_asset_pack(source.path,store)==ref&&inventory(store).size()==1,"Exact adoption retry reuses immutable existing pack");
 const auto old_license=read(store/ref.pack_sha256/"LICENSE.txt");
 write(store/ref.pack_sha256/"LICENSE.txt",bytes("Changed license declaration"));
 rejects([&]{(void)aibs::load_stored_asset(store,ref);},"License tampering invalidates stored pack identity");
 rejects([&]{(void)aibs::load_stored_asset(store,ref,&verified_pack_bytes);},"Charge-returning load also rejects altered license identity");
 check(verified_pack_bytes==777,"Digest failure does not publish a pack byte charge");
 rejects([&]{(void)aibs::adopt_asset_pack(source.path,store);},"Corrupt existing pack is never repaired or overwritten silently");
 write(store/ref.pack_sha256/"LICENSE.txt",old_license);
 const auto alternate=pack(scratch.path/"alternate","Different explicit rights declaration.\n");
 const auto ref2=aibs::adopt_asset_pack(alternate.path,store);
 check(ref2.asset_sha256==ref.asset_sha256&&ref2.pack_sha256!=ref.pack_sha256,"Different license bytes produce a different pack identity despite identical geometry");
 auto wrong=ref;wrong.asset_id=aibs::new_uuid();
 rejects([&]{(void)aibs::load_stored_asset(store,wrong);},"Foreign asset UUID rejects");
 wrong=ref;wrong.asset_sha256=std::string(64,'0');
 rejects([&]{(void)aibs::load_stored_asset(store,wrong);},"Foreign mesh digest rejects");
 wrong=ref;wrong.pack_sha256="../../escape";
 rejects([&]{aibs::validate_asset_pack_reference(wrong);},"Pack path traversal cannot enter a reference");
 wrong=ref;wrong.asset_sha256=std::string(64,'A');
 rejects([&]{aibs::validate_asset_pack_reference(wrong);},"Noncanonical uppercase SHA rejects");
 const auto extra=source.path/"unrelated.txt";write(extra,bytes("Do not import"));
 const auto inventory_before=inventory(store);
 rejects([&]{(void)aibs::adopt_asset_pack(source.path,store);},"Unexpected source pack file rejects");
 check(inventory(store)==inventory_before,"Rejected adoption preserves existing store");fs::remove(extra);
 const auto missing=source.path/"LICENSE.txt";const auto original=read(missing);fs::remove(missing);
 rejects([&]{(void)aibs::adopt_asset_pack(source.path,store);},"Missing source license rejects");write(missing,original);
 std::vector<aibs::AssetPackReference> repeated{ref,ref};
 const auto staged=scratch.path/"play-store";aibs::stage_asset_packs(store,repeated,staged);
 check(inventory(staged)==std::vector<std::string>{ref.pack_sha256},"Fresh snapshot stages deduplicated exact dependency closure");
 check(aibs::load_stored_asset(staged,ref).asset_id==ref.asset_id,"Fresh snapshot store loads after restart-style reopen");
 rejects([&]{aibs::stage_asset_packs(store,repeated,staged);},"Fresh staging never overwrites even matching destination");
 aibs::stage_asset_packs(store,std::vector<aibs::AssetPackReference>{ref2},staged,true);
 check(inventory(staged).size()==2&&aibs::load_stored_asset(staged,ref).asset_id==ref.asset_id,"Merge adds only new immutable dependencies and retains old snapshots");
 aibs::stage_asset_packs(store,std::vector<aibs::AssetPackReference>{ref2},staged,true);
 check(inventory(staged).size()==2,"Merge exact retry reuses existing pack");
 write(staged/ref.pack_sha256/"provenance.json",bytes("{\"changed\":true}"));
 rejects([&]{aibs::stage_asset_packs(store,std::vector<aibs::AssetPackReference>{ref2},staged,true);},"Merge rejects corruption in an existing private store");
 const auto failed=scratch.path/"failed-store";wrong=ref;wrong.pack_sha256=std::string(64,'0');
 const auto before_failed=inventory(scratch.path);
 rejects([&]{aibs::stage_asset_packs(store,std::vector<aibs::AssetPackReference>{ref,wrong},failed);},"Missing dependency rejects whole fresh closure");
 check(!fs::exists(failed)&&inventory(scratch.path)==before_failed,"Failed fresh stage leaves no final or orphan staging directory");
 repeated.assign(65,ref);
 rejects([&]{aibs::stage_asset_packs(store,repeated,failed);},"More than64 requested references reject");
 repeated.assign(64,ref);aibs::stage_asset_packs(store,repeated,failed);
 check(inventory(failed).size()==1,"64 repeated references remain one immutable pack");
 const auto long_parent=scratch.path/std::string(70,'d')/std::string(60,'e');fs::create_directories(long_parent);
 const auto long_store=long_parent/"packs";fs::create_directory(long_store);
 const auto long_ref=aibs::adopt_asset_pack(source.path,long_store);
 check((long_store/long_ref.pack_sha256/(long_ref.asset_sha256+".aibmesh")).native().size()>260,
     "Long path regression genuinely exceeds legacy MAX_PATH without shortening names");
 check(aibs::load_stored_asset(long_store,long_ref).asset_id==ref.asset_id,"Extended-path adoption/load preserves exact long-path asset identity");
 const auto long_private=long_parent/"private";aibs::stage_asset_packs(long_store,std::vector<aibs::AssetPackReference>{long_ref},long_private);
 check(aibs::load_stored_asset(long_private,long_ref).asset_id==ref.asset_id,"Fresh nested snapshot publication/reopen succeeds beyond260 characters");
 // Real valid payloads cross64MiB without inventing oversized header counts or
 // relying on decoder failure. Different licenses make17 distinct pack hashes.
 auto large=source.asset;
 large.vertices.resize(aibs::mesh_asset_max_vertices,large.vertices.front());
 large.indices.resize(aibs::mesh_asset_max_triangles*3);
 for(std::size_t index=0;index<large.indices.size();++index) large.indices[index]=static_cast<std::uint32_t>(index%3);
 large.triangle_materials.assign(aibs::mesh_asset_max_triangles,0);
 const auto large_bytes=aibs::encode_mesh_asset(large);
 const auto large_sha=aibs::asset_sha256(large_bytes);
 const auto budget_store=scratch.path/"budget-packs";fs::create_directory(budget_store);
 std::vector<aibs::AssetPackReference> budget_refs;std::size_t budget_total=0;
 for(unsigned index=0;index<17;++index) {
  const auto candidate=budget_store/("preparing-"+std::to_string(index));fs::create_directory(candidate);
  write(candidate/(large_sha+".aibmesh"),large_bytes);
  write(candidate/"catalog.aibcat",bytes("AIBCAT 1\n"+large.asset_id+" "+large_sha+" "+large_sha+".aibmesh\n"));
  write(candidate/"LICENSE.txt",bytes("Self-authored budget fixture license "+std::to_string(index)+"\n"));
  write(candidate/"provenance.json",bytes("{\"origin\":\"owned budget fixture\"}\n"));
  const auto pack_sha=expected_pack_sha(candidate);const auto destination=budget_store/pack_sha;
  check(candidate.parent_path()==budget_store&&destination.parent_path()==budget_store,"Budget fixture move stays within its owned source store");
  for(const auto& entry:fs::directory_iterator(candidate)) budget_total+=static_cast<std::size_t>(entry.file_size());
  fs::rename(candidate,destination);budget_refs.push_back({large.asset_id,large_sha,pack_sha});
 }
 check(budget_total>aibs::asset_store_maximum_staged_bytes&&budget_refs.size()<=aibs::asset_store_maximum_unique_packs,
     "Budget regression uses valid unique packs genuinely exceeding64MiB within32-pack count");
 const auto over_budget=scratch.path/"over-budget-private";const auto before_budget=inventory(scratch.path);
 rejects([&]{aibs::stage_asset_packs(budget_store,budget_refs,over_budget);},"Aggregate64MiB dependency read budget rejects before publication");
 check(!fs::exists(over_budget)&&inventory(scratch.path)==before_budget,"Over-budget closure leaves no partial destination or staging artifacts");
 const auto linked=scratch.path/"redirected";junction(linked,source.path);
 rejects([&]{(void)aibs::adopt_asset_pack(linked,store);},"Source junction rejects");
 check(RemoveDirectoryW(linked.c_str())!=0,"Remove owned junction itself without traversing its target");
 rejects([&]{(void)aibs::adopt_asset_pack(source.path,store/".."/"store");},"Store parent traversal rejects even when lexical normalization would return inside root");
 check(read(document)==bytes("Retained authored document")&&read(save)==bytes("Retained gameplay data"),"Asset store operations never mutate chapter documents or player data");
}
}
int main() {
 try { tests();std::cout<<"PASS: immutable asset store; checks="<<checks<<'\n';return 0; }
 catch(const std::exception& error) { std::cerr<<"FAIL: asset store: "<<error.what()<<'\n';return 1; }
}
