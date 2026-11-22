"""Bounded private integration channel; no execution or arbitrary proxy endpoint."""
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
from datetime import datetime,timezone,timedelta
import argparse,hashlib,http.client,json,os,re,secrets,socket,sqlite3,ssl,sys,time,uuid,threading
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from isolated_workers.protocol import scoped_exchange as codec
from isolated_workers.protocol.replay_claims import ReplayClaims

OPERATIONS=frozenset({'status','gateway_health','model_version'})

def provision_material(directory):
 """Fresh caller-protected directory only; never reads an existing login store."""
 from cryptography import x509
 from cryptography.hazmat.primitives import hashes,serialization
 from cryptography.hazmat.primitives.asymmetric import ec
 from cryptography.x509.oid import NameOID
 import ipaddress
 directory=Path(directory)
 if not directory.is_dir() or any(directory.iterdir()):raise ValueError('EMPTY_PRIVATE_DIRECTORY_REQUIRED')
 key=ec.generate_private_key(ec.SECP256R1());now=datetime.now(timezone.utc)
 name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'AI-BS private integration connector')])
 cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1')),x509.IPAddress(ipaddress.ip_address('10.0.2.2'))]),critical=False).sign(key,hashes.SHA256()))
 values={'server-key.pem':key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()),'server-cert.pem':cert.public_bytes(serialization.Encoding.PEM),'message-key.bin':secrets.token_bytes(32)}
 for name,data in values.items():
  with (directory/name).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 return {'certificate_sha256':cert.fingerprint(hashes.SHA256()).hex(),'expires_utc':(now+timedelta(days=1)).isoformat(),'private_key_or_message_key_exported':False}

def server_context(directory):
 context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
 context.load_cert_chain(str(Path(directory)/'server-cert.pem'),str(Path(directory)/'server-key.pem'));return context

class ChannelServer(HTTPServer):
 allow_reuse_address=False
 def __init__(self,port,context,key,policy,claim,probe,request_budget=256):
  if policy.direction!='guest_to_host' or policy.allowed_paths or policy.expected_files:raise ValueError('CONTROL_CHANNEL_POLICY_REQUIRED')
  if type(request_budget) is not int or not 1<=request_budget<=256:raise ValueError('REQUEST_BUDGET_REQUIRED')
  self.context=context;self.key=key;self.policy=policy;self.claim=claim;self.probe=probe;self.max_body=65536
  self.request_budget=request_budget;self.requests=0
  self.expired=threading.Event();self.connection_deadline=3.0;self.active={};self.active_lock=threading.Lock()
  super().__init__(('127.0.0.1',port),ChannelHandler);self.timeout=0.5
 def get_request(self):
  sock,address=self.socket.accept();sock.settimeout(3)
  if self.expired.is_set():sock.close();raise OSError('CHANNEL_EXPIRED')
  tls=self.context.wrap_socket(sock,server_side=True,do_handshake_on_connect=False)
  timer=threading.Timer(self.connection_deadline,lambda:self._close_active(tls));timer.daemon=True
  with self.active_lock:self.active[tls]=(timer,time.monotonic()+self.connection_deadline)
  timer.start()
  try:tls.do_handshake();return tls,address
  except Exception:self._close_active(tls);raise
 def _close_active(self,sock,hard=True):
  with self.active_lock:state=self.active.pop(sock,None)
  if state:state[0].cancel()
  try:sock.shutdown(socket.SHUT_RDWR if hard else socket.SHUT_WR)
  except OSError:pass
  sock.close()
 def remaining(self,sock):
  with self.active_lock:state=self.active.get(sock)
  remaining=state[1]-time.monotonic() if state else 0
  if remaining<=0 or self.expired.is_set():raise TimeoutError('ABSOLUTE_CHANNEL_DEADLINE')
  return remaining
 def shutdown_request(self,request):self._close_active(request,hard=False)
 def expire(self):
  self.expired.set()
  abort=getattr(self.probe,'abort',None)
  if callable(abort):abort()
  with self.active_lock:active=list(self.active)
  for sock in active:self._close_active(sock)
 def server_close(self):self.expire();super().server_close()
 def handle_error(self,request,client_address):pass

class ChannelHandler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.0'
 server_version='AIBSPrivateChannel/1'
 sys_version=''
 def log_message(self,*args):pass
 def _send(self,status,raw):
  self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers();self.wfile.write(raw);self.close_connection=True
 def do_GET(self):self._send(405,b'{"error":"authenticated_post_required"}')
 def do_POST(self):
  self.server.requests+=1
  if self.server.requests>self.server.request_budget:self._send(503,b'{"error":"channel_budget_exhausted"}');return
  if self.path!='/v1/message':self._send(404,b'{"error":"not_found"}');return
  sizes=self.headers.get_all('Content-Length',[])
  if len(sizes)!=1 or not re.fullmatch('[0-9]{1,6}',sizes[0]) or self.headers.get_all('Transfer-Encoding') or self.headers.get('Content-Type')!='application/json':self._send(400,b'{"error":"request_rejected"}');return
  size=int(sizes[0])
  if not 0<size<=self.server.max_body:self._send(413,b'{"error":"request_rejected"}');return
  try:
   raw=self.rfile.read(size)
   if len(raw)!=size:raise codec.Rejected('SHORT_BODY')
   bundle=codec.unpack(raw,self.server.key,self.server.policy,int(time.time()),self.server.claim)
  except (codec.Rejected,TimeoutError,OSError):self._send(401,b'{"error":"authentication_or_replay_rejected"}');return
  try:
   request=json.loads(bundle.message,object_pairs_hook=codec._unique)
   if bundle.kind!='message' or not isinstance(request,dict) or set(request)!={'operation'} or not isinstance(request['operation'],str) or request['operation'] not in OPERATIONS:raise ValueError('OPERATION_REFUSED')
  except (ValueError,TypeError,RecursionError):self._send(403,b'{"error":"operation_refused"}');return
  operation=request['operation']
  if operation=='status':result={'state':'private_channel_ready','worker_admitted':False,'execution_authorized':False,'apply_authorized':False,'verification_status':'not_run','operations':sorted(OPERATIONS)}
  else:
   try:result=self.server.probe(operation,self.server.remaining(self.connection))
   except Exception:result={'state':'upstream_unavailable','operation':operation}
  message=json.dumps({'request_nonce':bundle.nonce,'operation':operation,'result':result},sort_keys=True,separators=(',',':'))
  p=self.server.policy;out=codec.Policy(p.worker,p.owner,p.base_sha256,'host_to_guest',frozenset(),{})
  now=int(time.time());response=codec.pack(self.server.key,out,'message',message,{},uuid.uuid4().hex,now,now+60)
  self._send(200,response)

def pinned_probe(identities):
 """Fixed read-only loopback routes only; no developer key or proxy inheritance."""
 import psutil
 mapping={'gateway_health':(8000,'/health'),'model_version':(11434,'/api/version')}
 active=set();lock=threading.Lock();expired=threading.Event()
 def close(sock):
  try:sock.shutdown(socket.SHUT_RDWR)
  except OSError:pass
  sock.close()
 def abort():
  expired.set()
  with lock:sockets=list(active)
  for sock in sockets:close(sock)
 def probe(operation,remaining):
  if remaining<=0 or expired.is_set():raise TimeoutError('PROBE_DEADLINE')
  port,path=mapping[operation];pin=identities[str(port)]
  listeners=[x for x in psutil.net_connections(kind='tcp') if x.status==psutil.CONN_LISTEN and x.laddr.port==port]
  if len(listeners)!=1 or listeners[0].laddr.ip!='127.0.0.1' or listeners[0].pid!=pin['pid']:raise ValueError('LISTENER_IDENTITY_CHANGED')
  p=psutil.Process(pin['pid'])
  if p.create_time()!=pin['created'] or p.exe()!=pin['exe']:raise ValueError('PROCESS_IDENTITY_CHANGED')
  connection=http.client.HTTPConnection('127.0.0.1',port,timeout=min(3,remaining));cancelled=threading.Event();holder=[]
  def timeout():
   cancelled.set()
   with lock:sockets=list(holder)
   for sock in sockets:close(sock)
  watchdog=threading.Timer(remaining,timeout);watchdog.daemon=True;watchdog.start()
  try:
   connection.connect();raw=connection.sock
   with lock:holder.append(raw);active.add(raw)
   if cancelled.is_set() or expired.is_set():raise TimeoutError('PROBE_DEADLINE')
   connection.request('GET',path,headers={'Connection':'close'});response=connection.getresponse();data=response.read(4097)
   if len(data)>4096:raise ValueError('UPSTREAM_BOUND')
   result={'state':'responded','http_status':response.status,'operation':operation}
   if operation=='model_version' and response.status==200:
    value=json.loads(data).get('version')
    if isinstance(value,str) and re.fullmatch('[A-Za-z0-9.+-]{1,64}',value):result['version']=value
   return result
  finally:
   watchdog.cancel()
   with lock:
    for sock in holder:active.discard(sock)
   connection.close()
 probe.abort=abort
 return probe

def run(private_root,lifetime):
 """Entry invoked only after private ACL/source/port preflight by host controller."""
 import psutil
 private_root=Path(private_root);config=json.loads((private_root/'config.json').read_text())
 if not 1<=lifetime<=1800 or config['port']!=18443 or config['bind']!='127.0.0.1':raise ValueError('BOUNDED_PRIVATE_BIND_REQUIRED')
 for relative,digest in config['source_hashes'].items():
  path=(ROOT/relative).resolve()
  if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('SOURCE_IDENTITY_CHANGED')
 key=(private_root/'message-key.bin').read_bytes()
 policy=codec.Policy(config['worker'],config['owner'],config['base_sha256'],'guest_to_host',frozenset(),{})
 database=private_root/'replay.sqlite'
 if database.exists():raise ValueError('FRESH_LAUNCH_STORE_REQUIRED')
 c=sqlite3.connect(database);claims=ReplayClaims(c,create=True)
 server=ChannelServer(18443,server_context(private_root),key,policy,claims.claim,pinned_probe(config['upstreams']))
 process=psutil.Process();receipt={'pid':process.pid,'created':process.create_time(),'exe':process.exe(),'bind':'127.0.0.1','port':18443,'expires_unix':time.time()+lifetime,'worker_admitted':False,'execution_authorized':False,'source_hashes':config['source_hashes']}
 with (private_root/'ready.pending.json').open('x') as f:json.dump(receipt,f,indent=2);f.flush();os.fsync(f.fileno())
 os.rename(private_root/'ready.pending.json',private_root/'ready.json')
 deadline=time.monotonic()+lifetime
 watchdog=threading.Timer(lifetime,server.expire);watchdog.daemon=True;watchdog.start()
 try:
  while time.monotonic()<deadline and not server.expired.is_set():server.handle_request()
 finally:
  watchdog.cancel();server.server_close();c.close()
  with (private_root/'stopped.json').open('x') as f:json.dump({'state':'stopped','pid':process.pid,'created':process.create_time(),'utc':datetime.now(timezone.utc).isoformat()},f)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--private-root',required=True);parser.add_argument('--lifetime',type=int,default=900);args=parser.parse_args();run(args.private_root,args.lifetime)
