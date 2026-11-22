#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/asset_scene.hpp>
#include <aibs/engine.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <set>
#include <stdexcept>
#include <string_view>
#include <utility>

namespace aibs {
namespace {
constexpr std::size_t maximum_catalog_bytes=1024u*1024u;
constexpr std::size_t maximum_catalog_records=1000;
constexpr std::size_t maximum_scene_vertices=1000000;
void need(bool condition,const char* message) {
 if(!condition) throw std::invalid_argument(message);
}
class Handle {
public:
 explicit Handle(HANDLE value):value_(value) {
  need(value_!=INVALID_HANDLE_VALUE,"Asset path is absent, inaccessible or not a regular package component");
 }
 ~Handle(){if(value_!=INVALID_HANDLE_VALUE)CloseHandle(value_);}
 Handle(const Handle&)=delete;
 Handle& operator=(const Handle&)=delete;
 Handle(Handle&& other) noexcept:value_(std::exchange(other.value_,INVALID_HANDLE_VALUE)){}
 HANDLE get()const noexcept{return value_;}
private:
 HANDLE value_;
};
std::filesystem::path absolute_path(const std::filesystem::path& input) {
 need(!input.empty(),"Asset package root must be explicit");
 auto path=std::filesystem::absolute(input);
 need(path.is_absolute()&&path.native().size()<=32760,"Asset package path is invalid or too long");
 for(const auto& part:path.relative_path())
  need(part!=L"..", "Asset package path cannot contain parent traversal");
 return path.lexically_normal();
}
Handle open_component(const std::filesystem::path& path,bool directory) {
 // Hold every ancestor without share-delete until the complete read finishes.
 // OPEN_REPARSE_POINT lets us inspect the component itself before following it.
 Handle handle(CreateFileW(path.c_str(),directory?FILE_READ_ATTRIBUTES:GENERIC_READ,
  directory?(FILE_SHARE_READ|FILE_SHARE_WRITE):FILE_SHARE_READ,nullptr,OPEN_EXISTING,
  FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_BACKUP_SEMANTICS,nullptr));
 BY_HANDLE_FILE_INFORMATION info{};
 need(GetFileInformationByHandle(handle.get(),&info)!=0,"Could not inspect asset package component");
 need((info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)==0,"Asset package path contains a reparse point or symlink");
 need(((info.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)!=0)==directory,
  "Asset package component has the wrong file/directory type");
 return handle;
}
std::vector<std::byte> read_checked(const std::filesystem::path& input,std::size_t maximum) {
 const auto path=absolute_path(input);
 std::vector<Handle> ancestors;
 auto current=path.root_path();
 ancestors.push_back(open_component(current,true));
 const auto parent=path.parent_path();
 for(const auto& part:parent.relative_path()) {
  current/=part;
  ancestors.push_back(open_component(current,true));
 }
 auto file=open_component(path,false);
 LARGE_INTEGER length{};
 need(GetFileSizeEx(file.get(),&length)!=0&&length.QuadPart>0&&
  static_cast<unsigned long long>(length.QuadPart)<=maximum,"Asset file is empty or exceeds its read byte limit");
 std::vector<std::byte> bytes(static_cast<std::size_t>(length.QuadPart));
 std::size_t offset=0;
 while(offset<bytes.size()) {
  const auto chunk=static_cast<DWORD>(std::min<std::size_t>(bytes.size()-offset,65536));
  DWORD copied=0;
  need(ReadFile(file.get(),bytes.data()+offset,chunk,&copied,nullptr)!=0&&copied>0,
   "Asset file could not be read completely");
  offset+=copied;
 }
 LARGE_INTEGER after{};
 need(GetFileSizeEx(file.get(),&after)!=0&&after.QuadPart==length.QuadPart,
  "Asset file size changed during read");
 return bytes;
}
bool hex_digest(std::string_view value) {
 return value.size()==64&&std::all_of(value.begin(),value.end(),[](char c){
  return(c>='0'&&c<='9')||(c>='a'&&c<='f');
 });
}
bool finite(Vec3 value) {
 return std::isfinite(value.x)&&std::isfinite(value.y)&&std::isfinite(value.z);
}
bool unit(float value) {return std::isfinite(value)&&value>=0&&value<=1;}
void validate_destination(const SceneMesh& scene) {
 need(scene.vertices.size()<=maximum_scene_vertices&&scene.vertices.size()%3==0,
  "Destination scene exceeds the triangle vertex limit or is not triangular");
 for(const auto& vertex:scene.vertices) {
  need(finite(vertex.position)&&finite(vertex.normal)&&
   (vertex.normal.x!=0||vertex.normal.y!=0||vertex.normal.z!=0)&&
   unit(vertex.color.x)&&unit(vertex.color.y)&&unit(vertex.color.z)&&unit(vertex.emission),
   "Destination scene contains an invalid vertex or material");
 }
}
using Coordinates=std::array<double,3>;
using Rotation=std::array<Coordinates,3>;
Rotation matrix(Quaternion value) {
 const double x=value.x,y=value.y,z=value.z,w=value.w;
 const double norm=x*x+y*y+z*z+w*w;
 need(std::isfinite(norm)&&std::abs(norm-1)<=1e-4,
  "Asset rotation requires a finite unit quaternion");
 const double factor=2/norm;
 return {{{1-factor*(y*y+z*z),factor*(x*y-z*w),factor*(x*z+y*w)},
          {factor*(x*y+z*w),1-factor*(x*x+z*z),factor*(y*z-x*w)},
          {factor*(x*z-y*w),factor*(y*z+x*w),1-factor*(x*x+y*y)}}};
}
Coordinates rotate(const Rotation& rotation,Coordinates value) {
 Coordinates result{};
 for(std::size_t row=0;row<3;++row)
  for(std::size_t column=0;column<3;++column)result[row]+=rotation[row][column]*value[column];
 return result;
}
Vec3 position(const AssetVertex& vertex,Vec3 center,Vec3 scale,const Rotation& rotation) {
 auto value=rotate(rotation,{static_cast<double>(vertex.position.x)*scale.x,
  static_cast<double>(vertex.position.y)*scale.y,static_cast<double>(vertex.position.z)*scale.z});
 const Coordinates origin{center.x,center.y,center.z};
 for(std::size_t i=0;i<3;++i) {
  value[i]+=origin[i];
  need(std::isfinite(value[i])&&std::abs(value[i])<=std::numeric_limits<float>::max(),
   "Transformed asset position exceeds finite float bounds");
 }
 return {static_cast<float>(value[0]),static_cast<float>(value[1]),static_cast<float>(value[2])};
}
Vec3 normal(const AssetVertex& vertex,Vec3 scale,const Rotation& rotation) {
 auto value=rotate(rotation,{static_cast<double>(vertex.normal.x)/scale.x,
  static_cast<double>(vertex.normal.y)/scale.y,static_cast<double>(vertex.normal.z)/scale.z});
 const double length=std::hypot(value[0],value[1],value[2]);
 need(std::isfinite(length)&&length>0,"Transformed asset normal is invalid");
 return {static_cast<float>(value[0]/length),static_cast<float>(value[1]/length),static_cast<float>(value[2]/length)};
}
}

AssetCatalog::AssetCatalog(const std::filesystem::path& root):root_(absolute_path(root)) {
 const auto bytes=read_checked(root_/"catalog.aibcat",maximum_catalog_bytes);
 const std::string text(reinterpret_cast<const char*>(bytes.data()),bytes.size());
 constexpr std::string_view header="AIBCAT 1\n";
 need(text.starts_with(header)&&text.back()=='\n',"Unsupported or noncanonical asset catalog header/newline");
 need(std::all_of(text.begin(),text.end(),[](unsigned char c){return c=='\n'||(c>=32&&c<=126);}),
  "Asset catalog requires canonical ASCII and LF text");
 std::set<std::string> ids,digests,files;
 std::size_t offset=header.size();
 while(offset<text.size()) {
  need(records_.size()<maximum_catalog_records,"Asset catalog exceeds its record limit");
  const auto end=text.find('\n',offset);
  need(end!=std::string::npos,"Asset catalog record is not newline terminated");
  const auto line=std::string_view(text).substr(offset,end-offset);
  // Fixed UUID/digest/basename widths also exclude whitespace ambiguity,
  // traversal, absolute paths, alternate streams and Windows filename aliases.
  constexpr std::size_t line_size=36+1+64+1+64+8;
  need(line.size()==line_size&&line[36]==' '&&line[101]==' ',"Malformed asset catalog record");
  AssetRecord row{std::string(line.substr(0,36)),std::string(line.substr(37,64)),std::string(line.substr(102))};
  need(is_uuid(row.asset_id)&&hex_digest(row.sha256),"Invalid asset catalog UUID or digest");
  need(row.file==row.sha256+".aibmesh","Asset catalog filename must be its exact digest basename");
  need(ids.insert(row.asset_id).second&&digests.insert(row.sha256).second&&files.insert(row.file).second,
   "Duplicate asset catalog identity, digest or path");
  records_.push_back(std::move(row));offset=end+1;
 }
}
MeshAsset AssetCatalog::load(const std::string& asset_id)const {
 const auto found=std::find_if(records_.begin(),records_.end(),[&](const auto& row){return row.asset_id==asset_id;});
 need(found!=records_.end(),"Asset UUID is absent from the selected package catalog");
 const auto bytes=read_checked(root_/found->file,mesh_asset_max_input_bytes);
 need(asset_sha256(bytes)==found->sha256,"Asset file digest differs from its immutable catalog record");
 auto asset=decode_mesh_asset(bytes);
 need(asset.asset_id==found->asset_id,"Decoded asset UUID differs from its catalog identity");
 return asset;
}
void append_asset_mesh(SceneMesh& scene,const MeshAsset& asset,Vec3 center,Vec3 scale,Quaternion rotation) {
 validate_mesh_asset(asset);
 validate_destination(scene);
 need(finite(center)&&finite(scale)&&scale.x>0&&scale.y>0&&scale.z>0,
  "Asset transform requires finite center and positive finite scale");
 const auto rotation_matrix=matrix(rotation);
 need(asset.indices.size()<=maximum_scene_vertices-scene.vertices.size(),
  "Composed asset exceeds the renderer triangle vertex limit");
 // Stage everything, including both vector allocations and the landmark string.
 // Publication consists only of noexcept swaps after all validation succeeds.
 SceneMesh candidate=scene;
 candidate.vertices.reserve(scene.vertices.size()+asset.indices.size());
 candidate.landmarks.push_back(asset.name);
 for(std::size_t i=0;i<asset.indices.size();++i) {
  const auto& vertex=asset.vertices[asset.indices[i]];
  const auto& material=asset.materials[asset.triangle_materials[i/3]];
  candidate.vertices.push_back({position(vertex,center,scale,rotation_matrix),
   normal(vertex,scale,rotation_matrix),material.base_color,material.emission});
 }
 scene.vertices.swap(candidate.vertices);scene.landmarks.swap(candidate.landmarks);
}
}
