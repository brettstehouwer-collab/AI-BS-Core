"""Persistent content branches preserve old progress and reject corrupt publications."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
import hashlib
import json
import os
import shutil
import tempfile
import unittest
import uuid
from unittest.mock import patch
from native_studio.game_engine import saved_play_storage as store


def snapshot(payload=b'canonical-native-content', refs=(), kinds=()):
    return NS(payload=payload, fingerprint=hashlib.sha256(payload).hexdigest(),
        scope=NS(project='BS saved chapter', branch='main', world_id='88c72f4b-6534-4c01-b8de-d06d1264edd6'),
        definition_id='e6c41e3a-1839-458f-b846-4962f40821b5', content_revision=3,
        asset_refs=refs, dependency_kinds=kinds, asset_profile='warm-beginning', export_version=2,
        authored_inspections=False, initial_view_authored=False, opening_workshop_authored=False)


def synthetic_pack(parent, *, kind=0, payload=b'synthetic staged bytes'):
    asset_id = str(uuid.uuid4())
    digest = hashlib.sha256(payload).hexdigest()
    suffix, name = {0: ('.aibmesh', None), 1: ('.aibchar', 'character'), 2: ('.aibaud', 'audio')}[kind]
    filename = digest + suffix
    header = b'AIBCAT 1\n' if kind == 0 else ('AIBCAT 2\n' + name + ' ').encode()
    files = {filename: payload, 'catalog.aibcat': header + f'{asset_id} {digest} {filename}\n'.encode(),
             'LICENSE.txt': b'Synthetic test fixture; no original media.\n', 'provenance.json': b'{"fixture":true}\n'}
    manifest = ('AIBPACK 1\n' if kind == 0 else 'AIBPACK 2\n') + ''.join(
        f'{key} {len(raw)} {hashlib.sha256(raw).hexdigest()}\n' for key, raw in sorted(files.items()))
    pack_digest = hashlib.sha256(manifest.encode()).hexdigest()
    path = parent / pack_digest
    path.mkdir(parents=True)
    for key, raw in files.items():(path / key).write_bytes(raw)
    return NS(asset_id=asset_id, asset_sha256=digest, pack_sha256=pack_digest), path


class SavedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aibs-saved-publish-test-')
        self.project = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def publish(self, snap=None):
        snap = snap or snapshot()
        return store.finish_publication(store.prepare_publication(self.project, snap))

    def test_unchanged_authoring_save_reuses_timeline_and_never_opens_or_resets_db(self):
        first = self.publish()
        data = b'opaque retained gameplay save; Python must never decode or replace it'
        first.database_path.write_bytes(data)
        (first.slot_directory / 'world.sqlite-wal').write_bytes(b'owned WAL')
        # Per-invocation authoring checkpoint/epoch/revision is deliberately not
        # content identity, so an unchanged re-Save does not fork/reset progress.
        second_snapshot = snapshot()
        second_snapshot.checkpoint_id = str(uuid.uuid4())
        second_snapshot.generation = 995
        second_snapshot.revision = 99
        second = self.publish(second_snapshot)
        self.assertTrue(second.reused_publication and second.reused_slot)
        self.assertEqual(first.timeline_id, second.timeline_id)
        self.assertEqual(first.content_directory, second.content_directory)
        self.assertEqual(first.database_path.read_bytes(), data)
        self.assertEqual((first.slot_directory / 'world.sqlite-wal').read_bytes(), b'owned WAL')
        self.assertIs(store.revalidate_publication(second), second)

    def test_edited_content_starts_new_branch_and_preserves_old_content_slot_and_claim(self):
        first = self.publish()
        original = {p.relative_to(self.project).as_posix(): p.read_bytes()
                    for p in first.content_directory.rglob('*') if p.is_file()}
        first.database_path.write_bytes(b'old committed progress')
        claim = first.slot_directory / 'world.sqlite.initialized'
        claim.write_bytes(b'native seed-once claim')
        second = self.publish(snapshot(b'authored placement/hint changed'))
        self.assertNotEqual(first.timeline_id, second.timeline_id)
        self.assertNotEqual(first.content_directory, second.content_directory)
        self.assertFalse(second.database_path.exists())
        self.assertEqual(first.database_path.read_bytes(), b'old committed progress')
        self.assertEqual(claim.read_bytes(), b'native seed-once claim')
        for relative, raw in original.items():self.assertEqual((self.project / relative).read_bytes(), raw)

    def test_corrupt_existing_content_is_rejected_without_replacement_or_save_mutation(self):
        first = self.publish()
        first.content_path.write_bytes(b'corrupt retained publication')
        first.database_path.write_bytes(b'leave this save alone')
        prep = store.prepare_publication(self.project, snapshot())
        with self.assertRaisesRegex(ValueError, 'changed'):
            store.finish_publication(prep)
        self.assertEqual(first.content_path.read_bytes(), b'corrupt retained publication')
        self.assertEqual(first.database_path.read_bytes(), b'leave this save alone')
        store.discard_staging(prep)

    def test_extra_file_or_empty_directory_in_existing_publication_rejects(self):
        for directory in (False, True):
            with self.subTest(directory=directory):
                first = self.publish()
                extra = first.content_directory / 'unexpected'
                extra.mkdir() if directory else extra.write_bytes(b'extra')
                prep = store.prepare_publication(self.project, snapshot())
                with self.assertRaisesRegex(ValueError, 'Unexpected'):
                    store.finish_publication(prep)
                store.discard_staging(prep)
                extra.rmdir() if directory else extra.unlink()

    def test_slot_identity_and_typed_version_corruption_reject_without_reseed(self):
        first = self.publish()
        path = first.slot_directory / 'slot.json'
        original = path.read_bytes()
        for change in ('version', 'identity', 'timeline', 'extra'):
            with self.subTest(change=change):
                value = json.loads(original)
                if change == 'version':value['version'] = True
                elif change == 'identity':value['identity']['branch_id'] = 'foreign'
                elif change == 'timeline':value['timeline_id'] = 'not a UUID'
                else:value['extra'] = True
                raw = json.dumps(value).encode();path.write_bytes(raw)
                with self.assertRaises(ValueError):self.publish()
                self.assertEqual(path.read_bytes(), raw)
                self.assertFalse(first.database_path.exists())
        path.write_bytes(original)

    def test_invalid_snapshot_does_not_create_runtime_directory(self):
        for key, value in [('fingerprint', '0'*64), ('export_version', 1),
                           ('content_revision', True), ('asset_profile', 'unknown')]:
            with self.subTest(key=key):
                s = snapshot();setattr(s, key, value)
                with self.assertRaises(ValueError):store.prepare_publication(self.project, s)
                self.assertFalse((self.project / '.aibs-runtime').exists())

    def test_duplicate_and_unordered_dependencies_reject_before_writes(self):
        ref = NS(asset_id=str(uuid.uuid4()), asset_sha256='a'*64, pack_sha256='b'*64)
        for refs, kinds in [((ref, ref), (0, 0)), ((ref,), (True,)), ((ref,), ()), ((ref,)*33, (0,)*33)]:
            with self.subTest(refs=len(refs),kinds=kinds[:2]):
                with self.assertRaises(ValueError):store.prepare_publication(self.project, snapshot(refs=refs,kinds=kinds))
                self.assertFalse((self.project / '.aibs-runtime').exists())

    def test_cancelled_or_stale_publication_does_not_create_slot_or_content(self):
        prep = store.prepare_publication(self.project, snapshot())
        with self.assertRaisesRegex(ValueError, 'changed'):
            store.finish_publication(prep, context_valid=lambda: False)
        self.assertFalse((prep.root / 'content' / prep.identity['content_fingerprint']).exists())
        self.assertFalse((prep.root / 'saves' / prep.identity['content_fingerprint']).exists())
        store.discard_staging(prep)
        self.assertFalse(prep.staging.exists())

    def test_context_change_after_hashing_never_creates_player_slot(self):
        prep = store.prepare_publication(self.project, snapshot())
        answers = iter((True, False))
        with self.assertRaisesRegex(ValueError, 'changed'):
            store.finish_publication(prep, context_valid=lambda: next(answers))
        self.assertEqual(list((prep.root / 'content').iterdir()), [])
        self.assertEqual(list((prep.root / 'saves').iterdir()), [])
        store.discard_staging(prep)

    def test_cleanup_refuses_retained_slot_and_does_not_touch_external_sentinel(self):
        first = self.publish()
        sentinel = self.project / 'leave-me.txt';sentinel.write_bytes(b'leave')
        forged = store.PublicationPreparation(self.project, self.project / '.aibs-runtime',
                                              first.slot_directory, first.identity)
        with self.assertRaisesRegex(ValueError, 'Refusing cleanup'):
            store.discard_staging(forged)
        self.assertTrue((first.slot_directory / 'slot.json').exists())
        self.assertEqual(sentinel.read_bytes(), b'leave')

    def test_manifest_replacement_between_publication_and_launch_rejects(self):
        first = self.publish()
        path = first.content_directory / 'publication.json'
        value = json.loads(path.read_bytes())
        first.content_path.write_bytes(b'forged new bytes')
        value['files'][0]['bytes'] = len(b'forged new bytes')
        value['files'][0]['sha256'] = hashlib.sha256(b'forged new bytes').hexdigest()
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'manifest changed'):
            store.revalidate_publication(first)

    def test_native_staged_mesh_character_audio_four_file_closures_are_retained(self):
        for kind in (0, 1, 2):
            with self.subTest(kind=kind):
                source = self.project / ('source' + str(kind));source.mkdir()
                ref, pack = synthetic_pack(source, kind=kind, payload=b'different-kind'+bytes([kind]))
                s = snapshot(b'content'+bytes([kind]), (ref,), (kind,))
                prep = store.prepare_publication(self.project, s)
                destination = prep.staging / 'assets/packs'/ref.pack_sha256
                shutil.copytree(pack,destination)
                result = store.finish_publication(prep)
                self.assertEqual(len(list(result.asset_root.rglob('*'))),5)
                store.revalidate_publication(result)

    def test_changed_staged_payload_catalog_license_and_extra_member_reject_before_publication(self):
        source = self.project / 'source';source.mkdir()
        ref, pack = synthetic_pack(source)
        for change in ('payload','catalog','license','extra'):
            with self.subTest(change=change):
                prep = store.prepare_publication(self.project,snapshot(refs=(ref,),kinds=(0,)))
                destination = prep.staging / 'assets/packs'/ref.pack_sha256
                shutil.copytree(pack,destination)
                name={'payload':ref.asset_sha256+'.aibmesh','catalog':'catalog.aibcat','license':'LICENSE.txt','extra':'bad.txt'}[change]
                (destination/name).write_bytes(b'changed')
                with self.assertRaises(ValueError):store.finish_publication(prep)
                self.assertEqual(list((prep.root/'content').iterdir()),[])
                store.discard_staging(prep)

    def test_path_redirection_is_rejected_before_runtime_writes(self):
        # Mock the platform lstat flag: the actual junction integration proof is
        # separate; this exercises the same Windows reparse predicate on each ancestor.
        real = Path.lstat
        target = self.project
        def redirected(path):
            info=real(path)
            if path==target:return NS(st_mode=info.st_mode,st_file_attributes=store._REPARSE)
            return info
        with patch.object(Path,'lstat',redirected):
            with self.assertRaisesRegex(ValueError,'links or junctions'):
                store.prepare_publication(self.project,snapshot())
        self.assertFalse((self.project/'.aibs-runtime').exists())

    def test_duplicate_nonfinite_and_oversized_json_reject(self):
        for raw in (b'{"version":1,"version":1}',b'{"x":NaN}',b' '*(store.SLOT_LIMIT+1)):
            with self.subTest(length=len(raw)):
                with self.assertRaises(ValueError):store._json(raw,store.SLOT_LIMIT)

    def test_missing_and_malformed_capabilities_reject_before_project_writes(self):
        exe=self.project/'player.exe';exe.write_bytes(b'not executed by these tests')
        s=snapshot();path=self.project/'aibs_capabilities.json'
        with self.assertRaises(ValueError):store.require_saved_player(exe,s)
        base={'schema_version':1,'sdk_version':'0.16.0','target':'windows-x64','features':{
            flag:True for flag in ('chapter-saved-play-v1','durable_world','first_boot_chapter',
            'first_boot_content_play','chapter_content_export_v2','chapter_content_v3','chapter_asset_surfaces')}}
        path.write_text(json.dumps(base));self.assertEqual(store.require_saved_player(exe,s),exe)
        for raw in (b'{"schema_version":1,"schema_version":1}',b'{}',b' '*(16384+1)):
            path.write_bytes(raw)
            with self.assertRaises(ValueError):store.require_saved_player(exe,s)
        path.write_text(json.dumps(dict(base,features=dict(base['features'],**{'chapter-saved-play-v1':False}))))
        with self.assertRaisesRegex(ValueError,'Upgrade'):store.require_saved_player(exe,s)
        self.assertFalse((self.project/'.aibs-runtime').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows handle contract')
    def test_live_directory_handles_prevent_ancestor_rename_during_publication_io(self):
        parent=self.project/'owned-parent';child=parent/'child';child.mkdir(parents=True)
        moved=self.project/'moved-parent'
        with store._pinned_directory(child):
            with self.assertRaises(OSError):os.rename(parent,moved)
            self.assertTrue(child.is_dir());self.assertFalse(moved.exists())
        os.rename(parent,moved)
        self.assertTrue((moved/'child').is_dir())

    @unittest.skipUnless(os.name == 'nt', 'Windows handle contract')
    def test_read_handle_freezes_bytes_and_file_identity_until_close(self):
        path=self.project/'frozen.bin';path.write_bytes(b'original')
        with store._reader(path) as stream:
            with self.assertRaises(OSError):path.write_bytes(b'truncate')
            with self.assertRaises(OSError):os.rename(path,self.project/'renamed.bin')
            self.assertEqual(stream.read(),b'original')
        path.write_bytes(b'allowed after close')
        self.assertEqual(path.read_bytes(),b'allowed after close')

    def test_excess_pack_entries_fail_while_enumerating_before_any_payload_read(self):
        source=self.project/'source';source.mkdir();ref,pack=synthetic_pack(source)
        prep=store.prepare_publication(self.project,snapshot(refs=(ref,),kinds=(0,)))
        destination=prep.staging/'assets/packs'/ref.pack_sha256
        shutil.copytree(pack,destination)
        for i in range(5):(destination/('extra'+str(i))).write_bytes(b'x')
        with self.assertRaisesRegex(ValueError,'member limit'):
            store.finish_publication(prep)
        self.assertEqual(list((prep.root/'content').iterdir()),[])
        store.discard_staging(prep)



if __name__=='__main__':unittest.main()
