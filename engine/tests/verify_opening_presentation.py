"""Managed new-branch seven-stop native tour, real1080p timing and optional video.

No original-audio argument exists. Child processes are bounded and joined.
Automated walkthrough duration does not demonstrate8–12minute human pacing.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import uuid

ROLES=('controller','truck','diagnostic','bypass','seats','shelter','pencil')
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def bmp(path):
    with path.open('rb') as stream:
        header=stream.read(54)
        if len(header)!=54 or header[:2]!=b'BM':raise AssertionError('Missing native BMP: '+str(path))
        width,height=struct.unpack_from('<ii',header,18)
        if width<=0 or height==0 or path.stat().st_size<=54:raise AssertionError('Invalid native BMP geometry')
        return width,abs(height)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('factory','player','artifacts'):p.add_argument('--'+flag,type=Path,required=True)
    for flag in ('capacitor-pack','adam-pack','ffmpeg','ffprobe','failure-encoder'):p.add_argument('--'+flag,type=Path)
    p.add_argument('--record',action='store_true');p.add_argument('--skip-performance',action='store_true')
    p.add_argument('--encoder',choices=('auto','nvenc','software'),default='auto')
    args=p.parse_args();factory=args.factory.resolve(strict=True);player=args.player.resolve(strict=True);parent=args.artifacts.resolve(strict=True)
    if not parent.is_dir():raise ValueError('Existing evidence parent required')
    if args.record and not all((args.ffmpeg,args.ffprobe)):raise ValueError('Explicit installed ffmpeg and ffprobe required for video')
    work=parent/('p'+uuid.uuid4().hex[:8]);work.mkdir();report={'version':1,'status':'failed','human_pacing_measured':False,'original_audio_requested':False,'original_audio_autoplay':False,'work':str(work),'executables':{'player':sha(player),'factory':sha(factory)},'driver_sha256':sha(Path(__file__).resolve()),'checks':[],'processes':[]}
    env=os.environ.copy()
    for key in ('PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH'):env.pop(key,None)
    def check(value,message):
        if not value:raise AssertionError(message)
        report['checks'].append(message)
    def child(label,command,timeout):
        with (work/(label+'.stdout.log')).open('xb') as out,(work/(label+'.stderr.log')).open('xb') as err:
            process=subprocess.Popen(list(map(str,command)),stdin=subprocess.DEVNULL,stdout=out,stderr=err,env=env,cwd=player.parent,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:code=process.wait(timeout=timeout)
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
                report['processes'].append({'label':label,'pid':process.pid,'exit_code':process.returncode,'joined':process.poll() is not None})
        check(code==0,label+': bounded child terminal: '+(work/(label+'.stderr.log')).read_text(encoding='utf-8',errors='replace')[-1200:])
    def record(value,kind):return next(row['fields'] for row in value['components'] if row['type']==kind)
    def durable(value):return {key:value[key] for key in ('scope','visible_revision','durable_revision','durable_sequence','components','events')}
    try:
        project=work/'p';cmd=[factory,'--output',project]
        for name,value in (('--capacitor-pack',args.capacitor_pack),('--adam-pack',args.adam_pack)):
            if value:cmd += [name,value.resolve(strict=True)]
        child('factory',cmd,60);manifest=json.loads((project/'opening-manifest.json').read_text(encoding='utf-8'))
        check('chapter-initial-view-v1' in manifest['required_capabilities'],'New view-specific capability declared')
        check(not manifest['recording_bound'] and not manifest['audio_played'] and not manifest['timer_gates'],'No original audio bound/autoplay or normal-game timing gates')
        sidecar=project/'opening-tour.aibtour';lines=sidecar.read_text(encoding='ascii').splitlines();check(len(lines)==9 and lines[0]=='AIBTOUR 1','Strict bounded seven-role sidecar published')
        check(lines[1].split()==[manifest['definition_id'],manifest['world_id'],manifest['fingerprint']],'Sidecar exact definition/world/fingerprint pinned')
        bindings={role:identity for role,identity in map(str.split,lines[2:])};check(tuple(bindings)==ROLES and len(set(bindings.values()))==7,'Seven distinct typed role identities, no name parsing')
        stops={row['id']:row for row in manifest['stops']};source_files={str(path.relative_to(project)):sha(path) for path in project.rglob('*') if path.is_file()}
        def invoke(label,state,session,flags,timeout=180):
            state.mkdir(exist_ok=True);capture=work/(label+'.bmp');evidence=work/(label+'.json')
            command=[player,'--durable-world','--content-definition',project/'opening.aibd','--asset-root',project/'assets/packs','--database',state/'w.sqlite','--project','first-boot-warm-opening','--branch','warm-beginning-opening-v1','--play-session',session,'--stop-file',state/'stop','--capture',capture,'--durable-report',evidence,'--width','1920','--height','1080']+flags
            child(label,command,timeout);value=json.loads(evidence.read_text(encoding='utf-8')) if evidence.exists() else None
            return value,capture
        for route in ('repair','bypass'):
            state=work/route;session=str(uuid.uuid4());value,capture=invoke(route+'-tour',state,session,['--durable-step','opening-tour','--opening-tour-bindings',sidecar,'--opening-tour-route',route])
            check(value['status']=='passed' and value['opening_tour_verified'] and not value['opening_tour_realtime'],'Actual seven-stop synthetic-dt tour completed: '+route)
            check(value['initial_view_applied'],'Fresh boot applied content-owned unobstructed initial view: '+route)
            check(value['saved'] and value['pending_batches']==0 and value['visible_revision']==value['durable_revision'],'All real interactions durable: '+route)
            check(not value['opening_panel_visible'] and not value['human_pacing_measured'],'Ephemeral panels closed, no human pacing claim: '+route)
            check(value['metrics']['debug_errors']==0 and value['metrics']['debug_warnings']==0 and value['metrics']['nonbackground_pixels']>10000,'Native rendering and diagnostics: '+route)
            check(bmp(capture)==(1920,1080),'Physical native capture1080p: '+route)
            reads=value['tour_reads'];check(tuple(row['role'] for row in reads)==ROLES,'All seven actual E/Continue reads in authored order: '+route)
            for read in reads:
                role=read['role'];expected=stops[bindings[role]];check(read['target_uuid']==bindings[role] and read['title']==expected['title'] and read['source']==expected['source'] and bool(read['text']),'Exact physical stop text/source/UUID: '+route+'/'+role)
                check(read['revision_before']==read['revision_after'] and read['sequence_before']==read['sequence_after'],'Reading gives no synthetic durable credit: '+route+'/'+role)
                check(all(v>0 for v in bmp(Path(read['glyph_capture']))),'Actual owned native glyph capture: '+route+'/'+role)
            progress=record(value,'firstboot.ChapterProgress');check(progress['first_route']==route and progress['shelter_secured'] and progress['pencil_visited'],'Actual earned route/shelter/Pencil progression: '+route)
            guide=value['companion'];check(guide['follow_route_verified'] and guide['follow'] and not guide['recall_required'] and guide['character_frames']>0,'Adam physically follows actual doors with animated resource: '+route)
            check(not any(event['type']=='companion.outcome' for event in value['events']),'Tour substitutes no Recall/follow-state outcome: '+route)
            reopened,_=invoke(route+'-reopen',state,session,['--durable-step','inspect']);check(durable(reopened)==durable(value),'Fresh-process restart preserves all earned history: '+route)
        if not args.skip_performance:
            state=work/'performance';state.mkdir();performance=state/'performance.json';_,capture=invoke('performance',state,str(uuid.uuid4()),['--performance-report',performance,'--performance-seconds','15','--performance-warmup','2'],50)
            m=json.loads(performance.read_text(encoding='utf-8'));check(m['status']=='measured' and not m['synthetic_chapter_ticks_used_for_fps'] and m['measured_wall_seconds']>=15,'Actual >=15second steady-clock Present measurement')
            check((m['actual_client_width'],m['actual_client_height'])==(1920,1080) and bmp(capture)==(1920,1080),'Exact physical1920x1080 measured and captured')
            check(m['frame_count']==m['actual_present_delta'] and m['frame_count']>0,'Each measured interval corresponds to actual Present')
            check(math.isclose(m['fps'],m['frame_count']/m['measured_wall_seconds'],rel_tol=1e-10),'FPS derived from actual frames/wall seconds')
            check(0<m['frame_ms']['p50']<=m['frame_ms']['p95']<=m['frame_ms']['p99'] and m['private_bytes']['maximum_sampled']>0 and m['working_set_bytes']['maximum_sampled']>0,'Real frame distributions and process memory captured')
            check(not m['recording_enabled'] and not m['engine_requested_inference'] and m['background_gpu_users']=='unknown_not_enumerated_not_isolated','Recorder/inference off; background isolation not fabricated')
            check(m['gpu_debug_errors']==0 and m['gpu_debug_warnings']==0,'Measured native run has zero GPU debug errors/warnings')
            report['performance']=m;report['performance_60fps_mean_target_met']=m['fps']>=59.0
        if args.record:
            state=work/'recording';state.mkdir();movie=state/'walkthrough.mp4';value,_=invoke('recording',state,str(uuid.uuid4()),['--record-mp4',movie,'--record-ffmpeg',args.ffmpeg.resolve(strict=True),'--record-encoder',args.encoder,'--opening-tour-bindings',sidecar,'--opening-tour-route','repair','--walkthrough-read-seconds','8'],300)
            r=value['recording'];check(value['opening_tour_realtime'] and value['opening_tour_verified'] and len(value['tour_reads'])==7,'Real-time route and all seven readable memory stops recorded')
            check(r['finished'] and not r['failed'] and r['encoder_exit_code']==0 and r['frames_written']>100 and r['owned_hud_frames']>100,'Bounded encoder completed with actual owned HUD frames')
            check(not r['desktop_capture'] and not r['audio_capture'] and not r['original_audio_autoplay'],'Video contains owned renderer/controls only, no desktop/audio')
            check(r['producer_frame_capacity_peak']<=32*1024*1024 and r['encoder_frame_capacity_peak']<=32*1024*1024 and r['encoder_frame_capacity_active']==0,'Two bounded CPU frames, encoder pixel slot released atStop')
            child('video-probe',[args.ffprobe.resolve(strict=True),'-v','error','-count_frames','-show_streams','-show_format','-of','json',movie],60)
            probe=json.loads((work/'video-probe.stdout.log').read_text(encoding='utf-8'));streams=probe['streams'];video=[s for s in streams if s['codec_type']=='video']
            check(len(video)==1 and not any(s['codec_type']=='audio' for s in streams),'Actual MP4 has one video and no audio stream')
            stream=video[0];duration=float(stream['duration']);decoded=int(stream['nb_read_frames'])
            check((stream['width'],stream['height'])==(1920,1080) and duration>30 and abs(duration-r['wall_seconds'])<2,'Encoded physical1080p duration follows actual walkthrough wall clock')
            check(decoded>100 and decoded/duration>=24,'Actual decoded video >=24fps; raw capture count is not substituted')
            child('video-pts',[args.ffprobe.resolve(strict=True),'-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',movie],60)
            pts=[float(f['best_effort_timestamp_time']) for f in json.loads((work/'video-pts.stdout.log').read_text(encoding='utf-8'))['frames']]
            check(len(pts)==decoded and all(b>a for a,b in zip(pts,pts[1:])),'Decoded presentation timestamps strictly increase')
            child('video-pixels',[args.ffmpeg.resolve(strict=True),'-v','error','-i',movie,'-vf',"select=eq(n\\,0)+eq(n\\,%d)+eq(n\\,%d),scale=160:90"%(decoded//2,decoded-1),'-fps_mode','vfr','-frames:v','3','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],60)
            pixels=(work/'video-pixels.stdout.log').read_bytes();size=160*90*3;check(len(pixels)==size*3,'Three actual video frames decoded to bounded owned pixels')
            samples=[pixels[i*size:(i+1)*size] for i in range(3)];check(all(len(set(sample))>24 and sum(v>20 for v in sample)>size//20 for sample in samples) and len(set(samples))>1,'Actual decoded video is nonblack and shows changed scene/HUD content')
            report['decoded_video']={'frames':decoded,'duration':duration,'fps':decoded/duration,'strict_pts':True,'audio_streams':0}
            report['video']={'path':str(movie),'sha256':sha(movie),'native_recording':r}
        if args.failure_encoder:
            state=work/'encoder-failure';state.mkdir();session=str(uuid.uuid4());movie=state/'failed-recording.mp4'
            value,_=invoke('encoder-failure',state,session,['--record-mp4',movie,'--record-ffmpeg',args.failure_encoder.resolve(strict=True),'--record-encoder','software','--opening-tour-bindings',sidecar,'--opening-tour-route','repair','--walkthrough-read-seconds','2'],180)
            recording=value['recording'];check(recording['failed'] and bool(recording['error']),'Actual stalled/failed encoder is reported honestly')
            check(value['opening_tour_verified'] and value['opening_tour_realtime'] and value['saved'] and value['pending_batches']==0 and value['visible_revision']==value['durable_revision'],'Recorder failure leaves actual route and save processing alive')
            progress=record(value,'firstboot.ChapterProgress');check(progress['first_route']=='repair' and progress['shelter_secured'] and progress['pencil_visited'],'Actual repair/Pencil progression survives failed encoder')
            reopened,_=invoke('encoder-failure-reopen',state,session,['--durable-step','inspect']);check(durable(reopened)==durable(value),'Fresh process retains exact durable outcomes after actual encoder failure')
        check(source_files=={str(path.relative_to(project)):sha(path) for path in project.rglob('*') if path.is_file()},'All diagnostics leave immutable project/pack bytes unchanged')
        check(all(item['joined'] for item in report['processes']),'All child processes joined')
        report['status']='passed'
    finally:
        report['completed_at']=datetime.now(timezone.utc).isoformat();(work/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(work/'verification.json')
    print(len(report['checks']),'presentation acceptance checks passed; human pacing unmeasured')
if __name__=='__main__':main()
