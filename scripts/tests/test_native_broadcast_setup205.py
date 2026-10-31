"""Offscreen settings fixtures; no actual dialog, capture, services or profiles."""
from __future__ import annotations

import copy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication, QDialog
from native_studio import broadcast_stream_engine as profiles
from native_studio import omni_broadcast_studio as studio


class _Signal:
    def __init__(self):
        self.callbacks = []
    def connect(self, callback):
        self.callbacks.append(callback)
    def emit(self, value):
        for callback in self.callbacks:
            callback(value)


class NativeBroadcastSetup205Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def fixture_config(self):
        cfg = profiles.StreamProfileManager.get_defaults()
        cfg['destinations']['facebook'].update(enabled=True, key='synthetic-key-only',
                                              url='rtmps://example.invalid/rtmp/')
        return cfg

    def test_unmeasured_audio_meter_starts_with_zero_levels(self):
        meter=studio.ChannelVuMeter()
        self.addCleanup(meter.deleteLater)
        self.assertEqual((meter.left_peak,meter.right_peak,meter.target_l,meter.target_r),(0.0,0.0,0.0,0.0))

    def test_window_enumeration_preserves_exact_title_whitespace(self):
        class User32:
            def OpenInputDesktop(self,*args): return 1
            def IsWindowVisible(self,*args): return True
            def GetWindowThreadProcessId(self,hwnd,pid): pid._obj.value=999999
            def GetWindowTextLengthW(self,*args): return len('FixtureWindow  ')
            def GetWindowTextW(self,hwnd,buffer,length): buffer.value='FixtureWindow  '
            def GetWindowRect(self,hwnd,rect): rect._obj.right=1280;rect._obj.bottom=720
            def EnumDesktopWindows(self,desktop,callback,arg): callback(2468,0)
            def CloseDesktop(self,*args): pass
        with patch.object(studio.ctypes.windll,'user32',User32()):
            windows=studio.get_desktop_capture_windows()
        self.assertEqual(windows[0]['title'],'FixtureWindow  ')

    def test_explicit_display_source_remains_visible_when_game_layer_disabled(self):
        view=SimpleNamespace(canvas=Mock(),txt_telemetry=Mock(),scenes_sources=SimpleNamespace(sources_list=[{'type':'game','enabled':False},{'type':'screen','enabled':True}]))
        studio.UniversalOmniStudioNativeView._on_source_toggled(view,'Screen / Display Capture',True)
        view.canvas.set_game_capture_enabled.assert_called_with(True)
        view.canvas.set_desktop_capture_enabled.assert_called_with(True)

    def widget(self, cfg):
        with patch.object(profiles.StreamProfileManager, 'load', return_value=copy.deepcopy(cfg)), \
                patch.object(studio, 'PlatformPingProbeThread', side_effect=AssertionError('Probe thread forbidden')):
            widget = studio.MultiRtmpSettingsWidget()
        self.addCleanup(widget.deleteLater)
        self.addCleanup(widget.shutdown)
        return widget

    def test_saved_setup_refreshes_destinations_and_encoder_controls(self):
        initial = self.fixture_config()
        for destination in initial['destinations'].values():
            destination['enabled'] = True
        widget = self.widget(initial)
        saved = self.fixture_config()
        saved['encoder'].update(codec='x264 (CPU High-Profile)', resolution='3840x2160', bitrate_kbps=15000)
        current = [initial]

        class Dialog:
            def __init__(self):
                self.profile_applied = _Signal()
                self.cfg = saved
            def exec(self):
                current[0] = saved
                self.profile_applied.emit(copy.deepcopy(saved))
                return QDialog.DialogCode.Accepted
            def get_selected_platform_profile(self):
                # Choosing the setup defaults must not override saved target flags.
                return 'Twitch'

        with patch.object(studio, 'StreamRequirementsDialog', return_value=Dialog()), \
                patch.object(profiles.StreamProfileManager, 'load', side_effect=lambda: copy.deepcopy(current[0])):
            widget._open_requirements_dialog()
        enabled = {name for name, checkbox in widget.dest_checkboxes.items() if checkbox.isChecked()}
        self.assertEqual(enabled, {'facebook'})
        self.assertIn('x264', widget.combo_codec.currentText().lower())
        self.assertTrue(widget.combo_res.currentText().startswith('3840x2160'))
        self.assertIn('15,000', widget.combo_bitrate.currentText())

    def test_encoder_preset_never_implicitly_enables_extra_destinations(self):
        widget = self.widget(self.fixture_config())
        before = {name: checkbox.isChecked() for name, checkbox in widget.dest_checkboxes.items()}
        widget.apply_platform_preset('Twitch')
        self.assertEqual({name: checkbox.isChecked() for name, checkbox in widget.dest_checkboxes.items()}, before)

    def test_selected_window_handle_and_title_are_carried_to_daemon_payload(self):
        cfg = self.fixture_config()
        settings = self.widget(cfg)
        view = SimpleNamespace(
            rtmp_settings=settings,
            combo_fps=SimpleNamespace(currentText=lambda: '60 FPS'),
            canvas=Mock(), txt_telemetry=Mock(),
            scenes_sources=SimpleNamespace(sources_list=[{'type': 'game', 'enabled': True}]),
        )
        studio.UniversalOmniStudioNativeView._on_game_selected(view, 'FixtureWindow', 2468)
        with patch.object(profiles.StreamProfileManager, 'load', return_value=copy.deepcopy(cfg)):
            payload = studio.UniversalOmniStudioNativeView._stream_payload(view)
        self.assertEqual(payload.get('game_name'), 'FixtureWindow')
        self.assertIn({'type': 'window', 'hwnd': 2468, 'name': 'FixtureWindow', 'enabled': True}, payload.get('sources', []))
        self.assertFalse(any(source.get('type') in {'screen', 'desktop'} for source in payload.get('sources', [])))

    def test_window_selection_emits_raw_win32_title_for_exact_identity(self):
        rows = [{'hwnd': 2468, 'title': 'FixtureWindow', 'width': 1280, 'height': 720, 'pid': 77}]
        with patch.object(studio, 'get_desktop_capture_windows', return_value=rows), \
                patch.object(studio.urllib.request, 'urlopen', side_effect=AssertionError('No service probe allowed')):
            widget = studio.ActiveGameDiscoveryWidget(bus=None)
            widget._poller.stop()
            self.addCleanup(widget.deleteLater)
            self.addCleanup(widget.shutdown)
            events = []
            widget.game_selected.connect(lambda title, hwnd: events.append((title, hwnd)))
            self.assertEqual(widget.combo_games.itemText(1), '🎮 FixtureWindow (1280x720)')
            widget.combo_games.setCurrentIndex(1)
        self.assertEqual(events[-1], ('FixtureWindow', 2468))


if __name__ == '__main__':
    unittest.main()
