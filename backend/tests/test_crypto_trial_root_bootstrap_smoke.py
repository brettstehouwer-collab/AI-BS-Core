"""Ten protected locator-bootstrap checks; no account/store admission claim."""
from pathlib import Path
import os
import tempfile
import unittest

import win32security
from tests import test_crypto_trial_root_smoke as fixture
from security.crypto_trial_root import TrialRootLease, TrialRootError


class TrialRootBootstrapSmoke(unittest.TestCase):
    setUp=fixture.TrialRootSmoke.setUp
    close_all=fixture.TrialRootSmoke.close_all
    create=fixture.TrialRootSmoke.create

    def bootstrap(self,path):
        lease=TrialRootLease.open_for_locator(path);self.leases.append(lease);return lease

    def test_01_private_root_bootstrap_measures_identity_without_locator(self):
        created=self.create();path=created.path;identity=created.identity;created.close()
        lease=self.bootstrap(path)
        self.assertEqual(lease.identity,identity);self.assertEqual(lease.path,path)
        self.assertFalse((path/'store.json').exists());lease.validate()

    def test_02_bootstrap_identity_stable_across_close_and_expected_open(self):
        created=self.create();path=created.path;created.close()
        first=self.bootstrap(path);identity=first.identity;first.close()
        second=TrialRootLease.open(path,expected_identity=identity);self.leases.append(second)
        self.assertEqual(second.identity,identity)

    def test_03_existing_nonprivate_directory_refused_without_repair(self):
        path=self.parent/'unprotected';path.mkdir()
        info=win32security.OWNER_SECURITY_INFORMATION|win32security.DACL_SECURITY_INFORMATION
        before=win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(
            win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,info),1,info)
        with self.assertRaises(TrialRootError):self.bootstrap(path)
        after=win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(
            win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,info),1,info)
        self.assertEqual(before,after)

    def test_04_reparse_root_or_ancestor_refused(self):
        created=self.create();path=created.path;created.close()
        rootlink=self.parent/'rootlink';os.symlink(path,rootlink,target_is_directory=True)
        with self.assertRaises(TrialRootError):self.bootstrap(rootlink)
        parentlink=self.parent/'parentlink';os.symlink(self.parent,parentlink,target_is_directory=True)
        with self.assertRaises(TrialRootError):self.bootstrap(parentlink/'root')

    def test_05_os_temp_and_relative_paths_refused(self):
        for path in (Path(tempfile.gettempdir()),Path('relative')):
            with self.subTest(path=str(path)),self.assertRaises(TrialRootError):self.bootstrap(path)

    def test_06_original_open_still_requires_explicit_valid_identity(self):
        created=self.create();path=created.path;created.close()
        with self.assertRaises(TrialRootError):TrialRootLease.open(path,expected_identity=None)
        with self.assertRaises(TypeError):TrialRootLease.open(path)

    def test_07_closed_bootstrap_refuses_file_and_root_validation(self):
        created=self.create();path=created.path;created.close()
        lease=self.bootstrap(path);lease.close()
        with self.assertRaises(TrialRootError):lease.validate()
        with self.assertRaises(TrialRootError):lease.pin_file('store.json')

    def test_08_bootstrap_holds_root_and_ancestors_against_rename(self):
        created=self.create();path=created.path;created.close();lease=self.bootstrap(path)
        with self.assertRaises(OSError):os.rename(path,self.parent/'moved')
        with self.assertRaises(OSError):os.rename(self.parent,self.parent.with_name(self.parent.name+'_moved'))
        lease.validate()

    def test_09_bootstrap_pins_locator_against_replacement(self):
        created=self.create();path=created.path;(path/'store.json').write_text('{}');created.close()
        lease=self.bootstrap(path);identity=lease.pin_file('store.json')
        replacement=self.parent/'replacement';replacement.write_text('{"changed":true}')
        with self.assertRaises(OSError):os.replace(replacement,path/'store.json')
        lease.validate_file('store.json',identity)

    def test_10_post_bootstrap_acl_drift_refused_and_preserved(self):
        created=self.create();path=created.path;created.close();lease=self.bootstrap(path)
        sd=win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,win32security.DACL_SECURITY_INFORMATION)
        acl=sd.GetSecurityDescriptorDacl();acl.AddAccessAllowedAceEx(win32security.ACL_REVISION,3,0x120089,
            win32security.ConvertStringSidToSid('S-1-5-32-545'))
        win32security.SetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION|win32security.PROTECTED_DACL_SECURITY_INFORMATION,None,None,acl,None)
        with self.assertRaises(TrialRootError):lease.validate()
        self.assertEqual(win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION).GetSecurityDescriptorDacl().GetAceCount(),4)


if __name__=='__main__':unittest.main()
