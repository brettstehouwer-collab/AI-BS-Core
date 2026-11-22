#pragma once
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>
namespace aibs {
inline constexpr std::size_t audio_asset_maximum_payload_bytes=48u*1024u*1024u;
inline constexpr std::size_t audio_asset_maximum_decoded_bytes=64u*1024u*1024u;
inline constexpr std::size_t audio_wav_maximum_input_bytes=49u*1024u*1024u;
inline constexpr std::size_t audio_asset_maximum_captions=2048;
inline constexpr std::size_t audio_asset_maximum_caption_text_bytes=256u*1024u;
struct AudioCaption {std::uint64_t start_frame=0,end_frame=0;std::string text;bool operator==(const AudioCaption&)const=default;};
// An author's declaration only, never proof of linguistic/listening review.
enum class AudioCaptionReview : std::uint32_t {draft=0,checked=1};
// Entire source-rate interleaved signed PCM16LE. Byte ownership is independent
// of RIFF input lifetime; no encoded WAV, external path or borrowed data remains.
struct AudioAsset {
 std::string asset_id,name,source_sha256;
 std::uint32_t sample_rate=44100,channels=2;
 std::uint64_t frame_count=0;
 std::vector<std::byte> pcm;
 std::vector<AudioCaption> captions;
 AudioCaptionReview caption_review=AudioCaptionReview::draft;
 bool operator==(const AudioAsset&)const=default;
};
struct AudioAssetCost {std::size_t payload_bytes=0,decoded_bytes=0,pcm_bytes=0,caption_text_bytes=0;};
AudioAssetCost audio_asset_cost(const AudioAsset&);
void validate_audio_asset(const AudioAsset&);
// RIFF/WAVE PCM format1,16-bit,8000..192000Hz,one/two channels only.
// Unknown bounded chunks and odd-byte padding are retained in the source hash,
// skipped for playback PCM. Duplicate fmt/data, truncation and trailing reject.
AudioAsset import_pcm_wav(std::span<const std::byte>,std::string asset_id,std::string name);
}
