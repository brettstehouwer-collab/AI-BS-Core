from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json, os, sqlite3, sys

root = Path(r'C:\AI-BS')
parent = Path((root / 'workspace/proposal_history_v48_resume.txt').read_text(encoding='utf-8'))
phase = sys.argv[1] if len(sys.argv) == 2 else 'preservation'
assert phase in ('preservation', 'preservation_after_restore')
out = parent / phase
out.mkdir()
tree = ast.parse((root / 'workspace/proposal_v46_restore.py').read_text(encoding='utf-8'))
names = {'now', 'sha', 'read_json', 'exclusive_json', 'no_link_path', 'ro_database', 'verify_personal'}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
assert {n.name for n in nodes} == names
scope = {'Path': Path, 'datetime': datetime, 'timezone': timezone, 'hashlib': hashlib, 'json': json,
         'os': os, 'sqlite3': sqlite3, 'ROOT': root, 'runtime': out,
         'PERSONAL_TABLES': ('user_profiles', 'memory_facts', 'episodic_logs', 'knowledge_graph_triplets')}
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<read_only_personal_checks>', 'exec'), scope)
saved = json.loads((root / 'backups/retained_proposal_5_329_46_20261024T141425139154Z/runtime/personal_backup.json').read_text(encoding='utf-8'))
personal = scope['verify_personal'](saved)
helper = Path(r'C:\Users\footb\Documents\Codex\2026-10-22\c-ai-bs\work\verify_production_preservation_5_329_34.py').read_text(encoding='utf-8')
assert helper.count("cp / 'preservation_after_start.json'") == 1
helper = helper.replace("cp / 'preservation_after_start.json'", 'destination')
try:
    exec(compile(helper, '<read_only_document_database_checks>', 'exec'), {'destination': out / 'documents_databases.json'})
except SystemExit as result:
    assert result.code == 0
print(json.dumps({'status': personal['status'], 'personal_tables': personal['tables'], 'output': str(out)}))
