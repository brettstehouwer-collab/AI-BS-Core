#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/character_codec.hpp>
#include <array>
#include <bit>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace aibs;
namespace {
unsigned checks=0;
void need(bool ok,const char* why){++checks;if(!ok)throw std::runtime_error(why);}
void put(std::vector<std::byte>& b,std::size_t p,std::uint32_t v){for(unsigned k=0;k<4;++k)b.at(p+k)=static_cast<std::byte>((v>>(k*8))&255);}
void sign(std::vector<std::byte>& b){BCRYPT_ALG_HANDLE h=nullptr;need(BCryptOpenAlgorithmProvider(&h,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0,"Test hash provider failed");std::array<unsigned char,32> digest{};const auto result=BCryptHash(h,nullptr,0,reinterpret_cast<PUCHAR>(b.data()+48),static_cast<ULONG>(b.size()-48),digest.data(),32);BCryptCloseAlgorithmProvider(h,0);need(result>=0,"Test hashing failed");for(unsigned k=0;k<32;++k)b[16+k]=static_cast<std::byte>(digest[k]);}
CharacterAsset fixture(){CharacterAsset a;a.asset_id="12345678-1234-4234-8234-123456789abc";a.source_sha256=std::string(64,'a');a.name="Surface compatibility fixture";a.mesh.joints.resize(1);for(auto p:{Vec3{0,0,0},Vec3{1,0,0},Vec3{0,1,0}}){CharacterVertex v;v.position=p;a.mesh.vertices.push_back(v);}a.mesh.indices={0,1,2};a.materials.resize(1);a.draws={{0,3,0}};return a;}
std::vector<std::byte> wire(float roughness){auto b=encode_character_asset(fixture());const auto offset=b.size()-12;b.insert(b.begin()+static_cast<std::ptrdiff_t>(offset),4,std::byte{0});put(b,offset,std::bit_cast<std::uint32_t>(roughness));put(b,8,3);put(b,12,static_cast<std::uint32_t>(b.size()-48));sign(b);return b;}
template<class F>void rejects(F f){bool bad=false;try{f();}catch(const std::invalid_argument&){bad=true;}need(bad,"Invalid surface payload was accepted");}
}
int main(){try{
 const auto original=encode_character_asset(fixture());need(original[8]==std::byte{2},"Unchanged diffuse asset must retain version2");need(encode_character_asset(decode_character_asset(original))==original,"Legacy character bytes changed");
 const auto bytes=wire(.6f);const auto asset=decode_character_asset(bytes);need(encode_character_asset(asset)==bytes,"Surface factor must roundtrip exactly");need(character_asset_cost(asset).payload_bytes==bytes.size(),"Surface wire charge mismatch");
 for(float v:{.04f,.5f,.999f})need(encode_character_asset(decode_character_asset(wire(v)))==wire(v),"Valid roughness lost");
 for(float v:{-.1f,0.f,.039f,1.01f,std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity()})rejects([&]{(void)decode_character_asset(wire(v));});
 rejects([&]{(void)decode_character_asset(wire(1.f));}); // All-default v3 is a noncanonical promotion.
 auto corrupt=bytes;corrupt.back()^=std::byte{1};rejects([&]{(void)decode_character_asset(corrupt);});
 auto unknown=bytes;put(unknown,8,4);rejects([&]{(void)decode_character_asset(unknown);});
 auto short_body=bytes;short_body.pop_back();put(short_body,12,static_cast<std::uint32_t>(short_body.size()-48));sign(short_body);rejects([&]{(void)decode_character_asset(short_body);});
 std::cout<<"PASS "<<checks<<" character surface wire/legacy checks\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
