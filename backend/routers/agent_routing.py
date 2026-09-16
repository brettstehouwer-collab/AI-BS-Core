"""
AI-BS Multi-Agent Gateway & Task-Decoupled Routing Router
Exposes dedicated endpoints with isolated inference parameters (temperature, top_p, models)
for Creative Narrative Drafting, Code/IPC Compilation, and Biomimetic Engineering.
"""

import os
import sys
import logging
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends

logger = logging.getLogger("AgentRouting")
router = APIRouter(prefix="/api/agent", tags=["Multi-Agent Gateway & Routing"])

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11435")

# Defined specialized model mappings
AGENT_PROFILES = {
    "creative": {
        "model": "stehouwer_persona:v2",
        "fallback_model": "stehouwer_dolphin:latest",
        "temperature": 0.75,
        "top_p": 0.90,
        "description": "High-temperature creative narrative, character dialogue, and teleplay drafting."
    },
    "code": {
        "model": "qwen2.5-coder:latest",
        "fallback_model": "llama3.1:latest",
        "temperature": 0.10,
        "top_p": 0.95,
        "description": "Deterministic, zero-hallucination code generation, schema validation, and IPC commands."
    },
    "noco": {
        "model": "stehouwer_llm:latest",
        "fallback_model": "stehouwer_persona:v2",
        "temperature": 0.30,
        "top_p": 0.85,
        "description": "Biomimetic microgrid, thermal dynamics, and acoustic engineering reasoning."
    },
    "general": {
        "model": "stehouwer_llm:latest",
        "fallback_model": "llama3.1:latest",
        "temperature": 0.50,
        "top_p": 0.90,
        "description": "General conversational agent and business operational inquiries."
    }
}

class AgentPromptRequest(BaseModel):
    prompt: str = Field(..., description="User prompt or instruction")
    project_name: Optional[str] = Field("Default Project", description="Target screenplay or project context")
    system_instruction: Optional[str] = Field(None, description="Optional custom system directive override")
    stream: Optional[bool] = False
    custom_temperature: Optional[float] = None

class UniversalRouteRequest(BaseModel):
    prompt: str
    task_type: Optional[str] = Field("auto", description="'creative', 'code', 'noco', 'general', or 'auto'")
    project_name: Optional[str] = "Default Project"

async def call_ollama(model: str, fallback_model: str, system_prompt: str, user_prompt: str, temperature: float, top_p: float) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p
        }
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "success",
                    "model_used": model,
                    "response": data.get("message", {}).get("content", ""),
                    "total_duration": data.get("total_duration", 0),
                    "eval_count": data.get("eval_count", 0)
                }
            else:
                # Fallback to secondary model
                logger.warning(f"Primary model {model} failed ({resp.status_code}), attempting fallback {fallback_model}...")
                payload["model"] = fallback_model
                fb_resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
                if fb_resp.status_code == 200:
                    fb_data = fb_resp.json()
                    return {
                        "status": "success",
                        "model_used": fallback_model,
                        "response": fb_data.get("message", {}).get("content", ""),
                        "total_duration": fb_data.get("total_duration", 0),
                        "eval_count": fb_data.get("eval_count", 0)
                    }
                raise HTTPException(status_code=502, detail=f"Ollama inference failed: {resp.text}")
    except Exception as e:
        logger.error(f"Agent routing call error: {e}")
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@router.get("/profiles")
async def get_agent_profiles():
    """Returns active multi-agent task profiles and parameter configurations."""
    return {"status": "success", "profiles": AGENT_PROFILES}

@router.post("/draft")
async def route_creative_draft(req: AgentPromptRequest):
    """
    Creative Narrative & Teleplay Drafting Endpoint.
    Uses high-temperature profile (T=0.75) and injects grounded ChromaDB screenplay context.
    """
    profile = AGENT_PROFILES["creative"]
    temp = req.custom_temperature if req.custom_temperature is not None else profile["temperature"]

    # Attempt to retrieve ChromaDB screenplay context
    rag_context = ""
    try:
        from core.project_rag import get_chroma_client, get_project_collection_name, get_embedding_async
        col_name = get_project_collection_name(req.project_name)
        client = get_chroma_client()
        col = client.get_collection(col_name)
        if col.count() > 0:
            q_emb = await get_embedding_async(req.prompt)
            q_res = col.query(query_embeddings=[q_emb], n_results=min(3, col.count()))
            docs = q_res.get("documents", [[]])[0]
            if docs:
                rag_context = "\n=== RELEVANT PROJECT CONTEXT ===\n" + "\n---\n".join(docs) + "\n\n"
    except Exception as rag_err:
        logger.debug(f"Chroma context skip: {rag_err}")

    system = req.system_instruction or f"""You are the Stehouwer Creative Screenwriting & Narrative Agent.
Your role: Write vivid, emotionally resonant, high-dialogue-fidelity scenes and narrative prose.
Formatting: Output clean, standard Fountain or Screenplay format when generating scenes.
{rag_context}"""

    return await call_ollama(
        model=profile["model"],
        fallback_model=profile["fallback_model"],
        system_prompt=system,
        user_prompt=req.prompt,
        temperature=temp,
        top_p=profile["top_p"]
    )

@router.post("/compile")
async def route_code_compilation(req: AgentPromptRequest):
    """
    Deterministic Code & IPC Compilation Endpoint.
    Uses ultra-low temperature (T=0.10) for strict syntax integrity, zero hallucinations, and valid JSON.
    """
    profile = AGENT_PROFILES["code"]
    temp = req.custom_temperature if req.custom_temperature is not None else profile["temperature"]

    system = req.system_instruction or """You are the AI-BS Systems & Code Compiler Agent.
Your role: Generate production-grade, bug-free code, strict JSON schemas, and exact IPC socket payloads.
Directives:
1. No conversational filler or preamble.
2. Ensure strict type safety and error handling.
3. Obey Windows 11, WSL2, FastAPI, SQLite WAL, and React/Vite standards."""

    return await call_ollama(
        model=profile["model"],
        fallback_model=profile["fallback_model"],
        system_prompt=system,
        user_prompt=req.prompt,
        temperature=temp,
        top_p=profile["top_p"]
    )

@router.post("/noco")
async def route_noco_biomimetics(req: AgentPromptRequest):
    """
    Project NoCo Engineering & Biomimetic Reasoning Endpoint.
    Uses balanced engineering temperature (T=0.30) targeting microgrid thermodynamics and acoustic specs.
    """
    profile = AGENT_PROFILES["noco"]
    temp = req.custom_temperature if req.custom_temperature is not None else profile["temperature"]

    system = req.system_instruction or """You are the Project NoCo Biomimetic & Engineering Copilot.
Your role: Formulate thermodynamic energy equations, microgrid load balances, and acoustic room isolation specs.
Directives:
1. Ground calculations in verified physical constants.
2. Adhere to the NoCo Ideas and Stehouwer Publishing energy balance specifications."""

    return await call_ollama(
        model=profile["model"],
        fallback_model=profile["fallback_model"],
        system_prompt=system,
        user_prompt=req.prompt,
        temperature=temp,
        top_p=profile["top_p"]
    )

@router.post("/route")
async def route_universal_task(req: UniversalRouteRequest):
    """
    Universal Task Classifier & Dispatcher.
    Classifies prompt intent if 'auto' is specified and routes to the appropriate specialized profile.
    """
    task = req.task_type.lower()
    if task == "auto":
        p_lower = req.prompt.lower()
        if any(k in p_lower for k in ["scene", "dialogue", "screenplay", "character", "story", "write", "act ", "chapter"]):
            task = "creative"
        elif any(k in p_lower for k in ["code", "function", "bug", "endpoint", "api", "database", "sqlite", "react", "python"]):
            task = "code"
        elif any(k in p_lower for k in ["noco", "energy", "microgrid", "acoustic", "biomimetic", "subwoofer"]):
            task = "noco"
        else:
            task = "general"

    prompt_req = AgentPromptRequest(prompt=req.prompt, project_name=req.project_name)
    if task == "creative":
        return await route_creative_draft(prompt_req)
    elif task == "code":
        return await route_code_compilation(prompt_req)
    elif task == "noco":
        return await route_noco_biomimetics(prompt_req)
    else:
        profile = AGENT_PROFILES["general"]
        return await call_ollama(
            model=profile["model"],
            fallback_model=profile["fallback_model"],
            system_prompt="You are the Stehouwer AI central executive intelligence.",
            user_prompt=req.prompt,
            temperature=profile["temperature"],
            top_p=profile["top_p"]
        )
