#include <aibs/placed_assets.hpp>
#include <aibs/asset_store.hpp>
#include <aibs/content_dependencies.hpp>
#include <aibs/asset_scene.hpp>
#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <memory>
#include <stdexcept>

namespace aibs {
namespace {
void need(bool condition,const char* message){if(!condition)throw std::invalid_argument(message);}
constexpr std::size_t vertex_limit=1000000,memory_limit=64u*1024u*1024u;
std::size_t charge(const MeshAsset& asset){
 std::size_t result=asset.vertices.size()*sizeof(AssetVertex)+asset.indices.size()*sizeof(std::uint32_t)+asset.triangle_materials.size()*sizeof(std::uint32_t);
 for(const auto& material:asset.materials)result+=sizeof(MeshMaterial)+material.name.size();
 return result+asset.name.size()+asset.asset_id.size()+asset.source_sha256.size();
}
}
PlacedAssetVisuals::PlacedAssetVisuals(const FirstBootContent& content,const std::filesystem::path& store){
 const auto profile=content.definition().asset_profile;
 need(profile==AssetContentProfile::legacy_v1||profile==AssetContentProfile::warm_beginning,"Unsupported placed-asset content profile");
 const bool modern=profile==AssetContentProfile::warm_beginning;
 need(modern||content.definition().memories.empty(),"Memory audio requires warm-beginning content profile");
 const auto residency_limit=modern?asset_store_modern_staged_bytes:memory_limit;
 const auto pack_limit=modern?asset_store_modern_staged_bytes:asset_store_maximum_staged_bytes;
 std::map<std::string,StoredVisualAsset> loaded;std::size_t memory=0,pack_memory=0,expanded_memory=0;
 const auto& closure=closure_;
 if(modern){closure_=std::make_shared<const FirstBootAssetClosure>(load_first_boot_content_assets(content,store));memory=closure->decoded_bytes;pack_memory=closure->encoded_bytes;for(const auto& item:closure->assets)if(item.dependency.kind==FirstBootDependencyKind::character)companion_=std::shared_ptr<const CharacterAsset>(closure_,&std::get<CharacterAsset>(item.asset.payload));}
 else for(const auto& companion:content.definition().companions)need(!companion.model,"Character model requires the warm-beginning content profile");
 if(companion_){
  const auto& binding=content.definition().companions.front();const auto& vertices=companion_->mesh.vertices;auto low=vertices.front().position,high=low;
  for(const auto& vertex:vertices){const auto p=vertex.position;low.x=std::min(low.x,p.x);low.y=std::min(low.y,p.y);low.z=std::min(low.z,p.z);high.x=std::max(high.x,p.x);high.y=std::max(high.y,p.y);high.z=std::max(high.z,p.z);}
  const Vec3 center{binding.spawn.x+(low.x+high.x)*.5f,binding.spawn.y+(low.y+high.y)*.5f,binding.spawn.z+(low.z+high.z)*.5f};
  const Vec3 half{std::max(.005f,(high.x-low.x)*.5f),std::max(.005f,(high.y-low.y)*.5f),std::max(.005f,(high.z-low.z)*.5f)};
  companion_proxy_=SceneObject{binding.entity_id,binding.name+" bind-pose selection bounds",center,half,{.2f,.7f,.8f},0,true,{}};
 }
 const auto proxy=[&](const auto begin,const auto end,const FirstBootAssetPlacement& placement){
  need(begin!=end,"Placed mesh has no renderable triangles");
  Vec3 low=begin->position,high=low;
  for(auto it=begin;it!=end;++it){const auto p=it->position;low.x=std::min(low.x,p.x);low.y=std::min(low.y,p.y);low.z=std::min(low.z,p.z);high.x=std::max(high.x,p.x);high.y=std::max(high.y,p.y);high.z=std::max(high.z,p.z);}
  const Vec3 center{static_cast<float>((static_cast<double>(low.x)+high.x)/2),static_cast<float>((static_cast<double>(low.y)+high.y)/2),static_cast<float>((static_cast<double>(low.z)+high.z)/2)};
  const Vec3 half{std::max(.005f,static_cast<float>((static_cast<double>(high.x)-low.x)/2)),std::max(.005f,static_cast<float>((static_cast<double>(high.y)-low.y)/2)),std::max(.005f,static_cast<float>((static_cast<double>(high.z)-low.z)/2))};
  proxies_.push_back({placement.entity_id,placement.name,center,half,{.2f,.7f,.8f},0,placement.selectable,{}});
 };
 for(const auto& placement:content.definition().placements){
  const AssetPackReference reference{placement.asset_id,placement.asset_sha256,placement.pack_sha256};
  const SurfaceMeshAsset* surface=nullptr;const MeshAsset* geometry=nullptr;
  if(modern){
   const auto& payload=closure->require(reference,FirstBootDependencyKind::visual).payload;
   surface=std::get_if<SurfaceMeshAsset>(&payload);geometry=surface?&surface->geometry:std::get_if<MeshAsset>(&payload);
   need(geometry!=nullptr,"Character cannot be a static placement");
  }else{
   const auto key=reference.pack_sha256+reference.asset_sha256+reference.asset_id;auto found=loaded.find(key);
   if(found==loaded.end()){
    StoredVisualAsset asset;auto mesh=load_stored_asset(store,reference,&asset.encoded_bytes,pack_limit-pack_memory);asset.decoded_bytes=charge(mesh);asset.payload=std::move(mesh);
    need(asset.decoded_bytes<=residency_limit-memory,"Placed asset decoded residency exceeds content profile");memory+=asset.decoded_bytes;
    pack_memory+=asset.encoded_bytes;found=loaded.emplace(key,std::move(asset)).first;
   }
   geometry=&std::get<MeshAsset>(found->second.payload);
  }
  const auto& asset=*geometry;
  need(asset.indices.size()<=vertex_limit-geometry_.vertices.size()-textured_.vertices.size(),"Placed asset geometry exceeds renderer budget");
  if(modern){const auto bytes=asset.indices.size()*(surface?sizeof(TexturedVertex):sizeof(SceneVertex));need(bytes<=residency_limit-memory-expanded_memory,"Placed asset expanded residency exceeds128MiB");expanded_memory+=bytes;}
  if(surface){
   const auto first=textured_.vertices.size();append_surface_scene(textured_,*surface,placement.center,placement.scale,placement.rotation);
   proxy(textured_.vertices.begin()+static_cast<std::ptrdiff_t>(first),textured_.vertices.end(),placement);
  }else{
   SceneMesh part;append_asset_mesh(part,asset,placement.center,placement.scale,placement.rotation);proxy(part.vertices.begin(),part.vertices.end(),placement);
   geometry_.vertices.insert(geometry_.vertices.end(),part.vertices.begin(),part.vertices.end());
  }
  geometry_.landmarks.push_back(placement.name);
 }

 // Count actual retained capacities after composition, including copied image data.
 // The immutable closure includes AudioAsset PCM; session playback is charged later.
 const auto add=[&](std::size_t bytes){need(bytes<=residency_limit-resident_bytes_,"Retained content/projection residency exceeds profile");resident_bytes_+=bytes;};
 if(closure){add(closure->decoded_bytes);add(sizeof(FirstBootAssetClosure)+closure->assets.capacity()*sizeof(FirstBootResolvedAsset));}
 add(geometry_.vertices.capacity()*sizeof(SceneVertex));add(geometry_.landmarks.capacity()*sizeof(std::string));for(const auto& name:geometry_.landmarks)add(name.capacity()+1);
 add(textured_.vertices.capacity()*sizeof(TexturedVertex));add(textured_.draws.capacity()*sizeof(TexturedDraw));add(textured_.images.capacity()*sizeof(ImageAsset));
 for(const auto& image:textured_.images){add(image.levels.capacity()*sizeof(ImageMip));for(const auto& level:image.levels)add(level.rgba.capacity());}
 add(proxies_.capacity()*sizeof(SceneObject));for(const auto& p:proxies_){add(p.persistent_id.capacity()+1);add(p.name.capacity()+1);}
 if(companion_proxy_){add(companion_proxy_->persistent_id.capacity()+1);add(companion_proxy_->name.capacity()+1);}

}
SceneMesh PlacedAssetVisuals::mesh(const SceneSnapshot& scene)const{
 auto output=mesh_from_snapshot(scene);need(geometry_.vertices.size()<=vertex_limit-output.vertices.size()&&textured_.vertices.size()<=vertex_limit-output.vertices.size()-geometry_.vertices.size(),"Chapter and assets exceed renderer vertex budget");
 output.vertices.insert(output.vertices.end(),geometry_.vertices.begin(),geometry_.vertices.end());output.landmarks.insert(output.landmarks.end(),geometry_.landmarks.begin(),geometry_.landmarks.end());return output;
}
SceneSnapshot PlacedAssetVisuals::picking_scene(const SceneSnapshot& scene)const{
 auto output=scene;output.objects.insert(output.objects.end(),proxies_.begin(),proxies_.end());
 if(companion_proxy_)output.objects.push_back(*companion_proxy_);
 // Selection-only validation, never passed to the gameplay collision controller.
 (void)mesh_from_snapshot(output);return output;
}
SceneMesh PlacedAssetVisuals::selection_mesh(const std::string& id)const{
 const auto found=std::find_if(proxies_.begin(),proxies_.end(),[&](const auto& p){return p.persistent_id==id;});
 const SceneObject* selected=found==proxies_.end()?nullptr:&*found;
 if(!selected&&companion_proxy_&&companion_proxy_->persistent_id==id)selected=&*companion_proxy_;
 if(!selected)return {};
 SceneSnapshot lines{id,0,{}};const auto c=selected->center,h=selected->half_extent;
 const float thickness=.025f;
 const auto add=[&](Vec3 center,Vec3 half){lines.objects.push_back({id,"Placement bounds",center,half,{.1f,.85f,1},1,false,{}});};
 for(const float a:{-1.f,1.f})for(const float b:{-1.f,1.f}){
  add({c.x,c.y+a*h.y,c.z+b*h.z},{h.x,thickness,thickness});
  add({c.x+a*h.x,c.y,c.z+b*h.z},{thickness,h.y,thickness});
  add({c.x+a*h.x,c.y+b*h.y,c.z},{thickness,thickness,h.z});
 }
 return mesh_from_snapshot(lines);
}
}
