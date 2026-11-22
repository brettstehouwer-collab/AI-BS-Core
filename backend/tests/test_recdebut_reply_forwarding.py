"""Temporary ledgers and fake IONOS transports. Never opens a real inbox."""
import asyncio
import copy
import email
import json
import re
import threading
from email.message import EmailMessage

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
import recdebut_workflow as w
import recdebut_delivery as d
import recdebut_email_unsubscribe as intake
import recdebut_reply_forwarding as f


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(w,'DB_PATH',tmp_path/'mail.db')
    monkeypatch.setattr(f,'load_personal_contacts',lambda:(set(),set()))
    monkeypatch.setattr(intake,'load_personal_contacts',lambda:(set(),set()))
    p = {'enabled':True,'configured':True,'host':'imap.ionos.com','port':'993','user':f.ACCOUNT,
         'folder':'INBOX','password':'fake','digest':'stable',
         'smtp':{'provider':'smtp','sender':f.ACCOUNT,'copy_to':f.STAFF,'blockers':[]}}
    monkeypatch.setattr(f,'profile',lambda:copy.deepcopy(p))
    sent=[]
    def smtp(profile,message,destination,before):
        before(); sent.append((message,destination))
        return {'state':'ACCEPTED','receipt_id':message['Message-ID']}
    monkeypatch.setattr(d,'submit_smtp',smtp)
    plan={'id':'plan','channel':'email','recipients':[{'person_id':'athlete','destination':'avery@example.org'}]}
    with w.connect() as db:
        d.schema(db); f.schema(db)
        db.execute('CREATE TABLE rec_debut_athletes(id INTEGER,name TEXT,email TEXT,phone TEXT)')
        db.execute('INSERT INTO rec_debut_athletes VALUES(1,?,?,?)',('Avery Jones','avery@example.org','6165550101'))
        db.execute('INSERT INTO recdebut_send_plans VALUES(?,?,?,?,?)',('plan',json.dumps(plan),w.digest(plan),'COMPLETED',w.now()))
        db.execute('INSERT INTO recdebut_send_attempts VALUES(?,?,?,?,?,?)',('attempt','plan','athlete','ACCEPTED','<campaign@example.org>',w.now()))
    return p,sent


def reply(sender='avery@example.org', ancestor='<campaign@example.org>', mid='<reply@example.org>',body='Please send details.'):
    msg=EmailMessage();msg['From']=sender;msg['To']=f.ACCOUNT;msg['Subject']='Re: Get noticed'
    msg['Message-ID']=mid;msg['In-Reply-To']=ancestor;msg.set_content(body)
    return msg


class Mail:
    def __init__(self,messages,validity=1):
        self.messages={i:m.as_bytes() for i,m in messages.items()};self.validity=validity;self.body_reads=[];self.fetches=[]
    def response(self,name):
        return name,[str(self.validity if name=='UIDVALIDITY' else max(self.messages,default=0)+1).encode()]
    def uid(self,op,*args):
        if op=='search':
            lo,hi=map(int,args[-1].split()[-1].split(':'))
            return 'OK',[b' '.join(str(i).encode() for i in sorted(self.messages) if lo<=i<=hi)]
        assert op=='fetch' and 'BODY.PEEK[' in args[1]
        uid=int(args[0]);self.fetches.append(uid);raw=self.messages[uid]
        if 'HEADER.FIELDS' in args[1]: data=raw.split(b'\n\n',1)[0]+b'\n\n'
        else: self.body_reads.append(uid);data=raw
        limit=int(re.search(r'<0\.(\d+)>',args[1])[1]);data=data[:limit]
        return 'OK',[(f'1 (UID {uid} RFC822.SIZE {len(raw)} BODY[] {{{len(data)}}}'.encode(),data),b')']


def states():
    with w.connect() as db:return [dict(r) for r in db.execute('SELECT * FROM recdebut_reply_copies')]


def test_exact_reply_forwards_only_once_and_no_athlete_envelope(setup):
    p,sent=setup;mail=Mail({1:reply(),2:reply()})
    result=f.sync_mailbox(mail,p)
    assert result['status']=='scanned' and result['accepted']==1 and result['duplicate']==1
    assert sent[0][1]==f.STAFF and sent[0][0]['Reply-To']=='avery@example.org'
    assert f.sync_mailbox(mail,p)['scanned']==0
    assert len(sent)==1 and states()[0]['state']=='ACCEPTED'
    assert 'Please send details.' not in w.DB_PATH.read_bytes().decode(errors='ignore')


@pytest.mark.parametrize('kind',['wrong_sender','wrong_ancestor','not_accepted','auto','coach','personal','linked_coach','linked_personal','self','no_id'])
def test_unrelated_or_excluded_headers_never_fetch_body(setup,monkeypatch,kind):
    p,sent=setup;msg=reply()
    if kind=='wrong_sender':msg.replace_header('From','someone@example.org')
    if kind=='wrong_ancestor':msg.replace_header('In-Reply-To','<else@example.org>')
    if kind=='not_accepted':
        with w.connect() as db:db.execute("UPDATE recdebut_send_attempts SET state='UNCERTAIN'")
    if kind=='auto':msg['Auto-Submitted']='auto-replied'
    if kind=='self':msg.replace_header('From',f.ACCOUNT)
    if kind=='no_id':del msg['Message-ID']
    if kind=='personal':monkeypatch.setattr(f,'load_personal_contacts',lambda:(set(),{'avery@example.org'}))
    if kind=='linked_personal':
        monkeypatch.setattr(f,'load_personal_contacts',lambda:(set(),{'private@example.org'}))
        with w.connect() as db:
            db.execute('INSERT INTO rec_debut_athletes VALUES(2,?,?,?)',('Avery Jones','private@example.org',''))
    if kind in ('coach','linked_coach'):
        with w.connect() as db:
            db.execute('CREATE TABLE rec_debut_coaches(coach_name TEXT,coach_email TEXT,coach_phone TEXT)')
            db.execute('INSERT INTO rec_debut_coaches VALUES(?,?,?)',('Coach Jones','avery@example.org' if kind=='coach' else 'coach@example.org','6165550101'))
    mail=Mail({1:msg});result=f.sync_mailbox(mail,p)
    assert result['status']=='scanned' and not sent and not mail.body_reads


def test_uncertain_claim_is_never_retried_after_uidvalidity_change(setup,monkeypatch):
    p,sent=setup
    def fail(*args):raise OSError('private provider details')
    monkeypatch.setattr(d,'submit_smtp',fail)
    assert f.sync_mailbox(Mail({1:reply()}),p)['uncertain']==1
    assert f.sync_mailbox(Mail({1:reply()},validity=2),p)['duplicate']==1
    assert states()[0]['state']=='UNCERTAIN' and 'private provider' not in json.dumps(states())


@pytest.mark.parametrize('change',['config','privacy','ancestor','lease','stop'])
def test_final_submission_rechecks_all_authority(setup,monkeypatch,change):
    p,sent=setup;stop=threading.Event()
    def smtp(profile,message,destination,before):
        if change=='config':monkeypatch.setattr(f,'profile',lambda:{**p,'digest':'changed'})
        if change=='privacy':monkeypatch.setattr(f,'load_personal_contacts',lambda:(set(),{'avery@example.org'}))
        if change=='ancestor':
            with w.connect() as db:db.execute("UPDATE recdebut_send_attempts SET state='UNCERTAIN'")
        if change=='lease':
            with w.connect() as db:db.execute('UPDATE recdebut_reply_progress SET lease_until=0')
        if change=='stop':stop.set()
        before();sent.append(message)
        return {'state':'ACCEPTED'}
    monkeypatch.setattr(d,'submit_smtp',smtp)
    result=f.sync_mailbox(Mail({1:reply()}),p,stop=stop)
    assert not sent and states()[0]['state'] in ('BLOCKED','UNCERTAIN')


def test_attachments_pruned_and_capabilities_redacted(setup):
    p,sent=setup;msg=reply()
    msg.set_content('<p>My visible reply</p>',subtype='html')
    private=EmailMessage();private.set_content('PRIVATE ATTACHED MESSAGE SENTINEL')
    msg.add_attachment(private)
    msg.add_attachment(b'PRIVATE FILE SENTINEL',maintype='application',subtype='octet-stream',filename='private.txt')
    assert f.sync_mailbox(Mail({1:msg}),p)['accepted']==1
    text=sent[0][0].get_content()
    assert 'My visible reply' in text and 'PRIVATE' not in text
    raw=reply(body='Thanks https://recdebut-recruit.org/api/v1/recdebut/workflow/unsubscribe/abc').as_bytes()
    assert '/unsubscribe/' not in f.safe_body(raw)


def test_stop_suppressed_before_staff_copy_without_acknowledgement(setup):
    p,sent=setup
    assert f.sync_mailbox(Mail({1:reply(body='STOP')}),p)['accepted']==1
    with w.connect() as db:assert db.execute('SELECT destination FROM recdebut_suppressions').fetchone()[0]=='avery@example.org'
    assert len(sent)==1 and sent[0][1]==f.STAFF


def test_oversize_reply_retained_for_review_and_new_mail_not_stalled(setup):
    p,sent=setup
    result=f.sync_mailbox(Mail({1:reply(body='x'*300000),2:reply(mid='<new@example.org>')}),p)
    assert result['oversize']==1 and result['accepted']==1 and result['last_uid']==2
    assert any(r['code']=='reply_exceeds_read_limit' for r in states())


def test_live_snapshot_authenticated_and_does_not_touch_provider(setup):
    app=FastAPI();app.include_router(w.router,prefix='/api/v1/recdebut')
    with TestClient(app) as client:assert client.get('/api/v1/recdebut/workflow/email/live').status_code==403
    app.dependency_overrides[w.require_recdebut_access]=lambda:None
    with TestClient(app) as client:
        result=client.get('/api/v1/recdebut/workflow/email/live')
        assert result.status_code==200 and result.headers['cache-control']=='no-store'
        data=result.json();assert data['primary']=={'ACCEPTED':1} and data['outgoing_copies_missing']==1
        assert data['delivery_confirmation'] is None and 'password' not in result.text


def test_direct_athlete_email_needs_permission_but_no_fabricated_parent(setup):
    with w.connect() as db:
        person={'name':'Avery Jones','role':'athlete','email':'avery@example.org','source':'Tournament terms'}
        db.execute('INSERT INTO recdebut_workflow VALUES(?,?,?,?,?)',('direct','person',1,json.dumps(person),w.now()))
        draft={'channel':'email','body':'Hi {first_name}, welcome.','person_ids':['direct']}
        row={'id':'draft','revision':1,'payload':json.dumps(draft)}
        reasons=w.draft_preview(db,row)['audience'][0]['reasons']
        assert reasons==['Channel permission unconfirmed']
        person.update(email_permission='granted',permission_evidence='Original organizer email and terms reference')
        db.execute('UPDATE recdebut_workflow SET payload=? WHERE id=?',(json.dumps(person),'direct'))
        assert w.draft_preview(db,row)['reviewable']
        person['role']='parent'
        db.execute('UPDATE recdebut_workflow SET payload=? WHERE id=?',(json.dumps(person),'direct'))
        assert 'Family relationship unverified' in w.draft_preview(db,row)['audience'][0]['reasons']


def test_poll_shutdown_revokes_and_joins_worker(setup,monkeypatch):
    started=threading.Event();finished=threading.Event()
    def worker(stop):
        started.set();assert stop.wait(3);finished.set();return {'status':'stopped'}
    monkeypatch.setattr(f,'run_once',worker)
    async def exercise():
        task=asyncio.create_task(f.poll_loop())
        await asyncio.to_thread(started.wait,2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert finished.is_set()
    asyncio.run(exercise())


def test_connector_selects_readonly_and_continues_past_legacy_body_prefix_warning(setup,monkeypatch):
    p,sent=setup;calls=[]
    class Connection:
        def __init__(self,*args,**kwargs):calls.append(('connect',args,kwargs['timeout']))
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def login(self,user,password):calls.append(('login',user))
        def select(self,folder,readonly=False):calls.append(('select',folder,readonly));return 'OK',[]
    monkeypatch.setattr(f.imaplib,'IMAP4_SSL',Connection)
    monkeypatch.setattr(intake,'sync_receive_only_mailbox',lambda *a:{'success':False,'status':'body_prefix_incomplete','email_opt_outs_processed':0})
    monkeypatch.setattr(f,'sync_mailbox',lambda *a,**k:{'status':'scanned','scanned':0})
    result=f.run_once()
    assert result['status']=='scanned' and result['opt_out_warning']=='body_prefix_incomplete'
    assert ('select','INBOX',True) in calls and not sent


def test_active_lease_prevents_second_worker(setup):
    p,sent=setup
    with w.connect() as db:
        db.execute('INSERT INTO recdebut_reply_progress VALUES(?,?,?,?,?,?)',
                   (w.digest([p['host'],p['user'],p['folder']]),'1',0,'other',f.time.time()+180,w.now()))
    mail=Mail({1:reply()})
    assert f.sync_mailbox(mail,p)['status']=='mailbox_busy' and not mail.fetches and not sent


@pytest.mark.parametrize('recover',[True,False])
def test_worker_error_recovery_or_two_strike_pause(setup,monkeypatch,recover):
    calls=[];sleeps=[]
    def worker(stop):
        calls.append(1)
        if len(calls)==1 or not recover:raise f.sqlite3.OperationalError('private diagnostic')
        return {'status':'scanned'}
    async def delay(seconds):
        sleeps.append(seconds)
        if len(sleeps)==3:raise asyncio.CancelledError()
    monkeypatch.setattr(f,'run_once',worker)
    monkeypatch.setattr(f.asyncio,'sleep',delay)
    with pytest.raises(asyncio.CancelledError):asyncio.run(f.poll_loop())
    assert len(calls)==(3 if recover else 2)
    with w.connect() as db:
        row=db.execute('SELECT * FROM recdebut_reply_connector').fetchone()
        assert row['status']==('worker_failed' if recover else 'paused_after_repeated_errors')
        assert 'private diagnostic' not in str(dict(row))


def test_connector_refreshes_consumed_imap_response_identifiers(setup,monkeypatch):
    p,sent=setup
    class Connection(Mail):
        def __init__(self,*args,**kwargs):super().__init__({});self.responses={};self.selections=0
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def login(self,*args):return 'OK',[]
        def select(self,folder,readonly=False):
            assert readonly is True
            self.selections+=1;self.responses={'UIDVALIDITY':('UIDVALIDITY',[b'1']),'UIDNEXT':('UIDNEXT',[b'1'])}
            return 'OK',[]
        def response(self,name):return self.responses.pop(name,(name,[None]))
    connection=Connection()
    monkeypatch.setattr(f.imaplib,'IMAP4_SSL',lambda *a,**k:connection)
    def optouts(mail,*args):
        assert intake._response_number(mail,'UIDVALIDITY')==1
        assert intake._response_number(mail,'UIDNEXT')==1
        return {'success':True,'status':'scanned','email_opt_outs_processed':0}
    monkeypatch.setattr(intake,'sync_receive_only_mailbox',optouts)
    result=f.run_once()
    assert result['status']=='scanned'
    assert connection.selections==2 and not sent
