"""Synthetic SQLite and provider-free tests; never import the production application."""
import ast
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import recdebut_workflow as w
from core import outbound_messaging_policy as policy


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(w, 'DB_PATH', tmp_path / 'workflow.db')
    app = FastAPI()
    app.include_router(w.router, prefix='/api/v1/recdebut')
    app.dependency_overrides[w.require_recdebut_access] = lambda: None
    with TestClient(app) as c:
        yield c


BASE = '/api/v1/recdebut/workflow'


def test_public_registration_hold_precedes_all_writes():
    tree=ast.parse((Path(__file__).resolve().parents[1] / 'routers/rec_debut_router.py').read_text(encoding='utf-8'))
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='register_athlete_endpoint')
    assert len(node.body)==1 and isinstance(node.body[0],ast.Raise)
    module=ast.Module(body=[ast.FunctionDef(name=node.name,args=node.args,body=node.body,decorator_list=[],returns=None)],type_ignores=[])
    # Retain actual signature but replace annotation symbols in the isolated namespace.
    from fastapi import HTTPException
    namespace={'HTTPException':HTTPException,'RegistrationRequest':dict}
    exec(compile(ast.fix_missing_locations(module),'<isolated registration hold>','exec'),namespace)
    with pytest.raises(HTTPException) as raised: namespace[node.name]({})
    assert raised.value.status_code==503


def save(c, kind, id, payload, revision=0, expected=200):
    response = c.put(f'{BASE}/records/{kind}/{id}', json={'revision': revision, 'actor': 'Synthetic staff', 'payload': payload})
    assert response.status_code == expected, response.text
    return response.json()


def prepared(c):
    save(c, 'family', 'family1', {'name': 'Synthetic household'})
    person = {'name': 'Synthetic Parent', 'family_id': 'family1', 'role': 'parent', 'relationship': 'verified',
              'phone': '+1 (616) 555-0101', 'source': 'Synthetic form', 'sms_permission': 'granted', 'permission_evidence': 'Synthetic permission date'}
    save(c, 'person', 'person1', person)
    save(c, 'draft', 'draft1', {'title': 'Synthetic draft', 'channel': 'sms', 'body': 'Hello {first_name}', 'person_ids': ['person1']})
    return person


def preview(c):
    r = c.get(BASE + '/drafts/draft1/preview')
    assert r.status_code == 200
    assert r.headers['cache-control'] == 'no-store'
    return r.json()['preview']


def review(c, p):
    return c.post(BASE + '/drafts/draft1/review', json={'actor': 'Synthetic reviewer', 'revision': p['revision'], 'expected_digest': p['digest']})


def test_private_access_denied_before_database(tmp_path, monkeypatch):
    monkeypatch.setattr(w, 'DB_PATH', tmp_path / 'absent.db')
    app=FastAPI();app.include_router(w.router, prefix='/api/v1/recdebut')
    with TestClient(app) as c:
        assert c.get(BASE).status_code == 403
    assert not w.DB_PATH.exists()


@pytest.mark.parametrize('kind,payload', [
    ('family', {'name': 'Synthetic family'}), ('person', {'name': 'Synthetic person'}),
    ('followup', {'title': 'Call requested', 'due': '2026-10-27', 'owner': 'Staff'}),
    ('draft', {'title': 'Draft', 'channel': 'email', 'body': 'Hello', 'person_ids': []}),
    ('service', {'title': 'Consultation', 'price_cents': 0}),
    ('delivery', {'title': 'Review film'}), ('worklog', {'title': 'Prepared draft', 'minutes': 15, 'expense_cents': 0})])
def test_persistent_records_and_history(client, kind, payload):
    save(client, kind, 'record1', payload)
    snapshot=client.get(BASE)
    assert snapshot.headers['cache-control'] == 'no-store'
    data=snapshot.json();assert data['tenant']=='recdebut' and not data['sending_enabled']
    assert data['records'][0]['payload']==payload
    assert data['events'][0]['actor']=='Synthetic staff'


def test_revision_conflict_preserves_original(client):
    save(client, 'family', 'a', {'name': 'Original'})
    save(client, 'family', 'a', {'name': 'Stale'}, expected=409)
    assert client.get(BASE).json()['records'][0]['payload']['name']=='Original'


@pytest.mark.parametrize('kind,payload', [
    ('family', {'name': 'X', 'tenant': 'other'}), ('family', {'name': ''}),
    ('person', {'name': 'X', 'family_id': 'missing'}), ('person', {'name':'X','role':'invented'}),
    ('person', {'name':'X','sms_permission':'granted'}), ('person', {'name':'X','phone':'garbage'}),
    ('worklog', {'title':'X','minutes':-1}), ('worklog', {'title':'X','minutes':True}),
    ('draft', {'title':'X','channel':'sms','person_ids':['a','a']}),
    ('draft', {'title':'X','channel':'sms','person_ids':['a']*101}),
    ('followup', {'title':'X','due':'yesterday'})])
def test_malformed_records_rejected(client, kind, payload):
    save(client,kind,'invalid',payload,expected=422)
    assert client.get(BASE).json()['records']==[]


def test_exact_review_is_not_send_authority(client):
    prepared(client);p=preview(client)
    assert p['reviewable'] and p['audience'][0]['message']=='Hello Synthetic'
    assert review(client,p).status_code==200
    assert not client.get(BASE).json()['sending_enabled']
    assert client.get(BASE).json()['events'][0]['action']=='review_recorded_not_send_authorization'


def test_changed_contact_invalidates_review(client):
    person=prepared(client);p=preview(client)
    save(client,'person','person1',{**person,'name':'Changed Parent'},revision=1)
    assert review(client,p).status_code==409


@pytest.mark.parametrize('name,expected', [
    ('  María   López ', 'Hi María,'), ("Anne-Marie O’Neil", 'Hi Anne-Marie,'),
    ('', 'Hello,'), ('   ', 'Hello,'), ('Unknown Parent', 'Hello,'),
    ('[First Name]', 'Hello,'), ('<script> Bad', 'Hello,')])
@pytest.mark.parametrize('token', ['{first_name}', '[First Name]', '[Parent First Name]'])
def test_personalized_greeting_and_missing_name(name, expected, token):
    rendered = w.personalize_message('Hi ' + token + ',\nVisit https://recdebut.com/', name)
    assert rendered['message'] == expected + '\nVisit https://recdebut.com/'
    assert rendered['greeting_fallback'] == (expected == 'Hello,')


def test_each_preview_uses_matching_contact_not_audience_order(client):
    person = prepared(client)
    save(client, 'person', 'person2', {**person, 'name': 'Jordan Parent', 'phone': '+16165550102'})
    save(client, 'draft', 'draft1', {'title': 'Review', 'channel': 'sms',
         'body': 'Hi [Parent First Name], watch https://youtu.be/YJoPHIWmvnQ',
         'person_ids': ['person2', 'person1']}, revision=1)
    p = preview(client)
    assert [(a['destination'], a['message'].split(',')[0]) for a in p['audience']] == [
        ('6165550102', 'Hi Jordan'), ('6165550101', 'Hi Synthetic')]
    assert p['reviewable'] and p['sending_enabled'] is False


def test_unresolved_non_name_placeholder_blocks_review(client):
    prepared(client)
    save(client, 'draft', 'draft1', {'title': 'Review', 'channel': 'sms',
         'body': 'Hi {first_name}, [Unsubscribe link]', 'person_ids': ['person1']}, revision=1)
    p = preview(client)
    assert not p['reviewable']
    assert 'Message personalization needs review' in p['audience'][0]['reasons']


@pytest.mark.parametrize('role,channel,allowed', [('athlete','email',True), ('coach','email',False),
    ('unknown','email',False), ('athlete','sms',False), ('parent','email',True)])
def test_personalization_preserves_channel_audience_rules(client, role, channel, allowed):
    person = prepared(client)
    save(client, 'person', 'person1', {**person, 'role': role, 'name': 'Unknown',
         'email': 'synthetic@example.invalid', 'email_permission': 'granted'}, revision=1)
    save(client, 'draft', 'draft1', {'title': 'Review', 'channel': channel,
         'body': 'Hi [First Name], learn more.', 'person_ids': ['person1']}, revision=1)
    p = preview(client)
    assert p['audience'][0]['message'] == 'Hello, learn more.'
    assert p['reviewable'] == allowed
    assert not p['sending_enabled']


def test_opt_out_invalidates_review_and_cannot_be_erased_by_contact_save(client):
    person=prepared(client);p=preview(client)
    save(client,'person','person1',{**person,'sms_permission':'denied'},revision=1)
    assert review(client,p).status_code==409
    save(client,'person','person1',person,revision=2)
    p=preview(client);assert not p['reviewable']
    assert 'Suppressed / opted out' in p['audience'][0]['reasons']
    assert review(client,p).status_code==422


def test_shared_destination_and_unknown_role_block_review(client):
    person=prepared(client)
    save(client,'person','person2',{**person,'name':'Other contact','role':'unknown'})
    save(client,'draft','draft1',{'title':'Draft','channel':'sms','body':'Hello {first_name}','person_ids':['person1','person2']},revision=1)
    p=preview(client);assert not p['reviewable']
    assert 'Shared destination: review relationship' in p['audience'][1]['reasons']
    assert 'Parent/guardian role required' in p['audience'][1]['reasons']


def test_manual_suppression_normalization(client):
    prepared(client)
    assert client.post(BASE+'/suppressions',json={'destination':'1-616-555-0101','reason':'Synthetic STOP','actor':'Staff'}).status_code==200
    assert not preview(client)['reviewable']


def test_hold_overrides_environment_activation(monkeypatch):
    monkeypatch.setenv(policy.RECDEBUT_OUTBOUND_FLAG,'true');monkeypatch.setenv(policy.RECDEBUT_POLLING_FLAG,'true')
    assert not policy.outbound_messaging_enabled('recdebut')
    assert not policy.recdebut_polling_enabled()


@pytest.mark.parametrize('name', ['track_email_open','track_email_click','short_sms_tracking_redirect'])
def test_unsigned_tracking_has_no_database_provider_or_arbitrary_redirect(name):
    tree=ast.parse((Path(__file__).resolve().parents[1]/'routers/rec_debut_router.py').read_text(encoding='utf-8'))
    node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name==name)
    source=ast.unparse(node)
    assert 'sqlite3' not in source and 'send_' not in source and 'requests.' not in source
    if name!='track_email_open':assert 'RedirectResponse(\'https://recdebut.com/all-registration/\'' in source


def test_retained_tables_untouched(client):
    import sqlite3
    client.get(BASE)
    with sqlite3.connect(w.DB_PATH) as db:db.execute('CREATE TABLE legacy_roster(id INTEGER, name TEXT)');db.execute("INSERT INTO legacy_roster VALUES(1,'Synthetic original')")
    save(client,'family','family1',{'name':'New family'})
    with sqlite3.connect(w.DB_PATH) as db:assert db.execute('SELECT * FROM legacy_roster').fetchall()==[(1,'Synthetic original')]
