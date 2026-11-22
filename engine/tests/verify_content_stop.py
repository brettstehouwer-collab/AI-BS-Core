"""Focused real native marker-Stop proof with a deliberately held async commit."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,uuid

def verify(exe,fixture,output):
    exe,fixture,output=(p.resolve() for p in (exe,fixture,output))
    work=output/('content-stop-drain-'+str(uuid.uuid4()));work.mkdir(parents=True)
    result={'schema_version':1,'status':'failed','executable':str(exe),'work_directory':str(work),'checks':[]}
    def check(ok,why):
        if not ok:raise AssertionError(why)
        result['checks'].append(why)
    session=str(uuid.uuid4());scratch=work/'scratch';scratch.mkdir();stop=scratch/'stop.request';database=scratch/'world.sqlite'
    def run(step):
        report=work/(step+'.json');capture=work/(step+'.bmp')
        args=[str(exe),'--durable-world','--content-definition',str(work/'fixture'/'definition.aibd'),'--database',str(database),'--project','managed-content-proof','--branch','edited','--play-session',session,'--stop-file',str(stop),'--durable-step',step,'--capture',str(capture),'--durable-report',str(report)]
        child=subprocess.run(args,capture_output=True,text=True,timeout=45)
        (work/(step+'.stdout.log')).write_text(child.stdout,encoding='utf-8');(work/(step+'.stderr.log')).write_text(child.stderr,encoding='utf-8')
        check(child.returncode==0,f'{step}: native exit {child.returncode}: {child.stderr}')
        return json.loads(report.read_text(encoding='utf-8'))
    try:
        child=subprocess.run([str(fixture),str(work/'fixture')],capture_output=True,text=True,timeout=60)
        check(child.returncode==0,'canonical immutable fixture exported')
        definition=(work/'fixture'/'definition.aibd').read_bytes();fp=hashlib.sha256(definition).hexdigest()
        drained=run('stop-drain')
        check(drained['metrics']['close_drained'] and drained['saved'] and drained['pending_batches']==0,'Stop waited for held worker then actual durable completion')
        check(drained['durable_revision']==1 and drained['durable_sequence']==1 and len(drained['events'])==1,'exact pending construction committed once')
        check(drained['scope']['context']=='temporary_play' and drained['scope']['timeline_id']==session and drained['content']['fingerprint']==fp,'drained save retains exact temporary content binding')
        check(drained['metrics']['debug_errors']==0 and drained['metrics']['nonbackground_pixels']>10000,'actual stopped DX12 scene remains captureable')
        check(stop.is_file(),'native proof requested real adjacent marker Stop')
        stop.unlink();reopened=run('inspect')
        check(all(reopened[k]==drained[k] for k in ('scope','components','events','content','durable_revision','durable_sequence')),'restarted scratch contains actual acknowledged pending batch')
        check((work/'fixture'/'definition.aibd').read_bytes()==definition,'pending Stop never rewrites immutable definition')
        result['status']='passed'
    except Exception as error:result['error']=str(error)
    result['completed_at']=datetime.now(timezone.utc).isoformat();target=output/('content-stop-verification-'+work.name.removeprefix('content-stop-drain-')+'.json')
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));return 0 if result['status']=='passed' else 1

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: verify_content_stop.py NATIVE_EXECUTABLE FIXTURE_EXECUTABLE OUTPUT_DIRECTORY')
    raise SystemExit(verify(*(Path(p) for p in sys.argv[1:])))
