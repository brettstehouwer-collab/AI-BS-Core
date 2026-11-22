from datetime import datetime, timezone
from pathlib import Path
import hashlib, json

root = Path(r'C:\AI-BS')
cp = Path((root / 'workspace/proposal_history_v48_checkpoint.txt').read_text(encoding='utf-8').strip())
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

record = read(cp / 'checkpoint.json')
assert record['cloud_sync'] == 'pending'
assert all(sha(root / n) == h and sha(cp / 'after' / n) == h for n, h in record['files'].items())
assert all(sha(cp / n) == h for n, h in record['evidence'].items())

checks = {
    'source_and_saved_files_exact': True,
    'files_count': len(record['files']),
    'prior_evidence_hashes_exact': True,
    'evidence_count': len(record['evidence']),
    'cloud_sync_status': 'pending_private_verification',
    'handoff_exists': (root / 'docs/CODEX_HANDOFF.md').is_file(),
    'source_version': '5.329.48',
    'plan_revision': '1.60',
    'full_goal_complete': False,
    'new_whole_phase_completion': False,
    'scope': 'Saved proposal metadata history discovery and offline SSR of that data; browser and expanded execution not accepted',
}
(cp / 'completion.json').write_text(json.dumps(checks, indent=2) + '\n', encoding='utf-8')
record['completion'] = 'completion.json'
record['final_verified_at_utc'] = datetime.now(timezone.utc).isoformat()
record['evidence']['completion.json'] = sha(cp / 'completion.json')
(cp / 'checkpoint.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')

print(json.dumps({
    'files_exact': len(record['files']),
    'evidence_exact': len(record['evidence']),
    'handoff_exists': checks['handoff_exists'],
    'source_version': '5.329.48',
    'plan_revision': '1.60',
    'full_goal_complete': False,
}))
