# Indexed character resource and pose contract

`CharacterMesh` is an owned CPU resource for the dedicated character path. It
contains indexed vertices, one skeleton and at most eight baked clips. It does
not use `SceneMesh`, expand every indexed triangle or enter the 4096-vertex
transient stream. `CharacterPose` and `CharacterInstance` are independent fixed
storage; an instance contains no mesh copy. This module implements CPU
validation, sampling and a skinning reference. It does not implement GLB import,
a file codec, GPU resources, drawing, Adam's likeness or native movement.

The header is `aibs/character_scene.hpp`. Resource adoption calls
`validate_character_mesh` before publication. Per-frame callers use
`sample_character_clip`, `character_skin_palette` and
`validate_character_instance`; these inspect the skeleton, pose and accessed
sample frames without rescanning the complete vertex/animation resource.
Geometry, clips and source references remain immutable during those calls.

## Resource bounds

- 1–64 joints, one root at index0, every other parent earlier than its child.
  Importers must reorder joints and remap all vertex indices consistently.
- 1–262144 vertices, nonempty 32-bit triangle indices, at most1572864 indices.
  A vertex occupies72 bytes: position, normal, linear color/emission, UV,
  four16-bit joint indices and four32-bit weights. Every slot's joint is valid,
  including zero-weight slots; finite nonnegative weights sum to1 within1e-5.
  Vertex normals have squared norm1 within1e-4.
- At most8 clips, unique nonempty names of at most64 bytes without control
  bytes, duration greater than0 and at most3600 seconds, 1–4096 uniform frames.
  Every clip owns exactly `frame_count * joint_count` local TRS samples.
- Positive local scales are0.001–1000; translations/positions/UV are finite and
  bounded. Unit quaternions use the existing squared-norm tolerance1e-4.
  Affine matrices preserve orientation and reject singular or ill-conditioned
  linear blocks through a scale-relative determinant check. Global transforms,
  inverse-transpose normals and instances must also fit bounded finite values.
- The conservative canonical data charge is at most32MiB. It includes128 bytes
  of reserved metadata,72 bytes per vertex,4 per index,108 per joint, and32
  bytes plus name/terminator and40 bytes per sample for each clip. This is an
  explicit data budget, **not a claim that a binary file format exists**. A
  future importer/codec must independently reject actual complete files over
  32MiB and charge any additional embedded data before publication.
- Decoded owned storage is independently limited to64MiB. Its conservative
  charge includes container objects, actual vector capacities, clip string
  capacity and sample capacity. Excess reserved capacity is not free. The
  combined modern dependency closure retains its separate128MiB limit.

`character_mesh_cost` returns the data/decoded/animation charges and exact
indexed vertex/index byte counts. It does not include allocator bookkeeping or
pretend those counts are D3D allocation sizes. The renderer must separately
charge native alignment, frame buffers, palettes, textures and actual GPU
residency before publishing its owned resources.

## Transform and animation convention

The engine uses Y-up left-handed mesh coordinates, row-major matrices and row
vectors. `character_transform_matrix` builds `scale * rotation * translation`.
The matrices are composed as:

```text
global_pose[j] = local_pose[j] * global_pose[parent[j]]
skin[j]        = inverse_bind[j] * global_pose[j]
world_position = sum(weight[k] * (position * skin[joint[k]])) * instance.world
```

Inverse binds must invert global bind transforms **in mesh coordinates**;
`inverse_bind * global_bind` must be identity within5e-4. A future GLB importer
must convert node spaces, handedness, winding, inverse binds and baked clips
consistently rather than copying source matrices into this contract unchanged.

Clips are baked in place: root translation is exactly the bind translation at
every frame. BS/guide navigation owns world locomotion. Sampling interpolates
translation/scale linearly and rotations by shortest-arc quaternion slerp,
including opposite-sign representations of the same rotation. Looped clips
wrap at their duration; nonlooped clips clamp at the end. One-frame clips are
valid static poses. Time must be finite and nonnegative. Runtime pose and sample
evaluation perform no heap allocation and do not persist animation frames.

## Normal reference for the future shader

Each normal palette matrix is the inverse transpose of the corresponding skin
matrix's linear3×3 block. Blend those transformed normals, then apply the world
inverse transpose and normalize. Do not transform normals as positions or use
the position matrix when a bone or instance has nonuniform scale.

For stable degenerate blends, compute
`normal_scale = sum(weight * length(transformed_bone_normal))`. If the squared
length of the blended normal is at most `1e-12 * normal_scale * normal_scale`,
use the original bind normal before the world normal transform. The relative
test preserves valid very small inverse-transpose results at large scale. It
is a defined rendering fallback for cancelling normals, not an assertion that
collapsed linear-blend geometry has a unique physical surface normal.

The GPU skinning path must match `character_skin_vertex`, including that
fallback and matrix order. Robust GPU normalization should first scale by the
largest absolute component to avoid squaring very large finite world normals.
`CharacterSkinPalette` is a CPU value, not an HLSL constant-buffer layout; GPU
packing and alignment remain explicit renderer responsibilities. CPU checks
alone are not GPU animation evidence.

## Verification scope

The standalone MSVC C++20 fixture uses `/W4 /WX /permissive- /EHsc`. Tests include
an asymmetric skeleton with nonidentity parent rotation/translation and inverse
binds, weighted poses, nonuniform bone/world normals, shortest-arc interpolation,
loop/clamp/static clips, cancelling normals, large uniform/nonuniform scales,
malformed topology/weights/counts/matrices/clips, pose overflow and independent
payload/decoded capacity limits. Initial missing-header RED and later numerical
edge failures are retained under
`D:/AI-BS-Game-Resources/workshop/character-cpu-test`.

Central target/export registration and both installed SDK consumers now pass.
Indexed GPU drawing/readback and temporary articulated in-place animations now pass
source and installed SDK proofs; see CHARACTER_RENDERER.md and GUIDE_PRESENTATION.md.
GLB parsing/cooking, Adam likeness and packaged opening acceptance remain subsequent work.
