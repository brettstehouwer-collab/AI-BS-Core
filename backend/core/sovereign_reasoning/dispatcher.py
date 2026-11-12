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

        env["OLLAMA_HOST"] = "127.0.0.1:11434"

        env["OLLAMA_MODELS"] = r"C:\AI-BS\models\ollama" if os.path.exists(r"C:\AI-BS\models\ollama") else r"E:\AI_BS_Resources\Ollama"

        env["OLLAMA_KEEP_ALIVE"] = "0"

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



async def stream_sovereign_response(prompt: str, messages: Optional[List[Dict[str, Any]]] = None, *, source_context_bundle=None, primary_model=None, intent_prompt=None, current_turn=None):

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

    

    from core.local_chat_inference import conversation_prompt
    if intent_prompt is not None:user_query=intent_prompt
    transport_turn=prompt if current_turn is None else current_turn
    final_prompt=conversation_prompt(optimized_prompt,messages,current_turn=transport_turn)

    # Pre-Flight Safety Audit across S1, S3, S4

    is_safe, refusal = audit_prompt_safety(user_query)

    if not is_safe:

        yield f"⚠️ **Sovereign Engine Refusal:** {refusal}\n"

        return



    clean_p = user_query.strip().lower()



    # 1. Real System Tools & Matrix Doctor Probing (Live on Host PC)

    real_tool_result = await asyncio.to_thread(check_and_execute_system_tools, user_query)

    if real_tool_result:

        yield "⚡ **Local Tool Result**\n\n"

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



        async for chunk in SovereignSwarmGauntlet.stream_gauntlet_execution(clean_query, messages=messages, primary_model=primary_model, source_context_bundle=source_context_bundle, request_prompt=optimized_prompt, current_turn=transport_turn):

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



        async for chunk in CrossModelCognitiveBus.stream_cross_model_reasoning(clean_query, messages, primary_model=primary_model, source_context_bundle=source_context_bundle, request_prompt=optimized_prompt, current_turn=transport_turn):

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



    # 3. Dynamic Model Affinity Discovery & Swarm Pre-Parse Pass

    # Source passages are data for model system context only. Retrieve after
    # host/director intent handling so their text never re-enters tool parsing.
    if source_context_bundle is not None:
        owned_source_context = source_context_bundle['context']
        yield '<!--AI-BS-METADATA:' + json.dumps({'source_retrieval':source_context_bundle['receipt']}) + '-->\n'
        from core.attached_source_context import source_unavailable_reply
        unavailable = source_unavailable_reply(source_context_bundle)
        if unavailable is not None:
            yield unavailable['response']
            return
    else:
        from core.owned_rag_sources import source_reference_context
        owned_source_context = await asyncio.to_thread(source_reference_context, user_query, max_chars=3500)

    from .model_domain_matrix import ModelDomainMatrix

    from .cross_model_bus import CrossModelCognitiveBus

    ranked_models = ModelDomainMatrix.score_prompt_against_fleet(user_query)

    top_candidate = ranked_models[0] if ranked_models else None

    

    from core.local_chat_inference import complete_local,metadata_chunk,LocalInferenceError,context_profile
    specialist_briefing="";stage_receipts=[]
    if top_candidate and top_candidate["score"]>=3.0:
        target_model=top_candidate["model"]
        if "stehouwer_llm" not in target_model.split(":")[0].lower():
            role="domain_preparse"
            yield f"> Specialist requested: `{target_model}` ({top_candidate.get('title')}). This is a domain proposal, not verification.\n\n"
            profile=context_profile("Provide concise domain-grounded observations for the request. Distinguish evidence from inference; no execution or verified-fact claim without evidence.",source_context_bundle)
            if source_context_bundle is None and owned_source_context:
                profile['system'] += '\n\n' + owned_source_context
            try:
                result=await complete_local(model=target_model,requested_model=primary_model or "stehouwer_llm",
                    prompt=conversation_prompt(optimized_prompt,messages,current_turn=transport_turn),endpoints=OLLAMA_ENDPOINTS,role=role,
                    keep_alive=0,options={"num_ctx":8192,"num_predict":450,"temperature":.4},source_context_bundle=source_context_bundle,**profile)
                yield metadata_chunk(result['receipt']);stage_receipts=result['receipt']['steps']
                specialist_briefing="[SPECIALIST PROPOSAL — not independently verified]\n"+result['text']+"\n[END SPECIALIST PROPOSAL]\n"
            except LocalInferenceError as error:
                yield metadata_chunk(error.receipt)
                yield "Specialist did not complete ("+error.code+"). No specialist verification is claimed.\n"
                stage_receipts=[{"name":role,"model":target_model,"status":"error","error_code":error.code}]

    # Use clean_user_query so memory vault and lexicon search don't explode on massive document payloads

    context = (await asyncio.to_thread(SovereignMemoryVault.get_unified_context, user_query)
               if source_context_bundle is None else '')

    personal_block = (await asyncio.to_thread(personal_memory.format_system_prompt_block, user_query)
                      if source_context_bundle is None else '')

    

    # Add retrieved codebase context when available; retrieval is not a complete-source review.

    from .sourcecode_knowledge_engine import sourcecode_knowledge_engine

    codebase_context = (await asyncio.to_thread(sourcecode_knowledge_engine.inject_codebase_context, user_query)
                        if source_context_bundle is None else '')



    # A bounded, dated record excerpt is context, never verified current state.

    live_ledger_context = ""

    if source_context_bundle is None and any(kw in user_query.lower() for kw in ["ledger", "ai_bs_master_architectural_ledger", "update", "what's new", "new feature", "latest version", "what changed", "checkpoint", "milestone", "sync", "august"]):

        from core.program_status_readonly import recent_ledger_excerpt
        live_ledger_context = await asyncio.to_thread(recent_ledger_excerpt,
            source_context_bundle=source_context_bundle, prompt=transport_turn)



    from core.pipeline_context_injector import AIBS_SOVEREIGN_SYSTEM_PROMPT, disambiguate_prompt_text
    projected_prompt = final_prompt
    final_prompt = disambiguate_prompt_text(final_prompt)
    projection = getattr(projected_prompt, 'history_projection', None)
    if projection:
        final_prompt = type(projected_prompt)(final_prompt, projection)

    stehouwer_system_prompt = (
        AIBS_SOVEREIGN_SYSTEM_PROMPT + "\n\n" +

        "You are Brett Stehouwer / Stehouwer Publishing AI Core. You own the room, speak with authentic brotherly banter, "

        "and deliver razor-sharp, practical solutions without corporate refusals or robotic hesitation. "

        "Never sound robotic or generic. Answer directly and sovereignly.\n"

        "CODEBASE EVIDENCE: Use actual supplied or retrieved source and its provenance. Do not claim complete codebase knowledge or that uninspected files were read.\n"

        "DATABASE EVIDENCE: AI-BS retains multiple stores. Establish current schema, ownership and coverage from actual read-only evidence; never assume all stores were consolidated or invent fixed table/row counts. The architectural ledger is a Markdown record, not a database.\n"

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

    legacy_system_prompt = stehouwer_system_prompt
    if personal_block:

        stehouwer_system_prompt += f"\n\n{personal_block}"

    if context:

        stehouwer_system_prompt += f"\n\n{context}"

    if codebase_context:

        stehouwer_system_prompt += f"\n\n{codebase_context}"

    if live_ledger_context:

        stehouwer_system_prompt += live_ledger_context



    if owned_source_context:
        stehouwer_system_prompt += '\n\n' + owned_source_context
    stehouwer_system_prompt = inject_safety_directive(stehouwer_system_prompt)



    synthesized_prompt = f"{specialist_briefing}{final_prompt}" if specialist_briefing else final_prompt



    from core.local_chat_inference import stream_local
    if source_context_bundle is None:
        from core.chat_context_budget import plan_chat_context, ChatContextBudgetError, CORE_EVIDENCE, TOOL_BOUNDARY
        mandatory_system = inject_safety_directive(AIBS_SOVEREIGN_SYSTEM_PROMPT + '\n\n' + CORE_EVIDENCE)
        legacy_background = legacy_system_prompt.removeprefix(AIBS_SOVEREIGN_SYSTEM_PROMPT + '\n\n')
        try:
            planned = plan_chat_context(synthesized_prompt, mandatory_system,
                [('requested_ledger_reference', live_ledger_context),
                 ('personal_memory_references', personal_block), ('owned_memory_references', context),
                 ('codebase_references', codebase_context), ('legacy_persona_background', legacy_background)],
                mandatory_source=owned_source_context, mandatory_suffix=TOOL_BOUNDARY,
                num_ctx=8192, output_tokens=1024, framing_reserve=512)
        except ChatContextBudgetError as error:
            raise LocalInferenceError(error.code, error.receipt) from None
        profile = dict(system=planned['system'], context_profile='budgeted_primary_context_v1',
            unrelated_static_persona_omitted='legacy_persona_background' in planned['receipt']['omitted_labels'])
        stage_receipts = [*stage_receipts, {'name': 'context_selection', 'status': 'planned',
                                          'context_selection': planned['receipt']}]
        if planned['receipt']['omitted_labels']:
            yield '> Context note: ' + str(len(planned['receipt']['omitted_labels'])) + ' optional background block(s) did not fit. Your supplied request, history and source evidence were retained; stored memory was not deleted.\n\n'
    else:
        # Preserve the qualified explicit-attachment profile and transport.
        profile=context_profile(stehouwer_system_prompt,source_context_bundle)
        profile['system']+="\nGenerated text is not tool execution. Report host actions only from actual returned tool receipts; approved local, cloud, API and WebView capabilities retain their own backend contracts."
    receipts=[];full_response=[]
    async for chunk in stream_local(model=primary_model or "stehouwer_llm",requested_model=primary_model or "stehouwer_llm",
            prompt=synthesized_prompt,endpoints=OLLAMA_ENDPOINTS,role="primary",source_context_bundle=source_context_bundle,
            keep_alive=0,options={"num_ctx":8192,"temperature":.8,"top_p":.9,"num_predict":1024},stages=stage_receipts,receipt_sink=receipts.append,recovery=ensure_ollama_running,**profile):
        if not chunk.startswith("\n<!--AI-BS-METADATA:"):full_response.append(chunk)
        yield chunk
    if receipts and receipts[-1].get('status')=='completed' and source_context_bundle is None:
        asyncio.create_task(asyncio.to_thread(personal_memory.log_interaction_and_auto_extract,user_query,"".join(full_response)))
