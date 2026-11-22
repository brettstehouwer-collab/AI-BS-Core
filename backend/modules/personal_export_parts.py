"""Stateless bounded yearly parts; changed inventories invalidate old plans."""
from contextlib import contextmanager
from datetime import date
import hashlib
import io
import json
import re
import zipfile

from fastapi import APIRouter, Depends, Path, Response
from modules.personal_payment_documents import TABLE, PRIVATE, MAX_DOCUMENT, failure
from modules.personal_year_archive import encoded
from security.financial_auth import require_financial_owner

router=APIRouter(prefix='/api/personal-finance/exports',tags=['Personal multipart export'])
PART_BYTES=32*1024*1024
MAX_RECORDS=10000
MAX_FILES=20000
MAX_PLAN_BYTES=8*1024*1024
MAX_INLINE_BYTES=32*1024*1024


@contextmanager
def snapshot():
    from modules.accounting_router import get_db
    db=get_db()
    try:
        if db is not None:db.execute('BEGIN')
        yield db
    finally:
        if db is not None:db.close()


def public(unit):
    return {key:value for key,value in unit.items() if key!='data'}


def collect_units(db,owner,year):
    from modules.accounting_router import EntrySchema,has_table
    from modules.personal_payments import ManualPayment
    from modules.personal_financial_filings import FinancialFiling
    from modules.personal_ledger_export import export_year
    if db is None or not has_table(db,'accounting_owned_records_v1'):return []
    units=[]
    inline=metadata_bytes=scanned=0
    def add(unit):
        nonlocal inline,metadata_bytes
        inline+=len(unit.get('data',b''))
        metadata_bytes+=len(encoded(public(unit)))
        if len(units)>=MAX_FILES or inline>MAX_INLINE_BYTES or metadata_bytes>MAX_PLAN_BYTES:
            raise failure(413,'Year export planning limit reached; no incomplete plan produced')
        if unit['bytes']>PART_BYTES:
            raise failure(413,'An archive member exceeds the configured part limit')
        units.append(unit)
    def inline_file(name,raw,source):
        add({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'source':source,'data':raw})
    schemas={'entry':EntrySchema,'personal_payment':ManualPayment,'personal_filing':FinancialFiling}
    rows=db.execute("SELECT id,kind,payload,created_at,updated_at FROM accounting_owned_records_v1 "
                    "WHERE owner=? AND kind IN ('entry','personal_payment','personal_filing') ORDER BY id",(owner,))
    originals_exist=has_table(db,TABLE)
    documents=None
    try:
        for row in rows:
            scanned+=1
            if scanned>MAX_RECORDS:raise failure(413,'Owner record review limit reached')
            try:
                payload=json.loads(row['payload']);value=schemas[row['kind']].model_validate(payload)
                selected_year=value.filing_year if row['kind']=='personal_filing' else date.fromisoformat(value.date if row['kind']=='entry' else value.payment_date).year
            except (ValueError,TypeError):raise failure(409,'Owner records require review before multipart export') from None
            if selected_year!=year:continue
            ident,kind=row['id'],row['kind']
            source={'type':'record','kind':kind,'record_id':ident}
            inline_file(f'records/{kind}/{ident}.json',encoded({**dict(row),'recorded_payload':payload}),source)
            if kind=='entry':
                csv=export_year(year,owner,lambda _owner,_kind:[{**payload,'id':ident}]).body
                inline_file(f'accounting/{ident}.csv',csv,{**source,'type':'entry_csv'})
            if kind=='entry' or not originals_exist:continue
            # Planning reads metadata only, never all original BLOBs.
            documents=db.execute(f'SELECT document_id,filename,declared_media_type,size,sha256,created_at FROM {TABLE} '
                                 'WHERE owner=? AND payment_id=? ORDER BY document_id',(owner,ident))
            for index,doc in enumerate(documents,1):
                if (type(doc['size']) is not int or not 0<doc['size']<=MAX_DOCUMENT
                        or not isinstance(doc['sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',doc['sha256'])):
                    raise failure(409,'Original metadata requires review before multipart export')
                add({'path':f'originals/{kind}/{ident}/{index:04d}.bin','bytes':doc['size'],'sha256':doc['sha256'],
                     'source':{'type':'original','kind':kind,'record_id':ident,**dict(doc)}})
            documents.close();documents=None
        return sorted(units,key=lambda item:item['path'])
    finally:
        if documents is not None:documents.close()
        rows.close()


def make_plan(owner,year,units):
    inventory=[public(unit) for unit in units]
    fingerprint=hashlib.sha256(encoded({'owner_scope':owner,'year':year,'part_bytes':PART_BYTES,'files':inventory})).hexdigest()
    parts=[];current=[];size=0
    for index,unit in enumerate(units):
        if current and size+unit['bytes']>PART_BYTES:
            parts.append({'index':len(parts),'bytes':size,'files':current});current=[];size=0
        current.append(index);size+=unit['bytes']
    if current or not parts:parts.append({'index':len(parts),'bytes':size,'files':current})
    return {'version':3,'year':year,'fingerprint':fingerprint,'part_source_limit':PART_BYTES,
            'source_bytes':sum(unit['bytes'] for unit in units),'files':inventory,'parts':parts,
            'selection':'recorded accounting/payment dates; user-assigned filing year',
            'verification':'manual_unreconciled','source_change_behavior':'409; prepare a fresh plan and do not mix fingerprints',
            'coverage':'selected owner records, per-entry accounting CSVs and stored linked originals',
            'exclusions':['other owners','unowned legacy rows','unsent phone drafts/files','documents not filed here'],
            'tax_return_or_payroll_reconciliation':False}


@router.get('/{year}/parts')
def plan_parts(year:int=Path(ge=1,le=9999),owner=Depends(require_financial_owner)):
    with snapshot() as db:plan=make_plan(owner,year,collect_units(db,owner,year))
    return {'status':'success','plan':plan}


def part_bytes(db,owner,year,fingerprint,index):
    units=collect_units(db,owner,year);plan=make_plan(owner,year,units)
    if plan['fingerprint']!=fingerprint:raise failure(409,'Year export source changed; prepare a new plan before downloading more parts')
    if index>=len(plan['parts']):raise failure(404,'Year export part not found')
    members={}
    for unit_index in plan['parts'][index]['files']:
        unit=units[unit_index]
        if 'data' in unit:raw=unit['data']
        else:
            source=unit['source']
            row=db.execute(f'SELECT content FROM {TABLE} WHERE owner=? AND payment_id=? AND document_id=?',
                           (owner,source['record_id'],source['document_id'])).fetchone()
            if row is None:raise failure(409,'A planned original is unavailable')
            raw=row['content']
        if not isinstance(raw,bytes) or len(raw)!=unit['bytes'] or hashlib.sha256(raw).hexdigest()!=unit['sha256']:
            raise failure(409,'Original integrity requires review; no partial ZIP produced')
        members[unit['path']]=raw
    selected=[public(units[n]) for n in plan['parts'][index]['files']]
    manifest={key:value for key,value in plan.items() if key not in ('files','parts')}
    manifest.update(part_index=index,part_count=len(plan['parts']),total_file_count=len(units),files=selected,
                    complete_year_requires='all indexes from zero through part_count-1 with this same fingerprint')
    members['manifest.json']=encoded(manifest)
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(members):archive.writestr(zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0)),members[name])
    return output.getvalue()


@router.get('/{year}/parts/{fingerprint}/{index}.zip')
def download_part(year:int=Path(ge=1,le=9999),fingerprint:str=Path(pattern=r'^[a-f0-9]{64}$'),
                  index:int=Path(ge=0),owner=Depends(require_financial_owner)):
    with snapshot() as db:raw=part_bytes(db,owner,year,fingerprint,index)
    return Response(raw,media_type='application/zip',headers={**PRIVATE,'X-Content-Type-Options':'nosniff',
        'X-Content-SHA256':hashlib.sha256(raw).hexdigest(),
        'Content-Disposition':f'attachment; filename="personal-{year:04d}-{fingerprint[:12]}-part-{index+1:04d}.zip"'})
