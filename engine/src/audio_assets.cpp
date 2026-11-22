#include "audio_detail.hpp"
#include <aibs/engine.hpp>
namespace aibs {
AudioAssetCost audio_asset_cost(const AudioAsset& a){
 using namespace audio_detail;need(a.captions.size()<=audio_asset_maximum_captions,"Audio caption count exceeds2048");AudioAssetCost cost;cost.pcm_bytes=a.pcm.size();cost.payload_bytes=payload_cost(a.asset_id.size(),a.name.size(),a.source_sha256.size(),a.pcm.size());cost.decoded_bytes=add(sizeof(AudioAsset),a.pcm.capacity());for(const auto* s:{&a.asset_id,&a.name,&a.source_sha256})cost.decoded_bytes=add(cost.decoded_bytes,add(s->capacity(),1));need(a.captions.capacity()<=std::numeric_limits<std::size_t>::max()/sizeof(AudioCaption),"Audio caption capacity overflow");cost.decoded_bytes=add(cost.decoded_bytes,a.captions.capacity()*sizeof(AudioCaption));for(const auto& c:a.captions){cost.caption_text_bytes=add(cost.caption_text_bytes,c.text.size());need(cost.caption_text_bytes<=audio_asset_maximum_caption_text_bytes,"Audio caption text exceeds256KiB");cost.payload_bytes=add(cost.payload_bytes,add(20,c.text.size()));cost.decoded_bytes=add(cost.decoded_bytes,add(c.text.capacity(),1));}return cost;
}
void validate_audio_asset(const AudioAsset& a){
 using namespace audio_detail;need(is_uuid(a.asset_id),"Audio asset UUID invalid");identity(a.asset_id,a.source_sha256);label(a.name);format(a.sample_rate,a.channels,a.frame_count,a.pcm.size());const auto cost=audio_asset_cost(a);need(cost.payload_bytes<=audio_asset_maximum_payload_bytes&&cost.decoded_bytes<=audio_asset_maximum_decoded_bytes,"Audio complete payload/decoded charge exceeds profile");need(a.caption_review==AudioCaptionReview::draft||a.caption_review==AudioCaptionReview::checked,"Unknown audio caption review declaration");std::uint64_t previous=0;for(const auto& c:a.captions){need(c.start_frame>=previous&&c.start_frame<c.end_frame&&c.end_frame<=a.frame_count,"Audio captions overlap/are unsorted/outside recording");caption_text(c.text);previous=c.end_frame;}
}
AudioAsset import_pcm_wav(std::span<const std::byte> input,std::string asset_id,std::string name){
 using namespace audio_detail;need(input.size()>=12&&input.size()<=audio_wav_maximum_input_bytes,"WAV source outside bounded input profile");need(is_uuid(asset_id),"WAV import UUID invalid");label(name);
 Reader r{input};need(tag(r.take(4),"RIFF"),"WAV source must be RIFF little-endian");need(r.u32()==input.size()-8,"RIFF declared length differs from entire source");need(tag(r.take(4),"WAVE"),"RIFF source is not WAVE");
 bool has_fmt=false,has_data=false;std::uint32_t rate=0,channels=0;std::span<const std::byte> pcm;
 while(!r.data.empty()){
  const auto kind=r.take(4);const auto size=r.u32();const auto chunk=r.take(size);if(size%2)(void)r.take(1);
  if(tag(kind,"fmt ")){need(!has_fmt,"Duplicate WAV fmt chunk");has_fmt=true;need(size==16||size==18,"WAV PCM fmt supports16 or18 bytes with empty extension");Reader f{chunk};need(f.u16()==1,"WAV supports integer PCM format1 only");channels=f.u16();rate=f.u32();const auto byte_rate=f.u32();const auto block=f.u16(),bits=f.u16();need(rate>=8000&&rate<=192000&&(channels==1||channels==2)&&bits==16,"WAV supports source-rate PCM16 mono/stereo only");need(block==channels*2&&byte_rate==rate*block,"WAV byte rate/block alignment mismatch");if(size==18)need(f.u16()==0,"WAV PCM extension must be empty");}
  else if(tag(kind,"data")){need(!has_data,"Duplicate WAV data chunk");has_data=true;pcm=chunk;}
 }
 need(has_fmt&&has_data,"WAV requires exactly one fmt and data chunk");format(rate,channels,pcm.size()/(channels*2),pcm.size());need(payload_cost(asset_id.size(),name.size(),64,pcm.size())<=audio_asset_maximum_payload_bytes&&scanned_decoded(asset_id.size(),name.size(),64,pcm.size())<=audio_asset_maximum_decoded_bytes,"Imported WAV complete audio charge exceeds profile");
 AudioAsset out;out.asset_id=std::move(asset_id);out.name=std::move(name);out.source_sha256=digest_text(input);out.sample_rate=rate;out.channels=channels;out.frame_count=pcm.size()/(channels*2);out.pcm.assign(pcm.begin(),pcm.end());validate_audio_asset(out);return out;
}
}
