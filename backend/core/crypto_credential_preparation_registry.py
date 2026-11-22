"""Protected metadata selection only; no accounting, funds, runtime or dispatch.

Real preparation has one fixed server-selected index. Explicit TEST capabilities
may use owned fixture roots. Windows user/System/Administrators remain trusted.
"""
import json
from pathlib import Path
from threading import RLock

from security.crypto_trial_root import TrialRootLease
from .coding_locks import record_lock
from .coding_journal import write_json_record
from .crypto_com_acknowledgements import _json
from .crypto_execution_controls import ControlError, digest
from .personal_memory_scope import current_memory_principal

_CANONICAL_ROOT=Path('C:/AI-BS/saved_data/crypto_credential_preparation_registry')
_ACTUAL='VERIFIED_CREDENTIAL_PREPARATION_ONLY'
_TEST='TEST_CREDENTIAL_PREPARATION_ONLY'
_FIELDS={'schema','scope','root_identity','broker_sid','preparation'}


def _principal():
    principal=current_memory_principal()
    if principal is None:raise PermissionError('Verified principal required')
    return principal


def _canonical(path):return Path(path).absolute()==_CANONICAL_ROOT


def _admit_path(path,record,allow_test):
    if type(allow_test) is not bool:raise ControlError('Explicit test mode required')
    if record.get('scope')==_ACTUAL:
        if allow_test or not _canonical(path):raise ControlError('Real preparation requires canonical index')
    elif record.get('scope')!=_TEST or not allow_test or _canonical(path):
        raise ControlError('Explicit TEST capability required for custom index')


def _fresh(preparation,partition,generation,now_ms,allow_test):
    from .crypto_credential_preparation import validate_preparation
    return validate_preparation(preparation,principal=_principal(),
        credential_partition_sha256=partition,credential_generation_sha256=generation,
        now_ms=now_ms,allow_test=allow_test)


class CredentialPreparationRegistry:
    def __init__(self):
        self._lease=None;self._lock_context=None;self._record=None
        self._closed=True;self._guard=RLock();self._historical=False

    @property
    def path(self):return self._lease.path

    @property
    def identity(self):return list(self._lease.identity)

    def _own_lock(self,*,create):
        path=self.path/'registry.lock'
        if create:
            with path.open('xb'):pass
        self._lease.pin_file('registry.lock')
        self._lock_context=record_lock(path)
        try:self._lock_context.__enter__()
        except BaseException:
            self._lock_context=None;raise
        self._closed=False

    def _read(self):
        self._lease.validate();self._lease.pin_file('selection.json')
        with (self.path/'selection.json').open('rb') as stream:raw=stream.read(32769)
        if len(raw)>32768:raise ControlError('Bounded selection required')
        envelope=_json(raw)
        if (type(envelope) is not dict or envelope.keys()!={'record','sha256'}
                or type(envelope['record']) is not dict or envelope['record'].keys()!=_FIELDS
                or digest(envelope['record'])!=envelope['sha256']
                or raw!=json.dumps(envelope,indent=2,allow_nan=False).encode()):
            raise ControlError('Canonical immutable selection required')
        record=envelope['record'];cap=record['preparation']
        if (type(record['schema']) is not int or record['schema']!=1
                or record['scope']!='CREDENTIAL_PREPARATION_METADATA_INDEX'
                or record['root_identity']!=self.identity or record['broker_sid']!=self._lease.broker_sid
                or type(cap) is not dict or cap.get('scope') not in (_ACTUAL,_TEST)
                or cap.get('exchange_account_id') is not None or cap.get('account_identity_verified') is not False
                or cap.get('principal')!=_principal()
                or digest({k:v for k,v in cap.items() if k!='receipt_sha256'})!=cap.get('receipt_sha256')):
            if type(cap) is dict and cap.get('principal')!=_principal():
                raise PermissionError('Selected preparation owner differs')
            raise ControlError('Selection identity or capability integrity differs')
        return record

    @classmethod
    def create(cls,parent,name,*,preparation,credential_partition_sha256,
               credential_generation_sha256,now_ms,allow_test=False):
        _principal()
        cap=_fresh(preparation,credential_partition_sha256,credential_generation_sha256,now_ms,allow_test)
        target=Path(parent)/name;_admit_path(target,cap,allow_test)
        owner=cls()
        try:
            owner._lease=TrialRootLease.create(parent,name);owner._own_lock(create=True)
            record=dict(schema=1,scope='CREDENTIAL_PREPARATION_METADATA_INDEX',root_identity=owner.identity,
                broker_sid=owner._lease.broker_sid,preparation=cap)
            write_json_record(owner.path/'selection.json',{'record':record,'sha256':digest(record)},exclusive=True)
            owner._record=record
            if owner._read()!=record:raise ControlError('Selection readback differs')
            return owner
        except BaseException:
            owner.close();raise

    @classmethod
    def open(cls,path,*,expected_identity,allow_test=False,historical_review=False):
        _principal()
        if type(historical_review) is not bool:raise ControlError('Explicit historical mode required')
        owner=cls()
        try:
            owner._lease=TrialRootLease.open(path,expected_identity=expected_identity)
            owner._own_lock(create=False);owner._record=owner._read()
            if not historical_review:_admit_path(owner.path,owner._record['preparation'],allow_test)
            owner._historical=historical_review
            return owner
        except BaseException:
            owner.close();raise

    def _validate(self):
        _principal()
        if self._closed:raise ControlError('Preparation index owner is closed')
        if self._read()!=self._record:raise ControlError('Immutable selection changed')

    def review(self):
        with self._guard:
            self._validate()
            return dict(scope='METADATA_ONLY_CREDENTIAL_PREPARATION_INDEX',status='stored_preparation',
                test_only=self._record['preparation']['scope']==_TEST,fresh_authority=False,
                exchange_account_id=None,account_identity_verified=False,financial_runtime_created=False,
                live_dispatch_enabled=False,ready_for_live=False,orders_sent=0)

    def register(self,*,preparation,credential_partition_sha256,credential_generation_sha256,now_ms,allow_test=False):
        with self._guard:
            self._validate()
            if self._historical:raise ControlError('Historical review grants no preparation authority')
            cap=_fresh(preparation,credential_partition_sha256,credential_generation_sha256,now_ms,allow_test)
            _admit_path(self.path,cap,allow_test)
            old=self._record['preparation']
            keys=('principal','local_trial_uuid','credential_partition_sha256','credential_generation_sha256','scope','environment')
            if any(cap.get(key)!=old.get(key) for key in keys):
                raise ControlError('Selected preparation cannot rotate, reassign or reset')
            return self.review()

    def close(self):
        with self._guard:
            self._closed=True
            try:
                if self._lock_context is not None:
                    context=self._lock_context;self._lock_context=None;context.__exit__(None,None,None)
            finally:
                if self._lease is not None:self._lease.close()

    def __enter__(self):self._validate();return self
    def __exit__(self,*_):self.close()
