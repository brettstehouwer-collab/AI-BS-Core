"""Own one loopback Nginx origin and record bounded static acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,time,http.client
import psutil
OUT=Path(__file__).resolve().parent
m=json.loads((OUT/'static_manifest.json').read_text())
assert m['config_test_exit']==0
EXE=Path(m['exe']).resolve();PREFIX=Path(m['prefix']);CONF=Path(m['config']);PUBLIC=Path(m['public'])
assert hashlib.sha256(CONF.read_bytes()).hexdigest()==m['config_sha256']
listeners=lambda:[c for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==80]
assert not listeners(),'Unexpected existing80listener; preserved'
receipt={'utc':datetime.now(timezone.utc).isoformat(),'actor':'/root','authorization':'Operator requested fixing stehouwer-publishing.com','phase':'starting_origin','exe':str(EXE),'config':str(CONF),'config_sha256':m['config_sha256'],'access_log':'off; no visitor log collection'}
def save():(OUT/'origin_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
with (OUT/'nginx_runtime.stdout.txt').open('xb') as stdout,(OUT/'nginx_runtime.stderr.txt').open('xb') as stderr:
 child=subprocess.Popen([str(EXE),'-p',PREFIX.as_posix()+'/', '-c',CONF.as_posix()],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
master=psutil.Process(child.pid);receipt.update(master_pid=master.pid,master_created=master.create_time(),owner=master.username());save()
for _ in range(30):
 if child.poll() is not None:raise RuntimeError('Owned origin exited; evidence retained')
 current=listeners()
 if current:break
 time.sleep(.2)
else:raise RuntimeError('No80listener after bounded wait; preserve')
owned={master.pid}|{p.pid for p in master.children(recursive=True)}
assert all(c.laddr.ip in ('127.0.0.1','::1') and c.pid in owned and Path(psutil.Process(c.pid).exe()).resolve()==EXE for c in current),'Unexpected origin binding/ownership'
checks=[]
def request(target,host):
 connection=http.client.HTTPConnection('127.0.0.1',80,timeout=5)
 try:
  connection.request('GET',target,headers={'Host':host,'Connection':'close','User-Agent':'AI-BS-Restoration-Static-Check'})
  response=connection.getresponse();body=response.read(32768)
  return response.status,body,response.getheader('content-type')
 finally:connection.close()
expected=next(r['sha256'] for r in m['files'] if r['relative']=='index.html')
for host in ('stehouwer-publishing.com','www.stehouwer-publishing.com'):
 status,body,mime=request('/',host)
 checks.append({'host':host,'path':'/','status':status,'mime':mime,'hash_match':hashlib.sha256(body).hexdigest()==expected})
 assert status==200 and checks[-1]['hash_match']
for target in ('/ledger.html','/invoice.html','/invoice.pdf','/.env','/indexnow_key.txt','/api/health'):
 status,body,mime=request(target,'stehouwer-publishing.com')
 checks.append({'host':'stehouwer-publishing.com','path':target,'status':status,'private_file_absent':status==404})
 assert status==404
status,body,mime=request('/','unreviewed.invalid');assert status==404
receipt.update(phase='origin_ready',listener_bindings=[{'ip':c.laddr.ip,'port':c.laddr.port,'pid':c.pid,'created':psutil.Process(c.pid).create_time()} for c in current],local_checks=checks,unapproved_host_404=True,private_files_not_copied=True,scope='Static root only; no JavaScript/API/HLS/full-site workflow acceptance')
save()
print(json.dumps({'phase':receipt['phase'],'master_pid':master.pid,'local_static_checks':len(checks),'loopback_only':True,'unapproved_host_404':True},indent=2))

