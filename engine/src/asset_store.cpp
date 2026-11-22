#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/asset_store.hpp>
#include <aibs/surface_codec.hpp>
#include <aibs/character_codec.hpp>
#include <aibs/audio_codec.hpp>
#include <aibs/engine.hpp>
#include <algorithm>
#include <array>
#include <map>
#include <set>
#include <stdexcept>
#include <string_view>
#include <utility>

namespace aibs {
namespace {
namespace fs = std::filesystem;
using Bytes = std::vector<std::byte>;
constexpr std::size_t maximum_pack_bytes = 33u*1024u*1024u;
constexpr std::size_t maximum_existing_bytes = 128u*1024u*1024u;
constexpr std::size_t maximum_existing_packs = 256;
constexpr std::size_t maximum_catalog_bytes = 1024u*1024u;
constexpr std::size_t maximum_text_bytes = 64u*1024u;
void need(bool condition, const char* message) {
 if (!condition) throw std::invalid_argument(message);
}
std::string pack_file_sha256(std::span<const std::byte> body){
 need(body.size()<=asset_store_maximum_audio_pack_bytes,"Asset pack hash exceeds50MiB bound");
 struct Algorithm{BCRYPT_ALG_HANDLE value=nullptr;~Algorithm(){if(value)BCryptCloseAlgorithmProvider(value,0);}} algorithm;
 if(BCryptOpenAlgorithmProvider(&algorithm.value,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)throw std::runtime_error("Asset pack SHA256 provider unavailable");
 std::array<unsigned char,32> digest{};
 if(BCryptHash(algorithm.value,nullptr,0,const_cast<PUCHAR>(reinterpret_cast<const unsigned char*>(body.data())),static_cast<ULONG>(body.size()),digest.data(),static_cast<ULONG>(digest.size()))<0)throw std::runtime_error("Asset pack SHA256 computation failed");
 constexpr char hex[]="0123456789abcdef";std::string result;result.reserve(64);for(const auto value:digest){result.push_back(hex[value>>4]);result.push_back(hex[value&15]);}return result;
}
bool digest_text(std::string_view value) {
 return value.size()==64 && std::all_of(value.begin(),value.end(),[](char c) {
  return (c>='0'&&c<='9')||(c>='a'&&c<='f');
 });
}
fs::path native_path(const fs::path& absolute) {
 const auto& value=absolute.native();
 if(value.starts_with(L"\\\\?\\")) return absolute;
 if(value.starts_with(L"\\\\")) return fs::path(L"\\\\?\\UNC\\"+value.substr(2));
 return fs::path(L"\\\\?\\"+value);
}
fs::path absolute_path(const fs::path& input) {
 need(!input.empty(),"An explicit asset store/package path is required");
 auto spelling=input.native();
 if(spelling.starts_with(L"\\\\?\\UNC\\")) spelling=L"\\\\"+spelling.substr(8);
 else if(spelling.starts_with(L"\\\\?\\")) spelling=spelling.substr(4);
 for(const auto& part:fs::path(spelling).relative_path())
  need(part!=L"..","Asset store/package path traversal is not admitted");
 auto path=fs::absolute(fs::path(spelling));
 need(path.native().size()<=32760,"Asset store/package path exceeds Windows length bound");
 for (const auto& part:path.relative_path()) need(part!=L"..","Asset store/package path traversal is not admitted");
 return path.lexically_normal().make_preferred();
}
struct Handle {
 HANDLE value=INVALID_HANDLE_VALUE;
 explicit Handle(HANDLE input):value(input) {
  need(value!=INVALID_HANDLE_VALUE,"Asset store component is absent/inaccessible");
 }
 ~Handle() { if(value!=INVALID_HANDLE_VALUE) CloseHandle(value); }
 Handle(const Handle&)=delete;
 Handle& operator=(const Handle&)=delete;
 Handle(Handle&& other) noexcept:value(std::exchange(other.value,INVALID_HANDLE_VALUE)) {}
 void close() {
  const auto current=std::exchange(value,INVALID_HANDLE_VALUE);
  need(current!=INVALID_HANDLE_VALUE&&CloseHandle(current)!=0,"Could not close asset staging file");
 }
};
Handle open_component(const fs::path& path, bool directory) {
 const auto raw=CreateFileW(native_path(path).c_str(),directory?FILE_READ_ATTRIBUTES:GENERIC_READ,
     directory?(FILE_SHARE_READ|FILE_SHARE_WRITE):FILE_SHARE_READ,nullptr,OPEN_EXISTING,
     FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_BACKUP_SEMANTICS,nullptr);
 if(raw==INVALID_HANDLE_VALUE) {
  const auto code=GetLastError();const auto encoded=path.u8string();
  throw std::invalid_argument("Cannot open asset store component: "+
      std::string(reinterpret_cast<const char*>(encoded.data()),encoded.size())+" (Win32 "+std::to_string(code)+")");
 }
 Handle handle(raw);
 BY_HANDLE_FILE_INFORMATION info{};
 need(GetFileInformationByHandle(handle.value,&info)!=0,"Cannot inspect asset store component");
 need((info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)==0,"Asset store/package path redirects through a reparse point");
 need(((info.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)!=0)==directory,"Asset store/package component has wrong file/directory type");
 return handle;
}
struct Directory {
 fs::path path;
 std::vector<Handle> held;
 explicit Directory(const fs::path& input):path(absolute_path(input)) {
  auto current=path.root_path();const auto relative=path.relative_path();auto part=relative.begin();
  if(current.native().starts_with(L"\\\\")) {
   need(part!=relative.end(),"UNC asset root requires an explicit share");current/=*part;++part;
  }
  held.push_back(open_component(current,true));
  for(;part!=relative.end();++part) {current/=*part;held.push_back(open_component(current,true));}
 }
};
bool path_exists(const fs::path& path) {
 const auto attributes=GetFileAttributesW(native_path(path).c_str());
 if(attributes!=INVALID_FILE_ATTRIBUTES) return true;
 const auto error=GetLastError();
 need(error==ERROR_FILE_NOT_FOUND||error==ERROR_PATH_NOT_FOUND,"Could not inspect asset publication destination");
 return false;
}
std::size_t file_length(const Handle& handle, std::size_t maximum) {
 LARGE_INTEGER size{};
 need(GetFileSizeEx(handle.value,&size)!=0&&size.QuadPart>0&&
     static_cast<unsigned long long>(size.QuadPart)<=maximum,"Asset pack file is empty or exceeds its byte bound");
 return static_cast<std::size_t>(size.QuadPart);
}
Bytes read_handle(const Handle& handle, std::size_t count) {
 Bytes result(count);std::size_t offset=0;
 while(offset<result.size()) {
  const auto chunk=static_cast<DWORD>(std::min<std::size_t>(result.size()-offset,1024u*1024u));
  DWORD copied=0;
  need(ReadFile(handle.value,result.data()+offset,chunk,&copied,nullptr)!=0&&copied==chunk,"Cannot read complete immutable pack file");
  offset+=copied;
 }
 need(file_length(handle,count)==count,"Asset pack file length changed while reading");
 return result;
}
Bytes read_file(const fs::path& path, std::size_t maximum) {
 const auto absolute=absolute_path(path);Directory parent(absolute.parent_path());
 auto file=open_component(absolute,false);return read_handle(file,file_length(file,maximum));
}
std::string_view text(const Bytes& value) {
 return {reinterpret_cast<const char*>(value.data()),value.size()};
}
Bytes bytes(std::string_view value) {
 return {reinterpret_cast<const std::byte*>(value.data()),reinterpret_cast<const std::byte*>(value.data()+value.size())};
}
void bounded_text(const Bytes& value) {
 need(!value.empty()&&value.size()<=maximum_text_bytes,"Asset license/provenance text size is invalid");
 const auto raw=text(value);
 need(std::none_of(raw.begin(),raw.end(),[](char c){return c=='\0';})&&
     std::any_of(raw.begin(),raw.end(),[](unsigned char c){return c>32;}),"Asset license/provenance text is empty or contains NUL");
 need(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,raw.data(),static_cast<int>(raw.size()),nullptr,0)>0,
     "Asset license/provenance text must be UTF-8");
}
struct Pack {
 AssetPackReference reference;
 std::map<std::string,Bytes> files;
 std::size_t total=0;
 StoredAssetKind kind=StoredAssetKind::mesh_v1;
 std::size_t decoded_bytes=0;
};
std::size_t mesh_decoded_bytes(const MeshAsset& a) {
 std::size_t n=sizeof(MeshAsset)+a.vertices.size()*sizeof(AssetVertex)+a.indices.size()*4+a.triangle_materials.size()*4+a.materials.size()*sizeof(MeshMaterial)+a.asset_id.size()+a.name.size()+a.source_sha256.size();
 for(const auto& m:a.materials)n+=m.name.size();
 return n;
}
std::size_t surface_decoded_bytes(const SurfaceMeshAsset& a) {
 auto n=mesh_decoded_bytes(a.geometry)+sizeof(SurfaceMeshAsset)+a.corners.size()*sizeof(SurfaceCorner)+a.albedo_images.size()*4+a.images.size()*sizeof(ImageAsset);
 for(const auto& i:a.images)n+=image_resident_bytes(i)+i.levels.size()*sizeof(ImageMip);
 return n;
}
Pack read_pack(const fs::path& input, std::size_t remaining=asset_store_maximum_audio_pack_bytes) {
 Directory directory(input);
 struct Input { std::string name;Handle handle;std::size_t length; };
 std::vector<Input> inputs;inputs.reserve(4);
 std::set<std::string> names;
 std::string mesh_name;
 Pack result;
 for(const auto& entry:fs::directory_iterator(native_path(directory.path))) {
  need(inputs.size()<4,"Asset pack must contain exactly four native cooker files");
  const auto name=entry.path().filename().string();
  std::size_t maximum=0;
  if(name=="catalog.aibcat") maximum=maximum_catalog_bytes;
  else if(name=="LICENSE.txt"||name=="provenance.json") maximum=maximum_text_bytes;
  else if(name.size()>=64&&digest_text(std::string_view(name).substr(0,64))&&
      (name.substr(64)==".aibmesh"||name.substr(64)==".aibsurf"||name.substr(64)==".aibchar"||name.substr(64)==".aibaud")) {
   need(mesh_name.empty(),"Asset pack must contain exactly one cooked payload");mesh_name=name;
   maximum=name.substr(64)==".aibaud"?audio_asset_maximum_payload_bytes:mesh_asset_max_input_bytes;
  } else throw std::invalid_argument("Unexpected asset pack file or directory");
  need(names.insert(name).second,"Duplicate asset pack filename");
  auto handle=open_component(entry.path(),false);const auto length=file_length(handle,maximum);
  need(length<=asset_store_maximum_audio_pack_bytes-result.total&&length<=remaining-result.total,"Asset dependency pack/request exceeds its byte budget");
  result.total+=length;inputs.push_back({name,std::move(handle),length});
 }
 need(inputs.size()==4&&!mesh_name.empty()&&names.contains("catalog.aibcat")&&
     names.contains("LICENSE.txt")&&names.contains("provenance.json"),"Asset pack requires exactly payload/catalog/license/provenance");
 // Directory enumeration order must not decide the content-specific limit.
 // All lengths are checked before any content read; legacy payloads retain the
 // exact33MiB complete-pack cap even when the caller permits large audio.
 need(result.total<=(mesh_name.ends_with(".aibaud")?asset_store_maximum_audio_pack_bytes:maximum_pack_bytes),
      "Asset pack exceeds its content-specific complete byte bound");
 for(auto& input_file:inputs) result.files.emplace(input_file.name,read_handle(input_file.handle,input_file.length));
 const auto catalog=text(result.files.at("catalog.aibcat"));
 constexpr std::string_view legacy="AIBCAT 1\n",surface="AIBCAT 2\nsurface ",character="AIBCAT 2\ncharacter ",audio="AIBCAT 2\naudio ";
 result.kind=catalog.starts_with(surface)?StoredAssetKind::surface_v2:catalog.starts_with(character)?StoredAssetKind::character_v2:catalog.starts_with(audio)?StoredAssetKind::audio_v2:StoredAssetKind::mesh_v1;
 const auto header=result.kind==StoredAssetKind::surface_v2?surface:result.kind==StoredAssetKind::character_v2?character:result.kind==StoredAssetKind::audio_v2?audio:legacy;
 const std::string_view suffix=result.kind==StoredAssetKind::surface_v2?".aibsurf":result.kind==StoredAssetKind::character_v2?".aibchar":result.kind==StoredAssetKind::audio_v2?".aibaud":".aibmesh";
 const auto row_length=102u+64u+suffix.size();
 need(catalog.starts_with(header)&&catalog.size()==header.size()+row_length+1&&catalog.back()=='\n',"Asset store requires one canonical typed catalog record");
 const auto row=catalog.substr(header.size(),row_length);
 need(row[36]==' '&&row[101]==' ',"Malformed single-asset catalog row");
 result.reference.asset_id=std::string(row.substr(0,36));
 result.reference.asset_sha256=std::string(row.substr(37,64));
 need(is_uuid(result.reference.asset_id)&&digest_text(result.reference.asset_sha256)&&
     row.substr(102)==result.reference.asset_sha256+std::string(suffix)&&row.substr(102)==mesh_name,"Catalog asset UUID/digest/basename mismatch");
 const auto& mesh_bytes=result.files.at(mesh_name);
 need(pack_file_sha256(mesh_bytes)==result.reference.asset_sha256,"Cooked payload differs from catalog digest");
 std::string identity;
 if(result.kind==StoredAssetKind::surface_v2){const auto a=decode_surface_asset(mesh_bytes);identity=a.geometry.asset_id;result.decoded_bytes=surface_decoded_bytes(a);}
 else if(result.kind==StoredAssetKind::character_v2){const auto a=decode_character_asset(mesh_bytes);identity=a.asset_id;result.decoded_bytes=character_asset_cost(a).decoded_bytes;}
 else if(result.kind==StoredAssetKind::audio_v2){const auto a=decode_audio_asset(mesh_bytes);identity=a.asset_id;result.decoded_bytes=audio_asset_cost(a).decoded_bytes;}
 else{const auto a=decode_mesh_asset(mesh_bytes);identity=a.asset_id;result.decoded_bytes=mesh_decoded_bytes(a);}
 need(identity==result.reference.asset_id,"Decoded mesh UUID differs from catalog");
 bounded_text(result.files.at("LICENSE.txt"));bounded_text(result.files.at("provenance.json"));
 std::string manifest=result.kind==StoredAssetKind::mesh_v1?"AIBPACK 1\n":"AIBPACK 2\n";
 for(const auto& [name,value]:result.files) manifest+=name+" "+std::to_string(value.size())+" "+pack_file_sha256(value)+"\n";
 result.reference.pack_sha256=pack_file_sha256(bytes(manifest));
 return result;
}
void require_reference(const Pack& pack, const AssetPackReference& reference) {
 need(pack.reference==reference,"Immutable asset pack/reference digest or UUID mismatch");
}
struct Stage {
 fs::path path;
 std::vector<fs::path> files,children;
 bool published=false;
 unsigned publish_attempts=0;
 explicit Stage(const fs::path& parent) {
  files.reserve(asset_store_maximum_unique_packs*4);children.reserve(asset_store_maximum_unique_packs);
  for(unsigned attempt=0;attempt<16;++attempt) {
   auto candidate=parent/(".aibs-asset-stage-"+new_uuid());
   if(CreateDirectoryW(native_path(candidate).c_str(),nullptr)!=0) {path=std::move(candidate);return;}
   need(GetLastError()==ERROR_ALREADY_EXISTS,"Cannot create owned asset staging directory");
  }
  throw std::runtime_error("No fresh asset staging directory available");
 }
 ~Stage() {
  if(published) return;
  // Exact created files/empty directories only; never recursive deletion.
  try {
   for(auto it=files.rbegin();it!=files.rend();++it) DeleteFileW(native_path(*it).c_str());
   for(auto it=children.rbegin();it!=children.rend();++it) RemoveDirectoryW(native_path(*it).c_str());
   if(!path.empty()) RemoveDirectoryW(native_path(path).c_str());
  } catch(...) { /* Cleanup cannot throw; only this owner's exact paths are candidates. */ }
 }
 void child(const std::string& name) {
  auto destination=path/name;
  need(CreateDirectoryW(native_path(destination).c_str(),nullptr)!=0,"Cannot create owned staged pack child");
  children.push_back(std::move(destination));
 }
 void write(const fs::path& relative, const Bytes& data) {
  auto destination=path/relative;
  const auto raw=CreateFileW(native_path(destination).c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,
      FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_WRITE_THROUGH,nullptr);
  if(raw==INVALID_HANDLE_VALUE) {
   const auto code=GetLastError();const auto encoded=destination.u8string();
   throw std::invalid_argument("Cannot create staged asset file: "+
       std::string(reinterpret_cast<const char*>(encoded.data()),encoded.size())+" (Win32 "+std::to_string(code)+")");
  }
  Handle file(raw);
  files.push_back(std::move(destination));
  std::size_t offset=0;
  while(offset<data.size()) {
   const auto chunk=static_cast<DWORD>(std::min<std::size_t>(data.size()-offset,1024u*1024u));DWORD written=0;
   need(WriteFile(file.value,data.data()+offset,chunk,&written,nullptr)!=0&&written==chunk,"Cannot write complete staged asset file");offset+=written;
  }
  need(FlushFileBuffers(file.value)!=0,"Cannot flush staged asset file");file.close();
  need(read_file(files.back(),data.size())==data,"Staged asset file readback differs");
 }
 DWORD publish(const fs::path& destination) {
  const auto from=native_path(path),to=native_path(destination);
  ++publish_attempts;
  if(!MoveFileExW(from.c_str(),to.c_str(),MOVEFILE_WRITE_THROUGH)) return GetLastError();
  published=true;return ERROR_SUCCESS;
 }
 [[noreturn]] void publication_failed(const char* context,const fs::path& destination,DWORD error) const {
  const auto from=path.u8string(),to=destination.u8string();
  throw std::invalid_argument(std::string(context)+": MoveFileExW (Win32 "+std::to_string(error)+") after "+
      std::to_string(publish_attempts)+(publish_attempts==1?" attempt":" attempts")+" from '"+
      reinterpret_cast<const char*>(from.c_str())+"' to '"+reinterpret_cast<const char*>(to.c_str())+"'");
 }
};
void publish_pack(const Pack& pack, const Directory& store) {
 const auto destination=store.path/pack.reference.pack_sha256;
 if(path_exists(destination)) {
  const auto existing=read_pack(destination);require_reference(existing,pack.reference);
  need(existing.files==pack.files,"Existing immutable asset pack bytes differ");return;
 }
 Stage stage(store.path);
 for(const auto& [name,data]:pack.files) stage.write(name,data);
 auto error=stage.publish(destination);
 if(error==ERROR_SHARING_VIOLATION && !path_exists(destination)) {
  // A short-lived handle can deny the rename after every staged file was flushed.
  // Retry only this move, with the same verified pack and no replacement flag.
  Sleep(150);
  const auto staged=read_pack(stage.path);
  require_reference(staged,pack.reference);
  need(staged.files==pack.files,"Staged asset pack changed before publication retry");
  error=stage.publish(destination);
 }
 if(error!=ERROR_SUCCESS) {
  // A competing publisher may have won. Reuse only its exact verified bytes.
  if(GetFileAttributesW(native_path(destination).c_str())==INVALID_FILE_ATTRIBUTES)
   stage.publication_failed("Cannot publish fresh immutable asset pack",destination,error);
  const auto existing=read_pack(destination);require_reference(existing,pack.reference);
  need(existing.files==pack.files,"Competing asset publication differs from immutable pack");
 }
}
std::map<std::string,AssetPackReference> references(std::span<const AssetPackReference> input) {
 need(input.size()<=asset_store_maximum_references,"Asset store request exceeds64 references");
 std::map<std::string,AssetPackReference> unique;
 for(const auto& reference:input) {
  validate_asset_pack_reference(reference);
  const auto [found,inserted]=unique.emplace(reference.pack_sha256,reference);
  need(inserted||found->second==reference,"One pack digest has conflicting asset references");
  need(unique.size()<=asset_store_maximum_unique_packs,"Asset store request exceeds32 unique packs");
 }
 return unique;
}
std::map<std::string,std::size_t> existing_store(const Directory& store) {
 std::map<std::string,std::size_t> result;std::size_t total=0;
 for(const auto& entry:fs::directory_iterator(native_path(store.path))) {
  const auto name=entry.path().filename().string();
  need(digest_text(name)&&result.size()<maximum_existing_packs,"Private asset store contains unexpected entries or exceeds256 packs");
  const auto pack=read_pack(entry.path(),maximum_existing_bytes-total);
  need(pack.reference.pack_sha256==name,"Existing private store pack has corrupt manifest identity");
  total+=pack.total;result.emplace(name,pack.total);
 }
 return result;
}
}

void validate_asset_pack_reference(const AssetPackReference& reference) {
 need(is_uuid(reference.asset_id)&&digest_text(reference.asset_sha256)&&digest_text(reference.pack_sha256),
     "Asset reference requires a canonical UUID and lowercase SHA-256 digests");
}
AssetPackReference adopt_asset_pack(const fs::path& source_pack,const fs::path& store) {
 const auto pack=read_pack(source_pack);Directory destination(store);
 need(!fs::equivalent(native_path(absolute_path(source_pack)),native_path(destination.path)),"Source pack cannot also be its adoption store");
 publish_pack(pack,destination);return pack.reference;
}
MeshAsset load_stored_asset(const fs::path& store,const AssetPackReference& reference) {
 return load_stored_asset(store,reference,nullptr);
}
MeshAsset load_stored_asset(const fs::path& store,const AssetPackReference& reference,
                           std::size_t* verified_pack_bytes,std::size_t maximum_read_bytes) {
 validate_asset_pack_reference(reference);Directory root(store);
 const auto pack=read_pack(root.path/reference.pack_sha256,maximum_read_bytes);require_reference(pack,reference);
 need(pack.kind==StoredAssetKind::mesh_v1,"Typed pack requires its matching typed asset loader");
 auto mesh=decode_mesh_asset(pack.files.at(reference.asset_sha256+".aibmesh"));
 if(verified_pack_bytes)*verified_pack_bytes=pack.total;
 return mesh;
}
namespace {
StoredVisualAsset unpack_visual(const Pack& pack) {
 need(pack.kind==StoredAssetKind::mesh_v1||pack.kind==StoredAssetKind::surface_v2,"Character/audio pack is not static visual scenery");
 const auto& reference=pack.reference;
 StoredVisualAsset result;result.encoded_bytes=pack.total;result.decoded_bytes=pack.decoded_bytes;
 if(pack.kind==StoredAssetKind::surface_v2){
  auto a=decode_surface_asset(pack.files.at(reference.asset_sha256+".aibsurf"));
  result.payload=std::move(a);
 }else{result.payload=decode_mesh_asset(pack.files.at(reference.asset_sha256+".aibmesh"));}
 return result;
}
}
AssetPackInspection inspect_visual_asset_pack(const fs::path& source_pack,std::size_t maximum_read_bytes) {
 const auto pack=read_pack(source_pack,maximum_read_bytes);
 return {pack.reference,unpack_visual(pack)};
}
TypedAssetPackInspection inspect_asset_pack(const fs::path& source_pack,std::size_t maximum_read_bytes){
 const auto pack=read_pack(source_pack,maximum_read_bytes);StoredTypedAsset asset;
 asset.encoded_bytes=pack.total;asset.decoded_bytes=pack.decoded_bytes;
 if(pack.kind==StoredAssetKind::character_v2)asset.payload=decode_character_asset(pack.files.at(pack.reference.asset_sha256+".aibchar"));
 else if(pack.kind==StoredAssetKind::audio_v2)asset.payload=decode_audio_asset(pack.files.at(pack.reference.asset_sha256+".aibaud"));
 else if(pack.kind==StoredAssetKind::surface_v2)asset.payload=decode_surface_asset(pack.files.at(pack.reference.asset_sha256+".aibsurf"));
 else asset.payload=decode_mesh_asset(pack.files.at(pack.reference.asset_sha256+".aibmesh"));
 return {pack.reference,pack.kind,std::move(asset)};
}
StoredCharacterAsset load_stored_character_asset(const fs::path& store,const AssetPackReference& reference,
 std::size_t* verified_pack_bytes,std::size_t maximum_read_bytes){
 validate_asset_pack_reference(reference);Directory root(store);
 const auto pack=read_pack(root.path/reference.pack_sha256,maximum_read_bytes);require_reference(pack,reference);
 need(pack.kind==StoredAssetKind::character_v2,"Companion model requires a typed character pack");
 StoredCharacterAsset result{decode_character_asset(pack.files.at(reference.asset_sha256+".aibchar")),pack.total,pack.decoded_bytes};
 if(verified_pack_bytes)*verified_pack_bytes=pack.total;
 return result;
}
StoredAudioAsset load_stored_audio_asset(const fs::path& store,const AssetPackReference& reference,
 std::size_t* verified_pack_bytes,std::size_t maximum_read_bytes){
 validate_asset_pack_reference(reference);Directory root(store);
 const auto pack=read_pack(root.path/reference.pack_sha256,maximum_read_bytes);require_reference(pack,reference);
 need(pack.kind==StoredAssetKind::audio_v2,"Memory recording requires a typed audio pack");
 StoredAudioAsset result{decode_audio_asset(pack.files.at(reference.asset_sha256+".aibaud")),pack.total,pack.decoded_bytes};
 if(verified_pack_bytes)*verified_pack_bytes=pack.total;
 return result;
}
StoredVisualAsset load_stored_visual_asset(const fs::path& store,const AssetPackReference& reference,
 std::size_t* verified_pack_bytes,std::size_t maximum_read_bytes) {
 validate_asset_pack_reference(reference);Directory root(store);
 const auto pack=read_pack(root.path/reference.pack_sha256,maximum_read_bytes);require_reference(pack,reference);
 auto result=unpack_visual(pack);
 if(verified_pack_bytes)*verified_pack_bytes=result.encoded_bytes;
 return result;
}
void stage_asset_packs(const fs::path& source_store,std::span<const AssetPackReference> requested,
                      const fs::path& destination_store,bool merge_existing,AssetContentProfile profile) {
 need(profile==AssetContentProfile::legacy_v1||profile==AssetContentProfile::warm_beginning,"Unknown asset content profile");
 const auto limit=profile==AssetContentProfile::legacy_v1?asset_store_maximum_staged_bytes:asset_store_modern_staged_bytes;
 const auto unique=references(requested);Directory source(source_store);
 const auto destination=absolute_path(destination_store);Directory parent(destination.parent_path());
 need(merge_existing||!path_exists(destination),"Fresh asset snapshot store already exists");
 std::vector<Pack> packs;packs.reserve(unique.size());std::size_t total=0,decoded=0;
 for(const auto& [digest,reference]:unique) {
  auto pack=read_pack(source.path/digest,limit-total);require_reference(pack,reference);
  need(pack.kind==StoredAssetKind::mesh_v1||profile==AssetContentProfile::warm_beginning,"Typed dependency needs warm-beginning content profile");
  if(profile==AssetContentProfile::warm_beginning){need(pack.decoded_bytes<=asset_store_modern_staged_bytes-decoded,"Decoded dependency residency exceeds128MiB");decoded+=pack.decoded_bytes;}
  total+=pack.total;packs.push_back(std::move(pack));
 }
 if(merge_existing) {
  Directory target(destination);const auto present=existing_store(target);std::size_t merged=0;
  for(const auto& [digest,size]:present) {(void)digest;merged+=size;}
  std::size_t added=0;
  for(const auto& pack:packs) if(!present.contains(pack.reference.pack_sha256)) {
   need(pack.total<=maximum_existing_bytes-merged,"Private asset snapshot store exceeds128 MiB; close/reopen its owner");
   merged+=pack.total;++added;
  }
  need(added<=maximum_existing_packs-present.size(),"Private asset snapshot store exceeds256 packs; close/reopen its owner");
  for(const auto& pack:packs) publish_pack(pack,target);
 } else {
  Stage stage(parent.path);
  for(const auto& pack:packs) {
   stage.child(pack.reference.pack_sha256);
   for(const auto& [name,data]:pack.files) stage.write(fs::path(pack.reference.pack_sha256)/name,data);
  }
  const auto error=stage.publish(destination);
  if(error!=ERROR_SUCCESS)
   stage.publication_failed("Cannot publish fresh complete asset snapshot store",destination,error);
 }
}
}
