"""Fixed offscreen rich-writer fixture: private v2 pipe only, no HTTP transport."""
from pathlib import Path
import hashlib
import json
import os
import socket
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[3]
MARKER='NATIVE PIPE GUI FIXTURE EDIT'


def send(connection,value):
    raw=json.dumps(value,ensure_ascii=True).encode('ascii')+b'\n'
    if len(raw)>8192:raise ValueError()
    connection.sendall(raw)


def main():
    phase,step,directory,connection='unknown','arguments',None,None
    session=None;http_calls=[]
    try:
        if (len(sys.argv)!=6 or sys.argv[1]not in {'edit-save','reopen-export','draft-preserve','draft-restore'}
                or sys.argv[5]!='--native-creative-pipe-bootstrap'):raise ValueError()
        phase=sys.argv[1];coordination_port=int(sys.argv[2])
        if not 1<=coordination_port<=65535 or coordination_port==8080:raise ValueError()
        directory=Path(sys.argv[3]).resolve()
        if (not directory.is_dir() or directory.is_symlink()
                or not directory.is_relative_to((ROOT/'t').resolve())):raise ValueError()
        sys.path[:0]=[str(ROOT),str(ROOT/'backend'),sys.argv[4]]
        from unittest.mock import patch
        import httpx
        from native_studio.creative_session import CreativeSession,bootstrap_native_session
        def forbidden_http(*args,**kwargs):
            http_calls.append(True);raise AssertionError('HTTP not allowed in pipe fixture')
        def session_factory(*,endpoint):
            return CreativeSession(endpoint=endpoint,headers_provider=forbidden_http)
        with patch.object(httpx,'Client',side_effect=forbidden_http):
            step='v2_bootstrap_redeem'
            session,packet=bootstrap_native_session([sys.argv[0],'--native-creative-pipe-bootstrap'],
                sys.stdin.buffer,session_factory=session_factory)
            before_qt=not any(name.startswith('PyQt6') for name in sys.modules)
            if not session.owned_channel:raise AssertionError()
            os.write(1,b'fixed pipe fixture stdout sink probe\n')
            os.write(2,b'fixed pipe fixture stderr sink probe\n')
            connection=socket.create_connection(('127.0.0.1',coordination_port),timeout=10)
            connection.settimeout(45)
            send(connection,dict(kind='ready',phase=phase,pid=os.getpid(),bootstrap_before_qt=before_qt,
                                 pipe_mode=True,http_calls=len(http_calls)))
            if connection.recv(1)!=b'R':raise ValueError()
            step='qt_initialization'
            os.environ['QT_QPA_PLATFORM']='offscreen'
            qt_site=ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages'
            sys.path.insert(0,str(qt_site))
            dll_directory=os.add_dll_directory(str(qt_site/'PyQt6/Qt6/bin'))
            from PyQt6.QtGui import QFontDatabase,QTextCursor
            from PyQt6.QtWidgets import QApplication,QFileDialog,QMessageBox
            from native_studio.screenplay_client import DraftSession
            from native_studio.native_creative_entry import create_native_creative_window, dispose_closed_native_creative_window
            import native_studio.screenwriting_view as writer
            app=QApplication([]);app.setQuitOnLastWindowClosed(False)
            for filename in ('segoeui.ttf','cour.ttf'):
                font=Path('C:/Windows/Fonts')/filename
                if font.is_file():QFontDatabase.addApplicationFont(str(font))
            warnings=[]
            def pump(predicate,seconds=15):
                deadline=time.monotonic()+seconds
                while not predicate():
                    if time.monotonic()>=deadline:raise TimeoutError()
                    app.processEvents();time.sleep(.005)
                app.processEvents()
            recovery_root = directory.parent/'shared-recovery' if phase.startswith('draft-') else directory/'recovery'
            with patch.object(writer,'DraftSession',side_effect=lambda:DraftSession(recovery_root)), \
                    patch.object(QMessageBox,'warning',side_effect=lambda *args:warnings.append(True)), \
                    patch.object(QMessageBox,'information'), \
                    patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):
                step='initial_bound_read'
                window=create_native_creative_window(session,packet);window.show();view=window.writer
                pump(lambda:not view._writer_busy)
                if not view._delegated_editor_ready() or view.editor.isReadOnly() or warnings:raise PermissionError()
                try:
                    dispose_closed_native_creative_window(window, app)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('Open editor was disposed before its close barrier')
                result=dict(kind='complete',phase=phase,pid=os.getpid(),actual_rich_writer=True,
                    only_writing_page=view.suite_stack.count()==1,exports={},http_calls=len(http_calls),
                    disposal_refused_before_ready=True)
                if phase=='draft-preserve':
                    step='preserve_unsaved_draft'
                    view.editor.moveCursor(QTextCursor.MoveOperation.End)
                    view.editor.insertPlainText(' '+MARKER)
                    if not view._draft.dirty:raise AssertionError()
                    if not view._preserve_native_draft():raise AssertionError()
                    target=view._draft.recovery_path
                    choice={'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                            'rich_payload':view._draft.rich.recovery_payload() if view._draft.rich else None}
                    with (directory.parent/'recovery-choice.json').open('x',encoding='utf8')as stream:json.dump(choice,stream)
                    result.update(recovery_preserved=True,host_revision=view._draft.revision)
                elif phase=='draft-restore':
                    step='fresh_gui_restore_unsaved_draft'
                    choice=json.loads((directory.parent/'recovery-choice.json').read_text(encoding='utf8'))
                    target=Path(choice['path']);before=target.read_bytes()
                    if MARKER in view.editor.toPlainText() or view._draft.dirty:raise AssertionError()
                    with patch.object(QFileDialog,'getOpenFileName',return_value=(str(target),'')):
                        view.btn_recovery.click()
                    if (warnings or MARKER not in view.editor.toPlainText() or not view._draft.dirty
                            or view._draft.uncertain
                            or (view._draft.rich.recovery_payload() if view._draft.rich else None)!=choice['rich_payload']
                            or target.read_bytes()!=before
                            or hashlib.sha256(before).hexdigest()!=choice['sha256']):raise AssertionError()
                    restored_text=view.editor.toPlainText()
                    view.editor.undo();app.processEvents()
                    if view.editor.toPlainText()!=view._draft.baseline or view._draft.dirty:raise AssertionError('Recovered plain Undo')
                    view.editor.redo();app.processEvents()
                    if view.editor.toPlainText()!=restored_text or not view._draft.dirty:raise AssertionError('Recovered plain Redo')
                    result.update(recovery_restored=True,rich_document_loaded=view._draft.rich is not None,
                                  recovery_sha256=choice['sha256'],host_revision=view._draft.revision,
                                  restored_editor_undo_redo=True)
                elif phase=='edit-save':
                    step='edit_and_save';old_revision=view._draft.revision
                    view.editor.moveCursor(QTextCursor.MoveOperation.End)
                    view._insert_element_text('\n\n'+MARKER+'\n')
                    if not view._draft.dirty:raise AssertionError()
                    view._save_script();pump(lambda:not view._writer_busy)
                    if (view._draft.dirty or view._draft.uncertain or warnings
                            or view._draft.revision==old_revision):raise AssertionError()
                    result.update(saved_revision=view._draft.revision,saved_edit_present=MARKER in view.editor.toPlainText())
                else:
                    step='fresh_process_reopen'
                    result['reopened_edit_present']=MARKER in view.editor.toPlainText()
                    if not result['reopened_edit_present']:raise AssertionError()
                    for fmt,button in (('fdx',view.btn_export_fdx),('pdf',view.btn_export_pdf)):
                        step='explicit_reflow_export_'+fmt
                        action=next(action for action in button.menu().actions() if 'Reformatted'in action.text())
                        if not action.isVisible() or not action.isEnabled():raise AssertionError()
                        target=directory/('reformatted.'+fmt)
                        if target.exists():raise AssertionError()
                        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(target),'')):action.trigger()
                        pump(lambda:not view._writer_busy)
                        if warnings or not target.is_file():raise AssertionError()
                        raw=target.read_bytes()
                        if fmt=='fdx':
                            import xml.etree.ElementTree as ET
                            text=' '.join(ET.fromstring(raw).itertext())
                        else:
                            from pypdf import PdfReader
                            text=' '.join(page.extract_text()or'' for page in PdfReader(target).pages)
                        if MARKER not in ' '.join(text.split()):raise AssertionError()
                        result['exports'][fmt]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                                                   edit_present=True,profile='explicit_reflow')
                step='gui_close_and_drain'
                with patch.object(session,'close',return_value=False):
                    window.close();app.processEvents()
                    if window._close_state!='DRAINING' or not window._close_timer.isActive():raise AssertionError()
                    result['close_retained_until_channel_drain']=True
                pump(lambda:window._close_state=='READY' and window.bus.is_drained)
                result.update(gui_worker_drained=window.bus.is_drained,session_cleared_after_close=session._lease is None,
                    adopted_descriptors_closed=not session._bootstrap_resources._fds,http_calls=len(http_calls),
                    forbidden_modules_loaded=[name for name in ('native_studio.creation_suite_subtools',
                        'native_studio.screenwriting_modals')if name in sys.modules])
                if http_calls or not result['adopted_descriptors_closed']:raise AssertionError()
                with (directory/'result.json').open('x',encoding='utf-8')as stream:json.dump(result,stream,indent=2)
                send(connection,result)
                if connection.recv(1)!=b'X':raise ValueError()
            dispose_closed_native_creative_window(window, app)
            from PyQt6 import sip
            sip.delete(app)
            dll_directory.close();connection.close();return 0
    except BaseException as error:
        frames=traceback.extract_tb(error.__traceback__)
        failure=dict(kind='failure',phase=phase,step=step,exception_class=type(error).__name__,
            location=dict(file=Path(frames[-1].filename).name,line=frames[-1].lineno)if frames else None,
            http_calls=len(http_calls))
        if directory is not None and directory.is_dir():
            target=directory/'failure.json'
            if not target.exists():
                with target.open('x',encoding='utf-8')as stream:json.dump(failure,stream,indent=2)
        if connection is not None:
            try:send(connection,failure);connection.close()
            except OSError:pass
        return 2
    finally:
        if session is not None:session.close()


if __name__=='__main__':raise SystemExit(main())
