"""Owner-assigned filing metadata and originals; no payment or tax inference."""
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from modules.personal_payments import ManualPayment
from modules.personal_payment_documents import PRIVATE, failure, read_documents, receive_document
from security.financial_auth import require_financial_owner

router=APIRouter(prefix='/api/personal-finance/filings', tags=['Personal financial filing'])


class FinancialFiling(BaseModel):
    model_config=ConfigDict(extra='forbid')
    document_date: str
    filing_year: int = Field(ge=1, le=9999, strict=True)
    source: str = Field(min_length=1, max_length=160)
    document_type: Literal['pay_statement','receipt','ledger','tax_document','other_financial']
    notes: str = Field(default='', max_length=4000)

    @property
    def id(self):
        return None

    @field_validator('document_date')
    @classmethod
    def exact_date(cls, value):
        return ManualPayment.exact_date(value)

    @field_validator('source')
    @classmethod
    def nonblank(cls, value):
        return ManualPayment.nonblank(value)


def filing_original(info):
    result=dict(info)
    result['filing_id']=result.pop('payment_id')
    return result


@router.post('', status_code=201)
def create_filing(record: FinancialFiling, owner=Depends(require_financial_owner),
                  operation: str = Header(alias='Idempotency-Key', min_length=1, max_length=128)):
    from modules.accounting_router import save
    return save(owner, 'personal_filing', record, operation)


@router.get('')
def list_filings(filing_year: int | None = Query(default=None, ge=1, le=9999), owner=Depends(require_financial_owner)):
    from modules.accounting_router import records
    selected=[]
    for row in records(owner, 'personal_filing'):
        try:
            value=FinancialFiling.model_validate({k:v for k,v in row.items() if k not in ('id','verification')})
        except ValueError:
            raise failure(409, 'Stored financial filing requires review') from None
        if filing_year is None or value.filing_year==filing_year:
            selected.append(row)
    return {'status':'success','filings':selected,'count':len(selected),
            'classification':'user_assigned_unverified','original_coverage':'query each filing originals'}


@router.post('/{filing_id}/originals', status_code=201)
async def upload_original(request: Request, filing_id: int = Path(gt=0), owner=Depends(require_financial_owner),
                          operation: str = Header(alias='Idempotency-Key', min_length=1, max_length=128),
                          filename: str = Header(alias='X-Document-Name', min_length=1, max_length=1800),
                          encoding: str | None = Header(default=None, alias='X-Document-Name-Encoding')):
    result=await receive_document(request, filing_id, owner, operation, filename, encoding, kind='personal_filing')
    return {**result,'document':filing_original(result['document'])}


@router.get('/{filing_id}/originals')
def originals(filing_id: int = Path(gt=0), owner=Depends(require_financial_owner)):
    rows=read_documents(owner,filing_id,kind='personal_filing')
    return {'status':'success','documents':[filing_original(row) for row in rows],'count':len(rows)}


@router.get('/{filing_id}/originals/{document_id}')
def download(document_id: str, filing_id: int = Path(gt=0), owner=Depends(require_financial_owner)):
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',document_id):
        raise failure(404,'Original not found')
    info,raw=read_documents(owner,filing_id,document_id,kind='personal_filing')
    return Response(raw,media_type='application/octet-stream',headers={**PRIVATE,
        'Content-Disposition':"attachment; filename*=UTF-8''"+quote(info['filename'],safe=''),
        'X-Content-Type-Options':'nosniff','X-Content-SHA256':info['sha256']})
