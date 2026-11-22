"""Read-only, owner-bound receipts for the explicitly authorized local IONOS runs."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTAKE = ROOT / 'state/brand_campaigns_20261114/intake/aws-email-20261114'
BOUND_OWNER = 'd8956faab6e81c38dd08b420cb72251f6149f0854a63517c2e90f79f4536b3a9'

def read_records(owner_key, selected, intake=INTAKE):
    if owner_key != BOUND_OWNER or selected != 'productions':
        return {'available': False, 'messages': [], 'reason': 'No IONOS outreach journal is connected for this brand and owner.'}
    try:
        journal = intake / 'ionos-send-journal.jsonl'
        if journal.stat().st_size > 8_000_000:
            raise ValueError('Journal too large')
        events = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines() if line.strip()]
        messages = {}
        for path in sorted(intake.glob('tailored-*.json'))[:100]:
            if path.stat().st_size > 2_000_000:
                continue
            batch = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(batch, list):
                continue
            for item in batch[:1000]:
                if isinstance(item, dict) and item.get('from') == 'brett@stehouwerproductions.com':
                    messages[item.get('to', '').lower()] = {field: item.get(field, '') for field in ('business', 'to', 'from', 'reply_to', 'subject', 'body', 'fit_source')}
                    messages[item.get('to', '').lower()]['batch'] = path.stem
        grouped = {}
        for event in events:
            address = str(event.get('to', '')).lower()
            if address not in messages:
                continue
            record = grouped.setdefault(address, {**messages[address], 'events': [], 'status': 'reserved'})
            clean = {key: event.get(key, '') for key in ('utc', 'status', 'message_id', 'error_class')}
            record['events'].append(clean)
            record['status'] = clean['status']
            record['updated_at'] = clean['utc']
            if clean['message_id']:
                record['message_id'] = clean['message_id']
        records = sorted(grouped.values(), key=lambda r: r['updated_at'], reverse=True)
        for record in records:
            record['delivery_confirmed'] = False
            record['status_detail'] = ('IONOS SMTP accepted the message. Recipient delivery is not confirmed.' if record['status'] == 'provider_accepted' else
                                       'Recipient refused during SMTP. Recorded as unresolved by the dispatcher; not retried.' if record['events'][-1].get('error_class') == 'SMTPRecipientsRefused' else
                                       'Attempt held for reconciliation. Do not resend automatically.')
        counts = Counter(record['status'] for record in records)
        queue = []
        queue_available = False
        queue_path = intake / 'outreach-qualification.json'
        if queue_path.exists() and queue_path.stat().st_size <= 3_000_000:
            try:
                raw_queue = json.loads(queue_path.read_text(encoding='utf-8'))
                def organization(value):
                    return re.sub(r'[^a-z0-9]', '', str(value).lower())
                for item in raw_queue['rows'][:1000]:
                    row = {key: item.get(key, '') for key in ('business', 'email', 'category', 'status', 'reason', 'origin')}
                    address = str(row['email']).lower()
                    matching = grouped.get(address)
                    if matching:
                        row['status'] = matching['status']
                        row['reason'] = matching['status_detail'] + ' Do not resend.'
                    elif any(organization(row['business']) == organization(r['business']) or (
                        address and '@' in address and address.split('@')[-1] not in ('gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com') and
                        address.split('@')[-1] == r['to'].split('@')[-1]) for r in records):
                        row['status'] = 'previously_contacted_organization'
                        row['reason'] = 'This organization already has an attempted address. Do not send to an alternate inbox.'
                    queue.append(row)
                queue_available = True
            except (OSError, ValueError, TypeError, KeyError):
                queue = []
        return {'available': True, 'brand': selected, 'messages': records,
                'summary': {'provider_accepted': counts['provider_accepted'], 'delivery_confirmed': 0,
                            'held': len(records) - counts['provider_accepted'], 'attempted_recipients': len(records)},
                'updated_at': max((r['updated_at'] for r in records), default=None),
                'queue': queue, 'queue_available': queue_available,
                'queue_summary': dict(Counter(row['status'] for row in queue)),
                'incoming': {'connected': False, 'reply_to': 'stehouwerjulie@gmail.com',
                             'reason': 'Incoming replies are not connected. User requested outgoing and receipts only for now.'}}
    except (OSError, ValueError, TypeError, KeyError):
        return {'available': False, 'messages': [], 'reason': 'Outreach receipts are unavailable or invalid. No delivery totals inferred.'}
