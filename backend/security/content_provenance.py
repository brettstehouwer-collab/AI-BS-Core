"""Pure provenance data for trusted ingress adapters; no authorization or I/O.

IngressMetadata must come from verified application metadata, never a body,
model, request-claimed owner, or deserialized document label. Python types are
not authentication. Integration with actual identity/policy boundaries remains
required before using this dormant component in production.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re

MAX_CONTENT_BYTES = 1024 * 1024
MAX_PARENTS = 16
MAX_SOURCES = 64
MAX_TRANSFORMS = 8


class ProvenanceError(ValueError):
    pass


class SourceKind(str,Enum):
    USER_REQUEST='user_request'
    APPLICATION_POLICY='application_policy'
    DOCUMENT='document'
    TOOL_RESULT='tool_result'
    BROWSER_CONTENT='browser_content'
    SCREENSHOT='screenshot'
    OCR='ocr'
    RAG_RECORD='rag_record'
    MEMORY='memory'
    GENERATED_SUMMARY='generated_summary'
    UNKNOWN='unknown'


class Trust(str,Enum):
    UNTRUSTED='untrusted'
    USER_INTENT='user_intent'
    QUARANTINED='quarantined'


class Use(str,Enum):
    INSPECT='inspect'
    DISPLAY='display'
    CONTEXT='model_context'
    ARCHIVE='archive'


class Transformation(str,Enum):
    SUMMARIZE='summarize'
    RETRIEVE='retrieve'
    NORMALIZE='normalize'
    QUARANTINE='quarantine'


def _identifier(value, optional=False):
    if value is None and optional: return
    if (not isinstance(value,str) or not value or len(value)>256
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ProvenanceError('Invalid or excessive provenance identifier')


@dataclass(frozen=True)
class IngressMetadata:
    source_id: str
    owner: str | None
    kind: SourceKind
    permitted_uses: frozenset[Use]

    def __post_init__(self):
        _identifier(self.source_id)
        _identifier(self.owner,optional=True)
        if not isinstance(self.kind,SourceKind) or self.kind==SourceKind.APPLICATION_POLICY:
            raise ProvenanceError('Policy must use its dedicated trusted configuration path')
        if (not isinstance(self.permitted_uses,frozenset) or Use.INSPECT not in self.permitted_uses
                or any(not isinstance(x,Use) for x in self.permitted_uses)):
            raise ProvenanceError('Invalid permitted uses')
        if self.kind==SourceKind.USER_REQUEST and self.owner is None:
            raise ProvenanceError('User intent needs verified ingress ownership')


def _digest(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):
        raise ProvenanceError('Invalid provenance digest')


@dataclass(frozen=True)
class SourceRecord(IngressMetadata):
    content_sha256: str

    def __post_init__(self):
        super().__post_init__()
        _digest(self.content_sha256)


@dataclass(frozen=True)
class LineageStep:
    operation: Transformation
    input_fingerprints: tuple[str,...]
    output_sha256: str

    def __post_init__(self):
        if (not isinstance(self.operation,Transformation)
                or not isinstance(self.input_fingerprints,tuple)
                or not 1<=len(self.input_fingerprints)<=MAX_PARENTS):
            raise ProvenanceError('Invalid lineage step')
        for value in self.input_fingerprints: _digest(value)
        _digest(self.output_sha256)

    @property
    def step_id(self):
        return hashlib.sha256(json.dumps([self.operation.value,self.input_fingerprints,
            self.output_sha256],separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class Provenance:
    content_sha256: str
    owner: str | None
    trust: Trust
    permitted_uses: frozenset[Use]
    sources: tuple[SourceRecord,...]
    transformations: tuple[LineageStep,...] = ()

    @property
    def grants_execution_authority(self):
        return False


@dataclass(frozen=True)
class ContentEnvelope:
    content: bytes
    provenance: Provenance


def _bytes(content):
    if not isinstance(content,(str,bytes)):
        raise ProvenanceError('Content must be text or immutable bytes')
    if len(content)>MAX_CONTENT_BYTES:
        raise ProvenanceError('Content exceeds the inspection budget')
    try:
        encoded=content.encode('utf-8') if isinstance(content,str) else content
    except UnicodeError:
        raise ProvenanceError('Content encoding could not be inspected') from None
    if len(encoded)>MAX_CONTENT_BYTES:
        raise ProvenanceError('Encoded content exceeds the inspection budget')
    return encoded


def ingest(content, *, metadata=None):
    raw=_bytes(content)
    if metadata is not None and type(metadata) is not IngressMetadata:
        raise ProvenanceError('Use verified application ingress metadata, not content claims')
    digest=hashlib.sha256(raw).hexdigest()
    if metadata is None:
        metadata=IngressMetadata('unattributed:'+digest,None,SourceKind.UNKNOWN,frozenset({Use.INSPECT}))
    trust=(Trust.USER_INTENT if metadata.kind==SourceKind.USER_REQUEST else Trust.UNTRUSTED)
    uses=(metadata.permitted_uses if metadata.owner is not None and metadata.kind!=SourceKind.UNKNOWN
          else frozenset({Use.INSPECT}))
    source=SourceRecord(metadata.source_id,metadata.owner,metadata.kind,metadata.permitted_uses,digest)
    return ContentEnvelope(raw,Provenance(digest,metadata.owner,trust,uses,(source,)))


def _validated(envelope):
    if type(envelope) is not ContentEnvelope or type(envelope.provenance) is not Provenance:
        raise ProvenanceError('An attributed content envelope is required')
    p=envelope.provenance
    if (not isinstance(envelope.content,bytes) or len(envelope.content)>MAX_CONTENT_BYTES
            or hashlib.sha256(envelope.content).hexdigest()!=p.content_sha256
            or not isinstance(p.trust,Trust) or not isinstance(p.sources,tuple)
            or not p.sources or len(p.sources)>MAX_SOURCES
            or not isinstance(p.transformations,tuple) or len(p.transformations)>MAX_TRANSFORMS
            or any(type(s) is not SourceRecord for s in p.sources)
            or any(type(t) is not LineageStep for t in p.transformations)
            or not isinstance(p.permitted_uses,frozenset)
            or any(not isinstance(u,Use) for u in p.permitted_uses)):
        raise ProvenanceError('Content provenance is invalid')
    owners={s.owner for s in p.sources}
    allowed=frozenset.intersection(*(s.permitted_uses for s in p.sources))
    if len(owners)!=1 or p.owner!=next(iter(owners)) or not p.permitted_uses<=allowed:
        raise ProvenanceError('Source restrictions or ownership were changed')
    if p.trust==Trust.USER_INTENT and (p.transformations or any(s.kind!=SourceKind.USER_REQUEST for s in p.sources)):
        raise ProvenanceError('Derived or external data cannot be promoted to user intent')
    if (p.owner is None or any(s.kind==SourceKind.UNKNOWN for s in p.sources)) and p.permitted_uses!=frozenset({Use.INSPECT}):
        raise ProvenanceError('Unattributed data must remain inspection-only')
    if p.trust==Trust.QUARANTINED and p.permitted_uses!=frozenset({Use.INSPECT}):
        raise ProvenanceError('Quarantined data must remain inspection-only')
    if any(t.operation==Transformation.QUARANTINE for t in p.transformations) and p.trust!=Trust.QUARANTINED:
        raise ProvenanceError('Quarantine history cannot be removed by a trust label')
    return p


def _fingerprint(p):
    data=[p.content_sha256,p.owner,p.trust.value,sorted(u.value for u in p.permitted_uses),
          [[s.source_id,s.owner,s.kind.value,sorted(u.value for u in s.permitted_uses),
            s.content_sha256] for s in p.sources], [t.step_id for t in p.transformations]]
    return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()


def derive(content, parents, *, operation):
    if (not isinstance(parents,(tuple,list)) or not 1<=len(parents)<=MAX_PARENTS
            or not isinstance(operation,Transformation)):
        raise ProvenanceError('A bounded, typed transformation needs its parents')
    raw=_bytes(content)
    inputs=[_validated(e) for e in parents]
    owners={p.owner for p in inputs}
    if len(owners)!=1:
        raise ProvenanceError('Cross-owner derivation requires a separate authorized workflow')
    sources=[]
    for p in inputs:
        for source in p.sources:
            existing=next((s for s in sources if s.source_id==source.source_id),None)
            if existing is not None and existing!=source:
                raise ProvenanceError('Conflicting source identity')
            if existing is None: sources.append(source)
    history=[]
    for p in inputs:
        for step in p.transformations:
            if step not in history: history.append(step)
    if len(sources)>MAX_SOURCES or len(history)>=MAX_TRANSFORMS:
        raise ProvenanceError('Provenance lineage exceeds its bounded budget')
    uses=frozenset.intersection(*(p.permitted_uses for p in inputs))
    trust=(Trust.QUARANTINED if operation==Transformation.QUARANTINE
           or any(p.trust==Trust.QUARANTINED for p in inputs) else Trust.UNTRUSTED)
    if trust==Trust.QUARANTINED: uses=frozenset({Use.INSPECT})
    digest=hashlib.sha256(raw).hexdigest()
    step=LineageStep(operation,tuple(_fingerprint(p) for p in inputs),digest)
    return ContentEnvelope(raw,Provenance(digest,next(iter(owners)),
        trust,uses,tuple(sources),tuple(history)+(step,)))


def quarantine(envelope):
    _validated(envelope)
    return derive(envelope.content,(envelope,),operation=Transformation.QUARANTINE)
