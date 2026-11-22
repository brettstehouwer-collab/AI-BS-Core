"""Explicit current-turn durable trial status; never account or model I/O."""
import asyncio
import re

TOOL_NAME='get_crypto_trial_status'


def crypto_trial_status_declarations():
    return [{'name':TOOL_NAME,'description':
        'Read-only server-selected local crypto trial status. Never accesses an account or sends orders.',
        'parameters':{'type':'object','properties':{},'required':[], 'additionalProperties':False}}]


def crypto_protective_review_declarations():
    return [{'name':'get_crypto_protective_review','description':
        'Read-only server-selected qualification protection review; no account access, evidence replay or orders.',
        'parameters':{'type':'object','properties':{},'required':[], 'additionalProperties':False}}]


def crypto_preparation_status_declarations():
    return [{'name':'get_crypto_preparation_status','description':
        'Read retained local credential-scoped preparation; no account access, initialization or orders.',
        'parameters':{'type':'object','properties':{},'required':[], 'additionalProperties':False}}]


def _format_preparation(result):
    from core.crypto_preparation_status import validate_preparation_status
    try:checked=validate_preparation_status(result)
    except Exception:checked={'status':'unavailable'}
    messages={
        'not_registered':'No local credential-scoped preparation is registered.',
        'selected':'Retained local credential selection verified; no financial preparation is initialized.',
        'held_preparation':'Retained local credential-scoped seed preparation verified; this is dated evidence.',
        'unavailable':'Local preparation review is unavailable.',
        'denied':'Local preparation review access was denied.'}
    test=' This is synthetic TEST preparation.' if checked.get('test_only') else ''
    return (messages[checked['status']]+test+
        ' External funds are not reserved. This review does not provide fresh authentication. '
        'Exchange account identity and native protection are unverified. Live trading remains held. '
        'No account was accessed and no orders were sent.')


def _format_protection(result):
    from core.crypto_protective_review_contract import validate_protective_review
    try:
        checked=validate_protective_review(result)
    except Exception:
        checked={'status':'unavailable'}
    messages={
        'not_registered':'A local crypto trial store is not registered.',
        'not_prepared':'No local qualification protective draft is prepared.',
        'qualification':'Local protection qualification review only.',
        'held':'Local protection qualification review remains held.',
        'unavailable':'Local protection review is unavailable.',
        'denied':'Local protection review access was denied.'}
    state=checked['status'];detail=''
    if state in ('qualification','held','not_prepared'):
        detail=(f"\nDrafts: {checked['draft_count']}; pending raw evidence: {checked['pending_evidence_count']}; "
            f"observed state: {checked['observed_state']}; quarantined: {checked['quarantined']}.")
    return (messages.get(state,messages['unavailable'])+detail+
        '\nPending raw evidence is not automatically replayed. Native acceptance, executed-child mapping and '
        'full-position protection are unverified. Live trading remains held; live readiness is false. '
        'No account was accessed and no orders were sent.')


def _format(result):
    from core.crypto_trial_status_contract import validate_trial_status
    try:
        checked=validate_trial_status(result)
        if type(checked) is not dict:raise ValueError('invalid status')
    except Exception:
        checked={'status':'unavailable'}
    state=checked['status']
    messages={
        'not_registered':'A local crypto trial store is not registered.',
        'qualification':'Local crypto trial simulation: retained qualification state verified. This is not a funded trading account.',
        'held':'Local crypto trial simulation: retained qualification state is held.',
        'unavailable':'Local crypto trial status is unavailable.',
        'denied':'Local crypto trial status access was denied.'}
    cutoff=''
    if state in ('qualification','held'):
        cutoff=('\nLocal new-entry cutoff is latched; new entries are held.'
            if checked['entry_held'] else '\nLocal new-entry cutoff is not latched.')
    return (messages.get(state,messages['unavailable'])+cutoff+
        '\nLive trading remains held. Exchange account identity and native protection are unverified. '
        'Live readiness is false. No account was accessed and no orders were sent.')


async def crypto_trial_status_reply(body):
    raw=body.get('user_prompt')
    raw=raw if isinstance(raw,str) else body.get('prompt')
    if isinstance(raw,str) and re.match(r'^\s*/crypto-preparation(?:\s|$)',raw,re.IGNORECASE):
        if not re.fullmatch(r'\s*/crypto-preparation(?:\s+status)?\s*',raw,re.IGNORECASE):
            response='Use `/crypto-preparation status` for read-only retained preparation review. Live trading remains held.'
        else:
            from tools.tool_registry import ToolRegistry
            try:result=await asyncio.to_thread(ToolRegistry.execute_tool,'get_crypto_preparation_status',{})
            except Exception:result=None
            response=_format_preparation(result)
        return {'response':response,'provider':'local','model':'crypto-preparation-status',
                'device':'Local read-only preparation status'}
    if isinstance(raw,str) and re.match(r'^\s*/crypto-protection(?:\s|$)',raw,re.IGNORECASE):
        if not re.fullmatch(r'\s*/crypto-protection(?:\s+status)?\s*',raw,re.IGNORECASE):
            response='Use `/crypto-protection status` for read-only review. Live trading remains held; no account access or orders.'
        else:
            from tools.tool_registry import ToolRegistry
            try:
                result=await asyncio.to_thread(ToolRegistry.execute_tool,'get_crypto_protective_review',{})
            except Exception:
                result=None
            response=_format_protection(result)
        return {'response':response,'provider':'local','model':'crypto-protective-review',
                'device':'Local read-only protection review'}
    if not isinstance(raw,str) or not re.match(r'^\s*/crypto-trial(?:\s|$)',raw,re.IGNORECASE):
        return None
    if not re.fullmatch(r'\s*/crypto-trial(?:\s+status)?\s*',raw,re.IGNORECASE):
        response='Use `/crypto-trial status` to review local status. Live trading remains held; no account access or orders.'
    else:
        from tools.tool_registry import ToolRegistry
        try:
            result=await asyncio.to_thread(ToolRegistry.execute_tool,TOOL_NAME,{})
        except Exception:
            result=None
        response=_format(result)
    return {'response':response,'provider':'local','model':'crypto-trial-status',
            'device':'Local read-only trial status'}
