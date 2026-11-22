#include <aibs/surface_assets.hpp>
#include <aibs/asset_scene.hpp>
#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <stdexcept>
#include <type_traits>
namespace aibs {namespace {
void need(bool b,const char*m){if(!b)throw std::invalid_argument(m);}
std::vector<std::string_view> tokens(std::string_view s){std::vector<std::string_view> out;while(!s.empty()){const auto start=s.find_first_not_of(" \t\r");if(start==s.npos)break;s.remove_prefix(start);const auto end=s.find_first_of(" \t\r");out.push_back(s.substr(0,end));if(end==s.npos)break;s.remove_prefix(end);}return out;}
std::string_view sign(std::string_view s){need(!s.empty(),"Missing OBJ number");if(s[0]=='+'){s.remove_prefix(1);need(!s.empty()&&s[0]!='+'&&s[0]!='-',"Invalid OBJ number sign");}return s;}
float scalar(std::string_view s){s=sign(s);float x=0;const auto r=std::from_chars(s.data(),s.data()+s.size(),x);need(r.ec==std::errc{}&&r.ptr==s.data()+s.size()&&std::isfinite(x),"Invalid UV scalar");return x==0?0:x;}
std::size_t index(std::string_view s,std::size_t count){s=sign(s);std::int64_t n=0;const auto r=std::from_chars(s.data(),s.data()+s.size(),n);need(r.ec==std::errc{}&&r.ptr==s.data()+s.size()&&n!=0&&n>=-static_cast<std::int64_t>(count)&&n<=static_cast<std::int64_t>(count),"Invalid UV index");return n>0?static_cast<std::size_t>(n-1):static_cast<std::size_t>(static_cast<std::int64_t>(count)+n);}
using V=std::array<double,3>;
double dot(V a,V b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
V cross(V a,V b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
V normalize(V v){const auto length=std::sqrt(dot(v,v));need(std::isfinite(length)&&length>1e-20,"Degenerate tangent");for(auto& x:v)x/=length;return v;}
V vector(Vec3 p){return {p.x,p.y,p.z};}
void tangents(SurfaceMeshAsset&asset){
 for(std::size_t t=0;t<asset.corners.size();t+=3){const auto&g=asset.geometry;const auto p=vector(g.vertices[g.indices[t]].position),q=vector(g.vertices[g.indices[t+1]].position),r=vector(g.vertices[g.indices[t+2]].position);V e1{},e2{};for(unsigned c=0;c<3;++c){e1[c]=q[c]-p[c];e2[c]=r[c]-p[c];}
  const double du1=static_cast<double>(asset.corners[t+1].u)-asset.corners[t].u,dv1=static_cast<double>(asset.corners[t+1].v)-asset.corners[t].v,du2=static_cast<double>(asset.corners[t+2].u)-asset.corners[t].u,dv2=static_cast<double>(asset.corners[t+2].v)-asset.corners[t].v;
  const double determinant=du1*dv2-du2*dv1;const bool valid=std::abs(determinant)>1e-20;V raw{},bitangent{};
  if(valid)for(unsigned c=0;c<3;++c){raw[c]=(e1[c]*dv2-e2[c]*dv1)/determinant;bitangent[c]=(e2[c]*du1-e1[c]*du2)/determinant;}
  for(unsigned k=0;k<3;++k){const auto n=normalize(vector(g.vertices[g.indices[t+k]].normal));V tangent=raw;const auto projection=dot(n,raw);for(unsigned c=0;c<3;++c)tangent[c]-=n[c]*projection;
   if(!valid||dot(tangent,tangent)<1e-30){V axis{1,0,0};if(std::abs(n[0])>.8)axis={0,1,0};tangent=cross(n,axis);}
   tangent=normalize(tangent);auto&corner=asset.corners[t+k];corner.tangent={static_cast<float>(tangent[0]),static_cast<float>(tangent[1]),static_cast<float>(tangent[2])};corner.tangent_sign=valid&&dot(cross(n,tangent),bitangent)<0?-1.f:1.f;corner.tangent_valid=valid;
  }
 }
}
}
SurfaceMeshAsset import_surface_obj(std::string_view input,std::span<const MeshMaterial> materials,std::string id,std::string name,ObjUvOrigin origin){
 need(input.size()<=mesh_asset_max_input_bytes&&input.find('\0')==input.npos,"Invalid surface OBJ byte bound");need(origin==ObjUvOrigin::top_left||origin==ObjUvOrigin::bottom_left,"Invalid UV origin");
 SurfaceMeshAsset asset;std::vector<std::array<float,2>> uv;std::string normalized;normalized.reserve(input.size());const auto original=input;
 if(input.starts_with("\xef\xbb\xbf"))input.remove_prefix(3);
 while(!input.empty()){
  const auto end=input.find('\n');const auto original_line=input.substr(0,end);input=end==input.npos?std::string_view{}:input.substr(end+1);need(original_line.size()<=65536,"OBJ line budget");auto line=original_line;if(const auto c=line.find('#');c!=line.npos)line=line.substr(0,c);const auto fields=tokens(line);
  if(!fields.empty()&&fields[0]=="vt"){need(fields.size()==3&&uv.size()<mesh_asset_max_vertices,"Surface OBJ requires bounded 2D UV records");const auto u=scalar(fields[1]),v=scalar(fields[2]);uv.push_back({u,origin==ObjUvOrigin::bottom_left?1-v:v});}
  if(!fields.empty()&&fields[0]=="f"){
   need(fields.size()==4&&asset.corners.size()<mesh_asset_max_triangles*3,"Surface OBJ requires bounded triangles");normalized+='f';
   for(unsigned c=1;c<4;++c){const auto token=fields[c];const auto first=token.find('/');need(first!=token.npos,"Surface OBJ face requires UVs");const auto second=token.find('/',first+1);const auto coordinate=token.substr(first+1,second==token.npos?token.npos:second-first-1);const auto selected=uv.at(index(coordinate,uv.size()));asset.corners.push_back({selected[0],selected[1]});normalized+=' ';normalized.append(second==token.npos?token.substr(0,first):token);}
   normalized+='\n';
  }else{normalized.append(original_line);normalized+='\n';}
 }
 asset.geometry=import_obj(normalized,materials,std::move(id),std::move(name));asset.geometry.source_sha256=asset_sha256({reinterpret_cast<const std::byte*>(original.data()),original.size()});asset.albedo_images.assign(materials.size(),surface_no_image);tangents(asset);validate_surface_asset(asset);return asset;
}
void validate_surface_asset(const SurfaceMeshAsset&a){
 validate_mesh_asset(a.geometry);need(a.corners.size()==a.geometry.indices.size()&&a.albedo_images.size()==a.geometry.materials.size()&&a.images.size()<=32,"Invalid surface attribute/material counts");std::size_t total=0;for(const auto&i:a.images){validate_image_asset(i);const auto n=image_resident_bytes(i);need(n<=128u*1024u*1024u-total,"Surface image budget");total+=n;}
 bool fallback=false;for(const auto i:a.albedo_images){need(i==surface_no_image||i<a.images.size(),"Invalid surface image reference");if(i!=surface_no_image)need(a.images[i].semantic!=ImageSemantic::normal_map,"Normal-map image cannot be an albedo binding");fallback|=i==surface_no_image;}
 need(!fallback||a.images.size()<32,"No descriptor slot remains for constant material fallback");
 for(std::size_t i=0;i<a.corners.size();++i){const auto&c=a.corners[i];need(std::isfinite(c.u)&&std::isfinite(c.v)&&(c.tangent_sign==1||c.tangent_sign==-1),"Invalid surface UV/tangent sign");const auto t=vector(c.tangent);need(std::abs(dot(t,t)-1)<1e-4&&std::abs(dot(normalize(vector(a.geometry.vertices[a.geometry.indices[i]].normal)),t))<1e-4,"Invalid tangent basis");}
}
TexturedScene surface_scene(const SurfaceMeshAsset&a,Vec3 center,Vec3 scale,Quaternion rotation){
 validate_surface_asset(a);SceneMesh positions;append_asset_mesh(positions,a.geometry,center,scale,rotation);TexturedScene scene;scene.images=a.images;std::uint32_t white=surface_no_image;
 if(std::find(a.albedo_images.begin(),a.albedo_images.end(),surface_no_image)!=a.albedo_images.end()){white=static_cast<std::uint32_t>(scene.images.size());scene.images.push_back({ImageSemantic::srgb_color,{{1,1,{255,255,255,255}}}});}
 // Opaque primitives are grouped by material, bounding submissions to the
 // asset's64 slots even when the source alternates material on every face.
 for(std::size_t material=0;material<a.geometry.materials.size();++material){
  const auto first=static_cast<std::uint32_t>(scene.vertices.size());
  for(std::size_t t=0;t<a.geometry.triangle_materials.size();++t)if(a.geometry.triangle_materials[t]==material)for(unsigned c=0;c<3;++c){const auto i=t*3+c;const auto&v=positions.vertices[i];scene.vertices.push_back({v.position,v.normal,a.corners[i].u,a.corners[i].v});}
  const auto count=static_cast<std::uint32_t>(scene.vertices.size())-first;
  if(count){const auto index=a.albedo_images[material]==surface_no_image?white:a.albedo_images[material];const auto&m=a.geometry.materials[material];scene.draws.push_back({first,count,index,m.base_color,m.emission});}
 }
 validate_textured_scene(scene);return scene;
}
void append_surface_scene(TexturedScene& destination,const SurfaceMeshAsset& asset,Vec3 center,Vec3 scale,Quaternion rotation){
 validate_textured_scene(destination);
 auto part=surface_scene(asset,center,scale,rotation);
 need(part.vertices.size()<=1000000-destination.vertices.size(),"Composed surface vertex budget");
 need(part.draws.size()<=256-destination.draws.size(),"Composed surface draw budget");
 std::size_t image_bytes=0;for(const auto& i:destination.images)image_bytes+=image_resident_bytes(i);
 std::vector<std::uint32_t> remap(part.images.size()),additions;
 for(std::size_t i=0;i<part.images.size();++i){
  const auto found=std::find(destination.images.begin(),destination.images.end(),part.images[i]);
  if(found!=destination.images.end()){remap[i]=static_cast<std::uint32_t>(found-destination.images.begin());continue;}
  const auto pending=std::find_if(additions.begin(),additions.end(),[&](auto j){return part.images[i]==part.images[j];});
  if(pending!=additions.end()){remap[i]=static_cast<std::uint32_t>(destination.images.size()+static_cast<std::size_t>(pending-additions.begin()));continue;}
  need(destination.images.size()+additions.size()<32,"Composed surface descriptor budget");
  const auto bytes=image_resident_bytes(part.images[i]);need(bytes<=128u*1024u*1024u-image_bytes,"Composed surface image budget");image_bytes+=bytes;
  remap[i]=static_cast<std::uint32_t>(destination.images.size()+additions.size());additions.push_back(static_cast<std::uint32_t>(i));
 }
 const auto offset=static_cast<std::uint32_t>(destination.vertices.size());
 for(auto& draw:part.draws){draw.first+=offset;draw.image=remap[draw.image];}
 // All allocating work precedes the no-throw element publication. Reallocating
 // capacity is harmless if a later reserve fails; no logical elements changed.
 destination.images.reserve(destination.images.size()+additions.size());
 destination.vertices.reserve(destination.vertices.size()+part.vertices.size());
 destination.draws.reserve(destination.draws.size()+part.draws.size());
 static_assert(std::is_nothrow_move_constructible_v<ImageAsset>);
 static_assert(std::is_nothrow_copy_constructible_v<TexturedVertex>);
 static_assert(std::is_nothrow_copy_constructible_v<TexturedDraw>);
 for(const auto i:additions)destination.images.push_back(std::move(part.images[i]));
 destination.vertices.insert(destination.vertices.end(),part.vertices.begin(),part.vertices.end());
 destination.draws.insert(destination.draws.end(),part.draws.begin(),part.draws.end());
}
}
