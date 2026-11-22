# Authored lighting contract

This module supports checkpoint 4. Its CPU reference is complemented by the
DX12 lighting/shadow path and a chapter power adapter described below; opening
art and the complete packaged chapter remain unfinished.
Legacy rendering stays on its original shader branch until authored lighting
is explicitly enabled.

`SceneLighting` owns ambient color, exposure, at most one directional light and
32 point lights. A directional light's unit direction follows its rays toward
the world; Lambert shading uses the negative direction. Point lights use a finite
radius with smooth quadratic falloff. These are bounded authoring units, not a
photometric calibration or a complete PBR material model.

For an enabled scene the reference calculation is:

```text
irradiance = ambient
           + directional_color * intensity * max(dot(normal, -direction), 0)
           + sum(point_color * intensity * max(dot(normal, toward_point), 0)
                 * max(1 - distance / radius, 0)^2)
radiance = base_color * (irradiance + emission)
mapped = 1 - exp(-radiance * exposure)
output = standard_sRGB_transfer(mapped)
```

At a point light's exact center, the direction is the surface normal to keep the
calculation finite. The CPU reference normalizes nonzero surface normals and
requires `enabled=true`. It does not substitute for either legacy shader.
GPU shadow visibility multiplies only the directional Lambert term; ambient,
emission and point contributions remain independent of that map.

Exposure is bounded to 0.05–16, intensity to 0–100, point radius to greater than
0.05 and at most 500, and positions to absolute coordinates of at most one
million. Colors are finite normalized RGB. Validation is side-effect free.

The single directional shadow uses a centered orthographic volume. It follows
D3D left-handed, row-vector, row-major conventions with depth in 0–1. Its center
maps to depth 0.5. The view's eye is `center - direction * (near + far) / 2`;
world Y is the preferred up axis, falling back to Z near a vertical ray direction.
Half extent is 0.25–4096; near is 0.01–4096; far is at most 100000 and must exceed
near by at least 0.1. Resolution is explicitly 1024 or 2048, and normalized depth
bias is 0–0.05. Enabled shadows require enabled authored directional lighting.

`GpuLightingConstants` has an exact 1168-byte, 16-byte-aligned layout. GPU upload
storage must be rounded to the D3D constant-buffer alignment of 256 bytes
(1280 bytes). `pack_scene_lighting` zeroes all unused point slots and supplies an
identity shadow matrix when shadows are disabled. The packed block is owned CPU
data; it allocates no GPU resource and does not perform publication.

Standalone MSVC C++20 `/W4 /WX /permissive- /EHsc` tests passed 118 checks in
Release and Debug after an observed missing-header RED. They cover numerical
lighting references, finite point falloff, emission/exposure, axis/vertical/
oblique shadow depth and translation, exact buffer layout, maximum counts and
malformed data. Evidence: `D:/AI-BS-Game-Resources/workshop/lighting-cpu-test`.
CPU math alone is not proof that those pixels render correctly.

## Native resources and publication

`Dx12Renderer::set_lighting` stages a validated light configuration, while the
three-argument `set_scene` stages geometry, textures and lights atomically.
Existing scene callers retain the disabled legacy path. Two fixed 1280-byte
frame constant buffers are fence-protected. The bounded directional shadow map
is 1024 or 2048 square, with a depth-only caster pass and explicit resource
transitions. Textured draws use one combined image/shadow SRV heap. Per-frame
rendering neither rebuilds static scenery nor idles the GPU for light updates.
Publication keeps old resources until submitted work completes, preserving the
existing failure/quarantine lifetime contract.

`native_authored_lighting` compares actual GPU pixels with the CPU reference,
checks point and directional contribution, exposure, disabled legacy output,
shadowed ambient, unshadowed points, textured/transient casters and failed
replacement rollback. `native_chapter_lighting` drives both actual power routes
in private databases, compares identical lit/unlit geometry and then restarts
each case to verify the exact light-driving state and overview pixels. Results
are stored under `out/warm_beginning`; consult configuration-specific reports
and their timestamps rather than treating this contract as verification.
