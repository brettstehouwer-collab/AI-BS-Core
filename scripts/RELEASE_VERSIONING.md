# AI-BS source versions and recovery checkpoints

`C:\AI-BS\version.txt` is the application source version authority. Root, dashboard, and Broadcast Studio package versions, their root lock records, generated UI version modules, `release.json`, and the dashboard public version metadata are derived from it. Dependency versions are unchanged by this workflow.

## For each completed change set

1. Before editing, save exact copies of the affected source files in a clearly labeled dated folder under `C:\AI-BS\backups`. Record relative paths and SHA-256 hashes. Keep existing user edits. Manuscripts, Google Drive originals, and other created documents are retained in their labeled folders.
2. Complete and verify the change. Group related edits into one patch release; a version bump represents the change set, not every keystroke.
3. Run from the repository root:

   ```powershell
   npm run version:bump -- --label descriptive_change_set
   npm run version:check
   ```

   `version:bump` advances the patch number. It first saves exact copies of every metadata file it will replace under `backups\release_versioning\<UTC timestamp>_<label>_<unique id>\before`. The manifest records old and new SHA-256 hashes. `verified.json` records a successful check. It does not copy environment variables, credentials, manuscripts, or installed binaries.

4. Record the implementation, checks, and resulting source version in the current plan checkpoint. Build and publish only within the user's authorization. A source version alone does not prove deployment or binary rebuild.

## Commands

```powershell
# Read-only consistency check, also run automatically by both frontend npm prebuild hooks.
npm run version:check

# Repair only bounded metadata drift to the existing version.txt authority.
npm run version:sync -- --label metadata_alignment

# Explicitly advance to a reviewed version instead of automatically incrementing PATCH.
node scripts/release-version.cjs bump --version 5.330.0 --label reviewed_release
```

The helper rejects version downgrades, invalid versions/dates, unsafe checkpoint labels, external linked target paths, and metadata changed concurrently with its plan. It performs per-file atomic replacements; this is not a crash-atomic transaction across all files. If interrupted, review the checkpoint and `incomplete.json`, then rerun the consistency check. A leftover `.release.lock` requires checking that its recorded process has ended before manually recovering it.

## Scope boundaries

- Old installers, installed executables, update feeds, archived source, historical documentation, product-specific independent releases, and dependency versions keep their real versions. Rebuild and validate them before assigning a new artifact version.
- `frontend/public/updates/version.json` describes the older installer feed and is deliberately excluded. `frontend/public/version.json` describes application source used for the dashboard build.
- All generated `version.js` modules have identical contents. Runtime badges import these modules. Avoid new hardcoded release badges and avoid old recursive version sweep scripts.
- Some historical feature labels and independent subsystem badges may still contain older numbers. Those must be reviewed by meaning; never globally replace every version-like string.
- The standard dashboard `build` command currently runs the existing mirror sync. Release verification may choose direct `vite build` after an explicit `npm run version:check` to avoid unrelated mirror changes. Direct Vite invocation bypasses npm lifecycle hooks.
- This workflow keeps secrets out of checkpoints. Do not place environment or network secret values in Codex notes, release metadata, public bundles, or reports.
