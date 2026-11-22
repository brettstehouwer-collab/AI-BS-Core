"""Closed read-only trial-status contract; never financial data or activation."""
STATUSES=frozenset(('not_registered','qualification','held','unavailable','denied'))
BOOL_FIELDS=frozenset(('registered','stored_state_verified','account_metadata_bound',
    'exchange_account_identity_verified','local_entry_cutoff_enforced','entry_held',
    'production_store_admitted','native_protection_qualified','live_dispatch_enabled',
    'ready_for_live','account_accessed'))
FALSE_FIELDS=frozenset(('exchange_account_identity_verified','production_store_admitted',
    'native_protection_qualified','live_dispatch_enabled','ready_for_live','account_accessed'))
HEALTH_FIELDS=frozenset(('registered','stored_state_verified','account_metadata_bound','local_entry_cutoff_enforced'))
STATUS_FIELDS=BOOL_FIELDS|{'status','orders_sent'}


def validate_trial_status(value):
    if (type(value) is not dict or value.keys()!=STATUS_FIELDS
            or type(value['status']) is not str or value['status'] not in STATUSES
            or type(value['orders_sent']) is not int or value['orders_sent']!=0
            or any(type(value[key]) is not bool for key in BOOL_FIELDS)
            or any(value[key] is not False for key in FALSE_FIELDS)):
        raise ValueError('closed held trial-status metadata required')
    healthy=value['status'] in ('qualification','held')
    if (healthy and any(value[key] is not True for key in HEALTH_FIELDS)
            or not healthy and any(value[key] is not False for key in BOOL_FIELDS)):
        raise ValueError('inconsistent trial-status health flags')
    return dict(value)


def trial_status(status, *, entry_held=False):
    if type(status) is not str or status not in STATUSES or type(entry_held) is not bool:
        raise ValueError('known status and explicit entry-held flag required')
    value=dict.fromkeys(BOOL_FIELDS,False)
    if status in ('qualification','held'):
        value.update({key:True for key in HEALTH_FIELDS});value['entry_held']=entry_held
    elif entry_held:
        raise ValueError('unverified state cannot claim an entry latch')
    value.update(status=status,orders_sent=0)
    return validate_trial_status(value)
