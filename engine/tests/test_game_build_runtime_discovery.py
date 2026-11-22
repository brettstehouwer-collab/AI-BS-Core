"""Source-mode lazy page discovery; synthetic files are never executed."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication, QWidget
import native_studio.game_build_view as game_view

APP = QApplication.instance() or QApplication([])
VERSIONS = ('0.17.2', '0.17.1', '0.17.0', '0.16.6', '0.16.5', '0.16.4', '0.16.3', '0.16.2', '0.16.1', '0.16.0', '0.15.0')


class SourceRuntimeDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='aibs-discovery-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            widget.deleteLater()
        APP.processEvents()

    def stub_widget(self, *args, **kwargs):
        widget = QWidget()
        self.widgets.append(widget)
        return widget

    def owner(self, root=None):
        content, creator = QWidget(), QWidget()
        self.widgets.extend((content, creator))
        return SimpleNamespace(root=root or self.root, content_view=None,
            creator_view=None, _content_page=content, _creator_page=creator,
            _content_layout=Mock(), _creator_layout=Mock())

    def fixture(self, relative, root=None):
        path = (root or self.root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'file-only synthetic discovery fixture; never executed')
        return path

    def runtime(self, version, executable, root=None):
        return self.fixture(f'engine/install/{version}/runtime-release/bin/{executable}', root)

    def select(self, owner, index):
        # Call the real lazy handler directly: Qt slot exceptions must surface as
        # test failures rather than depending on the Qt unhandled-slot policy.
        game_view.GameBuildNativeView._workspace_changed(owner, index)

    def test_content_lazy_open_uses_instance_root_and_caches_page(self):
        expected = self.runtime('0.16.0', 'aibs_content_host.exe')
        owner = self.owner()
        with patch.object(game_view, '_bundle_root', return_value=None), patch(
                'native_studio.game_engine.content_view.ContentView',
                side_effect=self.stub_widget) as constructor:
            self.select(owner, 0)
            constructor.assert_not_called()
            self.select(owner, 2)
            constructor.assert_called_once()
            self.assertEqual(constructor.call_args.args[0], expected)
            self.assertIs(constructor.call_args.args[1], owner._content_page)
            self.assertIsNone(owner.creator_view)
            self.select(owner, 2)
            constructor.assert_called_once()
        owner._content_layout.addWidget.assert_called_once_with(owner.content_scroll)
        self.assertIs(owner.content_scroll.widget(),owner.content_view)

    def test_creator_lazy_open_uses_instance_root_and_caches_page(self):
        expected = self.runtime('0.15.0', 'aibs_creator_host.exe')
        owner = self.owner()
        with patch.object(game_view, '_bundle_root', return_value=None), patch(
                'native_studio.game_engine.creator_view.CreatorView',
                side_effect=self.stub_widget) as constructor:
            self.select(owner, 0)
            constructor.assert_not_called()
            self.select(owner, 1)
            constructor.assert_called_once_with(expected, owner._creator_page)
            self.assertIsNone(owner.content_view)
            self.select(owner, 1)
            constructor.assert_called_once()
        owner._creator_layout.addWidget.assert_called_once_with(owner.creator_scroll)
        self.assertIs(owner.creator_scroll.widget(),owner.creator_view)

    def test_content_host_precedence_and_retained_legacy_fallback(self):
        candidates = [self.runtime(v, 'aibs_content_host.exe') for v in VERSIONS]
        candidates += [self.fixture('engine/install/0.11.0/release/bin/aibs_content_host.exe'),
                       self.fixture('engine/install/release/bin/aibs_content_host.exe')]
        with patch.object(game_view, '_bundle_root', return_value=None), patch(
                'native_studio.game_engine.content_view.ContentView',
                side_effect=self.stub_widget) as constructor:
            for expected in candidates:
                with self.subTest(expected=expected.relative_to(self.root)):
                    self.select(self.owner(), 2)
                    self.assertEqual(constructor.call_args.args[0], expected)
                    expected.unlink()

    def test_creator_host_precedence_and_retained_legacy_fallback(self):
        candidates = [self.runtime(v, 'aibs_creator_host.exe') for v in VERSIONS]
        candidates += [self.fixture('engine/install/release/bin/aibs_creator_host.exe'),
                       self.fixture('engine/out/windows-msvc/Release/aibs_creator_host.exe')]
        with patch.object(game_view, '_bundle_root', return_value=None), patch(
                'native_studio.game_engine.creator_view.CreatorView',
                side_effect=self.stub_widget) as constructor:
            for expected in candidates:
                with self.subTest(expected=expected.relative_to(self.root)):
                    self.select(self.owner(), 1)
                    self.assertEqual(constructor.call_args.args[0], expected)
                    expected.unlink()

    def test_bundle_hosts_take_precedence_over_source_installations(self):
        bundle = self.root / 'bundle'
        content = self.fixture('game_assets/player/aibs_content_host.exe', bundle)
        creator = self.fixture('game_assets/player/aibs_creator_host.exe', bundle)
        self.runtime(VERSIONS[0], content.name)
        self.runtime(VERSIONS[0], creator.name)
        owner = self.owner()
        with patch.object(game_view, '_bundle_root', return_value=bundle), patch(
                'native_studio.game_engine.content_view.ContentView', side_effect=self.stub_widget) as content_ctor, patch(
                'native_studio.game_engine.creator_view.CreatorView', side_effect=self.stub_widget) as creator_ctor:
            self.select(owner, 2)
            self.select(owner, 1)
            self.assertEqual(content_ctor.call_args.args[0], content)
            self.assertEqual(creator_ctor.call_args.args[0], creator)
            self.assertEqual(content_ctor.call_args.kwargs['asset_cooker'], bundle/'game_assets/player/aibs_assetc.exe')

    def test_empty_checkout_keeps_predictable_unavailable_paths(self):
        owner = self.owner()
        with patch.object(game_view, '_bundle_root', return_value=None), patch(
                'native_studio.game_engine.content_view.ContentView', side_effect=self.stub_widget) as content_ctor, patch(
                'native_studio.game_engine.creator_view.CreatorView', side_effect=self.stub_widget) as creator_ctor:
            self.select(owner, 2)
            self.select(owner, 1)
            self.assertEqual(content_ctor.call_args.args[0], self.root/'engine/install/release/bin/aibs_content_host.exe')
            self.assertEqual(creator_ctor.call_args.args[0], self.root/'engine/out/windows-msvc/Release/aibs_creator_host.exe')

    def test_two_source_owners_do_not_use_global_project_root(self):
        other = self.root / 'other'
        first_host = self.runtime('0.16.2', 'aibs_content_host.exe')
        second_host = self.runtime('0.15.0', 'aibs_content_host.exe', other)
        with patch.object(game_view, '_bundle_root', return_value=None), patch(
                'native_studio.game_engine.content_view.ContentView', side_effect=self.stub_widget) as constructor:
            self.select(self.owner(), 2)
            self.assertEqual(constructor.call_args.args[0], first_host)
            self.select(self.owner(other), 2)
            self.assertEqual(constructor.call_args.args[0], second_host)

    def test_asset_tools_skip_incomplete_newer_pair_and_use_newest_complete_pair(self):
        newest = self.runtime(VERSIONS[0], 'aibs_assetc.exe')
        complete = self.runtime(VERSIONS[1], 'aibs_assetc.exe')
        player = self.runtime(VERSIONS[1], 'aibs_motherboard.exe')
        legacy = self.fixture('engine/install/0.11.0/release/bin/aibs_assetc.exe')
        self.fixture('engine/install/0.11.0/release/bin/aibs_motherboard.exe')
        with patch.object(game_view, '_bundle_root', return_value=None):
            self.assertEqual(game_view._asset_workspace_paths(self.root)[:2], (complete, player))
            new_player = self.runtime(VERSIONS[0], 'aibs_motherboard.exe')
            self.assertEqual(game_view._asset_workspace_paths(self.root)[:2], (newest, new_player))
            new_player.unlink()
            player.unlink()
            self.assertEqual(game_view._asset_workspace_paths(self.root)[0], legacy)

    def test_native_player_precedence_does_not_require_a_cooker(self):
        candidates = [self.runtime(v, 'aibs_motherboard.exe') for v in VERSIONS]
        candidates += [self.fixture('engine/install/0.11.0/release/bin/aibs_motherboard.exe')]
        with patch.object(game_view, '_bundle_root', return_value=None):
            for expected in candidates:
                with self.subTest(expected=expected.relative_to(self.root)):
                    self.assertEqual(game_view._native_player_path(self.root), expected)
                    expected.unlink()

    def test_opening_resources_prefer_current_source_and_retain_legacy_fallback(self):
        host = self.runtime(VERSIONS[0], 'aibs_creator_host.exe')
        factory = self.fixture('engine/install/'+VERSIONS[0]+'/runtime-release/bin/aibs_warm_opening_project.exe')
        legacy = self.root/'engine/assets/cooked/warm-opening'
        current = self.root/'engine/assets/cooked/warm-opening-v18'
        legacy.mkdir(parents=True)
        with patch.object(game_view, '_bundle_root', return_value=None):
            self.assertEqual(game_view._opening_workspace_paths(self.root, host), (factory, legacy))
            current.mkdir()
            self.assertEqual(game_view._opening_workspace_paths(self.root, host), (factory, current))
            surface = self.root/'engine/assets/cooked/warm-opening-v20-surface'
            surface.mkdir()
            self.assertEqual(game_view._opening_workspace_paths(self.root, host), (factory, surface))
            surface.rmdir()
            self.assertEqual(game_view._opening_workspace_paths(self.root, host), (factory, current))
            current.rmdir()
            self.assertEqual(game_view._opening_workspace_paths(self.root, host), (factory, legacy))

    def test_opening_bundle_never_borrows_source_character_assets(self):
        bundle = self.root/'bundle'
        host = self.fixture('game_assets/player/aibs_creator_host.exe', bundle)
        factory = self.fixture('game_assets/player/aibs_warm_opening_project.exe', bundle)
        current = self.root/'engine/assets/cooked/warm-opening-v18'
        current.mkdir(parents=True)
        (self.root/'engine/assets/cooked/warm-opening-v20-surface').mkdir()
        resources = bundle/'game_assets/opening'
        resources.mkdir()
        for discovered_bundle in (bundle, None):
            with self.subTest(explicit_bundle=discovered_bundle is not None), patch.object(game_view, '_bundle_root', return_value=discovered_bundle):
                self.assertEqual(game_view._opening_workspace_paths(self.root, host), (factory, resources))
                resources.rmdir()
                self.assertEqual(game_view._opening_workspace_paths(self.root, host), (factory, None))
                resources.mkdir()


if __name__ == '__main__':
    unittest.main()
