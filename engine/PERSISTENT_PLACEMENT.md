# Persistent chapter asset placement — SDK 0.10

This extends the native mesh/material pipeline with saved **visual instances** in First Boot chapters. Current verification and desktop availability are recorded in `out/persistent_placement_verification.json` and `BUILD_STATUS.md`.

## Document and dependency contract

Each instance stores its persistent entity UUID, display name, asset UUID, complete mesh SHA-256, complete pack SHA-256, position, positive scale, unit quaternion and editor-selectable flag. The three asset reference fields are immutable. To change the referenced asset, create a new instance and explicitly remove the old one. Transform/name/selectability edits retain the instance UUID.

Legacy content remains AIBD1 until the first placement is applied. Placement content uses AIBD2; erasing the last instance retains version 2. Existing operation encodings retain their previous bytes. Create/erase placement operations use typed request version 2 and new operation tags. The AIBA1 journal envelope remains unchanged and embeds the versioned chapter and its edit history. Old engines reject unsupported content rather than silently dropping instances.

A project owns `assets/packs/<pack-sha256>/`, containing exactly:

- `catalog.aibcat`
- `<mesh-sha256>.aibmesh`
- `LICENSE.txt`
- `provenance.json`

The canonical pack hash covers `AIBPACK 1\n` followed by filename-sorted `filename byte-count sha256\n` records for all four files. Both the mesh digest and complete pack digest must match. The copied license and provenance are dependencies, not optional annotations. Hashes detect changed bytes; they do not authenticate rights or establish a third-party license.

`aibs_assetc --adopt PACK --store STORE` verifies and copies to a new immutable pack directory, or verifies an exact existing pack before reuse. It never overwrites an existing revision. `--inspect-store STORE --ref ASSET_UUID MESH_SHA PACK_SHA` verifies a pinned reference. `--stage-store STORE --output NEW_STORE --ref ASSET_UUID MESH_SHA PACK_SHA` stages a bounded private closure; repeat `--ref` for additional revisions. `--merge` admits verified immutable dependencies into an existing private store before publishing an updated viewport snapshot.

Keep all project packs when backing up or moving a chapter. A deleted instance can remain reachable through Undo/Redo. Automatic pack garbage collection is intentionally absent.

## Authoring and rendering

The native chapter host binds an explicit project asset store. Preview, Apply, history travel and Save validate the referenced files, transforms and bounded dependency/render budgets before publication. A prepared preview is revalidated when applied, so a disappearing pack cannot silently publish. Opening and journal replay preserve authored rows even if a dependency is unavailable, allowing exact restoration or explicit removal; a missing dependency does not turn into a source-path fallback.

Python handles transport, UI and opaque snapshot bytes. It does not decode or rewrite AIBD. Snapshot dependencies derive from the same native export context. The native asset tool stages them before the 3D preview receives a replacement snapshot or a temporary Play process starts. A stale/cancelled context cannot publish its snapshot.

The DX12 projection loads immutable meshes and applies position, nonuniform scale and quaternion rotation. Normals use inverse-transpose scaling. Picking uses separate axis-aligned bounds; highlights outline those bounds. Physics continues to use the authored chapter collision scene. Imported meshes do not acquire collision, construction costs, sockets, light emission or gameplay interaction merely by being placed.

Play receives its own exact dependency closure and durable test state. Stop joins the owned native process before the scratch workspace is removed. The creator project and its immutable packs survive.

## Current bounds and scope

- At most 64 visual instances and 32 unique pinned references per chapter.
- A 64 MiB dependency closure, bounded decoded geometry residency and a one-million-vertex composed render limit.
- Existing chapter, message, journal and history limits still apply.
- Current materials remain opaque base color and normalized emission; UVs, texture maps, PBR, lighting/shadows, LODs, skeletal animation and imported collision need later explicit pipelines.

Core contracts are exercised by `asset_store_contracts`, `asset_placement_content`, `placed_assets_projection` and `native_persistent_placement_gpu`. Creator tests and two independent frozen Studio processes additionally cover Preview/Apply, Undo/Redo, Save/reopen, a new native owner epoch, unchanged UUID/TRS/reference hashes, native viewport/Play and missing-dependency rejection. Treat their recorded results as evidence; this document alone is not a claim that every gate has passed.
