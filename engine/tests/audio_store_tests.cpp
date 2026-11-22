#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <aibs/asset_store.hpp>
#include <aibs/audio_codec.hpp>
#include <aibs/engine.hpp>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace aibs;
namespace {
std::size_t checks=0;
void need(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
template<class F>void reject(F f,const char* message){bool failed=false;try{f();}catch(const std::invalid_argument&){failed=true;}need(failed,message);}
std::vector<std::byte> bytes(std::string_view text){return {reinterpret_cast<const std::byte*>(text.data()),reinterpret_cast<const std::byte*>(text.data()+text.size())};}
void write(const std::filesystem::path& path,std::span<const std::byte> body){const auto extended=std::filesystem::path(L"\\\\?\\"+std::filesystem::absolute(path).native());std::ofstream out(extended,std::ios::binary);out.write(reinterpret_cast<const char*>(body.data()),static_cast<std::streamsize>(body.size()));need(out.good(),"Cannot write private synthetic fixture");}
void text(const std::filesystem::path& path,std::string_view body){write(path,bytes(body));}
std::string audio_digest(std::span<const std::byte> body){
 std::array<unsigned char,32> out{};need(BCryptHash(BCRYPT_SHA256_ALG_HANDLE,nullptr,0,const_cast<PUCHAR>(reinterpret_cast<const unsigned char*>(body.data())),static_cast<ULONG>(body.size()),out.data(),static_cast<ULONG>(out.size()))>=0,"Independent test digest failed");constexpr char hex[]="0123456789abcdef";std::string result;for(const auto b:out){result+=hex[b>>4];result+=hex[b&15];}return result;
}
AudioAsset asset(std::size_t pcm_bytes=64){AudioAsset a;a.asset_id=new_uuid();a.name="Synthetic source-rate memory";a.source_sha256=std::string(64,'1');a.sample_rate=44100;a.channels=2;a.frame_count=pcm_bytes/4;a.pcm.resize(pcm_bytes);for(std::size_t i=0;i<a.pcm.size();++i)a.pcm[i]=std::byte(i%251);validate_audio_asset(a);return a;}
void pack(const std::filesystem::path& folder,const AudioAsset& a,std::string kind="audio",std::string suffix=".aibaud"){
 std::filesystem::create_directory(folder);const auto encoded=encode_audio_asset(a);const auto digest=audio_digest(encoded);write(folder/(digest+suffix),encoded);
 text(folder/"catalog.aibcat","AIBCAT 2\n"+kind+" "+a.asset_id+" "+digest+" "+digest+suffix+"\n");text(folder/"LICENSE.txt","AI-BS synthetic test PCM; no family media.\n");text(folder/"provenance.json","{\"source\":\"synthetic-audio-store-test\"}\n");
}
std::size_t entries(const std::filesystem::path& path){return static_cast<std::size_t>(std::distance(std::filesystem::directory_iterator(path),std::filesystem::directory_iterator{}));}
}
int main(int argc,char**argv){try{
 need(argc==2,"Pass private evidence parent");std::filesystem::create_directories(argv[1]);const auto root=std::filesystem::path(argv[1])/new_uuid();std::filesystem::create_directory(root);const auto store=root/"store";std::filesystem::create_directory(store);
 static_assert(asset_store_maximum_audio_pack_bytes==50u*1024u*1024u);
 auto a=asset();a.captions={{0,8,"Checked synthetic cue"},{8,16,"Second cue"}};a.caption_review=AudioCaptionReview::checked;pack(root/"source",a);const auto inspection=inspect_asset_pack(root/"source");
 need(inspection.kind==StoredAssetKind::audio_v2&&std::holds_alternative<AudioAsset>(inspection.asset.payload),"Generic typed inspection lost audio kind");
 need(std::get<AudioAsset>(inspection.asset.payload)==a,"Typed inspection changed source PCM");
 need(inspection.asset.decoded_bytes==audio_asset_cost(a).decoded_bytes,"Audio decoded charge differs");
 reject([&]{(void)inspect_visual_asset_pack(root/"source");},"Audio admitted as visual scenery");
 const auto reference=adopt_asset_pack(root/"source",store);need(reference==inspection.reference&&entries(store)==1,"Audio adoption differs from typed inspection");
 need(adopt_asset_pack(root/"source",store)==reference&&entries(store)==1,"Exact audio pack reuse duplicated data");
 std::size_t charged=999;const auto loaded=load_stored_audio_asset(store,reference,&charged);
 need(loaded.payload==a&&charged==loaded.encoded_bytes&&loaded.encoded_bytes==inspection.asset.encoded_bytes,"Stored audio bytes/charge changed");
 need(loaded.decoded_bytes==audio_asset_cost(a).decoded_bytes,"Stored decoded charge changed");
 reject([&]{(void)load_stored_asset(store,reference);},"Legacy mesh loader admitted audio");reject([&]{(void)load_stored_visual_asset(store,reference);},"Visual loader admitted audio");reject([&]{(void)load_stored_character_asset(store,reference);},"Character loader admitted audio");
 auto wrong=reference;wrong.asset_id=new_uuid();charged=777;reject([&]{(void)load_stored_audio_asset(store,wrong,&charged);},"Foreign audio UUID admitted");need(charged==777,"Failed load changed output charge");
 wrong=reference;wrong.pack_sha256=std::string(64,'a');reject([&]{(void)load_stored_audio_asset(store,wrong);},"Missing audio dependency admitted");
 charged=333;reject([&]{(void)load_stored_audio_asset(store,reference,&charged,inspection.asset.encoded_bytes-1);},"Audio read ignored whole pack bound");need(charged==333,"Bound rejection published a charge");
 const std::array refs{reference,reference};reject([&]{stage_asset_packs(store,refs,root/"legacy");},"Legacy profile staged audio");need(!std::filesystem::exists(root/"legacy"),"Rejected legacy closure published directory");
 stage_asset_packs(store,refs,root/"modern",false,AssetContentProfile::warm_beginning);need(entries(root/"modern")==1,"Audio closure was not deduplicated");need(load_stored_audio_asset(root/"modern",reference).payload==a,"Staging changed owned PCM");
 stage_asset_packs(store,refs,root/"modern",true,AssetContentProfile::warm_beginning);need(entries(root/"modern")==1,"Audio merge exact reuse duplicated data");
 pack(root/"wrong-kind",a,"character");reject([&]{(void)inspect_asset_pack(root/"wrong-kind");},"Catalog/audio suffix mismatch admitted");pack(root/"wrong-suffix",a,"audio",".aibchar");reject([&]{(void)inspect_asset_pack(root/"wrong-suffix");},"Audio catalog/character suffix mismatch admitted");
 const auto large=asset(34738176);pack(root/"large-source",large);const auto large_ref=adopt_asset_pack(root/"large-source",store);
 need(load_stored_audio_asset(store,large_ref).payload==large,"Default audio loader truncated >33MiB source-rate recording");
 reject([&]{(void)inspect_asset_pack(root/"large-source");},"Legacy33MiB generic default silently broadened");
 const auto large_inspect=inspect_asset_pack(root/"large-source",asset_store_maximum_audio_pack_bytes);need(large_inspect.asset.encoded_bytes>33u*1024u*1024u,"Large synthetic fixture did not cross original cap");
 const std::array mixed{reference,large_ref};stage_asset_packs(store,mixed,root/"large-stage",false,AssetContentProfile::warm_beginning);need(load_stored_audio_asset(root/"large-stage",large_ref).payload==large,"Large audio private closure changed bytes");
 std::vector<AssetPackReference> oversized{large_ref};
 for(unsigned i=0;i<3;++i){auto extra=large;extra.asset_id=new_uuid();const auto folder=root/("aggregate-source"+std::to_string(i));pack(folder,extra);oversized.push_back(adopt_asset_pack(folder,store));}
 reject([&]{stage_asset_packs(store,oversized,root/"oversized",false,AssetContentProfile::warm_beginning);},"Audio closure bypassed128MiB aggregate bound");need(!std::filesystem::exists(root/"oversized"),"Oversized closure published partial final store");
 auto corrupt=encode_audio_asset(large);corrupt[corrupt.size()/2]^=std::byte{1};write(store/large_ref.pack_sha256/(large_ref.asset_sha256+".aibaud"),corrupt);
 reject([&]{stage_asset_packs(store,mixed,root/"failed-stage",false,AssetContentProfile::warm_beginning);},"Corrupt audio closure staged");need(!std::filesystem::exists(root/"failed-stage"),"Corrupt closure published partial final store");need(load_stored_audio_asset(root/"modern",reference).payload==a,"Failed stage changed existing private store");
 reject([&]{stage_asset_packs(store,mixed,root/"modern",true,AssetContentProfile::warm_beginning);},"Corrupt audio merge admitted");need(entries(root/"modern")==1&&load_stored_audio_asset(root/"modern",reference).payload==a,"Failed merge changed retained store");
 std::ofstream report(root/"verification.json");report<<"{\"status\":\"passed\",\"checks\":"<<checks<<",\"large_pcm_bytes\":"<<large.pcm.size()<<",\"full_source_rate_preserved\":true,\"family_media_copied\":false}\n";need(report.good(),"Evidence write failed");std::cout<<"PASS "<<checks<<" audio store checks "<<root.string()<<'\n';return 0;
}catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}}
