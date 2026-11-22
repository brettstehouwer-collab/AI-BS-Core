#include <aibs/asset_store.hpp>
#include <aibs/surface_codec.hpp>
#include <aibs/engine.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace fs=std::filesystem;
void need(bool b){if(!b)throw std::runtime_error("Surface store contract failed");}
template<class F>void reject(F f){bool bad=false;try{f();}catch(const std::invalid_argument&){bad=true;}need(bad);}
void write(const fs::path&p,std::span<const std::byte>b){std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char*>(b.data()),static_cast<std::streamsize>(b.size()));need(bool(f));}
void write(const fs::path&p,const std::string&s){write(p,{reinterpret_cast<const std::byte*>(s.data()),s.size()});}
int main(int argc,char**argv){try{
 need(argc==2);const fs::path root=fs::path(argv[1])/new_uuid();fs::create_directories(root/"source");fs::create_directory(root/"store");
 const auto source=root/"source",store=root/"store";
 auto a=import_surface_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n",std::vector<MeshMaterial>{{"pcb",{1,1,1},0}},new_uuid(),"PCB surface",ObjUvOrigin::top_left);
 a.images={{ImageSemantic::srgb_color,{{1,1,{12,120,45,255}}}}};a.albedo_images={0};
 const auto payload=encode_surface_asset(a);const auto hash=asset_sha256(payload);const auto name=hash+".aibsurf";
 write(source/name,payload);write(source/"catalog.aibcat",std::string("AIBCAT 2\nsurface ")+a.geometry.asset_id+" "+hash+" "+name+"\n");
 write(source/"LICENSE.txt",std::string("Original AI-BS test content\n"));write(source/"provenance.json",std::string("{\"origin\":\"test\"}\n"));
 const auto ref=adopt_asset_pack(source,store);need(ref.asset_id==a.geometry.asset_id&&ref.asset_sha256==hash);need(adopt_asset_pack(source,store)==ref);
 auto loaded=load_stored_visual_asset(store,ref);need(std::holds_alternative<SurfaceMeshAsset>(loaded.payload));need(encode_surface_asset(std::get<SurfaceMeshAsset>(loaded.payload))==payload);need(loaded.encoded_bytes>payload.size()&&loaded.decoded_bytes>4);
 reject([&]{load_stored_asset(store,ref);});
 reject([&]{stage_asset_packs(store,std::vector<AssetPackReference>{ref},root/"legacy");});need(!fs::exists(root/"legacy"));
 stage_asset_packs(store,std::vector<AssetPackReference>{ref,ref},root/"modern",false,AssetContentProfile::warm_beginning);
 need(encode_surface_asset(std::get<SurfaceMeshAsset>(load_stored_visual_asset(root/"modern",ref).payload))==payload);
 const auto old_source=root/"v1-source";fs::create_directory(old_source);
 const auto old_bytes=encode_mesh_asset(a.geometry);const auto old_hash=asset_sha256(old_bytes);
 write(old_source/(old_hash+".aibmesh"),old_bytes);write(old_source/"catalog.aibcat",std::string("AIBCAT 1\n")+a.geometry.asset_id+" "+old_hash+" "+old_hash+".aibmesh\n");
 write(old_source/"LICENSE.txt",std::string("Owned legacy fixture\n"));write(old_source/"provenance.json",std::string("{}\n"));
 const auto old_ref=adopt_asset_pack(old_source,store);
 stage_asset_packs(store,std::vector<AssetPackReference>{ref,old_ref},root/"mixed",false,AssetContentProfile::warm_beginning);
 need(encode_mesh_asset(load_stored_asset(root/"mixed",old_ref))==old_bytes);
 need(std::holds_alternative<MeshAsset>(load_stored_visual_asset(root/"mixed",old_ref).payload));
 need(encode_surface_asset(std::get<SurfaceMeshAsset>(load_stored_visual_asset(root/"mixed",ref).payload))==payload);
 // Kind is authenticated by both catalog and binary signature, never suffix alone.
 write(source/"catalog.aibcat",std::string("AIBCAT 2\ncharacter ")+a.geometry.asset_id+" "+hash+" "+name+"\n");
 reject([&]{adopt_asset_pack(source,store);});
 write(source/"catalog.aibcat",std::string("AIBCAT 1\n")+a.geometry.asset_id+" "+hash+" "+name+"\n");
 reject([&]{adopt_asset_pack(source,store);});
 reject([&]{load_stored_visual_asset(store,ref,nullptr,payload.size());});
 auto damaged=payload;damaged.back()^=std::byte{1};write(store/ref.pack_sha256/name,damaged);
 reject([&]{load_stored_visual_asset(store,ref);});
 reject([&]{stage_asset_packs(store,std::vector<AssetPackReference>{ref},root/"damaged",false,AssetContentProfile::warm_beginning);});need(!fs::exists(root/"damaged"));
 need(load_stored_visual_asset(root/"modern",ref).encoded_bytes==loaded.encoded_bytes);
 std::cout<<"PASS typed surface identity, immutable adoption, profile isolation, dedup staging, corruption and failed-publication preservation\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
