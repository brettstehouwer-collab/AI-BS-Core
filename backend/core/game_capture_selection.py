"""Deterministic, credential-free capture selection and read-only Windows evidence.

Imports and construction perform no discovery. This module never captures pixels,
starts a process, changes foreground windows, or falls back to an arbitrary app.
Catalog membership is installation provenance, not proof of a captured frame.
Consumers must clear old frames before starting a changed selection and revalidate
the exact HWND/process identity immediately before publishing a new frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
import json
import math
import ntpath
import os
from pathlib import Path
import re
import sys
import time
from typing import Callable, Iterable
import xml.etree.ElementTree as ET

MAX_WINDOWS = 512
MAX_INSTALLATIONS = 1024
MAX_MANIFEST_BYTES = 1048576
_SOURCES = frozenset({'steam', 'epic', 'xbox', 'battlenet', 'gog', 'installed_game'})
_EXCLUDED_EXECUTABLES = frozenset({
    'chrome.exe', 'msedge.exe', 'firefox.exe', 'brave.exe', 'opera.exe',
    'iexplore.exe', 'explorer.exe', 'applicationframehost.exe', 'dwm.exe',
    'steam.exe', 'steamwebhelper.exe', 'epicgameslauncher.exe', 'epicwebhelper.exe',
    'battle.net.exe', 'agent.exe', 'blizzardbrowser.exe', 'eadesktop.exe',
    'ealauncher.exe', 'origin.exe', 'galaxyclient.exe', 'upc.exe',
    'ubisoftconnect.exe', 'riotclientservices.exe', 'crashreportclient.exe',
    'crashpad_handler.exe', 'werfault.exe', 'uninstall.exe', 'unins000.exe',
    'codcrashhandler.exe', 'bootstrapper.exe', 'obs64.exe', 'discord.exe',
    'powershell.exe', 'pwsh.exe', 'cmd.exe', 'python.exe', 'pythonw.exe',
    'node.exe', 'windowsterminal.exe', 'wt.exe', 'cscript.exe', 'wscript.exe',
    'mstsc.exe', 'anydesk.exe', 'teamviewer.exe',
    'msedgewebview2.exe', 'microsoftedgewebview2.exe', 'unrealcefsubprocess.exe',
})
_BROAD_ROOT_LEAVES = frozenset({
    'program files', 'program files (x86)', 'windows', 'users', 'games',
    'steam', 'steamlibrary', 'steamapps', 'common', 'epic games', 'xboxgames',
    'windowsapps', 'battle.net', 'blizzard', 'ea desktop', 'ubisoft game launcher',
})


def _windows_path(value: str) -> str:
    if (type(value) is not str or not 3 <= len(value) <= 32767
            or any(ord(c) < 32 for c in value) or value.startswith(('\\\\', '//'))):
        raise ValueError('An absolute local executable or installation path is required')
    drive, tail = ntpath.splitdrive(value)
    if not re.fullmatch(r'[A-Za-z]:', drive) or not tail.startswith(('\\', '/')):
        raise ValueError('An absolute local path is required')
    return ntpath.normcase(ntpath.normpath(value))


def _within(path: str, root: str) -> bool:
    return path.startswith(root.rstrip('\\') + '\\')


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    create_time: float
    exe: str

    def __post_init__(self):
        if (type(self.pid) is not int or not 0 < self.pid < 2**32
                or type(self.create_time) not in (int, float)
                or not math.isfinite(self.create_time) or self.create_time <= 0):
            raise ValueError('A live process identity is required')
        object.__setattr__(self, 'exe', _windows_path(self.exe))


@dataclass(frozen=True)
class WindowEvidence:
    hwnd: int
    title: str
    process: ProcessIdentity
    width: int
    height: int
    visible: bool = True
    minimized: bool = False
    foreground: bool = False
    package_family: str = ''

    def __post_init__(self):
        if (type(self.hwnd) is not int or not 0 < self.hwnd < 2**64
                or type(self.title) is not str or not 0 < len(self.title) <= 4096
                or any(ord(c) < 32 for c in self.title)
                or not isinstance(self.process, ProcessIdentity)
                or type(self.width) is not int or type(self.height) is not int
                or not 0 <= self.width <= 32768 or not 0 <= self.height <= 32768
                or any(type(v) is not bool for v in (self.visible, self.minimized, self.foreground))
                or type(self.package_family) is not str or len(self.package_family) > 256):
            raise ValueError('Invalid window evidence')

    @property
    def source_key(self) -> tuple:
        return ('window', self.hwnd, self.process.pid, self.process.create_time,
                self.process.exe, self.title, self.package_family)


@dataclass(frozen=True)
class GameInstallation:
    root: str
    source: str
    game_id: str
    executables: tuple[str, ...] = ()
    package_family: str = ''

    def __post_init__(self):
        root = _windows_path(self.root).rstrip('\\')
        if (len(root) <= 3 or ntpath.basename(root) in _BROAD_ROOT_LEAVES
                or self.source not in _SOURCES or type(self.game_id) is not str
                or not 0 < len(self.game_id) <= 256 or any(ord(c) < 32 for c in self.game_id)
                or type(self.executables) is not tuple or len(self.executables) > 32
                or type(self.package_family) is not str or len(self.package_family) > 256):
            raise ValueError('A narrow trusted game installation is required')
        exes = tuple(_windows_path(x) for x in self.executables)
        if any(not _within(x, root) for x in exes):
            raise ValueError('Launch executables must remain in the game installation')
        object.__setattr__(self, 'root', root)
        object.__setattr__(self, 'executables', exes)


@dataclass(frozen=True)
class ManualSource:
    kind: str
    window: WindowEvidence | None = None
    screen_id: str = ''

    def __post_init__(self):
        if self.kind == 'window':
            if not isinstance(self.window, WindowEvidence) or self.screen_id:
                raise ValueError('Manual sharing requires an exact window identity')
        elif self.kind == 'screen':
            if (self.window is not None or type(self.screen_id) is not str
                    or not 0 < len(self.screen_id) <= 256
                    or any(ord(c) < 32 for c in self.screen_id)):
                raise ValueError('Desktop sharing requires an explicit screen identity')
        else:
            raise ValueError('Only explicit window or screen sharing is supported')


@dataclass(frozen=True)
class SelectionDecision:
    source: WindowEvidence | None
    reason: str
    must_clear: bool
    manual: bool = False
    provenance: str = ''
    manual_source: ManualSource | None = None

    @property
    def source_key(self) -> tuple | None:
        if self.source is not None:
            return self.source.source_key
        if self.manual_source is not None and self.manual_source.kind == 'screen':
            return ('screen', self.manual_source.screen_id)
        return None


def _previous_key(previous) -> tuple | None:
    return previous.source_key if isinstance(previous, (SelectionDecision, WindowEvidence)) else None


def _available(window: WindowEvidence) -> bool:
    return window.visible and not window.minimized and window.width > 0 and window.height > 0


def _automatic_provenance(window, installations, approved_game):
    name = ntpath.basename(window.process.exe)
    if (name in _EXCLUDED_EXECUTABLES or 'launcher' in name
            or re.fullmatch(r'unitycrashhandler(?:32|64)\.exe',name)
            or re.fullmatch(r'epiconlineservices[a-z0-9_.-]*\.exe',name)):
        return ''
    if isinstance(approved_game, ProcessIdentity) and window.process == approved_game:
        return 'explicit_prior_game'
    for entry in installations:
        if (_within(window.process.exe, entry.root)
                and (not entry.executables or window.process.exe in entry.executables)
                and (not entry.package_family or entry.package_family == window.package_family)):
            return entry.source + ':' + entry.game_id
    return ''


def select_capture(windows: Iterable[WindowEvidence], installations: Iterable[GameInstallation],
                   *, manual: ManualSource | None = None,
                   previous: SelectionDecision | WindowEvidence | None = None,
                   approved_game: ProcessIdentity | None = None) -> SelectionDecision:
    """Choose from supplied evidence only. No arbitrary foreground/desktop fallback.

    must_clear is true before a newly selected source may publish pixels. A held
    decision has no source; the caller may publish a clearly labeled black slate.
    Manual source validity is independent of automatic game-catalog availability.
    """
    previous_key = _previous_key(previous)
    windows = tuple(islice(windows, MAX_WINDOWS + 1))
    if len(windows) > MAX_WINDOWS:
        return SelectionDecision(None, 'EVIDENCE_LIMIT_EXCEEDED', previous_key is not None)
    if any(not isinstance(w, WindowEvidence) for w in windows):
        return SelectionDecision(None, 'INVALID_WINDOW_EVIDENCE', previous_key is not None)
    if manual is not None:
        if not isinstance(manual, ManualSource):
            raise ValueError('Invalid manual source')
        if manual.kind == 'screen':
            key = ('screen', manual.screen_id)
            return SelectionDecision(None, 'MANUAL_SCREEN', previous_key != key, True, 'explicit_manual', manual)
        exact = [w for w in windows if w.source_key == manual.window.source_key and _available(w)]
        if not exact:
            return SelectionDecision(None, 'MANUAL_SOURCE_UNAVAILABLE', previous_key is not None,
                                     True, 'explicit_manual', manual)
        chosen = exact[0]
        return SelectionDecision(chosen, 'MANUAL_WINDOW', previous_key != chosen.source_key,
                                 True, 'explicit_manual', manual)
    installations = tuple(islice(installations, MAX_INSTALLATIONS + 1))
    if len(installations) > MAX_INSTALLATIONS or any(not isinstance(x, GameInstallation) for x in installations):
        return SelectionDecision(None, 'EVIDENCE_LIMIT_EXCEEDED', previous_key is not None)
    # Sort provenance too, so catalog enumeration order cannot change the decision.
    installations = sorted(installations, key=lambda e: (-len(e.root), e.source, e.game_id))
    candidates = [(w, _automatic_provenance(w, installations, approved_game)) for w in windows if _available(w)]
    candidates = [(w, proof) for w, proof in candidates if proof]
    if not candidates:
        return SelectionDecision(None, 'NO_VERIFIED_GAME', previous_key is not None)
    foreground = [(w, proof) for w, proof in candidates if w.foreground]
    pool = foreground or candidates
    sticky = [(w, proof) for w, proof in pool if w.source_key == previous_key]
    chosen, provenance = min(sticky or pool, key=lambda item: (
        -item[0].width * item[0].height, item[0].process.exe,
        item[0].process.pid, item[0].hwnd, item[0].title))
    return SelectionDecision(chosen, 'VERIFIED_GAME', previous_key != chosen.source_key,
                             False, provenance)


def _vdf(text: str):
    """Small bounded Valve KeyValues reader; no includes, macros or file access."""
    if type(text) is not str or len(text) > MAX_MANIFEST_BYTES:
        raise ValueError('Manifest exceeds bounds')
    tokens = re.findall(r'"((?:\\.|[^"\\])*)"|([{}])', text)
    if len(tokens) > 32768:
        raise ValueError('Manifest exceeds bounds')
    items = [symbol if symbol else value.replace('\\\\', '\\').replace('\\"', '"') for value, symbol in tokens]
    position = 0
    def section(depth=0):
        nonlocal position
        if depth > 8:
            raise ValueError('Manifest nesting exceeds bounds')
        result = {}
        while position < len(items):
            key = items[position]; position += 1
            if key == '}':
                return result
            if key == '{' or position >= len(items):
                raise ValueError('Invalid manifest')
            value = items[position]; position += 1
            result[key.casefold()] = section(depth+1) if value == '{' else value
        if depth:
            raise ValueError('Unclosed manifest')
        return result
    return section()


def parse_steam_libraries(text: str) -> tuple[str, ...]:
    try:
        data = _vdf(text).get('libraryfolders', {})
        if type(data) is not dict:return ()
        paths = []
        for key, value in data.items():
            if not key.isdecimal():continue
            path = value.get('path') if type(value) is dict else value
            paths.append(_windows_path(path))
        return tuple(sorted(set(paths)))[:32]
    except (ValueError, TypeError, AttributeError):return ()


def parse_steam_manifest(text: str, steamapps: str) -> GameInstallation | None:
    try:
        data = _vdf(text)['appstate']; install = data['installdir']; app_id = data['appid']
        if (type(install) is not str or not install or install in ('.', '..')
                or ntpath.basename(install) != install or '/' in install or '\\' in install
                or not str(app_id).isdecimal()):return None
        return GameInstallation(ntpath.join(_windows_path(steamapps), 'common', install), 'steam', str(app_id))
    except (ValueError, KeyError, TypeError):return None


def parse_epic_manifest(text: str) -> GameInstallation | None:
    try:
        if type(text) is not str or len(text) > MAX_MANIFEST_BYTES:return None
        data = json.loads(text); root = _windows_path(data['InstallLocation'])
        launch = data.get('LaunchExecutable', '')
        if type(launch) is not str or ntpath.isabs(launch) or '..' in launch.replace('/', '\\').split('\\'):
            return None
        exes = (_windows_path(ntpath.join(root, launch)),) if launch else ()
        return GameInstallation(root, 'epic', data['AppName'], exes)
    except (ValueError, KeyError, TypeError):return None


def parse_xbox_game_config(text: str,root: str,package_name: str | None=None) -> GameInstallation | None:
    """Require real game identity XML from the OS-reported package root."""
    try:
        if (type(text) is not str or len(text)>MAX_MANIFEST_BYTES
                or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper()):return None
        document = ET.fromstring(text)
        if document.tag.rsplit('}',1)[-1] != 'Game':return None
        identities = [child for child in document if child.tag.rsplit('}',1)[-1]=='Identity']
        if len(identities)!=1 or not identities[0].get('Name','').strip():return None
        return GameInstallation(root,'xbox',package_name or identities[0].get('Name'))
    except (ValueError,TypeError,ET.ParseError):return None


def parse_gaming_root(raw: bytes,drive_root: str) -> str | None:
    """Parse observed Xbox GamingRoot version1 registration, not a title guess."""
    try:
        drive = _windows_path(drive_root)
        if (type(raw) is not bytes or not 12<=len(raw)<=4096 or len(raw)%2
                or raw[:8]!=b'RGBX\x01\x00\x00\x00' or len(drive)!=3):return None
        relative = raw[8:].decode('utf-16le')
        if not relative.endswith('\x00') or '\x00' in relative[:-1]:return None
        relative = relative[:-1]
        parts = relative.replace('/','\\').split('\\')
        if (not relative or ntpath.isabs(relative) or ntpath.splitdrive(relative)[0]
                or any(part in ('','.','..') for part in parts)):return None
        result = _windows_path(ntpath.join(drive,relative))
        return result if _within(result,drive) else None
    except (ValueError,UnicodeError,TypeError):return None


def discover_xbox_content_installations(*,libraries=None,drive_roots=None,budget_seconds=.5):
    """Bounded registered XboxGames/Content catalog, without recursive drive scans.

    The system drive's .GamingRoot registration is checked by default. Additional
    locally approved drives or libraries can be supplied explicitly; unavailable
    drives are never guessed or swept. A config executable may be only a GDK
    bootstrapper, so this catalog uses its real game Identity and narrow Content
    root. It does not invent an exclusive child-game executable allowlist.
    """
    deadline = time.monotonic()+max(.05,min(float(budget_seconds),1.))
    if libraries is None:
        roots = drive_roots if drive_roots is not None else (os.environ.get('SystemDrive','C:')+'\\',)
        registered = []
        for drive in islice(roots,16):
            if time.monotonic()>deadline:break
            try:
                with (Path(drive)/'.GamingRoot').open('rb') as stream:raw=stream.read(4097)
                library=parse_gaming_root(raw,drive)
                if library:registered.append(library)
            except (OSError,ValueError):continue
        libraries = registered
    result = []
    for library in islice(libraries,32):
        if time.monotonic()>deadline:break
        try:
            library = Path(_windows_path(str(library)))
            if library.is_symlink() or library.is_junction():continue
            with os.scandir(library) as children:
                for index,child in enumerate(children):
                    if index>=256 or time.monotonic()>deadline:break
                    if not child.is_dir(follow_symlinks=False):continue
                    install=Path(child.path)
                    if install.is_junction():continue
                    for content in (install/'Content',install):
                        if content.is_symlink() or content.is_junction():continue
                        config=content/'MicrosoftGame.config'
                        if config.is_symlink() or config.is_junction():continue
                        text=read_manifest_text(config)
                        entry=parse_xbox_game_config(text,str(content)) if text else None
                        if entry:
                            result.append(entry);break
        except (OSError,ValueError):continue
    return tuple(sorted(set(result),key=lambda entry:(entry.root,entry.game_id)))


def catalog_from_installed_records(records: Iterable[dict]) -> tuple[GameInstallation, ...]:
    """Use game vendor installation metadata, never DisplayName/title guesses.

    Generic Microsoft/Windows packages are not inferred to be games. Xbox roots
    need MicrosoftGame.config evidence through the runtime catalog reader below.
    Explicit trusted installations can be supplied for portable/custom games.
    """
    result = []
    for index, record in enumerate(records):
        if index >= MAX_INSTALLATIONS:break
        if type(record) is not dict:continue
        publisher = str(record.get('Publisher', '')).casefold()
        source = 'battlenet' if publisher.startswith(('activision', 'blizzard entertainment')) else None
        if source is None:continue
        try:
            root = record['InstallLocation']
            result.append(GameInstallation(root, source, str(record.get('RegistryId') or root)))
        except (ValueError, KeyError, TypeError):continue
    return tuple(result)


def read_manifest_text(path) -> str | None:
    try:
        with Path(path).open('rb') as handle:raw = handle.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:return None
        return raw.decode('utf-8-sig')
    except (OSError, UnicodeError, ValueError):return None


def _registry_evidence(deadline: float):
    import winreg
    steam_roots = []; records = []; package_roots = []
    def values(hive, path, names, view=0):
        result = {}
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | view) as key:
                for name in names:
                    try:result[name] = winreg.QueryValueEx(key, name)[0]
                    except OSError:pass
        except OSError:pass
        return result
    steam = values(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', ('SteamPath',))
    if type(steam.get('SteamPath')) is str:steam_roots.append(steam['SteamPath'])
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | view) as parent:
                    for index in range(512):
                        if time.monotonic() > deadline:break
                        try:name = winreg.EnumKey(parent, index)
                        except OSError:break
                        record = values(hive, path+'\\'+name, ('InstallLocation','Publisher'), view)
                        record['RegistryId'] = name; records.append(record)
            except OSError:pass
    # OS package install metadata supplies candidate roots; only a local
    # MicrosoftGame.config marker certifies that a package is a game below.
    path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages'
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as parent:
            for index in range(512):
                if time.monotonic() > deadline:break
                try:name = winreg.EnumKey(parent, index)
                except OSError:break
                record = values(winreg.HKEY_LOCAL_MACHINE, path+'\\'+name, ('PackageRootFolder',))
                root = record.get('PackageRootFolder')
                if type(root) is str:package_roots.append((root,name))
    except OSError:pass
    return steam_roots, records, package_roots


def discover_game_installations(*, budget_seconds=1.5) -> tuple[GameInstallation, ...]:
    """Bounded read-only Steam/Epic/vendor/Windows package catalog discovery.

    No recursive drive scan, process execution, capture, network, credential
    reads, or PowerShell/WMI calls. Inaccessible/uncatalogued games stay held
    unless the caller explicitly supplies a trusted entry/prior game identity.
    A filesystem operation may exceed the soft budget on a stalled device; no
    thread is spawned to conceal that limitation.
    """
    if sys.platform != 'win32':return ()
    deadline = time.monotonic() + max(.05, min(float(budget_seconds), 3.0))
    result = list(discover_xbox_content_installations(budget_seconds=min(.5,max(.05,float(budget_seconds)*.4))))
    registry_deadline = min(deadline, time.monotonic() + min(.5, max(.05, float(budget_seconds)*.4)))
    steam_roots, records, package_roots = _registry_evidence(registry_deadline)
    result.extend(catalog_from_installed_records(records))
    libraries = set()
    for root in steam_roots[:8]:
        if time.monotonic() > deadline:break
        try:libraries.add(_windows_path(root))
        except ValueError:continue
        text = read_manifest_text(Path(root)/'steamapps'/'libraryfolders.vdf')
        if text:libraries.update(parse_steam_libraries(text))
    def manifests(folder, suffix):
        try:
            with os.scandir(folder) as entries:
                for index, entry in enumerate(entries):
                    if index >= 512 or time.monotonic() > deadline:return
                    if entry.name.casefold().endswith(suffix) and entry.is_file(follow_symlinks=False):
                        yield Path(entry.path)
        except OSError:return
    for library in sorted(libraries)[:32]:
        if time.monotonic() > deadline:break
        apps = Path(library)/'steamapps'
        for path in manifests(apps,'.acf'):
            if not path.name.casefold().startswith('appmanifest_'):continue
            text = read_manifest_text(path)
            entry = parse_steam_manifest(text, str(apps)) if text else None
            if entry:result.append(entry)
    program_data = os.environ.get('ProgramData', r'C:\ProgramData')
    for path in manifests(Path(program_data)/'Epic'/'EpicGamesLauncher'/'Data'/'Manifests','.item'):
        text = read_manifest_text(path); entry = parse_epic_manifest(text) if text else None
        if entry:result.append(entry)
    for root, package_name in package_roots:
        if time.monotonic() > deadline:break
        for relative in ('MicrosoftGame.config', 'Content/MicrosoftGame.config'):
            text = read_manifest_text(Path(root)/relative)
            entry = parse_xbox_game_config(text,root,package_name) if text else None
            if entry:
                result.append(entry)
                break
    unique = {(x.root,x.source,x.game_id):x for x in result}
    return tuple(unique[key] for key in sorted(unique))[:MAX_INSTALLATIONS]


def snapshot_windows() -> tuple[WindowEvidence, ...]:
    """Read bounded visible window/process identities; never capture or activate."""
    if sys.platform != 'win32':return ()
    import psutil
    import win32gui
    import win32process
    foreground = win32gui.GetForegroundWindow(); result = []; observed = 0
    processes = {}
    def visit(hwnd, _):
        nonlocal observed
        observed += 1
        if observed > MAX_WINDOWS:return False
        try:
            if not win32gui.IsWindowVisible(hwnd):return True
            title = win32gui.GetWindowText(hwnd)
            if not title:return True
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
            if pid == os.getpid():return True
            if pid not in processes:
                process = psutil.Process(pid)
                with process.oneshot():
                    identity = ProcessIdentity(pid,process.create_time(),process.exe())
                processes[pid] = identity
            left,top,right,bottom = win32gui.GetWindowRect(hwnd)
            # Recheck PID after querying process metadata to reject recycled HWNDs.
            if (win32process.GetWindowThreadProcessId(hwnd)[1] != pid
                    or psutil.Process(pid).create_time() != processes[pid].create_time):return True
            result.append(WindowEvidence(int(hwnd),title,processes[pid],max(0,right-left),max(0,bottom-top),
                                         True,bool(win32gui.IsIconic(hwnd)),hwnd==foreground))
        except (OSError, ValueError, psutil.Error):pass
        return True
    try:win32gui.EnumWindows(visit,None)
    except Exception:
        # pywin32 treats an explicit enumeration limit as an API failure. Never
        # select from a partial enumeration whose omitted windows are unknown.
        if observed > MAX_WINDOWS:raise ValueError('Window evidence exceeds bounds') from None
        raise
    if observed > MAX_WINDOWS:
        raise ValueError('Window evidence exceeds bounds')
    return tuple(result)


class WindowsGameAdapter:
    """Lazy read-only evidence adapter with bounded catalog refresh/recovery."""
    def __init__(self, *, window_reader: Callable = snapshot_windows,
                 catalog_reader: Callable = discover_game_installations,
                 trusted_installations: tuple[GameInstallation, ...] = (),
                 refresh_seconds: float = 30.0, clock: Callable = time.monotonic):
        self._window_reader = window_reader; self._catalog_reader = catalog_reader
        self._trusted = tuple(trusted_installations)
        if len(self._trusted) > MAX_INSTALLATIONS or any(not isinstance(x,GameInstallation) for x in self._trusted):
            raise ValueError('Invalid trusted installation catalog')
        self._refresh_seconds = max(1.0,min(float(refresh_seconds),300.0))
        self._clock = clock; self._catalog = (); self._next_catalog = 0.0
        self._cached_windows = ()

    @property
    def cached_windows(self) -> tuple[WindowEvidence, ...]:
        """Last successful worker enumeration; never performs discovery itself."""
        return self._cached_windows

    def snapshot_windows(self):
        self._cached_windows = ()
        windows = tuple(islice(self._window_reader(), MAX_WINDOWS + 1))
        if len(windows) <= MAX_WINDOWS and all(isinstance(w,WindowEvidence) for w in windows):
            self._cached_windows = windows
        return windows

    def decide(self, *, manual=None, previous=None, approved_game=None):
        if isinstance(manual, ManualSource) and manual.kind == 'screen':
            self._cached_windows = ()
            return select_capture((),(),manual=manual,previous=previous)
        try:windows = self.snapshot_windows()
        except Exception:
            return SelectionDecision(None,'WINDOW_EVIDENCE_UNAVAILABLE',_previous_key(previous) is not None,
                                     manual is not None,manual_source=manual)
        if manual is not None:
            return select_capture(windows,(),manual=manual,previous=previous)
        now = self._clock()
        if now >= self._next_catalog:
            try:self._catalog = tuple(islice(self._catalog_reader(), MAX_INSTALLATIONS + 1))
            except Exception:self._catalog = ()
            self._next_catalog = now + self._refresh_seconds
        return select_capture(windows, self._trusted+self._catalog, previous=previous, approved_game=approved_game)
