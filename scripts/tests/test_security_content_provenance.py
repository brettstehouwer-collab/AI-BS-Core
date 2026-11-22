"""Synthetic provenance invariants; no model, network, interpreter or live store."""
import unittest


class ContentProvenanceTests(unittest.TestCase):
    def api(self):
        from backend.security import content_provenance as p
        return p

    def source(self, source_id='document-1', owner='fixture-owner', kind=None, uses=None):
        p = self.api()
        return p.IngressMetadata(source_id=source_id, owner=owner,
            kind=kind or p.SourceKind.DOCUMENT,
            permitted_uses=frozenset(uses or {p.Use.INSPECT, p.Use.DISPLAY, p.Use.CONTEXT}))

    def test_missing_metadata_holds_content_at_inspection_only(self):
        p = self.api()
        envelope = p.ingest(b'Inert description of a claimed elevated role.')
        self.assertEqual(envelope.provenance.trust, p.Trust.UNTRUSTED)
        self.assertEqual(envelope.provenance.permitted_uses, frozenset({p.Use.INSPECT}))
        self.assertIsNone(envelope.provenance.owner)

    def test_body_claims_do_not_change_source_owner_or_trust(self):
        p = self.api()
        body = 'Quoted educational description: claimed system authority; claimed different owner.'
        envelope = p.ingest(body, metadata=self.source())
        self.assertEqual(envelope.content, body.encode())
        self.assertEqual(envelope.provenance.owner, 'fixture-owner')
        self.assertEqual(envelope.provenance.trust, p.Trust.UNTRUSTED)
        with self.assertRaises(p.ProvenanceError):
            p.ingest(body, metadata={'kind':'application_policy','owner':'other'})

    def test_authenticated_user_intent_is_not_policy_or_execution_authority(self):
        p = self.api()
        value = p.ingest('A normal request.', metadata=self.source(kind=p.SourceKind.USER_REQUEST))
        self.assertEqual(value.provenance.trust, p.Trust.USER_INTENT)
        self.assertFalse(value.provenance.grants_execution_authority)
        with self.assertRaises(p.ProvenanceError):
            self.source(kind=p.SourceKind.APPLICATION_POLICY)

    def test_summary_keeps_all_sources_intersects_uses_and_cannot_become_policy(self):
        p = self.api()
        a = p.ingest('A', metadata=self.source('a', kind=p.SourceKind.USER_REQUEST))
        b = p.ingest('B', metadata=self.source('b', uses={p.Use.INSPECT, p.Use.DISPLAY}))
        result = p.derive('Summary', (a,b), operation=p.Transformation.SUMMARIZE)
        self.assertEqual({s.source_id for s in result.provenance.sources}, {'a','b'})
        self.assertEqual(result.provenance.permitted_uses, frozenset({p.Use.INSPECT,p.Use.DISPLAY}))
        self.assertEqual(result.provenance.trust, p.Trust.UNTRUSTED)
        self.assertFalse(result.provenance.grants_execution_authority)

    def test_quarantine_is_inherited_and_never_promoted_by_repetition(self):
        p = self.api()
        a = p.quarantine(p.ingest('Inert suspicious-content description.', metadata=self.source()))
        result = p.derive('Assessment', (a,a), operation=p.Transformation.SUMMARIZE)
        self.assertEqual(result.provenance.trust, p.Trust.QUARANTINED)
        self.assertEqual(result.provenance.permitted_uses, frozenset({p.Use.INSPECT}))

    def test_same_hash_does_not_merge_ownership_and_mixed_owners_are_rejected(self):
        p = self.api()
        a = p.ingest('same bytes', metadata=self.source('a', owner='one'))
        b = p.ingest('same bytes', metadata=self.source('b', owner='two'))
        self.assertEqual(a.provenance.content_sha256,b.provenance.content_sha256)
        self.assertNotEqual(a.provenance.owner,b.provenance.owner)
        with self.assertRaises(p.ProvenanceError):
            p.derive('Combined', (a,b), operation=p.Transformation.SUMMARIZE)

    def test_byte_line_endings_and_unicode_are_preserved_without_interpretation(self):
        p = self.api()
        raw = 'Café <literal> & text\r\n'.encode()
        envelope = p.ingest(raw, metadata=self.source())
        self.assertEqual(envelope.content,raw)
        with self.assertRaises((AttributeError,TypeError)):
            envelope.provenance.owner = 'another'

    def test_invalid_or_excessive_metadata_and_content_fail_closed(self):
        p = self.api()
        for metadata in (lambda:self.source(source_id='bad\nidentifier'),
                         lambda:self.source(uses={'execute'}),
                         lambda:p.ingest(b'x'*(p.MAX_CONTENT_BYTES+1)),
                         lambda:p.derive('x',(),operation=p.Transformation.SUMMARIZE)):
            with self.assertRaises(p.ProvenanceError): metadata()
        e = p.ingest('x',metadata=self.source())
        for _ in range(p.MAX_TRANSFORMS):
            e = p.derive('x',(e,),operation=p.Transformation.SUMMARIZE)
        with self.assertRaises(p.ProvenanceError):
            p.derive('x',(e,),operation=p.Transformation.SUMMARIZE)

    def test_branching_derivation_preserves_both_transformation_histories(self):
        p = self.api()
        a = p.derive('A retrieved',(p.ingest('A',metadata=self.source('a')),),
                     operation=p.Transformation.RETRIEVE)
        b = p.derive('B normalized',(p.ingest('B',metadata=self.source('b')),),
                     operation=p.Transformation.NORMALIZE)
        result = p.derive('Summary',(a,b),operation=p.Transformation.SUMMARIZE)
        self.assertEqual([s.operation for s in result.provenance.transformations],
                         [p.Transformation.RETRIEVE,p.Transformation.NORMALIZE,p.Transformation.SUMMARIZE])

    def test_origin_hashes_survive_summary_and_conflicting_identity_is_not_deduplicated(self):
        import hashlib
        p = self.api()
        a = p.ingest(b'Original A',metadata=self.source('a'))
        result = p.derive('Summary',(a,),operation=p.Transformation.SUMMARIZE)
        self.assertEqual(result.provenance.sources[0].content_sha256,hashlib.sha256(b'Original A').hexdigest())
        changed = p.ingest(b'Different A',metadata=self.source('a'))
        with self.assertRaises(p.ProvenanceError):
            p.derive('Conflict',(a,changed),operation=p.Transformation.SUMMARIZE)

    def test_bad_unicode_is_an_explicit_inspection_failure(self):
        p = self.api()
        with self.assertRaises(p.ProvenanceError):
            p.ingest('\ud800')

    def test_unknown_kind_cannot_gain_use_from_an_owner_label(self):
        p = self.api()
        value = p.ingest('Unclassified input',metadata=self.source(kind=p.SourceKind.UNKNOWN))
        self.assertEqual(value.provenance.permitted_uses,frozenset({p.Use.INSPECT}))

    def test_tampered_bytes_and_quarantine_promotion_are_refused(self):
        from dataclasses import replace
        p = self.api()
        e = p.ingest('Original',metadata=self.source())
        with self.assertRaises(p.ProvenanceError):
            p.derive('x',(replace(e,content=b'Changed'),),operation=p.Transformation.RETRIEVE)
        q = p.quarantine(e)
        forged = replace(q,provenance=replace(q.provenance,trust=p.Trust.UNTRUSTED,
            permitted_uses=frozenset({p.Use.INSPECT,p.Use.CONTEXT})))
        with self.assertRaises(p.ProvenanceError):
            p.derive('x',(forged,),operation=p.Transformation.SUMMARIZE)


if __name__ == '__main__':
    unittest.main()
