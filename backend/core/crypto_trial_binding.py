"""Read-only current-key metadata observation, never trading-account identity.

Official get-accounts calls this_account.uuid 'UUID of the API key'. No mapping to
trade account IDs is inferred. Injected transports always yield qualification
evidence. Same-process Python mutation/monkeypatch is not a security boundary.
"""
from dataclasses import dataclass, field
from hashlib import sha256
import hmac
import http.client
import json
import ssl
import time
from uuid import UUID
import weakref

from .crypto_execution_controls import ControlError, digest, encode, stamp

METHOD='private/get-accounts'
HOST='api.crypto.com'
PATH='/exchange/v1/'+METHOD
URL='https://'+HOST+PATH
DOC_URL='https://exchange-developer.crypto.com/exchange/v1/docs/api/rest/private-get-accounts'
_MINT=object()
_ISSUED=weakref.WeakSet()
_MAX_BYTES=262144


@dataclass(frozen=True, init=False, eq=False)
class CurrentAccountObservation:
    """Opaque issued metadata capability; serialization alone cannot recreate it."""
    _record: tuple = field(repr=False)

    def __init__(self, *, _token=None, **record):
        if _token is not _MINT:
            raise ControlError('reader-issued observation required')
        object.__setattr__(self,'_record',tuple(sorted(record.items())))
        _ISSUED.add(self)

    @property
    def account(self):return dict(self._record)['account']
    @property
    def account_id(self):return dict(self._record)['account_id']
    @property
    def started_ms(self):return dict(self._record)['started_ms']
    @property
    def completed_ms(self):return dict(self._record)['completed_ms']
    @property
    def receipt_sha256(self):return dict(self._record)['receipt_sha256']
    @property
    def scope(self):return dict(self._record)['scope']

    def to_record(self):return dict(self._record)


@dataclass(frozen=True, init=False, eq=False)
class QualificationAccountObservation(CurrentAccountObservation):
    """Synthetic/injected evidence only; never authenticates an Exchange account."""


def is_current_account_observation(value, *, qualification=False):
    return (type(value) in (CurrentAccountObservation,QualificationAccountObservation)
        and value in _ISSUED and (value.scope=='VERIFIED_TLS_CURRENT_KEY_METADATA'
            or (qualification is True and value.scope=='QUALIFICATION_ONLY')))


def _uuid(value):
    try:
        if type(value) is not str or str(UUID(value))!=value:
            raise ValueError('invalid UUID')
    except (ValueError,AttributeError):
        raise ControlError('canonical current metadata UUID required') from None
    return value


def _interval(started,completed):
    stamp(started);stamp(completed)
    if not 1000000000000<=started<=completed<=started+10000:
        raise ControlError('bounded current millisecond observation interval required')


def _issue(kind, record):
    record=dict(record,trade_account_id=None,live_dispatch_enabled=False,
        ready_for_live=False,native_order_accepted=False,orders_sent=0)
    record['receipt_sha256']=digest(record)
    return kind(_token=_MINT,**record)


def qualification_account_observation(*,account_id,started_ms,completed_ms):
    """Explicit synthetic account fixture; not read from caller JSON/auth flags."""
    account_id=_uuid(account_id);_interval(started_ms,completed_ms)
    return _issue(QualificationAccountObservation,dict(schema=1,scope='QUALIFICATION_ONLY',
        account='cryptocom-exchange:'+account_id,account_id=account_id,key_metadata_uuid=None,
        account_identity_verified=False,started_ms=started_ms,completed_ms=completed_ms,
        source_method='SYNTHETIC_QUALIFICATION_FACTORY',request_sha256=digest({}),
        response_sha256=digest({'synthetic_account_id':account_id}),
        credential_partition_sha256=digest({'scope':'QUALIFICATION_ONLY'}),docs_url=DOC_URL))


def _builtin_transport(url, request_bytes):
    if url!=URL:
        raise ControlError('fixed metadata endpoint required')
    # HTTPSConnection does not consult proxy environment variables or follow redirects.
    connection=http.client.HTTPSConnection(HOST,port=443,timeout=10,
        context=ssl.create_default_context())
    try:
        connection.request('POST',PATH,body=request_bytes,headers={'Content-Type':'application/json'})
        response=connection.getresponse()
        return response.status,response.read(_MAX_BYTES+1)
    finally:
        connection.close()


def _json_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ControlError('duplicate metadata JSON key')
        result[key]=value
    return result


def read_current_account(*,credential_provider,private_sink,request_id=1,
                         qualification_transport=None,clock_ms=None):
    """Read metadata once with explicitly supplied credentials and private byte sink.

    Built-in transport verifies TLS host with system roots, fixed endpoint, no
    proxies or redirects. It observes current KEY metadata only, not account
    identity, balances, order-family coverage or protection. No retries occur.
    Explicit sink must durably preserve signed request/response bytes; its return
    constitutes caller acknowledgement. Failure prevents observation issuance.
    """
    if (type(request_id) is not int or not 0<=request_id<=9223372036854775807
            or not callable(credential_provider) or not callable(private_sink)
            or (qualification_transport is not None and not callable(qualification_transport))
            or (clock_ms is not None and (qualification_transport is None or not callable(clock_ms)))):
        raise ControlError('explicit bounded reader callbacks/request ID required')
    clock=clock_ms or (lambda:time.time_ns()//1000000)
    try:
        started=clock();_interval(started,started)
        credentials=credential_provider()
        if (type(credentials) not in (tuple,list) or len(credentials)!=2
                or any(type(v) is not str or not 1<=len(v)<=256 or v.strip()!=v for v in credentials)):
            raise ControlError('explicit bounded credentials required')
        api_key,secret=credentials
        body=dict(id=str(request_id),method=METHOD,api_key=api_key,params={},nonce=str(started))
        payload=METHOD+str(request_id)+api_key+str(started)
        body['sig']=hmac.new(secret.encode(),payload.encode(),sha256).hexdigest()
        request_bytes=encode(body).encode()
        partition=digest({'provider':'CRYPTOCOM_EXCHANGE_V1','api_key':api_key})
        status,response_bytes=(qualification_transport or _builtin_transport)(URL,request_bytes)
        completed=clock();_interval(started,completed)
        if type(status) is not int or type(response_bytes) is not bytes or len(response_bytes)>_MAX_BYTES:
            raise ControlError('bounded raw metadata response required')
        private_sink(dict(request_bytes=request_bytes,response_bytes=response_bytes,
            status=status,started_ms=started,completed_ms=completed,source_url=URL))
    except Exception:
        raise ControlError('current metadata transport/credential/private preservation failed') from None
    try:
        response=json.loads(response_bytes,object_pairs_hook=_json_object,
            parse_constant=lambda value:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
        response_id=response.get('id') if type(response) is dict else None
        if (status!=200 or type(response) is not dict
                or type(response_id) not in (int,str) or response_id not in (request_id,str(request_id))
                or response.get('method')!=METHOD or type(response.get('code')) is not int
                or response['code']!=0):
            raise ControlError('correlated successful current metadata response required')
        current=response['result']['this_account']
        metadata_uuid=_uuid(current['uuid'])
        if current.get('hierarchy') not in ('MASTER','SUB_ACCOUNT'):
            raise ControlError('documented current key hierarchy required')
    except Exception:
        raise ControlError('invalid or uncorrelated current key metadata response') from None
    qualified=qualification_transport is not None
    return _issue(QualificationAccountObservation if qualified else CurrentAccountObservation,
        dict(schema=1,scope='QUALIFICATION_ONLY' if qualified else 'VERIFIED_TLS_CURRENT_KEY_METADATA',
            account='cryptocom-key-metadata:'+metadata_uuid,account_id=None,
            key_metadata_uuid=metadata_uuid,account_identity_verified=False,
            started_ms=started,completed_ms=completed,source_method=METHOD,
            request_sha256=sha256(request_bytes).hexdigest(),response_sha256=sha256(response_bytes).hexdigest(),
            credential_partition_sha256=partition,docs_url=DOC_URL))
