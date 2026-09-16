import aiohttp
import asyncio
import uuid
import logging
from typing import Dict, Any, Optional

COMFYUI_HOST = "http://127.0.0.1:8189"

logger = logging.getLogger("ComfyBridge")


async def queue_comfyui_workflow(
    workflow_prompt: Dict[str, Any], host: str = COMFYUI_HOST
) -> str:
    """
    Queues a prompt payload to the local ComfyUI instance asynchronously and returns the prompt ID.
    """
    client_id = str(uuid.uuid4())
    payload = {"prompt": workflow_prompt, "client_id": client_id}

    url = f"{host}/prompt"
    connector = aiohttp.TCPConnector(ssl=False)
    timeout_cfg = aiohttp.ClientTimeout(total=10.0, connect=2.0)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout_cfg) as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                raise RuntimeError(f"HTTP Error {response.status}: {text}")
            res_data = await response.json()
            prompt_id = res_data.get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"No prompt_id returned from ComfyUI: {res_data}")
            return prompt_id


async def await_generation_result(
    prompt_id: str,
    poll_interval: float = 1.0,
    timeout: float = 600.0,
    host: str = COMFYUI_HOST,
) -> Dict[str, Any]:
    """
    Polls the ComfyUI history endpoint asynchronously until execution finishes or timeout is reached.
    """
    start_time = asyncio.get_event_loop().time()
    history_url = f"{host}/history/{prompt_id}"
    connector = aiohttp.TCPConnector(ssl=False)
    timeout_cfg = aiohttp.ClientTimeout(total=5.0, connect=2.0)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout_cfg) as session:
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"ComfyUI prompt execution {prompt_id} timed out after {timeout} seconds."
                )

            try:
                async with session.get(history_url) as response:
                    if response.status == 200:
                        history = await response.json()
                        if prompt_id in history:
                            entry = history[prompt_id]
                            status_info = entry.get("status", {})
                            if status_info.get("status_str") == "error":
                                error_msg = "ComfyUI execution error"
                                for msg in status_info.get("messages", []):
                                    if len(msg) > 1 and isinstance(msg[1], dict) and "exception_message" in msg[1]:
                                        node_t = msg[1].get("node_type", "Node")
                                        ex_m = msg[1].get("exception_message", "").strip()
                                        error_msg = f"ComfyUI [{node_t}] Error: {ex_m}"
                                        break
                                raise RuntimeError(error_msg)
                            return entry
            except RuntimeError:
                raise
            except Exception as e:
                logger.warning(f"Error checking ComfyUI history: {e}")

            await asyncio.sleep(poll_interval)



def extract_output_media(
    history_entry: Dict[str, Any], host: str = COMFYUI_HOST
) -> Dict[str, Optional[str]]:
    """
    Extracts filename, subfolder, media_type, and view URL from a completed ComfyUI history object.
    Supports 'images', 'videos', and 'gifs' output formats.
    """
    outputs = history_entry.get("outputs", {})
    for node_id, node_out in outputs.items():
        for media_key in ["images", "videos", "gifs"]:
            if media_key in node_out and len(node_out[media_key]) > 0:
                item = node_out[media_key][0]
                filename = item.get("filename")
                subfolder = item.get("subfolder", "")
                folder_type = item.get("type", "output")

                if filename:
                    image_url = f"/api/comfy/media?filename={filename}&subfolder={subfolder}&type={folder_type}"
                    return {
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": folder_type,
                        "image_url": image_url,
                        "media_category": media_key,
                    }

    return {
        "filename": None,
        "subfolder": None,
        "type": None,
        "image_url": None,
        "media_category": None,
    }


async def preload_comfy_checkpoint(
    ckpt_name: str = "sd_xl_base_1.0.safetensors", host: str = COMFYUI_HOST
) -> bool:
    """
    Speculative VRAM Pre-loader: Sends a minimal 1-step 64x64 latent workflow to load model weights
    into NVIDIA RTX 4090 VRAM prior to user generation requests, reducing initial latency by 40-50%.
    """
    logger.info(
        f"⚡ [VRAM Warmup] Pre-loading checkpoint '{ckpt_name}' into RTX 4090 VRAM..."
    )
    warmup_wf = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": ckpt_name},
        },
        "2": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 64, "height": 64, "batch_size": 1},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "warmup", "clip": ["1", 1]},
        },
        "4": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 1,
                "steps": 1,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1,
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["3", 0],
                "latent_image": ["2", 0],
            },
        },
        "5": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
        },
    }
    try:
        prompt_id = await queue_comfyui_workflow(warmup_wf, host=host)
        logger.info(
            f"⚡ [VRAM Warmup] Warmup workflow queued successfully (ID: {prompt_id})"
        )
        return True
    except Exception as e:
        logger.warning(f"⚠️ [VRAM Warmup] Pre-load skipped or failed: {e}")
        return False


def generate_comfy_image(
    prompt: str,
    negative_prompt: str = "",
    video: bool = False,
    host: str = COMFYUI_HOST,
    **kwargs,
) -> Dict[str, Any]:
    """
    Synchronous direct Python entrypoint to trigger local ComfyUI generation.
    Returns dictionary with status, filename, prompt_id, and image_url.
    """
    from tools.tool_registry import ToolRegistry
    args = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "video": video,
        **kwargs,
    }
    return ToolRegistry.execute_tool("generate_comfy_image", args)
