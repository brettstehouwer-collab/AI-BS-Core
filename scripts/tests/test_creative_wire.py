import io
import struct
import unittest
from native_studio.creative_wire import encode, read_message, WireError, MAX_FRAME


class CreativeWireTests(unittest.TestCase):
    def test_split_unicode_frames_preserve_message_boundaries(self):
        stream = io.BytesIO(encode({'text': 'é 猫', 'id': 1}) + encode({'id': 2}))
        fragmented = lambda length: stream.read(min(length, 1))
        self.assertEqual(read_message(fragmented), {'text': 'é 猫', 'id': 1})
        self.assertEqual(read_message(fragmented), {'id': 2})

    def test_oversize_rejected_before_body_read(self):
        calls = []
        def read(length):
            calls.append(length)
            return struct.pack('!I', MAX_FRAME + 1)
        with self.assertRaises(WireError): read_message(read)
        self.assertEqual(calls, [4])

    def test_malformed_and_truncated_messages_refused(self):
        for body in (b'{}', b'{"a":1,"a":2}', b'{"x":NaN}', b'[]', b'\xff'):
            raw = struct.pack('!I', len(body)) + body
            if body == b'{}': raw = raw[:-1]
            with self.subTest(body=body), self.assertRaises(WireError):
                read_message(io.BytesIO(raw).read)

    def test_nonfinite_encoder_refused(self):
        with self.assertRaises(WireError): encode({'x': float('inf')})

    def test_exponent_overflow_refused_at_any_depth(self):
        for body in (b'{"x":1e400}', b'{"x":[{"y":-1e400}]}'):
            with self.subTest(body=body), self.assertRaises(WireError):
                read_message(io.BytesIO(struct.pack('!I', len(body)) + body).read)

    def test_finite_numeric_values_roundtrip(self):
        value = {'zero': 0, 'negative': -7, 'fraction': 1.25, 'small': 1e-200}
        self.assertEqual(read_message(io.BytesIO(encode(value)).read), value)
