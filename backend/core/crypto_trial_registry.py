"""Principal-scoped server-selected runtime status; inert until explicitly used.

The private immutable descriptor contains metadata only, never balances, keys or
an execution request. Qualification stores remain qualification stores. Current
Windows user/Administrators are trusted; this is not hostile same-user isolation.
"""
import json
from pathlib import Path
from uuid import UUID
import weakref

from security.crypto_trial_root import TrialRootLease
from .coding_journal import write_json_record
from .crypto_com_acknowledgements import _json
from .crypto_execution_controls import ControlError, digest
from .crypto_trial_runtime_store import PersistentTrialRuntime
from .personal_memory_scope import current_memory_principal


_DEFAULT_ROOT=Path('C:/AI-BS/saved_data/crypto_trial_registry')
_DEFAULT=None
_FIELDS=frozenset(('schema','scope','root_identity','principal','runtime_root',
    'store_uuid','account','qualification'))


def _answer(status,*,entry_held=False):
    from .crypto_trial_status_contract import trial_status
    return trial_status(status,entry_held=entry_held)


def _read(lease):
    lease.pin_file('registry.json')
    with (lease.path/'registry.json').open('rb') as stream:
        raw=stream.read(32769)
    if len(raw)>32768:
        raise ControlError('bounded registry descriptor required')
    envelope=_json(raw)
    if (type(envelope) is not dict or envelope.keys()!={'record','sha256'}
            or type(envelope['record']) is not dict or envelope['record'].keys()!=_FIELDS
            or digest(envelope['record'])!=envelope['sha256']
            or raw!=json.dumps(envelope,indent=2,allow_nan=False).encode('utf-8')):
        raise ControlError('canonical private registry descriptor required')
    record=envelope['record']
    if (type(record['schema']) is not int or record['schema']!=1
            or record['scope']!='CURRENT_TRIAL_RUNTIME_REGISTRY'
            or record['root_identity']!=lease.identity or type(record['principal']) is not str
            or type(record['runtime_root']) is not str or not Path(record['runtime_root']).is_absolute()
            or type(record['qualification']) is not bool or type(record['account']) is not str
            or not record['account'] or type(record['store_uuid']) is not str
            or str(UUID(record['store_uuid']))!=record['store_uuid']):
        raise ControlError('registry metadata binding differs')
    lease.validate()
    return record


def _verified_status(runtime,record):
    if (runtime.root!=Path(record['runtime_root']) or runtime.store_uuid!=record['store_uuid']
            or runtime._record.get('account')!=record['account']
            or runtime._record.get('qualification') is not record['qualification']):
        raise ControlError('selected runtime identity differs')
    state=runtime.status();entry=runtime.coordinator.entry_status()
    if (type(state) is not dict or state.get('scope')!='DURABLE_TRIAL_MIRROR_NO_DISPATCH'
            or state.get('account_metadata_bound') is not True
            or any(state.get(k) is not False for k in ('exchange_account_identity_verified',
                'production_store_admitted','exchange_coverage_verified','native_protection_qualified',
                'live_dispatch_enabled','ready_for_live'))
            or type(state.get('orders_sent')) is not int or state['orders_sent']!=0
            or type(entry) is not dict or entry.get('scope')!='OFFLINE_DAILY_ENTRY_ADMISSION'
            or entry.get('local_cutoff_enforced') is not True or type(entry.get('entry_held')) is not bool
            or any(entry.get(k) is not False for k in ('live_daily_cutoff_enforced',
                'native_protection_qualified','guaranteed_maximum_loss','live_dispatch_enabled','ready_for_live'))
            or type(entry.get('orders_sent')) is not int or entry['orders_sent']!=0):
        raise ControlError('selected runtime status is not qualified held state')
    return _answer('qualification' if record['qualification'] else 'held',entry_held=entry['entry_held'])


class TrialRuntimeRegistry:
    def __init__(self,root=None,active_runtime=None):
        self._root=Path(root) if root is not None else _DEFAULT_ROOT
        self._active=weakref.ref(active_runtime) if active_runtime is not None else None

    @property
    def root(self):
        """Local infrastructure only; never returned by status()."""
        return self._root

    @classmethod
    def create(cls,parent,name,*,runtime,principal):
        current=current_memory_principal()
        if current is None or type(principal) is not str or current!=principal:
            raise PermissionError('matching verified principal required')
        if not isinstance(runtime,PersistentTrialRuntime) or runtime._closed:
            raise ControlError('active server-selected runtime required')
        # Validate the underlying owner rather than flattening unsafe flags.
        runtime_record=runtime._record
        descriptor=dict(schema=1,scope='CURRENT_TRIAL_RUNTIME_REGISTRY',root_identity=None,
            principal=principal,runtime_root=str(runtime.root),store_uuid=runtime.store_uuid,
            account=runtime_record['account'],qualification=runtime_record['qualification'])
        _verified_status(runtime,descriptor)
        with TrialRootLease.create(parent,name) as lease:
            descriptor['root_identity']=lease.identity
            write_json_record(lease.path/'registry.json',{'record':descriptor,'sha256':digest(descriptor)},exclusive=True)
            if _read(lease)!=descriptor:
                raise ControlError('registry descriptor readback differs')
            return cls(lease.path,active_runtime=runtime)

    def status(self):
        principal=current_memory_principal()
        if principal is None:
            return _answer('denied')
        try:
            self._root.lstat()
        except FileNotFoundError:
            return _answer('not_registered')
        except Exception:
            return _answer('unavailable')
        try:
            with TrialRootLease.open_for_locator(self._root) as lease:
                record=_read(lease)
                if record['principal']!=principal:
                    return _answer('denied')
                active=self._active() if self._active is not None else None
                if (active is not None and not active._closed
                        and active.root==Path(record['runtime_root'])
                        and active.store_uuid==record['store_uuid']
                        and active._record.get('account')==record['account']
                        and active._record.get('qualification') is record['qualification']):
                    return _verified_status(active,record)
                with PersistentTrialRuntime.open(Path(record['runtime_root']),
                        expected_store_uuid=record['store_uuid'],expected_account=record['account'],
                        qualification=record['qualification']) as runtime:
                    return _verified_status(runtime,record)
        except Exception:
            return _answer('unavailable')

    def protective_review(self):
        from .crypto_protective_review_contract import protective_review
        principal=current_memory_principal()
        if principal is None:return protective_review('denied')
        try:
            self._root.lstat()
        except FileNotFoundError:
            return protective_review('not_registered')
        except Exception:
            return protective_review('unavailable')
        try:
            from .crypto_protective_lifecycle import OfflineProtectiveLifecycle
            with TrialRootLease.open_for_locator(self._root) as lease:
                record=_read(lease)
                if record['principal']!=principal:return protective_review('denied')
                active=self._active() if self._active is not None else None
                if (active is not None and not active._closed
                        and active.root==Path(record['runtime_root'])
                        and active.store_uuid==record['store_uuid']
                        and active._record.get('account')==record['account']
                        and active._record.get('qualification') is record['qualification']):
                    _verified_status(active,record)
                    return OfflineProtectiveLifecycle.review_registered(active)
                with PersistentTrialRuntime.open(Path(record['runtime_root']),
                        expected_store_uuid=record['store_uuid'],expected_account=record['account'],
                        qualification=record['qualification']) as runtime:
                    _verified_status(runtime,record)
                    return OfflineProtectiveLifecycle.review_registered(runtime)
        except Exception:
            return protective_review('unavailable')


def get_default_registry():
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT=TrialRuntimeRegistry()
    return _DEFAULT
