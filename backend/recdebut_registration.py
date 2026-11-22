"""Atomic website receipt -> private staff casework. No sends or endorsements."""
import hashlib
import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

import recdebut_workflow as workflow
from security.recdebut_registration_auth import verify_registration

router = APIRouter()


class Registration(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    schema_version: Literal[1]
    event_id: UUID
    source: Literal['https://recdebut.com']
    form_reference: str = Field(min_length=1, max_length=100)
    athlete_name: str = Field(min_length=1, max_length=200)
    sport: str = Field(default='', max_length=100)
    grad_year: str = Field(default='', pattern=r'^(?:20[0-9]{2})?$')
    school: str = Field(default='', max_length=200)
    athlete_email: str = Field(default='', max_length=254)
    athlete_phone: str = Field(default='', max_length=40)
    guardian_name: str = Field(default='', max_length=200)
    guardian_email: str = Field(default='', max_length=254)
    guardian_phone: str = Field(default='', max_length=40)


def retain(data: Registration):
    approved = {value.strip() for value in os.environ.get('RECDEBUT_REGISTRATION_FORMS', '').split(',') if value.strip()}
    if not approved:
        raise HTTPException(503, 'Website registration forms have not been approved.')
    if data.form_reference not in approved:
        raise HTTPException(403, 'Website form is not approved for athlete intake.')
    payload = data.model_dump(mode='json')
    receipt_digest = workflow.digest(payload)
    identifier = 'web_' + hashlib.sha256(str(data.event_id).encode()).hexdigest()[:32]
    with workflow.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS recdebut_registration_receipts (event_id TEXT PRIMARY KEY, digest TEXT NOT NULL, family_id TEXT NOT NULL, received_at TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        prior = db.execute('SELECT * FROM recdebut_registration_receipts WHERE event_id=?', (str(data.event_id),)).fetchone()
        if prior:
            if prior['digest'] != receipt_digest:
                raise HTTPException(409, 'Registration event ID was reused with different data.')
            return {'accepted': True, 'duplicate': True, 'family_id': prior['family_id'], 'sending_enabled': False}
        records = [(identifier, 'family', {'name': data.athlete_name + ' family', 'athlete_name': data.athlete_name,
                    'sport': data.sport, 'grad_year': data.grad_year, 'school': data.school, 'source': data.source})]
        for role, name, email, phone in [('athlete', data.athlete_name, data.athlete_email, data.athlete_phone),
                                          ('parent', data.guardian_name, data.guardian_email, data.guardian_phone)]:
            if not (name or email or phone):
                continue
            records.append((identifier + '_' + role, 'person', {'name': name or 'Guardian (name unknown)',
                'family_id': identifier, 'role': role, 'phone': phone, 'email': email, 'source': data.source,
                'relationship': 'unknown', 'sms_permission': 'unknown', 'email_permission': 'unknown',
                'notes': 'Website submission; identity, relationship and permission require staff verification.'}))
        records.append((identifier + '_review', 'followup', {'family_id': identifier, 'title': 'Review website registration',
                        'owner': '', 'status': 'open', 'kind': 'registration', 'notes': 'Source form: ' + data.form_reference}))
        stamp = workflow.now()
        for record_id, kind, record in records:
            validated = workflow.validate_payload(db, kind, record)
            db.execute('INSERT INTO recdebut_workflow VALUES(?,?,?,?,?)', (record_id, kind, 1, workflow.encode(validated), stamp))
            workflow.event(db, record_id, 1, 'website_received', 'recdebut.com signed intake', validated)
        db.execute('INSERT INTO recdebut_registration_receipts VALUES(?,?,?,?)', (str(data.event_id), receipt_digest, identifier, stamp))
    return {'accepted': True, 'duplicate': False, 'family_id': identifier, 'sending_enabled': False}


@router.post('/webhooks/registration', dependencies=[Depends(verify_registration)])
async def receive(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    try:
        data = Registration.model_validate_json(await request.body())
    except ValueError:
        raise HTTPException(422, 'Invalid registration fields.') from None
    return retain(data)
