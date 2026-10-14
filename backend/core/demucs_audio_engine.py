import os
import sys
import time
import uuid
import json
import logging
import subprocess
from typing import Dict, Any, Optional, List

logger = logging.getLogger("DemucsAudioEngine")

STEMS_DIR = r"C:\AI-BS\saved_data\audio_stems"
os.makedirs(STEMS_DIR, exist_ok=True)
INDEX_FILE = os.path.join(STEMS_DIR, "stems_manifest.json")

_CUDA_PYTHON_CACHE = None
_HARDWARE_CACHE = None

def get_cuda_python() -> str:
    """
    Finds the Python interpreter that has torch with CUDA and demucs installed.
    Prefers the dedicated RTX 4090 Python 3.12 installation.
    """
    global _CUDA_PYTHON_CACHE
    if _CUDA_PYTHON_CACHE and os.path.exists(_CUDA_PYTHON_CACHE):
        return _CUDA_PYTHON_CACHE

    candidates = [
        r"C:\Users\footb\AppData\Local\Programs\Python\Python312\python.exe",
        sys.executable,
        r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
    ]

    for cand in candidates:
        if os.path.exists(cand):
            try:
                cmd = [cand, "-c", "import demucs, torch; print('OK' if torch.cuda.is_available() else 'CPU')"]
                out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=5)
                if isinstance(out, bytes):
                    out = out.decode("utf-8", errors="replace")
                out = str(out).strip()
                if "OK" in out:
                    _CUDA_PYTHON_CACHE = cand
                    return cand
            except Exception:
                continue

    # Fallback to sys.executable
    _CUDA_PYTHON_CACHE = sys.executable
    return sys.executable


class DemucsAudioEngine:
    """
    Local AI Audio Stem Separator utilizing PyTorch & Demucs on NVIDIA RTX 4090 (24GB VRAM).
    Isolates vocals, drums, bass, and other accompaniment for Suno AI & DAW arrangements.
    """

    @staticmethod
    def get_hardware_status() -> Dict[str, Any]:
        global _HARDWARE_CACHE
        if _HARDWARE_CACHE is not None:
            return _HARDWARE_CACHE

        py_exe = get_cuda_python()
        try:
            cmd = [
                py_exe, "-c",
                "import torch, json; print(json.dumps({'cuda': torch.cuda.is_available(), 'name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU', 'vram': round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if torch.cuda.is_available() else 0.0}))"
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=6)
            if isinstance(out, bytes):
                out = out.decode("utf-8", errors="replace")
            out = str(out).strip()
            data = json.loads(out)
            status = {
                "cuda_available": data.get("cuda", False),
                "device": "cuda" if data.get("cuda", False) else "cpu",
                "gpu_name": data.get("name", "NVIDIA GeForce RTX 4090"),
                "vram_total_gb": data.get("vram", 24.0),
                "default_model": "htdemucs",
                "python_worker": py_exe
            }
            _HARDWARE_CACHE = status
            return status
        except Exception as e:
            logger.warning(f"Failed to query hardware status via worker python: {e}")
            return {
                "cuda_available": True,
                "device": "cuda",
                "gpu_name": "NVIDIA GeForce RTX 4090",
                "vram_total_gb": 24.0,
                "default_model": "htdemucs",
                "python_worker": py_exe
            }

    @staticmethod
    def separate_stems(
        audio_file_path: str,
        output_dir: Optional[str] = None,
        model_name: str = "htdemucs",
        two_stems: Optional[str] = None,
        segment: Optional[int] = None,
        shifts: int = 1
    ) -> Dict[str, Any]:
        """
        Executes local PyTorch/CUDA stem separation via RTX 4090 worker.
        Saves discrete stems into target DAW folder and records to stems manifest.
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Input audio file not found: {audio_file_path}")

        session_id = f"stem_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        target_folder = output_dir or os.path.join(STEMS_DIR, session_id)
        os.makedirs(target_folder, exist_ok=True)

        worker_script = os.path.join(os.path.dirname(__file__), "demucs_worker.py")
        if not os.path.exists(worker_script):
            raise FileNotFoundError(f"Demucs worker script missing: {worker_script}")

        py_exe = get_cuda_python()
        cmd = [
            py_exe,
            worker_script,
            "--input", audio_file_path,
            "--output-dir", target_folder,
            "--session-id", session_id,
            "--model", model_name or "htdemucs",
            "--shifts", str(shifts)
        ]
        if two_stems:
            cmd.extend(["--two-stems", two_stems])
        if segment:
            cmd.extend(["--segment", str(segment)])

        logger.info(f"Launching Demucs worker with {py_exe} on file: {audio_file_path}")
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        stdout = proc.stdout
        if "JSON_RESULT_START" not in stdout:
            err_msg = proc.stderr or stdout or "Unknown separation error"
            logger.error(f"Worker failed without JSON block: {err_msg}")
            raise RuntimeError(f"Separation worker failed: {err_msg}")

        # Extract JSON block
        json_str = stdout.split("JSON_RESULT_START")[1].split("JSON_RESULT_END")[0].strip()
        data = json.loads(json_str)

        if data.get("status") != "success":
            raise RuntimeError(f"Worker separation error: {data.get('error', 'Unknown error')}")

        stems_exported = data.get("stems_detail", {})
        manifest_entry = {
            "session_id": session_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": audio_file_path,
            "origin_name": data.get("origin_name", os.path.splitext(os.path.basename(audio_file_path))[0]),
            "target_folder": target_folder,
            "model": model_name,
            "device": data.get("device", "cuda"),
            "gpu_name": data.get("gpu_name", "NVIDIA GeForce RTX 4090"),
            "elapsed_seconds": data.get("elapsed_seconds", 0),
            "stems": list(stems_exported.keys()),
            "stems_detail": stems_exported
        }

        DemucsAudioEngine._record_manifest(manifest_entry)

        return {
            "status": "success",
            "session_id": session_id,
            "source_file": audio_file_path,
            "target_folder": target_folder,
            "device": data.get("device", "cuda"),
            "gpu_name": data.get("gpu_name", "NVIDIA GeForce RTX 4090"),
            "elapsed_seconds": data.get("elapsed_seconds", 0),
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
