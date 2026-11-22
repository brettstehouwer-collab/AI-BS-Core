"""Bounded message framing for the proposed owned creative channel.

Framing confers no authority. The opt-in owned-pipe client/controller still require
transport identity and owner/source/revision checks; no production candidate is selected.
"""
import json
import math
import struct

MAX_FRAME = 8 * 1024 * 1024


class WireError(ValueError):
    pass


def encode(value):
    if type(value) is not dict:
        raise WireError('A message object is required.')
    try:
        body = json.dumps(value, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise WireError('Invalid message.') from None
    if not 1 <= len(body) <= MAX_FRAME:
        raise WireError('Message exceeds channel bound.')
    return struct.pack('!I', len(body)) + body


def read_message(read):
    """Read exactly one frame; caller must enforce I/O deadlines/cancellation."""
    def exact(length):
        result = bytearray()
        while len(result) < length:
            part = read(length - len(result))
            if type(part) is not bytes or not part or len(part) > length - len(result):
                raise WireError('Incomplete or invalid channel read.')
            result.extend(part)
        return bytes(result)
    length = struct.unpack('!I', exact(4))[0]
    if not 1 <= length <= MAX_FRAME:
        raise WireError('Message exceeds channel bound.')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise WireError('Duplicate message field.')
            result[key] = value
        return result
    def invalid_constant(_):
        raise WireError('Invalid numeric constant.')
    def finite_float(text):
        number = float(text)
        if not math.isfinite(number):
            raise WireError('Nonfinite channel number.')
        return number
    try:
        value = json.loads(exact(length).decode('utf-8'),
            object_pairs_hook=unique, parse_constant=invalid_constant,
            parse_float=finite_float)
        if type(value) is not dict:
            raise WireError('A message object is required.')
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise WireError('Invalid channel message.') from None
