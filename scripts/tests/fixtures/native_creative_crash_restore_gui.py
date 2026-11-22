"""Fresh actual GUI restores a retained private copy through the Recovery button."""
from pathlib import Path
import faulthandler,hashlib,json,os,socket,sys,time
ROOT=Path(__file__).resolve().parents[3]
MARKER='UNSAVED BACKEND LOSS SYNTHETIC EDIT'

def send(s,value):s.sendall(json.dumps(value).encode()+b'\n')

def main():
    session=None;connection=None;step='arguments';fault_log=None
    try:
        recovery=Path(sys.argv[2]).resolve()
        if not recovery.is_relative_to((ROOT/'t').resolve()):raise ValueError()
        fault_log=(recovery.parent/'restore-native-shutdown-fault.log').open('x',encoding='utf-8')
        faulthandler.enable(file=fault_log,all_threads=True)
        sys.path[:0]=[str(ROOT),str(ROOT/'backend'),sys.argv[3]]
        from unittest.mock import patch
        import httpx
        from native_studio.creative_session import CreativeSession,bootstrap_native_session
        calls=[]
        def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('No HTTP')
        with patch.object(httpx,'Client',side_effect=forbidden):
            session,packet=bootstrap_native_session([sys.argv[0],'--native-creative-pipe-bootstrap'],sys.stdin.buffer,
                session_factory=lambda *,endpoint:CreativeSession(endpoint=endpoint,headers_provider=forbidden))
            os.environ['QT_QPA_PLATFORM']='offscreen'
            site=ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages';sys.path.insert(0,str(site))
            dll=os.add_dll_directory(str(site/'PyQt6/Qt6/bin'))
            from PyQt6.QtWidgets import QApplication,QMessageBox,QFileDialog
            from native_studio.screenplay_client import DraftSession
            from native_studio.native_creative_entry import create_native_creative_window,dispose_closed_native_creative_window
            from PyQt6 import sip
            import native_studio.screenwriting_view as writer
            app=QApplication([]);app.setQuitOnLastWindowClosed(False);warnings=[]
            def pump(test,seconds=15):
                deadline=time.monotonic()+seconds
                while not test():
                    if time.monotonic()>deadline:raise TimeoutError(step)
                    app.processEvents();time.sleep(.005)
                app.processEvents()
            with patch.object(writer,'DraftSession',side_effect=lambda:DraftSession(recovery.parent)), \
                    patch.object(QMessageBox,'warning',side_effect=lambda *args:warnings.append(True)), \
                    patch.object(QMessageBox,'information'), \
                    patch.object(QFileDialog,'getOpenFileName',return_value=(str(recovery),'Recovery copies (*.json)')):
                step='fresh_host_read';window=create_native_creative_window(session,packet);window.show();view=window.writer
                pump(lambda:not view._writer_busy)
                if not view._delegated_editor_ready()or warnings or view._draft.dirty or view.editor.isReadOnly():raise AssertionError(step)
                baseline=view._draft.baseline;revision=view._draft.revision
                if MARKER in baseline:raise AssertionError('Host unexpectedly saved edit')
                # This real source-fenced PDF fixture returns plain projection;
                # widget type is not evidence that an FDX rich document loaded.
                if view._draft.rich is not None:raise AssertionError('Unexpected PDF fixture format')
                raw=recovery.read_bytes();record=json.loads(raw)
                if record['schema']!=3 or record['recovery_scope']!=session.recovery_scope:raise AssertionError('Owner/source binding')
                step='recovery_button'
                with patch.object(session._channel,'request',wraps=session._channel.request)as requests:
                    view.btn_recovery.click();app.processEvents()
                    if requests.call_count:raise AssertionError('Recovery unexpectedly dispatched host operation')
                if (view.editor.toPlainText()!=record['content'] or MARKER not in view.editor.toPlainText()
                        or not view._draft.dirty or view._draft.uncertain or view._draft.revision!=revision
                        or view._draft.baseline!=baseline or warnings or recovery.read_bytes()!=raw):raise AssertionError(step)
                step='normal_close';window.close();pump(lambda:window._close_state=='READY'and window.bus.is_drained)
                if calls or session._lease is not None or session._bootstrap_resources._fds:raise AssertionError('Drain')
                connection=socket.create_connection(('127.0.0.1',int(sys.argv[1])),timeout=10);connection.settimeout(20)
                send(connection,{'kind':'restore_gui','pid':os.getpid(),'dirty':view._draft.dirty,
                    'uncertain':view._draft.uncertain,'revision':revision,'recovery_button_used':True,
                    'restored_complete_draft':True,'host_operations_during_restore':0,'loaded_rich_document':False,
                    'recovery_sha256':hashlib.sha256(raw).hexdigest(),'gui_drained':True,'descriptors_closed':True,
                    'http_calls':len(calls),'recovery_scope':record['recovery_scope']})
                if connection.recv(1)!=b'X':raise ValueError()
                step='deterministic_qt_disposal'
                dispose_closed_native_creative_window(window,app)
                sip.delete(app)
            dll.close();return 0
    except BaseException as error:
        if connection is None:
            try:connection=socket.create_connection(('127.0.0.1',int(sys.argv[1])),timeout=3)
            except OSError:pass
        if connection is not None:
            try:send(connection,{'kind':'failure','step':step,'exception_class':type(error).__name__})
            except OSError:pass
        return 2
    finally:
        if session is not None:session.close()
        if connection is not None:connection.close()
        if fault_log is not None:
            faulthandler.disable();fault_log.close()
if __name__=='__main__':raise SystemExit(main())
