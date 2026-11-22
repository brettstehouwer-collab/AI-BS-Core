#include <aibs/surface_codec.hpp>
#include <aibs/engine.hpp>
#include <algorithm>
#include <bit>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {
void need(bool b){if(!b)throw std::runtime_error("Surface codec contract failed");}
template<class F>void reject(F f){bool failed=false;try{f();}catch(const std::invalid_argument&){failed=true;}need(failed);}
std::uint32_t integer(const std::vector<std::byte>&b,std::size_t p){std::uint32_t v=0;for(unsigned s=0;s<32;s+=8)v|=std::to_integer<std::uint32_t>(b.at(p+s/8))<<s;return v;}
void integer(std::vector<std::byte>&b,std::size_t p,std::uint32_t v){for(unsigned s=0;s<32;s+=8)b.at(p+s/8)=static_cast<std::byte>((v>>s)&255);}
void rehash(std::vector<std::byte>&b){const auto hash=asset_sha256(std::span(b).subspan(48));for(std::size_t i=0;i<32;++i){const auto digit=[](char c){return c<='9'?c-'0':c-'a'+10;};b[16+i]=static_cast<std::byte>(digit(hash[i*2])*16+digit(hash[i*2+1]));}}
}
int main(){try{
 const std::string obj="v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n";
 auto asset=import_surface_obj(obj,std::vector<MeshMaterial>{{"pcb",{.2f,.8f,.3f},0}},new_uuid(),"Textured PCB",ObjUvOrigin::top_left);
 asset.images={{ImageSemantic::srgb_color,{{2,2,{0,255,0,255,0,100,0,255,0,200,0,255,20,220,10,255}}}}};generate_image_mips(asset.images[0]);asset.albedo_images={0};
 const auto v1=encode_mesh_asset(asset.geometry);const auto encoded=encode_surface_asset(asset);auto decoded=decode_surface_asset(encoded);
 need(encoded.size()<=surface_asset_max_input_bytes&&integer(encoded,8)==2);need(encode_surface_asset(decoded)==encoded&&encode_mesh_asset(decoded.geometry)==v1);
 need(decoded.images==asset.images&&decoded.albedo_images==asset.albedo_images&&decoded.corners.size()==3&&decoded.corners[1].u==1&&decoded.corners[2].v==1);
 need(decoded.geometry.source_sha256==asset.geometry.source_sha256&&surface_scene(decoded).vertices.size()==3);
 auto zero=asset;zero.corners[0].u=-0.f;zero.corners[0].tangent.y=-0.f;need(encode_surface_asset(zero)==encoded);
 for(std::size_t n=0;n<encoded.size();++n)reject([&]{decode_surface_asset(std::span(encoded).first(n));});
 auto bad=encoded;bad.back()^=std::byte{1};reject([&]{decode_surface_asset(bad);});
 bad=encoded;bad[0]=std::byte{0};reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,8,3);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,12,0xffffffff);reject([&]{decode_surface_asset(bad);});
 bad=encoded;bad.push_back(std::byte{0});integer(bad,12,static_cast<std::uint32_t>(bad.size()-48));rehash(bad);reject([&]{decode_surface_asset(bad);});
 const auto corner_count=52+v1.size(),first_corner=corner_count+4,image_count=first_corner+3*28,first_image=image_count+4;
 bad=encoded;integer(bad,48,0xffffffff);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,corner_count,0xffffffff);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,first_corner,0x80000000);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,first_corner,0x7fc00000);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,first_corner+24,2);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,first_corner+20,std::bit_cast<std::uint32_t>(0.f));rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,image_count,33);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,first_image,3);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,first_image+4,14);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,first_image+8,4097);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,first_image+16,0xffffffff);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,bad.size()-8,0);rehash(bad);reject([&]{decode_surface_asset(bad);});
 bad=encoded;integer(bad,bad.size()-4,32);rehash(bad);reject([&]{decode_surface_asset(bad);});
 auto invalid=asset;invalid.images[0].semantic=ImageSemantic::normal_map;reject([&]{encode_surface_asset(invalid);});
 invalid=asset;invalid.corners[0].tangent={0,0,1};reject([&]{encode_surface_asset(invalid);});
 invalid=asset;invalid.images[0].levels.pop_back();reject([&]{encode_surface_asset(invalid);});
 auto fallback=asset;fallback.images.clear();fallback.albedo_images={surface_no_image};need(encode_surface_asset(decode_surface_asset(encode_surface_asset(fallback)))==encode_surface_asset(fallback));
 auto data=asset;data.images[0].semantic=ImageSemantic::linear_data;need(decode_surface_asset(encode_surface_asset(data)).images[0].semantic==ImageSemantic::linear_data);
 auto degenerate=asset;for(auto&c:degenerate.corners)c.tangent_valid=false;need(!decode_surface_asset(encode_surface_asset(degenerate)).corners[1].tangent_valid);
 // Individually valid image chains can exceed the aggregate cooked payload.
 // This path must reject before allocating the final publication buffer.
 ImageAsset large;for(std::uint32_t d=2048;d>=1;d/=2)large.levels.push_back({d,d,std::vector<unsigned char>(static_cast<std::size_t>(d)*d*4)});
 auto over=asset;over.images={large,large};over.albedo_images={0};reject([&]{encode_surface_asset(over);});
 std::vector<std::byte> huge(surface_asset_max_input_bytes+1);reject([&]{decode_surface_asset(huge);});
 need(encode_mesh_asset(decode_mesh_asset(v1))==v1);
 std::cout<<"PASS surface codec canonical roundtrip, embedded images/UVs, malformed bounds, corruption, semantics and legacy bytes\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
