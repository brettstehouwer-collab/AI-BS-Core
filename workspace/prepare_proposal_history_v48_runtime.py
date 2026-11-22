from pathlib import Path
import ast,hashlib,json
root=Path(r'C:\AI-BS');cp=Path((root/'workspace/proposal_history_v48_checkpoint.txt').read_text(encoding='utf-8').strip())
before=json.loads((cp/'before_manifest.json').read_text(encoding='utf-8'));checks=[]
def check(name,passed):checks.append({'name':name,'passed':bool(passed)});assert passed,name
for name in ['backend/core/coding_preparation_proposals.py','backend/routers/coding_preparation_router.py']:
    old=ast.parse((cp/'before'/name).read_text(encoding='utf-8'));new=ast.parse((root/name).read_text(encoding='utf-8'))
    existing={n.name:ast.dump(n) for n in new.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    check('All existing action/auth functions unchanged '+name,all(existing[n.name]==ast.dump(n) for n in old.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))))
for name in ['backend/core/coding_preparation_proposals.py','backend/routers/coding_preparation_router.py','backend/tests/test_proposal_history.py']:
    ast.parse((root/name).read_text(encoding='utf-8'));check('Syntax '+name,True)
panels=[base+'/CodingPreparationPanel.jsx' for base in ['frontend/src/components','frontend/components','frontend/src/components/components','frontend/components/components']]
check('Original four mirrors exact',len({before[n] for n in panels})==1)
for name in panels[1:]:
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==before[name]
    (root/name).write_bytes((root/panels[0]).read_bytes())
check('Updated four mirrors exact',len({(root/n).read_bytes() for n in panels})==1)
prior=root/'backups/retained_proposal_5_329_46_20261024T141425139154Z';old=json.loads((prior/'runtime/process.json').read_text(encoding='utf-8'))
for name,value in old['source_hashes'].items():
    if name not in ['backend/core/coding_preparation_proposals.py','backend/routers/coding_preparation_router.py']:
        check('Other loaded source unchanged '+name,hashlib.sha256((root/name).read_bytes()).hexdigest()==value)
with (cp/'source_audit.json').open('x',encoding='utf-8') as out:json.dump({'passed':sum(c['passed'] for c in checks),'count':len(checks),'checks':checks},out,indent=2)
backend=old['processes']['backend'];old_flat={'serving_pid':backend['serving']['pid'],'serving_created':backend['serving']['created'],'serving_exe':backend['serving']['exe'],
    'pid':backend['launcher']['pid'],'created':backend['launcher']['created'],'argv':backend['argv']}
old_path=cp/'source46_runtime_for_identity.json';old_path.write_text(json.dumps(old_flat,indent=2),encoding='utf-8')
work=Path(r'C:\Users\footb\Documents\Codex\2026-10-22\c-ai-bs\work')
source=(work/'restart_planning_controls_v45.py').read_text(encoding='utf-8')
source=source.replace("cp = Path((Path(__file__).parent / 'planning_controls_v45_checkpoint.txt').read_text(encoding='utf-8'))", "cp = Path((Path(__file__).parent / 'proposal_history_v48_checkpoint.txt').read_text(encoding='utf-8').strip())")
source=source.replace("audit['count'] == 13", "audit['count'] == "+str(len(checks)))
source=source.replace("root / 'backups/preparation_ui_5_329_43_20261024T115233251733Z/runtime/process.json'", "cp / 'source46_runtime_for_identity.json'")
source=source.replace("'5.329.45'","'5.329.48'")
source=source.replace("'backend/core/coding_preparation_planning.py',", "'backend/core/coding_preparation_proposals.py', 'backend/core/coding_preparation_planning.py',")
source=source.replace("runtime = cp / 'runtime'", "assert json.loads((cp / 'verified.json').read_text(encoding='utf-8'))['passed']\nassert json.loads((cp / 'client_green.json').read_text(encoding='utf-8'))['passed'] == 84\nassert json.loads((cp / 'view_green.json').read_text(encoding='utf-8'))['passed'] == 30\nruntime = cp / 'runtime'")
with (root/'workspace/restart_proposal_history_v48.py').open('x',encoding='utf-8') as out:out.write(source)
helper=(work/'verify_production_preservation_5_329_34.py').read_text(encoding='utf-8')
destination=cp/'preservation_before_restart.json';assert not destination.exists()
assert helper.count("cp / 'preservation_after_start.json'")==1
helper=helper.replace("cp / 'preservation_after_start.json'",'destination')
exec(compile(helper,'<read_only_selected_authority_preservation>','exec'),{'destination':destination})
