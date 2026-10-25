# Native screenplay safety checkpoint (staged only)

No staged changes have been installed. No native application, backend service, live manuscript operation, packaging or deployment was run.

## Files

- `before/screenwriting_view.py`: preserved active source (SHA256 recorded in `manifest_before.json`).
- `staged/native_studio/screenwriting_view.py`: candidate view implementation.
- `staged/native_studio/screenplay_client.py`: new narrow authenticated I/O and draft recovery helper.
- `prepare_staged_view.py`: reproducible candidate generator from the preserved source.
- `verify_staged_native_writer.py`: offline verification harness.
- `verification.json`: 44 checks passed, exact candidate hashes and retained fixture path.

## Changes

Native project catalog/read/create/import/save/export now use the actual project-scoped backend. The client obtains AI_BS_ADMIN_KEY from the process environment per request; it has no embedded key, no unauthenticated fallback, and only sends to 127.0.0.1:8080 with proxy environment and redirects disabled. Network calls run on EngineBus workers, with a single in-flight operation per writer view.

Editor initialization is blank/read-only until an authenticated project read succeeds. Empty host scripts stay empty. Project selection changes only after successful read. Switching from a dirty draft first saves the departing project's content with its exact revision. Failed or uncertain saves retain the current editor and block blind retries. Typing during a save or pending read remains in the current editor. Explicit Reload Host retains the outgoing draft before replacing the editor, with confirmation when unsaved or uncertain.

Unsaved drafts receive unique UTF-8 JSON recovery copies under workspace/native_screenplay_recovery after a one-second idle delay and before save/switch/reload, plus best-effort application quit capture. Copies contain project, revision and complete text. Existing recovery copies remain intact; unchanged snapshots are deduplicated. Recovery storage failure blocks transitions. The Recovery button displays the folder and latest path; automatic recovery merging is not implemented.

Create and import are backend create-only operations; duplicate project errors preserve existing work. Native imports accept strict UTF-8 Fountain/text, structurally checked FDX XML converted to text, and selectable-text PDF extraction with a layout-loss confirmation. DTD/entity declarations including UTF16 are rejected. Sources remain unchanged. A PDF with no extracted text fails with an OCR requirement. pypdf must be included in the packaged runtime; it exists in Python312 but not pyppeteer_env. Native FDX import does not preserve every Final Draft layout/formatting property and remains subject to the shared backend Fountain parser's existing semantic limitations.

Exports retrieve actual PDF/FDX bytes through the backend and verify the host revision before and after generation. Fountain export reads confirmed host text. Output creation is exclusive: existing files and previous exports cannot be replaced. The disconnected call-sheet PDF action is disabled instead of claiming success.

Adaptation first requires authenticated capabilities contract create-only-v1, then submits the real multipart manuscript to /api/screenplay/adapt with force=false. It monitors actual job ID/status; it does not manufacture an adapted scene. This requires the separately staged backend adaptation hardening. Old backends lacking the contract are refused before upload. Only one job is monitored per view, and a stopped monitor can be resumed with Adaptation Status. Existing external jobs are still subject to server-side save guards.

## Verification and limits

44 meaningful checks passed using the actual staged client through HTTP MockTransport and actual staged view methods in an isolated offscreen QWidget harness. No MainWindow or subsystem page construction occurred. Checks include CAS rejection, empty save/read, credential refusal without a request, unsafe path refusal, dirty transition safety, concurrent typing during save/read/create, immutable original/export files, real parser-readable PDF bytes, FDX conversion, UTF16 entity refusal, no-text PDF refusal, failed recovery storage, network uncertainty, safe adaptation gating and exact loopback authentication. Both staged files parse. Active screenwriting_view.py still matches its preserved backup.

This proves isolated behavior, not live integration or executable readiness. Backend8080 was unavailable; no restart was attempted. No signed-in native workflow, full installed app launch, actual model adaptation, native packaging/signature, or live export was verified. Other native modal actions and Unreal asset export paths remain outside this change and need their own review before release. Recovery text from the most recent one-second typing window may be absent after an abrupt process kill.

Activation requires root review and coordinated installation of both native files with the backend create-only adaptation contract. Version alignment is owned by the root release checkpoint.
