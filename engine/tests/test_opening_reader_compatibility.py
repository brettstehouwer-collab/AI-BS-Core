"""Reader selection and low-level admission, with no executable/GPU launch."""
import json,tempfile,unittest,uuid,hashlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_preview import ContentSnapshot,ContentExportAssembly,ContentViewportClient
from native_studio.game_engine.content_play import ContentPlayClient
from native_studio.game_engine.content_commands import ContentDescription,ContentExportChunk
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine.creator_payload import Scope
from test_opening_creator import fixture,CAP
APP=QApplication.instance()or QApplication([])
def snapshot(flag=False):
    payload=b'owned native bytes';scope=Scope('p','main',str(uuid.uuid4()),str(uuid.uuid4()))
    return ContentSnapshot(scope,1,2,'',str(uuid.uuid4()),2,hashlib.sha256(payload).hexdigest(),payload,frozenset(),asset_profile='warm-beginning',authored_inspections=flag)
class ReaderCompatibility(unittest.TestCase):
    def test_snapshot_flag_is_owned_strict_bool_and_defaults_false(self):
        s=snapshot();self.assertFalse(s.authored_inspections)
        for bad in (1,None,'yes'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):snapshot(bad)
    def test_assembly_pins_authored_flag_with_same_native_export_head(self):
        s=snapshot(True);d=ContentDescription(s.definition_id,2,s.fingerprint,False,1)
        a=ContentExportAssembly(s.scope,1,2,'',d,(),asset_profile='warm-beginning',authored_inspections=True)
        chunk=ContentExportChunk(s.definition_id,s.fingerprint,2,len(s.payload),0,s.payload)
        result=a.accept(chunk,s.scope,1,2,'');self.assertTrue(result.authored_inspections)
    def test_binary_selection_requires_new_reader_only_for_bound_triples(self):
        old=Path('C:/old-player.exe');new=Path('C:/new-player.exe')
        features={'first_boot_content_play':True,'chapter_asset_surfaces':True}
        view=SimpleNamespace(rows=(fixture(inspection_text='Synthetic',inspection_source='Synthetic origin',inspection_action='read'),),definition=SimpleNamespace(asset_profile='warm-beginning'),_binary_candidates=lambda name:(old,new))
        def caps(path):return {'features':{**features,**({CAP:True}if path==new else{})}}
        with patch('native_studio.game_engine.content_view.read_native_player_capabilities',side_effect=caps):
            self.assertEqual(ContentView._play_binary(view),new)
            view.rows=(fixture(),);self.assertEqual(ContentView._play_binary(view),old)
    def test_lowlevel_play_rejects_old_reader_before_private_files_or_launch(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);exe=root/'player.exe';exe.write_bytes(b'not executable')
            (root/'aibs_capabilities.json').write_text(json.dumps({'schema_version':1,'sdk_version':'0.12.0','features':{'chapter_asset_surfaces':True}}))
            client=ContentPlayClient()
            try:
                with patch.object(client,'_launch')as launch,self.assertRaisesRegex(ValueError,'inspection|Inspection'):
                    client.start(exe,snapshot(True))
                launch.assert_not_called();self.assertIsNone(client._directory)
            finally:
                if client._directory:client._directory.cleanup();client._directory=None
                client._path=None;client.state='closed';client._stager.shutdown();client.deleteLater()
    def test_lowlevel_preview_rejects_old_reader_before_launch(self):
        with tempfile.TemporaryDirectory()as directory:
            exe=Path(directory)/'viewport.exe';exe.write_bytes(b'not executable')
            client=ContentViewportClient()
            try:
                with patch.object(client,'_start_owned_content')as start,self.assertRaisesRegex(ValueError,'inspection|Inspection'):
                    client.start_content(exe,snapshot(True))
                start.assert_not_called();self.assertIsNone(client._directory)
            finally:
                if client._directory:client._directory.cleanup();client._directory=None
                client._path=None;client.state='closed';client._stager.shutdown();client.deleteLater()
    def test_publish_to_running_old_reader_rejects_without_replacing_previous_scene(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);exe=root/'viewport.exe';exe.write_bytes(b'not executable');(root/'scene.aibv').write_bytes(b'previous accepted scene')
            client=ContentViewportClient();client._directory=SimpleNamespace(cleanup=lambda:None);client._path=root;client.state='ready';client._content_executable=exe
            s=snapshot(True)
            try:
                with patch.object(client,'_publish_raw')as publish,self.assertRaisesRegex(ValueError,'inspection|Inspection'):
                    client.publish(s.scope,s.revision,s.checkpoint_id,s)
                publish.assert_not_called();self.assertEqual((root/'scene.aibv').read_bytes(),b'previous accepted scene')
            finally:client._directory=None;client._path=None;client.state='closed';client._stager.shutdown();client.deleteLater()
    def test_plain_modern_content_does_not_require_new_reader(self):
        with tempfile.TemporaryDirectory()as directory:
            exe=Path(directory)/'viewport.exe';exe.write_bytes(b'not executable')
            client=ContentViewportClient()
            try:
                with patch.object(client,'_start_owned_content')as start:client.start_content(exe,snapshot(False));start.assert_called_once()
            finally:client._stager.shutdown();client.deleteLater()
    def test_highlevel_preview_skips_old_reader_for_bound_snapshot(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);old=root/'old.exe';new=root/'new.exe';old.write_bytes(b'old');new.write_bytes(b'new')
            view=SimpleNamespace(_content_snapshot=snapshot(True),viewport=SimpleNamespace(state='closed',start_content=Mock()),selected_id=None,
                _binary_candidates=lambda name:(old,new),_controls=lambda:None)
            def caps(path):return {'features':{'chapter_asset_surfaces':True,**({CAP:True}if path==new else{})}}
            with patch('native_studio.game_engine.content_view.read_native_player_capabilities',side_effect=caps):ContentView._use_snapshot(view,'preview')
            self.assertEqual(view.viewport.start_content.call_args.args[0],new)
if __name__=='__main__':unittest.main()
