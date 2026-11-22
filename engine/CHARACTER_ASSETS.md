# Owned character assets and AIBChar2 payload versions2/3

`CharacterAssets` wraps the tested indexed `CharacterMesh` with an immutable
asset UUID, display name, source digest, owned images, material factors and
indexed draw ranges. `CharacterCodec` reads and writes those complete values;
it never resolves a path, URI, file, network resource or executable extension.
The modules do not change `CharacterMesh`, its72-byte vertex layout, pose
sampling or the CPU skinning oracle.

The public headers are `aibs/character_assets.hpp` and
`aibs/character_codec.hpp`. `CharacterAssets` links the existing CPU character,
image and Core UUID facilities. `CharacterCodec` uses a private BCrypt SHA-256
implementation and does not link the scene/asset renderer, avoiding a dependency
cycle when the renderer consumes owned character materials.

## Identity, materials and ownership

Asset identity is a canonical lowercase version4 UUID. Source identity is a
64-character lowercase SHA-256 string. This field records source provenance;
the binary codec separately verifies its own actual payload checksum. Display
names are nonempty valid UTF-8, at most128 bytes, without ASCII controls. Cooked
clip names use the same text policy with a64-byte maximum.

At most32 images,64 materials and64 draws are retained. Each material has an
optional owned sRGB albedo image, linear RGB base-color factors in0..1,
emission in0..16 and explicit `double_sided` state. `character_no_image` is the
only no-image sentinel. A default material remains double-sided for the existing
vertex-colored guide behavior; a glTF importer can preserve an authored false
value instead of silently changing culling.

SDK0.17.0 also retains finite scalar `roughness` in0.04..1. Its default1
preserves legacy diffuse rendering and the original inner payload version2.
When any material has nondefault roughness, the encoder selects inner payload
version3 and appends one float to every material record. The outer typed
`character_v2` pack kind and AIBChar2 magic remain unchanged. Rebuild C++
consumers for the expanded public `CharacterMaterial`; ABI compatibility with
older headers/libraries is not asserted.

Every owned image has a complete validated RGBA8 mip chain and alpha255 in every
pixel at every level. The source importer must apply the glTF OPAQUE policy
before mip generation. The hologram's opacity belongs to `CharacterInstance`,
not hidden texture alpha. A normal/data image cannot be bound as albedo. Unused
owned images/materials are retained and charged rather than silently discarded.

Draw ranges are ordered and contiguous: the first starts at index0, each
positive triangle-multiple count begins at the prior range's end, and the last
ends at the complete index count. Every material index is valid. Gaps,
overlaps, omitted triangles and trailing hidden geometry are rejected.

## Independent budgets

The complete cooked payload is at most32MiB, including the48-byte header,
metadata, geometry, skeleton, all baked animation samples, materials, draws and
every mip byte. `character_asset_cost().payload_bytes` is the exact canonical
wire charge for the current format, and encoding verifies it against the actual
output length. Decoding independently bounds the complete input length before
hashing or reading its body. Existing conservative `CharacterMesh` validation
and its32MiB subresource profile remain in force.

Decoded owned storage is separately limited to64MiB. Its charge includes
container objects, actual vector capacities, string capacities and all pixel
and animation capacity. A large unused reserve is not free. The cost API also
reports logical image, animation, indexed VB and IB bytes. It does not report
actual D3D allocation alignment, driver RAM, physical VRAM or whole-process peak
memory; GPU and dependency-closure admission remain separate owners.

## Canonical wire format

All integers are little-endian. Floats use IEEE754 binary32. Encoding maps
negative zero to positive zero. Decoding rejects nonfinite values and negative
zero in every scalar field before publication.

The48-byte header contains:

| Bytes | Value |
| --- | --- |
|8|`AIBChar2` magic|
|4|version2 for all-default roughness, otherwise version3|
|4|exact body length|
|32|SHA-256 of the complete body|

The body has three `u32 length + UTF-8 bytes` identity/name/source strings,
followed by eight u32 values: vertex, index, joint, clip, image, material and
draw counts, then zero reserved flags. The arrays follow in that order.

- Vertices occupy72 bytes: position3f, normal3f, color3f, emission1f, UV2f,
  four u16 joint indices and four float weights. Indices are u32.
- Joints occupy108 bytes: i32 parent encoded as u32,40-byte local TRS and a
 64-byte inverse-bind matrix. Root parent is `0xffffffff`; all other parents
  precede their children.
- Clips contain a length-prefixed name, duration float, frame count, looping0/1,
  zero reserved word and exactly `frame_count * joint_count`40-byte local TRS
  samples. Root translation remains in place, as required by `CharacterScene`.
- Images contain semantic, mip count and zero reserved word. Each mip contains
  width, height, exact RGBA byte count, zero reserved word, then complete pixels.
- Version2 materials occupy24 bytes: albedo-image u32,3f base color,1f emission
  and a canonical u32 `double_sided` value0/1. Their roughness decodes as1.
  Version3 materials occupy28 bytes, appending finite roughness in0.04..1.
  Other sidedness values and invalid roughness are rejected.
- Draws occupy12 bytes: first index, index count and material index as u32.

The reader checks the checksum, then scans the complete body without creating
owned arrays. This pass checks counts, ranges, exact scalar encodings, mip
chains, opacity, decoded charges and body exhaustion. Only after that complete
preflight succeeds does a second pass reserve and copy owned data. Final
`validate_character_asset` also enforces the unchanged hierarchy, inverse-bind,
animation and skinning contracts. Exceptions return no partially decoded asset
and mutate no caller data. Versions other than2/3, reserved flags and trailing bytes
are rejected.

## Verified scope

An isolated MSVC C++20 project under
`D:/AI-BS-Game-Resources/workshop/character-assets-test` retained the actual
missing-header RED and missing-codec-symbol RED. Release and Debug each passed
65 asset checks and2087 codec checks. Tests cover malformed identities and text,
aggregate32MiB versus separate64MiB capacity limits, image alpha/mip/semantic
contracts, draw coverage, actual animated CPU skinning after roundtrip,
sidedness, every single-byte corruption and every truncation of the fixture,
re-signed semantic malformations, negative-zero families, reserved fields,
trailing data and source-buffer destruction.

A forged large vertex count was rejected with0 bytes observed through the
test's C++ allocation hook. That is a scoped preflight assertion, not a claim
that every decoder call or the BCrypt provider allocates no memory. Initial
compile diagnostics and a test fixture that accidentally retained an earlier
large string capacity remain in the evidence; the test was corrected to use a
fresh value without weakening the capacity budget.

Evidence is copied under
`engine/out/warm_beginning/character-assets-codec-cpu/verification.json`.
Central CMake/SDK registration, typed store staging, importer behavior, GPU
materials and the final opening are verified by their respective integration
owners. These CPU results alone do not establish Adam likeness or packaged
game completion. No family reference files were used.
