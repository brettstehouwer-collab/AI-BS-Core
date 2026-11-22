"""Actual parser checks on inert source data; no candidate code is evaluated."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from core import coding_syntax as syntax


class SyntaxTests(unittest.TestCase):
    def test_parser_accepts_jsx_and_rejects_invalid_syntax_without_evaluation(self):
        if not syntax.available(): self.skipTest('Installed Node/Babel toolchain unavailable')
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder)/'should-not-exist'
            content = 'require("node:fs").writeFileSync(' + repr(str(marker).replace('\\', '/')) + ', "executed");'
            results = syntax.javascript_checks([
                {'path': 'module.js', 'content': content},
                {'path': 'App.jsx', 'content': 'export default () => <main />;'},
                {'path': 'bad.jsx', 'content': 'export default () => <main;'}])
            self.assertEqual([r['status'] for r in results], ['passed', 'passed', 'failed'])
            self.assertFalse(marker.exists())
            self.assertTrue(all(len(r['parser_sha256']) == 64 for r in results))

    def test_unavailable_parser_does_not_become_success(self):
        with patch.object(syntax.shutil, 'which', return_value=None):
            checks = syntax.javascript_checks([{'path': 'a.js', 'content': 'const x = 1;'}])
        self.assertEqual(checks[0]['status'], 'not_run')

    def test_limits_reject_before_parser_process(self):
        if not syntax.available(): self.skipTest('Installed Node/Babel toolchain unavailable')
        with patch.object(syntax.subprocess, 'run', side_effect=AssertionError('Must not spawn')):
            with self.assertRaises(ValueError):
                syntax.javascript_checks([{'path': 'a.js', 'content': 'x'*66000}])

    def test_node_options_and_secrets_not_inherited(self):
        class Result:
            returncode = 0
            stdout = b'[{"path":"a.js","kind":"syntax","status":"passed"}]'
        if not syntax.available(): self.skipTest('Installed Node/Babel toolchain unavailable')
        with patch.dict('os.environ', {'NODE_OPTIONS': '--require=bad.js', 'API_KEY': 'synthetic'}), \
                patch.object(syntax.subprocess, 'run', return_value=Result()) as run:
            syntax.javascript_checks([{'path': 'a.js', 'content': 'const x = 1;'}])
        self.assertNotIn('NODE_OPTIONS', run.call_args.kwargs['env'])
        self.assertNotIn('API_KEY', run.call_args.kwargs['env'])
