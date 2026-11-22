"""Actual authenticated proposal fixture; no proposed code/checks are executed."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,os,time,uuid
from dotenv import dotenv_values
import requests

ROOT=Path(r'C:\AI-BS');cp=ROOT/'backups/retained_proposal_5_329_46_20261024T141425139154Z'
config=dict(os.environ)
for path in (ROOT/'.env',ROOT/'backend/.env'):
    if path.is_file():config.update({k:v for k,v in dotenv_values(path).items() if v is not None})
headers={'X-Admin-Key':config['AI_BS_ADMIN_KEY'],'X-Client-ID':'stehouwer_publishing','Connection':'close'}
request_id='aee4d15396514b7884c7133f37a023be';plan_id='86c02dd0e2904fe39b6b26a83957f886'
base=f'/api/chat/coding-tasks/preparations/{request_id}/plans/{plan_id}'
proposal_id=uuid.uuid4().hex
report={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'checking','checks':[],
        'scope':'Existing retained source45 synthetic Python/JavaScript inputs; actual source46 model proposal only. No execution, original promotion, browser or VM.',
        'request_id':request_id,'plan_id':plan_id,'proposal_id':proposal_id}
session=requests.Session();session.trust_env=False
def check(name,passed,**evidence):
    report['checks'].append({'name':name,'passed':bool(passed),**evidence});assert passed,name
def call(port,method,path,auth=headers,body=None,timeout=15):
    return session.request(method,f'http://127.0.0.1:{port}'+path,headers=auth,json=body,timeout=(5,timeout))
try:
    original_cp=ROOT/'backups/planning_controls_5_329_45_20261024T131228359055Z'
    fixture=original_cp/'live_inputs'
    originals={p.relative_to(ROOT).as_posix():p.read_bytes() for p in fixture.rglob('*') if p.is_file()}
    check('Exactly four original synthetic source/check files',len(originals)==4)
    operations=[('GET',base+'/proposal-review',None),('POST',base+'/proposals',{'proposal_id':proposal_id,'reviewed_plan_sha256':'0'*64}),
                ('GET',base+'/proposals/'+proposal_id,None),('POST',base+'/proposals/'+proposal_id+'/recover',None),
                ('POST',base+'/proposals/'+proposal_id+'/cancel',None)]
    for port in (8080,8000):
        for label,auth in [('anonymous',{}),('invalid',{'X-Admin-Key':'invalid-proposal-fixture-key'})]:
            for method,path,body in operations:
                response=call(port,method,path,auth=auth,body=body)
                check(f'{port} {label} denied {method} {path.rsplit("/",1)[-1]}',response.status_code in (401,403),http=response.status_code)
        response=call(port,'GET',base+'/proposal-review')
        check(f'{port} authentic retained-plan review',response.status_code==200,http=response.status_code)
        review=response.json()
        check(f'{port} review confirms full source and no execution/apply',review['state']=='PLAN_REVIEW_READY' and review['source_complete'] is True
              and review['execution_authorized'] is False and review['apply_authorized'] is False and review['verification_status']=='not_run')
    digest=review['reviewed_plan_sha256']
    report['reviewed_plan_sha256']=digest
    check('Reviewed file roles remain exactly four originals',{f['path'] for f in review['files']}==set(originals))
    wrong=call(8000,'POST',base+'/proposals',body={'proposal_id':proposal_id,'reviewed_plan_sha256':'0'*64})
    check('Stale reviewed-plan digest rejected before inference',wrong.status_code==409,http=wrong.status_code)
    extra=call(8000,'POST',base+'/proposals',body={'proposal_id':proposal_id,'reviewed_plan_sha256':digest,'owner':'forged'})
    check('Forged proposal authority rejected',extra.status_code==422,http=extra.status_code)
    print(json.dumps({'status':'real_model_proposal_started','checks_passed':len(report['checks']),'proposal_id':proposal_id}),flush=True)
    started=time.monotonic()
    response=call(8000,'POST',base+'/proposals',body={'proposal_id':proposal_id,'reviewed_plan_sha256':digest},timeout=105)
    report['elapsed_seconds']=round(time.monotonic()-started,3)
    check('Actual proposal API completed',response.status_code==200,http=response.status_code)
    result=response.json()
    with (cp/'live_public_proposal.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
    report['proposal_state']=result.get('state');report['error_code']=result.get('error_code')
    check('Actual existing model produced a retained proposal',result.get('state')=='PROPOSAL_READY',state=result.get('state'),error_code=result.get('error_code'))
    check('Proposal explicitly remains unverified and unauthorized',result['execution_authorized'] is False and result['apply_authorized'] is False and result['verification_status']=='not_run')
    files=result['proposal']['files'];editable={f['path'] for f in review['files'] if f['role']=='editable'}
    check('Actual model changes only exactly selected editable files',{f['path'] for f in files}==editable)
    for item in files:
        expected=originals[item['path']].replace(b'1',b'42')
        check('Actual model proposed exact value change '+Path(item['path']).name,item['content'].encode('utf-8')==expected)
        check('Actual diff/source hashes bind originals and proposal '+Path(item['path']).name,
              item['base_sha256']==hashlib.sha256(originals[item['path']]).hexdigest()
              and item['proposed_sha256']==hashlib.sha256(expected).hexdigest()
              and '-'+originals[item['path']].decode('utf-8').strip() in item['diff'] and '+'+expected.decode('utf-8').strip() in item['diff'])
    report['proposal_diff_sha256']=hashlib.sha256(result['proposal']['diff'].encode('utf-8')).hexdigest()
    for port in (8080,8000):
        for method,path,body in [('GET',base+'/proposals/'+proposal_id,None),('POST',base+'/proposals/'+proposal_id+'/recover',None),
                                 ('POST',base+'/proposals',{'proposal_id':proposal_id,'reviewed_plan_sha256':digest})]:
            r=call(port,method,path,body=body)
            check(f'{port} exact inspect/recover/same-ID response {method} {path.rsplit("/",1)[-1]}',r.status_code==200 and r.json()==result)
        r=call(port,'POST',base+'/proposals/'+proposal_id+'/cancel')
        check(f'{port} terminal proposal is not cancelled or replayed',r.status_code==200 and r.json()['cancel_requested'] is False)
    cancel_id=uuid.uuid4().hex
    def pending():
        with requests.Session() as other:
            other.trust_env=False
            return other.post('http://127.0.0.1:8080'+base+'/proposals',headers=headers,
                              json={'proposal_id':cancel_id,'reviewed_plan_sha256':digest},timeout=(5,105))
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(pending);observed=False
        for _ in range(120):
            r=call(8000,'GET',base+'/proposals/'+cancel_id)
            if r.status_code==200 and r.json().get('state')=='RUNNING':observed=True;break
            if future.done():break
            time.sleep(.05)
        check('Actual proposal observed RUNNING before cancellation',observed)
        r=call(8000,'POST',base+'/proposals/'+cancel_id+'/cancel')
        check('Authenticated actual cancellation requested',r.status_code==200 and r.json()['cancel_requested'] is True)
        cancelled=future.result(timeout=15)
    data=cancelled.json()
    check('Actual proposal reaches terminal CANCELLED without source',cancelled.status_code==200 and data['state']=='CANCELLED' and data['proposal'] is None)
    retry=call(8000,'POST',base+'/proposals',body={'proposal_id':cancel_id,'reviewed_plan_sha256':digest})
    check('Cancelled proposal ID does not replay',retry.status_code==200 and retry.json()==data)
    report['cancellation']={'proposal_id':cancel_id,'state':data['state'],'server_compute_release_measured':False}
    for path,raw in originals.items():check('Original fixture preserved '+Path(path).name,(ROOT/path).read_bytes()==raw)
    check('No execution record or apply seal created',all(not (ROOT/'saved_data/coding_tasks'/item).exists() for item in (proposal_id,cancel_id)))
    for port in (8080,8000):check(f'{port} still healthy',call(port,'GET','/health',auth={}).status_code==200)
    report['status']='passed'
except BaseException as error:
    report.update(status='failed',error_type=type(error).__name__,failed_check=str(error) if isinstance(error,AssertionError) else 'Inspect retained local evidence; no secrets in output')
finally:
    session.close();report['completed_at_utc']=datetime.now(timezone.utc).isoformat()
    with (cp/'live.json').open('x',encoding='utf-8') as out:json.dump(report,out,indent=2)
    print(json.dumps({'status':report['status'],'passed':sum(c['passed'] for c in report['checks']),'count':len(report['checks']),
                     'proposal_state':report.get('proposal_state'),'elapsed_seconds':report.get('elapsed_seconds'),'failed_check':report.get('failed_check')}),flush=True)
raise SystemExit(report['status']!='passed')
