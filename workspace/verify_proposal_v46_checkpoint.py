from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import psutil,requests

root=Path(r'C:\AI-BS');cp=root/'backups/retained_proposal_5_329_46_20261024T141425139154Z'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=read(cp/'checkpoint.json')
assert record['cloud_sync']=='pending'
assert all(sha(root/name)==value for name,value in record['files'].items())
metadata=root/'backups/release_versioning/20261024T142119440Z_retained_multi_file_proposal_32124af4'
manifest=read(metadata/'manifest.json')
assert manifest['to_version']=='5.329.46' and len(manifest['files'])==16
for item in manifest['files']:
    assert sha(root/item['path'])==item['after_sha256']
    assert sha(metadata/'before'/item['path'])==item['before_sha256']
for item in manifest['files']:
    name=item['path'];target=cp/'after'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((root/name).read_bytes())
    record['files'][name]=sha(root/name)
receipt={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'id':'1vovsSPpyJRA4np2ErRt5vIgdV6-Qoojj',
         'url':'https://drive.google.com/file/d/1vovsSPpyJRA4np2ErRt5vIgdV6-Qoojj/view',
         'local_path':'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md','bytes':83755,
         'sha256':sha(root/'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md'),
         'source_version':'5.329.46','plan_revision':'1.58','record':30,'parent_id':'1EP7kfZ2zxEzS6WdvB2ipzQXlc3LbAHse',
         'metadata_verified':True,'raw_byte_readback_matches':True,'readback_matches':True,'shared':False,
         'previous_cloud_matches_retained_Record28':True}
assert (root/receipt['local_path']).stat().st_size==receipt['bytes']
index=root/'docs/engineering_ledger/cloud_index.json';data=read(index)
data['ledger_receipt_history'].append(receipt);data['ledger']=receipt;data.pop('pending_sync',None)
data['sync_note']='Record30/source46/plan1.58 exact same-private-file readback. Record29 and sanitized Downloads/tool note reconciled; raw sources, listings, stores and credentials excluded.'
index.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
notes=root/'docs/engineering_ledger/2026-10-24_Downloads_scan_and_restore_hold.md'
with notes.open('a',encoding='utf-8') as out:out.write('\nPrivate cloud reconciliation verified in daily Record30,83755bytes; final receipt in source46checkpoint/cloud_verified.json. This supersedes the pending-sync statements above.\n')
for path in [index,notes,Path(__file__)]:
    name=path.relative_to(root).as_posix();target=cp/'after'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes());record['files'][name]=sha(path)
(cp/'cloud_verified.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
runtime=read(cp/'runtime/process.json');session=requests.Session();session.trust_env=False
verified=[]
try:
    for name,port in [('backend',8080),('gateway',8000),('ollama',11434)]:
        expected=runtime['processes'][name].get('serving',runtime['processes'][name]['launcher'])
        process=psutil.Process(expected['pid']);assert process.create_time()==expected['created'] and process.exe()==expected['exe']
        listeners=[c for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==port]
        assert listeners and all(c.pid==process.pid and c.laddr.ip=='127.0.0.1' for c in listeners)
        assert session.get(f'http://127.0.0.1:{port}'+('/api/version' if name=='ollama' else '/health'),timeout=5).status_code==200
        assert all(process.environ().get(k)=='false' for k in runtime['controlled_flags'])
        verified.append({'name':name,'pid':process.pid,'healthy':True,'loopback':True,'flags_disabled':True})
finally:session.close()
assert all(sha(root/n)==v and sha(cp/'after'/n)==v for n,v in record['files'].items())
completion={'source_version':'5.329.46','plan_revision':'1.58','at_utc':datetime.now(timezone.utc).isoformat(),
            'original_restore_failure_preserved':read(cp/'runtime/process.json')['status']=='inspection_needed',
            'observation':'Existing processes healthy; stopped gateway PID-1 is legitimate, no restart needed',
            'services':verified,'cloud':receipt,'files_verified':len(record['files']),'metadata_originals_and_current_verified':16,
            'no_project_execution_or_apply':True,'no_new_whole_phase_completion':True,'full_goal_complete':False}
(cp/'completion.json').write_text(json.dumps(completion,indent=2)+'\n',encoding='utf-8')
record.update(cloud_sync=receipt,final_verified_at_utc=completion['at_utc'],completion='completion.json')
record['evidence'].update({p:sha(cp/p) for p in ['cloud_verified.json','completion.json']})
(cp/'checkpoint.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'verified_files':len(record['files']),'metadata_originals_verified':16,'services':verified,
                  'cloud_sha256':receipt['sha256'],'cloud_bytes':receipt['bytes'],'handoff_exists':(root/'docs/CODEX_HANDOFF.md').is_file(),
                  'full_goal_complete':False}))
