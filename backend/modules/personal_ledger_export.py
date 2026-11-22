"""Read-only year export of existing owner-scoped manual accounting records."""
import csv
from datetime import date
import io
import os

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import Response
from core.payment_receipts import usd_minor
from security.financial_auth import require_financial_owner

router = APIRouter(prefix='/api/personal-finance', tags=['Personal ledger'])


def ledger_reader():
    # Existing accounting authority; never copy/adopt unowned legacy tables.
    from modules.accounting_router import records
    return records


def cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text


@router.get('/ledger/{year}.csv')
def export_year(year: int = Path(ge=1, le=9999), owner=Depends(require_financial_owner), reader=Depends(ledger_reader)):
    columns = ['id', 'date', 'entry_type', 'amount', 'currency', 'category', 'description',
               'receipt_note', 'verification', 'user_recorded_tax_flag', 'user_recorded_category_code']
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(columns)
    selected = []
    for record in reader(owner, 'entry'):
        try:
            stamp = date.fromisoformat(record['date'])
            if stamp.isoformat() != record['date']:
                raise ValueError()
            if stamp.year != year:
                continue
            usd_minor(record['amount'])
            if record.get('currency') != 'USD' or record.get('entry_type') not in ('income', 'expense'):
                raise ValueError()
            selected.append(record)
        except (KeyError, ValueError, TypeError):
            raise HTTPException(409, 'Stored ledger data requires review; no partial export produced',
                                headers={'Cache-Control': 'private, no-store'}) from None
    for record in sorted(selected, key=lambda item: (item['date'], item['id'])):
        writer.writerow([cell(record.get(key, '')) for key in columns[:8]] + [
            'manual_unreconciled', 'true' if record.get('is_tax_deductible') is True else 'false',
            cell(record.get('schedule_c_code', ''))])
    return Response(output.getvalue().encode('utf-8-sig'), media_type='text/csv', headers={
        'Cache-Control': 'private, no-store', 'Vary': 'Authorization, X-Admin-Key, X-Api-Key',
        'X-Content-Type-Options': 'nosniff',
        'Content-Disposition': f'attachment; filename="personal-ledger-{year:04d}.csv"'})


def register_personal_ledger(app):
    if os.environ.get('AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT') != '1':
        return False
    app.include_router(router)
    from modules.personal_year_archive import router as archive_router
    app.include_router(archive_router)
    from modules.personal_filing_archive import router as filing_archive_router
    app.include_router(filing_archive_router)
    from modules.personal_export_parts import router as multipart_router
    app.include_router(multipart_router)
    return True
