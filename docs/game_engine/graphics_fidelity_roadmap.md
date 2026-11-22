# AI-BS native PC graphics fidelity roadmap

Date: 2026-11-01 (America/New_York). Status: **PROPOSED implementation sequence**, recording the creator's advanced-graphics targets. No graphics SDK version, vendor integration, licensing decision, performance preset or installation is selected by this document.

## 1. Current baseline and intended result

The SDK 0.4 work connects saved world identities and changes to visible native DX12 geometry. The renderer currently draws colored triangles with a depth buffer, vertex normals, basic directional diffuse shading and an ambient term. Its emissive-looking colors make restored traces and the execution-core landmark brighter; they do not emit physically simulated light into nearby surfaces. The current shader has no PBR material/texturing system, shadow maps, ambient-occlusion pass, anti-aliasing/reconstruction pass, screen-space reflections, volumetric medium, global illumination or ray/path-tracing pipeline.

Actual RTX 4090 raster rendering, GPU readback, resize/minimize lifecycle and debug-layer checks are useful baseline evidence. They do not verify the advanced techniques listed below. The engine has not recorded a DXR tier or vendor upscaler support query. A recorded feature level of 12.2 and the GPU's product name do not replace those feature-specific runtime checks or demonstrate that an implementation exists.

The artistic target is the motherboard world becoming habitable as BS restores it: readable amber power paths, distinct PCB/copper/aluminum surfaces, reflections in coolant infrastructure, depth around components, and light reaching previously dark architecture. Adam's safe presence should remain legible in the sheltered hub. Effects should support that meaning and gameplay readability. They must not turn a successful repair into an unreadable glare effect or make hazards detectable only with one graphics option enabled.

This is the native PC renderer roadmap. The separate HTML/WebGL concept remains its own playground. Adam's future phone companion follows PC progression; it does not choose the PC's rendering capabilities or become a second world/save authority.

## 2. Standard PC graphics and display settings

The creator also requested the normal PC settings catalog below. These are intended product controls, not a quota of menu items. Each appears as usable only when its real pipeline/window/presentation behavior is implemented and tested. Do not add arbitrary extra toggles or quality presets whose values all produce the same render.

Current behavior is narrower: a resizable native window, a fixed `Present(1, 0)` synchronization request, a fixed 45-degree **vertical** perspective field of view, and a request for per-monitor DPI awareness. There is no complete graphics settings menu, monitor-selection system, refresh-rate selector, frame limiter, HDR path or cosmetic post-processing stack. DPI awareness alone does not certify correct DPI-change/hot-plug behavior. Current behavior is an observation, not a proposed user default for the final game.

| Requested setting | Planned behavior and implementation prerequisites |
| --- | --- |
| Display mode: windowed / borderless / fullscreen | Keep windowed operation, add correctly sized borderless presentation, and explicitly decide whether a separate legacy exclusive-fullscreen path is needed. Report the effective mode honestly; borderless and exclusive fullscreen are not interchangeable API states. Preserve the prior usable bounds/mode and provide apply/revert behavior. |
| Monitor selection | Enumerate actual connected outputs and their adapter/output identity, DPI, work area, supported modes and relevant color capabilities. Handle disconnects, adapter changes and moving between displays with a usable fallback. Do not hardcode the creator's display model as the only supported output. |
| Resolution and aspect ratio | Separate desktop/output size, backbuffer dimensions and internal render resolution. Offer supported choices, keep picking/HUD/camera transforms coherent, and define letterbox/pillarbox behavior for deliberately constrained aspect ratios rather than accidental stretching. Temporal reconstruction stages later own render-scale changes. |
| Refresh rate | Enumerate real modes for the selected output and chosen presentation path. Explain when windowed/borderless presentation follows the desktop configuration. Never advertise an unsupported rate or equate display refresh with measured engine rendering/simulation rate. |
| VSync | Expose actual supported presentation behavior after querying requirements and testing it. Current interval-one presentation is not a user-selectable VSync menu. Uncapped/tearing, variable-refresh and any later frame-generation integration need their own support and pacing validation. |
| FPS cap / frame pacing | Implement a monotonic-clock limiter/pacing policy with measurable CPU/GPU/presentation effects, including focused, unfocused, minimized and paused behavior. A cap controls rendering work, not game-time progression or Adam memory frequency. Avoid a busy-spin-only default; select the final scheduling policy after measurement. |
| SDR brightness / gamma | Define the actual SDR output transfer/color pipeline, calibration pattern and UI behavior first. Keep artist exposure/tonemapping distinct from per-user display preference. A gamma slider must not merely multiply scene light or change gameplay visibility requirements unpredictably. |
| HDR and calibration | Require real OS/output color capability discovery, appropriate swapchain format/color space, an HDR-aware lighting/exposure/tonemapping path and meaningful calibration. Define SDR/HDR UI composition and display-switch fallback. A checkbox without those resources and output behavior is not HDR support. |
| Field of view | Expose a validated vertical-FOV value with clear aspect-ratio behavior and matching mouse picking, projection and sensitivity treatment. Current fixed 45-degree vertical projection is not an adjustable control. Reject invalid values without corrupting the current camera; evaluate first/third-person camera choices separately. |
| Overall quality / detailed controls | Quality presets must map to implemented resource budgets/pass choices and show a custom state after overrides. Define default/preset values through representative tests; no fixed Low/Medium/High/Ultra settings are approved here. |
| Motion blur | Add only with a real blur pass, motion inputs and valid camera/object handling. Keep it independently adjustable where supported and evaluate it alongside temporal reconstruction and frame generation. |
| Film grain | Add only as a real compositing pass with explicit placement relative to reconstruction/tonemapping. It is a cosmetic option, not an image-quality prerequisite. |
| Depth of field | Define the camera/focus model, UI readability and actual depth-based pass. Keep gameplay targeting readable; do not expose a slider that has no renderer effect. |
| Chromatic aberration | Optional real post-process only; define its composition and keep text/critical cues readable. It is not automatically part of a higher-fidelity preset. |

Microsoft's output interface documents monitor-specific capability information; its Advanced Color guidance covers the output/color pipeline needed for HDR. Microsoft also documents why modern flip-model borderless presentation should be evaluated before assuming a classic exclusive path is required. These are implementation references, not evidence that the current engine has integrated those capabilities. [DXGI output capabilities](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_6/nn-dxgi1_6-idxgioutput6), [Windows Advanced Color/HDR](https://learn.microsoft.com/en-us/windows/win32/direct3darticles/high-dynamic-range), [DXGI flip-model guidance](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model).

A basic settings milestone can proceed alongside G1 instrumentation: enumerate displays/modes, define versioned OS/user preferences, implement safe window/borderless transitions and pacing controls, then test persistence and recovery. HDR and post-processing controls follow their actual rendering prerequisites. The current SDK 0.4 scene/save integration does not implement this entire menu in the same slice.

Settings acceptance includes focus/Alt-Tab, resize/minimize/restore, moving between different-DPI displays, display disconnect/reconnect, unsupported/stale preference recovery, and apply/revert timeout. Check that the HUD, mouse rays and rendered scene agree after each supported change. Save/reload, graphics reset and preference-file corruption must leave BS's world, constructions, quest state and Adam's recorded history unchanged.

## 3. Advanced graphics feature register

The requested feature families are confirmed direction. Their exact algorithms, quality levels, SDKs and delivery order remain proposals.

| Target | Intended contribution in AI-BS | Current implementation / dependency |
| --- | --- | --- |
| Ray tracing: reflections, shadows and GI | Hardware-world reflections, contact/area shadows and indirect light from restored regions | Unimplemented; requires a queried supported path, scene acceleration structures, resource scheduling and filtering |
| Path tracing | Reference lighting and a possible optional high-fidelity rendering mode | Unimplemented; progressive accumulation, sampling, material/light coverage and denoising/reset rules must be designed |
| Global illumination | Light bounce that makes repaired architecture influence nearby spaces | Unimplemented; select a baseline GI approach and separately evaluate ray-based alternatives |
| Shadow quality | Ground BS, components, vehicles and constructions with readable light relationships | Unimplemented; begin with bounded raster shadow maps and filtering before optional ray-traced shadows |
| Ambient occlusion: SSAO / HBAO+ | Contact depth around heatsinks, sockets, machinery and building joints | Unimplemented; depth/normal inputs and a compositing contract first; HBAO+ is an optional candidate, not an installed dependency |
| LOD and draw distance | Preserve component silhouettes and useful distant landmarks while budgeting visible geometry | Unimplemented; chunk/asset identity, visibility, mesh levels and resource retirement are needed |
| Tessellation | Selective geometric detail or displacement on suitable surfaces | Unimplemented; authored displacement/patch data, crack control and level-of-detail policy must justify it |
| DLSS / FSR / XeSS | Optional image reconstruction/upscaling paths for compatible devices and integrations | Unimplemented; temporal inputs and provider-specific support/lifecycle validation are prerequisites |
| TAA / SMAA / DLAA | Reduce unstable edges and fine-trace shimmer through suitable selectable AA modes | Unimplemented; a spatial AA candidate can arrive before temporal AA; reconstruction modes must not blindly stack redundant AA passes |
| SSR | A raster reflection option for suitable visible surfaces, including parts of coolant/metal infrastructure | Unimplemented; depth hierarchy, material roughness, normals, scene color and missing-data fallback required |
| Volumetric fog | Controlled atmosphere and light shafts around cooling infrastructure and large component spaces | Unimplemented; medium/light representation, bounded integration and compositing required |

These are feature families, not a promise that every named technique will run simultaneously. For example, the AO implementation is selected per active pipeline; independent SSAO and HBAO+ passes should not both darken the same signal by default. Reflection and GI paths also need explicit ownership so contributions are not counted twice.

## 4. Staged engineering sequence

The following order is an AI-BS proposal based on the current renderer's missing inputs. Some work can proceed in parallel once its contracts exist. Each stage must preserve the runnable raster baseline and the existing world/Adam save tests.

### G1 — Linear materials and measurable rendering

Introduce explicit linear-light scene color, documented texture/color-space conversion, HDR intermediate buffers with controlled exposure/tonemapping, and a versioned material description. Start with albedo/base color, metallic/roughness, normal maps and emissive terms. Supply texture import/mips, tangent handling, sampler policy and missing-material behavior. Keep object identity separate from render resource handles.

Add CPU/GPU timestamp capture, resource-memory counters and named pass diagnostics before promising quality/performance presets. Build a fixed material/light test room with copper, PCB, matte insulation, aluminum, coolant and emissive traces. Establish the scene and camera paths used in later comparisons; do not call the current vertex-color shader PBR.

Acceptance: predictable color-space behavior, stable exposure under a controlled light change, normal-map orientation checks, correct material fallback, and captures showing actual bound textures/resources. A repaired core changes the authoritative state once; rendering its emission must not append another Adam memory event every frame.

### G2 — Pass/resource scheduling, depth/normals and raster shadows

Introduce a small render-graph/pass-resource contract: declared reads/writes, resource versions, barriers, lifetime/retirement and resize invalidation. Expose the depth/normal/material signals needed by later image-space effects. This does not require an immediate full deferred renderer; select forward/deferred/clustered details through measured scene requirements.

Add a bounded shadow-map path with tested light transforms, depth conventions, receiver/caster behavior, filtering and bias. Select sun/local-light shadow strategies after a light-budget test. Static/built/moving geometry must refer to the same admitted world revisions used by the main image. Dismantling a machine must retire its shadow contribution as well as its visible mesh.

Acceptance: a receiver/caster scene, contact and self-shadow inspection, controlled bias tests, resize/reload behavior, debug-layer checks and GPU capture identifying shadow resources and consumers. Retain a defined no-shadow fallback.

### G3 — Ambient occlusion and spatial AA

Build a baseline screen-space AO implementation or evaluate a pinned candidate behind one AO interface. Define radius/world units, normal/depth conventions, edge handling, filtering and which lighting terms AO affects. Keep AO from indiscriminately multiplying emissive light. Compare it with an AO-off reference so component sockets gain depth without becoming black cavities.

Evaluate a spatial anti-aliasing option, including the requested SMAA family, as a separate pass with its own selected implementation/license review. Test fine copper traces and moving camera edges before introducing history. No algorithm or third-party source is selected here.

HBAO+ remains a named candidate. NVIDIA's official repository describes its SSAO method and input requirements; its source license must be reviewed for the exact revision and distribution plan before integration. The documentation's existence does not make it a shipped AI-BS feature. [NVIDIA HBAO+ repository](https://github.com/NVIDIAGameWorks/HBAOPlus), [source license](https://github.com/NVIDIAGameWorks/HBAOPlus/blob/master/LICENSE.txt).

Acceptance: AO/AA on-off captures, silhouette/halo and thin-geometry cases, normal/depth debug views, stability while placing/removing a relay, and timing/memory recorded per enabled pass.

### G4 — Temporal foundation and reconstruction adapters

Add previous/current camera and object transforms, motion vectors, projection jitter, exposure conventions, history resources, disocclusion handling and explicit reset reasons. Reset or invalidate history for camera cuts, load/branch changes, teleports, relevant display/render-size changes, replaced geometry and material/light discontinuities. Newly built objects need valid first-frame motion/history behavior; removed objects must not remain as ghost geometry.

Implement and validate a native-resolution temporal AA baseline, then evaluate requested DLSS, FSR and XeSS adapters against the same normalized input contract. Native-resolution DLAA is an optional NVIDIA AA mode, not a synonym for lowering the input resolution. Select one AA/reconstruction owner for each pipeline configuration. Do not add a separate TAA accumulation pass in front of a temporal upscaler unless its integration explicitly requires that design.

Intel's developer guide describes jitter, motion-vector and history-alignment concerns for XeSS. AMD's upscaler documentation describes temporal inputs, jitter, camera-cut resets and interaction with TAA. These support the need for the temporal foundation; they do not select a version or establish compatibility with this engine. [Intel XeSS developer guide](https://www.intel.com/content/www/us/en/developer/articles/guide/xe-super-sampling-developer-guide.html), [AMD FidelityFX upscaler documentation](https://gpuopen.com/manuals/fidelityfx_sdk/techniques/super-resolution-upscaler/).

NVIDIA's integration guide requires initialization, device/feature support checks and correctly supplied rendering inputs. NVIDIA separately describes Super Resolution, DLAA and Ray Reconstruction. A provider adapter must report actual support and failure reasons rather than exposing every named mode for every GPU. Review the chosen package's license, initialization, application identification and redistribution requirements before implementation. [NVIDIA Streamline DLSS guide](https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuideDLSS.md), [NVIDIA DLSS technologies](https://developer.nvidia.com/rtx/dlss).

Frame generation is a separate later decision from image upscaling. It affects presentation, input-latency accounting, UI composition and resource lifetime; generated display frames must not advance gameplay ticks, inventory, quests or Adam history. Record base rendered-frame timing and presented-frame timing separately. NVIDIA and AMD document distinct frame-generation integration requirements. [NVIDIA frame-generation guide](https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuideDLSS_G.md), [AMD FSR integration overview](https://gpuopen.com/fidelityfx-super-resolution-3/).

Acceptance: motion-vector/jitter debug captures; moving camera and moving component tests; disocclusion, thin traces, emissive edges, ghosting and HUD stability; all reset reasons exercised; provider-unavailable fallback; resize/minimize/fullscreen recovery and restored native rendering after disabling a provider. Record results for each actual adapter/driver/provider/configuration combination.

### G5 — Reflections, atmosphere and scalable visible detail

Add SSR with a defined missing-screen-data fallback rather than treating it as complete world reflection. Evaluate reflection probes/environment lighting alongside material roughness and later ray-based paths. Coolant and polished metal are useful test cases; hidden/offscreen surfaces must not cause unbounded smears or falsely persistent reflections after an edit. AMD supplies an official stochastic SSR reference implementation for later evaluation. [AMD screen-space reflection sample](https://gpuopen.com/manuals/fidelityfx_sdk/samples/stochastic-screen-space-reflections/).

Introduce bounded volumetric fog/light integration, with clear composition and temporal-history rules if accumulation is used. Use it to distinguish cooling passages and monumental distances while retaining readable paths. A simple screen-depth color fade may be a useful first effect, but must be labeled separately from a true volumetric medium.

Build visibility/culling and asset/chunk LOD with stable instance identities, source revisions and render-resource retirement. Draw distance and mesh detail may change visual submission; they must not delete BS's constructions, erase NPC/quest state, or silently stop the already-defined active-play strategic simulation. Measure when chunked/incremental geometry replaces the current whole-scene mesh rebuild.

Evaluate tessellation only for assets that benefit from additional surface geometry. Define displacement bounds, normals, transition/seam rules, silhouette/error criteria and shadow consistency. It is not a substitute for good source meshes or normal mapping. Microsoft's tessellation reference explains the hull/tessellator/domain stage roles; AI-BS still needs its own DX12 PSO/material implementation and tests. [Microsoft tessellation-stage reference](https://learn.microsoft.com/en-us/windows/win32/direct3d11/direct3d-11-advanced-stages-tessellation).

Acceptance: deliberate SSR screen-edge/offscreen cases, fog-off readability comparison, stable LOD transitions while moving/building, no geometry/collision disagreement at active interaction distances, chunk-boundary placement/reload checks and bounded GPU memory under repeated sector traversal.

### G6 — Optional DXR lighting and path-traced reference

Query DXR support on the selected device using the appropriate D3D12 feature data; record the actual tier, shader model, limits and required formats. Handle unsupported/failed queries with the validated raster path. Microsoft's DXR documentation specifies feature-specific support queries. No DXR tier is asserted for the current application merely because raster feature level 12.2 was recorded. [Microsoft ray-tracing tier reference](https://learn.microsoft.com/en-us/windows/win32/api/d3d12/ne-d3d12-d3d12_raytracing_tier), [DirectX Raytracing functional specification](https://microsoft.github.io/DirectX-Specs/d3d/Raytracing.html).

Begin with one bounded ray effect and compare against the raster reference. Introduce BLAS/TLAS ownership, scratch/residency budgets, instance identity, update/rebuild policy, ray masks, shader tables or inline-query path, denoising and history reset. Placing, moving or dismantling geometry must update both visible meshes and ray structures at coherent world revisions. Ray-traced shadows/reflections and ray-based GI are distinct capabilities; completing one does not certify all of them.

Plan an optional path-traced reference mode for material/light validation before deciding whether a real-time path-traced mode fits selected hardware and scenes. Define samples/bounces, accumulation, stopping/reset rules, noise measurement and comparison artifacts. A still screenshot is not proof of usable interactive path tracing. A selected GI SDK or denoiser would need its own dependency/license/compatibility record; none is selected by this roadmap.

Acceptance: actual feature-query evidence, GPU captures with ray workloads and acceleration structures, dynamic construction/undo/reload tests, ray/raster fallback switching, denoising/disocclusion tests and measured memory/CPU/GPU/presentation behavior under named scene budgets.

## 5. Settings, support and save boundaries

The user-facing settings menu should list implemented controls and supported active modes. Planned effects belong in development status, not as working toggles. When implemented, each control reports requested versus effective mode and a meaningful fallback reason. Device/provider support is queried for the selected adapter and current runtime; a GPU brand alone is not a capability registry.

Display/render-size, fullscreen/window-mode and adapter changes need explicit apply/revert behavior with timeout recovery where a display could become unusable. Resource and temporal history resets must happen coherently. Provide restoration of defaults for graphics preferences; this must not reset the game world, Adam memory, inventory or quest progression.

Store OS/user graphics preferences separately from BS world checkpoints. A save made with one renderer mode must reload under another supported mode without changing its authoritative world facts. Camera/history caches, AO buffers, generated frames, reflection histories, acceleration structures and shader resources are derived state, not Adam's memories. Preserve creator-authored lights/material identifiers as project/world content where appropriate; keep per-machine quality choices separate.

No universal Low/Medium/High/Ultra mapping or FPS promise is approved here. Quality and cost depend on render/output resolution, scene/material/light count, ray samples, visible chunks, driver, shader compilation, memory pressure and CPU/GPU workload. Establish budgets and per-pass measurements first. Frame generation must not be presented as equivalent to increased simulation rate or lower input latency.

## 6. Required evidence before claiming a feature complete

1. A reproducible fixture scene/camera route, exact build, shader/provider revision, adapter/driver, render/output resolution and active settings accompany captures.
2. Native GPU captures and debug-layer results show the real pass/resources. A toggle label, shader filename, vendor DLL presence or visually plausible screenshot alone is insufficient.
3. Frame histories and debug buffers demonstrate motion, jitter, disocclusion and resets for temporal effects. Record stable and failure cases, not only a stationary view.
4. CPU/GPU pass times, presentation timing, memory/residency and transient allocation peaks are measured with repeated traversal and editing. Separate loading/compilation effects from steady-state results. Record percentile/frame-time distributions and test duration; set thresholds only after representative baselines.
5. Build/dismantle, repair, undo/redo, save/reload, device/provider fallback, resize/minimize and supported display changes preserve coherent geometry, effects, hints and authoritative progression. Re-run world/Adam checkpoint tests with renderer modes changed.
6. Image-quality comparisons use the same realized world state, exposure/camera conditions and appropriate references. An artistic preference and a measured correctness failure are recorded separately.
7. Record dependency notices, packaging requirements and selected immutable inputs before shipping a vendor integration. SDK updates re-enter compatibility/quality/performance verification rather than silently changing approved behavior.

The next concrete graphics milestone should be **G1 materials/color pipeline plus instrumentation**, scoped alongside the current world/interaction work. Advanced lighting remains a planned path toward the personal hardware-world art direction; no implementation or performance claim is created by this document.
