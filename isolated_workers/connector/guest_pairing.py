"""Pinned client-certificate status messages; no shared login or exported key."""
import hashlib,json,ssl,time,secrets,re
from datetime import datetime,timezone,timedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID
from isolated_workers.connector import tls_channel as base
codec=base.codec

def validate_public_identity(der):
 if type(der) is not bytes or not 100<=len(der)<=4096:raise ValueError('PUBLIC_CERTIFICATE_BOUND')
 cert=x509.load_der_x509_certificate(der)
 if cert.public_bytes(serialization.Encoding.DER)!=der:raise ValueError('EXACT_DER_REQUIRED')
 key=cert.public_key()
 if not isinstance(key,ec.EllipticCurvePublicKey) or not isinstance(key.curve,ec.SECP256R1) or not isinstance(cert.signature_hash_algorithm,hashes.SHA256):raise ValueError('P256_SHA256_REQUIRED')
 if cert.subject!=cert.issuer:raise ValueError('DEDICATED_SELF_SIGNED_IDENTITY_REQUIRED')
 key.verify(cert.signature,cert.tbs_certificate_bytes,ec.ECDSA(cert.signature_hash_algorithm))
 now=datetime.now(timezone.utc)
 if cert.not_valid_before_utc>now or cert.not_valid_after_utc<=now+timedelta(minutes=1) or cert.not_valid_after_utc>now+timedelta(days=2):raise ValueError('SHORT_CURRENT_VALIDITY_REQUIRED')
 if cert.not_valid_after_utc-cert.not_valid_before_utc>timedelta(days=2):raise ValueError('SHORT_TOTAL_VALIDITY_REQUIRED')
 constraints=cert.extensions.get_extension_for_class(x509.BasicConstraints).value
 usage=cert.extensions.get_extension_for_class(x509.KeyUsage).value
 eku=cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
 if constraints.ca or not usage.digital_signature or usage.key_cert_sign or usage.crl_sign or set(eku)!={ExtendedKeyUsageOID.CLIENT_AUTH}:raise ValueError('DEDICATED_CLIENT_AUTH_REQUIRED')
 return {'certificate_sha256':hashlib.sha256(der).hexdigest(),'certificate_pem':cert.public_bytes(serialization.Encoding.PEM).decode('ascii'),'expires_utc':cert.not_valid_after_utc.isoformat()}

def paired_context(private_root,der):
 identity=validate_public_identity(der)
 context=base.server_context(private_root)
 context.verify_mode=ssl.CERT_REQUIRED
 context.load_verify_locations(cadata=identity['certificate_pem'])
 # Trust only the explicitly relayed client leaf; retain normal validity/EKU
 # verification. No operating-system trust store or guest private key involved.
 context.verify_flags|=ssl.VERIFY_X509_PARTIAL_CHAIN
 return context,identity

class PairedServer(base.ChannelServer):
 def __init__(self,port,context,identity,policy,claim,probe,channel_epoch,bootstrap_bundle=None):
  if context.verify_mode!=ssl.CERT_REQUIRED or policy.worker!='guest:'+identity['certificate_sha256']:raise ValueError('PINNED_MTLS_POLICY_REQUIRED')
  if not isinstance(channel_epoch,str) or len(channel_epoch)!=64 or any(c not in '0123456789abcdef' for c in channel_epoch):raise ValueError('FRESH_CHANNEL_EPOCH_REQUIRED')
  self.peer_sha256=identity['certificate_sha256']
  self.channel_epoch=channel_epoch
  if bootstrap_bundle is not None and (type(bootstrap_bundle) is not bytes or not 0<len(bootstrap_bundle)<=65536):raise ValueError('STATIC_PUBLIC_BUNDLE_BOUND')
  self.bootstrap_bundle=bootstrap_bundle
  super().__init__(port,context,secrets.token_bytes(32),policy,claim,probe)
  self.RequestHandlerClass=PairedHandler

class PairedHandler(base.ChannelHandler):
 def do_GET(self):
  peer=self.connection.getpeercert(binary_form=True)
  if not peer or hashlib.sha256(peer).hexdigest()!=self.server.peer_sha256:self._send(401,b'{"error":"peer_refused"}');return
  if self.path!='/bootstrap/guest-status.zip' or self.server.bootstrap_bundle is None:self._send(405,b'{"error":"fixed_public_bundle_only"}');return
  self.server.requests+=1
  if self.server.requests>self.server.request_budget:self._send(503,b'{"error":"channel_budget_exhausted"}');return
  data=self.server.bootstrap_bundle
  self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Length',str(len(data)));self.send_header('X-AIBS-SHA256',hashlib.sha256(data).hexdigest());self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers();self.wfile.write(data);self.close_connection=True
 def do_POST(self):
  self.server.requests+=1
  if self.server.requests>self.server.request_budget:self._send(503,b'{"error":"channel_budget_exhausted"}');return
  peer=self.connection.getpeercert(binary_form=True)
  if not peer or hashlib.sha256(peer).hexdigest()!=self.server.peer_sha256:self._send(401,b'{"error":"peer_refused"}');return
  if self.path!='/v1/guest-message':self._send(404,b'{"error":"not_found"}');return
  sizes=self.headers.get_all('Content-Length',[])
  if len(sizes)!=1 or not re.fullmatch('[0-9]{1,5}',sizes[0]) or self.headers.get_all('Transfer-Encoding') or self.headers.get('Content-Type')!='application/json':self._send(400,b'{"error":"request_rejected"}');return
  size=int(sizes[0])
  if not 0<size<=4096:self._send(413,b'{"error":"request_rejected"}');return
  try:
   raw=self.rfile.read(size)
   if len(raw)!=size:raise ValueError('SHORT_BODY')
   body=json.loads(raw.decode('utf-8'),object_pairs_hook=codec._unique)
   if type(body) is not dict or set(body)!={'base_sha256','channel_epoch','issued','nonce','operation','version'} or raw!=codec._canonical(body):raise ValueError('SCOPED_FIELDS_REQUIRED')
   if type(body['version']) is not int or body['version']!=1 or body['base_sha256']!=self.server.policy.base_sha256:raise ValueError('STALE_BASE')
   if body['channel_epoch']!=self.server.channel_epoch:raise ValueError('STALE_CHANNEL_EPOCH')
   if type(body['issued']) is not int or abs(int(time.time())-body['issued'])>60 or not isinstance(body['nonce'],str) or not re.fullmatch('[a-f0-9]{32}',body['nonce']):raise ValueError('FRESH_REQUEST_REQUIRED')
   if not isinstance(body['operation'],str) or body['operation'] not in base.OPERATIONS:raise ValueError('OPERATION_REFUSED')
   p=self.server.policy
   if self.server.claim(p.worker,p.direction,body['nonce'],hashlib.sha256(raw).hexdigest(),body['issued']+60) is not True:raise ValueError('REPLAY_REFUSED')
  except Exception:self._send(401,b'{"error":"authenticated_request_refused"}');return
  operation=body['operation']
  if operation=='status':result={'state':'paired_status_channel_ready','worker_admitted':False,'execution_authorized':False,'apply_authorized':False,'verification_status':'not_run'}
  else:
   try:result=self.server.probe(operation,self.server.remaining(self.connection))
   except Exception:result={'state':'upstream_unavailable','operation':operation}
  response={'request_nonce':body['nonce'],'operation':operation,'worker':p.worker,'owner':p.owner,'base_sha256':p.base_sha256,'channel_epoch':self.server.channel_epoch,'result':result,'worker_admitted':False,'execution_authorized':False,'apply_authorized':False}
  self._send(200,codec._canonical(response))
