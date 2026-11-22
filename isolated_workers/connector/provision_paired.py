"""Register a relayed public certificate and provision a fresh mTLS status run."""
from pathlib import Path
import argparse,base64,hashlib,json,os,secrets,sys,zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from isolated_workers.connector.provision_connector import provision
from isolated_workers.connector.guest_pairing import validate_public_identity

def provision_paired(private_root,public_identity_path):
 path=Path(public_identity_path)
 if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size>16384:raise ValueError('PUBLIC_IDENTITY_FILE_BOUND')
 data=json.loads(path.read_text(encoding='utf-8-sig'))
 if not isinstance(data,dict) or data.get('private_key_export_refused') is not True or data.get('process_elevated',data.get('guest_process_elevated')) is not False:raise ValueError('GUEST_PUBLIC_REPORT_REQUIRED')
 encoded=data.get('certificate_der_b64')
 if not isinstance(encoded,str) or len(encoded)>5500:raise ValueError('PUBLIC_DER_BOUND')
 der=base64.b64decode(encoded,validate=True);identity=validate_public_identity(der)
 if data.get('certificate_sha256')!=identity['certificate_sha256']:raise ValueError('PUBLIC_FINGERPRINT_MISMATCH')
 root=Path(private_root);result=provision(root);config=json.loads((root/'config.json').read_text())
 extra=['isolated_workers/connector/guest_pairing.py','isolated_workers/connector/provision_paired.py','isolated_workers/connector/run_paired.py','isolated_workers/connector/provision_connector.py']
 config['source_hashes'].update({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in extra})
 clients=['isolated_workers/windows/guest/channel/GuestStatusClient.cs','isolated_workers/windows/guest/channel/Invoke-GuestChannelStatus.ps1']
 config['source_hashes'].update({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in clients})
 manifest={Path(p).name:config['source_hashes'][p] for p in clients}
 with zipfile.ZipFile(root/'guest-status-client.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
  for p in clients:archive.writestr(Path(p).name,(ROOT/p).read_bytes())
  archive.writestr('manifest.json',json.dumps(manifest,sort_keys=True,separators=(',',':')))
 config['bootstrap_sha256']=hashlib.sha256((root/'guest-status-client.zip').read_bytes()).hexdigest()
 config['worker']='guest:'+identity['certificate_sha256'];config['base_sha256']=config['source_hashes']['isolated_workers/connector/guest_pairing.py']
 config['channel_epoch']=secrets.token_hex(32);config['guest_certificate_sha256']=identity['certificate_sha256']
 with (root/'approved-guest.cer').open('xb') as f:f.write(der);f.flush();os.fsync(f.fileno())
 with (root/'paired-config.json').open('x') as f:json.dump(config,f,indent=2);f.flush();os.fsync(f.fileno())
 cert=json.loads((root/'certificate_receipt.json').read_text())
 recipe={'host':'10.0.2.2','port':18443,'server_certificate_sha256':cert['certificate_sha256'],'guest_certificate_sha256':identity['certificate_sha256'],'base_sha256':config['base_sha256'],'channel_epoch':config['channel_epoch'],'worker':config['worker'],'owner':config['owner'],'expires_unix':None}
 with (root/'public-recipe.json').open('x') as f:json.dump(recipe,f,indent=2)
 return {'fresh_paired_material':True,'guest_certificate_sha256':identity['certificate_sha256'],'worker_admitted':False,'execution_authorized':False,'OpenAI_credentials_accessed':False}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--private-root',required=True);parser.add_argument('--public-identity',required=True);args=parser.parse_args();print(json.dumps(provision_paired(args.private_root,args.public_identity)))
