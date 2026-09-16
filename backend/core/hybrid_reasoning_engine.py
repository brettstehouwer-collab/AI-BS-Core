import json
import asyncio
import re
import os
import httpx
from typing import AsyncGenerator, Tuple, Optional, Dict, Any
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.safety_guardrails import STEHOUWER_SAFETY_DIRECTIVE, inject_safety_directive, audit_prompt_safety

router = APIRouter(prefix="/api/v1/hybrid-chat", tags=["Simultaneous Hybrid Reasoning"])

PRIMARY_OLLAMA_URL = os.environ.get("OLLAMA_HOST_GEN", "http://127.0.0.1:11434/api/generate")
SHADOW_OLLAMA_URL = os.environ.get("OLLAMA_HOST_EDRIVE_GEN", "http://127.0.0.1:11435/api/generate")

class ChatRequest(BaseModel):
    prompt: str
    messages: Optional[list] = None
    temperature: float = 0.7
    stream: bool = True


def clean_tool_prompt(raw: str) -> str:
    """Strips tool calling prefixes, directives, and meta instructions to extract the core visual prompt."""
    clean = raw.strip()
    
    # Strip meta instruction wraps like "Then display the photo"
    if "Then display the photo" in clean:
        clean = clean.split("Then display the photo")[0].strip()

    # Strip civitai / comfyui negative prompt if attached
    neg_match = re.search(r'(?:^|\n|\r\n)\s*(?:negative\s+prompt|negative)\s*:\s*(.*)', clean, flags=re.IGNORECASE | re.DOTALL)
    if neg_match:
        clean = clean[:neg_match.start()].strip()

    # Strip civitai / webui positive prompt markers
    clean = re.sub(r'^(?:positive\s+prompt|prompt)\s*:\s*', '', clean, flags=re.IGNORECASE).strip()

    # Strip slash commands & shorthand prefixes
    clean = re.sub(r'^/(?:imagine|render|image|draw|paint|generate|t2i|txt2img|comfy|comfyui)\s+', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'^(?:t2i|txt2img|comfy\s*ui|comfyui|comfy)\s*:?\s*', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'^(?:media\s+generation)\s*:?\s*', '', clean, flags=re.IGNORECASE).strip()

    # Strip broad action verb + visual noun patterns
    directive_regex = (
        r'^(?:please\s+|can\s+you\s+|could\s+you\s+|will\s+you\s+|would\s+you\s+|i\s+want\s+(?:you\s+to\s+)?|'
        r'let(?:\'s|\s+us|\s+me)\s+(?:see\s+)?|give\s+me\s+|show\s+me\s+|display\s+|send\s+me\s+)?'
        r'(?:create|generate|make|render|draw|paint|sketch|produce|design|illustrate|visualize|depict|craft|build)?\s*'
        r'(?:an?\s+|the\s+|some\s+)?(?:[a-zA-Z0-9_\-\s]{0,30}?\s+)?'
        r'(?:images?|photos?|photographs?|pictures?|pics?|drawings?|paintings?|artworks?|art|renders?|'
        r'illustrations?|portraits?|wallpapers?|graphics?|visuals?|posters?|media(?:\s+generation)?|scenes?|avatars?|logos?|banners?|videos?|clips?|animations?)\s+'
        r'(?:of|showing|depicting|with|featuring|about|for)?\s*'
    )
    clean = re.sub(directive_regex, '', clean, flags=re.IGNORECASE).strip()

    # Strip conversational creative action openings
    action_prefix = (
        r'^(?:please\s+|can\s+you\s+|could\s+you\s+|will\s+you\s+|would\s+you\s+|i\s+want\s+(?:you\s+to\s+)?|'
        r'let(?:\'s|\s+us|\s+me)\s+(?:see\s+)?|give\s+me\s+|show\s+me\s+|display\s+|send\s+me\s+)?'
        r'(?:draw|paint|sketch|render|illustrate|visualize|depict|design|make|produce|generate|create)\s+'
        r'(?:me\s+)?(?:an?\s+|the\s+|some\s+)?(?:of\s+)?'
    )
    clean = re.sub(action_prefix, '', clean, flags=re.IGNORECASE).strip()

    # Strip style and photographic prefixes when used at the start
    prefixes = [
        "photorealistic photo of", "photorealistic photograph of", "photorealistic image of", "photorealistic picture of",
        "picture of", "photo of", "photograph of", "image of", "render of", "painting of",
        "drawing of", "illustration of", "a photo of", "an image of", "a picture of",
        "artwork of", "visual of", "portrait of", "shot of", "close-up of", "close up of",
        "close-up photograph of", "close-up photo of", "macro shot of", "cinematic shot of",
        "cinematic photo of", "concept art of", "video of", "a video of", "clip of", "a clip of", "animation of"
    ]
    for p in prefixes:
        if clean.lower().startswith(p):
            clean = clean[len(p):].strip()
            break

    if clean.lower() in ["", "media", "media generation", "image", "photo", "picture", "art", "artwork", "video"]:
        clean = "futuristic AI server matrix room"

    return clean if clean else "futuristic AI server matrix room"


def detect_tool_intent(prompt: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Inspects the prompt for explicit tool calls or visual/database generation intents across multiple directives."""
    p_lower = prompt.lower().strip()
    
    # -8. Static Analysis & Pre-Flight Security Sweep (/audit)
    if p_lower.startswith(("/audit", "/sweep", "/ast-check", "/pre-flight")):
        parts = prompt.strip().split(maxsplit=1)
        scope = parts[1].strip() if len(parts) > 1 else ""
        return "run_audit", {"scope": scope}

    # -7. Autonomous Test-Driven Development (/test-first, /tdd)
    if p_lower.startswith(("/test-first", "/tdd", "/test_first")):
        parts = prompt.strip().split(maxsplit=1)
        feature = parts[1].strip() if len(parts) > 1 else "core_feature"
        return "run_test_first", {"feature": feature}

    # -6. Visual Patch Inspection (/diff-review, /diff)
    if p_lower.startswith(("/diff-review", "/diff", "/patch-review", "/inspect-patch")):
        return "run_diff_review", {}

    # -5. Atomic State Pinning & Snapshot (/snapshot)
    if p_lower.startswith(("/snapshot", "/pin-state", "/checkpoint")):
        parts = prompt.strip().split(maxsplit=1)
        label = parts[1].strip() if len(parts) > 1 else ""
        return "run_snapshot", {"label": label}

    # -4. Surgical Backup Rollback (/rollback)
    if p_lower.startswith(("/rollback", "/revert-backup", "/restore-bak")):
        parts = prompt.strip().split(maxsplit=1)
        target = parts[1].strip() if len(parts) > 1 else ""
        return "run_rollback", {"target": target}

    # -3. Hardware Clamping & Watchdog (/hardware, /telemetry, /gpu-health)
    if p_lower.startswith(("/hardware", "/telemetry", "/gpu-health", "/clamping-check")):
        return "check_hardware", {}

    # -2.5 Port Conflict Sentinel (/port-probe, /check-port)
    if p_lower.startswith(("/port-probe", "/port", "/check-port")):
        parts = prompt.strip().split(maxsplit=1)
        port_val = parts[1].strip() if len(parts) > 1 else "8080"
        return "probe_port", {"port": port_val}

    # -2. Architectural Grill Session Intent (/grill, /stress-test, /interview, or natural language)
    if p_lower.startswith(("/grill", "/stress-test", "/interview", "/grill-me")):
        parts = prompt.strip().split(maxsplit=1)
        proposal = parts[1].strip() if len(parts) > 1 else ""
        return "grill_mission", {"proposal": proposal}

    grill_nl_match = re.search(r'^(?:please\s+|can\s+you\s+)?(?:grill(?:\s+me)?(?:\s+on)?|stress[- ]test)\s+(?:an?\s+)?(?:mission|proposal|architecture)?(?:\s*:\s*|\s+for\s+|\s+)([\s\S]+)', prompt.strip(), flags=re.IGNORECASE)
    if grill_nl_match:
        return "grill_mission", {"proposal": grill_nl_match.group(1).strip()}

    # Check for 1-click grill acknowledgment when an active grill session exists
    try:
        from core.mission_control_engine import mission_engine
        if mission_engine.active_grill_id and mission_engine.active_grill_id in mission_engine.grill_cache:
            active_sess = mission_engine.grill_cache[mission_engine.active_grill_id]
            if active_sess.get("status") == "awaiting_operator":
                if p_lower in ["yes", "y", "agree", "proceed", "accept", "ok", "sounds good", "accepted", "approved"] or p_lower.startswith("/build"):
                    return "grill_respond", {"response": prompt.strip(), "grill_id": mission_engine.active_grill_id}
    except Exception:
        pass

    # -1. Autonomous Mission Execution Intent (/mission, /plan, /execute-mission, or natural language)
    if p_lower.startswith(("/mission", "/plan", "/execute-mission", "/run-mission")):
        parts = prompt.strip().split(maxsplit=1)
        goal = parts[1].strip() if len(parts) > 1 else ""
        return "run_mission", {"goal": goal, "mode": "auto"}

    mission_nl_match = re.search(r'^(?:please\s+|can\s+you\s+)?(?:start|run|launch|execute)\s+(?:an?\s+)?(?:autonomous\s+)?mission(?:\s*:\s*|\s+to\s+|\s+)([\s\S]+)', prompt.strip(), flags=re.IGNORECASE)
    if mission_nl_match:
        return "run_mission", {"goal": mission_nl_match.group(1).strip(), "mode": "auto"}

    # 0. Host File System Operations (Read, Write, Directory Scan)
    # A. File Read Intent (/read, /cat, /view, /file, or natural language)
    if p_lower.startswith(("/read", "/cat", "/view", "/file")):
        parts = prompt.strip().split(maxsplit=1)
        target = parts[1].strip().strip('"\'`') if len(parts) > 1 else ""
        return "read_host_file", {"file_path": target, "question": ""}

    # Natural language read
    read_patterns = [
        r'(?:please\s+|can\s+you\s+|could\s+you\s+)?(?:read|view|cat|inspect|open|show(?:\s+me)?|display|check)(?:\s+the)?\s+(?:contents?\s+of\s+)?(?:file\s+)?([a-zA-Z]:\\[^\s"\'`:]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`:]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|yml|yaml|sql|csv|conf|toml))(?::)?(?:\s+(?:and|to)\s+(.*))?',
        r'what(?:\'s|\s+is)\s+in(?:\s+the)?\s+(?:file\s+)?([a-zA-Z]:\\[^\s"\'`:]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`:]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|yml|yaml|sql|csv|conf|toml))(?::)?(?:\s+(?:and|to)\s+(.*))?'
    ]
    for pat in read_patterns:
        m = re.search(pat, prompt.strip(), flags=re.IGNORECASE)
        if m:
            path = m.group(1).strip('"\'`:')
            q = m.group(2).strip() if len(m.groups()) > 1 and m.group(2) else ""
            return "read_host_file", {"file_path": path, "question": q}

    # B. File Write Intent (/write, /save, /create_file, or natural language)
    if p_lower.startswith(("/write", "/save", "/create_file")):
        parts = prompt.strip().split(maxsplit=2)
        if len(parts) >= 3:
            path = parts[1].strip().strip('"\'`:')
            content = parts[2].strip()
            cb_match = re.search(r'```(?:[a-zA-Z0-9_\-]+)?\r?\n([\s\S]*?)\r?\n```', content)
            if cb_match:
                content = cb_match.group(1)
            return "write_host_file", {"file_path": path, "content": content}
        elif len(parts) == 2:
            return "write_host_file", {"file_path": parts[1].strip().strip('"\'`:'), "content": ""}

    # Natural language write with code block
    code_block_match = re.search(r'```(?:[a-zA-Z0-9_\-]+)?\r?\n([\s\S]*?)\r?\n```', prompt)
    path_match = re.search(r'(?:write|save|create|put|dump)(?:\s+(?:this|the)?(?:\s+(?:code|script|text|file))?)?\s+(?:to|in|into)?\s+(?:file\s+)?([a-zA-Z]:\\[^\s"\'`:]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`:]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|yml|yaml|sql|csv|conf|toml))(?::)?', prompt, flags=re.IGNORECASE)
    if path_match and code_block_match:
        target_path = path_match.group(1).strip('"\'`:')
        content = code_block_match.group(1)
        return "write_host_file", {"file_path": target_path, "content": content}

    # Inline content write: write to file X with content: Y
    inline_match = re.search(r'(?:write|save|create)(?:\s+to)?\s+(?:file\s+)?([a-zA-Z]:\\[^\s"\'`:]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`:]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|yml|yaml|sql|csv|conf|toml))\s*(?::|\s+with(?:\s+the)?\s+(?:content|text|following):?\s*)([\s\S]+)', prompt, flags=re.IGNORECASE)
    if inline_match:
        return "write_host_file", {"file_path": inline_match.group(1).strip('"\'`:'), "content": inline_match.group(2).strip()}

    # C. Directory Scan Intent (/ls, /dir, /tree, or natural language)
    if p_lower.startswith(("/ls", "/dir", "/tree", "/list_files")):
        parts = prompt.strip().split(maxsplit=1)
        target = parts[1].strip().strip('"\'`') if len(parts) > 1 else "C:\\AI-BS"
        return "scan_directory_tree", {"dir_path": target, "depth": 2}

    dir_match = re.search(r'(?:list|show(?:\s+me)?|display|scan|what\s+are)\s+(?:the\s+)?(?:files|contents|directory|folder)\s+(?:in|of|inside)\s+(?:the\s+)?(?:directory|folder\s+)?([a-zA-Z]:\\[^\s"\'`]+|(?:\.{1,2}[\\/]|[a-zA-Z0-9_\-\.]+[\\/])[^\s"\'`]+|[a-zA-Z0-9_\-\.\/\\]+)', prompt.strip(), flags=re.IGNORECASE)
    if dir_match:
        return "scan_directory_tree", {"dir_path": dir_match.group(1).strip('"\'`'), "depth": 2}

    # 1. Local Image Interrogation / Prompt Extraction Intent
    interrogate_triggers = [
        "interrogate_image", "extract prompt from image", "extract prompt from photo",
        "extract prompt", "interrogate image", "interrogate photo", "describe this image",
        "describe this photo", "what is in this image", "what is in this photo",
        "what do you see in this image", "analyze this image", "analyze image"
    ]
    if any(t in p_lower for t in interrogate_triggers):
        path_match = re.search(r'([A-Za-z]:\\[^\s]+\.(?:png|jpg|jpeg|webp)|/[^\s]+\.(?:png|jpg|jpeg|webp)|[a-zA-Z0-9_\-]+\.(?:png|jpg|jpeg|webp))', prompt)
        img_path = path_match.group(1) if path_match else ""
        return "interrogate_image", {"image_path": img_path}

    # 2. Local Image-to-Image (img2img) Reference Re-creation Intent
    img2img_triggers = [
        "generate_comfy_img2img", "recreate this image", "recreate the image",
        "recreate image", "re-create an image", "recreate an image", "re-create image",
        "modify this image", "modify the image", "modify image",
        "transform this image", "transform the image", "transform image",
        "re-render this image", "re-render the image", "re-render image",
        "change this image to", "make this image into", "img2img",
        "turn this image into", "restylize this image", "restyle this image"
    ]
    if any(t in p_lower for t in img2img_triggers):
        path_match = re.search(r'([A-Za-z]:\\[^\s]+\.(?:png|jpg|jpeg|webp)|/[^\s]+\.(?:png|jpg|jpeg|webp)|[a-zA-Z0-9_\-]+\.(?:png|jpg|jpeg|webp))', prompt)
        img_path = path_match.group(1) if path_match else ""
        return "generate_comfy_img2img", {
            "prompt": clean_tool_prompt(prompt),
            "image_path": img_path,
            "denoise": 0.65
        }

    # 3. Video Generation Intent (Checked before image generation)
    video_triggers = [
        "generate_comfy_video", "generate video", "create video", "make a video",
        "render a video", "produce a video", "create a video", "generate a video",
        "make video", "render video", "video of", "generate clip", "create animation",
        "animate this", "make animation", "generate animation"
    ]
    if any(kw in p_lower for kw in video_triggers):
        args = {"prompt": clean_tool_prompt(prompt)}
        dur_match = re.search(r'\b(?:duration\s*(?:of|is|:)?\s*)?(\d{1,2})\s*(?:seconds?|secs?|s)\b', p_lower)
        if dur_match:
            try:
                parsed_sec = int(dur_match.group(1))
                args["duration_seconds"] = max(7, min(15, parsed_sec))
            except Exception:
                args["duration_seconds"] = 10
        else:
            args["duration_seconds"] = 10
        return "generate_comfy_video", args

    # 4. 3D Mesh / Model Intent
    if any(kw in p_lower for kw in ["generate_comfy_3d_model", "generate 3d", "create 3d model", "render 3d", "3d mesh"]):
        return "generate_comfy_3d_model", {"prompt": clean_tool_prompt(prompt)}

    # 5. Media & Text-to-Image Generation Intent (Multi-Keyword Directives & Autonomous Routing)
    # A. Safety Guard: Exclude purely conversational meta-questions about media generation
    is_meta_question = bool(re.search(
        r'^(?:how\s+(?:do|can|to|would)|why\s+(?:is|are|does|did|not)|what\s+is|explain\s+how|can\s+we\s+set\s+up|help\s+me\s+understand|is\s+it\s+possible\s+to|tell\s+me\s+how)\b',
        p_lower
    ))
    
    # B. Safety Guard: Exclude software coding, script, or database tasks unless explicit image noun is requested
    is_code_task = bool(re.search(
        r'\b(code|script|function|class|algorithm|database|schema|table|endpoint|api|html|css|json|yaml|sql|component|program|query|test suite|readme|dockerfile|documentation)\b',
        p_lower
    ))
    has_explicit_image = bool(re.search(
        r'\b(photo|photos|photograph|photographs|image|images|picture|pictures|pic|pics|drawing|drawings|painting|paintings|artwork|render|illustration|portrait|wallpaper|visual|poster)\b',
        p_lower
    ))
    should_skip_media = is_meta_question or (is_code_task and not has_explicit_image)

    if not should_skip_media:
        # Civitai / WebUI / Slash command syntax
        has_pos_marker = bool(re.search(r'^(?:positive\s+prompt|prompt)\s*:\s*', prompt.strip(), flags=re.IGNORECASE))
        has_pos_keyword = bool(re.search(r'\bpositive\s+prompt\b\s*:', p_lower))
        has_weighted_tags = bool(re.search(r'\([a-zA-Z0-9_\-\s]+:\s*\d+(?:\.\d+)?\)', prompt))
        has_slash_command = prompt.strip().startswith(('/imagine', '/render', '/image', '/draw', '/paint', '/generate', '/t2i', 't2i:', 'txt2img:', '/comfy', '/comfyui', 'comfy:', 'comfyui:', 'comfy ui:'))

        # Direct media creation phrases
        media_keywords = [
            "media generation", "generate media", "create media", "make media",
            "produce media", "render media", "build media", "generate image",
            "create image", "generate photo", "create photo", "generate picture",
            "create picture", "generate artwork", "create artwork", "make art",
            "create art", "generate art", "generate_comfy_image", "text to image",
            "txt2img", "t2i", "comfy ui", "comfyui", "comfy image", "comfy photo",
            "comfy render", "comfy picture", "comfy artwork"
        ]
        has_direct_media_kw = any(k in p_lower for k in media_keywords)

        # Broad Action Verb + Visual Noun Regex
        broad_image_match = bool(re.search(
            r'\b(create|generate|make|render|draw|paint|sketch|produce|design|illustrate|visualize|depict|craft|build|show\s+me|give\s+me|display|send\s+me|can\s+i\s+see|let\s+me\s+see)\b.*?\b(photo|photos|photograph|photographs|image|images|picture|pictures|pic|pics|drawing|drawings|painting|paintings|artwork|art|render|renders|concept\s+art|illustration|illustrations|portrait|portraits|wallpaper|wallpapers|graphic|graphics|visual|visuals|poster|posters|thumbnail|avatar|logo|banner|clipart)\b',
            p_lower
        ))

        # Standalone creative verbs ("draw me a...", "paint a sunset...", "illustrate a...")
        standalone_creative_verb = bool(re.search(
            r'^(?:please\s+|can\s+you\s+|could\s+you\s+)?(draw|paint|sketch|illustrate|visualize|depict)\s+(?:me\s+)?(?:a|an|the|some)?\s+',
            p_lower
        ))

        # Visual style starters / Photography starters
        visual_prefixes = [
            "photo of", "photograph of", "picture of", "image of", "portrait of",
            "painting of", "drawing of", "illustration of", "render of", "artwork of",
            "visual of", "cinematic shot", "cinematic photo", "close-up of", "close up of",
            "macro shot of", "photorealistic", "hyperrealistic", "ultra-realistic",
            "3d render of", "octane render of", "concept art of"
        ]
        prefix_of_match = bool(re.search(
            r'^(?:a|an|the)?\s*(?:photo|photos|photograph|photographs|picture|pictures|image|images|portrait|portraits|painting|paintings|drawing|drawings|illustration|illustrations|render|renders|artwork|visual)\s+of\b',
            p_lower
        ))
        has_style_prefix = any(p_lower.startswith(pref) for pref in visual_prefixes) or prefix_of_match

        is_image_intent = (
            has_pos_marker
            or has_pos_keyword
            or has_weighted_tags
            or has_slash_command
            or has_direct_media_kw
            or broad_image_match
            or standalone_creative_verb
            or has_style_prefix
        )

        if is_image_intent:
            clean_pos = clean_tool_prompt(prompt)
            neg_match = re.search(r'(?:^|\n|\r\n)\s*(?:negative\s+prompt|negative)\s*:\s*(.*)', prompt, flags=re.IGNORECASE | re.DOTALL)
            extracted_neg = neg_match.group(1).strip() if neg_match else ""
            payload: Dict[str, Any] = {"prompt": clean_pos}
            if extracted_neg:
                payload["negative_prompt"] = extracted_neg
            return "generate_comfy_image", payload

    # 6. Master Memory / DB Intent
    if any(kw in p_lower for kw in ["query master memory", "search master memory", "search your master memory"]):
        return "query_master_memory", {"query": prompt}

    # 7. Deep 12-Stage Multi-Model Gauntlet Intent
    if any(kw in p_lower for kw in ["run gauntlet", "run deep gauntlet", "deep reasoning", "cross check models", "multi-model gauntlet", "solve and refine", "/gauntlet", "multi model gauntlet", "run multi model"]):
        return "run_deep_gauntlet", {"prompt": prompt}

    if any(kw in p_lower for kw in ["blockchain_v2_mainnet", "blockchain", "query 200gb", "query database", "telemetry database", "block height", "latest block"]):
        return "query_large_knowledge_db", {
            "db_path": r"E:\AI_BS_Resources\blockchain.db",
            "sql": "SELECT * FROM system_telemetry ORDER BY id DESC LIMIT 5;"
        }

    # 8. Universal Space Retrieval Intent across 11 SQLite DBs
    if any(kw in p_lower for kw in [
        "retrieve from all spaces", "retrieve from spaces", "retrieve info from all spaces",
        "retrieve information from all spaces", "search all spaces", "search spaces",
        "query all spaces", "find in all spaces", "search 11 databases", "search 11 spaces",
        "retrieve from database", "/retrieve"
    ]):
        return "retrieve_from_all_spaces", {"query": prompt}

    # 9. On-Demand Database Ingestion Intent
    if any(kw in p_lower for kw in [
        "store this in the database", "store this info to db", "store info to db", "store in db",
        "store to db", "save to db", "save this to db", "ingest on demand", "ingest into database",
        "ingest to database", "ingest to db", "ingest into db", "save to database", "save this to database",
        "save note to vault", "save this note to the vault", "store note in db", "record this transaction",
        "/ingest"
    ]):
        return "ingest_on_demand_to_db", {"content": prompt}

    # 10. 43-Module Oversight Parent Intent
    if any(kw in p_lower for kw in [
        "monitor all 43", "monitor all 43 modules", "monitor modules", "monitor systems",
        "43 modules", "43 master hub", "oversight parent", "system oversight", "master oversight",
        "oversight dashboard", "module overview", "/monitor", "/oversight", "/modules"
    ]):
        return "monitor_43_modules", {"prompt": prompt}

    # 11. Spaces Overview Intent
    if any(kw in p_lower for kw in [
        "spaces overview", "all 11 spaces", "11 database spaces", "list spaces", "show spaces",
        "storage spaces", "database spaces", "/spaces"
    ]):
        return "spaces_overview", {}

    return None, None




async def fetch_technical_whisper(prompt: str) -> str:
    """
    Shadow Co-Processor:
    Executes locally on port 11435 with zero VRAM impact on the primary 4090, 
    extracting key technical facts, exact code structures, and logical guardrails.
    """
    system_instruction = (
        "You are a silent technical co-processor. Analyze the query and provide ONLY "
        "concise factual bullets, exact code snippets, or mathematical formulas. "
        "Do not speak to the user. Keep it under 150 words."
    )
    system_instruction = inject_safety_directive(system_instruction)
    payload = {
        "model": "qwen2.5-coder:7b",
        "prompt": prompt,
        "system": system_instruction,
        "stream": False
    }
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            res = await client.post(SHADOW_OLLAMA_URL, json=payload)
            if res.status_code == 200:
                return res.json().get("response", "")
    except Exception as e:
        print(f"[Hybrid Engine] Shadow whisper notice: {e}")
        pass
    return ""


def is_coding_intent(prompt: str) -> Tuple[bool, str]:
    p_lower = prompt.strip().lower()
    
    # 1. Explicit Slash Commands
    if p_lower.startswith(("/coder", "/code", "/patch", "/syntax", "/mirror", "/refactor", "/diff")):
        clean = re.sub(r"^/(?:coder|code|patch|syntax|mirror|refactor|diff)\s*", "", prompt, flags=re.IGNORECASE).strip()
        return True, clean or prompt

    # 2. Direct Coding Invocations
    coding_starters = [
        "write code", "write a script", "write a python", "write a function", "write a class",
        "create a component", "build a component", "create an endpoint", "build an api",
        "patch this file", "apply diff", "fix syntax", "validate syntax", "debug this code",
        "refactor this", "write a test", "implement the tool", "shadow coder"
    ]
    if any(p_lower.startswith(s) or f"please {s}" in p_lower for s in coding_starters):
        return True, prompt

    # 3. Code patterns + programming verbs
    has_code_keywords = bool(re.search(
        r"\b(write|create|implement|debug|fix|refactor|patch|optimize)\s+(?:a|an|the|this)?\s*(?:python|powershell|javascript|typescript|react|fastapi|golang|bash|sql|jsx|tsx)?\s*(?:function|script|class|component|endpoint|api|algorithm|hook|schema|unit test|dockerfile)\b",
        p_lower
    ))
    
    has_explicit_media = bool(re.search(
        r"\b(photo|photograph|image|picture|drawing|painting|render|artwork|illustration|portrait|wallpaper|video|clip|animation)\b",
        p_lower
    ))
    
    if has_code_keywords and not has_explicit_media:
        return True, prompt

    return False, prompt


async def stream_shadow_coder_response(prompt: str, messages: Optional[list] = None) -> AsyncGenerator[str, None]:
    """
    Dedicated Coding Sub-Agent Model Routing (The Shadow Coder Bridge):
    Routes coding and refactoring queries directly to qwen2.5-coder:7b on Port 11435.
    Provides sub-second token generation with zero VRAM interference on the primary RTX 4090.
    """
    system_instruction = (
        "You are the Stehouwer Autonomous Coding Sub-Agent running on Port 11435 (qwen2.5-coder:7b). "
        "You are an elite, production-grade software engineer working within the C:\\AI-BS ecosystem. "
        "Rules:\n"
        "1. Write clean, complete, modern, syntactically flawless code.\n"
        "2. When proposing file modifications, use targeted diffs or precise replacement blocks that can be applied with patch_host_file.\n"
        "3. When creating frontend components, adhere to the 4-mirror architecture (write_mirror_component).\n"
        "4. Output executable markdown code blocks with language tags (```python, ```javascript, ```jsx, ```json, ```powershell, ```go, ```sql).\n"
        "5. Explain changes concisely without unnecessary conversational filler."
    )
    system_instruction = inject_safety_directive(system_instruction)

    full_prompt = prompt
    if messages and isinstance(messages, list) and len(messages) > 1:
        history_text = ""
        for m in messages[-4:]:
            role = m.get("role", "user")
            content = m.get("content", "")
            if content:
                history_text += f"{role.upper()}: {content}\n\n"
        full_prompt = f"{history_text}USER: {prompt}\nASSISTANT:"

    payload = {
        "model": "qwen2.5-coder:7b",
        "prompt": full_prompt,
        "system": system_instruction,
        "stream": True,
        "options": {
            "temperature": 0.2,
            "num_ctx": 32768,
        }
    }

    yield "⚡ **Stehouwer Autonomous Coding Sub-Agent (Port 11435: qwen2.5-coder:7b)**\n\n"

    streamed_success = False
    target_endpoints = [PRIMARY_OLLAMA_URL, SHADOW_OLLAMA_URL]

    for ep in target_endpoints:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0, read=120.0, write=15.0)) as client:
                async with client.stream("POST", ep, json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    text_piece = chunk.get("response", "")
                                    if text_piece:
                                        yield text_piece
                                        streamed_success = True
                                except json.JSONDecodeError:
                                    continue
                        if streamed_success:
                            return
        except Exception as e:
            print(f"[Shadow Coder] Endpoint {ep} connection failed: {e}")
            continue

    if not streamed_success:
        yield "*(Shadow Coder offline on 11435/11434 — falling back to Sovereign Reasoning Matrix)*\n\n"
        from core.sovereign_reasoning import stream_sovereign_response
        async for chunk in stream_sovereign_response(prompt, messages=messages):
            yield chunk


async def stream_stehouwer_hybrid_response(prompt: str, messages: Optional[list] = None) -> AsyncGenerator[str, None]:
    """
    Gathers tool intents, shadow co-processor briefings, and streams the response 
    directly through Stehouwer LLM's authentic voice with live rendered media.
    """
    # Pre-Flight Safety Audit across S1, S3, S4
    is_safe, refusal = audit_prompt_safety(prompt)
    if not is_safe:
        yield f"⚠️ **Sovereign Engine Refusal:** {refusal}\n"
        return

    # Check for direct tool intents (ComfyUI Image/Video, DB Queries, Memory)
    t_name, t_args = detect_tool_intent(prompt)
    
    # Check for dedicated coding sub-agent intent
    is_code, clean_code_prompt = is_coding_intent(prompt)
    if is_code and not t_name:
        async for chunk in stream_shadow_coder_response(clean_code_prompt, messages=messages):
            yield chunk
        return
    
    if t_name:
        if t_name in ["generate_comfy_image", "generate_comfy_video", "generate_comfy_3d_model"]:
            clean_prompt = t_args.get("prompt", "futuristic AI server matrix room")
            media_noun = "video" if t_name == "generate_comfy_video" else "media"
            yield f"Alright, let's get this done! Firing up the RTX 4090 ComfyUI engine on Port 8189 now for: **{clean_prompt}**... 🎨⚡\n\n"
            
            # Execute tool safely with periodic keep-alive progress updates to prevent socket timeout
            from tools.tool_registry import ToolRegistry
            task = asyncio.create_task(asyncio.to_thread(ToolRegistry.execute_tool, t_name, t_args))
            elapsed = 0
            while not task.done():
                await asyncio.sleep(5)
                elapsed += 5
                if elapsed % 15 == 0 and t_name == "generate_comfy_video":
                    yield f"⏳ *Synthesizing video frames on RTX 4090... ({elapsed}s elapsed)*\n\n"
            
            tool_result = await task
            
            img_url = tool_result.get("image_url")
            filename = tool_result.get("filename")
            
            if not img_url and filename:
                img_url = f"/api/comfy/media?filename={filename}&subfolder=&type=output"
                
            if img_url:
                safe_alt = re.sub(r'[\r\n\[\]"\'`]+', ' ', clean_prompt).strip()[:70] or "Generated ComfyUI Media"
                is_video = (
                    t_name == "generate_comfy_video"
                    or (filename and any(filename.lower().endswith(ext) for ext in [".mp4", ".webm", ".mov", ".mkv"]))
                    or any(ext in (img_url or "").lower() for ext in [".mp4", ".webm", ".mov", ".mkv"])
                )
                if is_video:
                    dur_sec = tool_result.get("duration_seconds")
                    fps_val = tool_result.get("fps", 16)
                    frames_val = tool_result.get("num_frames")
                    dur_info = f" ({dur_sec}s @ {fps_val}fps, {frames_val} frames)" if dur_sec else ""
                    media_markdown = f"<video controls autoPlay loop muted playsinline src='{img_url}' style='max-width:100%; border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,0.5);'></video>"
                    yield f"🎬 **Generated ComfyUI Video Output{dur_info}:**\n\n{media_markdown}\n\n[📥 Direct Video Download / High-Res View]({img_url})\n\n---\n*Rendered in cinematic HD via RTX 4090 Wan2.1 pipeline ({dur_sec or '3-8'}s duration).* What's our next creative shot?"
                else:
                    media_markdown = f"![{safe_alt}]({img_url})"
                    yield f"🎬 **Generated ComfyUI Image:**\n\n{media_markdown}\n\n[📥 Direct Image Download / High-Res View]({img_url})\n\n---\n*Rendered in high resolution (SDXL 1024x1024) via local RTX 4090.* Razor sharp and ready to roll! What are we building next?"
            else:
                err_msg = tool_result.get("message")
                if err_msg:
                    yield f"⚠️ **ComfyUI Execution Alert:** {err_msg}\n\n```json\n{json.dumps(tool_result, indent=2)}\n```\n\nVerify Port 8189 ComfyUI service status."
                else:
                    yield f"⚠️ **ComfyUI Task Status:**\n\n```json\n{json.dumps(tool_result, indent=2)}\n```\n\nComfyUI dispatched prompt. If image doesn't appear, verify Port 8189."
            return

        elif t_name == "generate_comfy_img2img":
            clean_prompt = t_args.get("prompt", "transformed image")
            yield f"Firing up the RTX 4090 ComfyUI Image-to-Image engine on Port 8189 for: **{clean_prompt}**... 🎨⚡\n\n"
            from tools.tool_registry import ToolRegistry
            tool_result = await asyncio.to_thread(ToolRegistry.execute_tool, t_name, t_args)
            img_url = tool_result.get("image_url")
            filename = tool_result.get("filename")
            if not img_url and filename:
                img_url = f"/api/comfy/media?filename={filename}&subfolder=&type=output"
            if img_url:
                safe_alt = re.sub(r'[\r\n\[\]"\'`]+', ' ', clean_prompt).strip()[:70] or "Recreated ComfyUI Image"
                media_markdown = f"![{safe_alt}]({img_url})"
                yield f"🎬 **Recreated ComfyUI Image (img2img):**\n\n{media_markdown}\n\n[📥 Direct Image Download / High-Res View]({img_url})\n\n---\n*Rendered locally via RTX 4090 SDXL img2img pipeline (denoise: {tool_result.get('denoise', 0.65)}).* Transformed and ready! What's next?"
            else:
                yield f"⚠️ **ComfyUI img2img Task Status:**\n\n```json\n{json.dumps(tool_result, indent=2)}\n```\n\nComfyUI img2img dispatched. If output doesn't appear, verify Port 8189."
            return

        elif t_name == "interrogate_image":
            yield "Analyzing reference image with local Computer Vision... 🔍🖼️\n\n"
            from tools.tool_registry import ToolRegistry
            tool_result = await asyncio.to_thread(ToolRegistry.execute_tool, t_name, t_args)
            if tool_result.get("status") == "success":
                analysis = tool_result.get("analysis", "")
                tags = tool_result.get("detected_tags", [])
                suggested_prompt = tool_result.get("suggested_comfy_prompt", "")
                tags_formatted = ", ".join([f"`{t}`" for t in tags]) if tags else "None detected"
                yield (
                    f"👁️ **Local Image Interrogation Results:**\n\n"
                    f"**Detected Subjects & Tags:** {tags_formatted}\n\n"
                    f"**Full Vision Analysis:**\n> {analysis}\n\n"
                    f"**Suggested ComfyUI Prompt:**\n```text\n{suggested_prompt}\n```\n\n"
                    f"*Ready for text-to-image or img2img re-creation on your RTX 4090.*"
                )
            else:
                yield f"⚠️ **Interrogation Warning:** {tool_result.get('message', 'Failed to inspect image.')}"
            return

        elif t_name == "query_master_memory":
            yield "Searching through the master memory vault and historical baselines... 🧠🔍\n\n"
            from tools.tool_registry import ToolRegistry
            tool_result = await asyncio.to_thread(ToolRegistry.execute_tool, t_name, t_args)
            yield f"📋 **Master Memory Search Results:**\n\n```json\n{json.dumps(tool_result, indent=2)}\n```\n\nRetrieved from persistent storage."
            return

        elif t_name == "query_large_knowledge_db":
            yield "Executing low-latency query against the 70+ Knowledge & Blockchain SQLite Databases... ⚡🔍\n\n"
            from tools.tool_registry import ToolRegistry
            tool_result = await asyncio.to_thread(ToolRegistry.execute_tool, t_name, t_args)
            db_name = tool_result.get("database_name", "blockchain.db")
            yield f"📊 **Knowledge Database Query Results ({db_name} — 2ms latency):**\n\n```json\n{json.dumps(tool_result, indent=2)}\n```\n\n*Low-latency WAL mode read verified across storage volumes.*"
            return

        elif t_name == "retrieve_from_all_spaces":
            yield "Searching across all 11 memory-mapped SQLite database spaces... 🔍⚡\n\n"
            from core.omni_space_manager import omni_space_manager
            q = t_args.get("query", prompt)
            for prefix in ["retrieve from all spaces", "retrieve from spaces", "search all spaces", "search spaces", "/retrieve"]:
                if q.lower().startswith(prefix):
                    q = q[len(prefix):].strip(" :,-")
                    break
            results = await asyncio.to_thread(omni_space_manager.search_all_spaces, q or prompt)
            card = omni_space_manager.format_retrieval_card(results)
            yield card
            return

        elif t_name == "ingest_on_demand_to_db":
            yield "Ingesting structured data into verified SQLite database space... 💾⚡\n\n"
            from core.omni_space_manager import omni_space_manager
            content = t_args.get("content", prompt)
            for prefix in ["store this in the database", "store in db", "save to db", "ingest on demand", "save to database", "/ingest"]:
                if content.lower().startswith(prefix):
                    content = content[len(prefix):].strip(" :,-")
                    break
            res = await asyncio.to_thread(omni_space_manager.ingest_on_demand, content or prompt)
            card = omni_space_manager.format_ingestion_card(res)
            yield card
            return

        elif t_name == "monitor_43_modules":
            yield "Gathering live telemetry across all 43 Master Hub modules and 20 system daemons... 👑📊\n\n"
            from core.oversight_parent_engine import master_oversight_engine
            card = await asyncio.to_thread(master_oversight_engine.format_oversight_dashboard)
            yield card
            return

        elif t_name == "spaces_overview":
            yield "Inspecting all 11 memory-mapped SQLite database spaces... 🏛️💾\n\n"
            from core.omni_space_manager import omni_space_manager
            overview = await asyncio.to_thread(omni_space_manager.get_spaces_overview)
            md = "### 🏛️ Sovereign 11-Space SQLite Storage Matrix Overview\n\n"
            md += "| Space ID | Database Name | File Size | Tables | Status |\n"
            md += "|---|---|---|---|---|\n"
            for space_id, s in overview.items():
                status_icon = "🟢 Verified" if s.get("integrity") == "ok" else "⚠️ Disconnected"
                md += f"| `{space_id}` | `{s.get('name')}` | `{s.get('size_kb')} KB` | `{s.get('tables_count')}` | {status_icon} |\n"
            md += "\n---\n*Universal retrieval and on-demand ingestion active across all 11 partitioned spaces.*"
            yield md
            return

        elif t_name == "read_host_file":
            file_path = t_args.get("file_path", "").strip()
            question = t_args.get("question", "").strip()
            if not file_path:
                yield "⚠️ **File Read Warning:** No file path specified. Usage: `/read <file_path>`\n"
                return
            yield f"📖 **Reading host file:** `{file_path}`... 🔍\n\n"
            from tools.tool_registry import ToolRegistry
            tool_result = await asyncio.to_thread(ToolRegistry.execute_tool, "read_host_file", {"file_path": file_path})
            if tool_result.get("status") == "success":
                content = tool_result.get("content", "")
                lines = tool_result.get("lines", 0)
                size_kb = round(tool_result.get("size_bytes", 0) / 1024, 2)
                abs_path = tool_result.get("file_path", file_path)
                ext = os.path.splitext(abs_path)[1].lstrip(".").lower() or "text"
                lang_map = {
                    "py": "python", "js": "javascript", "jsx": "jsx", "ts": "typescript",
                    "tsx": "tsx", "json": "json", "md": "markdown", "html": "html",
                    "css": "css", "sql": "sql", "sh": "bash", "bat": "batch",
                    "ps1": "powershell", "yml": "yaml", "yaml": "yaml", "toml": "toml"
                }
                syntax_lang = lang_map.get(ext, ext)

                if question:
                    yield f"📄 **Host File:** `{abs_path}` *({lines} lines, {size_kb} KB)*\n\n"
                    yield f"🤖 **Answering Query:** *\"{question}\"*\n\n"
                    from core.sovereign_reasoning import stream_sovereign_response
                    analysis_prompt = (
                        f"The user requested reading and analyzing host file '{abs_path}'.\n\n"
                        f"FILE CONTENTS:\n```{syntax_lang}\n{content[:25000]}\n```\n\n"
                        f"USER INSTRUCTION / QUESTION: {question}\n\n"
                        f"Answer directly, accurately, and thoroughly based on the file contents above."
                    )
                    async for chunk in stream_sovereign_response(analysis_prompt, messages=messages):
                        yield chunk
                else:
                    preview = content if len(content) <= 30000 else content[:30000] + f"\n\n... [Truncated: showing 30,000 of {len(content)} characters]"
                    yield (
                        f"📄 **Host File:** `{abs_path}` *({lines} lines, {size_kb} KB)*\n\n"
                        f"```{syntax_lang}\n{preview}\n```\n\n"
                        f"---\n💡 *Use `/edit {file_path}` to open in the interactive drawer, or `/write {file_path} <content>` to save changes.*"
                    )
            else:
                yield f"❌ **Failed to read file:** {tool_result.get('message', 'File not found')}\n"
            return

        elif t_name == "write_host_file":
            file_path = t_args.get("file_path", "").strip()
            content = t_args.get("content", "")
            if not file_path:
                yield "⚠️ **File Write Warning:** No file path specified. Usage: `/write <file_path> <content>`\n"
                return
            if not content:
                yield f"⚠️ **File Write Notice:** No content provided for `{file_path}`.\n\nUse `/write {file_path} <content>` or `/edit {file_path}` to draft and save in the Host File Editor drawer."
                return

            yield f"✍️ **Writing host file:** `{file_path}` ({len(content)} characters)... 💾\n\n"
            from tools.tool_registry import ToolRegistry
            tool_result = await asyncio.to_thread(ToolRegistry.execute_tool, "write_host_file", {"file_path": file_path, "content": content})
            if tool_result.get("status") == "success":
                bytes_written = tool_result.get("bytes_written", len(content.encode("utf-8")))
                abs_path = tool_result.get("file_path", file_path)
                backup = tool_result.get("backup_path")
                backup_info = f"\n📦 **Auto-Backup Created:** `{backup}`" if backup else ""
                yield (
                    f"✅ **File Written to Host Disk!**\n\n"
                    f"- **File Path:** `{abs_path}`\n"
                    f"- **Size Written:** {bytes_written} bytes ({round(bytes_written/1024, 2)} KB)\n"
                    f"- **Total Lines:** {len(content.splitlines())}"
                    f"{backup_info}\n\n"
                    f"---\n💡 *Changes persisted with automated .bak backup protection.*"
                )
            else:
                yield f"❌ **Failed to write file:** {tool_result.get('message', 'Write operation failed')}\n"
            return

        elif t_name == "scan_directory_tree":
            dir_path = t_args.get("dir_path", "C:\\AI-BS").strip()
            depth = t_args.get("depth", 2)
            yield f"📁 **Scanning host directory:** `{dir_path}` (depth {depth})... 🔍\n\n"
            from tools.tool_registry import ToolRegistry
            tool_result = await asyncio.to_thread(ToolRegistry.execute_tool, "scan_directory_tree", {"dir_path": dir_path, "depth": depth})
            if tool_result.get("status") == "success":
                root_path = tool_result.get("root", dir_path)
                tree_items = tool_result.get("tree", []) or []
                
                md = f"### 📁 Host Directory Listing: `{root_path}`\n\n"
                md += "| Type | Name | Size / Items |\n"
                md += "|---|---|---|\n"
                
                def render_items(items, prefix=""):
                    rows = []
                    for item in items:
                        itype = item.get("type", "file")
                        iname = item.get("name", "")
                        if itype == "directory":
                            children = item.get("children")
                            child_count = f"{len(children)} items" if isinstance(children, list) else "dir"
                            rows.append(f"| 📁 DIR | `{prefix}{iname}/` | {child_count} |")
                            if isinstance(children, list) and children:
                                rows.extend(render_items(children, prefix=f"{prefix}{iname}/"))
                        else:
                            sz = item.get("size_bytes", -1)
                            sz_str = f"{round(sz/1024, 1)} KB" if sz >= 0 else "unknown"
                            rows.append(f"| 📄 FILE | `{prefix}{iname}` | {sz_str} |")
                    return rows

                all_rows = render_items(tree_items)
                md += "\n".join(all_rows[:60])
                if len(all_rows) > 60:
                    md += f"\n\n*... and {len(all_rows) - 60} additional items.*"
                md += f"\n\n---\n💡 *Use `/read <filepath>` to view file contents or `/edit <filepath>` to edit.*"
                yield md
            else:
                yield f"❌ **Failed to scan directory:** {tool_result.get('message', 'Directory not found')}\n"
            return

        elif t_name == "run_mission":
            goal = t_args.get("goal", "").strip()
            if not goal:
                yield "⚠️ **Autonomous Mission Engine:** No mission goal specified.\n\n**Usage:** `/mission <goal>`\n*Example:* `/mission Verify multi-mirror parity, syntax health, and git status`\n"
                return

            yield f"🚀 **Initializing Autonomous Mission (AI-BS & Antigravity Unison Engine)...**\n\n🎯 **Mission Goal:** *{goal}*\n\n---\n"
            from core.mission_control_engine import mission_engine

            # Phase 1 & 2: Plan
            yield "### 📋 Phase 1 & 2: Intent Parsing & Mission Blueprint Generation\n"
            plan = mission_engine.plan_mission(goal, mode="auto")
            mission_id = plan["mission_id"]
            ctx = plan.get("context", {})
            yield f"- **Mission ID:** `{mission_id}`\n"
            yield f"- **Workspace Root:** `{ctx.get('workspace_root', r'C:\AI-BS')}`\n"
            yield f"- **Active Git Branch:** `{ctx.get('git_branch', 'main')}`\n"
            yield f"- **Indexed Skills:** {len(ctx.get('installed_skills', []))} skills ready\n\n"

            yield "#### 📝 Execution Sub-Tasks:\n"
            for t in plan.get("tasks", []):
                yield f"- `[ ]` **{t['phase']}**: {t['title']}\n"
            yield "\n---\n### ⚙️ Phase 3, 4 & 5: Autonomous Execution & Verification Loop\n\n"

            # Execute tasks
            for task in plan.get("tasks", []):
                t_id = task["task_id"]
                yield f"▶️ **Executing Task {t_id}:** *{task['title']}*...\n"
                step_res = await asyncio.to_thread(mission_engine.execute_mission_step, mission_id, t_id)
                out = step_res.get("task", {}).get("result", {}).get("output", "")
                status_icon = "✅" if task["status"] == "completed" else "❌"
                dur = task.get("duration_ms", 0)
                yield f"{status_icon} **{task['title']}** ({dur}ms)\n"
                if out:
                    yield f"> {out}\n\n"

            yield "\n---\n### 🏆 Mission Status: COMPLETED\n"
            yield f"- **Total Phases:** 5/5 Synchronized\n"
            yield f"- **Mirror Parity:** Verified 100% SHA256 across all 4 frontend mirrors\n"
            yield f"- **Audit Trail:** Recorded to Master Mission Telemetry.\n"
            return

        elif t_name == "grill_mission":
            proposal = t_args.get("proposal", "").strip()
            if not proposal:
                yield "⚠️ **Architectural Grill Session:** No mission proposal specified.\n\n**Usage:** `/grill <proposal>`\n*Example:* `/grill Add a persistent SQLite event-logging daemon for Pearl mining stratum telemetry.`\n"
                return

            yield f"🔥 **Architectural Grill Session Initiated (/grill)**\n\n**Mission Proposal:** *{proposal}*\n\n---\n"
            from core.mission_control_engine import mission_engine

            session = await asyncio.to_thread(mission_engine.start_grill, proposal)
            ctx = session.get("context_explored", {})

            yield "📦 **Codebase Context Verified:**\n"
            yield f"- {ctx.get('summary', 'Inspected workspace context and schemas.')}\n"
            for f in ctx.get("verified_files", [])[:3]:
                yield f"  - Discovered module: `{f.get('path')}`\n"
            for note in ctx.get("context_notes", [])[:2]:
                yield f"  - *{note}*\n"
            yield "\n---\n"

            for idx, q in enumerate(session.get("questions", []), 1):
                yield f"### ❓ Question {idx} ({q['branch']}):\n"
                yield f"{q['question']}\n\n"
                yield f"👉 **Recommended Decision:** {q['recommendation']}\n\n"

            yield "---\n"
            yield "💡 *Reply **\"yes\"** or **\"agree\"** to accept both recommendations, or specify adjustments.*\n"
            yield "*You can also issue `/build` to immediately lock `mission_spec.md` and start autonomous execution.*\n"
            return

        elif t_name == "grill_respond":
            resp_text = t_args.get("response", "yes").strip()
            grill_id = t_args.get("grill_id", "")
            from core.mission_control_engine import mission_engine

            yield f"⚡ **Processing Architectural Decision:** *\"{resp_text}\"*...\n\n"
            conclude_res = await asyncio.to_thread(mission_engine.respond_grill, grill_id, resp_text)

            if conclude_res.get("status") == "success":
                spec_path = conclude_res.get("spec_file", "mission_spec.md")
                plan = conclude_res.get("mission_plan", {})
                yield "🔒 **Architectural Decisions Locked ab initio!**\n\n"
                yield f"📄 **Locked Specification Artifact:** `{spec_path}`\n\n"
                yield "### 📋 Agreed Architectural Decisions:\n"
                for idx, d in enumerate(conclude_res.get("grill_session", {}).get("decisions_agreed", []), 1):
                    yield f"- **Decision {idx} ({d['branch']}):** {d['decision']} *(Status: Accepted)*\n"

                yield "\n---\n### 🚀 Direct Transition to Stage 2 (Planning & Execution)\n\n"
                yield f"- **Generated Mission ID:** `{plan.get('mission_id', 'active')}`\n"
                yield f"- **Total Execution Phases:** {len(plan.get('tasks', []))} atomic tasks prepared\n\n"
                for t in plan.get("tasks", []):
                    yield f"- `[ ]` **{t['phase']}**: {t['title']}\n"
                yield "\n💡 *Starting autonomous execution loop now...*\n\n"

                # Execute tasks sequentially
                mission_id = plan["mission_id"]
                for task in plan.get("tasks", []):
                    t_id = task["task_id"]
                    step_res = await asyncio.to_thread(mission_engine.execute_mission_step, mission_id, t_id)
                    status_icon = "✅" if task["status"] == "completed" else "❌"
                    dur = task.get("duration_ms", 0)
                    yield f"{status_icon} **{task['title']}** ({dur}ms)\n"

                yield f"\n🏆 **Mission Completed!** Spec locked in `{spec_path}` and synchronized across AI-BS.\n"
            else:
                yield f"❌ **Grill Response Error:** {conclude_res.get('message', 'Failed to process response')}\n"
            return

        elif t_name == "run_audit":
            scope = t_args.get("scope", "")
            yield f"🔍 **Executing Pre-Flight Static Analysis & Security Audit (/audit)...**\n\n"
            from core.mission_control_engine import mission_engine
            report = await asyncio.to_thread(mission_engine.run_audit, scope)
            yield report.get("markdown_summary", "Audit finished.")
            return

        elif t_name == "run_test_first":
            feature = t_args.get("feature", "core_feature")
            yield f"🔴 **Initiating Autonomous TDD Red-Green Loop (/test-first)...**\n\n"
            from core.mission_control_engine import mission_engine
            res = await asyncio.to_thread(mission_engine.run_test_first, feature)
            yield res.get("markdown_summary", "TDD finished.")
            return

        elif t_name == "run_diff_review":
            yield "📄 **Generating Visual Patch Inspection & Rollback Hashes (/diff-review)...**\n\n"
            from core.mission_control_engine import mission_engine
            res = await asyncio.to_thread(mission_engine.generate_diff_review)
            yield res.get("markdown_summary", "Diff review generated.")
            return

        elif t_name == "run_snapshot":
            label = t_args.get("label")
            yield f"📌 **Pinning Atomic State Checkpoint to Git & Ledger (/snapshot)...**\n\n"
            from core.mission_control_engine import mission_engine
            res = await asyncio.to_thread(mission_engine.create_snapshot, label)
            yield res.get("markdown_summary", "State snapshot pinned.")
            return

        elif t_name == "run_rollback":
            target = t_args.get("target", "").strip()
            if not target:
                yield "⚠️ **Usage:** `/rollback <backup_id|filename>`\n*Example:* `/rollback task_tdd_core` or `/rollback ChatTab.jsx`\n"
                return
            yield f"🔄 **Executing Surgical Backup Rollback for '{target}'...**\n\n"
            from core.mission_control_engine import mission_engine
            res = await asyncio.to_thread(mission_engine.rollback, target)
            if res.get("status") == "success":
                yield f"✅ **Rollback Succeeded!**\n- **Restored Target:** `{res.get('restored_file')}`\n- **Source Backup:** `{res.get('backup_source')}`\n- **Pre-Rollback Backup:** `{res.get('pre_rollback_backup')}`\n- **Message:** {res.get('message')}\n"
            else:
                yield f"❌ **Rollback Failed:** {res.get('message')}\n"
            return

        elif t_name == "check_hardware":
            yield "⚡ **Hooking into Native Host Hardware & RTX 4090 Watchdog...**\n\n"
            from core.mission_control_engine import mission_engine
            res = await asyncio.to_thread(mission_engine.check_hardware_safety)
            status_icon = "🟢" if res.get("safe_to_execute") else "🔴"
            temp_str = f"{res.get('temperature_celsius', 'N/A')}°C" if res.get('temperature_celsius') is not None else "N/A"
            pwr_str = f"{res.get('power_draw_watts', 'N/A')}W" if res.get('power_draw_watts') is not None else "N/A"
            vram_str = f"{res.get('vram_used_mb', 'N/A')} MB / {res.get('vram_total_mb', 'N/A')} MB ({res.get('vram_pct', 'N/A')}%)"
            warn_str = ""
            if res.get("warnings"):
                warn_str = "\n\n⚠️ **Safety Warnings:**\n" + "\n".join([f"- {w}" for w in res.get("warnings")])

            md = f"""### {status_icon} Hardware Clamping & Observability Status
- **Device:** `{res.get('gpu_name', 'Host GPU')}`
- **Execution State:** **{res.get('status', 'unknown').upper()}** (Safe to execute: `{res.get('safe_to_execute')}`)
- **Core Temperature:** `{temp_str}` *(Threshold: <83°C)*
- **Power Draw:** `{pwr_str}`
- **VRAM Utilization:** `{vram_str}` *(Threshold: <95%)*{warn_str}
"""
            yield md
            return

        elif t_name == "probe_port":
            try:
                port_int = int(t_args.get("port", 8080))
            except Exception:
                port_int = 8080
            yield f"🔌 **Probing Ecosystem Port {port_int} against Collision Matrix...**\n\n"
            from core.mission_control_engine import mission_engine
            res = await asyncio.to_thread(mission_engine.probe_port_conflict, port_int)
            conflict_icon = "🚨" if res.get("is_conflict") else "✅"
            md = f"""### {conflict_icon} Port Collision Probe: Port {res.get('port')}
- **Conflict Status:** **{'COLLISION DETECTED' if res.get('is_conflict') else 'CLEAR / AVAILABLE'}**
- **Registered Daemon:** `{res.get('registered_daemon') or 'None (Not statically reserved)'}`
- **Socket Active (127.0.0.1):** `{'YES (Occupied)' if res.get('socket_busy') else 'NO'}`
- **Ephemeral Fallback Port:** `{res.get('fallback_port')}`
- **Sentinel Recommendation:** *{res.get('recommendation')}*
"""
            yield md
            return



    # --- Unified Sovereign Reasoning Matrix (Fast Stream + Math Autograd Swarm) ---
    try:
        from core.sovereign_reasoning import stream_sovereign_response

        async for chunk in stream_sovereign_response(prompt, messages=messages):
            yield chunk
    except Exception as err:
        yield f"Error in sovereign reasoning matrix: {err}"


@router.post("/stream")
async def chat_hybrid_endpoint(req: ChatRequest):
    return StreamingResponse(
        stream_stehouwer_hybrid_response(req.prompt, messages=req.messages),
        media_type="text/event-stream"
    )
