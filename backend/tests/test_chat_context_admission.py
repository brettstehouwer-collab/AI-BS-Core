"""Regression tests: context admission, history selection and history metadata isolation.

Source-level tests on isolated synthetic fixtures. They do not call Ollama, the
network, or the vault database, and they never mutate stored conversations.
"""
import copy
import json
import os
import sys

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from core.chat_context_budget import (CORE_EVIDENCE, TOOL_BOUNDARY, ChatContextBudgetError,
                                      plan_chat_context)
from core.local_chat_inference import (_MetadataEscaper, conversation_prompt, metadata_chunk)
from core.pipeline_context_injector import AIBS_SOVEREIGN_SYSTEM_PROMPT, disambiguate_prompt_text
from core.sovereign_reasoning.dispatcher import _select_history_prompt, inject_safety_directive

NUM_CTX, OUT, FRAME = 8192, 1024, 512
MAX_INPUT = NUM_CTX - OUT - FRAME  # 6656
MANDATORY_SYSTEM = inject_safety_directive(AIBS_SOVEREIGN_SYSTEM_PROMPT + '\n\n' + CORE_EVIDENCE)
FIXED = len(MANDATORY_SYSTEM.encode()) + len(TOOL_BOUNDARY.encode())
ERROR_TEXT = ('Error in sovereign reasoning matrix: Local inference context_budget_exceeded. '
              'No source was truncated or alternative model selected.')


def sized(n, ch='x'):
    return (ch * n)[:n]


def history_historical():
    """Measured sizes from conversation b534cdbc... before 'Are you online ?'."""
    return [
        dict(role='assistant', content=sized(2228, 'a')),
        dict(role='user', content='The owls it going ?'),
        dict(role='assistant', content=sized(482, 'b')),
        dict(role='user', content='What have you improved over the last 7 days ?'),
        dict(role='assistant', content=sized(1147, 'c')),
        dict(role='user', content='Re check back end'),
        dict(role='assistant', content=sized(208, 'd')),
    ]


def build(prompt, history, num_ctx=NUM_CTX):
    maximum = num_ctx - OUT - FRAME
    built, metrics = _select_history_prompt(prompt, history, prompt, FIXED, maximum, disambiguate_prompt_text)
    planned = plan_chat_context(built, MANDATORY_SYSTEM, [], mandatory_suffix=TOOL_BOUNDARY,
                                num_ctx=num_ctx, output_tokens=OUT, framing_reserve=FRAME)
    return built, metrics, planned


def test_unselected_historical_window_reproduces_failure_with_stage():
    window = history_historical()[-7:] + [dict(role='user', content='Are you online ?')]
    prompt = conversation_prompt('Are you online ?', window, current_turn='Are you online ?')
    assert len(prompt.encode()) + FIXED > MAX_INPUT  # the recorded 7,530 byte failure
    with pytest.raises(ChatContextBudgetError) as err:
        plan_chat_context(prompt, MANDATORY_SYSTEM, [], mandatory_suffix=TOOL_BOUNDARY)
    assert err.value.code == 'context_budget_exceeded'
    assert err.value.receipt['rejection_stage'] == 'mandatory_admission'
    assert err.value.receipt['over_budget_utf8_bytes'] > 0


def test_are_you_online_then_why_both_admitted_with_selection():
    hist = history_historical()
    built, metrics, planned = build('Are you online ?', hist)
    assert planned['receipt']['admitted_input_utf8_bytes'] <= MAX_INPUT
    assert metrics['history_turns_excluded'] >= 1          # oldest verbose turn evicted
    assert metrics['history_turns_admitted'] + metrics['history_turns_excluded'] == len(hist)
    assert built.endswith('Are you online ?')
    # 'Why' after the error response, still with verbose older turns
    hist2 = hist + [dict(role='user', content='Are you online ?'), dict(role='assistant', content=ERROR_TEXT)]
    built2, metrics2, planned2 = build('Why', hist2)
    assert planned2['receipt']['admitted_input_utf8_bytes'] <= MAX_INPUT
    assert built2.endswith('Why')
    assert 'context_budget_exceeded' in built2   # newest turns (the error) preferred over oldest


def test_selection_is_newest_contiguous_suffix_and_ordered():
    hist = history_historical()
    built, metrics, _ = build('Are you online ?', hist)
    admitted = metrics['history_turns_admitted']
    body = built.split('\n[CURRENT_USER_REQUEST]\n')[0].split(']\n', 1)[1]
    rows = json.loads(body)
    assert [r['content'][:12] for r in rows] == [r['content'][:12] for r in hist[len(hist) - admitted:]]


@pytest.mark.parametrize('after', ['verbose', 'error', 'fresh'])
def test_short_prompts_after_verbose_error_and_fresh(after):
    if after == 'fresh':
        hist = []
    elif after == 'verbose':
        hist = [dict(role='user', content='q'), dict(role='assistant', content=sized(6500, 'v'))]
    else:
        hist = [dict(role='user', content='q'), dict(role='assistant', content=ERROR_TEXT)] * 4
    for short in ('hello world test', 'run task', 'Why'):
        built, metrics, planned = build(short, hist)
        assert built.endswith(short)
        assert planned['receipt']['status'] == 'planned'


def test_duplicate_current_message_prevented_by_exclusion_not_text():
    earlier_same = [dict(role='user', content='test'), dict(role='assistant', content='ok')]
    # New clients exclude the current message by identity: earlier identical text is kept.
    report = {}
    out = conversation_prompt('test', earlier_same, current_turn='test', report=report)
    assert report['legacy_duplicate_removed'] is False
    assert json.loads(out.split(']\n', 1)[1].split('\n[CURRENT_USER_REQUEST]\n')[0])[0]['content'] == 'test'
    # Legacy clients that appended the current message as the final turn: exactly that copy is dropped.
    report = {}
    legacy = earlier_same + [dict(role='user', content='test')]
    conversation_prompt('test', legacy, current_turn='test', report=report)
    assert report['legacy_duplicate_removed'] is True and report['history_turns_available'] == 2
    assert out.count('[CURRENT_USER_REQUEST]') == 1


def test_current_prompt_never_truncated_and_fails_closed():
    huge = sized(MAX_INPUT, 'p')                    # mandatory request alone exceeds the budget
    built, metrics, = _select_history_prompt(huge, history_historical(), huge, FIXED, MAX_INPUT, disambiguate_prompt_text)
    assert built == huge and metrics['history_turns_admitted'] == 0
    with pytest.raises(ChatContextBudgetError) as err:
        plan_chat_context(built, MANDATORY_SYSTEM, [], mandatory_suffix=TOOL_BOUNDARY)
    assert err.value.receipt['rejection_stage'] == 'mandatory_admission'


def test_operation_rogue_prompt_with_history_admitted_prompt_intact():
    rogue = '# AI-BS CHALLENGE: OPERATION ROGUE INTELLIGENCE\n' + sized(2960, 'r')   # ~3 KB like the recorded 3,007
    hist = history_historical() + [dict(role='user', content='hello world test'), dict(role='assistant', content=ERROR_TEXT)]
    built, metrics, planned = build(rogue, hist)
    assert rogue in built   # prompt intact; the existing 'AI-BS' disambiguation note may follow it
    assert planned['receipt']['admitted_input_utf8_bytes'] <= MAX_INPUT


def test_persisted_history_not_mutated_and_source_provenance_preserved():
    hist = history_historical()
    snapshot = copy.deepcopy(hist)
    attached = '[ATTACHED FILE: a.txt (1.0 KB)]\n```txt\nSOURCE\n```\n[USER PROMPT]:\nsummarize'
    built, _, _ = build(attached, hist)
    assert hist == snapshot
    assert attached in built


@pytest.mark.parametrize('num_ctx', [8192, 16384, 32768])
def test_supported_context_windows_monotonic_and_model_limits(num_ctx):
    native = {'stehouwer_llm': 32768, 'nemotron-3.5-lightning': 32768, 'qwen2.5-coder': 32768, 'llama3.1': 131072}
    assert all(num_ctx <= limit for limit in native.values())
    hist = history_historical() * 4
    _, metrics, planned = build('Why', hist, num_ctx=num_ctx)
    assert planned['receipt']['maximum_input_utf8_bytes'] == num_ctx - OUT - FRAME
    prev = build('Why', hist, num_ctx=8192)[1]['history_turns_admitted']
    assert metrics['history_turns_admitted'] >= prev


def test_unsupported_window_rejected():
    with pytest.raises(ChatContextBudgetError) as err:
        plan_chat_context('x', MANDATORY_SYSTEM, [], num_ctx=40000)
    assert err.value.code == 'invalid_context_limit'


def test_metrics_are_sanitized_and_complete():
    _, metrics, _ = build('Why', history_historical())
    for key in ('token_accounting_basis', 'maximum_input_utf8_bytes', 'fixed_overhead_utf8_bytes', 'input_utf8_bytes_estimate',
                'history_turns_available', 'history_turns_admitted', 'history_turns_excluded'):
        assert key in metrics
    blob = json.dumps(metrics)
    assert 'aaaa' not in blob and 'Why' not in blob      # counts only, never message text


def test_assistant_history_never_carries_server_metadata_frames():
    receipt = dict(schema='aibs.local_inference.v1', type='aibs_cognitive_meta', provider='local', request_id='0' * 32,
                   model='m', status='completed', generation_verified=True, completion_verified=True, steps=[],
                   context_budget=dict(input_utf8_bytes=5248, admitted_context=8192))
    stored = '> note\n' + metadata_chunk(receipt) + 'answer' + metadata_chunk(receipt)
    out = conversation_prompt('next', [dict(role='user', content='q'), dict(role='assistant', content=stored)], current_turn='next')
    history_part = out.split('\n[CURRENT_USER_REQUEST]\n')[0]
    assert '<!--AI-BS-METADATA:' not in history_part and 'answer' in history_part


def test_metadata_escaper_fragmented_and_literal_model_text():
    esc = _MetadataEscaper()
    text = 'a <!--AI-BS-METADATA:{"x":1}--> b <!-- user comment --> c <!--AI-BS-MET'
    out = ''.join(esc.feed(ch) for ch in text) + esc.feed(final=True)
    assert '<!--AI-BS-METADATA:' not in out                 # model-authored prefix is neutralised
    assert '&lt;!--AI-BS-METADATA:' in out
    assert '<!-- user comment -->' in out                  # unrelated comments preserved
    assert out.endswith('<!--AI-BS-MET')                    # held partial prefix flushed as plain text
