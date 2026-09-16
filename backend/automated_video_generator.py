import os
import json
import logging
import httpx
import asyncio
from typing import Dict

from r2_storage import R2StorageManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [VideoGenerator] %(message)s"
)


class VideoGenerator:
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "sandbox", "videos")
            )
        self.output_dir = output_dir

        self.comfy_url = "http://127.0.0.1:8189"
        self.r2 = R2StorageManager()
        os.makedirs(self.output_dir, exist_ok=True)

    async def upload_to_r2(self, file_path: str, filename: str) -> str:
        """Uploads the generated video file to Cloudflare R2 bucket using R2StorageManager."""
        r2_object_name = f"marketing/{filename}"
        success = await self.r2.upload_file(file_path, r2_object_name)
        if success:
            cf_account_id = os.getenv(
                "CF_ACCOUNT_ID", "81041170430c35368afacc42e6efec67"
            )
            r2_url = f"https://{cf_account_id}.r2.cloudflarestorage.com/aibs-vault/{r2_object_name}"
            custom_domain = os.getenv(
                "R2_CUSTOM_DOMAIN", "assets.stehouwer-publishing.com"
            )
            if custom_domain:
                r2_url = f"https://{custom_domain}/{r2_object_name}"

            try:
                os.remove(file_path)
                logging.info(f"🗑️ Cleaned up local file: {file_path}")
            except Exception as e:
                logging.warning(f"⚠️ Failed to delete local file: {e}")

            return r2_url
        return ""

    async def generate_marketing_video(self, business_name: str, prompt: str) -> Dict:
        """Triggers a video generation workflow via ComfyUI, falling back to high-fidelity simulation if offline."""
        logging.info(
            f"🎬 Initializing marketing video generation for '{business_name}'..."
        )
        logging.info(f"Prompt: '{prompt}'")

        # 1. Check ComfyUI status
        comfy_online = False
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(self.comfy_url)
                if res.status_code == 200:
                    comfy_online = True
        except Exception:
            pass

        if not comfy_online:
            logging.error("ComfyUI is offline. Cannot generate physical video.")
            return {
                "status": "error",
                "message": "ComfyUI is unreachable on port 8188.",
            }

        logging.info(
            "⚡ ComfyUI is ONLINE on port 8188! Queuing generation workflow..."
        )

        prompt_id = None
        try:
            workflow_payload = {
                "client_id": "ai-bs-video-generator",
                "prompt": {
                    "3": {
                        "class_type": "KSampler",
                        "inputs": {
                            "cfg": 8,
                            "denoise": 1,
                            "latent_image": ["5", 0],
                            "model": ["4", 0],
                            "noise_seed": 42,
                            "steps": 20,
                        },
                    },
                    "4": {
                        "class_type": "CheckpointLoaderSimple",
                        "inputs": {"ckpt_name": "AnimateDiff_v3.safetensors"},
                    },
                    "5": {
                        "class_type": "EmptyLatentImage",
                        "inputs": {"batch_size": 16, "height": 512, "width": 512},
                    },
                    "6": {
                        "class_type": "CLIPTextEncode",
                        "inputs": {"text": prompt, "clip": ["4", 1]},
                    },
                    "7": {
                        "class_type": "VAEDecode",
                        "inputs": {"latent_image": ["3", 0], "vae": ["4", 2]},
                    },
                    "8": {
                        "class_type": "VHS_WriteVideo",
                        "inputs": {
                            "images": ["7", 0],
                            "filenames": f"pitch_{business_name.replace(' ', '_')}",
                        },
                    },
                },
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.comfy_url}/prompt", json=workflow_payload
                )
                if res.status_code == 200:
                    data = res.json()
                    prompt_id = data.get("prompt_id")
                    logging.info(
                        f"✅ ComfyUI prompt queued successfully. Prompt ID: {prompt_id}"
                    )
                else:
                    raise Exception(f"Failed to queue prompt: {res.text}")
        except Exception as e:
            logging.error(f"⚠️ ComfyUI prompt dispatch failed: {e}")
            return {"status": "error", "message": str(e)}

        # 2. Wait for ComfyUI to finish (Polling)
        video_filename = None
        if prompt_id:
            logging.info("⏳ Polling ComfyUI history for completion...")
            async with httpx.AsyncClient(timeout=10.0) as client:
                for _ in range(60):  # Poll for up to 600 seconds (10 mins)
                    await asyncio.sleep(10)
                    try:
                        history_res = await client.get(
                            f"{self.comfy_url}/history/{prompt_id}"
                        )
                        if history_res.status_code == 200:
                            history_data = history_res.json()
                            if prompt_id in history_data:
                                # Completed!
                                outputs = history_data[prompt_id].get("outputs", {})
                                # Find the output file
                                for node_id, node_output in outputs.items():
                                    if (
                                        "gifs" in node_output
                                        and len(node_output["gifs"]) > 0
                                    ):
                                        video_filename = node_output["gifs"][0].get(
                                            "filename"
                                        )
                                        break
                                break
                    except Exception as poll_e:
                        logging.warning(f"Polling error: {poll_e}")

        if not video_filename:
            return {
                "status": "error",
                "message": "Video generation timed out or failed to produce an output file.",
            }

        # 3. Fetch the physical video file from ComfyUI
        filename = f"pitch_{business_name.lower().replace(' ', '_')}_{video_filename}"
        output_path = os.path.join(self.output_dir, filename)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                video_res = await client.get(
                    f"{self.comfy_url}/view?filename={video_filename}&type=output"
                )
                if video_res.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(video_res.content)
                    logging.info(f"💾 Physical video file saved to: {output_path}")
                else:
                    raise Exception("Could not fetch video from /view endpoint.")
        except Exception as e:
            logging.error(f"❌ Failed to write physical video asset: {e}")
            return {"status": "error", "message": "Failed to download generated video."}

        # 4. Upload to Cloudflare R2
        r2_url = await self.upload_to_r2(output_path, filename)

        return {
            "status": "success",
            "business_name": business_name,
            "video_path": output_path,
            "r2_url": r2_url,
            "comfyui_integrated": comfy_online,
            "message": f"Physical marketing video generated successfully for {business_name}.",
        }
