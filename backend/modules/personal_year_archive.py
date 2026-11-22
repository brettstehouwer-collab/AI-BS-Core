"""Read-only, single-snapshot owner archive; original names remain metadata."""
import hashlib
import io
import json
import zipfile
from datetime import date

from fastapi import APIRouter, Depends, Path
from fastapi.responses import Response
from modules.personal_payment_documents import TABLE, PRIVATE, failure, metadata
from security.financial_auth import require_financial_owner

router = APIRouter(prefix='/api/personal-finance', tags=['Personal yearly archive'])
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_RECORDS = 10000
MAX_ORIGINALS = 10000


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8')


def records_for_year(db, owner, year):
    from modules.accounting_router import EntrySchema, has_table
    from modules.personal_payments import ManualPayment
    selected, seen, size = [], 0, 0
    if db is None or not has_table(db, 'accounting_owned_records_v1'):
        return selected
    for row in db.execute("SELECT id,kind,payload,created_at,updated_at FROM accounting_owned_records_v1 "
                          "WHERE owner=? AND kind IN ('entry','personal_payment') ORDER BY id", (owner,)):
        seen += 1
        size += len(row['payload'].encode('utf-8'))
        if seen > MAX_RECORDS or size > MAX_SOURCE_BYTES:
            raise failure(413, 'Year archive review limit reached; no partial archive produced')
        try:
            payload = json.loads(row['payload'])
            schema = EntrySchema if row['kind'] == 'entry' else ManualPayment
            value = schema.model_validate(payload)
            stamp = value.date if row['kind'] == 'entry' else value.payment_date
            if date.fromisoformat(stamp).year == year:
                selected.append({**dict(row), 'recorded_payload': payload})
        except (TypeError, ValueError):
            raise failure(409, 'Stored owner records require review; no partial archive produced') from None
    return selected


def assemble(db, owner, year):
    from modules.accounting_router import has_table
    from modules.personal_ledger_export import export_year
    records = records_for_year(db, owner, year)
    entries = [{**row['recorded_payload'], 'id': row['id']} for row in records if row['kind'] == 'entry']
    payments = [row for row in records if row['kind'] == 'personal_payment']
    files = {'records.json': encoded(records),
             'accounting-ledger.csv': export_year(year, owner, lambda _owner, _kind: entries).body}
    total = sum(len(value) for value in files.values())
    documents, missing = [], []
    originals_exist = db is not None and has_table(db, TABLE)
    for payment in payments:
        rows = db.execute(f'SELECT * FROM {TABLE} WHERE owner=? AND payment_id=? ORDER BY document_id',
                          (owner, payment['id'])) if originals_exist else []
        count = 0
        for row in rows:
            raw = row['content']
            if not isinstance(raw, bytes) or len(raw) != row['size'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise failure(409, 'Original-document integrity requires review; no partial archive produced')
            total += len(raw)
            if len(documents) >= MAX_ORIGINALS or total > MAX_SOURCE_BYTES:
                raise failure(413, 'Year archive byte/document limit reached; no partial archive produced')
            count += 1
            name = f"payments/{payment['id']}/original-{count:04d}.bin"
            files[name] = raw
            documents.append({**metadata(row), 'archive_path': name})
        if not count:
            missing.append(payment['id'])
    if total > MAX_SOURCE_BYTES:
        raise failure(413, 'Year archive byte limit reached; no partial archive produced')
    manifest = {'format': 'aibs-personal-year-archive', 'version': 1, 'year': year,
                'selection': 'recorded payment_date or accounting date; not a tax classification',
                'snapshot': 'single read transaction', 'verification': 'manual_unreconciled',
                'records': len(records), 'payments': len(payments), 'accounting_entries': len(entries),
                'originals': documents, 'payments_without_stored_originals': missing,
                'coverage': 'selected owner records and linked payment originals only',
                'exclusions': ['other owners', 'unowned legacy records', 'unsent phone drafts/files',
                               'standalone tax documents', 'work-area load files not linked here'],
                'tax_return_or_payroll_reconciliation': False,
                'files': {name: {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
                          for name, value in files.items()}}
    files['manifest.json'] = encoded(manifest)
    output = io.BytesIO()
    # Fixed member metadata makes repeated exports of the same snapshot byte-equal.
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(files):
            archive.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), files[name])
    return output.getvalue()


@router.get('/exports/{year}.zip')
def export_archive(year: int = Path(ge=1, le=9999), owner=Depends(require_financial_owner)):
    from modules.accounting_router import get_db
    db = get_db()
    try:
        if db is not None:
            db.execute('BEGIN')
        raw = assemble(db, owner, year)
    finally:
        if db is not None:
            db.close()
    return Response(raw, media_type='application/zip', headers={**PRIVATE,
                    'Content-Disposition': f'attachment; filename="personal-records-{year:04d}.zip"',
                    'X-Content-Type-Options': 'nosniff', 'X-Content-SHA256': hashlib.sha256(raw).hexdigest()})
