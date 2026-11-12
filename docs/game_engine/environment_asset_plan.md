# Environment assets — motherboard world

Updated 2026-11-01, America/New_York. This extends the approved M5–M7 graphics and world plans. It records the user's environment breakdown alongside the active asset pipeline; listed future features are not claims of implemented rendering.

AI-BS remains a custom native PC engine and creator. The world takes its layout from Brett's hardware: ASUS TUF GAMING X870-PLUS WIFI, Ryzen 9 9950X, RTX 4090 Founders Edition, DDR5, NVMe storage, cooling loops and the Tower 900 enclosure. Original engineering models and adaptations should establish that identity without presenting approximate geometry as official manufacturer CAD.

## First asset slice — verified limited delivery

Verified delivery: Studio96 / SDK0.9; engine/out/asset_pipeline_verification.json records actual tests. The current slice imports triangulated OBJ geometry and an explicit AIBMAT table of opaque base colors and emission. A native cooker emits a versioned, checksummed mesh, content-addressed catalog, copied license and import provenance. A render-only adapter places the mesh in the native motherboard scene. CPU geometry/material tests, actual GPU differences, standalone-package loading, independent SDK consumption and creator UI checks must pass before delivery is marked verified.

The renderer's existing vertex colors and emission are the material model for this slice. It does not implement image textures, physically based shading, authored light sources, shadow maps, lightmaps, sky lighting, volumetrics, automatic LOD or triangle-mesh physics. Texture coordinates accepted in OBJ are validated but not retained. Geometry expansion for the current renderer is bounded; indexed GPU draws and streaming remain later improvements.

## Environment inventory and delivery order

| Family | AI-BS world use | Required authoring data | Planned implementation/acceptance |
| --- | --- | --- | --- |
| Structural meshes | Motherboard substrate, CPU socket foundations, DIMM corridors, case walls, Jenison structures, sheltered hub and Pencil Room | Units, transform, pivot, placement bounds, stable asset ID, revision/hash and source/license | Start with imported static parts, then persistent visual bindings and placement previews. Never derive invisible collision changes from a visual refresh. |
| Props | Capacitors, coils, heatsink fins, connectors, screws, benches, repair tools, relay parts and later computer-part equipment | Mesh/material slots, interaction anchors, naming, provenance | First cooling assembly demonstrates detailed triangles and multiple materials. Interactive props additionally need typed gameplay definitions and save-backed outcomes. |
| Modular kits | Trace walkways, PCIe platforms, coolant pipes, cable bridges, sheltered-room walls and machine sockets | Grid dimensions, shared pivots, endpoints, orientation rules and supported collision proxies | Snap previews must show fit, affected routes and power dependencies before an explicit build action. Rendering alone does not validate connectivity or traversal. |
| Albedo maps | Circuit-board solder mask, metal paint, labels and wear | UV sets, sRGB interpretation, dimensions, mip chain, sampler and content hashes | Add bounded image import and GPU texture/descriptors before exposing a working texture control. Preserve constant-color materials as a fallback. |
| Normal maps | Fine traces, machining, screw heads and surface scratches | Tangent basis, handedness, linear decode and channel convention | Require retained UVs/tangents, tested normal transforms and comparison against flat shading. A normal map changes shading rather than collision or silhouette. |
| Roughness and metallic maps | Brushed heatsinks, copper contacts, plastic connectors, dielectric solder mask | Linear channels, declared packing, scalar defaults | Introduce a documented surface/lighting model and calibrated material tests. Glossiness conversion, if offered, must be explicit. |
| AO maps | Baked crevices around components | UV/channel, linear interpretation and strength | Apply to the appropriate ambient lighting contribution; document limitations rather than multiplying all direct lighting indiscriminately. |
| Height/displacement | Larger relief and optional close-range surface geometry | Scale/bias, UVs, tessellation/mesh subdivision policy and bounds | Keep shading-only parallax distinct from real geometry displacement. Real displacement requires culling, picking and collision decisions; it is not implied by a height texture. |
| Direct lights and shadows | Restored power stages, workbench lamps, warning arcs and the RTX 4090 awakening | Light type, transform, color/intensity, range and shadow budget | Add native point/spot/directional lights in stages, then measured shadow paths. Tie restoration light changes to actual world state and keep minimum navigation cues readable. |
| Lightmaps | Optional static hub and interior illumination | Separate UVs, bake provenance, static/dynamic eligibility and invalidation | Baking is a future workflow. Editable construction must invalidate affected data visibly; moving a wall cannot silently retain an incompatible bake. |
| Skybox/HDRI | The case interior, distant board horizon and changing ambient mood | Projection, color space, intensity, license and environment revision | Begin with a controllable environment background, then environment lighting/reflections when supported. Do not treat a background image as completed indirect lighting. |
| Fog and VFX | Coolant vapor, dust, heat haze, signal trails and infection atmosphere | Particle/material assets, emission regions, lifetime and bounded budgets | Begin with readable lightweight effects, then measured volumetrics. Effects must preserve door, hazard and interaction visibility and respect accessibility settings. |
| Collision meshes | Safe walkable board routes and component/vehicle boundaries | Explicit simplified proxies, layers, transforms and gameplay revision | Existing collision remains authoritative. New collision import requires separate native admission, movement tests and save/content compatibility; visual mesh triangles do not automatically become physics shapes. |
| LOD and optimization | Component neighborhoods, distant memory towers, GPU silhouette and large motherboard districts | LOD mesh revisions, screen-space thresholds, bounds and residency budgets | Add measured geometry/texture budgets, then LOD transitions, culling and asynchronous streaming. Preserve persistent identities across visual LOD changes. |
| Shaders | Constant-color/emissive surfaces now; future textures, surface lighting and atmosphere | Explicit shader version, vertex layout, pipeline state and supported material features | Add only validated paths. Unsupported material features must reject or show a declared fallback, rather than presenting a menu label as a completed effect. |

## Personal continuity and world coherence

Jenison remains the unwanted starting territory. The sheltered hub and Pencil Room gain their distinct detail through Brett's approved memories and authored adaptations, not arbitrary generated biography. Adam's guidance remains grounded in recorded choices and verified source material. Generated dialogue is a draft until accepted; an emissive material or lighting cue does not establish a recovered memory or a historical quotation.

The RTX 4090 FE awakening is a later coordinated scene of restored power, geometry, lighting, sound and saved progress. A bright imported prop is useful visual work but is not that completed cinematic or gameplay milestone.

## Compatibility and verification

Preserve original source assets and licenses. Record importer/schema versions, exact source/material/license hashes, units and coordinate conversion. Cook to a fresh folder; do not overwrite a published asset or a user's saved project. Catalog resolution must stay inside the chosen package and reject missing, redirected or damaged dependencies without source fallback.

The initial mesh catalog is presentation-only. AIBSSAVE, AIBD, AIBA and existing gameplay databases keep their current meaning. Persistent asset bindings, collision references, dependency previews, undo/redo and content migration require explicit versioned authoring work before imported meshes can replace interactive objects everywhere in the chapter.

Validation progresses from CPU import/format/path tests to actual DX12 readback, SDK use, creator process ownership and a packaged PC workflow. Measure model size, material count, load time, GPU memory and frame cost as the environments grow; avoid fixed performance guarantees based only on the workstation specifications.

Blender's official [OBJ export documentation](https://docs.blender.org/manual/en/5.0/files/import_export/obj.html) describes triangulation, normals, material groups and export transforms. AI-BS admits its documented subset; an OBJ exported successfully elsewhere is not automatically compatible with every AI-BS import option.


Persistent placement update — Studio97 / SDK0.10: visual instances, immutable project-owned packs, native Preview/Apply/history/Save and two-process restart are verified in engine/out/persistent_placement_verification.json. UVs/tangents/images, material maps, lighting/shadows, collision authoring, LOD, animation and audio remain staged work. See engine/PERSISTENT_PLACEMENT.md.
