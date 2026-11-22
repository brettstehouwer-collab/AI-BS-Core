from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,os,sqlite3

root=Path(r'C:\AI-BS');cp=root/'backups/retained_proposal_5_329_46_20261024T141425139154Z'
script=root/'workspace/proposal_v46_restore.py'
tree=ast.parse(script.read_text(encoding='utf-8'))
names={'now','sha','read_json','exclusive_json','no_link_path','verify_documents','ro_database','verify_personal'}
chosen=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
assert {n.name for n in chosen}==names
scope={'Path':Path,'datetime':datetime,'timezone':timezone,'hashlib':hashlib,'json':json,'os':os,'sqlite3':sqlite3,
       'ROOT':root,'CP':cp,'PRIOR':root/'backups/production_readiness_5_329_33_20261024T054356815Z',
       'runtime':cp/'runtime','PERSONAL_TABLES':('user_profiles','memory_facts','episodic_logs','knowledge_graph_triplets')}
exec(compile(ast.Module(body=chosen,type_ignores=[]),str(script)+'::read_only_helpers','exec'),scope)
docs=scope['verify_documents']('after_continuation')
personal=scope['verify_personal'](scope['read_json'](cp/'runtime/personal_backup.json'))
destination=cp/'preservation_after_live.json'
assert not destination.exists()
helper=Path(r'C:\Users\footb\Documents\Codex\2026-10-22\c-ai-bs\work\verify_production_preservation_5_329_34.py').read_text(encoding='utf-8')
assert helper.count("cp / 'preservation_after_start.json'")==1
helper=helper.replace("cp / 'preservation_after_start.json'",'destination')
exec(compile(helper,'<read_only_authority_preservation>','exec'),{'destination':destination})
print(json.dumps({'documents':docs,'personal':personal}))
