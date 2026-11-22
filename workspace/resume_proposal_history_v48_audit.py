"""Finish source48 observations without replaying generation, execution or restarts."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import json
import os
import sqlite3
import subprocess
import psutil
import requests

ROOT = Path(r'C:\AI-BS')
CP = ROOT / 'backups/proposal_history_5_329_48_20261024T145341207541Z'
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = CP / ('resume_' + stamp)
OUT.mkdir()
(ROOT / 'workspace/proposal_history_v48_resume.txt').write_text(str(OUT), encoding='utf-8')

def write(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

paused = read(CP / 'pause_checkpoint.json')
memory = ('docs/CODEX_HANDOFF.md', 'docs/CODEX_JOURNAL.md', 'docs/CODEX_DECISIONS.md',
          'docs/CODEX_TASKS.md', 'docs/AI_BS_Autonomy_Implementation_Plan.md',
          'docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md',
          'docs/engineering_ledger/cloud_index.json')
before = {}
for name in (*memory, 'AGENTS.md'):
    target = OUT / 'before' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = (ROOT / name).read_bytes()
    target.write_bytes(raw)
    before[name] = hashlib.sha256(raw).hexdigest()
for name in ('checkpoint.json', 'completion.json', 'pause_checkpoint.json'):
    (OUT / ('previous_' + name)).write_bytes((CP / name).read_bytes())
write('before_manifest.json', before)

checks = []
def check(name, valid, **details):
    checks.append({'name': name, 'passed': bool(valid), **details})
    assert valid, name

try:
    stable = {n: h for n, h in paused['files'].items() if n not in memory}
    check('Paused source and metadata unchanged', all(sha(ROOT / n) == h for n, h in stable.items()), files=len(stable))
    check('Paused evidence unchanged', all(sha(CP / n) == h for n, h in paused['evidence'].items()), files=len(paused['evidence']))
    runtime = read(CP / 'runtime_after_connection_closed/process.json')
    check('Retained loaded backend hashes still exact', all(sha(ROOT / n) == h for n, h in runtime['source_hashes'].items()))
    server = psutil.Process(runtime['serving_pid'])
    check('Same backend identity', server.create_time() == runtime['serving_created'] and server.exe() == runtime['serving_exe'])
    launcher = psutil.Process(runtime['pid'])
    check('Same backend launcher identity', launcher.create_time() == runtime['created'])
    services = []
    with requests.Session() as session:
        session.trust_env = False
        for port, process in [(8080, server)] + [(r['port'], psutil.Process(r['pid'])) for r in runtime['other_listeners_after']]:
            if port != 8080:
                expected = next(r for r in runtime['other_listeners_after'] if r['port'] == port)
                check('Same service identity ' + str(port), process.create_time() == expected['created'])
            if port in (8080, 8000, 11434):
                flags = {k: process.environ().get(k) for k in runtime['controlled_flags']}
                check('Six activation flags false ' + str(port), all(v == 'false' for v in flags.values()))
                response = session.get(f'http://127.0.0.1:{port}' + ('/api/version' if port == 11434 else '/health'), timeout=8, allow_redirects=False)
                check('Health ' + str(port), response.status_code == 200)
            services.append({'port': port, 'pid': process.pid, 'created': process.create_time(), 'exe': process.exe()})
        sockets = [c for c in psutil.net_connections(kind='tcp') if c.status == 'LISTEN' and c.laddr.port in (8080, 8000, 11434, 11435, 5173)]
        check('Exactly four loopback listeners; no11435', len(sockets) == 4 and all(c.laddr.ip == '127.0.0.1' for c in sockets) and {c.laddr.port for c in sockets} == {8080, 8000, 11434, 5173})
        tags = session.get('http://127.0.0.1:11434/api/tags', timeout=8, allow_redirects=False).json()['models']
        model = next(m for m in tags if m['name'] == 'stehouwer_llm:latest')
        check('Existing customized model digest unchanged', model['digest'] == '5213ff76656a20b564e1001cc3cc4e9e9b7f8cc80dd837cde54b341127e60b12')
    write('runtime_observation.json', {'at_utc': datetime.now(timezone.utc).isoformat(), 'services': services, 'same_processes': True, 'restart_performed': False, 'model_digest_exact': True, 'checks': checks})

    tree = ast.parse((ROOT / 'workspace/proposal_v46_restore.py').read_text(encoding='utf-8'))
    names = {'now', 'sha', 'read_json', 'exclusive_json', 'no_link_path', 'ro_database', 'verify_personal'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == names
    scope = {'Path': Path, 'datetime': datetime, 'timezone': timezone, 'hashlib': hashlib, 'json': json,
             'os': os, 'sqlite3': sqlite3, 'ROOT': ROOT, 'runtime': OUT,
             'PERSONAL_TABLES': ('user_profiles', 'memory_facts', 'episodic_logs', 'knowledge_graph_triplets')}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<retained_read_only_personal_helpers>', 'exec'), scope)
    personal = scope['verify_personal'](read(ROOT / 'backups/retained_proposal_5_329_46_20261024T141425139154Z/runtime/personal_backup.json'))
    check('Personal schema and every retained row exact', personal['status'] == 'verified')

    helper_path = Path(r'C:\Users\footb\Documents\Codex\2026-10-22\c-ai-bs\work\verify_production_preservation_5_329_34.py')
    helper = helper_path.read_text(encoding='utf-8')
    assert helper.count("cp / 'preservation_after_start.json'") == 1
    helper = helper.replace("cp / 'preservation_after_start.json'", 'destination')
    try:
        exec(compile(helper, '<retained_read_only_document_database_helpers>', 'exec'), {'destination': OUT / 'documents_databases_after_resume.json'})
    except SystemExit as result:
        assert result.code == 0
    documents = read(OUT / 'documents_databases_after_resume.json')
    check('Selected documents and copies preserved', documents['status'] == 'verified' and sum(d['files'] for d in documents['documents']) == 888)
    write('resume_audit.json', {'status': 'verified', 'observed_at_utc': datetime.now(timezone.utc).isoformat(),
          'checks': checks, 'source_version': '5.329.48', 'old_finalizer_replayed': False,
          'full_goal_complete': False, 'vm': 'explicitly_deferred', 'cloud': 'pending'})
    print(json.dumps({'status': 'verified', 'checkpoint': str(OUT), 'checks': len(checks), 'documents': 888, 'personal': personal['tables']}))
except BaseException as error:
    write('resume_failure.json', {'type': type(error).__name__, 'error': str(error) if isinstance(error, AssertionError) else 'Inspect local evidence', 'checks': checks})
    raise
