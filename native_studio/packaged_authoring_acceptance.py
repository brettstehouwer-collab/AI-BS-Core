"""Two-phase frozen default-bundle authoring and hidden viewport acceptance.

Author and reopen run in separate frozen processes. Existing source/project
bytes are read-only; all changes belong to a newly owned fixture. AI is disabled.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import os
import socket
import struct
import sys
import time
import traceback
import uuid
from unittest.mock import patch

from .packaged_chapter_acceptance import (VARIANTS, SOURCE, MANIFEST_SHA, PLAYER_SHA,
    need, io, plain, read, pin, write, receipt, tree, OwnedHandle)

HERO='cd8c08f8-c811-422b-893d-7c2ba34438b9'
PROXIES=('28ce164a-f967-46ad-b364-948bb7596a3e','83253340-2075-4f6a-9d4e-50a33803b19c',
         '40f14b51-52de-4111-8d8e-793823a7468e','16995d12-e5bb-4b28-b666-06252a0d9add')


def bundled_runtime(manifest):
    need(getattr(sys,'frozen',False) and getattr(sys,'_MEIPASS',None),'Frozen bundle required')
    bundle=plain(Path(sys._MEIPASS));binary=bundle/'game_assets/player'
    need(pin(manifest)['sha256']==MANIFEST_SHA,'Reviewed runtime manifest changed')
    rows=json.loads(read(manifest));need(len(rows)==18,'Complete reviewed runtime required')
    for relative,expected in rows.items():
        path=Path(relative)
        target=binary/Path(*path.parts[1:]) if path.parts[0]=='bin' else binary/(
            'cgltf-LICENSE.txt' if 'cgltf' in path.parts else path.name)
        need(pin(target)=={key:expected[key] for key in ('bytes','sha256')},'Bundled runtime differs: '+relative)
    need(pin(binary/'aibs_motherboard.exe')['sha256']==PLAYER_SHA,'Current bundled player required')
    return bundle,binary,rows


def run(report,work,manifest,phase):
    report,work,manifest=plain(report),plain(work),plain(manifest)
    need(work.parent==VARIANTS and report.parent==VARIANTS and report!=work and not io(report).exists(),
         'New report and direct reviewed D: fixture required')
    bundle,binary,runtime=bundled_runtime(manifest)
    source_before=tree(SOURCE)
    need(pin(SOURCE/'opening.aibd')['sha256']=='03d41a2bc1e400d9bf507613b11398c95ee7c84246deef2a2ee967188c2baf20','Wrong qualified source')
    application=pin(Path(sys.executable))
    if phase=='author':
        need(not io(work).exists(),'Preserve prior fixture; author output must be new')
        io(work).mkdir();io(work/'project').mkdir()
        for relative,expected in source_before.items():
            target=work/'project'/relative;io(target.parent).mkdir(parents=True,exist_ok=True)
            write(target,read(SOURCE/relative));need(pin(target)==expected,'Create-only source copy differs')
        fixture={'nonce':uuid.uuid4().hex,'source':str(SOURCE),'source_tree':source_before,
                 'application':application,'runtime_manifest':pin(manifest)}
        receipt(work/'fixture.json',fixture)
    else:
        need(io(work/'author.json').is_file(),'Successful retained author phase required')
        fixture=json.loads(read(work/'fixture.json'))
        need(fixture['source']==str(SOURCE) and fixture['source_tree']==source_before and
             fixture['application']==application and fixture['runtime_manifest']==pin(manifest),
             'Reopen fixture/source/package differs')
        previous=json.loads(read(work/'author.json'))
        need(previous['status']=='PASS_FROZEN_AUTHORING_AUTHOR','Author phase did not pass')
    # Windowed PyInstaller has no stderr by default. A Qt callback exception
    # must become durable evidence before PyQt's default abort path can hide it.
    callback_errors=[]
    acknowledged_callback_errors=0
    prior_hook=sys.excepthook
    diagnostic_stream=io(work/(phase+'-python-stderr.log')).open('x',encoding='utf8',buffering=1)
    prior_stderr=sys.stderr
    if sys.stderr is None:sys.stderr=diagnostic_stream

    def callback_exception(kind,value,tb):
        item={'kind':'unhandled-qt-or-python-callback','type':kind.__name__,
              'error':str(value),'traceback':''.join(traceback.format_exception(kind,value,tb))[-32768:]}
        callback_errors.append(item)
        receipt(work/(phase+'-callback-error-'+str(len(callback_errors))+'.json'),item)
        # Do not call the default windowed hook or rethrow across a Qt callback.
        # The outer event loop observes this failure and retains owned resources.

    sys.excepthook=callback_exception
    from PyQt6.QtCore import QObject,pyqtSignal,QCoreApplication,QEvent,QTimer,QPoint
    from PyQt6.QtWidgets import QApplication,QPushButton
    from PyQt6.QtGui import QFontDatabase,QFontInfo
    from PyQt6 import sip
    from native_studio.engine import EngineBus
    from native_studio.game_build_view import GameBuildNativeView
    from native_studio.game_engine import content_view
    app=QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        for name in ('segoeui.ttf','seguisb.ttf'):
            need(QFontDatabase.addApplicationFont(str(Path(os.environ['SystemRoot'])/'Fonts'/name))>=0,
                 'Actual system fonts required for frozen layout qualification')
    from native_studio.theme import STYLESHEET
    app.setStyleSheet(STYLESHEET)
    bus=EngineBus(max_threads=1)
    calls={'network':0,'provider':0};hub=view=owner=None
    record={'status':'INCOMPLETE','phase':phase,'python_pid':os.getpid(),'nonce':fixture['nonce'],
        'scope':'Frozen default-bundle authoring; explicit AI-disabled adapter; native hidden internal selection proof',
        'runtime':runtime,'application':application,'calls':calls,'ordinary_input_verified':False,
        'normal_mainwindow_qualified':False,'performance_measured':False,'hosted_or_installed_qualified':False}

    class DenyAI(QObject):
        inventory_ready=pyqtSignal(object,object);proposal_ready=pyqtSignal(str,str)
        failed=pyqtSignal(str,str);state_changed=pyqtSignal(str);busy=False
        def refresh_models(self):
            calls['provider']+=1;raise RuntimeError('AI inventory disabled')
        def generate(self,*args,**kwargs):
            calls['provider']+=1;raise RuntimeError('Model generation disabled')
        def cancel(self):return None

    def deny_network(*args,**kwargs):
        calls['network']+=1;raise RuntimeError('Network disabled')

    def spin(predicate,label,seconds=45):
        deadline=time.monotonic()+seconds
        while True:
            if len(callback_errors)>acknowledged_callback_errors:
                raise RuntimeError('Qt callback failed; inspect durable callback-error receipt')
            if predicate():return
            if time.monotonic()>deadline:raise TimeoutError(label+'; retain fixture, no kill/restart')
            if view:
                now=time.monotonic()
                owner_deadlines=[pending.deadline for pending in view.client._pending.values()]
                if view.client.state=='starting':owner_deadlines.append(view.client._launch_deadline)
                if view.client._closing:owner_deadlines.append(view.client._stop_deadline)
                render_deadline=getattr(view.viewport,'_deadline',None)
                if any(value and value-now<1 for value in (*owner_deadlines,render_deadline)):
                    for timer in view.findChildren(QTimer):timer.stop()
                    raise TimeoutError('Native watchdog deadline approached; retain owners without force termination')
                for client in (view.asset_client,view.viewport._stager):
                    timer=client._timer
                    if timer.isActive() and timer.isSingleShot() and 0<=timer.remainingTime()<1000:
                        timer.stop();raise TimeoutError('Asset watchdog deadline approached; retain child')
            app.processEvents();time.sleep(.005)

    def idle():
        spin(lambda:view.loaded and view.client.state=='ready' and not view.busy and
             not view.client.pending_count and not view.asset_client.busy,'Coherent idle authoring owner')

    def rows():
        return {row.uuid:{'type':row.type_id,'name':row.name,'fields':dict(row.fields)} for row in view.rows}

    def origins():
        result={}
        for name,module in tuple(sys.modules.items()):
            if (name=='native_studio' or name.startswith('native_studio.') or name.startswith('PyQt6.')) and getattr(module,'__file__',None):
                path=Path(module.__file__).resolve();need(path.is_relative_to(bundle.resolve()),'Module escaped bundle: '+name)
                result[name]=str(path)
        return result

    def viewport(label):
        directory=work/label;need(not io(directory).exists(),'Viewport evidence must be new');io(directory).mkdir()
        need(view.select_entity(HERO),'Hero UUID missing from actual selection')
        view.open_viewport(probe_directory=directory)
        paths=set();handles={}
        def completed():
            executable=getattr(view.viewport,'_content_executable',None)
            if executable is not None:paths.add(str(Path(executable).resolve()))
            pid=view.viewport.process_id
            if pid and pid not in handles:
                handle=OwnedHandle(pid,binary/'aibs_creator_viewport.exe');handles[pid]=handle
                receipt(directory/('process-'+str(pid)+'.started.json'),handle.info)
            return (not view.busy and view.viewport.state=='closed' and not view.client.pending_count and
                    not view.asset_client.busy and view.viewport.dependency_process_id==0 and io(directory/'viewport.json').is_file())
        spin(completed,label+' native viewport/asset worker join')
        need(paths=={str((binary/'aibs_creator_viewport.exe').resolve())},'Wrong or unobserved bundled viewport')
        need(len(handles)==1,'Exactly one owned viewport must be observed')
        terminal=[handle.finish() for handle in handles.values()]
        value=json.loads(read(directory/'viewport.json'))
        need(value.get('debug_layer') is True and value.get('debug_errors')==value.get('debug_warnings')==0
             and value.get('nonbackground_pixels',0)>100 and value.get('selected_uuid')==HERO,
             'Actual viewport GPU/debug/selected UUID proof failed')
        need(value.get('world_id')==view.client.head.scope.world_id,'Viewport world identity differs')
        bitmap=read(directory/'viewport.bmp');need(len(bitmap)>=54 and bitmap[:2]==b'BM','Actual viewport BMP missing')
        width,height=struct.unpack_from('<ii',bitmap,18);bits=struct.unpack_from('<H',bitmap,28)[0]
        offset=struct.unpack_from('<I',bitmap,10)[0]
        need(width>0 and abs(height)>0 and bits in (24,32) and offset>=54 and
             offset+((width*bits+31)//32)*4*abs(height)==len(bitmap),'Viewport capture payload invalid')
        snapshot=view._content_snapshot
        need(snapshot and snapshot.payload and snapshot.fingerprint==hashlib.sha256(snapshot.payload).hexdigest(),
             'Actual native export snapshot missing or corrupt')
        record[label]={'report':value,'executable':str(binary/'aibs_creator_viewport.exe'),
            'pin':pin(binary/'aibs_creator_viewport.exe'),'processes':terminal,'capture':pin(directory/'viewport.bmp'),
            'selection_scope':'Owned native hidden-window internal fixture, not a user click'}
        return snapshot

    def close_clean():
        idle();need(not view.client.dirty and not view.client.uncertain_operations,'Dirty/uncertain owner retained')
        view.close_project(discard=False)
        spin(lambda:view.client.state=='closed' and view._children_closed(),'Normal owner close')
        need(not getattr(view.client,'_killed',False),'Forced owner cleanup rejected')
        record['host']=owner.finish();hub.timer.stop();need(bus.shutdown(3000),'EngineBus not joined')
        hub.close();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);sip.delete(hub);app.processEvents()

    def layout_checks():
        """Measure the real loaded creator and scroll reachability, not a mock."""
        need(view.select_entity(HERO),'Select actual hero for populated inspector layout')
        results=[]
        def settle():
            for _ in range(12):app.processEvents()
        for width in (1150,1280,1620):
            for height in (500,650):
                hub.resize(width,height);hub.show();settle()
                scroll=hub.content_scroll
                need((hub.width(),hub.height())==(width,height),'Loaded workspace minimum exceeds requested size')
                need(view.width()<=scroll.viewport().width() and view.outliner.height()>=180,
                     'Loaded outliner/workspace was squeezed or overflowed')
                buttons=[button for button in view.findChildren(QPushButton) if button.isVisibleTo(view)]
                for button in buttons:
                    need(button.width()>=button.sizeHint().width(),'Clipped loaded command: '+button.text())
                    scroll.ensureWidgetVisible(button,8,8);settle()
                    top=button.mapTo(scroll.viewport(),QPoint(0,0))
                    need(top.x()>=0 and top.y()>=0 and top.x()+button.width()<=scroll.viewport().width()
                         and top.y()+button.height()<=scroll.viewport().height(),'Unreachable loaded command: '+button.text())
                results.append({'width':width,'height':height,'outliner_height':view.outliner.height(),
                    'readable_reachable_buttons':len(buttons),'font_family':QFontInfo(view.saved_play_button.font()).family(),
                    'font_points':QFontInfo(view.saved_play_button.font()).pointSizeF()})
                if width==1150 and height==500:
                    scroll.verticalScrollBar().setValue(0);settle()
                    need(hub.grab().save(str(io(work/(phase+'-loaded-top.png')))),'Loaded layout capture failed')
                    scroll.ensureWidgetVisible(view.stop_saved_play_button,8,8);settle()
                    need(hub.grab().save(str(io(work/(phase+'-loaded-actions.png')))),'Loaded actions capture failed')
        record['layout_checks']=results

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket,'connect',deny_network))
        stack.enter_context(patch.object(socket,'create_connection',deny_network))
        stack.enter_context(patch.object(content_view,'ContentAIClient',DenyAI))
        try:
            hub=GameBuildNativeView(bus);hub.workspace_tabs.setCurrentIndex(2);view=hub.content_view
            need(type(view) is content_view.ContentView and view.executable==binary/'aibs_content_host.exe'
                 and view.asset_client.cooker==binary/'aibs_assetc.exe','Actual default bundled creator tools required')
            view.open_project(work/'project');idle();owner=OwnedHandle(view.client.process_id,binary/'aibs_content_host.exe')
            record['host_opened']=owner.info;record['host_epoch']=view.client.head.scope.host_epoch
            record['module_origins_before']=origins()
            initial=rows();need(HERO in initial and set(PROXIES)<=set(initial),'Intended hero/proxy UUIDs absent')
            layout_checks()
            if phase=='author':
                receipt(work/'baseline-rows.json',initial)
                viewport('viewport_initial')
                need(view.select_entity(HERO),'Hero selection unavailable')
                original_x=initial[HERO]['fields']['x'];moved_x=original_x+1.5
                view.field_editors['x'].setText(str(moved_x))
                head=view.client.head.head_revision;journal_before=pin(work/'project/chapter.aiba')
                view.preview_button.click();spin(lambda:view.apply_button.isEnabled(),'Actual Preview')
                need(rows()==initial and view.client.head.head_revision==head and
                     pin(work/'project/chapter.aiba')==journal_before,'Preview mutated authoritative/save state')
                view.apply_preview();idle();moved=rows()
                expected=json.loads(json.dumps(initial));expected[HERO]['fields']['x']=moved_x
                need(moved==expected,'Apply changed unexpected UUIDs/types/fields')
                viewport('viewport_moved')
                view.undo_button.click();idle();need(rows()==initial,'Undo did not restore exact baseline')
                view.redo_button.click();idle();need(rows()==moved,'Redo did not restore exact moved fields')
                view.undo_button.click();idle();need(rows()==initial,'Final restoration differs')
                view.save_button.click();idle();need(not view.client.dirty,'Save did not acknowledge clean state')
                snapshot=viewport('viewport_saved')
                write(work/'current-opening.aibd',snapshot.payload)
                record.update(baseline_count=len(initial),journal=pin(work/'project/chapter.aiba'),
                    export=pin(work/'current-opening.aibd'),saved_fingerprint=snapshot.fingerprint,
                    definition_id=snapshot.definition_id,content_revision=snapshot.content_revision)
            else:
                need(os.getpid()!=previous['python_pid'] and owner.info['birth_filetime']!=previous['host_opened']['birth_filetime']
                     and record['host_epoch']!=previous['host_epoch'],'Fresh frozen/native owner identity required')
                need(initial==json.loads(read(work/'baseline-rows.json')),'Fresh owner lost complete typed baseline')
                need(pin(work/'project/chapter.aiba')==previous['journal'] and pin(work/'current-opening.aibd')==previous['export'],
                     'Saved journal/export changed before reopen')
                snapshot=viewport('viewport_reopened')
                need(snapshot.fingerprint==previous['saved_fingerprint'] and snapshot.definition_id==previous['definition_id']
                     and snapshot.content_revision==previous['content_revision'],'Fresh native export identity differs')
                need(pin(work/'project/chapter.aiba')==previous['journal'],'Reopen modified journal bytes')
            need(pin(work/'project/opening.aibd')==source_before['opening.aibd'],'Original copied static export overwritten')
            record['module_origins_after']=origins();close_clean()
            need(calls=={'network':0,'provider':0},'Unexpected provider/network attempt')
            record['status']='PASS_FROZEN_AUTHORING_'+phase.upper()
        except BaseException as error:
            # Preserve the primary exception before any Qt-object inspection,
            # process adoption or cleanup can itself fail and mask the cause.
            receipt(work/(phase+'-primary-error.json'),{'error_type':type(error).__name__,
                'error':str(error),'traceback':traceback.format_exc(limit=20)[-32768:],
                'callback_errors':callback_errors})
            record.update(status='FAILED',error_type=type(error).__name__,error=str(error))
            try:
                if view:
                    if owner is None and view.client.process_id:owner=OwnedHandle(view.client.process_id,binary/'aibs_content_host.exe')
                    record['failure_state']={'host':view.client.process_id,'viewport':view.viewport.process_id,
                        'dependency':view.viewport.dependency_process_id,'dirty':view.client.dirty,'pending':view.client.pending_count,
                        'busy':view.busy,'owner_state':view.client.state,'status':view.status.text(),'rows':rows()}
                    # Preserve uncertain owners instead of allowing QProcess's
                    # destruction or watchdogs to force-kill this fixture.
                    for timer in view.findChildren(QTimer):timer.stop()
            except BaseException as secondary:
                record['secondary_error']={'type':type(secondary).__name__,'error':str(secondary),
                                           'traceback':traceback.format_exc(limit=10)[-16384:]}
                receipt(work/(phase+'-secondary-error.json'),record['secondary_error'])
                # Resource state is uncertain. Keep the process/hook alive for
                # inspection; never let a diagnostic exception destroy owners.
                receipt(work/(phase+'-retained-uncertain.json'),{'worker_pid':os.getpid(),
                    'nonce':fixture['nonce'],'scope':'Primary and secondary failure preserved; no cleanup attempted'})
                while True:
                    app.processEvents();time.sleep(.1)
            receipt(work/(phase+'-failure.json'),record)
            if view and (view.client.process_id or not view._children_closed()):
                receipt(work/(phase+'-retained.json'),{'worker_pid':os.getpid(),'nonce':fixture['nonce'],
                    'instruction':'Create '+phase+'-close-retained.json with matching worker_pid/nonce; clean idle owners close normally. Dirty/uncertain fixtures remain retained.'})
                control=work/(phase+'-close-retained.json')
                while True:
                    app.processEvents()
                    if io(control).is_file():
                        request=json.loads(read(control))
                        if request.get('worker_pid')==os.getpid() and request.get('nonce')==fixture['nonce']:
                            if (view.loaded and view.client.state=='ready' and not view.busy and not view.client.pending_count
                                    and not view.client.dirty and not view.client.uncertain_operations and view._children_closed()):
                                acknowledged_callback_errors=len(callback_errors)
                                receipt(work/(phase+'-normal-close-request.json'),{'worker_pid':os.getpid(),
                                    'nonce':fixture['nonce'],'preserved_callback_errors':acknowledged_callback_errors})
                                close_clean();break
                    time.sleep(.05)
        finally:
            record['original_source_unchanged']=tree(SOURCE)==source_before
            if not record['original_source_unchanged']:record['status']='FAILED_SOURCE_PRESERVATION'
            receipt(work/(phase+'.json'),record);receipt(report,record)
    sys.excepthook=prior_hook
    sys.stderr=prior_stderr
    diagnostic_stream.close()
    return 0 if record['status']=='PASS_FROZEN_AUTHORING_'+phase.upper() else 2


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packaged-authoring-acceptance',required=True,type=Path,metavar='NEW_REPORT')
    parser.add_argument('--packaged-authoring-work',required=True,type=Path)
    parser.add_argument('--packaged-runtime-manifest',required=True,type=Path)
    parser.add_argument('--packaged-authoring-phase',choices=('author','reopen'),required=True)
    args=parser.parse_args(argv)
    return run(args.packaged_authoring_acceptance,args.packaged_authoring_work,args.packaged_runtime_manifest,args.packaged_authoring_phase)
