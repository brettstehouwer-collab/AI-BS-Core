#!/usr/bin/env python3
"""
AI-BS Matrix — Dual-Mode Local Image Generation Pipeline
===========================================================
Routes image generation requests between two local backends:
  1. PyTorch diffusers (CUDA-accelerated, RTX 4090)
  2. Ollama x/z-image-turbo (fast turbo model)

Auto-detects available environments and falls back gracefully.

Usage:
    python local_imagegen.py --prompt "A cozy cabin" --backend diffusers --output output.png
    python local_imagegen.py --prompt "A cozy cabin" --backend ollama --output output.png
    python local_imagegen.py --prompt "A cozy cabin" --auto --output output.png  # auto-detect

Requires:
    - Ollama running locally with x/z-image-turbo model
    - Python 3.12 + PyTorch CUDA + diffusers (for diffusers backend)
"""

import argparse
import asyncio
import base64
import io
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("local_imagegen")

# --- Paths ---
WORKSPACE = Path(__file__).parent.resolve()
IMAGEGEN_OUTPUT_DIR = WORKSPACE / "output" / "imagegen"
IMAGEGEN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Backend Detection ---
DIFFUSERS_AVAILABLE = False
CUDA_AVAILABLE = False
OLLAMA_AVAILABLE = False

try:
    import torch  # type: ignore
    DIFFUSERS_AVAILABLE = True
    CUDA_AVAILABLE = torch.cuda.is_available()
    if CUDA_AVAILABLE:
        logger.info(f"PyTorch CUDA detected: {torch.cuda.get_device_name(0)}")
    else:
        logger.warning(
            "PyTorch installed but CUDA NOT available — diffusers will be slow on CPU")
except ImportError:
    logger.info("PyTorch not installed — diffusers backend unavailable")

try:
    from diffusers import StableDiffusionPipeline, FluxPipeline  # type: ignore
    if DIFFUSERS_AVAILABLE:
        DIFFUSERS_AVAILABLE = True
except ImportError:
    logger.info("diffusers not installed — diffusers backend unavailable")

try:
    import ollama  # type: ignore
    OLLAMA_AVAILABLE = True
except ImportError:
    logger.info(
        "ollama Python SDK not installed — using subprocess for Ollama CLI")


# --- Configuration ---
@dataclass
class ImageGenConfig:
    """Configuration for image generation."""
    prompt: str
    backend: str = "auto"  # "diffusers", "ollama", "auto"
    output_path: Optional[str] = None
    model_id: str = ""  # auto-selected based on backend
    size: str = "1024x1024"
    quality: str = "medium"
    num_steps: int = 30
    guidance_scale: float = 7.5
    seed: Optional[int] = None

    def __post_init__(self):
        if not self.output_path:
            self.output_path = str(
                IMAGEGEN_OUTPUT_DIR /
                f"generated_{
                    hash(
                        self.prompt) %
                    10000}.png")

        # Auto-select model
        if not self.model_id:
            if self.backend == "diffusers":
                # or "black-forest-labs/FLUX.1-schnell"
                self.model_id = "runwayml/stable-diffusion-v1-5"
            elif self.backend == "ollama":
                self.model_id = "x/z-image-turbo"


@dataclass
class ImageGenResult:
    """Result from image generation."""
    status: str  # "success", "error", "fallback"
    output_path: Optional[str] = None
    backend_used: str = ""
    model_used: str = ""
    prompt: str = ""
    error: Optional[str] = None
    generation_time_sec: float = 0.0

    def __bool__(self):
        return self.status == "success"


# --- Diffusers Backend ---
class DiffusersBackend:
    """CUDA-accelerated image generation via Hugging Face diffusers."""

    MODELS = {
        "sd15": "runwayml/stable-diffusion-v1-5",
        "sdxl": "stabilityai/stable-diffusion-xl-base-1.0",
        "flux_schnell": "black-forest-labs/FLUX.1-schnell",
        "flux_dev": "black-forest-labs/FLUX.1-dev",
    }

    def __init__(self, model_id: str = "runwayml/stable-diffusion-v1-5"):
        self.model_id = model_id
        self.pipe = None
        logger.info(f"DiffusersBackend initialized with model: {model_id}")

    async def generate(self, config: ImageGenConfig) -> ImageGenResult:
        """Generate image using diffusers pipeline."""
        import time
        start = time.time()

        try:
            # Lazy load pipeline (downloads on first use)
            if self.pipe is None:
                logger.info(f"Loading model {self.model_id}...")
                torch_dtype = torch.float16 if CUDA_AVAILABLE else torch.float32

                if "FLUX" in self.model_id.upper():
                    from diffusers import FluxPipeline  # type: ignore
                    self.pipe = FluxPipeline.from_pretrained(
                        self.model_id,
                        torch_dtype=torch_dtype,
                    )
                else:
                    from diffusers import StableDiffusionPipeline  # type: ignore
                    self.pipe = StableDiffusionPipeline.from_pretrained(
                        self.model_id,
                        torch_dtype=torch_dtype,
                    )

                if CUDA_AVAILABLE:
                    self.pipe = self.pipe.to("cuda")
                    logger.info(
                        f"Model loaded on CUDA: {
                            torch.cuda.get_device_name(0)}")
                else:
                    logger.warning("Running on CPU — this will be slow")

            # Generate
            logger.info(
                f"Generating image ({
                    config.num_steps} steps, CFG {
                    config.guidance_scale})...")

            if "FLUX" in self.model_id.upper():
                from diffusers import FluxPipeline  # type: ignore
                image = self.pipe(
                    prompt=config.prompt,
                    num_inference_steps=config.num_steps,
                    guidance_scale=config.guidance_scale,
                    seed=config.seed,
                ).images[0]
            else:
                from diffusers import StableDiffusionPipeline  # type: ignore
                image = self.pipe(
                    prompt=config.prompt,
                    num_inference_steps=config.num_steps,
                    guidance_scale=config.guidance_scale,
                    height=int(
                        config.size.split("x")[1]) if "x" in config.size else 512,
                    width=int(
                        config.size.split("x")[0]) if "x" in config.size else 512,
                    seed=config.seed,
                ).images[0]

            # Save
            output = Path(config.output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(output))

            elapsed = time.time() - start
            logger.info(
                f"Diffusers generation complete: {output} ({
                    elapsed:.1f}s)")

            return ImageGenResult(
                status="success",
                output_path=str(output),
                backend_used="diffusers",
                model_used=self.model_id,
                prompt=config.prompt,
                generation_time_sec=elapsed,
            )

        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"Diffusers generation failed: {e}")
            return ImageGenResult(
                status="error",
                backend_used="diffusers",
                model_used=self.model_id,
                prompt=config.prompt,
                error=str(e),
                generation_time_sec=elapsed,
            )


# --- Ollama Backend ---
class OllamaBackend:
    """Local image generation via Ollama x/z-image-turbo."""

    def __init__(self, model_id: str = "x/z-image-turbo"):
        self.model_id = model_id
        logger.info(f"OllamaBackend initialized with model: {model_id}")

    async def generate(self, config: ImageGenConfig) -> ImageGenResult:
        """Generate image using Ollama."""
        import time
        start = time.time()

        output = Path(config.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Try Python SDK first
        try:
            return await self._generate_via_sdk(config, output, start)
        except Exception as sdk_error:
            logger.warning(
                f"Ollama SDK failed ({sdk_error}), falling back to CLI...")

        # Fallback to subprocess
        return await self._generate_via_cli(config, output, start)

    async def _generate_via_sdk(
            self,
            config: ImageGenConfig,
            output: Path,
            start: float) -> ImageGenResult:
        """Generate via ollama Python SDK."""
        try:
            import ollama  # type: ignore

            # Ollama image generation via SDK
            response = ollama.generate(
                model=self.model_id,
                prompt=config.prompt,
                stream=False,
            )

            # Extract image from response (format varies by model)
            if hasattr(response, 'image') and response.image:
                # Binary image data
                img_bytes = base64.b64decode(
                    response.image) if isinstance(
                    response.image,
                    str) else response.image
                image = __import__("PIL").Image.open(io.BytesIO(img_bytes))
                image.save(str(output))
            elif hasattr(response, 'model') and response.model:
                # Some models return metadata; check for file output
                logger.info(f"Ollama response model: {response.model}")
                # Check default Ollama output directory
                ollama_dir = Path.home() / ".ollama" / "helpers"
                if ollama_dir.exists():
                    latest = max(
                        ollama_dir.glob("*.png"),
                        key=lambda p: p.stat().st_mtime)
                    latest.rename(output)

            elapsed = time.time() - start
            logger.info(
                f"Ollama SDK generation complete: {output} ({
                    elapsed:.1f}s)")

            return ImageGenResult(
                status="success",
                output_path=str(output),
                backend_used="ollama",
                model_used=self.model_id,
                prompt=config.prompt,
                generation_time_sec=elapsed,
            )

        except Exception as e:
            raise e  # Re-raise to trigger CLI fallback

    async def _generate_via_cli(
            self,
            config: ImageGenConfig,
            output: Path,
            start: float) -> ImageGenResult:
        """Generate via Ollama CLI subprocess."""
        try:
            logger.info(
                f"Running: ollama run {
                    self.model_id} \"{
                    config.prompt}\"")

            # Run Ollama CLI — it saves to current directory by default
            proc = await asyncio.create_subprocess_exec(
                "ollama", "run", self.model_id, config.prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            elapsed = time.time() - start

            # Check for generated image in current/working directory
            png_files = list(Path.cwd().glob("*.png"))
            if png_files:
                latest = max(png_files, key=lambda p: p.stat().st_mtime)
                latest.rename(output)
                logger.info(
                    f"Ollama CLI generation complete: {output} ({
                        elapsed:.1f}s)")
                return ImageGenResult(
                    status="success",
                    output_path=str(output),
                    backend_used="ollama",
                    model_used=self.model_id,
                    prompt=config.prompt,
                    generation_time_sec=elapsed,
                )
            else:
                # Ollama may have printed the image to stdout or saved
                # elsewhere
                logger.warning(
                    "Ollama CLI ran but no PNG found — check output directory")
                return ImageGenResult(
                    status="error",
                    backend_used="ollama",
                    model_used=self.model_id,
                    prompt=config.prompt,
                    error="No output image found. Ollama may require interactive mode.",
                    generation_time_sec=elapsed,
                )

        except FileNotFoundError:
            return ImageGenResult(
                status="error",
                backend_used="ollama",
                model_used=self.model_id,
                prompt=config.prompt,
                error="Ollama CLI not found. Ensure Ollama is installed and in PATH.",
            )
        except Exception as e:
            elapsed = time.time() - start
            return ImageGenResult(
                status="error",
                backend_used="ollama",
                model_used=self.model_id,
                prompt=config.prompt,
                error=str(e),
                generation_time_sec=elapsed,
            )


# --- Orchestrator ---
class LocalImageGen:
    """Dual-mode image generation orchestrator."""

    def __init__(self):
        self.diffusers_backend: Optional[DiffusersBackend] = None
        self.ollama_backend: Optional[OllamaBackend] = None

        if DIFFUSERS_AVAILABLE and CUDA_AVAILABLE:
            logger.info("✓ Diffusers backend available (CUDA-accelerated)")
        elif DIFFUSERS_AVAILABLE:
            logger.warning("⚠ Diffusers available but NO CUDA — will be slow")

        if OLLAMA_AVAILABLE:
            logger.info("✓ Ollama backend available")

        # Check for x/z-image-turbo model
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            if "x/z-image-turbo" in result.stdout:
                logger.info("✓ x/z-image-turbo model found in Ollama")
            else:
                logger.warning(
                    "⚠ x/z-image-turbo not found. Run: ollama pull x/z-image-turbo")
        except Exception:
            pass

    async def generate(self, config: ImageGenConfig) -> ImageGenResult:
        """Generate image with auto/backend selection."""
        # Determine backend
        if config.backend == "auto":
            if DIFFUSERS_AVAILABLE and CUDA_AVAILABLE:
                config.backend = "diffusers"
                logger.info("Auto-selecting diffusers (CUDA available)")
            elif OLLAMA_AVAILABLE:
                config.backend = "ollama"
                logger.info(
                    "Auto-selecting Ollama (diffusers unavailable/slow)")
            else:
                return ImageGenResult(
                    status="error",
                    prompt=config.prompt,
                    error="No backend available. Install PyTorch CUDA or Ollama.",
                )

        # Execute
        if config.backend == "diffusers":
            if not DIFFUSERS_AVAILABLE:
                logger.warning(
                    "Diffusers requested but unavailable — falling back to Ollama")
                config.backend = "ollama"
                return await self.generate(config)

            if self.diffusers_backend is None:
                self.diffusers_backend = DiffusersBackend(
                    config.model_id or DiffusersBackend.MODELS["sd15"])

            return await self.diffusers_backend.generate(config)

        elif config.backend == "ollama":
            if not OLLAMA_AVAILABLE:
                logger.warning(
                    "Ollama requested but SDK unavailable — using subprocess")

            if self.ollama_backend is None:
                self.ollama_backend = OllamaBackend(
                    config.model_id or "x/z-image-turbo")

            return await self.ollama_backend.generate(config)

        else:
            return ImageGenResult(
                status="error",
                prompt=config.prompt,
                error=f"Unknown backend: {config.backend}",
            )

    async def generate_batch(
            self,
            prompts: List[str],
            **kwargs) -> List[ImageGenResult]:
        """Generate multiple images."""
        results = []
        for i, prompt in enumerate(prompts):
            config = ImageGenConfig(prompt=prompt, **kwargs)
            config.output_path = str(
                IMAGEGEN_OUTPUT_DIR /
                f"batch_{
                    i:03d}.png")
            result = await self.generate(config)
            results.append(result)
        return results


# --- Singleton Instance ---
_imagegen_instance = None


def get_local_imagegen() -> LocalImageGen:
    """Return a singleton instance of the LocalImageGen orchestrator."""
    global _imagegen_instance
    if _imagegen_instance is None:
        _imagegen_instance = LocalImageGen()
    return _imagegen_instance


# --- CLI Entry Point ---
def main():
    parser = argparse.ArgumentParser(
        description="AI-BS Matrix — Dual-Mode Local Image Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect best backend
  python local_imagegen.py --prompt "A cozy cabin" --auto

  # Force diffusers (requires PyTorch CUDA)
  python local_imagegen.py --prompt "A cozy cabin" --backend diffusers

  # Force Ollama (fast turbo model)
  python local_imagegen.py --prompt "A cozy cabin" --backend ollama

  # Custom parameters
  python local_imagegen.py --prompt "A cozy cabin" --backend ollama --output my_image.png --steps 50
        """
    )

    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        required=True,
        help="Text prompt for image generation")
    parser.add_argument(
        "--backend",
        "-b",
        type=str,
        choices=[
            "diffusers",
            "ollama",
            "auto"],
        default="auto",
        help="Backend to use (default: auto)")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path")
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="",
        help="Model ID (auto-selected if not specified)")
    parser.add_argument(
        "--size",
        "-s",
        type=str,
        default="1024x1024",
        help="Image size (e.g., 1024x1024)")
    parser.add_argument(
        "--steps",
        "-n",
        type=int,
        default=30,
        help="Number of inference steps")
    parser.add_argument(
        "--guidance",
        "-g",
        type=float,
        default=7.5,
        help="CFG guidance scale")
    parser.add_argument(
        "--seed",
        "-d",
        type=int,
        default=None,
        help="Random seed for reproducibility")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = ImageGenConfig(
        prompt=args.prompt,
        backend=args.backend,
        output_path=args.output,
        model_id=args.model,
        size=args.size,
        num_steps=args.steps,
        guidance_scale=args.guidance,
        seed=args.seed,
    )

    # Run
    imagegen = LocalImageGen()
    result = asyncio.run(imagegen.generate(config))

    # Output
    print("\n" + "=" * 60)
    if result.status == "success":
        print(f"✓ SUCCESS: {result.output_path}")
        print(f"  Backend: {result.backend_used}")
        print(f"  Model: {result.model_used}")
        print(f"  Time: {result.generation_time_sec:.1f}s")
    else:
        print(f"✗ ERROR: {result.error}")
    print("=" * 60)

    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
