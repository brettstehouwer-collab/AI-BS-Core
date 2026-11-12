# Combined gameplay and pacing review

When you choose to play, open `D:/AI-BS-Game-Resources/P47/CombinedOpeningReview` in File Explorer and double-click `Play_And_Measure_First_Boot.cmd`. Press Enter in its console to open the game. Use the main game's titlebar X when finished; do not close only the reading panel or the waiting console.

This is a separate SDK0.16.5 review build, using the same verified Studio103 art and Adam v10. It leaves installed Studio103, its launchers and existing saves untouched. The stable P44 manual-review launcher remains available. No test starts just because a file is inspected.

Explore normally, repair the main supply or build/connect the bypass, then reach the shelter/workbench and Pencil Room. Use Adam's existing guidance and the on-screen controls. Keep the game or its reading panel active. Switching to another app or minimizing invalidates this diagnostic sample. Reading, inspection and normal saving are included. A normal main-window close ends the measurement after at least15 measured seconds; it also has a15minute maximum. That is a safety bound, not a duration to wait for. Do not rush or stall to hit8–12minutes.

Afterwards, tell Codex which route you used, approximately how long you actively played excluding breaks, where you got lost or stalled, and whether Adam's guidance and the repair/build loop worked. Raw rendered duration includes reading and inspection; it cannot establish first-time pacing or qualitative acceptance by itself.

Each launch writes a small breadcrumb in `Launch_Attempts.log` beside the launcher. Python startup diagnostics are under `D:/AI-BS-Game-Resources/ReviewLaunches`; they exist even if SDK/resource validation fails before a game session is created. The console prints the exact diagnostic directory. A diagnostic attempt is not proof the game ran. No input, environment credentials or unrelated app data is recorded.

Actual game sessions, their separate retained test saves, feedback worksheets and raw performance reports are under `D:/AI-BS-Game-Resources/GameplayReviews/<unique-session>`. Validated measurements additionally get `result.json`; failed or interrupted runs keep their evidence and cannot become accepted samples. The native return code, saved ready/stopped lifecycle, world/timeline identity, immutable content fingerprint, actual1080p dimensions, mode flags, Present/time arithmetic, memory accounting and frame-time counters are checked. Runtime/shader/art pins are checked before and after the run. Human pacing remains unreviewed until actual feedback.

Developer inspection without starting a game: `python engine/tools/play_and_measure_opening.py` or run the launcher with `--inspect`. No desktop focus or input is forced. Cancellation joins only this launcher's retained native child. These review tools do not mark the opening, likeness or final package complete.
