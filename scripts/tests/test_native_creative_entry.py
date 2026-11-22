"""Pre-GUI entry contracts; no application, credentials or live listener."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
from native_studio import native_creative_entry as entry


class NativeEntry(unittest.TestCase):
    def test_ordinary_argv_never_bootstraps_or_opens_writer(self):
        writer=Mock()
        with patch.object(entry,'bootstrap_native_session') as bootstrap:
            self.assertEqual(entry.main(['studio.exe'],run_writer=writer),2)
        bootstrap.assert_not_called();writer.assert_not_called()

    def test_bootstrap_failure_never_opens_editor(self):
        writer=Mock()
        with patch.object(entry,'bootstrap_native_session',side_effect=RuntimeError('private-fixture')):
            self.assertEqual(entry.main(['studio.exe','--native-creative-bootstrap'],stream=object(),run_writer=writer),2)
        writer.assert_not_called()

    def test_verified_session_is_passed_then_closed_on_normal_exit(self):
        session=Mock();packet=object();order=[]
        def writer(s,p):
            self.assertIs(s,session);self.assertIs(p,packet);order.append('writer');return 0
        with patch.object(entry,'bootstrap_native_session',side_effect=lambda *a:(order.append('bootstrap') or (session,packet))):
            self.assertEqual(entry.main(['studio.exe','--native-creative-bootstrap'],stream=object(),run_writer=writer),0)
        self.assertEqual(order,['bootstrap','writer']);session.close.assert_called_once()

    def test_explicit_pipe_flag_uses_same_scoped_writer_entry(self):
        session=Mock();packet=object();writer=Mock(return_value=0)
        with patch.object(entry,'bootstrap_native_session',return_value=(session,packet)) as bootstrap:
            self.assertEqual(entry.main(['studio.exe','--native-creative-pipe-bootstrap'],stream=object(),run_writer=writer),0)
        bootstrap.assert_called_once();writer.assert_called_once_with(session,packet)
        session.close.assert_called_once()

    def test_writer_failure_closes_session_without_fallback(self):
        session=Mock()
        with patch.object(entry,'bootstrap_native_session',return_value=(session,object())):
            self.assertEqual(entry.main(['studio.exe','--native-creative-bootstrap'],stream=object(),run_writer=Mock(side_effect=RuntimeError('private'))),2)
        session.close.assert_called_once()

    def test_app_branch_precedes_qt_and_normal_main_call(self):
        source=Path('native_studio/app.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        branch=next(n for n in tree.body if isinstance(n,ast.If) and '--native-creative-bootstrap' in ast.unparse(n.test))
        qt=next(n for n in tree.body if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('PyQt6'))
        self.assertLess(branch.lineno,qt.lineno)
        self.assertIn('sys.exit(native_creative_main(sys.argv))',ast.unparse(branch))
