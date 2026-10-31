"""Exercise the actual close handler without constructing service-backed UI."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[2]


class WindowShutdownTests(unittest.TestCase):
    def pending_fixture(self, running=True):
        tree=ast.parse((ROOT/'native_studio/app.py').read_text(encoding='utf-8'))
        shell=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MainWindow')
        methods=[n for n in shell.body if isinstance(n,ast.FunctionDef)
                 and n.name in {'closeEvent','_finish_sampler_shutdown'}]
        calls=[];scheduled=[];callbacks=[]
        scope={'allow_exit_process_cleanup':lambda:False,
               'QTimer':SimpleNamespace(singleShot=lambda delay,fn:scheduled.append(fn)),
               'super':lambda:SimpleNamespace(closeEvent=lambda event:calls.append('closed'))}
        exec(compile(ast.Module(body=methods,type_ignores=[]),'<actual-pending-close>','exec'),scope)
        hub=SimpleNamespace(shutdown=Mock(return_value=False),
                            isRunning=Mock(return_value=running),
                            finished=SimpleNamespace(connect=Mock(side_effect=callbacks.append)))
        window=SimpleNamespace(view_daw=SimpleNamespace(shutdown=lambda:calls.append('audio')),
                               _subviews_cache={},hub=hub,
                               bus=SimpleNamespace(shutdown=lambda:calls.append('workers')),
                               close=Mock())
        window._finish_sampler_shutdown=lambda:scope['_finish_sampler_shutdown'](window)
        return scope,window,calls,scheduled,callbacks

    def test_pending_sampler_defers_window_and_worker_destruction(self):
        scope,window,calls,scheduled,callbacks=self.pending_fixture()
        event=Mock()
        scope['closeEvent'](window,event)
        event.ignore.assert_called_once()
        self.assertEqual(calls,['audio'])
        self.assertEqual(len(callbacks),1)
        self.assertEqual(scheduled,[])
        window.close.assert_not_called()

    def test_finish_race_schedules_close_once(self):
        scope,window,calls,scheduled,callbacks=self.pending_fixture(running=False)
        scope['closeEvent'](window,Mock())
        self.assertEqual(len(scheduled),1)
        scheduled[0]()
        for callback in callbacks:callback()
        window.close.assert_called_once()

    def test_repeated_pending_close_does_not_repeat_wait_or_connections(self):
        scope,window,calls,scheduled,callbacks=self.pending_fixture()
        scope['closeEvent'](window,Mock())
        repeated=Mock()
        scope['closeEvent'](window,repeated)
        repeated.ignore.assert_called_once()
        window.hub.shutdown.assert_called_once()
        self.assertEqual(len(callbacks),1)

    def test_cached_chat_flush_precedes_worker_shutdown(self):
        tree=ast.parse((ROOT/'native_studio/app.py').read_text(encoding='utf-8'))
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='closeEvent')
        calls=[]
        scope={'allow_exit_process_cleanup':lambda:False,
               'super':lambda:SimpleNamespace(closeEvent=lambda event:calls.append('closed'))}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<actual-window-close>','exec'),scope)
        part=lambda name:SimpleNamespace(shutdown=lambda:calls.append(name))
        window=SimpleNamespace(view_daw=part('audio'),_subviews_cache={'chat':part('chat-flushed'),'plain':object()},
                               hub=part('hub'),bus=part('workers'))
        scope['closeEvent'](window,object())
        self.assertEqual(calls,['audio','chat-flushed','hub','workers','closed'])


if __name__=='__main__':unittest.main()
