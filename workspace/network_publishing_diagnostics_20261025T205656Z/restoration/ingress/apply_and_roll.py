"""Root-authorized, identity-bound rolling ingress repair; no household changes."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,tempfile,time,shutil
import httpx,psutil

OUT=Path(__file__).resolve().parent
ORIGIN=OUT.parent/'origin_receipt.json'
MANIFEST=json.loads((OUT/'manifest.json').read_text())
FLAGS=('AI_BS_RECDEBUT_OUTBOUND_ENABLED','AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED','AI_BS_DISCORD_NOTIFICATIONS_ENABLED','AI_BS_BACKEND_MANAGE_DAEMONS','AI_BS_BACKEND_BACKGROUND_ENABLED','AI_BS_ALLOW_DESTRUCTIVE_ACTIONS')
TASK='AI-BS-Publishing-Cloudflare-Tunnel'
sha=lambda b:hashlib.sha256(b).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
events=[]
state={'actor':'/root/publishing_origin','authorization':'Direct user site restoration; root origin-ready GO','started_utc':now(),'status':'admitting','live_sources_applied':False,'user_task_replaced':False,'api_connector_replaced':False,'system_service_untouched':True,'network_configuration_untouched':True,'credentials_or_environment_logged':False,'windows_termination':'Scoped API terminate is an interruption after zero concurrent-request gauge; redundant user connector remains healthy'}
def save(event,**fields):
 row={'utc':now(),'event':event,**fields};events.append(row)
 with (OUT/'activation_events.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
 state['events']=events
 (OUT/'activation_receipt.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
 print(json.dumps(row),flush=True)
def identity(pid,expected):
 p=psutil.Process(pid)
 assert p.create_time()==expected['created'],'Process creation changed'
 assert os.path.normcase(p.exe())==os.path.normcase(expected['executable']),'Executable changed'
 assert p.username().casefold()==expected['owner'].casefold(),'Owner changed'
 assert sha(json.dumps(p.cmdline(),separators=(',',':')).encode())==expected['argv_sha256'],'Arguments changed'
 return p
def snapshot():
 ports={80,8000,8080,5173,11434,8189,8888,20241}
 rows=[]
 for c in psutil.net_connections(kind='tcp'):
  if c.status=='LISTEN' and c.laddr.port in ports:
   p=psutil.Process(c.pid);rows.append({'port':c.laddr.port,'ip':c.laddr.ip,'pid':c.pid,'created':p.create_time()})
 assert not any(r['port']==8888 for r in rows),'Unexpected Unreal listener'
 assert all(r['ip'] in ('127.0.0.1','::1') for r in rows),'Non-loopback peer listener'
 api=next(r for r in rows if r['port']==8080)
 env=psutil.Process(api['pid']).environ()
 assert all(env.get(k)=='false' for k in FLAGS),'Activation flags changed'
 return sorted(rows,key=lambda r:(r['port'],r['ip'],r['pid']))
def validate_origin():
 r=json.loads(ORIGIN.read_text());startup=json.loads((OUT.parent/'origin_startup_receipt.json').read_text())
 assert startup['phase']=='task_managed_origin_healthy' and startup['local_root_hash_match'],'Latest origin not ready'
 p=psutil.Process(startup['new_master_pid'])
 assert p.create_time()==startup['new_master_created'],'Origin master changed'
 assert os.path.normcase(p.exe())==os.path.normcase(r['exe']),'Origin executable changed'
 assert sha(Path(r['config']).read_bytes())==r['config_sha256'],'Origin config changed'
 actual=[(c.laddr.ip,c.pid) for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==80]
 expected=[(x['ip'],x['pid']) for x in startup['listener_bindings']]
 assert sorted(actual)==sorted(expected),'Origin listener identity changed'
 for _,pid in actual:assert psutil.Process(pid).ppid()==p.pid,'Origin worker ancestry changed'
 assert all(x.get('hash_match',True) for x in r['local_checks']),'Origin content check failed'
def metrics(pid,port):
 entries=[c for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==port]
 assert len(entries)==1 and entries[0].pid==pid and entries[0].laddr.ip=='127.0.0.1','Metrics ownership changed'
 with httpx.Client(trust_env=False,follow_redirects=False,timeout=4) as client:
  response=client.get(f'http://127.0.0.1:{port}/metrics')
 assert response.status_code==200 and len(response.content)<131072,'Metrics unavailable'
 wanted={'cloudflared_tunnel_ha_connections','cloudflared_tunnel_concurrent_requests_per_tunnel'};result={}
 for line in response.text.splitlines():
  if line.startswith('#'):continue
  key=line.split('{',1)[0].split(' ',1)[0]
  if key in wanted:result[key]=result.get(key,0.0)+float(line.rsplit(' ',1)[-1])
 assert wanted<=set(result),'Required readiness/concurrency gauge missing'
 return result
def wait_idle(pid,port):
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  m=metrics(pid,port)
  if m['cloudflared_tunnel_ha_connections']>=1 and m['cloudflared_tunnel_concurrent_requests_per_tunnel']==0:return m
  time.sleep(.5)
 raise RuntimeError('Concurrent requests did not drain; process preserved')
def wait_ready(pid,created,port):
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  p=psutil.Process(pid);assert p.create_time()==created,'New process identity changed'
  try:
   m=metrics(pid,port)
   if m['cloudflared_tunnel_ha_connections']>=4:return m
  except (AssertionError,httpx.HTTPError,ValueError):pass
  time.sleep(.5)
 raise RuntimeError('New connector did not establish four edge connections')
def health(label):
 with httpx.Client(trust_env=False,follow_redirects=False,timeout=8) as client:
  rows=[]
  for url in ('http://127.0.0.1:8000/health','https://api.brettstehouwer.live/health'):
   response=client.get(url)
   assert response.status_code==200 and response.json().get('status')=='online','API health lost'
   rows.append({'target':url,'status':response.status_code})
 save('api_health_'+label,checks=rows)
def atomic(path,data):
 handle=tempfile.NamedTemporaryFile(prefix=path.name+'.publishing-restoration-',suffix='.tmp',dir=path.parent,delete=False)
 try:
  handle.write(data);handle.flush();os.fsync(handle.fileno())
 finally:handle.close()
 os.replace(handle.name,path)
 assert path.read_bytes()==data
def task_action(action):
 assert action in ('Stop','Start')
 response=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',f"$ErrorActionPreference='Stop'; {action}-ScheduledTask -TaskName '{TASK}' -ErrorAction Stop"],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
 assert response.returncode==0,action+' scheduled task failed; raw output not retained'
def user_process(exclude):
 expected=MANIFEST['processes']['16512'];target=os.path.normcase(MANIFEST['files']['user']['live_path'])
 for _ in range(40):
  found=[]
  for p in psutil.process_iter(['pid','name']):
   if p.pid in exclude or (p.info['name'] or '').lower()!='cloudflared.exe':continue
   try:
    args=p.cmdline()
    selected=any(a=='--config' and i+1<len(args) and os.path.normcase(args[i+1])==target for i,a in enumerate(args))
    if selected and os.path.normcase(p.exe())==os.path.normcase(expected['executable']) and p.username().casefold()==expected['owner'].casefold():found.append(p)
   except (psutil.NoSuchProcess,psutil.AccessDenied):continue
  if len(found)==1:return found[0]
  assert len(found)<2,'Duplicate publishing task connector appeared'
  time.sleep(.5)
 raise RuntimeError('Scheduled task connector did not start')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');args=parser.parse_args()
 assert args.activate,'Explicit root-coordinated activation required'
 assert not (OUT/'activation_receipt.json').exists(),'Preserve earlier attempt and inspect before another activation'
 assert json.loads((OUT/'validation.json').read_text())['status']=='passed'
 assert shutil.disk_usage(OUT).free>8*1024*1024,'Insufficient room even for tiny records'
 validate_origin();before_peers=snapshot()
 old_user=identity(16512,MANIFEST['processes']['16512']);old_api=identity(34912,MANIFEST['processes']['34912']);identity(6252,MANIFEST['processes']['6252'])
 for row in MANIFEST['files'].values():assert sha(Path(row['live_path']).read_bytes())==row['before_sha256'],'Live source changed'
 health('before');save('admitted',origin_master_pid=json.loads((OUT.parent/'origin_startup_receipt.json').read_text())['new_master_pid'],peer_listeners=before_peers)
 old_api_args=old_api.cmdline();old_api_cwd=old_api.cwd();old_api_environment=old_api.environ()
 applied=[];new_user=None;new_api=None
 try:
  for label in ('user','scoped','boot'):
   row=MANIFEST['files'][label];target=Path(row['live_path']);data=(OUT/row['candidate_file']).read_bytes()
   assert sha(target.read_bytes())==row['before_sha256'] and sha(data)==row['candidate_sha256']
   atomic(target,data);applied.append(label);save('source_applied',source=label,sha256=sha(data))
  state['live_sources_applied']=True
  wait_idle(16512,20242);task_action('Stop');old_user.wait(timeout=20);save('old_user_task_stopped',pid=16512)
  task_action('Start');new_user=user_process({16512,34912,6252})
  state['new_user_pid']=new_user.pid;state['new_user_created']=new_user.create_time();save('new_user_task_started',pid=new_user.pid,created=new_user.create_time())
  ready=wait_ready(new_user.pid,new_user.create_time(),20242);health('after_user')
  state['user_task_replaced']=True;save('user_task_ready',ha_connections=ready['cloudflared_tunnel_ha_connections'])
  assert snapshot()==before_peers,'Peer identity changed before API rotation'
  old_api=identity(34912,MANIFEST['processes']['34912']);wait_idle(34912,20243)
  old_api.terminate();old_api.wait(timeout=20);save('old_api_connector_stopped',pid=34912,termination='Windows terminate after zero concurrent-request gauge')
  with (OUT/'api_connector_new.private.log').open('xb') as stream:
   child=subprocess.Popen(old_api_args,cwd=old_api_cwd,env=old_api_environment,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
  new_api=psutil.Process(child.pid);state['new_api_pid']=new_api.pid;state['new_api_created']=new_api.create_time();save('new_api_connector_started',pid=new_api.pid,created=new_api.create_time())
  ready=wait_ready(new_api.pid,new_api.create_time(),20243);health('after_api');state['api_connector_replaced']=True
  assert snapshot()==before_peers,'Peer identities changed during rotation'
  identity(6252,MANIFEST['processes']['6252']);validate_origin()
  for row in MANIFEST['files'].values():assert sha(Path(row['live_path']).read_bytes())==row['candidate_sha256']
  state['status']='restored_ingress_and_api_verified';save('complete',user_connector_pid=new_user.pid,api_connector_pid=new_api.pid,ha_connections=ready['cloudflared_tunnel_ha_connections'],all_peer_identities_unchanged=True)
 except Exception as error:
  state['status']='failed_preserved';save('failure',error_type=type(error).__name__)
  for label in reversed(applied):
   row=MANIFEST['files'][label];target=Path(row['live_path'])
   if sha(target.read_bytes())!=row['candidate_sha256']:
    save('rollback_source_identity_changed_preserved',source=label);continue
   atomic(target,(OUT/row['before_file']).read_bytes());save('rollback_source_restored',source=label)
  # Never kill an unexpected process or blindly re-run a failed command. A healthy
  # redundant connector remains available; root reviews any interrupted stage.
  if new_api is not None:
   save('new_api_retained_for_identity_review',pid=new_api.pid,created=state.get('new_api_created'))
  raise

if __name__=='__main__':main()
