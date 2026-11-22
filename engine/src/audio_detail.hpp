#pragma once
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/audio_assets.hpp>
#include <algorithm>
#include <array>
#include <limits>
#include <stdexcept>
#include <string_view>
namespace aibs::audio_detail {
inline void need(bool b,const char* message){if(!b)throw std::invalid_argument(message);}
inline std::size_t add(std::size_t a,std::size_t b){need(b<=std::numeric_limits<std::size_t>::max()-a,"Audio byte accounting overflow");return a+b;}
inline bool hex(char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}
inline void identity(std::string_view id,std::string_view source){
 need(id.size()==36&&id[14]=='4'&&(id[19]=='8'||id[19]=='9'||id[19]=='a'||id[19]=='b'),"Audio asset requires a canonical version4 UUID");
 for(std::size_t i=0;i<id.size();++i)need(i==8||i==13||i==18||i==23?id[i]=='-':hex(id[i]),"Audio UUID is not canonical lowercase");
 need(source.size()==64&&std::all_of(source.begin(),source.end(),hex),"Audio source SHA256 is not canonical lowercase");
}
inline void label(std::string_view s){need(!s.empty()&&s.size()<=128&&std::none_of(s.begin(),s.end(),[](unsigned char c){return c<32||c==127;}),"Audio name exceeds UTF8 label profile");need(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),static_cast<int>(s.size()),nullptr,0)>0,"Audio name is not UTF8");}
inline void caption_text(std::string_view s){need(!s.empty()&&s.size()<=audio_asset_maximum_caption_text_bytes&&s.find('\0')==std::string_view::npos,"Audio caption text is empty/NUL/oversized");need(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),static_cast<int>(s.size()),nullptr,0)>0,"Audio caption text is not UTF8");}
inline void format(std::uint32_t rate,std::uint32_t channels,std::uint64_t frames,std::size_t bytes){
 need(rate>=8000&&rate<=192000&&(channels==1||channels==2),"Audio format supports8000..192000Hz and one/two channels");
 const auto block=channels*2u;need(frames>0&&bytes>0&&bytes%block==0&&frames==bytes/block,"Audio PCM/frame count disagrees with interleaved PCM16LE");
}
inline std::array<std::byte,32> digest(std::span<const std::byte> bytes){
 need(bytes.size()<=audio_wav_maximum_input_bytes,"Audio hash input exceeds bounded source profile");
 struct Algorithm{BCRYPT_ALG_HANDLE value=nullptr;~Algorithm(){if(value)BCryptCloseAlgorithmProvider(value,0);}} algorithm;
 if(BCryptOpenAlgorithmProvider(&algorithm.value,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)throw std::runtime_error("Audio SHA256 provider unavailable");std::array<std::byte,32> result{};
 if(BCryptHash(algorithm.value,nullptr,0,const_cast<PUCHAR>(reinterpret_cast<const unsigned char*>(bytes.data())),static_cast<ULONG>(bytes.size()),reinterpret_cast<PUCHAR>(result.data()),static_cast<ULONG>(result.size()))<0)throw std::runtime_error("Audio SHA256 computation failed");return result;
}
inline std::string digest_text(std::span<const std::byte> b){constexpr char digits[]="0123456789abcdef";const auto h=digest(b);std::string result;result.reserve(64);for(auto v:h){const auto n=std::to_integer<unsigned>(v);result.push_back(digits[n>>4]);result.push_back(digits[n&15]);}return result;}
struct Reader{
 std::span<const std::byte> data;
 std::span<const std::byte> take(std::size_t n){need(n<=data.size(),"Truncated audio data");const auto result=data.first(n);data=data.subspan(n);return result;}
 std::uint16_t u16(){const auto b=take(2);return static_cast<std::uint16_t>(std::to_integer<unsigned>(b[0])|(std::to_integer<unsigned>(b[1])<<8));}
 std::uint32_t u32(){const auto b=take(4);std::uint32_t n=0;for(unsigned s=0;s<32;s+=8)n|=std::to_integer<std::uint32_t>(b[s/8])<<s;return n;}
 std::uint64_t u64(){const auto b=take(8);std::uint64_t n=0;for(unsigned s=0;s<64;s+=8)n|=std::to_integer<std::uint64_t>(b[s/8])<<s;return n;}
 std::string_view text(std::size_t limit){const auto n=u32();need(n>0&&n<=limit,"Audio text length exceeds bound");const auto b=take(n);return {reinterpret_cast<const char*>(b.data()),b.size()};}
};
inline bool tag(std::span<const std::byte> bytes,std::string_view name){return bytes.size()==name.size()&&std::equal(bytes.begin(),bytes.end(),reinterpret_cast<const std::byte*>(name.data()));}
inline std::size_t payload_cost(std::size_t id,std::size_t name,std::size_t source,std::size_t pcm){return add(104,add(id,add(name,add(source,pcm))));}
inline std::size_t scanned_decoded(std::size_t id,std::size_t name,std::size_t source,std::size_t pcm){std::size_t n=add(sizeof(AudioAsset),pcm);for(const auto length:{id,name,source})n=add(n,add(std::max<std::size_t>(15,length),1));return n;}
}
