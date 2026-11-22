"""Official local ingress parser/rule checks; no tunnel run or origin requests."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess
OUT=Path(__file__).resolve().parent
EXE=r'C:\Program Files (x86)\cloudflared\cloudflared.exe'
manifest=json.loads((OUT/'manifest.json').read_text())
results=[]
for label in ('scoped','user'):
 row=manifest['files'][label];candidate=OUT/row['candidate_file']
 assert hashlib.sha256(candidate.read_bytes()).hexdigest()==row['candidate_sha256']
 commands=[('validate',[EXE,'tunnel','--config',str(candidate),'ingress','validate'])]
 commands += [(name,[EXE,'tunnel','--config',str(candidate),'ingress','rule',url]) for name,url in [('publishing_rule','https://stehouwer-publishing.com/'),('api_sse_rule','https://api.brettstehouwer.live/sse')]]
 for name,command in commands:
  response=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
  text=response.stdout+'\n'+response.stderr
  sanitized=[]
  for line in text.splitlines():
   if re.search(r'(?i)(?:token|secret|password|authorization|private key)\s*(?:[:=]|\S)',line):sanitized.append('[sensitive matching line omitted]')
   else:sanitized.append(line[:1000])
  log=OUT/f'{label}_{name}.log'
  with log.open('x',encoding='utf-8') as stream:stream.write('\n'.join(sanitized)[:16384])
  result={'config':label,'check':name,'exit_code':response.returncode,'log':log.name,'output_bytes':len(text.encode()),'local_parser_only':True}
  if name=='publishing_rule':result['expected_service_reported']='http://127.0.0.1:80' in text
  if name=='api_sse_rule':result['expected_service_reported']='http_status:404' in text
  results.append(result)
  if response.returncode!=0:break
report={'actor':'/root/publishing_origin','utc':datetime.now(timezone.utc).isoformat(),'results':results,'status':'passed' if len(results)==6 and all(r['exit_code']==0 and r.get('expected_service_reported',True) for r in results) else 'failed','live_changes':False,'tunnel_run_invoked':False}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
assert report['status']=='passed'
