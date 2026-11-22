"""Actual typed FDX Qt writer; owned pipe, synthetic source, no HTTP/model path."""
from pathlib import Path
import copy,hashlib,json,os,socket,sys,time,traceback
ROOT=Path(__file__).resolve().parents[3]
INSERT='carefully '

def send(connection,value):
    raw=json.dumps(value,ensure_ascii=True).encode('ascii')+b'\n'
    if len(raw)>32768:raise ValueError('coordination bound')
    connection.sendall(raw)

def main():
    session=None;connection=None;directory=None;step='arguments'
    try:
        phase=sys.argv[1];port=int(sys.argv[2]);directory=Path(sys.argv[3]).resolve()
        if phase not in {'preserve','restore-save','reopen-export'}or not directory.is_relative_to((ROOT/'t').resolve()):raise ValueError()
        sys.path[:0]=[str(ROOT),str(ROOT/'backend'),sys.argv[4]]
        from unittest.mock import patch
        import httpx
        from native_studio.creative_session import CreativeSession,bootstrap_native_session
        calls=[]
        def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('No HTTP')
        with patch.object(httpx,'Client',side_effect=forbidden):
            step='bootstrap';session,packet=bootstrap_native_session([sys.argv[0],'--native-creative-pipe-bootstrap'],sys.stdin.buffer,
                session_factory=lambda *,endpoint:CreativeSession(endpoint=endpoint,headers_provider=forbidden))
            before_qt=not any(name.startswith('PyQt6')for name in sys.modules)
            os.environ['QT_QPA_PLATFORM']='offscreen'
            site=ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages';sys.path.insert(0,str(site))
            dll=os.add_dll_directory(str(site/'PyQt6/Qt6/bin'))
            from PyQt6 import sip
            from PyQt6.QtGui import QTextCursor
            from PyQt6.QtWidgets import QApplication,QFileDialog,QMessageBox
            from native_studio.screenplay_client import DraftSession
            from native_studio.native_creative_entry import create_native_creative_window,dispose_closed_native_creative_window
            import native_studio.screenwriting_view as writer
            app=QApplication([]);app.setQuitOnLastWindowClosed(False);warnings=[]
            def pump(predicate,seconds=15):
                deadline=time.monotonic()+seconds
                while not predicate():
                    if time.monotonic()>deadline:raise TimeoutError(step)
                    app.processEvents();time.sleep(.005)
                app.processEvents()
            recovery_root=directory.parent/'private-rich-recovery'
            with patch.object(writer,'DraftSession',side_effect=lambda:DraftSession(recovery_root)), \
                    patch.object(QMessageBox,'warning',side_effect=lambda *args:warnings.append(True)), \
                    patch.object(QMessageBox,'information'), \
                    patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):
                step='actual_rich_read';window=create_native_creative_window(session,packet);window.show();view=window.writer
                pump(lambda:not view._writer_busy)
                if not view._delegated_editor_ready()or view.editor.isReadOnly()or warnings or view._draft.rich is None:raise AssertionError(step)
                original_revision=view._draft.revision;loaded=copy.deepcopy(view._draft.rich.document)
                if (loaded['blocks'][0]['runs'][0]['attributes']!={'Style':'Bold','RevisionID':'5'}
                        or loaded['blocks'][0]['notes'][0]['text']!='NOTE ONLY'
                        or 'DocumentInfo'not in loaded['preserved_sections']):raise AssertionError('Rich fixture not loaded')
                result={'kind':'complete','phase':phase,'pid':os.getpid(),'loaded_rich_document':True,
                    'bootstrap_before_qt':before_qt,'only_writing_page':view.suite_stack.count()==1,
                    'original_revision':original_revision,'http_calls':0}
                if phase=='preserve':
                    step='exact_styled_paragraph_edit'
                    position=view._draft.rich.projection_spans[0]['start']+len('Bold & ')
                    # This fixture prefix is ASCII: QTextCursor positions here
                    # are exact UTF-16/codepoint-identical offsets.
                    cursor=view.editor.textCursor();cursor.setPosition(position);view.editor.setTextCursor(cursor)
                    view.editor.insertPlainText(INSERT)
                    if not view._draft.dirty or view._draft.rich.blocked_reason:raise AssertionError(step)
                    captured=view._draft.capture_rich_snapshot()
                    if captured['blocks'][0]['text']!='Bold & carefully literal *stars*':raise AssertionError('Exact text')
                    if captured['blocks'][0]['runs']!=loaded['blocks'][0]['runs']:raise AssertionError('Readonly style metadata changed')
                    path=view._draft.preserve();raw=path.read_bytes();record=json.loads(raw)
                    if record['rich_draft']!=view._draft.rich.recovery_payload()or record['schema']!=3:raise AssertionError('Complete rich recovery')
                    result.update(recovery_path=str(path),recovery_sha256=hashlib.sha256(raw).hexdigest(),
                        recovery_scope=record['recovery_scope'],rich_history_nodes=len(record['rich_draft']['history_nodes']),
                        dirty=True,host_saves=0)
                elif phase=='restore-save':
                    step='fresh_rich_recovery_button'
                    paths=list(recovery_root.glob('*.json'))
                    if len(paths)!=1:raise AssertionError('Expected one frozen recovery')
                    path=paths[0];raw=path.read_bytes();record=json.loads(raw)
                    if view._draft.dirty or view._draft.content!=record['baseline']:raise AssertionError('Fresh host baseline')
                    with patch.object(QFileDialog,'getOpenFileName',return_value=(str(path),'Recovery copies (*.json)')), \
                            patch.object(session._channel,'request',wraps=session._channel.request)as requests:
                        view.btn_recovery.click();app.processEvents()
                        if requests.call_count:raise AssertionError('Restore dispatched host operation')
                    if (view._draft.rich.recovery_payload()!=record['rich_draft']or view.editor.toPlainText()!=record['content']
                            or not view._draft.dirty or view._draft.uncertain or warnings):raise AssertionError('Rich restore mismatch')
                    # Exercise the actual recovered QTextDocument undo stack,
                    # including its contentsChange -> rich-draft synchronization.
                    if not view.editor.document().isUndoAvailable():raise AssertionError('Recovered editor has no Undo')
                    view.editor.undo();app.processEvents()
                    if (view.editor.toPlainText()!=record['baseline']or view._draft.content!=record['baseline']
                            or view._draft.capture_rich_snapshot()!=loaded):raise AssertionError('Recovered UI undo')
                    if not view.editor.document().isRedoAvailable():raise AssertionError('Recovered editor has no Redo')
                    view.editor.redo();app.processEvents()
                    if (view.editor.toPlainText()!=record['content']or view._draft.rich.recovery_payload()!=record['rich_draft']
                            or view._draft.content!=record['content']):raise AssertionError('Recovered UI redo')
                    step='explicit_rich_CAS_save'
                    with patch.object(session._channel,'request',wraps=session._channel.request)as requests:
                        view._save_script();pump(lambda:not view._writer_busy)
                        saves=[call for call in requests.call_args_list if call.args[0]=='save']
                        if len(saves)!=1:raise AssertionError('Expected one explicit save')
                    if (view._draft.dirty or view._draft.uncertain or warnings or view._draft.revision==original_revision
                            or view._draft.rich is None):raise AssertionError('Save not confirmed')
                    if path.read_bytes()!=raw:raise AssertionError('Recovery overwritten')
                    result.update(recovery_button_used=True,complete_rich_restore=True,restored_history_undo_redo=True,
                        actual_editor_undo_redo=True,
                        host_operations_during_restore=0,host_saves=1,saved_revision=view._draft.revision,
                        recovery_sha256=hashlib.sha256(raw).hexdigest(),recovery_scope=record['recovery_scope'])
                else:
                    step='fresh_rich_read_export'
                    if view._draft.dirty or loaded['blocks'][0]['text']!='Bold & carefully literal *stars*':raise AssertionError('Rich reopen text')
                    target=directory/'preserved.fdx'
                    # Select the ordinary preservation export, never reflow.
                    with patch.object(QFileDialog,'getSaveFileName',return_value=(str(target),'Final Draft (*.fdx)')):
                        action=next(action for action in view.btn_export_fdx.menu().actions()if 'Export Final Draft'in action.text())
                        if not action.isVisible()or not action.isEnabled():raise AssertionError('Preserved export unavailable')
                        action.trigger();pump(lambda:not view._writer_busy)
                    if not target.is_file()or warnings:raise AssertionError('Preserved FDX export missing')
                    raw=target.read_bytes()
                    if (b'<Unknown Flag="keep">inert</Unknown>'not in raw or b'<DualDialogue>'not in raw
                            or b'NOTE ONLY'not in raw or b'Style="Bold" RevisionID="5"'not in raw):raise AssertionError('Preserved XML metadata')
                    result.update(reopened_saved_rich_edit=True,export_path=str(target),export_sha256=hashlib.sha256(raw).hexdigest(),
                        export_bytes=len(raw),export_profile='rich-preserved',host_saves=0)
                step='normal_close';window.close();pump(lambda:window._close_state=='READY'and window.bus.is_drained)
                result.update(gui_drained=window.bus.is_drained,descriptors_closed=not session._bootstrap_resources._fds,
                    session_cleared=session._lease is None,warning_count=len(warnings),http_calls=len(calls))
                if calls or not result['session_cleared']or not result['descriptors_closed']:raise AssertionError('Close incomplete')
                connection=socket.create_connection(('127.0.0.1',port),timeout=10);connection.settimeout(20)
                send(connection,result)
                if connection.recv(1)!=b'X':raise ValueError()
                step='Qt_disposal';dispose_closed_native_creative_window(window,app);sip.delete(app)
            dll.close();return 0
    except BaseException as error:
        frames=traceback.extract_tb(error.__traceback__)
        failure={'kind':'failure','phase':sys.argv[1]if len(sys.argv)>1 else 'unknown','step':step,
            'exception_class':type(error).__name__,'location':{'file':Path(frames[-1].filename).name,'line':frames[-1].lineno}if frames else None}
        if directory is not None:
            (directory/'failure.json').write_text(json.dumps(failure,indent=2),encoding='utf-8')
        if connection is None:
            try:connection=socket.create_connection(('127.0.0.1',int(sys.argv[2])),timeout=3)
            except OSError:pass
        if connection is not None:
            try:send(connection,failure)
            except OSError:pass
        return 2
    finally:
        if session is not None:session.close()
        if connection is not None:connection.close()
if __name__=='__main__':raise SystemExit(main())
