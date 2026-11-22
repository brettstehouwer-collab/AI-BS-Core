"""Metadata-only protected preparation selection; synthetic credentials/transports."""
import json
from pathlib import Path
import unittest
from uuid import uuid4
from unittest.mock import patch
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
from core.crypto_credential_preparation_registry import CredentialPreparationRegistry

NOW=1794783600000


class CredentialPreparationRegistrySmoke(unittest.TestCase):
    def setUp(self):
        self.parent=Path('C:/AI-BS/backups')/('crypto_preparation_registry_fixtures_'+uuid4().hex)
        self.parent.mkdir();self.token=bind_memory_principal('local_admin')
        self.addCleanup(lambda:reset_memory_principal(self.token) if self.token is not None else None);self.owners=[]
        self.addCleanup(lambda:[x.close() for x in reversed(self.owners)])

    def capability(self,trial=None,key='SYNTHETIC_KEY',secret='SYNTHETIC_SECRET'):
        from core.crypto_credential_preparation import read_credential_preparation
        def transport(url,raw):
            body=json.loads(raw)
            return 200,json.dumps({'id':body['id'],'method':body['method'],'code':0,
                'result':{'this_account':{'uuid':'11111111-1111-4111-8111-111111111111','hierarchy':'MASTER'}}}).encode()
        ticks=iter([NOW,NOW+1,NOW+2])
        return read_credential_preparation(local_trial_uuid=trial or str(uuid4()),
            credential_provider=lambda:(key,secret),private_sink=lambda value:None,
            qualification_transport=transport,clock_ms=lambda:next(ticks))

    def args(self,cap,**changes):
        record=cap.to_record();args=dict(preparation=cap,
            credential_partition_sha256=record['credential_partition_sha256'],
            credential_generation_sha256=record['credential_generation_sha256'],now_ms=NOW+2,allow_test=True)
        args.update(changes);return args

    def create(self,cap=None,**changes):
        cap=cap or self.capability();owner=CredentialPreparationRegistry.create(self.parent,'index',**self.args(cap,**changes))
        self.owners.append(owner);return owner,cap

    def test_01_new_index_metadata_only_all_held(self):
        owner,_=self.create();answer=owner.review()
        self.assertFalse(answer['ready_for_live']);self.assertFalse(answer['live_dispatch_enabled']);self.assertEqual(answer['orders_sent'],0)
        self.assertEqual({p.name for p in owner.path.iterdir()},{'selection.json','registry.lock'})

    def test_02_restart_exact_identity_and_selection(self):
        owner,cap=self.create();path,identity=owner.path,owner.identity;before=owner.review();owner.close()
        reopened=CredentialPreparationRegistry.open(path,expected_identity=identity,allow_test=True);self.owners.append(reopened)
        self.assertEqual(reopened.review(),before);self.assertEqual(reopened.register(**self.args(cap)),before)

    def test_03_same_trial_idempotent_bytes_unchanged(self):
        owner,cap=self.create();before=(owner.path/'selection.json').read_bytes()
        self.assertEqual(owner.register(**self.args(cap)),owner.review())
        self.assertEqual((owner.path/'selection.json').read_bytes(),before)

    def test_04_different_trial_cannot_reset(self):
        owner,_=self.create();before=(owner.path/'selection.json').read_bytes()
        with self.assertRaises(Exception):owner.register(**self.args(self.capability()))
        self.assertEqual((owner.path/'selection.json').read_bytes(),before)

    def test_05_anonymous_denied_before_root_io(self):
        cap=self.capability();args=self.args(cap)
        reset_memory_principal(self.token);self.token=None
        with patch('security.crypto_trial_root.TrialRootLease.create') as create:
            with self.assertRaises(PermissionError):CredentialPreparationRegistry.create(self.parent,'index',**args)
            create.assert_not_called()

    def test_06_wrong_owner_cannot_read_or_reopen(self):
        owner,_=self.create();path,identity=owner.path,owner.identity
        token=bind_memory_principal('firebase:test:other-user')
        try:
            with self.assertRaises(PermissionError):owner.review()
            owner.close()
            with self.assertRaises(PermissionError):CredentialPreparationRegistry.open(path,expected_identity=identity,allow_test=True)
        finally:reset_memory_principal(token)

    def test_07_different_partition_refused(self):
        owner,_=self.create()
        with self.assertRaises(Exception):owner.register(**self.args(self.capability(key='SYNTHETIC_OTHER_KEY')))

    def test_08_rotated_secret_generation_refused(self):
        owner,cap=self.create();other=self.capability(trial=cap.to_record()['local_trial_uuid'],secret='SYNTHETIC_ROTATED_SECRET')
        with self.assertRaises(Exception):owner.register(**self.args(other))

    def test_09_serialized_record_is_not_issued_capability(self):
        cap=self.capability();args=self.args(cap);args['preparation']=cap.to_record()
        with self.assertRaises(Exception):CredentialPreparationRegistry.create(self.parent,'index',**args)
        self.assertFalse((self.parent/'index').exists())

    def test_10_test_capability_never_actual_mode(self):
        with self.assertRaises(Exception):self.create(allow_test=False)
        self.assertFalse((self.parent/'index').exists())

    def test_11_stale_capability_cannot_register_but_dated_review_allowed(self):
        owner,cap=self.create()
        with self.assertRaises(Exception):owner.register(**self.args(cap,now_ms=NOW+86400000))
        self.assertFalse(owner.review()['fresh_authority'])

    def test_12_corrupt_or_missing_record_never_autoheals(self):
        owner,_=self.create();path,identity=owner.path,owner.identity;owner.close()
        record=path/'selection.json';record.write_bytes(b'{}')
        with self.assertRaises(Exception):CredentialPreparationRegistry.open(path,expected_identity=identity,allow_test=True)
        self.assertEqual(record.read_bytes(),b'{}');record.unlink()
        with self.assertRaises(Exception):CredentialPreparationRegistry.open(path,expected_identity=identity,allow_test=True)
        self.assertFalse(record.exists())

    def test_13_identity_mismatch_and_existing_root_refuse(self):
        owner,cap=self.create();identity=owner.identity;path=owner.path;owner.close()
        with self.assertRaises(Exception):CredentialPreparationRegistry.open(path,expected_identity=[identity[0],identity[1]+1],allow_test=True)
        with self.assertRaises(Exception):CredentialPreparationRegistry.create(self.parent,'index',**self.args(cap))
        from core.crypto_credential_preparation_registry import _admit_path, _CANONICAL_ROOT
        actual={'scope':'VERIFIED_CREDENTIAL_PREPARATION_ONLY'}
        for path,override in ((self.parent/'different',False),(self.parent/'different',True),(_CANONICAL_ROOT,True)):
            with self.assertRaises(Exception):_admit_path(path,actual,override)
        with self.assertRaises(Exception):_admit_path(_CANONICAL_ROOT,{'scope':'TEST_CREDENTIAL_PREPARATION_ONLY'},True)

    def test_14_exclusive_owner_and_closed_object(self):
        owner,_=self.create()
        with self.assertRaises(Exception):CredentialPreparationRegistry.open(owner.path,expected_identity=owner.identity,allow_test=True)
        owner.close()
        with self.assertRaises(Exception):owner.review()

    def test_15_digests_and_raw_identifiers_never_public(self):
        owner,cap=self.create();answer=json.dumps(owner.review());record=cap.to_record()
        for key in ('credential_partition_sha256','credential_generation_sha256','local_trial_uuid','receipt_sha256','principal'):
            self.assertNotIn(record[key],answer)
        self.assertIsNone(owner.review()['exchange_account_id']);self.assertFalse(owner.review()['account_identity_verified'])


if __name__=='__main__':unittest.main()
