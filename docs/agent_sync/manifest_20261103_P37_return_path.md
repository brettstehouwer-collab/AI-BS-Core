# Return path fix; current tour still incomplete


## P37 current Workshop return-path fix (2026-11-03T15:38:12.751901+00:00)

P37 traced the bypass-note return failure to actual feet(-43.118,0,-6.682), where reversing the ideal approach clips a fixture. Added bounded collision-checked return doglegs using actual feet, with no actor reset or teleport. Registered CPU test passes;27checks include both retained failed snapshots, blocked-wall denial and actual PlayerController W movement through the post-door shelter corridor. Strict candidate build passes. NativeR04 passed the old failure, completed main repair/testing and door crossing, then timed out approaching shelter. Two runtime failures this turn are retained/joined; retries halted. Timeout now records exact feet, active/held-input/minimized/foreground state for the next diagnostic. Full tour/recording/performance/pacing and deployment remain unverified.

This changes diagnostic traversal/planning and timeout observation only; ordinary input, collision/rules, content IDs, saves and legacy tour selection remain intact. Actual steady-clock traversals stay distinct from CPU query simulation and human pacing. Next: Run the freshly compiled instrumented current tour in a new owned timeline and inspect its exact timeout input/focus/feet evidence. Preserve the earlierR03/R04slots. Correct diagnosed input/route handling, complete both canonical routes, then record and measure. Do not infer whole-opening completion from CPU checks.
