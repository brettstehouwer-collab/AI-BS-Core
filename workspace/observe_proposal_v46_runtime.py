from pathlib import Path
import hashlib,json,os
from datetime import datetime,timezone
from dotenv import dotenv_values
import psutil,requests
ROOT=Path(r'C:\AI-BS');cp=ROOT/'backups/retained_proposal_5_329_46_20261024T141425139154Z'
prior=json.loads((cp/'runtime/process.json').read_text(encoding='utf-8'))
config=dict(os.environ)
for path in (ROOT/'.env',ROOT/'backend/.env'):
    if path.is_file():config.update({k:v for k,v in dotenv_values(path).items() if v is not None})
session=requests.Session();session.trust_env=False
report={'at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Observe the same already-started processes; no restarts or task mutations','services':{}}
try:
    for name,port in [('backend',8080),('gateway',8000),('ollama',11434)]:
        old=prior['processes'][name].get('serving',prior['processes'][name]['launcher'])
        process=psutil.Process(old['pid'])
        assert process.create_time()==old['created'] and process.exe()==old['exe'] and process.cmdline()==old['argv']
        listeners=[c for c in psutil.net_connections(kind='tcp') if c.status=='LISTEN' and c.laddr.port==port]
        assert listeners and all(c.pid==process.pid and c.laddr.ip=='127.0.0.1' for c in listeners)
        env=process.environ(); flags={k:env.get(k)=='false' for k in prior['controlled_flags']}
        response=session.get(f'http://127.0.0.1:{port}'+('/api/tags' if name=='ollama' else '/health'),timeout=5)
        info={'pid':process.pid,'identity_verified':True,'loopback':True,'flags_disabled':flags,'http':response.status_code,
              'children':[{'pid':p.pid,'name':p.name()} for p in process.children(recursive=True)]}
        if name=='ollama':
            models=response.json().get('models',[])
            info.update(model_store_matches=env.get('OLLAMA_MODELS')==str(ROOT/'models/ollama'),
                        custom_model_preserved=any(m.get('name')=='stehouwer_llm:latest' and m.get('digest')=='5213ff76656a20b564e1001cc3cc4e9e9b7f8cc80dd837cde54b341127e60b12' for m in models),registered_models=len(models))
        else:info['health']=response.json()
        if name=='gateway':
            r=session.get(f'http://127.0.0.1:{port}/api/daemons/status',headers={'X-Admin-Key':config['AI_BS_ADMIN_KEY']},timeout=5)
            data=r.json();info['daemon_status_http']=r.status_code
            info['daemon_states']={k:{field:v.get(field) for field in ['running','pid','state']} for k,v in data.items()} if isinstance(data,dict) else {'unexpected_type':type(data).__name__}
        report['services'][name]=info
    report['source_hashes_exact']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in prior['source_hashes'].items()}
    for port in (8080,8000):
        base=f'http://127.0.0.1:{port}/api/chat/coding-tasks/preparations/identity'
        anon=session.get(base,timeout=5);auth=session.get(base,headers={'X-Admin-Key':config['AI_BS_ADMIN_KEY']},timeout=5)
        report['services']['backend' if port==8080 else 'gateway']['preparation_auth']={'anonymous':anon.status_code,'authorized':auth.status_code,'owner':auth.json().get('owner'),'execution_authorized':auth.json().get('execution_authorized')}
finally:
    session.close()
    with (cp/'runtime/observation_after_restore.json').open('x',encoding='utf-8') as out:json.dump(report,out,indent=2)
    print(json.dumps(report))
