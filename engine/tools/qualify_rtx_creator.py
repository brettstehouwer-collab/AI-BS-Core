"""Controlled source-creator acceptance of an existing qualified LH Prop01 variant.

Use recovery Python: --source-root QUALIFIED_VARIANT_ROOT --output NEW_FIXTURE_ROOT.
Both paths must remain under the reviewed D: RTX variants root. All copies and
receipts are create-only. Real ContentView and pinned native owners/viewport are
used offscreen; AI is explicitly disabled. No installed Studio or human-play
qualification is implied. A retained child is never restarted on a timeout.
"""
from contextlib import ExitStack
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import uuid
from unittest.mock import patch

ROOT = Path('C:/AI-BS')
VARIANTS = Path('D:/AI-BS-Game-Resources/RTX_Variants_20261111')
SDK = Path('D:/AI-BS-Game-Resources/P110/SDK174Recovery/sdk-preview-release/bin')
GPU = Path('D:/AI-BS-Game-Resources/Prop01_Native_Acceptance_20261105/build/Release/prop01_gpu_acceptance.exe')
EXPECTED_TOOLS = {
    SDK/'aibs_content_host.exe': '977d2d3d46abba6bfd8bb93b66acf08e0b9aaf1bece1bc63633f7f534b04f580',
    SDK/'aibs_creator_viewport.exe': '1f1d99a285092a1f77205577ba7b7dd6035d89da88179d82ce7162fc45d85643',
    SDK/'aibs_assetc.exe': 'f2c4ed2cbbc5c570cd56c699fa3c2a4b5787e675f91c82c46792bebca4e9700f',
    GPU: '8aad645aebce9f25c56a81a9d0c34882d5c743c6cd466e9bd8de36a3f10e4778',
}


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def long(path):
    value = str(path.absolute())
    return Path(value if value.startswith('\\\\?\\') else '\\\\?\\' + value)


def plain(path):
    for item in (path, *path.parents):
        p = long(item)
        if p.exists():
            need(not p.is_symlink() and not p.lstat().st_file_attributes & 0x400,
                 'Reparse/symlink fixture storage is not supported')


def read(path, maximum=64 * 1024 * 1024):
    plain(path)
    with long(path).open('rb') as stream:
        value = stream.read(maximum+1)
    need(len(value) <= maximum, 'Bounded fixture read exceeded')
    return value


def pin(path):
    value = read(path)
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}


def write(path, value):
    plain(path.parent)
    with long(path).open('xb') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, value):
    write(path, (json.dumps(value, indent=2, allow_nan=False)+'\n').encode('utf8'))


def load(path):
    return json.loads(read(path, 4 * 1024 * 1024).decode('utf-8-sig'))


def tree(directory):
    plain(directory)
    need(long(directory).is_dir(), 'Expected existing seed directory')
    rows, total = {}, 0
    root_long = long(directory)
    for here, dirs, files in os.walk(root_long, followlinks=False):
        for name in dirs:
            plain(Path(here)/name)
        for name in sorted(files):
            file = Path(here)/name
            info = pin(file)
            total += info['bytes']
            need(len(rows) < 2048 and total <= 512 * 1024 * 1024, 'Seed tree exceeds bounded fixture budget')
            rows[file.relative_to(root_long).as_posix()] = info
    return rows


def copy_tree(source, target, *, exclude=frozenset()):
    need(not long(target).exists(), 'Never replace an existing fixture destination')
    rows = tree(source)
    long(target).mkdir()
    for relative, info in rows.items():
        if relative in exclude:
            continue
        dest = target / relative
        long(dest.parent).mkdir(parents=True, exist_ok=True)
        write(dest, read(source / relative))
        need(pin(dest) == info, 'Create-only seed copy differs')


def tool_pins():
    pins = {str(path): pin(path) for path in EXPECTED_TOOLS}
    need(all(pins[str(path)]['sha256'] == expected for path, expected in EXPECTED_TOOLS.items()),
         'Pinned native tool identity changed')
    capabilities = load(SDK/'aibs_capabilities.json')
    need(capabilities['sdk_version'] == '0.17.4' and capabilities['features']['chapter_asset_surfaces'],
         'Expected retained SDK174 capabilities')
    for shader in sorted((SDK/'shaders').glob('*.cso')):
        pins[str(shader)] = pin(shader)
    return pins


def source_state(source):
    result = {'gpu_project': tree(source/'gpu/project'), 'repeated_pack': tree(source/'cooked_repeated')}
    for name in ('variant/variant_manifest.json', 'cpu/create-verification.json', 'gpu/expected_gpu.txt',
                 'gpu/base.aibd', 'gpu/captures/contextual_chapter.bmp', 'gpu/captures/closeup_front_quarter.bmp'):
        result[name] = pin(source/name)
    return result


def identity(source):
    manifest, cpu = load(source/'variant/variant_manifest.json'), load(source/'cpu/create-verification.json')
    need(manifest['coordinate_convention'] == 'dx12-left-handed', 'Use the explicitly qualified LH variant')
    lines = read(source/'gpu/expected_gpu.txt', 8192).decode('ascii').splitlines()
    need(len(lines) == 10 and lines[0] == 'PROP01-GPU-ACCEPTANCE 1', 'Expected actual GPU seed receipt')
    proxies = [row['id'] for row in cpu['proxy_parts']]
    need(len(proxies) == 4 and proxies == lines[2].split(';') and cpu['placement_id'] == lines[1],
         'CPU/GPU fixture identities differ')
    reference = [cpu[key] for key in ('asset_id', 'asset_sha256', 'pack_sha256')]
    need(reference == lines[6:9] and reference[0] == manifest['hero_asset_id'], 'Hero source references differ')
    need(pin(source/'gpu/project/chapter.aiba')['sha256'] == lines[5] and
         pin(source/'gpu/project/opening.aibd')['sha256'] == lines[4], 'Saved GPU seed bytes differ')
    return {'hero': lines[1], 'proxies': proxies, 'hero_ref': reference,
            'repeated_id': manifest['repeated_asset_id'], 'seed_lines': lines}


def safe_environment():
    values = {key: value for key, value in os.environ.items()
              if key.upper() in {'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP',
                                 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA'}}
    values.update(QT_QPA_PLATFORM='offscreen', AIBS_HEADLESS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    return values


class OwnedProcess:
    def __init__(self, pid):
        import _winapi
        import psutil
        process = psutil.Process(pid)
        self.pid, self.created = pid, process.create_time()
        need(Path(process.exe()).resolve() == (SDK/'aibs_content_host.exe').resolve(), 'Unexpected owned host executable')
        self.handle = _winapi.OpenProcess(0x100000 | 0x1000, False, pid)
        need(process.create_time() == self.created, 'Host identity changed during handle capture')

    def receipt(self):
        return {'pid': self.pid, 'created': self.created, 'retained_exact_handle': True}

    def finish(self):
        import _winapi
        need(_winapi.WaitForSingleObject(self.handle, 0) == 0, 'Owned host is not terminal')
        code = _winapi.GetExitCodeProcess(self.handle)
        _winapi.CloseHandle(self.handle)
        self.handle = None
        need(code == 0, 'Owned host did not close normally with exit0')
        return {**self.receipt(), 'terminal': True, 'exit_code': code}


def run_worker(source, output, phase):
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['AIBS_HEADLESS'] = '1'
    sys.path.insert(0, str(ROOT))
    # The recovery interpreter intentionally has no GUI packages. Reuse the
    # existing isolated reviewed Qt runtime, without install or global changes.
    qt_site = ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages'
    qt_bin = qt_site/'PyQt6/Qt6/bin'
    plain(qt_site); plain(qt_bin)
    need(qt_bin.is_dir(), 'Reviewed isolated Qt runtime is unavailable')
    sys.path.insert(0, str(qt_site))
    os.environ['PATH'] = str(qt_bin) + ';C:\\Windows\\System32'
    qt_dll_scope = os.add_dll_directory(str(qt_bin))
    from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication, QEvent
    from PyQt6 import QtCore
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFontDatabase, QFont, QRawFont
    from PyQt6 import sip
    from native_studio.game_engine.content_view import ContentView

    calls = {'network': 0, 'provider': 0}

    def forbidden_network(*args, **kwargs):
        calls['network'] += 1
        raise RuntimeError('Network access is disabled in this creator fixture')

    class DenyAI(QObject):
        inventory_ready = pyqtSignal(object, object)
        proposal_ready = pyqtSignal(str, str)
        failed = pyqtSignal(str, str)
        state_changed = pyqtSignal(str)
        busy = False

        def refresh_models(self):
            calls['provider'] += 1
            raise RuntimeError('AI inventory is disabled in this fixture')

        def generate(self, *args, **kwargs):
            calls['provider'] += 1
            raise RuntimeError('Model generation is disabled in this fixture')

        def cancel(self):
            return None

    config = load(output/'.rtx-creator-fixture.json')
    need(config['tool_sha256'] == pin(Path(__file__))['sha256'] and config['source'] == str(source),
         'Fixture source/configuration differs from its parent preparation')
    ident = config['identity']
    owner, view = None, None
    app = QApplication([])
    # This Qt offscreen platform has an empty generic font database on Windows.
    # Register existing OS fonts only for this process; never install/copy fonts
    # or change Windows/user preferences to make a fixture screenshot readable.
    fonts = []
    family_count_before = len(QFontDatabase.families())
    for name in ('segoeui.ttf', 'segoeuib.ttf', 'consola.ttf', 'consolab.ttf'):
        path = Path('C:/Windows/Fonts')/name
        need(path.is_file(), 'Required offscreen fixture font is missing')
        identifier = QFontDatabase.addApplicationFont(str(path))
        need(identifier >= 0, 'Could not register process-local fixture font')
        fonts.append({'name': name, 'families': QFontDatabase.applicationFontFamilies(identifier),
                      **pin(path)})
    app.setFont(QFont('Segoe UI', 9))
    raw_font = QRawFont.fromFont(app.font())
    glyphs = raw_font.glyphIndexesForString('AI-BS Creator 0123456789')
    need(raw_font.isValid() and glyphs and all(glyph != 0 for glyph in glyphs),
         'Offscreen fixture font lacks required label glyphs')
    record = {'schema': 1, 'stage': phase, 'status': 'INCOMPLETE', 'python_pid': os.getpid(),
              'scope': 'Actual source ContentView configured with explicit AI-disabled adapter; real pinned SDK owners/hidden viewport',
              'qt_runtime': {'site_packages': str(qt_site), 'qt_version': QtCore.QT_VERSION_STR,
                             'pyqt_version': QtCore.PYQT_VERSION_STR,
                             'core_extension': pin(Path(QtCore.__file__)),
                             'font_family_count_before': family_count_before,
                             'font_family_count_after': len(QFontDatabase.families()),
                             'process_local_fonts': fonts, 'label_glyphs_verified': True}}

    def spin(predicate, label, timeout=25):
        deadline = time.monotonic()+timeout
        while not predicate():
            if time.monotonic() > deadline:
                raise TimeoutError(label + '; owned resources retained, no replacement started')
            app.processEvents()
            time.sleep(.005)

    def idle(label):
        spin(lambda: view.loaded and view.client.state == 'ready' and not view.busy and
             not view.client.pending_count and not view.asset_client.busy, label)

    def rows():
        return {row.uuid: {'type': row.type_id, 'name': row.name,
                           'fields': {key: value for key, value in row.fields}} for row in view.rows}

    def hero_fields():
        return rows()[ident['hero']]['fields']

    def check_reference():
        fields = hero_fields()
        need([fields[key] for key in ('asset_id', 'asset_sha256', 'pack_sha256')] == ident['hero_ref'],
             'Actual hero fields differ from pinned LH source')

    def viewport(label):
        probe = output/label
        need(not long(probe).exists(), 'Viewport evidence directory must be new')
        long(probe).mkdir()
        need(view.select_entity(ident['hero']), 'Actual hero selection unavailable')
        view.open_viewport(probe_directory=probe)
        selected_paths = set()

        def completed():
            executable = getattr(view.viewport, '_content_executable', None)
            if executable is not None:
                selected_paths.add(str(Path(executable).resolve()))
            return (not view.busy and view.viewport.state == 'closed' and
                    not view.client.pending_count and not view.asset_client.busy and
                    view.viewport.dependency_process_id == 0 and long(probe/'viewport.json').is_file())

        spin(completed, label+' hidden viewport and dependency drain', 45)
        need(selected_paths == {str((SDK/'aibs_creator_viewport.exe').resolve())},
             'Exact pinned viewport binary selection was not observed')
        viewport_pin = pin(SDK/'aibs_creator_viewport.exe')
        need(viewport_pin['sha256'] == EXPECTED_TOOLS[SDK/'aibs_creator_viewport.exe'],
             'Observed viewport binary bytes differ from the retained SDK pin')
        report = load(probe/'viewport.json')
        need(report.get('debug_errors') == 0 and report.get('nonbackground_pixels', 0) > 100 and
             report.get('selected_uuid') == ident['hero'], 'Hidden viewport pixels/debug/selection failed')
        need(view._content_snapshot is not None and view._content_snapshot.payload, 'Real native export snapshot missing')
        record[label] = {'report': report, 'observed_executable_paths': sorted(selected_paths),
                         'observed_executable_pin': viewport_pin,
                         'selection_scope': 'Existing native hidden-window internal fixture; no desktop/user click claim'}
        return view._content_snapshot

    def capture(label):
        path = output/(label+'.png')
        need(not long(path).exists(), 'Never overwrite offscreen UI capture')
        need(view.grab().save(str(long(path)), 'PNG'), 'Offscreen widget render failed')
        record[label] = pin(path)

    def close_normally(*, discard=False):
        idle('Final creator drain before close')
        need(discard or (not view.client.dirty and not view.client.uncertain_operations),
             'Save admission is incomplete; no diagnostic discard was authorized')
        view.close_project(discard=discard)
        spin(lambda: view.client.state == 'closed' and view._children_closed(), 'Normal owned creator close')
        need(not getattr(view.client, '_killed', False), 'Owned host required forced cleanup')
        record['host'] = owner.finish()
        view.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        sip.delete(view)
        app.processEvents()

    def state_receipt():
        return {'state': view.client.state, 'dirty': view.client.dirty,
                'pending': view.client.pending_count, 'viewport': view.viewport.state,
                'asset_busy': view.asset_client.busy, 'rows': rows(),
                'uncertain_operation_count': len(view.client.uncertain_operations),
                'host': owner.receipt() if owner is not None else None,
                'host_epoch': view.client.head.scope.host_epoch if view.client.head else None,
                'head_revision': view.client.head.head_revision if view.client.head else None}

    def idle_for_diagnostic_close():
        return (view.loaded and view.client.state == 'ready' and not view.busy and
                not view.client.pending_count and not view.asset_client.busy and view._children_closed())

    def retained_failure_control():
        """Failure-only local test control, bound to this exact worker and fixture.

        Request basename: <stage>-close-retained-fixture[-<32hex request ID>].json
        Body has exactly fixture_nonce, worker_pid, discard_retained_fixture.
        Dirty/uncertain test-only RAM requires explicit true after preserving its
        complete visible rows/head state. Saved files are never deleted/replaced.
        """
        marker = output/(phase+'-retained-state.json')
        write_json(marker, {'status': 'OWNED_RESOURCES_RETAINED', 'worker_pid': os.getpid(),
                            'state': state_receipt(), 'control_prefix': phase+'-close-retained-fixture',
                            'fixture_config': '.rtx-creator-fixture.json'})
        seen = set()
        expression = re.compile(re.escape(phase)+r'-close-retained-fixture(?:-[a-f0-9]{32})?\.json\Z')
        while True:
            app.processEvents()
            candidates = [path for path in long(output).glob(phase+'-close-retained-fixture*.json')
                          if expression.fullmatch(path.name) and path.name not in seen]
            for path in sorted(candidates)[:16]:
                seen.add(path.name)
                response = output/(path.stem+'-receipt.json')
                result = {'status': 'REFUSED_OR_INCOMPLETE', 'worker_pid': os.getpid(),
                          'request': path.name, 'discard_requested': False}
                try:
                    request = json.loads(read(path, 4096).decode('utf8'))
                    need(isinstance(request, dict) and set(request) ==
                         {'fixture_nonce', 'worker_pid', 'discard_retained_fixture'}, 'Invalid diagnostic request schema')
                    need(request['fixture_nonce'] == config['fixture_nonce'] and
                         type(request['worker_pid']) is int and request['worker_pid'] == os.getpid() and
                         type(request['discard_retained_fixture']) is bool,
                         'Diagnostic request does not bind this fixture nonce and worker PID')
                    result['discard_requested'] = request['discard_retained_fixture']
                    # Preserve current typed fields and admission state before
                    # any explicit discard of this disposable test's RAM edits.
                    write_json(output/(path.stem+'-state-before-close.json'), state_receipt())
                    need(idle_for_diagnostic_close(), 'Pending/active resources must drain before a diagnostic close')
                    need(request['discard_retained_fixture'] or
                         (not view.client.dirty and not view.client.uncertain_operations),
                         'Dirty or uncertain fixture requires explicit discard_retained_fixture true')
                    need(owner is not None, 'Exact owned host handle unavailable; retain resources')
                    close_normally(discard=request['discard_retained_fixture'])
                    result.update(status='NORMAL_OWNED_HOST_CLOSE_AFTER_FAILED_TEST', host=record['host'],
                                  original_test_status='FAILED', saved_files_deleted=False)
                    write_json(response, result)
                    return
                except BaseException as cleanup_error:
                    result.update(error_type=type(cleanup_error).__name__, error=str(cleanup_error))
                    write_json(response, result)
            time.sleep(.05)

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', forbidden_network))
        stack.enter_context(patch.object(socket, 'create_connection', forbidden_network))
        try:
            view = ContentView(executable=SDK/'aibs_content_host.exe', asset_cooker=SDK/'aibs_assetc.exe',
                               sample_asset_pack=source/'cooked_repeated', ai_client=DenyAI())
            view.resize(1400, 1000)
            view.open_project(output/'project')
            idle('Open owned creator project')
            owner = OwnedProcess(view.client.process_id)
            record['host_opened'] = owner.receipt()
            record['host_epoch'] = view.client.head.scope.host_epoch
            need(view.definition.asset_profile == 'warm-beginning', 'Typed surface profile was not retained')
            check_reference()
            initial = rows()
            initial_content_revision = view.description.content_revision
            initial_definition_id = view.description.definition_id
            need(all(uid in initial for uid in ident['proxies']), 'Owned compound proxy UUID missing')
            if phase == 'author':
                write_json(output/'baseline-rows.json', initial)
                need(view.select_entity(ident['hero']), 'Hero is absent from actual outliner')
                capture('creator_selected')
                viewport('viewport_initial')
                view.inspect_asset_pack(source/'cooked_repeated', adopt_after=True)
                spin(lambda: view.adopted_asset is not None and not view.busy and not view.asset_client.busy,
                     'Inspect/adopt actual repeated LH pack')
                need(view.adopted_asset.asset_id == ident['repeated_id'], 'Repeated LH asset identity differs')
                view.preview_asset_placement('LH repeated creator instance', center=(-23.55,.0375,-22.35),
                                             scale=(44.117647,)*3)
                spin(lambda: view.apply_button.isEnabled(), 'Repeated asset Preview')
                need(rows() == initial, 'Preview mutated authoritative rows')
                view.apply_preview()
                idle('Apply repeated asset')
                repeated = view.selected_id
                placed = rows()
                need(repeated not in initial and set(placed) == set(initial)|{repeated} and
                     all(placed[uid] == value for uid,value in initial.items()), 'Repeated apply changed unrelated rows')
                need(placed[repeated]['fields']['asset_id'] == ident['repeated_id'], 'Placed reference is not the actual repeated pack')
                view.delete_selected()
                idle('Delete only newly placed repeated instance')
                need(rows() == initial, 'Delete did not restore exact baseline rows')
                view.undo_button.click()
                idle('Undo repeated deletion')
                need(rows() == placed, 'Undo lost repeated identity or other typed fields')
                view.redo_button.click()
                idle('Redo repeated deletion')
                need(rows() == initial, 'Redo changed baseline fields')
                need(view.select_entity(ident['hero']), 'Hero selection lost')
                original_x = hero_fields()['x']
                moved_x = original_x+1.5
                view.field_editors['x'].setText(str(moved_x))
                revision = view.client.head.head_revision
                view.preview_button.click()
                spin(lambda: view.apply_button.isEnabled(), 'Hero field Preview')
                need(rows() == initial and view.client.head.head_revision == revision, 'Hero Preview changed authoritative head')
                view.apply_preview()
                idle('Apply hero movement')
                moved = rows()
                need(hero_fields()['x'] == moved_x and all(moved[uid] == value for uid,value in initial.items()
                     if uid != ident['hero']), 'Hero movement changed unrelated rows')
                capture('creator_moved')
                view.undo_button.click(); idle('Undo hero movement')
                need(rows() == initial, 'Hero Undo did not restore all typed fields')
                view.redo_button.click(); idle('Redo hero movement')
                need(rows() == moved, 'Hero Redo lost moved fields')
                view.undo_button.click(); idle('Restore hero baseline before Save')
                need(rows() == initial, 'Final hero restoration differs')
                view.save_button.click(); idle('Acknowledged creator Save')
                need(not view.client.dirty, 'Creator did not acknowledge durable Save')
                snapshot = viewport('viewport_saved')
                need(hashlib.sha256(snapshot.payload).hexdigest() == snapshot.fingerprint, 'Exported snapshot digest differs')
                need(snapshot.definition_id == initial_definition_id and
                     snapshot.content_revision >= initial_content_revision,
                     'Saved export lost its definition or regressed content revision')
                # Save commits the journal. The immutable opening export is a
                # separate explicit artifact, and identical typed fields can
                # have a newer document revision after create/delete/history.
                write(output/'project/opening.aibd', snapshot.payload)
                need(read(output/'project/opening.aibd') == snapshot.payload,
                     'Explicit saved export differs from current native snapshot')
                record.update(baseline_row_count=len(initial), repeated_uuid=repeated,
                              baseline_content_revision=initial_content_revision,
                              saved_content_revision=snapshot.content_revision,
                              seed_export=pin(output/'seed-opening.aibd'),
                              saved_fingerprint=snapshot.fingerprint,
                              journal=pin(output/'project/chapter.aiba'), opening=pin(output/'project/opening.aibd'))
                # Actual authoring host identity, never a dummy epoch or Python PID.
                lines = ['PROP01-GPU-ACCEPTANCE 1', ident['hero'], ';'.join(ident['proxies']),
                         record['host_epoch'], snapshot.fingerprint, record['journal']['sha256'],
                         *ident['hero_ref'], str(owner.pid)]
                write(output/'expected_gpu.txt', ('\n'.join(lines)+'\n').encode('ascii'))
            else:
                first = load(output/'author.json')
                need(os.getpid() != first['python_pid'] and owner.pid != first['host_opened']['pid'] and
                     record['host_epoch'] != first['host_epoch'], 'Fresh Python/native owner identity not established')
                need(initial == load(output/'baseline-rows.json'), 'Fresh process lost typed fields or enclosed proxy parameters')
                need(pin(output/'project/chapter.aiba') == first['journal'] and
                     pin(output/'project/opening.aibd') == first['opening'], 'Saved bytes changed before fresh reopen')
                snapshot = viewport('viewport_reopened')
                need(snapshot.fingerprint == first['saved_fingerprint'], 'Fresh native export fingerprint differs')
                capture('creator_reopened')
                need(pin(output/'project/chapter.aiba') == first['journal'], 'Read/reopen modified durable journal')
            close_normally()
            need(calls == {'network': 0, 'provider': 0}, 'A denied network/provider attempt occurred')
            record.update(status='PASS', denied_calls=calls,
                          source_pins={str(Path(module.__file__).resolve()): pin(Path(module.__file__))
                            for module in list(sys.modules.values()) if getattr(module, '__file__', None)
                            and str(Path(module.__file__).resolve()).startswith(str(ROOT/'native_studio'))
                            and str(module.__file__).endswith('.py')})
            write_json(output/(phase+'.json'), record)
        except BaseException as error:
            record.update(status='FAILED', error_type=type(error).__name__, error=str(error), denied_calls=calls)
            if view is not None:
                record['failure_state'] = state_receipt()
            write_json(output/(phase+'-failure.json'), record)
            # Preserve a dirty/pending fixture and its real owned resources for
            # diagnosis. Parent detects this receipt and reports retention; it
            # does not kill/restart the child or discard unsaved authoring state.
            if view is not None and (view.client.state != 'closed' or not view._children_closed()):
                closed = False
                if (owner is not None and idle_for_diagnostic_close() and
                        not view.client.dirty and not view.client.uncertain_operations):
                    try:
                        close_normally()
                        write_json(output/(phase+'-failure-cleanup.json'), {
                            'status': 'NORMAL_CLEAN_IDLE_HOST_CLOSE_AFTER_FAILED_TEST',
                            'host': record['host'], 'original_test_status': 'FAILED'})
                        closed = True
                    except BaseException as cleanup_error:
                        write_json(output/(phase+'-failure-cleanup.json'), {
                            'status': 'INCOMPLETE', 'error_type': type(cleanup_error).__name__,
                            'error': str(cleanup_error), 'original_test_status': 'FAILED'})
                if not closed:
                    retained_failure_control()
            raise


def run_owned(command, output, stage, environment):
    import psutil
    stdout, stderr = output/(stage+'.stdout.log'), output/(stage+'.stderr.log')
    with long(stdout).open('xb') as out, long(stderr).open('xb') as err:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
            env=environment, cwd=ROOT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        created = psutil.Process(process.pid).create_time()
        started = time.monotonic()
        while process.poll() is None:
            retained = output/(stage+'-retained-state.json')
            if long(retained).is_file() or time.monotonic()-started > 180:
                result = {'pid': process.pid, 'created': created, 'terminal': False,
                          'status': 'RETAINED_OR_UNCONFIRMED_DO_NOT_RESTART', 'stage': stage}
                write_json(output/(stage+'-retained-process.json'), result)
                raise RuntimeError('Owned '+stage+' process retained; inspect exact identity before further action')
            time.sleep(.05)
        result = {'pid': process.pid, 'created': created, 'terminal': True,
                  'exit_code': process.returncode, 'stage': stage}
    write_json(output/(stage+'-process.json'), result)
    need(process.returncode == 0, 'Owned '+stage+' process failed; logs retained')
    return result


def orchestrate(source, output):
    need(source.is_relative_to(VARIANTS.resolve()) and output.is_relative_to(VARIANTS.resolve()) and
         output.parent.is_dir() and not long(output).exists() and not output.is_relative_to(source),
         'Use a qualified source and new separate output under reviewed RTX root')
    plain(source); plain(output)
    tools, before, ident = tool_pins(), source_state(source), identity(source)
    long(output).mkdir()
    record = {'schema': 1, 'status': 'INCOMPLETE', 'source': str(source),
              'scope': 'Controlled current-source creator, AI disabled; not installed Studio, ordinary play, performance or release qualification',
              'tools': tools, 'seed_before': before, 'identity': ident, 'processes': []}
    try:
        # Preserve the old static export separately; never overwrite it or
        # pretend that saving the journal updates a previously exported file.
        write(output/'seed-opening.aibd', read(source/'gpu/project/opening.aibd'))
        copy_tree(source/'gpu/project', output/'project', exclude=frozenset({'opening.aibd'}))
        write(output/'base.aibd', read(source/'gpu/base.aibd'))
        long(output/'captures').mkdir()
        for name in ('contextual_chapter.bmp', 'closeup_front_quarter.bmp'):
            write(output/'captures'/name, read(source/'gpu/captures'/name))
        write_json(output/'.rtx-creator-fixture.json', {'schema': 1, 'source': str(source),
            'fixture_nonce': uuid.uuid4().hex, 'tool_sha256': pin(Path(__file__))['sha256'], 'identity': ident})
        for stage in ('author', 'reopen'):
            command = [sys.executable, '-B', str(Path(__file__).resolve()), '--source-root', str(source),
                       '--output', str(output), '--stage', stage]
            record['processes'].append(run_owned(command, output, stage, safe_environment()))
            need(load(output/(stage+'.json'))['status'] == 'PASS', 'Creator worker receipt did not pass')
        record['processes'].append(run_owned([str(GPU), '--reopen-verify', '--output', str(output),
            '--shaders', str(SDK/'shaders')], output, 'gpu_reopen', safe_environment()))
        gpu = load(output/'gpu-reopen-verification.json')
        need(gpu['status'] == 'passed' and gpu['debug_errors'] == gpu['debug_warnings'] == 0 and
             gpu['reopen_pixel_diff_contextual'] == gpu['reopen_pixel_diff_closeup'] == 0,
             'Actual GPU reopen/pixel/debug acceptance failed')
        need(source_state(source) == before and tool_pins() == tools, 'Protected source or native tools changed')
        record.update(status='PASS_CONTROLLED_SOURCE_CREATOR', seed_unchanged=True, tools_unchanged=True,
                      author=load(output/'author.json'), reopen=load(output/'reopen.json'), gpu_reopen=gpu)
    except BaseException as error:
        record.update(status='FAILED_OR_RETAINED', error_type=type(error).__name__, error=str(error))
        try:
            record['seed_unchanged'] = source_state(source) == before
        except Exception as check_error:
            record['preservation_check_error'] = type(check_error).__name__
        raise
    finally:
        write_json(output/'creator-acceptance.json', record)
        print(json.dumps({'status': record['status'], 'receipt': str(output/'creator-acceptance.json')}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--stage', choices=('author', 'reopen'))
    args = parser.parse_args()
    source, output = args.source_root.resolve(strict=True), args.output.absolute()
    if args.stage:
        need(output.is_relative_to(VARIANTS.resolve()) and source.is_relative_to(VARIANTS.resolve()),
             'Worker paths outside reviewed fixture root')
        tool_pins()
        run_worker(source, output, args.stage)
    else:
        orchestrate(source, output)


if __name__ == '__main__':
    main()
