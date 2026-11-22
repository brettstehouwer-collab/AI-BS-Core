"""Version-1 pipe framing; payload semantics and owner dispatch are separate.

Callers read at most MAX_CHUNK bytes at a time and dispatch only fully returned
frames. A framing failure is terminal for the connection. This module performs
no filesystem access, process launch, or world mutation.
"""
from dataclasses import dataclass
from enum import IntEnum
import struct

MAX_PAYLOAD = 4 * 1024 * 1024
MAX_CHUNK = 65536
MAX_BURST = 8
UNSCOPED_REVISION = (1 << 64) - 1
_HEADER = struct.Struct('<4sHHHHIQ16sQ')


class WireError(ValueError):
    pass


class Opcode(IntEnum):
    HELLO = 0x0001
    OPEN = 0x0010
    DESCRIBE = 0x0011
    SNAPSHOT_PAGE = 0x0012
    PREVIEW = 0x0020
    APPLY_PREPARED = 0x0021
    APPLY_TRANSACTION = 0x0022
    RELEASE_PREPARED = 0x0023
    HISTORY = 0x0030
    SAVE = 0x0040
    START_PLAY = 0x0050
    STOP_PLAY = 0x0051
    SHUTDOWN = 0x00ff


@dataclass(frozen=True)
class Frame:
    opcode: Opcode
    request_id: int
    epoch: bytes
    revision: int
    payload: bytes
    response: bool = False


def _header(raw):
    magic, version, size, opcode, flags, length, request, epoch, revision = _HEADER.unpack(raw)
    if magic != b'AIBC' or version != 1 or size != 48:
        raise WireError('Unsupported creator frame header')
    try:
        opcode = Opcode(opcode)
    except ValueError as error:
        raise WireError('Unknown creator opcode') from error
    if flags not in (0, 1) or length > MAX_PAYLOAD or request == 0:
        raise WireError('Invalid creator flags, payload length or request identity')
    return opcode, request, epoch, revision, length, bool(flags)


def encode(frame):
    if (type(frame.request_id) is not int or not 0 < frame.request_id <= UNSCOPED_REVISION
            or type(frame.revision) is not int or not 0 <= frame.revision <= UNSCOPED_REVISION
            or type(frame.epoch) is not bytes or len(frame.epoch) != 16
            or type(frame.payload) is not bytes or len(frame.payload) > MAX_PAYLOAD
            or type(frame.response) is not bool):
        raise WireError('Invalid creator frame fields')
    try:
        opcode = Opcode(frame.opcode)
    except (ValueError, TypeError) as error:
        raise WireError('Unknown creator opcode') from error
    return _HEADER.pack(b'AIBC', 1, 48, opcode, int(frame.response), len(frame.payload),
                        frame.request_id, frame.epoch, frame.revision) + frame.payload


class Parser:
    def __init__(self):
        self._buffer = bytearray()
        self._pending = None
        self._failed = False
        self._closed = False

    @property
    def buffered_bytes(self):
        return len(self._buffer)

    def feed(self, chunk):
        if self._failed or self._closed:
            raise WireError('Creator connection is closed')
        try:
            if type(chunk) is not bytes or len(chunk) > MAX_CHUNK:
                raise WireError('Creator pipe read exceeds bounded chunk size')
            offset = 0
            frames = []
            while offset < len(chunk) or self._pending is not None:
                target = 48 if self._pending is None else self._pending[4]
                take = min(target - len(self._buffer), len(chunk) - offset)
                self._buffer.extend(memoryview(chunk)[offset:offset + take])
                offset += take
                if len(self._buffer) < target:
                    break
                if self._pending is None:
                    self._pending = _header(self._buffer)
                    self._buffer.clear()
                else:
                    opcode, request, epoch, revision, _, response = self._pending
                    if len(frames) >= MAX_BURST:
                        raise WireError('Creator frame burst exceeds admission limit')
                    frames.append(Frame(opcode, request, epoch, revision, bytes(self._buffer), response))
                    self._buffer.clear()
                    self._pending = None
            return frames
        except WireError:
            self._failed = True
            self._buffer.clear()
            self._pending = None
            raise

    def finish(self):
        if self._failed or self._buffer or self._pending is not None:
            self._failed = True
            raise WireError('Truncated or failed creator connection')
        self._closed = True
