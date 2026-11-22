import struct
import unittest
from native_studio.game_engine.creator_payload import (
    Scope, Transaction, Create, Erase, SetField, EditRequest, encode_edit, decode_edit, PayloadError,
)

UUID = '01234567-89ab-4cde-8fab-0123456789ab'


class CreatorPayloadTests(unittest.TestCase):
    def request(self):
        return EditRequest(Scope('project', 'main', UUID, UUID), Transaction(
            'gesture', 7, 'Unicode pencil: ✏',
            (Create('node', 'Node', UUID, (('x', -0.0), ('power', 3.5))),
             SetField('node', 'x', 4.5, UUID), Erase('node', UUID))))

    def test_roundtrip_and_numeric_bits(self):
        request = self.request()
        raw = encode_edit(request)
        decoded = decode_edit(raw)
        self.assertEqual(decoded.scope, request.scope)
        self.assertEqual(encode_edit(decoded), raw)
        self.assertIn(struct.pack('<d', -0.0), raw)
        self.assertEqual(decoded.transaction.edits[0].fields, (('power', 3.5), ('x', -0.0)))

    def test_truncation_and_trailing_bytes(self):
        raw = encode_edit(self.request())
        for size in range(len(raw)):
            with self.subTest(size=size), self.assertRaises(PayloadError):
                decode_edit(raw[:size])
        with self.assertRaises(PayloadError):
            decode_edit(raw + b'x')

    def test_invalid_utf8_uuid_and_huge_lengths(self):
        raw = bytearray(encode_edit(self.request()))
        for offset, value in ((0, b'\x02\0'), (2, b'\xff\xff\xff\xff'), (6, b'\xff'),
                              (6, b'\0')):
            invalid = raw.copy()
            invalid[offset:offset+len(value)] = value
            with self.assertRaises(PayloadError):
                decode_edit(bytes(invalid))
        request = self.request()
        for scope in (Scope('p', 'b', 'bad', UUID), Scope('p', 'b', UUID.upper(), UUID)):
            with self.assertRaises(PayloadError):
                encode_edit(EditRequest(scope, request.transaction))

    def test_bounds_duplicates_and_nonfinite(self):
        scope = self.request().scope
        for edits in ((), (Erase('n', UUID),)*257,
                      (Create('n', 'N', UUID, (('x', 1.), ('x', 2.))),),
                      (SetField('n', 'x', float('nan'), UUID),),
                      (SetField('n', 'x', float('inf'), UUID),)):
            with self.assertRaises(PayloadError):
                encode_edit(EditRequest(scope, Transaction('id', 0, '', edits)))
        with self.assertRaises(PayloadError):
            encode_edit(EditRequest(scope, Transaction('id', 0, 'x'*4097, (Erase('n',UUID),))))
        with self.assertRaises(PayloadError):
            decode_edit(b'x'*(1024*1024+1))

    def test_absent_legacy_uuid_is_preserved_for_host_retry_resolution(self):
        request = EditRequest(self.request().scope, Transaction('old', 0, '', (Erase('n',''),)))
        self.assertEqual(decode_edit(encode_edit(request)), request)

    def test_python_type_errors_are_payload_errors(self):
        request = self.request()
        with self.assertRaises(PayloadError):
            encode_edit(EditRequest(Scope('p', 'b', None, UUID), request.transaction))
        with self.assertRaises(PayloadError):
            encode_edit(EditRequest(request.scope, Transaction('id', 0, '', (SetField('n','x',10**1000,UUID),))))


if __name__ == '__main__':
    unittest.main()
