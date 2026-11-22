"""Create-only current-source Qt saved-player READY/STOPPED/resume acceptance.

Opens only the explicitly pinned game's own visible windows. No desktop input,
model calls, original saves, rendering/performance or human-play claims.
"""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qualify_rtx_creator import (ROOT, VARIANTS, SDK, need, plain, long, read, pin,
    write_json, load, tree, copy_tree, safe_environment)

SOURCE = VARIANTS/'Creator_LH_20261111_v05/project'
PLAYER = ROOT/'t/hudvis_build01/frozen_v02/aibs_motherboard.exe'
CANDIDATE = ROOT/'t/hudvis_build01/frozen-candidate-v02.json'
PLAYER_SHA = '60ee067f229e040a359e302bb90def884d49223af5a616e6065d9fced1583cda'
HOST_SHA = '977d2d3d46abba6bfd8bb93b66acf08e0b9aaf1bece1bc63633f7f534b04f580'
COOKER_SHA = 'f2c4ed2cbbc5c570cd56c699fa3c2a4b5787e675f91c82c46792bebca4e9700f'


def tools():
    candidate = load(CANDIDATE)
    for name, expected in candidate['artifact_pins'].items():
        need(pin(Path(name)) == expected, 'Current player artifact pin mismatch: '+name)
    for name, expected in candidate['source_pins'].items():
        current = ROOT/Path(name).relative_to(Path(candidate['worktree']))
        need(pin(current)['sha256'] == expected, 'Compiled current source differs: '+str(current))
    result = {name: pin(path) for name, path in {
        'player': PLAYER, 'host': SDK/'aibs_content_host.exe',
        'cooker': SDK/'aibs_assetc.exe', 'candidate': CANDIDATE,
        'harness': Path(__file__)}.items()}
    result['source_ui'] = {name: pin(ROOT/'native_studio/game_engine'/name) for name in (
        'content_view.py', 'saved_play.py', 'saved_play_storage.py', 'saved_chapter_export.py',
        'project_assets.py', 'content_client.py')}
    need(result['player']['sha256'] == PLAYER_SHA and result['host']['sha256'] == HOST_SHA
         and result['cooker']['sha256'] == COOKER_SHA, 'Exact native identities changed')
    return result


class ProcessHandle:
    def __init__(self, pid, executable):
        import _winapi
        import psutil
        process = psutil.Process(pid)
        need(Path(process.exe()).resolve() == executable.resolve(), 'Unexpected child executable')
        self.pid, self.birth = pid, process.create_time()
        self.handle = _winapi.OpenProcess(0x100000 | 0x1000, False, pid)
        need(process.create_time() == self.birth, 'PID identity changed')
        self.path = str(executable)

    def receipt(self):
        return {'pid': self.pid, 'birth': self.birth, 'executable': self.path,
                'exact_handle_retained': True}

    def finish(self):
        import _winapi
        need(_winapi.WaitForSingleObject(self.handle, 0) == 0, 'Owned child is not terminal')
        code = _winapi.GetExitCodeProcess(self.handle)
        _winapi.CloseHandle(self.handle)
        self.handle = None
        need(code == 0, 'Owned child did not return exit0')
        return {**self.receipt(), 'terminal': True, 'exit_code': code}


def worker(output):
    sys.path.insert(0, str(ROOT))
    qt_site = ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages'
    qt_bin = qt_site/'PyQt6/Qt6/bin'
    plain(qt_site); plain(qt_bin)
    sys.path.insert(0, str(qt_site))
    os.environ['PATH'] = str(qt_bin)+';C:\\Windows\\System32'
    dll_scope = os.add_dll_directory(str(qt_bin))
    from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication, QEvent
    from PyQt6.QtWidgets import QApplication
    from PyQt6 import sip, QtCore
    from native_studio.game_engine.content_view import ContentView
    from native_studio.game_engine.saved_chapter_export import hash_saved_journal
    from native_studio.game_engine.saved_play_storage import revalidate_publication

    config = load(output/'fixture.json')
    need(config['tools'] == tools(), 'Prepared tool identity changed')
    project = output/'project'
    app = QApplication([])
    calls = {'network': 0, 'provider': 0}
    record = {'status': 'INCOMPLETE', 'scope': 'Actual source ContentView; explicit AI-disabled adapter and pinned current player; saved lifecycle only',
              'python_pid': os.getpid(), 'qt': QtCore.QT_VERSION_STR,
              'invocations': [], 'calls': calls, 'human_input_verified': False,
              'route_or_action_durability_verified': False, 'performance_measured': False,
              'installed_studio_or_default_launcher_qualified': False}
    view, owner = None, None

    def deny_network(*args, **kwargs):
        calls['network'] += 1
        raise RuntimeError('Network is disabled in this owned fixture')

    class DenyAI(QObject):
        inventory_ready = pyqtSignal(object, object)
        proposal_ready = pyqtSignal(str, str)
        failed = pyqtSignal(str, str)
        state_changed = pyqtSignal(str)
        busy = False
        def refresh_models(self):
            calls['provider'] += 1
            raise RuntimeError('AI disabled')
        def generate(self, *args, **kwargs):
            calls['provider'] += 1
            raise RuntimeError('AI disabled')
        def cancel(self):
            return None

    class SuppliedRuntimeView(ContentView):
        def _binary_candidates(self, name):
            if name == 'aibs_motherboard.exe':
                return (PLAYER,)
            return super()._binary_candidates(name)

    def spin(predicate, label, seconds=50):
        deadline = time.monotonic()+seconds
        while not predicate():
            if time.monotonic() > deadline:
                raise TimeoutError(label+'; no forced termination or restart')
            # Stop before the production client's timeout would force a kill.
            if view and view.saved_play._deadline is not None and view.saved_play._deadline-time.monotonic() < 2:
                view.saved_play._timer.stop()
                raise TimeoutError('Native lifecycle deadline approached; exact owned process retained')
            app.processEvents()
            time.sleep(.005)

    def idle():
        spin(lambda: view.loaded and view.client.state == 'ready' and not view.busy and
             not view.client.pending_count and not view.asset_client.busy, 'Authoring owner idle')

    def close_owner():
        idle()
        need(not view.client.dirty and not view.client.uncertain_operations, 'Dirty fixture retained')
        view.close_project(discard=False)
        spin(lambda: view.client.state == 'closed' and view._children_closed(), 'Normal authoring close')
        need(not getattr(view.client, '_killed', False), 'Authoring host forced cleanup')
        record['host'] = owner.finish()
        view.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        sip.delete(view)
        app.processEvents()

    def invoke(label):
        journal = hash_saved_journal(project)
        transitions = []
        changed = lambda state: transitions.append(state)
        view.saved_play.state_changed.connect(changed)
        handle = None
        try:
            view.start_saved_play()
            def ready():
                if (not view.busy and not view.saved_export.busy and
                        view.saved_play.state == 'closed' and
                        view.saved_play_status.text().startswith(('Saved-play path', 'Saved chapter launch failed'))):
                    raise RuntimeError(view.saved_play_status.text())
                return view.saved_play.state == 'ready'
            spin(ready, label+' READY')
            client = view.saved_play
            handle = ProcessHandle(client.process_id, PLAYER)
            publication = revalidate_publication(client.publication)
            need(client.dependency_process_id == view.saved_export.process_id == 0,
                 'Saved export/dependency workers have not joined')
            snapshot = client.snapshot
            need(snapshot.asset_refs, 'Expected actual typed asset dependencies')
            expected = {key: value for key, value in tree(snapshot.asset_store).items()
                        if key.split('/')[0] in {ref.pack_sha256 for ref in snapshot.asset_refs}}
            need(tree(publication.asset_root) == expected, 'Published typed closure bytes differ')
            need(hash_saved_journal(project) == journal, 'Implicit journal change during launch')
            session, ready_head = client.session_id, tuple(client._ready_head)
            opened = handle.receipt()
            view.stop_saved_play()
            spin(lambda: client.state == 'closed' and client.process_id == client.dependency_process_id == 0,
                 label+' STOPPED and actual process exit')
            result = dict(client.last_result or {})
            need(result.get('graceful') is True and result.get('saved') is True and
                 result.get('forced') is False and result.get('ready_seen') is True,
                 'Actual native lifecycle did not close normally with saved acknowledgement')
            expected_scope = {'play_session': session, 'timeline_id': publication.timeline_id,
                'content_fingerprint': snapshot.fingerprint, 'context': 'player_world',
                'project_id': snapshot.scope.project, 'branch_id': snapshot.scope.branch,
                'world_id': snapshot.scope.world_id}
            need(all(result.get(key) == value for key, value in expected_scope.items()), 'STOPPED scope differs')
            need(all(result[key] >= old for key, old in zip(('durable_revision', 'durable_sequence'), ready_head)),
                 'Native durable head regressed')
            need(publication.database_path.is_file() and
                 publication.database_path.with_name('world.sqlite.initialized').is_file(), 'Database/claim missing')
            need(not list(publication.slot_directory.glob('stop.*.request')), 'Stop marker not removed after exit')
            need(hash_saved_journal(project) == journal, 'Player changed authoring journal')
            receipt = {'label': label, 'opened': opened, 'terminal': handle.finish(),
                'session': session, 'timeline': publication.timeline_id, 'database': str(publication.database_path),
                'claim': pin(publication.database_path.with_name('world.sqlite.initialized')),
                'database_pin': pin(publication.database_path), 'fingerprint': snapshot.fingerprint,
                'definition_id': snapshot.definition_id, 'asset_refs': [
                    {'asset_id': ref.asset_id, 'asset_sha256': ref.asset_sha256, 'pack_sha256': ref.pack_sha256}
                    for ref in snapshot.asset_refs], 'published_closure': expected,
                'ready_head': ready_head, 'result': result, 'transitions': transitions,
                'reused_slot': publication.reused_slot, 'reused_publication': publication.reused_publication,
                'stdout': client.stdout_tail.decode('utf8', 'replace'),
                'stderr': client.stderr_tail.decode('utf8', 'replace')}
            record['invocations'].append(receipt)
            write_json(output/(label+'.json'), receipt)
            return receipt
        finally:
            view.saved_play.state_changed.disconnect(changed)

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', deny_network))
        stack.enter_context(patch.object(socket, 'create_connection', deny_network))
        try:
            view = SuppliedRuntimeView(SDK/'aibs_content_host.exe', asset_cooker=SDK/'aibs_assetc.exe', ai_client=DenyAI())
            view.open_project(project)
            idle()
            owner = ProcessHandle(view.client.process_id, SDK/'aibs_content_host.exe')
            record['host_opened'] = owner.receipt()
            need(view._play_binary(saved=True) == PLAYER, 'Actual UI did not select pinned current player')
            first = invoke('first')
            second = invoke('resume')
            need(first['session'] != second['session'] and first['opened']['pid'] != second['opened']['pid'],
                 'Resume did not use fresh native invocation')
            need(second['reused_slot'] and second['reused_publication'], 'Resume did not reuse retained slot/publication')
            for key in ('timeline', 'database', 'claim', 'fingerprint', 'asset_refs', 'published_closure'):
                need(first[key] == second[key], 'Saved resume identity differs: '+key)
            need(second['ready_head'] == [first['result']['durable_revision'], first['result']['durable_sequence']]
                 or tuple(second['ready_head']) == (first['result']['durable_revision'], first['result']['durable_sequence']),
                 'Fresh player did not reopen the acknowledged durable head')
            need(calls == {'network': 0, 'provider': 0}, 'Unexpected provider/network attempt')
            close_owner()
            record['status'] = 'PASS_ACTUAL_CURRENT_SAVED_PLAYER_LIFECYCLE'
        except BaseException as error:
            record.update(status='FAILED', error_type=type(error).__name__, error=str(error))
            if view:
                view.saved_play._timer.stop()
                record['retained_state'] = {'host': view.client.process_id, 'player': view.saved_play.process_id,
                    'dependency': view.saved_play.dependency_process_id, 'saved_state': view.saved_play.state,
                    'dirty': view.client.dirty, 'pending': view.client.pending_count,
                    'status': view.saved_play_status.text()}
            write_json(output/'worker-failure.json', record)
            if view and (view.saved_play.process_id or view.saved_play.dependency_process_id or view.busy or view.client.pending_count):
                write_json(output/'worker-retained-state.json', {'worker_pid': os.getpid(), 'nonce': config['nonce'],
                    'instruction': 'No restart/kill. Create close-retained.json with matching worker_pid and nonce to request public stop and normal clean close.'})
                control = output/'close-retained.json'
                while True:
                    app.processEvents()
                    if control.exists():
                        request = load(control)
                        if request.get('worker_pid') == os.getpid() and request.get('nonce') == config['nonce']:
                            if view.saved_play.state == 'ready':
                                view.stop_saved_play()
                            if view.saved_play.state == 'closed' and not view.busy and not view.client.pending_count:
                                close_owner()
                                write_json(output/'retained-normal-close.json', record)
                                break
                    time.sleep(.05)
            elif view and owner and view.client.state == 'ready':
                close_owner()
            raise
        finally:
            write_json(output/'worker.json', record)
    dll_scope.close()


def main():
    global PLAYER, CANDIDATE, PLAYER_SHA
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--hud-fit-candidate', action='store_true',
                        help='Use only the separately pinned HUD-fit candidate, never default/installed discovery')
    args = parser.parse_args()
    if args.hud_fit_candidate:
        from qualify_rtx_hud_fit import validate_candidate, CANDIDATE as hud_candidate
        PLAYER, _ = validate_candidate()
        CANDIDATE, PLAYER_SHA = hud_candidate, pin(PLAYER)['sha256']
    output = args.output.absolute()
    need(output.parent == VARIANTS and output.name.startswith('Saved_Player_LH_'), 'Use a new direct reviewed RTX child')
    if args.worker:
        worker(output)
        return
    need(not long(output).exists(), 'Preserve previous attempts; output must be new')
    plain(output); plain(SOURCE)
    before, pinned = tree(SOURCE), tools()
    long(output).mkdir()
    report = {'status': 'INCOMPLETE', 'source': str(SOURCE), 'source_before': before, 'tools': pinned}
    try:
        copy_tree(SOURCE, output/'project')
        write_json(output/'fixture.json', {'nonce': uuid.uuid4().hex, 'tools': pinned})
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--output', str(output), '--worker']
        if args.hud_fit_candidate:
            command.append('--hud-fit-candidate')
        with long(output/'worker.stdout.log').open('xb') as stdout, long(output/'worker.stderr.log').open('xb') as stderr:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                env=safe_environment(), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            started = time.monotonic()
            while process.poll() is None:
                if long(output/'worker-retained-state.json').exists() or time.monotonic()-started > 180:
                    report['retained_worker_pid'] = process.pid
                    raise RuntimeError('Worker retained; no kill/restart; inspect fixture control receipt')
                time.sleep(.05)
            report['worker_exit'] = process.returncode
        need(process.returncode == 0, 'Worker failed; preserved logs and fixture')
        report['worker'] = load(output/'worker.json')
        need(report['worker']['status'] == 'PASS_ACTUAL_CURRENT_SAVED_PLAYER_LIFECYCLE', 'Worker did not qualify')
        need(tree(SOURCE) == before and tools() == pinned, 'Original input or pinned source changed')
        report.update(status='PASS_ACTUAL_CURRENT_SAVED_PLAYER_LIFECYCLE', original_source_unchanged=True)
    except BaseException as error:
        report.update(status='FAILED_OR_RETAINED', error_type=type(error).__name__, error=str(error),
                      original_source_unchanged=tree(SOURCE) == before)
        raise
    finally:
        write_json(output/'saved-player-acceptance.json', report)
        print(json.dumps({'status': report['status'], 'receipt': str(output/'saved-player-acceptance.json')}), flush=True)


if __name__ == '__main__':
    main()
