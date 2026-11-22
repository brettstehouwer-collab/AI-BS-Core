"""Finish readback verification without replaying checkpoint mutations."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
R=Path(r'C:\AI-BS')
E=Path(__file__).resolve().parent
B=R/'backups/post_reboot_verification_20261025_record100'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda b:hashlib.sha256(b).hexdigest()
checkpoint=load(B/'checkpoint.json')
before=load(B/'before_manifest.json')
assert checkpoint['record']==100
for rel,entry in checkpoint['final_document_hashes'].items():
    assert sha((R/rel).read_bytes())==entry['sha256'],rel
for rel in ('docs/CODEX_HANDOFF.md','docs/CODEX_JOURNAL.md','docs/CODEX_DECISIONS.md','docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md'):
    assert (R/rel).read_bytes().startswith((B/'before'/rel).read_bytes()),rel
assert sha((R/'AGENTS.md').read_bytes())==before['AGENTS.md']['sha256']
handoff=(R/'docs/CODEX_HANDOFF.md').read_text(encoding='utf-8-sig')
assert handoff.count('## Record100 — Post-reboot recovery accepted;')==1
assert 'Record100' in (R/'docs/CODEX_TASKS.md').read_text(encoding='utf-8-sig')
assert 'ADR-049' in (R/'docs/CODEX_DECISIONS.md').read_text(encoding='utf-8-sig')
cloud=load(R/'docs/engineering_ledger/cloud_index.json')
old_cloud=load(B/'before/docs/engineering_ledger/cloud_index.json')
assert cloud['ledger']==old_cloud['ledger'] and 100 in cloud['pending_local_records']
failure='The first checkpoint writer completed document writes and checkpoint JSON, then its final text assertion used Windows cp1252 and raised UnicodeDecodeError. No application failure or rollback occurred. Corrected explicit UTF-8 and verified existing results without rerunning the writer or duplicating appends.\n'
(E/'save_record100_attempt1.txt').write_text(failure,encoding='utf-8')
entry='\n\nRecord100 finalization verification: '+failure
with (R/'docs/CODEX_JOURNAL.md').open('ab') as f:f.write(entry.encode('utf-8'))
checkpoint['final_document_hashes']={rel:{'sha256':sha((R/rel).read_bytes()),'bytes':(R/rel).stat().st_size} for rel in before}
checkpoint['evidence_hashes']={str(f.relative_to(E)).replace('\\','/'):{'sha256':sha(f.read_bytes()),'bytes':f.stat().st_size} for f in E.rglob('*') if f.is_file()}
checkpoint['finalization_note']=failure.strip()
checkpoint['verified_utc']=datetime.now(timezone.utc).isoformat()
(B/'checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
for rel,item in load(B/'checkpoint.json')['final_document_hashes'].items():
    assert sha((R/rel).read_bytes())==item['sha256'],rel
receipt={'observed_utc':checkpoint['verified_utc'],'record':100,'all_seven_document_hashes_pass':True,'append_only_history_preserved':True,'checkpoint_readback_pass':True,'cloud_verified_ledger_unchanged':True,'duplicate_record100_appends':False,'application_runtime_changes':False,'first_attempt_diagnostic_preserved':True}
(B/'verification_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
