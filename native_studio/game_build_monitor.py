"""Read-only custom-engine build telemetry; independent of Qt/backend services."""
from __future__ import annotations

from datetime import datetime, timezone
import codecs
import json
import os
from pathlib import Path
import re
import shutil


def read_native_player_capabilities(executable: Path) -> dict:
    """Read a bounded adjacent declaration; never execute or select a binary."""
    executable = Path(executable)
    descriptor = executable.with_name('aibs_capabilities.json')
    unavailable = {'status': 'not_found', 'chapter_capable': False}
    if not executable.is_file() or not descriptor.is_file():
        return unavailable
    try:
        with descriptor.open('rb') as stream:
            encoded = stream.read(16 * 1024 + 1)
        if len(encoded) > 16 * 1024:
            raise ValueError('Native player capability declaration exceeds 16 KiB')
        data = json.loads(encoded.decode('utf-8-sig'))
        if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
            raise ValueError('Unsupported native player capability schema')
        version = data.get('sdk_version')
        if not isinstance(version, str) or len(version) > 32 or not re.fullmatch(
                r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
            raise ValueError('Invalid native player SDK version')
        features = data.get('features')
        if not isinstance(features, dict) or any(
                not isinstance(key, str) or not key or len(key) > 128 or type(value) is not bool
                for key, value in features.items()):
            raise ValueError('Invalid native player capability flags')
        supported_version = tuple(int(part) for part in version.split('.')) >= (0, 8, 0)
        return {'status': 'available', 'sdk_version': version, 'features': features,
                'chapter_capable': supported_version and features.get('first_boot_chapter') is True,
                'descriptor_path': str(descriptor)}
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        return {'status': 'unreadable', 'chapter_capable': False, 'error': str(exc)}


def _directory_metrics(directory: Path, inventory_suffix: str | None = None) -> tuple[dict, list]:
    """Bound work per poll and avoid following links outside generated output."""
    metrics = {'bytes': 0, 'file_count': 0, 'partial': False}
    inventory = []
    pending = [directory]
    inspected = 0
    while pending:
        current = pending.pop()
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            metrics['partial'] = True
            continue
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    inspected += 1
                    if inspected > 10000:
                        metrics['partial'] = True
                        return metrics, inventory
                    try:
                        path = Path(entry.path)
                        if entry.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                            metrics['partial'] = True
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(path)
                        elif entry.is_file(follow_symlinks=False):
                            stat = entry.stat(follow_symlinks=False)
                            metrics['bytes'] += stat.st_size
                            metrics['file_count'] += 1
                            if inventory_suffix and path.suffix == inventory_suffix:
                                inventory.append({'path': path, 'bytes': stat.st_size, 'modified_at': stat.st_mtime})
                    except OSError:
                        metrics['partial'] = True
        except FileNotFoundError:
            continue
        except OSError:
            metrics['partial'] = True
    return metrics, inventory


def _read_checkpoint_verification(path: Path) -> dict:
    if not path.exists():
        return {'status': 'not_run', 'checks': []}
    try:
        if path.stat().st_size > 1024 * 1024:
            raise ValueError('Checkpoint verification report exceeds 1 MiB')
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('schema_version') != 1:
            raise ValueError('Unsupported checkpoint verification schema')
        if data.get('status') not in {'passed', 'failed'}:
            raise ValueError('Invalid checkpoint verification status')
        checks = data.get('checks')
        if not isinstance(checks, list) or not checks or not all(isinstance(check, str) and check.strip() for check in checks):
            raise ValueError('Checkpoint verification requires named checks')
        completed = datetime.fromisoformat(data['completed_at'])
        if completed.utcoffset() is None:
            raise ValueError('Checkpoint verification timestamp requires a timezone')
        return {key: data[key] for key in ('status', 'checks', 'completed_at')}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return {'status': 'unreadable', 'checks': [], 'error': str(exc)}


def _read_bounded_json(path: Path, maximum_bytes: int = 1024 * 1024):
    """Bound the actual read and reject ambiguous duplicate/nonfinite JSON."""
    with path.open('rb') as stream:
        encoded = stream.read(maximum_bytes + 1)
    if len(encoded) > maximum_bytes:
        raise ValueError('Verification report exceeds 1 MiB')
    def invalid_constant(value):
        raise ValueError('Nonfinite verification number')
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate verification JSON field')
            result[key] = value
        return result
    return json.loads(encoded.decode('utf-8-sig'), parse_constant=invalid_constant,
                      object_pairs_hook=unique_pairs)


def _read_warm_beginning_summary(path: Path) -> dict:
    """A dedicated recorded summary never infers full-goal completion."""
    missing = {'status': 'not_run', 'goal_complete': False}
    if not path.exists():
        return missing
    try:
        data = _read_bounded_json(path)
        expected = {'schema_version', 'updated_at', 'goal_complete', 'native_source',
                    'packaged_candidate', 'deployed', 'remaining', 'next_step'}
        if type(data) is not dict or set(data) != expected or type(data['schema_version']) is not int or data['schema_version'] != 1:
            raise ValueError('Unsupported Warm Beginning summary schema')
        if type(data['goal_complete']) is not bool:
            raise ValueError('Warm Beginning goal completion must be explicit boolean')
        def text(value, maximum):
            if (type(value) is not str or not value.strip() or '\0' in value or
                    len(value.encode('utf-8')) > maximum or
                    any(ord(c) < 32 and c not in '\t\r\n' for c in value)):
                raise ValueError('Invalid bounded Warm Beginning summary text')
        text(data['updated_at'],128)
        completed = datetime.fromisoformat(data['updated_at'])
        if completed.utcoffset() is None:
            raise ValueError('Warm Beginning timestamp needs timezone')
        for key, version_field in (('native_source','sdk_version'),
                                   ('packaged_candidate','studio_version'),('deployed','studio_version')):
            entry = data[key]
            if type(entry) is not dict or set(entry) != {version_field,'status','summary','evidence_paths'}:
                raise ValueError('Invalid Warm Beginning evidence entry')
            version = entry[version_field]
            if type(version) is not str or len(version) > 32 or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)',version):
                raise ValueError('Invalid Warm Beginning evidence version')
            if type(entry['status']) is not str or entry['status'] not in {'passed','failed','not_run','in_progress','stale'}:
                raise ValueError('Unknown Warm Beginning evidence status')
            text(entry['summary'],4096)
            paths = entry['evidence_paths']
            if type(paths) is not list or len(paths) > 32 or (entry['status'] == 'passed' and not paths):
                raise ValueError('Warm Beginning pass needs bounded evidence paths')
            for item in paths:
                text(item,4096)
        remaining = data['remaining']
        if type(remaining) is not list or not 4 <= len(remaining) <= 32:
            raise ValueError('Warm Beginning remaining-work list is incomplete or exceeds bound')
        ids = set()
        for item in remaining:
            if type(item) is not dict or set(item) != {'id','title','status','detail'}:
                raise ValueError('Invalid Warm Beginning remaining-work entry')
            identity = item['id']
            if type(identity) is not str or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}',identity) or identity in ids:
                raise ValueError('Invalid/duplicate Warm Beginning remaining-work identity')
            ids.add(identity)
            if type(item['status']) is not str or item['status'] not in {'pending','in_progress','needs_review','completed','blocked'}:
                raise ValueError('Unknown Warm Beginning remaining-work status')
            text(item['title'],256);text(item['detail'],2048)
        if not {'likeness','checked_captions','human_pacing','final_package'} <= ids:
            raise ValueError('Warm Beginning summary omits required human/final acceptance work')
        text(data['next_step'],4096)
        if data['goal_complete'] and (any(data[k]['status'] != 'passed' for k in
                ('native_source','packaged_candidate','deployed')) or any(item['status'] != 'completed' for item in remaining)):
            raise ValueError('Warm Beginning explicit completion contradicts evidence/remaining work')
        return {**data, 'status': 'available', 'source_path': str(path)}
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RecursionError) as exc:
        return {'status':'unreadable','goal_complete':False,'error':str(exc)}


def _read_log_tail(path: Path, maximum_bytes: int = 32768) -> str:
    """Read one bounded tail; avoid split UTF8/code units and live partial writes."""
    with path.open('rb') as stream:
        signature = stream.read(4)
        if signature.startswith((b'\xff\xfe\x00\x00',b'\x00\x00\xfe\xff')):
            return 'Unsupported verification log encoding (UTF32).'
        if signature.startswith(b'\xff\xfe'):
            encoding, bom = 'utf-16-le', 2
        elif signature.startswith(b'\xfe\xff'):
            encoding, bom = 'utf-16-be', 2
        else:
            encoding, bom = 'utf-8', 3 if signature.startswith(b'\xef\xbb\xbf') else 0
        stream.seek(0,2);end = stream.tell()
        start = max(bom,end-maximum_bytes)
        if encoding.startswith('utf-16') and (start-bom) % 2:
            start += 1
        stream.seek(start);encoded = stream.read(min(maximum_bytes,max(0,end-start)))
    if start > bom:
        if encoding.startswith('utf-16') and len(encoded) >= 2:
            first = int.from_bytes(encoded[:2],'little' if encoding.endswith('le') else 'big')
            if 0xdc00 <= first <= 0xdfff:
                encoded = encoded[2:]
        elif encoding == 'utf-8':
            skipped = 0
            while skipped < min(3,len(encoded)) and encoded[skipped] & 0xc0 == 0x80:
                skipped += 1
            encoded = encoded[skipped:]
    return codecs.getincrementaldecoder(encoding)(errors='replace').decode(encoded,final=False)


def _read_milestone_verification(path: Path, timestamp_key: str = 'completed_at',
                                 extra_fields: tuple[str, ...] = ()) -> dict:
    if not path.exists():
        return {'status': 'not_run', 'checks': []}
    try:
        data = _read_bounded_json(path)
        if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
            raise ValueError('Unsupported verification schema')
        if data.get('status') not in {'passed', 'failed'}:
            raise ValueError('Invalid verification status')
        checks = data.get('checks')
        if (not isinstance(checks, list) or not 1 <= len(checks) <= 256 or
                not all(isinstance(check, str) and check.strip() and len(check) <= 8192 for check in checks)):
            raise ValueError('Verification requires named checks')
        if not isinstance(data.get(timestamp_key), str) or len(data[timestamp_key]) > 128:
            raise ValueError('Invalid verification timestamp')
        completed = datetime.fromisoformat(data[timestamp_key])
        if completed.utcoffset() is None:
            raise ValueError('Verification timestamp requires a timezone')
        if 'origin' in data and (not isinstance(data['origin'], str) or not data['origin'].strip() or len(data['origin']) > 8192):
            raise ValueError('Verification origin requires descriptive text')
        if 'metrics' in extra_fields and 'metrics' in data and not isinstance(data['metrics'], dict):
            raise ValueError('Verification metrics require an object')
        allowed = ('status', 'checks', timestamp_key, 'origin', 'version', 'adapter', 'adapter_name',
                   'adapter_description', 'software', 'warp', 'frames', 'resize_count', 'configuration') + extra_fields
        return {key: data[key] for key in allowed if key in data}
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        return {'status': 'unreadable', 'checks': [], 'error': str(exc)}


def _read_persistent_placement_verification(path: Path) -> dict:
    data=_read_milestone_verification(path,'verified_at',extra_fields=(
        'schema_version','sdk_version','studio_version','limitations','proof_paths','metrics','next_step','drive_checkpoint'))
    if data['status'] not in {'passed','failed'}:return data
    try:
        for field in ('sdk_version','studio_version'):
            value=data.get(field)
            if type(value) is not str or len(value)>32 or not re.fullmatch(r'\d+\.\d+\.\d+',value):
                raise ValueError('Invalid persistent placement '+field)
        for field in ('limitations','proof_paths'):
            values=data.get(field)
            if (type(values) is not list or not 1<=len(values)<=64
                    or any(type(value) is not str or not value.strip() or '\0' in value or len(value)>8192 for value in values)):
                raise ValueError('Invalid persistent placement '+field)
        if 'next_step' in data and (type(data['next_step']) is not str or len(data['next_step'])>8192):
            raise ValueError('Invalid persistent placement next step')
        if 'drive_checkpoint' in data and type(data['drive_checkpoint']) not in (str,dict):
            raise ValueError('Invalid persistent placement drive checkpoint')
        return data
    except (ValueError,TypeError) as error:
        return {'status':'unreadable','checks':[],'error':str(error)}


def _read_world_scene_verification(path: Path) -> dict:
    data = _read_milestone_verification(path, extra_fields=(
        'world_id', 'checkpoint_id', 'revision', 'restored_revision', 'entity_count',
        'object_count', 'memory_events', 'entity_ids', 'stable_ids', 'metrics'))
    if data['status'] not in {'passed', 'failed'}:
        return data
    try:
        for field in ('world_id', 'checkpoint_id'):
            if field in data and (not isinstance(data[field], str) or not data[field].strip()):
                raise ValueError(f'Invalid world-scene {field}')
        for field in ('revision', 'restored_revision', 'entity_count', 'object_count', 'memory_events'):
            if field in data and (type(data[field]) is not int or data[field] < 0):
                raise ValueError(f'Invalid world-scene {field}')
        if 'entity_ids' in data and (not isinstance(data['entity_ids'], list) or
                                    not all(isinstance(item, str) and item for item in data['entity_ids'])):
            raise ValueError('Invalid world-scene entity IDs')
        if 'stable_ids' in data:
            ids = data['stable_ids']
            if isinstance(ids, dict):
                valid = all(isinstance(key, str) and key and isinstance(value, str) and value
                            for key, value in ids.items())
            else:
                valid = isinstance(ids, list) and all(isinstance(item, str) and item for item in ids)
            if not valid:
                raise ValueError('Invalid world-scene stable IDs')
        if 'metrics' in data and not isinstance(data['metrics'], dict):
            raise ValueError('Invalid world-scene metrics')
        return data
    except (ValueError, TypeError) as exc:
        return {'status': 'unreadable', 'checks': [], 'error': str(exc)}


def _read_movement_verification(path: Path) -> dict:
    data = _read_milestone_verification(path, extra_fields=(
        'engine', 'engine_version', 'fixed_hz', 'metrics'))
    if data['status'] not in {'passed', 'failed'}:
        return data
    try:
        for field in ('engine', 'engine_version'):
            if field in data and (not isinstance(data[field], str) or not data[field].strip()):
                raise ValueError(f'Invalid movement {field}')
        if 'fixed_hz' in data and (type(data['fixed_hz']) is not int or not 1 <= data['fixed_hz'] <= 1000):
            raise ValueError('Invalid movement fixed tick rate')
        if 'metrics' in data and not isinstance(data['metrics'], dict):
            raise ValueError('Invalid movement metrics')
        return data
    except (ValueError, TypeError) as exc:
        return {'status': 'unreadable', 'checks': [], 'error': str(exc)}


def _read_obstacle_course_verification(path: Path) -> dict:
    data = _read_milestone_verification(path, extra_fields=('world_id', 'checkpoint_id', 'metrics'))
    if data['status'] not in {'passed', 'failed'}:
        return data
    try:
        for field in ('world_id', 'checkpoint_id'):
            if field in data and (not isinstance(data[field], str) or not data[field].strip()):
                raise ValueError(f'Invalid obstacle-course {field}')
        metrics = data.get('metrics')
        if metrics is not None and not isinstance(metrics, dict):
            raise ValueError('Invalid obstacle-course metrics')
        coverage = ('steps', 'slopes', 'walls', 'falls', 'focus', 'restart', 'interaction')
        if data['status'] == 'passed' and (not isinstance(metrics, dict) or
                                          any(metrics.get(check) is not True for check in coverage)):
            raise ValueError('Obstacle-course pass requires all seven traversal and continuity checks')
        if isinstance(metrics, dict):
            for check in coverage:
                if check in metrics and type(metrics[check]) is not bool:
                    raise ValueError(f'Invalid obstacle-course {check} result')
            if 'debug_errors' in metrics:
                errors = metrics['debug_errors']
                if type(errors) is not int or errors < 0 or (data['status'] == 'passed' and errors != 0):
                    raise ValueError('Obstacle-course GPU errors contradict verification status')
        return data
    except (ValueError, TypeError) as exc:
        return {'status': 'unreadable', 'checks': [], 'error': str(exc)}


def _read_gameplay_store_verification(path: Path) -> dict:
    data = _read_milestone_verification(path, extra_fields=('world_id', 'revision', 'metrics'))
    if data['status'] not in {'passed', 'failed'}:
        return data
    try:
        if 'world_id' in data and (not isinstance(data['world_id'], str) or not data['world_id'].strip()):
            raise ValueError('Invalid gameplay-store world identity')
        if 'revision' in data and (type(data['revision']) is not int or not 0 <= data['revision'] < 2**64):
            raise ValueError('Invalid gameplay-store revision')
        metrics = data.get('metrics')
        if metrics is not None and not isinstance(metrics, dict):
            raise ValueError('Invalid gameplay-store metrics')
        coverage = ('process_recovery', 'atomic_components_events', 'exact_retry', 'stale_writer', 'scope_isolation')
        if data['status'] == 'passed' and (not isinstance(metrics, dict) or
                                          any(metrics.get(check) is not True for check in coverage)):
            raise ValueError('Gameplay-store pass requires recovery, atomic commit, retry, stale-writer and scope checks')
        if isinstance(metrics, dict):
            for check in coverage:
                if check in metrics and type(metrics[check]) is not bool:
                    raise ValueError(f'Invalid gameplay-store {check} result')
            if 'durable_events' in metrics and (type(metrics['durable_events']) is not int or metrics['durable_events'] < 0):
                raise ValueError('Invalid gameplay-store durable event count')
        return data
    except (ValueError, TypeError) as exc:
        return {'status': 'unreadable', 'checks': [], 'error': str(exc)}


def _read_registry_migration_verification(path: Path) -> dict:
    data = _read_milestone_verification(path, extra_fields=(
        'schema_version', 'scope', 'revision', 'original_checkpoint_id', 'metrics', 'error', 'work_directory'))
    if data['status'] not in {'passed', 'failed'}:
        return data
    try:
        if type(data.get('schema_version')) is not int or data['schema_version'] != 1:
            raise ValueError('Unsupported registry-migration verification schema')
        if 'scope' in data:
            scope = data['scope']
            if not isinstance(scope, dict) or any(
                    not isinstance(scope.get(key), str) or not scope[key].strip()
                    for key in ('project_id', 'world_id', 'branch_id', 'timeline_id', 'context')):
                raise ValueError('Invalid registry-migration scope')
            if scope['context'] != 'player_world':
                raise ValueError('Registry-migration proof requires player-world context')
        if 'revision' in data and (type(data['revision']) is not int or not 0 <= data['revision'] < 2**64):
            raise ValueError('Invalid registry-migration revision')
        for field in ('original_checkpoint_id', 'work_directory', 'error'):
            if field in data and not isinstance(data[field], str):
                raise ValueError(f'Invalid registry-migration {field}')
        if 'original_checkpoint_id' in data and not data['original_checkpoint_id'].strip():
            raise ValueError('Invalid registry-migration original checkpoint identity')
        if data['status'] == 'passed' and data.get('error'):
            raise ValueError('Registry-migration error contradicts passed status')
        metrics = data.get('metrics')
        if 'metrics' in data and not isinstance(metrics, dict):
            raise ValueError('Invalid registry-migration metrics')
        coverage = ('before_commit_recovery', 'after_commit_recovery', 'atomic_registry_receipts',
                    'preserved_m2_evidence', 'exact_migration_retry', 'conflicting_migration_rejected',
                    'stale_registry_connection')
        if data['status'] == 'passed' and (not isinstance(metrics, dict) or
                                          any(metrics.get(check) is not True for check in coverage)):
            raise ValueError('Registry-migration pass requires all seven registry and evidence continuity checks')
        if isinstance(metrics, dict):
            for check in coverage + ('old_studio92_rejected',):
                if check in metrics and type(metrics[check]) is not bool:
                    raise ValueError(f'Invalid registry-migration {check} result')
            if 'processes' in metrics and (type(metrics['processes']) is not int or metrics['processes'] < 0 or
                                          (data['status'] == 'passed' and metrics['processes'] == 0)):
                raise ValueError('Invalid registry-migration process count')
        data['source_path'] = str(path)
        return data
    except (ValueError, TypeError) as exc:
        return {'status': 'unreadable', 'checks': [], 'error': str(exc)}


def _read_durable_world_verification(path: Path) -> dict:
    data = _read_milestone_verification(path, extra_fields=(
        'schema_version', 'scope', 'revision', 'durable_events', 'metrics', 'error', 'work_directory'))
    if data['status'] not in {'passed', 'failed'}:
        return data
    try:
        if type(data.get('schema_version')) is not int or data['schema_version'] != 1:
            raise ValueError('Unsupported native durable-world verification schema')
        if 'scope' in data:
            scope = data['scope']
            if not isinstance(scope, dict) or any(
                    not isinstance(scope.get(key), str) or not scope[key].strip()
                    for key in ('project_id', 'world_id', 'branch_id', 'timeline_id', 'context')):
                raise ValueError('Invalid native durable-world scope')
            if scope['context'] != 'player_world':
                raise ValueError('Native durable-world proof requires player-world context')
        for field in ('revision', 'durable_events'):
            if field in data and (type(data[field]) is not int or not 0 <= data[field] < 2**64):
                raise ValueError(f'Invalid native durable-world {field}')
        for field in ('error', 'work_directory'):
            if field in data and not isinstance(data[field], str):
                raise ValueError(f'Invalid native durable-world {field}')
        if data['status'] == 'passed' and data.get('error'):
            raise ValueError('Native durable-world error contradicts passed status')
        metrics = data.get('metrics')
        if 'metrics' in data and not isinstance(metrics, dict):
            raise ValueError('Invalid native durable-world metrics')
        coverage = ('native_gpu', 'repair_build_dismantle', 'restart_pixels_identical', 'stable_uuids',
                    'semantic_event_equality', 'tombstone_persistence', 'before_commit_recovery',
                    'after_commit_recovery', 'exact_retry', 'live_retry', 'close_drained',
                    'import_preserves_original')
        if data['status'] == 'passed' and (not isinstance(metrics, dict) or
                                          any(metrics.get(check) is not True for check in coverage)):
            raise ValueError('Native durable-world pass requires all twelve GPU, gameplay and recovery checks')
        if isinstance(metrics, dict):
            for check in coverage + ('debug_layer',):
                if check in metrics and type(metrics[check]) is not bool:
                    raise ValueError(f'Invalid native durable-world {check} result')
            errors = metrics.get('debug_errors')
            if 'debug_errors' in metrics and (type(errors) is not int or errors < 0):
                raise ValueError('Invalid native durable-world GPU error count')
            if data['status'] == 'passed' and (type(errors) is not int or errors != 0):
                raise ValueError('Native durable-world pass requires zero recorded GPU errors')
            if 'processes' in metrics and (type(metrics['processes']) is not int or metrics['processes'] < 0 or
                                          (data['status'] == 'passed' and metrics['processes'] == 0)):
                raise ValueError('Invalid native durable-world process count')
        return data
    except (ValueError, TypeError) as exc:
        return {'status': 'unreadable', 'checks': [], 'error': str(exc)}


def _read_first_boot_chapter_verification(path: Path) -> dict:
    data = _read_milestone_verification(path, extra_fields=(
        'schema_version', 'executablePath', 'executableSha256', 'work_directory', 'metrics', 'error'))
    if data['status'] not in {'passed', 'failed'}:
        return data
    try:
        if type(data.get('schema_version')) is not int or data['schema_version'] != 1:
            raise ValueError('Unsupported native First Boot chapter verification schema')
        for field in ('executablePath', 'executableSha256', 'work_directory'):
            if field in data or data['status'] == 'passed':
                if not isinstance(data.get(field), str) or not data[field].strip() or '\0' in data[field]:
                    raise ValueError(f'Invalid native chapter {field}')
        if 'executableSha256' in data and not re.fullmatch(r'[0-9a-fA-F]{64}', data['executableSha256']):
            raise ValueError('Invalid native chapter executable SHA-256')
        if 'error' in data and not isinstance(data['error'], str):
            raise ValueError('Invalid native chapter error')
        if data['status'] == 'passed' and data.get('error'):
            raise ValueError('Native chapter error contradicts passed status')
        metrics = data.get('metrics')
        if 'metrics' in data and not isinstance(metrics, dict):
            raise ValueError('Invalid native chapter metrics')
        coverage = ('native_gpu', 'actual_player_pov', 'actual_hud_fits', 'repair_route', 'bypass_route',
                    'occupied_door_close', 'optional_help', 'optional_decline', 'depart_return',
                    'feed_build_dismantle', 'latched_unpowered_return', 'restart_pixels_identity',
                    'actual_f9_reload', 'hazard_pause', 'hazard_recovery', 'critical_backpressure',
                    'recovery_consumes_old_input', 'stale_activation_rejected', 'empty_socket_survives',
                    'remote_node_reach', 'translated_board_supported', 'reload_failure_retains_live',
                    'live_f5_held_contact', 'close_drains_held_contact', 'explicit_m2_upgrade',
                    'm2_history_preserved', 'original_import_preserved')
        if data['status'] == 'passed' and (not isinstance(metrics, dict) or
                                          any(metrics.get(check) is not True for check in coverage)):
            raise ValueError('Native chapter pass requires all twenty-seven chapter and continuity checks')
        if isinstance(metrics, dict):
            for check in coverage + ('debug_layer',):
                if check in metrics and type(metrics[check]) is not bool:
                    raise ValueError(f'Invalid native chapter {check} result')
            for field in ('processes', 'debug_errors'):
                if field in metrics and (type(metrics[field]) is not int or metrics[field] < 0):
                    raise ValueError(f'Invalid native chapter {field}')
            if data['status'] == 'passed':
                if type(metrics.get('processes')) is not int or metrics['processes'] < 36:
                    raise ValueError('Native chapter pass requires at least thirty-six recorded processes')
                if type(metrics.get('debug_errors')) is not int or metrics['debug_errors'] != 0:
                    raise ValueError('Native chapter pass requires zero recorded GPU errors')
                if type(metrics.get('debug_layer')) is not bool:
                    raise ValueError('Native chapter proof must record its actual debug-layer observation')
        data['source_path'] = str(path)
        return data
    except (ValueError, TypeError) as exc:
        return {'status': 'unreadable', 'checks': [], 'error': str(exc)}


def _read_milestone_queue(path: Path) -> dict:
    """Read declared plans; loading a plan never certifies its runtime gates."""
    if not path.exists():
        return {'status': 'not_found', 'milestones': [], 'next_slices': []}
    try:
        if path.stat().st_size > 1024 * 1024:
            raise ValueError('Milestone queue exceeds 1 MiB')
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or data.get('schema_version') != 1:
            raise ValueError('Unsupported milestone queue schema')
        if datetime.fromisoformat(data['updated_at']).utcoffset() is None:
            raise ValueError('Milestone queue timestamp requires a timezone')
        milestones, slices = data['milestones'], data['next_slices']
        if not isinstance(milestones, list) or not 1 <= len(milestones) <= 64:
            raise ValueError('Invalid milestone list')
        if not isinstance(slices, list) or len(slices) > 3:
            raise ValueError('Invalid next-three slice list')
        identifiers = set()
        states = {'complete', 'in_progress', 'planned'}
        for item in milestones:
            if not isinstance(item, dict) or any(not isinstance(item.get(key), str) or not item[key].strip()
                                                 for key in ('id', 'title', 'status')):
                raise ValueError('Invalid milestone record')
            if item['id'] in identifiers or item['status'] not in states:
                raise ValueError('Duplicate milestone or invalid declared status')
            identifiers.add(item['id'])
            gates = item.get('gates', [])
            if not isinstance(gates, list) or len(gates) > 128:
                raise ValueError('Invalid milestone gates')
            for gate in gates:
                if (not isinstance(gate, dict) or gate.get('status') not in {'PROPOSED', 'UNVERIFIED', 'VERIFIED', 'FAILED'}
                        or not isinstance(gate.get('id'), str) or not gate['id'].strip()
                        or not isinstance(gate.get('description'), str) or not gate['description'].strip()):
                    raise ValueError('Invalid milestone gate')
                evidence = gate.get('evidence', [])
                if not isinstance(evidence, list) or not all(isinstance(p, str) and p.strip() for p in evidence):
                    raise ValueError('Invalid gate evidence paths')
        if data['current_milestone'] not in identifiers:
            raise ValueError('Current milestone does not exist')
        slice_ids = set()
        for item in slices:
            if (not isinstance(item, dict) or any(not isinstance(item.get(key), str) or not item[key].strip()
                                                  for key in ('id', 'title', 'milestone', 'status'))
                    or item['id'] in slice_ids or item['status'] not in states or item['milestone'] not in identifiers):
                raise ValueError('Invalid next slice or milestone dependency')
            slice_ids.add(item['id'])
        return {'status': 'loaded', **{key: data[key] for key in (
            'schema_version', 'updated_at', 'current_milestone', 'milestones', 'next_slices')}}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return {'status': 'unreadable', 'milestones': [], 'next_slices': [], 'error': str(exc)}


def _input_kind(relative: str) -> str:
    """Only positively identified documentation is exempt from build staleness."""
    name = relative.casefold()
    suffix = Path(name).suffix
    if name.startswith('engine/assets/'):
        return 'runtime_content'
    if name == 'engine/milestone_queue.json':
        return 'documentation'
    if name.startswith(('docs/game_engine/checkpoints/', 'docs/game_engine/concept_art/')):
        return 'documentation'
    if suffix in {'.md', '.rst', '.pdf', '.docx'}:
        return 'documentation'
    if name.startswith('docs/game_engine/') and (
            suffix == '.txt' or name in {'docs/game_engine/sdk_registry.json',
                'docs/game_engine/resource_catalog.json', 'docs/game_engine/planning_decisions.json',
                'docs/game_engine/drive_destination.json', 'docs/game_engine/component_contracts.json',
                'docs/game_engine/adam_first_boot_contracts.json'}):
        return 'documentation'
    if suffix in {'.c', '.cc', '.cpp', '.h', '.hpp', '.inl', '.hlsl', '.hlsli',
                  '.cmake', '.ps1', '.py', '.in', '.html', '.js', '.css'} or name.endswith('/cmakelists.txt'):
        return 'runtime_code'
    if suffix in {'.png', '.jpg', '.jpeg', '.obj', '.glb', '.gltf', '.wav', '.aibmat', '.aibmesh', '.aibsurf'}:
        return 'runtime_content'
    return 'unknown_input'


def _input_inventory(root: Path) -> tuple[list, bool]:
    """Bound metadata work, include unknown inputs and never traverse redirections."""
    records, pending, partial = [], [], False
    directories = ('engine/include', 'engine/src', 'engine/apps', 'engine/games', 'engine/tests',
        'engine/scripts', 'engine/cmake', 'engine/examples', 'engine/shaders', 'engine/assets',
        'engine/tools', 'engine/third_party', 'docs/game_engine', 'native_studio/game_engine')
    for relative in directories:
        path = root / relative
        if path.exists():
            pending.append((path, True))
    for relative in ('native_studio/game_build_monitor.py', 'native_studio/game_build_view.py'):
        path = root / relative
        if path.exists():
            pending.append((path, False))
    # Engine root contains build declarations and the separately reported docs.
    engine = root / 'engine'
    if engine.exists():
        try:
            with os.scandir(engine) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        pending.append((Path(entry.path), False))
        except OSError:
            partial = True
    inspected = 0
    while pending:
        path, directory = pending.pop()
        inspected += 1
        if inspected > 10000:
            partial = True
            break
        try:
            if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                partial = True
                continue
            if directory:
                with os.scandir(path) as entries:
                    for entry in entries:
                        if entry.name in {'__pycache__', '.pytest_cache', '.git'}:
                            continue
                        if len(pending) + inspected >= 10000:
                            partial = True
                            break
                        pending.append((Path(entry.path), entry.is_dir(follow_symlinks=False)))
            else:
                relative = path.relative_to(root).as_posix()
                records.append({'path': relative, 'modified_at': path.stat().st_mtime,
                                'kind': _input_kind(relative)})
        except OSError:
            partial = True
    records.sort(key=lambda item: (-item['modified_at'], item['path']))
    return records, partial


def read_build_progress(root: Path) -> dict:
    root = Path(root)
    report = root / 'engine/out/build_progress.json'
    result = {'status': 'not_run', 'events': [], 'configurations': {}, 'recent_files': [],
              'source_changed_since_build': False, 'drives': [], 'log': ''}
    if report.exists():
        try:
            if report.stat().st_size > 1024 * 1024:
                raise ValueError('Progress report exceeds 1 MiB')
            data = json.loads(report.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or data.get('schema_version') != 1:
                raise ValueError('Unsupported progress report schema')
            if data.get('status') not in {'running', 'passed', 'failed'}:
                raise ValueError('Invalid build status')
            if not isinstance(data.get('events', []), list) or not isinstance(data.get('configurations', {}), dict):
                raise ValueError('Invalid event/configuration records')
            result.update(data)
        except (OSError, ValueError, TypeError) as exc:
            result.update(status='unreadable', error=str(exc))
    records, partial = _input_inventory(root)
    runtime = [record for record in records if record['kind'] != 'documentation']
    documentation = [record for record in records if record['kind'] == 'documentation']
    result['recent_files'] = records[:20]
    result['tracked_file_count'] = len(records)
    result['recent_runtime_files'] = runtime[:20]
    result['recent_documentation_files'] = documentation[:20]
    result['source_inventory_partial'] = partial
    result['documentation_changed_since_build'] = False
    method = 'Modification-time inventory; deletions and backdated edits require source-manifest verification'
    result['source_freshness'] = {'status': 'not_verified', 'file_count': len(runtime), 'method': method}
    result['documentation_freshness'] = {'status': 'not_verified', 'file_count': len(documentation)}
    completed = result.get('completed_at')
    if completed:
        try:
            at = datetime.fromisoformat(completed)
            if at.utcoffset() is None:
                raise ValueError('Build completion timestamp requires a timezone')
            timestamp = at.timestamp()
            changed = any(record['modified_at'] > timestamp for record in runtime)
            docs_changed = any(record['modified_at'] > timestamp for record in documentation)
            result['source_changed_since_build'] = changed or partial
            result['documentation_changed_since_build'] = docs_changed
            result['source_freshness']['status'] = 'unknown' if partial else 'changed' if changed else 'current'
            result['documentation_freshness']['status'] = 'unknown' if partial else 'changed' if docs_changed else 'current'
        except (ValueError, TypeError):
            result['source_changed_since_build'] = True
            result['source_freshness']['status'] = 'unknown'
            result['documentation_freshness']['status'] = 'unknown'
    result['checkpoint_verification'] = _read_checkpoint_verification(root / 'engine/out/checkpoint_verification.json')
    result['renderer_verification'] = _read_milestone_verification(root / 'engine/out/renderer_verification.json')
    result['world_scene_verification'] = _read_world_scene_verification(root / 'engine/out/world_scene_verification.json')
    result['movement_verification'] = _read_movement_verification(root / 'engine/out/movement_verification.json')
    result['obstacle_course_verification'] = _read_obstacle_course_verification(root / 'engine/out/obstacle_course_verification.json')
    result['gameplay_store_verification'] = _read_gameplay_store_verification(root / 'engine/out/gameplay_store_verification.json')
    result['registry_migration_verification'] = _read_registry_migration_verification(root / 'engine/out/registry_migration_verification.json')
    result['durable_world_verification'] = _read_durable_world_verification(root / 'engine/out/durable_world_verification.json')
    result['first_boot_chapter_verification'] = _read_first_boot_chapter_verification(root / 'engine/out/first_boot_chapter_verification.json')
    result['creator_workspace_verification'] = _read_milestone_verification(root / 'engine/out/creator_workspace_verification.json')
    result['creator_viewport_verification'] = _read_milestone_verification(root / 'engine/out/creator_viewport_verification.json')
    result['first_boot_content_verification'] = _read_milestone_verification(root / 'engine/out/first_boot_content_verification.json')
    result['content_authoring_verification'] = _read_milestone_verification(root / 'engine/out/content_authoring_verification.json')
    result['chapter_creator_verification'] = _read_milestone_verification(
        root / 'engine/out/chapter_creator_verification.json', extra_fields=('metrics',))
    result['chapter_play_verification'] = _read_milestone_verification(
        root / 'engine/out/chapter_play_verification.json', extra_fields=('metrics',))
    result['ai_authoring_verification'] = _read_milestone_verification(
        root / 'engine/out/ai_authoring_verification.json', extra_fields=('metrics',))
    result['asset_pipeline_verification'] = _read_milestone_verification(
        root / 'engine/out/asset_pipeline_verification.json', extra_fields=('metrics',))
    result['persistent_placement_verification']=_read_persistent_placement_verification(
        root/'engine/out/persistent_placement_verification.json')
    result['warm_beginning_summary'] = _read_warm_beginning_summary(
        root/'engine/out/warm_beginning/monitor_summary.json')
    result['milestone_queue'] = _read_milestone_queue(root / 'engine/milestone_queue.json')
    result['hosting_verification'] = _read_milestone_verification(root / 'engine/out/site-verification/hosting_verification.json', 'verified_at')
    generated, _ = _directory_metrics(root / 'engine/out')
    installed, _ = _directory_metrics(root / 'engine/install')
    checkpoint_metrics, checkpoints = _directory_metrics(root / 'engine/out/checkpoints', '.aibs')
    checkpoints.sort(key=lambda item: (-item['modified_at'], str(item['path'])))
    for item in checkpoints:
        item['path'] = item['path'].relative_to(root).as_posix()
    result['checkpoints'] = checkpoints[:20]
    result['checkpoint_inventory_partial'] = checkpoint_metrics['partial']
    result['engine_storage'] = {'generated': generated, 'installed': installed}
    for drive in ('C:/', 'D:/', 'E:/'):
        try:
            usage = shutil.disk_usage(drive)
            result['drives'].append({'drive': drive, 'free_bytes': usage.free, 'total_bytes': usage.total,
                                     'low_space': usage.free < 20 * 1024**3})
        except OSError:
            continue
    log = root / 'engine/out/verification.log'
    if log.exists():
        try:
            result['log'] = _read_log_tail(log)
        except OSError as exc:
            result['log'] = str(exc)
    result['observed_at'] = datetime.now(timezone.utc).isoformat()
    return result
