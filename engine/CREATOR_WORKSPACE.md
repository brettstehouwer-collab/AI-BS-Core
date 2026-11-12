# AI-BS creator workspace

The source AI-BS game-build module now contains a lazy **Creator** tab alongside
the existing Build progress view. It uses the installed native creator owner
through `CreatorClient`, rather than a Python copy of the engine. Installed
Studio 5.329.94 and public website 5.329.87 have not been replaced.

Create a project in an explicitly selected existing directory, or open a saved
project. `.aibs-project.json` records the project, branch and numeric schema;
`world.aibs` is written only by an explicit native Save. New metadata is bounded,
strictly validated and exclusively published without replacing existing metadata
or worlds. Selected project folders remain in the browser for this widget's
lifetime; automatic filesystem discovery is not implemented.

The outliner selects persistent UUIDs, never aliases as identity. Add, Delete and
SDK transaction submission use native private Preview then Apply. Inspector
changes form one grouped transaction with explicit UUID targets; Preview alone
does not publish the candidate. Save compatibility comes from the actual native
codec assessment. It is not a geometry, route, socket, navigation or quest
dependency assessment. Undo and Redo use native history. Save/reopen preserves
the actual world and entity identities.

Snapshot pages are pinned to a scope, revision and checkpoint. Rows are published
only after all pages validate. When a concurrent SDK edit makes paging stale,
the previous rows remain visible but read-only; Refresh retrieves a coherent
snapshot before editing resumes. Failed refreshes do not repeat close/save
dialogs. No edit, save or recovery request is silently replayed.

Close waits for pending operations and the owned QProcess. Unsaved changes need
Save, explicit Discard or Cancel. A failed save cancels closing. Interrupted
operation recovery remains memory-only, as described in CREATOR_CLIENT.md.

Current projects use seven generic numeric fields: x/y/z, half_x/half_y/half_z
and capacity. These projects are not the protected First Boot chapter template.
Native 3D preview/picking now operates in a separately owned window; see
CREATOR_VIEWPORT.md. Chapter-aware content/dependency previews and an owned
native Play/Stop window are required next. Native host
in-process Play is an isolated World copy, not a playable PC viewport. M4 and the
20–30 minute personal alpha remain unfinished.

Verification: `python -m unittest discover -s engine/tests -p test_creator_workspace.py`
passes 16 tests, including actual installed-host and native-window integration.
The complete Python/Qt suite passes 106 tests. `creator-workspace-page-red.log` preserves the reproduced
stale-controls defect; `creator-workspace-page-green.log` verifies the fix.
`creator-workspace.png` is an actual Qt widget capture, not native 3D rendering.
`creator-workspace-ui-proof.json` records private-preview/save invariance and
joined child-process evidence. The later native viewport slice reran both complete
42-test native matrices and installed SDK consumers; see CREATOR_VIEWPORT.md.
