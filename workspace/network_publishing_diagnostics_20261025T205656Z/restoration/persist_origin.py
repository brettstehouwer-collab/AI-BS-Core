"""Put only the verified isolated origin under a new current-user logon task."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,time,psutil,http.client,hashlib
OUT=Path(__file__).resolve().parent
m=json.loads((OUT/'static_manifest.json').read_text());old=json.loads((OUT/'origin_receipt.json').read_text())
EXE=Path(m['exe']).resolve();PREFIX=Path(m['prefix']);CONF=Path(m['config'])
owned=psutil.Process(old['master_pid'])
assert owned.create_time()==old['master_created'] and Path(owned.exe()).resolve()==EXE
assert str(CONF) in owned.cmdline() or CONF.as_posix() in owned.cmdline()
task='Stehouwer-Publishing-Reviewed-Static-Origin'
exe=str(EXE).replace("'","''");prefix=PREFIX.as_posix().replace("'","''");conf=CONF.as_posix().replace("'","''")
ps=f"""$ErrorActionPreference='Stop'
$name='{task}'
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){{throw 'Existing task preserved'}}
$account=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action=New-ScheduledTaskAction -Execute '{exe}' -Argument '-p "{prefix}/" -c "{conf}"' -WorkingDirectory '{prefix}'
$trigger=New-ScheduledTaskTrigger -AtLogOn -User $account
$principal=New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Owned loopback-only reviewed Stehouwer Publishing static origin; no AI-BS backend or network configuration changes.' | Out-Null
[pscustomobject]@{{task=$name;registered=$true;principal=$account;runlevel='Limited'}} | ConvertTo-Json
"""
p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
(OUT/'origin_task_registration.stdout.txt').write_bytes(p.stdout);(OUT/'origin_task_registration.stderr.txt').write_bytes(p.stderr)
assert p.returncode==0,'Task registration failed; original running origin preserved'
receipt={'actor':'/root','utc':datetime.now(timezone.utc).isoformat(),'task':task,'old_master_pid':owned.pid,'old_master_created':owned.create_time(),'registered':True,'phase':'registered_before_controlled_handoff'}
def save():(OUT/'origin_startup_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
save()
signal=subprocess.run([str(EXE),'-p',PREFIX.as_posix()+'/', '-c',CONF.as_posix(),'-s','quit'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
(OUT/'origin_quit.stdout.txt').write_bytes(signal.stdout);(OUT/'origin_quit.stderr.txt').write_bytes(signal.stderr)
assert signal.returncode==0,'Graceful owned-origin signal failed; do not start duplicate'
deadline=time.monotonic()+12
while time.monotonic()<deadline:
 if not any(c.status=='LISTEN' and c.laddr.port==80 for c in psutil.net_connections(kind='tcp')):break
 time.sleep(.2)
else:raise RuntimeError('Port80 still occupied; preserve before task start')
ps=f"$ErrorActionPreference='Stop'; Start-ScheduledTask -TaskName '{task}';"
started=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
(OUT/'origin_task_start.stdout.txt').write_bytes(started.stdout);(OUT/'origin_task_start.stderr.txt').write_bytes(started.stderr)
assert started.returncode==0
for _ in range(40):
 rows=[c for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==80]
 if rows:break
 time.sleep(.25)
else:raise RuntimeError('Task-owned origin did not listen; retained manual startup plan')
assert all(c.laddr.ip in ('127.0.0.1','::1') and Path(psutil.Process(c.pid).exe()).resolve()==EXE for c in rows)
masters=[]
for proc in psutil.process_iter(['pid','exe','create_time','cmdline']):
 if proc.info['exe'] and Path(proc.info['exe']).resolve()==EXE and proc.info['create_time']>old['master_created']:
  args=proc.info['cmdline'] or []
  if str(CONF) in args or CONF.as_posix() in args:masters.append(proc)
assert masters
master=min(masters,key=lambda p:p.create_time())
connection=http.client.HTTPConnection('127.0.0.1',80,timeout=5)
connection.request('GET','/',headers={'Host':'stehouwer-publishing.com','Connection':'close'})
response=connection.getresponse();body=response.read(32768);connection.close()
expected=next(x['sha256'] for x in m['files'] if x['relative']=='index.html')
assert response.status==200 and hashlib.sha256(body).hexdigest()==expected
status=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',f"$ErrorActionPreference='Stop'; Get-ScheduledTask -TaskName '{task}' | Select-Object TaskName,State | ConvertTo-Json"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
(OUT/'origin_task_state.json').write_bytes(status.stdout);assert status.returncode==0
receipt.update(phase='task_managed_origin_healthy',new_master_pid=master.pid,new_master_created=master.create_time(),listener_bindings=[{'ip':c.laddr.ip,'pid':c.pid} for c in rows],local_root_status=200,local_root_hash_match=True,reboot_test_performed=False)
save();print(json.dumps(receipt,indent=2))

