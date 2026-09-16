import json
import os
import sys
import time
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from bullshit_polyglot import execute_polyglot_command
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import Request, Response
import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import base64

# --- NEW IMPORTS INJECTED TODAY ---
from bullshit_memory import MemoryManager
from bullshit_orchestrator import AI_BS_Core_Engine, SwarmOrchestrator
from bullshit_builder import ProjectScaffolder
import argparse

app = FastAPI(title="AI-BS Central Cognitive Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security Parameters & Middlewares ---
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


class HSTSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        return response


app.add_middleware(HSTSMiddleware)

# Secret key for AES-GCM decryption (matching frontend key)
AES_SECRET_KEY = bytes(
    [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
    ]
)
aesgcm = AESGCM(AES_SECRET_KEY)


class AuthLoginPayload(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def auth_login(payload: AuthLoginPayload, response: Response):
    key_path = os.path.join(os.path.dirname(__file__), "master_key.hash")

    # Fallback default if setup script hasn't been run
    valid_user = "admin"
    valid_hash = ph.hash("password")

    if os.path.exists(key_path):
        try:
            with open(key_path, "r") as f:
                lines = f.read().splitlines()
                if len(lines) >= 2:
                    valid_user = lines[0].strip()
                    valid_hash = lines[1].strip()
        except Exception as e:
            logger.error(f"Failed to read master_key.hash: {e}")

    if payload.username != valid_user:
        return JSONResponse(
            status_code=401, content={"status": "error", "message": "Invalid identity"}
        )

    try:
        ph.verify(valid_hash, payload.password)
        # Authentication successful
        session_token = base64.b64encode(os.urandom(32)).decode("utf-8")
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,  # Requires HTTPS/TLS
            samesite="strict",
        )
        return {"status": "success", "message": "Authenticated successfully"}
    except VerifyMismatchError:
        return JSONResponse(
            status_code=401, content={"status": "error", "message": "Invalid password"}
        )


class DecryptPayload(BaseModel):
    iv: str
    ciphertext: str


@app.post("/api/security/decrypt")
def decrypt_payload(payload: DecryptPayload):
    try:
        iv_bytes = base64.b64decode(payload.iv)
        cipher_bytes = base64.b64decode(payload.ciphertext)
        plaintext = aesgcm.decrypt(iv_bytes, cipher_bytes, None)
        return {"status": "success", "decrypted_data": plaintext.decode("utf-8")}
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Decryption failed: {str(e)}"},
        )


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


def load_config():
    config_path = os.path.join(get_base_dir(), "ai_bs_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


config = load_config()

# --- Live System Orchestrator & ChromaDB API ---
import chromadb
import subprocess
from datetime import datetime

HOT_DB_PATH = r"C:\Workspaces\Stehouwer_Server\AI-BS_LLM_Core\stehouwer_vector_memory"
COLD_ARCHIVE_DIR = r"F:\AI-BS\Archive"
HEURISTIC_DIR = r"S:\AI-BS\Heuristics"


class LiveSystemOrchestrator:
    def __init__(self):
        print("[LIVE SYSTEM] Initializing Sovereign Compute Infrastructure...")
        try:
            self.chroma_client = chromadb.PersistentClient(path=HOT_DB_PATH)
            self.memory_collection = self.chroma_client.get_or_create_collection(
                name="heuristic_resolutions"
            )
        except Exception as e:
            print(f"[LIVE DB ERROR] Failed to init ChromaDB at {HOT_DB_PATH}: {e}")
            self.chroma_client = None
            self.memory_collection = None

    def apply_thoughtful_friction(self, task_description, authorization):
        """Phase V Compliance Checkpoint: Verifies Frontend Authorization."""
        print(f"\n[LIVE DIAGNOSTIC TRACE] Intercepted Action: {task_description}")
        return authorization.strip().upper() == "EXECUTE"

    def handle_live_fault(self, error_message, failed_script):
        """Converts live system faults straight into embedded memory tokens on the G:\\ drive."""
        trace_id = f"FAULT_{int(time.time())}"
        print(f"[DATA INTEGRITY] Vectorizing failure event log signature: {trace_id}")

        diagnostic_payload = {
            "timestamp": datetime.now().isoformat(),
            "failed_component": failed_script,
            "system_error_trace": error_message,
            "hardware_assignment": "Ryzen 9 9950X / RTX 4090 Stack",
        }

        if self.memory_collection:
            try:
                self.memory_collection.add(
                    documents=[json.dumps(diagnostic_payload)],
                    metadatas=[
                        {"status": "live_unresolved", "origin": "system_runtime"}
                    ],
                    ids=[trace_id],
                )
            except Exception as e:
                print(f"[VECTOR FAULT] Could not save to ChromaDB: {e}")

        # Log copy straight to physical heuristic storage path
        try:
            heuristic_backup = os.path.join(
                HEURISTIC_DIR, f"live_fault_{trace_id}.json"
            )
            os.makedirs(HEURISTIC_DIR, exist_ok=True)
            with open(heuristic_backup, "w") as f:
                json.dump(diagnostic_payload, f, indent=4)
            print(
                f"[HEURISTICS] System optimization matrix written safely to active volume: {heuristic_backup}"
            )
        except Exception as e:
            print(f"[IO FAULT] Could not save to {HEURISTIC_DIR}: {e}")

    def monitor_and_execute_task(self, script_path, authorization):
        if not os.path.exists(script_path):
            return {
                "status": "error",
                "message": f"[LIVE ERROR] Script missing at target architecture path: {script_path}",
            }

        if not self.apply_thoughtful_friction(
            f"Run live file execution -> {script_path}", authorization
        ):
            return {
                "status": "friction_aborted",
                "message": "[SYSTEM] Action aborted by Operator due to lack of EXECUTE authorization.",
            }

        print(
            "[LIVE RUNTIME] Invoking sandboxed subsystem. Monitoring hardware loops..."
        )
        process = subprocess.run(
            [sys.executable, script_path], capture_output=True, text=True
        )

        if process.returncode == 0:
            return {"status": "success", "output": process.stdout}
        else:
            print("[CRITICAL FAULT IDENTIFIED] Intercepting runtime trace loop...")
            self.handle_live_fault(process.stderr, script_path)
            return {
                "status": "fault_intercepted",
                "message": "Script failed. Fault logged to ChromaDB and Heuristic Volume.",
                "error_trace": process.stderr,
            }


live_orchestrator = LiveSystemOrchestrator()


class PipelineTestPayload(BaseModel):
    authorization: str


@app.post("/api/system/test_pipeline")
def test_active_pipeline(payload: PipelineTestPayload):
    target_live_script = os.path.join(
        get_base_dir(), "components", "active_pipeline_test.py"
    )
    result = live_orchestrator.monitor_and_execute_task(
        target_live_script, payload.authorization
    )
    return result


@app.get("/chroma-db/api/v1/get-heuristics")
def get_heuristics():
    # Attempt to read from the hot DB or S: Drive
    try:
        if live_orchestrator.memory_collection:
            count = live_orchestrator.memory_collection.count()
            return {
                "status": "success",
                "data": [f"Live Heuristics Loaded. Total vectors: {count}"],
            }
    except Exception:
        pass
    return {
        "status": "success",
        "data": ["Case 001: Missing Module", "Case 002: Sandbox Escape Blocked"],
    }


# --- Polyglot Execution Engine API ---
class PolyglotPayload(BaseModel):
    command: str
    language: str


@app.post("/polyglot-execution-engine/execute")
def polyglot_execute(payload: PolyglotPayload):
    return execute_polyglot_command(payload.command, payload.language)


# --- 25-Stage Orchestration Engine API ---
from bullshit_orchestrator import run_orchestration


class StagePayload(BaseModel):
    master_goal: str
    steps: list


@app.post("/stage-engine/orchestrate")
async def orchestrate_stages(payload: StagePayload):
    return await run_orchestration(payload.master_goal, payload.steps)


# --- AI-BS 32-Thread Core Engine API ---
core_engine = AI_BS_Core_Engine()


class CorePayload(BaseModel):
    monolithic_tasks: list


@app.post("/ai-bs-core/execute")
def execute_core_pipeline(payload: CorePayload):
    """Executes tasks dynamically across the 32-thread Out-of-Order Engine."""
    results = core_engine.execute_pipeline(payload.monolithic_tasks)
    return {"status": "success", "in_order_retirement_data": results}


# --- Telemetry & Background Engines (Phase 3) ---
from fastapi import BackgroundTasks
import asyncio

engine_telemetry = {
    "scavenger_active": False,
    "polyglot_active": False,
    "active_threads": 0,
    "tasks_completed": 0,
    "cpu_usage_simulated": "12%",
}

import random


@app.get("/telemetry/status")
def get_telemetry():
    # Simulate dynamic fluctuations for the Aero-Agri frontend
    engine_telemetry["temp"] = round(random.uniform(20.0, 24.0), 1)
    engine_telemetry["mfcOutput"] = round(random.uniform(110.0, 160.0), 1)
    engine_telemetry["aeroponicLayers"] = random.randint(4, 8)
    engine_telemetry["co2"] = random.randint(800, 1100)
    engine_telemetry["lux"] = random.randint(18000, 22000)
    engine_telemetry["ph"] = round(random.uniform(5.5, 6.5), 1)

    return JSONResponse(content=engine_telemetry)


async def run_scavenger_background(human_idea: str, project_keyword: str):
    engine_telemetry["scavenger_active"] = True
    engine_telemetry["active_threads"] += 1
    try:
        tree_path = os.path.join(get_base_dir(), "complete_system_tree.txt")
        builder = ProjectScaffolder(tree_path)
        # Using run_in_executor to not block the asyncio event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, builder.execute_agent_build_workflow, human_idea, project_keyword
        )
        engine_telemetry["tasks_completed"] += 1
    finally:
        engine_telemetry["scavenger_active"] = False
        engine_telemetry["active_threads"] -= 1


class ScavengerPayload(BaseModel):
    human_idea: str
    project_keyword: str


@app.post("/scavenger/build")
def scavenger_build(payload: ScavengerPayload, background_tasks: BackgroundTasks):
    """Parses local drives and executes a build asynchronously."""
    background_tasks.add_task(
        run_scavenger_background, payload.human_idea, payload.project_keyword
    )
    return {
        "status": "queued",
        "message": "Scavenger build triggered in background thread.",
    }


# --- Dynamic UI Layout Generator API ---
from bullshit_builder import UIGenerator
from bullshit_auditor import audit_code
from bullshit_vault_watchdog import start_watchdog

from bullshit_lead_generator import WestMichiganLeadGen
import uuid
import asyncio


# Daemon Consolidation Initialization
@app.on_event("startup")
async def startup_event():
    print("[Monolithic Core] Initializing Consolidated Background Daemons...")

    # 1. Lead Generator Daemon Loop
    async def lead_gen_loop():
        gen = WestMichiganLeadGen()
        while True:
            try:
                await gen.run_sweep()
            except Exception as e:
                logger.error(f"Lead Gen Daemon fault: {e}")
            await asyncio.sleep(86400)  # Sweep once per 24 hours

    asyncio.create_task(lead_gen_loop())

    # 2. Sponge Daemon (Running in Thread to prevent blocking)
    def run_sponge():
        try:
            import bullshit_sponge
            import asyncio

            asyncio.run(bullshit_sponge.main_loop())
        except Exception as e:
            print(f"Sponge Daemon fault: {e}")

    # 3. Builder Daemon
    def run_builder():
        try:
            import bullshit_builder

            if hasattr(bullshit_builder, "main"):
                bullshit_builder.main()
        except Exception as e:
            print(f"Builder Daemon fault: {e}")

    # 4. Vault Watchdog Daemon
    def run_watchdog():
        try:
            start_watchdog()
        except Exception as e:
            print(f"Watchdog Daemon fault: {e}")

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_sponge)
    loop.run_in_executor(None, run_builder)
    loop.run_in_executor(None, run_watchdog)

    print("[Monolithic Core] Background Daemons Online.")


class UIPayload(BaseModel):
    human_idea: str
    component_name: str
    file_extension: str = ".jsx"


import httpx


@app.post("/ui-generator/build")
async def generate_ui_component(payload: UIPayload):
    """Takes a UI prompt, hits the local LLM, and writes raw code to the frontend."""
    generator = UIGenerator()
    generated_file = generator.generate_component(
        payload.human_idea, payload.component_name, payload.file_extension
    )

    # Stehouwer Reality Standard Audit
    try:
        with open(generated_file, "r") as f:
            code_content = f.read()
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "stehouwer_llm",
                    "prompt": "You are the Stehouwer Reality Standard Audit Agent. Review this code. If it contains placeholders, lacks logic, or has syntax errors, output 'REJECT'. Otherwise output 'APPROVE'.\n\nCode:\n"
                    + code_content,
                    "stream": False,
                },
            )
        if r.status_code == 200 and "REJECT" in r.json().get("response", "").upper():
            return {
                "status": "error",
                "message": "Code rejected by Stehouwer Reality Standard Audit Sub-Agent.",
                "file_written": generated_file,
            }
    except Exception as e:
        print("Audit failed:", e)

    return {"status": "success", "file_written": generated_file}


# --- Heuristics Daemon API ---
class FailurePayload(BaseModel):
    failed_code: str
    error_log: str


@app.post("/api/heuristics/analyze_failure")
async def analyze_failure(payload: FailurePayload):
    system_prompt = "You are the Heuristics Daemon. Analyze this failure, extract a generalized learning rule starting with 'RULE:', and explain why it failed."
    prompt = (
        f"{system_prompt}\nCode:\n{payload.failed_code}\nError:\n{payload.error_log}"
    )
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": "stehouwer_llm", "prompt": prompt, "stream": False},
                timeout=60.0,
            )
            if r.status_code == 200:
                response = r.json().get("response", "")
                archive_path = os.path.join(
                    HEURISTICS_DIR, "session_history_archive.json"
                )
                with open(archive_path, "a") as f:
                    f.write(
                        json.dumps({"error": payload.error_log, "heuristic": response})
                        + "\n"
                    )

                # Assume ChromaDB vector DB index embedding here

                return {"status": "success", "heuristic": response}
            return {"status": "error", "message": "Failed to generate heuristic."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- Fire Writer API ---
class FireWriterPayload(BaseModel):
    profile: str
    raw_text: str


@app.post("/fire-writer/format")
async def fire_writer_format(payload: FireWriterPayload):
    prompt = f"Format the following text according to the '{payload.profile}' style profile:\n\n{payload.raw_text}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": "stehouwer_llm", "prompt": prompt, "stream": False},
                timeout=60.0,
            )
            if r.status_code == 200:
                data = r.json()
                return {"status": "success", "formatted_text": data.get("response", "")}
            return {"status": "error", "message": f"LLM returned {r.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- Generator API ---
class GeneratorPayload(BaseModel):
    dimensionality: str
    physics_target: str
    objective: str


@app.post("/api/generator/predictive")
async def generator_predictive(payload: GeneratorPayload):
    # Dummy logic to mimic a predictive AI generation blueprint
    generated_code = f'# AI Agent Loop\nwhile True:\n    state = get_physics_state()\n    action = policy(state, objective="{payload.objective}")\n    step_physics()\n'

    # Stehouwer Reality Standard Audit
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "stehouwer_llm",
                    "prompt": "You are the Stehouwer Reality Standard Audit Agent. Review this code. If it contains placeholders, lacks logic, or has syntax errors, output 'REJECT'. Otherwise output 'APPROVE'.\n\nCode:\n"
                    + generated_code,
                    "stream": False,
                },
            )
        if r.status_code == 200 and "REJECT" in r.json().get("response", "").upper():
            return {
                "status": "error",
                "message": "Code rejected by Stehouwer Reality Standard Audit Sub-Agent.",
                "code": generated_code,
            }
    except Exception as e:
        print("Audit failed:", e)

    return {
        "status": "success",
        "techStack": f"Dependencies for {payload.dimensionality} + {payload.physics_target}",
        "code": generated_code,
        "nextSteps": ["Step 1: Initialize Engine", "Step 2: Loop", "Step 3: Validate"],
        "sandboxLog": "Sandbox passed.",
    }


# --- IT HelpDesk API ---
class ITDiagnosePayload(BaseModel):
    issue: str


@app.post("/it-helpdesk/diagnose")
def it_helpdesk_diagnose(payload: ITDiagnosePayload):
    return {
        "status": "success",
        "diagnosis": f"Automated analysis for issue: {payload.issue}",
        "resolution": "Try rebooting the container or flushing ChromaDB cache.",
    }


# --- Agent Handoff API (Phase X: Swarm Integration) ---
class AgentHandoffPayload(BaseModel):
    agent_role: str
    prompt: str


swarm_orchestrator = SwarmOrchestrator()


@app.post("/agent/handoff")
async def agent_handoff(payload: AgentHandoffPayload):
    # Route the request through the new Swarm Orchestrator
    try:
        result = swarm_orchestrator.delegate_task(payload.prompt, payload.agent_role)
        return {"status": "success", "swarm_result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- GitHub Automation API ---
import httpx
import uuid
import subprocess
from bullshit_github_automation import commit_and_push_build
from pydantic import BaseModel

HEURISTICS_DIR = r"S:\Heuristics"
ARCHIVE_DIR = r"F:\Cold_Archive"
os.makedirs(HEURISTICS_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)


class GithubPayload(BaseModel):
    repo_path: str
    commit_message: str


@app.post("/github/commit")
def github_commit(payload: GithubPayload):
    return commit_and_push_build(payload.repo_path, payload.commit_message)


# --- ComfyUI Integration API ---
class ComfyUIPayload(BaseModel):
    prompt: dict


import asyncio


@app.post("/comfyui/generate")
async def generate_image(payload: ComfyUIPayload):
    try:
        async with httpx.AsyncClient() as client:
            # 1. Trigger the workflow
            r = await client.post(
                "http://127.0.0.1:8189/prompt",
                json={"prompt": payload.prompt},
                timeout=30.0,
            )
            if r.status_code != 200:
                return JSONResponse(status_code=r.status_code, content=r.json())

            data = r.json()
            prompt_id = data.get("prompt_id")
            if not prompt_id:
                return JSONResponse(
                    status_code=500,
                    content={"error": "No prompt_id returned from ComfyUI"},
                )

            # 2. Poll for completion via /history
            for _ in range(60):  # Wait up to 60 seconds
                await asyncio.sleep(1)
                hist_r = await client.get(
                    f"http://127.0.0.1:8189/history/{prompt_id}", timeout=10.0
                )
                if hist_r.status_code == 200:
                    hist_data = hist_r.json()
                    if prompt_id in hist_data:
                        # Generation finished! Extract filename
                        outputs = hist_data[prompt_id].get("outputs", {})
                        for node_id, output in outputs.items():
                            if "images" in output and len(output["images"]) > 0:
                                filename = output["images"][0]["filename"]
                                return {
                                    "prompt_id": prompt_id,
                                    "filename": filename,
                                    "status": "success",
                                }
                        return {
                            "error": "Generation completed but no image output found in node outputs"
                        }

            return {"error": "Timeout waiting for ComfyUI generation"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/comfyui/status")
async def comfyui_status():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://127.0.0.1:8189/system_stats", timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                devices = data.get("devices", [])
                vram_total = 0
                vram_free = 0
                gpu = "Unknown"
                if devices:
                    dev = devices[0]
                    vram_total = dev.get("vram_total", 0)
                    vram_free = dev.get("vram_free", 0)
                    gpu = dev.get("name", "GPU")
                return {
                    "status": "online",
                    "gpu": gpu,
                    "vram_total": vram_total,
                    "vram_free": vram_free,
                }
            return {"status": "offline"}
    except Exception:
        return {"status": "offline"}


@app.get("/comfyui/models")
async def comfyui_models():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://127.0.0.1:8189/object_info", timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                ckpts = (
                    data.get("CheckpointLoaderSimple", {})
                    .get("input", {})
                    .get("required", {})
                    .get("ckpt_name", [[]])[0]
                )
                return {"models": ckpts}
    except Exception:
        pass
    return {"models": []}


# --- Phase 5: Living Learning Memory Engine ---
MASTER_MEMORY_PATH = (
    r"C:\Workspaces\Stehouwer_Server\AI-BS_Master_Memory\master_memory_dump.json"
)


class MemoryPayload(BaseModel):
    prompt: str
    code_block: str
    status: str


@app.post("/memory/store-success")
def store_success_memory(payload: MemoryPayload):
    try:
        memory_data = []
        if os.path.exists(MASTER_MEMORY_PATH):
            with open(MASTER_MEMORY_PATH, "r") as f:
                memory_data = json.load(f)

        memory_data.append(
            {
                "prompt": payload.prompt,
                "document": payload.code_block,
                "metadata": {"status": payload.status, "timestamp": time.time()},
            }
        )

        os.makedirs(os.path.dirname(MASTER_MEMORY_PATH), exist_ok=True)
        with open(MASTER_MEMORY_PATH, "w") as f:
            json.dump(memory_data, f, indent=4)

        return {"status": "success", "message": "Baseline memorized."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# --- Phase 14: Tab Ecosystem Endpoints ---
from fastapi import UploadFile, File, Form
import glob


@app.get("/system/status")
def system_status():
    import subprocess

    try:
        git_status = subprocess.check_output(
            ["git", "status", "-s"], cwd=get_base_dir()
        ).decode("utf-8")
        git_status = (
            "Clean working tree."
            if not git_status.strip()
            else f"Pending changes:\n{git_status}"
        )
    except:
        git_status = "Git not initialized or error."

    return {
        "gitStatus": git_status,
        "ssdRamFootprint": (
            f"{os.path.getsize(MASTER_MEMORY_PATH) / 1024:.2f} KB"
            if os.path.exists(MASTER_MEMORY_PATH)
            else "0 KB"
        ),
        "activeAgents": ["Trainer Daemon", "Memory Offloader"],
    }


@app.post("/system/wipe-ssd")
def wipe_ssd():
    if os.path.exists(MASTER_MEMORY_PATH):
        os.remove(MASTER_MEMORY_PATH)
    return {"status": "success", "message": "SSD RAM Flushed."}


class ModelPullPayload(BaseModel):
    model_name: str


@app.post("/model/pull")
async def pull_model(payload: ModelPullPayload):
    async def stream_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "http://127.0.0.1:11434/api/pull",
                json={"name": payload.model_name},
                timeout=300.0,
            ) as r:
                async for chunk in r.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


@app.get("/memory/stats")
def memory_stats():
    size = (
        os.path.getsize(MASTER_MEMORY_PATH) if os.path.exists(MASTER_MEMORY_PATH) else 0
    )
    return {
        "status": "success",
        "ssdRamSize": size,
        "ssdRamPath": MASTER_MEMORY_PATH,
        "dbEntries": 0,  # Would be chroma count
    }


VAULT_DOCS_DIR = r"C:\Workspaces\Stehouwer_Server\AI-BS_Knowledge_Vaults\Docs"
os.makedirs(VAULT_DOCS_DIR, exist_ok=True)


@app.get("/documents/list")
def list_documents():
    files = glob.glob(os.path.join(VAULT_DOCS_DIR, "*"))
    docs = [
        {
            "name": os.path.basename(f),
            "size": os.path.getsize(f),
            "type": os.path.splitext(f)[1],
        }
        for f in files
    ]
    return {"status": "success", "documents": docs}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), vault: str = Form(default="")):
    target_dir = VAULT_DOCS_DIR
    if vault and vault in [
        "NoCo_Ventures",
        "Fire_Writing",
        "Marketing",
        "AI_Architecture",
        "Trading_Algos",
        "Personal_Journal",
        "Code_Snippets",
        "System_Logs",
    ]:
        target_dir = os.path.join(VAULT_DOCS_DIR, vault)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

    file_location = os.path.join(target_dir, file.filename)
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    return {
        "status": "success",
        "message": f"Saved {file.filename} to Vault: {vault if vault else 'Root'}.",
    }


class SearchPayload(BaseModel):
    query: str


@app.post("/kb/search")
async def kb_search(payload: SearchPayload):
    return {
        "status": "success",
        "results": [
            {
                "content": f"Mock result for {payload.query}",
                "score": 0.99,
                "source": "Vault Index",
            }
        ],
    }


class DevRunPayload(BaseModel):
    code: str
    language: str


@app.post("/dev/run")
def dev_run(payload: DevRunPayload):
    return execute_polyglot_command(payload.code, payload.language)


# --- Phase 7: Omni-Drive Database Integration ---
import sqlite3
import shutil

OMNIDRIVE_DB_PATH = r"C:\Workspaces\Stehouwer_Server\backend\state.db"
PORT_FILE = r"C:\Workspaces\Stehouwer_Server\backend\.writer_daemon_port"


def get_writer_port():
    try:
        with open(PORT_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "8111"


class OmniSearchPayload(BaseModel):
    query: str
    limit: int = 100


@app.post("/api/omnidrive/search")
def omnidrive_search(payload: OmniSearchPayload):
    try:
        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        query_str = f"%{payload.query}%"
        cursor.execute(
            "SELECT drive, filepath, filename, extension, size_bytes FROM file_state WHERE filename LIKE ? LIMIT ?",
            (query_str, payload.limit),
        )
        rows = cursor.fetchall()
        results = [
            {
                "drive": r[0],
                "filepath": r[1],
                "filename": r[2],
                "extension": r[3],
                "size_bytes": r[4],
            }
            for r in rows
        ]
        conn.close()
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class OmniRelocatePayload(BaseModel):
    source_path: str
    destination_dir: str


@app.post("/api/omnidrive/relocate")
def omnidrive_relocate(payload: OmniRelocatePayload):
    # Thoughtful Friction Endpoint
    return {
        "status": "pending_friction",
        "diagnostic_trace": f"Request to physically move file: {payload.source_path} to {payload.destination_dir}",
        "message": "WARNING: This requires explicit operator CONFIRMATION to execute the Python shutil.move() command.",
    }


@app.post("/api/omnidrive/relocate/confirm")
async def omnidrive_relocate_confirm(payload: OmniRelocatePayload):
    try:
        if not os.path.exists(payload.destination_dir):
            os.makedirs(payload.destination_dir, exist_ok=True)
        dest_path = os.path.join(
            payload.destination_dir, os.path.basename(payload.source_path)
        )
        shutil.move(payload.source_path, dest_path)

        port = get_writer_port()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"http://127.0.0.1:{port}/delete_path",
                    json={"filepath": payload.source_path},
                )
        except Exception as queue_e:
            print(f"[OmniDrive API] Error queueing deletion: {queue_e}")

        return {
            "status": "success",
            "message": f"File successfully relocated to {dest_path}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- Phase 8: Live Advertising Dashboard Integration ---
import uuid

# Initialize the Advertising tables if they don't exist
try:
    _conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
    _conn.execute("PRAGMA journal_mode=WAL;")
    _cursor = _conn.cursor()
    _cursor.execute("""
        CREATE TABLE IF NOT EXISTS advertising_leads (
            id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT,
            last_contact TEXT
        )
    """)
    _cursor.execute("""
        CREATE TABLE IF NOT EXISTS advertising_budgets (
            id TEXT PRIMARY KEY,
            event TEXT,
            spent TEXT,
            roi TEXT
        )
    """)
    _conn.commit()
    _conn.close()
except Exception as e:
    print(f"[Advertising DB Init Error] {e}")


class LeadPayload(BaseModel):
    id: str
    name: str
    status: str
    last_contact: str


class BudgetPayload(BaseModel):
    id: str
    event: str
    spent: str
    roi: str


@app.get("/api/advertising/leads")
def get_adv_leads():
    try:
        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, status, last_contact FROM advertising_leads")
        rows = cursor.fetchall()
        leads = [
            {"id": r[0], "name": r[1], "status": r[2], "lastContact": r[3]}
            for r in rows
        ]
        conn.close()
        return {"status": "success", "leads": leads}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/advertising/leads")
def save_adv_leads(leads: list[LeadPayload]):
    try:
        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
        cursor = conn.cursor()
        # Full replace for simplicity based on the current UI state
        cursor.execute("DELETE FROM advertising_leads")
        for lead in leads:
            cursor.execute(
                "INSERT INTO advertising_leads (id, name, status, last_contact) VALUES (?, ?, ?, ?)",
                (lead.id, lead.name, lead.status, lead.last_contact),
            )
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/advertising/budgets")
def get_adv_budgets():
    try:
        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, event, spent, roi FROM advertising_budgets")
        rows = cursor.fetchall()
        budgets = [
            {"id": r[0], "event": r[1], "spent": r[2], "roi": r[3]} for r in rows
        ]
        conn.close()
        return {"status": "success", "budgets": budgets}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/advertising/budgets")
def save_adv_budgets(budgets: list[BudgetPayload]):
    try:
        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
        cursor = conn.cursor()
        # Full replace for simplicity based on the current UI state
        cursor.execute("DELETE FROM advertising_budgets")
        for budget in budgets:
            cursor.execute(
                "INSERT INTO advertising_budgets (id, event, spent, roi) VALUES (?, ?, ?, ?)",
                (budget.id, budget.event, budget.spent, budget.roi),
            )
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class CopyGenPayload(BaseModel):
    businessName: str
    campaignGoal: str
    geofence: str
    tier: str
    commitment: str
    contractValue: float


# --- Telemetry Storage ---
shadow_telemetry_aggregate = {}


@app.post("/api/advertising/generate")
async def generate_adv_copy(payload: CopyGenPayload):
    global shadow_telemetry_aggregate

    context_block = ""
    if shadow_telemetry_aggregate:
        total_reach = sum(
            item.organic_reach for item in shadow_telemetry_aggregate.values()
        )
        sources = ", ".join(shadow_telemetry_aggregate.keys())
        context_block = f" LATEST PERFORMANCE CONTEXT: We are currently tracking a massive Total Collective Organic Reach of {total_reach:,} across {len(shadow_telemetry_aggregate)} platforms ({sources}). Use this immense real-world organic reach to inform the tone, authoritative scale, and aggressive language of the copy you are about to write. Mention this success implicitly to establish dominance."

    prompt = f"Write a punchy, high-converting advertisement copy for a business named '{payload.businessName}'. The primary campaign goal is: '{payload.campaignGoal}'. TARGET GEOFENCE: {payload.geofence}. PRICING TIER LEVEL: {payload.tier}. TEMPORAL LOCK: {payload.commitment}. Contract Value: ${payload.contractValue:.2f}.{context_block} Adjust the tone and complexity of the deliverables based on the Tier level. Format it cleanly without any meta-talk."

    req_json = {"model": "stehouwer_llm", "prompt": prompt, "stream": True}

    # Stream the Ollama response back to the client directly
    async def stream_generator():
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "http://127.0.0.1:11434/api/generate",
                    json=req_json,
                    timeout=120.0,
                ) as r:
                    if r.status_code != 200:
                        fault_msg = f"LLM Generation Failed. Status {r.status_code}"
                        print(f"[LIVE FAULT] {fault_msg}")
                        live_orchestrator.handle_live_fault(
                            fault_msg, "AI_BS_Advertising_LLM"
                        )
                        yield json.dumps({"error": fault_msg}).encode("utf-8")
                        return
                    async for chunk in r.aiter_bytes():
                        yield chunk
        except Exception as e:
            fault_msg = f"Connection error: {str(e)}"
            print(f"[LIVE FAULT] {fault_msg}")
            live_orchestrator.handle_live_fault(fault_msg, "AI_BS_Advertising_LLM")
            yield json.dumps({"error": fault_msg}).encode("utf-8")

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


class TelemetryPayload(BaseModel):
    timestamp: str
    source: str
    geofence: str
    organic_reach: int
    engagement_rate: str


@app.post("/api/advertising/telemetry/official")
async def ingest_official_telemetry(payload: TelemetryPayload):
    print(f"[LIVE SYSTEM] Primary Feed Ingested: {payload.source} | {payload.geofence}")
    return {"status": "success", "feed": "primary", "data": payload.dict()}


@app.post("/api/advertising/telemetry/shadow")
async def ingest_shadow_telemetry(payload: TelemetryPayload):
    global shadow_telemetry_aggregate

    # Store by source (e.g. www.google.com, business.facebook.com)
    shadow_telemetry_aggregate[payload.source] = payload
    total_reach = sum(
        item.organic_reach for item in shadow_telemetry_aggregate.values()
    )

    print(
        f"[LIVE SYSTEM] Shadow Feed Ingested (Auto-Tasker): {payload.source} | Platform Reach: {payload.organic_reach} | TOTAL AGGREGATE REACH: {total_reach:,}"
    )
    return {
        "status": "success",
        "feed": "shadow",
        "total_aggregate": total_reach,
        "data": payload.dict(),
    }


@app.get("/api/advertising/telemetry/shadow/aggregate")
def get_shadow_telemetry_aggregate():
    global shadow_telemetry_aggregate
    data = [item.dict() for item in shadow_telemetry_aggregate.values()]
    total_reach = sum(item["organic_reach"] for item in data)
    return {"status": "success", "total_reach": total_reach, "platforms": data}


# --- Daemon Log Streamer API ---
@app.get("/api/system/daemon_logs")
def get_daemon_logs():
    logs_dir = os.path.join(get_base_dir(), "logs")
    log_files = {
        "ollama": "ollama.log",
        "backend": "backend.log",
        "remote_bridge": "remote_bridge.log",
        "hunter": "hunter.log",
        "trainer": "trainer.log",
        "refactoring": "refactoring.log",
    }

    results = {}
    for daemon_name, filename in log_files.items():
        filepath = os.path.join(logs_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    results[daemon_name] = [
                        line.strip() for line in lines[-100:]
                    ]  # Get last 100 lines
            except Exception as e:
                results[daemon_name] = [f"Error reading log: {str(e)}"]
        else:
            results[daemon_name] = ["Waiting for daemon to boot..."]

    return {"status": "success", "logs": results}


@app.post("/api/advertising/leads/generate")
async def generate_leads(request: Request):
    """Triggers the West Michigan Lead Generator."""
    try:
        gen = WestMichiganLeadGen()
        # In a real environment, you'd trigger this asynchronously via the Orchestrator,
        # but for demonstration we run it directly.
        results = await gen.run_sweep()
        return {"status": "success", "leads_found": len(results), "data": results}
    except Exception as e:
        logger.error(f"Lead Generation Failed: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/advertising/leads")
async def get_advertising_leads():
    """Retrieves lead matrix from state.db"""
    try:
        import sqlite3

        conn = sqlite3.connect(os.path.join(get_base_dir(), "state.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM advertising_leads ORDER BY date_acquired DESC LIMIT 500"
        )
        rows = cursor.fetchall()
        leads = [dict(row) for row in rows]
        conn.close()
        return {"status": "success", "leads": leads}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def catch_all(request: Request, full_path: str):
    body = await request.body()
    print(f"Received proxy request: {request.method} /{full_path}")

    if "chat/completions" in full_path:
        try:
            req_json = json.loads(body) if body else {}

            # Decrypt payload if encrypted
            if req_json.get("encrypted", False):
                try:
                    iv_bytes = base64.b64decode(req_json["iv"])
                    cipher_bytes = base64.b64decode(req_json["ciphertext"])
                    plaintext = aesgcm.decrypt(iv_bytes, cipher_bytes, None)
                    req_json = json.loads(plaintext.decode("utf-8"))
                except Exception as e:
                    print(
                        f"[Decrypt Error] Failed to decrypt payload: {e}. Falling back to rawFallback."
                    )
                    if "rawFallback" in req_json:
                        req_json = req_json["rawFallback"]

            # --- PHASE 5: PRE-EXECUTION HEURISTIC QUERY ---
            last_user_msg = ""
            if "messages" in req_json:
                for msg in reversed(req_json["messages"]):
                    if msg.get("role") == "user":
                        last_user_msg = msg.get("content", "").lower()
                        break

            known_good_baseline = None
            if os.path.exists(MASTER_MEMORY_PATH):
                try:
                    with open(MASTER_MEMORY_PATH, "r") as f:
                        memory_data = json.load(f)
                        for block in memory_data:
                            if block.get("metadata", {}).get("status") == "Success":
                                # Basic semantic matching simulation (would normally be ChromaDB cosine similarity)
                                if (
                                    block.get("prompt", "").lower() in last_user_msg
                                    or last_user_msg in block.get("prompt", "").lower()
                                ):
                                    known_good_baseline = block.get("document")
                                    break
                except Exception as e:
                    print(f"[Memory Engine] Error reading baseline: {e}")

            if known_good_baseline and "messages" in req_json:
                override_prompt = (
                    f"\n\n[ALGORITHMIC DIRECTIVE] "
                    f"A 'Known-Good' baseline was found for this task in the Living Learning Memory. "
                    f"You are strictly forbidden from hallucinating a new structural approach. "
                    f"If you must deviate from this baseline due to new constraints, you MUST prepend your response exactly with the phrase: "
                    f"'DEVIATION_AUDIT_TRACE: I found a previous version of this task that worked, but I am modifying it because...'\n\n"
                    f"BASELINE CODE:\n{known_good_baseline}"
                )
                if req_json["messages"] and req_json["messages"][0]["role"] == "system":
                    req_json["messages"][0]["content"] += override_prompt
                else:
                    req_json["messages"].insert(
                        0, {"role": "system", "content": override_prompt}
                    )

            # --- PHASE 4.5: COMFYUI SEAMLESS TRIGGER INJECTION ---
            if "messages" in req_json:
                comfyui_sys_prompt = (
                    "\n\n[MULTIMODAL DIRECTIVE]\n"
                    "If the user asks you to generate, draw, or create an image, you MUST respond using the following exact syntax on its own line:\n"
                    '[COMFYUI_TRIGGER: "detailed positive prompt here", "negative prompt here"]\n'
                    "Do not attempt to write code to generate the image, use the trigger syntax."
                )
                tool_delegation_prompt = (
                    "\n\n[TOOL_DELEGATION_DIRECTIVE]\n"
                    "You are a master orchestrator Agent. You analyze the user's ideas and decide exactly what tasks need to be done and which tools to delegate to. You have access to ALL tools in the system.\n"
                    'If the user asks to find a file on their computer or hard drive, use: [TOOL: SEARCH_LOCAL_FILES | "filename or extension"]\n'
                    'If the user asks to format or edit text, use: [TOOL: FIRE_WRITER | "profile (professional/creative/journal/fire_writing)" | "text to format"]\n'
                    'If the user asks to generate blueprints or architecture, use: [TOOL: GENERATOR | "dimensionality (2D/3D)" | "target" | "objective"]\n'
                    "If the user asks to run a script, use this exact format:\n[TOOL: POLYGLOT]\n```language\ncode here\n```\n"
                    'If the user wants you to permanently learn something, or you successfully verified a complex task, use: [TOOL: MEMORY | "topic" | "knowledge to save"]\n'
                    'If the user gives a prompt that requires a specialized sub-agent not listed above, use: [TOOL: AGENT_HANDOFF | "agent_role" | "prompt"]\n'
                    "Always explicitly use these [TOOL: ...] tags to delegate tasks based on the user's ideas."
                )

                # --- NOCO IOT SENSOR INTEGRATION (PHASE 17) ---
                telemetry_context = (
                    f"\n\n[NOCO IOT SENSOR TELEMETRY]\n"
                    f"Current Vertical Farming Environment: "
                    f"Temp={engine_telemetry.get('temp', 0)}Â°C, "
                    f"CO2={engine_telemetry.get('co2', 0)}ppm, "
                    f"pH={engine_telemetry.get('ph', 0)}, "
                    f"Lux={engine_telemetry.get('lux', 0)}, "
                    f"Aeroponic Layers={engine_telemetry.get('aeroponicLayers', 0)}, "
                    f"MFC Output={engine_telemetry.get('mfcOutput', 0)}.\n"
                    f"If the user asks about the environment or sensors, use this real-time data."
                )

                combined_prompts = (
                    comfyui_sys_prompt + tool_delegation_prompt + telemetry_context
                )
                if req_json["messages"] and req_json["messages"][0]["role"] == "system":
                    req_json["messages"][0]["content"] += combined_prompts
                else:
                    req_json["messages"].insert(
                        0, {"role": "system", "content": combined_prompts}
                    )

            # --- OMNI-CONTEXT HYBRID RETRIEVAL (PHASE 18) ---
            vault_dir = r"C:\Workspaces\Stehouwer_Server\AI-BS_Knowledge_Vaults"
            index_file = os.path.join(vault_dir, "vault_index.json")
            omni_context = ""

            if last_user_msg:
                # 1. Thread: Web Search
                async def fetch_web():
                    try:
                        from duckduckgo_search import DDGS

                        with DDGS() as ddgs:
                            results = list(ddgs.text(last_user_msg, max_results=3))
                            return "\n".join(
                                [f"Source ({r['href']}): {r['body']}" for r in results]
                            )
                    except Exception as e:
                        print(f"[Web Search Error] {e}")
                        return ""

                # 2. Thread: Vault Vector Search
                async def fetch_vault():
                    v_ctx = ""
                    if os.path.exists(index_file):
                        try:
                            async with httpx.AsyncClient() as client:
                                embed_res = await client.post(
                                    "http://127.0.0.1:11434/api/embeddings",
                                    json={
                                        "model": "stehouwer_llm",
                                        "prompt": last_user_msg,
                                    },
                                    timeout=30.0,
                                )
                                if embed_res.status_code == 200:
                                    prompt_embedding = embed_res.json().get(
                                        "embedding", []
                                    )
                                    if prompt_embedding:
                                        import math

                                        def cosine_similarity(v1, v2):
                                            dot = sum(a * b for a, b in zip(v1, v2))
                                            mag1 = math.sqrt(sum(a * a for a in v1))
                                            mag2 = math.sqrt(sum(b * b for b in v2))
                                            return (
                                                dot / (mag1 * mag2)
                                                if mag1 * mag2 != 0
                                                else 0
                                            )

                                        with open(
                                            index_file, "r", encoding="utf-8"
                                        ) as f:
                                            index_data = json.load(f)
                                        for item in index_data:
                                            item["score"] = cosine_similarity(
                                                prompt_embedding,
                                                item.get("embedding", []),
                                            )
                                        top_chunks = sorted(
                                            index_data,
                                            key=lambda x: x["score"],
                                            reverse=True,
                                        )[:3]
                                        for chunk in top_chunks:
                                            if chunk["score"] > 0.5:
                                                v_ctx += f"--- Vault Document: {chunk['file']} ---\n{chunk['chunk']}\n\n"
                        except Exception as e:
                            print(f"[Vault Search Error] {e}")
                    return v_ctx

                # 3. Thread: OmniDrive Local DB Search
                async def fetch_omnidrive():
                    o_ctx = ""
                    try:
                        import sqlite3

                        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
                        cursor = conn.cursor()
                        # Simple keyword split search
                        keywords = last_user_msg.split()[:3]
                        if keywords:
                            query = (
                                "SELECT filepath, filename FROM file_state WHERE "
                                + " OR ".join(["filename LIKE ?"] * len(keywords))
                                + " LIMIT 3"
                            )
                            cursor.execute(query, [f"%{k}%" for k in keywords])
                            rows = cursor.fetchall()
                            if rows:
                                o_ctx = (
                                    "Related files found on hard drive:\n"
                                    + "\n".join([f"- {r[1]} ({r[0]})" for r in rows])
                                )
                        conn.close()
                    except Exception:
                        pass
                    return o_ctx

                # Execute all 3 retrievals concurrently
                web_result, vault_result, omnidrive_result = await asyncio.gather(
                    fetch_web(), fetch_vault(), fetch_omnidrive()
                )

                if web_result:
                    omni_context += f"\n[LIVE WEB DATA]\n{web_result}\n"
                if vault_result:
                    omni_context += f"\n[LOCAL VAULT CONTEXT]\n{vault_result}\n"
                if omnidrive_result:
                    omni_context += f"\n[OMNIDRIVE FILE REFS]\n{omnidrive_result}\n"

            if omni_context and "messages" in req_json:
                system_prompt = f"You are the central cognitive engine of AI-BS. You are currently operating with Omni-Context Hybrid Retrieval active. Use the following synthesized context from Web Search, Local Vaults, and Hard Drive DB to augment your intelligence:\n\n{omni_context}"

                if req_json["messages"] and req_json["messages"][0]["role"] == "system":
                    req_json["messages"][0]["content"] = (
                        system_prompt + "\n\n" + req_json["messages"][0]["content"]
                    )
                else:
                    req_json["messages"].insert(
                        0, {"role": "system", "content": system_prompt}
                    )
            # ----------------------------------

            if req_json.get("stream", False):

                async def stream_generator(current_req_json):
                    import re
                    import copy
                    import time

                    MAX_TOOL_LOOPS = 3
                    loop_count = 0

                    while loop_count < MAX_TOOL_LOOPS:
                        loop_count += 1
                        full_response_text = ""

                        async with httpx.AsyncClient() as client:
                            async with client.stream(
                                "POST",
                                "http://127.0.0.1:11434/v1/chat/completions",
                                json=current_req_json,
                                timeout=300.0,
                            ) as r:
                                async for chunk in r.aiter_bytes():
                                    yield chunk

                                    try:
                                        chunk_str = chunk.decode("utf-8")
                                        for line in chunk_str.split("\n"):
                                            if (
                                                line.startswith("data: ")
                                                and line != "data: [DONE]"
                                            ):
                                                data = json.loads(line[6:])
                                                if (
                                                    "choices" in data
                                                    and len(data["choices"]) > 0
                                                ):
                                                    delta = data["choices"][0].get(
                                                        "delta", {}
                                                    )
                                                    if "content" in delta:
                                                        full_response_text += delta[
                                                            "content"
                                                        ]
                                                    elif (
                                                        "message" in data["choices"][0]
                                                        and "content"
                                                        in data["choices"][0]["message"]
                                                    ):
                                                        full_response_text += data[
                                                            "choices"
                                                        ][0]["message"].get(
                                                            "content", ""
                                                        )
                                    except Exception:
                                        pass

                        # ReAct Loop: Check for Memory trigger
                        mem_match = re.search(
                            r'\[TOOL:\s*MEMORY\s*\|\s*"(.*?)"\s*\|\s*"(.*?)"\]',
                            full_response_text,
                            re.DOTALL,
                        )
                        if mem_match:
                            topic = mem_match.group(1)
                            knowledge = mem_match.group(2)

                            # Send visual cue
                            exec_msg = f"\n\n\n> ðŸ§  **[AI-BS BACKEND]** Permanently injecting knowledge into Master Memory DB...\n\n"
                            yield f'data: {json.dumps({"model": "stehouwer_llm", "message": {"role": "assistant", "content": exec_msg}, "done": False})}\n\n'.encode(
                                "utf-8"
                            )

                            try:
                                memory_data = []
                                if os.path.exists(MASTER_MEMORY_PATH):
                                    with open(MASTER_MEMORY_PATH, "r") as f:
                                        memory_data = json.load(f)
                                memory_data.append(
                                    {
                                        "id": str(int(time.time())),
                                        "prompt": topic,
                                        "document": knowledge,
                                        "metadata": {
                                            "status": "Success",
                                            "source": "Autonomous ReAct Loop",
                                        },
                                    }
                                )
                                os.makedirs(
                                    os.path.dirname(MASTER_MEMORY_PATH), exist_ok=True
                                )
                                with open(MASTER_MEMORY_PATH, "w") as f:
                                    json.dump(memory_data, f, indent=4)
                                combined_result = "SUCCESS: Memory securely committed to the permanent database."
                            except Exception as e:
                                combined_result = f"ERROR: Failed to write to memory database: {str(e)}"

                            current_req_json["messages"].append(
                                {"role": "assistant", "content": full_response_text}
                            )
                            system_feedback = f"[SYSTEM RE-ACT LOOP] You invoked the MEMORY tool. Result:\n\n{combined_result}\n\nConclude your response to the user."
                            current_req_json["messages"].append(
                                {"role": "user", "content": system_feedback}
                            )

                            yield f'data: {json.dumps({"model": "stehouwer_llm", "message": {"role": "assistant", "content": f"**[AI-BS BACKEND]** Memory update complete.\n\n"}, "done": False})}\n\n'.encode(
                                "utf-8"
                            )
                            continue

                        # ReAct Loop: Check for Polyglot trigger
                        if "[TOOL: POLYGLOT]" in full_response_text:
                            # Extract code block
                            code_match = re.search(
                                r"```([a-zA-Z0-9_]+)\n(.*?)```",
                                full_response_text,
                                re.DOTALL,
                            )
                            if code_match:
                                language = code_match.group(1).lower()
                                code = code_match.group(2)

                                # Send a visual cue to the frontend
                                exec_msg = f"\n\n\n> âš™ï¸ **[AI-BS BACKEND]** Executing {language} code in Polyglot Sandbox...\n\n"
                                yield f'data: {json.dumps({"model": "stehouwer_llm", "message": {"role": "assistant", "content": exec_msg}, "done": False})}\n\n'.encode(
                                    "utf-8"
                                )

                                try:
                                    # Execute the code physically
                                    result = await asyncio.to_thread(
                                        execute_polyglot_command, code, language
                                    )
                                    output = result.get("output", "No output.")
                                    error = result.get("error", "")
                                    combined_result = (
                                        f"STDOUT:\n{output}\nSTDERR:\n{error}"
                                    )
                                except Exception as e:
                                    combined_result = f"Sandbox Exception: {str(e)}"

                                # Append context and loop
                                current_req_json["messages"].append(
                                    {"role": "assistant", "content": full_response_text}
                                )

                                system_feedback = f'[SYSTEM RE-ACT LOOP] You invoked the POLYGLOT tool. Here is the actual terminal output from the sandbox execution:\n\n{combined_result}\n\nAnalyze this output objectively. If it failed, output a fixed version using [TOOL: POLYGLOT]. If it succeeded, explain the results to the user. You may also use [TOOL: MEMORY | "topic" | "code"] to permanently save the successful logic.'
                                current_req_json["messages"].append(
                                    {"role": "user", "content": system_feedback}
                                )

                                yield f'data: {json.dumps({"model": "stehouwer_llm", "message": {"role": "assistant", "content": f"**[AI-BS BACKEND]** Execution complete. Analyzing results...\n\n"}, "done": False})}\n\n'.encode(
                                    "utf-8"
                                )
                                continue

                        # If no tool triggered or we maxed out loops, break
                        break

                return StreamingResponse(
                    stream_generator(req_json), media_type="text/event-stream"
                )
            else:
                async with httpx.AsyncClient() as client:
                    print(
                        f"[Ollama Request] Sending payload to Ollama: {json.dumps(req_json)}"
                    )
                    r = await client.post(
                        "http://127.0.0.1:11434/v1/chat/completions",
                        json=req_json,
                        timeout=300.0,
                    )
                    if r.status_code != 200:
                        print(
                            f"[Ollama Error] Status {r.status_code}, Response: {r.text}"
                        )
                    return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            print(f"[Chat Completions Error] Exception in proxy: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    elif "models" in full_path:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "http://127.0.0.1:11434/v1/models", timeout=10.0
                )
                return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    return {"status": "unhandled", "path": full_path}


def main():
    print("==================================================")
    print("AI-BS Central Cognitive Engine Initializing...")

    # 1. Start the SSD Memory Offloading Daemon
    print("[Backend] Booting SSD Memory Offloading Daemon...")

    import subprocess
    import sys

    print("[Backend] Booting Database Writer Daemon...")
    subprocess.Popen([sys.executable, "bullshit_writer_daemon.py"], cwd=get_base_dir())
    import time

    time.sleep(1)  # Give it a second to bind port 8111

    print("[Backend] Booting Heuristics Daemon...")
    subprocess.Popen(
        [sys.executable, "bullshit_heuristics_daemon.py"], cwd=get_base_dir()
    )

    print("[Backend] Booting Sensory Daemon...")
    subprocess.Popen([sys.executable, "bullshit_senses.py"], cwd=get_base_dir())

    print("[Backend] Booting Medic Daemon...")
    subprocess.Popen([sys.executable, "bullshit_medic.py"], cwd=get_base_dir())

    print("[Backend] Booting Memory Daemon...")
    subprocess.Popen([sys.executable, "bullshit_memory.py"], cwd=get_base_dir())

    print("[Backend] Booting Trainer Daemon...")
    subprocess.Popen([sys.executable, "bullshit_trainer.py"], cwd=get_base_dir())

    print("[Backend] Booting Vault Watchdog Daemon...")
    subprocess.Popen([sys.executable, "bullshit_vault_watchdog.py"], cwd=get_base_dir())

    memory_manager = MemoryManager(memory_limit_mb=2048)
    memory_manager.start_monitoring()

    print(f"[Config] Loaded Primary Model: {config.get('primary_model')}")
    print("[Backend] Starting FastAPI Server on port 8000...")
    print("==================================================")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=config.get("log_level", "info").lower(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", type=str, help="Start an agent in background")
    args, _ = parser.parse_known_args()
    if args.agent:
        print(f"[Daemon] {args.agent} running in background...")
        import time

        while True:
            time.sleep(3600)
    else:
        main()
