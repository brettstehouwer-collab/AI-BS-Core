import json
import asyncio
import random

async def handle_etiquette_chat(message: str, history: list) -> dict:
    return {"reply": "As a Noto's professional, I must ensure the guest is heard. My simulated response is: 'I apologize for the delay. We are preparing your Veal Saltimbocca fresh to our 25-year standards.'"}

async def handle_bocce_upsell() -> dict:
    return {"status": "success", "message": "SMS dispatched to VIP table 4: 'Game getting heated? Reply PINT for a round of IPAs.'"}

async def handle_banquet_architect(prompt: str) -> dict:
    from comfy_bridge import queue_comfyui_workflow, await_generation_result, extract_output_media
    import random
    import traceback
    
    try:
        # Build SDXL Workflow
        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
            },
            "2": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": 1024, "height": 768, "batch_size": 1},
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": f"fine dining italian restaurant banquet hall, elegant decor, professional photography, {prompt}", "clip": ["1", 1]},
            },
            "4": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": random.randint(1, 100000000),
                    "steps": 25,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["1", 0],
                    "positive": ["3", 0],
                    "negative": ["6", 0],
                    "latent_image": ["2", 0],
                },
            },
            "5": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "ugly, blurry, low resolution, bad quality, cartoon, anime, artificial, watermark", "clip": ["1", 1]},
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "notos_banquet", "images": ["5", 0]}
            }
        }
        
        prompt_id = await queue_comfyui_workflow(workflow)
        history = await await_generation_result(prompt_id)
        media_info = extract_output_media(history)
        
        if media_info["image_url"]:
            return {"status": "success", "image_url": media_info["image_url"]}
        else:
            return {"status": "error", "message": "ComfyUI returned empty media."}
            
    except Exception as e:
        print("Banquet Architect Error:", traceback.format_exc())
        return {"status": "error", "message": str(e)}

async def handle_cellar_master(answers: dict) -> dict:
    return {
        "status": "success", 
        "recommendations": [
            {"name": "Barolo DOCG", "reason": "Perfect match for heavy meat dishes."},
            {"name": "Chianti Classico", "reason": "A versatile Tuscan classic."},
            {"name": "Sicilian Nero d'Avola", "reason": "Pairs with our wood-fired pizzas."}
        ]
    }

async def handle_unreal_remote_control(command: str, payload: dict) -> dict:
    """
    Interfaces with the Unreal Engine Web Remote Control API (typically port 30010).
    Allows AI-BS to dynamically alter 3D scene properties (lighting, actors, materials) in real-time.
    """
    import aiohttp
    import traceback
    
    UNREAL_RC_URL = "http://127.0.0.1:30010/remote/object/call"
    
    try:
        # Example payload structure for Unreal Engine Remote Control API
        # This will need to be mapped precisely to the user's Unreal Project Blueprints/Actors
        unreal_payload = {
            "objectPath": "/Game/Maps/BanquetHall.BanquetHall:PersistentLevel.SceneController_2",
            "functionName": command,
            "parameters": payload,
            "generateTransaction": True
        }
        
        # We fire the request. If Unreal is not running/configured, it will gracefully fail.
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.put(UNREAL_RC_URL, json=unreal_payload, timeout=3.0) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"status": "success", "message": "Successfully synced with Unreal Engine 3D Studio.", "data": data}
                else:
                    return {"status": "error", "message": f"Unreal Engine returned HTTP {response.status}"}
                    
    except aiohttp.ClientConnectorError as e:
        print("Unreal Remote Control Error: Connection Refused. Is the UE Remote Control API running on port 30010?")
        return {"status": "warning", "message": "Unreal Engine is currently offline. Web state updated, but 3D sync failed.", "error": "Connection Refused"}
    except Exception as e:
        print("Unreal Remote Control Error (is the UE Remote Control API running on port 30010?):", e)
        # We return success for the frontend demo even if it fails, so the user can test the UI
        # before fully configuring their Unreal Project.
        return {"status": "warning", "message": "Unreal connection failed, but frontend state updated.", "error": str(e)}

async def handle_media_assistant_nlp(prompt: str) -> dict:
    """
    Intelligent Media Assistant Orchestrator.
    Takes a natural language prompt from the user, uses a local LLM to deduce the intent,
    and returns a structured JSON payload with instructions for the frontend to auto-select
    tools and update state (e.g. 2D vs 3D, table counts, lighting).
    """
    import httpx
    import json
    
    system_prompt = '''You are the Stehouwer Media Assistant, an intelligent orchestrator for the Banquet Architect Studio.
    You map user natural language requests into a strict JSON payload that the frontend UI will execute.
    
    Available Actions:
    1. "UPDATE_STATE": Update the sliders and dropdowns. 
       - valid keys: "tableCount" (integer 5-30), "lightingRig" (string: "Daylight Bright", "Evening Warm", "Intimate Candlelight", "Corporate Cool"), "floralColor" (string: "White/Cream", "Tuscan Red/Gold", "Blush Pink", "Minimalist Greenery"), "stylePreset" (string: "minimalist", "opulent", "rustic", "corporate"), "spawnActors" (array of objects), "materialOverride" (string).
    2. "SPAWN_ACTORS_HYBRID": To spawn assets, pass them in the `spawnActors` array as objects:
       `{"asset_keyword": "chair", "layout_mode": "ai_transform", "transform": {"x": 50, "y": 0, "z": 0, "rotation_z": 90}}` for precise positioning.
       `{"asset_keyword": "table", "layout_mode": "engine_procedural", "procedural_group": "dining_area"}` if you want to let Unreal handle the layout (to prevent stacking).
       The backend will automatically search the global Unreal Asset Registry (5000+ items) using your `asset_keyword` and inject the real package path.
    3. "TRIGGER_2D": Set this to true if the user implies they want to generate, render, or visualize a 2D image via ComfyUI.
    4. "TRIGGER_3D": Set this to true if the user implies they want to push to Unreal Engine or 3D.
    
    Respond ONLY with raw JSON in this exact schema, nothing else (no markdown, no backticks).
    {
      "assistant_reply": "A brief, professional 1-sentence confirmation of what you are adjusting.",
      "state_updates": {
        "tableCount": null,
        "lightingRig": null,
        "floralColor": null,
        "stylePreset": null,
        "spawnActors": null,
        "materialOverride": null,
        "prompt2D": null
      },
      "trigger_2d": false,
      "trigger_3d": false
    }
    Leave fields as null if they aren't explicitly requested to change. If the user provides a general aesthetic description, put it in "prompt2D".
    '''
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "qwen2.5-coder:latest",
                    "prompt": f"{system_prompt}\n\nUser Request: {prompt}\n\nJSON:",
                    "stream": False,
                    "options": {
                        "temperature": 0.1
                    }
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                # Clean up any potential markdown block
                if result.startswith("```json"):
                    result = result[7:]
                if result.startswith("```"):
                    result = result[3:]
                if result.endswith("```"):
                    result = result[:-3]
                    
                parsed_json = json.loads(result.strip())
                
                # Secondary Asset Lookup Pass (Hybrid Architecture)
                spawn_actors = parsed_json.get("state_updates", {}).get("spawnActors")
                if spawn_actors and isinstance(spawn_actors, list):
                    import sqlite3
                    import os
                    db_path = os.path.join(os.path.dirname(__file__), "unreal_assets.db")
                    if os.path.exists(db_path):
                        conn = sqlite3.connect(db_path)
                        try:
                            conn.execute("PRAGMA journal_mode=WAL;")
                            conn.execute("PRAGMA synchronous=NORMAL;")
                        except Exception:
                            pass
                        c = conn.cursor()
                        
                        resolved_count = 0
                        for actor_obj in spawn_actors:
                            if isinstance(actor_obj, dict) and "asset_keyword" in actor_obj:
                                keyword = actor_obj["asset_keyword"]
                                c.execute("SELECT package_path, asset_name FROM assets WHERE asset_name LIKE ? LIMIT 1", (f"%{keyword}%",))
                                row = c.fetchone()
                                if row:
                                    # Inject true package path and asset name
                                    actor_obj["package_path"] = row[0]
                                    actor_obj["asset_name"] = row[1]
                                    resolved_count += 1
                                else:
                                    actor_obj["package_path"] = f"/Fallback/Path/{keyword}"
                                    actor_obj["asset_name"] = keyword
                                    
                                # Default to engine_procedural if not specified
                                if "layout_mode" not in actor_obj:
                                    actor_obj["layout_mode"] = "engine_procedural"
                                    
                        conn.close()
                        
                        if resolved_count > 0:
                            parsed_json["assistant_reply"] += f" I mapped {resolved_count} specific 3D assets from the registry."
                            
                # Cleanup legacy search_assets if present
                if "search_assets" in parsed_json:
                    del parsed_json["search_assets"]

                return {
                    "status": "success",
                    "data": parsed_json
                }
            else:
                return {"status": "error", "message": f"LLM responded with HTTP {response.status_code}"}
                
    except Exception as e:
        print(f"Error in handle_media_assistant_nlp: {e}")
        return {"status": "error", "message": f"Media Assistant failed: {str(e)}"}

async def get_plate_scraping_data() -> dict:
    return {
        "status": "success",
        "data": [
            {"name": "Spaghetti Carbonara", "waste_percent": 12},
            {"name": "Veal Saltimbocca", "waste_percent": 5},
            {"name": "House Salad", "waste_percent": 28},
            {"name": "Chicken Parmesan", "waste_percent": 15},
            {"name": "Tiramisu", "waste_percent": 2}
        ]
    }

async def get_scheduling_data() -> dict:
    return {
        "status": "success",
        "shifts": [
            {"employee": "Mario", "role": "Head Chef", "location": "GR", "time": "14:00 - 22:00"},
            {"employee": "Luigi", "role": "Bartender", "location": "GH", "time": "16:00 - 00:00", "ai_flag": "High Volume Expected"}
        ]
    }

async def get_employee_chat() -> dict:
    return {
        "status": "success",
        "departments": [
            {
                "department": "Management & Urgent Alerts",
                "icon": "🚨",
                "channels": [
                    {
                        "id": "urgent-86",
                        "name": "urgent-86-manager-alerts",
                        "position": "All Management & Lead Staff",
                        "unread": 2,
                        "messages": [
                            {"sender": "Chef Marco", "role": "Executive Chef", "time": "6:14 PM", "text": "🚨 86 Chilean Sea Bass for the rest of tonight! Switching table 14 to Grilled Halibut."},
                            {"sender": "Tony Noto", "role": "Owner / Director", "time": "6:18 PM", "text": "Acknowledged. Update POS table screens and alert host stand immediately."}
                        ]
                    },
                    {
                        "id": "gm-handoff",
                        "name": "general-manager-handoff",
                        "position": "Shift Supervisors & GMs",
                        "unread": 0,
                        "messages": [
                            {"sender": "Sarah M.", "role": "Night GM (Grand Rapids)", "time": "4:45 PM", "text": "Private banquet ballroom is locked in for 175 guests at 6:30 PM. Extra valet attendant staffed."},
                            {"sender": "David L.", "role": "GM (Grand Haven)", "time": "5:02 PM", "text": "Grand Haven patio heaters are active. Waterfront bocce courts fully booked."}
                        ]
                    }
                ]
            },
            {
                "department": "Front of House (FOH)",
                "icon": "🤵",
                "channels": [
                    {
                        "id": "foh-servers",
                        "name": "servers-bartenders",
                        "position": "Waitstaff, Bartenders & Runners",
                        "unread": 1,
                        "messages": [
                            {"sender": "Anna K.", "role": "Lead Server", "time": "5:30 PM", "text": "Table 8 requested Barolo decanted 20 mins prior to entree service."},
                            {"sender": "Luigi P.", "role": "Head Bartender", "time": "5:32 PM", "text": "Smoked rosemary simple syrup is prepped at the main bar."}
                        ]
                    },
                    {
                        "id": "hosts-vip",
                        "name": "hosts-concierge-vip",
                        "position": "Host Stand & Greeters",
                        "unread": 0,
                        "messages": [
                            {"sender": "Elena R.", "role": "Hostess Lead", "time": "5:15 PM", "text": "Mayor's dinner party arriving at 7:00 PM for private booth #4. Tony requested personally greeting them."}
                        ]
                    },
                    {
                        "id": "sommeliers",
                        "name": "sommeliers-wine-cellar",
                        "position": "Sommeliers & Cellar Staff",
                        "unread": 0,
                        "messages": [
                            {"sender": "Matteo V.", "role": "Lead Sommelier", "time": "4:30 PM", "text": "Cellar Master AI recommended pushing the 2018 Chianti Classico Riserva tonight — 14 bottles chilled and staged."}
                        ]
                    }
                ]
            },
            {
                "department": "Back of House (BOH)",
                "icon": "🍳",
                "channels": [
                    {
                        "id": "line-cooks",
                        "name": "kitchen-line-chefs",
                        "position": "Line Cooks, Sauté & Grill",
                        "unread": 1,
                        "messages": [
                            {"sender": "Chef Marco", "role": "Executive Chef", "time": "5:00 PM", "text": "Veal Saltimbocca prep is 100% complete. Keep sear times sharp for the 7 PM rush."}
                        ]
                    },
                    {
                        "id": "dish-pit",
                        "name": "dish-pit-stewarding",
                        "position": "Dish Stewards & Sanitation",
                        "unread": 0,
                        "messages": [
                            {"sender": "Carlos T.", "role": "Steward Lead", "time": "5:10 PM", "text": "Plate scraping camera telemetry calibrated. Rinsing stations fully stocked."}
                        ]
                    },
                    {
                        "id": "pastry",
                        "name": "pastry-dessert-station",
                        "position": "Pastry Chefs & Dessert Expo",
                        "unread": 0,
                        "messages": [
                            {"sender": "Giulia B.", "role": "Pastry Chef", "time": "4:15 PM", "text": "Tiramisu sheet #2 sliced and espresso gelato churned for banquet dessert course."}
                        ]
                    }
                ]
            },
            {
                "department": "Banquets & Event Operations",
                "icon": "🏛️",
                "channels": [
                    {
                        "id": "banquet-ops",
                        "name": "banquet-event-logistics",
                        "position": "Banquet Captains & Setup Crew",
                        "unread": 0,
                        "messages": [
                            {"sender": "Rachel H.", "role": "Banquet Captain", "time": "4:00 PM", "text": "Room setup: 15 round tables + head table with champagne flute staging verified."}
                        ]
                    }
                ]
            }
        ]
    }

async def get_master_calendar() -> dict:
    return {
        "status": "success",
        "events": [
            {"title": "Smith Wedding", "date": "2026-08-15", "location": "GR Banquet Hall"},
            {"title": "Live Jazz Trio", "date": "2026-08-16", "location": "GH Bocce Courts"}
        ]
    }

async def handle_anonymous_suggestion(suggestion: str, name: str) -> dict:
    # Simulates AI categorizing and routing the suggestion safely
    return {
        "status": "success",
        "message": f"Suggestion securely routed to Management. {'(Submitted anonymously)' if not name else f'(Submitted as {name})'}",
        "ai_analysis": "AI Flagged as: Operational Feedback / High Priority"
    }

async def handle_nfc_timeclock(lat: float, lng: float) -> dict:
    # Noto's Grand Rapids approx coords: 42.915, -85.505
    # For simulation, we assume any latitude > 40 is 'inside' and < 40 is 'outside' just to mock it easily
    if lat > 40.0:
        return {
            "status": "success",
            "message": "NFC Tap Accepted: GPS verified inside 50ft Geofence. Clocked IN.",
            "color": "#3fb950"
        }
    else:
        return {
            "status": "error",
            "message": "NFC Tap Rejected: GPS coordinates located outside Geofence.",
            "color": "#d73a49"
        }
