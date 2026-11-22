"""Root-approved source/runtime reconciliation; never restarts a process."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess,os,tempfile,shutil
import httpx,psutil

OUT=Path(__file__).resolve().parent
manifest=json.loads((OUT/'manifest.json').read_text())
activation=json.loads((OUT/'activation_receipt.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
assert not (OUT/'reconciliation_receipt.json').exists(),'Keep earlier reconciliation evidence'
assert shutil.disk_usage(OUT).free>8*1024*1024,'Insufficient space for tiny evidence'
report={'actor':'/root/publishing_origin','utc':now(),'authorization':'Root GO after direct user publishing restoration authorization','status':'admitting','restart_performed':False,'original_failed_health_target_status':'UNKNOWN; not retained by first controller','zero_outage_claimed':False,'live_file_changes':[],'checks':[]}
def save():
 (OUT/'reconciliation_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def health(label):
 with httpx.Client(trust_env=False,follow_redirects=False,timeout=8) as client:
  for target in ('http://127.0.0.1:8000/health','https://api.brettstehouwer.live/health'):
   response=client.get(target)
   try:online=response.json().get('status')=='online'
   except ValueError:online=False
   report['checks'].append({'utc':now(),'phase':label,'target':target,'status':response.status_code,'online':online})
   save();assert response.status_code==200 and online,'Current API health failed'
def proc(pid,created,label,old_key):
 expected=manifest['processes'][old_key];p=psutil.Process(pid)
 assert p.create_time()==created and p.exe().casefold()==expected['executable'].casefold() and p.username().casefold()==expected['owner'].casefold()
 assert sha(json.dumps(p.cmdline(),separators=(',',':')).encode())==expected['argv_sha256'],'Connector arguments changed'
 report[label]={'pid':pid,'created':created,'executable_identity_checked':True,'arguments_identity_checked':True}
 return p
def peers():
 expected=next(event['peer_listeners'] for event in activation['events'] if event['event']=='admitted')
 ports={x['port'] for x in expected}|{8888}
 actual=[{'port':c.laddr.port,'ip':c.laddr.ip,'pid':c.pid,'created':psutil.Process(c.pid).create_time()} for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port in ports]
 sort=lambda rows:sorted(rows,key=lambda r:(r['port'],r['ip'],r['pid']))
 assert sort(actual)==sort(expected),'Protected peer listener identity changed'
 flags=('AI_BS_RECDEBUT_OUTBOUND_ENABLED','AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED','AI_BS_DISCORD_NOTIFICATIONS_ENABLED','AI_BS_BACKEND_MANAGE_DAEMONS','AI_BS_BACKEND_BACKGROUND_ENABLED','AI_BS_ALLOW_DESTRUCTIVE_ACTIONS')
 api=next(x for x in actual if x['port']==8080);env=psutil.Process(api['pid']).environ()
 assert all(env.get(k)=='false' for k in flags),'Core activation flags changed'
 report['protected_peers_unchanged']=True;report['six_core_controls_false']=True
def metric(pid,port):
 listeners=[c for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==port]
 assert len(listeners)==1 and listeners[0].pid==pid and listeners[0].laddr.ip=='127.0.0.1'
 with httpx.Client(trust_env=False,follow_redirects=False,timeout=4) as client:response=client.get(f'http://127.0.0.1:{port}/metrics')
 assert response.status_code==200 and len(response.content)<131072
 values=[float(line.rsplit(' ',1)[-1]) for line in response.text.splitlines() if line.startswith('cloudflared_tunnel_ha_connections ')]
 assert values and sum(values)>=4
 return {'pid':pid,'metrics_port':port,'ha_connections':sum(values),'raw_metrics_not_retained':True}
def atomic(path,data):
 handle=tempfile.NamedTemporaryFile(prefix=path.name+'.publishing-reconcile-',suffix='.tmp',dir=path.parent,delete=False)
 try:handle.write(data);handle.flush();os.fsync(handle.fileno())
 finally:handle.close()
 os.replace(handle.name,path);assert path.read_bytes()==data

proc(activation['new_user_pid'],activation['new_user_created'],'user_connector','16512')
proc(activation['new_api_pid'],activation['new_api_created'],'api_connector','34912')
proc(6252,manifest['processes']['6252']['created'],'system_connector_untouched','6252')
peers();health('before_source_reconciliation')
for label,row in manifest['files'].items():
 assert sha(Path(row['live_path']).read_bytes())==row['before_sha256'],'Before source changed'
 assert sha((OUT/row['candidate_file']).read_bytes())==row['candidate_sha256'],'Candidate changed'
applied=[]
try:
 for label in ('user','scoped','boot'):
  row=manifest['files'][label];target=Path(row['live_path'])
  assert sha(target.read_bytes())==row['before_sha256']
  atomic(target,(OUT/row['candidate_file']).read_bytes());applied.append(label)
  report['live_file_changes'].append({'source':label,'after_sha256':sha(target.read_bytes())});save()
 for row in manifest['files'].values():assert sha(Path(row['live_path']).read_bytes())==row['candidate_sha256']
 boot=Path(manifest['files']['boot']['live_path']).read_text()
 scoped_hash=sha(Path(manifest['files']['scoped']['live_path']).read_bytes())
 assert re.search(r"(?m)^CONFIG_SHA='([a-f0-9]{64})'",boot).group(1)==scoped_hash
 report['paired_core_pin_matches']=True
 report['readiness']=[metric(activation['new_user_pid'],20242),metric(activation['new_api_pid'],20243)]
 health('after_source_reconciliation');peers()
 tunnel=re.search(r'^tunnel:\s*(\S+)',Path(manifest['files']['scoped']['live_path']).read_text(),re.M).group(1)
 response=subprocess.run([r'C:\Program Files (x86)\cloudflared\cloudflared.exe','tunnel','info','--output','json',tunnel],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
 assert response.returncode==0,'Control-plane metadata unavailable'
 data=json.loads(response.stdout);conns=data.get('conns') or []
 assert data.get('id')==tunnel and len(conns)==2 and all(len(item.get('conns') or [])==4 for item in conns),'Unexpected registered replica state'
 report['registered_connectors']=[{'identity_sha256':sha(str(item.get('id','')).encode()),'run_at':item.get('run_at'),'edge_connections':len(item.get('conns') or []),'version':item.get('version')} for item in conns]
 report['status']='persistent_runtime_ingress_consistent_api_verified';report['finished_utc']=now();save()
 print(json.dumps({key:report[key] for key in ('status','restart_performed','paired_core_pin_matches','protected_peers_unchanged','six_core_controls_false','readiness','finished_utc')},indent=2))
except Exception as error:
 report['status']='reconciliation_failed_preserved';report['error_type']=type(error).__name__;save()
 for label in reversed(applied):
  row=manifest['files'][label];target=Path(row['live_path'])
  if sha(target.read_bytes())==row['candidate_sha256']:atomic(target,(OUT/row['before_file']).read_bytes())
 report['source_rollback_attempted']=True;save();raise
