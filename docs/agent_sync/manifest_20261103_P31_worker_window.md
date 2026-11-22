# Worker/window lifecycle checkpoint31


## Checkpoint31 worker/window lifecycle (2026-11-03T13:35:45.753698+00:00)

Implemented bounded EngineBus stop with explicit real-join result, retained runnable/signal owners, queued GUI delivery fences and one-shot drained notification. Finished signals are not treated as native return barriers; queued clear tasks no longer remain permanently active. The GUI close path uses0ms worker/sampler requests and waits asynchronously for both native barriers, with one-shot teardown, completion-race/repeated-close handling, final snapshots for both live chat owners, and preserved save veto/edit/retry while chapter shutdown is pending. A teardown exception retains the window. Closed chat entry points and late save acknowledgments are inert. Legacy worker3000ms/sampler2000ms defaults are retained.

Evidence: controlled REDs before implementation;8actual Qt pool tests and59 recovery/executive/shared-chat/window/sampler tests pass (67distinct). One actual source MainWindow opened, responded and closed with exit0; its entire owned Job joined without forced termination. This is source integration proof, not a frozen package/full-tab or causal SIP-crash claim. Static closure108declared/107source/106local dependencies passes. Studio100all2301files/five shortcuts and Studio101all2301files remain exact. No C++/SDK/GPU/render change or family-reference edit. Earlier private debugger stays halted/unvalidated.

Known limits: completed wrappers await a whole-pool barrier during continuous overlapping work; measure real memory. Final chat lock/fsync remains synchronous. Fresh Studio102 build and actual packaged normal close/playable acceptance remain required before deployment. Full Adam likeness,8–12minute pacing,1080p60 performance, current walkthrough and final complete source/art backup remain pending.31A is a selected source/evidence increment.

31A backup closeout (2026-11-03T13:38:13.629762+00:00): authenticated Drive raw restore verified whole archive SHA256/size and all57members exact membership/SHA256/size/CRC. Selected source increment, not full project/art restoration. Receipt: docs/game_engine/checkpoints/2026-11-01_Warm_Beginning_Workshop/checkpoint31A-drive.json. Goal remains active and incomplete.
