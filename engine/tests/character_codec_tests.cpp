#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/character_codec.hpp>
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>
namespace {bool bounded_allocations=false;std::size_t largest_allocation=0;}
void* operator new(std::size_t bytes){if(bounded_allocations){largest_allocation=std::max(largest_allocation,bytes);if(bytes>4096)throw std::bad_alloc();}if(void* p=std::malloc(bytes?bytes:1))return p;throw std::bad_alloc();}
void* operator new[](std::size_t bytes){return ::operator new(bytes);}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete[](void* p)noexcept{std::free(p);}
void operator delete(void* p,std::size_t)noexcept{std::free(p);}
void operator delete[](void* p,std::size_t)noexcept{std::free(p);}
using namespace aibs;
namespace {
std::size_t checks=0;
void need(bool value,const char* text){++checks;if(!value)throw std::runtime_error(text);}
template<class F>void bad(F f){bool rejected=false;try{f();}catch(const std::invalid_argument&){rejected=true;}need(rejected,"Malformed character payload accepted");}
CharacterAsset fixture(){CharacterAsset a;a.asset_id="12345678-1234-4234-8234-123456789abc";a.name="Owned character";a.source_sha256=std::string(64,'a');a.mesh.joints.resize(2);a.mesh.joints[0].bind_local.translation={.1f,0,0};a.mesh.joints[0].inverse_bind[12]=-.1f;a.mesh.joints[1].parent=0;a.mesh.joints[1].bind_local.translation={0,1,0};a.mesh.joints[1].inverse_bind[12]=-.1f;a.mesh.joints[1].inverse_bind[13]=-1;
 for(auto p:{Vec3{0,0,0},Vec3{1,0,0},Vec3{0,1,0}}){CharacterVertex v;v.position=p;v.joints={0,1,0,0};v.weights={.25f,.75f,0,0};a.mesh.vertices.push_back(v);}a.mesh.indices={0,1,2,2,1,0};CharacterClip c;c.name="wave";c.frame_count=2;c.looping=false;for(unsigned n=0;n<2;++n)for(const auto&j:a.mesh.joints)c.samples.push_back(j.bind_local);c.samples[3].rotation={0,0,std::sin(.1f),std::cos(.1f)};a.mesh.clips.push_back(c);ImageAsset image{ImageSemantic::srgb_color,{{2,2,{255,0,0,255,0,255,0,255,0,0,255,255,255,255,255,255}}}};generate_image_mips(image);a.images.push_back(image);a.materials={{0,{1,1,1},0,false},{character_no_image,{.7f,.5f,.2f},.4f,true}};a.draws={{0,3,0},{3,3,1}};return a;}
void put(std::vector<std::byte>& b,std::size_t p,std::uint32_t value){for(unsigned n=0;n<4;++n)b.at(p+n)=static_cast<std::byte>((value>>(n*8))&255);}
void sign(std::vector<std::byte>& b){BCRYPT_ALG_HANDLE algorithm=nullptr;need(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0,"Test hash provider unavailable");std::array<unsigned char,32> h{};const auto result=BCryptHash(algorithm,nullptr,0,reinterpret_cast<PUCHAR>(b.data()+48),static_cast<ULONG>(b.size()-48),h.data(),static_cast<ULONG>(h.size()));BCryptCloseAlgorithmProvider(algorithm,0);need(result>=0,"Test payload signing failed");for(unsigned n=0;n<32;++n)b[16+n]=static_cast<std::byte>(h[n]);}
}
int main(){try{
 auto a=fixture();const auto encoded=encode_character_asset(a);need(encoded.size()==character_asset_cost(a).payload_bytes,"Character wire cost differs from actual encoding");need(encoded.size()<4096,"Fixture unexpectedly large");need(std::equal(encoded.begin(),encoded.begin()+8,reinterpret_cast<const std::byte*>("AIBChar2")),"Wrong character magic");auto decoded=decode_character_asset(encoded);need(decoded==a,"Owned character fields changed on roundtrip");need(encode_character_asset(decoded)==encoded,"Character byte roundtrip is not exact");need(!decoded.materials[0].double_sided&&decoded.materials[1].double_sided,"Sidedness not retained");
 const auto palette=character_skin_palette(decoded.mesh,sample_character_clip(decoded.mesh,0,.5));const auto position=character_skin_vertex(decoded.mesh.vertices[1],palette);need(std::abs(position.position.x-(1+.75*(.9*(std::cos(.1)-1)+std::sin(.1))))<2e-5&&std::abs(position.position.y-.75*(.9*std::sin(.1)+1-std::cos(.1)))<2e-5,"Baked animation lost after codec roundtrip");
 auto zeros=a;zeros.mesh.vertices[0].position.x=-0.f;zeros.materials[0].emission=-0.f;need(encode_character_asset(zeros)==encoded,"Encoder does not canonicalize signed zero");
 for(std::size_t size=0;size<encoded.size();++size)bad([&]{decode_character_asset(std::span(encoded).first(size));});
 for(std::size_t byte=0;byte<encoded.size();++byte){auto corrupt=encoded;corrupt[byte]^=std::byte{1};bad([&]{decode_character_asset(corrupt);});}
 auto altered=encoded;altered.push_back(std::byte{});bad([&]{decode_character_asset(altered);});std::vector<std::byte> oversize(character_asset_max_input_bytes+1);bad([&]{decode_character_asset(oversize);});
 const auto counts=48+12+a.asset_id.size()+a.name.size()+a.source_sha256.size(),vertex=counts+32,index=vertex+72*a.mesh.vertices.size(),joint=index+4*a.mesh.indices.size(),clip=joint+108*a.mesh.joints.size(),clip_sample=clip+20+a.mesh.clips[0].name.size(),image=clip_sample+40*a.mesh.clips[0].samples.size(),mip=image+12,materials=mip+16+16+16+4,draws=materials+24*a.materials.size();
 const auto mutated=[&](std::size_t offset,std::uint32_t value){auto b=encoded;put(b,offset,value);sign(b);bad([&]{decode_character_asset(b);});};
 for(const auto [offset,value]:std::array<std::pair<std::size_t,std::uint32_t>,20>{{{counts,262145},{counts+4,1572865},{counts+8,65},{counts+12,9},{counts+16,33},{counts+20,65},{counts+24,65},{counts+28,1},{vertex,0x80000000},{vertex,0x7f800000},{vertex+24,0x7fc00000},{index,3},{joint,0},{clip+4+a.mesh.clips[0].name.size()+4,4097},{clip+4+a.mesh.clips[0].name.size()+8,2},{image,3},{image+8,1},{mip,4097},{mip+8,15},{materials+20,2}}})mutated(offset,value);
 mutated(mip+16,0x00ff00ff);mutated(draws,3);mutated(draws+4,0);mutated(draws+8,2);
 for(const auto offset:{vertex+64,joint+8,joint+48,clip_sample+8,materials+16})mutated(offset,0x80000000);
 mutated(joint+108,0xffffffffu);mutated(joint+4+28,0);mutated(joint+44+12*4,0);mutated(clip+16+a.mesh.clips[0].name.size(),1);mutated(mip+12,1);
 altered=encoded;altered.push_back(std::byte{});put(altered,12,static_cast<std::uint32_t>(altered.size()-48));sign(altered);bad([&]{decode_character_asset(altered);});
 // A material may legally retain and charge unused opaque images; every owned
 // image survives independent source destruction and the complete budget.
 auto unused=a;unused.images.push_back(unused.images[0]);const auto unused_bytes=encode_character_asset(unused);need(decode_character_asset(unused_bytes)==unused,"Unused owned image was silently dropped");
 // Malformed counts and truncated payloads cannot reach a large owned reserve.
 altered=encoded;put(altered,counts,262144);sign(altered);largest_allocation=0;bounded_allocations=true;try{bad([&]{decode_character_asset(altered);});}catch(...){bounded_allocations=false;throw;}bounded_allocations=false;need(largest_allocation<=4096,"Malformed count allocated before bounds check");
 auto source=encoded;auto owned=decode_character_asset(source);std::fill(source.begin(),source.end(),std::byte{});source.clear();source.shrink_to_fit();need(owned==a&&encode_character_asset(owned)==encoded,"Decoded character borrows input bytes");
 std::cout<<"PASS "<<checks<<" canonical character codec checks; malformed count peak allocation "<<largest_allocation<<" bytes\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
