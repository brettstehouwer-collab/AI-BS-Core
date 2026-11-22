"""Start/adopt only the reviewed local web core; no cleanup, fleet or model work."""
from __future__ import annotations
from dataclasses import dataclass,field
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import shutil,subprocess,sys,time

FLAGS=('AI_BS_RECDEBUT_OUTBOUND_ENABLED','AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED','AI_BS_DISCORD_NOTIFICATIONS_ENABLED','AI_BS_BACKEND_MANAGE_DAEMONS','AI_BS_BACKEND_BACKGROUND_ENABLED','AI_BS_ALLOW_DESTRUCTIVE_ACTIONS')
GATEWAY_SHA='923c828faf8f0db22d2f352dad72278620b58713b9300527c820a37d4f30afe2'
CONFIG_SHA='edac3b13da88af2de58e9706f17d4fdded96ce1d20282d896b77b60c9a58824e'
CLOUDFLARED_SHA='86aee4017b26625cee8484c113558f48effa4cd47f7aa05fcf425604e5d2b23c'
ROOT=Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ServiceSpec:
    name:str
    port:int
    argv:tuple[str,...]
    cwd:Path
    private:bool=False
    binary_sha:str=''
    extra:dict=field(default_factory=dict)


def controlled_environment(source,*,private):
    if private:
        result=dict(source)
    else:
        keep={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TEMP','TMP','USERPROFILE','USERNAME','USERDOMAIN','LOCALAPPDATA','APPDATA','PROGRAMDATA','PROGRAMFILES','PROGRAMFILES(X86)','HOMEDRIVE','HOMEPATH','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE','SESSIONNAME'}
        result={k:v for k,v in source.items() if k.upper() in keep}
    result.update({key:'false' for key in FLAGS})
    result['PYTHONUNBUFFERED']='1'
    return result


def service_specs(root):
    root=Path(root)
    python=str(Path(sys.base_prefix)/'python.exe')
    node=shutil.which('node.exe') or r'C:\Program Files\nodejs\node.exe'
    ollama=str(Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))/'Programs/Ollama/ollama.exe')
    config=root/'saved_data/core_runtime/api-tunnel-scoped.yml'
    cloudflared=str(Path(os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)'))/'cloudflared/cloudflared.exe')
    return [
        ServiceSpec('backend',8080,(python,'-m','uvicorn','AI_BS_Backend:app','--app-dir',str(root/'backend'),'--host','127.0.0.1','--port','8080','--workers','1','--no-access-log'),root/'backend',True),
        ServiceSpec('gateway',8000,(str(root/'go-core/aibs_engine.exe'),),root,True,GATEWAY_SHA),
        ServiceSpec('ollama',11434,(ollama,'serve'),root,extra={'OLLAMA_HOST':'127.0.0.1:11434','OLLAMA_MODELS':str(root/'models/ollama'),'OLLAMA_MAX_LOADED_MODELS':'1','OLLAMA_NUM_PARALLEL':'1','OLLAMA_FLASH_ATTENTION':'1'}),
        ServiceSpec('frontend',5173,(node,str(root/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','5173','--strictPort'),root/'frontend'),
        ServiceSpec('api_connector',20243,(cloudflared,'tunnel','--config',str(config),'--metrics','127.0.0.1:20243','run','d1acbd25-06c3-4be0-a7f4-ae3943263aed'),root,binary_sha=CLOUDFLARED_SHA),
    ]


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _argument(value):
    path=Path(value)
    return os.path.normcase(str(path.resolve())) if path.is_absolute() and path.exists() else value


def ipv4_listeners(entries,port):
    listeners=[c for c in entries if c.status=='LISTEN' and c.laddr.port==port]
    if any(c.laddr.ip not in {'127.0.0.1','::1'} for c in listeners):
        raise RuntimeError('A core port has a non-loopback binding; preserve it and inspect')
    return [c for c in listeners if c.laddr.ip=='127.0.0.1']


def validate_existing(spec,entries,process):
    if len(entries)!=1 or entries[0].laddr.ip!='127.0.0.1':
        raise RuntimeError('Existing core port is not one controlled loopback listener')
    if os.path.normcase(process.exe())!=os.path.normcase(spec.argv[0]):
        raise RuntimeError('Existing core executable differs; preserve it and inspect')
    if [_argument(v) for v in process.cmdline()[1:]]!=[_argument(v) for v in spec.argv[1:]]:
        raise RuntimeError('Existing core arguments differ; preserve it and inspect')
    if spec.private and not all(process.environ().get(key)=='false' for key in FLAGS):
        raise RuntimeError('Existing API process does not have the controlled flags')
    return {'pid':process.pid,'created':process.create_time(),'exe':process.exe(),'adopted':True}


def main(root=ROOT):
    import psutil,httpx
    from dotenv import dotenv_values
    sys.path.insert(0,str(root))
    from native_studio.screenplay_client import _private_recovery_directory
    runtime=root/'saved_data/core_runtime'
    _private_recovery_directory(runtime,runtime.parent)
    config=runtime/'api-tunnel-scoped.yml'
    if not config.is_file() or digest(config)!=CONFIG_SHA:
        raise RuntimeError('Reviewed private API connector configuration is unavailable')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt=runtime/f'core_boot_{stamp}.json'
    report={'utc':datetime.now(timezone.utc).isoformat(),'status':'starting','services':{},'flagsFalse':list(FLAGS),'credentialsLogged':False,'optionalFleetStarted':False}
    def save():receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
    source=dict(os.environ)
    for path in (root/'.env',root/'backend/.env'):
        if path.is_file():
            for key,value in dotenv_values(path).items():
                if value is not None:source.setdefault(key,value)
    if not source.get('AI_BS_ADMIN_KEY'):
        raise RuntimeError('Private local service configuration is not provisioned')
    specs=service_specs(root)
    try:
        # Admit every image first. An occupied/unreviewed port is never reclaimed.
        entries=psutil.net_connections(kind='tcp')
        for spec in specs:
            if not Path(spec.argv[0]).is_file() or spec.binary_sha and digest(spec.argv[0])!=spec.binary_sha:
                raise RuntimeError('A reviewed core image is unavailable')
            port=ipv4_listeners(entries,spec.port)
            if port:
                process=psutil.Process(port[0].pid)
                if process.username().casefold()!=psutil.Process().username().casefold():
                    raise RuntimeError('Existing core process has a different Windows owner')
                report['services'][spec.name]=validate_existing(spec,port,process)
        save()
        for spec in specs:
            if spec.name in report['services']:continue
            env=controlled_environment(source,private=spec.private);env.update(spec.extra)
            # Recheck after admission, including races with a second login launcher.
            if ipv4_listeners(psutil.net_connections(kind='tcp'),spec.port):
                raise RuntimeError('A core port changed during startup; preserve it and inspect')
            with (runtime/f'{spec.name}_{stamp}.local.log').open('xb') as stream:
                child=subprocess.Popen(list(spec.argv),cwd=spec.cwd,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
            process=psutil.Process(child.pid)
            report['services'][spec.name]={'pid':process.pid,'created':process.create_time(),'exe':process.exe(),'adopted':False}
            save()
        urls={8080:'/health',8000:'/health',11434:'/api/version',5173:'/',20243:'/ready'}
        deadline=time.monotonic()+120
        with httpx.Client(trust_env=False,follow_redirects=False,timeout=1.5) as client:
            while time.monotonic()<deadline:
                all_ready=True
                current=psutil.net_connections(kind='tcp')
                for spec in specs:
                    item=report['services'][spec.name]
                    process=psutil.Process(item['pid'])
                    if process.create_time()!=item['created']:raise RuntimeError('Core process identity changed')
                    port=ipv4_listeners(current,spec.port)
                    if not port:all_ready=False;continue
                    if len(port)!=1 or port[0].laddr.ip!='127.0.0.1' or port[0].pid!=process.pid:
                        raise RuntimeError('Core listener identity/binding differs')
                    try:
                        response=client.get(f'http://127.0.0.1:{spec.port}'+urls[spec.port])
                        ready=response.status_code==200
                        if spec.port==8000:ready=ready and response.json().get('version')=='5.329.52-firebase-id-token'
                    except (httpx.HTTPError,ValueError):ready=False
                    item['ready']=ready;all_ready=all_ready and ready
                save()
                if all_ready:
                    report['status']='healthy_controlled_core';save();print(json.dumps({'status':report['status'],'receipt':str(receipt),'pids':{k:v['pid'] for k,v in report['services'].items()}}));return 0
                time.sleep(0.5)
        report['status']='still_starting_observe_recorded_identities';save();return 2
    except Exception as error:
        report['status']='needs_inspection';report['errorType']=type(error).__name__;save()
        raise


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        print('Controlled core needs inspection ('+type(error).__name__+'). Existing processes and logs were retained.',file=sys.stderr)
        raise SystemExit(1)
