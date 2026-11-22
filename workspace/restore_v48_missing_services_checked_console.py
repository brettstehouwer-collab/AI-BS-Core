"""Restore reviewed local services after observing their recorded handles missing."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess, sys, time
import psutil, requests
from dotenv import dotenv_values

root = Path(r'C:\AI-BS')
out = Path((root / 'workspace/proposal_history_v48_resume.txt').read_text(encoding='utf-8'))
state_path = out / 'runtime_restoration_checked_console.json'
assert not state_path.exists()
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
flags = ['AI_BS_RECDEBUT_OUTBOUND_ENABLED', 'AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED',
         'AI_BS_DISCORD_NOTIFICATIONS_ENABLED', 'AI_BS_BACKEND_MANAGE_DAEMONS',
         'AI_BS_BACKEND_BACKGROUND_ENABLED', 'AI_BS_ALLOW_DESTRUCTIVE_ACTIONS']
record = {'status': 'preflight', 'at_utc': datetime.now(timezone.utc).isoformat(), 'processes': {}, 'checks': []}
session = requests.Session()
session.trust_env = False

def save():
    state_path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')

def check(name, value):
    record['checks'].append({'name': name, 'passed': bool(value)})
    save()
    assert value, name

def listeners(port):
    return [c for c in psutil.net_connections(kind='tcp') if c.status == 'LISTEN' and c.laddr.port == port]

def identity(p):
    return {'pid': p.pid, 'created': p.create_time(), 'exe': p.exe(), 'argv': p.cmdline()}

def launch(name, argv, cwd, env, port, health=None):
    check('Port vacant immediately before ' + name, not listeners(port))
    with (out / (name + '_restored.log')).open('xb') as log:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
    item = {'launcher': identity(psutil.Process(process.pid)), 'status': 'starting', 'port': port}
    record['processes'][name] = item
    save()
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        assert process.poll() is None, name + ' exited; inspect retained log before any retry'
        owners = listeners(port)
        if owners:
            assert len(owners) == 1 and owners[0].laddr.ip == '127.0.0.1'
            serving = psutil.Process(owners[0].pid)
            assert serving.pid == process.pid or any(p.pid == process.pid and p.create_time() == item['launcher']['created'] for p in serving.parents())
            assert serving.cmdline()[1:] == argv[1:]
            expected_exes = [argv[0]] + ([sys._base_executable] if name == 'backend' else [])
            assert os.path.normcase(serving.exe()) in [os.path.normcase(p) for p in expected_exes]
            if health:
                try:
                    if session.get(health, timeout=2, allow_redirects=False).status_code != 200:
                        time.sleep(.5)
                        continue
                except requests.RequestException:
                    time.sleep(.5)
                    continue
            assert all(serving.environ().get(f) == 'false' for f in flags)
            item.update(serving=identity(serving), status='healthy' if health else 'listener_verified', six_flags_false=True)
            save()
            print(json.dumps({'service': name, 'pid': serving.pid, 'status': item['status']}), flush=True)
            return serving
        time.sleep(.5)
    raise TimeoutError(name + ' observation timed out; inspect same recorded handle, do not replace')

try:
    check('Fresh preservation report verified', read(out / 'preservation/documents_databases.json')['status'] == read(out / 'preservation/personal_preservation_after.json')['status'] == 'verified')
    check('Only Ollama is currently serving', all(not listeners(p) for p in (8080,8000,5173,11435)))
    prior = read(root / 'backups/proposal_history_5_329_48_20261024T145341207541Z/runtime_after_connection_closed/process.json')
    check('Loaded source unchanged', all(sha(root / n) == h for n,h in prior['source_hashes'].items()))
    check('Vite configuration unchanged', sha(root / 'frontend/vite.config.js') == '5f2ff937e8182c0013bf6335728b99cec2adc8e84f9b4fc9052cd734e20ff95b')
    build = read(root / 'backups/gateway_identity_5_329_37_20261024T072602753556Z/build.json')
    check('Existing protected gateway binary unchanged', sha(build['binary']) == build['sha256'] == '18ed747d07b6a41aaa776175d00c4b16e32f3f3173063c142f4aaa92620c73a9')
    config = dict(os.environ)
    for p in (root / '.env', root / 'backend/.env'):
        if p.is_file():
            config.update({k:v for k,v in dotenv_values(p).items() if v is not None})
    assert config.get('AI_BS_ADMIN_KEY') and config.get('AI_BS_ADMIN_EMAILS')
    allowed = {'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TEMP','TMP','USERPROFILE','USERNAME','USERDOMAIN','LOCALAPPDATA','APPDATA','PROGRAMDATA','PROGRAMFILES','PROGRAMFILES(X86)','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE','CUDA_PATH'}
    limited = {k:v for k,v in os.environ.items() if k.upper() in allowed}
    limited.update({f:'false' for f in flags})

    owners = listeners(11434)
    check('One existing loopback Ollama owner', len(owners) == 1 and owners[0].laddr.ip == '127.0.0.1')
    ollama = psutil.Process(owners[0].pid)
    expected_exe = str(Path(os.environ['LOCALAPPDATA']) / 'Programs/Ollama/ollama.exe')
    assert os.path.normcase(ollama.exe()) == os.path.normcase(expected_exe) and ollama.cmdline()[1:] == ['serve']
    old_model = identity(ollama)
    assert all(c.name().lower() == 'conhost.exe' and Path(c.exe()).parent == Path(os.environ['SYSTEMROOT']) / 'System32' for c in ollama.children()), 'Non-console Ollama child present; preserve it'
    assert not session.get('http://127.0.0.1:11434/api/ps', timeout=5).json()['models'], 'Loaded model work present; preserve it'
    tags = session.get('http://127.0.0.1:11434/api/tags', timeout=5).json()['models']
    digest = next(m['digest'] for m in tags if m['name'] == 'stehouwer_llm:latest')
    check('Existing Stehouwer digest exact', digest == '5213ff76656a20b564e1001cc3cc4e9e9b7f8cc80dd837cde54b341127e60b12')
    session.close()
    session = requests.Session()
    session.trust_env = False
    assert not [c for c in ollama.net_connections(kind='tcp') if c.status == 'ESTABLISHED']
    # The desktop launcher inherited destructive=true; restart only its verified idle tree.
    app = ollama.parent()
    assert app is not None and os.path.normcase(app.exe()) == os.path.normcase(str(Path(expected_exe).with_name('ollama app.exe')))
    assert all(c.pid == ollama.pid or c.name().lower() == 'conhost.exe' for c in app.children(recursive=True))
    record['replaced_idle_model_process'] = {'server': old_model, 'desktop_launcher': identity(app), 'reason': 'Six AI-BS flags were not false; existing digest/store preserved', 'loaded_models': 0}
    save()
    assert ollama.create_time() == old_model['created']
    app.terminate()
    app.wait(timeout=10)
    if ollama.is_running():
        assert ollama.create_time() == old_model['created'] and ollama.exe() == old_model['exe']
        ollama.terminate()
        ollama.wait(timeout=10)
    check('Previous Ollama listener terminal', not listeners(11434))
    env = dict(limited, OLLAMA_MODELS=str(root / 'models/ollama'), OLLAMA_HOST='127.0.0.1:11434',
               OLLAMA_NO_CLOUD='1', OLLAMA_NUM_PARALLEL='1', OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_KEEP_ALIVE='5m')
    launch('ollama', [expected_exe,'serve'], Path(expected_exe).parent, env,11434,'http://127.0.0.1:11434/api/version')
    check('Restored same customized model registry', next(m['digest'] for m in session.get('http://127.0.0.1:11434/api/tags',timeout=5).json()['models'] if m['name']=='stehouwer_llm:latest') == digest)

    backend_env = dict(config)
    backend_env.update({f:'false' for f in flags})
    backend_env.update(PYTHONUNBUFFERED='1', AIBS_DEV_RELOAD='0')
    argv = [str(root/'pyppeteer_env/Scripts/python.exe'),'-m','uvicorn','AI_BS_Backend:app','--app-dir',str(root/'backend'),'--host','127.0.0.1','--port','8080','--workers','1','--no-access-log']
    launch('backend',argv,root/'backend',backend_env,8080,'http://127.0.0.1:8080/health')
    gateway_env = dict(limited)
    gateway_env.update({k:config[k] for k in ('AI_BS_ADMIN_KEY','AI_BS_ADMIN_EMAILS')})
    gateway = launch('gateway',[build['binary']],root,gateway_env,8000,'http://127.0.0.1:8000/health')
    assert session.get('http://127.0.0.1:8000/health',timeout=5).json()['version'] == build['compiled_version']
    response = session.get('http://127.0.0.1:8000/api/daemons/status',headers={'X-Admin-Key':config['AI_BS_ADMIN_KEY']},timeout=5)
    assert response.status_code == 200
    rows=response.json()
    check('All11 unrelated managed daemons stopped',len(rows)==11 and all(r['running'] is False and r['pid']==-1 and r['state']=='stopped' for r in rows.values()))
    argv=[r'C:\Program Files\nodejs\node.exe',str(root/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','5173','--strictPort']
    launch('frontend',argv,root/'frontend',limited,5173)
    for port in (8080,8000):
        url=f'http://127.0.0.1:{port}/api/chat/coding-tasks/preparations/identity'
        anon=session.get(url,timeout=5)
        admin=session.get(url,headers={'X-Admin-Key':config['AI_BS_ADMIN_KEY']},timeout=5)
        check('Actual access enforcement '+str(port),anon.status_code==403 and admin.status_code==200 and admin.json()['owner']=='local_admin' and admin.json()['execution_authorized'] is False)
    check('No11435 or unexpected service binding',not listeners(11435) and all(len(listeners(p))==1 and listeners(p)[0].laddr.ip=='127.0.0.1' for p in (8080,8000,11434,5173)))
    record.update(status='healthy_protected',inference_performed=False,project_execution=False,model_creation=False,vm='deferred',frontend_http_requested=False)
except BaseException as error:
    record.update(status='inspection_needed',error_type=type(error).__name__,reason=str(error) if isinstance(error,AssertionError) else 'Inspect preserved process identities and logs; do not replace blindly')
    raise
finally:
    save()
    session.close()
    print(json.dumps({'status':record['status'],'checks':len(record['checks']),'record':str(state_path)}),flush=True)
