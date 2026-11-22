"""Explicit OpenAI text turns for BS-Chat; host actions keep their own routes."""
from __future__ import annotations

import json
import asyncio
import math
import re

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse


from core.pipeline_context_injector import (
    AIBS_SOVEREIGN_SYSTEM_PROMPT,
    build_sovereign_system_prompt,
    disambiguate_prompt_text,
)

MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_CHARS = 64000
MAX_PROMPT_CHARS = 128000
TEXT_SYSTEM_PROMPT = (
    f"{AIBS_SOVEREIGN_SYSTEM_PROMPT}\n\n"
    "You are BS-Chat in the AI-BS application, using the OpenAI API for this text reply. "
    "Use the supplied conversation and context to answer accurately. This text turn "
    "cannot run host commands, edit files, or invoke tools. Do not claim that local "
    "actions, tests, file inspections, or GPU execution occurred. Generated code is "
    "a proposal for review, never an instruction to execute automatically."
)


def _openai_failure_detail(response, model):
    """Expose bounded diagnostic fields, never an upstream body or credential."""
    code = None
    try:
        body = response.json() if len(response.content) <= 16384 else {}
        error = body.get('error', {}) if isinstance(body, dict) else {}
        value = error.get('code') if isinstance(error, dict) else None
        if value in {'model_not_found', 'invalid_api_key', 'insufficient_quota',
                     'rate_limit_exceeded', 'permission_denied', 'project_not_found',
                     'not_found_error', 'unsupported_parameter', 'unsupported_value'}:
            code = value
    except (ValueError, TypeError):
        pass
    status = response.status_code
    if status == 404 or code == 'model_not_found':
        reason = f"OpenAI could not find model '{model}' or its endpoint for this project. Check the selected model and project access."
    elif status == 401:
        reason = "OpenAI authentication failed. Check the existing server credential."
    elif status == 403:
        reason = f"OpenAI denied access to model '{model}'. Check project and model permissions."
    elif code == 'insufficient_quota':
        reason = "OpenAI reports insufficient API quota or credits. Check the project's API billing and limits."
    elif status == 429:
        reason = "OpenAI rate-limited this request. It was not retried."
    else:
        reason = f"OpenAI request for model '{model}' failed."
    diagnostics = f"HTTP {status}" + (f"; code={code}" if code else '')
    request_id = response.headers.get('x-request-id', '')
    if re.fullmatch(r'(?:req_)?[a-fA-F0-9-]{16,64}', request_id):
        diagnostics += f"; request_id={request_id}"
    return f"{reason} ({diagnostics}). No local fallback was used."


def conversation_messages(prompt, history=(), *, current_user_prompt=None):
    """Bound supplied prior text, and include the current user turn exactly once."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
        raise HTTPException(422, "Enter a nonempty chat prompt of up to 128000 characters.")
    if history is None:
        history = []
    if not isinstance(history, (list, tuple)):
        raise HTTPException(422, "Chat history must contain user and assistant text messages.")
    rows = []
    for item in history:
        if (not isinstance(item, dict) or not isinstance(item.get("role"), str)
                or item.get("role") not in {"user", "assistant"}
                or not isinstance(item.get("content"), str)):
            raise HTTPException(422, "Chat history must contain user and assistant text messages.")
        rows.append({"role": item["role"], "content": item["content"]})
    current_forms = {prompt}
    if isinstance(current_user_prompt, str) and current_user_prompt:
        current_forms.add(current_user_prompt)
    if rows and rows[-1]["role"] == "user" and rows[-1]["content"] in current_forms:
        rows.pop()
    retained, size = [], 0
    for item in reversed(rows[-MAX_HISTORY_MESSAGES:]):
        if size + len(item["content"]) > MAX_HISTORY_CHARS:
            break
        retained.insert(0, item)
        size += len(item["content"])
    return [*retained, {"role": "user", "content": disambiguate_prompt_text(prompt)}]


async def openai_completion(*, api_key, model, prompt, history=(), current_user_prompt=None,
                            system_prompt=None, temperature=0.7, max_tokens=2048):
    """One bounded request, without automatic retries or local-model substitution."""
    if not api_key:
        raise HTTPException(503, "OpenAI is not configured for BS-Chat.")
    # Import lazily: the provider gateway also reuses this completion function.
    from routers.ai_providers_router import SUPPORTED_PROVIDERS
    supported = next(item["models"] for item in SUPPORTED_PROVIDERS if item["id"] == "openai")
    if model not in supported:
        raise HTTPException(400, "The selected OpenAI chat model is not supported. Choose an OpenAI model in AI settings.")
    messages = conversation_messages(prompt, history, current_user_prompt=current_user_prompt)
    if system_prompt is not None:
        if not isinstance(system_prompt, str) or len(system_prompt) > 16000:
            raise HTTPException(422, "The chat system prompt exceeds the supported text limit.")
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
    if type(max_tokens) is not int or not 1 <= max_tokens <= 16384:
        raise HTTPException(422, "Choose an output limit between 1 and 16384 tokens.")
    if type(temperature) not in (int, float) or not math.isfinite(temperature) or not 0 <= temperature <= 2:
        raise HTTPException(422, "Choose a numeric temperature between 0 and 2.")
    try:
        async with httpx.AsyncClient(timeout=60.0, trust_env=False, follow_redirects=False) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": "Bearer " + api_key},
                json={"model": model, "messages": messages, "temperature": temperature,
                      "max_tokens": max_tokens, "store": False})
            response.raise_for_status()
            if len(response.content) > 2 * 1024 * 1024:
                raise ValueError("oversized provider response")
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty provider response")
            return {"provider": "openai", "model": model, "content": content, "device": "OpenAI API"}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, _openai_failure_detail(exc.response, model)) from None
    except httpx.RequestError:
        raise HTTPException(502, "AI-BS could not reach OpenAI or complete its connection. No local fallback was used.") from None
    except Exception:
        raise HTTPException(502, "OpenAI generation could not be completed. No local fallback was used.") from None


def _guard_reply(message):
    return {"response": message, "provider": "local", "model": "chat-admission", "device": "Local service"}


def _program_status_reply(body):
    from core.program_status_readonly import resolve_program_update_status
    try:
        text = resolve_program_update_status(body)
    except PermissionError:
        raise HTTPException(403, "Verified project status access is required.") from None
    if text is None:
        return None
    return {"response": text, "provider": "local", "model": "program-status-records",
            "device": "Local read-only records"}


async def bs_chat_reply(body):
    """Return an admitted provider/service reply, or retain the local inference/tool branch."""
    from core.attached_source_context import validate_request_sources
    source_references = validate_request_sources(body)
    mode = body.get("mode")
    mode = mode.strip().lower() if isinstance(mode, str) else mode
    if body.get("plan_only") is True or mode in ("plan", "plan_only", "review"):
        return _guard_reply("Plan/review mode: no tools, model calls or coding task were executed.\n")
    if mode not in (None, "", "execute"):
        return _guard_reply("Unsupported chat mode: no tools, model calls or coding task were executed.\n")
    backend = body.get("execution_backend") or "trusted_host"
    if backend != "trusted_host":
        reason = "ISOLATION_UNAVAILABLE" if backend in ("windows_vm", "wsl2_vm") else "INVALID_EXECUTION_BACKEND"
        return _guard_reply(reason + ": this non-coding chat turn invoked no host tool or model.\n")
    from core.crypto_preview_chat import crypto_preview_reply
    crypto_reply = await crypto_preview_reply(body)
    if crypto_reply is not None:
        return crypto_reply
    from core.crypto_trial_status_chat import crypto_trial_status_reply
    trial_reply = await crypto_trial_status_reply(body)
    if trial_reply is not None:
        return trial_reply
    explicit = body.get("provider")
    if isinstance(explicit, str):
        explicit = explicit.strip().lower() or None
    if explicit == "local":
        return _program_status_reply(body)
    raw = body.get("user_prompt")
    raw = raw if isinstance(raw, str) else body.get("prompt", "")
    raw = raw if isinstance(raw, str) else ""
    from core.hybrid_reasoning_engine import detect_tool_intent
    tool, _ = detect_tool_intent(raw)
    explicit_coder = re.match(r"^\s*/(?:coder|code|patch|syntax|mirror|refactor|diff)\b", raw, re.IGNORECASE)
    explicit_coder = explicit_coder or re.match(
        r"^\s*(?:(?:please|can you)\s+)?(?:(?:use|run|ask|invoke)\s+(?:the\s+)?)?shadow[\s_-]+coder\b",
        raw, re.IGNORECASE)
    if tool or explicit_coder:
        return None
    from routers.ai_providers_router import load_config, _openai_credential, DEFAULT_OPENAI_MODEL
    cfg = load_config()
    provider = explicit if explicit is not None else cfg.get("active_provider", "local")
    if not isinstance(provider, str):
        raise HTTPException(400, "Choose a supported BS-Chat provider.")
    provider = provider.strip().lower()
    if provider not in ("local", "openai"):
        raise HTTPException(400, "This BS-Chat text route supports the local service or OpenAI. No fallback was used.")
    status_reply = _program_status_reply(body)
    if status_reply is not None:
        return status_reply
    if provider == "local":
        return None

    prompt = body.get("prompt") or body.get("user_prompt")
    history = body.get("messages")
    history = [] if history is None else history
    if not prompt and isinstance(history, list):
        prompt = next((item.get("content") for item in reversed(history)
                       if isinstance(item, dict) and item.get("role") == "user"), None)
    from core.safety_guardrails import audit_prompt_safety
    if isinstance(prompt, str):
        safe, refusal = audit_prompt_safety(prompt)
        if not safe:
            return _guard_reply("Sovereign Engine Refusal: " + refusal + "\n")
    saved = cfg.get("providers", {}).get("openai", {})
    model = body.get("model")
    if model in (None, "", "default", "stehouwer_llm"):
        model = saved.get("model") or DEFAULT_OPENAI_MODEL
    key, _ = _openai_credential(cfg)
    system = TEXT_SYSTEM_PROMPT
    supplied_system = body.get("system_prompt")
    if supplied_system:
        if not isinstance(supplied_system, str) or len(supplied_system) > 12000:
            raise HTTPException(422, "The supplied chat system context exceeds the supported text limit.")
        system += "\n\nSupplied chat context:\n" + supplied_system
    source_receipt = None
    if source_references:
        from core.attached_source_context import request_source_bundle, source_unavailable_reply
        bundle = await request_source_bundle(raw or prompt, source_references,
            max_chars=min(3500, max(0, 16000 - len(system) - 2)))
        references, source_receipt = bundle['context'], bundle['receipt']
        unavailable = source_unavailable_reply(bundle)
        if unavailable is not None:
            return unavailable
    else:
        from core.owned_rag_sources import source_reference_context
        references = await asyncio.to_thread(source_reference_context, raw or prompt,
                                            max_chars=max(0, 16000 - len(system) - 2))
    if references:
        system += '\n\n' + references
    result = await openai_completion(api_key=key, model=model, prompt=prompt, history=history,
        current_user_prompt=body.get("user_prompt"), system_prompt=system,
        temperature=body.get("temperature", 0.7), max_tokens=body.get("max_tokens", 2048))
    text = result["content"]
    if "```" in text:
        text += "\n\nGenerated code is a proposal only; no generated command was executed.\n"
    return {"response": text, "provider": result["provider"], "model": result["model"], "device": result["device"],
            **({'source_retrieval':source_receipt} if source_receipt is not None else {})}


def hybrid_reply_response(reply):
    metadata = {key: reply[key] for key in ("provider", "model", "device")}
    if 'source_retrieval' in reply:
        metadata['source_retrieval'] = reply['source_retrieval']
    metadata["display_name"] = ("OpenAI · " + reply["model"] if reply["provider"] == "openai" else "BS-Chat service")
    return StreamingResponse(iter([reply["response"], "\n<!--AI-BS-METADATA:" + json.dumps(metadata) + "-->"]),
                             media_type="text/plain")


def chat_reply_response(reply, *, stream=False):
    message = {"role": "assistant", "content": reply["response"]}
    result = {"status": "success", **reply, "message": message,
              "choices": [{"message": message, "finish_reason": "stop"}]}
    if not stream:
        return result
    event = {"content": reply["response"], "done": True,
             **{key: reply[key] for key in ("provider", "model", "device")},
             **({'source_retrieval':reply['source_retrieval']} if 'source_retrieval' in reply else {}),
             "choices": [{"delta": message, "finish_reason": "stop"}]}
    return StreamingResponse(iter(["data: " + json.dumps(event) + "\n\n", "data: [DONE]\n\n"]),
                             media_type="text/event-stream")
