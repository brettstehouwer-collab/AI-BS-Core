"""Synthetic offscreen editor surviving its exact owned backend's termination."""
from pathlib import Path
import faulthandler,hashlib,json,os,socket,sys,time,traceback
ROOT=Path(__file__).resolve().parents[3]
MARKER='UNSAVED BACKEND LOSS SYNTHETIC EDIT'
def send(s,v):s.sendall(json.dumps(v).encode()+b'\n')
def main():
    session=None;connection=None;step='arguments';directory=None;fault_log=None
    try:
        port=int(sys.argv[1]);directory=Path(sys.argv[2]).resolve()
        if not directory.is_relative_to((ROOT/'t').resolve()):raise ValueError()
        fault_log=(directory/'native-shutdown-fault.log').open('x',encoding='utf-8')
        faulthandler.enable(file=fault_log,all_threads=True)
        sys.path[:0]=[str(ROOT),str(ROOT/'backend'),sys.argv[3]]
        from unittest.mock import patch
        import httpx
        from native_studio.creative_session import CreativeSession,bootstrap_native_session
        calls=[]
        def forbidden(*a,**k):calls.append(True);raise AssertionError('No HTTP')
        with patch.object(httpx,'Client',side_effect=forbidden):
            step='bootstrap'
            session,packet=bootstrap_native_session([sys.argv[0],'--native-creative-pipe-bootstrap'],sys.stdin.buffer,
                session_factory=lambda *,endpoint:CreativeSession(endpoint=endpoint,headers_provider=forbidden))
            os.environ['QT_QPA_PLATFORM']='offscreen'
            site=ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages';sys.path.insert(0,str(site))
            dll=os.add_dll_directory(str(site/'PyQt6/Qt6/bin'))
            from PyQt6.QtGui import QTextCursor
            from PyQt6.QtWidgets import QApplication,QMessageBox
            from native_studio.screenplay_client import DraftSession
            from native_studio.native_creative_entry import create_native_creative_window,dispose_closed_native_creative_window
            from PyQt6 import sip
            import native_studio.screenwriting_view as writer
            app=QApplication([]);app.setQuitOnLastWindowClosed(False);warnings=[]
            def pump(test,seconds=15):
                end=time.monotonic()+seconds
                while not test():
                    if time.monotonic()>end:raise TimeoutError()
                    app.processEvents();time.sleep(.005)
                app.processEvents()
            with patch.object(writer,'DraftSession',side_effect=lambda:DraftSession(directory/'recovery')), \
                    patch.object(QMessageBox,'warning',side_effect=lambda *a:warnings.append(True)), \
                    patch.object(QMessageBox,'information'), \
                    patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):
                step='load';window=create_native_creative_window(session,packet);window.show();view=window.writer
                pump(lambda:not view._writer_busy)
                if not view._delegated_editor_ready() or view.editor.isReadOnly() or warnings:raise AssertionError()
                view.editor.moveCursor(QTextCursor.MoveOperation.End);view._insert_element_text('\n'+MARKER+'\n')
                if not view._draft.dirty:raise AssertionError()
                previous=view._draft.preserve();before=previous.read_bytes()
                connection=socket.create_connection(('127.0.0.1',port),timeout=10);connection.settimeout(30)
                send(connection,{'kind':'gui_ready','pid':os.getpid(),'unsaved':True})
                if connection.recv(1)!=b'L':raise ValueError()
                step='save_after_loss'
                with patch.object(session._channel,'request',wraps=session._channel.request)as requests:
                    view._save_script();pump(lambda:not view._writer_busy)
                    save_attempts=sum(call.args[0]=='save'for call in requests.call_args_list)
                if save_attempts!=1:raise AssertionError()
                if not view._draft.uncertain or not view._draft.dirty or not warnings:raise AssertionError()
                recovered=view._draft.preserve();raw=recovered.read_bytes();data=json.loads(raw)
                if (MARKER not in data.get('content','') or data['content']!=view._draft.content
                        or previous.read_bytes()!=before):raise AssertionError()
                step='normal_close';window.close();pump(lambda:window._close_state=='READY' and window.bus.is_drained)
                if calls or session._lease is not None or session._bootstrap_resources._fds:raise AssertionError()
                send(connection,{'kind':'complete','pid':os.getpid(),'uncertain':view._draft.uncertain,
                    'dirty':view._draft.dirty,'recovery_path':str(recovered),'recovery_sha256':hashlib.sha256(raw).hexdigest(),
                    'previous_recovery_unchanged':True,'recovery_matches_complete_draft':True,'save_attempts':save_attempts,
                    'http_calls':len(calls),'gui_drained':True,'descriptors_closed':True})
                if connection.recv(1)!=b'X':raise ValueError()
                step='deterministic_qt_disposal'
                dispose_closed_native_creative_window(window,app)
                sip.delete(app)
            dll.close();return 0
    except BaseException as error:
        failure={'kind':'failure','step':step,'exception_class':type(error).__name__}
        if directory is not None:
            (directory/'failure.json').write_text(json.dumps(failure),encoding='utf-8')
        if connection is not None:
            try:send(connection,failure)
            except OSError:pass
        return 2
    finally:
        if session is not None:session.close()
        if connection is not None:connection.close()
        if fault_log is not None:
            faulthandler.disable();fault_log.close()
if __name__=='__main__':raise SystemExit(main())
