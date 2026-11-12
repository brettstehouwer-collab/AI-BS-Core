# Native First Boot durable world — SDK0.7

The new native PC mode connects the typed gameplay store and save worker to real First Boot movement, interaction, collision and DX12 rendering. It is a separate mode/save from the original numeric checkpoint prototype and MovementCourse. It is still the small motherboard building yard, not the complete Jenison-to-Pencil-Room chapter.

## Run and controls

```powershell
engine/install/release/bin/aibs_motherboard.exe --durable-world
```

The source AI-BS game-build workspace has a dedicated **Launch durable First Boot world (PC / DX12)** button. Consult BUILD_STATUS for the actually deployed Studio version; an older frozen Studio package does not gain new source code automatically.

WASD/arrows walk; right-drag looks; Space jumps; Shift sprints; V changes first/third-person view; F2 enables inspection flight. E/left-click repairs a selected core or relay. B places a relay along the board-relative placement ray. Delete dismantles a relay. F5 retries a failed save. F9 reloads committed state at a clear entrance. Esc/window close waits for pending saves. Original mode retains its Ctrl+Z/Y history; typed gameplay history editing belongs to the later creator work.

Default database: `%LOCALAPPDATA%/AI-BS/FirstBootDurableWorld/world.sqlite`. `--world-db PATH` selects a different dedicated database. Startup validates the AI-BS database and registered game data and selects exactly one matching First Boot/main/player timeline. Ambiguous/foreign scopes reject; no arbitrary save is overwritten or silently reset. Original checkpoints remain at their existing paths.

## Actual game state

`AIBS::DurableFirstBoot` is a separate game SDK target over FirstBoot, GameplayWorld and LegacyImport. Registered `firstboot.Node` v1 components preserve UUID, alias/name, alive state and every original numeric field. Only alive nodes enter render/collision projection. Dismantled relays retain their complete tombstone; IDs and aliases cannot silently become a different typed entity. Imported historical UUIDs are also checked against the preserved original identity registry.

Repair records actual before capacity and an after value of100. Construction creates a declared relay recipe and matching build outcome. Dismantle marks an existing live relay dead and records that exact result. Base geometry/names cannot be changed by these actions; false outcomes, unsupported schemas, retired-ID reuse and invalid candidates reject. Healthy repair and already-dismantled operations are no-ops. SDK callers retain the immutable original request for exact retries; creating a fresh action creates a fresh identity.

The board-relative placement helper preserves the prototype offsets while supporting elevated/shifted authored boards. Ray and field limits remain explicit. Candidate world validation rejects a construction that removes every supported spawn; occupied-player collision also rejects before publication. The bounded spawn grid still does not promise to discover every narrow gap.

## Visibility, saving and close

The app prepares a typed candidate, validates its game rules, and stages collision/GPU geometry before publication. It draws or simulates no intermediate candidate frame. Save capacity is reserved before GameplayWorld installs visible state and activates its worker. Rejection restores the previous dependencies; a failed dependency rollback is fatal rather than drawing a world that was never accepted.

The HUD distinguishes visible and acknowledged durable revisions, SAVING, UNSAVED/RETRY and SAVED. Completion polling continues while focus/minimize pauses simulation. F9 refuses while saving or failed; a rejected reload retains the live world. Closing stops new actions but keeps the window and unsaved memory alive until successful storage completion. If saving fails, F5 remains available. Only then does the app close/join the owner. Forced process termination still loses uncommitted work; restart restores the atomic committed state.

This alpha integration stages dependencies through existing APIs and may allocate/copy or wait for GPU work during edits. It is not the later streamed nonthrowing publication system. Player/camera pose remains transient; reload starts at a validated entrance.

## Adam and original saves

Authored current guidance follows the visible world. Committed recall follows the acknowledged durable head, including the case where SQLite has committed but the owner has not consumed its completion. A failed visible repair cannot become a remembered completed action. Recall is cached when the visible or durable head changes, stays bounded, and needs no model/network service.

Explicit non-destructive migration into a **new** database:

```powershell
engine/install/release/bin/aibs_motherboard.exe --durable-world --world-db C:/chosen/new-world.sqlite --import-checkpoint C:/chosen/original.aibs
```

The importer captures the source once, validates the captured original schema and game topology/spawn, projects typed state and retains the complete original bytes atomically. It preserves original world/entity/retired UUIDs, revision, receipts, undo/redo and Adam edit records. The original file remains unchanged. Reopen the new database without the import flag. Later typed deltas are recovered from SQLite; restoring the archived old CreatorSession would restore only its original baseline.

Imported original edit recall is labeled separately from new semantic gameplay. Neither source descriptions nor authored guidance are presented as historical quotations from the real Adam. The personal story and selected Echos Within material remain their own source layer.

## Evidence and limits

The native process/GPU driver exercises repair/build/dismantle through shared Win32 input handlers, exact rendered restart equality, F9, tombstones, saved UUIDs/events, interruption before/after COMMIT, lost-completion exact retry, actual save failure/F5, deferred close while minimized, and original checkpoint import. The native HUD's actual Win32 label text is checked at pending, failed and saved phases. Verification arguments require an explicit database; malformed proof arguments do not open prompts or create default player data.

Actual configuration/results: BUILD_STATUS and `out/durable_world_verification.json`. These tests use synthetic explicit databases and the current machine's DX12 adapter. They do not certify physical power-loss behavior, arbitrary filesystems, every driver or the full story alpha. Store/worker/import limits remain in GAMEPLAY_CONTRACT. CPU/GPU performance profiling, assets/audio, full creator, campaign branches, vehicles, streaming and the phone companion remain later milestones.
