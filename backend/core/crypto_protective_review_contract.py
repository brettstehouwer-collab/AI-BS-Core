"""Closed protective replay metadata; no identifiers, finances or live authority."""
STATUSES=frozenset(('not_registered','not_prepared','qualification','held','unavailable','denied'))
STATES=frozenset(('NOT_PREPARED','UNSIGNED_DRAFT','REQUEST_RECEIVED','PENDING','NEW','ACTIVE',
    'FILLED','CANCELED','REJECTED','EXPIRED'))
FALSE_FIELDS=frozenset(('native_order_accepted','child_mapping_verified','full_position_protection_verified',
    'live_dispatch_enabled','ready_for_live','account_accessed'))
FIELDS=FALSE_FIELDS|{'status','draft_count','pending_evidence_count','observed_state','quarantined','orders_sent'}


def validate_protective_review(value):
    if (type(value) is not dict or value.keys()!=FIELDS or type(value['status']) is not str
            or value['status'] not in STATUSES or type(value['observed_state']) is not str
            or value['observed_state'] not in STATES or type(value['quarantined']) is not bool
            or type(value['orders_sent']) is not int or value['orders_sent']!=0
            or any(value[key] is not False for key in FALSE_FIELDS)
            or any(type(value[key]) is not int or not 0<=value[key]<=10000
                for key in ('draft_count','pending_evidence_count'))):
        raise ValueError('closed held protective review metadata required')
    healthy=value['status'] in ('qualification','held')
    if (healthy and (value['draft_count']==0 or value['observed_state']=='NOT_PREPARED')
            or not healthy and (value['draft_count']!=0 or value['pending_evidence_count']!=0
                or value['observed_state']!='NOT_PREPARED' or value['quarantined'])
            or value['status']=='qualification' and (value['pending_evidence_count']!=0 or value['quarantined']
                or value['observed_state'] in ('REJECTED','CANCELED','EXPIRED'))):
        raise ValueError('inconsistent protective review state')
    return dict(value)


def protective_review(status,**fields):
    value=dict.fromkeys(FALSE_FIELDS,False)
    value.update(status=status,draft_count=0,pending_evidence_count=0,observed_state='NOT_PREPARED',
        quarantined=False,orders_sent=0)
    value.update(fields)
    return validate_protective_review(value)
