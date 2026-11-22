"""One seed-only credential-scoped HELD store; never production account admission.

Reuses the protected lifetime owner/coordinator and their writer transaction.
READY is review-only in this phase; a later fresh financial-admission transition
is separate work. No runtime/path is selected by caller-supplied financial data.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import time
from uuid import uuid4

from security.crypto_trial_root import TrialRootLease
from .coding_journal import write_json_record
from .crypto_com_acknowledgements import _json
from .crypto_credential_preparation import validate_preparation
from .crypto_credential_preparation_registry import CredentialPreparationRegistry
from .crypto_current_snapshot import validate_current_snapshot
from .crypto_execution_controls import ControlError,digest,encode,number,stamp,text_decimal
from .crypto_reinvestment import OfflineReinvestment
from .crypto_trial_budget import create_baseline
from .crypto_trial_runtime_store import (PersistentTrialRuntime,_DurableCoordinator,_BOOTSTRAP,
    _DATABASE,_entry,_locator,_publish)
from .personal_memory_scope import current_memory_principal

MODE='HELD_CREDENTIAL_PREPARATION'
_CHILD='held-runtime'
_BINDING='held-runtime-binding.json'


def _document(lease,name,*,pin=True,limit=32768):
    lease.validate()
    if pin:lease.pin_file(name)
    with (lease.path/name).open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ControlError('bounded held-runtime document required')
    envelope=_json(raw)
    if (type(envelope) is not dict or envelope.keys()!={'record','sha256'}
            or digest(envelope['record'])!=envelope['sha256']
            or raw!=json.dumps(envelope,indent=2,allow_nan=False).encode()):
        raise ControlError('immutable held-runtime document differs')
    return envelope['record']


def _write(path,record,*,exclusive=False):
    write_json_record(path,{'record':record,'sha256':digest(record)},exclusive=exclusive)


def _selected(registry,allow_test):
    if not isinstance(registry,CredentialPreparationRegistry) or type(allow_test) is not bool:
        raise ControlError('owned selected preparation index required')
    registry._validate();cap=registry._record['preparation']
    test=cap['scope']=='TEST_CREDENTIAL_PREPARATION_ONLY'
    if test is not allow_test:raise ControlError('explicit matching actual/test held mode required')
    return cap


def _guard(entry):
    owner=entry['held_owner'];index=owner._index
    index._validate()
    if owner._closed or _document(index._lease,_BINDING,pin=entry['ready'])!=owner._binding:
        raise ControlError('selected held-runtime binding or owner differs')


class _HeldCoordinator(_DurableCoordinator):
    @staticmethod
    def _path(path,*,exists):
        entry=_entry(path)
        with entry['held_owner']._index._guard:
            _guard(entry)
            return _DurableCoordinator._path(path,exists=exists)

    @contextmanager
    def _tx(self):
        entry=_entry(self.path)
        # Consistent index -> runtime lock order; validation spans the operation.
        with entry['held_owner']._index._guard:
            _guard(entry)
            with super()._tx() as db:
                before=db.total_changes
                try:
                    yield db
                except BaseException:
                    # The inherited coordinator deliberately commits Held latches.
                    # Convert a READY write before its context can observe Held.
                    if entry['ready'] and db.total_changes!=before:
                        raise ControlError('HELD runtime refused financial mutation; transaction rolled back') from None
                    raise
                if entry['ready'] and db.total_changes!=before:
                    raise ControlError('HELD runtime is review-only; fresh financial admission is separate')


class HeldPreparationRuntime(PersistentTrialRuntime):
    @classmethod
    def create(cls,registry,*,preparation,snapshot,credential_partition_sha256,
            credential_generation_sha256,seed_budget_usdt,max_entry_budget_usdt,
            daily_loss_budget_usdt,now_ms=None,limits=None,allow_test=False):
        owner=cls();owner._index=registry
        try:
            if not isinstance(registry,CredentialPreparationRegistry):raise ControlError('selected index required')
            with registry._guard:
                selected=_selected(registry,allow_test)
                if not allow_test and now_ms is not None:
                    raise ControlError('actual mode uses trusted system clock; caller time is forbidden')
                current=stamp(now_ms) if allow_test else time.time_ns()//1000000
                cap=validate_preparation(preparation,principal=current_memory_principal(),
                    credential_partition_sha256=credential_partition_sha256,
                    credential_generation_sha256=credential_generation_sha256,now_ms=current,allow_test=allow_test)
                snap=validate_current_snapshot(snapshot,principal=current_memory_principal(),
                    credential_partition_sha256=credential_partition_sha256,
                    credential_generation_sha256=credential_generation_sha256,local_trial_uuid=cap['local_trial_uuid'],
                    now_ms=current,allow_test=allow_test)
                registry.register(preparation=preparation,credential_partition_sha256=credential_partition_sha256,
                    credential_generation_sha256=credential_generation_sha256,now_ms=current,allow_test=allow_test)
                if snap['source_preparation_receipt_sha256']!=cap['receipt_sha256']:
                    raise ControlError('snapshot must bind the CURRENT fresh preparation receipt')
                facts=snap['private_facts'];seed=number(seed_budget_usdt);maximum=number(max_entry_budget_usdt);daily=number(daily_loss_budget_usdt)
                free=number(facts.get('observed_free_quote_usdt'))
                if (seed<=0 or seed>free or maximum<seed or daily<=0
                        or facts.get('balance_bracket_unchanged') is not True
                        or facts.get('liabilities_status')=='RISK_OBSERVED'
                        or facts.get('observed_counts',{}).get('positions',0)>0):
                    raise ControlError('explicit seed, stable asset bracket and no observed liability risk required')
                if (registry.path/_BINDING).exists() or (registry.path/_CHILD).exists():
                    raise ControlError('selected trial already has runtime or incomplete creation; never reset')
                account='cryptocom-local-trial:'+cap['local_trial_uuid'];store_uuid=str(uuid4())
                opening=dict(schema=1,mode=MODE,test_only=allow_test,store_uuid=store_uuid,
                    index_identity=registry.identity,selected_preparation_receipt_sha256=selected['receipt_sha256'],
                    preparation=cap,snapshot=snap,seed_budget_usdt=text_decimal(seed),
                    max_entry_budget_usdt=text_decimal(maximum),daily_loss_budget_usdt=text_decimal(daily),
                    external_funds_reserved=False,preexisting_cro_included=False,
                    preexisting_cro_basis_known=False,exchange_account_id=None)
                if len(encode(opening).encode())>2*1024*1024:raise ControlError('bounded private opening record required')
                opening_sha=digest(opening)
                baseline=create_baseline(trial_id=cap['local_trial_uuid'],account=account,started_ms=snap['completed_ms'],
                    day_start_ms=(snap['completed_ms']//86400000)*86400000,opening_receipt_sha256=opening_sha)
                binding=dict(schema=1,mode=MODE,state='CREATING',test_only=allow_test,store_uuid=store_uuid,
                    index_identity=registry.identity,selected_preparation_receipt_sha256=selected['receipt_sha256'],
                    current_preparation_receipt_sha256=cap['receipt_sha256'],snapshot_receipt_sha256=snap['receipt_sha256'],
                    principal=cap['principal'],local_trial_uuid=cap['local_trial_uuid'],account=account,
                    credential_partition_sha256=credential_partition_sha256,credential_generation_sha256=credential_generation_sha256,
                    opening_receipt_sha256=opening_sha,baseline=baseline,child_identity=None,database_identity=None)
                # Marker survives failure even before child/DB exists: no empty retry.
                _write(registry.path/_BINDING,binding,exclusive=True);owner._binding=binding
                owner._own(TrialRootLease.create(registry.path,_CHILD))
                entry=owner._entry;entry['held_owner']=owner;token=_BOOTSTRAP.set(entry['token'])
                try:
                    record=dict(binding,root_identity=owner._lease.identity,broker_sid=owner._lease.broker_sid)
                    _publish(owner.root,record,exclusive=True)
                    _write(owner.root/'opening.json',opening,exclusive=True);owner._lease.pin_file('opening.json')
                    base=_HeldCoordinator.create(owner.root/_DATABASE,account=account,quote='USDT',cash=text_decimal(seed),limits=limits)
                    OfflineReinvestment.create(base,baseline,seed_budget_usdt=text_decimal(seed),max_entry_budget_usdt=text_decimal(maximum))
                    entry['base_init']=False
                    coordinator=_HeldCoordinator.register(base,daily_loss_budget_usdt=text_decimal(daily))
                    binding=dict(binding,state='READY',child_identity=owner._lease.identity,database_identity=entry['db_identity'])
                    record=dict(binding,root_identity=owner._lease.identity,broker_sid=owner._lease.broker_sid)
                    with coordinator._tx() as db:
                        db.execute('CREATE TABLE aibs_trial_runtime_binding(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL,fingerprint TEXT NOT NULL)')
                        db.execute('INSERT INTO aibs_trial_runtime_binding VALUES(1,?,?)',(encode(record),digest(record)))
                    _publish(owner.root,record);owner._lease.pin_file('store.json')
                    _write(registry.path/_BINDING,binding);registry._lease.pin_file(_BINDING)
                    owner._binding=binding;owner._record=record;owner.coordinator=coordinator
                    owner.reinvestment=OfflineReinvestment(coordinator);entry['ready']=True;owner.status()
                finally:_BOOTSTRAP.reset(token)
                return owner
        except BaseException as error:
            owner.close()
            if isinstance(error,(ControlError,PermissionError)):raise
            raise ControlError('held-runtime creation refused: '+type(error).__name__) from None

    @classmethod
    def open(cls,registry,*,expected_store_uuid=None,allow_test=False):
        """Reopen dated selected bookkeeping only; no fresh authentication authority."""
        owner=cls();owner._index=registry
        try:
            if not isinstance(registry,CredentialPreparationRegistry):raise ControlError('selected index required')
            with registry._guard:
                selected=_selected(registry,allow_test);binding=_document(registry._lease,_BINDING)
                if (binding.get('state')!='READY' or binding.get('mode')!=MODE or binding.get('test_only') is not allow_test
                        or binding.get('index_identity')!=registry.identity
                        or binding.get('selected_preparation_receipt_sha256')!=selected['receipt_sha256']
                        or binding.get('principal')!=current_memory_principal()
                        or any(binding.get(key)!=selected.get(key) for key in
                            ('local_trial_uuid','credential_partition_sha256','credential_generation_sha256'))
                        or expected_store_uuid is not None and binding.get('store_uuid')!=expected_store_uuid):
                    raise ControlError('dated selected held-runtime identity differs or creation incomplete')
                lease=TrialRootLease.open(registry.path/_CHILD,expected_identity=binding['child_identity']);owner._lease=lease
                lease.pin_file('store.json');record=_locator(lease.path)
                if record!=dict(binding,root_identity=lease.identity,broker_sid=lease.broker_sid):
                    raise ControlError('held-runtime locator/index binding differs')
                opening=_document(lease,'opening.json',limit=4*1024*1024)
                if (digest(opening)!=binding['opening_receipt_sha256']
                        or opening['preparation']['receipt_sha256']!=binding['current_preparation_receipt_sha256']
                        or opening['snapshot']['receipt_sha256']!=binding['snapshot_receipt_sha256']):
                    raise ControlError('immutable held opening evidence differs')
                lease.validate_file(_DATABASE,binding['database_identity']);lease.pin_file(_DATABASE)
                lease.pin_file('runtime.lock')  # Refuse missing/linked locks; _own must never heal reopen.
                owner._binding=binding;owner._own(lease,ready=True,db_identity=binding['database_identity'])
                owner._entry['held_owner']=owner;owner._record=record
                owner.coordinator=_HeldCoordinator(owner.root/_DATABASE);owner.reinvestment=OfflineReinvestment(owner.coordinator)
                owner.status();return owner
        except BaseException as error:
            owner.close()
            if isinstance(error,(ControlError,PermissionError)):raise
            raise ControlError('held-runtime reopening refused: '+type(error).__name__) from None

    def status(self):
        if self._closed or self._entry is None:raise ControlError('held-runtime owner closed')
        with self.coordinator._tx() as db:
            row=db.execute('SELECT payload,fingerprint FROM aibs_trial_runtime_binding WHERE id=1').fetchone()
            if row is None or row['payload']!=encode(self._record) or row['fingerprint']!=digest(self._record):
                raise ControlError('held-runtime database binding differs')
            if _locator(self.root)!=self._record:raise ControlError('held-runtime locator changed')
            opening=_document(self._lease,'opening.json',limit=4*1024*1024)
            if digest(opening)!=self._binding['opening_receipt_sha256']:raise ControlError('held opening changed')
        return dict(scope=MODE,test_only=self._record['test_only'],fresh_authority=False,
            local_seed_allocated=True,external_funds_reserved=False,exchange_account_id=None,
            account_identity_verified=False,native_order_accepted=False,live_dispatch_enabled=False,
            ready_for_live=False,orders_sent=0)

    def close(self):
        index=getattr(self,'_index',None)
        if isinstance(index,CredentialPreparationRegistry):
            with index._guard:return super().close()
        return super().close()
