from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

root = Path(r'C:\AI-BS')
out = root / 'backups/e_drive_compression_20261027'
dest = out / 'supervised_run_checkpoint'
dest.mkdir(exist_ok=False)
stamp = datetime.now(timezone.utc).isoformat()
start = json.loads((out / 'supervisor_start.json').read_text())
progress = json.loads((out / 'progress.json').read_text())
summary = (
    f'The authorized guarded compression pass is RUNNING, not complete. SupervisorPID{start["pid"]} '
    f'started{start["timestamp_utc"]}; process identities are historical checkpoint evidence only. '
    f'Latest observed progress {progress["timestamp_utc"]}: {json.dumps(progress["totals"],sort_keys=True)}, '
    f'available{progress["free_now"]:,} bytes; remaining planned records{progress["remaining"]}. '
    'Hidden supervisor runs the single locked low-priority runner to its natural completion, with no '
    'automatic retries, then validates retained receipts/counts/intents and appends the final engineering '
    'checkpoint. Failures retain a supervisor_failure.json and append a bounded stop record; do not '
    'infer completion merely from this launch. Read progress.json, completion.json and '
    'supervisor_completion.json for actual eventual outcome. Steam and protected model/database/VM/'
    'system/app trees remain excluded. Plan-only review found extensionless speech/transformer model '
    'weights under AI-BS Broadcast Studio, now excluded along with AI_BS_Resources/.jdks/.local/.cache; '
    'Pandora .bin installers skipped. Source fixes for CloseHandle failure and failed FSCTL with changed '
    'state were made before this restart; no such error was observed. Prior pause receipts and source '
    'versions retained. A multi-file apply_patch expected-context mismatch changed no files; verified '
    'current source, reapplied smaller patch and Python compile checks passed. No E mutation occurred '
    'during that patch failure. All compressed/reverted contents verified immediately per-file; active '
    'project playback/performance remains untested. No deletion/move, directory inheritance, ACL, '
    'service/network/VM, driver or activation-control changes. No cloud synchronization performed.\n'
)
receipt = {'timestamp_utc':stamp,'supervisor_start':start,'observed_progress':progress,'documents':[]}
for rel in ['docs/CODEX_HANDOFF.md','docs/CODEX_JOURNAL.md','docs/CODEX_TASKS.md',
            'docs/CODEX_DECISIONS.md','docs/E_DRIVE_COMPRESSION_ASSESSMENT_2026-10-27.md',
            'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md']:
    path = root / rel
    before = path.read_bytes()
    (dest / path.name).write_bytes(before)
    with path.open('ab') as stream:
        stream.write(('\n\n### Record152 continuation - Supervised compression running - '+stamp+'\n'+summary).encode())
        stream.flush()
        os.fsync(stream.fileno())
    after = path.read_bytes()
    assert after.startswith(before)
    receipt['documents'].append({'path':rel,'before_sha256':hashlib.sha256(before).hexdigest(),
                                'after_sha256':hashlib.sha256(after).hexdigest(),'prior_prefix_preserved':True})
(dest / 'checkpoint.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'documents':len(receipt['documents']),'status':'running','prior_prefix_preserved':True}))
