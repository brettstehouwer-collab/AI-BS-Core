"""Dormant authenticated data-envelope codec; no sockets, host paths or execution.

Caller owns key provisioning, confidential channel and an atomic durable replay
claim adapter. Authentication here never establishes execution/apply authority.
"""
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
import base64,binascii,hashlib,hmac,json,re

MAX_PACKET_BYTES=12*1024*1024
MAX_FILE_BYTES=1024*1024
MAX_TOTAL_BYTES=8*1024*1024
MAX_FILES=64
DOMAIN=b'AI-BS/integration-data/v1\x00'

class Rejected(ValueError):pass

def _require(condition,code):
 if not condition:raise Rejected(code)

def _hash(value):return isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value) is not None

def _path(value):
 _require(isinstance(value,str) and len(value)<=192,'PATH_BOUND')
 parts=value.split('/')
 _require(len(parts)>=2 and parts[0] in {'inputs','outputs'},'EXCHANGE_ROOT_REQUIRED')
 for part in parts:
  _require(re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_. -]{0,95}',part) is not None and part[-1] not in ' .','CANONICAL_PATH_REQUIRED')
  _require(part.split('.')[0].upper() not in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))},'WINDOWS_DEVICE_REFUSED')
  _require(not part.lower().endswith(('.db','.sqlite','.sqlite3','.db-wal','.db-shm','.pem','.key','.pfx','.vdi','.gguf','.safetensors')),'PRIVATE_STORE_TYPE_REFUSED')
 return value

@dataclass(frozen=True)
class Policy:
 worker:str
 owner:str
 base_sha256:str
 direction:str
 allowed_paths:frozenset
 expected_files:Mapping[str,str]
 def __post_init__(self):
  _require(all(isinstance(v,str) and re.fullmatch('[A-Za-z0-9_:.-]{1,128}',v) for v in [self.worker,self.owner]),'IDENTITY_REQUIRED')
  _require(_hash(self.base_sha256) and self.direction in {'host_to_guest','guest_to_host'},'SCOPE_REQUIRED')
  _require(isinstance(self.allowed_paths,frozenset) and len(self.allowed_paths)<=MAX_FILES,'PATH_ALLOWLIST_REQUIRED')
  paths=[_path(p) for p in self.allowed_paths]
  _require(all(p.startswith('inputs/' if self.direction=='host_to_guest' else 'outputs/') for p in paths),'DIRECTION_PATH_MISMATCH')
  _require(len({p.casefold() for p in paths})==len(paths),'WINDOWS_ALIAS_COLLISION')
  _require(isinstance(self.expected_files,Mapping) and set(self.expected_files)<=self.allowed_paths and all(_hash(v) for v in self.expected_files.values()),'EXPECTED_INPUTS_REQUIRED')
  object.__setattr__(self,'expected_files',MappingProxyType(dict(self.expected_files)))

@dataclass(frozen=True)
class Artifact:
 path:str
 data:bytes
 sha256:str

@dataclass(frozen=True)
class VerifiedBundle:
 kind:str
 message:str
 nonce:str
 files:tuple
 execution_authorized:bool=False
 apply_authorized:bool=False
 verification_status:str='not_run'

def _key(key):_require(type(key) is bytes and 32<=len(key)<=64,'KEY_REQUIRED')

def _canonical(value):
 try:return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
 except (TypeError,ValueError,UnicodeError,RecursionError):raise Rejected('JSON_DATA_REQUIRED') from None

def _sign(body,key):
 _key(key)
 mac=hmac.new(key,DOMAIN+_canonical(body),hashlib.sha256).hexdigest()
 raw=_canonical({'body':body,'mac':mac});_require(len(raw)<=MAX_PACKET_BYTES,'PACKET_BOUND');return raw

def _validate(body,policy,now):
 _require(type(body) is dict and set(body)=={'version','worker','owner','base_sha256','direction','kind','message','nonce','issued','expires','files'},'BODY_FIELDS')
 _require(type(body['version']) is int and body['version']==1,'VERSION')
 for name in ['worker','owner','base_sha256','direction']:_require(body[name]==getattr(policy,name),'SCOPE_MISMATCH')
 _require(body['kind'] in ('message','result','cancel','ack'),'KIND_REFUSED')
 _require(isinstance(body['message'],str) and len(body['message'])<=65536,'MESSAGE_BOUND')
 _require(isinstance(body['nonce'],str) and re.fullmatch('[a-f0-9]{32}',body['nonce']),'NONCE_REQUIRED')
 issued,expires=body['issued'],body['expires']
 _require(type(issued) is int and type(expires) is int and type(now) is int,'INTEGER_TIME_REQUIRED')
 _require(0<=issued<expires and expires-issued<=300 and issued-5<=now<expires,'EXPIRED_OR_FUTURE')
 entries=body['files'];_require(type(entries) is list and len(entries)<=MAX_FILES,'FILE_COUNT_BOUND')
 files=[];seen=set();total=0
 for entry in entries:
  _require(type(entry) is dict and set(entry)=={'path','sha256','size','data'},'FILE_FIELDS')
  path=_path(entry['path']);folded=path.casefold()
  _require(path in policy.allowed_paths and folded not in seen,'UNAPPROVED_OR_DUPLICATE_PATH');seen.add(folded)
  _require(type(entry['size']) is int and 0<=entry['size']<=MAX_FILE_BYTES and _hash(entry['sha256']),'FILE_METADATA_BOUND')
  encoded=entry['data'];_require(isinstance(encoded,str) and len(encoded)<=4*((MAX_FILE_BYTES+2)//3),'BASE64_BOUND')
  try:data=base64.b64decode(encoded,validate=True)
  except (ValueError,binascii.Error):raise Rejected('BASE64_REQUIRED') from None
  _require(base64.b64encode(data).decode('ascii')==encoded,'BASE64_CANONICAL_REQUIRED')
  total+=len(data);_require(total<=MAX_TOTAL_BYTES,'TOTAL_BYTES_BOUND')
  actual=hashlib.sha256(data).hexdigest()
  _require(len(data)==entry['size'] and actual==entry['sha256'],'FILE_HASH_OR_LENGTH_MISMATCH')
  _require(path not in policy.expected_files or actual==policy.expected_files[path],'STALE_INPUT')
  files.append(Artifact(path,data,actual))
 _require(body['kind'] not in {'cancel','ack'} or not files,'CONTROL_FILES_REFUSED')
 if body['kind'] not in {'cancel','ack'}:_require(set(policy.expected_files)<=set(f.path for f in files),'MISSING_EXPECTED_INPUT')
 return VerifiedBundle(body['kind'],body['message'],body['nonce'],tuple(files))

def pack(key,policy,kind,message,files,nonce,issued,expires):
 """Only explicitly supplied bytes; never opens a selected or arbitrary host path."""
 _key(key);_require(isinstance(policy,Policy) and isinstance(files,dict) and len(files)<=MAX_FILES,'POLICY_AND_FILES_REQUIRED')
 _require(all(isinstance(path,str) for path in files),'PATH_TYPE_REQUIRED')
 entries=[];total=0
 for path,data in sorted(files.items()):
  _path(path);_require(type(data) is bytes and len(data)<=MAX_FILE_BYTES,'FILE_BYTES_BOUND')
  total+=len(data);_require(total<=MAX_TOTAL_BYTES,'TOTAL_BYTES_BOUND')
  entries.append({'path':path,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'data':base64.b64encode(data).decode('ascii')})
 body={'version':1,'worker':policy.worker,'owner':policy.owner,'base_sha256':policy.base_sha256,'direction':policy.direction,'kind':kind,'message':message,'nonce':nonce,'issued':issued,'expires':expires,'files':entries}
 _validate(body,policy,issued);return _sign(body,key)

def _unique(pairs):
 out={}
 for key,value in pairs:
  _require(key not in out,'DUPLICATE_JSON_FIELD');out[key]=value
 return out

def unpack(raw,key,policy,now,claim):
 """Authenticate, validate all data, then atomically claim nonce before returning.

 claim(worker,direction,nonce,packet_sha256,expires) must durably return exactly
 True for the first claim only. A claim failure returns no artifact authority.
 TLS/confidentiality and durable adapter acceptance are separate prerequisites.
 """
 _key(key);_require(isinstance(policy,Policy) and callable(claim),'POLICY_AND_REPLAY_ADAPTER_REQUIRED')
 _require(type(raw) is bytes and 0<len(raw)<=MAX_PACKET_BYTES,'PACKET_BOUND')
 try:packet=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(Rejected('NONFINITE_JSON')))
 except (UnicodeError,ValueError,RecursionError):raise Rejected('JSON_REJECTED') from None
 _require(type(packet) is dict and set(packet)=={'body','mac'} and _hash(packet['mac']),'ENVELOPE_FIELDS')
 expected=hmac.new(key,DOMAIN+_canonical(packet['body']),hashlib.sha256).hexdigest()
 _require(hmac.compare_digest(packet['mac'],expected),'AUTHENTICATION_FAILED')
 _require(raw==_canonical(packet),'NONCANONICAL_ENVELOPE')
 result=_validate(packet['body'],policy,now)
 try:accepted=claim(policy.worker,policy.direction,result.nonce,hashlib.sha256(raw).hexdigest(),packet['body']['expires'])
 except Exception:raise Rejected('REPLAY_STORAGE_UNAVAILABLE') from None
 _require(accepted is True,'REPLAY_REFUSED')
 return result
