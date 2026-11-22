"""Native text edits mapped to the owner-checked rich document's literal spans.

The projection is not the master document. Unknown XML and styled runs remain
server-owned; only evidenced edits within an existing body paragraph are sent.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid

MAX_RICH_FIELD_BYTES=16*1024*1024
MAX_BYTES=MAX_RICH_FIELD_BYTES  # Retained public field/history limit.
MAX_RECOVERY_FILE_BYTES=32*1024*1024
MAX_RECOVERY_REPLAY_BYTES=64*1024*1024


class RichDraftError(ValueError):
    pass


def _copy(value, *, limit=MAX_BYTES):
    try:
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8')
        if len(raw)>limit:raise ValueError('large')
        return json.loads(raw)
    except (TypeError,ValueError,UnicodeError,RecursionError,OverflowError):
        raise RichDraftError('The rich document snapshot is invalid or oversized. The existing draft was retained.') from None


class NativeRichDraft:
    def __init__(self,data):
        if not isinstance(data,dict) or any(not isinstance(key,str) for key in data):
            raise RichDraftError('The rich document response must be a project snapshot.')
        # Confirmed responses contain the same text in independent bounded
        # document, projection and content fields. Bound each field (and all
        # remaining metadata together) rather than rejecting their duplication.
        fields={'fdx_document','projection_spans','content'}
        value=_copy({key:part for key,part in data.items() if key not in fields})
        value.update({key:_copy(data.get(key)) for key in fields})
        document=value.get('fdx_document');content=value.get('content');revision=value.get('revision')
        spans=value.get('projection_spans')
        if (not isinstance(document,dict) or document.get('schema')!='aibs_rich_fdx_v1'
                or not isinstance(content,str) or not isinstance(revision,str) or not re.fullmatch('[a-f0-9]{64}',revision)
                or document.get('document_sha256')!=revision
                or not isinstance(document.get('source_sha256'),str)
                or not re.fullmatch('[a-f0-9]{64}',document['source_sha256'])
                or not isinstance(document.get('blocks'),list) or not isinstance(spans,list)
                or len(spans)!=len(document['blocks']) or len(spans)>50000):
            raise RichDraftError('Reload the project with its confirmed rich document and body spans before editing.')
        previous=0;identifiers=set()
        for block,span in zip(document['blocks'],spans):
            if not isinstance(block,dict) or not isinstance(span,dict):raise RichDraftError('Invalid rich body span.')
            start,end=span.get('start'),span.get('end');identifier=block.get('id')
            if (not isinstance(identifier,str) or not identifier or identifier in identifiers
                    or not isinstance(block.get('type'),str)
                    or span.get('id')!=identifier or span.get('type')!=block.get('type')
                    or type(start)is not int or type(end)is not int or not previous<=start<=end<=len(content)
                    or not isinstance(block.get('text'),str) or span.get('text')!=block['text']
                    or content[start:end]!=block['text'] or block.get('edit_operations') not in (None,[])):
                raise RichDraftError('The rich document projection changed. Existing text and metadata were retained.')
            previous=end;identifiers.add(identifier)
        self.document=document;self.projection_spans=spans;self.revision=revision
        self.content=self._valid_content=content;self.blocked_reason=None;self.operations=[]
        self._history_base={'fdx_document':copy.deepcopy(document),'projection_spans':copy.deepcopy(spans),
                            'content':content,'revision':revision}
        self._history_nodes=[{'parent':None,'operation':None}]
        self._history_by_hash={self._content_hash(content):0};self._history_head=0;self._history_bytes=0
        self._committed_history_hashes=set()

    @staticmethod
    def _content_hash(content):return hashlib.sha256(content.encode('utf-8',errors='strict')).hexdigest()

    def _restore_known_content(self,content):
        key=self._content_hash(content)
        if key not in self._history_by_hash:
            if key in self._committed_history_hashes:
                self.content=content
                self.blocked_reason='Undo crosses a committed rich version. Your text is retained; use a separate text working copy or reopen the confirmed version to preserve original styles.'
                return True
            return False
        head=self._history_by_hash[key];path=[];node=head
        while node:
            row=self._history_nodes[node];path.append(row['operation']);node=row['parent']
        fresh=NativeRichDraft(self._history_base)
        for identifier,operation in reversed(path):fresh._apply(identifier,operation,remember=False)
        if fresh.content!=content:raise RichDraftError('The retained undo state no longer matches this draft.')
        for field in ('document','projection_spans','content','_valid_content','operations'):
            setattr(self,field,getattr(fresh,field))
        self._history_head=head;self.blocked_reason=None
        return True

    def _apply(self,identifier,operation,*,remember=True):
        block=next((row for row in self.document['blocks'] if row['id']==identifier),None)
        span=next((row for row in self.projection_spans if row['id']==identifier),None)
        if not block or not span or block.get('editable') is not True:
            raise RichDraftError('This paragraph is not available for native rich text edits. Preserve a separate working copy.')
        start,end=operation.get('start'),operation.get('end');replacement=operation.get('text')
        if (operation.get('before_text')!=block['text'] or type(start)is not int or type(end)is not int
                or not 0<=start<=end<=len(block['text']) or not isinstance(replacement,str)
                or len(block.get('edit_operations',[]))>=4096):
            raise RichDraftError('The rich edit no longer matches its acknowledged paragraph. Retain this draft and reload.')
        text=block['text'][:start]+replacement+block['text'][end:]
        old_end=span['end'];delta=len(text)-len(block['text'])
        content=self._valid_content[:span['start']]+text+self._valid_content[old_end:]
        # Qualify the next typed snapshot before mutating the recoverable version.
        proposed=copy.deepcopy(self.document)
        proposed_block=next(row for row in proposed['blocks'] if row['id']==identifier)
        proposed_block['text']=text;proposed_block.setdefault('edit_operations',[]).append(copy.deepcopy(operation))
        _copy(proposed)
        history_size=len(json.dumps([identifier,operation],ensure_ascii=False).encode('utf-8'))
        if remember and (len(self._history_nodes)>=4097 or self._history_bytes+history_size>MAX_BYTES):
            raise RichDraftError('The retained rich undo history is full. Save/reopen a confirmed version or preserve a separate working copy; your full text is retained.')
        block['text']=text;block.setdefault('edit_operations',[]).append(copy.deepcopy(operation))
        span['text']=text;span['end']+=delta
        for other in self.projection_spans:
            if other is not span and other['start']>=old_end:
                other['start']+=delta;other['end']+=delta
        self.operations.append((identifier,copy.deepcopy(operation)))
        self.content=self._valid_content=content
        if remember:
            self._history_nodes.append({'parent':self._history_head,'operation':[identifier,copy.deepcopy(operation)]})
            self._history_head=len(self._history_nodes)-1;self._history_bytes+=history_size
            self._history_by_hash[self._content_hash(content)]=self._history_head

    def edit(self,new_content):
        if not isinstance(new_content,str):raise RichDraftError('Screenplay text must be Unicode text.')
        if new_content==self.content:return
        if self.blocked_reason:
            self.content=new_content
            if new_content==self._valid_content:self.blocked_reason=None
            return
        try:
            if self._restore_known_content(new_content):return
        except UnicodeError:
            self.content=new_content;self.blocked_reason='The edited text is not valid Unicode.';return
        before=self._valid_content;start=0
        while start<min(len(before),len(new_content)) and before[start]==new_content[start]:start+=1
        suffix=0
        while suffix<min(len(before)-start,len(new_content)-start) and before[-suffix-1]==new_content[-suffix-1]:suffix+=1
        end=len(before)-suffix;replacement=new_content[start:len(new_content)-suffix if suffix else len(new_content)]
        matches=[span for span in self.projection_spans if span['start']<=start<=end<=span['end']]
        try:
            replacement.encode('utf-8',errors='strict')
            # Plain text alone cannot locate a repeated styled deletion or
            # insertion. UI edits use edit_utf16 instead; transformations without
            # an exact range must not guess which run the author changed.
            if start and before[:start-1]+new_content[start-1:start-1+len(replacement)]+before[end-1:]==new_content:
                raise RichDraftError('This repeated-text edit needs its exact editor range to preserve styles. Your full draft is retained.')
            if (len(matches)!=1 or '\n' in replacement or '\r' in replacement
                    or '\n' in before[start:end] or '\r' in before[start:end]):
                raise RichDraftError('This change crosses rich paragraph or title boundaries. Your full draft is retained; use a separate working copy for structural edits.')
            span=matches[0];block=next(row for row in self.document['blocks'] if row['id']==span['id'])
            operation=dict(id=uuid.uuid4().hex,before_text=block['text'],start=start-span['start'],end=end-span['start'],text=replacement)
            self._apply(block['id'],operation)
            if self.content!=new_content:raise RichDraftError('The native edit did not match the document projection.')
        except (RichDraftError,UnicodeError) as error:
            self.content=new_content;self.blocked_reason=str(error)

    def edit_utf16(self,position,removed,added,new_content):
        """Apply the exact QTextDocument contentsChange range (UTF-16 units)."""
        if new_content==self.content:return
        if self.blocked_reason:
            self.edit(new_content);return
        before=self._valid_content
        try:
            if self._restore_known_content(new_content):return
            if any(type(value)is not int or value<0 for value in (position,removed,added)):
                raise RichDraftError('Invalid native editor change range.')
            old=before.encode('utf-16-le');new=new_content.encode('utf-16-le')
            if position+removed>len(old)//2 or position+added>len(new)//2:
                raise RichDraftError('The editor range does not match the retained document.')
            start=len(old[:position*2].decode('utf-16-le'))
            end=len(old[:(position+removed)*2].decode('utf-16-le'))
            replacement=new[position*2:(position+added)*2].decode('utf-16-le')
            replacement.encode('utf-8',errors='strict')
            if before[:start]+replacement+before[end:]!=new_content:
                raise RichDraftError('The exact editor range does not reproduce this draft.')
            matches=[span for span in self.projection_spans if span['start']<=start<=end<=span['end']]
            if (len(matches)!=1 or any(c in replacement+before[start:end] for c in '\r\n')):
                raise RichDraftError('This change crosses rich paragraph/title boundaries. Preserve a separate text working copy.')
            span=matches[0];block=next(row for row in self.document['blocks'] if row['id']==span['id'])
            self._apply(block['id'],dict(id=uuid.uuid4().hex,before_text=block['text'],
                start=start-span['start'],end=end-span['start'],text=replacement))
        except (RichDraftError,UnicodeError) as error:
            self.content=new_content;self.blocked_reason=str(error)

    def capture(self):
        if self.blocked_reason:raise RichDraftError(self.blocked_reason)
        return _copy(self.document)

    def acknowledge(self,data,submitted_document):
        """Adopt the acknowledged version and replay only later local operations."""
        submitted=_copy(submitted_document);fresh=NativeRichDraft(data)
        if (not isinstance(submitted,dict) or not isinstance(submitted.get('blocks'),list)
                or any(not isinstance(row,dict) for row in submitted['blocks'])):
            raise RichDraftError('The submitted rich snapshot is invalid.')
        old_ids=[row['id'] for row in self.document['blocks']]
        if (fresh.document['source_sha256']!=self.document['source_sha256']
                or [row['id'] for row in fresh.document['blocks']]!=old_ids
                or [row['id'] for row in submitted.get('blocks',[])]!=old_ids
                or any(old['type']!=new['type'] or old['text']!=new['text']
                       for old,new in zip(submitted['blocks'],fresh.document['blocks']))):
            raise RichDraftError('The saved rich acknowledgment does not match the submitted document. Your local draft was retained.')
        for key in set(self.document)-{'blocks','document_sha256','applied_operation_ids'}:
            if fresh.document.get(key)!=self.document[key]:
                raise RichDraftError('Readonly rich metadata changed during save. Your complete local draft was retained.')
        for old,new in zip(self.document['blocks'],fresh.document['blocks']):
            if {k:v for k,v in old.items() if k not in {'text','runs','edit_operations'}} != {k:v for k,v in new.items() if k not in {'text','runs','edit_operations'}}:
                raise RichDraftError('Readonly paragraph metadata changed during save. Your complete local draft was retained.')
        covered={op['id'] for row in submitted['blocks'] for op in row.get('edit_operations',[])}
        for identifier,operation in self.operations:
            if operation['id'] not in covered:fresh._apply(identifier,operation)
        if self.blocked_reason:
            fresh.content=self.content;fresh.blocked_reason=self.blocked_reason
        elif fresh.content!=self.content:
            raise RichDraftError('Newer local rich edits could not be reconciled. Your complete draft was retained.')
        fresh._committed_history_hashes=(self._committed_history_hashes|set(self._history_by_hash))-set(fresh._history_by_hash)
        self.__dict__.update(fresh.__dict__)

    def recovery_payload(self, *, compact=False):
        if compact:
            return dict(format='aibs_rich_history_v1', content=self.content, revision=self.revision,
                        base_sha256=hashlib.sha256(json.dumps(self._history_base, ensure_ascii=False,
                            sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest(),
                        blocked_reason=self.blocked_reason, history_nodes=copy.deepcopy(self._history_nodes),
                        history_head=self._history_head,
                        committed_history_hashes=sorted(self._committed_history_hashes))
        return dict(content=self.content,revision=self.revision,fdx_document=_copy(self.document),
                    projection_spans=_copy(self.projection_spans),blocked_reason=self.blocked_reason,
                    operations=_copy(self.operations),history_base=copy.deepcopy(self._history_base),
                    history_nodes=copy.deepcopy(self._history_nodes),history_head=self._history_head,
                    committed_history_hashes=sorted(self._committed_history_hashes))

    def recovery_edit_sequence(self):
        """Return validated codepoint edits for rebuilding the editor's undo stack.

        Only the current history branch is linearized. Each edit is an absolute
        ``(start, end, replacement)`` in the text produced by preceding edits.
        Unsupported structural text remains a final undoable projection edit;
        it never becomes an authorized rich document operation.
        """
        validated = type(self).from_recovery(self.recovery_payload(compact=True), self._history_base)
        ancestry = []
        node = validated._history_head
        while node:
            row = validated._history_nodes[node]
            ancestry.append(row['operation'])
            node = row['parent']
        fresh = type(self)(validated._history_base)
        baseline = fresh.content
        sequence = []
        for identifier, operation in reversed(ancestry):
            span = next(item for item in fresh.projection_spans if item['id'] == identifier)
            sequence.append((span['start'] + operation['start'],
                             span['start'] + operation['end'], operation['text']))
            fresh._apply(identifier, operation, remember=False)
        if fresh.content != validated._valid_content:
            raise RichDraftError('The recovery editor sequence does not match the retained rich history.')
        if validated.content != fresh.content:
            if not validated.blocked_reason:
                raise RichDraftError('The recovery editor text has no qualified rich history.')
            sequence.append((0, len(fresh.content), validated.content))
        return baseline, sequence

    @classmethod
    def from_recovery(cls, payload, confirmed_data, *, allow_large_legacy=False):
        """Rebuild local edits from a freshly confirmed, unchanged host version.

        The caller separately verifies the private file and owner/project scope.
        Persisted document metadata is never trusted: every retained branch is
        replayed from the confirmed source, then compared with the saved head.
        """
        large_legacy = False
        try:
            value = _copy(payload)
        except RichDraftError:
            if not allow_large_legacy or not isinstance(payload, dict) or 'format' in payload:
                raise
            # Only the caller's already bounded32MiB private file may use this
            # compatibility path. Every field and derived state stays bounded.
            value = _copy(payload, limit=MAX_RECOVERY_FILE_BYTES)
            value = {key: _copy(part) for key, part in value.items()}
            large_legacy = True
        compact = isinstance(value, dict) and value.get('format') == 'aibs_rich_history_v1'
        expected = {'content', 'revision', 'fdx_document', 'projection_spans',
                    'blocked_reason', 'operations', 'history_base', 'history_nodes',
                    'history_head', 'committed_history_hashes'}
        fail = 'The recovery rich history does not match the confirmed project. Existing work was retained.'
        if compact:
            expected = {'format', 'content', 'revision', 'base_sha256', 'blocked_reason',
                        'history_nodes', 'history_head', 'committed_history_hashes'}
        if not isinstance(value, dict) or set(value) != expected:
            raise RichDraftError(fail)
        fresh = cls(confirmed_data)
        base_matches = (value['base_sha256'] == fresh.recovery_payload(compact=True)['base_sha256']
                        if compact else value['history_base'] == fresh._history_base)
        if value['revision'] != fresh.revision or not base_matches:
            raise RichDraftError(fail)
        nodes, head = value['history_nodes'], value['history_head']
        committed, blocked = value['committed_history_hashes'], value['blocked_reason']
        if (not isinstance(nodes, list) or not 1 <= len(nodes) <= 4097
                or nodes[0] != {'parent': None, 'operation': None}
                or type(head) is not int or not 0 <= head < len(nodes)
                or not isinstance(value['content'], str)
                or (blocked is not None and (not isinstance(blocked, str) or not blocked))
                or not isinstance(committed, list) or len(committed) > 50000
                or any(not isinstance(item, str) or not re.fullmatch('[a-f0-9]{64}', item) for item in committed)
                or committed != sorted(set(committed))):
            raise RichDraftError(fail)
        children = [[] for _ in nodes]
        ids = set()
        history_bytes = 0
        for index, row in enumerate(nodes[1:], 1):
            if (not isinstance(row, dict) or set(row) != {'parent', 'operation'}
                    or type(row['parent']) is not int or not 0 <= row['parent'] < index
                    or not isinstance(row['operation'], list) or len(row['operation']) != 2):
                raise RichDraftError(fail)
            identifier, operation = row['operation']
            if (not isinstance(identifier, str) or not isinstance(operation, dict)
                    or set(operation) != {'id', 'before_text', 'start', 'end', 'text'}
                    or not isinstance(operation['id'], str) or not re.fullmatch('[a-f0-9]{32}', operation['id'])
                    or operation['id'] in ids or not isinstance(operation['before_text'], str)
                    or not isinstance(operation['text'], str)
                    or type(operation['start']) is not int or type(operation['end']) is not int
                    or not 0 <= operation['start'] <= operation['end'] <= len(operation['before_text'])
                    or any(c in operation['text'] + operation['before_text'][operation['start']:operation['end']]
                           for c in '\r\n')):
                raise RichDraftError(fail)
            ids.add(operation['id'])
            history_bytes += len(json.dumps(row['operation'], ensure_ascii=False).encode('utf-8'))
            if history_bytes > MAX_BYTES:
                raise RichDraftError(fail)
            children[row['parent']].append(index)

        # Depth-first replay uses reversible edits, avoiding a document copy per
        # retained node and avoiding recursion for long valid edit histories.
        hashes = {fresh._content_hash(fresh.content): 0}
        selected = None
        stack = [(0, False)]
        replay_bytes = 0
        while stack:
            index, leaving = stack.pop()
            if leaving:
                identifier, operation = nodes[index]['operation']
                block = next(row for row in fresh.document['blocks'] if row['id'] == identifier)
                span = next(row for row in fresh.projection_spans if row['id'] == identifier)
                old_end = span['end']
                delta = len(operation['before_text']) - len(block['text'])
                fresh.content = fresh._valid_content = (fresh.content[:span['start']]
                    + operation['before_text'] + fresh.content[old_end:])
                block['text'] = span['text'] = operation['before_text']
                block['edit_operations'].pop()
                if not block['edit_operations'] and 'edit_operations' not in fresh._history_base['fdx_document']['blocks'][
                        next(i for i, row in enumerate(fresh.document['blocks']) if row['id'] == identifier)]:
                    del block['edit_operations']
                span['end'] += delta
                for other in fresh.projection_spans:
                    if other is not span and other['start'] >= old_end:
                        other['start'] += delta
                        other['end'] += delta
                fresh.operations.pop()
                continue
            if index:
                identifier, operation = nodes[index]['operation']
                if compact or large_legacy:
                    replay_bytes += len(json.dumps(fresh.document, ensure_ascii=False).encode('utf-8'))
                    replay_bytes += len(json.dumps(operation, ensure_ascii=False).encode('utf-8'))
                    if replay_bytes > MAX_RECOVERY_REPLAY_BYTES:
                        raise RichDraftError('The recovery history exceeds the bounded replay work limit. Keep the draft open and save a confirmed version.')
                fresh._apply(identifier, operation, remember=False)
                key = fresh._content_hash(fresh.content)
                hashes[key] = max(index, hashes.get(key, 0))
                stack.append((index, True))
            if index == head:
                selected = {key: _copy(part) for key, part in {
                    'fdx_document': fresh.document, 'projection_spans': fresh.projection_spans,
                    'operations': fresh.operations, 'content': fresh.content}.items()} if compact or large_legacy else _copy({
                    'fdx_document': fresh.document, 'projection_spans': fresh.projection_spans,
                    'operations': fresh.operations, 'content': fresh.content})
            stack.extend((child, False) for child in reversed(children[index]))
        if ((not compact and (selected['fdx_document'] != value['fdx_document']
                or selected['projection_spans'] != value['projection_spans']
                or selected['operations'] != value['operations']))
                or (blocked is None and selected['content'] != value['content'])
                or set(committed) & set(hashes)):
            raise RichDraftError(fail)
        fresh.document = selected['fdx_document']
        fresh.projection_spans = selected['projection_spans']
        fresh.operations = [(identifier, operation) for identifier, operation in selected['operations']]
        fresh._valid_content = selected['content']
        fresh.content = value['content']
        fresh.blocked_reason = blocked
        fresh._history_nodes = nodes
        fresh._history_head = head
        fresh._history_by_hash = hashes
        fresh._history_bytes = history_bytes
        fresh._committed_history_hashes = set(committed)
        return fresh
