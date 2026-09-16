import argparse
import json
import os
import sys


def load_personas():
    personas_path = os.path.join(os.path.dirname(__file__), "ai_bs_personas.json")
    if not os.path.exists(personas_path):
        print(f"Error: {personas_path} not found.")
        return {}
    with open(personas_path, "r") as f:
        return json.load(f)


def run_agent(agent_key, personas):
    if agent_key not in personas:
        print(f"[Daemon] Unknown agent persona: {agent_key}")
        sys.exit(1)

    persona_info = personas[agent_key]
    print(f"==================================================")
    print(f"Booting Agent Matrix Protocol: {agent_key}")
    print(f"Alias: {persona_info['alias']}")
    print(f"Persona: {persona_info['persona']}")
    print(f"Capabilities: {persona_info['capabilities']}")
    print(f"==================================================")
    print(f"[Daemon] {persona_info['alias']} running in background...")

    import time
    import urllib.request
    import json
    import os

    # Try to import bullshit_polyglot for autonomous execution
    try:
        import bullshit_polyglot
    except ImportError:
        polyglot = None
        print(
            f"[Daemon] Warning: polyglot execution engine not available to {agent_key}"
        )

    sandbox_dir = os.path.join(os.path.dirname(__file__), "sandbox")

    try:
        while True:
            # The Scavenger Loop
            if polyglot and os.path.exists(sandbox_dir):
                for file in os.listdir(sandbox_dir):
                    if file.endswith(".error"):
                        script_name = file.replace(".error", "")
                        script_path = os.path.join(sandbox_dir, script_name)
                        error_path = os.path.join(sandbox_dir, file)

                        if os.path.exists(script_path):
                            print(
                                f"[{persona_info['alias']}] Found failed script: {script_name}. Attempting to fix..."
                            )

                            with open(script_path, "r", encoding="utf-8") as f:
                                script_code = f.read()
                            with open(error_path, "r", encoding="utf-8") as f:
                                error_log = f.read()

                            prompt = (
                                f"You are {persona_info['alias']}. {persona_info['persona']}\n"
                                f"A script failed to execute in the sandbox. Your job is to fix it.\n\n"
                                f"SCRIPT:\n```python\n{script_code}\n```\n\n"
                                f"ERROR:\n{error_log}\n\n"
                                f"Output ONLY the corrected Python script without any markdown formatting or explanations."
                            )

                            # Call local Ollama
                            try:
                                req = urllib.request.Request(
                                    "http://127.0.0.1:11434/api/generate",
                                    data=json.dumps(
                                        {
                                            "model": "stehouwer_llm",  # or default fallback
                                            "prompt": prompt,
                                            "stream": False,
                                        }
                                    ).encode("utf-8"),
                                    headers={"Content-Type": "application/json"},
                                )
                                with urllib.request.urlopen(
                                    req, timeout=120
                                ) as response:
                                    res_body = json.loads(
                                        response.read().decode("utf-8")
                                    )
                                    fixed_code = res_body.get("response", "").strip()

                                    # Strip markdown if LLM accidentally includes it
                                    if fixed_code.startswith("```python"):
                                        fixed_code = fixed_code[9:]
                                    if fixed_code.endswith("```"):
                                        fixed_code = fixed_code[:-3]

                                    print(
                                        f"[{persona_info['alias']}] Generated fix. Applying and re-executing..."
                                    )

                                    # Overwrite the script with the fix
                                    with open(script_path, "w", encoding="utf-8") as f:
                                        f.write(fixed_code.strip())

                                    # Delete the error log so we don't infinitely loop if it fails again (it will generate a new one)
                                    os.remove(error_path)

                                    # Execute it
                                    ext = (
                                        "python"
                                        if script_name.endswith(".py")
                                        else "powershell"
                                    )
                                    polyglot.execute_polyglot_command(
                                        fixed_code.strip(), ext
                                    )

                            except Exception as e:
                                print(
                                    f"[{persona_info['alias']}] Error calling LLM or fixing script: {e}"
                                )

            time.sleep(30)

    except KeyboardInterrupt:
        print(f"[Daemon] {persona_info['alias']} shutting down.")


def start_fastapi_server():
    # To mock the FastAPI backend that the frontend looks for on port 8000
    try:
        import uvicorn
        from fastapi import Request, FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import StreamingResponse, JSONResponse
        import json
        import httpx

        from core.system_logger import setup_logger
        setup_logger()

        app = FastAPI(title="AI-BS Backend API")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Import and include the System Health router
        from routers.system_health_router import router as system_health_router
        app.include_router(system_health_router)

        # Import and include the ComfyUI router
        from routers.comfyui_router import router as comfyui_router
        app.include_router(comfyui_router)

        # Import and include the Wan Media router (Wan-Dancer & WanSong)
        try:
            from routers.wan_media_router import router as wan_media_router
            app.include_router(wan_media_router)
        except ImportError as e:
            print(f"Warning: Could not load wan_media_router: {e}")
        
        # Import and include the Unreal Lifecycle router
        from core.unreal_lifecycle_daemon import unreal_router
        app.include_router(unreal_router)

        # Import and include the Lexicon Vault router
        from routers.lexicon_router import router as lexicon_router
        app.include_router(lexicon_router)

        # Import and include the Master Matrix EventBus router
        from routers.matrix_router import router as matrix_router
        app.include_router(matrix_router)

        # Import and include the Multi-Agent Gateway & Task Routing router
        from routers.agent_routing import router as agent_routing_router
        app.include_router(agent_routing_router)

        # Import and include the Drop Sniffer & Watchdog Telemetry router
        from routers.drop_sniffer_router import router as drop_sniffer_router
        app.include_router(drop_sniffer_router)

        # Import and include the VST3 Engine router
        from routers.vst_router import router as vst_router
        app.include_router(vst_router)

        @app.get("/")
        def read_root():
            return {"status": "AI-BS Backend Online"}

        @app.api_route(
            "/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        )
        async def catch_all(request: Request, full_path: str):
            body = await request.body()
            print(f"Received request: {request.method} /{full_path}")

            # Proxy to Ollama for chat completions
            if "chat/completions" in full_path:
                try:
                    req_json = json.loads(body) if body else {}

                    if req_json.get("stream", False):

                        async def stream_generator():
                            async with httpx.AsyncClient() as client:
                                async with client.stream(
                                    "POST",
                                    "http://127.0.0.1:11434/v1/chat/completions",
                                    json=req_json,
                                    timeout=300.0,
                                ) as r:
                                    async for chunk in r.aiter_bytes():
                                        yield chunk

                        return StreamingResponse(
                            stream_generator(), media_type="text/event-stream"
                        )
                    else:
                        async with httpx.AsyncClient() as client:
                            r = await client.post(
                                "http://127.0.0.1:11434/v1/chat/completions",
                                json=req_json,
                                timeout=300.0,
                            )
                            return JSONResponse(
                                status_code=r.status_code, content=r.json()
                            )
                except Exception as e:
                    print(f"Error proxying to local LLM: {e}")
                    return JSONResponse(status_code=500, content={"error": str(e)})

            elif "models" in full_path:
                try:
                    async with httpx.AsyncClient() as client:
                        r = await client.get(
                            "http://127.0.0.1:11434/v1/models", timeout=10.0
                        )
                        return JSONResponse(status_code=r.status_code, content=r.json())
                except Exception as e:
                    print(f"Error proxying models: {e}")
                    return JSONResponse(status_code=500, content={"error": str(e)})

            elif (
                "traffic-summary" in full_path
                or "analytics/traffic-summary" in full_path
            ):
                try:
                    from commercial_gateway.site_analytics_router import (
                        get_site_traffic_summary,
                    )

                    return await get_site_traffic_summary(limit=50)
                except Exception as e:
                    return JSONResponse(status_code=500, content={"error": str(e)})

            elif "analytics/track" in full_path:
                try:
                    from commercial_gateway.site_analytics_router import (
                        track_site_beacon,
                        TrafficBeaconPayload,
                    )

                    req_json = json.loads(body) if body else {}
                    payload = TrafficBeaconPayload(**req_json)
                    return await track_site_beacon(payload, request)
                except Exception as e:
                    return JSONResponse(status_code=500, content={"error": str(e)})

            elif full_path == "api/v1/lost-property":
                if request.method == "GET":
                    cache_file = os.path.join(
                        os.path.dirname(__file__), "core", "lost_property_cache.json"
                    )
                    if os.path.exists(cache_file):
                        with open(cache_file, "r") as f:
                            data = json.load(f)
                        return {"status": "success", "data": data}
                    return {"status": "success", "data": []}

            elif full_path == "api/v1/lost-property/scan":
                if request.method == "POST":
                    try:
                        from core.lost_property_scanner import run_scan

                        result = run_scan()
                        return JSONResponse(
                            status_code=200 if "error" not in result else 500,
                            content=result,
                        )
                    except Exception as e:
                        return JSONResponse(status_code=500, content={"error": str(e)})

            elif full_path == "api/v1/emails":
                if request.method == "GET":
                    cache_file = os.path.join(
                        os.path.dirname(__file__), "core", "emails_cache.json"
                    )
                    if os.path.exists(cache_file):
                        with open(cache_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        return {"status": "success", "data": data}
                    return {"status": "success", "data": []}

            elif "health" in full_path:
                import time

                return {
                    "status": "online",
                    "service": "AI-BS Commercial Gateway",
                    "version": "1.0.0-sandboxed",
                    "gpu_accelerated": True,
                    "timestamp": time.time(),
                }

            elif full_path == "api/v1/demos/lead-forager/stream":
                try:
                    from demo_lead_forager import generate_leads_stream
                    return StreamingResponse(generate_leads_stream(), media_type="text/event-stream")
                except Exception as e:
                    return JSONResponse(status_code=500, content={"error": str(e)})

            elif full_path == "api/v1/demos/booking/chat":
                if request.method == "POST":
                    try:
                        from demo_autonomous_booking import process_chat_turn
                        req_json = json.loads(body) if body else {}
                        user_message = req_json.get("message", "")
                        history = req_json.get("history", "")
                        
                        result = process_chat_turn(user_message, history)
                        return JSONResponse(status_code=200, content=result)
                    except Exception as e:
                        return JSONResponse(status_code=500, content={"error": str(e)})

            elif full_path == "api/v1/demos/ghost/launch":
                if request.method == "POST":
                    try:
                        import subprocess
                        subprocess.Popen(["C:\\AI-BS\\Launch_Ghost_Demo.bat"], cwd="C:\\AI-BS")
                        return JSONResponse(status_code=200, content={"status": "Ghost launched successfully"})
                    except Exception as e:
                        return JSONResponse(status_code=500, content={"error": str(e)})

            elif full_path.startswith("api/v1/demos/noto/"):
                import demo_noto
                endpoint = full_path.replace("api/v1/demos/noto/", "")
                
                if endpoint == "etiquette" and request.method == "POST":
                    req_json = json.loads(body) if body else {}
                    return JSONResponse(status_code=200, content=await demo_noto.handle_etiquette_chat(req_json.get("message", ""), req_json.get("history", [])))
                elif endpoint == "bocce-upsell" and request.method == "POST":
                    return JSONResponse(status_code=200, content=await demo_noto.handle_bocce_upsell())
                elif endpoint == "banquet-architect" and request.method == "POST":
                    req_json = json.loads(body) if body else {}
                    return JSONResponse(status_code=200, content=await demo_noto.handle_banquet_architect(req_json.get("prompt", "")))
                elif endpoint == "cellar-master" and request.method == "POST":
                    req_json = json.loads(body) if body else {}
                    return JSONResponse(status_code=200, content=await demo_noto.handle_cellar_master(req_json))
                elif endpoint == "plate-scraping" and request.method == "GET":
                    return JSONResponse(status_code=200, content=await demo_noto.get_plate_scraping_data())
                elif endpoint == "scheduling" and request.method == "GET":
                    return JSONResponse(status_code=200, content=await demo_noto.get_scheduling_data())
                elif endpoint == "employee-chat" and request.method == "GET":
                    return JSONResponse(status_code=200, content=await demo_noto.get_employee_chat())
                elif endpoint == "master-calendar" and request.method == "GET":
                    return JSONResponse(status_code=200, content=await demo_noto.get_master_calendar())
                elif endpoint == "anonymous-suggestion" and request.method == "POST":
                    req_json = json.loads(body) if body else {}
                    return JSONResponse(status_code=200, content=await demo_noto.handle_anonymous_suggestion(req_json.get("suggestion", ""), req_json.get("name", "")))
                elif endpoint == "nfc-timeclock" and request.method == "POST":
                    req_json = json.loads(body) if body else {}
                    return JSONResponse(status_code=200, content=await demo_noto.handle_nfc_timeclock(req_json.get("lat", 0.0), req_json.get("lng", 0.0)))

            # Generic response fallback
            return {
                "response": "Local AI environment is online.",
                "message": "Local AI environment is online.",
                "status": "success",
                "answer": "Local AI environment is online.",
                "text": "Local AI environment is online.",
            }

        print("[Backend] Starting FastAPI Server on port 8000...")
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except ImportError:
        print(
            "[Backend] 'fastapi' or 'uvicorn' not installed. Starting dummy socket on 8000 to satisfy Electron..."
        )
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 8000))
        s.listen(1)
        while True:
            conn, addr = s.accept()
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-BS CLI Router")
    parser.add_argument(
        "--agent", type=str, help="Start a specific background agent persona"
    )
    parser.add_argument(
        "--server", action="store_true", help="Start the FastAPI backend server"
    )

    args = parser.parse_args()
    personas = load_personas()

    if args.agent:
        run_agent(args.agent, personas)
    elif args.server:
        start_fastapi_server()
    else:
        parser.print_help()
