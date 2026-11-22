from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess
import psutil, requests
from dotenv import dotenv_values

root = Path(r'C:\AI-BS')
cp = root / 'backups/proposal_history_5_329_48_20261024T145341207541Z'
out = Path((root / 'workspace/proposal_history_v48_resume.txt').read_text(encoding='utf-8'))
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))
record = read(out / 'runtime_restoration_checked_console.json')
assert record['status'] == 'inspection_needed' and record['reason'] == 'Actual access enforcement 8000'
config = dict(os.environ)
for p in (root / '.env', root / 'backend/.env'):
    if p.is_file(): config.update({k:v for k,v in dotenv_values(p).items() if v is not None})
checks = []
flags = ['AI_BS_RECDEBUT_OUTBOUND_ENABLED','AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED','AI_BS_DISCORD_NOTIFICATIONS_ENABLED','AI_BS_BACKEND_MANAGE_DAEMONS','AI_BS_BACKEND_BACKGROUND_ENABLED','AI_BS_ALLOW_DESTRUCTIVE_ACTIONS']
with requests.Session() as s:
    s.trust_env = False
    for name,item in record['processes'].items():
        original=item['serving']; process=psutil.Process(original['pid'])
        assert process.create_time()==original['created'] and process.exe()==original['exe'] and process.cmdline()==original['argv']
        assert all(process.environ().get(f)=='false' for f in flags)
        checks.append({'name':name+' exact current identity and six false flags','passed':True,'pid':process.pid})
    sockets=[c for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port in (8080,8000,5173,11434,11435)]
    assert len(sockets)==4 and all(c.laddr.ip=='127.0.0.1' for c in sockets)
    for port,denied in [(8080,403),(8000,401)]:
        url=f'http://127.0.0.1:{port}/api/chat/coding-tasks/preparations/identity'
        for mode,headers,status in [('anonymous',{},denied),('invalid',{'X-Admin-Key':'intentionally-invalid-check'},denied),('administrator',{'X-Admin-Key':config['AI_BS_ADMIN_KEY']},200)]:
            response=s.get(url,headers=headers,timeout=5,allow_redirects=False)
            assert response.status_code==status
            if status==200:assert response.json()['owner']=='local_admin' and response.json()['execution_authorized'] is False
            checks.append({'name':f'{port} {mode}','passed':True,'status':status})
    daemons=s.get('http://127.0.0.1:8000/api/daemons/status',headers={'X-Admin-Key':config['AI_BS_ADMIN_KEY']},timeout=5).json()
    assert len(daemons)==11 and all(d['state']=='stopped' and d['running'] is False and d['pid']==-1 for d in daemons.values())
    assert read(out/'preservation_after_restore/documents_databases.json')['status']==read(out/'preservation_after_restore/personal_preservation_after.json')['status']=='verified'
with (out/'runtime_verified.json').open('x',encoding='utf-8') as f:
    json.dump({'status':'healthy_protected','at_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,
               'processes':record['processes'],'four_loopback_only':True,'six_flags_false':True,
               'unrelated_daemons_stopped':11,'restart_repeated':False,'frontend_http_requested':False},f,indent=2)

text=(root/'workspace/proposal_history_v48_live.cjs').read_text(encoding='utf-8')
line="const cp=fs.readFileSync(__dirname+'/proposal_history_v48_checkpoint.txt','utf8').trim();"
assert text.count(line)==1
text=text.replace(line,'const cp='+json.dumps(out.as_posix())+';',1)
assert hashlib.sha256((cp/'view_green.cjs').read_bytes()).hexdigest()==read(cp/'pause_checkpoint.json')['evidence']['view_green.cjs']
(out/'view_green.cjs').write_bytes((cp/'view_green.cjs').read_bytes())
script=out/'client_post_restore.cjs'
with script.open('x',encoding='utf-8') as f:f.write(text)
env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'}}
env['AI_BS_ADMIN_KEY']=config['AI_BS_ADMIN_KEY']
result=subprocess.run([r'C:\Program Files\nodejs\node.exe',str(script)],cwd=root,env=env,capture_output=True,text=True,timeout=35)
with (out/'client_post_restore_runner.json').open('x',encoding='utf-8') as f:json.dump({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},f,indent=2)
assert result.returncode==0, 'Read-only client acceptance failed; inspect retained evidence'
print(json.dumps({'runtime':'verified','current_client_checks':read(out/'client_live.json')['count'],'output':str(out)}))
