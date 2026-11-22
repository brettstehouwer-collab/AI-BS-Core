"""Explicit new-branch factory, both physical routes and fresh-process proof.

No original recording option is accepted. Parent runs serially with GPU tests.
The managed opening-controls step must prove actual focused native panel input,
pause, occlusion and glyph readback. Human pacing is never inferred from this
automated traversal's elapsed time.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--factory',type=Path,required=True)
    parser.add_argument('--player',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--capacitor-pack',type=Path)
    parser.add_argument('--adam-pack',type=Path)
    args=parser.parse_args()
    factory=args.factory.resolve(strict=True);player=args.player.resolve(strict=True)
    parent=args.artifacts.resolve(strict=True)
    if not parent.is_dir() or not factory.is_file() or not player.is_file():
        raise ValueError('Explicit executable files and an existing evidence directory are required')
    work=parent/('o'+uuid.uuid4().hex[:8]);work.mkdir()
    report={'version':1,'status':'failed','work':str(work),'checks':[],
        'family_recording_requested':False,'original_audio_played':False,
        'inspection_controls_verified':False,'human_pacing_measured':False,
        'executables':{'factory':sha(factory),'player':sha(player)},
        'driver_sha256':sha(Path(__file__).resolve()),'processes':[],
        'coverage':{'unearned_seed':False,'opening_controls':False,'repair_route':False,
            'bypass_route':False,'door_cycle':False,'help':False,'decline':False,
            'depart_return':False,'feed_loss':False,'f9':False,'fresh_restart':False}}
    environment=os.environ.copy()
    for key in ('PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH'):
        environment.pop(key,None)

    def check(value,message):
        if not value:raise AssertionError(message)
        report['checks'].append(message)

    def identity(value):
        check(isinstance(value,str) and str(uuid.UUID(value))==value
            and uuid.UUID(value).version==4,'Canonical persistent UUID: '+str(value))

    def record(value,alias):
        return next(item['fields'] for item in value['components']
            if item['entity_id']==value['chapter_ids'][alias])

    def durable(value):
        return {key:value[key] for key in ('scope','visible_revision','durable_revision',
            'durable_sequence','saved','pending_batches','chapter_ids','components','events')}

    def bitmap(path):
        with path.open('rb') as stream:header=stream.read(54)
        return len(header)==54 and header[:2]==b'BM' and path.stat().st_size>54

    def child(label,command,timeout=180):
        with (work/(label+'.stdout.log')).open('xb') as out,(work/(label+'.stderr.log')).open('xb') as err:
            process=subprocess.Popen(list(map(str,command)),stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                env=environment,cwd=player.parent,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                code=process.wait(timeout=timeout)
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
                report['processes'].append({'label':label,'pid':process.pid,'exit_code':process.returncode,'joined':process.poll() is not None})
        check(code==0,label+': child completed: '+(work/(label+'.stderr.log')).read_text(encoding='utf-8',errors='replace')[-1600:])

    try:
        project=work/'p';command=[factory,'--output',project]
        for name,value in (('--capacitor-pack',args.capacitor_pack),('--adam-pack',args.adam_pack)):
            if value is not None:command += [name,value.resolve(strict=True)]
        child('factory',command,45)
        expected=json.loads((project/'opening-manifest.json').read_text(encoding='utf-8'))
        check(expected['required_capability']=='chapter-authored-inspections-v1' and len(expected['stops'])==7,'Seven explicit authored inspection stops declared')
        check(not expected['recording_bound'] and not expected['audio_played'] and not expected['timer_gates'],'Proof contains no original recording, autoplay or timing gate')
        for key in ('definition_id','world_id'):identity(expected[key])
        expected_model=next((dict((name,dependency[name]) for name in ('asset_id','asset_sha256','pack_sha256'))
            for dependency in expected['dependencies'] if dependency['kind']==1),None)
        check((expected_model is not None)==(args.adam_pack is not None),'Optional exact model dependency agrees with explicit input')
        inputs={str(path.relative_to(project)):sha(path) for path in project.rglob('*') if path.is_file()}

        def run(route,step,session,label):
            state=work/route;state.mkdir(exist_ok=True)
            evidence=work/(label+'.json');capture=work/(label+'.bmp')
            child(label,[player,'--durable-world','--content-definition',project/'opening.aibd',
                '--asset-root',project/'assets/packs','--database',state/'w.sqlite',
                '--project','first-boot-warm-opening','--branch','warm-beginning-opening-v1',
                '--play-session',session,'--stop-file',state/'stop','--durable-step',step,
                '--capture',capture,'--durable-report',evidence])
            value=json.loads(evidence.read_text(encoding='utf-8'))
            check(value['status']=='passed' and value['saved'] and value['pending_batches']==0
                and value['visible_revision']==value['durable_revision'],label+': durable head acknowledged')
            scope=value['scope'];check(scope['project_id']=='first-boot-warm-opening'
                and scope['branch_id']=='warm-beginning-opening-v1'
                and scope['timeline_id']==session and scope['world_id']==expected['world_id']
                and scope['context']=='temporary_play',label+': exact isolated world/timeline')
            check(value['content']['definition_id']==expected['definition_id']
                and value['content']['fingerprint']==expected['fingerprint'],label+': immutable opening pinned')
            gpu=value['metrics'];check(gpu['debug_errors']==0 and gpu['debug_warnings']==0
                and gpu['nonbackground_pixels']>10000 and gpu['hud_fits'],label+': actual GPU image, clean diagnostics and readable HUD')
            check(gpu['hud_readback'] and gpu['hud_capture'] and gpu['hud_needed_height']<=gpu['hud_height'],label+': native HUD glyphs fit actual capture')
            guide=value['companion'];check(guide['character_rendered'] and guide['character_frames']>0
                and guide['character_readback_changed_bytes']>300,label+': actual indexed Adam resource rendered')
            check(guide['model_reference']==expected_model and guide['character_kind']==
                ('cooked_character' if expected_model else 'temporary_articulated'),label+': exact optional character kind/reference')
            intent=next(item for item in value['components'] if item['type']=='firstboot.CompanionIntent')
            check(guide['entity_id']==intent['entity_id'] and guide['follow']==intent['fields']['follow']
                and guide['anchor']==[intent['fields'][key] for key in ('anchor_x','anchor_y','anchor_z')],label+': guide matches saved intent/anchor')
            check(not guide['recall_required'] and guide['feet'] is not None
                and guide['scene_revision']==value['visible_revision'],label+': current independent guide reconstructed')
            for path in (capture,Path(str(capture)+'.pov.bmp'),Path(str(capture)+'.hud.bmp')):
                check(bitmap(path),label+': actual native GPU/POV/HUD BMP '+path.name)
            check({stop['id'] for stop in expected['stops']}<=
                {item['persistent_id'] for item in value['scene_objects']},label+': all seven panels remain physical scene fixtures')
            entities={item['entity_id'] for item in value['components']}
            check(len(entities)==len(value['components']),label+': no duplicated component UUIDs')
            previous=None;seen=set()
            for event in value['events']:
                check(event['event_id'] not in seen and event['subject_id'] in entities
                    and event['type'] in ('repair.outcome','construction.outcome','route.outcome',
                        'hazard.outcome','mechanism.outcome','quest.outcome','companion.outcome')
                    and event['revision']<=value['durable_revision']
                    and (previous is None or event['sequence']==previous+1),label+': authentic contiguous typed event '+event['event_id'])
                seen.add(event['event_id']);previous=event['sequence']
            check((previous or 0)==value['durable_sequence'],label+': acknowledged sequence agrees with real history')
            return value

        controls_session=str(uuid.uuid4());control_seed=run('controls','seed',controls_session,'controls-seed')
        check(not record(control_seed,'progress')['shelter_secured']
            and not record(control_seed,'progress')['pencil_visited']
            and record(control_seed,'progress')['first_route']=='none'
            and not control_seed['lighting']['main_power'] and not control_seed['lighting']['bypass_power']
            and control_seed['lighting']['points']==2,'Warm reserve nook grants no shelter, route or restored power')
        report['coverage']['unearned_seed']=True
        controls=run('controls','opening-controls',controls_session,'opening-controls')
        check(controls['opening_inspections_count']==7 and controls['opening_controls_verified']
            and controls['opening_control_checks']>=20 and not controls['opening_panel_visible'],
            'Actual seven-stop opening panel controls, pause/input/reload verified and panel closed')
        check(bitmap(work/'opening-controls.bmp.opening-panel.bmp'),
            'Actual read-only opening panel glyph BMP retained')
        check(type(controls['guide_clip']) is int and 0<=controls['guide_clip']<=3
            and type(controls['guidance_gestures']) is int and controls['guidance_gestures']>0,
            'Actual guidance pulse count and valid idle/walk/catch-up/guidance clip observed')
        check(durable(controls)==durable(control_seed),'Reading/seating, blocked choices and panel reload create no durable progress/history')
        report['coverage']['opening_controls']=True;report['inspection_controls_verified']=True

        for route in ('repair-route','bypass-route'):
            session=str(uuid.uuid4());seed=run(route,'seed',session,route+'-seed')
            check(not record(seed,'progress')['shelter_secured'] and record(seed,'progress')['first_route']=='none',route+': fresh unearned starting state')
            first=run(route,route,session,route)
            progress=next(row['fields'] for row in first['components'] if row['type']=='firstboot.ChapterProgress')
            check(progress['first_route']==route.removesuffix('-route') and progress['shelter_secured']
                and progress['pencil_visited'],route+': actual route reaches shelter and Pencil Room')
            check(first['metrics'][route.replace('-','_')] and first['metrics']['walking_ticks']>500,
                route+': actual grounded W/E/B controller proof executed')
            check(first['lighting']['points']==6 and first['lighting'][
                'main_power' if route=='repair-route' else 'bypass_power']
                and sha(work/(route+'.bmp'))!=sha(work/(route+'-seed.bmp')),
                route+': restored circuit adds real lights and changes actual native pixels')
            check(first['companion']['follow_route_verified'] and first['companion']['follow'],route+': Adam physically follows without automatic Recall')
            restarted=run(route,'inspect',session,route+'-reopen')
            check(durable(restarted)==durable(first)
                and sha(work/(route+'.bmp'))==sha(work/(route+'-reopen.bmp')),
                route+': fresh process preserves exact choices, scope, heads/history and overview pixels')
            report['coverage'][route.replace('-','_')]=True;report['coverage']['fresh_restart']=True
            if route=='repair-route':
                cycled=run(route,'door-cycle',session,'opening-door-cycle')
                check(cycled['metrics']['door_cycle'],'Actual occupied-door rejection, clear close and reopen')
                report['coverage']['door_cycle']=True
                helped=run(route,'help',session,'opening-help')
                check(helped['metrics']['help'] and record(helped,'npc_quest')['lamp_connected'],
                    'Actual Ctrl+Y and lamp interaction preserve optional help route')
                report['coverage']['help']=True
                returned=run(route,'depart-return',session,'opening-depart-return')
                check(returned['metrics']['depart_return'],'Actual grounded departure and return through dressed hub')
                report['coverage']['depart_return']=True
                reloaded=run(route,'reload',session,'opening-f9')
                check(reloaded['metrics']['reload'] and durable(reloaded)==durable(returned),
                    'Actual F9 reload preserves optional choices and chapter state')
                report['coverage']['f9']=True
            else:
                declined=run(route,'decline',session,'opening-decline')
                check(declined['metrics']['decline'] and not record(declined,'npc_quest')['lamp_connected'],
                    'Actual Ctrl+Z preserves optional decline without forcing lamp help')
                report['coverage']['decline']=True
                removed=run(route,'feed-loss',session,'opening-feed-loss')
                relay=record(first,'fault')['bypass_relay']
                check(removed['metrics']['feed_loss'] and not next(item['fields']['alive']
                    for item in removed['components'] if item['entity_id']==relay)
                    and record(removed,'service_door')['open']
                    and record(removed,'service_door')['unlocked'] and 'relay feed is offline' in removed['hint'],
                    'Actual Delete retains relay tombstone and truthful unpowered latched return')
                report['coverage']['feed_loss']=True
                final=run(route,'inspect',session,'opening-feed-loss-reopen')
                check(durable(final)==durable(removed),'Fresh process retains dismantled feed and decline')
        check({str(path.relative_to(project)):sha(path) for path in project.rglob('*') if path.is_file()}==inputs,
            'All source chapter, metadata and adopted dependency bytes unchanged by play/restart')
        check(all(report['coverage'].values()),'Every requested dressed-opening coverage item executed')
        report['status']='passed'
    except Exception as error:
        report['error']=str(error)
    finally:
        report['completed_at']=datetime.now(timezone.utc).isoformat()
        destination=work/'verification.json';destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'report':str(destination),'checks':len(report['checks']),
        **({'error':report['error']} if 'error' in report else {})}))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
