"""Real Windows deep typed publication, reuse and tamper rejection regression."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace as NS
import unittest
import uuid

from native_studio.game_engine import saved_play_storage as store


def io(path):
    value = os.path.abspath(path)
    return Path('\\\\?\\'+value) if os.name == 'nt' else Path(value)


@unittest.skipUnless(os.name == 'nt', 'Exercises actual Windows extended-length filesystem paths')
class DeepSavedPublication(unittest.TestCase):
    def test_deep_typed_publication_reuses_slot_rejects_tampering_and_preserves_save(self):
        base = Path(tempfile.mkdtemp(prefix='aibs-deep-publication-'))
        # The staging root itself is short; hashed children exceed MAX_PATH.
        # This also exercises reuse's recursive cleanup from a short root.
        project = base/'project'
        io(project).mkdir(parents=True)
        try:
            payload = b'Synthetic publication payload, not a native geometry test'
            digest = hashlib.sha256(payload).hexdigest()
            asset = str(uuid.uuid4())
            files = {digest+'.aibsurf': payload,
                'catalog.aibcat': f'AIBCAT 2\nsurface {asset} {digest} {digest}.aibsurf\n'.encode(),
                'LICENSE.txt': b'Synthetic test data\n', 'provenance.json': b'{"synthetic":true}\n'}
            manifest = 'AIBPACK 2\n'+''.join(f'{name} {len(raw)} {hashlib.sha256(raw).hexdigest()}\n'
                                                for name, raw in sorted(files.items()))
            pack_sha = hashlib.sha256(manifest.encode()).hexdigest()
            snap = NS(payload=b'synthetic canonical content', fingerprint=hashlib.sha256(b'synthetic canonical content').hexdigest(),
                scope=NS(project='deep-test', branch='main', world_id=str(uuid.uuid4())),
                definition_id=str(uuid.uuid4()), content_revision=6, asset_profile='warm-beginning',
                export_version=2, dependency_kinds=(0,), asset_refs=(NS(asset_id=asset,
                    asset_sha256=digest, pack_sha256=pack_sha),))

            def stage():
                prep = store.prepare_publication(project, snap)
                pack = prep.staging/'assets/packs'/pack_sha
                io(pack).mkdir(parents=True)
                for name, raw in files.items():
                    io(pack/name).write_bytes(raw)
                self.assertGreater(len(str(pack/(digest+'.aibsurf'))), 260)
                return prep

            first = store.finish_publication(stage())
            self.assertEqual(first.project, project)
            self.assertFalse(str(first.project).startswith('\\\\?\\'))
            sentinel = b'opaque committed save must survive publication validation'
            io(first.database_path).write_bytes(sentinel)
            second = store.finish_publication(stage())
            self.assertTrue(second.reused_slot and second.reused_publication)
            self.assertEqual(first.timeline_id, second.timeline_id)
            self.assertIs(store.revalidate_publication(second), second)
            cooked = second.asset_root/pack_sha/(digest+'.aibsurf')
            self.assertEqual(store._read(cooked, 1024), payload)
            io(cooked).write_bytes(b'tampered bytes')
            with self.assertRaisesRegex(ValueError, 'changed'):
                store.revalidate_publication(second)
            self.assertEqual(io(first.database_path).read_bytes(), sentinel)
            with self.assertRaisesRegex(ValueError, 'traverse'):
                store.checked_path(project/'..'/'outside')
        finally:
            intended = Path(tempfile.gettempdir()).absolute()
            self.assertEqual(base.absolute().parent, intended)
            self.assertTrue(base.name.startswith('aibs-deep-publication-'))
            for here, dirs, files in os.walk(io(base), followlinks=False):
                for name in dirs:
                    self.assertFalse((Path(here)/name).lstat().st_file_attributes & 0x400)
            self.assertFalse(io(base).lstat().st_file_attributes & 0x400)
            shutil.rmtree(io(base))


if __name__ == '__main__':
    unittest.main()
