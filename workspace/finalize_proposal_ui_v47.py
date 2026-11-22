from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess
import psutil,requests

root=Path(r'C:\AI-BS');cp=Path((root/'workspace/proposal_ui_v47_checkpoint.txt').read_text(encoding='utf-8').strip())
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=read(cp/'before_manifest.json');assert not (cp/'checkpoint.json').exists()
for name in ['docs/CODEX_HANDOFF.md','docs/AI_BS_Autonomy_Implementation_Plan.md','docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md','docs/engineering_ledger/cloud_index.json']:
    assert sha(root/name)==before[name], 'Documentation changed concurrently: '+name
tests={name:read(cp/name) for name in ['client_green.json','view_green.json','client_live.json']}
assert tests['client_green.json']['passed']==tests['client_green.json']['count']==70
assert tests['view_green.json']['passed']==tests['view_green.json']['count']==26
assert tests['client_live.json']['status']=='passed' and tests['client_live.json']['count']==14
audit=read(cp/'source_audit.json');assert len(audit)==24 and all(c['passed'] for c in audit)
assert read(cp/'documents_final.json')['status']==read(cp/'personal_preservation_after.json')['status']=='verified'
panel_paths=[base+'/CodingPreparationPanel.jsx' for base in ['frontend/src/components','frontend/components','frontend/src/components/components','frontend/components/components']]
assert len({sha(root/n) for n in panel_paths})==1
prior=root/'backups/retained_proposal_5_329_46_20261024T141425139154Z'
runtime=read(prior/'runtime/process.json');health=[];session=requests.Session();session.trust_env=False
try:
    for name,port in [('backend',8080),('gateway',8000),('ollama',11434)]:
        old=runtime['processes'][name].get('serving',runtime['processes'][name]['launcher']);p=psutil.Process(old['pid'])
        assert p.create_time()==old['created'] and p.exe()==old['exe']
        assert all(p.environ().get(k)=='false' for k in runtime['controlled_flags'])
        assert session.get(f'http://127.0.0.1:{port}'+('/api/version' if name=='ollama' else '/health'),timeout=5).status_code==200
        health.append({'service':name,'pid':p.pid,'healthy':True,'activation_flags_false':True})
    listeners=[c for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port in (8080,8000,11434,5173)]
    assert len(listeners)==4 and all(c.laddr.ip=='127.0.0.1' for c in listeners)
    assert next(c for c in listeners if c.laddr.port==5173).pid==111384
finally:session.close()
assert all(sha(root/n)==h for n,h in runtime['source_hashes'].items())
metadata=root/'backups/release_versioning/20261024T144616233Z_proposal_review_controls_4a6e57f5'
version_manifest=read(metadata/'manifest.json');assert version_manifest['to_version']=='5.329.47' and len(version_manifest['files'])==16
for item in version_manifest['files']:
    assert sha(root/item['path'])==item['after_sha256'] and sha(metadata/'before'/item['path'])==item['before_sha256']
entry='''## Record 31 - Source47 proposal review controls

**Implemented:** Existing CodingPreparationPanel and projectPreparation client now expose explicit Review saved plan, Generate code proposal, same-ID retry, inspect/recover, cancellation, per-file diff/candidate source and base/candidate hashes. Only a confirmed question-free parent and complete-input review enable generation. Every candidate stays Tests not run / Not applied; no Run/Verify/Apply action, executor, backend permission or storage schema change. Plain escaped React text only. Four explicitly selected panel mirrors match; no broad mirror sync/build or dependency installation.

**Boundaries/recovery:** Scope binds current backend/actor, independently verified owner, preparation/snapshot/review, immutable parent and reviewed proposal digest. Fixed create body contains only proposal_id/reviewed_plan_sha256. Proposed source SHA256 is independently checked with Web Crypto before display; editable/base hashes, byte limits, combined diff, outcome and false authority flags are validated. Reject changed terminal results. Pending intent survives lost replies under its owned preparation/plan; identical retry never silently allocates a new ID. Independent cancellation works while generation waits; source/parent edits freeze and late RUNNING acknowledgements cannot replace a terminal candidate. Account/backend changes or close abort/hide stale replies and prevent follow-up requests. Saved IDs can be entered explicitly after reload and server recovery does not replay. IDs seen in this session and unsent intent are memory-only; automatic complete proposal-history discovery and permanent browser drafts are NOT claimed.

**Tests/errors:** Client red70passed41legacy/29newmissing; green70/70. React red26passed18/8missing; green26/26. These controlled-store/SSR/callback cases are not actual browser DOM acceptance. A view-runner generation command failed because of shell quoting (exit1/no output); saved UTF8generator with exact existing-file checks was used, no product edit in that failed generation step.24source observations pass, including all18loaded backend source hashes,4panel parity and targeted secret/action rendering checks. No full TypeScript check or broad tests; old known unrelated failures were not reclassified.

**Actual API/client:**14checks use the real configured local administrator through existing8000 APIs, no fake live Firebase identity. Inspected source46retained synthetic preparation, plan, full-source review, two-file proposal and cancelled record. Client independently validated actual candidate hashes, terminal recovery returned identical evidence, switching back retained immutable evidence. No inference/create/cancel/check/apply request was sent; only GET and terminal recover. Actual data rendered through the offline React view with correct diff/status and no execution button. Real signed-in browser UI acceptance remains pending; no HTTP5173/native/tunnel/browser-policy workaround.

**Runtime/preservation:** No service restart or new model call. Same backend332884/launcher138312(source46startup), gateway116980(compiled37), Ollama165656 and Vite111384; four loopback listeners, six activation flagsfalse and backend/gateway/model health200. Source metadata47 does not rebuild older binaries. All888selected documents AND copies exact; personal profile1/facts44/triplets29/events392 every row/schema/integrity exact against private46snapshot. Models, user sources and conversation data preserved; no credentials/raw source/candidate/chat/Downloads listing uploaded. The previous46vault/master integrity/count evidence remains its historical observation, not rerun as a new47database-byte claim.

**Checkpoint/next:** Source5.329.47/plan1.59, backups/proposal_ui_5_329_47_20261024T143740416296Z, metadata originals20261024T144616233Z_proposal_review_controls_4a6e57f5. Shared dirty main HEAD539dfcbcf165285f9f55ba6ef329a3ae166af2b7; current status/source/evidence hashes in checkpoint.json, no reset/clean/commit/mass stage/deletion. Historical3of6limited trusted-local phases; no new whole-phase completion. Next bounded improvement is owner-scoped metadata discovery of saved proposal IDs after reload, retaining explicit inspection/recovery and no inference/replay. Actual isolated execution/apply, VM14case/controller/transport acceptance, browser/Firebase/native release/rollback/signing, confidential overview and measured memory/learning remain incomplete. VM remains explicitly deferred; UI redesign later. Same private daily ledger only, exact readback required; no background sync guarantee.

'''
ledger=root/'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md';assert '## Record 31 ' not in ledger.read_text(encoding='utf-8')
with ledger.open('a',encoding='utf-8') as out:out.write('\n\n'+entry)
handoff=root/'docs/CODEX_HANDOFF.md'
with handoff.open('a',encoding='utf-8') as out:out.write('\n\n## v5.329.47 / plan1.59 - BS-Chat retained proposal review controls\n\n'+entry.split('\n\n',1)[1])
plan=root/'docs/AI_BS_Autonomy_Implementation_Plan.md';text=plan.read_text(encoding='utf-8')
old='Plan revision: 1.58 | Updated: October 24, 2026 | Local application source: v5.329.46';assert text.count(old)==1
text=text.replace(old,'Plan revision: 1.59 | Updated: October 24, 2026 | Local application source: v5.329.47',1)
text=text.replace('Current source checkpoint v5.329.46 is not a Firebase/Windows release.','Current source checkpoint v5.329.47 is not a Firebase/Windows release.',1).replace('Local application source is v5.329.46.','Local application source is v5.329.47.',1)
text+='\n\n**Source47/plan1.59 proposal-review panel:** explicit complete-input review, generate, same-ID retry, independent cancel, inspect/recover and escaped per-file diffs/source/hashes now use source46API. Client validates candidate SHA256/scope/false authority and hides stale owners/backends.70client/26offline view cases,24source observations and14real configured-admin API/client reads+offline render pass. All888selected documents/copies and personal rows preserved. No backend/model change, restart, inference or execution/apply. IDs seen in this session are temporary; explicit saved-ID entry supports recovery after reload, while server-wide proposal discovery is next. Four panel mirrors exact,16metadata originals preserved. Actual browser acceptance, isolated execution, VM/release/signing/whole-goal gates remain open; no new whole phase completed. Checkpoint: backups/proposal_ui_5_329_47_20261024T143740416296Z.\n'
plan.write_text(text,encoding='utf-8')
index=root/'docs/engineering_ledger/cloud_index.json';data=read(index);data['pending_sync']={'record':31,'source_version':'5.329.47','plan_revision':'1.59','reason':'Proposal review checkpoint pending private same-file byte verification'};index.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
spec=root/'docs/phase5/PROPOSAL_REVIEW_UI.md'
with spec.open('a',encoding='utf-8') as out:out.write('\n\nImplemented and verified at source47/plan1.59:70client,26offline view,24source and14actualAPI/client observations. See Record31 and the checkpoint for evidence/scope limitations.\n')
files=list(before)+['docs/phase5/PROPOSAL_REVIEW_UI.md']
files += [p.relative_to(root).as_posix() for p in (root/'workspace').glob('*v47*') if p.is_file()]
files += [i['path'] for i in version_manifest['files']]
files=list(dict.fromkeys(files));(cp/'after').mkdir()
for name in files:
    target=cp/'after'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((root/name).read_bytes())
git=lambda *args:subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe',*args],cwd=root,text=True)
status=git('status','--porcelain=v1','-uno');(cp/'git_status_final.txt').write_text(status,encoding='utf-8')
record={'source_version':'5.329.47','plan_revision':'1.59','record':31,'at_utc':datetime.now(timezone.utc).isoformat(),'git_head':git('rev-parse','HEAD').strip(),'tracked_changes':len(status.splitlines()),
        'counts':{'client':70,'offline_view':26,'source_checks':24,'actual_client':14},'runtime':health,'frontend_pid':111384,
        'files':{n:sha(root/n) for n in files},'evidence':{p.name:sha(p) for p in cp.iterdir() if p.is_file()},
        'cloud_sync':'pending','full_goal_complete':False,'new_whole_phase_completion':False,'vm':'explicitly_deferred',
        'next':'Owner-scoped metadata proposal-ID discovery; actual browser/isolated execution/release gates remain open.'}
(cp/'checkpoint.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checkpoint':str(cp),'source':record['source_version'],'plan':record['plan_revision'],'files':len(files),'handoff_exists':handoff.is_file(),'cloud':'pending'}))
