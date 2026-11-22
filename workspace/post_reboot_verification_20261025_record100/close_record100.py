import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
R=Path(r'C:\AI-BS');E=Path(__file__).resolve().parent;B=R/'backups/post_reboot_verification_20261025_record100'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda b:hashlib.sha256(b).hexdigest()
cp=load(B/'checkpoint.json');obs=load(E/'closing_observation.json')
for rel,item in cp['final_document_hashes'].items():
    assert sha((R/rel).read_bytes())==item['sha256'],rel
codex=max(obs['codex'],key=lambda p:p['PrivateMemorySize64'])
private=codex['PrivateMemorySize64']/2**30
note=f"\n\nRecord100 closing observation ({obs['observed_utc']}): Codex {codex['Id']} private commit {private:.3f} GiB, approximately level with the 22:27:10 sample after the earlier jumps; system commit {obs['commit_percent']:.2f}%, C: free {obs['c_free_gib']:.3f} GiB, pagefile file length {obs['pagefile_bytes']/2**30:.3f} GiB. Short stability does not prove the underlying issue fixed. No settings/process/network changes. Next diagnostic remains a small fresh Codex session after saving and closing active work.\n"
for rel in ('docs/CODEX_HANDOFF.md','docs/CODEX_JOURNAL.md','docs/CODEX_TASKS.md','docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md'):
    with (R/rel).open('ab') as f:f.write(note.encode('utf-8'))
status=f'''Record100: post-reboot check complete

Stehouwer Publishing and www are online (HTTP 200). Public API health is also 200. Both publishing logon tasks recovered under footb. All 19 reviewed files match, and private paths remain 404. These are startup and basic availability checks; full workflows remain pending.

At {obs['observed_utc']} (6:30 PM Eastern):
- C: has {obs['c_free_gib']:.1f} GiB free, about {obs['c_free_gib']-124.69:.1f} GiB more than the final pre-reboot sample.
- System commit is {obs['commit_percent']:.1f}%.
- Codex private commit is {private:.1f} GiB. It rose from 4.3 to 8.3 to 16.3 GiB during this run, then stayed near 16.3 for the final three minutes. The underlying cause is unresolved.
- The pagefile is {obs['pagefile_bytes']/2**30:.1f} GiB; its settings were not changed.

Major work remains deferred. For the next diagnostic, save other active work, close/reopen Codex, and use a small fresh task from NEXT_SESSION.txt. This is a diagnostic step, not a promised fix. No reboot, app termination/update, deletion, paging change or network reconfiguration was performed by this run.

Checkpoint: C:/AI-BS/backups/post_reboot_verification_20261025_record100/checkpoint.json
Detailed evidence: Recovery_Report.txt and the timestamped JSON samples in this directory.
Official OpenAI troubleshooting reference: https://learn.chatgpt.com/docs/reference/troubleshooting
'''
(E/'STATUS.txt').write_text(status,encoding='utf-8')
cp['closing_observation']=obs
cp['final_document_hashes']={rel:{'sha256':sha((R/rel).read_bytes()),'bytes':(R/rel).stat().st_size} for rel in cp['final_document_hashes']}
cp['evidence_hashes']={str(f.relative_to(E)).replace('\\','/'):{'sha256':sha(f.read_bytes()),'bytes':f.stat().st_size} for f in E.rglob('*') if f.is_file()}
cp['verified_utc']=datetime.now(timezone.utc).isoformat()
(B/'checkpoint.json').write_text(json.dumps(cp,indent=2)+'\n',encoding='utf-8')
for rel,item in load(B/'checkpoint.json')['final_document_hashes'].items():
    assert sha((R/rel).read_bytes())==item['sha256'],rel
receipt=load(B/'verification_receipt.json');receipt.update(observed_utc=cp['verified_utc'],closing_observation_recorded=True,all_seven_document_hashes_pass=True)
(B/'verification_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'saved':True,'record':100,'documents_verified':7,'c_free_gib':round(obs['c_free_gib'],1),'commit_percent':round(obs['commit_percent'],1),'codex_private_gib':round(private,1),'status_file':str(E/'STATUS.txt')}))
