from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,os,sqlite3

root=Path(r'C:\AI-BS');cp=Path((root/'workspace/proposal_ui_v47_checkpoint.txt').read_text(encoding='utf-8').strip())
before=json.loads((cp/'before_manifest.json').read_text(encoding='utf-8'))
panel='frontend/src/components/CodingPreparationPanel.jsx';panels=[base+'/CodingPreparationPanel.jsx' for base in ['frontend/src/components','frontend/components','frontend/src/components/components','frontend/components/components']]
assert len({before[n] for n in panels})==1
for name in panels[1:]:
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==before[name]
    (root/name).write_bytes((root/panel).read_bytes())
checks=[]
def check(name,passed):checks.append({'name':name,'passed':bool(passed)});assert passed,name
check('Four explicitly backed-up panel mirrors match',len({(root/n).read_bytes() for n in panels})==1)
prior=root/'backups/retained_proposal_5_329_46_20261024T141425139154Z'
runtime=json.loads((prior/'runtime/process.json').read_text(encoding='utf-8'))
for name,value in runtime['source_hashes'].items():check('Loaded backend source unchanged '+name,hashlib.sha256((root/name).read_bytes()).hexdigest()==value)
text=(root/panel).read_text(encoding='utf-8')
check('No HTML/Markdown/tool-action rendering introduced',all(value not in text for value in ['dangerouslySetInnerHTML','ReactMarkdown','tool_call','Run in Host IDE']))
check('No executor or apply route in the proposal client',all(value not in (root/'frontend/src/utils/projectPreparation.js').read_text(encoding='utf-8') for value in ['/executive/','/execute','/apply']))
check('No source/form/chat host mirror sweeps',len(panels)==4)
for path in [root/panel,root/'frontend/src/utils/projectPreparation.js']:
    data=path.read_text(encoding='utf-8')
    check('No credential/private-key patterns in changed source '+path.name,all(token not in data for token in ['BEGIN PRIVATE KEY','ghp_','sk-aibs','AIzaSy','sk_aibs_dev_']))
with (cp/'source_audit.json').open('x',encoding='utf-8') as out:json.dump(checks,out,indent=2)
# Reuse only the prior verified, read-only preservation helpers, never its launcher.
source=root/'workspace/proposal_v46_restore.py';tree=ast.parse(source.read_text(encoding='utf-8'))
names={'now','sha','read_json','exclusive_json','no_link_path','verify_documents','ro_database','verify_personal'}
chosen=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in chosen}==names
scope={'Path':Path,'datetime':datetime,'timezone':timezone,'hashlib':hashlib,'json':json,'os':os,'sqlite3':sqlite3,'ROOT':root,
       'runtime':cp,'PRIOR':root/'backups/production_readiness_5_329_33_20261024T054356815Z',
       'PERSONAL_TABLES':('user_profiles','memory_facts','episodic_logs','knowledge_graph_triplets')}
exec(compile(ast.Module(body=chosen,type_ignores=[]),str(source)+'::read_only_helpers','exec'),scope)
documents=scope['verify_documents']('final')
personal=scope['verify_personal'](scope['read_json'](prior/'runtime/personal_backup.json'))
print(json.dumps({'source_checks':len(checks),'all_source_checks_passed':all(c['passed'] for c in checks),
                  'documents':documents['status'],'personal':personal['status']}))
