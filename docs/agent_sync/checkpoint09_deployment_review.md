# Checkpoint09 deployment review

Read-only review on 2026-11-02 by the character renderer/transport agent. No
launcher, installed release, production, build-progress or deployment state was
changed by this review. Findings are a point-in-time snapshot while the parent
agent continues implementation and verification.

## Retained baseline and present readiness

- VERIFIED: `native_studio/releases/v5.329.97/AI_BS_Studio/AI_BS_Studio.exe`
  exists (34,225,379 bytes). `engine/install/0.10.0/release/bin/aibs_motherboard.exe`
  exists (3,191,808 bytes). Keep both as rollback artifacts; do not replace their
  contents or relabel them as SDK0.11.
- VERIFIED: `engine/install/0.11.0/release/bin` exists separately, with all native
  hosts, player, asset cooker and a capabilities declaration identifying0.11.0.
  Installation alone does not establish current-source equivalence or new
  character feature acceptance.
- VERIFIED: inspected Executive/Sovereign Studio shortcuts on the local and
  OneDrive desktops still target Studio97. Other unrelated shortcuts were only
  read and must not be promoted.
- NOT READY at review: `read_build_progress` reports a historical passed
  `warm-beginning-indexed-guide-source-sdk-tested` observation completed
  `2026-11-02T05:47:25.940561+00:00`, but runtime source freshness is **changed**.
  Documentation freshness is separately **changed**; source inventory is complete.
  Do not turn the historical pass into a new pass without the current checks.
- Storage observation: C:83,040,661,504; D:181,025,435,648; E:146,813,599,744 free
  bytes. None crosses the monitor's20GiB low-space threshold. This observation
  does not grant a remote Drive quota or prove upload integrity.

## Concrete packaging gaps found

1. `scripts/build_native_game_release.py::NATIVE_PLAYER_ASSETS` and
   `scripts/verify_native_creator_release.py::ALLOWED_ASSETS` list only the two
   motherboard shaders. Runtime SDK0.11 additionally reads
   `textured.vs.cso`, `textured.ps.cso`, `shadow.vs.cso`, `character.vs.cso` and
   `character.ps.cso` from the adjacent shaders directory. Include and verify
   all five, the asset cooker for editing, and the actual installed third-party
   notices for image decoding and cgltf. Existing CMake install rules already
   install these shader outputs. Do not weaken the package allowlist.
2. `native_studio/game_build_view.py::_asset_workspace_paths` and Chapter
   creator selection prioritize installed0.10 over the current build. Add the
   verified installed0.11 prefix before0.10, preserving frozen-bundle priority
   and retained fallback behavior. Otherwise a newly changed source UI can
   select an old host/cooker and correctly refuse its new capabilities.
3. The source authority is currently `v5.329.97`, and the matching release
   directory already exists. The builder correctly refuses to overwrite it.
   Advance the source version once for the tested delivery and use a fresh
   staging/release path. Do not mutate old release files to simulate a new build.
4. Existing frozen smoke entry points cover monitor, creator, asset and
   placement/reopen behavior. They do not by themselves prove the new typed
   character closure, four named clips, GPU material route or AIBD3 model
   binding across restart. Add the current native/Qt integration evidence to
   the release checks; preserve those existing smoke gates.

## Companion model-reference authoring review

VERIFIED risk at review: `content_jobs.py::ContentProposalJobs.begin` excludes
AssetPlacement immutable reference fields and the chapter profile, but exposes
the four CompanionBinding fields `model_bound`, `model_asset_id`,
`model_asset_sha256`, `model_pack_sha256`. `content_proposals.py::encode_proposal`
rejects only the three placement reference names. Consequently a model-generated
proposal can carry a partial or arbitrary companion reference through Python
admission, despite the inspector directing assignment through verified adoption.
Native validation remains authoritative, so this is not a claim of an accepted
invalid pack or successful unauthorized runtime publication.

Recommended correction, assigned by the parent after this review: first record
a failing focused test, exclude those four fields from AI job capabilities and
reject those four names in proposal encoding. Preserve editable name,
spawn coordinates and initial-follow intent. The explicit Preview Adam model
action continues to send one grouped four-field native Preview followed by the
user's Apply and Save.

## Executable delivery sequence for the parent

These are proposed commands, **not commands run by this reviewer**. Resolve
current build sessions first. Use the same Python environment/minor version for
PyInstaller and static verification. The example98 paths assume the source
version is still97 and98 has no existing release; otherwise select the actual
next unused version. Keep SDK0.10 and Studio97 untouched.

```powershell
# After code freeze and focused character/native/Qt acceptance:
powershell -NoProfile -ExecutionPolicy Bypass -File C:/AI-BS/engine/scripts/verify.ps1 -Configuration Release
powershell -NoProfile -ExecutionPolicy Bypass -File C:/AI-BS/engine/scripts/verify.ps1 -Configuration Debug

# Group the verified delivery into one source release; helper saves exact old metadata.
npm run version:bump -- --label warm_beginning_character_pipeline
npm run version:check

# Builder rejects reused work/output paths and freezes the declared module/input graph.
python C:/AI-BS/scripts/build_native_game_release.py stage --work C:/AI-BS/backups/native_game98_checkpoint09 --output C:/AI-BS/native_studio/releases/v5.329.98 --include-player --native-sdk C:/AI-BS/engine/install/0.11.0/release --asset-pack C:/AI-BS/engine/assets/cooked/motherboard-reference
python C:/AI-BS/scripts/build_native_game_release.py build --work C:/AI-BS/backups/native_game98_checkpoint09
python C:/AI-BS/scripts/verify_native_creator_release.py --work C:/AI-BS/backups/native_game98_checkpoint09 --report C:/AI-BS/backups/native_game98_checkpoint09/static_package_verification.json
```

Run these packaged entry points as separate owned processes, with absolute fresh
report paths and existing service-management/background-update flags disabled:

```text
AI_BS_Studio.exe --game-build-smoke <fresh-monitor-report.json>
AI_BS_Studio.exe --creator-release-smoke <fresh-creator-report.json>
AI_BS_Studio.exe --asset-release-smoke <fresh-assets-report.json>
AI_BS_Studio.exe --placement-release-smoke <fresh-create-report.json>
AI_BS_Studio.exe --placement-reopen-smoke <fresh-reopen-report.json> --placement-source-report <create-report.json>
```

Require exit0, report `status=passed`, real frozen-process identity, no source
fallback, complete joined-child cleanup, unchanged retained baseline and the
specific new character/native closure acceptance. Static package verification
establishes staged/frozen source and assets, not runtime, signing or web parity.

Before promotion, back up exactly the existing five approved Studio shortcuts
from the prior deployment inventory; compare their current target/arguments,
working directory and icon. Point those shortcuts at the fully verified fresh
executable, then read those properties back and verify executable hash/version.
`Launch_Native_Studio.bat` is a historical source launcher that starts ecosystem
daemons; it is not the retained frozen97 desktop path and should not be used as
the deployment smoke mechanism.

Update ledger/build monitor with actual current verification receipts and keep
code/content freshness separate from this documentation change. Back up source,
SDK additions, editable derived art and proof receipts to the existing organized
Drive collection with a local file manifest and remote metadata readback. Keep
family originals outside distributable packs, real saves and the separate Unreal
demo unchanged. Firebase hosting is an independent web deployment; native
Studio packaging does not prove the new web UI is deployed.
