"""Bounded read-only process/config/listener inspection; sanitized evidence only."""
from datetime import datetime, timezone
import hashlib, importlib.util, json, os
from pathlib import Path
import sys
import psutil

ROOT = Path(r'C:\AI-BS')
OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('reviewed_core_boot', ROOT/'scripts/core_boot.py')
boot = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = boot
spec.loader.exec_module(boot)  # Only definitions; main() is guarded and never called.
checkpoint = json.loads((ROOT/'backups/reboot_handoff_20261025T220833Z/checkpoint.json').read_text())
connections = psutil.net_connections(kind='tcp')
ports = {80,8000,8080,5173,11434,8189,8888,20241,20242,20243,20244,20245}
listeners = [c for c in connections if c.status=='LISTEN' and c.laddr.port in ports]

def utc(epoch): return datetime.fromtimestamp(epoch, timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def identity(process):
    return {'pid':process.pid, 'created_epoch':process.create_time(), 'created_utc':utc(process.create_time()),
            'exe':process.exe(), 'owner':process.username()}

report = {'actor':'/root/postboot_runtime','observed_utc':datetime.now(timezone.utc).isoformat(),
          'boot_utc':utc(psutil.boot_time()), 'user':os.environ.get('USERNAME'),
          'scope':'read-only process/config/listener inspection; no service activation or mutation',
          'listeners':[], 'core':{}, 'connectors':[], 'nginx':[], 'configs':{}, 'errors':[]}
for conn in sorted(listeners, key=lambda c:(c.laddr.port,c.laddr.ip,c.pid or 0)):
    entry={'port':conn.laddr.port,'ip':conn.laddr.ip,'pid':conn.pid,'loopback':conn.laddr.ip in {'127.0.0.1','::1'}}
    try: entry['process']=identity(psutil.Process(conn.pid))
    except (psutil.Error,OSError) as error:entry['error_type']=type(error).__name__
    report['listeners'].append(entry)

for service in boot.service_specs(ROOT):
    found = [c for c in listeners if c.laddr.port==service.port]
    entry={'port':service.port,'present':bool(found),'admitted':False}
    if found:
        try:
            ipv4=boot.ipv4_listeners(found,service.port)
            process=psutil.Process(ipv4[0].pid)
            boot.validate_existing(service,ipv4,process)
            entry.update(identity(process));entry['admitted']=True
            if service.binary_sha:entry['binary_sha_matches_reviewed']=sha(process.exe())==service.binary_sha
            if service.private:
                environment=process.environ()
                entry['six_false_controls']={key:environment.get(key)=='false' for key in boot.FLAGS}
                del environment
        except (Exception,) as error:entry['error_type']=type(error).__name__
    report['core'][service.name]=entry

expected_configs={'scripts/core_boot.py':ROOT/'scripts/core_boot.py',
                 'saved_data/core_runtime/api-tunnel-scoped.yml':ROOT/'saved_data/core_runtime/api-tunnel-scoped.yml',
                 'user_cloudflared_config':Path.home()/'.cloudflared/config.yml'}
for name,path in expected_configs.items():
    digest=sha(path)
    report['configs'][name]={'sha256':digest,'matches_record99':digest==checkpoint['config_hashes'][name]}
report['paired_core_pin_matches']=sha(expected_configs['saved_data/core_runtime/api-tunnel-scoped.yml'])==boot.CONFIG_SHA

origin_prefix=Path(r'C:\StehouwerPublishing.com\restoration_staging\20261025T205656Z')
origin_config=origin_prefix/'nginx.static.conf'
report['origin_config']={'sha256':sha(origin_config),'loopback_listen_directives':origin_config.read_text().count('listen 127.0.0.1:80'),
                        'access_log_off':'access_log off;' in origin_config.read_text()}
for process in psutil.process_iter(['pid','name']):
    if (process.info['name'] or '').lower() not in {'cloudflared.exe','nginx.exe'}: continue
    try:
        entry=identity(process);args=process.cmdline()
        if (process.info['name'] or '').lower()=='cloudflared.exe':
            entry['kind']='other_connector_args_not_retained'
            for label,path in [('publishing_user_config',expected_configs['user_cloudflared_config']),
                               ('scoped_api_config',expected_configs['saved_data/core_runtime/api-tunnel-scoped.yml'])]:
                if any(os.path.normcase(str(arg)).replace('/','\\')==os.path.normcase(str(path)) for arg in args):
                    entry['kind']=label;entry['selected_config_sha256']=sha(path)
            entry['token_argument_present']=any(arg.lower()=='--token' or arg.lower().startswith('--token=') for arg in args)
            entry['metric_listeners']=[{'port':c.laddr.port,'ip':c.laddr.ip} for c in listeners if c.pid==process.pid and 20241<=c.laddr.port<=20245]
            report['connectors'].append(entry)
        else:
            expected_exe=Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Packages/nginxinc.nginx_Microsoft.Winget.Source_8wekyb3d8bbwe/nginx-1.31.3/nginx.exe'
            entry['reviewed_exe_matches']=os.path.normcase(process.exe())==os.path.normcase(str(expected_exe))
            entry['parent_pid']=process.ppid()
            entry['explicit_reviewed_config']=any(str(arg).replace('\\','/').rstrip('/')==str(origin_config).replace('\\','/') for arg in args)
            entry['explicit_reviewed_prefix']=any(str(arg).replace('\\','/').rstrip('/')==str(origin_prefix).replace('\\','/') for arg in args)
            report['nginx'].append(entry)
        del args
    except (psutil.Error,OSError) as error:report['errors'].append({'pid':process.pid,'error_type':type(error).__name__})
report['core_loopback_only']=all(c.laddr.ip=='127.0.0.1' for c in listeners if c.laddr.port in {8000,8080,5173,11434})
report['unreal_8888_off']=not any(c.laddr.port==8888 for c in listeners)
report['finished_utc']=datetime.now(timezone.utc).isoformat()
(OUT/'runtime_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
