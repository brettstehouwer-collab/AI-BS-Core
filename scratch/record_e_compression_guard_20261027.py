from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os

root = Path(r'C:\AI-BS')
out = root / 'backups/e_drive_compression_20261027'
dest = out / 'reservation_guard_checkpoint'
dest.mkdir(exist_ok=False)
stamp = datetime.now(timezone.utc).isoformat()
text = (
    'Broad compression was paused between files after156 full-hash-preserved operations because available '
    'space fell despite reported allocation savings. Read-only VSS showed zero allocated shadow storage; '
    'volume counters showed5,100,965,888 reserved bytes. A bounded restoration of the incompressible '
    'Cymatics-AURORA-Sources.zip to its original uncompressed state released3,884,363,776 available bytes '
    'with full SHA-256, identity, size and creation/write-time preservation. The two root installers were '
    'likewise restored and verified. Available space then47,466,958,848 bytes, above initial46,668,140,544; '
    'reserved space18,862,080. The precise NTFS reservation mechanism remains unproven; no VSS deletion, '
    'volume setting, registry, restart or process changes were made. Initial unaligned/subcluster allocation '
    'metrics are retained as historical observations and not equated with usable reclaimed space. '
    'Revised pass skips already encoded archive/installer/media formats, uses same-handle allocation queries '
    'and volume available/used/reserved counters after each close, and restores any newly compressed file '
    'with no available-space gain. Restoration revalidates original hash, identity and creation/write times '
    'before mutation and verifies again afterward; any unresolved mutation/restore intent or verification '
    'failure blocks continuation. An exclusive C-side run lock prevents runner interleaving. '
    'The initial paused completion/stop marker and script versions are retained; guarded continuation is '
    'authorized under the operator instruction. Remaining original exclusions still apply. '
    'No project latency/dropout acceptance is established. The read-only fsutil allocationreport returned '
    'Error50/not-supported and was not repeated. Evidence:backups/e_drive_compression_20261027. '
    'Cloud synchronization remains pending.\n'
)
receipt = {'timestamp_utc': stamp, 'documents': []}
for rel in ['docs/CODEX_HANDOFF.md', 'docs/CODEX_JOURNAL.md', 'docs/CODEX_TASKS.md',
            'docs/CODEX_DECISIONS.md', 'docs/E_DRIVE_COMPRESSION_ASSESSMENT_2026-10-27.md',
            'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md']:
    path = root / rel
    before = path.read_bytes()
    (dest / path.name).write_bytes(before)
    addition = '\n\n### Record152 continuation - Reserved-space guard - ' + stamp + '\n' + text
    with path.open('ab') as f:
        f.write(addition.encode('utf-8'))
        f.flush()
        os.fsync(f.fileno())
    after = path.read_bytes()
    assert after.startswith(before)
    receipt['documents'].append({'path':rel, 'before_sha256': hashlib.sha256(before).hexdigest(),
                                 'after_sha256': hashlib.sha256(after).hexdigest(), 'prior_prefix_preserved': True})
for name in ['compress_e_ntfs_20261027.py', 'restore_e_compressed_20261027.py',
             'e_compression_reservation_probe_20261027.py']:
    (dest / name).write_bytes((root / 'scratch' / name).read_bytes())
(dest / 'checkpoint.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'documents':len(receipt['documents']), 'prior_prefix_preserved':True}))
