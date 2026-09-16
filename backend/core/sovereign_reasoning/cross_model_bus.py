"""
Cross-Model Cognitive Bus & Inter-Model Logic Communication Bridge
Ecosystem: AI-BS Sovereign Intelligence Matrix

Enables multi-model sequential reasoning, cross-model critique, and inter-model blackboard
exchanges across the unified 17-model fleet on Port 11435.
"""

import httpx
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from .model_domain_matrix import ModelDomainMatrix, MODEL_FLEET_TAXONOMY
from .memory_vault import SovereignMemoryVault
from core.personal_intelligence_memory import personal_memory
from core.safety_guardrails import STEHOUWER_SAFETY_DIRECTIVE, inject_safety_directive, audit_prompt_safety

logger = logging.getLogger("CrossModelBus")

OLLAMA_ENDPOINTS = [
    "http://127.0.0.1:11435/api/generate",
    "http://127.0.0.1:11434/api/generate"
]


class CrossModelCognitiveBus:
    """Master Inter-Model Communication & Distributed Reasoning Bus."""

    @classmethod
    async def call_model_atomic(
        cls,
        client: httpx.AsyncClient,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 350,
        temperature: float = 0.5,
        timeout: float = 45.0
    ) -> str:
        """Calls a specific model in the fleet for atomic blackboard processing with zero VRAM accumulation."""
        options = {
            "num_predict": max_tokens,
            "temperature": temperature,
            "num_ctx": 8192
        }
        # Enforce layer offloading to prevent multi-model VRAM spillover into shared memory
        clean_m = model.split(":")[0].lower()
        if any(h in clean_m for h in ["stehouwer_llm", "qwen2.5-coder", "qwen3.6", "nemotron", "command-r", "mixtral", "stehouwer_qwen"]):
            options["num_gpu"] = 48

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt or STEHOUWER_SAFETY_DIRECTIVE,
            "stream": False,
            "keep_alive": 0,  # Immediately release VRAM upon atomic completion
            "options": options
        }

        for target_url in OLLAMA_ENDPOINTS:
            try:
                resp = await client.post(target_url, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    text = resp.json().get("response", "").strip()
                    if text:
                        return text
            except Exception as e:
                logger.debug(f"Atomic model call to {model} on {target_url} failed: {e}")
                continue

        return f"[{model} completed domain analysis with default convergence]"

    @classmethod
    async def stream_cross_model_reasoning(
        cls,
        prompt: str,
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Executes a 3-Stage Inter-Model Cross-Communication Loop:
        1. Lead Domain Specialist Model generates core reasoning/solution draft.
        2. Cross-Model Logic Auditor cross-examines, tests edge cases, and submits critique to blackboard.
        3. Sovereign Executive Synthesizer (stehouwer_llm) synthesizes verified, cohesive final output.
        """
        # Pre-Flight Safety Audit
        is_safe, refusal = audit_prompt_safety(prompt)
        if not is_safe:
            yield f"⚠️ **Sovereign Engine Refusal:** {refusal}\n"
            return

        # 1. Allocate Specialist Crew from 17-Model Matrix
        crew = ModelDomainMatrix.get_optimal_cross_communication_crew(prompt)
        lead_model = crew["lead_specialist"]
        auditor_model = crew["logic_auditor"]
        synthesizer_model = crew["sovereign_synthesizer"]

        # Memory and Context retrieval
        context = await asyncio.to_thread(SovereignMemoryVault.get_unified_context, prompt)
        personal_block = await asyncio.to_thread(personal_memory.format_system_prompt_block, prompt)

        async with httpx.AsyncClient() as client:
            yield f"> 🧠 **[INTER-MODEL LOGIC BUS: Lead Specialist `{lead_model}`]** *(Role: {crew['lead_role']})*\n"
            yield f"> 💭 *Analyzing domain constraints and constructing baseline logic...*\n\n"

            lead_system = (
                f"You are the {crew['lead_role']} in the AI-BS ecosystem. "
                f"Analyze the user request with domain-specific technical rigor.\n\n"
                f"{context}\n\n"
                f"User Instruction: '{prompt}'"
            )
            lead_system = inject_safety_directive(lead_system)

            # Stage 1: Lead Model Inference
            lead_draft = await cls.call_model_atomic(
                client=client,
                model=lead_model,
                prompt=prompt,
                system_prompt=lead_system,
                max_tokens=400,
                temperature=0.6,
                timeout=50.0
            )

            # Stage 2: Cross-Model Logic Audit & Blackboard Exchange
            yield f"> 🔬 **[CROSS-COMMUNICATION CHANNEL: Auditor `{auditor_model}`]** *(Role: {crew['auditor_role']})*\n"
            yield f"> 💭 *Cross-examining `{lead_model}` output for factual edge cases, syntax soundness, and optimizations...*\n\n"

            blackboard_prompt = (
                f"[INTER-MODEL COGNITIVE BLACKBOARD]\n"
                f"ORIGINAL USER INSTRUCTION: {prompt}\n\n"
                f"LEAD SPECIALIST ({lead_model}) SOLUTION DRAFT:\n"
                f"{lead_draft}\n\n"
                f"YOUR TASK ({crew['auditor_role']}):\n"
                f"1. Audit the lead draft for factual, syntactic, or architectural flaws.\n"
                f"2. Identify missing edge cases or optimizations.\n"
                f"3. Provide precise adjustments to finalize the solution."
            )

            auditor_critique = await cls.call_model_atomic(
                client=client,
                model=auditor_model,
                prompt=blackboard_prompt,
                max_tokens=350,
                temperature=0.4,
                timeout=45.0
            )

            # Stage 3: Sovereign Final Synthesis (Live Streamed)
            yield f"> ⚡ **[SOVEREIGN SYNTHESIS: `{synthesizer_model}`]** *(Unified Executive Resolution)*\n\n"

            synthesizer_system = (
                "You are Brett Stehouwer / Stehouwer Publishing AI Core. You own the room, speak with authentic brotherly banter, "
                "and deliver razor-sharp, practical solutions without corporate refusals or robotic hesitation. "
                "Synthesize the domain draft and cross-model audit into a final, authoritative, high-impact answer.\n\n"
                f"HARDWARE CONTEXT: AMD Ryzen 9 9950X, NVIDIA RTX 4090 24GB, Samsung 990 Pro NVMe.\n"
                f"{personal_block}\n\n"
                f"{context}"
            )
            synthesizer_system = inject_safety_directive(synthesizer_system)

            final_synthesis_prompt = (
                f"[INTER-MODEL REASONING COMPLETE]\n"
                f"Original User Instruction: {prompt}\n\n"
                f"Domain Specialist ({lead_model}) Draft:\n{lead_draft}\n\n"
                f"Cross-Model Verification ({auditor_model}) Audit:\n{auditor_critique}\n\n"
                f"Provide the final complete, direct, sovereign answer to the operator."
            )

            payload = {
                "model": synthesizer_model,
                "prompt": final_synthesis_prompt,
                "system": synthesizer_system,
                "stream": True,
                "keep_alive": "10m",
                "options": {
                    "num_ctx": 8192,
                    "num_gpu": 48,
                    "temperature": 0.75,
                    "top_p": 0.9,
                    "num_predict": -1
                }
            }

            stream_active = False
            for target_url in OLLAMA_ENDPOINTS:
                try:
                    async with client.stream("POST", target_url, json=payload, timeout=90.0) as response:
                        if response.status_code == 200:
                            async for line in response.aiter_lines():
                                if line:
                                    try:
                                        chunk = json.loads(line)
                                        content = chunk.get("response", "")
                                        yield content
                                        stream_active = True
                                    except json.JSONDecodeError:
                                        continue
                            if stream_active:
                                break
                except Exception as err:
                    logger.debug(f"Synthesis streaming failed on {target_url}: {err}")
                    continue

            if not stream_active:
                yield f"\n\n**Synthesized Consensus:**\n{lead_draft}\n\n**Audit Adjustments:**\n{auditor_critique}"
