# Manual First Boot review

The installed Studio103 opening can be reviewed using a fresh retained test slot:

`D:/AI-BS-Game-Resources/P44/ManualOpeningReview/Play_First_Boot_Review.cmd`

Nothing opens until you run the launcher and press Enter. It verifies the installed Studio103 player and six curated asset packs, creates a separate chapter and player database on D:, and opens normal native Play at 1920×1080. Existing personal saves, releases and references are untouched. The test save and logs remain in `D:/AI-BS-Game-Resources/OpeningReviews/<unique-session>/` after closing.

Explore the warm nook, use Adam's current guidance, and choose either repairing the supply or building and connecting the relay bypass. Continue to the real shelter/workbench and Pencil Room. Use the on-screen controls. Close the game normally when finished; wait for saving to finish before closing the console. Do not feel obliged to finish in a particular time.

Afterwards, tell Codex:

- Which route you used and whether you reached shelter and the Pencil Room.
- Approximately how many minutes you actually played, excluding breaks.
- Where you were lost, stalled, rushed, or uncertain which action to take.
- Whether Adam's guidance helped and the repair/build loop felt satisfying.

A blank `feedback.json` is also retained with the session. It stays unreviewed until actual feedback is supplied. The console records launch-to-exit elapsed time, including startup, menus and waiting. That is not a measurement of active gameplay, first-time pacing acceptance, or FPS. No input is automated and no desktop focus is forced. The separate stationary benchmark remains unchanged. Whole-opening frame-time instrumentation is still required.

Developer inspection without launching: `python engine/tools/review_opening.py`. Interactive launch: add `--run`. Ctrl+C requests graceful shutdown of this launcher’s own child, then joins it; only that retained child may be stopped if it cannot close. This helper is source-side tooling and does not replace installed Studio103 or its shortcuts.
