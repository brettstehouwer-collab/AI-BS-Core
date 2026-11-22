"""Manual payment evidence, separate from accounting income and provider facts."""
from datetime import date, timedelta
import os
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.payment_receipts import usd_minor
from security.financial_auth import require_financial_owner

router = APIRouter(prefix='/api/personal-finance', tags=['Personal payment evidence'])


class ManualPayment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    payment_date: str
    week_start: str
    amount: str
    currency: Literal['USD'] = 'USD'
    source: str = Field(min_length=1, max_length=160)
    payer: str = Field(min_length=1, max_length=160)
    reference: str = Field(default='', max_length=255)
    notes: str = Field(default='', max_length=4000)
    load_references: list[str] = Field(default_factory=list, max_length=100)
    evidence_references: list[str] = Field(default_factory=list, max_length=20)

    @property
    def id(self):
        # Reuse the existing writer's append path; clients cannot update by ID.
        return None

    @field_validator('payment_date', 'week_start')
    @classmethod
    def exact_date(cls, value):
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError('Use YYYY-MM-DD')
        return value

    @field_validator('amount')
    @classmethod
    def exact_amount(cls, value):
        if usd_minor(value) == 0:
            raise ValueError('A payment amount must be positive')
        return value

    @field_validator('week_start')
    @classmethod
    def complete_week(cls, value):
        if (date.max - date.fromisoformat(value)).days < 6:
            raise ValueError('The full seven-day period must fit in the calendar')
        return value

    @field_validator('source', 'payer')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('A source and payer description are required')
        return value

    @field_validator('load_references', 'evidence_references')
    @classmethod
    def bounded_references(cls, values):
        if any(not item.strip() or len(item) > 512 for item in values):
            raise ValueError('References must contain 1–512 characters')
        if len(set(values)) != len(values):
            raise ValueError('Duplicate references require review')
        return values


@router.post('/payments', status_code=201)
def record_payment(payment: ManualPayment, owner=Depends(require_financial_owner),
                   request_key: str = Header(alias='Idempotency-Key', min_length=1, max_length=128)):
    from modules.accounting_router import save
    return save(owner, 'personal_payment', payment, request_key)


@router.get('/payments')
def list_payments(week_start: str | None = Query(default=None), owner=Depends(require_financial_owner)):
    from modules.accounting_router import records
    if week_start is not None:
        try:
            ManualPayment.exact_date(week_start)
            ManualPayment.complete_week(week_start)
        except ValueError:
            raise HTTPException(422, 'Use YYYY-MM-DD for week_start') from None
    selected = []
    for row in records(owner, 'personal_payment'):
        try:
            # Validate before filtering; never silently drop corrupt evidence.
            value = ManualPayment.model_validate({k: v for k, v in row.items()
                                                 if k not in ('id', 'verification')})
        except ValueError:
            raise HTTPException(409, 'Stored payment evidence requires review',
                                headers={'Cache-Control': 'private, no-store'}) from None
        if week_start is None or value.week_start == week_start:
            selected.append(row)
    total = sum(usd_minor(row['amount']) for row in selected)
    return {'status': 'success', 'payments': selected, 'count': len(selected),
            'currency': 'USD', 'recorded_total': f'{total // 100}.{total % 100:02d}',
            'week_start': week_start,
            'week_end': (date.fromisoformat(week_start) + timedelta(days=6)).isoformat() if week_start else None,
            'verification': 'manual_unreconciled', 'references_verified': False,
            'original_documents_preserved': False, 'expected_pay': None,
            'accounting_income_posted': False}


def register_personal_payments(app):
    if os.environ.get('AI_BS_ENABLE_PERSONAL_PAYMENTS') != '1':
        return False
    app.include_router(router)
    from modules.personal_payment_documents import router as documents_router
    app.include_router(documents_router)
    from modules.personal_financial_filings import router as filings_router
    app.include_router(filings_router)
    return True
