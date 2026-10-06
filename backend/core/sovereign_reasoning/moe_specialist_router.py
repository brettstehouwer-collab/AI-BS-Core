#!/usr/bin/env python3
"""
Sovereign Mixture-of-Specialists (MoE) Routing Engine
AI-BS Antigravity Unison Architecture
Dynamically classifies incoming agent and operator intents, dispatching to
the optimal specialized model in the local 29-model Ollama fleet (Ports 11434/11435).
"""

import os
import sys
import re
import json
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from pathlib import Path
import httpx

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logger = logging.getLogger("moe_specialist_router")

_backend_dir = Path(__file__).resolve().parent.parent.parent
_root_dir = _backend_dir.parent

DEFAULT_OLLAMA_PORT = 11434
OLLAMA_BASE_URL = f"http://127.0.0.1:{DEFAULT_OLLAMA_PORT}"

from enum import Enum
from dataclasses import dataclass, asdict

class SpecialistDomain(str, Enum):
    CODE = "code"
    CREATIVE = "creative"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    REASONING = "reasoning"
    EMBEDDING = "embedding"


@dataclass
class RoutingDecision:
    domain: str
    confidence: float
    selected_model: str
    fallback_model: str
    reasoning: str
    context_window: int
    params: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __getitem__(self, item):
        return getattr(self, item)

    def get(self, item, default=None):
        return getattr(self, item, default)


# Domain Specialist Mapping Matrix
SPECIALIST_MATRIX = {
    "code": {
        "primary": "qwen2.5-coder:latest",
        "fallback": "stehouwer_llm:latest",
        "description": "Deterministic polyglot code synthesis, AST analysis, refactoring, and tool execution.",
        "params": "32.8B Q5_K_M",
        "context_window": 32768,
        "keywords": ["code", "function", "class", "debug", "python", "javascript", "typescript", "c++", "rust", "sql", "html", "css", "api", "git", "terminal", "compile", "ast", "regex", "refactor", "algorithm"]
    },
    "creative": {
        "primary": "stehouwer_dolphin:latest",
        "fallback": "unrestricted-llama3.1:latest",
        "description": "Uninhibited narrative prose, cinematic dialogue, screenplay scripts, lyrics, and Fire Writing.",
        "params": "8.0B Q8_0",
        "context_window": 131072,
        "keywords": ["story", "dialogue", "scene", "script", "lyrics", "poem", "essay", "fire writing", "prose", "character", "screenplay", "narrative", "unfiltered", "creative", "fiction", "novel"]
    },
    "function_calling": {
        "primary": "stehouwer-hermes:latest",
        "fallback": "qwen2.5-coder:latest",
        "description": "Structured JSON function calling, tool schema generation, and multi-turn agent loops.",
        "params": "8.0B Q8_0",
        "context_window": 131072,
        "keywords": ["tool", "json", "schema", "argument", "parameter", "function call", "agent loop", "dispatch", "hook", "workflow", "dag", "call"]
    },
    "vision": {
        "primary": "qwen3.6:latest",
        "fallback": "gemma4:12b",
        "description": "Multimodal perception, image analysis, layout parsing, and visual OCR.",
        "params": "36.0B / 11.9B",
        "context_window": 262144,
        "keywords": ["image", "photo", "picture", "visual", "ocr", "layout", "diagram", "screenshot", "camera", "frame", "render", "pixel", "canvas"]
    },
    "reasoning": {
        "primary": "llama3.3:70b",
        "fallback": "stehouwer_llm:latest",
        "description": "Deep multi-step reasoning, scholarly verification, logical deduction, and architectural synthesis.",
        "params": "70.6B Q4_K_M",
        "context_window": 131072,
        "keywords": ["reasoning", "prove", "verify", "why", "logic", "philosophy", "deduction", "analysis", "compare", "contrast", "architecture", "strategy", "governance"]
    },
    "embedding": {
        "primary": "nomic-embed-text:latest",
        "fallback": "nomic-embed-text:latest",
        "description": "Dense high-dimensional vector representations for ChromaDB vector search (Port 8002).",
        "params": "137M F16",
        "context_window": 2048,
        "keywords": ["embed", "vector", "search", "semantic", "similarity", "chromadb", "retrieve"]
    }
}


class SovereignMoERouter:
    def __init__(self, ollama_url: str = OLLAMA_BASE_URL):
        self.ollama_url = ollama_url.rstrip("/")
        self.specialists = SPECIALIST_MATRIX
        self._cached_available_models: List[str] = []
        self._last_models_check: float = 0.0

    async def get_available_models(self) -> List[str]:
        """Queries local Ollama on Port 11434 to list installed models."""
        now = time.time()
        if self._cached_available_models and (now - self._last_models_check < 30.0):
            return self._cached_available_models

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{self.ollama_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    self._cached_available_models = [m.get("name") for m in data.get("models", [])]
                    self._last_models_check = now
                    return self._cached_available_models
        except Exception as e:
            logger.warning(f"Failed to query Ollama tags on {self.ollama_url}: {e}")

        # Fallback to standard installed roster
        return [
            "stehouwer_llm:latest",
            "qwen2.5-coder:latest",
            "stehouwer_dolphin:latest",
            "stehouwer-hermes:latest",
            "qwen3.6:latest",
            "gemma4:12b",
            "llama3.3:70b",
            "nomic-embed-text:latest"
        ]

    def classify_intent(self, prompt: str, explicit_domain: Optional[str] = None) -> RoutingDecision:
        """Classifies the prompt into an optimal specialist domain with confidence scoring."""
        if explicit_domain and explicit_domain.lower() in self.specialists:
            domain = explicit_domain.lower()
            spec = self.specialists[domain]
            return RoutingDecision(
                domain=domain,
                confidence=1.0,
                selected_model=spec["primary"],
                fallback_model=spec["fallback"],
                reasoning=f"Explicit domain override '{domain}' requested.",
                context_window=spec["context_window"],
                params=spec["params"]
            )

        p_lower = prompt.lower()
        domain_scores: Dict[str, int] = {d: 0 for d in self.specialists}

        for domain, spec in self.specialists.items():
            for kw in spec["keywords"]:
                # Word boundary match for exact keywords
                matches = len(re.findall(r'\b' + re.escape(kw) + r'\b', p_lower))
                domain_scores[domain] += matches * 2

        # Check for code blocks or syntax indicators
        if "```" in prompt or "def " in prompt or "class " in prompt or "function(" in prompt:
            domain_scores["code"] += 6
        if any(token in p_lower for token in ["traceback", "syntaxerror", "exception", "import ", "const "]):
            domain_scores["code"] += 5

        # Check for dialogue / creative markers
        if any(token in p_lower for token in ["write a story", "chapter", "script", "scene:", "act 1"]):
            domain_scores["creative"] += 8

        # Check for image / visual markers
        if any(token in p_lower for token in ["describe this image", "look at the image", "in the picture"]):
            domain_scores["vision"] += 10

        best_domain = max(domain_scores, key=domain_scores.get)
        top_score = domain_scores[best_domain]

        # Default to code / stehouwer_llm if ambiguity
        if top_score == 0:
            best_domain = "code"
            confidence = 0.5
            reason = "Defaulted to Sovereign Core Code model (general inquiry)."
        else:
            confidence = min(0.99, round(top_score / (sum(domain_scores.values()) + 1e-5), 2))
            reason = f"Keyword density matches {best_domain} specialization (score: {top_score})."

        spec = self.specialists[best_domain]
        return RoutingDecision(
            domain=best_domain,
            confidence=confidence,
            selected_model=spec["primary"],
            fallback_model=spec["fallback"],
            reasoning=reason,
            context_window=spec["context_window"],
            params=spec["params"]
        )

    async def discover_fleet(self) -> Dict[str, Any]:
        """Discovers active local Ollama models on Port 11434."""
        models = await self.get_available_models()
        return {
            "online": len(models) > 0,
            "port": DEFAULT_OLLAMA_PORT,
            "model_count": len(models),
            "models": models
        }

    async def dispatch(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        domain_hint: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Alias for route_and_generate to service REST and agent runner clients."""
        return await self.route_and_generate(
            prompt=prompt,
            system_prompt=system_prompt,
            domain_override=domain_hint,
            temperature=temperature
        )

    async def stream_dispatch(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        domain_hint: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncGenerator[str, None]:
        """Alias for stream_specialist_response."""
        async for chunk in self.stream_specialist_response(
            prompt=prompt,
            system_prompt=system_prompt,
            domain_override=domain_hint,
            temperature=temperature
        ):
            yield chunk

    async def route_and_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        domain_override: Optional[str] = None,
        model_override: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Routes a prompt to the specialist model and executes generation via Ollama."""
        classification = self.classify_intent(prompt, domain_override)
        target_model = model_override or classification["selected_model"]

        # Verify model availability
        available = await self.get_available_models()
        if target_model not in available and target_model + ":latest" in available:
            target_model = target_model + ":latest"
        elif target_model not in available:
            # Fallback to secondary model if primary unavailable
            fallback = classification["fallback_model"]
            if fallback in available or fallback + ":latest" in available:
                target_model = fallback
            elif "stehouwer_llm:latest" in available:
                target_model = "stehouwer_llm:latest"
            elif available:
                target_model = available[0]

        start_t = time.time()
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_ctx": min(32768, classification.get("context_window", 32768))
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                res = await client.post(f"{self.ollama_url}/api/generate", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    elapsed = round((time.time() - start_t) * 1000, 2)
                    return {
                        "status": "success",
                        "response": data.get("response", ""),
                        "model_used": target_model,
                        "domain": classification["domain"],
                        "confidence": classification["confidence"],
                        "duration_ms": elapsed,
                        "eval_count": data.get("eval_count", 0),
                        "tokens_per_sec": round(data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9), 1) if data.get("eval_duration") else 0
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Ollama HTTP {res.status_code}: {res.text}",
                        "model_attempted": target_model
                    }
        except Exception as e:
            logger.error(f"MoE execution failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "model_attempted": target_model
            }

    async def stream_specialist_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        domain_override: Optional[str] = None,
        model_override: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Streams tokens directly from the specialized model as Server-Sent Events (SSE)."""
        classification = self.classify_intent(prompt, domain_override)
        target_model = model_override or classification["selected_model"]

        meta_header = {
            "type": "META_CLASSIFICATION",
            "domain": classification["domain"],
            "model": target_model,
            "confidence": classification["confidence"],
            "reasoning": classification["reasoning"]
        }
        yield f"data: {json.dumps(meta_header)}\n\n"

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": min(32768, classification.get("context_window", 32768))
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", f"{self.ollama_url}/api/generate", json=payload) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                token = chunk.get("response", "")
                                is_done = chunk.get("done", False)
                                yield f"data: {json.dumps({'token': token, 'done': is_done})}\n\n"
                                if is_done:
                                    break
                            except Exception:
                                continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"


# Global singleton router instance
moe_router = SovereignMoERouter()

if __name__ == "__main__":
    test_queries = [
        "Write a Python script with FastAPI to stream video chunks",
        "Write a heartbreaking scene between two estranged lovers in 1940s Chicago",
        "Call the tool get_stock_levels with parameters venue_id=notos and category=liquor",
        "Describe the visual architecture of this living room floorplan image",
        "What is the ontological distinction between substance and accident in Spinoza's metaphysics?"
    ]
    print("=== Sovereign MoE Intent Classification Benchmark ===")
    for q in test_queries:
        res = moe_router.classify_intent(q)
        print(f"Query:  {q[:50]}...")
        print(f"➔ Domain: {res['domain']} | Model: {res['selected_model']} | Conf: {res['confidence']}")
        print("-" * 60)
