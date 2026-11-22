# Bounded character source import

`AIBS::CharacterImport` exposes `aibs/character_import.hpp` and returns an owned
`CharacterAsset`. It privately compiles cgltf1.15 from commit
`360db1a95480fe102ae9c69b27c5d101167ff5ba`. The vendored202865-byte header has
SHA256 `e378a21c084bf1f288bb799de827bb26906efb024255f1ecf1705ea13f11c6ec`;
`cmake/CgltfDependency.cmake` verifies these bytes. Its full MIT notice is retained
and installed separately. No cgltf pointers/types appear in public SDK headers.

```cpp
CharacterImportDiagnostics diagnostics;
CharacterImportOptions options;
options.asset_id = new_uuid();
options.name = "Derived guide model";
options.clips = {{0,"idle",true},{1,"walk",true},
                 {2,"catchup",true},{3,"guidance",false}};
auto asset = import_character_gltf(source_bytes, supplied_resources,
                                   options, &diagnostics);
```

Clip indices/names/order/looping are explicit. A static generic character can
select no clips; that does not make it compatible with Adam's four-slot
`GuidePresentation`. Companion binding publication must check that presentation
contract separately. Imported scene detail does not add BS collision geometry.

## Source profile and ownership

The importer accepts GLB2 or glTF2.0 JSON. Both are synchronous memory inputs;
all retained strings, geometry, image/mip bytes and baked samples are owned by
the result. It never calls cgltf's filesystem/buffer-loading helpers. Deny-all
file callbacks remain installed. JSON external buffers/images must match exact
caller-supplied relative ASCII URIs using unreserved characters and `/`.
Duplicate/undeclared resources, absolute/drive/network paths, backslashes,
percent aliases, `.`/`..`, empty path components and data URIs reject. GLB uses
embedded BIN/image buffer views only. Unknown/reordered chunks, inconsistent
lengths, trailing chunks/bytes and nonzero BIN padding reject.

The source SHA is SHA256 of a canonical `AIBS_GLTF_SOURCE 1` manifest containing
the original document length/SHA and sorted URI/length/SHA records for every
supplied resource. It is not merely a hash of JSON that ignores external data.
The returned asset contains no URI map, borrowed input span or source path.

One selected default scene contains exactly one skinned mesh instance and one
skin with1..64 joints. Multiple scenes need an explicit glTF default. The joint
array may be shuffled and may contain static/animated helper ancestors. The
selected skin must have one actual joint ancestor root. A supplied skeleton
hint must be a common ancestor. Cycles, repeated children/multiple parents,
duplicate joints and unsupported scene instancing reject.

Supported geometry is indexed triangles with float POSITION/NORMAL, unsigned
byte/short JOINTS_0 and float or normalized unsigned byte/short WEIGHTS_0.
Optional TEXCOORD_0 and COLOR_0 use the documented float/normalized encodings.
Other attribute sets, additional influences, sparse accessors, morph targets,
compressed geometry and unsupported extensions reject. Dense interleaved vertex
attributes preserve primitive vertices/UV seams, require4-byte alignment and an
explicit shared-view stride. Index, image, inverse-bind and animation data cannot
claim a vertex byteStride. Counts, arithmetic, accessor bounds and position
min/max against actual binary values are checked before publication.

Weight sums are range-checked before deterministic normalization: absolute
source error at most1e-5 for floats, `2/255 + 1e-7` for UNORM8, or
`2/65535 + 1e-7` for UNORM16. Negative/nonfinite/zero-total distributions and
out-of-range joints reject; a malformed distribution is not silently repaired.

Materials retain RGB factors and single/double-sided flags. SDK0.17.0 supports
opaque base color with metallic0 and finite scalar roughness in0.04..1, PNG
sRGB albedo and linear mip filtering/repeat sampling. Roughness1 retains the
legacy diffuse behavior; lower values opt into the qualified direct-light
surface response. Roughness maps and other PBR/normal/emissive/occlusion textures,
texture transforms, alpha modes, image encodings and requested samplers reject.
OPAQUE source alpha factors, vertex alpha and PNG alpha have no visual effect.
PNG base RGB is preserved, base alpha becomes255, then the final sRGB mip chain
is regenerated in linear light. This avoids hidden PNG alpha darkening the
opaque texture during premultiplied mip generation. Material/vertex RGB stay
separate; coincident positions across primitives are not deduplicated away.

## Exact transforms and animation

Source calculations use double column-vector matrices. The coordinate basis is
`H=diag(-1,1,1,1)`; engine matrices are explicitly transposed row-vector values.
The instantiating mesh-node transform is ignored for skinning, as glTF requires,
unless that node actually lies on a selected joint's ancestor path.

For source default joint globals `Jb[j]` and supplied inverse binds `I[j]`, all
`B[j]=Jb[j]*I[j]` must agree on one nonsingular common bind shape. Absent inverse
binds mean identity. The importer does not invent inverses to reinterpret a
different source asset. Incoherent bind shapes request an export rest-pose fix.

Positions are baked with `H*B`; normals use its inverse transpose. Winding flips
iff `det(H*B)<0`, including reflected bind shapes. Cooked inverse binds are
`(H*I[j]*inverse(B)*H)^T`. Joint locals include every helper ancestor between
the joint and its nearest joint parent. Deterministic parent-before-child order
uses source node index to break ties and remaps every vertex slot, inverse bind,
bind local and baked sample. Converted matrices must reconstruct through positive
TRS without shear/reflection loss and pass the unchanged CPU identity-bind checks.
The normal convention is the existing per-bone inverse-transpose engine oracle.

Selected translation/rotation/scale channels must use LINEAR interpolation.
Duplicate targets, animation on matrix nodes, unsupported interpolation and
invalid/nonincreasing times reject. Missing channels use defaults; values clamp
outside an individual channel's key range. Duration is the greatest selected
channel key time, measured from source time0. A late first key is held before its
time rather than shifting the whole animation backward.

At requested rate `R` and positive duration `T`, `N=ceil(T*R)+1` uniform samples
are baked at `k*T/(N-1)`, including both endpoints. Rotations use shortest-arc
quaternion interpolation. The contract promises source-equivalent bake samples;
the uniformly sampled runtime is not an analytic guarantee between those samples.
Root translation must exactly match its declared bind translation at every
sample. Root travel is rejected, not stripped or hidden under a synthetic root.
Looping first/last TRS components must agree within absolute1e-5; quaternion signs
are equivalent. Nonlooping guidance clamps through the existing sampler.

## Budgets, diagnostics and failure behavior

- Combined document and supplied dependency bytes:32MiB; JSON chunk/document:4MiB.
- At most1024 nodes/depth64,2048 accessors,4096 buffer views,64 buffers,
  64 scenes/meshes/materials/primitives,32 images and64 textures/samplers.
- At most8 selected clips,4096 baked frames/clip,60Hz requested bake rate,
  262144 source keys/channel,3072 channels/samplers/animation and32MiB cached key
  times. The existing complete cooked32MiB and decoded64MiB asset costs also apply.
- Private cgltf allocations, including allocation headers, are capped at64MiB.
  Actual aggregate live parser bytes are observable through
  `character_import_live_parser_bytes()`. Engine-owned source/parser/output/scratch
  accounting is checked against256MiB before bounded reserves/decodes and before
  publication. This is not a measured whole-process/WIC/driver RAM limit.

Optional diagnostics contain the per-call parser peak, a conservative
`engine_owned_live_upper_bound_bytes`, the owned `source_skin_to_cooked` index
map and `baked_intervals_seconds`. They publish only after all validation and
parser release succeed. A rejected import, including parser exhaustion, preserves
the caller's previous diagnostics. No gameplay state, save, file or GPU resource
is modified by this function. Typed cooking/staging, creator publication and GPU
adoption remain separate strong transactions.

## Actual isolated verification

`tests/fixtures/generate_character_import.py` generates synthetic source assets
and a separate original-source double-precision `J(t)*IBM` oracle. It uses no
family media, Blender installation, network or third-party Python library.
Release and Debug standalone MSVC C++20 builds each pass399 checks with
`/W4 /WX /permissive- /EHsc` at this source checkpoint. They cover shuffled64-joint
skins/joint63/four weights, nonidentity common bind and helper animation,
ignored reflected mesh transforms, source-space normal/position comparisons
after nonidentity world placement, reflected-bind winding, exact4096-frame
baking, late-first keys, quaternion-sign loop seams, UV/material ownership,
opaque-alpha sRGB mips, interleaved input and quantized weights.

Malformed cases include chunks, padding, indices/strides/ranges/bounds,
cycles/multiple parents, source transforms, material/sampler/image profiles,
unsafe URI aliases, duplicate JSON properties, escaped NULs, root motion,
loop seams and actual64MiB parser allocator exhaustion. Every rejection checks
the real live parser-byte counter returns to0; successful diagnostics and
failed-output rollback are checked too. Missing-header RED, illegal animation
stride RED, small loop seam RED and position-bound mismatch RED are retained.

Evidence is under `engine/out/warm_beginning/character-import-cpu`; the original
isolated build is `D:/AI-BS-Game-Resources/Develop/character-import`.
Root central SDK, cooker, store, renderer, creator and packaged proofs are
recorded separately; these importer tests do not claim that those paths pass,
or that Adam's likeness/the complete opening is finished.

Primary references: [pinned cgltf header](https://raw.githubusercontent.com/jkuhlmann/cgltf/360db1a95480fe102ae9c69b27c5d101167ff5ba/cgltf.h)
and [Khronos glTF2 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html).
