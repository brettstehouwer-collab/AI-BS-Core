"""Protected durable trial-store lifecycle; no live financial dispatch authority.

A single accounting DB retains the qualified coordinator, allocations and latch.
Creation/reopening requires an explicit root lease and exclusive lifetime lock.
Current key metadata is not Exchange account identity; production admission stays
held until an issued observation proves that separate identity requirement.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import threading
import json
import os
import time
from uuid import UUID, uuid4

from security.crypto_trial_root import TrialRootLease
from .coding_journal import write_json_record
from .crypto_com_acknowledgements import _json as _strict_json
from .coding_locks import record_lock
from .crypto_execution_controls import ControlError, OfflineExecutionCoordinator, digest, encode, number, text_decimal
from .crypto_reinvestment import OfflineReinvestment
from .crypto_trial_admission import OfflineTrialAdmission
from .crypto_trial_binding import is_current_account_observation
from .crypto_trial_budget import _validated_baseline
from .crypto_trial_projection import _decoded

_REGISTRY = {}
_REGISTRY_LOCK = threading.RLock()
_BOOTSTRAP = ContextVar('trial_store_bootstrap',default=None)
_DATABASE = 'accounting.sqlite3'


def _key(path):
    return str(Path(path).absolute()).casefold()


def _entry(path):
    with _REGISTRY_LOCK:
        entry = _REGISTRY.get(_key(path))
    if entry is None or entry['closed']:
        raise ControlError('runtime owner is closed or absent')
    return entry


class _DurableCoordinator(OfflineTrialAdmission):
    def __init__(self, path):
        entry = _entry(path)
        self._runtime_token = entry['token']
        if entry['base_init']:
            OfflineExecutionCoordinator.__init__(self,path)
        else:
            super().__init__(path)

    @staticmethod
    def _path(path, *, exists):
        path = Path(path).absolute();entry = _entry(path)
        with entry['guard']:
            if (entry['closed'] or path != entry['lease'].path/_DATABASE
                    or (not entry['ready'] and _BOOTSTRAP.get() is not entry['token'])):
                raise ControlError('registered runtime root/initialization differs')
            entry['lease'].validate()
            if exists and entry['db_identity'] is None:
                if _BOOTSTRAP.get() is not entry['token']:
                    raise ControlError('missing runtime database identity')
                entry['db_identity'] = entry['lease'].pin_file(_DATABASE)
            entry['lease'].validate_file(_DATABASE,entry['db_identity'] if exists else None,exists=exists)
            return path

    @contextmanager
    def _tx(self):
        entry = _entry(self.path)
        with entry['guard']:
            if entry['closed'] or self._runtime_token is not entry['token']:
                raise ControlError('stale runtime coordinator cannot operate')
            with super()._tx() as db:
                yield db


def _locator(root):
    with (Path(root)/'store.json').open('rb') as stream:
        raw = stream.read(32769)
    if len(raw)>32768:
        raise ControlError('bounded runtime locator required')
    envelope = _strict_json(raw)
    if (type(envelope) is not dict or envelope.keys()!={'record','sha256'}
            or digest(envelope['record'])!=envelope['sha256']
            or raw!=json.dumps(envelope,indent=2,allow_nan=False).encode('utf-8')):
        raise ControlError('runtime locator fingerprint differs')
    return envelope['record']


def _publish(root, record, *, exclusive=False):
    write_json_record(Path(root)/'store.json',{'record':record,'sha256':digest(record)},exclusive=exclusive)


class PersistentTrialRuntime:
    """Own one stable protected store, preserving evidence on every refusal."""
    def __init__(self):
        self._entry = None;self._lease = None;self._lock = None;self._closed = False;self._lock_entered = False

    @property
    def root(self):return self._root

    @property
    def store_uuid(self):return self._record['store_uuid']

    def _own(self, lease, *, ready=False, db_identity=None):
        self._lease=lease;self._root=lease.path
        try:
            with (self.root/'runtime.lock').open('xb') as stream:
                stream.write(b'\0');stream.flush();os.fsync(stream.fileno())
        except FileExistsError:
            pass
        lease.pin_file('runtime.lock')
        self._lock=record_lock(self.root/'runtime.lock');self._lock.__enter__();self._lock_entered=True
        entry=dict(lease=lease,guard=threading.RLock(),token=object(),closed=False,
                   ready=ready,base_init=not ready,db_identity=db_identity)
        with _REGISTRY_LOCK:
            if _key(self.root/_DATABASE) in _REGISTRY:
                raise ControlError('runtime already owned in this process')
            _REGISTRY[_key(self.root/_DATABASE)]=entry
        self._entry=entry

    @classmethod
    def create(cls, parent, name, *, observation, baseline, seed_budget_usdt,
               max_entry_budget_usdt, daily_loss_budget_usdt, qualification=False,
               limits=None, initial_cash_usdt=None):
        owner=cls()
        try:
            if type(qualification) is not bool or not is_current_account_observation(observation,qualification=qualification):
                raise ControlError('issued current metadata observation required')
            observation_record=observation.to_record();baseline=_validated_baseline(baseline)
            if not qualification:
                now_ms=time.time_ns()//1000000
                if not now_ms-60000<=observation.started_ms<=observation.completed_ms<=now_ms+5000:
                    raise ControlError('current wall-clock metadata observation required')
            if (not qualification and observation_record.get('account_identity_verified') is not True):
                raise ControlError('current key metadata does not prove Exchange account identity')
            if (observation.account!=baseline['account'] or not observation.completed_ms<=baseline['started_ms']<=observation.completed_ms+60000):
                raise ControlError('baseline must bind the same fresh observed identity')
            seed=number(seed_budget_usdt);cash=number(initial_cash_usdt) if initial_cash_usdt is not None else seed
            if seed<=0 or cash<seed:
                raise ControlError('explicit positive seed and sufficient qualification cash required')
            owner._own(TrialRootLease.create(parent,name))
            entry=owner._entry;token=_BOOTSTRAP.set(entry['token'])
            try:
                record=dict(schema=1,scope='DURABLE_TRIAL_MIRROR_NO_DISPATCH',state='CREATING',
                    store_uuid=str(uuid4()),account=observation.account,qualification=qualification,
                    root_identity=owner._lease.identity,database_identity=None,broker_sid=owner._lease.broker_sid,
                    observation=observation_record,baseline_sha256=baseline['baseline_sha256'],
                    initial_cash_usdt=text_decimal(cash))
                _publish(owner.root,record,exclusive=True)
                base=_DurableCoordinator.create(owner.root/_DATABASE,account=observation.account,quote='USDT',cash=text_decimal(cash),limits=limits)
                OfflineReinvestment.create(base,baseline,seed_budget_usdt=seed_budget_usdt,max_entry_budget_usdt=max_entry_budget_usdt)
                entry['base_init']=False
                coordinator=_DurableCoordinator.register(base,daily_loss_budget_usdt=daily_loss_budget_usdt)
                record=dict(record,state='READY',database_identity=entry['db_identity'])
                with coordinator._tx() as db:
                    db.execute('CREATE TABLE aibs_trial_runtime_binding(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL,fingerprint TEXT NOT NULL)')
                    db.execute('INSERT INTO aibs_trial_runtime_binding VALUES(1,?,?)',(encode(record),digest(record)))
                _publish(owner.root,record)
                owner._lease.pin_file('store.json');entry['ready']=True
                owner._record=record;owner.coordinator=coordinator;owner.reinvestment=OfflineReinvestment(coordinator)
                owner.status()
            finally:
                _BOOTSTRAP.reset(token)
            return owner
        except BaseException as exc:
            owner.close()
            if isinstance(exc,ControlError):raise
            raise ControlError('durable trial creation refused: '+type(exc).__name__) from exc

    @classmethod
    def open(cls, root, *, expected_store_uuid, expected_account, qualification=False):
        owner=cls()
        try:
            if type(expected_store_uuid) is not str or str(UUID(expected_store_uuid))!=expected_store_uuid or type(qualification) is not bool:
                raise ControlError('explicit canonical store UUID and mode required')
            lease=TrialRootLease.open_for_locator(root)
            owner._lease=lease
            lease.pin_file('store.json');record=_locator(lease.path)
            if record.get('state')!='READY':
                raise ControlError('unfinished creation retained; explicit recovery required')
            if (record.get('root_identity')!=lease.identity or record.get('schema')!=1
                    or record.get('scope')!='DURABLE_TRIAL_MIRROR_NO_DISPATCH'
                    or record.get('store_uuid')!=expected_store_uuid or record.get('account')!=expected_account
                    or record.get('qualification') is not qualification or record.get('broker_sid')!=lease.broker_sid):
                raise ControlError('runtime locator/account/store/mode differs')
            obs=record['observation'];unsigned={key:value for key,value in obs.items() if key!='receipt_sha256'}
            if (digest(unsigned)!=obs.get('receipt_sha256') or obs.get('account')!=expected_account
                    or (not qualification and obs.get('account_identity_verified') is not True)):
                raise ControlError('stored observation binding differs or remains unqualified')
            lease.validate_file(_DATABASE,record['database_identity']);lease.pin_file(_DATABASE)
            owner._own(lease,ready=True,db_identity=record['database_identity'])
            owner._record=record;owner.coordinator=_DurableCoordinator(owner.root/_DATABASE)
            owner.reinvestment=OfflineReinvestment(owner.coordinator);owner.status()
            return owner
        except BaseException as exc:
            owner.close()
            if isinstance(exc,ControlError):raise
            raise ControlError('durable trial reopening refused: '+type(exc).__name__) from exc

    def status(self):
        if self._closed or self._entry is None:
            raise ControlError('runtime owner is closed')
        with self.coordinator._tx() as db:
            row=db.execute('SELECT payload,fingerprint FROM aibs_trial_runtime_binding WHERE id=1').fetchone()
            if row is None or row['payload']!=encode(self._record) or row['fingerprint']!=digest(self._record):
                raise ControlError('runtime database/locator binding differs')
            if _locator(self.root)!=self._record:
                raise ControlError('immutable pinned runtime locator differs')
        return dict(scope='DURABLE_TRIAL_MIRROR_NO_DISPATCH',store_uuid=self.store_uuid,
            account_metadata_bound=True,exchange_account_identity_verified=False,
            production_store_admitted=False,exchange_coverage_verified=False,
            observation_scope=self._record['observation']['scope'],live_dispatch_enabled=False,
            native_protection_qualified=False,ready_for_live=False,orders_sent=0)

    def close(self):
        if self._closed:return
        entry=self._entry
        guard=entry['guard'] if entry is not None else threading.RLock()
        with guard:
            self._closed=True
            if entry is not None:
                entry['closed']=True
                with _REGISTRY_LOCK:
                    if _REGISTRY.get(_key(self.root/_DATABASE)) is entry:
                        del _REGISTRY[_key(self.root/_DATABASE)]
            try:
                if self._lock_entered:self._lock.__exit__(None,None,None);self._lock_entered=False
            finally:
                if self._lease is not None:self._lease.close()

    def __enter__(self):self.status();return self
    def __exit__(self,*_):self.close()
