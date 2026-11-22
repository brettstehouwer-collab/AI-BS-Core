#include <aibs/surface_assets.hpp>
#include <aibs/engine.hpp>
#include <iostream>
#include <stdexcept>
using namespace aibs;
void need(bool b){if(!b)throw std::runtime_error("Surface import contract failed");}
template<class F>void reject(F f){bool failed=false;try{f();}catch(const std::invalid_argument&){failed=true;}need(failed);}
int main(){try{
 const std::string obj="v 0 0 0\nv 1 0 0\nv 0 1 0\nv 1 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nvt 1 1\nvt 0.25 0.5\nvt 0.75 1\nf 1/1 2/2 3/3\nf 2/5 4/4 3/6\n";
 const std::vector<MeshMaterial> materials{{"pcb",{1,1,1},1}};
 auto asset=import_surface_obj(obj,materials,new_uuid(),"UV seam",ObjUvOrigin::bottom_left);
 need(asset.geometry.vertices.size()==4&&asset.corners.size()==6);need(asset.corners[1].u==1&&asset.corners[3].u==.25f);need(asset.corners[0].v==1&&asset.corners[0].tangent_sign==-1);
 need(asset.geometry.source_sha256==asset_sha256({reinterpret_cast<const std::byte*>(obj.data()),obj.size()}));
 asset.images={{ImageSemantic::srgb_color,{{1,1,{40,220,70,255}}}}};asset.albedo_images={0};
 auto scene=surface_scene(asset,{4,5,6});need(scene.vertices.size()==6&&scene.images.size()==1&&scene.draws.size()==1&&scene.vertices.front().position==Vec3{4,5,6});need(scene.vertices[3].u==.25f);validate_textured_scene(scene);
 auto broken=asset;broken.corners.pop_back();reject([&]{validate_surface_asset(broken);});broken=asset;broken.albedo_images[0]=2;reject([&]{validate_surface_asset(broken);});
 broken=asset;broken.images[0].semantic=ImageSemantic::normal_map;
 reject([&]{validate_surface_asset(broken);});reject([&]{surface_scene(broken);});
 auto wrong_layer=scene;wrong_layer.images[0].semantic=ImageSemantic::normal_map;
 reject([&]{validate_textured_scene(wrong_layer);});
 const std::string simple="v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/-3 2/-2 3/-1\n";
 auto negative=import_surface_obj(simple,materials,new_uuid(),"Negative UV",ObjUvOrigin::top_left);need(negative.corners[0].tangent_sign==1&&negative.corners[0].v==0);
 reject([&]{import_surface_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",materials,new_uuid(),"Missing UV",ObjUvOrigin::top_left);});
 reject([&]{import_surface_obj(simple+"vt +-1 0\n",materials,new_uuid(),"Bad sign",ObjUvOrigin::top_left);});
 const auto v1=encode_mesh_asset(asset.geometry);need(encode_mesh_asset(decode_mesh_asset(v1))==v1);
 auto alternating=asset;alternating.geometry.materials.push_back({"metal",{.5f,.5f,.5f},0});alternating.albedo_images={0,0};alternating.geometry.indices.clear();alternating.geometry.triangle_materials.clear();alternating.corners.clear();
 for(unsigned t=0;t<600;++t){for(unsigned c=0;c<3;++c){alternating.geometry.indices.push_back(asset.geometry.indices[c]);alternating.corners.push_back(asset.corners[c]);}alternating.geometry.triangle_materials.push_back(t%2);}
 need(surface_scene(alternating).draws.size()==2);
 std::cout<<"PASS UV seam, source identity, coordinate origin, mirrored tangents, negative references, native scene projection and v1 compatibility\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
