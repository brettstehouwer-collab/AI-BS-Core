# Next character renderer slice — proposed, not implemented

Read-only renderer review of the now-tested CPU CharacterScene contract. Keep
`character_rendered:false` until actual native indexed drawing/readback passes.

Proposed API additions preserve existing overloads:

```cpp
void set_character(const CharacterMesh&);
void clear_character();
void render(const Camera&, const SceneMesh& transient, const CharacterInstance&);
void set_scene(const SceneMesh&, const TexturedScene&, const SceneLighting&,
               const CharacterMesh*); // explicit whole-resource transaction
```

Existing render overloads draw no character. Existing scene setters preserve
the separately owned character; the four-input transaction explicitly replaces
or clears it. Validate a pose before mapping, resizing or recording commands.

- Dedicated default-heap indexed geometry, stride72: position0, normal12,
  color24, emission36, UV40, u16 joint indices48, float weights56.
- Two fixed frame-fenced character CBs. Proposed explicit layout:64 skin plus64
  normal matrices, world/world-normal, tint/emission and opacity/joint controls;
  8,352 bytes rounded to8,448. Never memcpy the CPU palette as an implicit wire
  layout. Link Render publicly to CharacterScene; compile/install a shader pair.
- Separate root signature/PSOs can bind camera constants, character CB, existing
  lighting CB and shadow SRV. Rebind the current lighting descriptor heap after
  textured drawing. Keep root-signature cost within the documented limit.
- Charge actual GPU allocations and upload staging before publication. Geometry
  bounds are18MiB VB plus6MiB IB; a32MiB active GPU profile includes fixed pose
  resources. Report replacement peak separately because old/new/staging coexist.
- Match CPU row-vector skinning exactly: blend bone XYZ, then apply world with
  w=1. Weight tolerance means carrying blended homogeneous W would incorrectly
  scale world translation. Blend per-bone inverse-transpose normals; use the
  relative cancellation fallback and scale-safe final normalization.
  The CPU oracle also bounds intermediate/output vector conversion to1e12;
  instance validation alone does not inspect every transformed vertex. Stage
  conservative geometry/influence bounds and reject a GPU pose outside those
  oracle bounds before changing the frame. Do not accept geometry that only the
  shader can evaluate while its CPU reference rejects it.
- Adam does not enter the directional shadow pass. Draw the depth-tested steady
  hologram after opaque/textured scenery. Proposed nearest-surface depth prepass
  and EQUAL-depth alpha pass prevent overlapping limbs accumulating brightness.
  Revisit this last-transparent-slot policy when adding other transparency.
- Preserve existing world RTV behavior. For correct linear alpha blending, the
  character pass can use an sRGB RTV view with linear tone-mapped RGB output;
  blending already encoded colors into UNORM would be incorrect. His emission
  does not imply a dynamic point light or per-frame `set_lighting` calls.
- Upload/submission ownership retains VB/IB, staging, allocator and list through
  existing SubmissionLifetime poison/quarantine rules. Replacement/clear drains
  once; ordinary poses never allocate, drain or rebuild static scenery.

Begin with GPU fixtures: asymmetric/nonidentity binds; four unequal weights and
joint63; nonuniform bone/world scales; sums just above/below1 with world
translation; cancelling/large normals; two actual sampled animation times;
opacity0/.5/1 and a linear blend oracle; closed-door occlusion; unchanged shadow
map with/without Adam; stable allocations/replacements/idles during pose frames;
bad mesh/pose/joint-transaction rollback; clear/recreate and resize/minimize.

Primary API references supplied by the review:

- https://learn.microsoft.com/en-us/windows/win32/direct3d12/root-signature-limits
- https://learn.microsoft.com/en-us/windows/win32/direct3d11/d3d10-graphics-programming-guide-output-merger-stage

This is explicit engineering rationale for the next implementation, not GPU,
animation, authored-likeness or whole-opening completion evidence.
