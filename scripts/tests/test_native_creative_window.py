"""Actual Qt entry window/bus close barriers with disposable synthetic drafts."""
import json,os,threading,time
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from PyQt6.QtCore import QCoreApplication,QEvent
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication,QMessageBox
from scripts.tests.test_native_creative_scoped_view import Fixture
from native_studio.creative_session import Bootstrap,CreativeSession
from native_studio.screenplay_client import DraftSession,ScreenplayClient
from native_studio.native_creative_entry import create_native_creative_window
import native_studio.screenwriting_view as writer


class CreativeWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        cls.font=QFontDatabase.addApplicationFont('C:/Windows/Fonts/cour.ttf')

    @classmethod
    def tearDownClass(cls):
        if cls.font>=0:QFontDatabase.removeApplicationFont(cls.font)

    def pump_until(self,predicate,timeout=5):
        deadline=time.monotonic()+timeout
        while not predicate() and time.monotonic()<deadline:
            self.app.processEvents();time.sleep(.005)
        self.assertTrue(predicate(),'Qt condition did not complete before fixture deadline')

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.fixture=Fixture();self.release=threading.Event()
        self.session=CreativeSession(headers_provider=lambda:{'X-API-Key':'synthetic'},
            transport=httpx.MockTransport(self.fixture.handle))
        self.packet=Bootstrap('nch_g_'+'a'*43,'Bound',self.fixture.data['revision'],self.fixture.source,'b'*64)
        self.session.redeem(self.packet)
        client=ScreenplayClient
        for guard in (patch.object(writer,'ScreenplayClient',side_effect=lambda **kw:client(transport=httpx.MockTransport(self.fixture.handle),**kw)),
                      patch.object(writer,'DraftSession',side_effect=lambda:DraftSession(Path(self.temp.name)/'private')),
                      patch.object(QMessageBox,'warning'),patch.object(QMessageBox,'information')):
            guard.start();self.addCleanup(guard.stop)
        self.window=create_native_creative_window(self.session,self.packet)
        self.addCleanup(self.cleanup_window)
        self.window.show()
        self.pump_until(lambda:not self.window.writer._writer_busy)
        self.assertFalse(self.window.writer.editor.isReadOnly())

    def cleanup_window(self):
        self.release.set()
        self.window.close()
        self.pump_until(lambda:self.window.bus.is_drained)
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_normal_close_preserves_complete_utf8_draft_before_session_release(self):
        text='INT. FIXTURE - DAY\nUnsaved full text — Ω\n'
        self.window.writer.editor.setPlainText(text)
        self.window.close()
        self.pump_until(lambda:self.window._close_state=='READY')
        self.assertTrue(self.window.bus.is_drained)
        self.assertIsNone(self.session._lease)
        recovery=self.window.writer._draft.recovery_path
        self.assertEqual(json.loads(recovery.read_text(encoding='utf-8'))['content'],text)

    def test_close_waits_for_worker_barrier_and_suppresses_late_callback(self):
        started=threading.Event();delivered=[]
        def work():started.set();self.release.wait(3);return 'late'
        self.window.bus.submit(work,on_result=delivered.append)
        self.assertTrue(started.wait(2))
        self.window.close()
        self.assertEqual(self.window._close_state,'DRAINING')
        self.assertIsNotNone(self.session._lease)
        self.assertFalse(self.window.bus.is_drained)
        self.release.set()
        self.pump_until(lambda:self.window._close_state=='READY')
        self.assertIsNone(self.session._lease)
        self.assertEqual(delivered,[])

    def test_recovery_failure_leaves_window_and_session_open(self):
        self.window.writer.editor.setPlainText('Synthetic unsaved draft')
        with patch.object(self.window.writer._draft,'preserve',side_effect=OSError('synthetic unavailable')):
            self.window.close();self.app.processEvents()
            self.assertEqual(self.window._close_state,'OPEN')
            self.assertFalse(self.window.bus._stopping)
            self.assertIsNotNone(self.session._lease)
            self.assertTrue(self.window.isVisible())

if __name__=='__main__':unittest.main()
