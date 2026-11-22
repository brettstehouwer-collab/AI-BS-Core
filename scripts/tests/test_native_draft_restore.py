"""Private recovery is local, owner/source bound and revision checked."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from native_studio.screenplay_client import DraftSession, ScreenplayError


@unittest.skipUnless(os.name == 'nt', 'Windows private recovery')
class DraftRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'private'
        self.host = dict(project='Synthetic', revision='revision-1', content='Host text')

    def fresh(self, scope='a'*64, host=None):
        draft = DraftSession(self.root)
        draft.recovery_scope = scope
        draft.load(host or self.host)
        return draft

    def saved_copy(self):
        draft = self.fresh()
        draft.content = 'Unsaved text — complete\nSecond line'
        path = draft.preserve()
        return draft, path

    def test_fresh_session_restores_without_changing_host_or_recovery(self):
        old, path = self.saved_copy()
        raw = path.read_bytes()
        fresh = self.fresh()
        fresh.restore(path)
        self.assertEqual(fresh.content, old.content)
        self.assertEqual(fresh.baseline, self.host['content'])
        self.assertTrue(fresh.dirty)
        self.assertFalse(fresh.uncertain)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(self.host['content'], 'Host text')

    def test_different_owner_source_binding_and_revision_refused(self):
        _, path = self.saved_copy()
        for fresh in (self.fresh('b'*64), self.fresh(host={**self.host, 'revision':'revision-2'}),
                      self.fresh(host={**self.host, 'project':'Other'}),
                      self.fresh(host={**self.host, 'content':'Changed host'})):
            before = fresh.content
            with self.assertRaises(ScreenplayError):
                fresh.restore(path)
            self.assertEqual(fresh.content, before)

    def test_current_dirty_draft_preserved_before_replacement(self):
        old, path = self.saved_copy()
        fresh = self.fresh()
        fresh.content = 'Other unsaved current work'
        fresh.restore(path)
        records = [json.loads(p.read_bytes()) for p in self.root.glob('*.json')]
        self.assertIn('Other unsaved current work', [r['content'] for r in records])
        self.assertEqual(fresh.content, old.content)

    def test_legacy_unbound_and_duplicate_or_extra_fields_refused(self):
        _, path = self.saved_copy()
        record = json.loads(path.read_bytes())
        payloads = [json.dumps({**record, 'schema':1}),
                    json.dumps({**record, 'unexpected':True}),
                    json.dumps(record)[:-1] + ',"content":"duplicate"}']
        for number, payload in enumerate(payloads):
            candidate = self.root / f'invalid-{number}.json'
            candidate.write_text(payload, encoding='utf8')
            fresh = self.fresh()
            with self.assertRaises(ScreenplayError):
                fresh.restore(candidate)
            self.assertEqual(fresh.content, 'Host text')

    def test_outside_root_hardlink_and_oversized_file_refused(self):
        _, path = self.saved_copy()
        outside = Path(self.temp.name) / 'outside.json'
        outside.write_bytes(path.read_bytes())
        linked = self.root / 'linked.json'
        os.link(outside, linked)
        large = self.root / 'large.json'
        with large.open('wb') as stream:
            stream.truncate(32*1024*1024+1)
        for candidate in (outside, linked, large):
            with self.assertRaises(ScreenplayError):
                self.fresh().restore(candidate)

    def test_uncertain_or_pending_host_requires_fresh_read(self):
        _, path = self.saved_copy()
        fresh = self.fresh()
        fresh.uncertain = True
        with self.assertRaises(ScreenplayError):
            fresh.restore(path)
        fresh.load(self.host)
        fresh.pending_operation = {'kind':'WRITE'}
        with self.assertRaises(ScreenplayError):
            fresh.restore(path)

    def test_rich_record_roundtrip_retains_styles_and_undo(self):
        from scripts.tests.test_native_rich_writer import fixture
        data=fixture()
        old=self.fresh(host=data)
        old.content=old.content.replace('🐈','🐕')
        path=old.preserve()
        fresh=self.fresh(host=data)
        fresh.restore(path)
        self.assertEqual(fresh.rich.recovery_payload(),old.rich.recovery_payload())
        self.assertEqual(fresh.capture_rich_snapshot(),old.capture_rich_snapshot())
        fresh.content=data['content']
        self.assertFalse(fresh.dirty)
        self.assertEqual(fresh.capture_rich_snapshot(),data['fdx_document'])

    def test_rich_record_tampering_retains_current_draft(self):
        from scripts.tests.test_native_rich_writer import fixture
        data=fixture()
        old=self.fresh(host=data)
        old.content=old.content.replace('🐈','🐕')
        path=old.preserve()
        record=json.loads(path.read_bytes())
        record['rich_draft']['fdx_document']['title_page'][0]['text']='Changed private metadata'
        altered=self.root/'altered.json'
        altered.write_text(json.dumps(record),encoding='utf8')
        fresh=self.fresh(host=data)
        with self.assertRaises(ScreenplayError):fresh.restore(altered)
        self.assertEqual(fresh.content,data['content'])


if __name__ == '__main__':
    unittest.main()
