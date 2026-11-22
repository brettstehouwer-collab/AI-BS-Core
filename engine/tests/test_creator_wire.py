import struct
import unittest

from native_studio.game_engine.creator_wire import (
    Frame, Opcode, Parser, WireError, encode, MAX_PAYLOAD, UNSCOPED_REVISION,
)


class CreatorWireTests(unittest.TestCase):
    def frame(self, payload=b'abc'):
        return Frame(Opcode.PREVIEW, 27, bytes(range(16)), 9, payload)

    def test_exact_header_and_all_split_boundaries(self):
        frame = self.frame(struct.pack('<d', -0.0))
        raw = encode(frame)
        self.assertEqual(raw[:16], b'AIBC\x01\x00\x30\x00\x20\x00\x00\x00\x08\x00\x00\x00')
        self.assertEqual(raw[16:24], struct.pack('<Q', 27))
        self.assertEqual(raw[24:40], bytes(range(16)))
        self.assertEqual(raw[40:48], struct.pack('<Q', 9))
        for split in range(len(raw) + 1):
            with self.subTest(split=split):
                parser = Parser()
                self.assertEqual(parser.feed(raw[:split]) + parser.feed(raw[split:]), [frame])
                parser.finish()

    def test_every_truncation_fails_at_eof(self):
        raw = encode(self.frame())
        for end in range(1, len(raw)):
            parser = Parser()
            parser.feed(raw[:end])
            with self.subTest(end=end), self.assertRaises(WireError):
                parser.finish()

    def test_invalid_headers_poison_connection(self):
        raw = bytearray(encode(self.frame()))
        for offset, data in [(0, b'FAIL'), (4, b'\x02\x00'), (6, b'\x31\x00'),
                             (8, b'\x99\x00'), (10, b'\x02\x00'),
                             (12, struct.pack('<I', MAX_PAYLOAD + 1)),
                             (16, b'\0' * 8)]:
            broken = raw.copy()
            broken[offset:offset + len(data)] = data
            parser = Parser()
            with self.subTest(offset=offset), self.assertRaises(WireError):
                parser.feed(bytes(broken[:48]))
            self.assertLessEqual(parser.buffered_bytes, 48)
            with self.assertRaises(WireError):
                parser.feed(bytes(raw))

    def test_coalesced_and_empty_frames(self):
        a = Frame(Opcode.HELLO, 1, bytes(16), UNSCOPED_REVISION, b'')
        b = self.frame()
        parser = Parser()
        self.assertEqual(parser.feed(encode(a) + encode(b)), [a, b])
        parser.finish()

    def test_read_chunk_and_frame_burst_are_bounded(self):
        parser = Parser()
        with self.assertRaises(WireError):
            parser.feed(b'x' * (65536 + 1))
        raw = encode(self.frame(b''))
        parser = Parser()
        with self.assertRaises(WireError):
            parser.feed(raw * 9)

    def test_maximum_payload_arrives_incrementally(self):
        frame = self.frame(b'x' * MAX_PAYLOAD)
        raw = encode(frame)
        parser = Parser()
        frames = []
        for start in range(0, len(raw), 65536):
            frames.extend(parser.feed(raw[start:start + 65536]))
            self.assertLessEqual(parser.buffered_bytes, MAX_PAYLOAD)
        self.assertEqual(frames, [frame])
        parser.finish()

    def test_encoder_rejects_invalid_fields(self):
        for frame in [Frame(Opcode.HELLO, 0, bytes(16), 0, b''),
                      Frame(Opcode.HELLO, 1, b'', 0, b''),
                      Frame(Opcode.HELLO, 1, bytes(16), -1, b''),
                      self.frame(b'x' * (MAX_PAYLOAD + 1))]:
            with self.assertRaises(WireError):
                encode(frame)


if __name__ == '__main__':
    unittest.main()
