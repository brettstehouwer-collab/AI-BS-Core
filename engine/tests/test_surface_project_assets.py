"""Typed surface profile contracts without launching a GPU or authoring owner."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.project_assets import AssetDependency, ProjectAssetClient
from native_studio.game_engine.content_view import ChapterProjectDefinition, ContentView
from native_studio.game_engine.content_client import ContentClient
from native_studio.game_engine.creator_client import CreatorClient
from native_studio.game_engine.content_preview import ContentSnapshot, ContentViewportClient, ContentExportAssembly
from native_studio.game_engine.content_play import ContentPlayClient
from native_studio.game_engine.asset_view import AssetView
from native_studio.game_engine.creator_payload import Scope

APP = QApplication.instance() or QApplication([])
ASSET = '876721b8-1abe-492a-926f-f5b922d23be9'
SHA, PACK = 'a'*64, 'b'*64

class Stager(QObject):
    receipt=pyqtSignal(str,object);failed=pyqtSignal(str);closed=pyqtSignal()
    def __init__(self,*args):super().__init__();self.busy=False;self.process_id=0
    def stage_store(self,*args,**kwargs):self.args=args;self.kwargs=kwargs;self.busy=True
    def stop(self):self.busy=False
    def shutdown(self):self.busy=False

class SurfaceProjectContracts(unittest.TestCase):
    def test_legacy_metadata_remains_v1_and_modern_profile_survives_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/'old';modern=root/'modern';old.mkdir();modern.mkdir()
            legacy=ChapterProjectDefinition.create(old,'Legacy')
            self.assertEqual(json.loads(legacy.path.read_text()),{'version':1,'project':'Legacy','branch':'main'})
            self.assertEqual(ChapterProjectDefinition.load(old).asset_profile,'legacy_v1')
            created=ChapterProjectDefinition.create(modern,'Modern',asset_profile='warm-beginning')
            self.assertEqual(json.loads(created.path.read_text())['version'],2)
            self.assertEqual(ChapterProjectDefinition.load(modern).asset_profile,'warm-beginning')
            data=json.loads(created.path.read_text());data['asset_profile']='unbounded';created.path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):ChapterProjectDefinition.load(modern)

    def test_profile_rejects_unknown_values_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):ChapterProjectDefinition.create(directory,'Bad',asset_profile='unbounded')
            self.assertFalse((Path(directory)/'.aibs-chapter-project.json').exists())

    def test_stage_flags_are_explicit_and_old_arguments_stay_identical(self):
        client=ProjectAssetClient(Path('C:/unused.exe'));ref=AssetDependency(ASSET,SHA,PACK)
        with patch.object(client,'_start') as start:
            client.stage_store('C:/source','C:/target',[ref],profile='warm-beginning')
            self.assertEqual(start.call_args.args[0][-2:],['--profile','warm-beginning'])
            client.stage_store('C:/source','C:/target',[ref])
            self.assertNotIn('--profile',start.call_args.args[0])
            with self.assertRaises(ValueError):client.stage_store('C:/source','C:/target',[ref],profile='unbounded')

    def test_host_launch_profile_is_local_explicit_and_legacy_unchanged(self):
        self.assertEqual(CreatorClient()._launch_arguments('C:/owned'),['--workspace','C:/owned'])
        client=ContentClient();self.assertEqual(client._launch_arguments('C:/owned'),['--workspace','C:/owned'])
        client.asset_profile='warm-beginning'
        self.assertEqual(client._launch_arguments('C:/owned'),['--workspace','C:/owned','--asset-profile','warm-beginning'])
        client.asset_profile='unbounded'
        with self.assertRaises(ValueError):client._launch_arguments('C:/owned')

    def test_typed_inspection_retains_surface_counts_and_rejects_unknown_kind(self):
        row={'asset_id':ASSET,'name':'PCB','sha256':SHA,'triangles':1,'materials':1,
             'kind':'surface','image_count':2,'decoded_image_bytes':20,'decoded_bytes':200}
        admitted=AssetView._rows({'assets':[row]})[0]
        self.assertEqual(admitted['kind'],'surface');self.assertEqual(admitted['image_count'],2)
        for field,value in [('kind','audio'),('image_count',33),('decoded_bytes',128*1024*1024+1),('decoded_image_bytes',-1)]:
            with self.subTest(field=field),self.assertRaises(ValueError):AssetView._rows({'assets':[{**row,field:value}]})
        legacy={k:v for k,v in row.items() if k not in {'kind','image_count','decoded_image_bytes','decoded_bytes'}}
        self.assertEqual(AssetView._rows({'assets':[legacy]})[0],legacy)

    def test_surface_cook_mode_preserves_legacy_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for n in ('cooker.exe','player.exe','part.obj','part.aibmat','rights.txt'):(root/n).write_bytes(b'fixture')
            view=AssetView(root/'cooker.exe',root/'player.exe')
            try:
                with patch.object(view,'_start_tool') as start:
                    args=(root/'part.obj',root/'part.aibmat',root/'rights.txt',root/'new',ASSET,'Part')
                    view.cook_asset(*args,surface=True,uv_origin='bottom-left')
                    self.assertEqual(start.call_args.args[0][0],'--cook-surface')
                    self.assertEqual(start.call_args.args[0][-2:],['--uv-origin','bottom-left'])
                    view.cook_asset(*args);self.assertEqual(start.call_args.args[0][0],'--source')
                    with self.assertRaises(ValueError):view.cook_asset(*args,surface=True,uv_origin='guess')
            finally:view.close();view.deleteLater()

    def snapshot(self,root):
        payload=b'Native opaque modern content'
        return ContentSnapshot(Scope('project','main',str(uuid.uuid4()),str(uuid.uuid4())),1,2,'',str(uuid.uuid4()),3,
            hashlib.sha256(payload).hexdigest(),payload,frozenset(),(AssetDependency(ASSET,SHA,PACK),),root/'store',
            asset_profile='warm-beginning')

    def test_modern_play_and_viewport_stage_with_same_profile_as_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);exe=root/'player.exe';exe.write_bytes(b'fixture');snapshot=self.snapshot(root)
            with patch('native_studio.game_engine.content_play.ProjectAssetClient',Stager):
                play=ContentPlayClient(asset_cooker=root/'cooker.exe')
                with patch.object(play,'_launch') as launch:
                    play.start(exe,snapshot);self.assertEqual(play._stager.kwargs['profile'],'warm-beginning');launch.assert_not_called()
                play._finish_stage_only()
            with patch('native_studio.game_engine.content_preview.ProjectAssetClient',Stager):
                viewport=ContentViewportClient(asset_cooker=root/'cooker.exe')
                viewport.start_content(exe,snapshot);self.assertEqual(viewport._stager.kwargs['profile'],'warm-beginning')
                viewport._finish_stage_only()

    def test_authoritative_profile_field_is_checked_and_not_editable(self):
        view=ContentView(Path('C:/unused.exe'))
        try:
            view.definition=SimpleNamespace(asset_profile='warm-beginning')
            rows=[SimpleNamespace(type_id='authoring.ChapterSettings',fields=(('asset_profile','warm_beginning'),))]
            self.assertEqual(view._validated_asset_profile(rows),'warm-beginning')
            with self.assertRaises(ValueError):view._validated_asset_profile([])
            view.definition=SimpleNamespace(asset_profile='legacy_v1')
            self.assertEqual(view._validated_asset_profile([]),'legacy_v1')
            with self.assertRaises(ValueError):view._validated_asset_profile(rows)
        finally:view.definition=None;view.close();view.deleteLater()

if __name__=='__main__':unittest.main()
