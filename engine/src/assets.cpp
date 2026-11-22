#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/assets.hpp>
#include <aibs/engine.hpp>
#include <algorithm>
#include <array>
#include <bit>
#include <charconv>
#include <cmath>
#include <limits>
#include <map>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace aibs {
namespace {
constexpr std::array<std::byte,8> magic{std::byte{65},std::byte{73},std::byte{66},std::byte{77},std::byte{101},std::byte{115},std::byte{104},std::byte{49}};
constexpr std::size_t header_bytes = 48;
constexpr std::size_t maximum_name = 4096, maximum_material_name = 256;
[[noreturn]] void invalid(const char* message) { throw std::invalid_argument(message); }
bool finite(Vec3 value) { return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z); }
bool unit(float value) { return std::isfinite(value) && value >= 0 && value <= 1; }
bool text(std::string_view value, std::size_t maximum) {
 return !value.empty() && value.size() <= maximum && std::none_of(value.begin(),value.end(),[](unsigned char c) { return c < 32 || c == 127; });
}
bool sha_text(std::string_view value) {
 return value.size() == 64 && std::all_of(value.begin(),value.end(),[](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); });
}
void validate_materials(std::span<const MeshMaterial> materials) {
 if (materials.empty() || materials.size() > mesh_asset_max_materials) invalid("Mesh requires 1..64 explicit materials");
 for (std::size_t i=0;i<materials.size();++i) {
  const auto& material=materials[i];
  if (!text(material.name,maximum_material_name) || material.name.find('#') != std::string::npos ||
      !unit(material.base_color.x) || !unit(material.base_color.y) || !unit(material.base_color.z) || !unit(material.emission))
   invalid("Mesh material requires a bounded name and normalized finite base color/emission");
  for (std::size_t j=0;j<i;++j) if (material.name == materials[j].name) invalid("Mesh material names must be unique");
 }
}
Vec3 normal(double x, double y, double z) {
 const double length=std::sqrt(x*x+y*y+z*z);
 if (!std::isfinite(length) || length == 0) invalid("Mesh requires finite nonzero normals and nondegenerate triangles");
 return {static_cast<float>(x/length),static_cast<float>(y/length),static_cast<float>(z/length)};
}
Vec3 face_normal(Vec3 a, Vec3 b, Vec3 c) {
 const double ax=static_cast<double>(b.x)-a.x, ay=static_cast<double>(b.y)-a.y, az=static_cast<double>(b.z)-a.z;
 const double bx=static_cast<double>(c.x)-a.x, by=static_cast<double>(c.y)-a.y, bz=static_cast<double>(c.z)-a.z;
 return normal(ay*bz-az*by,az*bx-ax*bz,ax*by-ay*bx);
}
std::uint32_t float_bits(float value) { return value == 0 ? 0 : std::bit_cast<std::uint32_t>(value); }
struct Algorithm {
 BCRYPT_ALG_HANDLE handle=nullptr;
 ~Algorithm() { if (handle) BCryptCloseAlgorithmProvider(handle,0); }
};
struct Hash {
 BCRYPT_HASH_HANDLE handle=nullptr;
 ~Hash() { if (handle) BCryptDestroyHash(handle); }
};
std::array<std::byte,32> digest(std::span<const std::byte> input) {
 if (input.size() > mesh_asset_max_input_bytes) invalid("Mesh hash input exceeds 32 MiB");
 Algorithm algorithm;
 if (BCryptOpenAlgorithmProvider(&algorithm.handle,BCRYPT_SHA256_ALGORITHM,nullptr,0) < 0) throw std::runtime_error("Could not open SHA-256 provider");
 DWORD object_size=0, written=0;
 if (BCryptGetProperty(algorithm.handle,BCRYPT_OBJECT_LENGTH,reinterpret_cast<PUCHAR>(&object_size),sizeof(object_size),&written,0) < 0 || written != sizeof(object_size) || object_size > 1024*1024)
  throw std::runtime_error("Could not obtain bounded SHA-256 workspace");
 std::vector<unsigned char> workspace(object_size);
 Hash hash;
 if (BCryptCreateHash(algorithm.handle,&hash.handle,workspace.data(),object_size,nullptr,0,0) < 0) throw std::runtime_error("Could not create SHA-256 hash");
 if (!input.empty() && BCryptHashData(hash.handle,reinterpret_cast<PUCHAR>(const_cast<std::byte*>(input.data())),static_cast<ULONG>(input.size()),0) < 0)
  throw std::runtime_error("Could not hash mesh bytes");
 std::array<std::byte,32> output{};
 if (BCryptFinishHash(hash.handle,reinterpret_cast<PUCHAR>(output.data()),static_cast<ULONG>(output.size()),0) < 0) throw std::runtime_error("Could not finish SHA-256 hash");
 return output;
}
bool space(char c) { return c == ' ' || c == '\t' || c == '\r'; }
std::string_view trim(std::string_view value) {
 while (!value.empty() && space(value.front())) value.remove_prefix(1);
 while (!value.empty() && space(value.back())) value.remove_suffix(1);
 return value;
}
struct Tokens {
 std::string_view remaining;
 std::string_view next() {
  remaining=trim(remaining);
  const auto end=remaining.find_first_of(" \t\r");
  const auto token=remaining.substr(0,end);
  remaining=end == std::string_view::npos ? std::string_view{} : remaining.substr(end);
  return token;
 }
 void end() { if (!next().empty()) invalid("OBJ record has unsupported extra fields"); }
};
float number(std::string_view token) {
 if (token.empty()) invalid("OBJ requires a numeric field");
 if (token.front() == '+') {
  token.remove_prefix(1);
  if (token.empty() || token.front() == '+' || token.front() == '-') invalid("OBJ number has an invalid sign");
 }
 float value=0;
 const auto result=std::from_chars(token.data(),token.data()+token.size(),value,std::chars_format::general);
 if (result.ec != std::errc{} || result.ptr != token.data()+token.size() || !std::isfinite(value)) invalid("OBJ numeric field must be finite and valid");
 return value == 0 ? 0 : value;
}
std::size_t reference(std::string_view token, std::size_t count) {
 if (token.empty()) invalid("OBJ reference is missing");
 if (token.front() == '+') {
  token.remove_prefix(1);
  if (token.empty() || token.front() == '+' || token.front() == '-') invalid("OBJ reference has an invalid sign");
 }
 std::int64_t value=0;
 const auto result=std::from_chars(token.data(),token.data()+token.size(),value);
 if (result.ec != std::errc{} || result.ptr != token.data()+token.size() || value == 0) invalid("OBJ reference requires a nonzero integer");
 if (value > 0) {
  if (static_cast<std::uint64_t>(value) > count) invalid("OBJ positive reference is out of range");
  return static_cast<std::size_t>(value-1);
 }
 if (value < -static_cast<std::int64_t>(count)) invalid("OBJ negative reference is out of range");
 return static_cast<std::size_t>(static_cast<std::int64_t>(count)+value);
}
struct Reference { std::size_t position=0; std::size_t normal_index=0; bool supplied_normal=false; };
Reference face_reference(std::string_view token,std::size_t positions,std::size_t normals,std::size_t coordinates) {
 const auto first=token.find('/');
 if (first == std::string_view::npos) return {reference(token,positions),0,false};
 const auto second=token.find('/',first+1);
 if (second == std::string_view::npos || token.find('/',second+1) != std::string_view::npos) invalid("Supported OBJ faces use v, v//vn, or v/vt/vn references");
 const auto uv=token.substr(first+1,second-first-1);
 if (!uv.empty()) (void)reference(uv,coordinates);
 return {reference(token.substr(0,first),positions),reference(token.substr(second+1),normals),true};
}
struct Writer {
 std::vector<std::byte> data;
 void integer(std::uint32_t value) { for (unsigned shift=0;shift<32;shift+=8) data.push_back(static_cast<std::byte>((value>>shift)&255)); }
 void scalar(float value) { integer(float_bits(value)); }
 void vector(Vec3 value) { scalar(value.x);scalar(value.y);scalar(value.z); }
 void string(std::string_view value) {
  integer(static_cast<std::uint32_t>(value.size()));
  const auto* first=reinterpret_cast<const std::byte*>(value.data());
  data.insert(data.end(),first,first+value.size());
 }
};
struct Reader {
 std::span<const std::byte> data;
 std::span<const std::byte> take(std::size_t count) {
  if (count > data.size()) invalid("Truncated mesh asset payload");
  const auto value=data.first(count);data=data.subspan(count);return value;
 }
 std::uint32_t integer() {
  const auto value=take(4);std::uint32_t result=0;
  for (unsigned i=0;i<4;++i) result |= std::to_integer<std::uint32_t>(value[i])<<(8*i);
  return result;
 }
 float scalar() {
  const auto value=integer();
  if (value == 0x80000000u) invalid("Mesh asset contains noncanonical signed zero");
  const auto result=std::bit_cast<float>(value);
  if (!std::isfinite(result)) invalid("Mesh asset contains a nonfinite number");
  return result;
 }
 Vec3 vector() { const float x=scalar(),y=scalar(),z=scalar();return {x,y,z}; }
 std::string string(std::size_t maximum) {
  const auto count=integer();
  if (count > maximum) invalid("Mesh asset string exceeds its budget");
  const auto value=take(count);
  return {reinterpret_cast<const char*>(value.data()),value.size()};
 }
 std::size_t count(std::size_t maximum,std::size_t element_bytes) {
  const auto value=integer();
  if (value > maximum || static_cast<std::size_t>(value)*element_bytes > data.size()) invalid("Mesh asset count exceeds its budget or payload");
  return value;
 }
};
struct File {
 HANDLE handle=INVALID_HANDLE_VALUE;
 ~File() { if (handle != INVALID_HANDLE_VALUE) CloseHandle(handle); }
 void close() {
  const auto previous=handle;handle=INVALID_HANDLE_VALUE;
  if (!CloseHandle(previous)) throw std::runtime_error("Could not close mesh asset file");
 }
};
std::filesystem::path plain_path(const std::filesystem::path& path) {
 if (path.empty() || !path.has_filename()) invalid("Mesh asset requires a file path");
 const auto absolute=std::filesystem::absolute(path).lexically_normal();
 for (auto part=absolute;!part.empty();) {
  const auto attributes=GetFileAttributesW(part.c_str());
  if (attributes != INVALID_FILE_ATTRIBUTES && (attributes&FILE_ATTRIBUTE_REPARSE_POINT) != 0) invalid("Redirected mesh asset paths are not admitted");
  const auto parent=part.parent_path();if (parent == part) break;part=parent;
 }
 return absolute;
}
}

std::string asset_sha256(std::span<const std::byte> input) {
 constexpr char hex[]="0123456789abcdef";
 const auto hash=digest(input);std::string result;result.reserve(64);
 for (const auto byte:hash) { const auto value=std::to_integer<unsigned>(byte);result+=hex[value>>4];result+=hex[value&15]; }
 return result;
}

void validate_mesh_asset(const MeshAsset& asset) {
 if (!is_uuid(asset.asset_id) || !text(asset.name,maximum_name) || !sha_text(asset.source_sha256)) invalid("Mesh asset requires a UUID, bounded name and lowercase source SHA-256");
 if (asset.vertices.empty() || asset.vertices.size() > mesh_asset_max_vertices || asset.indices.empty() ||
     asset.indices.size() > mesh_asset_max_triangles*3 || asset.indices.size()%3 != 0 ||
     asset.triangle_materials.size() != asset.indices.size()/3) invalid("Mesh asset vertex/triangle budgets or counts are invalid");
 validate_materials(asset.materials);
 for (const auto& vertex:asset.vertices) {
  if (!finite(vertex.position) || !finite(vertex.normal)) invalid("Mesh vertices require finite positions/normals");
  (void)normal(vertex.normal.x,vertex.normal.y,vertex.normal.z);
 }
 for (const auto index:asset.indices) if (index >= asset.vertices.size()) invalid("Mesh triangle index is out of range");
 for (std::size_t triangle_index=0;triangle_index<asset.triangle_materials.size();++triangle_index) {
  if (asset.triangle_materials[triangle_index] >= asset.materials.size()) invalid("Mesh triangle material is out of range");
  const auto offset=triangle_index*3;
  (void)face_normal(asset.vertices[asset.indices[offset]].position,asset.vertices[asset.indices[offset+1]].position,asset.vertices[asset.indices[offset+2]].position);
 }
}

MeshAsset import_obj(std::string_view obj,std::span<const MeshMaterial> materials,std::string asset_id,std::string name) {
 if (obj.size() > mesh_asset_max_input_bytes || obj.find('\0') != std::string_view::npos) invalid("OBJ input exceeds 32 MiB or contains NUL bytes");
 if (!is_uuid(asset_id) || !text(name,maximum_name)) invalid("OBJ import requires a UUID and bounded asset name");
 validate_materials(materials);
 MeshAsset asset;asset.asset_id=std::move(asset_id);asset.name=std::move(name);
 asset.source_sha256=asset_sha256({reinterpret_cast<const std::byte*>(obj.data()),obj.size()});
 asset.materials.assign(materials.begin(),materials.end());
 std::vector<Vec3> positions,normals;
 std::size_t coordinates=0;std::uint32_t material=0;
 using Key=std::tuple<std::size_t,std::uint32_t,std::uint32_t,std::uint32_t>;
 std::map<Key,std::uint32_t> vertices;
 if (obj.starts_with("\xef\xbb\xbf")) obj.remove_prefix(3);
 while (!obj.empty()) {
  const auto end=obj.find('\n');auto line=obj.substr(0,end);
  obj=end == std::string_view::npos ? std::string_view{} : obj.substr(end+1);
  if (line.size() > 65536) invalid("OBJ line exceeds 64 KiB");
  if (const auto comment=line.find('#');comment != std::string_view::npos) line=line.substr(0,comment);
  Tokens tokens{line};const auto command=tokens.next();
  if (command.empty()) continue;
  if (command == "v" || command == "vn") {
   auto& values=command == "v" ? positions : normals;
   if (values.size() >= mesh_asset_max_vertices) invalid("OBJ position/normal count exceeds 100000");
   const float x=number(tokens.next()),y=number(tokens.next()),z=number(tokens.next());tokens.end();
   values.push_back(command == "v" ? Vec3{x,y,z} : normal(x,y,z));
  } else if (command == "vt") {
   if (coordinates >= mesh_asset_max_vertices) invalid("OBJ texture-coordinate count exceeds 100000");
   std::size_t count=0;
   for (auto field=tokens.next();!field.empty();field=tokens.next()) { if (++count > 3) invalid("OBJ texture coordinate has too many fields");(void)number(field); }
   if (count == 0) invalid("OBJ texture coordinate is missing");
   ++coordinates;
  } else if (command == "usemtl") {
   const auto selected=trim(tokens.remaining);
   const auto found=std::find_if(asset.materials.begin(),asset.materials.end(),[&](const MeshMaterial& candidate) { return candidate.name == selected; });
   if (found == asset.materials.end()) invalid("OBJ usemtl does not name an explicit engine material");
   material=static_cast<std::uint32_t>(found-asset.materials.begin());
  } else if (command == "f") {
   if (asset.triangle_materials.size() >= mesh_asset_max_triangles) invalid("OBJ triangle count exceeds 100000");
   std::array<Reference,3> face{};
   for (auto& vertex:face) vertex=face_reference(tokens.next(),positions.size(),normals.size(),coordinates);
   tokens.end();
   const auto generated=face_normal(positions[face[0].position],positions[face[1].position],positions[face[2].position]);
   for (const auto& vertex:face) {
    const auto n=vertex.supplied_normal ? normals[vertex.normal_index] : generated;
    const Key key{vertex.position,float_bits(n.x),float_bits(n.y),float_bits(n.z)};
    auto found=vertices.find(key);
    if (found == vertices.end()) {
     if (asset.vertices.size() >= mesh_asset_max_vertices) invalid("OBJ expanded vertex count exceeds 100000");
     const auto index=static_cast<std::uint32_t>(asset.vertices.size());
     asset.vertices.push_back({positions[vertex.position],n});found=vertices.emplace(key,index).first;
    }
    asset.indices.push_back(found->second);
   }
   asset.triangle_materials.push_back(material);
  } else if (command == "o" || command == "g" || command == "s" || command == "mtllib") {
   // Metadata only. Smoothing is deliberately not used, and mtllib never opens
   // a file: the caller's explicit engine material table is authoritative.
   if (trim(tokens.remaining).size() > maximum_name) invalid("OBJ metadata exceeds 4096 bytes");
   if ((command == "s" || command == "mtllib") && trim(tokens.remaining).empty()) invalid("OBJ metadata value is missing");
  } else invalid("Unsupported OBJ record; only triangulated v/vn/vt/f/usemtl and inert metadata are admitted");
 }
 validate_mesh_asset(asset);return asset;
}

std::vector<std::byte> encode_mesh_asset(const MeshAsset& asset) {
 validate_mesh_asset(asset);
 std::size_t size=12+asset.asset_id.size()+asset.name.size()+asset.source_sha256.size()+16+
     asset.vertices.size()*24+asset.indices.size()*4+asset.triangle_materials.size()*4;
 for (const auto& material:asset.materials) size+=20+material.name.size();
 if (size > mesh_asset_max_input_bytes-header_bytes) invalid("Encoded mesh exceeds 32 MiB");
 Writer payload;payload.data.reserve(size);
 payload.string(asset.asset_id);payload.string(asset.name);payload.string(asset.source_sha256);
 payload.integer(static_cast<std::uint32_t>(asset.vertices.size()));
 for (const auto& vertex:asset.vertices) { payload.vector(vertex.position);payload.vector(vertex.normal); }
 payload.integer(static_cast<std::uint32_t>(asset.indices.size()));for (const auto value:asset.indices) payload.integer(value);
 payload.integer(static_cast<std::uint32_t>(asset.triangle_materials.size()));for (const auto value:asset.triangle_materials) payload.integer(value);
 payload.integer(static_cast<std::uint32_t>(asset.materials.size()));
 for (const auto& material:asset.materials) { payload.string(material.name);payload.vector(material.base_color);payload.scalar(material.emission); }
 const auto checksum=digest(payload.data);
 Writer output;output.data.reserve(header_bytes+payload.data.size());
 output.data.insert(output.data.end(),magic.begin(),magic.end());output.integer(1);output.integer(static_cast<std::uint32_t>(payload.data.size()));
 output.data.insert(output.data.end(),checksum.begin(),checksum.end());output.data.insert(output.data.end(),payload.data.begin(),payload.data.end());
 return output.data;
}

MeshAsset decode_mesh_asset(std::span<const std::byte> bytes) {
 if (bytes.size() < header_bytes || bytes.size() > mesh_asset_max_input_bytes) invalid("Mesh binary size is invalid");
 Reader header{bytes};const auto signature=header.take(magic.size());
 if (!std::equal(signature.begin(),signature.end(),magic.begin()) || header.integer() != 1) invalid("Mesh binary magic/version is unsupported");
 const auto payload_size=header.integer();
 if (payload_size > mesh_asset_max_input_bytes-header_bytes || payload_size != bytes.size()-header_bytes) invalid("Mesh binary payload size/trailing bytes are invalid");
 const auto checksum=header.take(32);const auto calculated=digest(header.data);
 if (!std::equal(checksum.begin(),checksum.end(),calculated.begin())) invalid("Mesh binary payload checksum mismatch");
 Reader reader{header.data};MeshAsset asset;
 asset.asset_id=reader.string(36);asset.name=reader.string(maximum_name);asset.source_sha256=reader.string(64);
 auto count=reader.count(mesh_asset_max_vertices,24);asset.vertices.reserve(count);
 for (std::size_t i=0;i<count;++i) { const auto position=reader.vector(),n=reader.vector();asset.vertices.push_back({position,n}); }
 count=reader.count(mesh_asset_max_triangles*3,4);asset.indices.reserve(count);
 for (std::size_t i=0;i<count;++i) asset.indices.push_back(reader.integer());
 count=reader.count(mesh_asset_max_triangles,4);asset.triangle_materials.reserve(count);
 for (std::size_t i=0;i<count;++i) asset.triangle_materials.push_back(reader.integer());
 count=reader.count(mesh_asset_max_materials,20);asset.materials.reserve(count);
 for (std::size_t i=0;i<count;++i) { MeshMaterial material;material.name=reader.string(maximum_material_name);material.base_color=reader.vector();material.emission=reader.scalar();asset.materials.push_back(std::move(material)); }
 if (!reader.data.empty()) invalid("Mesh payload contains trailing bytes");
 validate_mesh_asset(asset);return asset;
}

MeshAsset load_mesh_asset(const std::filesystem::path& path) {
 const auto source=plain_path(path);
 File file;file.handle=CreateFileW(source.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_SEQUENTIAL_SCAN,nullptr);
 if (file.handle == INVALID_HANDLE_VALUE) throw std::runtime_error("Could not open mesh asset file");
 BY_HANDLE_FILE_INFORMATION information{};LARGE_INTEGER length{};
 if (!GetFileInformationByHandle(file.handle,&information) || (information.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)) != 0 || !GetFileSizeEx(file.handle,&length))
  throw std::runtime_error("Mesh asset is not a plain regular file");
 if (length.QuadPart < static_cast<LONGLONG>(header_bytes) || length.QuadPart > static_cast<LONGLONG>(mesh_asset_max_input_bytes)) invalid("Mesh asset file exceeds its size budget");
 std::vector<std::byte> data(static_cast<std::size_t>(length.QuadPart));DWORD read=0;
 if (!ReadFile(file.handle,data.data(),static_cast<DWORD>(data.size()),&read,nullptr) || read != data.size()) throw std::runtime_error("Could not read complete mesh asset file");
 return decode_mesh_asset(data);
}

void save_mesh_asset(const std::filesystem::path& path,const MeshAsset& asset) {
 const auto data=encode_mesh_asset(asset);const auto destination=plain_path(path);
 if (GetFileAttributesW(destination.c_str()) != INVALID_FILE_ATTRIBUTES) throw std::runtime_error("Immutable mesh asset destination already exists");
 const auto temporary=destination.parent_path()/(L".aibmesh-"+std::filesystem::path(new_uuid()).wstring()+L".tmp");
 bool created=false;
 try {
  File file;file.handle=CreateFileW(temporary.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_TEMPORARY|FILE_FLAG_WRITE_THROUGH,nullptr);
  if (file.handle == INVALID_HANDLE_VALUE) throw std::runtime_error("Could not create mesh asset publication file");
  created=true;DWORD written=0;
  if (!WriteFile(file.handle,data.data(),static_cast<DWORD>(data.size()),&written,nullptr) || written != data.size() || !FlushFileBuffers(file.handle))
   throw std::runtime_error("Could not flush complete mesh asset publication");
  file.close();
  // No REPLACE_EXISTING flag: racing/existing destinations remain untouched.
  if (!MoveFileExW(temporary.c_str(),destination.c_str(),MOVEFILE_WRITE_THROUGH)) throw std::runtime_error("Could not publish new immutable mesh asset");
  created=false;
 } catch (...) { if (created) DeleteFileW(temporary.c_str());throw; }
}
}
