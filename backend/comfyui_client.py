import urllib.request
import urllib.parse
import json
import logging
import email.mime.multipart
import email.mime.application
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

COMFYUI_SERVER = "http://127.0.0.1:8189"

def upload_image_to_comfyui(file_bytes: bytes, filename: str) -> Optional[Dict[str, Any]]:
    """Uploads an image to ComfyUI's input directory."""
    try:
        # Create a multipart form data request manually since we don't have requests library
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        body = bytearray()
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode('utf-8'))
        body.extend(b'Content-Type: application/octet-stream\r\n\r\n')
        body.extend(file_bytes)
        body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

        req = urllib.request.Request(f"{COMFYUI_SERVER}/upload/image", data=body)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            logger.info(f"Successfully uploaded {filename} to ComfyUI")
            return result
    except Exception as e:
        logger.error(f"Failed to upload image to ComfyUI: {e}")
        return None

def inject_prompt_into_workflow(workflow: Dict[str, Any], prompt_text: str, base_image: str | None = None) -> Dict[str, Any]:
    """
    Intelligently scans a raw ComfyUI API JSON graph and injects the dynamic prompt_text 
    into the primary positive CLIPTextEncode node, and injects base_image into LoadImage node.
    """
    import random
    modified_workflow = json.loads(json.dumps(workflow))
    
    for node_id, node_data in modified_workflow.items():
        # Inject text prompt
        if node_data.get("class_type") == "CLIPTextEncode":
            title = node_data.get("_meta", {}).get("title", "").lower()
            if "negative" not in title:
                if "inputs" in node_data and "text" in node_data["inputs"]:
                    node_data["inputs"]["text"] = prompt_text
                    
        # Inject FLUX 3 prompt and randomize seed
        if node_data.get("class_type") == "Flux3ImageToVideoNode":
            if "inputs" in node_data:
                node_data["inputs"]["prompt"] = prompt_text
                node_data["inputs"]["seed"] = random.randint(1, 999999999999999)
        
        # Inject base image
        if base_image and node_data.get("class_type") == "LoadImage":
            if "inputs" in node_data and "image" in node_data["inputs"]:
                node_data["inputs"]["image"] = base_image
    
    return modified_workflow

def queue_prompt(prompt: Dict[str, Any], client_id: str) -> Optional[Dict[str, Any]]:
    """Sends the modified JSON graph to ComfyUI's /prompt endpoint."""
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    try:
        req = urllib.request.Request(f"{COMFYUI_SERVER}/prompt", data=data)
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except Exception as e:
        logger.error(f"Failed to queue prompt to ComfyUI: {e}")
        return None

def get_history(prompt_id: str) -> Optional[Dict[str, Any]]:
    try:
        with urllib.request.urlopen(f"{COMFYUI_SERVER}/history/{prompt_id}") as response:
            return json.loads(response.read())
    except Exception as e:
        logger.error(f"Failed to get ComfyUI history for {prompt_id}: {e}")
        return None

def get_image(filename: str, subfolder: str, folder_type: str) -> Optional[bytes]:
    """Downloads an image from ComfyUI."""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    url = f"{COMFYUI_SERVER}/view?{url_values}"
    try:
        with urllib.request.urlopen(url) as response:
            return response.read()
    except Exception as e:
        logger.error(f"Failed to get image from ComfyUI: {e}")
        return None
