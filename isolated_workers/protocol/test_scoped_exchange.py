"""Protocol infrastructure only; no guest, HTTP, execution or filesystem authority."""
import base64,copy,hashlib,importlib.util,json,os,sys,threading,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('scoped_exchange',Path(__file__).with_name('scoped_exchange.py'))
exchange=importlib.util.module_from_spec(spec);sys.modules[spec.name]=exchange;spec.loader.exec_module(exchange)

class ClaimCache:
 def __init__(self):self.seen=set();self.lock=threading.Lock()
 def claim(self,worker,direction,nonce,digest,expires):
  with self.lock:
   k=(worker,direction,nonce)
   if k in self.seen:return False
   self.seen.add(k);return True

class ProtocolTests(unittest.TestCase):
 def setUp(self):
  self.key=os.urandom(32);self.cache=ClaimCache();self.files={'inputs/main.py':b'print("data only")\n'}
  self.policy=exchange.Policy('worker-fixture','owner-fixture','a'*64,'host_to_guest',frozenset(self.files),{'inputs/main.py':hashlib.sha256(self.files['inputs/main.py']).hexdigest()})
 def packet(self,**changes):
  kwargs=dict(key=self.key,policy=self.policy,kind='message',message='fixture data',files=self.files,nonce='1'*32,issued=1000,expires=1100)
  kwargs.update(changes);return exchange.pack(**kwargs)
 def receive(self,raw=None,**changes):
  kwargs=dict(raw=self.packet() if raw is None else raw,key=self.key,policy=self.policy,now=1001,claim=self.cache.claim);kwargs.update(changes);return exchange.unpack(**kwargs)
 def test_roundtrip_data_and_authority(self):
  result=self.receive();self.assertEqual(result.files[0].data,self.files['inputs/main.py']);self.assertFalse(result.execution_authorized);self.assertFalse(result.apply_authorized);self.assertEqual(result.verification_status,'not_run')
 def test_replay_and_concurrent_single_acceptance(self):
  raw=self.packet();results=[]
  def accept():
   try:self.receive(raw);results.append(True)
   except exchange.Rejected:results.append(False)
  threads=[threading.Thread(target=accept) for _ in range(8)]
  for t in threads:t.start()
  for t in threads:t.join()
  self.assertEqual(sum(results),1)
 def test_tamper_and_wrong_key_do_not_claim(self):
  raw=self.packet();obj=json.loads(raw);obj['body']['message']='tampered'
  with self.assertRaises(exchange.Rejected):self.receive(json.dumps(obj).encode())
  with self.assertRaises(exchange.Rejected):self.receive(raw,key=os.urandom(32))
  self.assertEqual(len(self.cache.seen),0);self.receive(raw)
 def test_owner_worker_direction_and_stale_base(self):
  for field,value in [('owner','other'),('worker','other'),('direction','guest_to_host'),('base_sha256','b'*64)]:
   with self.subTest(field=field):
    p=copy.copy(self.policy);object.__setattr__(p,field,value)
    with self.assertRaises(exchange.Rejected):self.receive(policy=p)
 def test_expiry_future_and_ttl(self):
  for now in [900,1101]:
   with self.assertRaises(exchange.Rejected):self.receive(now=now)
  for issued,expires in [(1000,1000),(1000,1301),(True,1100),(1000,1100.0)]:
   with self.assertRaises(exchange.Rejected):self.packet(issued=issued,expires=expires)
 def test_windows_path_aliases_and_disallowed_files(self):
  for path in ['../secret','inputs/../main.py','C:/private','inputs\\main.py','inputs/main.py:stream','inputs/CON','inputs/aux.txt','inputs/a.','inputs/a ','inputs//a','inputs/.env','inputs/a.db','inputs/MAIN.py','outputs/unapproved.txt']:
   with self.subTest(path=path):
    with self.assertRaises(exchange.Rejected):self.packet(files={path:b'x'})
 def test_manifest_input_hash_mismatch(self):
  with self.assertRaises(exchange.Rejected):self.packet(files={'inputs/main.py':b'changed'})
 def test_missing_expected_input(self):
  with self.assertRaises(exchange.Rejected):self.packet(files={})
 def test_duplicate_unknown_and_noncanonical_fields(self):
  raw=self.packet();obj=json.loads(raw);obj['unexpected']=True
  for bad in [json.dumps(obj).encode(),b'{"body":{},"body":{},"mac":"x"}',b'[]',raw+b'junk',b'{"body":NaN}',b'\xff']:
   with self.assertRaises(exchange.Rejected):self.receive(bad)
 def test_bounds_and_key(self):
  for key in [b'',b'short','secret']:
   with self.assertRaises(exchange.Rejected):self.packet(key=key)
  with self.assertRaises(exchange.Rejected):self.packet(message='x'*65537)
  with self.assertRaises(exchange.Rejected):self.receive(b'x'*(exchange.MAX_PACKET_BYTES+1))
 def test_authenticated_structural_corruption(self):
  # Use the sender key to test validation beyond HMAC, never a fabricated seal.
  for change in ['bad_hash','bad_size','extra_file','base64','authority']:
   obj=json.loads(self.packet());body=obj['body']
   if change=='bad_hash':body['files'][0]['sha256']='0'*64
   elif change=='bad_size':body['files'][0]['size']=True
   elif change=='extra_file':body['files'].append(copy.deepcopy(body['files'][0]))
   elif change=='base64':body['files'][0]['data']='@@@'
   else:body['execution_authorized']=True
   raw=exchange._sign(body,self.key)
   with self.assertRaises(exchange.Rejected):self.receive(raw)
  self.assertEqual(len(self.cache.seen),0)
 def test_no_claim_adapter_no_acceptance(self):
  with self.assertRaises(exchange.Rejected):self.receive(claim=None)
 def test_fail_closed_storage_exception(self):
  def unavailable(*args):raise OSError('fixture storage failure')
  with self.assertRaises(exchange.Rejected):self.receive(claim=unavailable)
 def test_cancel_ack_no_files_and_no_execution(self):
  # Cancellation is an authenticated message, not evidence cancellation occurred.
  p=exchange.Policy('worker-fixture','owner-fixture','a'*64,'host_to_guest',frozenset(),{})
  for kind in ['cancel','ack']:
   raw=exchange.pack(self.key,p,kind,'data only',{},'2'*32,1000,1100)
   result=exchange.unpack(raw,self.key,p,1001,ClaimCache().claim);self.assertEqual(result.kind,kind);self.assertFalse(result.execution_authorized)
 def test_output_result_has_only_approved_output_bytes(self):
  p=exchange.Policy('worker-fixture','owner-fixture','a'*64,'guest_to_host',frozenset({'outputs/result.txt'}),{})
  raw=exchange.pack(self.key,p,'result','data',{'outputs/result.txt':b'review required'},'3'*32,1000,1100)
  result=exchange.unpack(raw,self.key,p,1001,ClaimCache().claim)
  self.assertEqual(result.files[0].data,b'review required');self.assertFalse(result.apply_authorized)
 def test_policy_direction_alias_and_defensive_copy(self):
  for paths,direction in [(frozenset({'inputs/main.py','inputs/MAIN.py'}),'host_to_guest'),(frozenset({'inputs/main.py'}),'guest_to_host')]:
   with self.assertRaises(exchange.Rejected):exchange.Policy('worker','owner','a'*64,direction,paths,{})
  hashes=dict(self.policy.expected_files);p=exchange.Policy('worker','owner','a'*64,'host_to_guest',self.policy.allowed_paths,hashes);hashes.clear()
  self.assertEqual(len(p.expected_files),1)
  with self.assertRaises(TypeError):p.expected_files['inputs/main.py']='0'*64
 def test_large_file_and_bad_path_type_refused(self):
  with self.assertRaises(exchange.Rejected):self.packet(files={'inputs/main.py':b'x'*(exchange.MAX_FILE_BYTES+1)})
  with self.assertRaises(exchange.Rejected):self.packet(files={1:b'x'})
 def test_job_control_messages_do_not_require_input_attachment(self):
  for kind in ['cancel','ack']:
   raw=self.packet(kind=kind,files={})
   result=self.receive(raw);self.assertEqual(result.kind,kind);self.assertEqual(result.files,());self.cache=ClaimCache()
   with self.assertRaises(exchange.Rejected):self.packet(kind=kind)

if __name__=='__main__':unittest.main()
