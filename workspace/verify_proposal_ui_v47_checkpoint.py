from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
root=Path(r'C:\AI-BS');cp=Path((root/'workspace/proposal_ui_v47_checkpoint.txt').read_text(encoding='utf-8').strip())
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=read(cp/'checkpoint.json');assert record['cloud_sync']=='pending'
assert all(sha(root/n)==h and sha(cp/'after'/n)==h for n,h in record['files'].items())
assert all(sha(cp/n)==h for n,h in record['evidence'].items())
ledger=root/'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md';assert ledger.stat().st_size==88394
receipt={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'id':'1vovsSPpyJRA4np2ErRt5vIgdV6-Qoojj',
         'url':'https://drive.google.com/file/d/1vovsSPpyJRA4np2ErRt5vIgdV6-Qoojj/view',
         'local_path':ledger.relative_to(root).as_posix(),'bytes':ledger.stat().st_size,'sha256':sha(ledger),
         'source_version':'5.329.47','plan_revision':'1.59','record':31,'parent_id':'1EP7kfZ2zxEzS6WdvB2ipzQXlc3LbAHse',
         'shared':False,'metadata_verified':True,'readback_matches':True,'raw_byte_readback_matches':True,
         'previous_cloud_matches_retained_Record30':True}
index=root/'docs/engineering_ledger/cloud_index.json';value=read(index)
value['ledger_receipt_history'].append(receipt);value['ledger']=receipt;value.pop('pending_sync',None)
value['sync_note']='Record31/source47/plan1.59 exact same-private-file readback. Proposal UI evidence summarized; no raw candidates, chats, credentials or documents exported.'
index.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
for path in [index,Path(__file__)]:
    name=path.relative_to(root).as_posix();target=cp/'after'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes());record['files'][name]=sha(path)
(cp/'cloud_verified.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
assert all(sha(root/n)==h and sha(cp/'after'/n)==h for n,h in record['files'].items())
checks={'source_and_saved_files_exact':True,'files_count':len(record['files']),
        'prior_evidence_hashes_exact':True,'evidence_count':len(record['evidence']),
        'private_cloud_byte_receipt':receipt,'handoff_exists':(root/'docs/CODEX_HANDOFF.md').is_file(),
        'source_version':'5.329.47','plan_revision':'1.59','full_goal_complete':False,'new_whole_phase_completion':False,
        'scope':'UI client/offline view/actual retained API reads; browser and expanded execution not accepted'}
(cp/'completion.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
record['cloud_sync']=receipt;record['completion']='completion.json';record['final_verified_at_utc']=datetime.now(timezone.utc).isoformat()
record['evidence'].update({n:sha(cp/n) for n in ['cloud_verified.json','completion.json']})
(cp/'checkpoint.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files_exact':len(record['files']),'evidence_exact':len(record['evidence']),'cloud_sha256':receipt['sha256'],
                  'cloud_bytes':receipt['bytes'],'handoff_exists':checks['handoff_exists'],'source_version':'5.329.47','full_goal_complete':False}))
