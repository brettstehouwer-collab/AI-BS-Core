"""Append evidence corrections; retain prior checkpoints and all failed observers."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, subprocess

root=Path(r'C:\AI-BS')
cp=root/'backups/proposal_history_5_329_48_20261024T145341207541Z'
out=Path((root/'workspace/proposal_history_v48_resume.txt').read_text(encoding='utf-8'))
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not (out/'local_finalization.json').exists(), 'Inspect existing finalization instead of replay'
runtime=read(out/'runtime_verified.json')
assert runtime['status']=='healthy_protected' and all(c['passed'] for c in runtime['checks'])
assert read(out/'client_live.json')['status']=='passed' and read(out/'client_live.json')['count']==16
assert read(out/'preservation_after_restore/documents_databases.json')['status']==read(out/'preservation_after_restore/personal_preservation_after.json')['status']=='verified'
paused=read(cp/'pause_checkpoint.json')
memory=set(paused['after_memory_sha256'])
stable={n:h for n,h in paused['files'].items() if n not in memory}
assert all(sha(root/n)==h for n,h in stable.items())
assert all(sha(cp/n)==h for n,h in paused['evidence'].items())
assert read(cp/'verified.json')['tests']==38 and read(cp/'verified.json')['passed']
assert read(cp/'client_green.json')['passed']==84 and read(cp/'view_green.json')['passed']==30
assert read(cp/'source_audit.json')['passed']==23
assert read(cp/'live.json')['count']==26
before={n:sha(root/n) for n in memory}
now=datetime.now(timezone.utc).isoformat()
pids={name:item['serving']['pid'] for name,item in runtime['processes'].items()}
entry=f'''## Record 33 - Source48 resumed verification and corrected operational checkpoint

Observed {now}. The user explicitly resumed development with full local permissions, removed the stop-after-each-task preference, and updated the objective to put Windows VM completion first again. VM setup is now back in scope, superseding the earlier deferral. This authorizes legitimate setup and routine operations; it does not supply a password, grant an unverified license entitlement, validate signing material or authorize reporting an incomplete isolation gate as passed. No blanket security/policy bypass or administrator password was installed or stored.

Source remains v5.329.48; this operational reconciliation is plan1.61. Existing code/metadata and all paused evidence hashes match. Retained backend38/38, client84/84, offline React30/30, source23/23, four identical panel mirrors and prior26actual observations remain their original evidence. A fresh16-case API/client/offline-render check passed against the restored services with the existing real configured administrator and retained two-file proposal. It verifies metadata discovery, candidate byte hashes, inspection and terminal recovery. No inference, generated project checks, apply, real-browser DOM acceptance, Firebase or Windows release occurred. Candidate checks still read Tests not run / Not applied.

Runtime drift was observed, not guessed: the old backend/gateway/Vite PIDs were absent, while the Ollama desktop app had restarted a loopback server from the same existing model store. Cause of the other processes stopping was not established. The first read-only audit stopped on the missing old backend handle; its evidence was retained. The first restoration observer stopped before mutation on a legitimate Windows conhost helper. An explicitly checked System32 conhost exemption allowed the second restoration. That run started the required services but its last observer incorrectly expected403from the gateway. Independent follow-up proved actual backend anonymous/invalid403, gateway anonymous/invalid401, and both real-admin200. No service was restarted again to repair this observer assumption. All failure artifacts remain unchanged.

Current verified serving PIDs: backend{pids['backend']}, gateway{pids['gateway']}, Vite{pids['frontend']}, Ollama{pids['ollama']}. Exact creation times/executables/argv are in runtime_verified.json. Four127.0.0.1listeners only, no11435; six actual autonomous/outbound flags false in all four processes. The previous idle Ollama desktop/server inherited a true destructive flag; only that verified idle process tree was replaced with a local-only server and six false flags, preserving the existing model manifest digest5213ff76656a20b564e1001cc3cc4e9e9b7f8cc80dd837cde54b341127e60b12. No model download/create/alias/training. Gateway remains the verified compiled5.329.37binary; source metadata48does not rebuild it. All11registered unrelated daemons are stopped, reporting pid-1. No frontend HTTP request or denied-origin workaround was used.

Fresh post-restoration preservation passed: all866screenplays+22selected documents AND retained copies exact; personal schema/integrity/every row exact against the private source46snapshot (profiles1,facts44,episodes392,triplets29). stehouwer_vault.db bytes and retained snapshot exact. Both authority databases pass integrity/schema/table-count comparison; aibs_master.db retains the previously documented historical byte difference, so no full master-byte identity or full-row equality claim is made. Raw personal rows, proposals, credentials and local file listings remain local.

VM inspection: no VirtualBox or existing standard-worker process was active at the direct observation. The saved machine XML has aborted=true and a newer77percent-installer snapshot/differencing disk, so old boot scripts expecting the earlier snapshot must not be replayed. Read-CurrentVMState.ps1 is prepared, syntax-checked and checks the existing worker SID before two read-only VBoxManage queries; no guest has been booted by this resumed work. User initially reported collection complete, but no matching fresh result or worker process was found, so completion is unverified and local password entry/output are pending. Do not automate authentication, reset the password, weaken the worker check or substitute privileged host execution. Microsoft Task Scheduler documentation confirms another account's S4U registration still requires credentials and batch-logon rights; no scheduled task or logon-policy change was attempted.

The supplied backend/core/run_phase4_controller.ps1 does not exist. Existing coding_vm_inputs.py, coding_vm_staging.py and coding_vm_artifacts.py implement input validation/staging/artifact binding, not a live guest controller. Ports11434/11435are model APIs, not proof of guest containment. No fake controller task rows were inserted into aibs_master.db. Phase4actual controller/transport/cancellation/recovery14-case acceptance, Phase5isolated larger-project verification/apply and Phase6browser/platform release/rollback/signing/overview remain incomplete. Historical3of6limited trusted-local phases only. No new whole phase completion.

Save point: backups/proposal_history_5_329_48_20261024T145341207541Z/{out.name}. Preserve original checkpoint.json, completion.json, pause_checkpoint.json, before/failure/test/live/runtime evidence and this resume directory. Shared dirty main HEAD539dfcbcf165285f9f55ba6ef329a3ae166af2b7; no reset, clean, commit, mass stage or deletion. Previous Record32contains two historical headings and incomplete finalization claims; both remain retained, with this later evidence controlling current status. Next: obtain/verify fresh worker VM state, then perform an explicitly reviewed recovery from the actual disk/snapshot; no repeat of the failed boot/login recipes.

Cloud: prior private same-file Record31was freshly downloaded and matched88394bytes/SHA256f3d992fd176cc389901eb9a85ade5cfdeaaf94e60e124089c882015063f102f6before any update. Only this sanitized engineering ledger is eligible for the same private file update. Current Record33sync remains pending until exact raw readback; no background synchronization promise.
'''

def append(path,text):
    old=path.read_bytes()
    with path.open('ab') as f:f.write(('\n\n'+text+'\n').encode('utf-8'))
    assert path.read_bytes().startswith(old)

ledger=root/'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md'
assert '## Record 33 ' not in ledger.read_text(encoding='utf-8')
append(ledger,entry)
handoff=root/'docs/CODEX_HANDOFF.md'
append(handoff,'## v5.329.48 / plan1.61 - Resumed source48 verification; VM scope reauthorized\n\n'+entry.split('\n\n',1)[1])
append(root/'docs/CODEX_JOURNAL.md',f'## {now} - Resume verification, source48/plan1.61\n\n'+entry.split('\n\n',1)[1])
append(root/'docs/CODEX_DECISIONS.md',f'''## ADR-007: Resumed full goal with legitimate worker and release boundaries
- Date: {now}
- User reauthorized the Windows VM completion scope in the edited objective and requested continuous progress. Earlier pause/VM deferral no longer controls new work.
- Preserve independent worker authentication and accepted guest containment; broad local permissions do not create passwords, guest entitlement, signed packages or empirical verification.
- Retain failed observers and reconcile actual401gateway/403backend denials using fresh observations without restarting healthy services. No host fallback, scheduled-task credential bypass or replay of stale snapshot scripts.
- Root AGENTS.md now has SectionC and was read with SHA256 recorded; the earlier note that its addendum was absent is historical.
- Source48verification is finalized locally with retained manifests; cloud completion requires exact private raw readback. No new platform release or whole phase completion.''')
plan=root/'docs/AI_BS_Autonomy_Implementation_Plan.md'
text=plan.read_text(encoding='utf-8')
old='Plan revision: 1.60 | Updated: October 24, 2026 | Local application source: v5.329.48'
assert text.count(old)==1
text=text.replace(old,old.replace('1.60','1.61'),1)
paragraph='**Latest operator decision: defer Windows VM setup.**'
assert text.count(paragraph)==1
start=text.index(paragraph);end=text.index('\n\n',start)
text=text[:start]+('**Latest operator decision: resume Windows VM completion.** The updated objective and unrestricted-automation request explicitly put VM provisioning back in scope. Preserve its disks, snapshots and crash evidence. Continue approved work without routine checkpoint pauses, while respecting real account authentication, legitimate licensing, isolation and signing requirements. Fresh worker state is required before recovery; do not replay older snapshot boot scripts or substitute host execution. The named run_phase4_controller.ps1 is absent and actual14-case worker/controller acceptance remains incomplete.')+text[end:]
text+='\n\n**Plan1.61 operational reconciliation, source48 unchanged:** Fresh post-restoration preservation and16actual configured-admin client/API observations passed; paused source/test/evidence hashes remain exact. Record33and the resumed checkpoint record current PIDs, observer failures, actual401/403denials and VM reauthorization. Worker authentication/fresh VM state and actual isolation acceptance remain pending; no external release.\n'
plan.write_text(text,encoding='utf-8')
tasks=root/'docs/CODEX_TASKS.md'
text=tasks.read_text(encoding='utf-8')
text=text.replace('Plan revision: 1.60 | Updated: October 24, 2026 | Local application source: v5.329.48','Plan revision: 1.61 | Updated: October 24, 2026 | Local application source: v5.329.48',1)
text=re.sub(r'- \*\*Next Bounded Objective:\*\*[^\n]+','- **Next Bounded Objective:** Verify fresh standard-worker VM state, then legitimate VM recovery and actual controller acceptance. Source48final verification complete locally; private cloud receipt pending.',text,count=1)
text=re.sub(r'- \*\*Active In-Progress Checkpoint:\*\*[^\n]+','- **Active In-Progress Checkpoint:** '+out.as_posix(),text,count=1)
text+='\n\n## Current resumed state - '+now+'\n\n- [x] User resumed work; VM completion reauthorized; continue without routine checkpoint pauses.\n- [x] Source48hash-bound implementation,38backend/84client/30view/23source checks and prior26actual observations retained. Fresh16API/client/offline-view observations pass after service restoration.\n- [x] Post-restoration888document/copy hashes, all retained personal rows and authority DB integrity/schema/count checks passed.\n- [x] Current runtime identities/access denials and all six false flags verified; previous failed observers retained.\n- [ ] Exact private Record33ledger cloud readback.\n- [ ] Fresh worker VM inspection output, legitimate VM recovery/provisioning and real14-case containment/controller acceptance.\n- [ ] Remaining Phase5isolated checks/apply and Phase6release/browser/signing/overview. No new whole-phase completion.\n'
tasks.write_text(text,encoding='utf-8')
index=root/'docs/engineering_ledger/cloud_index.json'; data=read(index)
data['pending_sync']={'record':33,'source_version':'5.329.48','plan_revision':'1.61','reason':'Resumed verified source48 operational reconciliation awaiting exact private same-file raw readback'}
index.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

raw=ledger.read_text(encoding='utf-8')
secret_patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'ghp_[A-Za-z0-9]{20,}',r'AIzaSy[A-Za-z0-9_-]{25,}',r'sk-[A-Za-z0-9_-]{25,}',r'Bearer\s+eyJ[A-Za-z0-9_.-]+']
assert not any(re.search(p,raw) for p in secret_patterns), 'Potential credential in sanitized ledger; do not upload'
git=lambda *args:subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe',*args],cwd=root,text=True)
assert git('rev-parse','HEAD').strip()=='539dfcbcf165285f9f55ba6ef329a3ae166af2b7'
status=git('status','--porcelain=v1','-uno')
(out/'git_status_after_verification.txt').write_text(status,encoding='utf-8')
result={'status':'local_verified_cloud_pending','source_version':'5.329.48','plan_revision':'1.61','record':33,
        'at_utc':now,'git_head':git('rev-parse','HEAD').strip(),'tracked_changes':len(status.splitlines()),
        'before_memory_sha256':before,'after_memory_sha256':{n:sha(root/n) for n in memory},
        'stable_files':stable,'runtime_file':'runtime_verified.json','post_restore_acceptance':'client_live.json',
        'prior_live_observations':26,'current_live_client_observations':16,'full_goal_complete':False,
        'cloud':'pending','vm':'reauthorized_fresh_worker_state_pending','ledger_bytes':ledger.stat().st_size,'ledger_sha256':sha(ledger)}
with (out/'local_finalization.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps({'status':result['status'],'record':33,'source':'5.329.48','plan':'1.61','ledger_bytes':result['ledger_bytes'],'ledger_sha256':result['ledger_sha256'],'pids':pids}))
