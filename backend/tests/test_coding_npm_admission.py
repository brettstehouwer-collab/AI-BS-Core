"""Verification admission must not mistake placeholder npm scripts for tests."""
import json
import unittest
from core.coding_vm_inputs import _validate_project_inputs


class NpmAdmissionTests(unittest.TestCase):
    def validate(self, command):
        files = [{'relative_path': 'src/App.jsx', 'role': 'editable'},
                 {'relative_path': 'package.json', 'role': 'dependency'},
                 {'relative_path': 'package-lock.json', 'role': 'dependency'}]
        contents = {'src/App.jsx': b'export default () => <main />;',
                    'package.json': json.dumps({'scripts': {'test': command}}).encode(),
                    'package-lock.json': b'{}'}
        _validate_project_inputs(files, contents, [{'check_id': 'web', 'argv': ['npm', 'run', 'test']}])

    def test_placeholder_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            self.validate('echo "Error: no test specified" && exit 1')

    def test_real_script_is_admitted_without_executing(self):
        self.validate('node --test tests/app.test.mjs')

    def test_missing_script_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'does not define'):
            self.validate('')
