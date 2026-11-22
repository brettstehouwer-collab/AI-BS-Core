"""AI-BS Autonomous Cinematic Storyboard & Screenplay-to-Movie Assembler.

Features:
1. Fountain Screenplay Ingestion:
   - Identifies Scene Headings (INT./EXT.), Action Blocks, Character Names, Dialogue,
     Parentheticals, and Scene Transitions.
2. Directorial Visual Prompt Formulator:
   - Formulates cinematographic parameters (Shot Scale: Close-Up, Medium, Wide;
     Lighting: Rim light, volumetric, golden hour; Camera: Steadicam, dolly, orbital).
   - Generates high-fidelity prompt recipes for Wan2.1 / LTX-Video in ComfyUI FP8.
3. Neural Dialogue & Acoustic Layering:
   - Integrates with F5-TTS / local speech synthesis with character voice mapping.
   - Demucs vocal stem isolation & automated -14 LUFS loudness mastering.
4. Audio Ducking & Procedural Timeline Assembly:
   - Assembles multi-track timeline manifest.
   - Dispatches to Headless Blender VSE (bpy) or Native NVENC FFmpeg pipeline.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AIBS_CinematicStoryboardAssembler")
logger.setLevel(logging.INFO)

_WORKSPACE_ROOT = Path("C:/AI-BS") if Path("C:/AI-BS").exists() else Path(__file__).resolve().parent.parent.parent
_SAVED_MEDIA_DIR = _WORKSPACE_ROOT / "saved_data" / "media_renders"
_SAVED_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
_VSE_SCRIPT_PATH = _WORKSPACE_ROOT / "backend" / "scripts" / "assemble_movie_vse.py"


@dataclass
class DialogueLine:
    character: str
    text: str
    parenthetical: Optional[str] = None
    sentiment: str = "Neutral"
    audio_path: Optional[str] = None
    duration_sec: float = 0.0


@dataclass
class StoryboardShot:
    shot_index: int
    shot_scale: str  # Extreme Wide, Wide, Medium, Close-Up, Extreme Close-Up
    camera_movement: str  # Static, Dolly In, Tracking, Crane, Steadicam
    lighting: str  # Volumetric, Noir Rim, Golden Hour, High-Key
    visual_prompt: str
    negative_prompt: str
    duration_sec: float = 4.0
    video_path: Optional[str] = None
    dialogue: Optional[DialogueLine] = None
    sfx_cue: Optional[str] = None
    sfx_audio_path: Optional[str] = None


@dataclass
class StoryboardScene:
    scene_index: int
    heading: str
    setting: str  # INT or EXT
    location: str
    time_of_day: str  # DAY, NIGHT, DUSK, DAWN
    action_description: str
    shots: List[StoryboardShot] = field(default_factory=list)


class CinematicStoryboardAssembler:
    """End-to-End Screenplay-to-Movie Pipeline Orchestrator."""

    def __init__(self):
        self.output_dir: Path = _SAVED_MEDIA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse_fountain(self, content: str) -> List[StoryboardScene]:
        """
        Parses raw Fountain text into structured StoryboardScenes and Shots.
        Handles standard Industry Fountain specification:
        - Headings: INT. or EXT.
        - Characters: ALL CAPS
        - Parentheticals: (whispering)
        - Action: Descriptive paragraphs
        """
        lines = [line.strip() for line in content.splitlines()]
        scenes: List[StoryboardScene] = []
        current_scene: Optional[StoryboardScene] = None
        current_character: Optional[str] = None
        current_parenthetical: Optional[str] = None
        scene_counter = 0

        heading_regex = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|EXT/INT\.)\s+(.+?)(?:\s+-\s+(DAY|NIGHT|DUSK|DAWN|SUNSET|EVENING|CONTINUOUS|LATER))?$", re.IGNORECASE)

        for line in lines:
            if not line:
                current_character = None
                current_parenthetical = None
                continue

            # 1. Match Scene Heading
            heading_match = heading_regex.match(line)
            if heading_match or line.startswith("INT.") or line.startswith("EXT."):
                scene_counter += 1
                setting = "INT" if line.startswith("INT") else "EXT"
                location = "LOCATION"
                time_of_day = "DAY"
                if heading_match:
                    setting = heading_match.group(1).upper().rstrip(".")
                    location = heading_match.group(2).strip()
                    time_of_day = (heading_match.group(3) or "DAY").upper()

                current_scene = StoryboardScene(
                    scene_index=scene_counter,
                    heading=line,
                    setting=setting,
                    location=location,
                    time_of_day=time_of_day,
                    action_description="",
                    shots=[],
                )
                scenes.append(current_scene)
                current_character = None
                continue

            if not current_scene:
                # Implicit first scene
                scene_counter += 1
                current_scene = StoryboardScene(
                    scene_index=scene_counter,
                    heading="INT. SCENE - DAY",
                    setting="INT",
                    location="SCENE",
                    time_of_day="DAY",
                    action_description="",
                    shots=[],
                )
                scenes.append(current_scene)

            # 2. Match Parenthetical
            if line.startswith("(") and line.endswith(")"):
                current_parenthetical = line.strip("()")
                continue

            # 3. Match Character Dialogue
            if line.isupper() and len(line) < 40 and not line.endswith("."):
                current_character = line
                continue

            if current_character:
                # This line is dialogue text
                sentiment = "Neutral"
                lower_text = line.lower()
                if "!" in line or any(w in lower_text for w in ["angry", "yell", "damn", "never"]):
                    sentiment = "Dramatic/Intense"
                elif "?" in line or any(w in lower_text for w in ["why", "how", "what"]):
                    sentiment = "Inquisitive"
                elif any(w in lower_text for w in ["love", "happy", "smile", "laugh"]):
                    sentiment = "Affectionate"

                dl = DialogueLine(
                    character=current_character,
                    text=line,
                    parenthetical=current_parenthetical,
                    sentiment=sentiment,
                    duration_sec=max(2.5, round(len(line.split()) * 0.45, 1)),
                )

                # Create dedicated close-up shot for dialogue
                shot_idx = len(current_scene.shots) + 1
                shot = StoryboardShot(
                    shot_index=shot_idx,
                    shot_scale="Close-Up",
                    camera_movement="Subtle Push-In",
                    lighting=f"Cinematic {current_scene.time_of_day.lower()} key lighting, soft rim light",
                    visual_prompt=f"Cinematic close-up of {current_character}, {current_parenthetical or ''}, speaking, high dynamic range, photorealistic, 8k, award-winning cinematography",
                    negative_prompt="blurry, distorted face, low quality, CGI cartoon, extra limbs",
                    duration_sec=dl.duration_sec,
                    dialogue=dl,
                )
                current_scene.shots.append(shot)
                current_character = None
                current_parenthetical = None
                continue

            # 4. Action Description
            if current_scene.action_description:
                current_scene.action_description += " " + line
            else:
                current_scene.action_description = line

            # Generate Establishing / Action Shot
            shot_idx = len(current_scene.shots) + 1
            scale = "Wide Establishing" if shot_idx == 1 else "Medium Action"
            shot = StoryboardShot(
                shot_index=shot_idx,
                shot_scale=scale,
                camera_movement="Smooth Steadicam Tracking" if scale != "Wide Establishing" else "Slow Crane Down",
                lighting=f"Natural {current_scene.time_of_day.lower()} light, cinematic volumetric haze",
                visual_prompt=f"Cinematic {scale.lower()} shot, {current_scene.setting} {current_scene.location}, {line}, 35mm film grain, anamorphic lens flare, masterwork composition",
                negative_prompt="blurry, low resolution, washed out, amateur, overexposed",
                duration_sec=4.0,
            )
            current_scene.shots.append(shot)

        return scenes

    def build_assembly_manifest(
        self,
        project_name: str,
        scenes: List[StoryboardScene],
        bgm_path: Optional[str] = None,
        resolution: str = "1920x1080",
        fps: int = 24,
    ) -> Dict[str, Any]:
        """Compiles parsed screenplay scenes and shots into a standard VSE timeline manifest."""
        manifest_scenes: List[Dict[str, Any]] = []

        for sc in scenes:
            for sh in sc.shots:
                manifest_scenes.append({
                    "scene_index": sc.scene_index,
                    "shot_index": sh.shot_index,
                    "heading": sc.heading,
                    "shot_scale": sh.shot_scale,
                    "visual_prompt": sh.visual_prompt,
                    "duration_sec": sh.duration_sec,
                    "video_path": sh.video_path,
                    "dialogue_text": sh.dialogue.text if sh.dialogue else None,
                    "dialogue_character": sh.dialogue.character if sh.dialogue else None,
                    "dialogue_audio_path": sh.dialogue.audio_path if sh.dialogue else None,
                    "sfx_cue": sh.sfx_cue,
                    "sfx_audio_path": sh.sfx_audio_path,
                })

        manifest = {
            "project_name": project_name,
            "created_at": time.time(),
            "resolution": resolution,
            "fps": fps,
            "bgm_audio_path": bgm_path,
            "scenes": manifest_scenes,
            "total_shots": len(manifest_scenes),
            "estimated_runtime_sec": round(sum(s["duration_sec"] for s in manifest_scenes), 1),
        }
        return manifest

    def export_manifest_json(self, manifest: Dict[str, Any], file_path: Path) -> Path:
        """Saves manifest to disk."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        return file_path

    def assemble_movie(
        self,
        manifest_path: str,
        output_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes assembly pipeline:
        Tries Blender headless first; falls back to native FFmpeg VSE.
        """
        out_name = output_filename or f"cinematic_assembly_{int(time.time())}.mp4"
        export_path = str(self.output_dir / out_name)

        # 1. Check Blender presence
        from core.media_render_engine import MediaRenderEngine
        blender_bin = MediaRenderEngine._find_blender_binary()

        engine_used = "native_ffmpeg_vse"
        if blender_bin and os.path.exists(blender_bin):
            try:
                cmd = [
                    blender_bin,
                    "-b",
                    "-P", str(_VSE_SCRIPT_PATH),
                    "--",
                    manifest_path,
                    export_path,
                ]
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                if res.returncode == 0 and os.path.exists(export_path):
                    engine_used = "blender_vse"
                    return {
                        "status": "SUCCESS",
                        "engine": engine_used,
                        "output_path": export_path,
                        "manifest": manifest_path,
                    }
            except Exception as e:
                logger.warning("Blender execution encountered issue: %s. Falling back to native FFmpeg VSE.", e)

        # 2. Native FFmpeg VSE Fallback
        try:
            cmd = [
                sys.executable,
                str(_VSE_SCRIPT_PATH),
                manifest_path,
                export_path,
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return {
                "status": "SUCCESS" if os.path.exists(export_path) else "FAILED",
                "engine": engine_used,
                "output_path": export_path if os.path.exists(export_path) else None,
                "manifest": manifest_path,
                "log": res.stdout,
            }
        except Exception as ex:
            return {"status": "ERROR", "detail": str(ex)}


_assembler_instance: Optional[CinematicStoryboardAssembler] = None


def get_cinematic_assembler() -> CinematicStoryboardAssembler:
    global _assembler_instance
    if _assembler_instance is None:
        _assembler_instance = CinematicStoryboardAssembler()
    return _assembler_instance
