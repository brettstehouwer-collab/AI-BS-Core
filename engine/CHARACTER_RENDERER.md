# Indexed character rendering

This source SDK adds a dedicated, owned indexed character path to the native
DX12 renderer. It renders an adopted `CharacterMesh` with a transient
`CharacterInstance` pose. It does not add a GLB decoder, character pack codec,
Adam likeness, voice synthesis or general transparency system.

## API and publication

```cpp
renderer.set_character(mesh);
renderer.render(camera, transient_geometry, instance);
renderer.clear_character();
renderer.set_scene(base, textured, lighting, &mesh);
renderer.set_scene(base, textured, lighting, nullptr); // explicit clear
```

The old `render(camera)` and `render(camera, transient)` overloads draw no
character. The existing scene, texture and lighting setters preserve the
separately adopted character. The four-input `set_scene` stages all four layers
and publishes them together after validation and synchronization; its null
character pointer clears that layer explicitly. A rejected input preserves the
previous base geometry, texture resources, lights and character.

`set_character` validates the complete mesh before allocating resources. The
renderer keeps a copy of its skeleton and a conservative source-position
envelope; it does not retain borrowed pointers to the input vertices or clips.
The caller owns the animation library and supplies sampled poses. A character
instance without an adopted resource is rejected, including opacity-zero
instances. An opacity-zero valid instance draws nothing and leaves world depth
unchanged. A minimized window still validates a supplied pose but submits no
frame.

## Geometry, constants and frame lifetime

The vertex layout is explicitly checked: 72 bytes, with position at0, normal
at12, linear albedo at24, emission at36, UV at40, four `uint16_t` joint indices
at48 and four floating weights at56. Indices are `uint32_t`. The dedicated
default-heap vertex and index buffers use `DrawIndexedInstanced`; character
vertices never consume the4096-vertex transient allocation.

Each adopted resource has two fixed upload-heap constant buffers, one per
swapchain frame. Its matching frame fence must complete before a buffer is
mapped. The current SDK0.17.0 explicit8368-byte constant layout contains64 skin
matrices,64 normal matrices, world/world-normal matrices, tint/emission,
controls and camera world position for the direct-light surface response;
the committed buffer width is8448 bytes to respect256-byte CB alignment.
Ordinary poses do not replace geometry, allocate buffers, rebuild static scenery
or call a full queue idle. They update only the selected frame's constants.

Default vertex/index buffers are created in `COMMON`, transitioned explicitly
to `COPY_DEST`, uploaded, and transitioned to vertex/index access. Requesting
`COPY_DEST` as the creation state produced observed DX12 warning1328 on the
current runtime because buffer creation effectively uses `COMMON`. The fix
changes the state sequence; it does not suppress the warning.

Upload work uses the existing `SubmissionLifetime` owner. Both default
resources, both fixed constants, staging buffers, command allocator and command
list remain retained through submission and a failed signal/wait. A failed
synchronization poisons the renderer. Its owner is quarantined until fence
completion or device removal proves release safe. Failure never permits early
release of submitted resources. This is an ownership contract; device-failure
injection is not claimed by the normal GPU readback test.

## Accounting and limits

The CPU `CharacterScene` limits remain unchanged: at most64 joints, four weights
per vertex,262144 vertices,1572864 indices, eight clips and4096 frames per clip,
with32MiB canonical payload and64MiB decoded-storage bounds.

The renderer independently obtains committed allocation sizes with
`GetResourceAllocationInfo`. Active character resources, including the two
aligned constant allocations, must total at most32MiB. Replacement accounting
includes the previous active resources, the staged replacement and both upload
allocations; its separate hard ceiling is96MiB. These are resource allocation
charges, not measurements of driver paging or total process VRAM consumption.
World textures, directional shadows, swapchain/depth surfaces and pipeline
metadata have separate ownership and are not relabeled as character bytes.

`RenderStats` exposes:

- `character_replacements`: completed explicit character publications,
  including clears and the four-layer transaction.
- `character_buffer_allocations`: cumulative adopted vertex/index plus two
  constant buffers; temporary upload buffers are included in replacement-byte
  accounting rather than this adopted-buffer counter.
- `character_frames`: frames that submit visible, nonzero-opacity character
  drawing.
- `character_active_gpu_bytes`: the current adopted resource allocation charge.
- `character_replacement_peak_gpu_bytes`: the largest staged old/new/upload
  replacement charge observed.

Counters do not stand in for image evidence. Tests inspect both actual GPU
readbacks and resource stability across ordinary animated frames.

## Skinning and finite envelopes

Matrices follow the CPU row-vector contract: local times parent-global,
inverse-bind times current-global. The shader blends transformed XYZ positions
and then applies the world matrix as a point with W=1. A weight sum accepted
within the CPU tolerance must not scale world translation through homogeneous
W. Per-bone inverse-transpose normal transforms are blended separately.

The relative cancellation test falls back to the bind normal before the world
normal transform. Scale-safe lengths and normalization avoid squaring very
large post-transform normals. Tint multiplies linear vertex albedo; instance
emission adds to vertex emission.

Before a visible frame can resize surfaces, map constants or record commands,
the renderer validates the pose, appearance, world transform and actual camera
view/projection matrix. It propagates a conservative absolute source envelope
through all skin matrices, the world transform and all four clip components.
Nonfinite matrices or envelopes above `FLT_MAX/64` are rejected. This bounded
GPU profile intentionally leaves arithmetic headroom; it does not impose a
mistaken1e12 vertex-output bound on the CPU oracle. The CPU matrix-entry bound
and CPU vector conversion rules remain authoritative and unchanged.

## Hologram depth, lighting and blending

The character is drawn after opaque base, transient and textured scenery.
It respects their depth. A depth-only nearest-surface pass precedes an
EQUAL-depth color pass, preventing farther body surfaces from accumulating
brightness behind the nearest surface. It is deliberately the last transparent
slot and is not general order-independent transparency; exactly coincident
duplicate triangles are not deduplicated by this policy.

The color pass uses an sRGB RTV view of the existing presentation buffer.
Existing authored lighting returns encoded presentation RGB, so the character
shader decodes that result before hardware linear alpha blending. The sRGB
view decodes the destination, blends in linear space, and encodes the stored
result. The older UNORM scene passes retain their original behavior. The
lighting-disabled character branch preserves the legacy light/emission style.

The character samples the current authored lights and directional shadow, but
does not enter the directional shadow-caster pass. Emission does not silently
create a moving point light or trigger per-frame `set_lighting` calls.

The root signature uses21 DWORDs:16 camera constants, two2-DWORD CBVs and one
1-DWORD shadow descriptor table. This stays below the documented64-DWORD limit.

## Diagnostics and verification

`RenderStats::debug_messages` retains up to32 warning/error/corruption excerpts,
each at most2048 description bytes with the message ID. Severity counters still
count every retrieved message; this bounded diagnostic view does not filter,
dismiss or reduce those counters.

`tests/character_gpu_tests.cpp` compares real indexed GPU output with independently
CPU-skinned geometry under the same lighting. Fixtures cover asymmetric and
nonidentity transforms, joint63/four unequal weights, near-one weight sums with
amplified translation, normal cancellation/large normal magnitudes, two actual
animation samples, linear-alpha composition, nearest/rear body surfaces,
static/transient/textured door occlusion, exclusion from world shadow casting,
transaction rollback, resource stability, clear/recreate and minimize/resize.
A verified RED case demonstrated that an enormous finite camera could submit a
nonfinite projection; the new projection envelope rejects that case before a
frame changes. Final root regression results are recorded separately after
the current full verification run completes; this document does not declare
that in-flight run passed.

Primary API references checked during implementation:

- [Root signature limits](https://learn.microsoft.com/en-us/windows/win32/direct3d12/root-signature-limits)
- [Output-merger depth and sRGB blending](https://learn.microsoft.com/en-us/windows/win32/direct3d11/d3d10-graphics-programming-guide-output-merger-stage)
- [Resource states and buffer promotion/decay](https://learn.microsoft.com/en-us/windows/win32/direct3d12/using-resource-barriers-to-synchronize-resource-states-in-direct3d-12)

The visible articulated figure built on this API is a development placeholder.
Recognizable family likeness, the bounded GLB import/pack route, final authored
animations and the completed8–12minute opening remain separate deliverables.


## Owned character material extension

The source API now additionally accepts `set_character_asset(const CharacterAsset&)`
and the distinctly named `set_scene_character_asset(base, textured, lighting, asset)`.
The distinct name preserves existing four-input `nullptr` calls to the original
`CharacterMesh*` transaction. A null typed pointer explicitly clears the character;
legacy single/two/three-layer setters preserve either character resource kind.
The old `CharacterMesh` entry point remains vertex-colored with its original
normal and legacy-light presentation behavior.

A typed resource owns all indexed material draw ranges, images and a shader-visible
material/shadow descriptor heap. Source arrays, decoded mip chains and original
asset lifetime are not runtime dependencies after adoption. One owned white image
provides the no-image material fallback. Images use sRGB SRVs with linear repeat
filtering; UV origin remains upper-left. The pixel shader multiplies sampled linear
albedo by vertex, material and instance color, and sums their emission values.
The authored lighting path retains the existing tone map and sRGB composition.
With authored lighting disabled, typed linear materials receive an explicit transfer
to presentation sRGB, while the old mesh route preserves its earlier behavior.
Texture alpha is deliberately not an opacity source in this opaque asset profile.

Single-sided materials use back-face culling. Double-sided typed materials disable
culling and reverse back-face normals before lighting, following glTF material
semantics. Each material uses its matching culling policy in both passes: all
material depth draws complete before any EQUAL-depth color draws. Thus an invisible
single-sided back face cannot write depth in front of another visible material.
The legacy untyped mesh route preserves its prior uncullled normal convention.
This still implements nearest distinct-depth surface composition, not general OIT
or a guarantee for coincident duplicate triangles.

The root signature uses27 DWORDs:16 camera, two2-DWORD CBVs, two1-DWORD descriptor
tables, and five per-material constants. All index/vertex/pose/image native resource
allocations are charged using `GetResourceAllocationInfo`; the complete adopted
character resource profile remains32MiB. Texture staging is charged using actual
placed-copy footprints and native upload-buffer allocation sizes. The old/new plus
all upload staging peak is separately bounded to96MiB. These are resource allocation
charges, not total process or driver VRAM measurements; descriptor heaps, pipeline
objects and allocator bookkeeping are bounded objects rather than a claim of exact
driver-private memory accounting.

A pending submission owns the complete staged `CharacterGpu`, including its
material heap, resources and palette buffers, along with every upload buffer,
allocator and command list. Failed completion retains that owner through the same
poison/quarantine path as other renderer submissions. Active frame failure retains
the complete renderer owner. A lighting or joint scene change stages replacement
character descriptors for the new shadow resource, then swaps them only after the
shared queue drains. Ordinary pose frames never recreate images/heaps/buffers,
rebuild static scenery or perform a full idle.

The focused material GPU fixture is `tests/character_material_gpu_tests.cpp`.
It exercises constant-UV checker corners and seams, signed repeating UVs, complete
mip sampling, sRGB decoding, material/vertex/instance factors, destruction of CPU
source data, culling and back-face lighting, independent material depth, rollback,
legacy setters and minimize/resize. Root records actual build/GPU outcomes separately;
writing these cases or retaining image bytes alone does not prove they passed.

Additional primary references inspected:

- [Shader-visible descriptor ownership and handles](https://learn.microsoft.com/en-us/windows/win32/direct3d12/creating-descriptor-heaps)
- [glTF double-sided materials](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#double-sided)
