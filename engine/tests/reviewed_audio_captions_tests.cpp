#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <aibs/audio_assets.hpp>
#include <aibs/audio_codec.hpp>
#include <algorithm>
#include <array>
#include <charconv>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string_view>
#include "../apps/reviewed_audio_captions.inl"
namespace {
unsigned checks=0;
void check(bool v,const char* text){if(!v)throw std::runtime_error(text);++checks;}
aibs::AudioAsset source(){aibs::AudioAsset a;a.asset_id="265a23aa-7368-470a-80e0-934643b328e2";a.name="Synthetic source";a.source_sha256=std::string(64,'a');a.frame_count=128;a.pcm.resize(512);return a;}
std::string fixture(){return R"({"schema_version":1,"status":"LISTENING_REVIEW_VALIDATED_FOR_NATIVE_ATTACHMENT","caption_review":"checked","source_sha256":")"+std::string(64,'a')+R"(","source_caption_draft_sha256":")"+std::string(64,'b')+R"(","review_export_sha256":")"+std::string(64,'c')+R"(","sample_rate":44100,"channels":2,"frame_count":128,"caption_count":2,"captions":[{"start_frame":0,"end_frame":64,"text":"Synthetic cue one.\nExact second line."},{"start_frame":64,"end_frame":128,"text":"Synthetic cue two."}],"reviewer":"Synthetic reviewer","reviewed_at_utc":"2026-11-02T00:00:00Z","automatic_approval":false,"declaration":"Human-supplied listening review declarations validated; this tool did not listen or verify spoken wording.","native_attachment_status":"not_supported_by_current_audio_cooker_cli"})";}
std::string replace(std::string s,std::string_view before,std::string_view after){const auto p=s.find(before);if(p==s.npos)throw std::runtime_error("Bad test replacement");s.replace(p,before.size(),after);return s;}
void rejects(std::string s){auto a=source();const auto before=a;bool caught=false;try{(void)aibs_caption_tool::parse_reviewed_captions(s,a);}catch(const std::invalid_argument&){caught=true;}check(caught,"Malformed reviewed sidecar admitted");check(a==before,"Rejected sidecar mutated imported audio");}
}
int main(){try{
 auto a=source();const auto before=a;auto r=aibs_caption_tool::parse_reviewed_captions(fixture(),a);
 check(a==before,"Parsing changed original PCM or metadata");check(r.captions.size()==2&&r.captions[0].start_frame==0&&r.captions[1].end_frame==128,"Source frame interval preserved");check(r.captions[0].text=="Synthetic cue one.\nExact second line.","Caption text altered");check(r.draft_sha256==std::string(64,'b')&&r.review_sha256==std::string(64,'c'),"Provenance lost");
 a.captions=std::move(r.captions);a.caption_review=aibs::AudioCaptionReview::checked;aibs::validate_audio_asset(a);const auto bytes=aibs::encode_audio_asset(a);const auto round=aibs::decode_audio_asset(bytes);check(round==a&&round.pcm==before.pcm,"Existing v2 codec did not preserve reviewed asset");
 auto bom="\xef\xbb\xbf"+fixture();check(aibs_caption_tool::parse_reviewed_captions(bom,before).captions.size()==2,"UTF8 BOM rejected");
 const auto unicode=replace(fixture(),"Synthetic cue two.","Snowman \\u2603 and \\ud83d\\ude80");check(aibs_caption_tool::parse_reviewed_captions(unicode,before).captions[1].text=="Snowman \xe2\x98\x83 and \xf0\x9f\x9a\x80","Unicode escape decoding changed text");
 for(const auto* bad:{"DRAFT_REQUIRES_LISTENING_REVIEW","DRAFT_LISTENING_REVIEW_IN_PROGRESS","LISTENING_REVIEW_COMPLETED","checked"})rejects(replace(fixture(),"LISTENING_REVIEW_VALIDATED_FOR_NATIVE_ATTACHMENT",bad));
 for(const auto* bad:{"draft","","true"})rejects(replace(fixture(),"\"caption_review\":\"checked\"",std::string("\"caption_review\":\"")+bad+"\""));
 for(const auto* bad:{"true","0","null","\"false\""})rejects(replace(fixture(),"\"automatic_approval\":false",std::string("\"automatic_approval\":")+bad));
 for(const auto* bad:{"0","2","1.0","true","1e0","01","-1","18446744073709551616"})rejects(replace(fixture(),"\"schema_version\":1",std::string("\"schema_version\":")+bad));
 for(const auto* bad:{"1","0","3","true","2.0"})rejects(replace(fixture(),"\"caption_count\":2",std::string("\"caption_count\":")+bad));
 for(const auto* bad:{"0","1","127","129","true","128.0"})rejects(replace(fixture(),"\"frame_count\":128",std::string("\"frame_count\":")+bad));
 rejects(replace(fixture(),"44100","48000"));rejects(replace(fixture(),"\"channels\":2","\"channels\":1"));rejects(replace(fixture(),std::string(64,'a'),std::string(64,'d')));rejects(replace(fixture(),std::string(64,'b'),std::string(64,'B')));rejects(replace(fixture(),std::string(64,'c'),"not-a-hash"));
 rejects(replace(fixture(),"\"start_frame\":64","\"start_frame\":63"));rejects(replace(fixture(),"\"end_frame\":128","\"end_frame\":129"));rejects(replace(fixture(),"\"start_frame\":0","\"start_frame\":64"));rejects(replace(fixture(),"\"start_frame\":0","\"start_frame\":false"));rejects(replace(fixture(),"\"start_frame\":0","\"start_frame\":0.0"));
 rejects(replace(fixture(),"Synthetic reviewer",""));rejects(replace(fixture(),"Synthetic reviewer",std::string(101,'x')));rejects(replace(fixture(),"Synthetic reviewer","\\u00a0"));
 for(const auto* bad:{"2026-11-02","2026-02-30T00:00:00Z","2026-11-02T24:00:00Z","2026-11-02T00:00:00+01:00","bad"})rejects(replace(fixture(),"2026-11-02T00:00:00Z",bad));
 check(aibs_caption_tool::parse_reviewed_captions(replace(fixture(),"2026-11-02T00:00:00Z","2024-02-29T23:59:59.123456+00:00"),before).captions.size()==2,"UTC fractional/leap-day timestamp rejected");
 rejects(replace(fixture(),"Synthetic cue two.",""));rejects(replace(fixture(),"Synthetic cue two.","   "));rejects(replace(fixture(),"Synthetic cue two.","\\u0000"));rejects(replace(fixture(),"Synthetic cue two.","\\ud800"));rejects(replace(fixture(),"Synthetic cue two.","\\udc00"));rejects(replace(fixture(),"Synthetic cue two.","\\uD800x"));rejects(replace(fixture(),"Synthetic cue two.",std::string("\xc0\x80",2)));rejects(replace(fixture(),"Synthetic cue two.",std::string(256u*1024u,'x')));
 rejects(fixture()+"garbage");rejects(fixture()+"{}");rejects("["+fixture()+"]");rejects(std::string(1024u*1024u+1,' '));rejects(fixture().substr(0,fixture().size()-1));
 rejects(replace(fixture(),"\"schema_version\":1","\"schema_version\":1,\"schema_version\":1"));rejects(replace(fixture(),"\"schema_version\":1","\"schema_version\":1,\"unknown\":0"));rejects(replace(fixture(),"\"reviewer\":\"Synthetic reviewer\",",""));rejects(replace(fixture(),"\"start_frame\":0","\"start_frame\":0,\"start_frame\":0"));rejects(replace(fixture(),"\"start_frame\":0","\"start_frame\":0,\"unknown\":0"));
 std::cout<<"Reviewed caption checks passed: "<<checks<<"\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
