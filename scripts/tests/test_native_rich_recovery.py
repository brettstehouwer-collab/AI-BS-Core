"""Recovery replays local rich edits against a fresh confirmed host snapshot."""
import copy
import unittest

from native_studio.rich_screenplay_draft import NativeRichDraft, RichDraftError
from scripts.tests.test_native_rich_writer import fixture, acknowledged


class RichRecoveryTests(unittest.TestCase):
    def draft(self):
        data = fixture()
        draft = NativeRichDraft(data)
        draft.edit(data['content'].replace('🐈', '🐕'))
        return data, draft

    def test_rich_roundtrip_preserves_metadata_and_is_independent(self):
        data, draft = self.draft()
        payload = draft.recovery_payload()
        restored = NativeRichDraft.from_recovery(payload, data)
        self.assertEqual(restored.recovery_payload(), payload)
        self.assertEqual(restored.capture()['blocks'][0]['runs'], data['fdx_document']['blocks'][0]['runs'])
        restored.edit(restored.content.replace('Hello.', 'Welcome.'))
        self.assertNotEqual(restored.content, draft.content)
        self.assertEqual(payload, draft.recovery_payload())

    def test_undo_redo_and_alternative_branch_survive(self):
        data, draft = self.draft()
        dog = draft.content
        draft.edit(data['content'])
        draft.edit(data['content'].replace('Hello.', 'Welcome.'))
        other = draft.content
        restored = NativeRichDraft.from_recovery(draft.recovery_payload(), data)
        restored.edit(dog)
        self.assertEqual(restored.content, dog)
        self.assertEqual(restored.capture()['blocks'][0]['text'], 'He sees 🐕.')
        restored.edit(other)
        self.assertEqual(restored.content, other)
        self.assertEqual(restored.capture()['blocks'][2]['text'], 'Welcome.')
        restored.edit(data['content'])
        self.assertEqual(restored.capture(), data['fdx_document'])

    def test_blocked_structural_text_retained_without_authorizing_capture(self):
        data, draft = self.draft()
        valid = draft.content
        draft.edit(valid + '\nNew paragraph')
        restored = NativeRichDraft.from_recovery(draft.recovery_payload(), data)
        self.assertEqual(restored.recovery_payload(), draft.recovery_payload())
        with self.assertRaises(RichDraftError):
            restored.capture()
        restored.edit(valid)
        self.assertEqual(restored.capture(), NativeRichDraft.from_recovery(
            dict(draft.recovery_payload(), content=valid, blocked_reason=None), data).capture())

    def test_changed_source_revision_or_readonly_metadata_refused(self):
        data, draft = self.draft()
        for kind in ('source', 'revision', 'notes', 'content'):
            changed = copy.deepcopy(data)
            if kind == 'source':
                changed['fdx_document']['source_sha256'] = 'b' * 64
            elif kind == 'revision':
                changed['revision'] = changed['fdx_document']['document_sha256'] = 'b' * 64
            elif kind == 'notes':
                changed['fdx_document']['blocks'][0]['notes'][0]['text'] = 'Changed'
            else:
                changed['content'] += '\n'
            with self.subTest(kind=kind), self.assertRaises(RichDraftError):
                NativeRichDraft.from_recovery(draft.recovery_payload(), changed)

    def test_tampered_head_document_spans_operations_and_text_refused(self):
        data, draft = self.draft()
        for kind in ('document', 'span', 'operations', 'content', 'head', 'unknown'):
            value = draft.recovery_payload()
            if kind == 'document': value['fdx_document']['blocks'][0]['runs'][0]['text'] = 'Injected'
            elif kind == 'span': value['projection_spans'][0]['end'] += 1
            elif kind == 'operations': value['operations'][0][1]['text'] = 'Injected'
            elif kind == 'content': value['content'] += 'Injected'
            elif kind == 'head': value['history_head'] = True
            else: value['unknown'] = 'field'
            with self.subTest(kind=kind), self.assertRaises(RichDraftError):
                NativeRichDraft.from_recovery(value, data)

    def test_dormant_branch_is_replayed_and_tamper_refused(self):
        data, draft = self.draft()
        draft.edit(data['content'])
        draft.edit(data['content'].replace('Hello.', 'Welcome.'))
        for kind in ('cycle', 'before', 'id', 'paragraph', 'range', 'newline'):
            value = draft.recovery_payload()
            row = value['history_nodes'][1]
            if kind == 'cycle': row['parent'] = 1
            elif kind == 'before': row['operation'][1]['before_text'] = 'wrong'
            elif kind == 'id': row['operation'][1]['id'] = 'not-an-id'
            elif kind == 'paragraph': row['operation'][0] = 'unknown'
            elif kind == 'range': row['operation'][1]['start'] = True
            else: row['operation'][1]['text'] = '\n'
            with self.subTest(kind=kind), self.assertRaises(RichDraftError):
                NativeRichDraft.from_recovery(value, data)

    def test_committed_undo_remains_blocked_after_recovery(self):
        data, draft = self.draft()
        submitted = draft.capture()
        saved = acknowledged(data, submitted)
        draft.acknowledge(saved, submitted)
        draft.edit(data['content'])
        restored = NativeRichDraft.from_recovery(draft.recovery_payload(), saved)
        self.assertEqual(restored.recovery_payload(), draft.recovery_payload())
        with self.assertRaises(RichDraftError): restored.capture()

    def test_invalid_root_and_oversized_payload_refused(self):
        data, draft = self.draft()
        for bad in (None, [], {}, dict(draft.recovery_payload(), content='x' * (16 * 1024 * 1024))):
            with self.assertRaises(RichDraftError): NativeRichDraft.from_recovery(bad, data)

    def test_initial_block_without_edit_operations_keeps_exact_metadata(self):
        data = fixture()
        for block in data['fdx_document']['blocks']: del block['edit_operations']
        draft = NativeRichDraft(data)
        draft.edit(data['content'].replace('🐈', '🐕'))
        draft.edit(data['content'])
        draft.edit(data['content'].replace('Hello.', 'Welcome.'))
        restored = NativeRichDraft.from_recovery(draft.recovery_payload(), data)
        self.assertEqual(restored.recovery_payload(), draft.recovery_payload())

    def test_linear_history_exceeding_python_recursion_depth(self):
        data = fixture([('b1', 'Action', 'x')])
        draft = NativeRichDraft(data)
        for index in range(1050):
            draft._apply('b1', dict(id=f'{index:032x}', before_text=draft.document['blocks'][0]['text'],
                                    start=0, end=1, text=chr(0x400 + index)))
        restored = NativeRichDraft.from_recovery(draft.recovery_payload(), data)
        self.assertEqual(restored.recovery_payload(), draft.recovery_payload())
        restored.edit(data['content'])
        self.assertEqual(restored.capture(), data['fdx_document'])

    def test_editor_sequence_codepoints_reproduce_current_branch_without_mutation(self):
        data, draft = self.draft()
        abandoned = draft.content
        draft.edit(data['content'])
        draft.edit(data['content'].replace('Hello.', 'Welcome 🐾.'))
        draft.edit(draft.content.replace('🐈', '🐕'))
        before = draft.recovery_payload()
        restored = NativeRichDraft.from_recovery(before, data)
        baseline, edits = restored.recovery_edit_sequence()
        self.assertEqual(baseline, data['content'])
        self.assertEqual(len(edits), 2)
        content = baseline
        states = [content]
        for start, end, replacement in edits:
            content = content[:start] + replacement + content[end:]
            states.append(content)
        self.assertEqual(content, restored.content)
        self.assertNotIn(abandoned, states)
        self.assertEqual(restored.recovery_payload(), before)
        for state in reversed(states[:-1]):
            restored.edit(state)
            self.assertIsNone(restored.blocked_reason)
        self.assertEqual(restored.capture(), data['fdx_document'])

    def test_blocked_editor_sequence_retains_full_projection_as_final_undoable_edit(self):
        data, draft = self.draft()
        valid = draft.content
        draft.edit(valid + '\nNew structural paragraph 🐾')
        baseline, edits = draft.recovery_edit_sequence()
        self.assertEqual(len(edits), 2)
        content = baseline
        for start, end, replacement in edits:
            content = content[:start] + replacement + content[end:]
        self.assertEqual(content, draft.content)
        self.assertEqual(edits[-1], (0, len(valid), draft.content))
        with self.assertRaises(RichDraftError): draft.capture()


if __name__ == '__main__':
    unittest.main()
