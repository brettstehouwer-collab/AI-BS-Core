# AI-BS Dashboard web release v5.329.109

**Deployed and verified:** https://ai-bs-dashboard.web.app

Hosting version `cc4229899104e8ba` is the exact version tested on the preview channel. The previous web release, v5.329.97, is preserved in rollback channel `pre-web-v109-20261104-210648`. The release date is November 4, 2026 in America/New_York; machine receipts use UTC.

## Included updates

The release includes the current Studio overview and styling, financial/runtime availability states, and the separately coordinated BS-chat OpenAI provider selection, conversation history and error handling. The BS-chat task supplied 19 matching frontend hashes and a `WEB_RELEASE_READY` checkpoint confirming compatibility with the running backend. Its live conversation check is attributed peer evidence; this deployment issued no paid requests and restarted no services.

This task repaired the browser's manuscript adaptation controls:

- An existing-project conflict cannot force a restart, attach another job or retry an upload automatically.
- Job acceptance checks the protected contract, project identity and ownership token.
- Completed, failed, canceled, interrupted, reset and missing jobs produce appropriate terminal states. A disappeared job never implies successful completion.
- Cancel/reset requests carry the known job token and require a confirmed response.
- Status polling permits one request at a time, uses a 15-second timeout, cancels on unmount and ignores late responses.

## Verification

- All 150 focused frontend tests passed. The canonical strict TypeScript check passed. All 499 component files match across four source trees.
- The production build succeeded. Source, dependency/environment metadata and the 19 coordinated input hashes remained unchanged during compilation.
- Syntax parsing found 113 compiled JavaScript modules and 483 module references; 122 unique dependencies resolve.
- All 1,137 candidate files matched their manifest hashes, sizes and inventory before upload and promotion. Credential scanning passed without logging secret values.
- Preview and production each matched 18 selected key files exactly. Seven excluded private/bulk URLs returned 404 or the exact SPA fallback.
- Live and preview both reference Hosting version `cc4229899104e8ba`. Hosting reports 1,139 files, including two platform-owned initialization files.
- The crypto safety status remains `dispatch_enabled=False`, and its guard rejected execution. Native Studio, game SDKs, installers, Firebase rules and Functions were not deployed.

These checks establish artifact identity and focused contracts. They do not establish acceptance of every authenticated production workflow.

## Preserved failures and limits

The first candidate was withheld because another authorized task changed chat/navigation source during compilation. Its output and source hashes are retained.

A relocated frontend copy using a dependency junction failed strict TypeScript checking on installed remark-gfm/vfile compatibility. One controlled comparison also failed, then stopped. That copy remains unqualified and was not deployed. No casts, weaker checks, package upgrades or dependency aliases were introduced. The released candidate uses the coordinated canonical source, its passing normal type check, and stable source/dependency pins. Relocated dependency compatibility remains a follow-up item.

A local verification regex initially mistook public JSDoc type references for runtime imports. Installed Babel parsing replaced it and passed. An initial channel-metadata request lacked an explicit Firebase config; the corrected read succeeded. Existing large-chunk build warnings remain a performance follow-up.

## Preservation and storage

Installed native v5.329.107, held native candidates and the paused game work remain untouched. Original PDFs, manuscripts, family files, recordings, saves and unrelated dirty changes were preserved.

The old frontend dist was not replaced. Existing Hosting exclusions kept 36 files, about 1.39 GB, out of staging. Unchanged static assets were reused through hardlinks between this task's own retained staging trees. Originals and failed evidence were not deleted. Raw CLI account metadata remains in the private backup workspace.

The public release receipt is saved in the existing audit Drive folder: https://drive.google.com/file/d/1ys6rr_tkKJvWuFClx1ljcMXmJfszcU_w/view
Full source patches, preimages, test logs and verification receipts remain beside this report and in the backup workspace.

## Continuity and next step

Reviewed the current AGENTS contract, directory index, relevant handoffs, November 2 Hosting receipt, and the latest relevant user/assistant messages and ready manifest from chat `01a19992-d614-7021-b4ef-47695d694047`. This was a bounded review, not a review of every prior chat. Helpers were `dashboard_web_release_review` and `firebase_release_readiness`.

Refresh the hosted Dashboard to load v5.329.109. Qualify the relocated dependency setup separately. Resume native packaging or game qualification only when requested.
