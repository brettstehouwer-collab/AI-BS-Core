"""Pinned-mTLS socket fixtures; no guest key-store or guest acceptance claim."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,http.client,json,sqlite3,ssl,sys,threading,time,unittest,uuid
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from isolated_workers.connector import guest_pairing as pairing
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
E=ROOT/'backups/guest_enrollment_20261025_record114/tls_tests'

def client_material(root,label='fixture',days=1,ca=False,client_auth=True,age_days=0):
 key=ec.generate_private_key(ec.SECP256R1());now=datetime.now(timezone.utc)
 name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,label)])
 cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=max(age_days,2)) if days<0 or age_days else now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=days)).add_extension(x509.BasicConstraints(ca=ca,path_length=None),critical=True).add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,key_encipherment=False,data_encipherment=False,key_agreement=False,key_cert_sign=ca,crl_sign=ca,encipher_only=False,decipher_only=False),critical=True).add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH if client_auth else ExtendedKeyUsageOID.SERVER_AUTH]),critical=False).sign(key,hashes.SHA256()))
 der=cert.public_bytes(serialization.Encoding.DER);public=root/(label+uuid.uuid4().hex+'.pem');private=public.with_suffix('.key')
 public.write_bytes(cert.public_bytes(serialization.Encoding.PEM));private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
 return der,public,private

class PairingTests(unittest.TestCase):
 def setUp(self):
  self.root=E/uuid.uuid4().hex;self.root.mkdir(parents=True);self.material=self.root/'server';self.material.mkdir()
  pairing.base.provision_material(self.material)
  self.der,self.public,self.private=client_material(self.root)
  context,self.identity=pairing.paired_context(self.material,self.der)
  self.policy=pairing.codec.Policy('guest:'+self.identity['certificate_sha256'],'owner-fixture','a'*64,'guest_to_host',frozenset(),{})
  self.c=sqlite3.connect(self.root/'disposable_replay.sqlite',check_same_thread=False);self.claims=pairing.base.ReplayClaims(self.c,create=True)
  self.server=pairing.PairedServer(0,context,self.identity,self.policy,self.claims.claim,lambda op,remaining:{'state':'fixture_responded'},'c'*64)
  self.thread=threading.Thread(target=lambda:self.server.serve_forever(poll_interval=0.02),daemon=True);self.thread.start()
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join(4);self.assertFalse(self.thread.is_alive());self.c.close()
 def request(self,body=None,cert=True,material=None,path='/v1/guest-message'):
  context=ssl.create_default_context(cafile=str(self.material/'server-cert.pem'))
  if cert:
   public,private=material if material else (self.public,self.private);context.load_cert_chain(str(public),str(private))
  c=http.client.HTTPSConnection('127.0.0.1',self.server.server_port,context=context,timeout=3)
  raw=pairing.codec._canonical(self.body() if body is None else body)
  try:c.request('POST',path,body=raw,headers={'Content-Type':'application/json'});r=c.getresponse();return r.status,r.read(8193)
  finally:c.close()
 def body(self,**changes):
  body={'base_sha256':self.policy.base_sha256,'channel_epoch':self.server.channel_epoch,'issued':int(time.time()),'nonce':uuid.uuid4().hex,'operation':'status','version':1};body.update(changes);return body
 def test_approved_peer_status_stays_unadmitted(self):
  status,raw=self.request();self.assertEqual(status,200);data=json.loads(raw)
  self.assertEqual(data['worker'],self.policy.worker);self.assertEqual(data['owner'],self.policy.owner)
  self.assertFalse(data['worker_admitted']);self.assertFalse(data['execution_authorized']);self.assertFalse(data['apply_authorized'])
 def test_missing_client_certificate_fails_tls(self):
  with self.assertRaises((ssl.SSLError,OSError,http.client.HTTPException)):self.request(cert=False)
 def test_other_key_same_subject_fails_tls(self):
  der,pub,key=client_material(self.root)
  with self.assertRaises((ssl.SSLError,OSError,http.client.HTTPException)):self.request(material=(pub,key))
 def test_exact_peer_pin_checked_after_tls(self):
  self.server.peer_sha256='0'*64;self.assertEqual(self.request()[0],401)
 def test_wrong_mapping_refused(self):
  p=pairing.codec.Policy('other-worker','owner-fixture','a'*64,'guest_to_host',frozenset(),{})
  context,identity=pairing.paired_context(self.material,self.der)
  with self.assertRaises(ValueError):pairing.PairedServer(0,context,identity,p,self.claims.claim,lambda *args:{},'c'*64)
 def test_wrong_base_replay_and_extra_identity_refused(self):
  body=self.body();self.assertEqual(self.request(body)[0],200);self.assertEqual(self.request(body)[0],401)
  for bad in [self.body(base_sha256='b'*64),self.body(owner='other-owner'),self.body(worker='other-worker'),self.body(issued=int(time.time())-120)]:
   self.assertEqual(self.request(bad)[0],401)
 def test_no_execution_or_legacy_hmac_route(self):
  self.assertEqual(self.request(self.body(operation='execute'))[0],401);self.assertEqual(self.request(path='/v1/message')[0],404)
 def test_public_identity_profile_and_bounds(self):
  for kwargs in [{'days':-1},{'ca':True},{'client_auth':False},{'days':3},{'age_days':10}]:
   der,_,_=client_material(self.root,**kwargs)
   with self.assertRaises(ValueError):pairing.validate_public_identity(der)
  for der in [b'',self.der+b'junk',b'x'*4097]:
   with self.assertRaises(ValueError):pairing.validate_public_identity(der)
 def test_trust_is_private_context_only(self):
  context,identity=pairing.paired_context(self.material,self.der)
  self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED);self.assertEqual(identity['certificate_sha256'],hashlib.sha256(self.der).hexdigest())
 def test_request_budget_and_absolute_timer_inherited(self):
  self.server.request_budget=1
  self.assertEqual(self.request()[0],200);self.assertEqual(self.request()[0],503)
 def test_old_packet_rejected_with_fresh_database_and_new_epoch(self):
  old=self.body();self.assertEqual(self.request(old)[0],200)
  fresh=sqlite3.connect(self.root/'fresh_epoch_replay.sqlite',check_same_thread=False)
  try:
   self.server.claim=pairing.base.ReplayClaims(fresh,create=True).claim;self.server.channel_epoch='d'*64
   self.assertEqual(self.request(old)[0],401);self.assertEqual(fresh.execute('SELECT COUNT(*) FROM integration_replay_v1').fetchone()[0],0)
   self.assertEqual(self.request()[0],200)
  finally:self.server.claim=self.claims.claim;fresh.close()
 def test_non_ascii_content_length_refused(self):
  context=ssl.create_default_context(cafile=str(self.material/'server-cert.pem'));context.load_cert_chain(str(self.public),str(self.private))
  c=http.client.HTTPSConnection('127.0.0.1',self.server.server_port,context=context,timeout=3)
  try:
   c.request('POST','/v1/guest-message',body=b'{}',headers={'Content-Type':'application/json','Content-Length':'\u00b2'});response=c.getresponse();self.assertEqual(response.status,400);response.read()
  finally:c.close()
 def test_public_bundle_download_requires_exact_approved_peer(self):
  data=b'bounded public source fixture';self.server.bootstrap_bundle=data
  context=ssl.create_default_context(cafile=str(self.material/'server-cert.pem'));context.load_cert_chain(str(self.public),str(self.private))
  c=http.client.HTTPSConnection('127.0.0.1',self.server.server_port,context=context,timeout=3)
  try:
   c.request('GET','/bootstrap/guest-status.zip');response=c.getresponse();self.assertEqual(response.status,200);self.assertEqual(response.getheader('X-AIBS-SHA256'),hashlib.sha256(data).hexdigest());self.assertEqual(response.read(),data)
  finally:c.close()

if __name__=='__main__':unittest.main()
