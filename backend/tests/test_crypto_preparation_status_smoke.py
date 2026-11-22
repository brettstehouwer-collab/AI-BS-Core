"""Fifteen new closed preparation-status checks; protected TEST fixtures only."""
from contextvars import Context
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from core.crypto_preparation_status import PreparationStatusReader,validate_preparation_status,preparation_status
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from tests.test_crypto_held_preparation_admission_smoke import HeldPreparationAdmissionSmoke as Fixture

FIELDS={'status','test_only','fresh_authority','local_seed_allocated','external_funds_reserved',
    'account_identity_verified','native_order_accepted','live_dispatch_enabled','ready_for_live','orders_sent'}


class PreparationStatusSmoke(unittest.TestCase):
    def setUp(self):
        self.fixture=Fixture('test_01_success_is_local_seed_only_and_never_dispatches')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def reader(self,**changes):
        args=dict(active_registry=self.fixture.registry,allow_test=True);args.update(changes)
        return PreparationStatusReader(**args)

    def test_01_anonymous_denied_without_disk_io(self):
        reader=self.reader()
        with patch('pathlib.Path.lstat',side_effect=AssertionError('No anonymous disk IO')):
            answer=Context().run(reader.status)
        self.assertEqual(answer,preparation_status('denied'))

    def test_02_missing_root_is_not_registered_without_creation(self):
        root=self.fixture.parent/'missing-index'
        answer=PreparationStatusReader(root=root,allow_test=True).status()
        self.assertEqual(answer,preparation_status('not_registered'));self.assertFalse(root.exists())

    def test_03_selected_metadata_only_is_dated_not_seeded(self):
        answer=self.reader().status();self.assertEqual(answer,preparation_status('selected',test_only=True))
        self.assertFalse(answer['fresh_authority']);self.assertFalse(answer['local_seed_allocated'])

    def test_04_existing_held_runtime_is_dated_and_seed_flagged_only(self):
        runtime=self.fixture.create()
        answer=self.reader(active_runtime=runtime).status()
        self.assertEqual(answer,preparation_status('held_preparation',test_only=True))
        self.assertTrue(answer['local_seed_allocated']);self.assertFalse(answer['external_funds_reserved'])

    def test_05_active_registry_supplies_trusted_root_when_omitted(self):
        reader=PreparationStatusReader(active_registry=self.fixture.registry,allow_test=True)
        self.assertEqual(reader.status()['status'],'selected')
        self.assertFalse((self.fixture.registry.path/'held-runtime').exists())

    def test_06_other_verified_principal_is_denied(self):
        token=bind_memory_principal('firebase:project:other-user')
        try:self.assertEqual(self.reader().status(),preparation_status('denied'))
        finally:reset_memory_principal(token)

    def test_07_explicit_root_cannot_override_active_registry_selection(self):
        answer=self.reader(root=self.fixture.parent/'different-index').status()
        self.assertEqual(answer,preparation_status('unavailable'))
        self.assertFalse((self.fixture.parent/'different-index').exists())

    def test_08_custom_actual_and_canonical_test_modes_refuse_without_opening(self):
        cases=(dict(root=self.fixture.registry.path,allow_test=False),
            dict(root=Path('C:/AI-BS/saved_data/crypto_credential_preparation_registry'),allow_test=True))
        for args in cases:
            with self.subTest(args=args),patch('pathlib.Path.lstat',side_effect=AssertionError('Mode refusal before disk')):
                self.assertEqual(PreparationStatusReader(**args).status(),preparation_status('unavailable'))

    def test_09_corrupt_selection_is_unavailable_without_rewrite(self):
        path=self.fixture.registry.path/'selection.json';raw=path.read_bytes()+b' '
        path.write_bytes(raw)
        self.assertEqual(self.reader().status(),preparation_status('unavailable'))
        self.assertEqual(path.read_bytes(),raw)

    def test_10_missing_held_database_refuses_without_empty_reinitialization(self):
        runtime=self.fixture.create();root=runtime.root;runtime.close();db=root/'accounting.sqlite3'
        db.rename(root/'accounting.sqlite3.retained')
        self.assertEqual(self.reader().status(),preparation_status('unavailable'))
        self.assertFalse(db.exists())

    def test_11_partial_marker_without_child_is_unavailable_not_selected(self):
        marker=self.fixture.registry.path/'held-runtime-binding.json';marker.write_bytes(b'{}')
        self.assertEqual(self.reader().status(),preparation_status('unavailable'))
        self.assertEqual(marker.read_bytes(),b'{}');self.assertFalse((self.fixture.registry.path/'held-runtime').exists())
        other=Fixture('test_01_success_is_local_seed_only_and_never_dispatches')
        other.setUp();self.addCleanup(other.doCleanups)
        child=other.registry.path/'held-runtime';child.mkdir()
        answer=PreparationStatusReader(active_registry=other.registry,allow_test=True).status()
        self.assertEqual(answer,preparation_status('unavailable'))
        self.assertFalse((other.registry.path/'held-runtime-binding.json').exists())

    def test_12_borrowed_active_owners_are_never_closed(self):
        runtime=self.fixture.create();registry=self.fixture.registry
        self.assertEqual(self.reader(active_runtime=runtime).status()['status'],'held_preparation')
        self.assertFalse(registry._closed);self.assertFalse(runtime._closed)
        self.assertFalse(runtime.status()['ready_for_live']);self.assertFalse(registry.review()['fresh_authority'])

    def test_13_closed_handles_reopen_existing_held_state_without_reviving_owners(self):
        runtime=self.fixture.create();registry=self.fixture.registry
        reader=self.reader(active_runtime=runtime);runtime.close();registry.close()
        self.assertEqual(reader.status(),preparation_status('held_preparation',test_only=True))
        self.assertTrue(runtime._closed);self.assertTrue(registry._closed)

    def test_14_contract_rejects_extra_fields_unsafe_flags_and_bad_types(self):
        valid=preparation_status('selected',test_only=True)
        cases=[dict(valid,root='PRIVATE_ROOT'),dict(valid,orders_sent=False),dict(valid,orders_sent=1),
            dict(valid,ready_for_live=True),dict(valid,native_order_accepted=True),dict(valid,fresh_authority=True),
            dict(valid,test_only='true'),dict(valid,status='unknown'),dict(valid,local_seed_allocated=True)]
        for value in cases:
            with self.subTest(keys=tuple(value)),self.assertRaises(ValueError):validate_preparation_status(value)
        self.assertEqual(validate_preparation_status(valid),valid)
        self.assertIsNot(validate_preparation_status(valid),valid)

    def test_15_public_reply_has_no_financial_or_identity_fields(self):
        self.fixture.create();answer=self.reader().status();encoded=json.dumps(answer)
        self.assertEqual(set(answer),FIELDS)
        for secret in (str(self.fixture.registry.path),self.fixture.trial,'local_admin','SYNTHETIC_KEY','SYNTHETIC_SECRET'):
            self.assertNotIn(secret,encoded)
        self.assertEqual(answer['orders_sent'],0);self.assertFalse(answer['live_dispatch_enabled'])


if __name__=='__main__':unittest.main()

