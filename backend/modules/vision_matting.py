"""
AI-BS Local Hybrid Background Matting & Vision Processing Engine
----------------------------------------------------------------
Provides sub-second alpha matting, foreground extraction, and mask generation
using BiRefNet / U2Net on NVIDIA RTX 4090 silicon via ONNX Runtime GPU.
Maintains persistent singleton lifecycle to eliminate weight re-instantiation overhead.
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image

# Link CUDA 13 / cuDNN 9 runtime libraries from ComfyUI embedded environment
CUDA_DLL_DIR = r"C:\AI-BS\ComfyUI\python_embeded\Lib\site-packages\torch\lib"
if os.path.exists(CUDA_DLL_DIR):
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(CUDA_DLL_DIR)
        except Exception:
            pass
    os.environ["PATH"] = CUDA_DLL_DIR + os.pathsep + os.environ.get("PATH", "")

# Configure local offline weight storage to prevent remote phone-home / external queries
REMBG_DIR = r"C:\AI-BS\models\rembg"
os.environ["U2NET_HOME"] = REMBG_DIR
os.environ["REMBG_HOME"] = REMBG_DIR
Path(REMBG_DIR).mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("AIBSI-VisionMatting")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - [AI-BS VisionMatting] - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

try:
    import onnxruntime as ort
    from rembg import new_session, remove
except ImportError as e:
    logger.error(f"Missing required dependencies for VisionMatting: {e}")
    ort = None
    new_session = None
    remove = None


class LocalMattingEngine:
    """
    Persistent standalone background matting engine powered by BiRefNet / U2Net via ONNX Runtime GPU.
    """
    def __init__(self, model_name: str = "birefnet-general"):
        """
        Available local models:
        - 'birefnet-general': SOTA sub-pixel edge definition (hair, fur, semi-transparency).
        - 'u2net': Balanced standard matting.
        - 'isnet-general-use': High-contrast boundary extraction.
        """
        self.model_name = model_name
        self.providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.active_provider = "UNKNOWN"
        self.session = None
        self.is_ready = False
        self._init_lock = threading.Lock()
        
        self._initialize_session()

    def _initialize_session(self):
        if not new_session:
            logger.error("rembg.new_session is unavailable.")
            return

        with self._init_lock:
            start_t = time.time()
            try:
                # Initialize session with explicit CUDA execution provider
                self.session = new_session(self.model_name, providers=self.providers)
                
                # Check active provider from inner ONNX runtime session if accessible
                if hasattr(self.session, "inner_session"):
                    active_providers = self.session.inner_session.get_providers()
                    self.active_provider = active_providers[0] if active_providers else "UNKNOWN"
                else:
                    self.active_provider = "CUDAExecutionProvider" if "CUDAExecutionProvider" in ort.get_available_providers() else "CPUExecutionProvider"
                
                self.is_ready = True
                elapsed = (time.time() - start_t) * 1000.0
                logger.info(f"LocalMattingEngine loaded '{self.model_name}' on {self.active_provider} in {elapsed:.1f}ms.")
            except Exception as e:
                logger.warning(f"Failed to load '{self.model_name}' on CUDA ({e}). Attempting CPU fallback...")
                try:
                    self.session = new_session(self.model_name, providers=["CPUExecutionProvider"])
                    self.active_provider = "CPUExecutionProvider"
                    self.is_ready = True
                    logger.info(f"LocalMattingEngine loaded '{self.model_name}' on CPU fallback.")
                except Exception as ex:
                    logger.error(f"Fatal error initializing LocalMattingEngine: {ex}")
                    self.is_ready = False

    def extract_foreground(
        self,
        input_path: str,
        output_path: str,
        alpha_matting: bool = True,
        fg_threshold: int = 240,
        bg_threshold: int = 10,
        erode_size: int = 10
    ) -> str:
        """
        Extracts foreground subject with sub-pixel alpha transparency and saves as PNG.
        """
        if not self.is_ready or not self.session:
            raise RuntimeError("LocalMattingEngine is not initialized or model failed to load.")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        out_dir = os.path.dirname(output_path)
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)

        start_t = time.time()
        with Image.open(input_path) as img:
            result = remove(
                img,
                session=self.session,
                alpha_matting=alpha_matting,
                alpha_matting_foreground_threshold=fg_threshold,
                alpha_matting_background_threshold=bg_threshold,
                alpha_matting_erode_size=erode_size
            )
            result.save(output_path, format="PNG")

        elapsed_ms = (time.time() - start_t) * 1000.0
        logger.info(f"Foreground extracted in {elapsed_ms:.1f}ms -> {output_path}")
        return output_path

    def generate_mask_only(self, input_path: str, output_path: str) -> str:
        """
        Generates single-channel binary/greyscale alpha mask and saves as PNG.
        """
        if not self.is_ready or not self.session:
            raise RuntimeError("LocalMattingEngine is not initialized or model failed to load.")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        out_dir = os.path.dirname(output_path)
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)

        start_t = time.time()
        with Image.open(input_path) as img:
            mask = remove(img, session=self.session, only_mask=True)
            mask.save(output_path, format="PNG")

        elapsed_ms = (time.time() - start_t) * 1000.0
        logger.info(f"Alpha mask generated in {elapsed_ms:.1f}ms -> {output_path}")
        return output_path

    def get_runtime_telemetry(self) -> Dict[str, Any]:
        """
        Returns hardware telemetry for health inspection and observability.
        """
        return {
            "status": "READY" if self.is_ready else "ERROR",
            "model_name": self.model_name,
            "active_provider": self.active_provider,
            "cuda_available": "CUDAExecutionProvider" in ort.get_available_providers() if ort else False,
            "weight_cache_dir": REMBG_DIR,
            "vram_dedicated_estimate_mb": 1200 if "CUDA" in self.active_provider else 0
        }


# --- Persistent Module Singleton Scaffolding ---
_ENGINE_SINGLETON: Optional[LocalMattingEngine] = None
_SINGLETON_LOCK = threading.Lock()


def get_matting_engine(model_name: str = "birefnet-general") -> LocalMattingEngine:
    """
    Thread-safe access to persistent LocalMattingEngine instance.
    Prevents repeated ONNX graph construction and weight reloads across HTTP requests.
    """
    global _ENGINE_SINGLETON
    if _ENGINE_SINGLETON is None or _ENGINE_SINGLETON.model_name != model_name:
        with _SINGLETON_LOCK:
            if _ENGINE_SINGLETON is None or _ENGINE_SINGLETON.model_name != model_name:
                _ENGINE_SINGLETON = LocalMattingEngine(model_name=model_name)
    return _ENGINE_SINGLETON


if __name__ == "__main__":
    print("Testing LocalMattingEngine standalone on GPU...")
    engine = get_matting_engine()
    telemetry = engine.get_runtime_telemetry()
    print("Engine Telemetry:", telemetry)
    
    # Test synthetic image matting
    test_in = os.path.join(REMBG_DIR, "test_synthetic.png")
    test_out = os.path.join(REMBG_DIR, "test_synthetic_matte.png")
    
    # Create simple 256x256 test image with red circle on green background
    from PIL import ImageDraw
    img = Image.new("RGB", (256, 256), color=(34, 139, 34))
    draw = ImageDraw.Draw(img)
    draw.ellipse((64, 64, 192, 192), fill=(220, 20, 60))
    img.save(test_in)
    
    out = engine.extract_foreground(test_in, test_out, alpha_matting=False)
    print(f"Extraction test SUCCESS: Output written to {out}")
    if os.path.exists(test_in):
        os.remove(test_in)
    if os.path.exists(test_out):
        os.remove(test_out)
