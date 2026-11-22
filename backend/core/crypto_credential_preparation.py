"""Issued credential-scoped local preparation, never Exchange account identity.

Private records include credential-generation fingerprints and must stay under the
caller's protected sink/archive policy. Public status contains no identifiers or
fingerprints. No cash, fee, fill, coverage, runtime or dispatch authority is issued.
"""
from dataclasses import dataclass, field
from hashlib import sha256
import hmac
import time
from uuid import UUID
import weakref

from .crypto_execution_controls import ControlError, digest, stamp
from .crypto_trial_binding import read_current_account, is_current_account_observation
from .personal_memory_scope import current_memory_principal

ENVIRONMENT='CRYPTOCOM_EXCHANGE_V1_PRODUCTION'
ACTUAL_SCOPE='VERIFIED_CREDENTIAL_PREPARATION_ONLY'
TEST_SCOPE='TEST_CREDENTIAL_PREPARATION_ONLY'
MAX_AGE_MS=60000
_TOKEN=object()
_ISSUED=weakref.WeakSet()


@dataclass(frozen=True,init=False,eq=False)
class CredentialPreparation:
    """Process-issued capability. to_record() is PRIVATE, not public status."""
    _record: tuple=field(repr=False)

    def __init__(self,*,_token=None,**record):
        if _token is not _TOKEN:raise ControlError('reader-issued credential preparation required')
        object.__setattr__(self,'_record',tuple(sorted(record.items())))
        _ISSUED.add(self)

    def to_record(self):return dict(self._record)


@dataclass(frozen=True,init=False,eq=False)
class TestCredentialPreparation(CredentialPreparation):
    """Injected-transport evidence only, never an actual verified credential read."""


def is_credential_preparation(value,allow_test=False):
    return (type(value) in (CredentialPreparation,TestCredentialPreparation) and value in _ISSUED
        and (type(value) is CredentialPreparation and value.to_record()['scope']==ACTUAL_SCOPE
            or allow_test is True and type(value) is TestCredentialPreparation and value.to_record()['scope']==TEST_SCOPE))


def _principal(value):
    if type(value) is not str or not 1<=len(value)<=512 or any(ord(c)<32 or ord(c)==127 for c in value):
        raise ControlError('verified preparation principal required')
    return value


def _sha(value):
    if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ControlError('private canonical credential binding required')
    return value


def validate_preparation(value,*,principal,credential_partition_sha256,
                         credential_generation_sha256,now_ms,allow_test=False):
    """Validate an issued fresh capability against trusted private expected scope."""
    if not is_credential_preparation(value,allow_test=allow_test):
        raise ControlError('issued credential preparation required; serialized records are not authority')
    principal=_principal(principal);stamp(now_ms)
    record=value.to_record();unsigned={key:item for key,item in record.items() if key!='receipt_sha256'}
    if (record['receipt_sha256']!=digest(unsigned) or current_memory_principal()!=principal
            or record['principal']!=principal or record['environment']!=ENVIRONMENT
            or record['credential_partition_sha256']!=_sha(credential_partition_sha256)
            or record['credential_generation_sha256']!=_sha(credential_generation_sha256)
            or record['exchange_account_id'] is not None or record['account_identity_verified'] is not False
            or not 1000000000000<=record['started_ms']<=record['completed_ms']<=record['started_ms']+10000
            or not record['completed_ms']<=now_ms<=record['completed_ms']+MAX_AGE_MS):
        raise ControlError('credential/principal/generation/freshness preparation binding differs')
    return record


def read_credential_preparation(*,local_trial_uuid,credential_provider,private_sink,
                                qualification_transport=None,clock_ms=None):
    """Read fixed current key metadata using one supplied pair; preserve privately.

    Credential partition is the existing API-key identity hash. Generation is a
    domain-separated HMAC of that same key using its secret, so a rotated secret
    changes generation without storing the secret. Neither digest is public or
    account identity. Reopening a serialized record cannot recreate this capability.
    """
    principal=_principal(current_memory_principal())
    try:
        if type(local_trial_uuid) is not str or str(UUID(local_trial_uuid))!=local_trial_uuid:
            raise ValueError('invalid local UUID')
    except (ValueError,AttributeError):
        raise ControlError('explicit canonical LOCAL trial UUID required') from None
    if not callable(credential_provider) or not callable(private_sink):
        raise ControlError('explicit credential and protected sink callbacks required')
    binding={}
    def paired_provider():
        if binding:raise ControlError('credential provider must be invoked once')
        pair=credential_provider()
        if (type(pair) not in (tuple,list) or len(pair)!=2
                or any(type(v) is not str or not 1<=len(v)<=256 or v.strip()!=v for v in pair)):
            raise ControlError('explicit bounded credential pair required')
        key,secret=pair
        binding['credential_partition_sha256']=digest({'provider':'CRYPTOCOM_EXCHANGE_V1','api_key':key})
        binding['credential_generation_sha256']=hmac.new(secret.encode(),
            b'AI-BS/credential-preparation-generation/v1\0'+key.encode(),sha256).hexdigest()
        return pair
    try:
        observation=read_current_account(credential_provider=paired_provider,private_sink=private_sink,
            qualification_transport=qualification_transport,clock_ms=clock_ms)
        if not is_current_account_observation(observation,qualification=qualification_transport is not None):
            raise ControlError('issued current metadata observation required')
        metadata=observation.to_record()
        test=qualification_transport is not None
        if (metadata['scope']!=('QUALIFICATION_ONLY' if test else 'VERIFIED_TLS_CURRENT_KEY_METADATA')
                or metadata['credential_partition_sha256']!=binding.get('credential_partition_sha256')
                or current_memory_principal()!=principal):
            raise ControlError('current metadata credential scope differs')
        now_ms=(clock_ms or (lambda:time.time_ns()//1000000))();stamp(now_ms)
        if not observation.completed_ms<=now_ms<=observation.completed_ms+MAX_AGE_MS:
            raise ControlError('fresh current credential metadata required')
        record=dict(schema=1,scope=TEST_SCOPE if test else ACTUAL_SCOPE,environment=ENVIRONMENT,
            principal=principal,local_trial_uuid=local_trial_uuid,source_method=metadata['source_method'],
            started_ms=observation.started_ms,completed_ms=observation.completed_ms,
            credential_partition_sha256=binding['credential_partition_sha256'],
            credential_generation_sha256=binding['credential_generation_sha256'],
            request_sha256=metadata['request_sha256'],response_sha256=metadata['response_sha256'],
            metadata_receipt_sha256=observation.receipt_sha256,exchange_account_id=None,trade_account_id=None,
            account_identity_verified=False,live_dispatch_enabled=False,ready_for_live=False,
            native_order_accepted=False,orders_sent=0)
        record['receipt_sha256']=digest(record)
        private_sink({'kind':'PRIVATE_CREDENTIAL_PREPARATION_BINDING','record':dict(record)})
        if current_memory_principal()!=principal:raise ControlError('preparation principal changed')
        return (TestCredentialPreparation if test else CredentialPreparation)(_token=_TOKEN,**record)
    except Exception:
        raise ControlError('credential preparation read/private binding failed') from None


def preparation_status(value,allow_test=False):
    """Sanitized status only; does not confer freshness or preparation authority."""
    admitted=is_credential_preparation(value,allow_test=allow_test)
    if admitted and current_memory_principal()!=value.to_record()['principal']:admitted=False
    return dict(status='local_preparation_only' if admitted else 'held',
        test_evidence=admitted and type(value) is TestCredentialPreparation,
        exchange_account_identity_verified=False,account_identity_verified=False,
        live_dispatch_enabled=False,ready_for_live=False,native_order_accepted=False,orders_sent=0)
