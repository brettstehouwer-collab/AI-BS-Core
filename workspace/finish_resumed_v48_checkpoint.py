from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess

root=Path(r'C:\AI-BS'); cp=root/'backups/proposal_history_5_329_48_20261024T145341207541Z'
out=Path((root/'workspace/proposal_history_v48_resume.txt').read_text(encoding='utf-8'))
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
local=read(out/'local_finalization.json')
assert not (out/'checkpoint.json').exists()
ledger=root/'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md'
assert sha(out/'cloud_record33_readback.md')==sha(ledger)==local['ledger_sha256']
assert (out/'cloud_record33_readback.md').stat().st_size==ledger.stat().st_size==101995
now=datetime.now(timezone.utc).isoformat()
receipt={'verified_at_utc':now,'id':'1vovsSPpyJRA4np2ErRt5vIgdV6-Qoojj','url':'https://drive.google.com/file/d/1vovsSPpyJRA4np2ErRt5vIgdV6-Qoojj/view',
         'local_path':'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md','bytes':101995,'sha256':sha(ledger),
         'source_version':'5.329.48','plan_revision':'1.61','record':33,'parent_id':'1EP7kfZ2zxEzS6WdvB2ipzQXlc3LbAHse',
         'shared':False,'metadata_verified':True,'readback_matches':True,'raw_byte_readback_matches':True,'previous_cloud_matches_retained_Record31':True}
with (out/'cloud_receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
index=root/'docs/engineering_ledger/cloud_index.json'; data=read(index)
assert data['pending_sync']['record']==33
data['verified_files'].append(receipt) if 'verified_files' in data else None
if 'verified_files' not in data:
    collections=[(k,v) for k,v in data.items() if isinstance(v,list) and v and isinstance(v[-1],dict) and v[-1].get('record')==31]
    assert len(collections)==1
    collections[0][1].append(receipt)
data.pop('pending_sync')
index.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
message=f'''## {now} - Source48 resumed checkpoint complete; private Record33 verified

Source5.329.48/plan1.61 operational verification is complete, with the explicit remaining-phase limitations in Record33. Same private daily ledger101995UTF8bytes/SHA256{receipt['sha256']} matched exact raw readback, same file ID/private parent/shared=false. Cloud archive contains sanitized Record33; runtime, private DB rows and proposals were not exported. No platform release.

Authoritative resumed save point: {out.as_posix()}/checkpoint.json. Backend80276, gateway25576, Vite111704, Ollama148912 verified on loopback with six false flags. Preserve the older checkpoint/completion/pause records as historical; updated top-level checkpoint links this reconciliation.

New external concurrent file observation: backend/core/run_phase4_controller.ps1 was absent at first inspection but appeared during this resumed turn. Its1493byte body only checks model ports/processes, ignores Headless/AutoApprove, continues on errors and unconditionally logs isolation Ready. It has NOT been executed, reviewed as accepted containment or used as proof of any Phase4case. Preserve its before-image and replace false-success behavior before any controller execution. No current worker VM observation was found after the user's initial success reply; the exact read-only runas command and local-password handoff have been supplied, and output is pending. Continue approved safe work; do not replay old boot scripts or infer credentials/guest licensing from full local permission.
'''
for name in ('docs/CODEX_HANDOFF.md','docs/CODEX_JOURNAL.md'):
    p=root/name; before=p.read_bytes()
    with p.open('ab') as f:f.write(('\n\n'+message+'\n').encode('utf-8'))
    assert p.read_bytes().startswith(before)
tasks=root/'docs/CODEX_TASKS.md'; text=tasks.read_text(encoding='utf-8')
text=text.replace('- [ ] Exact private Record33ledger cloud readback.','- [x] Exact private Record33ledger cloud readback:101995bytes; private same-file receipt in resumed checkpoint.',1)
text+='\n\nCurrent source48/plan1.61 resumed checkpoint finalized locally and cloud-verified. Next: fix the newly appeared false-positive Phase4port-only harness while awaiting fresh standard-worker VM state; actual VM/controller acceptance remains incomplete.\n'
tasks.write_text(text,encoding='utf-8')
names=list(local['stable_files'])+list(local['after_memory_sha256'])+['AGENTS.md','isolated_workers/windows/control/Read-CurrentVMState.ps1',
    'workspace/resume_proposal_history_v48_audit.py','workspace/finish_v48_preservation.py','workspace/restore_v48_missing_services.py',
    'workspace/restore_v48_missing_services_checked_console.py','workspace/confirm_v48_restored_acceptance.py','workspace/finalize_resumed_v48_local.py','workspace/finish_resumed_v48_checkpoint.py']
names=list(dict.fromkeys(names))
files={}
for name in names:
    p=root/name; target=out/'after'/name; target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(p.read_bytes())
    files[name]=sha(p)
evidence={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and 'after' not in p.relative_to(out).parts}
status=subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe','status','--porcelain=v1','-uno'],cwd=root,text=True)
record={'status':'verified','source_version':'5.329.48','plan_revision':'1.61','record':33,'at_utc':now,
    'git_head':local['git_head'],'tracked_changes':len(status.splitlines()),'files':files,'evidence':evidence,'cloud_sync':'verified',
    'cloud_receipt':'cloud_receipt.json','before_memory_sha256':local['before_memory_sha256'],
    'after_memory_sha256':{n:sha(root/n) for n in local['after_memory_sha256']},
    'counts':{'backend_retained':38,'client_retained':84,'offline_view_retained':30,'source_retained':23,'actual_previous':26,'actual_after_restore':16},
    'runtime':read(out/'runtime_verified.json')['processes'],'preservation':'preservation_after_restore',
    'vm':'reauthorized_fresh_worker_state_pending','full_goal_complete':False,'new_whole_phase_completion':False,
    'browser_dom_acceptance':False,'platform_release':False,
    'next':'Fresh standard-worker VM observation and real controller implementation/acceptance; remove false-ready port-only harness first'}
with (out/'checkpoint.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
assert all(sha(root/n)==h and sha(out/'after'/n)==h for n,h in files.items())
assert all(sha(out/n)==h for n,h in evidence.items())
top=read(cp/'checkpoint.json')
top['resumed_verified_checkpoint']=(out/'checkpoint.json').relative_to(root).as_posix()
top['resumed_verified_checkpoint_sha256']=sha(out/'checkpoint.json')
top['historical_checkpoint_preserved_at']=(out/'previous_checkpoint.json').relative_to(root).as_posix()
top['current_source_version']='5.329.48';top['current_plan_revision']='1.61';top['current_record']=33
top['current_status']='verified_resumed_checkpoint';top['cloud_sync']='verified_in_resumed_checkpoint'
(cp/'checkpoint.json').write_text(json.dumps(top,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'verified_files':len(files),'verified_evidence':len(evidence),'checkpoint':str(out/'checkpoint.json'),'cloud':'verified','source':'5.329.48','plan':'1.61'}))
