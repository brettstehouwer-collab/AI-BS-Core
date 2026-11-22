"""Private native keys/companion admission, routes and fresh-process save proof."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, math, subprocess, sys, uuid

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(fixture, player, output, model_pack=None):
    fixture, player, output = (Path(p).resolve() for p in (fixture, player, output))
    output.mkdir(parents=True, exist_ok=True)
    work=output/('companion-native-'+str(uuid.uuid4()));work.mkdir()
    report=output/(work.name+'-verification.json')
    result={'schema_version':1,'status':'failed','checks':[],'work_directory':str(work),
            'gpu_requested':True,'character_rendering_requested':True,
            'family_references_used':False,'model_inference':False,'processes_joined':False}
    processes=[]
    def check(value,message):
        if not value:raise AssertionError(message)
        result['checks'].append(message)
    def child(exe,args,label,seconds=240):
        with (work/(label+'.stdout.log')).open('xb') as stdout,(work/(label+'.stderr.log')).open('xb') as stderr:
            p=subprocess.Popen([str(exe),*map(str,args)],stdout=stdout,stderr=stderr,stdin=subprocess.DEVNULL,
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p)
            try:code=p.wait(timeout=seconds)
            finally:
                if p.poll() is None:p.kill();p.wait(timeout=15)
        check(code==0,label+': actual process completed: '+(work/(label+'.stderr.log')).read_text(encoding='utf-8',errors='replace')[-2000:])
    def run(folder,step,session,label):
        capture=work/(label+'.bmp');proof=work/(label+'.json')
        child(player,['--durable-world','--content-definition',work/'content/companion.aibd','--asset-root',work/'content/empty-packs',
                      '--database',folder/'world.sqlite','--project','companion-native-proof','--branch','main','--play-session',session,
                      '--stop-file',folder/'stop.request','--durable-step',step,'--capture',capture,'--durable-report',proof],label)
        data=json.loads(proof.read_text(encoding='utf-8'))
        check(data['status']=='passed' and data['saved'] and data['pending_batches']==0 and data['visible_revision']==data['durable_revision'],label+': actual durable head acknowledged')
        check(data['scope']['context']=='temporary_play' and data['scope']['project_id']=='companion-native-proof' and data['scope']['timeline_id']==session and data['scope']['world_id']==expected['world_id'],label+': exact isolated scope')
        check(data['content']['fingerprint']==expected['fingerprint'],label+': immutable authored definition pinned')
        guide=data['companion'];record=next(r for r in data['components'] if r['type']=='firstboot.CompanionIntent')
        check(guide['entity_id']==record['entity_id']==expected['companion_id'] and guide['follow']==record['fields']['follow'] and guide['anchor']==[record['fields']['anchor_x'],record['fields']['anchor_y'],record['fields']['anchor_z']],label+': runtime agrees with exact saved intent/anchor')
        check(not guide['recall_required'] and guide['feet'] is not None and guide['scene_revision']==data['visible_revision'],label+': current independent controller reconstructed')
        check(guide['character_rendered'],label+': articulated guide produces actual indexed native pixels')
        kind='cooked_character' if model_pack is not None else 'temporary_articulated'
        check(guide['character_kind']==kind and guide['character_readback_changed_bytes']>300 and guide['character_frames']>0,label+': character resource kind and paired GPU readback verified')
        if model_pack is not None:
            check(guide['model_reference']==expected['model_reference'],label+': exact cooked character reference survives native restart')
        check(data['metrics']['debug_errors']==0 and data['metrics']['debug_warnings']==0 and data['metrics']['nonbackground_pixels']>10000 and data['metrics']['hud_fits'],label+': actual GPU readback, zero debug diagnostics and complete native HUD')
        check(capture.is_file() and capture.read_bytes()[:2]==b'BM',label+': actual native capture exists')
        return data
    try:
        result['source_sha256']={p.name:sha(p) for p in (Path(__file__),Path(__file__).with_name('companion_native_fixture.cpp'))}
        result['executable_sha256']={'fixture':sha(fixture),'native_player':sha(player)}
        child(fixture,[work/'content',*([Path(model_pack).resolve()] if model_pack is not None else [])],'prepare',60)
        expected=json.loads((work/'content/expected.json').read_text(encoding='utf-8'))
        original=sha(work/'content/companion.aibd')
        for step in ('companion-controls','repair-route','bypass-route'):
            folder=work/step;folder.mkdir();session=str(uuid.uuid4());first=run(folder,step,session,step)
            if step=='companion-controls':
                check(first['companion']['controls_verified'] and not first['companion']['follow'], 'Actual F6/F7/F8, held-credit rejection, inspection/pause gating and F9 reload passed')
                check(first['visible_revision']==4 and first['durable_sequence']==4,'Only four deliberate companion choices persisted')
                progress=next(r['fields'] for r in first['components'] if r['type']=='firstboot.ChapterProgress')
                check(not progress['shelter_secured'] and progress['first_route']=='none','Companion choices grant no repair, route or shelter progress')
            else:
                check(first['companion']['follow'] and first['companion']['follow_route_verified'],step+': Adam physically follows the actual route without an automatic Recall')
            reopened=run(folder,'inspect',session,step+'-reopened')
            check(reopened['components']==first['components'] and reopened['events']==first['events'] and reopened['visible_revision']==first['visible_revision'] and reopened['durable_sequence']==first['durable_sequence'],step+': fresh process preserves exact state, events and head')
            check(reopened['companion']['anchor']==first['companion']['anchor'] and reopened['companion']['follow']==first['companion']['follow'],step+': fresh process restores only durable intent/anchor')
            if not reopened['companion']['follow']:
                check(math.dist(reopened['companion']['feet'],reopened['companion']['anchor'])<.03,'Restarted waiting guide stays at its supported anchor')
        check(sha(work/'content/companion.aibd')==original,'Native controls/routes preserve the authored source bytes')
        result['status']='passed'
    except Exception as error:result['error']=str(error)
    finally:
        for p in processes:
            if p.poll() is None:p.kill();p.wait(timeout=15)
        result['processes_joined']=all(p.poll() is not None for p in processes)
        result['completed_at']=datetime.now(timezone.utc).isoformat()
        report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'report':str(report),'checks':len(result['checks']),**({'error':result['error']} if 'error' in result else {})}))
    return 0 if result['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(verify(*sys.argv[1:]))
