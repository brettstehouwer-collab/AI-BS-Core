#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/audio_assets.hpp>
#include <aibs/audio_codec.hpp>
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>
using namespace aibs;
namespace {
std::atomic<std::size_t> largest_allocation=0;
std::atomic<bool> track_allocations=false;
void observe(std::size_t n){if(track_allocations){auto old=largest_allocation.load();while(old<n&&!largest_allocation.compare_exchange_weak(old,n)){}}}
}
void* operator new(std::size_t n){observe(n);if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete[](void* p)noexcept{std::free(p);}
void operator delete(void* p,std::size_t)noexcept{std::free(p);}
void operator delete[](void* p,std::size_t)noexcept{std::free(p);}
namespace {
using Bytes=std::vector<std::byte>;
std::size_t checks=0;
void need(bool b,const char* why){++checks;if(!b)throw std::runtime_error(why);}
template<class F>void rejects(F f,const char* why){bool bad=false;try{f();}catch(const std::invalid_argument&){bad=true;}need(bad,why);}
void u16(Bytes& b,std::uint16_t n){b.push_back(static_cast<std::byte>(n&255));b.push_back(static_cast<std::byte>(n>>8));}
void u32(Bytes& b,std::uint32_t n){for(unsigned s=0;s<32;s+=8)b.push_back(static_cast<std::byte>((n>>s)&255));}
void set32(Bytes& b,std::size_t offset,std::uint32_t n){for(unsigned s=0;s<32;s+=8)b.at(offset+s/8)=static_cast<std::byte>((n>>s)&255);}
void set64(Bytes& b,std::size_t offset,std::uint64_t n){for(unsigned s=0;s<64;s+=8)b.at(offset+s/8)=static_cast<std::byte>((n>>s)&255);}
void tag(Bytes& b,std::string_view s){for(char c:s)b.push_back(static_cast<std::byte>(c));}
std::array<std::byte,32> hash(std::span<const std::byte> b){BCRYPT_ALG_HANDLE a=nullptr;need(BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0,"Test hash open");std::array<std::byte,32> h{};const auto status=BCryptHash(a,nullptr,0,const_cast<PUCHAR>(reinterpret_cast<const unsigned char*>(b.data())),static_cast<ULONG>(b.size()),reinterpret_cast<PUCHAR>(h.data()),32);BCryptCloseAlgorithmProvider(a,0);need(status>=0,"Test hash");return h;}
std::string hex(std::span<const std::byte> b){constexpr char h[]="0123456789abcdef";std::string r;for(auto v:b){const auto n=std::to_integer<unsigned>(v);r.push_back(h[n>>4]);r.push_back(h[n&15]);}return r;}
void rehash(Bytes& b){const auto h=hash(std::span<const std::byte>(b).subspan(52));std::copy(h.begin(),h.end(),b.begin()+20);}
const std::string id="12345678-1234-4abc-8def-123456789abc";
Bytes pcm(){return {std::byte{0},std::byte{0},std::byte{255},std::byte{127},std::byte{0},std::byte{128},std::byte{255},std::byte{255}};}
void chunk(Bytes& b,std::string_view name,const Bytes& data){tag(b,name);u32(b,static_cast<std::uint32_t>(data.size()));b.insert(b.end(),data.begin(),data.end());if(data.size()%2)b.push_back(std::byte{0xa5});}
Bytes wav(std::uint32_t rate=44100,std::uint16_t channels=2,bool extras=false,bool data_first=false){Bytes b;tag(b,"RIFF");u32(b,0);tag(b,"WAVE");Bytes fmt;u16(fmt,1);u16(fmt,channels);u32(fmt,rate);u32(fmt,rate*channels*2);u16(fmt,static_cast<std::uint16_t>(channels*2));u16(fmt,16);if(extras)chunk(b,"JUNK",{std::byte{1},std::byte{2},std::byte{3}});if(data_first)chunk(b,"data",pcm());chunk(b,"fmt ",fmt);if(extras)chunk(b,"LIST",{std::byte{4}});if(!data_first)chunk(b,"data",pcm());set32(b,4,static_cast<std::uint32_t>(b.size()-8));return b;}
AudioAsset fixture(){return import_pcm_wav(wav(),id,"Test");}
std::size_t body_fields(const AudioAsset& a){return 52+12+a.asset_id.size()+a.name.size()+a.source_sha256.size();}
void asset_tests(){
 auto a=fixture();need(a.asset_id==id&&a.name=="Test"&&a.sample_rate==44100&&a.channels==2&&a.frame_count==2&&a.pcm==pcm(),"WAV import changed exact metadata/PCM");need(a.source_sha256==hex(hash(wav())),"Source hash is not complete RIFF SHA256");validate_audio_asset(a);const auto cost=audio_asset_cost(a);need(cost.pcm_bytes==8&&cost.payload_bytes==208+8&&cost.decoded_bytes>=sizeof(AudioAsset)+8,"Complete byte charges incorrect");
 auto extra=import_pcm_wav(wav(44100,2,true,true),id,"Odd chunks");need(extra.pcm==a.pcm&&extra.frame_count==2,"Unknown padded chunks/data-before-fmt changed PCM");
 for(auto rate:{8000u,44100u,48000u,192000u})for(auto channels:std::array<std::uint16_t,2>{1,2}){const auto b=import_pcm_wav(wav(rate,channels),id,"Rate");need(b.sample_rate==rate&&b.channels==channels&&b.frame_count==8/(channels*2),"Source format was resampled/downmixed");}
 auto b=a;b.asset_id="12345678-1234-4ABC-8def-123456789abc";rejects([&]{validate_audio_asset(b);},"Uppercase UUID accepted");b=a;b.asset_id[14]='1';rejects([&]{validate_audio_asset(b);},"Nonv4 UUID accepted");b=a;b.source_sha256[0]='G';rejects([&]{validate_audio_asset(b);},"Invalid source SHA accepted");
 for(const std::string name:{std::string{},std::string(129,'a'),std::string("line\nname"),std::string("nul\0name",8),std::string("\xc0\x80",2)}){b=a;b.name=name;rejects([&]{validate_audio_asset(b);},"Invalid UTF8/label accepted");}
 b=a;b.name="M\xc3\xa9moire";validate_audio_asset(b);need(decode_audio_asset(encode_audio_asset(b))==b,"Valid UTF8 label changed");
 for(auto rate:{0u,7999u,192001u,std::numeric_limits<std::uint32_t>::max()}){b=a;b.sample_rate=rate;rejects([&]{validate_audio_asset(b);},"Invalid sample rate accepted");}
 for(auto channels:{0u,3u,65535u}){b=a;b.channels=channels;rejects([&]{validate_audio_asset(b);},"Unsupported channels accepted");}
 b=a;b.frame_count=0;rejects([&]{validate_audio_asset(b);},"Empty frame count accepted");b=a;b.frame_count=std::numeric_limits<std::uint64_t>::max();rejects([&]{validate_audio_asset(b);},"Frame product overflow accepted");b=a;b.pcm.pop_back();rejects([&]{validate_audio_asset(b);},"Unaligned PCM accepted");b=a;b.frame_count=1;rejects([&]{validate_audio_asset(b);},"Frame/PCM mismatch accepted");b=a;b.pcm.clear();rejects([&]{validate_audio_asset(b);},"Empty PCM accepted");
 {auto cap=a;cap.pcm.reserve(audio_asset_maximum_decoded_bytes+1);need(audio_asset_cost(cap).decoded_bytes>audio_asset_maximum_decoded_bytes,"Retained capacity not charged");rejects([&]{validate_audio_asset(cap);},"Decoded capacity limit not enforced");}
 {auto large=a;large.pcm.resize(audio_asset_maximum_payload_bytes-208);large.frame_count=large.pcm.size()/4;need(audio_asset_cost(large).payload_bytes==audio_asset_maximum_payload_bytes,"Exact payload boundary incorrect");const auto encoded=encode_audio_asset(large);need(encoded.size()==audio_asset_maximum_payload_bytes&&decode_audio_asset(encoded)==large,"Exact48MiB payload rejected");large.pcm.insert(large.pcm.end(),4,std::byte{});++large.frame_count;rejects([&]{validate_audio_asset(large);},"Over48MiB complete payload accepted");}
}
void wav_tests(){
 const auto good=wav();for(std::size_t n=0;n<good.size();++n)rejects([&]{(void)import_pcm_wav(std::span(good).first(n),id,"Truncated");},"Truncated WAV accepted");
 auto b=good;b[0]=std::byte{'X'};rejects([&]{(void)import_pcm_wav(b,id,"Bad");},"Wrong RIFF magic accepted");b=good;b[8]=std::byte{'X'};rejects([&]{(void)import_pcm_wav(b,id,"Bad");},"Wrong WAVE type accepted");b=good;b.push_back(std::byte{});rejects([&]{(void)import_pcm_wav(b,id,"Trailing");},"Trailing RIFF bytes accepted");b=good;set32(b,4,std::numeric_limits<std::uint32_t>::max());rejects([&]{(void)import_pcm_wav(b,id,"RIFF size");},"Forged RIFF length accepted");
 for(auto offset:{20u,22u,32u,34u}){b=good;b[offset]=std::byte{255};rejects([&]{(void)import_pcm_wav(b,id,"fmt");},"Unsupported/inconsistent fmt accepted");}
 b=good;set32(b,28,1);rejects([&]{(void)import_pcm_wav(b,id,"rate product");},"Inconsistent byte rate accepted");b=good;set32(b,24,7999);set32(b,28,7999*4);rejects([&]{(void)import_pcm_wav(b,id,"low rate");},"Out of profile WAV rate accepted");
 b=good;set32(b,40,7);b.pop_back();b.push_back(std::byte{});rejects([&]{(void)import_pcm_wav(b,id,"partial frame");},"Partial PCM frame accepted");
 b=good;tag(b,"data");u32(b,0);set32(b,4,static_cast<std::uint32_t>(b.size()-8));rejects([&]{(void)import_pcm_wav(b,id,"duplicate data");},"Duplicate data accepted");b=good;Bytes f;f.insert(f.end(),good.begin()+20,good.begin()+36);chunk(b,"fmt ",f);set32(b,4,static_cast<std::uint32_t>(b.size()-8));rejects([&]{(void)import_pcm_wav(b,id,"duplicate fmt");},"Duplicate fmt accepted");
 b=good;b[12]=std::byte{'X'};rejects([&]{(void)import_pcm_wav(b,id,"missing fmt");},"Missing fmt accepted");b=good;b[36]=std::byte{'X'};rejects([&]{(void)import_pcm_wav(b,id,"missing data");},"Missing data accepted");
 b=wav(44100,2,true);b.resize(23);set32(b,4,static_cast<std::uint32_t>(b.size()-8));rejects([&]{(void)import_pcm_wav(b,id,"padding");},"Missing odd-chunk padding accepted");b=good;set32(b,40,0xfffffff0);largest_allocation=0;track_allocations=true;rejects([&]{(void)import_pcm_wav(b,id,"forged data");},"Forged data length accepted");track_allocations=false;need(largest_allocation<4096,"Malformed WAV allocated PCM before range admission");
 // PCM fmt18 with an explicitly empty extension is valid; extensible/compressed is not.
 b=good;b.insert(b.begin()+36,2,std::byte{});set32(b,16,18);set32(b,4,static_cast<std::uint32_t>(b.size()-8));need(import_pcm_wav(b,id,"fmt18").pcm==pcm(),"Valid empty PCM extension rejected");b[36]=std::byte{1};rejects([&]{(void)import_pcm_wav(b,id,"extension");},"PCM extension mismatch accepted");
 {Bytes over(audio_wav_maximum_input_bytes+1);rejects([&]{(void)import_pcm_wav(over,id,"Too large");},"WAV input budget not enforced");}
}
void codec_tests(){
 const auto a=fixture();const auto good=encode_audio_asset(a);need(good.size()==audio_asset_cost(a).payload_bytes&&decode_audio_asset(good)==a,"Codec roundtrip changed owned PCM");need(encode_audio_asset(decode_audio_asset(good))==good,"Codec is not canonical");for(std::size_t n=0;n<good.size();++n)rejects([&]{(void)decode_audio_asset(std::span(good).first(n));},"Truncated codec accepted");
 for(std::size_t n=0;n<good.size();++n){auto b=good;b[n]^=std::byte{1};rejects([&]{(void)decode_audio_asset(b);},"Single-byte corruption accepted");}
 auto b=good;b.push_back(std::byte{});rejects([&]{(void)decode_audio_asset(b);},"Trailing codec bytes accepted");
 for(auto offset:{9u,10u,11u}){b=good;b[offset]=std::byte{1};rejects([&]{(void)decode_audio_asset(b);},"Reserved header accepted");}
 const auto fields=body_fields(a);for(const auto offset:{fields,fields+4,fields+8,fields+12}){b=good;set32(b,offset,0xffffffff);rehash(b);rejects([&]{(void)decode_audio_asset(b);},"Invalid codec format/reserved accepted");}
 b=good;set64(b,fields+16,std::numeric_limits<std::uint64_t>::max());rehash(b);largest_allocation=0;track_allocations=true;rejects([&]{(void)decode_audio_asset(b);},"Forged frame count accepted");track_allocations=false;need(largest_allocation<4096,"Forged count allocated large decoded storage");
 b=good;set64(b,fields+24,std::numeric_limits<std::uint64_t>::max());rehash(b);rejects([&]{(void)decode_audio_asset(b);},"Forged PCM length accepted");b=good;set32(b,52,0xffffffff);rehash(b);rejects([&]{(void)decode_audio_asset(b);},"Forged text length accepted");
 b=good;b[56]=std::byte{'X'};rehash(b);rejects([&]{(void)decode_audio_asset(b);},"Checksummed malformed UUID accepted");b=good;b[56+36+4]=std::byte{0xc0};rehash(b);rejects([&]{(void)decode_audio_asset(b);},"Checksummed malformed UTF8 accepted");
 auto retained=a;try{retained=decode_audio_asset(b);}catch(const std::invalid_argument&){}need(retained==a,"Failed replacement changed old asset");
 {Bytes over(audio_asset_maximum_payload_bytes+1);largest_allocation=0;track_allocations=true;rejects([&]{(void)decode_audio_asset(over);},"Oversized payload accepted");track_allocations=false;need(largest_allocation<4096,"Oversized input allocated decoded payload");}
}
void caption_tests(){
 auto a=fixture();a.pcm.resize(400);a.frame_count=100;need(a.captions.empty()&&a.caption_review==AudioCaptionReview::draft,"WAV import must not invent checked captions");a.captions={{0,20,"First line\nSecond line"},{40,100,"M\xc3\xa9moire \xf0\x9f\x92\xa1"}};validate_audio_asset(a);const auto b=encode_audio_asset(a);need(decode_audio_asset(b)==a,"Caption timestamps/UTF8/newlines changed in codec");auto declared=a;declared.caption_review=AudioCaptionReview::checked;need(decode_audio_asset(encode_audio_asset(declared))==declared,"Author-declared checked state not retained");
 for(unsigned kind=0;kind<7;++kind){auto bad=a;if(kind==0)bad.captions[0].end_frame=101;if(kind==1)bad.captions[0].end_frame=0;if(kind==2)bad.captions[1].start_frame=19;if(kind==3)std::swap(bad.captions[0],bad.captions[1]);if(kind==4)bad.captions[0].text.clear();if(kind==5)bad.captions[0].text=std::string("bad\0cue",7);if(kind==6)bad.captions[0].text=std::string("\xed\xa0\x80",3);rejects([&]{validate_audio_asset(bad);},"Invalid cue range/order/UTF8 accepted");}
 auto bad=a;bad.caption_review=static_cast<AudioCaptionReview>(2);rejects([&]{validate_audio_asset(bad);},"Unknown caption review declaration accepted");
 {auto boundary=a;boundary.captions={{0,100,std::string(audio_asset_maximum_caption_text_bytes,'x')}};need(decode_audio_asset(encode_audio_asset(boundary))==boundary,"Exact256KiB caption text rejected");boundary.captions[0].text.push_back('x');rejects([&]{validate_audio_asset(boundary);},"Over256KiB caption text accepted");}
 {auto boundary=a;boundary.pcm.resize(audio_asset_maximum_captions*2*4);boundary.frame_count=audio_asset_maximum_captions*2;boundary.captions.clear();for(std::uint64_t i=0;i<audio_asset_maximum_captions;++i)boundary.captions.push_back({i*2,i*2+1,"x"});need(decode_audio_asset(encode_audio_asset(boundary))==boundary,"Exact2048 cue limit rejected");boundary.captions.push_back({0,1,"x"});rejects([&]{validate_audio_asset(boundary);},"Over2048 captions accepted");}
 {auto retained=a;retained.captions[0].text.reserve(audio_asset_maximum_decoded_bytes);rejects([&]{validate_audio_asset(retained);},"Retained cue text capacity not charged");}
 auto encoded=b;const auto captions=body_fields(a)+32+a.pcm.size();set32(encoded,captions,2);rehash(encoded);rejects([&]{(void)decode_audio_asset(encoded);},"Checksummed unknown caption review accepted");encoded=b;set32(encoded,captions+4,0xffffffff);rehash(encoded);rejects([&]{(void)decode_audio_asset(encoded);},"Forged caption count accepted");encoded=b;set64(encoded,captions+8+8,101);rehash(encoded);rejects([&]{(void)decode_audio_asset(encoded);},"Checksummed caption past end accepted");
 {auto large=a;large.pcm.resize(16384);large.frame_count=4096;auto corrupt=encode_audio_asset(large);const auto first_cue=body_fields(large)+32+large.pcm.size()+8;set32(corrupt,first_cue+16,0xffffffff);rehash(corrupt);largest_allocation=0;track_allocations=true;rejects([&]{(void)decode_audio_asset(corrupt);},"Forged cue length accepted");track_allocations=false;need(largest_allocation<4096,"Decoder allocated owned PCM before caption preflight");}
}
void original(const std::filesystem::path& path,const std::filesystem::path& report){
 const auto length=std::filesystem::file_size(path);need(length<=audio_wav_maximum_input_bytes,"Original WAV exceeds input profile");Bytes raw(static_cast<std::size_t>(length));std::ifstream f(path,std::ios::binary);f.read(reinterpret_cast<char*>(raw.data()),static_cast<std::streamsize>(raw.size()));need(f.good(),"Original WAV read failed");const auto a=import_pcm_wav(raw,id,"Podium original full recording");need(a.sample_rate==44100&&a.channels==2&&a.frame_count==8684544&&a.pcm.size()==34738176,"Original recording lost frames/channels/source rate");need(a.source_sha256=="1464299dbe1280b979384f12fc34db1f6626b52ed3d1fb699541cf74082c2a08","Original recording differs from previously verified derivative");const auto encoded=encode_audio_asset(a);need(decode_audio_asset(encoded)==a,"Full original codec roundtrip changed PCM");const auto cost=audio_asset_cost(a);std::ofstream out(report);out<<"{\"status\":\"passed\",\"scope\":\"full source PCM import and codec only; no playback/caption claim\",\"sample_rate\":"<<a.sample_rate<<",\"channels\":"<<a.channels<<",\"frames\":"<<a.frame_count<<",\"pcm_bytes\":"<<a.pcm.size()<<",\"wav_bytes\":"<<raw.size()<<",\"source_sha256\":\""<<a.source_sha256<<"\",\"pcm_sha256\":\""<<hex(hash(a.pcm))<<"\",\"encoded_sha256\":\""<<hex(hash(encoded))<<"\",\"payload_bytes\":"<<cost.payload_bytes<<",\"decoded_bytes\":"<<cost.decoded_bytes<<",\"source_rate_channels_pcm_preserved\":true,\"family_source_copied\":false}\n";need(out.good(),"Cannot write original metadata-only proof");
}
}
int main(int argc,char** argv){try{asset_tests();wav_tests();codec_tests();caption_tests();if(argc==4&&std::string_view(argv[1])=="--original")original(argv[2],argv[3]);else need(argc==1,"Use --original WAV REPORT or no arguments");std::cout<<"PASS "<<checks<<" audio asset/WAV/codec and caption-data checks; playback and caption review not implemented\n";return 0;}catch(const std::exception& e){track_allocations=false;std::cerr<<e.what()<<'\n';return 1;}}
