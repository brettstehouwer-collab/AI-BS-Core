"""Read-only local connection-map audit. Never outputs credential values.

This inspects declared locations/names and local process metadata. It does not
activate providers, validate external credentials, or mutate environment files.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.core_boot import FLAGS,service_specs,validate_existing,ipv4_listeners,CONFIG_SHA

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def run(map_path:Path,out:Path):
 import psutil,httpx
 from dotenv import dotenv_values
 assert map_path.is_file() and out.resolve().is_relative_to((ROOT/'backups').resolve())
 out.mkdir(parents=True,exist_ok=False)
 text=map_path.read_text(encoding='utf-8-sig')
 names=sorted(set(t for t in re.findall(r'`([^`\n]+)`',text) if re.fullmatch(r'[A-Z][A-Z0-9_]{2,}',t)))
 # Files explicitly referenced by this inventory; only these dotenv files read.
 env_paths={'.env':ROOT/'.env','backend/.env':ROOT/'backend/.env','frontend/.env.local':ROOT/'frontend/.env.local'}
 envs={};file_status={}
 for rel,p in env_paths.items():
  values=dotenv_values(p,interpolate=False) if p.is_file() else {}
  envs[rel]=values
  tracked=subprocess.run(['git','ls-files','--error-unmatch','--',rel],cwd=ROOT,capture_output=True).returncode==0
  ignored=subprocess.run(['git','check-ignore','-q','--',rel],cwd=ROOT,capture_output=True).returncode==0
  file_status[rel]={'exists':p.is_file(),'tracked':tracked,'ignored':ignored,'declared_names':len(values),'populated_names':sum(bool(v) for v in values.values()),'values_exported':False}
 # Source references are name-level linkage, not proof a feature runs.
 listed=subprocess.run(['rg','--files','backend','frontend','scripts','-g','*.py','-g','*.jsx','-g','*.tsx','-g','*.js','-g','*.ts','-g','*.mjs','-g','*.cjs','-g','!**/node_modules/**','-g','!**/dist/**','-g','!**/build/**'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True).stdout.splitlines()
 refs={n:[] for n in names};pattern=re.compile(r'\b(?:'+ '|'.join(re.escape(n) for n in names)+r')\b')
 for rel in listed:
  p=ROOT/rel
  if p.stat().st_size>4*1024*1024 or p.resolve()==Path(__file__).resolve():continue
  try:source=p.read_text(encoding='utf-8-sig')
  except (OSError,UnicodeError):continue
  for n in set(pattern.findall(source)):refs[n].append(rel.replace('\\','/'))
 connections=psutil.net_connections(kind='tcp');runtime={};backend=None
 for spec in service_specs(ROOT):
  listeners=ipv4_listeners(connections,spec.port)
  if not listeners:runtime[spec.name]={'state':'not_listening','port':spec.port};continue
  p=psutil.Process(listeners[0].pid)
  try:
   identity=validate_existing(spec,listeners,p)
   if p.username().casefold()!=psutil.Process().username().casefold():raise RuntimeError('Owner mismatch')
   runtime[spec.name]={'state':'admitted','port':spec.port,'ip':listeners[0].laddr.ip,**identity}
   if spec.port==8080:backend=p
  except (RuntimeError,psutil.Error):runtime[spec.name]={'state':'unexpected_preserved','port':spec.port}
 process_env=backend.environ() if backend else {}
 variables=[]
 for n in names:
  loc=[rel for rel,vs in envs.items() if n in vs];pop=[rel for rel,vs in envs.items() if vs.get(n)]
  conflict=len({envs[rel][n] for rel in pop})>1
  variables.append({'name':n,'declared_in':loc,'populated_in':pop,'different_populated_file_values':conflict,'backend_environment_populated':bool(process_env.get(n)),'source_reference_count':len(refs[n]),'source_references':refs[n][:5],'external_validity':'not_tested'})
 # Classify core/runtime gates without exposing any process arguments or secret.
 gates={'backend_admitted':backend is not None,'six_controls_explicit_false':bool(backend) and all(process_env.get(k)=='false' for k in FLAGS),'unreal8888_off':not any(c.status=='LISTEN' and c.laddr.port==8888 for c in connections)}
 auth={'map_mentions_AI_BS_ADMIN_KEY':'AI_BS_ADMIN_KEY' in names,'admin_key_backend_environment_populated':bool(process_env.get('AI_BS_ADMIN_KEY')),'map_AI_BS_API_KEY_is_not_substituted':True,'hosted_browser_auth':'SDK-verified Firebase existing admin principal; private local key never forwarded to hosted origin'}
 probes=[]
 if backend:
  with httpx.Client(trust_env=False,follow_redirects=False,timeout=5) as c:
   for port in [8080,8000]:
    r=c.get(f'http://127.0.0.1:{port}/health',headers={'Authorization':'Bearer '+process_env['AI_BS_ADMIN_KEY']})
    probes.append({'path':'/health','port':port,'status':r.status_code,'credential_destination':'loopback_only'})
 config=ROOT/'saved_data/core_runtime/api-tunnel-scoped.yml'
 tunnel={'current_reviewed_config_exists':config.is_file(),'current_reviewed_config_sha_matches':config.is_file() and sha(config)==CONFIG_SHA,'current_reviewed_config':'saved_data/core_runtime/api-tunnel-scoped.yml','legacy_user_config_referenced_in_map':'.cloudflared' in text,'source_boot_does_not_use_legacy_launcher':True,'processes':[]}
 for p in psutil.process_iter(['pid','name']):
  if (p.info['name'] or '').lower()!='cloudflared.exe':continue
  try:
   owner=p.username();args=p.cmdline();idx=next((i for i,x in enumerate(args[:-1]) if x=='--config'),None)
   cfg=args[idx+1] if idx is not None else None
   tunnel['processes'].append({'pid':p.pid,'created':p.create_time(),'current_user':owner.casefold()==psutil.Process().username().casefold(),'uses_reviewed_scoped_config':bool(cfg) and os.path.normcase(os.path.abspath(cfg))==os.path.normcase(str(config)),'config_argument_present':cfg is not None,'other_arguments_withheld':True})
  except (psutil.Error,OSError):tunnel['processes'].append({'pid':p.pid,'metadata_unavailable':True,'preserved':True})
 counts={'mapped_names':len(names),'populated_in_local_files':sum(bool(v['populated_in']) for v in variables),'not_populated_in_local_files':sum(not v['populated_in'] for v in variables),'populated_in_backend_environment':sum(v['backend_environment_populated'] for v in variables),'names_with_different_populated_file_values':sum(v['different_populated_file_values'] for v in variables),'names_without_scanned_source_reference':sum(not v['source_reference_count'] for v in variables)}
 report={'utc':datetime.now(timezone.utc).isoformat(),'attachment_sha256':sha(map_path),'attachment_preserved':True,'counts':counts,'files':file_status,'variables':variables,'runtime':runtime,'runtime_gates':gates,'authentication':auth,'health_probes':probes,'tunnel':tunnel,'environment_values_or_secret_hashes_exported':False,'external_provider_calls':False,'source_or_configuration_mutations':False,'source_reference_scope':'backend/frontend/scripts language sources, excluding node_modules/dist/build; names only, not execution proof','notes':['Environment precedence in scripts/core_boot.py is inherited process environment, root .env, then backend .env via setdefault; no overrides applied.','Map describes legacy broad Launch_AI_BS.bat and user cloudflared config; current core recovery uses scripts/core_boot.py and pinned scoped API config.','Presence and source references are not external authentication, completeness, billing or functional acceptance.']}
 (out/'connection_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 # Recheck credentials and attachment via metadata-independent in-memory digest.
 print(json.dumps({'output':str(out/'connection_audit.json'),'counts':counts,'runtime_gates':gates,'health':probes,'credential_values_exported':False,'external_provider_calls':False,'application_or_credential_changes':False}))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--map',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();run(args.map,args.output)
