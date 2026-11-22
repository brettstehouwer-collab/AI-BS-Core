from pathlib import Path
import ast, hashlib, json
root = Path('C:/AI-BS')
cp = Path((root/'workspace/proposal_v46_checkpoint.txt').read_text(encoding='utf-8'))
manifest = json.loads((cp/'before_manifest.json').read_text(encoding='utf-8'))
checks = []
def check(name, passed):
    checks.append({'name':name,'passed':bool(passed)})
    assert passed, name
router = 'backend/routers/coding_preparation_router.py'
old = ast.parse((cp/'before'/router).read_text(encoding='utf-8-sig'))
new = ast.parse((root/router).read_text(encoding='utf-8-sig'))
current = {n.name:ast.dump(n) for n in new.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
check('Every existing preparation/planning route body and auth dependency preserved',
      all(current.get(n.name)==ast.dump(n) for n in old.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))))
for name in ['backend/core/coding_preparation_proposals.py','backend/tests/test_preparation_proposals.py',
             'workspace/proposal_v46_restore.py']:
    ast.parse((root/name).read_text(encoding='utf-8-sig'))
    check('Python source parses: '+name,True)
for name, digest in manifest.items():
    if name.startswith(('backend/core/','frontend/')):
        check('Existing application source unchanged: '+name,hashlib.sha256((root/name).read_bytes()).hexdigest()==digest)
source = (root/'backend/core/coding_preparation_proposals.py').read_text(encoding='utf-8')
tree = ast.parse(source)
imports = [n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
check('Proposal module has no subprocess/exec/eval/tool execution entry',
      not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'exec','eval','compile','__import__'} for n in ast.walk(tree))
      and 'subprocess' not in ast.dump(ast.Module(body=imports,type_ignores=[])))
(cp/'source_audit.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(checks),'passed':all(c['passed'] for c in checks)}))
