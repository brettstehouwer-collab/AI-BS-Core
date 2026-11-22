"""Pure native/client fixtures: no real IPC, process, screen, key or network I/O."""
from __future__ import annotations
import ast
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
import native_studio
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]

def load_client():
    path = ROOT/'native_studio/broadcast_secondary_control.py'
    spec = importlib.util.spec_from_file_location('_audit_native_coordinator207', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class NativeDispatchComposition207Tests(unittest.TestCase):
    def test_start_uses_secondary_client_and_never_launches_legacy_8005(self):
        from native_studio import broadcast_control, broadcast_service
        client = ModuleType('native_studio.broadcast_secondary_control')
        client.start_broadcast = Mock(return_value={'status':'starting','active':True})
        payload = {'source_mode':'auto_game','source':None,'targets':['youtube']}
        with patch.dict(sys.modules, {'native_studio.broadcast_secondary_control':client}), \
             patch.object(native_studio,'broadcast_secondary_control',client,create=True), \
             patch.object(broadcast_service, 'ensure_broadcast_service_online', side_effect=AssertionError('legacy startup')), \
             patch.object(broadcast_control.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            self.assertEqual(broadcast_control.send_broadcast_command('stream', True, payload)['status'], 'starting')
        client.start_broadcast.assert_called_once_with(payload)

    def test_stop_uses_same_secondary_client_and_no_http(self):
        from native_studio import broadcast_control
        client = ModuleType('native_studio.broadcast_secondary_control')
        client.stop_broadcast = Mock(return_value={'status':'stopping','active':True})
        with patch.dict(sys.modules, {'native_studio.broadcast_secondary_control':client}), \
             patch.object(native_studio,'broadcast_secondary_control',client,create=True), \
             patch.object(broadcast_control.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            self.assertEqual(broadcast_control.send_broadcast_command('stream', False, {})['status'], 'stopping')
        client.stop_broadcast.assert_called_once_with()

    def test_archive_button_explains_shared_archive_without_legacy_dispatch(self):
        from native_studio import broadcast_control
        with patch.object(broadcast_control.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            self.assertEqual(broadcast_control.send_broadcast_command('record', True, {})['status'], 'archive_accompanies_broadcast')

class NativeClientContract207Tests(unittest.TestCase):
    def setUp(self): self.client = load_client()

    def test_client_does_not_import_backend_or_probe_hardware(self):
        text = (ROOT/'native_studio/broadcast_secondary_control.py').read_text()
        tree = ast.parse(text)
        self.assertFalse(any(isinstance(n, ast.ImportFrom) and (n.module or '').startswith('backend') for n in ast.walk(tree)))
        self.assertNotIn('detect_optimal_encoder', text)

    def test_auto_window_screen_are_explicit_and_exact(self):
        self.assertIsNone(self.client.validate_source('auto_game', None))
        identity = {'hwnd':207,'pid':900,'title':'Fortnite  '}
        self.assertEqual(self.client.validate_source('window', identity), identity)
        self.assertEqual(self.client.validate_source('screen', {'screen_id':'DISPLAY1'}), {'screen_id':'DISPLAY1'})
        for mode, source in [('window',None),('window',{'hwnd':0,'pid':900,'title':'x'}),('window',{'hwnd':207,'pid':True,'title':'x'}),('auto_game',identity),('screen',{}),('screen',{'screen_id':''}),('foreground',None)]:
            with self.subTest(mode=mode, source=source):
                with self.assertRaises(ValueError): self.client.validate_source(mode, source)

    def test_commands_are_secret_free_and_fixed(self):
        command = self.client.coordinator_command({'source_mode':'auto_game','source':None,'targets':['youtube','facebook']})
        self.assertEqual(command[1:6], ['-B','-m','backend.core.broadcast_secondary','--source-mode','auto_game'])
        self.assertEqual(command[-3:], ['--targets','youtube','facebook'])
        with self.assertRaises(ValueError):
            self.client.coordinator_command({'source_mode':'auto_game','source':None,'targets':['youtube'],'key':'synthetic-secret'})

    def test_window_cli_preserves_raw_caption_and_no_automatic_fallback(self):
        command = self.client.coordinator_command({'source_mode':'window','source':{'hwnd':207,'pid':900,'title':'Fortnite  '},'targets':['youtube']})
        self.assertEqual(command[command.index('--title')+1], 'Fortnite  ')
        self.assertNotIn('desktop', command)

    def test_legacy_requires_verified_owner_and_never_claims_ingest(self):
        raw = {'status':'running_unverified','encoder_pid':207,'process_running':True,'frames_encoded':60}
        with patch.object(self.client, '_read_status', return_value=(raw,True)), patch.object(self.client, '_verified_owner', return_value={'controller_pid':900,'encoder_pid':207}):
            status = self.client.read_broadcast_status()
        self.assertEqual(status['status'], 'legacy_upgrade_required')
        self.assertTrue(status['active']); self.assertFalse(status['can_select'])
        self.assertFalse(status['ingest_verified'])
        with patch.object(self.client, '_read_status', return_value=(raw,True)), patch.object(self.client, '_verified_owner', return_value=None):
            self.assertEqual(self.client.read_broadcast_status()['status'], 'owner_unverified')

    def test_protocol2_holding_is_visible_and_not_game_live(self):
        raw = {'protocol_version':2,'session_id':'a'*32,'status':'running_unverified','source_mode':'auto_game','capture_state':'holding','game_frame_verified':False,'audio_mode':'generated_silence','encoder_pid':207,'controller_pid':900}
        with patch.object(self.client, '_read_status', return_value=(raw,True)), patch.object(self.client, '_verified_owner', return_value={'controller_pid':900,'encoder_pid':207}):
            status = self.client.read_broadcast_status()
        self.assertEqual(status['capture_state'],'holding')
        self.assertFalse(status['game_frame_verified']);self.assertTrue(status['can_select'])

    def test_stale_owned_status_keeps_stop_available_but_holds_source_changes(self):
        raw = {'protocol_version':2,'session_id':'a'*32,'status':'running_unverified','encoder_pid':207,'controller_pid':900}
        with patch.object(self.client, '_read_status', return_value=(raw,False)), patch.object(self.client, '_verified_owner', return_value={'controller_pid':900,'encoder_pid':207}):
            status = self.client.read_broadcast_status()
        self.assertTrue(status['active']);self.assertTrue(status['can_stop']);self.assertFalse(status['can_select'])
        self.assertEqual(status['status'],'status_stale')

    def test_select_serialization_composes_exact_backend_contract(self):
        state = {'active':True,'can_select':True,'session_id':'a'*32,'status':'running_unverified'}
        with tempfile.TemporaryDirectory(prefix='native_ipc207_') as folder:
            target = Path(folder)/'command.json'
            with patch.object(self.client,'COMMAND',target), patch.object(self.client,'read_broadcast_status',return_value=state), \
                 patch.object(self.client,'ipc_paths',return_value={'command':target},create=True), \
                 patch.object(self.client,'write_private_json',side_effect=lambda path,data:path.write_text(json.dumps(data)),create=True):
                result = self.client.select_broadcast_source('window',{'hwnd':207,'pid':900,'title':'Fortnite  '})
            command = json.loads(target.read_text())
            self.assertEqual(set(command), {'version','request_id','session_id','action','source_mode','source'})
            self.assertEqual(command['version'],2);self.assertEqual(command['session_id'],'a'*32)
            self.assertEqual(command['source']['title'],'Fortnite  ')
            self.assertEqual(result['status'],'pending')
            self.assertEqual(len(command['request_id']),32)
            self.assertLess(len(target.read_bytes()),16384)
            from backend.core.broadcast_secondary import validate_control_command
            self.assertEqual(validate_control_command(command,'a'*32),command)

    def test_legacy_source_change_does_not_write_or_spawn(self):
        with patch.object(self.client,'read_broadcast_status',return_value={'status':'legacy_upgrade_required','active':True,'can_select':False}), \
             patch.object(self.client,'_atomic_json',side_effect=AssertionError('write')), patch.object(self.client,'_spawn',side_effect=AssertionError('spawn')):
            self.assertEqual(self.client.select_broadcast_source('auto_game',None)['status'],'legacy_upgrade_required')

    def test_unverified_owner_cannot_stop(self):
        with patch.object(self.client,'read_broadcast_status',return_value={'status':'owner_unverified','active':False,'can_stop':False}), patch.object(self.client,'_atomic_json',side_effect=AssertionError('write')):
            self.assertEqual(self.client.stop_broadcast()['status'],'owner_unverified')

    def test_stop_is_session_scoped_and_does_not_force_kill(self):
        state={'status':'running_unverified','active':True,'can_stop':True,'protocol_version':2,'session_id':'a'*32}
        with tempfile.TemporaryDirectory(prefix='native_stop207_') as folder:
            target=Path(folder)/'stop.json'
            with patch.object(self.client,'STOP',target),patch.object(self.client,'read_broadcast_status',return_value=state), \
                 patch.object(self.client,'ipc_paths',return_value={'stop':target},create=True), \
                 patch.object(self.client,'write_private_json',side_effect=lambda path,data:path.write_text(json.dumps(data)),create=True):
                self.assertEqual(self.client.stop_broadcast()['status'],'stopping')
            self.assertEqual(json.loads(target.read_text())['session_id'],'a'*32)

    def test_existing_controller_prevents_duplicate_start(self):
        with patch.object(self.client,'read_broadcast_status',return_value={'status':'legacy_upgrade_required','active':True}),patch.object(self.client,'_spawn',side_effect=AssertionError('duplicate')):
            self.assertEqual(self.client.start_broadcast({'source_mode':'auto_game','source':None,'targets':['youtube']})['status'],'legacy_upgrade_required')

    def test_controller_in_other_working_directory_is_not_adopted(self):
        command = self.client.coordinator_command({'source_mode':'auto_game','source':None,'targets':['youtube']})
        process = SimpleNamespace(is_running=lambda:True,cmdline=lambda:command,exe=lambda:str(self.client.PYTHON),cwd=lambda:'C:/UnrelatedProject')
        self.assertFalse(self.client._controller_owned(process))

    def test_modern_status_uses_private_validated_reader(self):
        with tempfile.TemporaryDirectory(prefix='native_private207_') as folder:
            target=Path(folder)/'private_status.json';target.write_text('{}')
            legacy=Path(folder)/'legacy_status.json';legacy.write_text('{"legacy_fixture":true}')
            with patch.object(self.client,'ipc_paths',return_value={'status':target},create=True), \
                 patch.object(self.client,'STATUS',legacy), \
                 patch.object(self.client,'read_private_json',return_value={'protocol_version':2},create=True) as read:
                raw,_=self.client._read_status()
            self.assertEqual(raw,{'protocol_version':2});read.assert_called_once_with(target)

    def test_shared_legacy_status_cannot_claim_modern_protocol(self):
        with tempfile.TemporaryDirectory(prefix='native_legacy207_') as folder:
            target=Path(folder)/'shared_status.json';target.write_text('{"protocol_version":2}')
            with patch.object(self.client,'STATUS',target),patch.object(self.client,'ipc_paths',return_value={'status':Path(folder)/'absent.json'},create=True):
                with self.assertRaises(ValueError):self.client._read_status()

    def test_dead_private_status_does_not_hide_verified_legacy_sender(self):
        modern={'protocol_version':2,'session_id':'a'*32,'status':'failed','process_running':False}
        legacy={'status':'running_unverified','encoder_pid':207,'process_running':True}
        with patch.object(self.client,'_read_status',return_value=(modern,False)), \
             patch.object(self.client,'_verified_owner',side_effect=lambda raw: {'controller_pid':900,'encoder_pid':207} if raw is legacy else None), \
             patch.object(self.client,'_read_legacy_status',return_value=(legacy,True),create=True):
            result=self.client.read_broadcast_status()
        self.assertEqual(result['status'],'legacy_upgrade_required');self.assertTrue(result['can_stop'])
        self.assertFalse(result['can_select']);self.assertNotIn('session_id',result)

    def test_failed_dead_controller_can_be_retried_without_duplicate(self):
        raw={'status':'failed','process_running':False}
        @contextmanager
        def lock(): yield
        with patch.object(self.client,'_read_status',return_value=(raw,False)),patch.object(self.client,'_verified_owner',return_value=None):
            self.assertTrue(self.client.read_broadcast_status()['can_start'])
            with patch.object(self.client,'_start_lock',lock),patch.object(self.client,'_existing_controller',return_value=True),patch.object(self.client,'_spawn',side_effect=AssertionError('duplicate')):
                self.assertEqual(self.client.start_broadcast({'source_mode':'auto_game','source':None,'targets':['youtube']})['status'],'controller_present')

def ui_method(class_name, name):
    tree=ast.parse((ROOT/'native_studio/omni_broadcast_studio.py').read_text(encoding='utf-8-sig'))
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name==class_name)
    method=next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name==name)
    ns={'time':SimpleNamespace(strftime=lambda _: 'fixture'), 'validate_source':load_client().validate_source,
        'json':json,'urllib':SimpleNamespace(request=SimpleNamespace(Request=Mock(),urlopen=Mock())),
        'StreamProfileManager':SimpleNamespace(load=Mock(side_effect=AssertionError('profile/key access'))),
        'read_broadcast_status':Mock(), 'select_broadcast_source':Mock(), 'send_broadcast_command':Mock()}
    exec(compile(ast.Module([method],type_ignores=[]),str(ROOT/'native_studio/omni_broadcast_studio.py'),'exec'),ns)
    return ns[name],ns

class NativeCoordinatorUi207Tests(unittest.TestCase):
    def payload_view(self,mode='auto_game',source=None):
        return SimpleNamespace(game_discovery=SimpleNamespace(source_selection=lambda:(mode,source)),
            rtmp_settings=SimpleNamespace(dest_checkboxes={'youtube':SimpleNamespace(isChecked=lambda:True)}),
            scenes_sources=SimpleNamespace(sources_list=[{'type':'mic','enabled':True}]))

    def test_auto_payload_needs_no_window_and_reads_no_keys(self):
        method,_=ui_method('UniversalOmniStudioNativeView','_stream_payload')
        self.assertEqual(method(self.payload_view()),{'source_mode':'auto_game','source':None,'targets':['youtube']})

    def test_manual_payload_preserves_exact_identity_and_has_no_audio_request(self):
        method,_=ui_method('UniversalOmniStudioNativeView','_stream_payload')
        identity={'hwnd':207,'pid':900,'title':'Fortnite  '}
        result=method(self.payload_view('window',identity))
        self.assertEqual(result,{'source_mode':'window','source':identity,'targets':['youtube']})
        self.assertNotIn('mic',json.dumps(result));self.assertNotIn('key',result)

    def test_explicit_screen_draft_is_distinct_from_auto_and_can_be_held(self):
        method,_=ui_method('UniversalOmniStudioNativeView','_stream_payload')
        result=method(self.payload_view('screen',{'screen_id':'DISPLAY1'}))
        self.assertEqual(result['source_mode'],'screen');self.assertEqual(result['source'],{'screen_id':'DISPLAY1'})

    def state_view(self):
        return SimpleNamespace(_stream_request_pending=False,btn_stream=Mock(),canvas=Mock(),
            lbl_broadcast_status=Mock(),lbl_silent_audio=Mock(),_coordinator_status={},_is_streaming=False)

    def test_legacy_owner_visible_stop_only_upgrade_required(self):
        method,_=ui_method('UniversalOmniStudioNativeView','_apply_broadcast_status')
        view=self.state_view();method(view,{'status':'legacy_upgrade_required','active':True,'can_stop':True,'can_select':False})
        self.assertTrue(view._is_streaming)
        self.assertIn('Stop',view.btn_stream.setText.call_args.args[0])
        self.assertIn('upgrade',view.lbl_broadcast_status.setText.call_args.args[0].lower())

    def test_holding_does_not_claim_game_capture_or_ingest(self):
        method,_=ui_method('UniversalOmniStudioNativeView','_apply_broadcast_status')
        view=self.state_view();method(view,{'status':'running_unverified','active':True,'can_stop':True,'can_select':True,'capture_state':'holding','source_mode':'auto_game','game_frame_verified':False})
        text=view.lbl_broadcast_status.setText.call_args.args[0].lower()
        self.assertIn('holding',text);self.assertIn('silent',text)
        self.assertNotIn('game live',text)

    def test_window_choice_does_not_start_unsafe_local_preview(self):
        method,_=ui_method('UniversalOmniStudioNativeView','_on_game_selected')
        view=SimpleNamespace(game_discovery=SimpleNamespace(_window_pid_by_handle={207:900}),canvas=Mock(),txt_telemetry=Mock())
        method(view,'Fortnite  ',207)
        self.assertFalse(any(call.args and call.args[0]==207 for call in view.canvas.set_target_window.call_args_list))

    def test_archive_button_reports_shared_archive_instead_of_dispatching_legacy(self):
        method,_=ui_method('UniversalOmniStudioNativeView','_toggle_record')
        view=SimpleNamespace(_is_recording=False,_dispatch_broadcast=Mock(),txt_telemetry=Mock())
        method(view)
        view._dispatch_broadcast.assert_not_called()
        self.assertIn('archive',view.txt_telemetry.append.call_args.args[0].lower())

    def test_local_scene_switch_never_dispatches_legacy_requests_on_gui_thread(self):
        method,ns=ui_method('UniversalOmniStudioNativeView','_on_scene_switched')
        view=SimpleNamespace(canvas=Mock(),txt_telemetry=Mock())
        method(view,'Fixture scene')
        ns['urllib'].request.urlopen.assert_not_called()

class NativeDesktopHandle207Tests(unittest.TestCase):
    def test_owned_desktop_handle_closes_after_success_and_failure(self):
        import ctypes
        from ctypes import wintypes
        tree=ast.parse((ROOT/'native_studio/omni_broadcast_studio.py').read_text(encoding='utf-8-sig'))
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_desktop_capture_windows')
        for fail in (False,True):
            api=SimpleNamespace(OpenInputDesktop=Mock(return_value=207),CloseDesktop=Mock(),
                                EnumDesktopWindows=Mock(side_effect=RuntimeError('fixture') if fail else None))
            fake=SimpleNamespace(windll=SimpleNamespace(user32=api),WINFUNCTYPE=lambda *args:lambda fn:fn)
            ns={'sys':SimpleNamespace(platform='win32'),'ctypes':fake,'wintypes':wintypes,'os':SimpleNamespace(getpid=lambda:900),
                'List':list,'Dict':dict,'Any':object}
            exec(compile(ast.Module([node],type_ignores=[]),'desktop_handle_fixture','exec'),ns)
            self.assertEqual(ns[node.name](),[])
            api.CloseDesktop.assert_called_once_with(207)

class NativeCoordinatorOffscreen207Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont,QFontDatabase
        from native_studio.theme import STYLESHEET
        cls.app=QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
        cls.app.setFont(QFont('Segoe UI',9));cls.app.setStyleSheet(STYLESHEET)

    def view(self):
        from native_studio import omni_broadcast_studio as studio
        from native_studio import broadcast_stream_engine as profiles
        class Bus:
            def __init__(self):self.jobs=[]
            def submit(self,fn,*args,**kwargs):self.jobs.append((fn,args,kwargs))
        bus=Bus()
        rows=[{'hwnd':207,'pid':900,'title':'Fortnite  ','width':1280,'height':720}]
        with patch.object(profiles.StreamProfileManager,'load',side_effect=profiles.StreamProfileManager.get_defaults), \
             patch.object(studio,'get_desktop_capture_windows',return_value=rows), \
             patch.object(studio.QGuiApplication,'screens',return_value=[SimpleNamespace(name=lambda:'DISPLAY1')]):
            view=studio.UniversalOmniStudioNativeView(bus)
        self.addCleanup(view.deleteLater);self.addCleanup(view.shutdown)
        return view,bus,studio

    def test_launch_only_queues_readonly_status_and_displays_actual_fixed_profile(self):
        view,bus,studio=self.view()
        self.assertEqual([job[0] for job in bus.jobs],[studio.read_broadcast_status])
        self.assertEqual(view.game_discovery.source_selection(),('auto_game',None))
        self.assertEqual(view.combo_fps.currentText(),'30 FPS');self.assertFalse(view.combo_fps.isEnabled())
        self.assertTrue(view.rtmp_settings.combo_res.currentText().startswith('1280x720'))
        self.assertFalse(view.rtmp_settings.combo_codec.isEnabled());self.assertFalse(view.audio_mixer.isEnabled())
        self.assertIn('Silent audio',view.lbl_broadcast_status.text())

    def test_manual_window_survives_return_to_auto_and_back_without_dispatch(self):
        view,bus,_=self.view();picker=view.game_discovery
        picker.combo_source_mode.setCurrentIndex(1);picker.combo_games.setCurrentIndex(1)
        expected=('window',{'hwnd':207,'pid':900,'title':'Fortnite  '})
        self.assertEqual(picker.source_selection(),expected)
        picker.chk_auto.setChecked(True);self.assertEqual(picker.source_selection(),('auto_game',None))
        picker.chk_auto.setChecked(False);self.assertEqual(picker.source_selection(),expected)
        self.assertEqual(len(bus.jobs),1);self.assertFalse(view.canvas._capture_timer.isActive())

    def test_screen_requires_explicit_id_and_holding_status_never_claims_sharing(self):
        view,bus,_=self.view();picker=view.game_discovery
        picker.combo_source_mode.setCurrentIndex(2)
        with self.assertRaises(ValueError):picker.source_selection()
        picker.combo_screens.setCurrentIndex(1);self.assertEqual(picker.source_selection(),('screen',{'screen_id':'DISPLAY1'}))
        view._apply_broadcast_status({'status':'running_unverified','active':True,'can_stop':True,'can_select':True,'source_mode':'screen','capture_state':'holding','game_frame_verified':False})
        self.assertIn('unsupported',view.lbl_broadcast_status.text());self.assertIn('Holding black',view.lbl_broadcast_status.text())
        self.assertFalse(view.canvas._capture_timer.isActive());self.assertEqual(len(bus.jobs),1)

    def test_apply_waits_for_matching_ack_and_does_not_start_another_encoder(self):
        view,bus,studio=self.view();picker=view.game_discovery
        picker.combo_source_mode.setCurrentIndex(1);picker.combo_games.setCurrentIndex(1)
        view._coordinator_status={'active':True,'can_select':True}
        view.btn_apply_source.click()
        self.assertEqual(len(bus.jobs),2)
        fn,args,callbacks=bus.jobs[-1]
        self.assertIs(fn,studio.select_broadcast_source)
        self.assertEqual(args,('window',{'hwnd':207,'pid':900,'title':'Fortnite  '}))
        self.assertFalse(view.btn_apply_source.isEnabled())
        callbacks['on_result']({'status':'pending','request_id':'b'*32})
        view._apply_broadcast_status({'status':'running_unverified','active':True,'can_stop':True,'can_select':True,'source_mode':'window','capture_state':'holding','game_frame_verified':False,'last_command_id':'b'*32,'command_status':'applied'})
        self.assertTrue(view.btn_apply_source.isEnabled());self.assertFalse(view._source_request_pending)

    def test_coordinator_canvas_paints_unavailable_and_actual_output_without_invented_stats(self):
        view,_bus,studio=self.view()
        painter=Mock();factory=Mock(return_value=painter)
        with patch.object(studio,'QPainter',factory):view.canvas.paintEvent(None)
        labels=[call.args[-1] for call in painter.drawText.call_args_list if call.args and isinstance(call.args[-1],str)]
        self.assertIn('Preview unavailable',labels)
        self.assertIn('Output 1280x720 30 FPS',labels)
        self.assertFalse(any('60 FPS' in text or '1920x1080' in text or 'PREVIEW 60' in text for text in labels))

    def test_unsupported_coordinator_presets_are_disabled_and_qualified(self):
        view,_bus,_studio=self.view()
        buttons=view.rtmp_settings.preset_buttons
        self.assertEqual(len(buttons),5)
        self.assertEqual([button.text() for button in buttons],['Twitch','YouTube','Kick','TikTok','Local'])
        self.assertIn('Presets unavailable',view.rtmp_settings.lbl_presets.text())
        self.assertTrue(all(not button.isEnabled() and '720p' in button.toolTip() for button in buttons))
        self.assertFalse(view.rtmp_settings.btn_auto_best.isEnabled())

    def test_preset_and_encoder_controls_fit_1920_without_right_edge_clipping(self):
        from PyQt6.QtCore import QPoint
        from PyQt6.QtGui import QImage,QPainter
        view,_bus,_studio=self.view()
        self.assertLessEqual(view.minimumSizeHint().width(),1920)
        view.resize(1920,1400);view.ensurePolished();view.layout().activate()
        self.assertEqual(view.width(),1920)
        image=QImage(view.size(),QImage.Format.Format_ARGB32)
        painter=QPainter(image)
        try:view.render(painter)
        finally:painter.end()
        controls=[*view.rtmp_settings.preset_buttons,view.rtmp_settings.combo_bitrate,*view.rtmp_settings.dest_badges.values()]
        for control in controls:
            position=control.mapTo(view,QPoint(0,0))
            self.assertLessEqual(position.x()+control.width(),view.width(),control.objectName() or control.__class__.__name__)

if __name__=='__main__': unittest.main()
