"""Explicit owner-delegated native writer entry; no ordinary-shell startup.

Bootstrap is completed before Qt, EngineBus or writer imports. The writer retains
its existing rich editor, revision checks, exports and private recovery behavior.
No production candidate is selected or service started by importing this module.
"""
import sys

from native_studio.creative_session import bootstrap_native_session, CreativeSessionError


def create_native_creative_window(session, packet):
    """Create the existing scoped writer only, with its own safe close barrier."""
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QMainWindow
    from native_studio.engine import EngineBus
    from native_studio.screenwriting_view import ScreenwritingNativeView

    class NativeCreativeWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self._close_state='OPEN'
            self.session=session
            self.bus=EngineBus(max_threads=2)
            self.writer=ScreenwritingNativeView(self.bus,creative_session=session,bootstrap=packet)
            self.setCentralWidget(self.writer)
            self.setWindowTitle('AI-BS — Connected Screenwriting Project')
            self.resize(1400,900)
            self._close_timer=QTimer(self)
            self._close_timer.setInterval(20)
            self._close_timer.timeout.connect(self._finish_close)
            self.bus.drained.connect(self._finish_close)

        def closeEvent(self,event):
            if self._close_state=='READY':
                event.accept();return
            event.ignore()
            if self._close_state!='OPEN':return
            if not self.writer._preserve_native_draft():return
            self._close_state='DRAINING'
            self.writer.setEnabled(False)
            for timer in self.writer.findChildren(QTimer):timer.stop()
            self._close_timer.start()
            self.bus.shutdown(0)
            self._finish_close()

        def _finish_close(self):
            if self._close_state=='DRAINING' and self.bus.is_drained:
                if self.session.close() is not True:
                    return
                self._close_timer.stop()
                self._close_state='READY'
                QTimer.singleShot(0,self.close)

    return NativeCreativeWindow()


def dispose_closed_native_creative_window(window, app):
    """Destroy drained Qt objects while the QApplication is still alive.

    READY schedules a final close callback. Leaving that callback and the
    unparented EngineBus to interpreter shutdown gives SIP no stable teardown
    order. This function never destroys an editor still draining or holding work.
    """
    from PyQt6 import sip
    from PyQt6.QtCore import QCoreApplication, QEvent
    bus = window.bus
    if window._close_state != 'READY' or not bus.is_drained:
        raise RuntimeError('The creative window must finish its close barrier before disposal.')
    app.processEvents()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    if not sip.isdeleted(window):
        sip.delete(window)
    if not sip.isdeleted(bus):
        sip.delete(bus)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def _run_writer(session,packet):
    from PyQt6.QtWidgets import QApplication
    from native_studio.theme import STYLESHEET,apply_dark_titlebar
    app=QApplication([sys.argv[0]])
    app.setStyleSheet(STYLESHEET)
    window=create_native_creative_window(session,packet)
    apply_dark_titlebar(window)
    window.show()
    result = app.exec()
    dispose_closed_native_creative_window(window, app)
    from PyQt6 import sip
    sip.delete(app)
    return result


def main(argv=None,*,stream=None,run_writer=None):
    argv=list(sys.argv if argv is None else argv)
    if not any(flag in argv for flag in ('--native-creative-bootstrap','--native-creative-pipe-bootstrap')):return 2
    session=None
    try:
        prepared=bootstrap_native_session(argv,sys.stdin.buffer if stream is None else stream)
        if prepared is None:raise CreativeSessionError()
        session,packet=prepared
        return (_run_writer if run_writer is None else run_writer)(session,packet)
    except Exception:
        # The child has no authorization fallback and never emits document,
        # credential, transport or traceback details onto inherited output.
        return 2
    finally:
        if session is not None:session.close()


if __name__=='__main__':
    raise SystemExit(main())
