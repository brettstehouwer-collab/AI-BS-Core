"""
Multi-Provider AI Gateway & BYOK (Bring Your Own Key) Router for AI-BS Matrix.
Enables users to connect their own OpenAI, Anthropic, Gemini, Groq, DeepSeek,
Replicate, and Fal.ai API accounts or use the local RTX 4090 Ollama engine.
"""

import os
import asyncio
import json
import httpx
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Body, Depends, Request
from pydantic import BaseModel, Field, StrictStr, StrictBool, ConfigDict
from security.host_control_access import AdminHostControlRoute, require_host_admin

router = APIRouter(prefix="/api/ai", tags=["AI Providers & BYOK Gateway"], route_class=AdminHostControlRoute)

CONFIG_FILE = os.path.join("C:\\AI-BS", "database", "ai_providers_config.json")
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


def _unmasked_key(value: Optional[str]) -> str:
    """Display markers are never credentials or replacements for saved keys."""
    key = value.strip() if isinstance(value, str) else ""
    return "" if "*" in key or "..." in key else key


def _openai_credential(cfg: dict, *, request_key=None, header_key=None) -> tuple[str, str]:
    """Resolve a server credential without copying the environment into config."""
    saved = cfg.get("providers", {}).get("openai", {})
    candidates = (("request", request_key), ("header", header_key),
                  ("saved", saved.get("api_key")),
                  ("environment", os.environ.get("OPENAI_API_KEY")))
    for source, value in candidates:
        key = _unmasked_key(value)
        if key:
            return key, source
    return "", "none"


def load_config() -> dict:
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "active_provider": "local",
        "providers": {
            "local": {"model": "stehouwer_llm", "host": "http://127.0.0.1:11434"},
            "openai": {"api_key": "", "model": DEFAULT_OPENAI_MODEL},
            "anthropic": {"api_key": "", "model": "claude-3-5-sonnet-20241022"},
            "gemini": {"api_key": "", "model": "gemini-2.0-flash"},
            "groq": {"api_key": "", "model": "llama-3.3-70b-versatile"},
            "deepseek": {"api_key": "", "model": "deepseek-chat"},
            "replicate": {"api_key": "", "model": "black-forest-labs/flux-1.1-pro"},
            "fal": {"api_key": "", "model": "fal-ai/flux/dev"}
        }
    }


def save_config(cfg: dict):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


SUPPORTED_PROVIDERS = [
    {
        "id": "local",
        "name": "Local AI-BS Engine (RTX 4090)",
        "icon": "🖥️",
        "description": "Runs 100% locally on your hardware with 0 cloud cost and complete privacy.",
        "models": ["stehouwer_llm", "nemotron-3.5-lightning", "llama3.1:latest", "mistral:latest", "gemma:latest"],
        "requires_key": False
    },
    {
        "id": "openai",
        "name": "OpenAI (GPT-4o / o1)",
        "icon": "🟢",
        "description": "Industry standard reasoning and multimodal text generation.",
        "models": [DEFAULT_OPENAI_MODEL, "gpt-4o", "gpt-4o-mini", "o1", "o3-mini", "gpt-4-turbo"],
        "requires_key": True,
        "key_hint": "sk-..."
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "icon": "🟣",
        "description": "Exceptional long-form screenwriting, prose adaptation, and nuanced creative writing.",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "requires_key": True,
        "key_hint": "sk-ant-..."
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "icon": "🔵",
        "description": "Massive 2M token context window for entire book manuscripts and screenplay bibles.",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "requires_key": True,
        "key_hint": "AIzaSy..."
    },
    {
        "id": "groq",
        "name": "Groq LPU Engine",
        "icon": "⚡",
        "description": "Ultra-fast inference (500+ tokens/sec) for instantaneous screenplay & task generation.",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "deepseek-r1-distill-llama-70b"],
        "requires_key": True,
        "key_hint": "gsk_..."
    },
    {
        "id": "deepseek",
        "name": "DeepSeek AI",
        "icon": "🔴",
        "description": "High-intelligence mathematical reasoning and deep narrative analysis at low cost.",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "requires_key": True,
        "key_hint": "sk-..."
    },
    {
        "id": "replicate",
        "name": "Replicate (FLUX & Video)",
        "icon": "🎨",
        "description": "Cloud GPU rendering for FLUX.1 image generation and Wan 2.1 video workflows.",
        "models": ["black-forest-labs/flux-1.1-pro", "black-forest-labs/flux-dev", "wan-video/wan-2.1-t2v-14b"],
        "requires_key": True,
        "key_hint": "r8_..."
    },
    {
        "id": "fal",
        "name": "Fal.ai (Ultra-Fast Video)",
        "icon": "✨",
        "description": "Sub-second image diffusion and fast cinematic AI video rendering pipelines.",
        "models": ["fal-ai/flux/dev", "fal-ai/flux-realism", "fal-ai/wan/v2.1/text-to-video"],
        "requires_key": True,
        "key_hint": "key_..."
    }
]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class KeyValidationRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    model: Optional[str] = None


class MultiProviderGenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = "You are a professional assistant in the AI-BS ecosystem."
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = Field(default=0.7, strict=True, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2048, strict=True, ge=1, le=16384)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/providers")
async def list_providers():
    """List all supported AI providers and their configuration."""
    cfg = load_config()
    providers_with_state = []
    
    for p in SUPPORTED_PROVIDERS:
        p_copy = dict(p)
        saved_info = cfg.get("providers", {}).get(p["id"], {})
        p_copy["is_configured"] = bool(saved_info.get("api_key") or p["id"] == "local")
        p_copy["saved_model"] = saved_info.get("model", p["models"][0])
        p_copy["is_active"] = (cfg.get("active_provider") == p["id"])
        # Mask API key for security
        key = saved_info.get("api_key", "")
        p_copy["masked_key"] = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else ("***" if key else "")
        if p["id"] == "openai":
            key, source = _openai_credential(cfg)
            p_copy["is_configured"] = bool(key)
            p_copy["credential_source"] = source
            if source == "environment":
                p_copy["masked_key"] = "***"
        providers_with_state.append(p_copy)

    return {
        "active_provider": cfg.get("active_provider", "local"),
        "providers": providers_with_state
    }


@router.post("/config")
async def save_provider_configuration(payload: Dict[str, Any] = Body(...)):
    """Save active provider selection and custom API keys."""
    cfg = load_config()
    
    if "active_provider" in payload:
        cfg["active_provider"] = payload["active_provider"]

    if "providers" in payload:
        for p_id, p_data in payload["providers"].items():
            if p_id not in cfg["providers"]:
                cfg["providers"][p_id] = {}
            if p_id == "openai":
                key = _unmasked_key(p_data.get("api_key"))
                if key:
                    cfg["providers"][p_id]["api_key"] = key
            elif "api_key" in p_data and p_data["api_key"] and not p_data["api_key"].startswith("***"):
                cfg["providers"][p_id]["api_key"] = p_data["api_key"].strip()
            if "model" in p_data:
                cfg["providers"][p_id]["model"] = p_data["model"]

    save_config(cfg)
    return {"status": "success", "message": "AI Provider settings updated successfully."}


@router.post("/validate-key")
async def validate_provider_api_key(req: KeyValidationRequest, x_ai_key: Optional[str] = Header(None)):
    """
    Test live connectivity with a provider using the supplied API key.
    """
    provider = req.provider.lower()
    key = (req.api_key or "").strip()
    if provider == "openai":
        key, _ = _openai_credential(load_config(), request_key=req.api_key, header_key=x_ai_key)
    
    if provider == "local":
        for o_port in [11434, 11435]:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                    r = await client.get(f"http://127.0.0.1:{o_port}/api/tags")
                    if r.status_code == 200:
                        models = [m.get("name") for m in r.json().get("models", [])]
                        return {"status": "valid", "provider": "local", "port": o_port, "models": models}
            except Exception:
                continue
        return {"status": "error", "message": "Local Ollama is offline or unreachable across ports 11434/11435"}

    if not key:
        raise HTTPException(status_code=400, detail="API key is required for validation.")

    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=provider != "openai", follow_redirects=False) as client:
            # 1. OpenAI
            if provider == "openai":
                r = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"}
                )
                if r.status_code == 200:
                    if len(r.content) > 2 * 1024 * 1024:
                        raise ValueError("oversized model listing")
                    data = r.json()
                    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
                        raise ValueError("invalid model listing")
                    identifiers = {item["id"] for item in data["data"]
                                   if isinstance(item, dict) and isinstance(item.get("id"), str)}
                    model = (req.model or "").strip()
                    supported = next(item["models"] for item in SUPPORTED_PROVIDERS if item["id"] == "openai")
                    result = {"status": "valid", "provider": "openai", "authenticated": True,
                              "models": [item for item in supported if item in identifiers],
                              "validation_scope": "authentication_and_model_listing", "generation_verified": False}
                    if model:
                        result.update(model=model, model_available=model in identifiers, model_supported=model in supported)
                        if model not in identifiers:
                            return {**result, "status": "error", "message":
                                f"OpenAI authentication succeeded, but selected model '{model}' is not listed for this credential/project. Choose an available model. No generation was attempted."}
                        if model not in supported:
                            return {**result, "status": "error", "message":
                                f"OpenAI lists model '{model}', but this BS-Chat route does not support it. Choose a supported model. No generation was attempted."}
                        result["message"] = f"OpenAI authentication succeeded and model '{model}' is listed. Generation has not been tested."
                    else:
                        result["message"] = "OpenAI authentication succeeded. No selected model or generation was tested."
                    return result
                return {"status": "error", "message": f"OpenAI authentication failed (HTTP {r.status_code})."}

            # 2. Anthropic
            elif provider == "anthropic":
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "ping"}]
                    }
                )
                if r.status_code == 200:
                    return {"status": "valid", "provider": "anthropic", "message": "Successfully authenticated with Anthropic Claude API."}
                return {"status": "error", "message": f"Anthropic authentication failed ({r.status_code}): {r.text[:120]}"}

            # 3. Google Gemini
            elif provider == "gemini":
                r = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                )
                if r.status_code == 200:
                    return {"status": "valid", "provider": "gemini", "message": "Successfully authenticated with Google Gemini API."}
                return {"status": "error", "message": f"Gemini authentication failed ({r.status_code}): {r.text[:120]}"}

            # 4. Groq
            elif provider == "groq":
                r = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {key}"}
                )
                if r.status_code == 200:
                    return {"status": "valid", "provider": "groq", "message": "Successfully authenticated with Groq LPU API."}
                return {"status": "error", "message": f"Groq authentication failed ({r.status_code}): {r.text[:120]}"}

            # 5. DeepSeek
            elif provider == "deepseek":
                r = await client.get(
                    "https://api.deepseek.com/models",
                    headers={"Authorization": f"Bearer {key}"}
                )
                if r.status_code == 200:
                    return {"status": "valid", "provider": "deepseek", "message": "Successfully authenticated with DeepSeek API."}
                return {"status": "error", "message": f"DeepSeek authentication failed ({r.status_code}): {r.text[:120]}"}

            # 6. Replicate
            elif provider == "replicate":
                r = await client.get(
                    "https://api.replicate.com/v1/account",
                    headers={"Authorization": f"Bearer {key}"}
                )
                if r.status_code == 200:
                    return {"status": "valid", "provider": "replicate", "message": "Successfully authenticated with Replicate API."}
                return {"status": "error", "message": f"Replicate authentication failed ({r.status_code}): {r.text[:120]}"}

            # 7. Fal.ai
            elif provider == "fal":
                r = await client.get(
                    "https://rest.alpha.fal.ai/tokens",
                    headers={"Authorization": f"Key {key}"}
                )
                if r.status_code in [200, 404]:
                    return {"status": "valid", "provider": "fal", "message": "Fal.ai API key format accepted."}
                return {"status": "error", "message": f"Fal.ai authentication failed ({r.status_code})."}

            else:
                return {"status": "error", "message": f"Unknown provider: {provider}"}

    except Exception as e:
        if provider == "openai":
            return {"status": "error", "message": "OpenAI connection could not be verified."}
        return {"status": "error", "message": f"Network or connection error: {str(e)}"}


@router.post("/generate")
async def generate_with_provider(
    req: MultiProviderGenerateRequest,
    x_ai_provider: Optional[str] = Header(None),
    x_ai_key: Optional[str] = Header(None)
):
    """
    Universal Text Generation Endpoint.
    Routes to the active provider (Local, OpenAI, Claude, Gemini, Groq, DeepSeek).
    """
    cfg = load_config()
    provider = req.provider or x_ai_provider or cfg.get("active_provider", "local")
    provider = provider.lower()
    
    saved_provider_cfg = cfg.get("providers", {}).get(provider, {})
    api_key = req.api_key or x_ai_key or saved_provider_cfg.get("api_key", "")
    model = req.model or saved_provider_cfg.get("model")
    if provider == "openai":
        api_key, _ = _openai_credential(cfg, request_key=req.api_key, header_key=x_ai_key)

    # 1. LOCAL OLLAMA
    if provider == "local":
        model = model or "stehouwer_llm"
        for o_port in [11434, 11435]:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0, read=90.0)) as client:
                    r = await client.post(
                        f"http://127.0.0.1:{o_port}/api/chat",
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": req.system_prompt},
                                {"role": "user", "content": req.prompt}
                            ],
                            "stream": False,
                            "options": {"temperature": req.temperature, "num_predict": req.max_tokens}
                        }
                    )
                    if r.status_code == 200:
                        text = r.json().get("message", {}).get("content", "")
                        return {"provider": "local", "model": model, "content": text}
            except Exception:
                continue
        raise HTTPException(status_code=502, detail="Local Ollama generation error: Ports 11434 & 11435 unreachable.")

    # Check key requirement for cloud providers
    if not api_key:
        raise HTTPException(status_code=401, detail=f"API key missing for provider: {provider}. Please configure it in AI Settings.")

    # 2. OPENAI
    if provider == "openai":
        model = model or DEFAULT_OPENAI_MODEL
        from core.bs_chat_provider import openai_completion
        result = await openai_completion(api_key=api_key, model=model, prompt=req.prompt,
            system_prompt=req.system_prompt, temperature=req.temperature, max_tokens=req.max_tokens)
        return {key: result[key] for key in ("provider", "model", "content")}

    # 3. ANTHROPIC CLAUDE
    elif provider == "anthropic":
        model = model or "claude-3-5-sonnet-20241022"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": model,
                        "system": req.system_prompt,
                        "messages": [{"role": "user", "content": req.prompt}],
                        "max_tokens": req.max_tokens,
                        "temperature": req.temperature
                    }
                )
                r.raise_for_status()
                text = r.json()["content"][0]["text"]
                return {"provider": "anthropic", "model": model, "content": text}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Anthropic error: {str(e)}")

    # 4. GOOGLE GEMINI
    elif provider == "gemini":
        model = model or "gemini-2.0-flash"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                r = await client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": f"{req.system_prompt}\n\n{req.prompt}"}]}],
                        "generationConfig": {"temperature": req.temperature, "maxOutputTokens": req.max_tokens}
                    }
                )
                r.raise_for_status()
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return {"provider": "gemini", "model": model, "content": text}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gemini error: {str(e)}")

    # 5. GROQ
    elif provider == "groq":
        model = model or "llama-3.3-70b-versatile"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": req.system_prompt},
                            {"role": "user", "content": req.prompt}
                        ],
                        "temperature": req.temperature,
                        "max_tokens": req.max_tokens
                    }
                )
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
                return {"provider": "groq", "model": model, "content": text}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Groq error: {str(e)}")

    # 6. DEEPSEEK
    elif provider == "deepseek":
        model = model or "deepseek-chat"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": req.system_prompt},
                            {"role": "user", "content": req.prompt}
                        ],
                        "temperature": req.temperature,
                        "max_tokens": req.max_tokens
                    }
                )
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
                return {"provider": "deepseek", "model": model, "content": text}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"DeepSeek error: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported generation provider: {provider}")


class OpenCodeWorkerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: StrictStr = Field(min_length=1, max_length=96)
    prompt: StrictStr = Field(min_length=1, max_length=32768)
    public_input_only: StrictBool = False


@router.get("/opencode/models")
async def list_opencode_workers():
    """Additional official-client workers; no provider configuration is changed."""
    from core.opencode_worker import list_worker_models
    return {"models": list_worker_models(), "primary_unchanged": True,
            "role": "additional_coding_review_workers"}


@router.post("/opencode/work")
async def delegate_opencode_work(payload: OpenCodeWorkerRequest, request: Request,
                                 owner: str = Depends(require_host_admin)):
    """Only explicit task text crosses into a fresh, owner-bound OpenCode worker."""
    from core.opencode_worker import run_worker, WorkerError
    work = asyncio.create_task(run_worker(owner=owner, model=payload.model, prompt=payload.prompt,
                                         public_input_only=payload.public_input_only))
    try:
        while not work.done():
            if await request.is_disconnected():
                raise HTTPException(499, "OpenCode worker request was cancelled.")
            await asyncio.wait({work}, timeout=.15)
        return await work
    except WorkerError as error:
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.public_message}) from None
    finally:
        if not work.done():
            work.cancel()
        await asyncio.gather(work, return_exceptions=True)
