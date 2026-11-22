# Owned PCM assets and AIBAudio2

Current SDK0.17.0 includes the canonical audio codec, typed audio store/cooker,
XAudio2 playback, memory interaction and creator dependency integration. These
foundations are included in the deployed Studio5.329.106 engineering preview;
they do not mean the opening includes Adam's original recording. Its default
six-role asset bundle contains no audio role. Family captions remain drafts,
with listening review deferred by the creator; no family recording is marked
checked or bound in that default opening.

See [memory runtime](MEMORY_AUDIO_RUNTIME.md),
[playback contract](MEMORY_PLAYBACK.md) and the
[current acceptance audit](../docs/game_engine/WARM_BEGINNING_ACCEPTANCE_AUDIT.md).
Historical source-only reports below retain their original scope. Logs and
original-recording reports contain metadata/hashes, not the private media.

## Public contract

`include/aibs/audio_assets.hpp` owns one complete interleaved signed PCM16LE
recording: canonical lowercase version4 `asset_id`, nonempty UTF8 `name` up to128
bytes without ASCII controls, lowercase64-hex `source_sha256`, `sample_rate`,
`channels`, `frame_count`, and `std::vector<std::byte> pcm`. Rates8000..192000Hz
and one/two channels are allowed. Empty recordings reject. Every PCM byte must
belong to a full frame; frame count must equal `pcm.size()/(channels*2)`.

Optional `AudioCaption` records hold `start_frame`, exclusive `end_frame` and
UTF8 text. At most2048 cues and256KiB total cue text are permitted. Cues are
nonempty, ordered, nonoverlapping and within the recording; gaps are valid.
NUL/invalid UTF8 reject; valid multiline text is preserved. `caption_review`
is `AudioCaptionReview::draft` by default, or the author's explicit `checked`
declaration. The declaration cannot certify that captions were heard/reviewed
or that their wording is correct. WAV import always produces no cues/draft.

`import_pcm_wav(span,UUID,name)` retains source sample rate, channel order and
all PCM bytes. It does no trimming, resampling, downmixing, normalization or
voice generation. `source_sha256` hashes the entire WAV source, including
metadata, unknown chunks and padding. It is a source identity, distinct from
the PCM digest and the encoded-asset digest.

`audio_asset_cost` reports four separate quantities:

- `payload_bytes`: exact complete encoded envelope/body/strings/PCM length.
- `decoded_bytes`: conservative owned object, all retained string capacities
  including terminators, PCM/caption vector capacities, and all retained cue
  text capacities. This is not total process RSS.
- `pcm_bytes`: the owned PCM vector's logical bytes.
- `caption_text_bytes`: total logical UTF8 caption bytes.

The complete encoded asset is limited to48MiB and complete decoded/capacity
charge to64MiB. WAV source input has a49MiB bound to allow container metadata.
The lower encoded limit still applies after import, before PCM is copied.
Source buffers, encoded buffers, temporary replacements and a future playback
copy must be charged separately when simultaneously resident. These modules
make no zero-copy or total-process-memory claim.

## WAV profile

The reader requires an exact little-endian RIFF/WAVE file with its declared
RIFF length equal to the whole input. It accepts exactly one `fmt ` and one
`data` chunk in either order. Unknown chunks are bounded, skipped and included
in the source hash. Odd chunks consume one required pad byte, whose value is
not constrained. Header/chunk range checks run before PCM allocation.

The supported format is integer PCM tag1,16bits, with matching byte rate and
block alignment. The `fmt ` chunk is16bytes, or18bytes with `cbSize=0`.
Compressed/floating/extensible formats, RF64/RIFX, duplicate chunks, missing
required chunks, partial frames, inconsistent rates/alignments, missing pad
bytes, truncation and trailing bytes reject. The limited profile deliberately
does not claim arbitrary WAV support.

## Exact AIBAudio2 wire format

All integers are little endian. There is no implicit alignment padding.

| Offset | Bytes | Field |
|---|---:|---|
|0|9|ASCII `AIBAudio2`|
|9|3|Reserved, all zero|
|12|4|Version, exactly2|
|16|4|Body length, exactly whole input minus52|
|20|32|SHA256 of the complete body|
|52|variable|Body below|

The body contains three `u32 byteLength + UTF8 bytes` strings: UUID, name and
source SHA. Next are `u32 sample_rate`, `u32 channels`, `u32 bits=16`,
`u32 reserved=0`, `u64 frame_count`, `u64 pcm_byte_count`, then the exact PCM
bytes. After PCM, the body contains `u32 caption_review` (draft0/checked1),
`u32 caption_count`, then each cue's `u64 start_frame`, `u64 end_frame` and
`u32 text_byte_length + UTF8 bytes`. No trailing bytes are permitted. These
fields were added before this previously unreleased audio format was frozen;
there is no released legacy audio wire compatibility claim.

Metadata identity, UTF8, every cue range/count/text and complete budgets are
scanned without constructing owned PCM or cue arrays. Only a fully admitted
view is copied into a new asset. A failed decode cannot mutate a caller's old
asset. PCM remains byte-exact irrespective of caption declarations.

The codec has no filesystem/network/resource lookup. SHA uses the Windows
BCrypt provider; provider failures are runtime errors. Malformed input rejects
with `std::invalid_argument`.

## Build and verification

The isolated CMake project consumes installed SDK0.11 Core and Windows BCrypt.
It does not compile or modify the canonical engine. `audio_assets` and
`audio_codec` are separate static targets. Both and their test executable use
C++20 and MSVC `/W4 /WX /permissive- /EHsc`.

`missing-header-red.log` preserves the actual initial C1083 missing-API RED.
`caption-api-red.log` preserves the actual missing-caption-API RED before the
new optional fields were implemented.
`build-release-initial-warning.log` preserves a test initializer-list narrowing
warning promoted to an error; the fixture was corrected with an explicitly
typed array, with no warning suppression or requirement changes.

The synthetic suite exercises source-rate/channel preservation, signed sample
extremes, odd unknown chunks, data-before-fmt, strict RIFF/fmt rejection,
truncation, metadata/UTF8/UUID errors, every single-byte cooked corruption,
rechecksummed semantic corruption, exact48MiB payload acceptance, excess
payload/capacity rejection, byte-exact roundtrip, and failed replacement.
Allocation guards verify malformed ranges/counts and oversized input do not
allocate a large owned PCM vector before admission.

The caption suite includes Unicode/multiline roundtrip, exclusive-end ranges,
valid gaps, forbidden overlap/sorting/out-of-recording cues, empty/NUL/invalid
UTF8, unknown review states, exact2048-cue/256KiB-text boundaries, retained
cue-text capacity, rechecksummed malformed cues and rejection before even a
16KiB PCM allocation when the final caption record is malformed.

Run from this directory with an installed SDK matching the configuration:

```powershell
cmake -S . -B out-release -G 'Visual Studio 17 2022' -A x64 -DCMAKE_PREFIX_PATH=C:/AI-BS/engine/install/0.11.0/release
cmake --build out-release --config Release
ctest --test-dir out-release -C Release --output-on-failure
cmake -S . -B out-debug -G 'Visual Studio 17 2022' -A x64 -DCMAKE_PREFIX_PATH=C:/AI-BS/engine/install/0.11.0/debug
cmake --build out-debug --config Debug
ctest --test-dir out-debug -C Debug --output-on-failure
```

`audio_tests --original WAV REPORT` additionally reads an existing private
reference WAV, checks its known source hash/format/full frame count and the
complete codec roundtrip, then writes only metadata/hashes to `REPORT`. It
never saves PCM, WAV, an encoded family asset, or the original video here.

Verified reference:44100Hz, stereo,16bit,8,684,544frames,
196.92843537414967seconds,34,738,176PCM bytes,34,738,254WAV bytes.
WAV SHA256 `1464299dbe1280b979384f12fc34db1f6626b52ed3d1fb699541cf74082c2a08`.
PCM SHA256 `fd916ec50b31950a36ba46ef511c8c7701fa7ad217e12458d9f69b8f643cdb42`.
Final reports record exact encoded and decoded bytes for the fixed synthetic
UUID/name with empty draft captions. They do not publish a playable family
asset or assert that the actual draft captions were reviewed.

## Current integration and remaining family-media gate

Canonical typed audio catalogs and source-rate PCM loading are implemented.
Audio payloads have a48MiB bound and complete audio packs a50MiB bound; legacy
mesh limits remain unchanged. Complete encoded/decoded dependency closures and
active GPU resources have their separate admission checks under the128MiB
opening profile. AIBD3 memory bindings survive authoring/export/restart, and
native Play/Pause/Stop uses sample-clock state rather than wall-clock captions.
Synthetic muted-device and creator proofs establish those technical scopes.

The cooker optionally accepts `--captions-reviewed` through the explicit review
adapter. It validates the supplied review declarations and bounds; it cannot
certify that somebody actually listened or that the words are correct. Without
that sidecar it produces empty draft captions. The original62-segment family
draft remains unreviewed. Keep the private original-recording candidate unbound
while that review is pending; no final caption or original-playback acceptance
is inferred from synthetic tests or an author declaration.
