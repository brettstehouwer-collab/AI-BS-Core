# Typed character integration review

Review date: 2026-11-02. Reviewer: Codex `character_gltf_import` agent.

Scope: read-only inspection of `content_dependencies.cpp`, companion-model authoring in `content_authoring.cpp`, `placed_assets.cpp`, `creator_viewport.cpp`, and `durable_world.cpp`, with the relevant renderer resource publication code and test sources. No shared builds, GPU runs, source edits, or family-reference access were performed for this review. Actual runtime acceptance remains the parent agent's build/test evidence.

## Result

No blocking integration defect found in the inspected paths. The following conclusions are VERIFIED by source inspection, not new runtime measurements.

| Concern | Inspected behavior |
| --- | --- |
| Missing, corrupt, or wrongly typed companion model | Complete typed closure inspection compares all immutable reference fields and catalog role. Character assets cannot become static visual placements. Missing/corrupt dependencies throw before a new projection is published. |
| Invalid guide clip set | `load_first_boot_content_assets` constructs `GuidePresentation` for every character dependency. Its constructor requires exactly `idle`, `walk`, `catchup`, `guidance` in that order, after mesh validation. The creator's sampling of clip zero therefore has a validated idle clip. |
| Partially assigned model reference | Grouped authoring applies fields to a copied definition; `FirstBootContent::create` validates the complete final reference. Preview and Apply also validate the dependency closure. Failed validation retains the published authoring document/view. |
| Character memory lifetime | `PlacedAssetVisuals` owns a `shared_ptr<const CharacterAsset>`. `ChapterLive` retains its immutable `PlacedAssetVisuals` owner before constructing its borrowing `GuidePresentation`; destruction order releases the presenter first. The creator uses a model only while its current or staged projection owner is alive. |
| GPU admission and replacement rollback | Creator replacement builds its candidate projection first, then calls the atomic scene/texture/light/character setter before replacing its CPU snapshot and owners. The setter validates and stages all candidate resources, drains the queue, then performs nonthrowing publication swaps. Character GPU admission checks actual allocation sizes before resource publication. Failed GPU waits poison/retain submitted owners rather than pretending the renderer remains healthy. |
| Collision and picking | Imported companion bounds are added only by `PlacedAssetVisuals::picking_scene`. Gameplay uses the original authored scene and explicit collision proxies. The `companions.size() <= 1` content invariant makes the use of `companions.front()` consistent with the one retained character model. |
| Gameplay updates and restart | Routine scene/light replacement preserves the independently adopted character resource. Reload reconstructs World, Player, and Companion candidates before owner swaps; the immutable model/presenter binding remains valid and presentation state is reset. A declared missing model is rejected instead of silently using the placeholder. An intentionally unbound companion uses the existing placeholder in Play. |

## Remaining acceptance and documented limits

- The existing `character_store_tests.cpp` covers a successful private grouped model assignment, typed ownership after the source pack is removed, and corrupt dependency staging rollback. It does not yet exercise a complete **assign -> Undo -> Redo -> Save -> reopen -> Preview -> isolated Play** sequence with the model binding attached. Treat that integration sequence as UNVERIFIED until the parent acceptance run records it.
- Source inspection found the missing/invalid-clip rejection gates, but the same store/authoring integration test currently lacks direct assertions that incomplete assignment, a valid generic character with the wrong guide clip set, and a dependency corrupted between Preview and Apply each retain the exact published authoring snapshot. These are useful next regression cases; no bypass was found in the implementation.
- Character selection uses the documented bind-pose AABB at the authored spawn. It is an approximate editor picking proxy, not animated per-frame geometry or a collision shape. Creator preview shows the imported idle animation at that spawn. This does not prove in-game Follow/Wait/Recall or likeness.
- Audio bindings are explicitly rejected by the current publication/projection path because the typed audio loader is unfinished. This is an explicit remaining checkpoint, not a supported optional playback claim.
- Individual resource profiles are bounded, but a successful preflight does not guarantee physical VRAM allocation under unrelated workloads. Allocation/device failures still require the existing renderer failure handling; they are not evidence of content or save corruption.

## Evidence inspected

- `engine/src/content_dependencies.cpp`: complete reference/kind checking and four-clip contract.
- `engine/games/content_authoring.cpp`: private stage/preview/apply/save validation and monotonic placement format promotion.
- `engine/games/first_boot_content.cpp`: single-companion invariant and complete model-reference validation.
- `engine/src/placed_assets.cpp` and `engine/include/aibs/placed_assets.hpp`: immutable owned model and picking-only proxy.
- `engine/apps/creator_viewport.cpp`: staged projection/GPU adoption before CPU publication.
- `engine/apps/durable_world.cpp`: immutable model lifetime, placeholder fallback only when unbound, and reconstructed runtime reload.
- `engine/src/render_dx12.cpp` and `engine/src/render_character.inl`: staged resource admission, publication swaps, and retained failed submissions.
- `engine/tests/character_store_tests.cpp`, `placed_assets_tests.cpp`, `character_material_gpu_tests.cpp`, and `character_gpu_tests.cpp`: inspected test source coverage; not rerun by this reviewer.
