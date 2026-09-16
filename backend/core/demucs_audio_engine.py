import os
import sys
import time
import uuid
import json
import logging
from typing import Dict, Any, Optional, List
import torch

logger = logging.getLogger("DemucsAudioEngine")

STEMS_DIR = r"C:\AI-BS\saved_data\audio_stems"
os.makedirs(STEMS_DIR, exist_ok=True)
INDEX_FILE = os.path.join(STEMS_DIR, "stems_manifest.json")


class DemucsAudioEngine:
    """
    Local AI Audio Stem Separator using PyTorch & Demucs on NVIDIA RTX 4090.
    Directly isolates vocals, drums, bass, and instrumental accompaniment for Suno AI and DAW workflows.
    """

    @staticmethod
    def get_hardware_status() -> Dict[str, Any]:
        cuda_ok = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_ok else "None (CPU Fallback)"
        vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if cuda_ok else 0.0
        return {
            "cuda_available": cuda_ok,
            "device": "cuda" if cuda_ok else "cpu",
            "gpu_name": gpu_name,
            "vram_total_gb": vram_gb,
            "default_model": "htdemucs"
        }

    @staticmethod
    def separate_stems(
        audio_file_path: str,
        output_dir: Optional[str] = None,
        model_name: str = "htdemucs",
        two_stems: Optional[str] = None, # e.g. "vocals" for vocal/instrumental split
        segment: Optional[int] = None,
        shifts: int = 1
    ) -> Dict[str, Any]:
        """
        Executes local PyTorch/CUDA stem separation.
        Saves discrete stems into target DAW folder.
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Input audio file not found: {audio_file_path}")

        start_time = time.time()
        session_id = f"stem_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        target_folder = output_dir or os.path.join(STEMS_DIR, session_id)
        os.makedirs(target_folder, exist_ok=True)

        device = "cuda" if torch.cuda.is_available() else "cpu"

        import demucs.api
        separator = demucs.api.Separator(
            model=model_name,
            device=device,
            segment=segment,
            shifts=shifts
        )

        origin_name = os.path.splitext(os.path.basename(audio_file_path))[0]
        logger.info(f"Separating audio: {audio_file_path} on {device} using {model_name}...")

        # Run Demucs separation
        origin, separated = separator.separate_audio_file(audio_file_path)

        stems_exported = {}
        for stem_name, stem_tensor in separated.items():
            out_stem_path = os.path.join(target_folder, f"{stem_name}.wav")
            demucs.api.save_audio(stem_tensor, out_stem_path, samplerate=separator.samplerate)
            stems_exported[stem_name] = {
                "path": out_stem_path,
                "filename": f"{stem_name}.wav",
                "size_bytes": os.path.getsize(out_stem_path),
                "url": f"/api/v1/audio/demucs/file/{session_id}/{stem_name}.wav"
            }

        # If 4 stems, also generate composite 'instrumental.wav' (drums + bass + other)
        if "drums" in separated and "bass" in separated and "other" in separated:
            try:
                instrumental_tensor = separated["drums"] + separated["bass"] + separated["other"]
                inst_path = os.path.join(target_folder, "instrumental.wav")
                demucs.api.save_audio(instrumental_tensor, inst_path, samplerate=separator.samplerate)
                stems_exported["instrumental"] = {
                    "path": inst_path,
                    "filename": "instrumental.wav",
                    "size_bytes": os.path.getsize(inst_path),
                    "url": f"/api/v1/audio/demucs/file/{session_id}/instrumental.wav"
                }
            except Exception as e:
                logger.warning(f"Error mixing composite instrumental: {e}")

        elapsed_sec = round(time.time() - start_time, 2)

        manifest_entry = {
            "session_id": session_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": audio_file_path,
            "origin_name": origin_name,
            "target_folder": target_folder,
            "model": model_name,
            "device": device,
            "elapsed_seconds": elapsed_sec,
            "stems": list(stems_exported.keys()),
            "stems_detail": stems_exported
        }

        DemucsAudioEngine._record_manifest(manifest_entry)

        return {
            "status": "success",
            "session_id": session_id,
            "source_file": audio_file_path,
            "target_folder": target_folder,
            "device": device,
            "elapsed_seconds": elapsed_sec,
            "stems_count": len(stems_exported),
            "stems": stems_exported
        }

    @staticmethod
    def _record_manifest(entry: Dict[str, Any]):
        manifest = []
        if os.path.exists(INDEX_FILE):
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = []
        manifest.insert(0, entry)
        try:
            with open(INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(manifest[:100], f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write stems manifest: {e}")

    @staticmethod
    def list_recent_sessions() -> List[Dict[str, Any]]:
        if os.path.exists(INDEX_FILE):
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
