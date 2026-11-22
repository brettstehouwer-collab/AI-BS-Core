from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import psutil
import requests

root = Path(r'C:\AI-BS')
cp = Path((root / 'workspace/proposal_history_v48_checkpoint.txt').read_text(encoding='utf-8').strip())
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

assert not (cp / 'checkpoint.json').exists(), 'Checkpoint already finalized'

tests = {
    'client_green.json': read(cp / 'client_green.json'),
    'view_green.json': read(cp / 'view_green.json'),
    'verified.json': read(cp / 'verified.json'),
    'client_live.json': read(cp / 'client_live.json'),
}
assert tests['client_green.json']['passed'] == tests['client_green.json']['count'] == 84
assert tests['view_green.json']['passed'] == tests['view_green.json']['count'] == 30
assert tests['verified.json']['passed']
assert tests['client_live.json']['status'] == 'passed' and tests['client_live.json']['count'] == 16

audit = read(cp / 'source_audit.json')
assert audit['passed'] == audit['count'] == 23

preservation = read(cp / 'preservation_before_restart.json')
assert preservation['status'] == 'verified'

panel_paths = [
    base + '/CodingPreparationPanel.jsx'
    for base in [
        'frontend/src/components',
        'frontend/components',
        'frontend/src/components/components',
        'frontend/components/components',
    ]
]
assert len({sha(root / n) for n in panel_paths}) == 1

runtime = read(cp / 'runtime_after_connection_closed/process.json')
assert runtime['status'] == 'healthy'
session = requests.Session()
session.trust_env = False
health = []
flags = [
    'AI_BS_RECDEBUT_OUTBOUND_ENABLED',
    'AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED',
    'AI_BS_DISCORD_NOTIFICATIONS_ENABLED',
    'AI_BS_BACKEND_MANAGE_DAEMONS',
    'AI_BS_BACKEND_BACKGROUND_ENABLED',
    'AI_BS_ALLOW_DESTRUCTIVE_ACTIONS',
]
try:
    for name, port in [('backend', 8080), ('gateway', 8000), ('ollama', 11434)]:
        pid = runtime['serving_pid'] if name == 'backend' else next(item['pid'] for item in runtime['other_listeners_before'] if item['port'] == port)
        p = psutil.Process(pid)
        assert p.is_running()
        if name == 'backend':
            assert all(p.environ().get(k) == 'false' for k in flags)
        url = f'http://127.0.0.1:{port}' + ('/api/version' if name == 'ollama' else '/health')
        assert session.get(url, timeout=5).status_code == 200
        health.append({'service': name, 'pid': p.pid, 'healthy': True, 'activation_flags_false': True})

    listeners = [c for c in psutil.net_connections(kind='tcp') if c.status == 'LISTEN' and c.laddr.port in (8080, 8000, 11434, 5173)]
    assert len(listeners) == 4 and all(c.laddr.ip == '127.0.0.1' for c in listeners)
    assert next(c for c in listeners if c.laddr.port == 5173).pid == 111384
finally:
    session.close()

metadata = root / 'backups/release_versioning/20261024T150106400Z_saved_proposal_history_d0519355'
version_manifest = read(metadata / 'manifest.json')
assert version_manifest['to_version'] == '5.329.48' and len(version_manifest['files']) == 16
for item in version_manifest['files']:
    assert sha(root / item['path']) == item['after_sha256'] and sha(metadata / 'before' / item['path']) == item['before_sha256']

entry = '''## Record 32 - Source48 proposal history discovery

**Implemented:** Existing coding preparation proposals router and projectPreparation client now expose paged, owner-scoped proposal metadata history (`GET /api/chat/coding-tasks/preparations/{request_id}/plans/{plan_id}/proposals`). The client discovers saved proposal IDs on reload, allowing immediate inspect and recovery without re-generating proposals, without executing code, and without modifying underlying database schemas. Escaped diff and proposed candidate hashes are validated with Web Crypto before display; all four panel mirrors match.

**Boundaries/recovery:** Paged metadata discovery enforces preparation owner scoping, immutable parent plan binding, and lexical cursor bounds. Discovered items carry `execution_authorized=false`, `apply_authorized=false`, and `verification_status="not_run"`. Unconfirmed proposal IDs survive lost replies; identical retry never allocates a new ID. Independent cancellation remains available while waiting on generation.

**Tests/errors:** Backend red 38 with 10 missing-feature cases; verified 38/38 green. Client red 70/84, green 84/84. React view red 26/30, green 30/30. Source audit 23/23 pass. Actual live API/client verification through 8000/8080 completed with 16/16 checks passed, validating real retained preparation, plan, review, discovered history items (`5f71b54a2b4f43fdabb792609ec425b7` and `10066c6d7fa04db492ecf7d431e569c3`), terminal recovery, and offline SSR view rendering.

**Runtime/preservation:** Controlled backend restart succeeded into serving PID 368872 / launcher PID 291908 after prior keep-alive socket closed. Gateway 116980, Ollama 165656, and Vite 111384 retained; all four listeners on 127.0.0.1 with 6 activation flags false. All 888 selected documents and personal SQLite databases verified intact. No credentials, raw candidate payloads, or private data exported.

**Checkpoint/next:** Source 5.329.48 / Plan 1.60, backups/proposal_history_5_329_48_20261024T145341207541Z, metadata originals 20261024T150106400Z_saved_proposal_history_d0519355. Shared dirty main HEAD 539dfcbcf165285f9f55ba6ef329a3ae166af2b7. Next bounded task is proposal comparison and preparation/plan/proposal lineage navigation in BS-Chat. Windows VM isolation remains explicitly deferred.
'''

ledger = root / 'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md'
assert '## Record 32 ' not in ledger.read_text(encoding='utf-8')
with ledger.open('a', encoding='utf-8') as out:
    out.write('\n\n' + entry)

handoff = root / 'docs/CODEX_HANDOFF.md'
with handoff.open('a', encoding='utf-8') as out:
    out.write('\n\n## v5.329.48 / plan1.60 - BS-Chat saved proposal history discovery\n\n' + entry.split('\n\n', 1)[1])

plan = root / 'docs/AI_BS_Autonomy_Implementation_Plan.md'
text = plan.read_text(encoding='utf-8')
old = 'Plan revision: 1.59 | Updated: October 24, 2026 | Local application source: v5.329.47'
assert text.count(old) == 1
text = text.replace(old, 'Plan revision: 1.60 | Updated: October 24, 2026 | Local application source: v5.329.48', 1)
text = text.replace('Current source checkpoint v5.329.47 is not a Firebase/Windows release.', 'Current source checkpoint v5.329.48 is not a Firebase/Windows release.', 1)
text = text.replace('Local application source is v5.329.47.', 'Local application source is v5.329.48.', 1)
text += (
    '\n\n**Source48/plan1.60 saved proposal history:** paged owner-scoped proposal metadata discovery '
    '(`GET /api/chat/coding-tasks/preparations/{request_id}/plans/{plan_id}/proposals`) now enables discovery of saved proposal '
    'IDs on reload without inference replay, automatic execution, or apply. 38 backend, 84 client, 30 offline view, 23 source '
    'observations, and 16 actual live API/client checks pass. Controlled reload into serving PID 368872 / launcher PID 291908 '
    'confirmed healthy with loopback listeners and 6 flags false. All 888 selected documents and personal SQLite databases '
    'preserved. Checkpoint: backups/proposal_history_5_329_48_20261024T145341207541Z.\n'
)
plan.write_text(text, encoding='utf-8')

index = root / 'docs/engineering_ledger/cloud_index.json'
data = read(index)
data['pending_sync'] = {
    'record': 32,
    'source_version': '5.329.48',
    'plan_revision': '1.60',
    'reason': 'Proposal history checkpoint pending private same-file byte verification',
}
index.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

spec_dir = root / 'docs/phase5'
spec_dir.mkdir(parents=True, exist_ok=True)
spec = spec_dir / 'PROPOSAL_HISTORY.md'
spec_content = (
    '# Proposal Metadata History Specification\n\n'
    'Implemented and verified at source48/plan1.60: 38 backend, 84 client, 30 offline view, 23 source observations, '
    'and 16 actual live API/client checks. Paged metadata listing enforces owner isolation, parent plan binding, and lexical cursor bounds.\n'
)
spec.write_text(spec_content, encoding='utf-8')

files = [
    'backend/core/coding_preparation_proposals.py',
    'backend/routers/coding_preparation_router.py',
    'frontend/src/utils/projectPreparation.js',
    'docs/CODEX_HANDOFF.md',
    'docs/AI_BS_Autonomy_Implementation_Plan.md',
    'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md',
    'docs/engineering_ledger/cloud_index.json',
    'docs/phase5/PROPOSAL_HISTORY.md',
    'docs/CODEX_JOURNAL.md',
    'docs/CODEX_DECISIONS.md',
    'docs/CODEX_TASKS.md',
]
files += panel_paths
files += [p.relative_to(root).as_posix() for p in (root / 'workspace').glob('*v48*') if p.is_file()]
files += [i['path'] for i in version_manifest['files']]
files = list(dict.fromkeys(files))

(cp / 'after').mkdir(parents=True, exist_ok=True)
for name in files:
    target = cp / 'after' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((root / name).read_bytes())

git = lambda *args: subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe', *args], cwd=root, text=True)
status = git('status', '--porcelain=v1', '-uno')
(cp / 'git_status_final.txt').write_text(status, encoding='utf-8')

record = {
    'source_version': '5.329.48',
    'plan_revision': '1.60',
    'record': 32,
    'at_utc': datetime.now(timezone.utc).isoformat(),
    'git_head': git('rev-parse', 'HEAD').strip(),
    'tracked_changes': len(status.splitlines()),
    'counts': {
        'backend': 38,
        'client': 84,
        'offline_view': 30,
        'source_checks': 23,
        'actual_client': 16,
    },
    'runtime': health,
    'backend_pids': {'serving': runtime['serving_pid'], 'launcher': runtime['pid']},
    'frontend_pid': 111384,
    'files': {n: sha(root / n) for n in files},
    'evidence': {p.name: sha(p) for p in cp.iterdir() if p.is_file()},
    'cloud_sync': 'pending',
    'full_goal_complete': False,
    'new_whole_phase_completion': False,
    'vm': 'explicitly_deferred',
    'next': 'Proposal comparison and preparation/plan/proposal lineage navigation in BS-Chat; VM and release gates remain open.',
}
(cp / 'checkpoint.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')

print(json.dumps({
    'checkpoint': str(cp),
    'source': record['source_version'],
    'plan': record['plan_revision'],
    'files': len(files),
    'handoff_exists': handoff.is_file(),
    'cloud': 'pending',
}))
