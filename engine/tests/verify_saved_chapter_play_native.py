"""Opt-in real Qt -> saved export -> native stage -> saved player acceptance.

This opens only the supplied native game's own windows. It does not control
desktop input, walk a route, edit runtime rules, or claim action durability.
Run only with the parent's exclusive GPU lease and --allow-native-window.
Original projects are read-only inputs; every fixture/result is retained.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

sys.path.insert(0, 'C:/AI-BS')
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine.saved_chapter_export import hash_saved_journal
from native_studio.game_engine.saved_play_storage import checked_path, revalidate_publication

LIMIT = 128 * 1024 * 1024
ROOT_FILES = frozenset(('.aibs-chapter-project.json', 'chapter.aiba',
    'opening.aibd', 'opening-tour.aibtour', 'opening-manifest.json'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root, *, maximum=256):
    result = {}
    for path in root.rglob('*'):
        checked_path(path)
        if not path.is_file():
            continue
        if len(result) == maximum:
            raise ValueError('Acceptance inventory member limit')
        size = path.stat().st_size
        if size > 48 * 1024 * 1024:
            raise ValueError('Acceptance inventory file limit')
        result[path.relative_to(root).as_posix()] = {'bytes': size, 'sha256': sha(path)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host', 'player', 'cooker', 'source-project', 'project', 'evidence'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--old-player', type=Path, help='Optional actual SDK015 binary for capability rejection; never executed')
    parser.add_argument('--allow-native-window', action='store_true', help='Parent must grant the exclusive GPU lease before supplying this')
    args = parser.parse_args()
    if not args.allow_native_window:
        parser.error('Prepared driver is not authorized to launch without --allow-native-window and the parent GPU lease')
    host, player, cooker = (checked_path(p, directory=False) for p in (args.host, args.player, args.cooker))
    source = checked_path(args.source_project, directory=True)
    project = Path(os.path.abspath(args.project))
    evidence = Path(os.path.abspath(args.evidence))
    if project.drive.lower() != 'd:' or evidence.drive.lower() != 'd:':
        raise ValueError('Acceptance uses a new explicit D: project and evidence directory only')
    if project == source or source in project.parents or project in source.parents:
        raise ValueError('Acceptance project must be separate from the read-only source')
    if project.exists() or evidence.exists():
        raise ValueError('Use new project/evidence directories; historical attempts are preserved')
    if len(str(project)) > 50:
        raise ValueError('This baseline acceptance fixture requires a short new D: project (for example D:/AI-BS-Game-Resources/T27/NR01); deep-root support is a separate acceptance')
    evidence.mkdir(parents=True)
    report = {'status': 'failed', 'scope': 'Actual saved-chapter launch/resume/publication baseline only',
        'route_or_action_durability_verified': False, 'human_pacing_verified': False,
        'likeness_approved': False, 'performance_measured': False,
        'original_family_media_used': False, 'global_input_or_desktop_capture_used': False,
        'project': str(project), 'source_project': str(source), 'checks': [], 'invocations': [],
        'negative_admission': [], 'runtime': {name: {'path': str(path), 'sha256': sha(path)}
            for name, path in (('host', host), ('player', player), ('cooker', cooker))}}
    app = QApplication.instance() or QApplication([])
    view = None
    source_files = {}

    def check(value, message):
        if not value:
            raise AssertionError(message)
        report['checks'].append(message)

    def spin(predicate, message, *, seconds=60, failure=None):
        end = time.monotonic() + seconds
        while not predicate() and time.monotonic() < end:
            app.processEvents()
            if failure is not None and failure():
                raise AssertionError(message + ': ' + view.saved_play_status.text())
            time.sleep(.003)
        check(bool(predicate()), message)

    def idle():
        spin(lambda: view.loaded and not view.busy and not view.client.pending_count,
            'Authoring owner is coherent and idle')

    class SuppliedRuntimeView(ContentView):
        def __init__(self, *args, supplied_player, **kwargs):
            self.supplied_player = supplied_player
            super().__init__(*args, **kwargs)

        def _binary_candidates(self, name):
            # Explicit binary selection only. Both ordinary UI feature checks
            # and the saved client's strict actual capability reader remain.
            if name == 'aibs_motherboard.exe':
                return (self.supplied_player,)
            return super()._binary_candidates(name)

    def invoke(label):
        journal = hash_saved_journal(project)
        previous_session = view.saved_play.session_id
        transitions = []
        def changed(state):
            transitions.append({'state': state, 'elapsed_seconds': time.monotonic() - started})
        view.saved_play.state_changed.connect(changed)
        started = time.monotonic()
        try:
            view.start_saved_play()
            spin(lambda: view.saved_play.state == 'ready', label + ': native READY',
                failure=lambda: (view.saved_play.session_id != previous_session
                    and view.saved_play.state == 'closed' and not view.saved_export.busy))
            client = view.saved_play
            publication = revalidate_publication(client.publication)
            ready = {'player': client.process_id, 'export': view.saved_export.process_id,
                'dependency': client.dependency_process_id, 'owner': view.client.process_id}
            check(ready['player'] > 0 and ready['owner'] > 0 and ready['export'] == ready['dependency'] == 0,
                label + ': second owner/stager joined before running native player')
            check(len(client.snapshot.asset_refs) == 6 and 2 not in client.snapshot.dependency_kinds,
                label + ': current six-pack non-audio closure retained')
            check(hash_saved_journal(project) == journal, label + ': no implicit authoring SAVE during launch')
            root_files = inventory(client.snapshot.asset_store)
            published = inventory(publication.asset_root)
            expected = {name: row for name, row in root_files.items()
                if name.split('/')[0] in {ref.pack_sha256 for ref in client.snapshot.asset_refs}}
            check(published == expected and len(published) == 24, label + ': all six published packs retain exact source bytes')
            session, timeline = client.session_id, publication.timeline_id
            ready_head = tuple(client._ready_head)
            view.stop_saved_play()
            spin(lambda: client.state == 'closed' and client.process_id == client.dependency_process_id == 0,
                label + ': native STOPPED and actual child exit')
            result = dict(client.last_result or {})
            check(result.get('graceful') is True and result.get('saved') is True and result.get('forced') is False,
                label + ': native normal exit proves a verified save drain')
            check(result.get('ready_seen') is True and result.get('play_session') == session
                and result.get('timeline_id') == timeline and result.get('context') == 'player_world'
                and result.get('project_id') == client.snapshot.scope.project
                and result.get('branch_id') == client.snapshot.scope.branch
                and result.get('world_id') == client.snapshot.scope.world_id,
                label + ': exact session/project/branch/world/player timeline receipt')
            check(all(result[key] >= old for key, old in zip(('durable_revision', 'durable_sequence'), ready_head)),
                label + ': durability head does not regress')
            check(publication.database_path.is_file() and publication.database_path.with_name('world.sqlite.initialized').is_file(),
                label + ': retained native database and initialization claim exist')
            check(not any(publication.slot_directory.glob('stop.*.request')),
                label + ': invocation stop marker removed only after native exit')
            check(hash_saved_journal(project) == journal, label + ': authoring journal unchanged after native gameplay drain')
            record = {'label': label, 'session_id': session, 'timeline_id': timeline,
                'fingerprint': client.snapshot.fingerprint, 'checkpoint_id': client.snapshot.checkpoint_id,
                'content_directory': str(publication.content_directory), 'slot_directory': str(publication.slot_directory),
                'database_sha256': sha(publication.database_path), 'reused_slot': publication.reused_slot,
                'reused_publication': publication.reused_publication, 'ready_process_ids': ready,
                'ready_head': ready_head, 'result': result, 'state_transitions': transitions,
                'total_wall_seconds': time.monotonic() - started,
                'stdout_tail': client.stdout_tail.decode('utf-8', 'replace'),
                'stderr_tail': client.stderr_tail.decode('utf-8', 'replace')}
            report['invocations'].append(record)
            return publication, record
        finally:
            view.saved_play.state_changed.disconnect(changed)

    def reject_before_window(label, publication, *, copied_claim=False):
        root = evidence / label
        root.mkdir()
        database = root / 'world.sqlite'
        if copied_claim:
            shutil.copyfile(publication.database_path, database)
            shutil.copyfile(publication.database_path.with_name('world.sqlite.initialized'), root / 'world.sqlite.initialized')
            expected = 'Saved player initialization claim is corrupt or belongs to another immutable content/timeline'
        else:
            database.write_bytes(b'private rejected admission fixture')
            expected = 'Retained player database has no initialization claim; implicit adoption is prohibited'
        before = inventory(root)
        session, timeline = str(uuid.uuid4()), str(uuid.uuid4())
        command = [str(player), '--durable-world', '--persistent-play', '--timeline-id', timeline,
            '--content-definition', str(publication.content_path), '--asset-root', str(publication.asset_root),
            '--database', str(database), '--project', view.definition.project, '--branch', view.definition.branch,
            '--play-session', session, '--stop-file', str(root / ('stop.' + session + '.request'))]
        result = subprocess.run(command, cwd=player.parent, capture_output=True, timeout=45,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (root / 'stdout.log').write_bytes(result.stdout)
        (root / 'stderr.log').write_bytes(result.stderr)
        check(result.returncode != 0 and expected.encode() in result.stderr,
            label + ': explicit native admission rejection before renderer/window construction')
        check(b'aibs.saved_play.ready' not in result.stdout and b'aibs.saved_play.stopped' not in result.stdout,
            label + ': failed admission cannot claim player readiness or a save drain')
        after = inventory(root)
        check(all(after[name] == row for name, row in before.items()), label + ': rejected database/claim bytes unchanged')
        check(not any(root.glob('world.sqlite-*')), label + ': no SQLite WAL/SHM created on rejected admission')
        report['negative_admission'].append({'case': label, 'exit_code': result.returncode,
            'expected_native_error': expected, 'database_sha256': sha(database), 'unchanged_inputs': before,
            'process_joined': True, 'no_window_evidence': 'Exact native error precedes NativeWindow construction in run_chapter; no global window inspection used'})

    try:
        selected = []
        total = 0
        for path in source.rglob('*'):
            checked_path(path)
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            if relative.as_posix() == 'chapter.aiba.lock':
                continue
            allowed = (len(relative.parts) == 1 and relative.name in ROOT_FILES
                or len(relative.parts) == 4 and relative.parts[:2] == ('assets', 'packs'))
            if not allowed:
                raise ValueError('Source acceptance project contains an unexpected member: ' + relative.as_posix())
            total += path.stat().st_size
            if len(selected) == 128 or path.stat().st_size > 32 * 1024 * 1024 or total > LIMIT:
                raise ValueError('Acceptance source copy budget')
            selected.append((relative, path))
            source_files[relative.as_posix()] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
        project.mkdir(parents=True)
        for relative, path in selected:
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            check(sha(target) == source_files[relative.as_posix()]['sha256'], 'Read-only source copied exactly: ' + relative.as_posix())
        view = SuppliedRuntimeView(host, asset_cooker=cooker, supplied_player=player)
        view.open_project(project)
        idle()
        check(not any(row.type_id == 'authoring.MemoryBinding' for row in view.rows), 'No original-memory audio binding admitted in this baseline')
        if args.old_player is not None:
            previous = view.supplied_player
            view.supplied_player = checked_path(args.old_player, directory=False)
            rejected = False
            try:
                view.start_saved_play()
            except ValueError:
                rejected = True
            finally:
                view.supplied_player = previous
            check(rejected and not view.saved_export.busy and view.saved_play.process_id == 0
                and not (project / '.aibs-runtime').exists(), 'Actual old player capability rejection precedes export/publication/process launch')
        first, one = invoke('first saved chapter')
        second, two = invoke('resume same saved chapter')
        check(one['session_id'] != two['session_id'] and one['timeline_id'] == two['timeline_id']
            and first.database_path == second.database_path and two['reused_slot'], 'Resume uses new invocation and identical retained player timeline/database')
        fingerprint = view.description.fingerprint
        view.save_world()
        idle()
        check(view.description.fingerprint == fingerprint, 'Unchanged explicit authoring Save keeps gameplay content fingerprint')
        third, three = invoke('unchanged authoring Save')
        check(three['timeline_id'] == one['timeline_id'] and three['reused_slot'], 'Unchanged Save reuses existing slot/timeline')
        old_slot, old_content = inventory(first.slot_directory), inventory(first.content_directory)
        reject_before_window('reject-unclaimed-database', first)
        reject_before_window('reject-foreign-timeline', first, copied_claim=True)
        check(inventory(first.slot_directory) == old_slot, 'Negative admission fixtures do not touch the real retained slot')
        view.add_fixture('Saved Play branch marker')
        idle()
        check(view.client.dirty and view.description.dirty and not view.saved_play_button.isEnabled(), 'Unsaved authoring edit disables saved Play')
        rejected = False
        try:
            view.start_saved_play()
        except ValueError:
            rejected = True
        check(rejected and view.saved_play.state == 'closed' and not view.saved_export.busy, 'Unsaved edit cannot launch or implicitly save gameplay')
        view.save_world()
        idle()
        check(view.description.fingerprint != fingerprint, 'Actual saved authoring edit produces new content identity')
        fourth, four = invoke('new saved authored content')
        check(four['timeline_id'] != one['timeline_id'] and fourth.database_path != first.database_path
            and not four['reused_slot'], 'Changed saved content receives a distinct new player slot/timeline')
        check(inventory(first.slot_directory) == old_slot and inventory(first.content_directory) == old_content,
            'New branch preserves every old database/claim/slot/publication byte')
        report['source_files'] = source_files
        check(all(sha(source / name) == row['sha256'] for name, row in source_files.items()), 'All selected original project files remain unchanged')
        report['status'] = 'passed'
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        report['source_files'] = source_files
        report['selected_originals_unchanged'] = all(sha(source / name) == row['sha256']
            for name, row in source_files.items())
        report['all_owned_processes_joined'] = view is None
        if view is not None:
            view.saved_export.stop()
            view.saved_play.stop()
            view.play.stop()
            view.viewport.stop()
            view.asset_client.stop()
            end = time.monotonic() + 18
            while not view._children_closed() and time.monotonic() < end:
                app.processEvents()
                time.sleep(.003)
            if not view._children_closed():
                view.saved_play.shutdown()
                view.play._shutdown()
                view.viewport._shutdown()
                view.asset_client.shutdown()
            view.client.stop()
            end = time.monotonic() + 5
            while (view.client.process_id or view.saved_export.process_id) and time.monotonic() < end:
                app.processEvents()
                time.sleep(.003)
            ids = {'owner': view.client.process_id, 'saved_export': view.saved_export.process_id,
                'saved_player': view.saved_play.process_id, 'saved_dependency': view.saved_play.dependency_process_id,
                'isolated_play': view.play.process_id, 'preview': view.viewport.process_id, 'project_asset': view.asset_client.process_id}
            report['final_process_ids'] = ids
            report['all_owned_processes_joined'] = not any(ids.values())
            if any(ids.values()):
                report['status'] = 'failed'
                report['cleanup_error'] = 'An owned child remains unjoined; no fixture or retained data was deleted'
            else:
                view.definition = None
                view.deleteLater()
                app.processEvents()
        for name in ('host', 'player', 'cooker'):
            report['runtime'][name]['unchanged'] = sha(Path(report['runtime'][name]['path'])) == report['runtime'][name]['sha256']
        if (not report['selected_originals_unchanged'] or
                any(not runtime['unchanged'] for runtime in report['runtime'].values())):
            report['status'] = 'failed'
            report['freshness_error'] = 'A protected source or supplied runtime changed during acceptance'
        (evidence / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'checks': len(report['checks']),
        'invocations': len(report['invocations']), 'report': str(evidence / 'verification.json')}))


if __name__ == '__main__':
    main()
