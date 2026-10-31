"""Offline DACL/JSON fixtures; never modify the real IPC directory."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace,ModuleType
import sys
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[2]

class PrivateBroadcastIpc207Tests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('_audit_private_ipc207',ROOT/'native_studio/broadcast_ipc.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)

    def descriptor(self,owner='user',protected=True,aces=None):
        from types import SimpleNamespace
        items=aces if aces is not None else [((0,3),0x1f01ff,'user'),((0,3),0x1f01ff,'system')]
        return SimpleNamespace(GetSecurityDescriptorOwner=lambda:owner,
            GetSecurityDescriptorControl=lambda:((0x1000 if protected else 0),1),
            GetSecurityDescriptorDacl=lambda:SimpleNamespace(GetAceCount=lambda:len(items),GetAce=lambda i:items[i]))

    def test_private_owner_system_only_protected_dacl_is_accepted(self):
        self.module._validate_descriptor(self.descriptor(),'user','system',sid_text=str)

    def test_foreign_owner_unprotected_or_broad_acl_is_rejected(self):
        for sd in [self.descriptor(owner='other'),self.descriptor(protected=False),
                   self.descriptor(aces=[((0,3),0x1f01ff,'user'),((0,3),0x1f01ff,'Authenticated Users')]),
                   self.descriptor(aces=[((0,19),0x1f01ff,'user'),((0,3),0x1f01ff,'system')]),
                   self.descriptor(aces=[((0,3),0x120089,'user'),((0,3),0x1f01ff,'system')])]:
            with self.subTest(sd=sd):
                with self.assertRaises(ValueError):self.module._validate_descriptor(sd,'user','system',sid_text=str)

    def test_null_empty_dacl_cannot_be_certified(self):
        with self.assertRaises(ValueError):self.module._validate_descriptor(self.descriptor(aces=[]),'user','system',sid_text=str)

    def test_json_duplicate_nonfinite_and_oversize_are_rejected(self):
        for data in [b'{"version":2,"version":1}',b'{"value":NaN}',b'[]',b'{"x":"'+b'a'*16384+b'"}']:
            with self.subTest(data=data[:25]):
                with self.assertRaises(ValueError):self.module._decode_json(data,16384)
        self.assertEqual(self.module._decode_json(b'{"version":2}',16384),{'version':2})

    def test_private_namespace_does_not_reuse_existing_application_parent(self):
        shell_module=ModuleType('win32com.shell')
        folder=Mock(side_effect=lambda _hwnd,kind,*args:'C:/Users/Fixture' if kind==40 else 'C:/Users/Fixture/AppData/Local/Packages/VirtualCache')
        shell_module.shell=SimpleNamespace(SHGetFolderPath=folder)
        shell_module.shellcon=SimpleNamespace(CSIDL_LOCAL_APPDATA=28,CSIDL_PROFILE=40)
        with patch.dict(sys.modules,{'win32com.shell':shell_module}): paths=self.module.ipc_paths()
        self.assertEqual(paths['status'],Path('C:/Users/Fixture/.aibs-private/BroadcastIPC/broadcast_secondary_status.json'))
        self.assertEqual(folder.call_args.args[1],40)

    def test_profile_ipc_fixture_resolves_to_same_physical_location(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix='profile_ipc208_') as folder:
            profile=Path(folder);shell_module=ModuleType('win32com.shell')
            shell_module.shell=SimpleNamespace(SHGetFolderPath=lambda _hwnd,kind,*args:str(profile) if kind==40 else str(profile/'VirtualizedLocalCache'))
            shell_module.shellcon=SimpleNamespace(CSIDL_LOCAL_APPDATA=28,CSIDL_PROFILE=40)
            with patch.dict(sys.modules,{'win32com.shell':shell_module}): path=self.module.ipc_paths()['status']
            expected=profile/'.aibs-private/BroadcastIPC/broadcast_secondary_status.json'
            self.assertEqual(path,expected);self.assertEqual(path.resolve(),expected.absolute())

    def test_existing_foreign_parent_is_never_taken_over(self):
        file_api=ModuleType('win32file');file_api.CreateDirectory=Mock()
        security=ModuleType('win32security');security.SetNamedSecurityInfo=Mock()
        path=SimpleNamespace(exists=lambda:True,is_dir=lambda:True)
        with patch.dict(sys.modules,{'win32file':file_api,'win32security':security}), \
             patch.object(self.module,'_not_redirected'),patch.object(self.module,'_security_attributes',return_value=(None,None,'current-user')), \
             patch.object(self.module,'_descriptor',return_value=SimpleNamespace(GetSecurityDescriptorOwner=lambda:'foreign-owner')):
            with self.assertRaisesRegex(ValueError,'IPC_OWNER_MISMATCH'):self.module._secure_directory(path)
        file_api.CreateDirectory.assert_not_called();security.SetNamedSecurityInfo.assert_not_called()

class PrivateConnectionDiagnostic208Tests(unittest.TestCase):
    def test_storage_failure_returns_false_without_unhandled_exception_or_vault_read(self):
        from native_studio import local_connection as connection,broadcast_ipc as ipc
        from native_studio import screenplay_client
        import tempfile,os
        with tempfile.TemporaryDirectory(prefix='diagnostic208_') as folder, \
             patch.dict(os.environ,{'LOCALAPPDATA':folder}), \
             patch.object(screenplay_client,'_private_recovery_directory',side_effect=RuntimeError('fixture storage error')), \
             patch.object(ipc,'_secure_directory',side_effect=RuntimeError('fixture storage error')), \
             patch.object(connection,'connection_diagnostics',side_effect=AssertionError('diagnostic/vault accessed before storage')):
            self.assertFalse(connection.write_connection_diagnostic())

    def test_diagnostic_uses_profile_private_sibling_and_preserves_no_credentials(self):
        from native_studio import local_connection as connection,broadcast_ipc as ipc
        from native_studio import screenplay_client
        import tempfile,os
        with tempfile.TemporaryDirectory(prefix='diagnostic_profile208_') as folder:
            root=Path(folder)/'.aibs-private'
            def make_private(path):path.mkdir(parents=True,exist_ok=True)
            with patch.object(ipc,'private_profile_root',return_value=root,create=True), \
                 patch.object(ipc,'_secure_directory',side_effect=make_private) as secure, \
                 patch.object(screenplay_client,'_private_recovery_directory',side_effect=AssertionError('legacy appdata store')), \
                 patch.dict(os.environ,{'LOCALAPPDATA':str(Path(folder)/'VirtualizedLocalCache')}), \
                 patch.object(connection,'connection_diagnostics',return_value={'available':True,'stage':'ready'}):
                self.assertTrue(connection.write_connection_diagnostic())
            self.assertEqual([call.args[0] for call in secure.call_args_list],[root,root/'NativeDiagnostics'])
            records=list((root/'NativeDiagnostics').glob('local_connection_*.json'))
            self.assertEqual(len(records),1)
            self.assertNotIn('VirtualizedLocalCache',str(records[0]))

if __name__=='__main__':unittest.main()
