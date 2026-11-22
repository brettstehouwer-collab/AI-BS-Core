"""Pure joint context admission; preserve authored input and source evidence."""
from __future__ import annotations
import hashlib

CORE_EVIDENCE = (
    'CODEBASE EVIDENCE: Use actual supplied or retrieved source and its provenance. Do not claim complete codebase knowledge or that uninspected files were read.\n'
    'DATABASE EVIDENCE: AI-BS retains multiple stores. Establish current schema, ownership and coverage from actual read-only evidence; never assume all stores were consolidated or invent fixed table/row counts. The architectural ledger is a Markdown record, not a database.\n'
    'DOCUMENT ANALYSIS CAPABILITY: When provided with attached files or indexed document chapters, analyze them thoroughly with high precision. '
    "Cite specific chapters, verses, lines, or sections directly. If the document is large and indexed, address the user's focus immediately and invite them to explore any specific chapter.\n"
)
TOOL_BOUNDARY = ('\nGenerated text is not tool execution. Report host actions only from actual returned tool receipts; '
                 'approved local, cloud, API and WebView capabilities retain their own backend contracts.')


class ChatContextBudgetError(ValueError):
    def __init__(self, code, receipt=None):
        self.code, self.receipt = code, receipt or {}
        super().__init__('Chat context admission failed: ' + code)


def _raw(text):
    if not isinstance(text, str):
        raise ChatContextBudgetError('invalid_context_input')
    try:
        return text.encode('utf-8', errors='strict')
    except UnicodeError:
        raise ChatContextBudgetError('invalid_unicode') from None


def plan_chat_context(prompt, mandatory_system, optional_blocks=(), *, mandatory_source='',
                      mandatory_suffix='',
                      num_ctx=8192, output_tokens=1024, framing_reserve=512):
    """Admit whole optional blocks in caller order under the unchanged guard.

    No request/history/source slicing, summarization, model changes or I/O.
    Receipt contains labels, lengths and hashes, never the context text.
    """
    for value, low, high in ((num_ctx, 1, 32768), (output_tokens, 1, 8192),
                             (framing_reserve, 0, 8192)):
        if type(value) is not int or not low <= value <= high:
            raise ChatContextBudgetError('invalid_context_limit')
    prompt_raw, system_raw, source_raw = _raw(prompt), _raw(mandatory_system), _raw(mandatory_source)
    suffix_raw = _raw(mandatory_suffix)
    system = mandatory_system + ('\n\n' + mandatory_source if mandatory_source else '')
    current_bytes = len(prompt_raw) + len(_raw(system)) + len(suffix_raw)
    maximum_input = num_ctx - output_tokens - framing_reserve
    receipt = {'schema': 'aibs.chat_context_selection.v1', 'policy': 'whole_optional_blocks_v1',
               'num_ctx': num_ctx, 'output_tokens': output_tokens, 'framing_reserve': framing_reserve,
               'maximum_input_utf8_bytes': maximum_input, 'mandatory_input_utf8_bytes': current_bytes,
               'prompt_utf8_bytes': len(prompt_raw), 'prompt_sha256': hashlib.sha256(prompt_raw).hexdigest(),
               'mandatory_system_utf8_bytes': len(system_raw), 'mandatory_source_utf8_bytes': len(source_raw),
               'mandatory_suffix_utf8_bytes': len(suffix_raw),
               'mandatory_source_sha256': hashlib.sha256(source_raw).hexdigest() if source_raw else None,
               'authored_input_preserved': True, 'mandatory_source_preserved': True,
               'optional_blocks': [], 'omitted_labels': []}
    if current_bytes > maximum_input:
        receipt.update(status='mandatory_over_budget', admitted_input_utf8_bytes=current_bytes,
                       rejection_stage='mandatory_admission', over_budget_utf8_bytes=current_bytes - maximum_input)
        raise ChatContextBudgetError('context_budget_exceeded', receipt)
    seen = set()
    for label, text in optional_blocks:
        if (not isinstance(label, str) or not label or len(label) > 100 or label in seen
                or any(ord(c) < 32 for c in label)):
            raise ChatContextBudgetError('invalid_context_block')
        seen.add(label)
        raw = _raw(text)
        row = {'label': label, 'utf8_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if not text:
            row['status'] = 'empty'
        elif current_bytes + 2 + len(raw) <= maximum_input:
            system += '\n\n' + text
            current_bytes += 2 + len(raw)
            row['status'] = 'admitted_whole'
        else:
            row.update(status='omitted_whole', reason='joint_context_budget')
            receipt['omitted_labels'].append(label)
        receipt['optional_blocks'].append(row)
    receipt.update(status='planned', admitted_input_utf8_bytes=current_bytes)
    return {'prompt': prompt, 'system': system + mandatory_suffix, 'receipt': receipt}
