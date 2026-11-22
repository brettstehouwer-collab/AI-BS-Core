"""Stage tiny private before/candidate copies; never modifies live files/processes."""
from pathlib import Path
from datetime import datetime,timezone
import ast,copy,hashlib,json,re,shutil
import psutil,yaml

OUT=Path(__file__).resolve().parent
ROOT=Path(r'C:\AI-BS')
FILES={
 'user':Path.home()/'.cloudflared/config.yml',
 'scoped':ROOT/'saved_data/core_runtime/api-tunnel-scoped.yml',
 'boot':ROOT/'scripts/core_boot.py',
}
EXPECTED={
 'user':'305cd3471bd06bac31b7614defc0b851ebb5f40cc16af9b8077fa87241d39a68',
 'scoped':'edac3b13da88af2de58e9706f17d4fdded96ce1d20282d896b77b60c9a58824e',
 'boot':'c8ddaeb76b7379e8d20c84a540c4c9894e77ff7e5cd767f2739bb54c24040b24',
}
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not (OUT/'manifest.json').exists(),'Retain prior preparation; inspect before repeating'
disk=shutil.disk_usage(ROOT)
assert disk.free>8*1024*1024,'Insufficient room even for tiny evidence'
raw={k:p.read_bytes() for k,p in FILES.items()}
for k,b in raw.items():
 assert len(b)<16384 and sha(b)==EXPECTED[k],f'Live {k} changed; re-review'
 if k!='boot':assert not re.search(rb'(?im)^\s*(?:token|password|secret|api[_-]?key)\s*:',b),'Do not copy credential values'
newline=b'\r\n' if b'\r\n' in raw['scoped'] else b'\n'
needle=b'  - service: http_status:404'
assert raw['scoped'].count(needle)==1
addition=newline.join([b'  - hostname: stehouwer-publishing.com',b'    service: http://127.0.0.1:80',b'  - hostname: www.stehouwer-publishing.com',b'    service: http://127.0.0.1:80'])+newline
candidate={'scoped':raw['scoped'].replace(needle,addition+needle)}
assert raw['user'].count(b'service: http://127.0.0.1:8099')==2
candidate['user']=raw['user'].replace(b'service: http://127.0.0.1:8099',b'service: http_status:404')
candidate['boot'],count=re.subn(rb"(?m)^CONFIG_SHA='[a-f0-9]{64}'",("CONFIG_SHA='"+sha(candidate['scoped'])+"'").encode(),raw['boot'])
assert count==1
old_s,new_s,old_u,new_u=[yaml.safe_load(b) for b in (raw['scoped'],candidate['scoped'],raw['user'],candidate['user'])]
assert old_s['tunnel']==new_s['tunnel']==old_u['tunnel']==new_u['tunnel']
assert all(a.get('credentials-file')==b.get('credentials-file') for a,b in ((old_s,new_s),(old_u,new_u)))
assert len(new_s['ingress'])==len(old_s['ingress'])+2
assert len(old_u['ingress'])==len(new_u['ingress'])
changed=[]
for i,(a,b) in enumerate(zip(old_u['ingress'],new_u['ingress'])):
 if a!=b:
  assert a['hostname']=='api.brettstehouwer.live' and a.get('path') in ('/sse','/messages')
  expected=copy.deepcopy(a);expected['service']='http_status:404';assert expected==b;changed.append(i)
assert len(changed)==2
tree_before,tree_after=[ast.parse(b.decode('utf-8-sig')) for b in (raw['boot'],candidate['boot'])]
def remove_pin(tree):
 tree.body=[n for n in tree.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONFIG_SHA' for t in n.targets))]
 return ast.dump(tree,include_attributes=False)
assert remove_pin(tree_before)==remove_pin(tree_after)
def route(cfg,host,path):
 for rule in cfg['ingress']:
  if rule.get('hostname') and rule['hostname']!=host:continue
  if rule.get('path') and not re.search(rule['path'],path):continue
  return rule['service']
checks=[]
for host,path,expected in [('api.brettstehouwer.live','/sse','http_status:404'),('api.brettstehouwer.live','/messages','http_status:404'),('api.brettstehouwer.live','/health','http://127.0.0.1:8000'),('stehouwer-publishing.com','/','http://127.0.0.1:80'),('www.stehouwer-publishing.com','/','http://127.0.0.1:80')]:
 for label,cfg in [('scoped',new_s),('user',new_u)]:
  assert route(cfg,host,path)==expected
  checks.append(dict(config=label,host=host,path=path,expected=expected,passed=True))
rows={}
for label,path in FILES.items():
 suffix='.py' if label=='boot' else '.yml'
 before_name=f'{label}.before{suffix}';candidate_name=f'{label}.candidate{suffix}'
 for name,data in ((before_name,raw[label]),(candidate_name,candidate[label])):
  with (OUT/name).open('xb') as stream:stream.write(data)
 rows[label]=dict(live_path=str(path),before_file=before_name,candidate_file=candidate_name,before_sha256=sha(raw[label]),candidate_sha256=sha(candidate[label]),before_bytes=len(raw[label]),candidate_bytes=len(candidate[label]))
processes={}
for pid in (16512,34912,6252):
 p=psutil.Process(pid)
 args=p.cmdline()
 processes[str(pid)]={'created':p.create_time(),'executable':p.exe(),'owner':p.username(),'argv_sha256':sha(json.dumps(args,separators=(',',':')).encode()),'token_parameter_present':any(a=='--token' or a.startswith('--token=') for a in args),'raw_arguments_not_retained':True}
report=dict(actor='/root/publishing_origin',utc=datetime.now(timezone.utc).isoformat(),status='staged_only',live_files_changed=False,processes_changed=False,credentials_files_opened=False,credential_references_preserved=True,core_boot_only_pin_changed=True,user_unrelated_rules_unchanged=True,files=rows,route_assertions=checks,processes=processes,system_service_must_remain_untouched=True,disk={'free_bytes':disk.free,'total_bytes':disk.total,'free_percent':round(100*disk.free/disk.total,2),'small_output_only':True})
(OUT/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':'staged_only','live_changes':0,'candidate_files':3,'before_copies':3,'route_assertions':len(checks),'core_boot_ast_only_pin_changed':True,'evidence_bytes':sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())},indent=2))
