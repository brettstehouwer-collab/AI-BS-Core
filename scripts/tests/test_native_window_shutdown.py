"""Actual close methods on owned inert Qt windows; no MainWindow services."""
import ast, os, sys, threading, time, unittest
from pathlib import Path
from types import SimpleNamespace
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from PyQt6.QtCore import QCoreApplication,QEvent,QObject,QThread,QTimer,pyqtSignal
from PyQt6.QtWidgets import QApplication,QWidget

class Owner(QObject):
    finished=pyqtSignal();drained=pyqtSignal()
    def __init__(self,calls,name):
        super().__init__();self.calls=calls;self.name=name;self.joined=False;self.finish_on_stop=False
    @property
    def is_drained(self):return self.joined
    def shutdown(self,timeout_ms=3000):
        self.calls.append((self.name,timeout_ms))
        if self.finish_on_stop:self.joined=True;self.notify()
        return self.joined
    def wait(self,timeout):
        assert timeout==0
        return self.joined
    def notify(self):(self.drained if self.name=='bus' else self.finished).emit()

class WindowShutdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.calls=[]
        tree=ast.parse((ROOT/'native_studio/app.py').read_text(encoding='utf-8'))
        shell=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MainWindow')
        methods=[n for n in shell.body if isinstance(n,ast.FunctionDef) and n.name in {'closeEvent','_poll_shutdown'}]
        self.assertEqual({n.name for n in methods},{'closeEvent','_poll_shutdown'},'Missing combined native close barrier')
        cls=ast.ClassDef(name='OwnedWindow',bases=[ast.Name(id='QWidget',ctx=ast.Load())],keywords=[],body=methods,decorator_list=[])
        scope={'QWidget':QWidget,'QTimer':QTimer,'allow_exit_process_cleanup':lambda:self.calls.append('final-exit-check') or False}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),'<actual-window-close>','exec'),scope)
        self.window=scope['OwnedWindow']();self.window._subviews_cache={}
        self.window.view_daw=SimpleNamespace(shutdown=lambda:self.calls.append('audio'))
        self.window.bus=Owner(self.calls,'bus');self.window.hub=Owner(self.calls,'sampler')
        self.producer=QTimer(self.window);self.producer.start(1000);self.window.show()
    def tearDown(self):
        if hasattr(self,'window'):
            self.window._close_state='CLOSED';self.window.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.app.processEvents()
    def pump(self,condition):
        end=time.monotonic()+2
        while not condition() and time.monotonic()<end:self.app.processEvents();time.sleep(.002)
        self.assertTrue(condition())
    def joined(self,owner):owner.joined=True;owner.notify()
    def test_sampler_first_cannot_close_with_worker_still_running(self):
        self.assertFalse(self.window.close());self.assertFalse(self.window.isEnabled());self.assertFalse(self.producer.isActive())
        self.joined(self.window.hub);self.app.processEvents();self.assertTrue(self.window.isVisible())
        self.joined(self.window.bus);self.pump(lambda:self.window._close_state=='CLOSED');self.assertFalse(self.window.isVisible())
    def test_bus_first_waits_for_actual_sampler_join_not_just_finished_signal(self):
        self.window.close();self.joined(self.window.bus);self.window.hub.finished.emit()
        self.app.processEvents();self.assertTrue(self.window.isVisible())
        self.joined(self.window.hub);self.pump(lambda:self.window._close_state=='CLOSED')
    def test_repeated_close_and_duplicate_notifications_teardown_once(self):
        self.window._subviews_cache['audio-alias']=self.window.view_daw
        self.window.close();self.window.close()
        self.assertEqual(self.calls.count('audio'),1);self.assertEqual(self.calls.count(('bus',0)),1);self.assertEqual(self.calls.count(('sampler',0)),1)
        self.joined(self.window.hub);self.joined(self.window.bus);self.window.bus.drained.emit();self.window.hub.finished.emit()
        self.pump(lambda:self.window._close_state=='CLOSED');self.window.close()
        self.assertEqual(self.calls.count('final-exit-check'),1)
    def test_completion_inside_stop_request_is_rechecked_after_setup(self):
        self.window.bus.finish_on_stop=self.window.hub.finish_on_stop=True
        self.window.close();self.pump(lambda:self.window._close_state=='CLOSED')
        self.assertEqual(self.calls.count(('bus',0)),1);self.assertEqual(self.calls.count(('sampler',0)),1)
    def test_chat_veto_keeps_editing_and_save_retry_usable_before_teardown(self):
        allowed,draft,saved=[False],['first'],[]
        def flush():
            if not allowed[0]:return False
            saved.append(draft[0]);return True
        view=SimpleNamespace(_chat_recovery=SimpleNamespace(flush_for_close=flush),shutdown=lambda:self.calls.append('chat-stop'))
        self.window._subviews_cache['chat']=view
        self.assertFalse(self.window.close());self.assertEqual(self.calls,[]);self.assertTrue(self.window.isEnabled());self.assertTrue(self.producer.isActive())
        draft[0]='newest unsent';allowed[0]=True;self.window.close()
        self.assertEqual(saved,['newest unsent']);self.assertEqual(self.calls.count('chat-stop'),1)
    def test_both_chat_snapshots_rechecked_after_pending_game_close(self):
        draft,saved,ready,callbacks=['first'],[],[False],[]
        def prepare(callback):callbacks.append(callback);return ready[0]
        def flush():saved.append(draft[0]);return True
        self.window._subviews_cache.update(game_build=SimpleNamespace(prepare_close=prepare,shutdown=lambda:self.calls.append('game-stop')),
            executive=SimpleNamespace(_chat_recovery=SimpleNamespace(flush_for_close=flush),shutdown=lambda:None),
            chat=SimpleNamespace(_chat_recovery=SimpleNamespace(flush_for_close=flush),shutdown=lambda:None))
        self.assertFalse(self.window.close());self.assertEqual(self.calls,[]);self.assertTrue(self.window.isEnabled())
        draft[0]='edited while game draining';ready[0]=True;callbacks[0]();self.app.processEvents()
        self.assertEqual(saved,['edited while game draining']*2);self.assertFalse(self.window.isEnabled())
    def test_real_worker_and_sampler_keep_GUI_responsive_until_both_join(self):
        from native_studio.engine import EngineBus
        entered,release=threading.Event(),threading.Event();sample_entered,sample_release=threading.Event(),threading.Event()
        class Sampler(QThread):
            def run(self):sample_entered.set();sample_release.wait(5)
            def shutdown(self,timeout_ms=2000):return bool(self.wait(timeout_ms))
        bus=EngineBus(max_threads=1);sampler=Sampler();self.window.bus=bus;self.window.hub=sampler
        def work():entered.set();release.wait(5)
        heartbeat=QTimer();beats=[];heartbeat.setInterval(5);heartbeat.timeout.connect(lambda:beats.append(True))
        try:
            bus.submit(work);sampler.start();self.assertTrue(entered.wait(1) and sample_entered.wait(1));heartbeat.start()
            before=time.monotonic();self.assertFalse(self.window.close());self.assertLess(time.monotonic()-before,.2)
            self.pump(lambda:len(beats)>=4);self.assertTrue(self.window.isVisible())
            sample_release.set();self.assertTrue(sampler.wait(1000));self.app.processEvents();self.assertTrue(self.window.isVisible())
            release.set();self.pump(lambda:self.window._close_state=='CLOSED');self.assertTrue(bus.is_drained)
        finally:
            release.set();sample_release.set();heartbeat.stop();self.assertTrue(sampler.wait(2000));self.assertTrue(bus.shutdown(2000))

    def test_component_teardown_failure_retains_window_instead_of_accepting_close(self):
        def failed():raise RuntimeError('synthetic teardown failure')
        self.window._subviews_cache['failing-component']=SimpleNamespace(shutdown=failed)
        self.window.close();self.joined(self.window.bus);self.joined(self.window.hub)
        self.app.processEvents()
        self.assertEqual(self.window._close_state,'STOPPING')
        self.assertEqual(self.window._shutdown_error,'RuntimeError')
        self.assertTrue(self.window.isVisible())
        self.assertNotIn('final-exit-check',self.calls)

    def test_process_and_terminal_owners_both_gate_native_window_destruction(self):
        batch = SimpleNamespace(is_drained=False, shutdown=lambda:self.calls.append('batch-stop'),
                                snapshot=lambda:{'drain_failed':False})
        terminal = SimpleNamespace(is_drained=False, shutdown=lambda:self.calls.append('terminal-stop'))
        self.window.bus._process_batch_controller = batch
        self.window.bus._native_terminal = terminal
        self.window.close()
        self.joined(self.window.bus);self.joined(self.window.hub)
        self.app.processEvents()
        self.assertEqual(self.window._close_state,'STOPPING')
        self.assertIn('batch-stop',self.calls);self.assertIn('terminal-stop',self.calls)
        batch.is_drained=True
        self.window._poll_shutdown()
        self.assertEqual(self.window._close_state,'STOPPING')
        terminal.is_drained=True
        self.window._poll_shutdown()
        self.pump(lambda:self.window._close_state=='CLOSED')

    def test_unproved_owned_process_cleanup_retains_attention_state(self):
        messages=[]
        self.window.statusBar=lambda:SimpleNamespace(showMessage=messages.append)
        self.window.bus._process_batch_controller=SimpleNamespace(
            is_drained=False,shutdown=lambda:None,snapshot=lambda:{'drain_failed':True})
        self.window.close()
        self.joined(self.window.bus);self.joined(self.window.hub)
        self.app.processEvents()
        self.assertEqual(self.window._close_state,'STOPPING')
        self.assertIn('not confirmed',self.window._shutdown_error)
        self.assertTrue(messages)
        self.assertTrue(self.window.isVisible())

if __name__=='__main__':unittest.main(verbosity=2)
