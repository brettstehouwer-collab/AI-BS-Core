"""Pure admission checks only: no Qt, process, network, or model execution."""
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from native_studio import packaged_writer_acceptance as subject


class AdmissionChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root / 'run'
        self.run.mkdir()
        self.guard = patch.object(subject, 'ROOT', self.root)
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def args(self, phase='preserve'):
        return ['--packaged-writer-acceptance', '--native-creative-pipe-bootstrap',
                '--writer-acceptance-phase', phase, '--writer-acceptance-output', str(self.run / phase)]

    def reject(self, argv):
        with self.assertRaises((RuntimeError, SystemExit)):
            subject.parse_options(argv)
        self.assertEqual(list(self.run.iterdir()), [])

    def test_valid_phases(self):
        for phase in subject.PHASES:
            self.assertEqual(subject.parse_options(self.args(phase)).output.name, phase)

    def test_unknown_argument(self):
        self.reject(self.args() + ['--script', 'anything.py'])

    def test_repeated_argument(self):
        self.reject(self.args() + ['--writer-acceptance-phase', 'preserve'])

    def test_missing_bootstrap(self):
        self.reject([x for x in self.args() if x != '--native-creative-pipe-bootstrap'])

    def test_unsupported_phase(self):
        self.reject(self.args('send'))

    def test_relative_output(self):
        args = self.args(); args[-1] = 'preserve'; self.reject(args)

    def test_outside_output(self):
        args = self.args(); args[-1] = str(self.root.parent / 'preserve'); self.reject(args)

    def test_existing_output(self):
        (self.run / 'preserve').mkdir()
        with self.assertRaises(RuntimeError):
            subject.parse_options(self.args())

    def test_wrong_leaf(self):
        args = self.args(); args[-1] = str(self.run / 'wrong'); self.reject(args)

    def test_missing_parent(self):
        args = self.args(); args[-1] = str(self.run / 'missing' / 'preserve'); self.reject(args)
        for project, content in [('other', subject.MARKER), (subject.PROJECT, 'ordinary manuscript'),
                                 (subject.PROJECT, subject.MARKER + 'x' * 65536)]:
            with self.assertRaises(RuntimeError):
                subject.validate_synthetic(project, content)

    def test_receipt_create_only(self):
        subject.receipt(self.run, 'result.json', {'status': 'FAIL'})
        with self.assertRaises(FileExistsError):
            subject.receipt(self.run, 'result.json', {'status': 'PASS'})

    def test_no_top_level_qt_or_gui(self):
        tree = ast.parse(Path(subject.__file__).read_text(encoding='utf8'))
        imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any('PyQt' in ast.unparse(node) for node in imports))


if __name__ == '__main__':
    unittest.main()
