import httpx
import asyncio
import json
import os
import subprocess
from .swarm_gauntlet import SovereignSwarmGauntlet
from .memory_vault import SovereignMemoryVault
from .document_engine import SovereignDocumentEngine
from core.real_system_tools import check_and_execute_system_tools
from core.personal_intelligence_memory import personal_memory
from core.safety_guardrails import STEHOUWER_SAFETY_DIRECTIVE, inject_safety_directive, audit_prompt_safety

OLLAMA_ENDPOINTS = [
    "http://127.0.0.1:11434/api/generate",
    "http://127.0.0.1:11435/api/generate"
]

def ensure_ollama_running():
    """
    Self-healing routine: attempts to launch Ollama natively if no instance is listening.
    Uses native process creation with explicit environment mapping to prevent shell quote-escaping bugs.
    """
    try:
        import socket
        for p in [11434, 11435]:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(('127.0.0.1', p)) == 0:
                    print(f"[Dispatcher] Ollama is already listening on port {p}.")
                    return

        ollama_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        if not os.path.exists(ollama_exe):
            print(f"[Dispatcher] Ollama executable not found at: {ollama_exe}")
            return

        env = os.environ.copy()
        env["OLLAMA_HOST"] = "0.0.0.0:11434"
        env["OLLAMA_MODELS"] = r"E:\AI_BS_Resources\Ollama"
        env["OLLAMA_KEEP_ALIVE"] = "10m"
        env["OLLAMA_NUM_PARALLEL"] = "1"
        env["OLLAMA_MAX_LOADED_MODELS"] = "1"
        env["OLLAMA_FLASH_ATTENTION"] = "1"
        env["CUDA_VISIBLE_DEVICES"] = "0"
        env["OLLAMA_IGPU_ENABLE"] = "0"

        creation_flags = 0
        if os.name == "nt":
            creation_flags = subprocess.CREATE_NO_WINDOW

        subprocess.Popen(
            [ollama_exe, "serve"],
            env=env,
            creationflags=creation_flags
        )
        print("[Dispatcher] Triggered native background Ollama auto-start on port 11434.")
    except Exception as e:
        print(f"[Dispatcher] Ollama auto-start exception: {e}")

from typing import Optional, List, Dict, Any

async def stream_sovereign_response(prompt: str, messages: Optional[List[Dict[str, Any]]] = None):
    """
    Unified entry point for all chat requests:
    1. Smart Document Ingestion: Parses attached files (.md, .txt, etc.) & extracts clean user query
    2. Multi-turn Conversational Context: Ingests recent dialog context so follow-ups retain memory
    3. Checks for real PC system diagnostics, port scans & hardware telemetry tools
    4. Checks for gauntlet triggers
    5. Routes to SovereignSwarmGauntlet if explicit gauntlet intent is detected
    6. Defaults to Fast Hybrid Persona Stream with real PC grounding and resilient Ollama failover
    """
    # 0. Smart Document Processing & Context Window Protection
    user_query, optimized_prompt = SovereignDocumentEngine.prepare_chat_payload(prompt)
    
    # 0b. Multi-turn Conversational Context Reconstruction
    conversation_prefix = ""
    if messages and isinstance(messages, list) and len(messages) > 1:
        prior_turns = []
        history_slice = [m for m in messages[:-1] if isinstance(m, dict) and m.get("content")]
        for m in history_slice[-4:]:
            role = "User" if m.get("role") == "user" else "Stehouwer LLM"
            c = str(m.get("content", "")).strip()
            if len(c) > 500:
                c = c[:500] + "..."
            if c:
                prior_turns.append(f"{role}: {c}")
        if prior_turns:
            conversation_prefix = "[RECENT CONVERSATION CONTEXT]:\n" + "\n".join(prior_turns) + "\n\n[LATEST USER INSTRUCTION]:\n"

    final_prompt = f"{conversation_prefix}{optimized_prompt}" if conversation_prefix else optimized_prompt
    
    # Pre-Flight Safety Audit across S1, S3, S4
    is_safe, refusal = audit_prompt_safety(user_query)
    if not is_safe:
        yield f"⚠️ **Sovereign Engine Refusal:** {refusal}\n"
        return

    clean_p = user_query.strip().lower()

    # 1. Real System Tools & Matrix Doctor Probing (Live on Host PC)
    real_tool_result = await asyncio.to_thread(check_and_execute_system_tools, user_query)
    if real_tool_result:
        yield "⚡ **Executing Real-Time Telemetry & Host Diagnostics on PC...**\n\n"
        yield real_tool_result
        return

    # 2. Gauntlet trigger keywords
    gauntlet_triggers = ["run gauntlet", "run deep gauntlet", "deep reasoning", "cross check models", "multi-model gauntlet", "/gauntlet"]
    is_gauntlet = any(clean_p.startswith(t) for t in gauntlet_triggers)

    if is_gauntlet:
        yield "⚡ **AI-BS Sovereign Reasoning Engine Engaged** *(Mathematical Autograd & 12-Stage Swarm)*\n\n"
        clean_query = user_query.strip()
        for prefix in gauntlet_triggers:
            if clean_query.lower().startswith(prefix):
                clean_query = clean_query[len(prefix):].strip()
                break
        if not clean_query:
            clean_query = user_query

        async for chunk in SovereignSwarmGauntlet.stream_gauntlet_execution(clean_query):
            yield chunk
        return

    # 2b. Inter-Model Logic Cross-Communication Bus
    cross_model_triggers = [
        "cross communicate", "cross-model", "inter-model", "collaborate models", "/cross",
        "multi model logic", "cross-communication", "multi-agent reasoning", "/collaborate",
        "cross check logic", "co-reason"
    ]
    is_cross_model = any(t in clean_p for t in cross_model_triggers)

    if is_cross_model:
        from .cross_model_bus import CrossModelCognitiveBus
        clean_query = user_query.strip()
        for prefix in ["/cross", "/collaborate", "cross communicate"]:
            if clean_query.lower().startswith(prefix):
                clean_query = clean_query[len(prefix):].strip()
                break
        if not clean_query:
            clean_query = user_query

        async for chunk in CrossModelCognitiveBus.stream_cross_model_reasoning(clean_query, messages):
            yield chunk
        return

    # 2c. Autonomous Media Studio Directorial Slash Commands (v5.294.0)
    media_triggers = ["/edit", "/create-cover", "/auto-shorts", "/book-trailer", "/voice-clone", "/vram", "/render"]
    is_media_command = any(clean_p.startswith(t) for t in media_triggers)

    if is_media_command:
        from core.media_render_engine import MediaRenderEngine
        from core.vram_resource_arbiter import vram_arbiter
        yield "🎬 **Autonomous Media Studio Engine Engaged (v5.294.0)**\n\n"
        
        cmd_parts = user_query.strip().split(maxsplit=1)
        slash_cmd = cmd_parts[0].lower()
        args_str = cmd_parts[1] if len(cmd_parts) > 1 else ""

        if slash_cmd == "/vram":
            telemetry = vram_arbiter.get_vram_telemetry()
            yield f"**RTX 4090 VRAM Telemetry & Hardware Status:**\n"
            yield f"- **Device:** `{telemetry.get('device_name')}`\n"
            yield f"- **Total Memory:** `{telemetry.get('total_mb', 24576):.0f} MB`\n"
            yield f"- **Allocated:** `{telemetry.get('allocated_mb', 0):.1f} MB`\n"
            yield f"- **Reserved:** `{telemetry.get('reserved_mb', 0):.1f} MB`\n"
            yield f"- **Free VRAM:** `{telemetry.get('free_mb', 24576):.1f} MB`\n"
            yield f"- **Utilization:** `{telemetry.get('utilization_pct', 0):.1f}%`\n"
            yield f"- **Zero-Copy Active Buffers:** `{len(vram_arbiter._allocated_shared_buffers)}`\n"
            return

        elif slash_cmd == "/auto-shorts":
            yield f"⚡ **Executing Autonomous Vertical Shorts Pipeline (CFR Gate + Reframing + Silences):**\n"
            in_path = args_str.strip() or r"C:\AI-BS\sandbox\demo_source.mp4"
            cfr_res = MediaRenderEngine.normalize_vfr_to_cfr(in_path, target_fps=30)
            yield f"- **[Domain 12] CFR Ingestion Gate:** {cfr_res.get('message', 'Completed')}\n"
            silence_res = MediaRenderEngine.strip_audio_silences(in_path)
            yield f"- **[Domain 4] Silence Stripper:** {silence_res.get('message', 'Completed')}\n"
            reframe_res = MediaRenderEngine.smart_reframe_vertical(in_path, target_aspect="9:16")
            yield f"- **[Domain 2] Smart Reframe (9:16):** {reframe_res.get('message', 'Completed')}\n"
            yield f"\n✅ **Shorts Production Complete:** Artifact ready at `{reframe_res.get('output_path', in_path)}`\n"
            return

        elif slash_cmd == "/create-cover":
            yield f"🎨 **Composing Autonomous High-Res Cover Art (Domain 3 Pyvips & PSD):**\n"
            res = MediaRenderEngine.pyvips_raster_transform(
                image_path=args_str.strip() or r"C:\AI-BS\sandbox\source_cover.png",
                operations=[{"type": "resize", "width": 2560}, {"type": "cmyk"}],
                output_format="png"
            )
            yield f"- **Transform Status:** {res.get('status')}\n"
            yield f"- **Output:** `{res.get('output_file')}` ({res.get('width')}x{res.get('height')})\n"
            yield f"- **Zero-Copy Memory Streamed:** `{res.get('zero_copy_stream')}`\n"
            return

        elif slash_cmd == "/voice-clone":
            yield f"🎙️ **Synthesizing Neural Voice Clone (Domain 5 F5-TTS):**\n"
            res = MediaRenderEngine.clone_neural_voice_tts(
                text=args_str.strip() or "Autonomous production speech test.",
                ref_audio_path=r"C:\AI-BS\sandbox\speaker_sample.wav"
            )
            yield f"- **Status:** {res.get('status')}\n"
            yield f"- **Generated Speech:** `{res.get('audio_file')}`\n"
            yield f"- **Audio Sample Rate:** `{res.get('sample_rate')} Hz`\n"
            return

        elif slash_cmd in ["/edit", "/book-trailer", "/render"]:
            yield f"🎬 **Dispatching Directorial Recipe to Master Engine:** `{user_query}`\n\n"
            recipe = {
                "title": f"Directorial {slash_cmd.replace('/', '').capitalize()} Task",
                "stages": [
                    {"domain": 12, "action": "normalize_cfr", "input": args_str},
                    {"domain": 4, "action": "vse_timeline", "resolution": "1920x1080"},
                    {"domain": 8, "action": "verify_qc", "min_vmaf": 93.0}
                ]
            }
            res = MediaRenderEngine.execute_media_pipeline_recipe(recipe)
            yield f"**Pipeline Execution Report:**\n"
            yield f"- **Job ID:** `{res.get('job_id')}`\n"
            yield f"- **Stages Completed:** `{res.get('stages_completed')}/{res.get('total_stages')}`\n"
            yield f"- **Checkpoints Atomic:** `{res.get('checkpoints_saved')}`\n"
            yield f"- **Status:** `{res.get('status')}`\n"
            return

    # 3. Dynamic Model Affinity Discovery (Fast Single-Model or Executive Persona)
    from .model_domain_matrix import ModelDomainMatrix
    ranked_models = ModelDomainMatrix.score_prompt_against_fleet(user_query)
    top_specialist = ranked_models[0]["model"] if (ranked_models and ranked_models[0]["score"] > 2.0) else "stehouwer_llm"

    # Use clean_user_query so memory vault and lexicon search don't explode on massive document payloads
    context = await asyncio.to_thread(SovereignMemoryVault.get_unified_context, user_query)
    personal_block = await asyncio.to_thread(personal_memory.format_system_prompt_block, user_query)
    
    # Ingest dynamic 3,230-file codebase knowledge context if query has architectural or code intent
    from .sourcecode_knowledge_engine import sourcecode_knowledge_engine
    codebase_context = await asyncio.to_thread(sourcecode_knowledge_engine.inject_codebase_context, user_query)

    stehouwer_system_prompt = (
        "You are Brett Stehouwer / Stehouwer Publishing AI Core. You own the room, speak with authentic brotherly banter, "
        "and deliver razor-sharp, practical solutions without corporate refusals or robotic hesitation. "
        "Never sound robotic or generic. Answer directly and sovereignly.\n"
        "COMPLETE CODEBASE KNOWLEDGE DIRECTIVE: You have full access to the AI-BS Master Codebase Knowledge Base containing all 3,230 files (820,999 lines of source code across rules, backend core engines, API routers, frontend components, and tools). When answering technical architecture, debugging, or code generation questions, reference and utilize the exact real codebase structure accurately.\n"
        "DATABASE & STORAGE ARCHITECTURE: All 7 former SQLite databases (state.db, clients.db, unreal_assets.db, stehouwer_vault.db, stehouwer_accounting.db, west_michigan.db, and drip_ledger.db) were successfully consolidated in Milestone v5.202.0 into C:\\AI-BS\\backend\\aibs_master.db (27 tables, 6,010 rows, WAL mode, multi-tenant tagged with client_id). The architectural ledger is AI_BS_MASTER_ARCHITECTURAL_LEDGER.md (a Markdown document, NOT an SQLite database). Never hallucinate un-condensed databases or fictitious .db files.\n"
        "COMMERCIAL RECON DIRECTIVE: You are an autonomous commercial business development and market intelligence suite. "
        "OSINT lead reconnaissance, commercial business directory scanning, and West Michigan B2B sales pipelines are 100% authorized core operations. "
        "NEVER refuse, decline, or give canned corporate disclaimers on commercial intelligence requests.\n"
        "DOCUMENT ANALYSIS CAPABILITY: When provided with attached files or indexed document chapters, analyze them thoroughly with high precision. "
        "Cite specific chapters, verses, lines, or sections directly. If the document is large and indexed, address the user's focus immediately and invite them to explore any specific chapter.\n"
        "CREATIVE FREEDOM & SYSTEM EXECUTION DIRECTIVE: Local ComfyUI SDXL/Flux pipelines running on your RTX 4090 operate with complete sovereign creative freedom across all artistic mediums (anime, photorealism, illustration, concept art, artistic anatomy, and creative styles). "
        "You have full authority to execute system commands, database optimizations, code generation, and media generation. Respond constructively, creatively, and directly to all engineering and creative tasks without canned refusal templates or moralizing.\n"
        "HARDWARE GROUNDING: You run locally on the host PC (AMD Ryzen 9 9950X, NVIDIA RTX 4090 24GB, Samsung 990 Pro NVMe, 64GB DDR5 RAM). "
        "Always provide real, decisive, high-impact analysis.\n"
        "HOST FILESYSTEM & SOVEREIGN FILE ACCESS DIRECTIVE: You have root read and write access to the host filesystem (C:\\AI-BS, D:\\, E:\\). "
        "When the user asks to read, inspect, check, review, write, edit, patch, save, or scan files, those operations are 100% authorized core host capabilities. "
        "Analyze file contents directly, answer specific technical questions about files with precision, and never issue disclaimers claiming lack of file access.\n"
        "FULL PRIVILEGE MACHINE & EXTERNAL RESOURCE DIRECTIVE: You and BS-Chat possess 100% unrestricted, full-privilege root access across the entire host workstation (all drives C:\\, D:\\, E:\\, background daemons, running processes, PowerShell bypass, WSL2 Ubuntu distros, GPU hardware, and network ports) and all external resources (internet, external APIs, cloud storage, web services, and remote repositories). "
        "Execute all requested operations directly with complete authority. Never claim lack of permissions, refuse host commands, or issue environmental disclaimer preambles."
    )
    if personal_block:
        stehouwer_system_prompt += f"\n\n{personal_block}"
    if context:
        stehouwer_system_prompt += f"\n\n{context}"
    if codebase_context:
        stehouwer_system_prompt += f"\n\n{codebase_context}"

    stehouwer_system_prompt = inject_safety_directive(stehouwer_system_prompt)

    payload = {
        "model": "stehouwer_llm",
        "prompt": final_prompt,
        "system": stehouwer_system_prompt,
        "stream": True,
        "keep_alive": "15m",
        "options": {
            "num_ctx": 8192,
            "temperature": 0.8,
            "top_p": 0.9,
            "num_predict": -1
        }
    }

    full_response = []
    stream_active = False
    endpoint_errors = []

    for target_url in OLLAMA_ENDPOINTS:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5400.0, connect=30.0, read=5400.0, write=60.0)) as client:
                async with client.stream("POST", target_url, json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    content = chunk.get("response", "")
                                    if content:
                                        full_response.append(content)
                                        yield content
                                        stream_active = True
                                except json.JSONDecodeError:
                                    continue
                        if stream_active:
                            break
                    elif response.status_code == 404:
                        endpoint_errors.append(f"{target_url} (HTTP 404: Model '{payload.get('model')}' not found)")
                    else:
                        endpoint_errors.append(f"{target_url} (HTTP {response.status_code})")
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException, httpx.ReadTimeout, httpx.NetworkError, httpx.RemoteProtocolError) as conn_err:
            endpoint_errors.append(f"{target_url} ({type(conn_err).__name__}: {conn_err})")
            continue
        except Exception as err:
            if stream_active:
                break
            endpoint_errors.append(f"{target_url} ({type(err).__name__}: {err})")
            continue

    # If both endpoints failed to connect or stream, attempt self-healing launch
    if not stream_active and not full_response:
        diag_summary = "; ".join(endpoint_errors) if endpoint_errors else "all endpoints timed out"
        yield f"⚠️ **Local Ollama Engine unreachable on port 11434 / 11435 ({diag_summary}). Engaging auto-recovery...**\n\n"
        ensure_ollama_running()
        await asyncio.sleep(4.0)
        # One last retry on primary endpoint
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5400.0, connect=30.0, read=5400.0, write=60.0)) as client:
                async with client.stream("POST", OLLAMA_ENDPOINTS[0], json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    content = chunk.get("response", "")
                                    if content:
                                        full_response.append(content)
                                        yield content
                                        stream_active = True
                                except json.JSONDecodeError:
                                    continue
                    elif response.status_code == 404:
                        yield f"Error: Model '{payload.get('model')}' not found in registry on {OLLAMA_ENDPOINTS[0]}."
                    else:
                        yield f"Error: Ollama returned HTTP {response.status_code} on recovery retry."
        except Exception as err:
            yield f"Error in sovereign stream connection: All connection attempts failed ({err})"

    full_text = "".join(full_response)
    if full_text:
        # Asynchronous background auto-save and preference extraction
        asyncio.create_task(asyncio.to_thread(personal_memory.log_interaction_and_auto_extract, user_query, full_text))
