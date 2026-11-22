"""Fifteen owned NTFS lease checks; fixtures stay outside OS temp and originals."""
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest
from uuid import uuid4

import win32security
from security.crypto_trial_root import TrialRootLease, TrialRootError


class TrialRootSmoke(unittest.TestCase):
    def setUp(self):
        self.parent=Path('C:/AI-BS/backups')/('crypto_runtime_root_fixtures_'+uuid4().hex)
        self.parent.mkdir(exist_ok=False)
        self.leases=[]
        self.addCleanup(self.close_all)

    def close_all(self):
        for lease in reversed(self.leases):lease.close()

    def create(self, name='root'):
        lease=TrialRootLease.create(self.parent,name);self.leases.append(lease);return lease

    def reopen(self,path,identity):
        lease=TrialRootLease.open(path,expected_identity=identity);self.leases.append(lease);return lease

    def test_01_create_measured_identity_and_sid(self):
        lease=self.create()
        self.assertIsInstance(lease.path,Path)
        self.assertEqual(len(lease.identity),2)
        self.assertTrue(all(type(value) is int and value>=0 for value in lease.identity))
        self.assertRegex(lease.broker_sid,r'^S-1-5-21-')
        lease.validate()

    def test_02_close_reopen_preserves_root_identity_and_bytes(self):
        lease=self.create();identity=lease.identity;path=lease.path
        (path/'store.json').write_bytes(b'{"synthetic":true}')
        lease.close();reopened=self.reopen(path,identity)
        self.assertEqual(reopened.identity,identity)
        self.assertEqual((path/'store.json').read_bytes(),b'{"synthetic":true}')
        reopened.validate()

    def test_03_wrong_root_identity_refused(self):
        lease=self.create();identity=lease.identity;path=lease.path;lease.close()
        with self.assertRaises(TrialRootError):self.reopen(path,[identity[0],identity[1]+1])
        for invalid in (None,[True,1],[1],['1','2']):
            with self.subTest(invalid=invalid),self.assertRaises(TrialRootError):self.reopen(path,invalid)

    def test_04_create_never_adopts_existing_leaf(self):
        lease=self.create();(lease.path/'store.json').write_text('retained')
        with self.assertRaises(TrialRootError):self.create()
        self.assertEqual((lease.path/'store.json').read_text(),'retained')

    def test_05_production_root_refuses_os_temp(self):
        with self.assertRaises(TrialRootError):TrialRootLease.create(Path(tempfile.gettempdir()),'trial_'+uuid4().hex)

    def test_06_names_and_relative_parent_paths_refused(self):
        for name in ('../escape','a/b','a\\b','root:stream','CON','name.','name '):
            with self.subTest(name=name),self.assertRaises(TrialRootError):self.create(name)
        with self.assertRaises(TrialRootError):TrialRootLease.create(Path('relative'),'root')

    def test_07_context_closes_idempotently_and_validation_then_refuses(self):
        with TrialRootLease.create(self.parent,'context') as lease:lease.validate()
        lease.close()
        with self.assertRaises(TrialRootError):lease.validate()

    def test_08_held_root_cannot_be_renamed(self):
        lease=self.create()
        with self.assertRaises(OSError):os.rename(lease.path,self.parent/'moved')
        lease.validate()

    def test_09_held_ancestor_cannot_be_renamed(self):
        lease=self.create()
        with self.assertRaises(OSError):os.rename(self.parent,self.parent.with_name(self.parent.name+'_moved'))
        lease.validate()

    def test_10_pinned_database_allows_sqlite_writes_but_denies_delete(self):
        lease=self.create();path=lease.path/'accounting.sqlite3';path.touch()
        identity=lease.pin_file('accounting.sqlite3')
        db=sqlite3.connect(path)
        try:
            db.execute('CREATE TABLE synthetic(value INTEGER)');db.execute('INSERT INTO synthetic VALUES(1)');db.commit()
            self.assertEqual(db.execute('SELECT value FROM synthetic').fetchone(),(1,))
        finally:db.close()
        lease.validate_file('accounting.sqlite3',identity)
        with self.assertRaises(OSError):path.unlink()

    def test_11_changed_file_identity_refused_after_reopen(self):
        lease=self.create();path=lease.path/'accounting.sqlite3';path.write_bytes(b'first')
        file_id=lease.pin_file('accounting.sqlite3');root_id=lease.identity;lease.close()
        replacement=self.parent/'replacement';replacement.write_bytes(b'second');os.replace(replacement,path)
        reopened=self.reopen(path.parent,root_id)
        with self.assertRaises(TrialRootError):reopened.validate_file('accounting.sqlite3',file_id)

    def test_12_hardlinks_and_file_reparse_points_refused(self):
        lease=self.create();path=lease.path/'accounting.sqlite3';path.write_bytes(b'original')
        link=lease.path/'second';os.link(path,link)
        with self.assertRaises(TrialRootError):lease.pin_file('accounting.sqlite3')
        link.unlink();path.unlink()
        target=self.parent/'synthetic-target';target.write_bytes(b'target');os.symlink(target,path)
        with self.assertRaises(TrialRootError):lease.pin_file('accounting.sqlite3')

    def test_13_file_names_and_missing_file_state_checked(self):
        lease=self.create()
        for name in ('../accounting.sqlite3','a/b','a\\b','accounting.sqlite3:secret','NUL','a.'):
            with self.subTest(name=name),self.assertRaises(TrialRootError):lease.pin_file(name)
        lease.validate_file('store.json',None,exists=False)
        with self.assertRaises(TrialRootError):lease.pin_file('store.json')
        (lease.path/'store.json').write_text('{}')
        with self.assertRaises(TrialRootError):lease.validate_file('store.json',None,exists=False)

    def test_14_acl_drift_refused_without_repair(self):
        lease=self.create();path=lease.path;identity=lease.identity
        descriptor=win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,win32security.DACL_SECURITY_INFORMATION)
        acl=descriptor.GetSecurityDescriptorDacl();acl.AddAccessAllowedAceEx(win32security.ACL_REVISION,3,0x120089,
            win32security.ConvertStringSidToSid('S-1-5-32-545'))
        win32security.SetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION|win32security.PROTECTED_DACL_SECURITY_INFORMATION,None,None,acl,None)
        with self.assertRaises(TrialRootError):lease.validate()
        lease.close()
        with self.assertRaises(TrialRootError):self.reopen(path,identity)
        self.assertEqual(win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION).GetSecurityDescriptorDacl().GetAceCount(),4)

    def test_15_alternate_stream_and_reparse_ancestor_refused(self):
        lease=self.create();path=lease.path/'accounting.sqlite3';path.write_bytes(b'main')
        Path(str(path)+':synthetic').write_bytes(b'stream')
        with self.assertRaises(TrialRootError):lease.pin_file('accounting.sqlite3')
        target=self.parent/'target';target.mkdir();redirect=self.parent/'redirect';os.symlink(target,redirect,target_is_directory=True)
        with self.assertRaises(TrialRootError):TrialRootLease.create(redirect,'root')


if __name__=='__main__':unittest.main()
