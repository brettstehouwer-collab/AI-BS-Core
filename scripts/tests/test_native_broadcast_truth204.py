"""Offline Qt fixtures. No screen capture, external dispatch, or user credentials."""
import ast
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QTextEdit, QDialog
from native_studio import broadcast_stream_engine as profiles
from native_studio import omni_broadcast_studio as studio

ROOT = Path(__file__).resolve().parents[2]


class NativeBroadcastTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self):
        with patch.object(profiles.StreamProfileManager, 'load', return_value=profiles.StreamProfileManager.get_defaults()):
            dialog = profiles.StreamRequirementsDialog()
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_dialog_does_not_invent_daemon_readiness(self):
        dialog = self.dialog()
        self.assertNotIn('14 Core', dialog.lbl_status.text())
        self.assertIn('not checked', dialog.lbl_status.text().lower())

    def test_failed_save_keeps_dialog_open_and_does_not_emit_success(self):
        dialog = self.dialog(); emitted = []
        dialog.profile_applied.connect(emitted.append)
        with patch.object(profiles.StreamProfileManager, 'save', return_value=False):
            dialog._apply_and_close()
        self.assertEqual(emitted, [])
        self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertIn('failed', dialog.lbl_status.text().lower())

    def test_network_fields_roundtrip_without_claiming_live_application(self):
        dialog = self.dialog()
        dialog.combo_delay.setCurrentIndex(2)
        dialog.chk_auto_rec.setChecked(False)
        dialog.spin_rec_interval.setValue(9)
        dialog.spin_max_retries.setValue(4)
        with patch.object(profiles.StreamProfileManager, 'save', return_value=True) as save:
            dialog._save_and_apply()
        network = save.call_args.args[0]['network']
        self.assertEqual(network['stream_delay_sec'], 30)
        self.assertFalse(network['auto_reconnect'])
        self.assertEqual(network['retry_delay_sec'], 9)
        self.assertEqual(network['max_retries'], 4)
        self.assertIn('not applied', dialog.lbl_status.text().lower())

    def test_platform_profile_uses_combo_keyframe_without_attribute_error(self):
        dialog = self.dialog()
        with patch.object(profiles.QMessageBox, 'information'):
            dialog._apply_platform_profile_to_encoder()
        self.assertEqual(dialog.spin_bitrate.value(), 6000)

    def test_facebook_credentials_control_is_present_and_masked(self):
        dialog = self.dialog()
        self.assertTrue(hasattr(dialog, 'edit_fb_key'))
        self.assertEqual(dialog.edit_fb_key.echoMode(), profiles.QLineEdit.EchoMode.Password)
        self.assertTrue(dialog.edit_fb_url.text().startswith('rtmps://'))

    def test_audio_meters_have_no_random_measurements(self):
        mixer = studio.AdvancedAudioMixerWidget()
        self.addCleanup(mixer.deleteLater); self.addCleanup(mixer.shutdown)
        with patch.object(studio.random, 'random', side_effect=AssertionError('fake audio')):
            mixer._animate_vu_meters()
        self.assertIn('not measured', ' '.join(x.text() for x in mixer.findChildren(QLabel)).lower())

    def test_record_control_has_actual_dispatch_and_no_fabricated_file(self):
        tree = ast.parse((ROOT/'native_studio/omni_broadcast_studio.py').read_text(encoding='utf-8-sig'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name=='UniversalOmniStudioNativeView')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name=='_toggle_record')
        text = ast.unparse(method)
        self.assertIn('_dispatch_broadcast', text)
        self.assertNotIn('master_', text)

    def test_dispatch_does_not_optimistically_set_live(self):
        view = self.fake_view()
        studio.UniversalOmniStudioNativeView._toggle_stream(view)
        self.assertFalse(view._is_streaming)
        self.assertEqual(len(view.bus.jobs), 1)
        self.assertFalse(view.btn_stream.isEnabled())
        job = view.bus.jobs.pop(); job['on_result']({'status':'error'})
        self.assertFalse(view._is_streaming)
        self.assertIn('unverified', view.txt_telemetry.toPlainText().lower())
        self.assertTrue(view.btn_stream.isEnabled())

    def test_acknowledged_start_and_failed_stop_preserve_last_confirmed_state(self):
        view = self.fake_view()
        studio.UniversalOmniStudioNativeView._toggle_stream(view)
        view.bus.jobs.pop()['on_result']({'status':'streaming'})
        self.assertTrue(view._is_streaming)
        studio.UniversalOmniStudioNativeView._toggle_stream(view)
        view.bus.jobs.pop()['on_error']('fixture transport unavailable')
        self.assertTrue(view._is_streaming)
        self.assertIn('unverified', view.txt_telemetry.toPlainText().lower())

    def test_lost_start_acknowledgement_offers_stop_instead_of_duplicate_start(self):
        view=self.fake_view()
        studio.UniversalOmniStudioNativeView._toggle_stream(view)
        view.bus.jobs.pop()['on_error']('fixture timeout after dispatch')
        self.assertTrue(view._is_streaming)
        self.assertIn('stop',view.btn_stream.text().lower())
        self.assertIn('unverified',view.txt_telemetry.toPlainText().lower())

    def test_unreadable_original_profile_is_not_overwritten_by_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'profiles.json';target.write_bytes(b'{broken historical evidence')
            before=target.read_bytes()
            with patch.object(profiles.StreamProfileManager,'PROFILE_FILE',target):
                self.assertFalse(profiles.StreamProfileManager.save(profiles.StreamProfileManager.get_defaults()))
            self.assertEqual(target.read_bytes(),before)

    def test_unavailable_protected_key_survives_attempted_save(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'profiles.json'
            data=profiles.StreamProfileManager.get_defaults()
            data['destinations']['facebook'].update(key_dpapi='invalid-fixture-cipher',key='')
            target.write_text(json.dumps(data));before=target.read_bytes()
            with patch.object(profiles.StreamProfileManager,'PROFILE_FILE',target):
                loaded=profiles.StreamProfileManager.load()
                self.assertFalse(profiles.StreamProfileManager.save(loaded))
            self.assertEqual(target.read_bytes(),before)

    def fake_view(self):
        class Bus:
            def __init__(self): self.jobs=[]
            def submit(self, fn, *args, **kwargs): self.jobs.append(kwargs)
        view=SimpleNamespace(bus=Bus(),_is_streaming=False,_is_recording=False,
            btn_stream=QPushButton(),btn_record=QPushButton(),canvas=Mock(),txt_telemetry=QTextEdit())
        self.addCleanup(view.btn_stream.deleteLater);self.addCleanup(view.btn_record.deleteLater);self.addCleanup(view.txt_telemetry.deleteLater)
        view._dispatch_broadcast=lambda *a: studio.UniversalOmniStudioNativeView._dispatch_broadcast(view,*a)
        view._stream_payload=lambda: {'endpoints':[{'name':'fixture','enabled':True,'url':'rtmps://example.invalid/live','key':'fixture-only'}]}
        return view

    def test_atomic_profile_write_failure_preserves_original_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'profiles.json';target.write_text('{"custom":"original"}')
            before=target.read_bytes()
            with patch.object(profiles.StreamProfileManager, 'PROFILE_FILE', target), patch.object(profiles.os, 'replace', side_effect=OSError('fixture failure')):
                self.assertFalse(profiles.StreamProfileManager.save({'custom':'new'}))
            self.assertEqual(target.read_bytes(),before)

    def test_profile_keys_are_protected_and_roundtrip_with_local_dpapi(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'profiles.json'
            data=profiles.StreamProfileManager.get_defaults()
            data['destinations']['facebook']['key']='synthetic-credential-only'
            with patch.object(profiles.StreamProfileManager,'PROFILE_FILE',target):
                self.assertTrue(profiles.StreamProfileManager.save(data))
                self.assertNotIn('synthetic-credential-only',target.read_text())
                self.assertEqual(profiles.StreamProfileManager.load()['destinations']['facebook']['key'],'synthetic-credential-only')
            self.assertEqual(data['destinations']['facebook']['key'],'synthetic-credential-only')

    def test_payload_uses_configured_facebook_endpoint_and_no_default_dispatch(self):
        from native_studio.broadcast_control import stream_payload
        cfg=profiles.StreamProfileManager.get_defaults()
        with self.assertRaises(ValueError): stream_payload(cfg)
        cfg['destinations']['facebook'].update(enabled=True,url='rtmps://example.invalid:443/rtmp/',key='fixture-only')
        payload=stream_payload(cfg)
        self.assertEqual(payload['endpoints'][0]['url'],'rtmps://example.invalid:443/rtmp/')
        self.assertEqual(payload['encoder'],'h264_nvenc')
        self.assertEqual(payload['endpoints'][0]['key'],'fixture-only')

    def test_requested_broadcast_delay_is_held_until_enforced_by_backend(self):
        from native_studio.broadcast_control import stream_payload
        cfg=profiles.StreamProfileManager.get_defaults()
        cfg['destinations']['facebook'].update(enabled=True,url='rtmps://example.invalid/live',key='fixture-only')
        cfg['network']['stream_delay_sec']=30
        with self.assertRaises(ValueError): stream_payload(cfg)

    def test_canvas_does_not_seed_measured_encoder_latency(self):
        canvas=studio.LiveBroadcastCanvas();self.addCleanup(canvas.deleteLater);self.addCleanup(canvas.shutdown)
        self.assertIn('not measured',canvas.latency_text.lower())

    def test_meeting_page_has_no_fictitious_sessions_or_enabled_dead_controls(self):
        page=studio.VideoMeetingsWebRtcWidget();self.addCleanup(page.deleteLater)
        self.assertEqual(page.findChild(studio.QTableWidget).rowCount(),0)
        self.assertTrue(all(not b.isEnabled() for b in page.findChildren(QPushButton)))
        self.assertNotIn('Feed Active',' '.join(x.text() for x in page.findChildren(QLabel)))

    def test_complete_native_broadcast_view_constructs_without_desktop_or_network_actions(self):
        class Bus:
            def submit(self,*args,**kwargs): pass
        with patch.object(profiles.StreamProfileManager,'load',return_value=profiles.StreamProfileManager.get_defaults()), patch.object(studio,'get_desktop_capture_windows',return_value=[]), patch.object(studio.urllib.request,'urlopen',side_effect=AssertionError('network prohibited')) as network, patch.object(studio.subprocess,'Popen',side_effect=AssertionError('process prohibited')) as process:
            view=studio.UniversalOmniStudioNativeView(Bus())
        self.addCleanup(view.deleteLater);self.addCleanup(view.shutdown)
        self.assertEqual(network.call_count,0);self.assertEqual(process.call_count,0)
        labels=' '.join(x.text() for x in view.findChildren(QLabel))
        self.assertNotIn('0.3ms',labels);self.assertNotIn('4455: READY',labels)
        self.assertTrue(all(not ch.isChecked() for ch in view.rtmp_settings.dest_checkboxes.values()))


if __name__=='__main__': unittest.main()
