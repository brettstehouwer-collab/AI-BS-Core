"""Provision fresh host-private channel material after ACL preflight; no login access."""
from pathlib import Path
import argparse,hashlib,json,psutil,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from isolated_workers.connector.tls_channel import provision_material

def provision(private_root):
 p=Path(private_root)
 for parent in [p,*p.parents]:
  if parent.is_symlink() or parent.is_junction():raise ValueError('LINKED_PRIVATE_ROOT_REFUSED')
 certificate=provision_material(p);upstreams={};username=psutil.Process().username()
 for port in [8000,11434]:
  listeners=[x for x in psutil.net_connections(kind='tcp') if x.status==psutil.CONN_LISTEN and x.laddr.port==port]
  if len(listeners)!=1 or listeners[0].laddr.ip!='127.0.0.1':raise ValueError('CORE_LOOPBACK_REQUIRED')
  proc=psutil.Process(listeners[0].pid)
  if proc.username()!=username:raise ValueError('OWNED_CORE_REQUIRED')
  upstreams[str(port)]={'pid':proc.pid,'created':proc.create_time(),'exe':proc.exe()}
 relatives=['isolated_workers/connector/tls_channel.py','isolated_workers/protocol/scoped_exchange.py','isolated_workers/protocol/replay_claims.py']
 sources={relative:hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() for relative in relatives}
 config={'port':18443,'bind':'127.0.0.1','worker':'S-1-5-21-2133766663-4066672948-2456486318-1005','owner':'stehouwer_publishing','base_sha256':sources[relatives[0]],'source_hashes':sources,'upstreams':upstreams,'worker_admitted':False}
 with (p/'config.json').open('x') as f:json.dump(config,f,indent=2)
 with (p/'certificate_receipt.json').open('x') as f:json.dump(certificate,f,indent=2)
 return {'fresh_material_provisioned':True,'certificate_expires':certificate['expires_utc'],'port':18443,'worker_admitted':False}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--private-root',required=True);args=parser.parse_args();print(json.dumps(provision(args.private_root)))
