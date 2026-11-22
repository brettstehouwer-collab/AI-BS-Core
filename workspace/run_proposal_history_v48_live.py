from pathlib import Path
import json,os,subprocess
from dotenv import dotenv_values
root=Path(r'C:\AI-BS');cp=Path((root/'workspace/proposal_history_v48_checkpoint.txt').read_text(encoding='utf-8').strip())
config=dict(os.environ)
for path in (root/'.env',root/'backend/.env'):
    if path.is_file():config.update({k:v for k,v in dotenv_values(path).items() if v is not None})
environment={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'}}
assert config.get('AI_BS_ADMIN_KEY');environment['AI_BS_ADMIN_KEY']=config['AI_BS_ADMIN_KEY']
result=subprocess.run([r'C:\Program Files\nodejs\node.exe',str(root/'workspace/proposal_history_v48_live.cjs')],cwd=root,env=environment,capture_output=True,text=True,timeout=30)
with (cp/'client_live_runner.json').open('x',encoding='utf-8') as out:json.dump({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},out,indent=2)
print(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}))
raise SystemExit(result.returncode)
