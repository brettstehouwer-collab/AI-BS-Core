"""Run only the reviewed certificate-paired status channel, bounded in time."""
from pathlib import Path
import argparse,hashlib,json,os,psutil,sqlite3,sys,threading,time
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from isolated_workers.connector import guest_pairing as pairing

def run(private_root,lifetime):
 root=Path(private_root);config=json.loads((root/'paired-config.json').read_text())
 if type(lifetime) is not int or not 1<=lifetime<=1800 or config['bind']!='127.0.0.1' or config['port']!=18443:raise ValueError('BOUNDED_PRIVATE_BIND_REQUIRED')
 for rel,digest in config['source_hashes'].items():
  path=(ROOT/rel).resolve()
  if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('SOURCE_IDENTITY_CHANGED')
 der=(root/'approved-guest.cer').read_bytes();context,identity=pairing.paired_context(root,der)
 if identity['certificate_sha256']!=config['guest_certificate_sha256']:raise ValueError('GUEST_IDENTITY_CHANGED')
 policy=pairing.codec.Policy(config['worker'],config['owner'],config['base_sha256'],'guest_to_host',frozenset(),{})
 if (root/'replay.sqlite').exists():raise ValueError('FRESH_RUN_REQUIRED')
 connection=sqlite3.connect(root/'replay.sqlite');claims=pairing.base.ReplayClaims(connection,create=True)
 bundle=(root/'guest-status-client.zip').read_bytes()
 if hashlib.sha256(bundle).hexdigest()!=config['bootstrap_sha256']:raise ValueError('PUBLIC_BUNDLE_CHANGED')
 server=pairing.PairedServer(18443,context,identity,policy,claims.claim,pairing.base.pinned_probe(config['upstreams']),config['channel_epoch'],bundle)
 process=psutil.Process();expires=time.time()+lifetime
 receipt={'pid':process.pid,'created':process.create_time(),'exe':process.exe(),'bind':'127.0.0.1','port':18443,'expires_unix':expires,'guest_certificate_sha256':identity['certificate_sha256'],'channel_epoch':config['channel_epoch'],'worker_admitted':False,'execution_authorized':False,'transport':'pinned_mutual_TLS'}
 for final,data in [('ready.json',receipt),('public-live-recipe.json',{**json.loads((root/'public-recipe.json').read_text()),'expires_unix':expires})]:
  pending=root/(final+'.pending')
  with pending.open('x') as f:json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
  os.rename(pending,root/final)
 watchdog=threading.Timer(lifetime,server.expire);watchdog.daemon=True;watchdog.start();deadline=time.monotonic()+lifetime
 try:
  while not server.expired.is_set() and time.monotonic()<deadline:server.handle_request()
 finally:
  watchdog.cancel();server.server_close();connection.close()
  with (root/'stopped.json').open('x') as f:json.dump({'state':'stopped','pid':process.pid,'created':process.create_time(),'utc':datetime.now(timezone.utc).isoformat()},f)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--private-root',required=True);parser.add_argument('--lifetime',type=int,default=900);args=parser.parse_args();run(args.private_root,args.lifetime)
