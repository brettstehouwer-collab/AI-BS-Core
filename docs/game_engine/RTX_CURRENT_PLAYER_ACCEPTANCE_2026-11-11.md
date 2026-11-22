# Current player and qualified LH asset — November 11, 2026

## Verified controlled hidden load/reload

`engine/tools/qualify_rtx_current_player.py` admitted the frozen current HUD
player (`60ee067f229e040a359e302bb90def884d49223af5a616e6065d9fced1583cda`),
its nine artifact pins and all 158 compiled-source pins against canonical source.
It copied the complete Creator v05 project and immutable asset store into a new
owned directory, with a fresh SQLite database and a new temporary-play session.
No original game database or original asset master was admitted or modified.

Retained result:
`D:\AI-BS-Game-Resources\RTX_Variants_20261111\Player_LH_20261111_v02\qualification.json`.

Two distinct native processes seeded and reloaded the same temporary timeline.
Both exited normally with code zero. Full runtime components, event history,
scope, content identity, revision and sequence remained equal. The final
content revision is 6 and export fingerprint is
`03d41a2bc1e400d9bf507613b11398c95ee7c84246deef2a2ee967188c2baf20`.
Both reports acknowledged saved state and no pending batches, with the actual
internal F9 reload flag present only in the reload process.

At 1440×900 both actual native GPU reports show debug-layer enabled, zero errors
and warnings, and more than 10,000 nonbackground pixels. Actual HUD text readback,
capture and text-fit checks passed. All 22 generated BMPs were independently
checked for complete BMP headers, dimensions and pixel payload lengths after
the run. The HUD image was visually inspected and contains readable controls,
switch direction, companion instructions and the SAVED status. This is a hidden
controlled capture, not an observation of ordinary desktop play.

## Retained failed small-window check

The first fresh run, `Player_LH_20261111_v01`, failed the qualifier's HUD-fit
requirement at 960×640. The native process itself exited zero with a saved world,
working capture and zero graphics debug errors/warnings. Its HUD needed 629
pixels of height but had 616. The native report's general `status: passed` does
not override this failed acceptance assertion. All failure files remain intact.

The second run used the normal player's 1440×900 dimensions explicitly; it did
not fix or waive small-window support. At this size the HUD needed 407 pixels and
had 411. Small-window layout remains an explicit outstanding repair/regression
gate. Neither the frozen player nor its source was altered by this qualification.

## Qualification boundaries and next step

This establishes controlled current-player asset dependency loading, rendering,
HUD and temporary-world reload. Static authored placements are retained in the
immutable content and are not one-for-one runtime ECS rows; do not compare the
creator's 116 authoring rows to the runtime's 65 components as an equality test.
The content fingerprint binds the entire authored placement and dependency
definition; this test is not a new independent art-view acceptance.

Persistent `SavedChapterPlayClient` READY → stop → STOPPED → fresh resume is a
separate gate, using another new copied project and retained slot. The current
player must be supplied explicitly: the creator's retained SDK host otherwise
finds its older sibling player first. Installed Studio/default-launcher parity,
ordinary human play, Nsight profiling, performance and full release remain open.
No provider inference, business activation or deployment follows from these tests.

## Actual saved-player lifecycle and long-path repair

The genuine source ContentView/SavedChapterPlayClient path passed in fresh
`Saved_Player_LH_20261111_v03`. The current player was supplied explicitly,
without bypassing capability checks. Players35716 and34920 and host36476 each
closed normally with retained exact-handle exit0. New play-session IDs resumed
the same retained database, content publication, initialization claim and
timeline; READY/STOPPED heads stayed0/0. The actual closure is one dependency
and four published files, not the old test fixture's six dependencies. No model
or network attempts occurred; all12 original creator-project files are unchanged.

This run exposed and repaired two real Windows MAX_PATH defects in
`native_studio/game_engine/saved_play_storage.py`: per-file inspection of a
292-character staged asset, then recursive reuse cleanup from a short staging
root containing long descendants. Windows I/O-only extended spellings now cover
inspection, handles, reads/writes, enumeration, directory publication and owned
staging cleanup. Public paths, content identities, reparse rejection, parent
handle pinning and payload hashes retain their contracts. Recursive cleanup
forces extended spelling even when its root is short.

A new synthetic regression reproduced the defects before their fixes, then
passed publication/reuse, tamper refusal and preservation of an opaque save
sentinel. All19 existing storage/security tests also passed. Their legacy
copytree fixtures required child-only extended TEMP spelling; no global setting
changed. Intermediate test failures and complete production preimages remain
under saved-player v01/v02. The exact source patch is
`docs/agent_sync/RTX_SAVED_PLAY_LONG_PATH_2026-11-11.patch`.

This qualifies observed long asset publication and saved lifecycle at this
fixture depth. Stop markers were217 characters; saved_play.py still uses plain
marker I/O, so arbitrary-depth project support is unqualified. No gameplay
actions were supplied, and human pacing, performance, default launcher,
installed Studio and release remain open. Next repair the retained small-window
HUD failure before broadening gameplay/performance qualification.
