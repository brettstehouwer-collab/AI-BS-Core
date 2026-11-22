"""Dated, principal-scoped preparation review; no credentials, reads or dispatch."""
from contextlib import ExitStack
from pathlib import Path

from .personal_memory_scope import current_memory_principal

_ROOT=Path('C:/AI-BS/saved_data/crypto_credential_preparation_registry')
_STATUSES=frozenset(('not_registered','selected','held_preparation','unavailable','denied'))
_FALSE=frozenset(('fresh_authority','external_funds_reserved','account_identity_verified',
    'native_order_accepted','live_dispatch_enabled','ready_for_live'))
_BOOL=_FALSE|{'test_only','local_seed_allocated'}
_FIELDS=_BOOL|{'status','orders_sent'}


def validate_preparation_status(value):
    if (type(value) is not dict or value.keys()!=_FIELDS
            or type(value['status']) is not str or value['status'] not in _STATUSES
            or type(value['orders_sent']) is not int or value['orders_sent']!=0
            or any(type(value[key]) is not bool for key in _BOOL)
            or any(value[key] is not False for key in _FALSE)
            or value['local_seed_allocated'] is not (value['status']=='held_preparation')
            or value['test_only'] and value['status'] not in ('selected','held_preparation')):
        raise ValueError('Closed dated preparation status required')
    return dict(value)


def preparation_status(status,*,test_only=False):
    value=dict.fromkeys(_BOOL,False)
    value.update(status=status,test_only=test_only,local_seed_allocated=status=='held_preparation',orders_sent=0)
    return validate_preparation_status(value)


def _same_state(value,expected):
    return (type(value) is dict and value.keys()==expected.keys()
        and all(type(value[key]) is type(item) and value[key]==item for key,item in expected.items()))


def _exists(path):
    try:path.lstat();return True
    except FileNotFoundError:return False


class PreparationStatusReader:
    def __init__(self,root=None,active_registry=None,active_runtime=None,allow_test=False):
        self._root=Path(root) if root is not None else active_registry.path if active_registry is not None else _ROOT
        self._registry=active_registry;self._runtime=active_runtime;self._allow_test=allow_test

    def status(self):
        if current_memory_principal() is None:return preparation_status('denied')
        try:
            from .crypto_credential_preparation_registry import CredentialPreparationRegistry
            from .crypto_held_preparation_runtime import HeldPreparationRuntime
            from security.crypto_trial_root import TrialRootLease
            if (type(self._allow_test) is not bool
                    or (self._root.absolute()==_ROOT) is self._allow_test):
                return preparation_status('unavailable')
            active=self._registry
            if active is not None and (not isinstance(active,CredentialPreparationRegistry)
                    or active.path!=self._root):
                return preparation_status('unavailable')
            if not _exists(self._root):return preparation_status('not_registered')
            with ExitStack() as stack:
                if active is not None and not active._closed:index=active
                else:
                    with TrialRootLease.open_for_locator(self._root) as measured:
                        index=CredentialPreparationRegistry.open(self._root,
                            expected_identity=measured.identity,allow_test=self._allow_test)
                    stack.callback(index.close)
                with index._guard:
                    state=index.review()
                    if not _same_state(state,dict(scope='METADATA_ONLY_CREDENTIAL_PREPARATION_INDEX',status='stored_preparation',
                            test_only=self._allow_test,fresh_authority=False,exchange_account_id=None,
                            account_identity_verified=False,financial_runtime_created=False,
                            live_dispatch_enabled=False,ready_for_live=False,orders_sent=0)):
                        raise ValueError('Selected preparation differs')
                    marker=_exists(index.path/'held-runtime-binding.json')
                    child=_exists(index.path/'held-runtime')
                    if not marker and not child:return preparation_status('selected',test_only=self._allow_test)
                    if not marker or not child:raise ValueError('Incomplete held preparation')
                    runtime=self._runtime
                    if runtime is not None and not runtime._closed:
                        if not isinstance(runtime,HeldPreparationRuntime) or runtime._index is not index:
                            raise ValueError('Borrowed runtime selection differs')
                    else:
                        runtime=HeldPreparationRuntime.open(index,allow_test=self._allow_test)
                        stack.callback(runtime.close)
                    state=runtime.status()
                    if not _same_state(state,dict(scope='HELD_CREDENTIAL_PREPARATION',test_only=self._allow_test,
                            fresh_authority=False,local_seed_allocated=True,external_funds_reserved=False,
                            exchange_account_id=None,account_identity_verified=False,native_order_accepted=False,
                            live_dispatch_enabled=False,ready_for_live=False,orders_sent=0)):
                        raise ValueError('Held preparation differs')
                    return preparation_status('held_preparation',test_only=self._allow_test)
        except PermissionError:return preparation_status('denied')
        except Exception:return preparation_status('unavailable')
