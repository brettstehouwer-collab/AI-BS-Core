"""Prepare a pinned Workshop.7.1 five-minute review; --play explicitly opens it."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from native_studio.game_engine.saved_play_storage import checked_path

PACKAGE = ROOT/'native_studio/releases/v5.329.173-workshop.7.1/AI_BS_Studio'
PLAYER = PACKAGE/'_internal/game_assets/player/aibs_motherboard.exe'
DEFAULT_PROJECT = ROOT/'t/fw-71cb086b/Workshop'
OUTPUT = ROOT/'t/workshop-performance'
PLAYER_SHA = '27c63cc08969e1b2c975fee05c927559dc9992cc2c46b9f51a14a27c3c63f212'
MANIFEST_SHA = 'b0d8cb7ef48671d148c45af7ac22751e22297ad5014a0e342217c07ebce0fdf5'


def digest(path):
    checked_path(path, directory=False)
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path, limit=1024*1024):
    checked_path(path, directory=False)
    if path.stat().st_size > limit:
        raise ValueError('Oversized metadata')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate metadata key')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite metadata')))


def write(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def runtime():
    path=ROOT/'backups/workshop_corridor_20261121_v01/build/qualified-stage/package-manifest.json'
    if digest(path)!=MANIFEST_SHA:
        raise ValueError('Workshop.7.1 package manifest changed')
    manifest = read(path)
    selected = {key:value for key,value in manifest.items() if key.startswith('_internal/game_assets/player/')}
    if not selected or digest(PLAYER) != PLAYER_SHA:
        raise ValueError('Workshop.7.1 player pin differs')
    for name, sha in selected.items():
        if digest(PACKAGE/name) != sha:
            raise ValueError('Packaged runtime member differs: '+name)
    return selected


def project_files(project):
    project = checked_path(project, directory=True)
    manifest = read(project/'opening-manifest.json')
    metadata = read(project/'.aibs-chapter-project.json')
    wanted_packs={item['pack_sha256'] for item in manifest.get('dependencies',[])}
    files = {}
    total = 0
    for here, directories, names in os.walk(project, followlinks=False):
        here = Path(here)
        if here==project:
            directories[:]=[name for name in directories if name=='assets']
            names=[name for name in names if name in ('opening.aibd','opening-manifest.json')]
        elif here==project/'assets':
            directories[:]=[name for name in directories if name=='packs'];names=[]
        elif here==project/'assets/packs':
            directories[:]=[name for name in directories if name in wanted_packs];names=[]
        for name in directories:
            checked_path(here/name, directory=True)
        for name in names:
            path = checked_path(here/name, directory=False)
            total += path.stat().st_size
            if len(files) >= 256 or total > 128*1024**2 or path.stat().st_size > 49*1024**2:
                raise ValueError('Published chapter closure exceeds review limits')
            files[path.relative_to(project).as_posix()] = digest(path)
    if manifest.get('opening_workshop') is not True or manifest.get('recording_bound') is not False:
        raise ValueError('Expected a published Workshop without recorded audio')
    if files.get('opening.aibd') != manifest.get('fingerprint'):
        raise ValueError('Published definition differs from its manifest')
    uuid.UUID(manifest['world_id'])
    dependencies = manifest.get('dependencies')
    if not isinstance(dependencies,list) or not 1 <= len(dependencies) <= 32:
        raise ValueError('Missing bounded chapter dependencies')
    packs = set()
    for dependency in dependencies:
        pack = dependency['pack_sha256']; asset = dependency['asset_sha256']
        if len(pack)!=64 or any(c not in '0123456789abcdef' for c in pack+asset) or len(asset)!=64:
            raise ValueError('Invalid dependency identity')
        packs.add(pack)
        members = [name for name in files if name.startswith('assets/packs/'+pack+'/')]
        if not any(Path(name).stem==asset and files[name]==asset for name in members):
            raise ValueError('Referenced asset bytes absent from dependency closure')
        if 'assets/packs/'+pack+'/catalog.aibcat' not in files:
            raise ValueError('Referenced pack catalog absent')
    actual = {Path(name).parts[2] for name in files if name.startswith('assets/packs/')}
    if actual != packs:
        raise ValueError('Pack closure differs from manifest dependencies')
    files={name:sha for name,sha in files.items() if name in ('opening.aibd','opening-manifest.json') or
        name.startswith('assets/packs/')}
    return project, files, manifest, metadata


def verify_packs(project, manifest):
    # Reuse the maintained typed catalog, payload, complete pack hash and
    # closure validator. Its temporary role manifest is never an input asset.
    from native_studio.game_engine.opening_assets import read_opening_assets, OPENING_ROLES
    dependencies=manifest['dependencies']
    if len(dependencies)!=6 or [item['kind'] for item in dependencies]!=[0,1,0,0,0,0]:
        raise ValueError('Workshop review requires its six standard typed dependencies')
    path=project/'opening-assets.json'
    write(path,{'version':1,'roles':{role:{'directory':'assets/packs/'+item['pack_sha256'],
        **{key:item[key] for key in ('asset_id','asset_sha256','pack_sha256')}}
        for role,item in zip(OPENING_ROLES,dependencies)}})
    try:
        read_opening_assets(project,verify_pack_contents=True)
    finally:
        path.unlink()


def staged_files(project):
    files={}
    for here,_,names in os.walk(project):
        for name in names:
            path=Path(here)/name
            files[path.relative_to(project).as_posix()]=digest(path)
    return files


def prepare(project):
    pins = runtime()
    project, files, manifest, metadata = project_files(project)
    checked_path(OUTPUT, directory=True, missing=True)
    OUTPUT.mkdir(exist_ok=True)
    session = OUTPUT/str(uuid.uuid4());session.mkdir()
    copied = session/'chapter';copied.mkdir()
    for name, sha in files.items():
        target = copied/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:
            stream.write((project/name).read_bytes())
        if digest(target)!=sha:
            raise ValueError('Chapter changed while copying')
    if project_files(project)[1] != files:
        raise ValueError('Source chapter changed during preparation')
    verify_packs(copied,manifest)
    invocation, timeline = str(uuid.uuid4()), str(uuid.uuid4())
    command = [str(PLAYER),'--durable-world','--content-definition',str(copied/'opening.aibd'),
        '--asset-root',str(copied/'assets/packs'),'--database',str(session/'world.sqlite'),
        '--project',metadata['project'],'--branch',metadata['branch'],'--play-session',invocation,
        '--stop-file',str(session/('stop.'+invocation+'.request')),'--persistent-play',
        '--timeline-id',timeline,'--width','1920','--height','1080','--performance-gameplay',
        '--performance-seconds','300','--performance-warmup','2',
        '--performance-report',str(session/'performance.json'),'--capture',str(session/'after.bmp')]
    request = {'status':'prepared_not_launched','source_project':str(project),'source_files':files,
        'runtime_files':pins,'player_sha256':PLAYER_SHA,'expected_fingerprint':manifest['fingerprint'],
        'expected_world':manifest['world_id'],'expected_timeline':timeline,'play_session':invocation,
        'project_id':metadata['project'],'branch_id':metadata['branch'],'command':command,
        'existing_save_used':False,'focus_forced':False,'automated_input':False,
        'content_scope':'Exact published opening.aibd and dependencies; authoring changes require republishing first'}
    write(session/'request.json',request)
    return session, request


def assess_session(session):
    session = checked_path(session,directory=True)
    if session.parent != OUTPUT:
        raise ValueError('Assessment requires a review-owned session')
    request = read(session/'request.json'); process = read(session/'process.json')
    from workshop_performance_review import assess, summarize_gpu_samples
    try:
        gpu = read(session/'gpu-memory.json',limit=2*1024*1024)
        gpu_summary = summarize_gpu_samples(gpu,expected_pid=process.get('pid'))
    except (ValueError,OSError) as exc:
        gpu_summary = {**summarize_gpu_samples(None,expected_pid=process.get('pid')),
            'sidecar_error':type(exc).__name__+': '+str(exc)}
    sidecar = {'gpu_memory_report':str(session/'gpu-memory.json'),
        'gpu_process_local_samples':gpu_summary}
    try:
        report = read(session/'performance.json')
    except (ValueError,OSError) as exc:
        return {**sidecar,'review_status':'unusable_native_report','cli_exit_code':2,'process':process,
            'error':type(exc).__name__+': '+str(exc),'gate_pass':False}
    result = assess(report,expected_fingerprint=request['expected_fingerprint'],
        expected_world=request['expected_world'],expected_timeline=request['expected_timeline'])
    result={**result,'process':process,**sidecar,'native_error':report.get('error')}
    if process.get('exit_code') != 0 or process.get('interrupted') or not process.get('joined') or report.get('status')!='measured':
        return {**result,'review_status':'unusable_native_or_process_failure','cli_exit_code':2,
            'error':report.get('error')}
    stdout=session/'stdout.log'
    if stdout.stat().st_size > 65536:
        raise ValueError('Oversized lifecycle log')
    notices=[json.loads(line) for line in stdout.read_text().splitlines() if line.startswith('{')]
    if [row.get('event') for row in notices] != ['aibs.saved_play.ready','aibs.saved_play.stopped']:
        raise ValueError('Missing normal saved-play lifecycle')
    for row in notices:
        if any(row.get(key)!=value for key,value in {'play_session':request['play_session'],
            'project_id':request['project_id'],'branch_id':request['branch_id'],
            'timeline_id':request['expected_timeline'],'world_id':request['expected_world'],
            'content_fingerprint':request['expected_fingerprint'],'saved':True}.items()):
            raise ValueError('Lifecycle binding mismatch')
    if notices[-1].get('durable_revision') != report.get('durable_revision'):
        raise ValueError('Stopped/report durable head differs')
    return {**result,'review_status':'assessed','cli_exit_code':0 if result.get('gate_pass') is True else 3}


def play(session, request):
    print('Prepared review: '+str(session))
    print('Take the main repair route or relay bypass toward the shelter and Pencil Room. The review uses a separate save.')
    print('The five-minute timer measures the game and its reading panel while they are in front. Switching apps or closing early ends the sample.')
    if runtime()!=request['runtime_files'] or project_files(Path(request['source_project']))[1]!=request['source_files']:
        raise ValueError('Runtime/source changed after preparation')
    if staged_files(session/'chapter')!=request['source_files']:
        raise ValueError('Prepared chapter changed')
    verify_packs(session/'chapter',read(session/'chapter/opening-manifest.json'))
    write(session/'launch-intent.json',{'command':request['command']})
    interrupted=False
    observer_error=None
    from workshop_gpu_memory import GpuMemorySampler
    with (session/'stdout.log').open('xb') as out,(session/'stderr.log').open('xb') as err:
        process=subprocess.Popen(request['command'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,
            cwd=str(PLAYER.parent),shell=False)
        try:
            with GpuMemorySampler(process,interval_seconds=1.0) as sampler:
                process.wait(timeout=390)
        except (subprocess.TimeoutExpired,KeyboardInterrupt):
            interrupted=True
        except Exception as exc:
            interrupted=True
            observer_error=type(exc).__name__+': '+str(exc)[:240]
        finally:
            if process.poll() is None:
                (session/('stop.'+request['play_session']+'.request')).write_bytes(b'stop\n')
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=10);interrupted=True
            write(session/'process.json',{'pid':process.pid,'exit_code':process.returncode,
                'joined':process.poll() is not None,'interrupted':interrupted,
                'gpu_observer_error':observer_error,'gpu_report':'gpu-memory.json'})
        try:
            gpu_report=sampler.report()
        except Exception as exc:
            gpu_report={'status':'unknown','error':type(exc).__name__,'gpu_verification_claimed':False}
        write(session/'gpu-memory.json',gpu_report)
    if runtime()!=request['runtime_files'] or project_files(Path(request['source_project']))[1]!=request['source_files']:
        raise ValueError('Runtime/source changed during review')
    try:
        result=assess_session(session)
    except (ValueError,OSError) as exc:
        result={'review_status':'assessment_validation_failed','cli_exit_code':3,
            'gate_pass':False,'error':type(exc).__name__+': '+str(exc)}
    result={**result,'gpu_memory_report':str(session/'gpu-memory.json'),
        'gpu_memory_assessment':'Separate observer evidence; unknown data does not establish GPU budget qualification'}
    write(session/'assessment.json',result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=DEFAULT_PROJECT)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare-only',action='store_true')
    mode.add_argument('--play',action='store_true')
    mode.add_argument('--assess-session',type=Path,help='Recover assessment of an already completed session; never launches')
    args=parser.parse_args(argv)
    try:
        if args.assess_session:
            try:
                result=assess_session(args.assess_session)
            except (ValueError,OSError) as exc:
                result={'review_status':'assessment_validation_failed','cli_exit_code':3,
                    'gate_pass':False,'error':type(exc).__name__+': '+str(exc)}
        else:
            project=args.project
            if args.play and project==DEFAULT_PROJECT and not project.exists():
                import tkinter
                from tkinter import filedialog
                window=tkinter.Tk();window.withdraw()
                try:
                    selected=filedialog.askdirectory(title='Choose your published Workshop project')
                finally:
                    window.destroy()
                if not selected:
                    raise ValueError('No project selected; review was not launched')
                project=Path(selected)
            session, request=prepare(project)
            result=play(session,request) if args.play else {'status':'prepared_not_launched','session':str(session),
                'command':request['command'],'expected_fingerprint':request['expected_fingerprint']}
        if args.play:
            if result.get('review_status') == 'unusable_native_or_process_failure':
                print('The player could not finish a valid measurement. Reason:', result.get('native_error') or 'See performance.json.')
            elif result.get('timing_pass'):
                print('The five-minute timing checks passed. See the assessment for route coverage and remaining checks.')
            else:
                print('The review is incomplete. See the assessment for the checks that need attention.')
            print('Results and separate save:', session)
        else:
            print(json.dumps(result, indent=2))
        return result.get('cli_exit_code', 0)
    except (Exception,KeyboardInterrupt) as exc:
        print(type(exc).__name__+': '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':
    raise SystemExit(main())
