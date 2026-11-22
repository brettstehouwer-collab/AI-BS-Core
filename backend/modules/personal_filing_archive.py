"""V2 adds standalone filings to the unchanged V1 yearly export contract."""
import hashlib
import io
import json
import zipfile
from fastapi import APIRouter, Depends, Path, Response
from modules.personal_payment_documents import TABLE, PRIVATE, failure, metadata
from modules.personal_year_archive import assemble, encoded, MAX_SOURCE_BYTES, MAX_RECORDS, MAX_ORIGINALS
from modules.personal_financial_filings import FinancialFiling, filing_original
from security.financial_auth import require_financial_owner

router=APIRouter(prefix='/api/personal-finance',tags=['Personal complete yearly archive'])


def complete_archive(db, owner, year):
    from modules.accounting_router import has_table
    with zipfile.ZipFile(io.BytesIO(assemble(db,owner,year))) as prior:
        manifest=json.loads(prior.read('manifest.json'))
        files={name:prior.read(name) for name in prior.namelist() if name!='manifest.json'}
    selected=[]
    scanned=0
    total=sum(len(value) for value in files.values())
    if db is not None and has_table(db,'accounting_owned_records_v1'):
        for row in db.execute("SELECT id,payload,created_at,updated_at FROM accounting_owned_records_v1 WHERE owner=? AND kind='personal_filing' ORDER BY id",(owner,)):
            scanned+=1
            total+=len(row['payload'].encode('utf-8'))
            if scanned+manifest['records']>MAX_RECORDS or total>MAX_SOURCE_BYTES:
                raise failure(413,'Complete year archive limit reached; no partial archive produced')
            try:
                payload=json.loads(row['payload'])
                value=FinancialFiling.model_validate(payload)
            except (TypeError,ValueError):
                raise failure(409,'Financial filing requires review; no partial archive produced') from None
            if value.filing_year==year:
                selected.append({**dict(row),'recorded_payload':payload})
    files['filings.json']=encoded(selected)
    missing=[]
    for filing in selected:
        rows=db.execute(f'SELECT * FROM {TABLE} WHERE owner=? AND payment_id=? ORDER BY document_id',(owner,filing['id'])) if has_table(db,TABLE) else []
        count=0
        for row in rows:
            raw=row['content']
            if not isinstance(raw,bytes) or len(raw)!=row['size'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
                raise failure(409,'Filing original integrity requires review; no partial archive produced')
            total+=len(raw)
            if len(manifest['originals'])>=MAX_ORIGINALS or total>MAX_SOURCE_BYTES:
                raise failure(413,'Complete year archive limit reached; no partial archive produced')
            count+=1
            name=f"filings/{filing['id']}/original-{count:04d}.bin"
            files[name]=raw
            manifest['originals'].append({**filing_original(metadata(row)),'archive_path':name})
        if not count:
            missing.append(filing['id'])
    if sum(len(value) for value in files.values())>MAX_SOURCE_BYTES:
        raise failure(413,'Complete year archive limit reached; no partial archive produced')
    manifest.update(version=2,filings=len(selected),filings_without_stored_originals=missing,
        selection=manifest['selection']+'; standalone documents use user-assigned filing_year',
        coverage='selected owner accounting/payment records and standalone filings with their stored originals')
    manifest['exclusions']=[v for v in manifest['exclusions'] if v!='standalone tax documents']+['financial documents not filed here']
    manifest['files']={name:{'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in files.items()}
    files['manifest.json']=encoded(manifest)
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(files):archive.writestr(zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0)),files[name])
    return output.getvalue()


@router.get('/exports/{year}/complete.zip')
def export_complete(year: int = Path(ge=1,le=9999),owner=Depends(require_financial_owner)):
    from modules.accounting_router import get_db
    db=get_db()
    try:
        if db is not None:db.execute('BEGIN')
        raw=complete_archive(db,owner,year)
    finally:
        if db is not None:db.close()
    return Response(raw,media_type='application/zip',headers={**PRIVATE,
        'Content-Disposition':f'attachment; filename="personal-complete-{year:04d}.zip"',
        'X-Content-Type-Options':'nosniff','X-Content-SHA256':hashlib.sha256(raw).hexdigest()})
