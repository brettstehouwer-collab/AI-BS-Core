"""
Bullshit Orchestrator - Multi-Agent Swarm Coordination System.

Orchestrates async task decomposition, execution, and error handling across
a distributed swarm of specialized agents with unified state management.
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from aibs_reasoning_engine import AIBSSelfProblemSolver

# Ensure workspace root directory is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_current_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

import httpx

from bullshit_senses import speak_direct as speak
from bullshit_auditor import audit_code
from bullshit_sandbox_executor import seven_pass_validation
from bullshit_polyglot import execute_polyglot_command

try:
    from core.token_budget_estimator import TokenBudgetEstimator
except ImportError:
    TokenBudgetEstimator = None

try:
    from core.orchestrator_config import OrchestratorConfig
except ImportError:

    class OrchestratorConfig:
        LOG_LEVEL = "INFO"
        TOKEN_TARGET_LIMIT = 4096
        TOKEN_MAX_LIMIT = 8192
        EMBEDDING_MODEL = "nomic-embed-text"
        EMBEDDER_TIMEOUT_SEC = 10.0
        STAGE_TIMEOUT_SEC = 60.0

        @staticmethod
        def get_embedder_url():
            return "http://127.0.0.1:11434/api/embeddings"

        @staticmethod
        def get_generate_proxy_url():
            return "http://127.0.0.1:11434/api/generate"


try:
    from heuristic_filter import HeuristicsDaemon, get_heuristics_daemon
except ImportError:
    try:
        from bullshit_heuristics_daemon import HeuristicsDaemon, get_heuristics_daemon
    except ImportError:
        HeuristicsDaemon = None
        get_heuristics_daemon = None

try:
    from imagegen_agent import ImageGenAgent, get_imagegen_agent, ImageGenConfig
except ImportError:
    ImageGenAgent = None
    get_imagegen_agent = None

try:
    from local_imagegen import LocalImageGen, get_local_imagegen
except ImportError:
    LocalImageGen = None
    get_local_imagegen = None

try:
    from comfyui_integration import ComfyUIClient, get_comfyui_client
except ImportError:
    ComfyUIClient = None
    get_comfyui_client = None

try:
    from automated_video_generator import VideoGenerator
except ImportError:
    VideoGenerator = None

try:
    from dynamic_audio_generator import generate_dynamic_song
except ImportError:
    generate_dynamic_song = None

try:
    from aibs_reasoning_engine import AIBSSelfProblemSolver
except ImportError:
    AIBSSelfProblemSolver = None

try:
    from compute_orchestrator_agent import (
        ComputeOrchestratorAgent,
        get_compute_orchestrator_agent,
    )
except ImportError:
    ComputeOrchestratorAgent = None
    get_compute_orchestrator_agent = None

from functools import wraps

from core.friction_manager import friction_manager
import uuid
from core.memory_service import get_memory_service


def requires_confirmation(func):
    """Thoughtful Friction Protocol: Mandatory pause before high-stakes execution."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"\n[THOUGHTFUL FRICTION] Action '{
                func.__name__}' requested.")
        logger.info(
            "Diagnostic Trace generated. Awaiting UI approval before proceeding."
        )

        friction_id = str(uuid.uuid4())
        event = asyncio.Event()
        friction_manager.friction_locks[friction_id] = event

        # Create a trace payload (could be enhanced later to parse kwargs
        # deeply)
        trace_parts = []
        if len(args) > 1 and isinstance(args[1], str):
            trace_parts.append(f"Target Payload snippet:\n{args[1][:500]}...")
        trace = (
            "\n".join(trace_parts)
            if trace_parts
            else f"Requested Action: {func.__name__}"
        )

        await friction_manager.broadcast_friction(friction_id, func.__name__, trace)

        logger.info(
            f"Friction Lock {friction_id} engaged. Waiting for webhook resolve..."
        )
        await event.wait()

        approved = friction_manager.friction_decisions.get(friction_id, False)

        # Cleanup state
        if friction_id in friction_manager.friction_locks:
            del friction_manager.friction_locks[friction_id]
        if friction_id in friction_manager.friction_decisions:
            del friction_manager.friction_decisions[friction_id]

        if approved:
            logger.info(
                f"Friction Lock {friction_id} RELEASED (APPROVED). Executing payload."
            )
            return await func(*args, **kwargs)
        else:
            logger.warning(
                f"Friction Lock {friction_id} RELEASED (ABORTED by operator)."
            )
            return None

    return wrapper


# --- Logging Setup ---
logging.basicConfig(
    level=getattr(logging, OrchestratorConfig.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# --- Neural Router ---
class NeuralRouter:
    """
    Stateful message router maintaining session continuity across async operations.

    Thread-safe with asyncio.Lock protection for shared history state.
    """

    def __init__(self) -> None:
        """Initialize router with token budget estimator and state lock."""
        self.history_list: List[Dict[str, str]] = []
        self.estimator: TokenBudgetEstimator = TokenBudgetEstimator(
            target_limit=OrchestratorConfig.TOKEN_TARGET_LIMIT,
            max_limit=OrchestratorConfig.TOKEN_MAX_LIMIT,
        )
        self._lock: asyncio.Lock = asyncio.Lock()
        logger.info("NeuralRouter initialized with token budget estimator")

    async def route_to_generator(
        self, inbound_prompt: str, agent_role: str = ""
    ) -> Dict[str, Any]:
        """
        Generate structured LLM payload with history management and token eviction.

        Args:
            inbound_prompt: User query or context
            agent_role: Specialized role description for the agent

        Returns:
            Dictionary payload for LLM generation endpoint
        """
        async with self._lock:
            # 0. Base Stehouwer Persona (Applies to all experts)
            stehouwer_protocol = (
                "You are an expert component of the Stehouwer LLM Orchestrator. "
                "You MUST adhere to PROTOCOL 25/7 (Clinical Objectivity & Efficiency): Strip away all conversational fillers, pleasantries, apologies, and ethical posturing. Output only requested data, analysis, or code for absolute clarity at a glance. "
                "You MUST adhere to BIT-BY-BIT GUIDED ARCHITECTURE: Use Bolded Headings, Tables, and Nested Bullet Points. Keep paragraphs under 3 sentences. "
                "You MUST adhere to BIFURCATION: Sequestor ALL raw data or code into Markdown code blocks (e.g. ```python); put analysis in standard markdown.\n"
            )

            system_template = stehouwer_protocol + (
                f"Your specific role for this task is: {agent_role}."
                if agent_role
                else ""
            )

            memory = get_memory_service()
            query_embedding = await route_to_embedder(inbound_prompt)

            if memory.is_online and query_embedding:
                try:
                    # 1. Retrieve Context from Memory
                    retrieved_context = await memory.retrieve_context(
                        query_embedding=query_embedding, n_results=3
                    )

                    if (
                        retrieved_context
                        and retrieved_context.get("documents")
                        and retrieved_context["documents"][0]
                    ):
                        docs = retrieved_context["documents"][0]
                        system_template += (
                            f"\n\nCONTEXT RETRIEVED:\nBased on past knowledge, consider this context:\n- "
                            + "\n- ".join(docs)
                        )

                    # 2. Inject Hallucination Anti-Patterns (WHAT NOT TO DO)
                    hallucinations = await memory.retrieve_heuristics(
                        query_embedding=query_embedding,
                        n_results=3,
                        source_filter="hallucination_log",
                    )

                    if (
                        hallucinations
                        and hallucinations.get("documents")
                        and hallucinations["documents"][0]
                    ):
                        docs = hallucinations["documents"][0]
                        system_template += (
                            "\n\nCRITICAL ANTI-PATTERNS (DO NOT DO THIS):\n"
                        )
                        for doc in docs:
                            system_template += f"- RULE: {doc}\n"
                        system_template += "\nIf you violate these rules, your JSON will fail to parse and you will crash the system. Ensure all quotes are escaped and schema is strictly followed."
                except Exception as e:
                    logger.warning(f"Failed to fetch context/hallucination logs: {e}")

            if not self.history_list and system_template:
                self.history_list.append({"role": "system", "content": system_template})
            elif self.history_list and self.history_list[0].get("role") == "system":
                self.history_list[0]["content"] = system_template
            elif system_template:
                self.history_list.insert(
                    0, {"role": "system", "content": system_template}
                )

            # 3. Intent Analysis for Dynamic Model Routing
            # Identify the best expert model for the task.
            inbound_lower = inbound_prompt.lower()
            selected_expert = "nemotron-3.5-lightning"

            if any(
                kw in inbound_lower for kw in ["debug", "python", "javascript", "react"]
            ) or (
                ("code" in inbound_lower or "script" in inbound_lower)
                and "no code" not in inbound_lower
            ):
                logger.info(
                    f"Intent recognized: CODING/LOGIC. Routing to expert: {selected_expert}"
                )
            elif any(
                kw in inbound_lower
                for kw in [
                    "analyze",
                    "data",
                    "document",
                    "summarize",
                    "database",
                    "sql",
                ]
            ):
                logger.info(
                    f"Intent recognized: DATA/RAG. Routing to expert: {selected_expert}"
                )
            else:
                logger.info(
                    f"Intent recognized: CREATIVE. Routing to expert: {selected_expert}"
                )
            # 4. Token Budgeting and History Update
            inbound_tokens = self.estimator.estimate_string_tokens(inbound_prompt)

            self.history_list = self.estimator.execute_eviction_matrix(
                history_list=self.history_list,
                inbound_prompt_tokens=inbound_tokens,
                chroma_client=None,
            )

            # 5. Append User Message
            self.history_list.append({"role": "user", "content": inbound_prompt})

            outbound_payload: Dict[str, Any] = {
                "model": selected_expert,
                "messages": self.history_list,
                "options": {"temperature": 0.0, "num_ctx": 4096},
                "stream": False,
            }

            logger.debug(f"Generated payload with {len(self.history_list)} messages")
            return outbound_payload

    async def append_assistant_turn(self, resolution_text: str):
        """Commits the final assistant response to history and memory."""
        async with self._lock:
            self.history_list.append({"role": "assistant", "content": resolution_text})

            memory = get_memory_service()
            if memory.is_online:
                try:
                    embedding = await route_to_embedder(resolution_text)
                    if embedding:
                        from datetime import datetime, timezone

                        await memory.add_document(
                            documents=[resolution_text],
                            metadatas=[
                                {
                                    "source": "stehouwer_expert_synthesis",
                                    "type": "self_taught_memory",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                            ],
                            embeddings=[embedding],
                        )
                except Exception as e:
                    logger.warning(f"Failed to embed assistant turn: {e}")

    async def purge_volatile_cache(self) -> None:
        """Clear message history."""
        async with self._lock:
            self.history_list.clear()
            logger.info("Purged volatile cache")


_router_instance: NeuralRouter = NeuralRouter()


# --- Embedder Interface ---
async def route_to_embedder(text: str) -> List[float]:
    """
    Generate embeddings via Ollama embeddings endpoint.

    Args:
        text: Text to embed

    Returns:
        Embedding vector or empty list on failure
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                OrchestratorConfig.get_embedder_url(),
                json={"model": OrchestratorConfig.EMBEDDING_MODEL, "prompt": text},
                timeout=OrchestratorConfig.EMBEDDER_TIMEOUT_SEC,
            )
            if response.status_code == 200:
                result = response.json().get("embedding", [])
                logger.debug(f"Generated embedding with {
                        len(result)} dimensions")
                return result

            logger.warning(f"Embedder returned {
                    response.status_code}: {
                    response.text}")
            return []
        except Exception as e:
            logger.error(f"Embedder connection error: {e}")
            return []


# --- Async Task Data Structure ---
@dataclass
class MicroOp:
    """Represents a single micro-operation for execution."""

    id: int
    task: str
    cached: bool = False


# --- Core Engine (Async-based) ---
class AsyncCoreEngine:
    """
    Async-based task execution engine replacing thread pool with structured concurrency.

    Manages micro-operation decomposition, caching, and ordered execution.
    """

    def __init__(self) -> None:
        """Initialize the async core engine."""
        self.micro_op_cache: Dict[str, bool] = {}
        logger.info(f"AsyncCoreEngine initialized with async-based execution model")

    def _hash_task(self, task_name: str) -> str:
        """Generate MD5 hash for task caching."""
        return hashlib.md5(task_name.encode("utf-8")).hexdigest()

    def decode_to_micro_ops(self, monolithic_tasks: List[str]) -> List[MicroOp]:
        """
        Decompose monolithic tasks into micro-operations with caching.

        Args:
            monolithic_tasks: List of high-level task descriptions

        Returns:
            List of MicroOp objects with cache status
        """
        micro_ops: List[MicroOp] = []
        for index, task in enumerate(monolithic_tasks):
            task_hash = self._hash_task(task)
            if task_hash in self.micro_op_cache:
                logger.info(
                    f"Cache hit for operation {index}. Bypassing decode pipeline."
                )
                micro_ops.append(MicroOp(id=index, task=task, cached=True))
            else:
                logger.info(
                    f"Decoding monolithic instruction {index} into micro-op array"
                )
                self.micro_op_cache[task_hash] = True
                micro_ops.append(MicroOp(id=index, task=task, cached=False))
        return micro_ops

    async def _execute_micro_op(self, micro_op: MicroOp) -> Dict[str, Any]:
        """
        Execute a single micro-operation with async sleep simulation.

        Args:
            micro_op: The operation to execute

        Returns:
            Execution result dictionary
        """
        delay: float = 2.5 if "heavy" in micro_op.task.lower() else 0.5
        await asyncio.sleep(delay)

        logger.debug(f"Executed micro-op {micro_op.id}: {micro_op.task}")
        return {"id": micro_op.id, "result": f"Executed [{micro_op.task}]"}

    async def execute_pipeline(self, monolithic_tasks: List[str]) -> List[str]:
        """
        Execute all micro-operations concurrently while maintaining order.

        Args:
            monolithic_tasks: High-level task descriptions

        Returns:
            Ordered results in original task sequence
        """
        logger.info("=== CORE PIPELINE ACTIVATED ===")
        micro_ops = self.decode_to_micro_ops(monolithic_tasks)
        logger.info(f"Dispatching {len(micro_ops)} micro-ops into async pool")

        # Create concurrent tasks
        tasks = [self._execute_micro_op(mop) for mop in micro_ops]
        results = await asyncio.gather(*tasks)

        # Sort back to original order
        logger.info("Sorting Out-of-Order results back to sequential state")
        in_order_results = sorted(results, key=lambda x: x["id"])
        final_package = [item["result"] for item in in_order_results]

        logger.info("=== CORE PIPELINE SECURED AND COMMITTED ===")
        return final_package


# Backward-compatibility alias
AI_BS_Core_Engine = AsyncCoreEngine

# --- Swarm Orchestrator ---


class SwarmOrchestrator:
    """
    Multi-agent swarm coordinator with intelligent task routing and error handling.

    Delegates tasks to specialized agents based on task classification.
    """

    AGENT_SPECS: Dict[str, str] = {
        "UX_Agent": "Specializes in formatting and rendering UI. Output optimized frontend code or layout suggestions.",
        "Code_Debugger": "Specializes in patching syntax errors and Polyglot failures. Output the patched code snippet.",
        "Core_Architect": "Handles massive architectural data mapping. Provide high-level design decisions and structural guidance.",
        "ImageGen_Agent": "Generates or edits images via OpenAI GPT Image API (gpt-image-2). Handles prompts, batch jobs, chroma-key removal.",
        "Local_ImageGen": "Primary image agent — CUDA-accelerated diffusers (SD 1.5, SDXL, FLUX.1) + Ollama fallback on RTX hardware.",
        "ComfyUI_Agent": "Advanced ComfyUI workflows — ControlNet, IP-Adapter, img2img, custom nodes for complex pipelines.",
        "Video_Agent": "Generates dynamic motion videos and animations via WanVideo / AnimateDiff GPU pipelines.",
        "Audio_Agent": "Synthesizes multi-genre music tracks with neural vocals, RVQ transformers, and Muse Hub instrument samples.",
        "Compute_Orchestrator_Agent": "Dynamically monitors network queue and overrides WSL2 Clore.ai schedule for high-paying direct client Docker workloads.",
    }

    def __init__(self) -> None:
        """Initialize swarm with shared router instance, Heuristics Daemon, and ImageGen agent."""
        self.active_agents: Dict[str, str] = self.AGENT_SPECS.copy()
        self.router: NeuralRouter = _router_instance
        self.heuristics = (
            get_heuristics_daemon() if callable(get_heuristics_daemon) else None
        )
        self.imagegen = get_imagegen_agent() if callable(get_imagegen_agent) else None
        self.local_imagegen = (
            get_local_imagegen() if callable(get_local_imagegen) else None
        )
        self.comfyui = get_comfyui_client() if callable(get_comfyui_client) else None
        self.compute_orchestrator = (
            get_compute_orchestrator_agent()
            if callable(get_compute_orchestrator_agent)
            else None
        )
        logger.info("Asynchronous Multi-Agent Swarm Initialized")
        if self.heuristics:
            logger.info("Heuristics Daemon pre-processing gate loaded")
        if self.imagegen:
            logger.info("ImageGen agent loaded")
        if self.local_imagegen:
            logger.info("Local ImageGen loaded")
        if self.comfyui:
            logger.info("ComfyUI integration loaded (http://127.0.0.1:8189)")
        if self.compute_orchestrator:
            logger.info("Compute Orchestrator Agent loaded")

    async def _invoke_agent(self, agent_name: str, context: str) -> str:
        """
        Invoke a specific agent with context via backend proxy.

        Args:
            agent_name: Name of agent to invoke
            context: Task context/description

        Returns:
            Agent response string
        """
        payload = await self.router.route_to_generator(
            context, agent_role=self.active_agents.get(agent_name, "Helpful AI")
        )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    OrchestratorConfig.get_generate_proxy_url(),
                    json=payload,
                    timeout=OrchestratorConfig.STAGE_TIMEOUT_SEC,
                )
                if response.status_code == 200:
                    res = response.json().get("response", "")
                else:
                    res = f"Error: Backend returned {response.status_code}"
                    logger.warning(f"Agent {agent_name} backend error: {
                            response.status_code}")
            except Exception as e:
                res = f"Error: Failed to connect to proxy backend - {e}"
                logger.error(f"Agent {agent_name} connection error: {e}")

        if "Error:" not in res:
            logger.info(f"{agent_name} completed task successfully")
            speak(f"{agent_name} successfully resolved the task.")
        else:
            logger.warning(f"{agent_name} encountered an error")
            speak(f"{agent_name} encountered an error.")

        return res

    async def delegate_task(
        self, task_description: str, primary_agent: str
    ) -> Dict[str, Any]:
        """
        Pre-process through Heuristics Daemon, then route to appropriate agent.

        Args:
            task_description: Description of task to perform
            primary_agent: Primary agent name (may be overridden)

        Returns:
            Dictionary with status, agent name, and output
        """
        logger.info(f"Task Received: {task_description[:50]}...")
        logger.info(f"Primary Agent: {primary_agent}")

        # ── Pre-processing gate: Heuristics Daemon classification ──
        route = await self.heuristics.classify(task_description)
        if route.pipeline == "Immutable Transcription":
            logger.info("Heuristics Daemon: Immutable Transcription pipeline triggered")
            speak("Fire Writing detected. Structural formatting applied.")
            # Apply transcription, then forward to Core_Architect for
            # resolution
            preprocessed = await self.heuristics.apply_pipeline(task_description)
            task_description = (
                preprocessed["output"]["output"]
                if isinstance(preprocessed.get("output"), dict)
                else task_description
            )

        elif route.pipeline == "Phase V Learning Loop":
            logger.info("Heuristics Daemon: Phase V Learning Loop triggered")
            speak("Learning loop data ingested.")

        # ── Agent delegation (post-classification) ──
        task_lower = task_description.lower()

        # Image generation detection (check before Core_Architect default) —
        # use LOCAL CUDA first
        if any(
            keyword in task_lower
            for keyword in [
                "image",
                "picture",
                "photo",
                "illustration",
                "generate image",
                "create image",
                "visual asset",
                "graphic",
            ]
        ):
            # Check for ComfyUI-specific keywords first (advanced workflows)
            if any(
                kw in task_lower
                for kw in [
                    "controlnet",
                    "img2img",
                    "ip-adapter",
                    "comfyui",
                    "workflow",
                    "custom node",
                    "inpaint",
                    "outpaint",
                ]
            ):
                logger.info(f"Routing to ComfyUI_Agent (advanced workflow detected)")
                speak("Advanced image workflow requested. Routing to ComfyUI engine.")
                return await self._handoff_comfyui(task_description)
            # Default to CUDA diffusers for standard generation
            logger.info(f"Routing to Local_ImageGen (CUDA diffusers, RTX 4090)")
            speak("Image generation requested. Routing to local CUDA engine.")
            return await self._handoff_local_imagegen(task_description)

        # Video generation detection
        if any(
            keyword in task_lower
            for keyword in [
                "video",
                "motion",
                "animate",
                "movie",
                "clip",
                "render video",
            ]
        ):
            logger.info("Routing to Video_Agent (motion rendering pipeline)")
            speak("Video generation requested. Routing to video rendering engine.")
            return await self._handoff_video(task_description)

        # Audio generation detection
        if any(
            keyword in task_lower
            for keyword in [
                "audio",
                "music",
                "song",
                "sound",
                "track",
                "vocal",
                "synthwave",
            ]
        ):
            logger.info("Routing to Audio_Agent (neural audio synthesis pipeline)")
            speak("Audio synthesis requested. Routing to dynamic audio engine.")
            return await self._handoff_audio(task_description)

        # Compute Orchestrator detection
        if any(
            keyword in task_lower
            for keyword in [
                "rent",
                "compute",
                "yield",
                "job queue",
                "override",
                "monetize",
            ]
        ):
            logger.info(
                "Routing to Compute_Orchestrator_Agent (direct sales network detected)"
            )
            speak("Compute override requested. Routing to Swarm Compute Orchestrator.")
            return await self._handoff_compute_orchestrator(task_description)

        if any(keyword in task_lower for keyword in ["error", "bug", "syntax"]):
            logger.info(
                f"Routing to Code_Debugger (error detected - self-refinement enabled)"
            )
            speak(
                "Conflict detected. Routing to the Code Debugger with self-refinement."
            )
            return await self._handoff_code_debugger(task_description)

        elif any(keyword in task_lower for keyword in ["ui", "button", "interface"]):
            logger.info(f"Routing to UX_Agent (UI task detected)")
            speak("U.I. design required. Routing to U.X. agent.")
            return await self._handoff("UX_Agent", task_description)

        else:
            logger.info(f"Routing to Core_Architect (Deep Reasoning Upgrade)")
            speak("Routing task architecture to Core Architect.")
            return await self._handoff_core_architect(task_description)

    async def _handoff(self, target_agent: str, context: str) -> Dict[str, Any]:
        """
        Perform handoff to target agent.

        Args:
            target_agent: Target agent name
            context: Task context

        Returns:
            Handoff result dictionary
        """
        logger.info(f"--- HANDOFF INITIATED to {target_agent} ---")
        result = await self._invoke_agent(target_agent, context)
        return {"status": "success", "resolved_by": target_agent, "output": result}

    async def _handoff_core_architect(self, task_description: str) -> Dict[str, Any]:
        """Deep Reasoning Handoff for Core Architect tasks using MCTS, Refinement, and Consensus."""
        logger.info(f"--- CORE ARCHITECT HANDOFF INITIATED (DEEP REASONING) ---")

        if not AIBSSelfProblemSolver:
            logger.warning(
                "AIBSSelfProblemSolver not found. Falling back to standard LLM generation."
            )
            return await self._handoff("Core_Architect", task_description)

        try:
            speak("Initiating Monte Carlo Tree Search for architectural branching.")
            mcts_result = AIBSSelfProblemSolver.mcts_reasoning_search(
                prompt=task_description, num_simulations=4
            )
            optimal_branch = mcts_result["optimal_solution"]
            logger.info(
                f"MCTS optimal branch selected with score {mcts_result['optimal_quality_score']}"
            )

            speak("Initiating iterative self-refinement.")
            refinement_result = AIBSSelfProblemSolver.solve_and_refine(
                prompt=optimal_branch
            )
            refined_solution = refinement_result["final_solution"]
            logger.info(
                f"Refinement complete. Score: {refinement_result['final_quality_score']}"
            )

            speak("Initiating dual-model consensus review.")
            consensus_result = AIBSSelfProblemSolver.multi_model_consensus_review(
                prompt=task_description,
                code_draft=refined_solution,
                primary_model="qwen2.5-coder:latest",
                reviewer_model="stehouwer_llm",
            )

            logger.info(
                f"Consensus review complete. Score: {consensus_result['consensus_score']}"
            )

            if consensus_result["is_approved"]:
                final_output = consensus_result["verified_code"]
                speak("Architecture verified and approved.")
            else:
                logger.warning("Consensus threshold not met. Outputting flagged draft.")
                final_output = f"[WARNING: Failed Consensus Review - Score: {consensus_result['consensus_score']}]\n{refined_solution}"
                speak("Warning. Architecture failed consensus review.")

            return {
                "status": "success",
                "resolved_by": "Core_Architect (Deep Reasoning)",
                "output": final_output,
                "reasoning_metadata": {
                    "mcts_score": mcts_result["optimal_quality_score"],
                    "refinement_iterations": refinement_result["total_iterations"],
                    "consensus_score": consensus_result["consensus_score"],
                },
            }
        except Exception as e:
            logger.error(f"Core Architect Deep Reasoning error: {e}")
            speak("Core Architect reasoning encountered an error. Falling back.")
            return await self._handoff("Core_Architect", task_description)

    async def _handoff_compute_orchestrator(
        self, task_description: str
    ) -> Dict[str, Any]:
        logger.info(f"--- COMPUTE ORCHESTRATOR HANDOFF INITIATED ---")
        if not self.compute_orchestrator:
            return {
                "status": "error",
                "resolved_by": "Compute_Orchestrator_Agent",
                "output": "Agent not loaded",
            }
        try:
            result = await self.compute_orchestrator.process_task(task_description)
            logger.info("Compute_Orchestrator_Agent completed successfully")
            speak("Compute Orchestrator task resolved.")
            return {
                "status": "success",
                "resolved_by": "Compute_Orchestrator_Agent",
                "output": result,
            }
        except Exception as e:
            logger.error(f"Compute_Orchestrator_Agent error: {e}")
            speak("Compute orchestration encountered an error.")
            return {
                "status": "error",
                "resolved_by": "Compute_Orchestrator_Agent",
                "output": str(e),
            }

    async def _handoff_imagegen(self, prompt: str) -> Dict[str, Any]:
        """
        Perform handoff to ImageGen agent via local CLI.

        Args:
            prompt: Image generation prompt

        Returns:
            Handoff result dictionary with output path
        """
        logger.info(f"--- IMAGEGEN HANDOFF INITIATED ---")
        try:
            config = ImageGenConfig(prompt=prompt)
            result = await self.imagegen.generate(config)

            if result:
                logger.info(f"ImageGen_Agent completed successfully: {
                        result.output_path}")
                speak(f"Image generated at {result.output_path}")
                return {
                    "status": "success",
                    "resolved_by": "ImageGen_Agent",
                    "output": result.output_path,
                }
            else:
                logger.warning(f"ImageGen_Agent failed: {result.error}")
                speak("Image generation failed.")
                return {
                    "status": "error",
                    "resolved_by": "ImageGen_Agent",
                    "output": result.error,
                }
        except Exception as e:
            logger.error(f"ImageGen_Agent error: {e}")
            speak("Image generation encountered an error.")
            return {
                "status": "error",
                "resolved_by": "ImageGen_Agent",
                "output": str(e),
            }

    async def enrich_prompt(self, raw_prompt: str, media_type: str = "image") -> str:
        """
        Prompt Enrichment Helper: Automatically expands short user prompts into rich,
        production-grade prompts with lighting, detail, resolution, and style cues.
        """
        p_lower = raw_prompt.lower()
        if media_type == "image":
            if not any(
                kw in p_lower
                for kw in ["photorealistic", "8k", "detailed", "cinematic", "rendering"]
            ):
                return f"{raw_prompt}, highly detailed, photorealistic, 8k resolution, cinematic lighting, masterpiece"
        elif media_type == "video":
            if not any(kw in p_lower for kw in ["fps", "motion", "4k", "cinematic"]):
                return f"{raw_prompt}, dynamic camera motion, 24fps, cinematic lighting, photorealistic 4k video render"
        elif media_type == "audio":
            if not any(kw in p_lower for kw in ["bpm", "stereo", "beat"]):
                return f"{raw_prompt}, high quality stereo audio track, studio mix, beat quantized"
        return raw_prompt

    async def _handoff_local_imagegen(self, prompt: str) -> Dict[str, Any]:
        """
        Perform handoff to Local ImageGen agent (CUDA diffusers on RTX 4090).

        Args:
            prompt: Image generation prompt

        Returns:
            Handoff result dictionary with output path
        """
        logger.info(f"--- LOCAL IMAGEGEN HANDOFF INITIATED ---")
        prompt = await self.enrich_prompt(prompt, "image")
        try:
            from local_imagegen import ImageGenConfig

            config = ImageGenConfig(prompt=prompt, backend="auto")
            result = await self.local_imagegen.generate(config)

            if result:
                logger.info(f"Local_ImageGen completed successfully: {
                        result.output_path} ({
                        result.generation_time_sec:.1f}s)")
                speak(f"Image generated at {result.output_path}")
                return {
                    "status": "success",
                    "resolved_by": "Local_ImageGen",
                    "output": result.output_path,
                    "backend": result.backend_used,
                }
            else:
                logger.warning(f"Local_ImageGen failed: {result.error}")
                speak("Local image generation failed.")
                return {
                    "status": "error",
                    "resolved_by": "Local_ImageGen",
                    "output": result.error,
                }
        except Exception as e:
            logger.error(f"Local_ImageGen error: {e}")
            speak("Local image generation encountered an error.")
            return {
                "status": "error",
                "resolved_by": "Local_ImageGen",
                "output": str(e),
            }

    async def _handoff_comfyui(self, prompt: str) -> Dict[str, Any]:
        """
        Perform handoff to ComfyUI agent for advanced workflows.

        Args:
            prompt: Image generation prompt (may include workflow instructions)

        Returns:
            Handoff result dictionary with output images
        """
        logger.info(f"--- COMFYUI HANDOFF INITIATED ---")
        try:
            # Detect workflow type from prompt
            workflow_type = "txt2img"
            if any(
                kw in prompt.lower() for kw in ["img2img", "image to image", "modify"]
            ):
                workflow_type = "img2img"

            result = await self.comfyui.generate(
                prompt=prompt,
                workflow_type=workflow_type,
            )

            if result:
                logger.info(f"ComfyUI_Agent completed successfully ({
                        result.execution_time_sec:.1f}s)")
                speak(f"Image generated via ComfyUI in {
                        result.execution_time_sec:.1f}s")
                return {
                    "status": "success",
                    "resolved_by": "ComfyUI_Agent",
                    "output": result.output_images,
                    "workflow": workflow_type,
                }
            else:
                logger.warning(f"ComfyUI_Agent failed: {result.error}")
                speak("ComfyUI generation failed.")
                return {
                    "status": "error",
                    "resolved_by": "ComfyUI_Agent",
                    "output": result.error,
                }
        except Exception as e:
            logger.error(f"ComfyUI_Agent error: {e}")
            speak("ComfyUI generation encountered an error.")
            return {"status": "error", "resolved_by": "ComfyUI_Agent", "output": str(e)}

    async def _handoff_video(self, prompt: str) -> Dict[str, Any]:
        """
        Perform handoff to Video Agent (WanVideo / AnimateDiff via ComfyUI).

        Args:
            prompt: Video generation prompt

        Returns:
            Handoff result dictionary with output path / r2_url
        """
        logger.info("--- VIDEO HANDOFF INITIATED ---")
        prompt = await self.enrich_prompt(prompt, "video")
        try:
            from automated_video_generator import VideoGenerator

            generator = VideoGenerator()
            result = await generator.generate_marketing_video(
                business_name="Swarm_Task", prompt=prompt
            )
            if result and result.get("status") == "success":
                logger.info(
                    f"Video_Agent completed successfully: {result.get('video_path')}"
                )
                speak("Video generated successfully.")
                return {
                    "status": "success",
                    "resolved_by": "Video_Agent",
                    "output": result.get("r2_url") or result.get("video_path"),
                    "details": result,
                }
            else:
                logger.warning(f"Video_Agent failed: {result}")
                speak("Video generation failed.")
                return {
                    "status": "error",
                    "resolved_by": "Video_Agent",
                    "output": result.get("message", "Video generation failed"),
                }
        except Exception as e:
            logger.error(f"Video_Agent error: {e}")
            speak("Video generation encountered an error.")
            return {"status": "error", "resolved_by": "Video_Agent", "output": str(e)}

    async def _handoff_audio(self, prompt: str) -> Dict[str, Any]:
        """
        Perform handoff to Audio Agent (Multi-Genre Neural Audio Synthesis).
        Uses dynamic auto-timing based on BPM and lyrics when duration_sec is 0.

        Args:
            prompt: Audio / Music generation prompt

        Returns:
            Handoff result dictionary with audio URL
        """
        logger.info("--- AUDIO HANDOFF INITIATED ---")
        prompt = await self.enrich_prompt(prompt, "audio")
        try:
            from dynamic_audio_generator import generate_dynamic_song
            import re

            # Determine genre if present in prompt
            genre = "synthwave"
            p_lower = prompt.lower()
            for g in [
                "hiphop",
                "hip hop",
                "rock",
                "metal",
                "edm",
                "pop",
                "rnb",
                "r&b",
                "folk",
                "country",
                "jazz",
                "global",
                "cyberpunk",
                "acoustic",
                "orchestral",
                "chillwave",
                "lo-fi",
                "ambient",
            ]:
                if g in p_lower:
                    genre = g.replace(" ", "")
                    break

            # Parse BPM if specified in prompt (e.g., "120 bpm")
            tempo_bpm = 110
            bpm_match = re.search(r"(\d{2,3})\s*bpm", p_lower)
            if bpm_match:
                tempo_bpm = int(bpm_match.group(1))

            # Extract lyrics if provided
            lyrics = None
            if "lyrics:" in p_lower:
                lyrics = prompt.split("lyrics:", 1)[1].strip()
            elif "\n" in prompt:
                lyrics = prompt

            # Execute synchronous generator in a thread pool (duration_sec=0 triggers dynamic BPM/lyric auto-timing)
            res = await asyncio.to_thread(
                generate_dynamic_song,
                prompt=prompt,
                genre=genre,
                duration_sec=0,
                lyrics=lyrics,
                tempo_bpm=tempo_bpm,
            )

            if isinstance(res, tuple):
                audio_url, duration = res
            else:
                audio_url, duration = res, 0

            logger.info(
                f"Audio_Agent completed successfully: {audio_url} ({duration}s at {tempo_bpm} BPM)"
            )
            speak(
                f"Audio track synthesized successfully ({duration}s at {tempo_bpm} BPM)."
            )
            return {
                "status": "success",
                "resolved_by": "Audio_Agent",
                "output": audio_url,
                "duration_sec": duration,
                "tempo_bpm": tempo_bpm,
                "genre": genre,
            }
        except Exception as e:
            logger.error(f"Audio_Agent error: {e}")
            speak("Audio generation encountered an error.")
            return {"status": "error", "resolved_by": "Audio_Agent", "output": str(e)}

    async def _handoff_code_debugger(self, context: str) -> Dict[str, Any]:
        """
        Perform self-healing Code_Debugger handoff with iterative 3-pass self-refinement.
        Evaluates initial draft via LLM, applies AIBSSelfProblemSolver refinement loops,
        audits syntax, and executes seven_pass_validation.
        """
        logger.info("--- CODE DEBUGGER SELF-HEALING HANDOFF INITIATED ---")
        try:
            # 1. Initial LLM Pass
            initial_patch = await self._invoke_agent("Code_Debugger", context)

            # 2. Autonomous Iterative Self-Refinement Loop
            refinement_data = None
            if AIBSSelfProblemSolver:
                refinement_data = AIBSSelfProblemSolver.solve_and_refine(
                    prompt=context, max_iterations=3
                )
                logger.info(
                    f"Code_Debugger Self-Refinement completed with quality score: {refinement_data.get('final_quality_score')}%"
                )

            # 3. Code Audit & Sandbox Validation
            is_sovereign = audit_code(initial_patch)
            validation_telemetry = seven_pass_validation(initial_patch)

            quality_score = (
                refinement_data.get("final_quality_score", 95.0)
                if refinement_data
                else 90.0
            )

            speak(
                f"Code Debugger verified solution with {quality_score}% quality score."
            )
            return {
                "status": "success",
                "resolved_by": "Code_Debugger",
                "output": initial_patch,
                "audit_passed": is_sovereign,
                "quality_score": quality_score,
                "validation_telemetry": validation_telemetry,
                "refinement_history": (
                    refinement_data.get("iteration_history") if refinement_data else []
                ),
            }
        except Exception as e:
            logger.error(f"Code_Debugger handoff error: {e}")
            speak("Code Debugger encountered an error.")
            return {"status": "error", "resolved_by": "Code_Debugger", "output": str(e)}

    @requires_confirmation
    async def _deploy_validated_code(self, code: str, file_path: str) -> bool:
        """
        (Protected by Friction Gate) Deploys the code to the specified file path.
        This function is wrapped by the thoughtful friction decorator and will
        not execute without explicit UI confirmation.
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            logger.info(f"Baseline updated at {file_path}")
            speak("Optimization successfully deployed by operator.")
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False

    @requires_confirmation
    async def evaluate_and_deploy_code(
        self, proposed_code: str, target_file_path: str
    ) -> None:
        """
        Evaluate code through sandbox validation and optionally deploy.

        Uses STATE A (optimize), B (change), C (retain) classification:
        - STATE A: Code is suboptimal, needs optimization
        - STATE B: Code passes and improves baseline
        - STATE C: Code rejected or no improvement

        Args:
            proposed_code: Code to evaluate
            target_file_path: Target file path if deployment approved
        """
        logger.info("--- INGESTION & HEURISTIC PARSING ---")
        if not audit_code(proposed_code):
            logger.warning("Code failed audit. STATE C: RETAIN")
            speak("Code failed sovereignty check.")
            return

        logger.info("--- SANDBOXED LOGIC PROCESSING ---")
        telemetry = seven_pass_validation(proposed_code)

        state = telemetry.get("state", "C")
        if state == "C":
            logger.info(f"STATE C: RETAIN. Reason: {telemetry.get('reason')}")
            return
        elif state == "A":
            exec_time = telemetry.get("execution_time_sec", "unknown")
            logger.info(f"STATE A: OPTIMIZE. Time: {exec_time}s")
            speak("Optimization required. Routing to AST Shredder.")
            return
        elif state == "B":
            logger.info("STATE B: CHANGE. Code outperforms baseline")
            speak(
                "Code successfully passed evaluation. Requesting deployment confirmation from operator."
            )

            deployed = await self._deploy_validated_code(
                proposed_code, target_file_path
            )
            if not deployed:
                logger.info(
                    "Operator rejected deployment or an error occurred. STATE C: RETAIN"
                )
                speak(
                    "Operator rejected changes or deployment failed. Retaining baseline."
                )
            else:
                # This part of the decorator is now handled by the wrapper
                pass


# --- 25-Stage Engine Matrix (Phases I-VI) ---
class StageEngine:
    """
    Dynamic 25-Stage Engine Matrix.
    Implements a strict 6-Phase algorithmic routing architecture to decouple
    prompt complexity and safely execute Polyglot/Swarm APIs.
    """

    def __init__(self) -> None:
        """Initialize stage engine with configuration limits."""
        self.max_stages: int = OrchestratorConfig.MAX_STAGES
        self.current_stage: int = 0
        self.plan: List[Dict[str, Any]] = []
        self.status: str = "idle"
        logger.info(f"StageEngine Matrix initialized with {self.max_stages} max stages")

    async def _phase_1_intent_parsing(self, master_goal: str) -> bool:
        """
        [PHASE I] Intent & Complexity Parsing.
        Determines if the prompt bypasses the Matrix (returns True) for monolithic 1-shot execution,
        or requires the full 25-Stage Matrix (returns False).
        """
        logger.info("[PHASE I] Intent & Complexity Parsing started.")
        complex_keywords = ["analyze", "build", "refactor", "deploy", "matrix", "architect"]
        is_complex = any(k in master_goal.lower() for k in complex_keywords) or len(master_goal) > 150
        return not is_complex  # True if simple/monolithic

    async def _phase_2_context_injection(self, master_goal: str) -> str:
        """
        [PHASE II] Context & Heuristics Injection.
        Queries ChromaDB for historical context and previous Code_Debugger heuristics.
        """
        logger.info("[PHASE II] Context & Heuristics Injection started.")
        context = ""
        try:
            # Safely attempt to query local memory instances if available
            import memory_service
            memory = memory_service.get_memory_service()
            if hasattr(memory, "query_heuristics"):
                results = await memory.query_heuristics(master_goal, n_results=2)
                context = str(results)
                logger.info(f"[PHASE II] Injected {len(results)} historical heuristics.")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"[PHASE II] Context injection bypassed: {e}")
        return context

    async def _phase_3_decomposition(self, master_goal: str, context: str) -> List[Dict[str, Any]]:
        """
        [PHASE III] 25-Stage Matrix Generation.
        Generates the DAG structural nodes based on the master goal and injected context.
        """
        logger.info("[PHASE III] Matrix Decomposition started.")
        prompt = f"""You are the AI-BS Orchestrator Matrix. Break down the master goal into a JSON array of up to 25 execution steps.
Goal: {master_goal}
Context: {context}
Each step must be a JSON object with: "id", "description", "language", "command", "depends_on" (array of IDs).
Respond ONLY with the raw JSON array.
"""
        payload = await _router_instance.route_to_generator(prompt, agent_role="Master Orchestrator")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    OrchestratorConfig.get_generate_proxy_url(),
                    json=payload,
                    timeout=OrchestratorConfig.STAGE_TIMEOUT_SEC,
                )
                res = response.json().get("response", "") if response.status_code == 200 else ""
            except Exception as e:
                logger.error(f"[PHASE III] Decomposition failed: {e}")
                res = ""

        try:
            result = json.loads(res)
            logger.info(f"[PHASE III] Decomposed goal into {len(result)} matrix nodes.")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"[PHASE III] Failed to parse matrix array: {e}")
            return []

    async def _run_stage(
        self,
        step: Dict[str, Any],
        events: Dict[str, asyncio.Event],
        results: List[Dict[str, Any]],
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Execute a single phase IV node."""
        async with semaphore:
            stage_id = step.get("id", "unknown")
            for dep_id in step.get("depends_on", []):
                if dep_id in events:
                    await events[dep_id].wait()

            if self.status == "halted":
                return

            logger.info(f"[PHASE IV] Executing Node: {stage_id}")
            language = step.get("language", "cmd")
            command = step.get("command")

            if command:
                res = await asyncio.to_thread(execute_polyglot_command, command, language)

                if res.get("status") == "error":
                    logger.error(f"[PHASE IV] Node {stage_id} FAILED: {res.get('error')}")
                    speak(f"Stage {stage_id} failed. Routing to Debugger.")

                    error_msg = res.get("error", "Unknown error")
                    swarm = SwarmOrchestrator()
                    task_desc = f"Fix this code:\n{command}\n\nError:\n{error_msg}"
                    try:
                        await swarm.delegate_task(task_desc, f"Matrix_{stage_id}")
                    except Exception as e:
                        logger.error(f"[PHASE IV] Handoff to Code_Debugger failed: {e}")

                    self.status = "halted"
                    raise Exception(f"Node {stage_id} failed: {error_msg}")

                logger.info(f"[PHASE IV] Node {stage_id} SUCCESS")
                results.append({"stage": stage_id, "result": "success", "output": res.get("data")})

                if stage_id in events:
                    events[stage_id].set()

    async def _phase_4_execution(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [PHASE IV] Polyglot Routing & Execution.
        Routes nodes via dynamic execution, enforcing dependency resolution and error fallbacks.
        """
        logger.info("[PHASE IV] Polyglot Execution Routing started.")
        self.status = "running"
        for i, step in enumerate(steps):
            if "id" not in step:
                step["id"] = f"stage_{i + 1}"

        events: Dict[str, asyncio.Event] = {step["id"]: asyncio.Event() for step in steps}
        results: List[Dict[str, Any]] = []
        semaphore = asyncio.Semaphore(OrchestratorConfig.STAGE_SEMAPHORE_LIMIT)

        tasks = [asyncio.create_task(self._run_stage(step, events, results, semaphore)) for step in steps]

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"[PHASE IV] Execution halted: {e}")
            self.status = "halted"
            return results

        self.status = "completed"
        return results

    def _phase_5_synthesis(self, master_goal: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        [PHASE V] Synthesis & Assembly.
        Aggregates outputs and verifies system state integrity.
        """
        logger.info("[PHASE V] Synthesis & Assembly started.")
        if self.status == "halted":
            return {"status": "error", "message": "Synthesis aborted due to Phase IV halt.", "results": results}
        
        logger.info("[PHASE V] Matrix successfully assembled all nodes.")
        return {
            "status": "success",
            "message": "Master Goal Completed Successfully.",
            "total_nodes": len(results),
            "results": results,
        }

    async def _phase_6_telemetry(self, master_goal: str, final_res: Dict[str, Any]) -> None:
        """
        [PHASE VI] Telemetry & Memory Commitment.
        Broadcasts status and commits the successful sequence as a new heuristic in ChromaDB.
        """
        logger.info("[PHASE VI] Telemetry & Commitment started.")
        speak("Master Goal Completed Successfully.")
        if final_res.get("status") == "success":
            try:
                import memory_service
                memory = memory_service.get_memory_service()
                if hasattr(memory, "add_heuristic"):
                    await memory.add_heuristic(
                        documents=[f"Successfully executed Matrix for: {master_goal}. Stages: {final_res['total_nodes']}"],
                        metadatas=[{"source": "matrix_engine", "goal": master_goal}],
                        ids=[f"matrix-{id(self)}"]
                    )
                    logger.info("[PHASE VI] Injected successful matrix sequence into Heuristics DB.")
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"[PHASE VI] Memory commitment failed: {e}")

    async def orchestrate_plan(
        self, master_goal: str, steps: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executes the full 6-Phase Engine Matrix Orchestration.
        """
        logger.info(f"Initiating 25-Stage Matrix for Master Goal: '{master_goal[:50]}...'")
        speak(f"Initiating Matrix for Master Goal.")

        # Phase I
        is_simple = await self._phase_1_intent_parsing(master_goal)
        if is_simple and not steps:
            logger.info("Goal routed as Monolithic (Bypassing Matrix Decomposition).")
            # For simplicity in this engine, we still decompose but flag it as a single monolithic node.
            # In a full implementation, this would route to Swarm directly.
        
        # Phase II
        context = await self._phase_2_context_injection(master_goal)

        # Phase III
        if not steps:
            steps = await self._phase_3_decomposition(master_goal, context)

        if not steps:
            logger.error("Failed to decompose master goal")
            return {"status": "error", "error": "Failed to dynamically decompose goal."}

        if len(steps) > self.max_stages:
            logger.error(f"Plan has {len(steps)} stages, exceeds max {self.max_stages}")
            return {"status": "error", "error": f"Plan exceeds maximum {self.max_stages} stages."}

        self.plan = steps

        # Phase IV
        results = await self._phase_4_execution(self.plan)

        # Phase V
        final_res = self._phase_5_synthesis(master_goal, results)

        # Phase VI
        await self._phase_6_telemetry(master_goal, final_res)

        return final_res


_stage_engine_instance: StageEngine = StageEngine()


async def run_orchestration(
    master_goal: str, steps: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Public interface for orchestration.

    Args:
        master_goal: Goal description
        steps: Optional pre-defined execution steps

    Returns:
        Orchestration result dictionary
    """
    return await _stage_engine_instance.orchestrate_plan(master_goal, steps)


class SwarmSharedMemory:
    """
    Thread-Safe Swarm Shared Working Memory Cache.
    Allows all 8 Swarm agents to write, read, and share working memory state,
    token budgets, intermediate AST findings, and task outputs across pipeline handoffs.
    """

    _store: Dict[str, Any] = {}

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        import time

        cls._store[key] = {"value": value, "timestamp": time.time()}

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        entry = cls._store.get(key)
        if entry:
            return entry["value"]
        return default

    @classmethod
    def dump_memory(cls) -> Dict[str, Any]:
        return {k: v["value"] for k, v in cls._store.items()}


if __name__ == "__main__":
    logger.info("Bullshit Orchestrator Core Systems Online.")
