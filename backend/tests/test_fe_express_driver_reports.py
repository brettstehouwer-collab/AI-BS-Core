"""Trusted application tests against temporary SQLite data, never worker execution."""
import io
import json
import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fe_express_driver_reports import ReportStore, router, get_store


@pytest.fixture
def api(tmp_path):
    store = ReportStore(tmp_path / 'test.sqlite')
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app), store


def daily(**changes):
    return dict(revision=0, unit='TEST-TRUCK', loaded_miles=120, deadhead_miles=30,
                driving_hours=3, other_duty_hours=1, fuel_gallons=10, fuel_cost=40,
                other_expenses=5, notes='Synthetic day', **changes)


def shipment(**changes):
    result=dict(revision=0, driver_id='OWNER-DEVIN', load_number='TEST-001',
                pickup_date='2026-10-26', delivery_date='2026-10-27',
                origin='Test origin', destination='Test receiver', broker='Test broker',
                agreed_rate=500, status='ASSIGNED', notes='Synthetic shipment', dispatch_id='')
    result.update(changes)
    return result


BASE='/driver-reports'
ID='11111111-1111-4111-8111-111111111111'
DOC='22222222-2222-4222-8222-222222222222'
PDF=b'%PDF-1.4\nsynthetic document for storage tests\n%%EOF'


def test_weekly_save_formats_keep_data_and_literal_spreadsheet_text(api):
    import fitz
    import openpyxl
    c, _ = api
    payload = daily()
    payload['notes'] = '=HYPERLINK("https://example.invalid") <signed> & safe'
    assert c.put(f'{BASE}/days/OWNER-DEVIN/2026-10-26', json=payload).status_code == 200
    query = '?driver_id=OWNER-DEVIN&week=2026-10-26'
    results = {ext: c.get(f'{BASE}/weekly.{ext}{query}') for ext in ['pdf','xlsx','csv','json']}
    for ext, response in results.items():
        assert response.status_code == 200, (ext, response.text[:100])
        assert response.headers['cache-control'] == 'no-store'
        assert f'.{ext}"' in response.headers['content-disposition']
    with fitz.open(stream=results['pdf'].content, filetype='pdf') as pdf:
        text = ''.join(page.get_text() for page in pdf)
        assert '120' in text and '<signed> & safe' in text
        assert 'Daily logs' in text and 'Shipment' in text
    wb = openpyxl.load_workbook(io.BytesIO(results['xlsx'].content))
    assert wb.sheetnames == ['Summary','Daily logs','Shipments']
    notes = list(wb['Daily logs'].values)[1][-1]
    assert notes == payload['notes']
    assert all(cell.data_type != 'f' for sheet in wb for row in sheet for cell in row)
    assert "'=HYPERLINK" in results['csv'].content.decode('utf-8-sig')
    assert results['json'].json()['days'][0]['notes'] == payload['notes']
    assert c.get(f'{BASE}/weekly.exe{query}').status_code == 404


def valid_pdf(pages=1):
    import fitz
    with fitz.open() as doc:
        for i in range(pages):
            page=doc.new_page()
            page.insert_text((72,72), 'SYNTHETIC paperwork page '+str(i+1), color=(1,0,0))
        return doc.tobytes()


def packet_setup(api, proof=None):
    c,store=api
    c.put(f'{BASE}/shipments/{ID}',json=shipment())
    second='33333333-3333-4333-8333-333333333333'
    for did,kind,data in [(DOC,'rate_confirmation',valid_pdf()),(second,'bol',proof or valid_pdf())]:
        assert c.put(f'{BASE}/shipments/{ID}/documents/{did}?kind={kind}',content=data,headers={'content-type':'application/pdf','X-File-Name':kind+'.pdf'}).status_code==200
    return c,store,dict(rate_confirmation_id=DOC,signed_delivery_id=second)


def test_packet_print_copy_is_grayscale_and_original_unchanged(api):
    import fitz
    c,_,params=packet_setup(api)
    original=c.get(f'{BASE}/shipments/{ID}/documents/{DOC}').content
    r=c.get(f'{BASE}/shipments/{ID}/packet.pdf',params=params)
    assert r.status_code==200 and r.headers['cache-control']=='no-store'
    with fitz.open(stream=r.content,filetype='pdf') as doc:
        assert len(doc)==2
        pix=doc[0].get_pixmap()
        pixels=memoryview(pix.samples)
        assert all(pixels[i]==pixels[i+1]==pixels[i+2] for i in range(0,len(pixels),3))
    assert c.get(f'{BASE}/shipments/{ID}/documents/{DOC}').content==original


def test_packet_rejects_wrong_roles_missing_and_corruption(api):
    c,store,params=packet_setup(api)
    url=f'{BASE}/shipments/{ID}/packet.pdf'
    assert c.get(url).status_code==422
    assert c.get(url,params={**params,'signed_delivery_id':DOC}).status_code==422
    assert c.get(url,params={**params,'rate_confirmation_id':params['signed_delivery_id']}).status_code==422
    assert c.get(url,params={**params,'signed_delivery_id':'44444444-4444-4444-8444-444444444444'}).status_code==404
    with store.connect() as db:
        db.execute('UPDATE fe_report_documents SET data=? WHERE document_id=?',(b'changed',DOC))
    assert c.get(url,params=params).status_code==409


@pytest.mark.parametrize('data,status',[(PDF,415),(None,413)])
def test_packet_invalid_or_excessive_pages(api,data,status):
    c,_,params=packet_setup(api,data if data else valid_pdf(31))
    assert c.get(f'{BASE}/shipments/{ID}/packet.pdf',params=params).status_code==status


def test_packet_image_proof_and_encrypted_pdf(api):
    import fitz
    from PIL import Image
    import hashlib
    c,store,params=packet_setup(api)
    image=io.BytesIO();Image.new('RGB',(600,800),'blue').save(image,format='PNG')
    with store.connect() as db:
        raw=image.getvalue()
        db.execute('UPDATE fe_report_documents SET data=?,mime=?,length=?,sha256=? WHERE document_id=?',(raw,'image/png',len(raw),hashlib.sha256(raw).hexdigest(),params['signed_delivery_id']))
    r=c.get(f'{BASE}/shipments/{ID}/packet.pdf',params=params)
    assert r.status_code==200
    with fitz.open(stream=r.content,filetype='pdf') as doc: assert len(doc)==2
    with fitz.open(stream=valid_pdf(),filetype='pdf') as doc:
        raw=doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='synthetic-owner',user_pw='synthetic-password')
    with store.connect() as db:
        db.execute('UPDATE fe_report_documents SET data=?,mime=?,length=?,sha256=? WHERE document_id=?',(raw,'application/pdf',len(raw),hashlib.sha256(raw).hexdigest(),params['signed_delivery_id']))
    assert c.get(f'{BASE}/shipments/{ID}/packet.pdf',params=params).status_code==415


def test_weekly_totals_weighted_fuel_and_empty_days(api):
    c,_=api
    assert c.put(f'{BASE}/days/OWNER-DEVIN/2026-10-26',json=daily()).status_code==200
    day=daily();day.update(fuel_gallons=30,fuel_cost=150,loaded_miles=60,deadhead_miles=10)
    assert c.put(f'{BASE}/days/OWNER-DEVIN/2026-10-27',json=day).status_code==200
    assert c.put(f'{BASE}/shipments/{ID}',json=shipment()).status_code==200
    r=c.get(BASE+'/weekly',params={'driver_id':'OWNER-DEVIN','week':'2026-10-28'}).json()
    assert r['week_start']=='2026-10-26' and r['week_end']=='2026-11-01'
    assert r['totals']['total_miles']==220
    assert r['totals']['total_hours']==8
    assert r['totals']['average_fuel_price']==4.75  # weighted, not (4+5)/2
    assert r['totals']['fuel_cost_per_mile']==0.86
    assert r['totals']['agreed_revenue']==500
    assert r['totals']['revenue_less_recorded_expenses']==300
    assert r['missing_log_dates']==['2026-10-28','2026-10-29','2026-10-30','2026-10-31','2026-11-01']


def test_revision_conflict_preserves_original_and_duplicate_submission(api):
    c,_=api; url=f'{BASE}/days/OWNER-DEVIN/2026-10-26'
    assert c.put(url,json=daily()).json()['revision']==1
    assert c.put(url,json=daily()).status_code==409
    edit=daily();edit.update(revision=1,notes='Updated')
    assert c.put(url,json=edit).json()['revision']==2
    assert c.put(url,json=edit).status_code==409
    assert c.get(BASE+'/weekly',params={'driver_id':'OWNER-DEVIN','week':'2026-10-26'}).json()['days'][0]['notes']=='Updated'


@pytest.mark.parametrize('field,value', [('fuel_cost',-1),('fuel_cost',float('inf')),('driving_hours',25),('fuel_gallons',0)])
def test_invalid_daily_values(api,field,value):
    c,_=api;p=daily();p[field]=value
    if value==float('inf'):
        # JSON encoding rejects Infinity in requests; pass raw invalid JSON at the API boundary.
        response=c.put(f'{BASE}/days/OWNER-DEVIN/2026-10-26',content=json.dumps(p),headers={'content-type':'application/json'})
    else:response=c.put(f'{BASE}/days/OWNER-DEVIN/2026-10-26',json=p)
    assert response.status_code==422


def test_hours_total_and_unknown_driver_and_invalid_dates(api):
    c,_=api;p=daily();p.update(driving_hours=20,other_duty_hours=10)
    assert c.put(f'{BASE}/days/OWNER-DEVIN/2026-10-26',json=p).status_code==422
    assert c.put(f'{BASE}/days/missing/2026-10-26',json=daily()).status_code==404
    assert c.get(BASE+'/weekly?driver_id=OWNER-DEVIN&week=bad').status_code==422
    assert c.put(f'{BASE}/shipments/{ID}',json=shipment(delivery_date='2026-10-25')).status_code==422


def test_shipment_documents_completeness_download_and_weekly_zip(api):
    c,_=api
    assert c.put(f'{BASE}/shipments/{ID}',json=shipment(status='DELIVERED')).status_code==200
    put=f'{BASE}/shipments/{ID}/documents/{DOC}?kind=rate_confirmation'
    headers={'Content-Type':'application/pdf','X-File-Name':'rate.pdf'}
    assert c.put(put,content=PDF,headers=headers).status_code==200
    assert c.put(put,content=PDF,headers=headers).status_code==200  # Same exact upload is idempotent.
    assert c.put(put,content=PDF+b'changed',headers=headers).status_code==409
    week=c.get(BASE+'/weekly?driver_id=OWNER-DEVIN&week=2026-10-26').json()
    packet=week['shipments'][0]
    assert packet['missing_documents']==['bol'] and len(packet['documents'])==1
    doc=c.get(f'{BASE}/shipments/{ID}/documents/{DOC}')
    assert doc.content==PDF and doc.headers['content-disposition'].startswith('attachment;')
    assert doc.headers['cache-control']=='no-store'
    export=c.get(BASE+'/weekly.zip?driver_id=OWNER-DEVIN&week=2026-10-26')
    assert export.status_code==200
    with zipfile.ZipFile(io.BytesIO(export.content)) as z:
        assert {'weekly_report.json','daily_log.csv','shipments.csv','weekly_report.html'}<=set(z.namelist())
        assert any(z.read(n)==PDF for n in z.namelist() if n.startswith('shipments/'))
        assert all('..' not in n and not n.startswith('/') for n in z.namelist())


@pytest.mark.parametrize('filename,content,mime', [('../bad.pdf',PDF,'application/pdf'),('bad.html',b'<script>x</script>','text/html'),('fake.pdf',b'not a pdf','application/pdf'),('evil%0A.pdf',PDF,'application/pdf')])
def test_reject_bad_uploads_without_storage(api,filename,content,mime):
    c,store=api;c.put(f'{BASE}/shipments/{ID}',json=shipment())
    r=c.put(f'{BASE}/shipments/{ID}/documents/{DOC}?kind=bol',content=content,headers={'X-File-Name':filename,'Content-Type':mime})
    assert r.status_code in (400,415)
    with sqlite3.connect(store.path) as db:assert db.execute('SELECT COUNT(*) FROM fe_report_documents').fetchone()[0]==0


def test_size_and_document_count_limits(api,monkeypatch):
    import fe_express_driver_reports as module
    c,_=api;c.put(f'{BASE}/shipments/{ID}',json=shipment())
    monkeypatch.setattr(module,'MAX_FILE_BYTES',20)
    assert c.put(f'{BASE}/shipments/{ID}/documents/{DOC}?kind=bol',content=PDF,headers={'X-File-Name':'x.pdf','Content-Type':'application/pdf'}).status_code==413
    monkeypatch.setattr(module,'MAX_FILE_BYTES',1000);monkeypatch.setattr(module,'MAX_DOCUMENTS',0)
    assert c.put(f'{BASE}/shipments/{ID}/documents/{DOC}?kind=bol',content=PDF,headers={'X-File-Name':'x.pdf','Content-Type':'application/pdf'}).status_code==413


def test_week_spanning_shipment_counts_revenue_once_and_zero_denominators(api):
    c,_=api;c.put(f'{BASE}/shipments/{ID}',json=shipment(pickup_date='2026-10-25'))
    a=c.get(BASE+'/weekly?driver_id=OWNER-DEVIN&week=2026-10-19').json()
    b=c.get(BASE+'/weekly?driver_id=OWNER-DEVIN&week=2026-10-26').json()
    assert len(a['shipments'])==len(b['shipments'])==1
    assert a['totals']['agreed_revenue']==0 and b['totals']['agreed_revenue']==500
    assert b['totals']['average_fuel_price'] is None and b['totals']['revenue_per_mile'] is None


def test_export_escapes_html_and_csv_formula(api):
    c,_=api;c.put(f'{BASE}/shipments/{ID}',json=shipment(load_number='=2+2',notes='<script>alert(1)</script>'))
    response=c.get(BASE+'/weekly.zip?driver_id=OWNER-DEVIN&week=2026-10-26')
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        assert "'=2+2" in z.read('shipments.csv').decode('utf8')
        text=z.read('weekly_report.html').decode('utf8')
        assert '<script>' not in text and '&lt;script&gt;' in text


def test_existing_driver_profiles_reused_and_read_only(api):
    c,store=api;c.get(BASE+'/drivers')
    with sqlite3.connect(store.path) as db:
        db.execute('CREATE TABLE fe_express_contractor_drivers(driver_id TEXT, full_name TEXT)')
        db.execute('INSERT INTO fe_express_contractor_drivers VALUES (?,?)',('SYNTHETIC','Synthetic driver'))
    r=c.get(BASE+'/drivers').json()['drivers']
    assert {'driver_id':'SYNTHETIC','full_name':'Synthetic driver'} in r
    assert c.put(f'{BASE}/days/SYNTHETIC/2026-10-26',json=daily()).status_code==200


def test_routes_inherit_fe_authorization():
    import ast
    source=(Path(__file__).resolve().parents[1]/'routers/fe_express_router.py').read_text(encoding='utf8')
    tree=ast.parse(source)
    assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='include_router' and any(isinstance(a,ast.Name) and a.id=='driver_reports_router' for a in n.args) for n in ast.walk(tree))
    assert 'dependencies=[Depends(require_fe_express_access)]' in source


def test_concurrent_stale_writes_have_one_winner(api):
    from concurrent.futures import ThreadPoolExecutor
    c,_=api
    def save(_):return c.put(f'{BASE}/days/OWNER-DEVIN/2026-10-26',json=daily()).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save,range(2)))==[200,409]


def test_package_total_bound_and_private_cache(api,monkeypatch):
    import fe_express_driver_reports as module
    c,_=api;c.put(f'{BASE}/shipments/{ID}',json=shipment())
    monkeypatch.setattr(module,'MAX_SHIPMENT_BYTES',len(PDF)-1)
    assert c.put(f'{BASE}/shipments/{ID}/documents/{DOC}?kind=bol',content=PDF,headers={'X-File-Name':'x.pdf','Content-Type':'application/pdf'}).status_code==413
    monkeypatch.setattr(module,'MAX_SHIPMENT_BYTES',len(PDF))
    assert c.put(f'{BASE}/shipments/{ID}/documents/{DOC}?kind=bol',content=PDF,headers={'X-File-Name':'x.pdf','Content-Type':'application/pdf'}).status_code==200
    monkeypatch.setattr(module,'MAX_EXPORT_BYTES',len(PDF)-1)
    assert c.get(BASE+'/weekly.zip?driver_id=OWNER-DEVIN&week=2026-10-26').status_code==413
    assert c.get(BASE+'/weekly?driver_id=OWNER-DEVIN&week=2026-10-26').headers['cache-control']=='no-store'
def test_driver_excel_contains_editable_seven_day_template_without_creating_logs(api):
    from openpyxl import load_workbook
    c, _ = api
    payload = daily()
    assert c.put(f'{BASE}/days/OWNER-DEVIN/2026-10-28', json=payload).status_code == 200
    response = c.get(BASE + '/weekly.xlsx?driver_id=OWNER-DEVIN&week=2026-10-28')
    assert response.status_code == 200
    book = load_workbook(io.BytesIO(response.content))
    rows = list(book['Daily logs'].values)
    assert [r[0] for r in rows[1:]] == ['2026-10-26','2026-10-27','2026-10-28','2026-10-29','2026-10-30','2026-10-31','2026-11-01']
    assert rows[1][2] is None  # Blank day is not a recorded zero-mile day.
    assert rows[3][2] == payload['loaded_miles']
    assert not book['Daily logs'].protection.sheet
    assert book['Daily logs'].freeze_panes == 'A2'
    assert 'do not sync' in str(dict(book['Summary'].values)['editing_help'])
    saved = c.get(BASE + '/weekly?driver_id=OWNER-DEVIN&week=2026-10-28').json()
    assert len(saved['days']) == 1 and len(saved['missing_log_dates']) == 6

