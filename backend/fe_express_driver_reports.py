"""Private FE Express daily logs, shipment paperwork and weekly exports.

These are operator-entered business records, not certified ELD or payroll records.
"""
import csv
import hashlib
import html
import io
import json
import math
import sqlite3
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import unquote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_DOCUMENTS = 20
MAX_SHIPMENT_BYTES = 50 * 1024 * 1024
MAX_EXPORT_BYTES = 64 * 1024 * 1024
OWNER = {'driver_id': 'OWNER-DEVIN', 'full_name': 'Devin (owner)'}
def private_response(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'


router = APIRouter(prefix='/driver-reports', tags=['FE Express driver reports'], dependencies=[Depends(private_response)])


class FiniteRecord(BaseModel):
    @model_validator(mode='before')
    @classmethod
    def finite_json(cls, values):
        if isinstance(values, dict) and any(isinstance(v, float) and not math.isfinite(v) for v in values.values()):
            raise HTTPException(422, 'Numeric values must be finite.')
        return values


class DailyLog(FiniteRecord):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    revision: int = Field(ge=0)
    unit: str = Field(default='', max_length=100)
    loaded_miles: float = Field(default=0, ge=0, le=10000)
    deadhead_miles: float = Field(default=0, ge=0, le=10000)
    driving_hours: float = Field(default=0, ge=0, le=24)
    other_duty_hours: float = Field(default=0, ge=0, le=24)
    fuel_gallons: float = Field(default=0, ge=0, le=10000)
    fuel_cost: float = Field(default=0, ge=0, le=1000000)
    other_expenses: float = Field(default=0, ge=0, le=1000000)
    notes: str = Field(default='', max_length=4000)

    @model_validator(mode='after')
    def valid_totals(self):
        if self.driving_hours + self.other_duty_hours > 24:
            raise ValueError('Combined daily hours cannot exceed 24.')
        if self.fuel_cost > 0 and self.fuel_gallons == 0:
            raise ValueError('Enter gallons for purchased fuel.')
        return self


class Shipment(FiniteRecord):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    revision: int = Field(ge=0)
    driver_id: str = Field(min_length=1, max_length=100)
    load_number: str = Field(min_length=1, max_length=100)
    pickup_date: date
    delivery_date: date
    origin: str = Field(default='', max_length=300)
    destination: str = Field(default='', max_length=300)
    broker: str = Field(default='', max_length=300)
    agreed_rate: float = Field(default=0, ge=0, le=10000000)
    status: Literal['ASSIGNED', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED'] = 'ASSIGNED'
    notes: str = Field(default='', max_length=4000)
    dispatch_id: str = Field(default='', max_length=100)

    @model_validator(mode='after')
    def valid_dates(self):
        if self.delivery_date < self.pickup_date:
            raise ValueError('Delivery cannot precede pickup.')
        return self


class ReportStore:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS fe_report_days (
                    driver_id TEXT NOT NULL, log_date TEXT NOT NULL,
                    revision INTEGER NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(driver_id, log_date));
                CREATE TABLE IF NOT EXISTS fe_report_shipments (
                    shipment_id TEXT PRIMARY KEY, driver_id TEXT NOT NULL,
                    pickup_date TEXT NOT NULL, delivery_date TEXT NOT NULL,
                    revision INTEGER NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS fe_report_documents (
                    document_id TEXT PRIMARY KEY, shipment_id TEXT NOT NULL,
                    kind TEXT NOT NULL, filename TEXT NOT NULL, mime TEXT NOT NULL,
                    length INTEGER NOT NULL, sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL, data BLOB NOT NULL);
                CREATE INDEX IF NOT EXISTS fe_report_documents_shipment
                    ON fe_report_documents(shipment_id);
            ''')
            yield db
            db.commit()
        finally:
            db.close()


def get_store():
    return ReportStore(Path(__file__).resolve().parents[1] / 'saved_data' / 'fe_express.db')


def drivers(db):
    result = [dict(OWNER)]
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='fe_express_contractor_drivers'").fetchone():
        result += [dict(r) for r in db.execute('SELECT driver_id, full_name FROM fe_express_contractor_drivers WHERE driver_id != ?', (OWNER['driver_id'],))]
    return result


def require_driver(db, driver_id):
    found = next((d for d in drivers(db) if d['driver_id'] == driver_id), None)
    if not found:
        raise HTTPException(404, 'Driver profile not found.')
    return found


def require_shipment(db, shipment_id):
    row = db.execute('SELECT * FROM fe_report_shipments WHERE shipment_id=?', (str(shipment_id),)).fetchone()
    if not row:
        raise HTTPException(404, 'Shipment not found.')
    return row


def serialize(payload, **extra):
    return json.dumps(dict(payload, **extra), allow_nan=False, ensure_ascii=False)


@router.get('/drivers')
def list_drivers(store: ReportStore = Depends(get_store)):
    with store.connect() as db:
        return {'drivers': drivers(db)}


@router.put('/days/{driver_id}/{log_date}')
def save_day(driver_id: str, log_date: date, item: DailyLog, store: ReportStore = Depends(get_store)):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        require_driver(db, driver_id)
        row = db.execute('SELECT revision FROM fe_report_days WHERE driver_id=? AND log_date=?', (driver_id, log_date.isoformat())).fetchone()
        if item.revision != (row['revision'] if row else 0):
            raise HTTPException(409, 'This day changed. Refresh the weekly report before saving again.')
        data = item.model_dump()
        data.update(revision=item.revision + 1, driver_id=driver_id, log_date=log_date.isoformat(), updated_at=datetime.now(timezone.utc).isoformat())
        db.execute('INSERT INTO fe_report_days VALUES(?,?,?,?) ON CONFLICT(driver_id,log_date) DO UPDATE SET revision=excluded.revision,payload=excluded.payload',
                   (driver_id, log_date.isoformat(), data['revision'], serialize(data)))
        return data


@router.put('/shipments/{shipment_id}')
def save_shipment(shipment_id: UUID, item: Shipment, store: ReportStore = Depends(get_store)):
    sid = str(shipment_id)
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        require_driver(db, item.driver_id)
        row = db.execute('SELECT revision FROM fe_report_shipments WHERE shipment_id=?', (sid,)).fetchone()
        if item.revision != (row['revision'] if row else 0):
            raise HTTPException(409, 'This shipment changed. Refresh before saving again.')
        data = item.model_dump(mode='json')
        data.update(shipment_id=sid, revision=item.revision + 1, updated_at=datetime.now(timezone.utc).isoformat())
        db.execute('INSERT INTO fe_report_shipments VALUES(?,?,?,?,?,?) ON CONFLICT(shipment_id) DO UPDATE SET driver_id=excluded.driver_id,pickup_date=excluded.pickup_date,delivery_date=excluded.delivery_date,revision=excluded.revision,payload=excluded.payload',
                   (sid, item.driver_id, data['pickup_date'], data['delivery_date'], data['revision'], serialize(data)))
        return data


DocumentKind = Literal['rate_confirmation', 'bol', 'pod', 'fuel_receipt', 'other']


@router.put('/shipments/{shipment_id}/documents/{document_id}')
async def upload_document(shipment_id: UUID, document_id: UUID, kind: DocumentKind, request: Request, store: ReportStore = Depends(get_store)):
    filename = unquote(request.headers.get('x-file-name', ''))
    if not filename or len(filename) > 180 or any(ord(c) < 32 or ord(c) == 127 for c in filename) or any(c in filename for c in '/\\:') or filename in ('.', '..'):
        raise HTTPException(400, 'Use a simple document filename without paths or control characters.')
    mime = request.headers.get('content-type', '').split(';')[0].lower()
    ext = Path(filename).suffix.lower()
    allowed = {'.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}
    if allowed.get(ext) != mime:
        raise HTTPException(415, 'Upload a PDF, JPEG or PNG document.')
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_FILE_BYTES:
            raise HTTPException(413, 'Document exceeds the 10 MiB upload limit.')
        data.extend(chunk)
    raw = bytes(data)
    valid = (mime == 'application/pdf' and raw.startswith(b'%PDF-')) or (mime == 'image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (mime == 'image/jpeg' and raw.startswith(b'\xff\xd8\xff'))
    if not valid:
        raise HTTPException(415, 'Document bytes do not match its file type.')
    digest = hashlib.sha256(raw).hexdigest()
    sid, did = str(shipment_id), str(document_id)
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        require_shipment(db, sid)
        old = db.execute('SELECT * FROM fe_report_documents WHERE document_id=?', (did,)).fetchone()
        if old:
            if (old['shipment_id'], old['kind'], old['filename'], old['mime'], old['sha256']) != (sid, kind, filename, mime, digest):
                raise HTTPException(409, 'This document ID already holds a different upload.')
            return {k: old[k] for k in old.keys() if k != 'data'}
        counts = db.execute('SELECT COUNT(*),COALESCE(SUM(length),0) FROM fe_report_documents WHERE shipment_id=?', (sid,)).fetchone()
        if counts[0] >= MAX_DOCUMENTS or counts[1] + len(raw) > MAX_SHIPMENT_BYTES:
            raise HTTPException(413, 'Shipment paperwork limit reached (20 files / 50 MiB).')
        receipt = dict(document_id=did, shipment_id=sid, kind=kind, filename=filename, mime=mime, length=len(raw), sha256=digest, created_at=datetime.now(timezone.utc).isoformat())
        db.execute('INSERT INTO fe_report_documents VALUES(?,?,?,?,?,?,?,?,?)', (*receipt.values(), raw))
        return receipt


@router.get('/shipments/{shipment_id}/documents/{document_id}')
def download_document(shipment_id: UUID, document_id: UUID, store: ReportStore = Depends(get_store)):
    with store.connect() as db:
        row = db.execute('SELECT * FROM fe_report_documents WHERE shipment_id=? AND document_id=?', (str(shipment_id), str(document_id))).fetchone()
        if not row:
            raise HTTPException(404, 'Document not found.')
        suffix = Path(row['filename']).suffix.lower()
        return attachment(row['data'], f'{document_id}{suffix}', row['mime'])


@router.get('/shipments/{shipment_id}/packet.pdf')
def print_packet(shipment_id: UUID, rate_confirmation_id: UUID, signed_delivery_id: UUID, store: ReportStore = Depends(get_store)):
    """Separate grayscale print copy. Original uploads and their signatures remain unchanged.

    The uploader selects the signed paperwork; this does not verify a signature.
    Rasterization omits executable PDF actions, attachments and interactive forms.
    """
    import fitz
    with store.connect() as db:
        db.execute('BEGIN')
        require_shipment(db, str(shipment_id))
        documents=[]
        for did, kinds in [(rate_confirmation_id, {'rate_confirmation'}), (signed_delivery_id, {'bol','pod'})]:
            row=db.execute('SELECT * FROM fe_report_documents WHERE shipment_id=? AND document_id=?', (str(shipment_id),str(did))).fetchone()
            if not row:
                raise HTTPException(404, 'Selected shipment document not found.')
            if row['kind'] not in kinds:
                raise HTTPException(422, 'Select a rate confirmation and a separate signed BOL or proof of delivery.')
            if len(row['data']) != row['length'] or hashlib.sha256(row['data']).hexdigest() != row['sha256']:
                raise HTTPException(409, 'Stored document integrity check failed.')
            documents.append(dict(row))
    try:
        with fitz.open() as output:
            for row in documents:
                filetype={'application/pdf':'pdf','image/png':'png','image/jpeg':'jpeg'}[row['mime']]
                with fitz.open(stream=row['data'],filetype=filetype) as source:
                    if source.needs_pass:
                        raise HTTPException(415, 'Unlock the document before uploading a printable copy.')
                    if not len(source) or len(output)+len(source)>30:
                        raise HTTPException(413, 'Print packets support at most 30 pages. Download originals separately.')
                    for page in source:
                        rect=page.rect
                        if not all(math.isfinite(v) and 0<v<=14400 for v in [rect.width,rect.height]):
                            raise HTTPException(415, 'Unsupported document page dimensions.')
                        scale=min(150/72,2048/rect.width,2048/rect.height)
                        pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False,annots=True)
                        target=output.new_page(width=rect.width,height=rect.height)
                        target.insert_image(target.rect,stream=pix.tobytes('png'))
            output.set_metadata({'title':'FE Express shipment print copy','subject':'Grayscale print copy; original uploads retained. Signatures not independently verified.'})
            raw=output.tobytes(garbage=4,deflate=True)
            if len(raw)>32*1024*1024:
                raise HTTPException(413, 'Print packet exceeds 32 MiB. Download originals separately.')
    except HTTPException:
        raise
    except (RuntimeError,ValueError,KeyError,fitz.FileDataError):
        raise HTTPException(415, 'Cannot render this document. Download the original or upload a readable PDF, JPEG or PNG.') from None
    return attachment(raw, f'shipment-{shipment_id}-print.pdf', 'application/pdf')


def weekly(db, driver_id, week):
    driver = require_driver(db, driver_id)
    start = week - timedelta(days=week.weekday())
    end = start + timedelta(days=6)
    days = [json.loads(r['payload']) for r in db.execute('SELECT payload FROM fe_report_days WHERE driver_id=? AND log_date BETWEEN ? AND ? ORDER BY log_date', (driver_id, start.isoformat(), end.isoformat()))]
    shipments = []
    for row in db.execute('SELECT * FROM fe_report_shipments WHERE driver_id=? AND pickup_date<=? AND delivery_date>=? ORDER BY pickup_date,shipment_id', (driver_id, end.isoformat(), start.isoformat())):
        s = json.loads(row['payload'])
        s['documents'] = [dict(d) for d in db.execute('SELECT document_id,kind,filename,mime,length,sha256,created_at FROM fe_report_documents WHERE shipment_id=? ORDER BY created_at,document_id', (row['shipment_id'],))]
        kinds = {d['kind'] for d in s['documents']}
        required = [] if s['status'] == 'CANCELLED' else ['rate_confirmation'] + (['bol'] if s['status'] == 'DELIVERED' else [])
        s['missing_documents'] = [k for k in required if k not in kinds]
        shipments.append(s)
    fields = ['loaded_miles', 'deadhead_miles', 'driving_hours', 'other_duty_hours', 'fuel_gallons', 'fuel_cost', 'other_expenses']
    totals = {k: round(math.fsum(d[k] for d in days), 2) for k in fields}
    totals['total_miles'] = round(totals['loaded_miles'] + totals['deadhead_miles'], 2)
    totals['total_hours'] = round(totals['driving_hours'] + totals['other_duty_hours'], 2)
    totals['agreed_revenue'] = round(math.fsum(s['agreed_rate'] for s in shipments if s['status'] != 'CANCELLED' and start.isoformat() <= s['delivery_date'] <= end.isoformat()), 2)
    totals['average_fuel_price'] = round(totals['fuel_cost'] / totals['fuel_gallons'], 2) if totals['fuel_gallons'] else None
    totals['fuel_cost_per_mile'] = round(totals['fuel_cost'] / totals['total_miles'], 2) if totals['total_miles'] else None
    totals['revenue_per_mile'] = round(totals['agreed_revenue'] / totals['total_miles'], 2) if totals['total_miles'] else None
    totals['revenue_less_recorded_expenses'] = round(totals['agreed_revenue'] - totals['fuel_cost'] - totals['other_expenses'], 2)
    logged = {d['log_date'] for d in days}
    return dict(driver=driver, week_start=start.isoformat(), week_end=end.isoformat(), days=days, shipments=shipments, totals=totals,
                missing_log_dates=[(start + timedelta(days=i)).isoformat() for i in range(7) if (start + timedelta(days=i)).isoformat() not in logged],
                revenue_basis='Agreed rates counted once in the scheduled delivery week; not paid revenue. Revenue less recorded expenses excludes unrecorded costs and is not profit.',
                generated_at=datetime.now(timezone.utc).isoformat())


@router.get('/weekly')
def get_weekly(driver_id: str, week: date, store: ReportStore = Depends(get_store)):
    with store.connect() as db:
        db.execute('BEGIN')
        return weekly(db, driver_id, week)


def attachment(data, filename, mime):
    return Response(data, media_type=mime, headers={'Content-Disposition': f'attachment; filename="{filename}"', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


def csv_bytes(rows, columns):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(columns)
    for row in rows:
        values = []
        for key in columns:
            value = str(row.get(key, ''))
            if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
    return stream.getvalue().encode('utf-8-sig')


def report_html(report):
    esc = lambda v: html.escape(str(v))
    def table(rows, columns):
        return '<table><thead><tr>' + ''.join('<th>' + esc(c.replace('_', ' ')) + '</th>' for c in columns) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + esc(r.get(c, '')) + '</td>' for c in columns) + '</tr>' for r in rows) + '</tbody></table>'
    return ('<!doctype html><html><head><meta charset="utf-8"><title>FE Express weekly driver report</title><style>body{font:14px Arial;margin:28px;color:#111}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #aaa;padding:6px;text-align:left;overflow-wrap:anywhere}h1{font-size:24px}@media print{body{margin:0}tr{break-inside:avoid}}</style></head><body><h1>FE Express weekly driver report</h1><p>'
            + esc(report['driver']['full_name']) + ' | ' + esc(report['week_start']) + ' through ' + esc(report['week_end']) + '</p><p>' + esc(report['revenue_basis']) + '</p>'
            + table([report['totals']], ['total_miles','total_hours','fuel_gallons','fuel_cost','average_fuel_price','other_expenses','agreed_revenue','revenue_less_recorded_expenses'])
            + '<h2>Daily logs</h2>' + table(report['days'], ['log_date','unit','loaded_miles','deadhead_miles','driving_hours','other_duty_hours','fuel_gallons','fuel_cost','other_expenses','notes'])
            + '<p>Days without entries: ' + esc(', '.join(report['missing_log_dates']) or 'None') + '</p><h2>Shipment assignments &amp; paperwork</h2>'
            + table(report['shipments'], ['load_number','pickup_date','delivery_date','origin','destination','broker','agreed_rate','status','missing_documents','notes'])
            + '<p>Generated ' + esc(report['generated_at']) + '. Uploaded documents are included separately in the weekly ZIP.</p></body></html>').encode('utf8')


DAILY_COLUMNS = ['log_date','unit','loaded_miles','deadhead_miles','driving_hours','other_duty_hours','fuel_gallons','fuel_cost','other_expenses','notes']
SHIPMENT_COLUMNS = ['load_number','pickup_date','delivery_date','origin','destination','broker','agreed_rate','status','missing_documents','notes']


def report_pdf(report):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    styles = getSampleStyleSheet()
    stream = io.BytesIO()
    doc = SimpleDocTemplate(stream, title='FE Express weekly driver report', leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    def para(value, style='BodyText'):
        return Paragraph(html.escape(str(value)).replace('\n','<br/>'), styles[style])
    story = [para('FE Express weekly driver report','Title'), para(f'{report["driver"]["full_name"]} | {report["week_start"]} through {report["week_end"]}'), para(report['revenue_basis']), Spacer(1,12)]
    summary = [[para(key.replace('_',' ')), para('—' if value is None else value)] for key,value in report['totals'].items()]
    table = Table(summary, colWidths=[330,174])
    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.append(table)
    # Individual fields wrap over pages; long notes cannot create an unsplittable table row.
    for heading, records, columns in [('Daily logs',report['days'],DAILY_COLUMNS),('Shipment assignments & paperwork',report['shipments'],SHIPMENT_COLUMNS)]:
        story.extend([Spacer(1,12),para(heading,'Heading2')])
        if not records:
            story.append(para('No saved entries.'))
        for record in records:
            for key in columns:
                story.append(para(key.replace('_',' ') + ': ' + str(record.get(key,''))))
            story.append(Spacer(1,10))
    story.extend([para('Days without entries: ' + (', '.join(report['missing_log_dates']) or 'None')),para('Generated ' + report['generated_at'] + '. Original paperwork is available separately in the weekly ZIP.')])
    doc.build(story)
    return stream.getvalue()


def report_xlsx(report):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    book = Workbook()
    book.remove(book.active)
    def sheet(name, columns, rows):
        ws = book.create_sheet(name)
        ws.append(columns)
        for record in rows:
            ws.append([json.dumps(record.get(k,''),ensure_ascii=False) if isinstance(record.get(k), (list,dict)) else record.get(k) for k in columns])
        for row in ws:
            for cell in row:
                if isinstance(cell.value,str):
                    cell.data_type = 's'  # User text must never become an Excel formula.
                cell.alignment = Alignment(vertical='top',wrap_text=True)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 25
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
    summary = {'driver':report['driver']['full_name'],'driver_id':report['driver']['driver_id'],'week_start':report['week_start'],'week_end':report['week_end'],**report['totals'],'revenue_basis':report['revenue_basis'],'missing_log_dates':report['missing_log_dates'], 'editing_help':'Enter information in the Daily logs sheet. Blank dates have no saved log. Summary is a snapshot of saved records; offline edits do not sync to FE Express or recalculate this summary. Save daily entries in FE Express to update the website.'}
    sheet('Summary',['field','value'],[{'field':key,'value':value} for key,value in summary.items()])
    saved_days = {d['log_date']: d for d in report['days']}
    start = date.fromisoformat(report['week_start'])
    dates = [(start + timedelta(days=i)).isoformat() for i in range(7)]
    sheet('Daily logs',DAILY_COLUMNS,[saved_days.get(day, {'log_date':day}) for day in dates])
    daily_sheet = book['Daily logs']
    daily_sheet.column_dimensions['J'].width = 60
    daily_sheet.print_title_rows = '1:1'
    daily_sheet.sheet_properties.pageSetUpPr.fitToPage = True
    daily_sheet.page_setup.orientation = 'landscape'
    daily_sheet.page_setup.fitToWidth = 1
    daily_sheet.page_setup.fitToHeight = 0
    for row in daily_sheet.iter_rows(min_row=2, max_row=8, min_col=3, max_col=9):
        for cell in row:
            cell.number_format = '#,##0.00'
    sheet('Shipments',SHIPMENT_COLUMNS,report['shipments'])
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


@router.get('/weekly.pdf')
@router.get('/weekly.xlsx')
@router.get('/weekly.csv')
@router.get('/weekly.json')
def export_report(request: Request, driver_id: str, week: date, store: ReportStore = Depends(get_store)):
    with store.connect() as db:
        db.execute('BEGIN')
        report = weekly(db,driver_id,week)
    ext = request.url.path.rsplit('.',1)[-1]
    if ext == 'pdf':
        data, mime = report_pdf(report), 'application/pdf'
    elif ext == 'xlsx':
        data, mime = report_xlsx(report), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif ext == 'csv':
        columns = list(dict.fromkeys(['record_type',*DAILY_COLUMNS,*SHIPMENT_COLUMNS,'field','value']))
        rows = [{'record_type':'summary','field':key,'value':value} for key,value in {'driver':report['driver']['full_name'],'week_start':report['week_start'],'week_end':report['week_end'],**report['totals'],'revenue_basis':report['revenue_basis']}.items()]
        rows += [dict(record_type='daily',**d) for d in report['days']]
        rows += [dict(record_type='shipment',**s) for s in report['shipments']]
        data, mime = csv_bytes(rows,columns), 'text/csv'
    else:
        data, mime = json.dumps(report,ensure_ascii=False,indent=2).encode('utf8'), 'application/json'
    return attachment(data,f'fe-express-week-{report["week_start"]}.{ext}',mime)


@router.get('/weekly.html')
def export_html(driver_id: str, week: date, store: ReportStore = Depends(get_store)):
    with store.connect() as db:
        db.execute('BEGIN')
        report = weekly(db, driver_id, week)
        return attachment(report_html(report), f'fe-express-week-{report["week_start"]}.html', 'text/html')


@router.get('/weekly.zip')
def export_week(driver_id: str, week: date, store: ReportStore = Depends(get_store)):
    with store.connect() as db:
        db.execute('BEGIN')  # One consistent read snapshot for report and document bytes.
        report = weekly(db, driver_id, week)
        docs = [d for s in report['shipments'] for d in s['documents']]
        if len(docs) > 200 or sum(d['length'] for d in docs) > MAX_EXPORT_BYTES:
            raise HTTPException(413, 'Weekly paperwork is too large. Download individual documents instead.')
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('weekly_report.json', json.dumps(report, indent=2, ensure_ascii=False))
            z.writestr('weekly_report.html', report_html(report))
            z.writestr('daily_log.csv', csv_bytes(report['days'], ['log_date','unit','loaded_miles','deadhead_miles','driving_hours','other_duty_hours','fuel_gallons','fuel_cost','other_expenses','notes']))
            z.writestr('shipments.csv', csv_bytes(report['shipments'], ['shipment_id','driver_id','load_number','pickup_date','delivery_date','origin','destination','broker','agreed_rate','status','notes']))
            for s in report['shipments']:
                for d in s['documents']:
                    row = db.execute('SELECT data FROM fe_report_documents WHERE document_id=? AND shipment_id=?', (d['document_id'], s['shipment_id'])).fetchone()
                    if not row or hashlib.sha256(row['data']).hexdigest() != d['sha256']:
                        raise HTTPException(409, 'Stored document integrity check failed.')
                    z.writestr(f'shipments/{s["shipment_id"]}/{d["kind"]}-{d["document_id"]}{Path(d["filename"]).suffix.lower()}', row['data'])
        return attachment(stream.getvalue(), f'fe-express-week-{report["week_start"]}.zip', 'application/zip')
