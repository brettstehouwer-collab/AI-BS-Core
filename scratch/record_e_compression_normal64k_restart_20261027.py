"""Append the reviewed compression policy and actual launch state to the engineering record."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

root = Path(r'C:\AI-BS')
parent = root / 'backups/e_drive_compression_20261027'
out = parent / 'normal_64k_20261027T195041Z'
phase = sys.argv[1]
assert phase in {'prepared', 'running'}
dest = out / (phase + '_checkpoint')
dest.mkdir(exist_ok=False)
stamp = datetime.now(timezone.utc).isoformat()
manifest = json.loads((out / 'preparation_manifest.json').read_text())
verification = json.loads((out / 'policy_verification.json').read_text())
assert verification['all_passed'] and not verification['e_file_reads_or_mutations']
for source in manifest['sources']:
    assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest() == source['sha256']
progress = json.loads((out / 'progress.json').read_text()) if phase == 'running' else None
start = json.loads((out / 'supervisor_start.json').read_text()) if phase == 'running' else None
if phase == 'running':
    assert progress['minimum_file_bytes'] == 65536 and progress['priority_class'] == 0x20
    assert progress['priority_mode'] == 'normal'
    assert not (out / 'supervisor_failure.json').exists()
state = ('REVISED RUNNING: supervisorPID' + str(start['pid']) + ', runnerPID' + str(progress['pid']) +
         ', observedUTC' + progress['timestamp_utc'] + '; counts are cumulative: ' +
         json.dumps(progress['totals'], sort_keys=True) + '. ') if phase == 'running' else (
         'PREPARED, not running: original background pass stopped cleanly at a file boundary. '
         'Its supervisor validated all cumulative receipts and appended the incomplete stop checkpoint. ')
summary = (
    'Operator explicitly directs skipping files under64KB and normal priority while retaining all verification. '
    + state +
    'The new cutoff is strictly below65,536bytes; a65,536byte file still enters the original admission checks. '
    'Skipped tiny files are recorded before opening/mutation. Already processed files stay unchanged. '
    'The revised runner sets and queries NORMAL_PRIORITY_CLASS0x20 before dispatch; failure blocks work. '
    'All15 other runner functions and the restoration function are AST-identical to the previous version. '
    'Synthetic exact-boundary, denied-priority and wrong-reported-priority checks passed without any E:file '
    'read or mutation; all4 revised sources compiled. Source review found no blocking issue. '
    'This preserves same-handle full before/after SHA256, identity, size, creation/write time, compression '
    'state and allocation checks, durable pre-mutation intents, per-file usable-space checks, verified '
    'no-net-gain restoration,8GiB free floor and immediate verification-error/two-operation-error halts. '
    'The original parent run.lock is shared across variants; work remains serial. Old scripts and all '
    'old receipts remain in place with the parent stop_requested marker. The new evidence child directory '
    'contains verified copies of the complete cumulative plan/pilot/results/intents/restorations; supervisor '
    'checks original snapshot hashes and cumulative prefixes after the run. Child stop_requested controls '
    'the revised runner. New helper imports, finalizer and source pins all bind the revised variants. '
    'Steam/model/database/VM/system/app exclusions remain. Active DAW/project latency acceptance is '
    'untested. No deletion/move, ACL/inheritance, service, VM, network, driver or activation-control changes. '
    'Evidence:backups/e_drive_compression_20261027/normal_64k_20261027T195041Z; active_run.json in the parent '
    'locates the revised receipts. Preserve earlier failures and incomplete receipts. Cloud ledger sync pending.\n'
)
receipt = {'phase': phase, 'timestamp_utc': stamp, 'source_pins': manifest['sources'],
           'observed_progress': progress, 'supervisor_start': start, 'documents': []}
for rel in ['docs/CODEX_HANDOFF.md', 'docs/CODEX_JOURNAL.md', 'docs/CODEX_TASKS.md',
            'docs/CODEX_DECISIONS.md', 'docs/E_DRIVE_COMPRESSION_ASSESSMENT_2026-10-27.md',
            'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md']:
    path = root / rel
    before = path.read_bytes()
    (dest / path.name).write_bytes(before)
    addition = '\n\n### Record152 continuation - Normal-priority64KiB policy ' + phase + ' - ' + stamp + '\n' + summary
    if rel.endswith('CODEX_TASKS.md'):
        addition += ('\n- [x] Operator-authorized size/priority policy prepared and checked; old pass stopped and preserved.\n'
                     + ('- [x] Revised single-runner pass resumed with verified normal priority; completion remains pending.\n'
                        if phase == 'running' else '- [ ] Revised runner launch and runtime verification pending.\n')
                     + '- [ ] Revised eligible-file pass and final receipt validation pending.\n')
    with path.open('ab') as stream:
        stream.write(addition.encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())
    after = path.read_bytes()
    assert after.startswith(before), str(path)
    receipt['documents'].append({'path': rel, 'before_sha256': hashlib.sha256(before).hexdigest(),
                                 'after_sha256': hashlib.sha256(after).hexdigest(), 'prior_prefix_preserved': True})
active = parent / 'active_run.json'
if active.exists():
    (dest / 'active_run_before.json').write_bytes(active.read_bytes())
active_data = {'checkpoint_utc': stamp, 'checkpoint_state': phase, 'evidence_directory': str(out),
               'minimum_file_bytes': 65536, 'priority_mode': 'normal',
               'stop_marker': str(out / 'stop_requested'),
               'live_status_files': ['progress.json', 'completion.json', 'supervisor_completion.json', 'supervisor_failure.json']}
temporary = dest / 'active_run_after.json'
temporary.write_text(json.dumps(active_data, indent=2) + '\n')
with active.open('wb') as stream:
    stream.write(temporary.read_bytes())
    stream.flush()
    os.fsync(stream.fileno())
(dest / 'checkpoint.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'phase': phase, 'documents_appended': len(receipt['documents']),
                  'prior_bytes_preserved': True, 'evidence_directory': str(out)}))
