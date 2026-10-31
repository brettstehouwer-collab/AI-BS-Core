"""Offline policy/catalog fixtures. Never enumerate or capture the actual desktop."""
from __future__ import annotations

from dataclasses import replace
import importlib
import json
from pathlib import Path
import tempfile
from contextlib import nullcontext
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class GameSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = importlib.import_module('backend.core.game_capture_selection')

    def window(self, hwnd=10, pid=70, exe=r'C:\Games\Fixture\bin\Game.exe', **changes):
        fields = dict(hwnd=hwnd, title='Fixture game  ',
                      process=self.m.ProcessIdentity(pid, 123.5, exe),
                      width=1280, height=720, visible=True, minimized=False, foreground=False)
        fields.update(changes)
        return self.m.WindowEvidence(**fields)

    def installed(self, root=r'C:\Games\Fixture', source='steam', **changes):
        return self.m.GameInstallation(root=root, source=source, game_id='fixture', **changes)

    def select(self, windows, **kwargs):
        return self.m.select_capture(windows, [self.installed()], **kwargs)

    def test_verified_catalog_game_selected_without_title_name_guessing(self):
        game=self.window(title='Unrelated display name')
        decision=self.select([game])
        self.assertEqual(decision.source, game)
        self.assertEqual(decision.provenance, 'steam:fixture')
        self.assertTrue(decision.must_clear)

    def test_browser_and_launcher_never_automatic_fallback_even_inside_game_root(self):
        for exe in (r'C:\Games\Fixture\chrome.exe',r'C:\Games\Fixture\EpicGamesLauncher.exe',
                    r'C:\Games\Fixture\Battle.net.exe',r'C:\Windows\explorer.exe'):
            with self.subTest(exe=exe):
                result=self.select([self.window(exe=exe, foreground=True)])
                self.assertIsNone(result.source)
                self.assertEqual(result.reason, 'NO_VERIFIED_GAME')

    def test_command_hosts_never_become_automatic_games_from_install_root(self):
        for name in ('powershell.exe','pwsh.exe','cmd.exe','python.exe','node.exe','WindowsTerminal.exe'):
            with self.subTest(name=name):
                self.assertIsNone(self.select([self.window(exe='C:\\Games\\Fixture\\'+name)]).source)

    def test_explicit_install_executable_allowlist_does_not_admit_root_helpers(self):
        entry=self.installed(executables=(r'C:\Games\Fixture\bin\Game.exe',))
        game=self.window();helper=self.window(22,82,r'C:\Games\Fixture\bin\Helper.exe',foreground=True)
        self.assertEqual(self.m.select_capture([game,helper],[entry]).source,game)
        self.assertIsNone(self.m.select_capture([helper],[entry]).source)

    def test_known_embedded_browsers_and_auxiliary_game_helpers_are_excluded(self):
        for name in ('msedgewebview2.exe','MicrosoftEdgeWebView2.exe','UnrealCEFSubProcess.exe',
                     'UnityCrashHandler64.exe','UnityCrashHandler32.exe','EpicOnlineServices.exe',
                     'EpicOnlineServicesUserHelper.exe','GameLauncher.exe','CODLauncher.exe'):
            with self.subTest(name=name):
                self.assertIsNone(self.select([self.window(exe='C:\\Games\\Fixture\\'+name,foreground=True)]).source)

    def test_manual_browser_window_wins_and_loss_holds_without_game_fallback(self):
        browser=self.window(20,80,r'C:\Browser\chrome.exe',title='Shared browser')
        manual=self.m.ManualSource(kind='window',window=browser)
        game=self.window(foreground=True)
        result=self.select([game,browser],manual=manual)
        self.assertEqual(result.source,browser); self.assertTrue(result.manual)
        lost=self.select([game],manual=manual,previous=result)
        self.assertIsNone(lost.source); self.assertTrue(lost.must_clear)
        self.assertEqual(lost.reason,'MANUAL_SOURCE_UNAVAILABLE')

    def test_manual_screen_requires_explicit_nonempty_identity_and_blocks_auto(self):
        with self.assertRaises(ValueError):self.m.ManualSource(kind='screen')
        manual=self.m.ManualSource(kind='screen',screen_id='display-1')
        result=self.select([self.window(foreground=True)],manual=manual)
        self.assertIsNone(result.source); self.assertTrue(result.manual)
        self.assertEqual(result.manual_source,manual)
        self.assertEqual(result.source_key,('screen','display-1'))

    def test_foreground_only_breaks_ties_among_verified_games(self):
        a=self.window();b=self.window(11,71,foreground=True)
        browser=self.window(22,82,r'C:\Browser\chrome.exe',foreground=True)
        self.assertEqual(self.select([a,b,browser]).source,b)
        prior=self.select([a]); result=self.select([a,browser],previous=prior)
        self.assertEqual(result.source,a);self.assertFalse(result.must_clear)

    def test_valid_previous_is_sticky_when_no_other_verified_game_is_foreground(self):
        a=self.window(width=640,height=480);b=self.window(11,71,width=1920,height=1080)
        prior=self.select([a])
        self.assertEqual(self.select([b,a],previous=prior).source,a)

    def test_multiwindow_choice_deterministic_and_uses_main_window_area(self):
        a=self.window(10,70,width=640,height=480);b=self.window(11,70)
        self.assertEqual(self.select([a,b]).source,b)
        self.assertEqual(self.select([b,a]).source,b)
        c=self.window(12,70)
        self.assertEqual(self.select([c,b]).source,b)

    def test_pid_create_time_executable_title_or_hwnd_change_clears_old_pixels(self):
        old=self.window();previous=self.select([old])
        changes=[replace(old,hwnd=11), replace(old,title='Fixture game'),
                 replace(old,process=replace(old.process,pid=71)),
                 replace(old,process=replace(old.process,create_time=124.0)),
                 replace(old,process=replace(old.process,exe=r'C:\Games\Fixture\Other.exe'))]
        for candidate in changes:
            with self.subTest(candidate=candidate):
                self.assertTrue(self.select([candidate],previous=previous).must_clear)

    def test_lost_hidden_minimized_or_zero_sized_game_clears_without_fallback(self):
        old=self.window();prior=self.select([old])
        for windows in ([],[replace(old,visible=False)],[replace(old,minimized=True)],
                        [replace(old,width=0)]):
            with self.subTest(windows=windows):
                result=self.select(windows,previous=prior)
                self.assertIsNone(result.source);self.assertTrue(result.must_clear)

    def test_path_boundaries_no_prefix_or_relative_root_admission(self):
        self.assertIsNone(self.select([self.window(exe=r'C:\Games\FixtureOther\Game.exe')]).source)
        for path in ('Games\\Fixture','C:\\',r'C:\Program Files',r'\\server\share\Game'):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):self.installed(root=path)

    def test_catalog_sources_support_launcher_independent_games_and_package_identity(self):
        game=self.window(exe=r'D:\Installed\AnyGame\Game.exe')
        for source in ('steam','epic','xbox','battlenet','installed_game'):
            with self.subTest(source=source):
                entry=self.installed(root=r'D:\Installed\AnyGame',source=source)
                self.assertEqual(self.m.select_capture([game],[entry]).source,game)
        packaged=replace(game,package_family='Fixture.Game_abcd')
        entry=self.installed(root=r'D:\Installed\AnyGame',source='xbox',package_family='Other.Game_abcd')
        self.assertIsNone(self.m.select_capture([packaged],[entry]).source)

    def test_synthetic_steam_epic_xbox_and_cod_installs_use_process_provenance_only(self):
        for source,root,exe in (
            ('steam',r'D:\SteamLibrary\steamapps\common\Fixture',r'D:\SteamLibrary\steamapps\common\Fixture\bin\Game.exe'),
            ('epic',r'D:\Epic Games\Fixture',r'D:\Epic Games\Fixture\bin\Shipping.exe'),
            ('xbox',r'D:\XboxGames\Fixture\Content',r'D:\XboxGames\Fixture\Content\cod.exe'),
            ('battlenet',r'D:\Call of Duty',r'D:\Call of Duty\cod.exe')):
            with self.subTest(source=source):
                game=self.window(exe=exe,title='No launcher or game name in title')
                entry=self.installed(root=root,source=source)
                browser=self.window(22,82,r'C:\Browser\chrome.exe',foreground=True)
                result=self.m.select_capture([browser,game],[entry])
                self.assertEqual(result.source,game);self.assertEqual(result.provenance,source+':fixture')

    def test_explicitly_approved_exact_game_process_allows_custom_install(self):
        custom=self.window(exe=r'C:\Portable\Custom\Play.exe')
        result=self.m.select_capture([custom],[],approved_game=custom.process)
        self.assertEqual(result.source,custom)
        reused=replace(custom,process=replace(custom.process,create_time=999.0))
        self.assertIsNone(self.m.select_capture([reused],[],approved_game=custom.process).source)
        browser=self.window(exe=r'C:\Browser\chrome.exe')
        self.assertIsNone(self.m.select_capture([browser],[],approved_game=browser.process).source)

    def test_decisions_are_immutable_and_do_not_retain_unknown_metadata(self):
        result=self.select([self.window()])
        with self.assertRaises(Exception):result.reason='changed'
        self.assertEqual(len(result.source_key),7)
        self.assertNotIn('token',repr(result).lower())

    def test_input_limits_hold_instead_of_selecting_truncated_unstable_candidates(self):
        result=self.select([self.window(i+1,i+1) for i in range(513)])
        self.assertIsNone(result.source);self.assertEqual(result.reason,'EVIDENCE_LIMIT_EXCEEDED')

    def test_generator_consumption_is_bounded_before_any_source_admission(self):
        def candidates():
            for i in range(600):
                if i>513:raise AssertionError('Unbounded candidate iteration')
                yield self.window(i+1,i+1)
        self.assertEqual(self.select(candidates()).reason,'EVIDENCE_LIMIT_EXCEEDED')


class GameCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=importlib.import_module('backend.core.game_capture_selection')

    def test_steam_manifest_preserves_library_boundary_without_game_name_heuristics(self):
        text='"AppState" { "appid" "777" "installdir" "FixtureGame" "name" "Anything" }'
        entry=self.m.parse_steam_manifest(text,r'D:\SteamLibrary\steamapps')
        self.assertEqual(entry.root,r'd:\steamlibrary\steamapps\common\fixturegame')
        self.assertEqual((entry.source,entry.game_id),('steam','777'))
        for install in ('..\\Escape','C:\\Escape',''):
            self.assertIsNone(self.m.parse_steam_manifest(text.replace('FixtureGame',install),r'D:\SteamLibrary\steamapps'))

    def test_steam_library_parser_handles_current_nested_format_bounded(self):
        text='"libraryfolders" { "0" { "path" "C:\\\\Steam" "apps" { "777" "1" } } "1" { "path" "D:\\\\SteamLibrary" } }'
        self.assertEqual(self.m.parse_steam_libraries(text),(r'c:\steam',r'd:\steamlibrary'))
        self.assertEqual(self.m.parse_steam_libraries('x'*1048577),())

    def test_epic_manifest_only_retains_install_evidence_and_rejects_escape(self):
        record={'InstallLocation':r'C:\Games\Fixture','AppName':'fixture',
                'LaunchExecutable':r'bin\Play.exe','AuthorizationToken':'do-not-retain'}
        result=self.m.parse_epic_manifest(json.dumps(record))
        self.assertEqual(result.executables,(r'c:\games\fixture\bin\play.exe',))
        self.assertNotIn('do-not-retain',repr(result))
        record['LaunchExecutable']=r'..\Other\Play.exe'
        self.assertIsNone(self.m.parse_epic_manifest(json.dumps(record)))

    def test_installed_registry_catalog_requires_game_publisher_or_explicit_game_marker(self):
        records=[{'InstallLocation':r'C:\Apps\Browser','Publisher':'Browser Corp','DisplayName':'Game browser'},
                 {'InstallLocation':r'D:\Games\Fixture','Publisher':'Activision','DisplayName':'Fixture'},
                 {'InstallLocation':r'D:\Games\Another','Publisher':'Blizzard Entertainment','DisplayName':'Another'}]
        entries=self.m.catalog_from_installed_records(records)
        self.assertEqual(len(entries),2)
        self.assertTrue(all(x.source=='battlenet' for x in entries))

    def test_adapter_is_inert_until_snapshot_and_injected_evidence_controls_policy(self):
        win=self.m.WindowEvidence(10,'Fixture',self.m.ProcessIdentity(70,1.0,r'C:\Games\Fixture\Play.exe'),1280,720)
        windows=Mock(return_value=(win,));catalog=Mock(return_value=(self.m.GameInstallation(r'C:\Games\Fixture','steam','777'),))
        adapter=self.m.WindowsGameAdapter(window_reader=windows,catalog_reader=catalog)
        windows.assert_not_called();catalog.assert_not_called()
        result=adapter.decide()
        self.assertEqual(result.source,win);windows.assert_called_once();catalog.assert_called_once()

    def test_adapter_exposes_only_current_immutable_server_window_cache(self):
        win=self.m.WindowEvidence(10,'Fixture  ',self.m.ProcessIdentity(70,1.0,r'C:\Games\Fixture\Play.exe'),1280,720)
        reader=Mock(side_effect=[(win,),OSError('fixture')])
        adapter=self.m.WindowsGameAdapter(window_reader=reader,catalog_reader=lambda:())
        self.assertEqual(adapter.cached_windows,());reader.assert_not_called()
        adapter.decide();self.assertEqual(adapter.cached_windows,(win,))
        adapter.decide();self.assertEqual(adapter.cached_windows,())

    def test_manual_screen_cannot_refresh_an_older_cached_window_enumeration(self):
        win=self.m.WindowEvidence(10,'Fixture',self.m.ProcessIdentity(70,1.0,r'C:\Games\Fixture\Play.exe'),1280,720)
        adapter=self.m.WindowsGameAdapter(window_reader=lambda:(win,),catalog_reader=lambda:())
        adapter.decide();self.assertEqual(adapter.cached_windows,(win,))
        adapter.decide(manual=self.m.ManualSource('screen',screen_id='display-1'))
        self.assertEqual(adapter.cached_windows,())

    def test_adapter_failure_clears_previous_and_does_not_reuse_stale_windows(self):
        win=self.m.WindowEvidence(10,'Fixture',self.m.ProcessIdentity(70,1.0,r'C:\Games\Fixture\Play.exe'),1280,720)
        entry=self.m.GameInstallation(r'C:\Games\Fixture','steam','777')
        adapter=self.m.WindowsGameAdapter(window_reader=Mock(side_effect=[(win,),OSError('fixture')]),catalog_reader=lambda:(entry,))
        prior=adapter.decide();result=adapter.decide(previous=prior)
        self.assertIsNone(result.source);self.assertTrue(result.must_clear)
        self.assertEqual(result.reason,'WINDOW_EVIDENCE_UNAVAILABLE')

    def test_catalog_failure_never_drops_explicit_manual_share(self):
        win=self.m.WindowEvidence(10,'Browser',self.m.ProcessIdentity(70,1.0,r'C:\Browser\chrome.exe'),1280,720)
        adapter=self.m.WindowsGameAdapter(window_reader=lambda:(win,),catalog_reader=Mock(side_effect=OSError()))
        result=adapter.decide(manual=self.m.ManualSource('window',window=win))
        self.assertEqual(result.source,win);self.assertTrue(result.manual)

    def test_explicit_screen_share_does_not_depend_on_window_or_game_discovery(self):
        windows=Mock(side_effect=OSError());catalog=Mock(side_effect=OSError())
        adapter=self.m.WindowsGameAdapter(window_reader=windows,catalog_reader=catalog)
        result=adapter.decide(manual=self.m.ManualSource('screen',screen_id='display-1'))
        self.assertEqual(result.reason,'MANUAL_SCREEN')
        windows.assert_not_called();catalog.assert_not_called()

    def test_failed_catalog_recovers_after_monotonic_refresh_boundary(self):
        win=self.m.WindowEvidence(10,'Fixture',self.m.ProcessIdentity(70,1.0,r'C:\Games\Fixture\Play.exe'),1280,720)
        entry=self.m.GameInstallation(r'C:\Games\Fixture','steam','777')
        clock=Mock(return_value=10.0);catalog=Mock(side_effect=[OSError(),(entry,)])
        adapter=self.m.WindowsGameAdapter(window_reader=lambda:(win,),catalog_reader=catalog,refresh_seconds=2,clock=clock)
        self.assertIsNone(adapter.decide().source)
        clock.return_value=11.0;self.assertIsNone(adapter.decide().source)
        clock.return_value=12.0;self.assertEqual(adapter.decide().source,win)
        self.assertEqual(catalog.call_count,2)

    def test_readonly_windows_adapter_uses_exact_raw_title_and_process_start_time(self):
        process=SimpleNamespace(create_time=lambda:123.5,exe=lambda:r'C:\Games\Fixture\Game.exe',oneshot=nullcontext)
        psutil=SimpleNamespace(Process=Mock(return_value=process),Error=RuntimeError)
        gui=SimpleNamespace(GetForegroundWindow=lambda:10,IsWindowVisible=lambda _:True,
                            GetWindowText=lambda _:'Fixture  ',GetWindowRect=lambda _:(0,0,1280,720),
                            IsIconic=lambda _:False,EnumWindows=lambda callback,data:callback(10,data))
        windows=SimpleNamespace(GetWindowThreadProcessId=lambda _:(1,70))
        with patch.dict('sys.modules',{'psutil':psutil,'win32gui':gui,'win32process':windows}),patch.object(self.m.sys,'platform','win32'),patch.object(self.m.os,'getpid',return_value=999):
            result=self.m.snapshot_windows()
        self.assertEqual(len(result),1);self.assertEqual(result[0].title,'Fixture  ')
        self.assertEqual(result[0].process.create_time,123.5)
        self.assertTrue(result[0].foreground)

    def test_recycled_process_during_window_snapshot_is_rejected(self):
        old=SimpleNamespace(create_time=lambda:123.5,exe=lambda:r'C:\Games\Fixture\Game.exe',oneshot=nullcontext)
        new=SimpleNamespace(create_time=lambda:999.0)
        psutil=SimpleNamespace(Process=Mock(side_effect=[old,new]),Error=RuntimeError)
        gui=SimpleNamespace(GetForegroundWindow=lambda:10,IsWindowVisible=lambda _:True,
                            GetWindowText=lambda _:'Fixture',GetWindowRect=lambda _:(0,0,1280,720),
                            IsIconic=lambda _:False,EnumWindows=lambda callback,data:callback(10,data))
        windows=SimpleNamespace(GetWindowThreadProcessId=lambda _:(1,70))
        with patch.dict('sys.modules',{'psutil':psutil,'win32gui':gui,'win32process':windows}),patch.object(self.m.sys,'platform','win32'),patch.object(self.m.os,'getpid',return_value=999):
            self.assertEqual(self.m.snapshot_windows(),())

    def test_snapshot_limit_holds_even_if_win32_returns_normally_after_callback_false(self):
        def enumerate_windows(callback,data):
            for hwnd in range(1,600):
                if callback(hwnd,data) is False:return
        gui=SimpleNamespace(GetForegroundWindow=lambda:0,IsWindowVisible=lambda _:False,
                            EnumWindows=enumerate_windows)
        with patch.dict('sys.modules',{'psutil':SimpleNamespace(),'win32gui':gui,'win32process':SimpleNamespace()}),patch.object(self.m.sys,'platform','win32'):
            with self.assertRaisesRegex(ValueError,'bounds'):self.m.snapshot_windows()

    def test_runtime_catalog_reads_only_bounded_known_manifest_locations(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);steam=base/'Steam';apps=steam/'steamapps';apps.mkdir(parents=True)
            (apps/'appmanifest_777.acf').write_text('"AppState" { "appid" "777" "installdir" "Fixture" }',encoding='utf-8')
            epic=base/'ProgramData'/'Epic'/'EpicGamesLauncher'/'Data'/'Manifests';epic.mkdir(parents=True)
            (epic/'fixture.item').write_text(json.dumps({'InstallLocation':str(base/'EpicFixture'),
                                                       'AppName':'epicfixture','LaunchExecutable':'Game.exe'}),encoding='utf-8')
            xbox=base/'XboxFixture';xbox.mkdir();(xbox/'MicrosoftGame.config').write_text('<Game configVersion="1"><Identity Name="Fixture"/></Game>',encoding='utf-8')
            records=[{'InstallLocation':str(base/'VendorFixture'),'Publisher':'Activision','RegistryId':'fixture'}]
            with patch.object(self.m.sys,'platform','win32'),patch.object(self.m,'_registry_evidence',return_value=([str(steam)],records,[(str(xbox),'Fixture.Package_123')])),patch.dict(self.m.os.environ,{'ProgramData':str(base/'ProgramData')}),patch.object(self.m,'discover_xbox_content_installations',return_value=()):
                entries=self.m.discover_game_installations()
            self.assertEqual({x.source for x in entries},{'steam','epic','xbox','battlenet'})

    def test_xbox_config_requires_real_game_identity_xml_not_a_comment_marker(self):
        for text in ('<!-- <Game --> <Application/>','<Game/>',
                     '<Game><Identity/></Game>','<!DOCTYPE Game [<!ENTITY x "fixture">]><Game><Identity Name="&x;"/></Game>'):
            with self.subTest(text=text):
                self.assertIsNone(self.m.parse_xbox_game_config(text,r'D:\XboxGames\Fixture','fixture.package'))
        entry=self.m.parse_xbox_game_config('<Game xmlns="urn:fixture"><Identity Name="Fixture"/></Game>',r'D:\XboxGames\Fixture','fixture.package')
        self.assertEqual(entry.source,'xbox')

    def test_gaming_root_version1_registration_derives_library_without_fixed_folder_name(self):
        raw=b'RGBX'+(1).to_bytes(4,'little')+'InstalledTitles\x00'.encode('utf-16le')
        self.assertEqual(self.m.parse_gaming_root(raw,'C:\\'),r'c:\installedtitles')
        for bad in (b'',raw[:6],b'NOPE'+raw[4:],b'RGBX'+(2).to_bytes(4,'little')+raw[8:],
                    b'RGBX'+(1).to_bytes(4,'little')+'..\\Escape\x00'.encode('utf-16le'),
                    b'RGBX'+(1).to_bytes(4,'little')+'C:\\Elsewhere\x00'.encode('utf-16le')):
            with self.subTest(raw=bad):self.assertIsNone(self.m.parse_gaming_root(bad,'C:\\'))

    def test_registered_xbox_content_game_bootstrap_is_not_an_exclusive_capture_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            library=Path(folder)/'RegisteredGames';content=library/'AnyGame'/'Content';content.mkdir(parents=True)
            (content/'MicrosoftGame.config').write_text(
                '<Game configVersion="1"><Identity Name="Fixture.StoreGame"/>'
                '<ExecutableList><Executable Name="Game/Binaries/GDKLauncher.exe" Id="App"/></ExecutableList></Game>',encoding='utf-8')
            entries=self.m.discover_xbox_content_installations(libraries=(str(library),))
            self.assertEqual(len(entries),1);entry=entries[0]
            self.assertEqual(entry.root,self.m._windows_path(str(content)))
            self.assertEqual((entry.source,entry.game_id,entry.executables),('xbox','Fixture.StoreGame',()))
            process=self.m.ProcessIdentity
            game=self.m.WindowEvidence(207,'Arbitrary title',process(900,1.,str(content/'Game/Binaries/ActualGame.exe')),1280,720)
            helper=self.m.WindowEvidence(208,'Launcher',process(901,1.,str(content/'Game/Binaries/GDKLauncher.exe')),1280,720,foreground=True)
            self.assertEqual(self.m.select_capture([helper,game],entries).source,game)

    def test_xbox_content_discovery_requires_real_identity_and_does_not_recurse(self):
        with tempfile.TemporaryDirectory() as folder:
            library=Path(folder)/'Games';nested=library/'NotAGame'/'Deeper'/'Content';nested.mkdir(parents=True)
            (nested/'MicrosoftGame.config').write_text('<Game><Identity Name="TooDeep"/></Game>')
            invalid=library/'CommentOnly'/'Content';invalid.mkdir(parents=True)
            (invalid/'MicrosoftGame.config').write_text('<!-- <Game --> <Application/>')
            self.assertEqual(self.m.discover_xbox_content_installations(libraries=(str(library),)),())

    def test_main_catalog_includes_registered_xbox_content_even_without_appmodel_entries(self):
        entry=self.m.GameInstallation(r'C:\InstalledTitles\Fixture\Content','xbox','Fixture.StoreGame')
        with patch.object(self.m.sys,'platform','win32'),patch.object(self.m,'_registry_evidence',return_value=([],[],[])),patch.object(self.m,'discover_xbox_content_installations',return_value=(entry,)) as discover,patch.object(self.m.os,'scandir',side_effect=FileNotFoundError()):
            self.assertIn(entry,self.m.discover_game_installations())
        discover.assert_called_once()

    def test_bounded_manifest_reader_never_recurses_or_reads_oversized_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.item';path.write_bytes(b'x'*1048577)
            self.assertIsNone(self.m.read_manifest_text(path))
            path.write_text('fixture',encoding='utf-8')
            self.assertEqual(self.m.read_manifest_text(path),'fixture')


if __name__=='__main__':unittest.main()
