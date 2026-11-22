"""Actual local TLS infrastructure fixtures, never guest/worker acceptance."""
from pathlib import Path
import http.client,importlib.util,json,os,sqlite3,ssl,sys,threading,time,unittest,uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from isolated_workers.connector import tls_channel as channel
codec=channel.codec
E=ROOT/'backups/private_connector_20261025_record113/tls_tests'

class ChannelTests(unittest.TestCase):
 def setUp(self):
  self.root=E/uuid.uuid4().hex;self.root.mkdir(parents=True)
  channel.provision_material(self.root);self.key=(self.root/'message-key.bin').read_bytes()
  self.c=sqlite3.connect(self.root/'disposable_replay.sqlite',check_same_thread=False)
  self.claims=channel.ReplayClaims(self.c,create=True)
  self.policy=codec.Policy('worker-fixture','owner-fixture','a'*64,'guest_to_host',frozenset(),{})
  self.calls=[]
  def probe(op,remaining):self.calls.append(op);return {'state':'fixture_responded','operation':op}
  self.server=channel.ChannelServer(0,channel.server_context(self.root),self.key,self.policy,self.claims.claim,probe)
  self.thread=threading.Thread(target=lambda:self.server.serve_forever(poll_interval=0.02),daemon=True);self.thread.start()
  self.context=ssl.create_default_context(cafile=str(self.root/'server-cert.pem'))
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join(4);self.assertFalse(self.thread.is_alive());self.c.close()
 def packet(self,operation='status',key=None,nonce=None):
  now=int(time.time());return codec.pack(self.key if key is None else key,self.policy,'message',json.dumps({'operation':operation}),{},nonce or uuid.uuid4().hex,now,now+60)
 def request(self,raw,path='/v1/message',method='POST',context=None):
  c=http.client.HTTPSConnection('127.0.0.1',self.server.server_port,context=context or self.context,timeout=3)
  try:
   c.request(method,path,body=raw,headers={'Content-Type':'application/json'});response=c.getresponse();return response.status,response.read(65537)
  finally:c.close()
 def decode(self,raw):
  p=self.policy;reverse=codec.Policy(p.worker,p.owner,p.base_sha256,'host_to_guest',frozenset(),{})
  result=codec.unpack(raw,self.key,reverse,int(time.time()),lambda *args:True);return json.loads(result.message)
 def test_authenticated_status_signed_reply_and_loopback(self):
  raw=self.packet();status,response=self.request(raw);self.assertEqual(status,200);result=self.decode(response)['result']
  self.assertEqual(self.server.server_address[0],'127.0.0.1');self.assertFalse(result['worker_admitted']);self.assertFalse(result['execution_authorized']);self.assertFalse(result['apply_authorized']);self.assertEqual(self.calls,[])
 def test_wrong_key_and_no_auth_refused(self):
  for raw in [b'{}',self.packet(key=os.urandom(32))]:self.assertEqual(self.request(raw)[0],401)
  self.assertEqual(self.calls,[]);self.assertEqual(self.c.execute('SELECT COUNT(*) FROM integration_replay_v1').fetchone()[0],0)
 def test_replay_refused(self):
  raw=self.packet();self.assertEqual(self.request(raw)[0],200);self.assertEqual(self.request(raw)[0],401)
 def test_unapproved_commands_and_paths_refused(self):
  for op in ['execute','codex_rpc','http://example.invalid','file_write']:self.assertEqual(self.request(self.packet(op))[0],403)
  for path in ['/api/executive/run','/api/generate','/v1/message?path=private','http://127.0.0.1:8080/health']:self.assertEqual(self.request(self.packet(),path)[0],404)
  self.assertEqual(self.calls,[])
 def test_gateway_and_model_use_only_fixed_probe_operations(self):
  for op in ['gateway_health','model_version']:
   status,response=self.request(self.packet(op));self.assertEqual(status,200);self.assertEqual(self.decode(response)['operation'],op)
  self.assertEqual(self.calls,['gateway_health','model_version'])
 def test_untrusted_server_certificate_refused(self):
  with self.assertRaises(ssl.SSLError):self.request(self.packet(),context=ssl.create_default_context())
 def test_plain_http_not_accepted(self):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
  try:
   with self.assertRaises((OSError,http.client.HTTPException)):c.request('POST','/v1/message',body=self.packet());c.getresponse()
  finally:c.close()
 def test_oversize_and_get_refused(self):
  self.assertEqual(self.request(b'x'*65537)[0],413);self.assertEqual(self.request(b'',method='GET')[0],405)
 def test_attached_files_policy_refused(self):
  p=codec.Policy('worker','owner','a'*64,'guest_to_host',frozenset({'outputs/x.txt'}),{})
  with self.assertRaises(ValueError):channel.ChannelServer(0,channel.server_context(self.root),self.key,p,self.claims.claim,lambda x:{})
 def test_provision_does_not_replace_existing_material(self):
  before=(self.root/'message-key.bin').read_bytes()
  with self.assertRaises(ValueError):channel.provision_material(self.root)
  self.assertEqual((self.root/'message-key.bin').read_bytes(),before)
 def test_request_budget_prevents_unbounded_claim_growth(self):
  self.server.request_budget=1
  self.assertEqual(self.request(self.packet())[0],200);self.assertEqual(self.request(self.packet())[0],503)
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM integration_replay_v1').fetchone()[0],1)
 def test_absolute_deadline_closes_slow_header_connection(self):
  self.server.connection_deadline=0.3
  import socket
  raw=socket.create_connection(('127.0.0.1',self.server.server_port),timeout=2);tls=self.context.wrap_socket(raw,server_hostname='127.0.0.1');started=time.monotonic();closed=False
  try:
   tls.sendall(b'POST /v1/message HTTP/1.1\r\nX-Slow: ')
   for _ in range(12):
    time.sleep(0.06)
    try:tls.sendall(b'x')
    except OSError:closed=True;break
   if not closed:closed=tls.recv(1)==b''
   self.assertTrue(closed);self.assertLess(time.monotonic()-started,1.2)
  finally:tls.close()
 def test_global_expiry_interrupts_active_request(self):
  import socket
  raw=socket.create_connection(('127.0.0.1',self.server.server_port),timeout=2);tls=self.context.wrap_socket(raw,server_hostname='127.0.0.1')
  try:
   tls.sendall(b'POST /v1/message HTTP/1.1\r\nX-Slow: ');self.server.expire();self.assertEqual(tls.recv(1),b'');self.assertTrue(self.server.expired.is_set())
  finally:tls.close()
 def test_upstream_probe_has_absolute_deadline(self):
  import socket,psutil
  from unittest.mock import patch
  from types import SimpleNamespace
  listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(2);stop=threading.Event()
  def drip():
   try:
    conn,_=listener.accept()
    with conn:
     conn.recv(8192);conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 4000\r\nConnection: close\r\n\r\n')
     while not stop.wait(0.03):conn.sendall(b'x')
   except OSError:pass
  thread=threading.Thread(target=drip,daemon=True);thread.start();process=psutil.Process()
  probe=channel.pinned_probe({'8000':{'pid':process.pid,'created':process.create_time(),'exe':process.exe()}})
  real_http=http.client.HTTPConnection
  def fixture_http(host,port,timeout):return real_http('127.0.0.1',listener.getsockname()[1],timeout=timeout)
  fake=SimpleNamespace(status=psutil.CONN_LISTEN,laddr=SimpleNamespace(port=8000,ip='127.0.0.1'),pid=process.pid)
  started=time.monotonic()
  try:
   with patch.object(channel.http.client,'HTTPConnection',fixture_http),patch.object(psutil,'net_connections',return_value=[fake]):
    try:probe('gateway_health',0.2)
    except (OSError,http.client.HTTPException):pass
   self.assertLess(time.monotonic()-started,0.8)
  finally:stop.set();listener.close();thread.join(2)

if __name__=='__main__':unittest.main()
