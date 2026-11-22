# Adam neck surface: failed correction retained

2026-11-04T02:30:27.304813+00:00. Status: FAILED; two-strike diagnostic halt. This checkpoint is evidence of an unsuccessful bounded art operation, not a completed v25 character or a passing gameplay release.

Native v24c close-ups show an uneven neck surface. Read-only inspection locates nonuniform neck geometry around the earlier head/body transition. The first skin-only Taubin fairing attempt preserves non-neck anchors, UVs, weights and binds but fails triangle guards: area ratio0.18294 and normal dot-0.97647. An in-memory diagnostic retains the32 offending triangles/85 vertices without saving a candidate. No assertion is removed.

The second algorithm admits each local update only when incident triangles retain at least0.45 area ratio and0.65 normal dot. The final orientation/area checks pass, and weighted roughness energy falls from0.01338367 to0.00611128. However maximum displacement is12.480mm, above the original8mm bound. It fails before saving. These values do not establish a usable correction or approved anatomy.

Stop repeating both smoothing recipes. The likely remaining flaw is missing cumulative-displacement enforcement during update admission. A reviewed repair must enforce triangle integrity and movement bounds together, or replace the local transition topology; the original final assertions remain applicable. Do not increase the bound simply to pass this result.

All owned processes are joined. There is no new v25 master, GLB or cooked asset. The v24c master is SHA-identical, all2,301 installed Studio106 files are unchanged, and no engine/SDK, real save or original family reference was modified. The previous v24c/72A verified art checkpoint remains available. These diagnostics can be backed up as a verified archive of a failed operation; the product status remains FAILED.

Other work remains available: naturalistic hair/clothing refinement and the prepared Studio106 human opening review. Caption listening review and first-time pacing/performance remain pending. The full goal remains active and incomplete.
