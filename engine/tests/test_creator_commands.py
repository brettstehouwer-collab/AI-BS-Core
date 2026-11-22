import math
import struct
import unittest
from native_studio.game_engine.creator_commands import decode_response, decode_page, decode_description, Status
from native_studio.game_engine.creator_payload import PayloadError

UUID='01234567-89ab-4cde-8fab-0123456789ab'


def text(value):
    raw=value.encode('utf-8') if isinstance(value,str) else value
    return struct.pack('<I',len(raw))+raw


def response(status=0,compatible=0,count=0,body_size=0,message='OK'):
    return (struct.pack('<HH',1,status)+text(message)+text(UUID)+text('p')+text('b')+text(UUID)+
            struct.pack('<Q',9)+text('')+struct.pack('<Q',1)+text('')+text('')+struct.pack('<BQ',compatible,0)+
            text('Not assessed')+struct.pack('<IQQI',count,0,0,body_size))


class CreatorCommandTests(unittest.TestCase):
    def test_response_keeps_head_and_original_operation_revisions_distinct(self):
        decoded=decode_response(response())
        self.assertEqual(decoded.status,Status.OK)
        self.assertEqual((decoded.head_revision,decoded.operation_revision),(9,1))
        self.assertEqual(decoded.scope.host_epoch,UUID)

    def test_every_response_truncation_and_trailing_data(self):
        raw=response()
        for end in range(len(raw)):
            with self.subTest(end=end),self.assertRaises(PayloadError):
                decode_response(raw[:end])
        with self.assertRaises(PayloadError):
            decode_response(raw+b'x')

    def test_invalid_response_bounds_flags_status_and_text(self):
        for raw in (response(status=99),response(compatible=2),response(count=10001),
                    response(body_size=512*1024+1),response(message=b'\xff'),response(message=b'\0')):
            with self.assertRaises(PayloadError):
                decode_response(raw)

    def test_schema_roundtrip_and_rejections(self):
        raw=struct.pack('<I',1)+text('x')+struct.pack('<dd',-100.,100.)
        self.assertEqual(decode_description(raw),(('x',-100.,100.),))
        for invalid in (struct.pack('<I',65),raw+b'extra',
                        struct.pack('<I',1)+text('x')+struct.pack('<dd',math.nan,100.),
                        struct.pack('<I',1)+text('x')+struct.pack('<dd',10.,0.)):
            with self.assertRaises(PayloadError):
                decode_description(invalid)

    def test_page_identity_and_exact_negative_zero(self):
        raw=text('a')+struct.pack('<BI',0,1)+text('a')+text('A')+text(UUID)+struct.pack('<I',1)+text('x')+struct.pack('<d',-0.)
        rows,cursor,more=decode_page(raw)
        self.assertEqual((cursor,more,rows[0].uuid),('a',False,UUID))
        self.assertEqual(math.copysign(1,rows[0].fields[0][1]),-1)
        for end in range(len(raw)):
            with self.subTest(end=end),self.assertRaises(PayloadError):
                decode_page(raw[:end])

    def test_oversized_and_duplicate_page_fields_reject(self):
        prefix=text('a')+struct.pack('<BI',0,1)+text('a')+text('A')+text(UUID)
        field=text('x')+struct.pack('<d',1.)
        for raw in (text('')+struct.pack('<BI',0,65),prefix+struct.pack('<I',65),
                    prefix+struct.pack('<I',2)+field+field,
                    prefix+struct.pack('<I',1)+text('x')+struct.pack('<d',math.inf)):
            with self.assertRaises(PayloadError):
                decode_page(raw)


if __name__=='__main__':unittest.main()
