from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess

root=Path(r'C:\AI-BS');cp=root/'backups/retained_proposal_5_329_46_20261024T141425139154Z'
assert not (cp/'checkpoint.json').exists()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
focused=read(cp/'publication_green28.json');regressions=read(cp/'regressions.json');audit=read(cp/'source_audit.json');live=read(cp/'live.json')
assert focused['passed'] and focused['tests']==28 and focused['skipped']==0
assert sum(r['tests'] for r in regressions)==69 and all(r['passed'] and not r['skipped'] for r in regressions)
assert len(audit)==13 and all(c['passed'] for c in audit)
assert live['status']=='passed' and len(live['checks'])==55 and all(c['passed'] for c in live['checks'])
runtime=read(cp/'runtime/process.json');observation=read(cp/'runtime/observation_after_restore.json')
assert all(observation['source_hashes_exact'].values())
assert all(sha(root/p)==h for p,h in runtime['source_hashes'].items())
preservation=read(cp/'preservation_after_live.json');personal=read(cp/'runtime/personal_preservation_after.json')
assert preservation['status']==personal['status']=='verified'
assert all(p['every_row_exact'] for p in personal['tables'].values())
for name in ['backend','gateway','ollama']:
    service=observation['services'][name]
    assert service['identity_verified'] and service['loopback'] and service['http']==200 and all(service['flags_disabled'].values())
assert all(r['running'] is False and r['pid']<=0 and r['state']=='stopped' for r in observation['services']['gateway']['daemon_states'].values())
assert observation['services']['ollama']['custom_model_preserved']
paths=['docs/CODEX_HANDOFF.md','docs/AI_BS_Autonomy_Implementation_Plan.md','docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md','docs/engineering_ledger/cloud_index.json']
(cp/'finalization_before').mkdir()
for name in paths:(cp/'finalization_before'/name.replace('/','__')).write_bytes((root/name).read_bytes())
plan=root/paths[1];text=plan.read_text(encoding='utf-8')
old='Plan revision: 1.57 | Updated: October 24, 2026 | Local application source: v5.329.45'
assert text.count(old)==1
text=text.replace(old,'Plan revision: 1.58 | Updated: October 24, 2026 | Local application source: v5.329.46',1)
text=text.replace('Current source checkpoint v5.329.45 is not a Firebase/Windows release.','Current source checkpoint v5.329.46 is not a Firebase/Windows release.',1)
text=text.replace('Local application source is v5.329.45.','Local application source is v5.329.46.',1)
text+='\n\n**v5.329.46 / plan1.58 retained multi-file proposals:** Reviewed parent plans now produce complete-input exact-hunk candidate source and diffs, retained and independently authenticated, with stale-hash/role/edit boundaries, same-ID inspection, cancellation and recovery. Tests remain NOT RUN and execution/apply stay unauthorized. Retained28focused,69regression and13source observations plus55actual model/core/gateway observations pass; the real two-file Python/JavaScript fixture generated exact changes in57.797seconds and a separate running proposal was cancelled. Current services are loopback8080/332884,8000/116980,11434/165656 and5173/111384; gateway binary remains37, source metadata46. The initial stopped-daemon PID0 expectation was an observer error; this binary reports-1. Existing failure preserved; same processes re-observed without restart. All888selected documents/copies and personal rows unchanged; vault/master integrity/counts retained. No project code/check execution, browser acceptance, VM retry or publication. Next is frontend retained-proposal/diff review and recovery controls, followed by still-open isolated execution and release gates. Full goal remains incomplete; no additional whole-phase completion. Details: docs/phase5/RETAINED_PROPOSALS.md and backups/retained_proposal_5_329_46_20261024T141425139154Z.\n'
plan.write_text(text,encoding='utf-8')
entry='''## Record 30 - Completed source46 live proposal checkpoint and reconciled requests

**Actual current evidence:** Reviewed the interrupted companion run and its retained artifacts, not just the pasted progress report. Source46 has28focused proposal cases passing/no skips,69existing preparation/planning regression cases and13source-audit observations. Existing route bodies/auth and selected original modules remain unchanged. Two reproduced review defects, final-newline diff formatting and retained-source changes during publication, were corrected before the retained28case pass. No repeat of the source build/version bump or whole-plan completion claim.

**Implementation:** core/coding_preparation_proposals.py implements review_plan/generate_proposal/read_proposal/recover_proposal/cancel_proposal;5independently authenticated operations in coding_preparation_router.py. Parent must be PLAN_PROPOSED without questions; complete retained UTF8 source max20,000bytes, context wire65,536bytes, known-secret checks and exact selected roles/checks. Model returns SHA-bound unique/nonoverlapping hunks for exactly the editable files. Server reconstructs source/diff and retains immutable input/result evidence; Windows metadata/source handles deny writes through successful publication. Same ID inspects; uncertain recovery does not replay; final cancellation admission is locked. Existing local Stehouwer only,90second client deadline/32,768provider bytes/context16,384/predict4,096, no proxies/redirects/tools/remote fallback. No private reasoning export. Source size/context settings do not guarantee inference quality or time.

**Live:**55actual observations passed through8080/8000. Earlier selected synthetic Python/JS sources and fixed tests reused, original plan unchanged. Existing model produced exact two-file value changes and diff in57.797seconds, statePROPOSAL_READY. Review/input/output hashes, unauthorized/invalid credentials, stale review409, forged body422, inspect/recover/same-ID exact results and terminal cancel no-op pass. A second real operation was observed RUNNING, cancelled through authenticated API, reached CANCELLED/proposalNone and did not replay. All original source/check bytes preserved; no execution task or review/apply seal. Verification remains not_run, execution_authorizedfalse, apply_authorizedfalse. Server GPU compute-release timing unmeasured. One fixture is not broad model-quality acceptance. Normal greeting/browser UI not rerun or accepted by this evidence.

**Restoration finding:** The companion restore started only the approved services then stopped its observer on an empty AssertionError. Actual same-process observation identified stopped gateway registrations with pid-1, while the observer expected0. All11are runningfalse/statestopped; only expected conhost child, no managed daemon launched. Original runtime/process.json failure retained, later observation records identity/creation/exe/argv/loopback/health and6disabled flags. Backend332884/launcher138312, gateway116980(compiled37), Ollama165656(original30tags/modeldigest), Vite111384. Source startup hashes exact. No restart in this continuation. Earlier local45preflight correctly stopped on changed router; preserve that failed script, do not weaken its old hash guard or run it against46.

**Preservation:** All866screenplays+22selectedDocuments AND retained copies exact. Personal profile1/facts44/triplets29/events392 every row/schema exact and integrityOK against the fresh private46snapshot. Vault/master integrity/schema-count authorities retained; vault bytes exact. The historically recorded master byte difference remains, not a new finding; full-row master comparison not repeated. Models/Modelfiles retained. No raw personal stores, source/proposal payloads, Downloads listing, credentials or connection metadata exported to cloud.

**Steering/tools:** User's read-only Downloads request completed1,858files/218folders with no unreadable paths; exact five-file report stays local outside repository, no downloaded file changed. Separate sanitized Downloads note is reconciled here. Browser-control connection remains unavailable and prior saved-origin deny has not been bypassed. Firecrawl and Drive tool availability is separate from localhost access. Remote Desktop Commander tools later appeared, but actual list_devices failed with Unknown tool; no connection success claimed or configuration changed. No repeated workaround/VM retry, DNS, purchases or publication. User's explicit VM deferral supersedes stale goal wording.

**Checkpoint/next:** Source5.329.46/plan1.58, backups/retained_proposal_5_329_46_20261024T141425139154Z; before/failure/test/live/runtime/preservation evidence retained. Metadata original backup20261024T142119440Z_retained_multi_file_proposal_32124af4; no new metadata bump. Shared dirty main HEAD539dfcbcf165285f9f55ba6ef329a3ae166af2b7, current status/hashes in checkpoint.json; no reset/clean/commit/mass stage/deletion. Historical3of6limited trusted-local phases only. Next implement source46proposal/diff display and owner/backend/pending-ID/recovery controls in existing preparation panel. Larger-project actual isolated checks/apply, complete VM14case/controller acceptance, browser/Firebase/native releases/rollback/signing, confidential-method-safe overview and measured memory/learning work remain incomplete. Cloud receives only sanitized ledger through existing private same-file byte verification; no background sync promise.

'''
ledger=root/paths[2];text=ledger.read_text(encoding='utf-8');assert '## Record 30 ' not in text
with ledger.open('a',encoding='utf-8') as out:out.write('\n\n'+entry)
handoff=root/paths[0]
with handoff.open('a',encoding='utf-8') as out:
    out.write('\n\n## v5.329.46 / plan1.58 - Retained proposal backend and live acceptance\n\n'+entry.split('\n\n',1)[1])
index=root/paths[3];data=read(index);data['pending_sync']={'record':30,'source_version':'5.329.46','plan_revision':'1.58','reason':'Completed46and reconciled Downloads/tool summaries await same-private-file readback'}
index.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
notes=root/'docs/engineering_ledger/2026-10-24_Downloads_scan_and_restore_hold.md'
with notes.open('a',encoding='utf-8') as out:out.write('\n\nReconciled into main daily Record30/source46/plan1.58. Cloud completion is recorded by its final same-file receipt, not by this note.\n')
git=lambda *args:subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe',*args],cwd=root,text=True)
status=git('status','--porcelain=v1','-uno');(cp/'git_status_final.txt').write_text(status,encoding='utf-8')
sources=list(runtime['source_hashes'])+['backend/tests/test_preparation_proposals.py','docs/phase5/RETAINED_PROPOSALS.md',*paths,
          'docs/engineering_ledger/2026-10-24_Downloads_scan_and_restore_hold.md']
sources+=['workspace/'+p.name for p in (root/'workspace').glob('*proposal_v46*.py')]
(cp/'after').mkdir()
for name in sources:
    target=cp/'after'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((root/name).read_bytes())
evidence=[p for p in cp.rglob('*') if p.is_file() and not any(part in {'after','before','finalization_before'} or part.startswith('fixtures_') or part.startswith('regression_fixtures_') for part in p.relative_to(cp).parts)]
record={'source_version':'5.329.46','plan_revision':'1.58','record':30,'at_utc':datetime.now(timezone.utc).isoformat(),
        'git_head':git('rev-parse','HEAD').strip(),'tracked_changes':len(status.splitlines()),'full_goal_complete':False,
        'new_whole_phases_complete':0,'vm':'explicitly_deferred','browser_acceptance':'not_verified',
        'counts':{'proposal_tests':28,'regression_tests':69,'source_checks':13,'live_observations':55},
        'files':{n:sha(root/n) for n in sources},'evidence':{p.relative_to(cp).as_posix():sha(p) for p in evidence},
        'runtime_processes':{n:s['pid'] for n,s in observation['services'].items()},'frontend_pid':111384,'cloud_sync':'pending',
        'next':'Retained proposal/diff frontend review controls; expanded execution still gated by deferred VM acceptance.'}
(cp/'checkpoint.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checkpoint':str(cp),'source':record['source_version'],'plan':record['plan_revision'],'tracked_changes':record['tracked_changes'],
                  'handoff_exists':handoff.is_file(),'cloud':'pending'}))
