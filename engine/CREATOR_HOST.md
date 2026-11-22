# Creator host SDK guide

`AIBS::CreatorHost` is the generic C++ authoring owner introduced during M4. It edits the existing numeric `CreatorSession` document through scoped, grouped transactions, exposes immutable snapshots and prepared previews, and separates authored state from a temporary Play World. Include `<aibs/creator_host.hpp>` and link `AIBS::CreatorHost`, or `AIBS::Engine`, which includes it.

This is a source SDK foundation. The companion native stdin/stdout owner now wraps this API; see [CREATOR_PROTOCOL.md](CREATOR_PROTOCOL.md) for that tested process contract. A visual creator workspace, native picking bridge, child Play process, editable chapter definitions and navigation validation remain unfinished. First Boot's protected chapter layout remains governed by its existing game-specific rules. Installed Studio5.329.94 and the public playground are separate retained deliveries; this document does not assert a newer installed release.

## Owner and document identity

Create a host by transferring a session, or open an explicitly selected checkpoint:

```cpp
aibs::CreatorHost host(std::move(session));

auto resumed = aibs::CreatorHost::open(
    checkpoint_path, schemas, "my-project", "main");
```

The constructor accepts `CreatorSession&&` and optional `CreatorHostLimits`. The host is noncopyable and has one single-threaded owner. Serialize access on that owner; its busy guard rejects reentrant mutating calls from dependency callbacks and is not a multithreaded synchronization mechanism. Construction and `open` can throw when admission or loading fails. Command methods generally return `CreatorHostResult` with a status, message and revision; check those results.

`CreatorScope` contains `project`, `branch` and `world_id`. Every submitted document command uses the complete scope, with the current authored revision where specified. A display alias such as `relay-core` is a map key; its `Entity::persistent_id` is the durable UUID. Sending an alias alone does not establish target identity. `epoch_id()` identifies this host lifetime and is distinct from the document world UUID and a Play epoch.

`open(path, schemas, project, branch, limits)` uses the existing `CheckpointStore::load` path and creates a new host epoch. It does not silently create a missing checkpoint. Core first applies its own bounded file decoder and replay validation; host limits are checked after that load. A custom small host budget does not reduce Core's earlier decoding allocations. Supply the intended schema/project/branch rather than interpreting arbitrary files as the current document.

## Read immutable snapshots

`snapshot()` returns `std::shared_ptr<const CreatorSnapshot>`. Its public fields are:

| Field | Meaning |
| --- | --- |
| `scope`, `revision` | Exact authored document identity and revision. |
| `world` | Read-only entity map; numeric fields and persistent UUIDs. |
| `history` | Original authoring `MemoryEvent` journal, including undo/redo events. |
| `schemas` | Read-only map of numeric field IDs and allowed bounds. |
| `checkpoint_id` | Last published checkpoint identity; empty before the first save. |
| `undo_depth`, `redo_depth`, `receipt_count` | Retained Core history and original apply-receipt counts. |
| `charged_bytes` | Conservative logical storage charge, not measured process memory. |

Each snapshot retains its immutable session owner. It remains valid after another document is published or the host is destroyed. Holding a snapshot therefore retains its World and history. Copy the shared pointer, not the noncopyable snapshot object. To inspect the current document after a successful mutation, obtain a new `snapshot()`; an older one deliberately continues to describe its original state.

Core also exposes `SchemaRegistry::fields()`, `CreatorSession::schemas()`, `undo_depth()`, `redo_depth()`, `receipt_count()`, `charged_storage_bytes()` and `accepted_transaction(id)`. The latter points to the original accepted request before UUID realization; it is a borrowed pointer invalidated by mutation. Do not retain that pointer across callbacks or owner mutations.

## Submit one grouped gesture

The following example creates an independent generic document, then prepares and applies a two-field edit. It does not touch a First Boot save.

```cpp
#include <aibs/creator_host.hpp>
#include <stdexcept>
#include <utility>

void edit_example() {
    aibs::SchemaRegistry schemas;
    if (!schemas.add({"x", -100, 100}) ||
        !schemas.add({"half_x", 0.1, 10}))
        throw std::runtime_error("Schema registration failed");

    aibs::CreatorHost host(
        aibs::CreatorSession(schemas, "creator-example", "main"));
    auto initial = host.snapshot();
    const auto uuid = aibs::new_uuid();
    const aibs::Transaction create{
        "example.create", initial->revision,
        {aibs::Create{{"cube", "Example cube",
                      {{"x", 0}, {"half_x", 1}}, uuid}}},
        "Created example cube"};
    if (host.apply(initial->scope, create).status !=
        aibs::CreatorHostStatus::applied)
        throw std::runtime_error("Creation rejected");

    const auto before = host.snapshot();
    const aibs::Transaction gesture{
        "example.move-and-resize", before->revision,
        {aibs::SetField{"cube", "x", 3, uuid},
         aibs::SetField{"cube", "half_x", 2, uuid}},
        "Moved and resized cube"};

    auto prepared = host.preview(before->scope, gesture,
        [](const aibs::CreatorSnapshot&,
           const aibs::CreatorSnapshot&,
           const aibs::Transaction&) {
            aibs::CreatorDependencyPreview result;
            result.render_rebuild = true;
            result.collision_rebuild = true;
            return result;
        });
    if (prepared.status != aibs::CreatorHostStatus::prepared ||
        !prepared.change)
        throw std::runtime_error(prepared.message);

    // The preview has not published anything to the live document.
    if (host.snapshot() != before)
        throw std::runtime_error("Unexpected publication");
    const auto& dependencies = prepared.change->dependencies();
    // Surface dependencies.save.compatible/message in an inspector.
    (void)dependencies;

    const auto applied = host.apply(prepared.change);
    if (applied.status != aibs::CreatorHostStatus::applied)
        throw std::runtime_error(applied.message);
}
```

`Transaction` contains an operation `id`, `expected_revision`, ordered `edits` and a description. `Create` requires an explicit valid persistent UUID; `SetField` and `Erase` require the target UUID. Core's older permissive omitted-UUID behavior remains available at Core level and is not accepted for new host submissions.

The host validates target aliases sequentially, so `Create → SetField` and `Erase(old UUID) → Create(new UUID) → SetField(new UUID)` work within one group. Invalid fields, non-finite values, stale UUIDs, duplicate/reused UUIDs, unknown targets, bounds failures or a revision conflict reject the whole group. A successful group creates one Core apply/history entry. Use one transaction for a completed transform gesture rather than a separate entry for every mouse sample.

`apply(scope, transaction, assessor)` is a convenience that prepares and then applies through these same checks. It does not bypass preview admission. There is no implicit save in either apply overload.

## Prepared changes and dependency checks

`preview(scope, transaction, assessor)` returns `prepared` and a private `CreatorPreparedPtr` on success. The token exposes only `snapshot()` for the candidate and `dependencies()` for its preview. Preview leaves the live snapshot, revision, journal and history unchanged. The request is frozen before invoking caller-provided observation code, preventing a mutable alias captured by a callback from changing the request accepted into the token.

Tokens bind an immutable shared host-owner identity, generation and before-snapshot identity. Foreign, stale and no-longer-admitted preparations reject. Apply re-runs the same assessor against the actual before/after snapshots and frozen request, then requires the refreshed preview to match the original. Changed dependency keys, notes, validity or rebuild flags require another preview. Do not put timestamps or other deliberately unstable values in an assessor result.

An assessor may return `valid = false` to reject the candidate and can describe render/collision rebuilds, dependency keys and explanatory notes. It is an observation function; it must not perform document mutations or rely on side effects. Reentrant host mutations reject while it runs. Captured objects must remain valid for as long as the token can be applied; ownership of arbitrary callback captures is the caller's responsibility.

The host supplies exact changed UUIDs and save compatibility itself. Generic `navigation_validated` remains false with an explicit note; an assessor cannot claim generic navigation validation by setting that flag. Real door/power/socket/quest/source relationships require a game-specific assessor and content definitions. The generic host does not infer those relationships from entity names.

The admission registry holds weak references to prepared tokens. Discard every client reference to abandon a preparation; expired entries are pruned on subsequent preview admission. Keeping a token intentionally retains its immutable candidate and assessor. Successful apply/history/save publication invalidates outstanding preparations. A previously accepted operation can still be recognized as a duplicate rather than being applied twice.

## Retry original requests exactly

Retain the original transaction for retry. Within the matching document scope, the host looks up the persisted original accepted request before current-head or live-target validation. An exact retry can therefore return `duplicate` after its target was deleted, its change was undone, or the document was saved and reopened. It adds no revision, event or effect. A duplicate result identifies the original accepted revision; refresh `snapshot()` to read the current head.

Request comparison at this boundary includes double bit patterns, including `+0.0` versus `-0.0`. Reusing an operation ID with different content rejects, even if the old Core equality would consider the numeric values equal. Core equality and checkpoint format1 are unchanged. Do not generate a new operation ID merely because delivery acknowledgment was lost; that represents a new operation rather than a retry. Reopen can recover only requests preserved by the last successful checkpoint.

## Undo and redo use host-epoch requests

There are no separate public `CreatorHost::undo()`/`redo()` methods. Call `travel` with a `CreatorHistoryRequest`:

```cpp
const auto head = host.snapshot();
const aibs::CreatorHistoryRequest undo{
    "inspector.undo.1", host.epoch_id(), head->scope, head->revision,
    aibs::CreatorHistoryDirection::undo};
const auto result = host.travel(undo);
```

Use `CreatorHistoryDirection::redo` for redo. A new request checks the live scope/revision and available history, then publishes the result atomically. Retrying the same request in the same host epoch returns `duplicate`; reusing its ID with different content rejects. New requests need their own IDs and the then-current revision. Successful history travel invalidates preparations and advances the authored revision.

The document's Core undo/redo stacks are saved. The caller's host-level history request receipts are not durably recorded by format1. Reopening creates a new host epoch and rejects old-epoch requests. Do not interpret retained undo history as a promise of cross-restart exactly-once undo/redo command delivery.

## Save explicitly and inspect compatibility

`save(path)` uses the existing scoped format1 checkpoint publisher. It does not select a default user slot. Ensure the parent directory exists and choose an explicit path for the document. An existing slot must match the world/checkpoint head; another owner changing that slot requires reload/reconciliation rather than an overwrite assumption.

On success, the result is `saved`, the checkpoint UUID changes, and prepared tokens are invalidated. Authored revision does not change. Older immutable snapshots retain their old checkpoint identity. A first save adds a36-character checkpoint UUID; the host reserves this logical storage growth before filesystem publication. A session already exactly at its budget may consequently reject its first save before a file is written.

On failure, `save` returns `rejected` with a diagnostic and retains the current authored snapshot, revision, checkpoint identity and admitted preparations. A failed save does not turn a previous in-memory apply into a durable one. A `.lock` artifact may exist from the underlying lock/open attempt; failure does not promise zero filesystem activity. Use the returned message to distinguish unavailable directories, a busy or stale slot, encoding limits and write/publication failures.

`CreatorDependencyPreview::save` is a `CheckpointAssessment` containing `compatible`, `encoded_bytes` and `message`. `CheckpointStore::assess(session)` is also public for bounded Core callers. It copies the complete session, supplies a fixed-width placeholder checkpoint UUID if needed, and runs the exact existing format1 validation/encoder without creating files or publishing a checkpoint. Compatible encoded bytes match that format's output size; compatibility does not establish free disk space, lock availability or successful durable publication.

The original16MiB file bound is not the only constraint. For example, undoing a change in a5,001-entity World produces5,001 erase plus5,001 create journal edits:10,002 items exceed format1's10,000-item collection limit even though the live entity count is below the host's default10,000. Legal individual strings can also yield excessive cumulative replay work. Assessment reports these actual collection/string/replay-byte failures. A candidate can be admitted in memory while reporting incompatible saving; display that consequence before publishing rather than calling all admitted states save-compatible. Existing original checkpoint formats are not silently expanded by the host.

## Play remains isolated in process

`start_play(scope, expected_revision)` returns `playing` when it creates a separate `CreatorPlaySession`. Only one is active in a host. `play()` returns its shared pointer, with immutable `epoch`, `scope` and `authored_revision`, and a mutable copied `world`. Edits to that World do not change the authored document, its memory, undo history or saved checkpoint.

`stop_play(play_epoch)` requires the matching active epoch, returns `stopped` and releases the host reference. A client retaining the Play pointer can keep using its isolated copy; Stop does not revoke that memory. Starting a later Play creates a different epoch. These calls do not launch or stop an OS process, save gameplay progress, execute the full chapter, or apply simulated changes back to authoring. Child lifetime management and explicit apply-back remain future contracts.

## Logical admission limits

Pass an optional `CreatorHostLimits` to construction or `open` to lower or intentionally configure these defaults:

| Setting | Default |
| --- | ---: |
| `maximum_live_entities` |10,000 |
| `maximum_fields_per_entity` |64 |
| `maximum_string_bytes` |4,096 |
| `maximum_edits` |256 |
| `maximum_request_bytes` |1MiB logical request charge |
| `maximum_session_bytes` |64MiB logical session charge |
| `maximum_prepared` |8 admitted retained tokens |
| `maximum_prepared_bytes` |64MiB aggregate prepared logical charge |
| `maximum_history_receipts` |1,024 host-epoch history receipts |

Session charge uses saturating accounting for schema, scope strings, live World, used/retired UUID evidence, journal, original apply receipts and both full Worlds in every undo/redo entry. Request/candidate accounting includes their owned content and defined overhead. Rejections do not prune authored history to fit a budget; choose a deliberate document/branch workflow when limits are reached.

These are logical admission limits. They do not measure or cap RSS, allocator spare capacity, temporary Core copies, arbitrary assessor closures or snapshots/Play Worlds retained by callers. Preview and exact save assessment can stage additional complete session copies. Limits are checked around those operations but are not a no-allocation or fixed-RSS guarantee. Expired weak preparation entries release admission slots, not client-owned objects. The host loads under Core's codec bounds before applying its own document limits.

## Build and verify

Use the configured Windows x64/MSVC toolchain from `C:\AI-BS\engine`. The existing prerequisites and pinned dependencies are described in `README.md`; no new dependency is required for the host.

```powershell
Set-Location C:\AI-BS\engine
python -m cmake --preset windows-msvc
python -m cmake --build --preset debug --target aibs_creator_introspection_tests aibs_checkpoint_assessment_tests aibs_creator_host_tests aibs_creator_host_contract_tests
$creatorCtest = python -c "import cmake,pathlib; print(pathlib.Path(cmake.CMAKE_BIN_DIR)/'ctest.exe')"
& $creatorCtest --test-dir out/windows-msvc -C Debug -R '^(creator_introspection|checkpoint_assessment|creator_host|creator_host_contracts)$' --output-on-failure
```

Repeat using `--preset release` and `-C Release`. The four CTest names cover read-only introspection, exact checkpoint assessment, the original grouped host fixture and expanded host validation. See their actual logs and `BUILD_STATUS.md` for results; this guide deliberately does not freeze a count while contract cases are being expanded.

The existing installed-SDK consumer is `examples/sdk_consumer`, whose `main.cpp` uses `CreatorHost` to preview/apply, save/reopen and retry an original request through installed targets. Full verification builds the engine/tests, installs matching configuration outputs, then configures and runs that separate consumer:

```powershell
Set-Location C:\AI-BS
powershell.exe -NoProfile -ExecutionPolicy Bypass -File engine/scripts/verify.ps1 -Configuration Debug
powershell.exe -NoProfile -ExecutionPolicy Bypass -File engine/scripts/verify.ps1 -Configuration Release
```

For a separate client, use `find_package(AIBS 0.8 CONFIG REQUIRED)` with `CMAKE_PREFIX_PATH` pointing to the intended `engine/install/debug` or `engine/install/release`, then link `AIBS::CreatorHost`. Rebuild C++ consumers when public headers change; this source addition does not assert binary ABI compatibility with older libraries.

M4 completion still requires the managed bounded process/Qt bridge, usable creator UI and native selection, editable content definitions, game-specific dependency/migration previews, and repeated isolated chapter Play/Stop proof. A passing generic library fixture establishes this slice, not those unfinished systems or the complete First Boot alpha.
