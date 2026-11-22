"""Opt-in frozen chapter acceptance through actual bundled default selection.

Bypasses MainWindow and disables AI explicitly. No ordinary-input, installed
release, provider-startup, action-durability or performance claim follows.
"""
import argparse
from contextlib import ExitStack
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
import uuid
from unittest.mock import patch

VARIANTS = Path('D:/AI-BS-Game-Resources/RTX_Variants_20261111')
SOURCE = VARIANTS/'Creator_LH_20261111_v05/project'
MANIFEST_SHA = '37db74d74c97399e5884e497b4a49a9909bd44e80d18908c1055c5fbbded4091'
PLAYER_SHA = '4324fca383f876db588997f6353cde2915a5613f8e31c3fe3571f95a807c55ce'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def io(path):
    value = os.path.abspath(path)
    return Path(value if value.startswith('\\\\?\\') else '\\\\?\\'+value)


def plain(path):
    p = Path(os.path.abspath(path))
    need('..' not in Path(path).parts, 'No ancestor traversal')
    for item in (p, *p.parents):
        try:
            stat = io(item).lstat()
        except FileNotFoundError:
            continue
        need(not stat.st_file_attributes & 0x400, 'No redirected fixture paths')
    return p


def read(path, limit=64*1024*1024):
    plain(path)
    with io(path).open('rb') as stream:
        raw = stream.read(limit+1)
    need(len(raw) <= limit, 'Bounded fixture file read')
    return raw


def pin(path):
    raw = read(path)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    plain(path)
    with io(path).open('xb') as stream:
        stream.write(value);stream.flush();os.fsync(stream.fileno())


def receipt(path, value):
    write(path, (json.dumps(value, indent=2, allow_nan=False)+'\n').encode('utf8'))


def tree(root):
    rows, total = {}, 0
    plain(root)
    for here, directories, files in os.walk(io(root), followlinks=False):
        for name in directories:
            plain(Path(here)/name)
        for name in files:
            path = Path(here)/name
            info = pin(path);total += info['bytes']
            need(len(rows) < 2048 and total <= 512*1024*1024, 'Bounded fixture tree')
            rows[path.relative_to(io(root)).as_posix()] = info
    return rows


class OwnedHandle:
    def __init__(self, pid, expected):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        k.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype = wintypes.HANDLE
        k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        k.GetProcessTimes.argtypes = [wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE,wintypes.DWORD]
        k.GetExitCodeProcess.argtypes = [wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = k.OpenProcess(0x100000|0x1000,False,pid)
        need(self.handle, 'Cannot retain exact child handle')
        text = ctypes.create_unicode_buffer(32768);length = wintypes.DWORD(len(text))
        need(k.QueryFullProcessImageNameW(self.handle,0,text,ctypes.byref(length)), 'Cannot identify owned child')
        need(Path(text.value).resolve() == expected.resolve(), 'Owned executable differs from bundle')
        times = [wintypes.FILETIME() for _ in range(4)]
        need(k.GetProcessTimes(self.handle,*(ctypes.byref(item) for item in times)), 'Cannot identify child birth')
        self.info = {'pid':pid, 'executable':str(expected), 'birth_filetime':
            (times[0].dwHighDateTime<<32)|times[0].dwLowDateTime,'exact_handle_retained':True}

    def finish(self):
        need(self.kernel.WaitForSingleObject(self.handle,0)==0,'Owned child still live')
        code = wintypes.DWORD()
        need(self.kernel.GetExitCodeProcess(self.handle,ctypes.byref(code)) and code.value==0,'Owned child did not exit0')
        self.kernel.CloseHandle(self.handle)
        return {**self.info,'terminal':True,'exit_code':code.value}


def run(report, work, manifest, allow_window):
    need(allow_window, 'Explicit owned native-window allowance required')
    need(getattr(sys,'frozen',False) and getattr(sys,'_MEIPASS',None), 'Frozen bundle required; no source fallback')
    bundle = plain(Path(sys._MEIPASS))
    report, work = plain(report), plain(work)
    need(work.parent==VARIANTS and report.parent==VARIANTS and report!=work and
         not io(work).exists() and not io(report).exists(), 'New separate reviewed D: work/report paths required')
    manifest = plain(manifest)
    need(pin(manifest)['sha256']==MANIFEST_SHA, 'Reviewed runtime manifest changed')
    expected = json.loads(read(manifest))
    need(len(expected)==18,'Expected reviewed complete runtime18file closure')
    binary = bundle/'game_assets/player'
    mapped = {}
    for relative, item in expected.items():
        path = Path(relative)
        target = binary/Path(*path.parts[1:]) if path.parts[0]=='bin' else binary/(
            'cgltf-LICENSE.txt' if 'cgltf' in path.parts else path.name)
        need(pin(target)=={key:item[key] for key in ('bytes','sha256')}, 'Bundled runtime differs: '+relative)
        mapped[relative] = {'path':str(target), **pin(target)}
    need(pin(binary/'aibs_motherboard.exe')['sha256']==PLAYER_SHA,'Wrong bundled current player')
    before = tree(SOURCE)
    need(pin(SOURCE/'opening.aibd')['sha256']=='03d41a2bc1e400d9bf507613b11398c95ee7c84246deef2a2ee967188c2baf20', 'Wrong qualified LH source')
    io(work).mkdir();io(work/'project').mkdir()
    for relative, info in before.items():
        target = work/'project'/relative
        io(target.parent).mkdir(parents=True,exist_ok=True)
        write(target, read(SOURCE/relative));need(pin(target)==info,'Create-only copy differs')
    from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication, QEvent
    from PyQt6.QtWidgets import QApplication
    from PyQt6 import sip
    from native_studio import engine, game_build_view
    from native_studio.game_engine import content_view, saved_play, saved_play_storage, saved_chapter_export
    app = QApplication.instance() or QApplication([])
    bus = engine.EngineBus(max_threads=1)
    calls = {'network':0,'provider':0}
    record = {'status':'INCOMPLETE','scope':'Controlled frozen GameBuildNativeView chapter tab; AI explicitly disabled',
        'python_pid':os.getpid(),'nonce':uuid.uuid4().hex,'runtime':mapped,'invocations':[],
        'ordinary_input_verified':False,'normal_mainwindow_startup_qualified':False,
        'provider_startup_qualified':False,'performance_measured':False,'action_durability_verified':False,'calls':calls}
    hub, view, owner = None, None, None

    def origins():
        values = {}
        for name, module in tuple(sys.modules.items()):
            if (name=='native_studio' or name.startswith('native_studio.') or name.startswith('PyQt6.')) and getattr(module,'__file__',None):
                path = Path(module.__file__).resolve()
                need(path.is_relative_to(bundle.resolve()),'Module escaped frozen bundle: '+name)
                values[name] = str(path)
        return values

    class DenyAI(QObject):
        inventory_ready=pyqtSignal(object,object);proposal_ready=pyqtSignal(str,str)
        failed=pyqtSignal(str,str);state_changed=pyqtSignal(str)
        busy=False
        def refresh_models(self):
            calls['provider']+=1;raise RuntimeError('AI inventory disabled')
        def generate(self,*args,**kwargs):
            calls['provider']+=1;raise RuntimeError('AI generation disabled')
        def cancel(self):
            return None

    def deny_network(*args,**kwargs):
        calls['network']+=1;raise RuntimeError('Network disabled in packaged acceptance')

    def spin(predicate,label,seconds=50):
        end=time.monotonic()+seconds
        while not predicate():
            if time.monotonic()>end:raise TimeoutError(label+'; retain owners, no restart')
            if view and view.saved_play._deadline is not None and view.saved_play._deadline-time.monotonic()<2:
                view.saved_play._timer.stop();raise TimeoutError('Lifecycle deadline approached; no force kill')
            app.processEvents();time.sleep(.005)

    def idle():
        spin(lambda:view.loaded and view.client.state=='ready' and not view.busy and
             not view.client.pending_count and not view.asset_client.busy,'Coherent owner')

    def close_clean():
        idle();need(not view.client.dirty and not view.client.uncertain_operations,'Dirty fixture retained')
        view.close_project(discard=False)
        spin(lambda:view.client.state=='closed' and view._children_closed(),'Normal owner close')
        need(not getattr(view.client,'_killed',False),'Owner forced cleanup')
        record['host']=owner.finish();hub.timer.stop()
        need(bus.shutdown(3000),'Owned EngineBus did not join')
        hub.close();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);sip.delete(hub);app.processEvents()

    def invoke(label):
        journal=saved_chapter_export.hash_saved_journal(work/'project')
        view.start_saved_play();spin(lambda:view.saved_play.state=='ready',label+' READY')
        client=view.saved_play;handle=OwnedHandle(client.process_id,binary/'aibs_motherboard.exe')
        receipt(work/(label+'.started.json'),handle.info)
        publication=saved_play_storage.revalidate_publication(client.publication)
        snapshot=client.snapshot
        need(client.dependency_process_id==view.saved_export.process_id==0,'Stage/export worker not joined')
        expected_closure={name:info for name,info in tree(snapshot.asset_store).items()
            if name.split('/')[0] in {ref.pack_sha256 for ref in snapshot.asset_refs}}
        need(tree(publication.asset_root)==expected_closure,'Published closure differs')
        session, head=client.session_id, tuple(client._ready_head)
        view.stop_saved_play();spin(lambda:client.state=='closed' and client.process_id==client.dependency_process_id==0,label+' STOPPED')
        result=dict(client.last_result or {})
        need(result.get('saved') is True and result.get('graceful') is True and
             result.get('forced') is False and result.get('ready_seen') is True,'Native lifecycle did not drain normally')
        for key,value in {'play_session':session,'timeline_id':publication.timeline_id,'content_fingerprint':snapshot.fingerprint,
            'project_id':snapshot.scope.project,'branch_id':snapshot.scope.branch,'world_id':snapshot.scope.world_id,'context':'player_world'}.items():
            need(result.get(key)==value,'STOPPED identity differs: '+key)
        need(all(result[key]>=value for key,value in zip(('durable_revision','durable_sequence'),head)),'Durable head regressed')
        need(saved_chapter_export.hash_saved_journal(work/'project')==journal,'Authoring journal changed')
        need(not tuple(publication.slot_directory.glob('stop.*.request')),'Invocation stop marker retained after exit')
        row={'label':label,'process':handle.finish(),'session':session,'timeline':publication.timeline_id,
            'database':str(publication.database_path),'claim':pin(publication.database_path.with_name('world.sqlite.initialized')),
            'ready_head':head,'result':result,'reused_slot':publication.reused_slot,'reused_publication':publication.reused_publication,
            'published_closure':expected_closure,'stdout':client.stdout_tail.decode('utf8','replace'),
            'stderr':client.stderr_tail.decode('utf8','replace')}
        record['invocations'].append(row);receipt(work/(label+'.json'),row)
        return row

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket,'connect',deny_network))
        stack.enter_context(patch.object(socket,'create_connection',deny_network))
        # Explicit AI-only constructor DI; every actual bundle path/default
        # selection, native owner, export, stage and player remains untouched.
        stack.enter_context(patch.object(content_view,'ContentAIClient',DenyAI))
        try:
            hub=game_build_view.GameBuildNativeView(bus)
            hub.workspace_tabs.setCurrentIndex(2);view=hub.content_view
            need(type(view) is content_view.ContentView,'Actual bundled ContentView required')
            need(view.executable==binary/'aibs_content_host.exe' and
                 view.asset_client.cooker==binary/'aibs_assetc.exe','Default bundle host/cooker selection differs')
            view.open_project(work/'project');idle();owner=OwnedHandle(view.client.process_id,binary/'aibs_content_host.exe')
            record['host_opened']=owner.info
            need(view._play_binary(saved=True)==binary/'aibs_motherboard.exe','Default bundle player selection differs')
            record['module_origins_before']=origins()
            first,second=invoke('first'),invoke('resume')
            need(first['session']!=second['session'] and first['process']['pid']!=second['process']['pid'],'Fresh native player required')
            need(second['reused_slot'] and second['reused_publication'],'Actual retained slot/publication not reused')
            for key in ('timeline','database','claim','published_closure'):
                need(first[key]==second[key],'Resume identity differs: '+key)
            need(tuple(second['ready_head'])==(first['result']['durable_revision'],first['result']['durable_sequence']), 'Fresh READY head differs')
            need(calls=={'network':0,'provider':0},'Unexpected network/provider attempt')
            record['module_origins_after']=origins();close_clean()
            record['status']='PASS_FROZEN_DEFAULT_BUNDLE_CHAPTER_LIFECYCLE'
        except BaseException as error:
            record.update(status='FAILED',error_type=type(error).__name__,error=str(error))
            if view:
                view.saved_play._timer.stop()
                if owner is None and view.client.process_id:
                    owner=OwnedHandle(view.client.process_id,binary/'aibs_content_host.exe')
                    record['host_opened']=owner.info
                record['failure_state']={'host':view.client.process_id,'player':view.saved_play.process_id,
                    'dependency':view.saved_play.dependency_process_id,'saved_state':view.saved_play.state,
                    'dirty':view.client.dirty,'pending':view.client.pending_count,'status':view.saved_play_status.text(),
                    'last_result':view.saved_play.last_result}
            receipt(work/'failure.json',record)
            if view and (not view._children_closed() or view.busy or view.client.pending_count or
                         view.client.dirty or view.client.uncertain_operations or
                         (view.client.process_id and view.client.state!='ready')):
                receipt(work/'retained.json',{'worker_pid':os.getpid(),'nonce':record['nonce'],
                    'control':'Create close-retained.json with matching worker_pid/nonce to request public stop and clean close; never kill/restart.'})
                while True:
                    app.processEvents()
                    if view.saved_play._deadline is not None and view.saved_play._deadline-time.monotonic()<2:view.saved_play._timer.stop()
                    if io(work/'close-retained.json').exists():
                        request=json.loads(read(work/'close-retained.json'))
                        if request.get('worker_pid')==os.getpid() and request.get('nonce')==record['nonce']:
                            if view.saved_play.state=='ready':view.stop_saved_play()
                            if (view.saved_play.state=='closed' and view.client.state=='ready' and
                                    not view.busy and not view.client.pending_count and
                                    not view.client.dirty and not view.client.uncertain_operations):
                                close_clean();break
                    time.sleep(.05)
            elif view and owner and view.client.state=='ready':
                close_clean()
        finally:
            record['original_source_unchanged']=tree(SOURCE)==before
            record['journal_unchanged']=pin(work/'project/chapter.aiba')==before['chapter.aiba']
            if not record['original_source_unchanged'] or not record['journal_unchanged']:record['status']='FAILED_SOURCE_PRESERVATION'
            receipt(report,record)
    return 0 if record['status']=='PASS_FROZEN_DEFAULT_BUNDLE_CHAPTER_LIFECYCLE' else 2


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packaged-chapter-acceptance',required=True,type=Path,metavar='NEW_REPORT')
    parser.add_argument('--packaged-chapter-work',required=True,type=Path,metavar='NEW_WORK')
    parser.add_argument('--packaged-runtime-manifest',required=True,type=Path)
    parser.add_argument('--allow-native-window',action='store_true')
    args=parser.parse_args(argv)
    return run(args.packaged_chapter_acceptance,args.packaged_chapter_work,args.packaged_runtime_manifest,args.allow_native_window)
