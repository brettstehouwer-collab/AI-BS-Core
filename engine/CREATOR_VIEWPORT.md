# Native creator viewport

The source Creator tab now offers **Open 3D preview** and **Close 3D preview**.
`aibs_creator_viewport.exe` owns a separate DX12 window: WASD/right-mouse look,
Space/Ctrl vertical movement, V to frame the world, click/E to select. Selection
highlights the geometry and selects its persistent UUID in the Qt inspector.
Inspector selection returns to the preview. Applied edits/history and refreshed
SDK edits publish authoritative geometry; private previews remain unpublished.

This is an authoring preview. It does not run grounded gameplay, save, repair,
build the chapter bypass or modify Adam's memory. Gameplay remains in the existing
player. Editable chapter content/dependencies and owned native Play/Stop are next.
Installed Studio94/public87 are unchanged. Source AI-BS uses the new SDK executable.

Generic nodes with complete x/y/z and half extents render as boxes. Missing
transforms remain in the outliner without invented geometry. Positions are limited
to +/-1,000,000 and half extents to .001–10,000; schema admission remains in the
host. Projects declaring firstboot.kind call the existing native first_boot_scene
on the full world, preserving composite hardware geometry and enabling authoring
picks on board/traces. First Boot projection is conservatively capped at512
entities; generic snapshots at10,000 entities,64 fields/entity and1MiB total.
Seven-field projects do not silently become protected First Boot chapters.

## Process and snapshot contract

ViewportClient owns a QProcess and a unique temporary directory. A fsynced,
atomically replaced scene.aibv contains AIBV magic, version1, projection mode,
snapshot UUID, project/branch/world UUID, checkpoint UUID, uint64 revision,
selected UUID and bounded source entities. Fields are finite binary64; text and
UUID rules reuse strict payload primitives. This read-only projection protocol
does not change the CreatorHost command wire or checkpoint format.

The native child polls at100ms, validates the complete candidate and stages the
renderer replacement before publishing its new snapshot tag. Invalid replacements
retain the old scene and emit diagnostics. No authoring command exists here.
Highlighting uses transient slightly enlarged geometry, preserving authored bounds.

ASCII stdout records are `AIBV1 READY snapshot_uuid world_uuid revision` and
`AIBV1 PICK snapshot_uuid world_uuid revision entity_uuid` (`-` means no hit).
Only the owned process/current snapshot can select; Qt also checks the current
authoritative head. Old picks cannot rebind through an alias or newer revision.
The window receives rows only after the entire pinned authoring snapshot validates.

Qt reads bounded64KiB stdout chunks with256-byte lines; stderr retains16KiB.
Snapshot readiness has a10s deadline. Stop writes an owned marker; the native
window exits after GPU work completes. A2s deadline kills an unresponsive child.
Project close joins the viewport before the creator owner. Application exit has
a bounded wait/kill fallback. No edits or saves are automatically replayed.

## Actual proof and limits

Debug42/42, Release42/42 and both installed SDK consumers1/1 pass. All106 Python/Qt
tests pass, including16 workspace and3 viewport tests. Source and installed previews
in each configuration rendered a real-owner saved world, consumed a Win32 pointer
click, selected its UUID in Qt, changed actual GPU pixels for the highlight and
joined without changing revision/save bytes. All four runs observed the D3D12 debug
layer enabled and zero errors. See creator_viewport_verification.json and
creator-viewport-* logs in engine/out. Projection tests also reuse the real First
Boot seed and reject every truncation of their binary fixture.

Current costs include full snapshot files and mesh replacements. This is a separate
window, not an embedded viewport, streaming, incremental GPU editing, transform
gizmos or a performance benchmark. Full M4 and the personal alpha remain unfinished.


Current typed chapter integration: [CHAPTER_PLAY](CHAPTER_PLAY.md). Revision0.20
verifies native typed preview and isolated Play; earlier generic viewport limits
and historical counts above remain scoped to their original checkpoints. Live
AI generation and the complete personal alpha are still unfinished.
