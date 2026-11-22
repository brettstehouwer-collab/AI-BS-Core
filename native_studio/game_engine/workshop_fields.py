"""Closed five-fixture opening workflow and conservative saved-history guard.

The native owner validates gameplay and navigation. These checks validate typed
ownership and reader requirements before publishing authoring requests or files.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import os
import struct
import tempfile

from .creator_payload import PayloadError, _uuid

WORKSHOP_CAPABILITY = 'chapter-workshop-commissioning-v1'
WORKSHOP_BINDING_FIELD = 'hint.workshop.binding'
WORKSHOP_ROLE_FIELD = 'workshop_role'
WORKSHOP_ACTIONS = ('tool', 'supply', 'path', 'tester', 'bench')
WORKSHOP_LABELS = ('Diagnostic probe', 'Supply sample', 'Path sample', 'Circuit tester', 'Shelter workbench')
_HEADER = 'AIBWORKSHOP 1\n'
_JOURNAL_LIMIT = 1024 * 1024


def workshop_default_centers(rows):
    """Factory-relative suggestions; native Preview still validates real routes.

    Read current owned anchors, never fixture titles or arbitrary global board
    coordinates. Missing/ambiguous anchors fail before generating a request.
    """
    rows = tuple(rows)
    def owned(kind):
        matches = [row for row in rows if row.type_id == kind]
        if len(matches) != 1:
            raise PayloadError('Workshop default placement requires one owned ' + kind + ' anchor')
        values = dict(matches[0].fields)
        if len(values) != len(matches[0].fields):
            raise PayloadError('Duplicate Workshop placement anchor fields')
        return values
    def vector(fields, prefix):
        values = tuple(fields.get(prefix + axis) for axis in 'xyz')
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
            raise PayloadError('Workshop default placement requires finite ' + prefix + 'x/y/z anchors')
        return values
    def f32(value):
        try:
            result = struct.unpack('<f', struct.pack('<f', value))[0]
        except (OverflowError, struct.error) as error:
            raise PayloadError('Workshop placement anchor exceeds native float range') from error
        if not math.isfinite(result):
            raise PayloadError('Workshop placement anchor exceeds native float range')
        return result
    def add(a, b):
        return tuple(f32(f32(x) + f32(y)) for x, y in zip(a, b))
    settings = owned('authoring.ChapterSettings')
    if settings.get('asset_profile') != 'warm_beginning':
        raise PayloadError('Workshop default placement requires Warm Beginning anchors')
    origin = add(vector(settings, 'jenison_return.0.'), (32., -.2, 25.))
    isolation = vector(owned('firstboot.PowerFault'), 'isolation_')
    lamp = vector(owned('firstboot.NPCQuest'), 'lamp_')
    return (add(origin, (-35.45, 1.45, -28.25)), add(origin, (-33.4, 1.3, -6.9)),
        add(origin, (-42.5, 1.55, -7.)), add(isolation, (0., 1.1, -1.25)),
        add(lamp, (1.4, 1.15, -.9)))


def decode_workshop_binding(value):
    if type(value) is not str:
        raise PayloadError('Workshop binding requires bounded text')
    try:
        raw = value.encode('utf-8', errors='strict')
    except UnicodeError as error:
        raise PayloadError('Invalid Workshop binding UTF-8') from error
    if value == '':
        return ()  # Native virtual authoring field; no on-disk hint.
    if len(raw) > 256 or not value.startswith(_HEADER) or not value.endswith('\n'):
        raise PayloadError('Workshop binding requires AIBWORKSHOP 1 and five UUID lines with a final LF')
    lines = value[len(_HEADER):].split('\n')
    if len(lines) != 6 or lines[-1] != '':
        raise PayloadError('Workshop binding must name exactly tool, supply, path, tester and bench')
    result = tuple(_uuid(item) for item in lines[:-1])
    if len(set(result)) != 5:
        raise PayloadError('Workshop actions require five distinct owned fixtures')
    return result


def encode_workshop_binding(identities):
    identities = tuple(identities)
    if len(identities) != 5:
        raise PayloadError('Select one fixture for each of the five Workshop actions')
    result = _HEADER + ''.join(_uuid(identity) + '\n' for identity in identities)
    decode_workshop_binding(result)
    return result


def workshop_bindings_from_rows(rows, asset_profile=None):
    if asset_profile not in (None, 'legacy_v1', 'warm-beginning'):
        raise PayloadError('Invalid Workshop asset profile')
    rows = tuple(rows)
    if any(row.type_id == 'firstboot.OpeningWorkshop' for row in rows):
        raise PayloadError('Opening Workshop runtime progress is not an authoring observation')
    metadata = [row for row in rows if any(key == WORKSHOP_BINDING_FIELD for key, _ in row.fields)]
    roles = []
    for row in rows:
        fields = dict(row.fields)
        if WORKSHOP_ROLE_FIELD not in fields:
            continue
        if row.type_id != 'authoring.Fixture' or fields[WORKSHOP_ROLE_FIELD] is not True:
            raise PayloadError('Workshop role observations require an owned fixture and the boolean true')
        from .opening_fields import fixture_inspection_fields
        fixture_inspection_fields(row)
        roles.append(row.uuid)
    if not metadata:
        if roles:
            raise PayloadError('Workshop fixtures require one complete five-action binding')
        return ()
    settings = [row for row in rows if row.type_id == 'authoring.ChapterSettings']
    if len(metadata) != 1 or len(settings) != 1 or metadata[0] is not settings[0]:
        raise PayloadError('Workshop binding requires one owned chapter settings observation')
    fields = dict(settings[0].fields)
    if len(fields) != len(settings[0].fields):
        raise PayloadError('Duplicate Workshop settings fields')
    identities = decode_workshop_binding(fields[WORKSHOP_BINDING_FIELD])
    if not identities:
        if roles:
            raise PayloadError('Clear the Workshop binding and demote its five fixtures in one grouped Preview')
        return ()
    if fields.get('asset_profile') != 'warm_beginning' or asset_profile == 'legacy_v1':
        raise PayloadError('Opening Workshop requires an AIBD3 Warm Beginning chapter')
    if set(roles) != set(identities) or len(roles) != 5:
        raise PayloadError('Workshop binding must match exactly five owned Workshop-role fixtures')
    for action, identity in zip(WORKSHOP_ACTIONS, identities):
        owned = [row for row in rows if row.uuid == identity]
        if len(owned) != 1 or owned[0].type_id != 'authoring.Fixture':
            raise PayloadError('Workshop ' + action + ' must reference an owned fixture')
        values = dict(owned[0].fields)
        if values.get('selectable') is not True:
            raise PayloadError('Workshop ' + action + ' must remain selectable; rebind it before editing')
        if any(values.get(key, '') for key in ('inspection_text', 'inspection_source', 'inspection_action')):
            raise PayloadError('Workshop ' + action + ' cannot also carry a reading or quiet-seat panel')
    return identities


def opening_workshop_authored_from_rows(rows, asset_profile=None):
    return bool(workshop_bindings_from_rows(rows, asset_profile))


def edits_require_workshop(edits):
    from .content_commands import SetField
    return any(isinstance(edit, SetField) and edit.field in (WORKSHOP_ROLE_FIELD, WORKSHOP_BINDING_FIELD) for edit in edits)


def edits_publish_workshop(edits):
    from .content_commands import SetField
    return any(isinstance(edit, SetField) and
        (edit.field == WORKSHOP_ROLE_FIELD and edit.value is True or
         edit.field == WORKSHOP_BINDING_FIELD and bool(decode_workshop_binding(edit.value))) for edit in edits)


def validate_workshop_edits(rows, edits, asset_profile=None):
    """Validate final grouped state; temporary partial bindings are not published."""
    from .content_commands import TypedRow, SetField, CreateFixture, EraseFixture, _fixture_fields
    states = {row.uuid: [row.type_id, row.name, dict(row.fields)] for row in rows}
    for edit in edits:
        if isinstance(edit, CreateFixture):
            if edit.uuid in states:
                raise PayloadError('Workshop edit cannot replace an existing identity')
            fields = dict(_fixture_fields(edit))
            # Modern native observations expose the complete empty inspection triple.
            if asset_profile == 'warm-beginning':
                fields.update(inspection_text='', inspection_source='', inspection_action='')
            states[edit.uuid] = ['authoring.Fixture', edit.name, fields]
        elif isinstance(edit, EraseFixture):
            states.pop(edit.uuid, None)
        elif isinstance(edit, SetField):
            if edit.field in (WORKSHOP_ROLE_FIELD, WORKSHOP_BINDING_FIELD) and edit.uuid not in states:
                raise PayloadError('Workshop edits require an owned fixture or chapter settings')
            if edit.uuid not in states:
                continue
            kind, name, fields = states[edit.uuid]
            if edit.field == WORKSHOP_ROLE_FIELD:
                if kind != 'authoring.Fixture' or type(edit.value) is not bool:
                    raise PayloadError('Workshop role requires an owned fixture and a typed boolean')
                if edit.value:
                    fields[WORKSHOP_ROLE_FIELD] = True
                else:
                    fields.pop(WORKSHOP_ROLE_FIELD, None)
            elif edit.field == WORKSHOP_BINDING_FIELD:
                if kind != 'authoring.ChapterSettings':
                    raise PayloadError('Workshop binding belongs to chapter settings')
                decode_workshop_binding(edit.value)
                if edit.value:
                    fields[edit.field] = edit.value
                else:
                    fields.pop(edit.field, None)
            else:
                fields[edit.field] = edit.value
    result = tuple(TypedRow(identity, kind, fields.get('name', name), tuple(sorted(fields.items())))
        for identity, (kind, name, fields) in states.items())
    workshop_bindings_from_rows(result, asset_profile)


def require_workshop_host(executable, required):
    if type(required) is not bool:
        raise ValueError('Invalid saved Workshop history requirement')
    if required:
        from native_studio.game_build_monitor import read_native_player_capabilities
        if read_native_player_capabilities(executable).get('features', {}).get(WORKSHOP_CAPABILITY) is not True:
            raise ValueError('This chapter contains Workshop history; upgrade the native Host before opening it')


def _read_bounded(path, limit):
    if path.is_symlink():
        raise ValueError('Workshop project files cannot be symbolic links')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Workshop project file exceeds its bounded size')
    return raw


def _journal_fingerprint(path):
    try:
        raw = _read_bounded(path, _JOURNAL_LIMIT)
        return (len(raw), hashlib.sha256(raw).hexdigest())
    except (OSError, ValueError):
        return None  # Ambiguous or missing journals never permit a downgrade.


def _replace_metadata(path, raw):
    descriptor, name = tempfile.mkstemp(prefix='.aibs-workshop-', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class WorkshopSaveGuard:
    """Conservative pre-Save declaration; rollback requires unchanged disk proof."""
    metadata: Path
    previous: bytes
    declared: bytes
    journal: Path
    before_journal: object

    @classmethod
    def prepare(cls, definition):
        if getattr(definition, 'opening_workshop', False):
            return None
        if definition.asset_profile != 'warm-beginning':
            raise ValueError('Saved Workshop history requires a Warm Beginning project')
        path = definition.path
        # Reconcile current metadata instead of overwriting another writer.
        loaded = type(definition).load(definition.directory)
        if loaded != definition:
            raise ValueError('Chapter metadata changed; reopen the project before saving')
        previous = _read_bounded(path, 64 * 1024)
        journal = definition.directory / 'chapter.aiba'
        fingerprint = _journal_fingerprint(journal)
        declared = (json.dumps({'version': 3, 'project': definition.project, 'branch': definition.branch,
            'asset_profile': definition.asset_profile, 'opening_workshop': True}, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        if _read_bounded(path, 64 * 1024) != previous:
            raise ValueError('Chapter metadata changed during Workshop Save preparation')
        _replace_metadata(path, declared)
        return cls(path, previous, declared, journal, fingerprint)

    def restore_if_uncommitted(self):
        """Only use for an explicit rejected Save; unknown transport outcomes stay v3."""
        if self.before_journal is None or _journal_fingerprint(self.journal) != self.before_journal:
            return False
        try:
            if _read_bounded(self.metadata, 64 * 1024) != self.declared:
                return False
            # Recheck journal immediately before replacement, never infer from ACK alone.
            if _journal_fingerprint(self.journal) != self.before_journal:
                return False
            _replace_metadata(self.metadata, self.previous)
            return True
        except (OSError, ValueError):
            return False
