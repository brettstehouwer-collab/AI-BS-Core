"""Actual managed typed Play: SDK fixture, DX12/actions, isolated restart, stop/join."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,time,uuid

def verify(exe,fixture,output):
    exe,fixture,output=map(lambda p:p.resolve(),(exe,fixture,output))
    work=output/('managed-content-play-'+str(uuid.uuid4()));work.mkdir(parents=True)
    result={'schema_version':1,'status':'failed','executable':str(exe),'work_directory':str(work),'checks':[]}
    def check(ok,message):
        if not ok:raise AssertionError(message)
        result['checks'].append(message)
    def child(args,label,expected=0):
        p=subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=90)
        (work/(label+'.stdout.log')).write_text(p.stdout,encoding='utf-8');(work/(label+'.stderr.log')).write_text(p.stderr,encoding='utf-8')
        check(p.returncode==expected,f'{label}: exit {p.returncode}, expected {expected}: {p.stderr}')
        return p
    session=str(uuid.uuid4());scratch=work/'scratch';scratch.mkdir();database=scratch/'world.sqlite';stop=scratch/'stop.request'
    protected=work/'protected';protected.mkdir()
    sentinels={protected/'chapter.aiba':b'Retained authoring document - not a Play database',protected/'player.sqlite':b'Retained player save - not a Play database'}
    for path,data in sentinels.items():path.write_bytes(data)
    definition=work/'fixture'/'definition.aibd'
    def arguments(content=definition,play=session):
        return ['--durable-world','--content-definition',str(content),'--database',str(database),'--project','managed-content-proof','--branch','edited','--play-session',play,'--stop-file',str(stop)]
    def run(step,label):
        report,capture=work/(label+'.json'),work/(label+'.bmp')
        child([*arguments(),'--durable-step',step,'--durable-report',str(report),'--capture',str(capture)],label)
        data=json.loads(report.read_text(encoding='utf-8'))
        check(data['scope']['context']=='temporary_play' and data['scope']['timeline_id']==session,'isolated complete scratch scope')
        check(data['saved'] and data['pending_batches']==0,'all actual actions acknowledged')
        check(data['metrics']['debug_errors']==0 and data['metrics']['nonbackground_pixels']>10000,'actual DX12 content render/readback')
        check(capture.read_bytes()[:2]==b'BM','actual GPU capture')
        return data
    try:
        p=subprocess.run([str(fixture),str(work/'fixture')],capture_output=True,text=True,timeout=60)
        check(p.returncode==0,'canonical SDK content fixture exported')
        original=definition.read_bytes();definition_hash=hashlib.sha256(original).hexdigest()
        malformed=arguments();at=malformed.index('--database');del malformed[at:at+2]
        child(malformed,'malformed-managed',1)
        seeded=run('seed','seed')
        check(seeded['content']['fingerprint']==definition_hash,'immutable AIBD fingerprint is native runtime binding')
        objects=seeded['scene_objects']
        check(any(o['name']=='Main feed door' and o['center'][0]==-32.5 for o in objects),'authored moved main door reaches scene')
        check(any(o['name']=='Service relay socket' and o['center'][0]==-41.5 for o in objects),'authored moved socket reaches scene')
        check(any(o['persistent_id']==seeded['chapter_ids']['npc_quest'] and o['center'][0]==-39.5 for o in objects),'authored moved NPC anchor reaches scene')
        check(any(o['name']=='Pencil Room writing desk' and o['center'][0]==-39.5 for o in objects),'authored moved fixture reaches scene')
        check('edited world remembers' in seeded['hint'],'authored Adam cue reaches native HUD/report')
        progressed=run('content-route','route')
        check(progressed['metrics']['bypass_route'] and progressed['metrics']['walking_ticks']>500,'actual walking/build/relay/connect/door route')
        check(progressed['metrics']['repair_route'] and progressed['metrics']['decline'],'actual repair and optional moved NPC interaction')
        check(any(c['type']=='firstboot.ChapterProgress' and c['fields']['pencil_visited'] for c in progressed['components']),'physical moved chapter opens Pencil Room')
        restart=run('reload','restart')
        for key in ('scope','components','events','durable_revision','durable_sequence','content'):
            check(restart[key]==progressed[key],'restart preserves '+key)
        saved_hash=hashlib.sha256(database.read_bytes()).hexdigest()
        wrong=child([*arguments(work/'fixture'/'wrong.aibd'),'--durable-step','seed','--capture',str(work/'wrong.bmp'),'--durable-report',str(work/'wrong.json')],'wrong-binding',1)
        check('fingerprint mismatch' in wrong.stderr,'wrong content fails its immutable binding')
        check(hashlib.sha256(database.read_bytes()).hexdigest()==saved_hash,'wrong binding does not rewrite scratch database')
        child([*arguments(play=str(uuid.uuid4())),'--durable-step','seed','--capture',str(work/'wrong-session.bmp'),'--durable-report',str(work/'wrong-session.json')],'wrong-session',1)
        check(hashlib.sha256(database.read_bytes()).hexdigest()==saved_hash,'wrong session does not rewrite scratch database')
        with (work/'managed.stdout.log').open('w',encoding='utf-8') as stdout,(work/'managed.stderr.log').open('w',encoding='utf-8') as stderr:
            process=subprocess.Popen([str(exe),*arguments()],stdout=stdout,stderr=stderr,text=True)
            try:
                deadline=time.monotonic()+30
                while time.monotonic()<deadline:
                    text=(work/'managed.stdout.log').read_text(encoding='utf-8')
                    if 'aibs.play.ready' in text:break
                    if process.poll() is not None:raise AssertionError('Managed child exited before ready')
                    time.sleep(.05)
                check('aibs.play.ready' in text,'managed actual first frame reports ready')
                stop.write_text('stop requested by managed controller\n',encoding='utf-8');process.wait(timeout=30)
                check(process.returncode==0,'managed marker closes and joins native child')
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
        notices=[json.loads(line) for line in (work/'managed.stdout.log').read_text(encoding='utf-8').splitlines()]
        check([n['event'] for n in notices]==['aibs.play.ready','aibs.play.stopped'],'bounded ready and stopped lifecycle records')
        check(all(n['play_session']==session and n['content_fingerprint']==definition_hash and n['saved'] for n in notices),'graceful native lifecycle identifies exact saved session')
        check(definition.read_bytes()==original,'Play never modifies exported content')
        check(all(path.read_bytes()==data for path,data in sentinels.items()),'authoring and player-save sentinels remain byte-identical')
        check(not list(work.glob('*.sqlite')),'all gameplay files remain inside explicit scratch directory')
        result['status']='passed'
    except Exception as error:result['error']=str(error)
    result['completed_at']=datetime.now(timezone.utc).isoformat()
    target=output/('content-play-verification-'+work.name.removeprefix('managed-content-play-')+'.json');target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result));return 0 if result['status']=='passed' else 1

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: verify_content_play.py NATIVE_EXECUTABLE FIXTURE_EXECUTABLE OUTPUT_DIRECTORY')
    raise SystemExit(verify(*(Path(p) for p in sys.argv[1:])))
