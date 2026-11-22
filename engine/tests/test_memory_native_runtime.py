"""Explicit bounded process proof of native PC memory controls; synthetic only.

Run manually with --fixture/--player/--artifacts. No default discovery or family
recording is used. The parent serializes this with other real GPU tests.
"""
from pathlib import Path
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
import subprocess
import uuid


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--player',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True)
    options=parser.parse_args()
    fixture=options.fixture.resolve(strict=True)
    player=options.player.resolve(strict=True)
    parent=options.artifacts.resolve(strict=True)
    if not parent.is_dir() or not fixture.is_file() or not player.is_file():
        raise ValueError('Explicit existing fixture/player and evidence parent required')
    # Keep legacy Win32 evidence paths deliberately short. Never move/delete a
    # caller's project or source; this script only creates one new proof child.
    work=parent/('m'+uuid.uuid4().hex[:8]);work.mkdir()
    report={'schema_version':1,'status':'failed','family_references_used':False,
        'synthetic_silence':True,'work_directory':str(work),'processes':[],
        'player_sha256':digest(player),'fixture_sha256':digest(fixture)}
    environment=os.environ.copy()
    for key in ('PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH'):
        environment.pop(key,None)
    def run(label,arguments,timeout):
        try:
            process=subprocess.Popen(arguments,cwd=player.parent,env=environment,stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:out,error=process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill();out,error=process.communicate(timeout=5)
                raise RuntimeError(label+' exceeded deadline; owned child killed and joined')
            finally:
                report['processes'].append({'label':label,'pid':process.pid,'exit_code':process.returncode,'joined':process.poll() is not None})
            (work/(label+'.stdout.log')).write_bytes(out)
            (work/(label+'.stderr.log')).write_bytes(error)
            if process.returncode:
                raise RuntimeError(label+' failed: '+error.decode('utf-8','replace')[-2000:])
        except Exception:
            raise
    try:
        project=work/'p'
        run('fixture',[str(fixture),str(project)],25)
        expected=json.loads((project/'expected.json').read_text(encoding='utf-8'))
        if expected.get('family_references_used') is not False or expected.get('synthetic_silence') is not True:
            raise ValueError('Refuse unlabelled/non-synthetic memory proof fixture')
        pack=project/'assets/packs'/expected['pack_sha256']
        inputs=[project/'memory.aibd',project/'chapter.aiba',project/'.aibs-chapter-project.json',*pack.iterdir()]
        before={str(path.relative_to(project)):digest(path) for path in inputs}
        capture=work/'m.bmp';native_report=work/'m.json'
        run('memory-controls',[str(player),'--durable-world','--content-definition',str(project/'memory.aibd'),
            '--asset-root',str(project/'assets/packs'),'--database',str(work/'w.sqlite'),
            '--stop-file',str(work/'stop'),'--project','memory-native-proof','--branch','main',
            '--play-session',str(uuid.uuid4()),'--durable-step','memory-controls',
            '--capture',str(capture),'--durable-report',str(native_report)],55)
        native=json.loads(native_report.read_text(encoding='utf-8'))
        if native.get('status')!='passed' or native.get('memory_controls_verified') is not True:
            raise ValueError('Actual native memory controls proof did not complete')
        if native.get('memory_control_checks',0)<20 or native['memory_resumed_frame']<=native['memory_paused_frame']:
            raise ValueError('No measured source-frame pause/resume evidence')
        if native['metrics']['debug_errors'] or native['metrics']['debug_warnings']:
            raise ValueError('Native GPU diagnostics failed')
        media=native['memory_playback']
        if media['owned_pcm_bytes']!=0 or media['resident_bytes']>128*1024**2:
            raise ValueError('Stopped native media resources did not drain within profile')
        after={str(path.relative_to(project)):digest(path) for path in inputs}
        if before!=after:raise ValueError('Playback controls rewrote immutable content, authoring save or adopted pack')
        if not capture.is_file():raise ValueError('Actual GPU capture missing')
        report.update(status='passed',native_report=str(native_report),native=native,
            immutable_input_hashes=before,capture=str(capture))
    except Exception as error:
        report['error']=str(error)
    finally:
        report['completed_at']=datetime.now(timezone.utc).isoformat()
        (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'status':report['status'],'report':str(work/'verification.json'),
            **({'error':report['error']} if 'error'in report else {})}))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
