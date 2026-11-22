"""Actual curated-opening Qt/native factory/Host proof, without a renderer."""
import argparse,datetime,hashlib,json,os,shutil,sys,time
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView,ChapterProjectDefinition
from native_studio.game_engine.content_commands import SetField
from native_studio.game_engine.opening_assets import read_opening_assets
from native_studio.game_engine.workshop_fields import workshop_bindings_from_rows

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(root):return {p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)}for p in sorted(root.rglob('*'))if p.is_file()}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sdk',type=Path,required=True)
    parser.add_argument('--resources',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();sdk=args.sdk.resolve(strict=True);resources=args.resources.resolve(strict=True);work=args.output.absolute()
    if work.exists():raise RuntimeError('Preserve previous proof attempts; choose a fresh output')
    work.resolve().relative_to(Path('D:/AI-BS-Game-Resources').resolve());work.mkdir(parents=True)
    temp=work/'Temp';temp.mkdir();os.environ.update(TEMP=str(temp),TMP=str(temp));__import__('tempfile').tempdir=str(temp)
    bundle=read_opening_assets(resources,verify_pack_contents=True);source_before=inventory(resources);sdk_before=inventory(sdk)
    (work/'resources-before.json').write_text(json.dumps(source_before,indent=2)+'\n');(work/'sdk-before.json').write_text(json.dumps(sdk_before,indent=2)+'\n')
    app=QApplication.instance()or QApplication([]);app.setQuitOnLastWindowClosed(False)
    view=ContentView(sdk/'bin/aibs_content_host.exe',asset_cooker=sdk/'bin/aibs_assetc.exe',
        opening_factory=sdk/'bin/aibs_warm_opening_project.exe',opening_assets_root=resources)
    job=view.opening_client;messages=[];errors=[];results=[];trace=[];checks=[];owners=[]
    job.failed.connect(errors.append);job.completed.connect(results.append);job.message.connect(messages.append)
    original_launch=job._launch;original_finished=job._finished
    def launch(executable,arguments,mode):
        trace.append({'sequence':len(trace)+1,'executable':str(executable),'args':arguments,'mode':mode})
        original_launch(executable,arguments,mode)
    def finished(process,generation,code,status):
        if process is job._process:
            job._drain(process,False);job._drain(process,True);name=str(len(trace)).zfill(2)+'-'+str(job._mode)
            (work/(name+'.stdout.log')).write_bytes(bytes(job._out));(work/(name+'.stderr.log')).write_bytes(bytes(job._err))
            trace[-1].update(exit_code=code,generation=generation)
        original_finished(process,generation,code,status)
    job._launch=launch;job._finished=finished
    def check(value,label):
        checks.append({'check':label,'passed':bool(value)})
        if not value:raise RuntimeError(label)
    def spin(predicate,label,seconds=60):
        deadline=time.monotonic()+seconds
        while not predicate()and time.monotonic()<deadline:app.processEvents();time.sleep(.002)
        check(predicate(),label+'; '+view.status.text())
    def idle():spin(lambda:view.loaded and not view.busy and view.client.pending_count==0,'native owner idle')
    status='failed';error=None;observations={}
    try:
        with patch.object(view.viewport,'start_content',side_effect=RuntimeError('Viewport prohibited'))as viewport,patch.object(view.play,'start',side_effect=RuntimeError('Player prohibited'))as player:
            check(not job.availability_error,'installed015 tools and curated resources are available')
            output=work/'FirstBootOpening';view.create_first_boot_opening(output)
            check(job.busy,'creation starts asynchronously with a live owned job')
            try:view.create_first_boot_opening(work/'ConcurrentOpening')
            except ValueError:check(True,'busy creation refuses a second output without superseding work')
            else:raise RuntimeError('Busy opening job was replaced')
            spin(lambda:bool(errors)or(view.loaded and not view.busy and not job.busy and view.client.pending_count==0),'actual factory publication auto-opens the native chapter')
            check(not errors,'native adoption/inspection/factory completed without errors')
            check(len(results)==1 and results[0].directory==output,'one successful publication has the requested new directory')
            check([row['mode']for row in trace]==['adopt','inspect']*6+['factory'],'six immutable packs were asynchronously adopted and typed-inspected before factory creation')
            check(all('--audio-pack'not in row['args']for row in trace),'creation never supplies original audio')
            check(job.process_id==0 and not list(work.glob('.aibs-opening-*')),'all factory/asset children joined and owned scratch copies were removed')
            check(ChapterProjectDefinition.load(output).opening_workshop,'new chapter has typed-v3 Workshop metadata')
            factory_report=json.loads((output/'opening-manifest.json').read_text())
            actual={tuple(row[key]for key in('asset_id','asset_sha256','pack_sha256'))for row in factory_report['dependencies']}
            check(actual=={asset.reference for asset in bundle.roles},'native atomic output contains the exact curated dependency closure')
            check(factory_report['recording_bound']is False and factory_report['family_source_files_copied']is False,'no original recording or family source files are copied')
            binding=workshop_bindings_from_rows(view.rows,'warm-beginning');check(len(binding)==5,'native owner exposes five current Workshop bindings')
            check(not any(row.type_id=='authoring.MemoryBinding'for row in view.rows),'no original-memory audio station is silently added')
            owners.append({'pid':view.client.process_id,'generation':view.client.generation,'epoch':view.client.epoch.hex()})
            initial=view.description.fingerprint
            packet=view._encode_edits((SetField(binding[0],'emission',.035),),'Curated Creator native Preview proof')
            view._submit_packet(packet,apply_after_preview=False)
            spin(lambda:not view.busy and view.client.pending_count==0,'actual native authoring Preview completed')
            check(bool(view._token)and view.description.fingerprint==initial,'Preview is private and does not publish edits')
            view.apply_preview();idle();edited=view.description.fingerprint
            check(edited!=initial,'Apply publishes the authored fixture change')
            try:view.create_first_boot_opening(work/'MustNotDiscardUnsavedChapter')
            except ValueError:check(view.client.dirty and view.description.fingerprint==edited,'unsaved chapter edits are preserved when opening creation is refused')
            else:raise RuntimeError('Unsaved chapter was discarded')
            view.save_world();idle();saved=digest(output/'chapter.aiba')
            try:view.create_first_boot_opening(work/'MustNotReplaceOpenProject')
            except ValueError:check(True,'an open chapter is never discarded to create another opening')
            else:raise RuntimeError('Open chapter was replaced')
            check(not(work/'MustNotReplaceOpenProject').exists(),'protected new target was not created')
            view.close_project();spin(lambda:view.client.state=='closed','first native authoring owner joined')
            view.open_project(output);idle();owners.append({'pid':view.client.process_id,'generation':view.client.generation,'epoch':view.client.epoch.hex()})
            check(view.description.fingerprint==edited and workshop_bindings_from_rows(view.rows,'warm-beginning')==binding,'fresh native owner restores saved edits and all Workshop bindings')
            check(digest(output/'chapter.aiba')==saved,'read-only reopen preserves exact saved journal bytes')
            view.close_project();spin(lambda:view.client.state=='closed','second native authoring owner joined')
            before_existing=inventory(output);trace_count=len(trace)
            try:view.create_first_boot_opening(output)
            except ValueError:check(True,'existing output is refused before any subprocess starts')
            else:raise RuntimeError('Existing output was admitted')
            check(len(trace)==trace_count and inventory(output)==before_existing,'existing project files remain byte-identical')
            bad=work/'BadCurator';shutil.copytree(resources,bad)
            data=json.loads((bad/'opening-assets.json').read_text());data['roles']['capacitor']['pack_sha256']='0'*64
            (bad/'opening-assets.json').write_text(json.dumps(data))
            job.assets_root=bad;failure_count=len(errors);failed_output=work/'WrongReferenceOpening'
            view.create_first_boot_opening(failed_output)
            spin(lambda:not job.busy and len(errors)>failure_count,'actual native immutable-reference mismatch returned')
            check(not failed_output.exists()and view.definition is None,'bad curated reference fails before factory publication or project opening')
            check(job.process_id==0 and not list(work.glob('.aibs-opening-*')),'failed native verification joins its child and clears only owned scratch data')
            job.assets_root=resources;cancelled_output=work/'CancelledOpening';callbacks=[]
            view.create_first_boot_opening(cancelled_output)
            check(not view.prepare_close(lambda:callbacks.append('joined')),'closing waits for asynchronous cancellation')
            spin(lambda:not job.busy and bool(callbacks),'close cancellation joins before its deferred callback')
            check(job.process_id==0 and not cancelled_output.exists()and view.definition is None,'closing does not publish or auto-open cancelled work')
            viewport.assert_not_called();player.assert_not_called()
            observations={'project':str(output),'initial_fingerprint':initial,'saved_and_reopened_fingerprint':edited,'binding':binding,
                'manifest_sha256':bundle.manifest_sha256,'curated_bytes':bundle.total_bytes,'owners':owners,'recording_bound':False}
            status='passed_actual_curated_opening_creator_factory_host'
    except Exception as exc:error=str(exc)
    finally:
        job.stop();deadline=time.monotonic()+15
        while job.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.002)
        if view.client.state!='closed':
            view.client.stop();deadline=time.monotonic()+15
            while view.client.state!='closed'and time.monotonic()<deadline:app.processEvents();time.sleep(.002)
        terminal=job.process_id==0 and view.client.process_id==0
        if not terminal:status='failed_child_not_joined';error='A native child did not join'
        source_after=inventory(resources);sdk_after=inventory(sdk)
        if source_before!=source_after or sdk_before!=sdk_after:status='failed_readonly_input_changed';error='Curated input or installed SDK changed'
        (work/'resources-after.json').write_text(json.dumps(source_after,indent=2)+'\n');(work/'sdk-after.json').write_text(json.dumps(sdk_after,indent=2)+'\n')
        (work/'child-commands.json').write_text(json.dumps(trace,indent=2)+'\n');(work/'messages.json').write_text(json.dumps(messages,indent=2)+'\n')
        receipt={'status':status,'error':error,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'goal_complete':False,
            'checks':checks,'checks_passed':sum(row['passed']for row in checks),'observations':observations,'errors_including_expected_negative_cases':errors,
            'curated_source_before_after_identical':source_before==source_after,'installed_SDK_before_after_identical':sdk_before==sdk_after,
            'installed_SDK_files':len(sdk_before),'all_children_terminal':terminal,'native_child_commands':trace,
            'GPU_Player_Viewport_visible_window_audio_inference_or_network_used':False,'QApplication_mode':'offscreen; widget never shown'}
        (work/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
        view.definition=None;view.busy=False;view.close();view.deleteLater();app.processEvents()
        print(json.dumps({'status':status,'error':error,'checks':receipt['checks_passed'],'receipt':str(work/'verification.json'),'sha256':digest(work/'verification.json')}))
    return 0 if status=='passed_actual_curated_opening_creator_factory_host'else 1

if __name__=='__main__':raise SystemExit(main())
