"""Run the authorized compression pass to completion and retain its final checkpoint."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

root = Path(r'C:\AI-BS')
out = Path('C:\\AI-BS\\backups\\e_drive_compression_20261027\\normal_64k_20261027T195041Z')
source = root / 'scratch/compress_e_ntfs_normal64k_20261027.py'
restorer = root / 'scratch/restore_e_compressed_normal64k_20261027.py'
finalizer = root / 'scratch/record_e_compression_normal64k_20261027.py'

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def json_write(name, value):
    with (out / name).open('w', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())

def rows(name):
    path = out / name
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []

assert not (out / 'supervisor_start.json').exists(), 'Supervisor already launched'
fingerprints = {str(path): sha(path) for path in [source, restorer, finalizer]}
started = utc()
json_write('supervisor_start.json', {'timestamp_utc': started, 'pid': os.getpid(),
           'executable': sys.executable, 'source_sha256': fingerprints,
           'authorization': 'Operator: skip files under64KB, use normal priority, retain all verification checks',
           'minimum_file_bytes': 65536, 'priority_mode': 'normal',
           'previous_run': str(out.parent), 'shared_run_lock': str(out.parent / 'run.lock'),
           'behavior': 'No retries; guarded pass then receipt validation and append-only final checkpoint'})
for path in [source, restorer, finalizer]:
    (out / ('supervised_' + path.name)).write_bytes(path.read_bytes())

try:
    execution = subprocess.run([sys.executable, str(source), 'all'], cwd=str(root), check=False)
    status = {'timestamp_utc': utc(), 'runner_exit_code': execution.returncode,
              'final_checkpoint_written': False, 'receipt_validation_passed': False}
    if execution.returncode:
        raise RuntimeError('Compression runner exited with error; no retry')
    receipt = json.loads((out / 'completion.json').read_text(encoding='utf-8'))
    assert receipt['started_utc'] >= started, 'Stale completion receipt'
    assert receipt['minimum_file_bytes'] == 65536 and receipt['priority_class'] == 0x20
    assert receipt['normal_priority_applied'] and not receipt['background_priority_applied']
    preparation = json.loads((out / 'preparation_manifest.json').read_text())
    prefix_checks = []
    for item in preparation['baseline_copies']:
        prior = (out.parent / item['name']).read_bytes()
        current = (out / item['name']).read_bytes()
        assert sha(out.parent / item['name']) == item['sha256'], 'Prior evidence changed'
        assert len(prior) == item['bytes'] and current.startswith(prior), 'Cumulative prefix changed'
        prefix_checks.append({'name': item['name'], 'prior_sha256': item['sha256'],
                              'prior_bytes': item['bytes'], 'prefix_preserved': True})
    json_write('baseline_prefix_verification.json', {'timestamp_utc': utc(), 'files': prefix_checks})
    assert all(sha(Path(path)) == digest for path,digest in fingerprints.items()), 'Source changed during run'
    results = rows('pilot_results.jsonl') + rows('results.jsonl')
    assert len({row['path'] for row in results}) == len(results), 'Duplicate result paths'
    bad = [row for row in results if row['status'] in {'operation_failed','verification_failed'}]
    assert not bad, 'Recorded operation/verification failure'
    done = {row['path'] for row in results}
    assert all(row['path'] in done for row in rows('intents.jsonl')), 'Unresolved compression intent'
    restored = rows('restoration_results.jsonl')
    restored.append(json.loads((out / 'reservation_reversal_probe.json').read_text(encoding='utf-8')))
    assert all(row['verified'] and row['before_sha256'] == row['after_sha256'] for row in restored)
    terminal = {(row['path'],row['started_utc']) for row in restored}
    assert all((row['path'],row['started_utc']) in terminal for row in rows('restoration_intents.jsonl'))
    restored_paths = {row['path'] for row in restored}
    retained = []
    for row in results:
        assert Path(row['path']).parts[1].casefold() not in {'steam','steamlibrary'}, 'Steam path touched'
        if row['status'] in {'compressed_verified','compressed_then_reverted_no_net_gain'}:
            assert row['before_sha256'] == row['after_sha256']
            assert row['content_and_identity_preserved'] and row['creation_and_write_times_preserved']
            if row['status'] == 'compressed_verified' and row['path'] not in restored_paths:
                retained.append(row)
            if row['status'] == 'compressed_then_reverted_no_net_gain':
                assert row['restoration_verified'] and row['path'] in restored_paths
    assert len(retained) == receipt['compressed_verified'], 'Retained count mismatch'
    status.update({'minimum_file_bytes': 65536, 'priority_mode': 'normal',
                   'below_64k_policy_skips': sum(row.get('reason') == 'below_64k_policy' for row in results),
                   'receipt_validation_passed': True, 'retained_compressed_files': len(retained),
                   'restorations_verified': len(restored), 'result_records': len(results),
                   'eligible_pass_complete': receipt['eligible_pass_complete'], 'halt_reason': receipt['halt_reason'],
                   'free_after': receipt['free_after'],
                   'available_gain_bytes': receipt['free_after'] - receipt['free_before_plan']})
    json_write('receipt_validation.json', status)
    final = subprocess.run([sys.executable, str(finalizer), 'finish'], cwd=str(root), check=False)
    assert final.returncode == 0, 'Final checkpoint write failed; preserve partial evidence'
    status.update({'timestamp_utc': utc(), 'final_checkpoint_written': True,
                   'final_checkpoint_sha256': sha(out / 'finish_checkpoint.json')})
    json_write('supervisor_completion.json', status)
except Exception as exc:
    failure = {'timestamp_utc': utc(), 'error_type':type(exc).__name__, 'message':str(exc),
               'traceback':traceback.format_exc(), 'automatic_retry': False,
               'state': 'Stopped; preserve evidence and inspect before resuming'}
    json_write('supervisor_failure.json', failure)
    # Retain a bounded failure record even when final receipt validation cannot finish.
    addition = ('\n\n### Record152 continuation - Compression supervisor stopped - ' + utc() + '\n' +
                'The authorized compression supervisor stopped without automatic retry. '
                'Inspect backups/e_drive_compression_20261027/normal_64k_20261027T195041Z/supervisor_failure.json and retained '
                'per-file intents/results before further mutation. This does not claim pass completion.\n')
    for rel in ['docs/CODEX_HANDOFF.md','docs/CODEX_JOURNAL.md','docs/CODEX_TASKS.md']:
        with (root / rel).open('ab') as stream:
            stream.write(addition.encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
    raise
