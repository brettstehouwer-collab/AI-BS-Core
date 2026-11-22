"""Explicit draft roots need no home profile; synthetic data and directories only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from native_studio.screenplay_client import DraftSession, ScreenplayError


class ExplicitRecoveryTests(unittest.TestCase):
    def test_explicit_path_never_consults_home(self):
        root = Path(tempfile.gettempdir()) / 'synthetic-explicit-recovery'
        for value in (root, str(root)):
            with self.subTest(kind=type(value).__name__), \
                 patch.object(Path, 'home', side_effect=AssertionError('Home must not be consulted')) as home:
                draft = DraftSession(value)
                self.assertEqual(draft.recovery_root, root)
                self.assertEqual(draft._recovery_store, root.parent)
                home.assert_not_called()

    def test_falsey_pathlike_is_explicit_and_empty_invalid_values_never_default(self):
        class FalseyPath:
            def __bool__(self): return False
            def __fspath__(self): return str(Path(tempfile.gettempdir()) / 'falsey-explicit-root')
        class EmptyPath:
            def __fspath__(self): return ''
        with patch.object(Path, 'home', side_effect=AssertionError('No implicit default')) as home:
            value = FalseyPath()
            self.assertEqual(DraftSession(value).recovery_root, Path(os.fspath(value)))
            self.assertEqual(DraftSession(Path('.')).recovery_root, Path('.'))
            for value in ('', '   ', False, 0, b'', b'explicit-bytes', EmptyPath()):
                with self.subTest(kind=type(value).__name__), self.assertRaises(ScreenplayError):
                    DraftSession(value)
            home.assert_not_called()

    def test_default_recovery_profile_and_parent_are_exactly_preserved(self):
        synthetic_home = Path('C:/Users/Synthetic-Profile-Only')
        expected_profile = hashlib.sha256(str(synthetic_home).casefold().encode('utf-8')).hexdigest()[:16]
        expected = Path(r'C:\AI-BS\saved_data\native_screenplay_recovery') / expected_profile
        for kwargs in ({}, {'recovery_root': None}):
            target = 'native_studio.windows_profile.current_user_profile_directory' if os.name == 'nt' else 'pathlib.Path.home'
            with self.subTest(kwargs=bool(kwargs)), patch(target, return_value=synthetic_home) as home:
                draft = DraftSession(**kwargs)
                self.assertEqual(draft.recovery_root, expected)
                self.assertEqual(draft._recovery_store, expected.parent)
                home.assert_called_once_with()

    @unittest.skipUnless(os.name == 'nt', 'Existing Windows private recovery ACL')
    def test_unicode_preserve_and_fresh_session_readback_without_home_environment(self):
        with tempfile.TemporaryDirectory(prefix='aibs-explicit-draft-') as temporary:
            directory = Path(temporary).resolve()
            self.assertEqual(directory.parent, Path(tempfile.gettempdir()).resolve())
            self.assertTrue(directory.name.startswith('aibs-explicit-draft-'))
            root = directory / 'recovery-é-猫'
            original = dict(project='Synthetic', revision='fixture-r1', content='Original fixture.\n')
            content = 'Unsaved Unicode — é 猫 🐈\nSecond line retained.\n'
            with patch.dict(os.environ):
                for name in ('USERPROFILE', 'HOMEPATH', 'HOMEDRIVE', 'HOME'):
                    os.environ.pop(name, None)
                with patch.object(Path, 'home', side_effect=AssertionError('No home during explicit recovery')) as home:
                    draft = DraftSession(root)
                    draft.load(original)
                    draft.content = content
                    first = draft.preserve()
                    first_bytes = first.read_bytes()
                    payload = json.loads(first_bytes.decode('utf-8'))
                    self.assertEqual(payload['content'], content)
                    self.assertEqual(payload['project'], 'Synthetic')
                    self.assertEqual(payload['revision'], 'fixture-r1')
                    reopened = DraftSession(root)
                    reopened.load(original)
                    reopened.content = payload['content']
                    self.assertTrue(reopened.dirty)
                    self.assertEqual(reopened.content, content)
                    second = reopened.preserve()
                    self.assertNotEqual(first, second)
                    self.assertEqual(first.read_bytes(), first_bytes)
                    self.assertEqual(json.loads(second.read_text(encoding='utf-8'))['content'], content)
                    home.assert_not_called()


if __name__ == '__main__': unittest.main(verbosity=2)
