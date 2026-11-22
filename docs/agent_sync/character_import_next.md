# Next character import slice — proposal, not implemented

This is implementation preparation against the current native source. The
indexed renderer and temporary figure do not establish GLB import, character
pack loading, likeness or completion of the opening. No dependency, binary,
catalog or source implementation was installed by this reconnaissance.

## Current integration points

- `engine/include/aibs/character_scene.hpp` owns indexed geometry, one
  parent-before-child skeleton, inverse binds and uniformly baked clips. Its
  validator requires `inverse_bind * global_bind == identity`, positive
  nonsingular TRS, at most64 joints and four weights per vertex. Geometry and
  animation data currently have no UUID wrapper, material table or image owner.
- `asset_store.hpp/.cpp` verifies exact four-file packs and immutable
  UUID/payload-SHA/pack-SHA references. Its implementation currently distinguishes
  only v1 mesh and v2 surface. The `legacy_v1` profile retains64MiB encoded
  dependency accounting; explicit `warm_beginning` adds separate128MiB encoded
  and decoded/composed residency accounting.
- `FirstBootCompanionBinding::model` already holds an optional immutable asset
  reference in AIBD3. `FirstBootMemoryBinding::audio` is similarly structural.
  `games/content_authoring.cpp::validate_asset_dependencies` and
  `src/placed_assets.cpp` explicitly reject these currently unimplemented media
  loaders. Do not remove a rejection before its typed replacement validates the
  complete dependency and runtime resource route.
- `native_studio/game_engine/project_assets.py::dependencies_from_rows` currently
  collects only `authoring.AssetPlacement` rows. `content_view.py` pins those
  references into `ContentExportAssembly`; `content_preview.py` and
  `content_play.py` then stage private dependency stores. A model reference hidden
  in AIBD3 would currently be omitted from that Python reference list. The new
  native closure description must include companion models and memory audio.
- `ChapterLive` currently creates the generated placeholder. Its resource
  lifetime already keeps the owned mesh before the borrowing presenter, and old
  renderer scene setters preserve the independently adopted character. Imported
  models should replace that development resource only after complete adoption.

## Pinned parser and dependency ownership

Use cgltf1.15 at commit `360db1a95480fe102ae9c69b27c5d101167ff5ba`.
The official immutable `cgltf.h` was read in memory during reconnaissance:
202865 bytes, SHA256
`e378a21c084bf1f288bb799de827bb26906efb024255f1ecf1705ea13f11c6ec`.
The header declares version1.15 and embeds its MIT notice. On implementation,
retain that full notice in third-party licensing and record this exact pin/hash.
Compile `CGLTF_IMPLEMENTATION` in one private translation unit; the SDK public
headers must expose engine-owned types rather than cgltf pointers.

Use `cgltf_parse` on already bounded memory, then engine count/range checks,
explicit buffer association and `cgltf_validate`. cgltf is a parser, not the
engine's complete asset validator. Its file-loading helpers can resolve external
resources; do not invoke filesystem fallback from the decoder. Install deny-all
file callbacks and use an explicit resource map for a `.gltf` source. Parsing,
accessor unpacking and image decode must all share bounded accounting and unwind
cleanly on failure. Any automatic source/library fetching belongs to the build
dependency setup, never to runtime content loading.

## Proposed owned API

Add `CharacterAssets`, `CharacterImport` and `CharacterCodec` as separate
modules. Keep `CharacterScene` and all existing callers intact.

```cpp
struct CharacterMaterial {
 std::uint32_t albedo_image; // explicit no-image sentinel allowed
 Vec3 base_color{1,1,1};
 float emission=0;
};
struct CharacterDraw {
 std::uint32_t first_index=0,index_count=0,material=0;
};
struct CharacterAsset {
 std::string asset_id,name,source_sha256;
 CharacterMesh mesh;
 std::vector<ImageAsset> images;
 std::vector<CharacterMaterial> materials;
 std::vector<CharacterDraw> draws;
};
struct GltfInputResource {
 std::string_view uri;
 std::span<const std::byte> bytes;
};
struct CharacterClipSelection {
 std::uint32_t source_animation;
 std::string name;
 bool looping=false;
};
struct CharacterImportOptions {
 std::string asset_id,name;
 std::vector<CharacterClipSelection> clips;
 std::uint32_t bake_rate=30; // supported1..60; actual interval is uniform
};
CharacterAsset import_character_gltf(std::span<const std::byte> source,
 std::span<const GltfInputResource> resources,const CharacterImportOptions&);
void validate_character_asset(const CharacterAsset&);
std::vector<std::byte> encode_character_asset(const CharacterAsset&);
CharacterAsset decode_character_asset(std::span<const std::byte>);
```

Input spans are borrowed only for the synchronous import call. The returned
asset owns every retained byte, mip, sample and string; source paths, URI maps,
cgltf nodes and executable extras never escape. The source digest should cover
a canonical manifest of document bytes and every explicitly supplied dependency
URI/length/SHA, not just the JSON file when external buffers were used.

The wrapper, rather than `CharacterMesh`, holds identity/materials/images so the
tested vertex stride, skinning oracle and pose API remain stable. Materials and
index ranges must be completely validated and disjoint, cover the full index
array exactly once, and never hide missing geometry behind an empty draw.

## Deliberately bounded source profile

Implement one selected scene, exactly one skin and one skinned mesh instance
with1..64 triangle primitives/materials. Blender can join body/clothing objects
into that mesh while retaining separate materials. Reject another renderable
mesh instance instead of silently discarding it. Source joints may be in any
array order; a single joint ancestor must root the selected skin tree.

Initially accept:

- Indexed triangle primitives; positions/normals as finite float VEC3;
  JOINTS_0 as unsigned byte/short VEC4; WEIGHTS_0 as float or normalized unsigned
  byte/short VEC4; optional COLOR_0 and TEXCOORD_0 with supported legal accessor
  encodings. Require matching vertex counts and normals. Preserve UV seams by
  retaining distinct primitive vertices rather than position-only deduplication.
- Explicit normalized-weight conversion and deterministic normalization to a
  unit sum when source quantization requires it. Reject negative, nonfinite or
  zero-total weights, values above1, and sums outside the selected encoding's
  quantization envelope: absolute sum error at most `1e-5` for float,
  `2/255 + 1e-7` for UNORM8, or `2/65535 + 1e-7` for UNORM16. Never repair an
  arbitrary malformed distribution by normalizing it. Never drop a fifth
  nonzero influence. Reject JOINTS_1 or
  WEIGHTS_1 in this profile instead of silently truncating them. Record the
  normalization policy in provenance and check the final CPU tolerance.
- No sparse accessors or compressed primitives in this first slice. Dense
  interleaved accessors are supported only after checked stride/offset/alignment
  arithmetic. Enforce component types, normalized flags, triangle divisibility,
  index bounds and exact accessor-unpack return counts independently.
- Static nonsingular node matrices when decomposable where a joint local TRS
  is required; translation/rotation/scale animation using LINEAR interpolation.
  Reject matrix-plus-TRS conflicts, shear that cannot be represented exactly by
  the CPU TRS contract, reflected joint locals and animation targeting a matrix
  node. Reject STEP/CUBICSPLINE with an actionable request to export uniformly
  sampled LINEAR clips. Do not falsely claim arbitrary glTF curve support.
- Opaque base-color materials, linear base-color/vertex-color factors and PNG
  base-color images. Require the deliberately supported diffuse profile
  (metallic0, roughness1); do not silently flatten arbitrary PBR materials.
  Character hologram emission/opacity remains engine presentation data.
  Reject normal/occlusion/metallic-roughness/emissive textures, morph targets,
  alpha-mask/blend materials, unsupported texture transforms, other UV sets,
  skin instancing and unsupported required extensions. These can be added by
  separately tested format/profile changes.
- Linear filtering/repeat sampling only, with explicitly documented defaults;
  reject incompatible requested sampler states. This first texture route is
  base-color support, not a claim of a complete glTF material renderer.

Both GLB2 and `.gltf` JSON may enter the same API. For JSON, every nonembedded
buffer/image must match one exact caller-supplied canonical relative URI; no
network, drive path, `..`, percent-encoded alias, backslash, empty component,
data URI or unprovided fallback is allowed. GLB embedded buffer/image ranges are
still checked before association. Reject unexpected chunks/trailing bytes and
inconsistent declared lengths, allowing only the specified GLB padding.

Proposed import limits: combined source/dependency bytes32MiB, JSON chunk4MiB,
1024 nodes, hierarchy depth64,2048 accessors,4096 buffer views,32 images and
64 materials/primitives. These are import-profile limits, not changes to legacy
assets. A tracked cgltf allocator is capped at64MiB; total import live accounting
(source, parser, output and scratch capacities) is capped at256MiB. Count and
checked-multiply guards must run before reserves/unpacks. Preserve the existing
image decoder's1..4096 dimension/13-mip bounds and pass its remaining budget
before pixel allocation.

The **complete cooked character payload**, including metadata, geometry,
materials, all owned RGBA8 mip chains and baked animation, must fit32MiB. Its
complete decoded charge must fit64MiB. Neither limit is a separate allowance
per image or clip. Preview/Save/Play must additionally charge the deduplicated
encoded closure against128MiB and its decoded/composed CPU residency against
the separate existing128MiB modern limit before publication. GPU admission
additionally charges actual allocations under each renderer resource profile;
it is not measured by the encoded file length. Keep the existing renderer's
32MiB active indexed-character allocation profile: extending character textures
must include their actual allocations and staging/replacement peak in that
profile, not hide them in the static-texture budget. Record the distinct
encoded, decoded/composed and GPU charges and total replacement peak so that
none is mistaken for total process RAM/VRAM measurement.

## Exact coordinate, bind and skeleton conversion

All equations below use **column-vector source math** until the explicit final
transpose. Use double intermediates for import transforms, checked inverses and
decomposition; validate the float result through the current CPU oracle.

Choose `H = diag(-1,1,1,1)` to convert right-handed glTF into the engine's
left-handed coordinates while preserving +Y up and the guide's +Z forward.
Distances remain meters. For a source transform `L`, its engine row-vector
matrix is `(H * L * H)^T`. For directly convertible local TRS this means
translation `(-tx,ty,tz)`, quaternion `(qx,-qy,-qz,qw)`, and unchanged positive
scale. Do not apply these component rules to an already composed sheared matrix.

**Do not multiply a skinned primitive by its instantiating mesh-node transform.**
The glTF skinning result is the weighted sum of `J(t) * IBM * p`; the mesh-node
global transform is absent. A mesh node affects that result only if it actually
lies on a selected joint's ancestor path. A test must vary a nonidentity,
nonancestor mesh node without changing the imported skinned result.

The CPU requires an identity skin palette at its declared bind pose. Support the
coherent-bind subset without assuming that the ignored mesh node is its basis:

1. Compute source joint default global transforms `Jb[j]` from the acyclic node
   hierarchy. Read each source inverse bind `I[j]`; absent inverse binds mean
   identity, not an inferred inverse silently substituted for the source.
2. Calculate `B[j] = Jb[j] * I[j]`. All skin joints must agree on one finite,
   nonsingular affine common bind-shape `B` within a strict documented numeric
   tolerance. Reject incompatible default-pose/inverse-bind combinations with
   an export-rest-pose diagnostic. Arbitrary heterogeneous bind shapes are a
   valid general glTF possibility that this CPU-compatible subset cannot
   approximate safely.
3. Bake each source position with `p_asset = H * B * p`; transform its normal by
   `inverseTranspose(H * B)` and normalize. Flip each triangle's second/third
   indices iff `det(H * B) < 0`, rather than assuming every source transform has
   positive determinant. Source UV(0,0) and the WIC image origin are both upper
   left; no unconditional V flip is needed.
4. Convert each joint's inverse bind to
   `I_asset[j] = (H * I[j] * inverse(B) * H)^T`.
   Convert a source animated joint global to
   `G_asset[j](t) = (H * J[j](t) * H)^T`.
   The engine skin is `I_asset * G_asset`. At bind it is identity, and for any
   weighted pose, applying it to the baked vertex gives exactly the converted
   glTF `sum(w * J(t) * I * p)` result before ordinary float rounding. Normals
   use the existing per-bone inverse-transpose CPU convention, including its
   relative-cancellation rule.
5. Produce a deterministic parent-before-child joint order (original node index
   breaks ties), retaining a source skin-index→cooked-index table. JOINTS_0
   addresses the source skin array, **not source node indices**. Remap all four
   slots, inverse binds, bind locals and every clip sample consistently.
6. Nonjoint helper nodes between joints are not discarded. For a joint and its
   nearest joint parent, compute the effective local column matrix as
   `inverse(J_parent(t)) * J_joint(t)`, or `J_root(t)` for the one root, including
   all relevant ancestors/helpers. Decompose each bind/baked matrix into a
   positive TRS and verify reconstruction with bounded error. If a composition
   produces shear/reflection outside the CPU contract, reject it; do not use an
   approximate rotation/scale fit. Negative/sheared mesh-node transforms that
   are not joint ancestors remain irrelevant to skinning.

Use tolerance relative to bounded matrix magnitude with an absolute floor;
e.g. reconstructed matrix component error at most
`2e-6 * max(1,maxAbs(original))`, followed by the unchanged CPU inverse-bind
identity check (`5e-4`) and all existing scale/affine limits. The independent
test oracle must use original source globals and inverse binds, never simply
repeat the import helper being tested.

## Uniform clip timing and in-place policy

Clip selection and cooked names/looping are explicit import options; glTF names
need not be unique and glTF does not declare looping. Preserve caller-selected
ordering for the existing presenter's `idle`, `walk`, `catchup`, `guidance`
slots. Do not guess a clip by substring or reinterpret the podium video as
motion capture.

For each selected animation, use source time0 as the beginning. Its duration is
the greatest selected channel key time, **not last-minus-earliest time**. Clamp
an individual channel outside its own key range. A first key at10seconds must
remain held from0..10 rather than shift the whole clip to0. Missing TRS channels
use that node's defaults. Reject duplicate node/path targets, nonfinite or
nonincreasing key times, mismatched key counts and unsupported interpolation.
Interpolate source rotations along the shortest quaternion arc and normalize.

For positive duration `T` and requested rate `R`, choose
`N = ceil(T*R)+1` and sample exactly at `k*T/(N-1)` for `k=0..N-1`.
This is truly uniform and includes both endpoints; reject `N>4096` or more than
eight clips before allocation. A source animation with no positive duration
needs an explicit static-clip duration option or must be rejected; do not invent
a nonzero duration silently. Each sampled local matrix is converted as above
and stored as owned frame-major TRS. Baking approximates the source between
sample instants; the contract promises exact source evaluation at bake samples,
not arbitrary analytic curve equivalence at every possible time.

The cooked root translation must equal its declared bind translation at every
sample under the existing strict CPU in-place rule. Reject root travel rather
than silently stripping motion or letting a synthetic stationary root disguise
travel in the actual skeleton root. Record the selected root/index map in
provenance. Looping clips must have compatible first/last poses (quaternion
sign-equivalent rotations count as equal); otherwise report the seam for
authoring correction. Nonlooping guidance clamps and holds its last pose.

## Typed pack, closure and strong rollback route

Propose an `AIBChar2` canonical little-endian payload and a `.aibchar` extension.
Its checksummed framing must include the wrapper identity, metadata, mesh,
indexed material ranges, images with complete mip chains and animation samples.
Canonicalize signed zero on encode and reject noncanonical encodings on decode,
as the existing codecs do. Reject unknown versions, excessive lengths/counts,
invalid UTF-8/names, checksum mismatch and trailing bytes before publication.
All length multiplication/addition needs checked arithmetic before allocation.

Retain the exact four-file layout:

```text
catalog.aibcat
<payload-sha256>.aibchar
LICENSE.txt
provenance.json
```

The catalog row becomes `AIBCAT 2\ncharacter <UUID> <SHA> <SHA>.aibchar\n`.
Its pack identity uses the existing sorted four-file `AIBPACK 2` manifest scheme.
Extend the internal kind discriminator to an explicit enum; do not infer
"not surface" means legacy mesh. UUID, payload digest, filename suffix, catalog
kind and decoded payload kind must all agree. v1 and existing surface wire bytes
remain unchanged. License/provenance retains bounded UTF-8 checks and records
cgltf pin, source-manifest digest, conversion basis, bind policy, joint map,
bake rate/actual intervals, clip selections and normalization policy.
Keep original family photographs/video, private source paths and private
reference annotations outside distributable packs. Their private archival
provenance can point to the derived model separately; a cooked character pack
must not bundle those original references merely to describe the model.

Add typed inspect/load APIs without widening `StoredVisualAsset` into an unsafe
"everything is scenery" path. For example `inspect_asset_pack` may return an
explicit kind and a typed variant, while `load_stored_character_asset` returns
only `CharacterAsset`; existing visual/legacy loaders keep rejecting foreign
kinds. `stage_asset_packs` should verify/copy typed character packs only under
`warm_beginning` and charge their complete encoded/decoded/resident closure.
Keep audio rejected until its real decoder arrives.

Add a native dependency collector over the complete immutable
`FirstBootContent`: placements, optional companion model and optional audio,
deduplicated by verified reference/kind. Expose that closure with the pinned
native content export or another versioned native command; Python must not
reconstruct a partial closure from visible placement rows. Bind the closure
receipt to definition UUID/fingerprint/revision and recheck it before scratch
publication. Copy it through Preview, Save and isolated Play using the existing
private-store lifecycle. Existing packs are never rewritten; failed staging
may leave an unused verified immutable child but never a partial final snapshot.

Native presentation should stage all CPU dependencies and the four-layer GPU
transaction before admitting a new creator snapshot. Change the logical head
only after dependency validation and render staging succeed. Preserve old
resources and the previous character on rejection. Do not serialize animation
frames, bone matrices, footsteps or cached render resources into saves. Model
binding changes require the existing compatible new Play branch; placement edits
must preserve AIBD3 companion/light/media bindings and never downgrade content.
Imported scenery still uses explicit collision proxies; the character renderer
does not become BS collision geometry.

The new character-image path needs owned SRVs/indexed material draws in the
dedicated renderer, staged atomically with its mesh. The current vertex-colored
`set_character(CharacterMesh)` overload remains available. Actual image
color-space/UV/readback tests are required before declaring textured-character
support; merely retaining embedded image bytes is insufficient.

## RED fixtures and next executable step

Begin by registering a small generated in-memory GLB fixture/test against the
new import API and verify the actual missing-API RED before implementation.
Use synthetic data, not family originals, for malformed/failure tests.

Required fixtures include:

1. Asymmetric four-weight/joint63 skin, shuffled skin order, nonidentity binds,
   static helper ancestors and a coherent nonidentity common `B`. Compare every
   sampled joint/selected deformed vertex and normal with an independent double
   source oracle. Apply nonidentity world placement and compare actual GPU
   readback, not just catalog checks.
2. Change a nonancestor mesh node's translation, rotation, scale and negative
   determinant without changing the skinned result. Separately animate a real
   joint ancestor and require the result to change. Catch accidental mesh-node
   multiplication, forgotten transpose, wrong handedness and wrong index map.
3. A UV checker with distinct corners and duplicated seam positions, an sRGB
   albedo test and normal-transform test; verify complete mip ownership after
   original buffers/parser are destroyed. Exercise multiple indexed materials.
4. Late-first-key time, mismatched channel ranges, shortest-arc rotations, exact
   final sample, looping seam, nonlooping clamp, root-motion rejection and
   frame/clip budget boundaries. Reject unsupported interpolation honestly.
5. Truncated/oversized GLB chunks, invalid JSON/counts/strides/ranges/indices,
   cycles/multiple parents, invalid quaternion, shear/singular/reflected joint
   local, incoherent `B`, NaN/Inf, zero weights, fifth influence, sparse accessors,
   unsupported required extensions and image decompression bombs. Exercise
   allocator exhaustion without a crash or leaked parsed owner.
6. Wrong-kind catalog, altered payload/image/animation, UUID/digest/suffix
   mismatch, malformed dependency closure and a corrupt immutable child.
   Confirm failed replacement keeps actual old GPU pixels and all logical heads.
7. Character dependency survives placement edit, Undo/Redo, Save, project close,
   original source removal and isolated Preview/Play/restart. Preserve v1/v2
   golden bytes, AIBD1/2 readers and AIBD3 monotonic bindings. Verify the installed
   SDK consumes the owned importer/codec rather than reaching into source paths.

Only after those pass should the Blender-generated authored Adam model use this
route. Close-up/full-body likeness previews and family feedback remain their
own acceptance step; imported geometry does not imply a recognizable likeness.

Primary material inspected:

- [Pinned cgltf1.15 header](https://raw.githubusercontent.com/jkuhlmann/cgltf/360db1a95480fe102ae9c69b27c5d101167ff5ba/cgltf.h)
- [Pinned cgltf usage notes](https://raw.githubusercontent.com/jkuhlmann/cgltf/360db1a95480fe102ae9c69b27c5d101167ff5ba/README.md)
- [Khronos glTF2 specification source](https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/Specification.adoc)

The common-bind conversion, bounded profile and API above are proposed engine
decisions derived from those source semantics and the existing CPU invariant.
They are not a statement that all legal glTF assets are supported.
