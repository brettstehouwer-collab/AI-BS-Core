"""Narrow local release operations; never controls the trading gate."""
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(r'C:\AI-BS')
POINTER = ROOT / 'scratch/crypto_release_checkpoint_path.txt'
FLAGS = ('AI_BS_RECDEBUT_OUTBOUND_ENABLED', 'AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED',
         'AI_BS_DISCORD_NOTIFICATIONS_ENABLED', 'AI_BS_BACKEND_MANAGE_DAEMONS',
         'AI_BS_BACKEND_BACKGROUND_ENABLED', 'AI_BS_ALLOW_DESTRUCTIVE_ACTIONS',
         'RECDEBUT_REPLY_FORWARDING_ENABLED')
SUPPORT = ['Crypto-Swarm/go.mod','Crypto-Swarm/go.sum',
           'Crypto-Swarm/internal/queue/manager.go','Crypto-Swarm/internal/daemons/researcher.go',
           'Crypto-Swarm/cryptoswarm-desktop/go.mod','Crypto-Swarm/cryptoswarm-desktop/go.sum',
           'Crypto-Swarm/cryptoswarm-desktop/internal/queue/manager.go',
           'Crypto-Swarm/cryptoswarm-desktop/internal/daemons/researcher.go',
           'Crypto-Swarm/cryptoswarm-desktop/internal/aeo/engine.go']

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def prepare():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    cp = ROOT / 'backups' / ('crypto_release_' + stamp)
    cp.mkdir(exist_ok=False)
    POINTER.write_text(str(cp), encoding='utf-8')
    paths = set()
    for name in ('manifest_crypto_integrity_audit_20261030T184032Z.json',
                 'manifest_crypto_execution_controls_20261030T185003Z.json'):
        paths.update(json.loads((ROOT/'docs/agent_sync'/name).read_text())['changed_paths'])
    paths.update(['frontend/firebase.json', 'frontend/.firebaserc', 'frontend/vite.config.js'])
    before = {}
    for rel in sorted(paths):
        path = ROOT / rel
        raw = path.read_bytes()
        out = cp/'before'/rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
        before[rel] = {'sha256':hashlib.sha256(raw).hexdigest(), 'size':len(raw)}
    save(cp/'before_manifest.json', before)
    for suffix, args in [('status_before.txt',['status','--short','--untracked-files=all']),
                         ('head_before.txt',['rev-parse','HEAD']),
                         ('staged_before.txt',['diff','--cached','--stat'])]:
        (cp/suffix).write_bytes(subprocess.check_output(['git',*args],cwd=ROOT))
    print(json.dumps({'checkpoint':str(cp), 'snapshot_paths':len(paths)}))

def launch(kind):
    import psutil
    from dotenv import dotenv_values
    cp = Path(POINTER.read_text())
    env = dict(os.environ)
    for file in (ROOT/'.env', ROOT/'backend/.env'):
        if file.is_file():
            for key, value in dotenv_values(file).items():
                if value is not None:
                    env.setdefault(key, value)
    env.update({key:'false' for key in FLAGS})
    env['PYTHONUNBUFFERED'] = '1'
    python = str(ROOT/'pyppeteer_env/Scripts/python.exe')
    if kind in ('backend','crypto'):
        port = 8080 if kind == 'backend' else 8007
        if any(c.status == 'LISTEN' and c.laddr.port == port for c in psutil.net_connections(kind='tcp')):
            raise RuntimeError('Port already occupied; preserve the existing process')
        module = 'AI_BS_Backend:app' if kind == 'backend' else 'crypto_trader_bot:app'
        args = [python,'-m','uvicorn',module,'--app-dir',str(ROOT/'backend'),
                '--host','127.0.0.1','--port',str(port),'--workers','1','--no-access-log']
        cwd = ROOT/'backend'
    elif kind == 'news':
        database = ROOT/'state/crypto_news_telemetry.db'
        args = [python,'-m','backend.daemons.news_catalyst_daemon','--database',str(database),
                '--model','llama3.1:8b-instruct-q5_K_M','--symbols','CRO,BTC,ETH']
        if not database.exists(): args.append('--initialize')
        cwd = ROOT
    else:
        raise ValueError('unknown service')
    with (cp/(kind+'.local.log')).open('xb') as log:
        child = subprocess.Popen(args,cwd=cwd,env=env,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
    item = {'pid':child.pid,'started_utc':datetime.now(timezone.utc).isoformat(),
            'argv':args,'flags':{key:'false' for key in FLAGS},'log':str(cp/(kind+'.local.log'))}
    save(cp/(kind+'_launch.json'), item)
    print(json.dumps(item))

def stage_public():
    cp = Path(POINTER.read_text())
    config = json.loads((ROOT/'frontend/firebase.json').read_text())
    hosting = config['hosting']
    excluded = set(hosting['ignore']) | {'ghost_preload.js', 'telemetry.json'}
    stage = cp/'public'
    stage.mkdir(exist_ok=False)
    copied, skipped = [], []
    public = ROOT/'frontend/public'
    for path in sorted(public.rglob('*')):
        if not path.is_file(): continue
        rel = path.relative_to(public).as_posix()
        parts = path.relative_to(public).parts
        omit = (any(p.startswith('.') or p == 'node_modules' for p in parts)
                or path.suffix.lower() in {'.zip','.exe','.apk','.map'}
                or 'updates' in parts or 'media/generated/' in rel or rel in excluded)
        if omit:
            skipped.append(rel)
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(public.resolve()):
            raise RuntimeError('Linked public file requires separate review')
        target = stage/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)
        copied.append({'path':rel,'size':target.stat().st_size,
                       'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    save(cp/'public_manifest.json',{'copied':copied,'excluded':skipped})
    hosting['public'] = str(cp/'dist')
    hosting['ignore'] = list(hosting['ignore'])+['ghost_preload.js','telemetry.json']
    save(cp/'firebase.hosting.json', config)
    build_script = "import {build} from 'file:///C:/AI-BS/frontend/node_modules/vite/dist/node/index.js';\n" + \
        'await build('+json.dumps({'root':str(ROOT/'frontend'),
             'configFile':str(ROOT/'frontend/vite.config.js'), 'publicDir':str(stage),
             'build':{'outDir':str(cp/'dist'),'emptyOutDir':False}})+');\n'
    (cp/'build.mjs').write_text(build_script,encoding='utf-8')
    print(json.dumps({'copied_files':len(copied),'copied_bytes':sum(x['size'] for x in copied),
                      'excluded_files':len(skipped),'build_script':str(cp/'build.mjs')}))

def verify():
    import psutil
    import urllib.request
    import urllib.error
    cp = Path(POINTER.read_text())
    result = {'utc':datetime.now(timezone.utc).isoformat(), 'http':[], 'listeners':[], 'money':{}}
    for port, route in [(8080,'/health'),(8007,'/healthz'),(8080,'/api/telemetry/news-catalysts'),
                        (8000,'/api/telemetry/news-catalysts'),(11434,'/api/version'),(5173,'/')]:
        url = f'http://127.0.0.1:{port}{route}'
        try:
            with urllib.request.urlopen(url,timeout=5) as response:
                raw = response.read(1_000_000)
                body = json.loads(raw) if 'json' in response.headers.get('Content-Type','') else {'bytes':len(raw)}
                result['http'].append({'url':url,'status':response.status,'body':body})
        except (OSError, ValueError) as error:
            result['http'].append({'url':url,'error':type(error).__name__, 'code':getattr(error,'code',None)})
    for entry in psutil.net_connections(kind='tcp'):
        if entry.status != 'LISTEN' or entry.laddr.port not in {8080,8007,8000,11434,5173,20243}: continue
        process = psutil.Process(entry.pid)
        env = process.environ()
        result['listeners'].append({'port':entry.laddr.port,'bind':entry.laddr.ip,'pid':entry.pid,
            'parent_pid':process.ppid(),'flags':{key:env.get(key) for key in FLAGS}})
    for rel, expected in {
        'Crypto-Swarm/drip_ledger.json':'6a31b6bcf6fd89ef35ff6e7c41ba9749f559edcb97e5900649ddd291b12db098',
        'backend/crypto_ledger.json':'0331785a0ee70ba484a00e33dfe0bf32e3840c004b8c6b0da7009691073a2efd',
    }.items():
        actual = hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
        result['money'][rel] = {'sha256':actual,'unchanged':actual==expected}
    save(cp/'runtime_verification.json', result)
    safe_http = []
    for item in result['http']:
        body = item.get('body',{})
        if item['url'].endswith('news-catalysts'):
            body = {key:body.get(key) for key in ('configured','worker_state','advisory_only','trading_enabled','counts','feeds')}
        safe_http.append({**item,'body':body})
    print(json.dumps({'http':safe_http,'listeners':result['listeners'],'money':result['money']}))

def audit():
    import ast
    import re
    cp = Path(POINTER.read_text())
    manifest = json.loads((cp/'before_manifest.json').read_text())
    parsed, secret_flags = 0, []
    patterns = [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                r'AKIA[0-9A-Z]{16}',r'gh[pousr]_[A-Za-z0-9]{30,}']
    for rel in manifest:
        path = ROOT/rel
        text = path.read_text(encoding='utf-8-sig', errors='replace')
        if path.suffix == '.py':
            ast.parse(text)
            parsed += 1
        if any(re.search(pattern,text) for pattern in patterns): secret_flags.append(rel)
    dist = cp/'dist'
    forbidden = [str(p.relative_to(dist)) for p in dist.rglob('*') if p.is_file() and
                 (p.suffix.lower() in {'.db','.sqlite','.sqlite3','.pem','.key','.map','.zip','.exe','.apk'}
                  or any(part.startswith('.') for part in p.relative_to(dist).parts))]
    mirrors = {}
    for name in ('CryptoLiveStreamTab.jsx','CryptoNewsCatalysts.jsx'):
        paths = [ROOT/'frontend'/prefix/name for prefix in ('src/components','components','src/components/components','components/components')]
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        mirrors[name] = {'parity':len(set(hashes))==1,'sha256':hashes[0]}
    report = {'python_ast':parsed,'secret_file_flags':secret_flags,'forbidden_build_files':forbidden,
              'mirror_checks':mirrors,'dist_files':sum(p.is_file() for p in dist.rglob('*'))}
    save(cp/'predeploy_audit.json',report)
    print(json.dumps(report))
    if secret_flags or forbidden or not all(x['parity'] for x in mirrors.values()):
        raise RuntimeError('Preflight needs inspection')

def verify_deploy():
    import urllib.request
    import urllib.error
    cp = Path(POINTER.read_text())
    dist = cp/'dist'
    report = {'utc':datetime.now(timezone.utc).isoformat(),'checks':[]}
    candidates = [dist/'index.html', *sorted((dist/'js').glob('UnifiedCryptoHub.*.js'))]
    if len(candidates) != 2: raise RuntimeError('Expected exactly one crypto hub bundle')
    for path in candidates:
        rel = path.relative_to(dist).as_posix()
        request = urllib.request.Request('https://ai-bs-dashboard.web.app/'+rel+'?release=crypto193043',
                                         headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'identity','Cache-Control':'no-cache'})
        try:
            with urllib.request.urlopen(request,timeout=15) as response:
                raw = response.read(5_000_000)
                actual = hashlib.sha256(raw).hexdigest()
                expected = hashlib.sha256(path.read_bytes()).hexdigest()
                report['checks'].append({'path':rel,'status':response.status,'sha256':actual,'matches':actual==expected})
        except (OSError, ValueError) as error:
            report['checks'].append({'path':rel,'error':type(error).__name__,'code':getattr(error,'code',None)})
    request = urllib.request.Request('https://api.brettstehouwer.live/api/telemetry/news-catalysts',
                                     headers={'User-Agent':'Mozilla/5.0','Origin':'https://ai-bs-dashboard.web.app'})
    try:
        with urllib.request.urlopen(request,timeout=10) as response:
            body = json.load(response)
            report['public_api'] = {'status':response.status,'allow_origin':response.headers.get('Access-Control-Allow-Origin'),
                **{key:body.get(key) for key in ('configured','worker_state','advisory_only','trading_enabled','counts')}}
    except (OSError, ValueError) as error:
        report['public_api'] = {'error':type(error).__name__,'code':getattr(error,'code',None)}
    save(cp/'hosting_verification.json',report)
    print(json.dumps(report))

def git_plan():
    cp = Path(POINTER.read_text())
    paths = [p for p in json.loads((cp/'before_manifest.json').read_text())
             if p.startswith(('backend/','Crypto-Swarm/','scripts/tests/','frontend/'))
             and p not in {'frontend/firebase.json','frontend/.firebaserc','frontend/vite.config.js'}]
    paths += SUPPORT
    for name in ('CRYPTO_SUBSYSTEM_INTEGRITY_AUDIT_2026-10-30.md','CRYPTO_EXECUTION_CONTROLS_AND_NEWS_2026-10-30.md'):
        paths.append('docs/'+name)
    for name in ('manifest_crypto_integrity_audit_20261030T184032Z.json','manifest_crypto_execution_controls_20261030T185003Z.json'):
        paths.append('docs/agent_sync/'+name)
    tracked = []
    for rel in paths:
        if subprocess.run(['git','ls-files','--error-unmatch','--',rel],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode: continue
        head = subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT).replace(b'\r\n',b'\n')
        before = ROOT/'backups/crypto_integrity_audit_20261030T184032Z/before'/rel
        tracked.append({'path':rel,'initial_matches_head':before.is_file() and before.read_bytes().replace(b'\r\n',b'\n')==head})
    save(cp/'commit_allowlist.json', sorted(set(paths)))
    save(cp/'tracked_scope_review.json',tracked)
    print(json.dumps({'paths':len(set(paths)),'tracked':tracked}))

def check_go():
    cp = Path(POINTER.read_text())
    paths = json.loads((cp/'commit_allowlist.json').read_text())
    destination = cp/'go_source_check'
    destination.mkdir(exist_ok=False)
    for rel in paths:
        if not rel.startswith('Crypto-Swarm/') or Path(rel).suffix not in {'.go','.mod','.sum'}: continue
        out = destination/rel
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_bytes((ROOT/rel).read_bytes())
    env = dict(os.environ, GOPROXY='off', GOTOOLCHAIN='local', GOSUMDB='off')
    receipt = []
    for name in ('Crypto-Swarm','Crypto-Swarm/cryptoswarm-desktop'):
        completed = subprocess.run([r'C:\Program Files\Go\bin\go.exe','test','-count=1','-v','./internal/daemons','./internal/api'],
            cwd=destination/name,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        log_name = 'go_desktop.txt' if name.endswith('desktop') else 'go_main.txt'
        (cp/log_name).write_bytes(completed.stdout)
        receipt.append({'module':name,'returncode':completed.returncode,'output':completed.stdout.decode(errors='replace')})
    save(cp/'go_source_verification.json',receipt)
    print(json.dumps(receipt))
    if any(x['returncode'] for x in receipt): raise RuntimeError('Go source check failed')

def close_docs():
    cp = Path(POINTER.read_text())
    stamp = datetime.now(timezone.utc).isoformat()
    host = json.loads((cp/'hosting_verification.json').read_text())
    if not all(x.get('matches') for x in host['checks']): raise RuntimeError('Hosting bytes are not verified')
    deploy_raw = (cp/'firebase_deploy_direct.log').read_bytes()
    deploy_text = deploy_raw.decode('utf-16' if deploy_raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    if 'Deploy complete!' not in deploy_text:
        raise RuntimeError('Successful Firebase receipt missing')
    report = f'''# Crypto service and Firebase release — Record189

Verified {stamp}. Project/site: ai-bs-dashboard. Version v5.329.72 retained.

- Started backend API on127.0.0.1:8080 and held public-market daemon on127.0.0.1:8007. Existing gateway8000, frontend5173, Ollama11434 and API connector20243 were preserved. Actual listener PIDs and seven disabled flags are in the local runtime receipt.
- Started the explicit advisory news worker with installed llama3.1:8b-instruct-q5_K_M:local and CRO/BTC/ETH allowlist. Dedicated news-only database; no financial database initialization. Actual public feeds and local inference observed: CoinTelegraph/Decrypt succeeded and three articles analyzed; CoinDesk returned FEED_HTTP_ERROR and follows bounded backoff. This is operational evidence, not predictive-quality acceptance.
- Loaded /healthz reports dispatch_enabled=false and reconciliation_required=true. Execution controls remain OFFLINE_ONLY; no exchange adapter, live-enable, order, cancellation or protective exit was added. No exchange exposure reconciliation is claimed. Two financial JSON hashes remain unchanged, including the historical corrupt drip ledger.
- Built the current working-tree frontend into an isolated output directory, avoiding broad mirror synchronization and preserving the old dist. Preserved configured Hosting exclusions and additionally omitted stale ghost_preload.js/telemetry.json. Published1137 files through Hosting only. No Firestore, rules, Storage, Functions or other sites deployed.
- Published https://ai-bs-dashboard.web.app; exact remote SHA-256 matches for index.html and the new UnifiedCryptoHub bundle. Public news API returns200, correct Firebase-origin CORS, advisory_only=true and trading_enabled=false with browser headers. Python's default user agent initially received edge403; no authentication boundary was weakened.
- Verification:68 focused Python offline tests pass5.953s; isolated commit-source Go packages pass4 main+3 desktop hold tests and both API packages compile.19 Python AST parses, two four-mirror component hash checks, version consistency and bounded credential/artifact scans pass. Build warnings concern existing large chunks and mixed static/dynamic Firestore imports.
- Git scope includes crypto source/tests, four UI mirrors, reports/manifests and nine source/module dependencies needed for focused Go package builds. Main backend is staged by task-specific hunks; preexisting RecDebut work and unrelated dirty-tree content stay outside the commit. The deployed application was built from the existing dirty working tree; this scoped commit is not a complete reconstruction of every deployed application source.

Evidence directory (local/private): {cp}. Contains before snapshots, hashes, allowlist, full build/deploy/test logs, runtime/Hosting verification and resulting commit receipt. No Git push requested or performed.

Diagnostics: npx resolved latest Firebase CLI15.34.2 but its Windows executable wrapper repeatedly exited0 without executing deployment. After two attempts, preserved empty logs and pivoted to direct Node invocation of that exact npx-installed latest CLI; deployment completed. Two unrelated diagnostic one-liners had PowerShell/Python quoting errors and were replaced by a file-based verifier. Never treated exit0 alone as deploy acceptance.

Remaining: trusted live exchange adapter/reconciliation/signing/rate controls and existing exchange-held protections remain unverified; no source hold removed. CoinDesk feed failure remains visible. Browser sign-in/navigation acceptance is separate from verified HTTP artifacts/API. Static review also found a preexisting provider-key literal already in Git HEAD, outside this crypto delta; do not disclose it, and address removal/rotation separately.
'''
    rel = 'docs/CRYPTO_SERVICE_FIREBASE_RELEASE_2026-10-30.md'
    (ROOT/rel).write_text(report,encoding='utf-8')
    paragraph = f'''\n\n## Current Status & Handover: Record189 - Authorized crypto service / Firebase release ({stamp})

Operator explicitly authorized service startup, Firebase deployment and scoped Git checkpoint. Started controlled API8080 and held daemon8007 on127.0.0.1 with all six activation flags plus reply forwarding false; retained existing gateway8000/frontend5173/Ollama11434/API connector20243. Started explicit separate advisory RSS/local-only news worker; local model source accepted, two feeds polled and3 articles analyzed. CoinDesk reports bounded FEED_HTTP_ERROR.

Hosting-only ai-bs-dashboard release completed;1137 files from isolated build, old dist/mirrors preserved. Exact remote index/crypto hub SHA-256 matches; public news API200 with browser headers/correct CORS and trading_enabled=false. Loaded daemon /healthz confirms dispatch_enabled=false. Financial JSON bytes unchanged; execution coordinator remains offline-only and no order/cancellation/private exchange operation performed.

68 Python tests pass5.953s; isolated allowlisted Go source packages pass7 hold tests and both APIs compile.19 Python AST, four-mirror parity, version consistency and artifact scans pass. Wrapper no-op deployment receipts retained; pivoted to exact npx-installed latest Firebase CLI via Node, then verified actual published bytes. Scoped Git staging excludes unrelated main-backend RecDebut hunk and earlier shared-document work. v5.329.72 retained; no push. Current dirty-tree build is not fully reproducible from the scoped crypto commit alone.

Report: {rel}. Evidence: {cp}. Exact resulting commit is recorded in commit_receipt.json there. Live exchange/reconciliation/protective-stop gates and browser navigation acceptance remain separate; no live hold removed. Other campaign/VM/evaluation work unchanged.
'''
    for doc, section in [('docs/CODEX_HANDOFF.md',paragraph),
        ('docs/CODEX_JOURNAL.md',paragraph.replace('## Current Status & Handover: Record189','## Record189'))]:
        path = ROOT/doc
        if 'Record189 - Authorized crypto service' in path.read_text(encoding='utf-8-sig'): raise RuntimeError('Record already exists')
        with path.open('a',encoding='utf-8',newline='') as stream: stream.write(section)
    tasks = ROOT/'docs/CODEX_TASKS.md'
    text = tasks.read_text(encoding='utf-8-sig')
    start = text.index('<!-- AUTO_CHECKPOINT_SUMMARY_START -->')
    end = text.index('<!-- AUTO_CHECKPOINT_SUMMARY_END -->')+len('<!-- AUTO_CHECKPOINT_SUMMARY_END -->')
    summary = '''<!-- AUTO_CHECKPOINT_SUMMARY_START -->
## Current Authoritative Checkpoint Summary - Record189
- Authorized local service start and Hosting-only release verified: backend8080, held daemon8007, advisory RSS/local Ollama worker; existing gateway/frontend/Ollama/tunnel preserved. All new process activation flags false, including reply forwarding.
- https://ai-bs-dashboard.web.app deployed1137 files; remote index/crypto-hub hashes match. Public news API200 with correct CORS/browser headers, two feeds working/three articles analyzed; CoinDesk failure remains bounded and visible.
- dispatch_enabled=false in loaded8007; offline execution coordinator not connected. No order, cancellation, private exchange action or ledger repair. Both monetary JSON hashes preserved.
-68 Python tests and7 isolated Go tests pass; APIs compile,19 Python AST, version5.329.72 consistency and four-mirror parity verified. Scoped crypto commit excludes unrelated edits; no push. Build came from current dirty working tree.
- Report: docs/CRYPTO_SERVICE_FIREBASE_RELEASE_2026-10-30.md; receipts in backups/crypto_release_20261030T193043Z. Live reconciliation/adapter/protective orders, full browser acceptance and earlier campaign/VM/evaluation gates remain separate.
<!-- AUTO_CHECKPOINT_SUMMARY_END -->'''
    tasks.write_text(text[:start]+summary+text[end:]+'''

### Authorized crypto services and Firebase release (Record189)
- [x] Start controlled backend8080 and held8007 on loopback; preserve existing core services and all disabled activation flags.
- [x] Start separate advisory public RSS/local-model worker; verify actual local inference and two healthy feeds. CoinDesk remains degraded with bounded retries.
- [x] Build isolated frontend, deploy existing ai-bs-dashboard Hosting only and compare exact published index/crypto hub hashes; verify public news API/CORS.
- [x] Re-run68 offline Python tests and7 isolated Go source checks; inspect scoped Git diff and retain exact receipts. No live dispatch or Git push.
- [ ] Existing exchange reconciliation/protection and live-adapter acceptance remain unverified; browser navigation/sign-in acceptance separate.
''',encoding='utf-8')
    with (ROOT/'docs/CODEX_DECISIONS.md').open('a',encoding='utf-8') as stream:
        stream.write(f'''\n\n## ADR-116 - Controlled advisory service and Hosting release with trading held - {stamp}
- Requirement: explicit operator service-start, Firebase-deploy and commit authorization following Record187/188.
- Decision: launch only missing controlled API and held market-data service, plus explicit separate advisory news worker. Keep seven activation flags false, hard order guard and OFFLINE_ONLY coordinator unchanged. Retain healthy core processes; no fleet auto-start or live adapter.
- Release: isolated Vite output avoids overwriting mirrors/dist; preserve configured exclusions and omit stale identifying/corrupt support artifacts. Publish existing ai-bs-dashboard Hosting only; require real CLI receipt plus exact remote-byte/API checks before claiming success. Stage only crypto work and reviewed build dependencies; preserve unrelated working-tree edits.
- Acceptance/status:68 Python+7 Go tests pass; two API packages compile; loaded8007 confirms held execution; two public feeds/local inference and published-byte hashes verified. CoinDesk remains degraded. Full browser/live financial acceptance is unverified. See docs/CRYPTO_SERVICE_FIREBASE_RELEASE_2026-10-30.md and {cp}.
''')
    paths = json.loads((cp/'commit_allowlist.json').read_text())+[rel]
    paths += ['docs/CODEX_HANDOFF.md','docs/CODEX_JOURNAL.md','docs/CODEX_DECISIONS.md','docs/CODEX_TASKS.md']
    save(cp/'commit_allowlist.json',sorted(set(paths)))
    save(cp/'after_manifest.json',{p:{'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),'size':(ROOT/p).stat().st_size} for p in paths})
    print(json.dumps({'report':rel,'paths':len(set(paths))}))

def stage_commit():
    import re
    cp = Path(POINTER.read_text())
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT).strip():
        raise RuntimeError('Index is no longer empty; preserve and inspect')
    expected = (cp/'head_before.txt').read_text().strip()
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() != expected:
        raise RuntimeError('HEAD changed during release')
    paths = json.loads((cp/'commit_allowlist.json').read_text())
    manifest_rel = 'docs/agent_sync/manifest_crypto_release_20261030T193043Z.json'
    manifest = {'schema':'aibs.engineering_handoff.v1','id':'crypto_release_20261030T193043Z','record':189,
                'created_utc':datetime.now(timezone.utc).isoformat(),'branch':'main','base_commit':expected,
                'outgoing_agent':'OpenAI Codex','receiving_agent':'next engineering session; acknowledgement pending',
                'status':'VERIFIED_HOSTING_AND_HELD_RUNTIME','version':'5.329.72','site':'https://ai-bs-dashboard.web.app',
                'changed_paths':paths+[manifest_rel], 'evidence':str(cp), 'source_manifest_sha256':hashlib.sha256((cp/'after_manifest.json').read_bytes()).hexdigest(),
                'verification':{'python_tests':68,'go_tests':7,'python_ast':19,'published_bytes_match':True,
                    'dispatch_enabled':False,'financial_json_unchanged':True,'go_api_packages_compile':2},
                'incomplete':['CoinDesk FEED_HTTP_ERROR; bounded backoff','Browser signed-in navigation unrun',
                    'Live exchange reconciliation and provider adapter remain unverified; no live enable',
                    'Existing unrelated dirty-tree changes excluded from scoped Git commit'],
                'commit_receipt':str(cp/'commit_receipt.json')}
    save(ROOT/manifest_rel,manifest)
    paths.append(manifest_rel)
    special = {'backend/AI_BS_Backend.py','docs/CODEX_HANDOFF.md','docs/CODEX_JOURNAL.md','docs/CODEX_DECISIONS.md','docs/CODEX_TASKS.md'}
    regular = [p for p in paths if p not in special]
    subprocess.run(['git','add','-f','--',*regular],cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def stage_blob(rel,text):
        blob = subprocess.check_output(['git','hash-object','-w','--stdin'],cwd=ROOT,input=text.encode('utf-8')).decode().strip()
        subprocess.run(['git','update-index','--cacheinfo','100644,'+blob+','+rel],cwd=ROOT,check=True)
    def head(rel):
        return subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT).decode('utf-8-sig').replace('\r\n','\n')
    rel = 'backend/AI_BS_Backend.py'
    text = head(rel)
    anchor = 'from routers.trading_router import router as trading_domain_router\n'
    if text.count(anchor) != 1: raise RuntimeError('Router anchor changed')
    text = text.replace(anchor,anchor+'from routers.news_catalyst_router import router as news_catalyst_router\napp.include_router(news_catalyst_router)\n')
    old = '    return {"status": "success", "message": "Emergency TWAP liquidation sequence triggered."}'
    if text.count(old) != 1: raise RuntimeError('Liquidation anchor changed')
    text = text.replace(old,'    raise HTTPException(status_code=503, detail="Liquidation held pending reconciled exchange execution; no orders dispatched")')
    stage_blob(rel,text)
    markers = {'docs/CODEX_HANDOFF.md':'## Current Status & Handover: Record187',
               'docs/CODEX_JOURNAL.md':'## Record187 - Crypto',
               'docs/CODEX_DECISIONS.md':'## ADR-114 - ',
               'docs/CODEX_TASKS.md':'### Crypto static audit and containment (Record187;'}
    for rel, marker in markers.items():
        current = (ROOT/rel).read_text(encoding='utf-8-sig')
        base = head(rel)
        if marker in base: raise RuntimeError('Task records already in HEAD')
        section = current[current.index(marker):]
        if rel.endswith('CODEX_TASKS.md'):
            pattern = r'<!-- AUTO_CHECKPOINT_SUMMARY_START -->.*?<!-- AUTO_CHECKPOINT_SUMMARY_END -->'
            summary = re.search(pattern,current,re.S).group()
            base, count = re.subn(pattern,lambda match:summary,base,flags=re.S)
            if count != 1: raise RuntimeError('Task summary anchor changed')
        stage_blob(rel,base.rstrip()+'\n\n'+section)
    staged_paths = subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
    if set(staged_paths) != set(paths): raise RuntimeError('Unexpected staged path set')
    subprocess.run(['git','diff','--cached','--check'],cwd=ROOT,check=True)
    (cp/'staged_changes.patch').write_bytes(subprocess.check_output(['git','diff','--cached','--binary'],cwd=ROOT))
    (cp/'staged_stat.txt').write_bytes(subprocess.check_output(['git','diff','--cached','--stat'],cwd=ROOT))
    save(cp/'commit_allowlist.json',sorted(paths))
    print(json.dumps({'staged_paths':len(paths),'backend_unrelated_hunk_excluded':True,'shared_docs_prior_edits_excluded':True}))

def finish_stage():
    cp = Path(POINTER.read_text())
    paths = json.loads((cp/'commit_allowlist.json').read_text())
    manifest_rel = 'docs/agent_sync/manifest_crypto_release_20261030T193043Z.json'
    if manifest_rel not in paths: paths.append(manifest_rel)
    staged = subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
    if set(paths) != set(staged): raise RuntimeError('Index differs from exact release allowlist')
    check = subprocess.run(['git','diff','--cached','--check'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (cp/'whitespace_review.txt').write_bytes(check.stdout)
    # Keep original legacy source bytes. Verify no other whitespace/conflict
    # class exists after explicitly ignoring inherited end-of-line whitespace.
    subprocess.run(['git','-c','core.whitespace=-blank-at-eol,-blank-at-eof','diff','--cached','--check'],cwd=ROOT,check=True)
    (cp/'staged_changes.patch').write_bytes(subprocess.check_output(['git','diff','--cached','--binary'],cwd=ROOT))
    (cp/'staged_stat.txt').write_bytes(subprocess.check_output(['git','diff','--cached','--stat'],cwd=ROOT))
    save(cp/'commit_allowlist.json',sorted(paths))
    save(cp/'stage_review.json',{'paths':len(paths),'plain_diff_check_returncode':check.returncode,
        'inherited_trailing_whitespace_preserved':True,'other_diff_check_passed':True,
        'main_backend_only_two_task_hunks':True,'unrelated_shared_doc_changes_unstaged':True})
    print(json.dumps({'ready_paths':len(paths),'inherited_whitespace_recorded':True}))

def commit():
    cp = Path(POINTER.read_text())
    paths = json.loads((cp/'commit_allowlist.json').read_text())
    staged = subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
    if set(paths) != set(staged): raise RuntimeError('Index changed since scope review')
    message = ('Harden crypto execution controls and add advisory news telemetry\n\n'
               'Keep live dispatch held; add offline fill accounting, durable recovery, shared risk and stop controls.\n'
               'Add separate public RSS/local-model news telemetry and mirrored dashboard panel.\n'
               'Record controlled service startup and verified Firebase Hosting deployment.\n\n'
               'Validation: 68 Python offline tests; 7 isolated Go hold tests and both API packages compile; production build and published-byte checks.\n')
    (cp/'commit_message.txt').write_text(message,encoding='utf-8')
    completed = subprocess.run(['git','commit','--file',str(cp/'commit_message.txt')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (cp/'git_commit.txt').write_bytes(completed.stdout)
    if completed.returncode:
        print(completed.stdout.decode(errors='replace'))
        raise RuntimeError('Commit failed; staged changes retained')
    actual = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    committed_paths = subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r',actual],cwd=ROOT,text=True).splitlines()
    if set(paths) != set(committed_paths): raise RuntimeError('Committed scope differs')
    receipt = {'commit':actual,'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        'paths':committed_paths,'utc':datetime.now(timezone.utc).isoformat(),'push_performed':False,'scope_matches':True,
        'staged_patch_sha256':hashlib.sha256((cp/'staged_changes.patch').read_bytes()).hexdigest()}
    save(cp/'commit_receipt.json',receipt)
    (cp/'status_after.txt').write_bytes(subprocess.check_output(['git','status','--short','--untracked-files=all'],cwd=ROOT))
    print(json.dumps({'commit':actual,'files':len(paths),'scope_matches':True,'push_performed':False}))

if __name__ == '__main__':
    if sys.argv[1] == 'prepare': prepare()
    elif sys.argv[1] == 'launch': launch(sys.argv[2])
    elif sys.argv[1] == 'stage-public': stage_public()
    elif sys.argv[1] == 'verify': verify()
    elif sys.argv[1] == 'audit': audit()
    elif sys.argv[1] == 'verify-deploy': verify_deploy()
    elif sys.argv[1] == 'git-plan': git_plan()
    elif sys.argv[1] == 'check-go': check_go()
    elif sys.argv[1] == 'close-docs': close_docs()
    elif sys.argv[1] == 'stage-commit': stage_commit()
    elif sys.argv[1] == 'finish-stage': finish_stage()
    elif sys.argv[1] == 'commit': commit()
