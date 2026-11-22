# Current game build safety checkpoint

This archive consolidates the prior selected engine source snapshot, managed Qt client overlay, and current creator workspace source. It is a selected game-build backup, not a complete AI-BS workstation image. Restore to a separate review directory first; do not blindly overwrite unrelated work.

VERIFIED: full selected file bytes, per-file SHA-256, ZIP CRC and exact archive readback. Installed Studio 5.329.94 and public site 5.329.87 were not changed by this backup. Creator workspace changes are source-only.

FAILED: latest test_creator_workspace run has 1 failure among 13 tests: test_paged_refresh_never_publishes_a_mixed_revision. The Add button remains enabled after a stale paged refresh. The prior full Python run passed 99 tests before this new regression test was added. Both logs are preserved. No engine fixes or new test execution were performed during this backup request.

Next engineering step: inspect and repair stale snapshot control gating, run the targeted workspace tests and full Python suite, then continue native viewport/picking and editable chapter definitions. M4 remains incomplete.

The separate Unreal demo and walkthrough have existing independent Drive backups. Original memoir/photos, personal saves, credentials, models, dependency caches, generated executables and whole unrelated project trees are excluded from this selected source snapshot. Dependency manifests and relevant source/build configuration are preserved.

Storage guidance: keep source, assets, authored maps, project descriptors, saves, design documents, and unique evidence. Generated Intermediate/build caches may be rebuildable, but no files were deleted or moved. Historical backups and installed releases require individual review before removal. Uploading does not reclaim local space. Drive remaining quota is not exposed by the connector.

Cloud destination: https://drive.google.com/drive/folders/1AwSiCmdkm3o8v0hgD0sY9xYID_6JghV-
