"""Bounded version-1 numeric authoring requests; host owns semantic admission."""
from dataclasses import dataclass
import math
import re
import struct

MAX_BYTES = 1024 * 1024
_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z')


class PayloadError(ValueError):
    pass


@dataclass(frozen=True)
class Scope:
    project: str
    branch: str
    world_id: str
    host_epoch: str


@dataclass(frozen=True)
class Create:
    alias: str
    name: str
    uuid: str
    fields: tuple


@dataclass(frozen=True)
class Erase:
    alias: str
    uuid: str


@dataclass(frozen=True)
class SetField:
    alias: str
    field: str
    value: float
    uuid: str


@dataclass(frozen=True)
class Transaction:
    operation_id: str
    revision: int
    description: str
    edits: tuple


@dataclass(frozen=True)
class EditRequest:
    scope: Scope
    transaction: Transaction


def _uuid(value, optional=False):
    if type(value) is not str or len(value) not in (0, 36):
        raise PayloadError('Invalid canonical UUID')
    if not (optional and value == '') and not _UUID.fullmatch(value):
        raise PayloadError('Invalid canonical UUID')
    return value


class _Writer:
    def __init__(self):
        self.data = bytearray()

    def number(self, value, fmt):
        try:
            raw = struct.pack('<' + fmt, value)
        except (struct.error, TypeError, OverflowError) as error:
            raise PayloadError('Invalid numeric field') from error
        self.append(raw)

    def append(self, raw):
        if len(self.data) + len(raw) > MAX_BYTES:
            raise PayloadError('Payload byte limit exceeded')
        self.data.extend(raw)

    def text(self, value, required=False):
        if type(value) is not str or len(value) > 4096 or '\0' in value or (required and not value):
            raise PayloadError('Invalid text field')
        try:
            raw = value.encode('utf-8', errors='strict')
        except UnicodeError as error:
            raise PayloadError('Invalid UTF-8 text') from error
        if len(raw) > 4096:
            raise PayloadError('Text byte limit exceeded')
        self.number(len(raw), 'I')
        self.append(raw)


class _Reader:
    def __init__(self, data):
        if type(data) is not bytes or len(data) > MAX_BYTES:
            raise PayloadError('Payload byte limit exceeded')
        self.data = data
        self.offset = 0

    def read(self, size):
        if size > len(self.data) - self.offset:
            raise PayloadError('Truncated payload')
        value = self.data[self.offset:self.offset + size]
        self.offset += size
        return value

    def number(self, fmt):
        return struct.unpack('<' + fmt, self.read(struct.calcsize('<' + fmt)))[0]

    def text(self, required=False):
        size = self.number('I')
        if size > 4096:
            raise PayloadError('Text byte limit exceeded')
        try:
            value = self.read(size).decode('utf-8', errors='strict')
        except UnicodeError as error:
            raise PayloadError('Invalid UTF-8 text') from error
        if '\0' in value or (required and not value):
            raise PayloadError('Invalid text field')
        return value


def encode_edit(request):
    w = _Writer()
    w.number(1, 'H')
    s = request.scope
    for value in (s.project, s.branch, _uuid(s.world_id), _uuid(s.host_epoch)):
        w.text(value, True)
    t = request.transaction
    w.text(t.operation_id, True)
    if type(t.revision) is not int:
        raise PayloadError('Invalid revision')
    w.number(t.revision, 'Q')
    w.text(t.description)
    if not 1 <= len(t.edits) <= 256:
        raise PayloadError('Edit count limit')
    w.number(len(t.edits), 'I')
    for edit in t.edits:
        tag = {Create: 0, Erase: 1, SetField: 2}.get(type(edit))
        if tag is None:
            raise PayloadError('Unknown edit kind')
        w.number(tag, 'B')
        w.text(edit.alias, True)
        if tag == 0:
            w.text(edit.name)
            w.text(_uuid(edit.uuid, True))
            if len(edit.fields) > 64 or len({k for k, _ in edit.fields}) != len(edit.fields):
                raise PayloadError('Field count or duplicate key')
            w.number(len(edit.fields), 'I')
            for field, value in sorted(edit.fields):
                w.text(field, True)
                _write_double(w, value)
        elif tag == 1:
            w.text(_uuid(edit.uuid, True))
        else:
            w.text(edit.field, True)
            _write_double(w, edit.value)
            w.text(_uuid(edit.uuid, True))
    return bytes(w.data)


def _write_double(w, value):
    if type(value) not in (int, float):
        raise PayloadError('Invalid finite number')
    try:
        finite = math.isfinite(value)
    except OverflowError as error:
        raise PayloadError('Number exceeds binary64 range') from error
    if not finite:
        raise PayloadError('Invalid finite number')
    w.number(value, 'd')


def decode_edit(data):
    r = _Reader(data)
    if r.number('H') != 1:
        raise PayloadError('Unsupported payload version')
    scope = Scope(r.text(True), r.text(True), _uuid(r.text(True)), _uuid(r.text(True)))
    operation, revision, description = r.text(True), r.number('Q'), r.text()
    count = r.number('I')
    if not 1 <= count <= 256:
        raise PayloadError('Edit count limit')
    edits = []
    for _ in range(count):
        tag = r.number('B')
        if tag not in (0, 1, 2):
            raise PayloadError('Unknown edit kind')
        alias = r.text(True)
        if tag == 0:
            name, uuid = r.text(), _uuid(r.text(), True)
            fields_count = r.number('I')
            if fields_count > 64:
                raise PayloadError('Field count limit')
            fields = []
            for _ in range(fields_count):
                fields.append((r.text(True), r.number('d')))
            edits.append(Create(alias, name, uuid, tuple(fields)))
        elif tag == 1:
            edits.append(Erase(alias, _uuid(r.text(), True)))
        else:
            field, value = r.text(True), r.number('d')
            edits.append(SetField(alias, field, value, _uuid(r.text(), True)))
    if r.offset != len(data):
        raise PayloadError('Trailing payload bytes')
    result = EditRequest(scope, Transaction(operation, revision, description, tuple(edits)))
    # Common validation catches duplicate/non-finite fields; never changes IDs.
    encode_edit(result)
    return result
