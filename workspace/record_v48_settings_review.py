from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

root=Path(r'C:\AI-BS');cp=Path((root/'workspace/proposal_history_v48_checkpoint.txt').read_text(encoding='utf-8').strip())
paths=['docs/CODEX_HANDOFF.md','docs/CODEX_JOURNAL.md','docs/CODEX_DECISIONS.md','docs/CODEX_TASKS.md']
snapshot=cp/'memory_before_settings_review';snapshot.mkdir()
before={}
for name in paths:
    raw=(root/name).read_bytes();(snapshot/Path(name).name).write_bytes(raw);before[name]=hashlib.sha256(raw).hexdigest()
stamp=datetime.now(timezone.utc).isoformat()
decision='''

## ADR-005: Runtime evidence and settings ownership clarification
- Date: 2026-10-24
- Status: Current evidence correction; supersedes conflicting names/claims in earlier notes without removing their history.
- The six actual verified runtime opt-in flags are AI_BS_RECDEBUT_OUTBOUND_ENABLED, AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED, AI_BS_DISCORD_NOTIFICATIONS_ENABLED, AI_BS_BACKEND_MANAGE_DAEMONS, AI_BS_BACKEND_BACKGROUND_ENABLED and AI_BS_ALLOW_DESTRUCTIVE_ACTIONS. They remain false. The AIBS_* names listed in ADR-003 were not established as equivalent controls and must not replace these actual runtime checks.
- Verified personal authority is backend/database/aibs_personal_intelligence.db. Prior preservation checks used the source paths recorded in backups/production_readiness_5_329_33_20261024T054356815Z/backup_report.json, including stehouwer_vault.db and backend/aibs_master.db. Basenames in earlier prose are not proof of a live database path; preserve any additional existing database rather than substituting an empty or similarly named file.
- Five persistent-memory files are now required by the user's replacement instructions. Root AGENTS.md was read and still contains the original project directive; the new memory rules are present in C:/Users/footb/.codex/AGENTS.md. Do not claim the root file already has the addendum or overwrite its existing operational sections.
- Existing config.toml defaults were observed as gpt-6.1-sol, reasoning ultra and priority tier, with approval never, danger-full-access and trusted AI-BS. These are file defaults, not proof of the active chat's effective setting. Recommend Medium and standard/default speed for the requested low-usage workflow. No config was edited by this review.
- Command permissions, Browser/Computer Use controls and app connections are separate. Global browser config already lists localhost5173 as allowed; actual browser-control tools remain unavailable to this session. Root project browser config paths stated in earlier task prose were not found. Do not edit policy files, install workarounds or claim a connector is functional merely because a permission/config/tag exists.
- Antigravity should own only its specifically assigned Codex settings changes while Codex owns the current AI-BS code/runtime task. Avoid concurrent source/version/handoff/ledger edits. Existing routine restart authorization remains valid; an observer's conservative open-connection guard is an implementation issue to diagnose, not a new approval-policy rejection.
- Lifecycle script and hooks.json exist. This review did not execute hooks, validate automatic lifecycle delivery, change their trusted hashes or establish the installed binary version. Preserve hook-written JOURNAL/TASKS changes and keep handoff/plan/cloud-ledger/index outside automatic hook writes.
'''
with (root/'docs/CODEX_DECISIONS.md').open('a',encoding='utf-8') as out:out.write(decision)
journal=f'''

## {stamp} - Source48 in progress; settings and memory instructions reviewed
- User reaffirmed VM deferral and asked for accurate progress, then supplied replacement five-file persistent-memory instructions and asked which settings/paths could help Antigravity improve Codex operation.
- Current task remains proposal-history discovery only.38backend cases now pass/no skips,84client and30offline view cases pass;23source observations and four panel mirrors pass. One missing journal input raised raw FileNotFoundError; it now becomes explicit evidence failure, and all38cases pass. Initial generated client test accidentally changed an old ID-validation loop; before-images/red evidence retained and generator restricted to its wrapper before corrected red70/84 and green84/84. No test weakened.
- Source metadata5.329.48 is consistent; last fully finalized checkpoint remains source47/plan1.59. Metadata originals: backups/release_versioning/20261024T150106400Z_saved_proposal_history_d0519355.
- One controlled restart attempt stopped BEFORE terminating anything because the current backend has an established connection from the installed Codex ChatGPT.exe process. Original backend332884/launcher138312 still serves source46code. Gateway116980, Ollama165656 and Vite111384 retained. Do not report source48history live acceptance yet. Failure: active checkpoint/runtime/process.json, statusinspection_needed, inbound API connection active. No repeated restart, killing of Codex/browser, VM work, unisolated generated execution, publication or approval-policy edit.
- Actual config defaults, separate browser-tool availability and corrections to invented flag/database/config-path claims are recorded in ADR-005. No credential values copied. Settings guidance is based on official OpenAI documentation and local selected-field reads; global config/hooks remain owned by Antigravity and unchanged by this review.
- Next: resolve controlled backend reload, verify actual owner-scoped proposal history and client recovery through8080/8000, then finalize48with SHA-bound handoff/journal/tasks/decisions and sanitized cloud receipt. No next side task before this checkpoint. VM and release gates remain open.
'''
with (root/'docs/CODEX_JOURNAL.md').open('a',encoding='utf-8') as out:out.write(journal)
tasks=root/'docs/CODEX_TASKS.md';text=tasks.read_text(encoding='utf-8')
old='- [x] **`v5.329.45` / Plan `1.57`:** Retained multi-file code proposal generation (`PROPOSAL_READY`), full-source review hash binding, and non-execution/non-apply boundaries.'
new='- [x] **`v5.329.45` / Plan `1.55` (later diagnostic plan1.57):** Stehouwer planning controls, history and cancellation; generated-code proposals arrived at46, not45.'
if old in text:text=text.replace(old,new,1)
text+='\n\n## Source48 current progress correction - '+stamp+'\n\n- [x]38backend /84client /30offline view /23source observations and four panel parity checks pass.\n- [x]Source48metadata backups and selected document/vault/master pre-restart preservation retained.\n- [ ]Controlled backend reload and source48actual API/client history verification: pending one diagnosed Codex-app connection; previous attempt changed no processes.\n- [ ]Finalize source48/plan1.60 and cloud verification after actual checks pass. Last finalized checkpoint is still47/1.59.\n- [ ]Actual Browser tool connection and UI acceptance: pending. Global C:/Users/footb/.codex/browser/config.toml allows localhost5173, but project browser config/session paths in older prose were not found and tool access was not established.\n\nDo not begin the optional49comparison/navigation refinements before48is finalized. VM remains explicitly deferred. See ADR-005 for actual flag and database-path authority corrections.\n'
tasks.write_text(text,encoding='utf-8')
handoff='''

## Source48 in progress - settings review and five-file memory transition

Current source metadata5.329.48; latest finalized checkpoint47/plan1.59. Active backups/proposal_history_5_329_48_20261024T145341207541Z contains original source/docs, backend red38with10missing-feature failures/errors, green38with one missing-input FileNotFoundError, verified38pass, client corrected red70/84 then84pass, view red26/30 then30pass,23source checks, four panel parity, and selected document/vault/master pre-restart preservation. Existing source/action/auth functions stay AST-identical; only metadata history/helper/GETroute and client/view discovery were added. No candidate execution/apply. Source48metadata originals20261024T150106400Z_saved_proposal_history_d0519355.

Restart attempt runtime/process.json stopped before terminating backend332884/launcher138312 because an established loopback connection is owned by installed Codex ChatGPT.exe PID280356. Exact peer path/identity was read, not assumed from a process name. Existing8000/116980,11434/165656,5173/111384 remain; current backend still has source46startup. History route live verification is NOT achieved. Do not replay restart script blindly: it creates a unique runtime directory and the failure must remain. Diagnose the connection and preserve user work; no killing Codex/browser, bypassing actual browser policy, whole daemon launch or reauthorizing already-approved routine maintenance.

User supplied replacement AGENTS instructions: maintain AGENTS/HANDOFF/JOURNAL/DECISIONS/TASKS, append lifecycle/history/ADRs, retain original sections, verify handoff before/after hashes, two-strike diagnostic halt, keep six actual runtime flagsfalse and VM deferred. New ADR-005 corrects unverified flag/database/config-path claims in the initial Antigravity memory notes without deleting their history. Hook/script files exist; automatic execution/runtime version not verified by this review. Root AGENTS.md still has the old project directive; global C:/Users/footb/.codex/AGENTS.md carries the new memory rules. Antigravity is editing settings; avoid concurrent settings/source/version/checkpoint writes.

Settings evidence: global config defaultsgpt-6.1-sol/ultra/priority, approvalnever/danger-full-access/trustedAI-BS. Current chat overrides are not inferred from file defaults. Recommend Medium/standard speed as requested; no configuration edits made. Global browser config already allows localhost5173, but actual Browser tools remain unavailable; more broad permissions do not establish a connection. User asked for exact settings paths, not an automatic security-policy change. Never copy credentials/config contents into ledger/cloud.

Next: finish ONLY source48reload plus real metadata-history/client acceptance, then final checkpoint and sanitized cloud reconciliation. Current five-file memory transition is backed up/hash-recorded in memory_before_settings_review and memory_transition.json; retain its before/after hash chain rather than overwriting the original before_manifest. Source48is stillinprogress; full goal and isolated execution/releases remain incomplete.
'''
with (root/'docs/CODEX_HANDOFF.md').open('a',encoding='utf-8') as out:out.write(handoff)
after={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in paths}
for name in paths:assert (root/name).read_bytes().startswith((snapshot/Path(name).name).read_bytes()) if name!='docs/CODEX_TASKS.md' else True
record={'at_utc':stamp,'source_version':'5.329.48','finalized_checkpoint':'5.329.47','before':before,'after':after,
        'scope':'User-replaced persistent-memory rules and settings advice; no config or application change',
        'cloud':'Local lifecycle/settings notes pending sanitized reconciliation in final48ledger',
        'handoff_exists':(root/'docs/CODEX_HANDOFF.md').is_file()}
(cp/'memory_transition.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'memory_files':len(paths),'handoff_exists':record['handoff_exists'],'handoff_sha256':after['docs/CODEX_HANDOFF.md'],
                  'settings_changed':False,'checkpoint':str(cp),'source48_live_verified':False}))
