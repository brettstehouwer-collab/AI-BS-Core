"""Six correlated credential-scoped CURRENT reads; never atomic account coverage.

Only explicit paired credentials/private sink; no defaults, history, order methods
or retries. Serialized records, key UUIDs and balance observations are not account
identity or preparation/admission authority. All nested record data is PRIVATE.
"""
from dataclasses import dataclass,field
from hashlib import sha256
import hmac
import http.client
import json
import ssl
import time
import weakref

from .crypto_com_acknowledgements import _json
from .crypto_credential_preparation import (ENVIRONMENT,CredentialPreparation,TestCredentialPreparation,
    is_credential_preparation,validate_preparation,_principal,_sha)
from .crypto_current_snapshot_facts import project_current_snapshot
from .crypto_execution_controls import ControlError,digest,encode,stamp
from .personal_memory_scope import current_memory_principal

READS=(('before','private/user-balance',{}),('ordinary','private/get-open-orders',{}),
    ('advanced','private/advanced/get-open-orders',{}),('positions','private/get-positions',{}),
    ('fees','private/get-instrument-fee-rate',{'instrument_name':'CRO_USDT'}),('after','private/user-balance',{}))
_METHODS=frozenset(row[1] for row in READS)
_MAX_BYTES=262144
MAX_INTERVAL_MS=30000
MAX_AGE_MS=60000
ACTUAL_SCOPE='VERIFIED_TLS_CREDENTIAL_CURRENT_SNAPSHOT_ONLY'
TEST_SCOPE='TEST_CREDENTIAL_CURRENT_SNAPSHOT_ONLY'
_TOKEN=object()
_ISSUED=weakref.WeakSet()


@dataclass(frozen=True,init=False,eq=False)
class CurrentSnapshot:
    _payload:str=field(repr=False)

    def __init__(self,*,_token=None,**record):
        if _token is not _TOKEN:raise ControlError('reader-issued current snapshot required')
        object.__setattr__(self,'_payload',encode(record));_ISSUED.add(self)

    def to_record(self):
        """PRIVATE deep copy; includes linkable credential hashes and financial facts."""
        return json.loads(self._payload)


@dataclass(frozen=True,init=False,eq=False)
class TestCurrentSnapshot(CurrentSnapshot):
    """Injected current-state observations, never actual verified transport."""


def is_current_snapshot(value,allow_test=False):
    return (type(value) in (CurrentSnapshot,TestCurrentSnapshot) and value in _ISSUED
        and (type(value) is CurrentSnapshot and value.to_record()['scope']==ACTUAL_SCOPE
            or allow_test is True and type(value) is TestCurrentSnapshot and value.to_record()['scope']==TEST_SCOPE))


def validate_current_snapshot(value,*,principal,credential_partition_sha256,
        credential_generation_sha256,local_trial_uuid,now_ms,allow_test=False):
    if not is_current_snapshot(value,allow_test=allow_test):
        raise ControlError('issued snapshot required; serialized facts are not authority')
    principal=_principal(principal);stamp(now_ms);record=value.to_record()
    unsigned={key:item for key,item in record.items() if key!='receipt_sha256'}
    if (digest(unsigned)!=record['receipt_sha256'] or record['principal']!=principal
            or current_memory_principal()!=principal or record['environment']!=ENVIRONMENT
            or record['credential_partition_sha256']!=_sha(credential_partition_sha256)
            or record['credential_generation_sha256']!=_sha(credential_generation_sha256)
            or record['local_trial_uuid']!=local_trial_uuid
            or not 1000000000000<=record['started_ms']<=record['completed_ms']<=record['started_ms']+MAX_INTERVAL_MS
            or not record['completed_ms']<=now_ms<=record['completed_ms']+MAX_AGE_MS
            or record['exchange_account_id'] is not None or record['atomic_snapshot_verified'] is not False
            or record['full_order_family_coverage_verified'] is not False):
        raise ControlError('snapshot principal/credential/trial/freshness binding differs')
    return record


def _builtin_transport(method,raw_request):
    if method not in _METHODS:raise ControlError('fixed current read-only method required')
    connection=http.client.HTTPSConnection('api.crypto.com',port=443,timeout=5,
        context=ssl.create_default_context())
    try:
        connection.request('POST','/exchange/v1/'+method,body=raw_request,headers={'Content-Type':'application/json'})
        response=connection.getresponse()
        return response.status,response.read(_MAX_BYTES+1)
    finally:connection.close()


def read_current_snapshot(*,preparation,credential_provider,private_sink,
                          qualification_transport=None,clock_ms=None):
    """Observe fixed six methods once, preserving each original before parsing.

    Actual issued preparation uses only built-in default verified HTTPS with no
    proxy/redirect mechanism or injected clock. Test preparation requires explicit
    injected transport and can issue only a test snapshot. Sink acknowledgement
    is caller responsibility; raw signed requests/responses and final binding
    record must stay under protected local archival policy, never public/cloud.
    """
    principal=_principal(current_memory_principal())
    test=type(preparation) is TestCredentialPreparation
    if (not is_credential_preparation(preparation,allow_test=test)
            or not callable(credential_provider) or not callable(private_sink)
            or (test and not callable(qualification_transport))
            or (not test and (qualification_transport is not None or clock_ms is not None))
            or (clock_ms is not None and not callable(clock_ms))):
        raise ControlError('matching actual/test preparation and explicit reader callbacks required')
    clock=clock_ms or (lambda:time.time_ns()//1000000)
    try:
        started=clock();stamp(started)
        pair=credential_provider()
        if (type(pair) not in (tuple,list) or len(pair)!=2
                or any(type(v) is not str or not 1<=len(v)<=256 or v.strip()!=v for v in pair)):
            raise ControlError('explicit bounded credential pair required')
        key,secret=pair
        partition=digest({'provider':'CRYPTOCOM_EXCHANGE_V1','api_key':key})
        generation=hmac.new(secret.encode(),b'AI-BS/credential-preparation-generation/v1\0'+key.encode(),sha256).hexdigest()
        source=validate_preparation(preparation,principal=principal,credential_partition_sha256=partition,
            credential_generation_sha256=generation,now_ms=started,allow_test=test)
        results={};receipts=[];last=started;total_bytes=0
        for request_id,(label,method,params) in enumerate(READS,1):
            if current_memory_principal()!=principal:raise ControlError('snapshot principal changed')
            requested=clock();stamp(requested)
            if not last<=requested<=started+MAX_INTERVAL_MS:raise ControlError('current read interval differs')
            body=dict(id=str(request_id),method=method,api_key=key,params=dict(params),nonce=str(requested))
            param_text=''.join(name+params[name] for name in sorted(params))
            body['sig']=hmac.new(secret.encode(),(method+str(request_id)+key+param_text+str(requested)).encode(),sha256).hexdigest()
            raw_request=encode(body).encode()
            url='https://api.crypto.com/exchange/v1/'+method
            status,raw_response=(qualification_transport(url,raw_request) if test else _builtin_transport(method,raw_request))
            completed=clock();stamp(completed)
            if type(status) is not int or type(raw_response) is not bytes or len(raw_response)>_MAX_BYTES+1:
                raise ControlError('bounded original current response required')
            private_sink(dict(kind='PRIVATE_CURRENT_SNAPSHOT_RAW',label=label,source_url=url,request_bytes=raw_request,
                response_bytes=raw_response,status=status,started_ms=requested,completed_ms=completed))
            total_bytes+=len(raw_response)
            if (not requested<=completed<=started+MAX_INTERVAL_MS or current_memory_principal()!=principal
                    or len(raw_response)>_MAX_BYTES or total_bytes>6*_MAX_BYTES):
                raise ControlError('bounded current response/interval/principal required')
            reply=_json(raw_response)
            response_id=reply.get('id') if type(reply) is dict else None
            if (status!=200 or type(reply) is not dict or type(response_id) not in (int,str)
                    or response_id not in (request_id,str(request_id)) or reply.get('method')!=method
                    or type(reply.get('code')) is not int or reply['code']!=0 or type(reply.get('result')) is not dict):
                raise ControlError('correlated successful current read required')
            results[label]=reply['result'];last=completed
            receipts.append(dict(label=label,method=method,request_id=request_id,started_ms=requested,completed_ms=completed,
                request_sha256=sha256(raw_request).hexdigest(),response_sha256=sha256(raw_response).hexdigest()))
        facts=project_current_snapshot(results)
        completed=clock();stamp(completed)
        if not last<=completed<=started+MAX_INTERVAL_MS or current_memory_principal()!=principal:
            raise ControlError('bounded final snapshot interval/principal required')
        record=dict(schema=1,scope=TEST_SCOPE if test else ACTUAL_SCOPE,environment=ENVIRONMENT,
            principal=principal,local_trial_uuid=source['local_trial_uuid'],credential_partition_sha256=partition,
            credential_generation_sha256=generation,source_preparation_receipt_sha256=source['receipt_sha256'],
            started_ms=started,completed_ms=completed,reads=receipts,private_facts=facts,
            exchange_account_id=None,trade_account_id=None,account_identity_verified=False,
            atomic_snapshot_verified=False,full_order_family_coverage_verified=False,
            live_dispatch_enabled=False,ready_for_live=False,native_order_accepted=False,orders_sent=0)
        record['receipt_sha256']=digest(record)
        private_sink({'kind':'PRIVATE_CURRENT_SNAPSHOT_BINDING','record':json.loads(encode(record))})
        if current_memory_principal()!=principal:raise ControlError('snapshot principal changed during preservation')
        return (TestCurrentSnapshot if test else CurrentSnapshot)(_token=_TOKEN,**record)
    except Exception:
        raise ControlError('current snapshot read/correlation/private preservation failed') from None


def snapshot_status(value,allow_test=False):
    """Sanitized dated status only; never a fresh snapshot validation receipt."""
    admitted=is_current_snapshot(value,allow_test=allow_test)
    if admitted and current_memory_principal()!=value.to_record()['principal']:admitted=False
    return dict(status='current_observations_only' if admitted else 'held',
        test_evidence=admitted and type(value) is TestCurrentSnapshot,atomic_snapshot_verified=False,
        full_order_family_coverage_verified=False,account_identity_verified=False,
        native_order_accepted=False,live_dispatch_enabled=False,ready_for_live=False,orders_sent=0)
