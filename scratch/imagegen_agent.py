"""
ImageGen Agent — OpenAI GPT Image API Integration
====================================================
Wraps the Codex image generation CLI (`scripts/image_gen.py`) as an async tool
for the AI-BS Swarm Orchestrator.

Provides:
- Image generation from text prompts (gpt-image-2 default)
- Image editing with reference images
- Chroma-key background removal
- Batch generation from JSONL manifests

Requires: OPENAI_API_KEY environment variable
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# --- Paths ---
WORKSPACE = Path(__file__).parent
IMAGEGEN_CLI = WORKSPACE / "stehouwer_vector_memory" / \
    "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"
CHROMA_KEY_REMOVER = WORKSPACE / "stehouwer_vector_memory" / "skills" / \
    ".system" / "imagegen" / "scripts" / "remove_chroma_key.py"
IMAGEGEN_OUTPUT = WORKSPACE / "output" / "imagegen"

# --- Defaults (from image_gen.py) ---
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "auto"
DEFAULT_QUALITY = "medium"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_CONCURRENCY = 5


@dataclass
class ImageGenResult:
    """Result from an image generation or edit operation."""
    status: str  # "success", "error", "dry_run"
    output_path: Optional[str] = None
    model: str = DEFAULT_MODEL
    size: str = DEFAULT_SIZE
    quality: str = DEFAULT_QUALITY
    prompt: str = ""
    b64_images: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def __bool__(self):
        return self.status == "success"


@dataclass
class ImageGenConfig:
    """Configuration for a single image generation request."""
    prompt: str
    model: str = DEFAULT_MODEL
    size: str = DEFAULT_SIZE
    quality: str = DEFAULT_QUALITY
    output_format: str = DEFAULT_OUTPUT_FORMAT
    n: int = 1
    background: Optional[str] = None  # "transparent", "opaque", "auto"
    output_path: Optional[str] = None
    dry_run: bool = False
    input_images: List[str] = field(default_factory=list)  # for edit mode
    mask_image: Optional[str] = None  # for edit mode


class ImageGenAgent:
    """
    Async image generation agent wrapping the Codex CLI fallback.

    Operates as a pre-processing gate in the Swarm Orchestrator pipeline.
    Routes creative/media input to the correct processing pipeline before
    agent delegation.

    Usage:
        agent = ImageGenAgent()
        result = await agent.generate(ImageGenConfig(prompt="A cozy cabin"))
    """

    def __init__(self):
        self._output_dir = IMAGEGEN_OUTPUT
        self._output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ImageGenAgent initialized")

    # --- Core Generation ---
    async def generate(self, config: ImageGenConfig) -> ImageGenResult:
        """
        Generate images from a text prompt.

        Args:
            config: Image generation configuration

        Returns:
            ImageGenResult with output path or error
        """
        if not os.getenv("OPENAI_API_KEY") and not config.dry_run:
            return ImageGenResult(
                status="error",
                model=config.model,
                prompt=config.prompt,
                error="OPENAI_API_KEY is not set. Export it before running.",
            )

        cmd = [
            "python", str(IMAGEGEN_CLI), "generate",
            "--prompt", config.prompt,
            "--model", config.model,
            "--size", config.size,
            "--quality", config.quality,
            "--output-format", config.output_format,
            "--n", str(config.n),
        ]

        if config.background:
            cmd.extend(["--background", config.background])
        if config.dry_run:
            cmd.append("--dry-run")
        if config.output_path:
            out = Path(config.output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--out", str(out)])
        else:
            # Default output path
            out = self._output_dir / \
                f"generated_{hash(config.prompt) % 10000}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--out", str(out)])

        logger.info(
            f"ImageGen: {'[DRY RUN] ' if config.dry_run else ''}Running: {' '.join(cmd[:5])}...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                output_path = str(out) if config.output_path else str(out)
                logger.info(f"ImageGen: Generated image at {output_path}")
                return ImageGenResult(
                    status="success",
                    output_path=output_path,
                    model=config.model,
                    size=config.size,
                    quality=config.quality,
                    prompt=config.prompt,
                )
            else:
                error_msg = stderr.decode().strip()
                logger.warning(f"ImageGen: Generation failed: {error_msg}")
                return ImageGenResult(
                    status="error",
                    model=config.model,
                    prompt=config.prompt,
                    error=error_msg,
                )
        except FileNotFoundError:
            return ImageGenResult(
                status="error",
                model=config.model,
                prompt=config.prompt,
                error=f"CLI not found at {IMAGEGEN_CLI}. Ensure Codex skills are installed.",
            )

    # --- Image Editing ---
    async def edit(self, config: ImageGenConfig) -> ImageGenResult:
        """
        Edit existing images with a prompt.

        Args:
            config: Must include input_images list

        Returns:
            ImageGenResult with output path or error
        """
        if not config.input_images:
            return ImageGenResult(
                status="error",
                model=config.model,
                prompt=config.prompt,
                error="Edit mode requires input_images.",
            )

        cmd = [
            "python", str(IMAGEGEN_CLI), "edit",
            "--prompt", config.prompt,
            "--model", config.model,
            "--quality", config.quality,
        ]

        for img in config.input_images:
            cmd.extend(["--image", img])

        if config.mask_image:
            cmd.extend(["--mask", config.mask_image])
        if config.output_path:
            out = Path(config.output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--out", str(out)])
        else:
            out = self._output_dir / \
                f"edited_{hash(config.prompt) % 10000}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--out", str(out)])

        logger.info(f"ImageGen: Editing images...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                logger.info(f"ImageGen: Edited image at {out}")
                return ImageGenResult(
                    status="success",
                    output_path=str(out),
                    model=config.model,
                    prompt=config.prompt,
                )
            else:
                error_msg = stderr.decode().strip()
                logger.warning(f"ImageGen: Edit failed: {error_msg}")
                return ImageGenResult(
                    status="error",
                    model=config.model,
                    prompt=config.prompt,
                    error=error_msg,
                )
        except FileNotFoundError:
            return ImageGenResult(
                status="error",
                model=config.model,
                prompt=config.prompt,
                error=f"CLI not found at {IMAGEGEN_CLI}.",
            )

    # --- Batch Generation ---
    async def generate_batch(
            self,
            manifest_path: str,
            concurrency: int = DEFAULT_CONCURRENCY) -> List[ImageGenResult]:
        """
        Run many generation jobs from a JSONL manifest file.

        Args:
            manifest_path: Path to JSONL file with prompt entries
            concurrency: Number of parallel jobs

        Returns:
            List of ImageGenResults
        """
        try:
            with open(manifest_path, "r") as f:
                entries = [json.loads(line) for line in f if line.strip()]
        except Exception as e:
            return [
                ImageGenResult(
                    status="error",
                    error=f"Failed to read manifest: {e}")]

        semaphore = asyncio.Semaphore(concurrency)

        async def _process_entry(entry: dict) -> ImageGenResult:
            async with semaphore:
                config = ImageGenConfig(
                    prompt=entry.get("prompt", ""),
                    model=entry.get("model", DEFAULT_MODEL),
                    size=entry.get("size", DEFAULT_SIZE),
                    quality=entry.get("quality", DEFAULT_QUALITY),
                    output_path=entry.get("output"),
                )
                return await self.generate(config)

        tasks = [_process_entry(e) for e in entries]
        results = await asyncio.gather(*tasks)
        return list(results)

    # --- Chroma-Key Background Removal ---
    async def remove_chroma_key(
            self,
            input_path: str,
            output_path: Optional[str] = None) -> ImageGenResult:
        """
        Remove a flat chroma-key background from a generated image.

        Args:
            input_path: Path to the source image (should have solid chroma-key bg)
            output_path: Output path (auto-generated if not provided)

        Returns:
            ImageGenResult with alpha-channel PNG
        """
        if not CHROMA_KEY_REMOVER.exists():
            return ImageGenResult(
                status="error",
                error=f"Chroma-key remover not found at {CHROMA_KEY_REMOVER}",
            )

        out = output_path or str(Path(input_path).with_suffix(".png"))

        cmd = [
            "python", str(CHROMA_KEY_REMOVER),
            "--input", input_path,
            "--out", out,
            "--auto-key", "border",
            "--soft-matte",
            "--transparent-threshold", "12",
            "--opaque-threshold", "220",
            "--despill",
        ]

        logger.info(f"ImageGen: Removing chroma-key from {input_path}...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                logger.info(f"ImageGen: Chroma-key removed. Output at {out}")
                return ImageGenResult(
                    status="success",
                    output_path=out,
                )
            else:
                error_msg = stderr.decode().strip()
                logger.warning(
                    f"ImageGen: Chroma-key removal failed: {error_msg}")
                return ImageGenResult(
                    status="error",
                    error=error_msg,
                )
        except FileNotFoundError:
            return ImageGenResult(
                status="error",
                error=f"Chroma-key remover not found at {CHROMA_KEY_REMOVER}",
            )

    # --- Prompt Engineering Helper ---
    @staticmethod
    def augment_prompt(raw_prompt: str, use_case: str = "general") -> str:
        """
        Normalize a raw prompt into a clean spec following prompting best practices.

        Structure: scene/backdrop -> subject -> key details -> constraints -> output intent

        Args:
            raw_prompt: User's raw prompt
            use_case: One of 'general', 'photorealistic', 'ui_mockup', 'infographic', 'concept_art'

        Returns:
            Augmented prompt string
        """
        # Base structure normalization
        augmented = raw_prompt.strip()

        if use_case == "photorealistic":
            augmented += ", photorealistic, detailed textures, natural lighting"
        elif use_case == "ui_mockup":
            augmented += ", clean UI mockup, negative space for copy, modern design"
        elif use_case == "infographic":
            augmented += ", infographic style, clear hierarchy, data visualization"
        elif use_case == "concept_art":
            augmented += ", concept art, dramatic lighting, detailed environment"

        return augmented

    # --- Model Selection Helper ---
    @staticmethod
    def recommend_model(use_case: str) -> str:
        """
        Recommend the best GPT Image model for a use case.

        Args:
            use_case: One of 'generation', 'editing', 'transparency', 'batch', 'draft'

        Returns:
            Model name (gpt-image-2, gpt-image-1.5, etc.)
        """
        recommendations = {
            "generation": "gpt-image-2",
            "editing": "gpt-image-2",
            # Only gpt-image-1.5 supports background=transparent
            "transparency": "gpt-image-1.5",
            "batch": "gpt-image-1-mini",  # Cost-sensitive drafts
            "draft": "gpt-image-2",  # Use --quality low for drafts
        }
        return recommendations.get(use_case, DEFAULT_MODEL)


# --- Singleton instance for SwarmOrchestrator integration ---
_agent_instance: Optional[ImageGenAgent] = None


def get_imagegen_agent() -> ImageGenAgent:
    """Get or create the singleton ImageGenAgent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ImageGenAgent()
    return _agent_instance
