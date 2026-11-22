from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

root = Path(r'C:\AI-BS')
out = root / 'backups/e_drive_compression_20261027'
phase = sys.argv[1]
assert phase in {'start', 'finish'}
backup = out / (phase + '_document_originals')
backup.mkdir(exist_ok=False)
stamp = datetime.now(timezone.utc).isoformat()
plan = json.loads((out / 'plan.json').read_text())
if phase == 'start':
    pilot = json.loads((out / 'pilot_receipt.json').read_text())
    summary = (
        'Operator explicitly directs: ignore Steam and compress the rest. This newer apply authorization '
        'includes ordinary audio/sample files previously excluded while assessment-only. Apply transparent '
        'per-file NTFS LZNT1 on E:; preserve filenames, contents, creation/write times and directory inheritance. '
        'Exclude Steam, VM/WSL/backing storage, databases/sidecars/index stores, model weights, system/boot '
        'and protected app-managed trees, reparse/offline/encrypted/sparse/read-only/system files, hardlinks, '
        'files above30GB and recently changing/busy files. No deletion/move, ACL change, service/VM action or '
        'whole-directory compression. Per-file intent is retained before mutation; same-handle SHA-256, '
        'identity, size, compression state, allocation and creation/write timestamps are checked. Background '
        'priority,8GiB free-space floor and immediate verification-failure halt apply. '
        f'Pilot compressed {pilot["compressed_verified"]} files with byte/hash/time/identity preservation and '
        f'{pilot["totals"]["saved_bytes"]:,} bytes measured reclaimed. Broad pass pending; no performance/DAW '
        'acceptance claimed. Initial Windows Python3.12 DirEntry zero-inode guard skipped both pilot files '
        'without mutation; explicit os.stat correction succeeded once. Initial plan/guard evidence retained. '
        'Independent review corrected post-mutation exception classification and compound model exclusions. '
    )
else:
    result = json.loads((out / 'completion.json').read_text())
    counts = result['totals']
    summary = (
        f'Authorized E: NTFS compression pass ended; halt_reason={result["halt_reason"]!r}. '
        f'Counts={json.dumps(counts, sort_keys=True)}. '
        f'Retained per-file allocation delta={counts.get("saved_bytes",0):,} bytes '
        f'({counts.get("saved_bytes",0)/2**30:.2f}GiB). Volume free space changed from '
        f'{result["free_before_plan"]:,} to {result["free_after"]:,} bytes (available-space gain '
        f'{(result["free_after"]-result["free_before_plan"])/2**30:.2f}GiB); concurrent writes can affect '
        'the volume delta. Initial tiny/resident allocation estimates were not uniform physical '
        'allocation measures; later operations use same-handle FileStandardInfo. Every compressed_verified '
        'entry binds matching full before/after SHA-256, size, '
        'file identity and creation/write timestamps. This is preservation verification, not active-project '
        'latency/dropout acceptance. Steam and recorded protected types/trees were excluded; busy/changing '
        'files were skipped without forcing handles or stopping processes. Already encoded formats and '
        'the additional AI-BS Broadcast Studio, AI_BS_Resources, .jdks/.local/.cache app/runtime trees were '
        'excluded by the final runner. Initial compressed ZIP/installers were restored with full byte/time/'
        'identity verification after a reserved-space loss was diagnosed. The current guard measures '
        'usable space after every file close and restores attempts with no net gain; durable unresolved '
        'compression/restoration intents block resumption. Initial and paused receipts are preserved. '
        'CloseHandle failure or failed FSCTL with changed state now cause a verification halt; these '
        'branches were reviewed, not fault-injected. Plan-only review found extensionless model weights '
        'within the now protected application tree. No deletion/move/permissions, '
        'directory inheritance, service, network, VM or model configuration changes. '
    )
common = summary + ('Evidence:backups/e_drive_compression_20261027 including plan, intents, pilot and '
                    'per-file result receipts. Preserve historical assessment and incomplete attempts. '
                    'Cloud engineering-ledger synchronization pending.\n')
paths = ['docs/E_DRIVE_COMPRESSION_ASSESSMENT_2026-10-27.md', 'docs/CODEX_HANDOFF.md',
         'docs/CODEX_JOURNAL.md', 'docs/CODEX_TASKS.md',
         'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md']
if phase == 'start':
    paths.append('docs/CODEX_DECISIONS.md')
receipt = {'phase': phase, 'timestamp_utc': stamp, 'record':152, 'documents':[], 'evidence':[]}
for rel in paths:
    path = root / rel
    before = path.read_bytes()
    (backup / path.name).write_bytes(before)
    title = 'ADR-095 addendum' if rel.endswith('CODEX_DECISIONS.md') else 'Record152 continuation'
    addition = '\n\n### ' + title + ' - Authorized E compression ' + phase + ' - ' + stamp + '\n' + common
    if rel.endswith('CODEX_TASKS.md'):
        addition += ('\n- [x] Explicit authorization received; same-handle log/WAV preservation pilot passed.\n'
                     '- [ ] Authorized ordinary-file compression in progress; final receipt pending.\n') if phase == 'start' else (
                     '\n- [x] Compression attempt ended; measured outcome and exclusions retained in completion.json.\n'
                     + ('- [x] Final guarded eligible-file pass completed.\n' if result.get('eligible_pass_complete') else
                        '- [ ] Eligible-file pass incomplete; consult halt reason and remaining count.\n') +
                     '- [ ] Active DAW/AI-BS workload performance acceptance remains untested.\n')
    with path.open('ab') as stream:
        stream.write(addition.encode())
    after = path.read_bytes()
    assert after.startswith(before)
    receipt['documents'].append({'path':rel, 'before_sha256':hashlib.sha256(before).hexdigest(),
                                 'after_sha256':hashlib.sha256(after).hexdigest(), 'prior_byte_prefix_preserved':True})
script = root / 'scratch/compress_e_ntfs_20261027.py'
copy = out / ('compress_e_ntfs_' + phase + '.py')
copy.write_bytes(script.read_bytes())
for path in [out / 'plan.json', out / 'pilot_receipt.json', copy] + ([out/'completion.json'] if phase == 'finish' else []):
    receipt['evidence'].append({'path':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(out / (phase + '_checkpoint.json')).write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'phase':phase, 'documents_appended':len(paths), 'prior_bytes_preserved':True}))
