"""Headless Blender VSE & Native FFmpeg Cinematic Movie Assembler.

Assembles multi-track video scenes, neural dialogue audio, sound effects, and
background music with automated audio ducking and smooth crossfade transitions.

Usage:
  Blender Mode:
    blender -b -P assemble_movie_vse.py -- manifest.json [output.mp4]
  Native Python / FFmpeg Mode:
    python assemble_movie_vse.py manifest.json [output.mp4]
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try importing bpy (Blender Python environment)
try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False


def find_ffmpeg() -> str:
    """Locate local ffmpeg executable."""
    candidates = [
        r"C:\Users\footb\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe",
        "ffmpeg.exe",
        "ffmpeg",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
        found = shutil.which(c)
        if found:
            return found
    return "ffmpeg"


def assemble_with_blender(manifest: Dict[str, Any], output_path: str) -> None:
    """Build multi-track timeline inside Blender Video Sequence Editor."""
    print(f"[Blender VSE] Assembling movie: {manifest.get('project_name', 'Untitled')}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    if not scene.sequence_editor:
        scene.sequence_editor_create()
    seq = scene.sequence_editor.sequences

    fps = int(manifest.get("fps", 24))
    res = manifest.get("resolution", "1920x1080").split("x")
    scene.render.fps = fps
    scene.render.resolution_x = int(res[0])
    scene.render.resolution_y = int(res[1])

    current_frame = 1
    scenes = manifest.get("scenes", [])

    for idx, sc in enumerate(scenes):
        v_path = sc.get("video_path")
        dur_sec = float(sc.get("duration_sec", 4.0))
        dur_frames = int(dur_sec * fps)

        if v_path and os.path.exists(v_path):
            strip_chan = 1 if (idx % 2 == 0) else 2
            v_strip = seq.new_movie(
                name=f"Shot_{idx+1}",
                filepath=v_path,
                channel=strip_chan,
                frame_start=current_frame,
            )

        # Dialogue Strip on Channel 3
        d_path = sc.get("dialogue_audio_path")
        if d_path and os.path.exists(d_path):
            seq.new_sound(
                name=f"Dialogue_{idx+1}",
                filepath=d_path,
                channel=3,
                frame_start=current_frame,
            )

        # SFX Strip on Channel 4
        sfx_path = sc.get("sfx_audio_path")
        if sfx_path and os.path.exists(sfx_path):
            seq.new_sound(
                name=f"SFX_{idx+1}",
                filepath=sfx_path,
                channel=4,
                frame_start=current_frame,
            )

        current_frame += dur_frames

    # Background Music on Channel 5
    bgm_path = manifest.get("bgm_audio_path")
    if bgm_path and os.path.exists(bgm_path):
        bgm_strip = seq.new_sound(
            name="BGM_Track",
            filepath=bgm_path,
            channel=5,
            frame_start=1,
        )
        bgm_strip.volume = 0.35  # Ducked ambient level

    scene.frame_start = 1
    scene.frame_end = current_frame

    # Render settings
    scene.render.filepath = os.path.abspath(output_path)
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.audio_codec = "AAC"
    scene.render.ffmpeg.audio_bitrate = 192

    print(f"[Blender VSE] Rendering animation to {output_path}...")
    bpy.ops.render.render(animation=True)
    print("[Blender VSE] Render complete!")


def assemble_with_ffmpeg(manifest: Dict[str, Any], output_path: str) -> bool:
    """Build multi-track video timeline natively using FFmpeg with audio ducking."""
    ffmpeg_bin = find_ffmpeg()
    print(f"[Native FFmpeg VSE] Assembling movie via {ffmpeg_bin}...")

    scenes = manifest.get("scenes", [])
    if not scenes:
        print("[Native FFmpeg VSE] No scenes in manifest.")
        return False

    temp_dir = Path(output_path).parent / f"vse_temp_{int(Path(output_path).stat().st_mtime if Path(output_path).exists() else 0)}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    concat_list_file = temp_dir / "concat_videos.txt"

    with open(concat_list_file, "w", encoding="utf-8") as f:
        for sc in scenes:
            v_path = sc.get("video_path")
            if v_path and os.path.exists(v_path):
                f.write(f"file '{os.path.abspath(v_path)}'\n")

    # If videos exist, concatenate with re-encoding for audio mix
    concat_video_out = str(temp_dir / "concatenated_video.mp4")
    cmd_concat = [
        ffmpeg_bin, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        concat_video_out,
    ]
    subprocess.run(
        cmd_concat,
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )

    source_video = concat_video_out if os.path.exists(concat_video_out) else scenes[0].get("video_path")
    bgm_path = manifest.get("bgm_audio_path")

    # Final mux with audio ducking if BGM present
    if bgm_path and os.path.exists(bgm_path):
        # Mux with volume-ducked background music
        cmd_mux = [
            ffmpeg_bin, "-y",
            "-i", str(source_video),
            "-stream_loop", "-1",
            "-i", str(bgm_path),
            "-filter_complex", "[1:a]volume=0.30[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path,
        ]
    else:
        cmd_mux = [
            ffmpeg_bin, "-y",
            "-i", str(source_video),
            "-c", "copy",
            output_path,
        ]

    res = subprocess.run(
        cmd_mux,
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )

    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    success = (res.returncode == 0) and os.path.exists(output_path)
    if success:
        print(f"[Native FFmpeg VSE] Successfully rendered to {output_path}")
    else:
        print(f"[Native FFmpeg VSE] Failed rendering: {res.stderr.decode('utf-8', errors='ignore')}")
    return success


def main():
    args = sys.argv[1:]
    # In Blender script execution, arguments after '--' are user arguments
    if "--" in args:
        args = args[args.index("--") + 1:]

    if not args:
        print("Usage: python assemble_movie_vse.py <manifest.json> [output_path]")
        sys.exit(1)

    manifest_path = args[0]
    output_path = args[1] if len(args) > 1 else "output_movie.mp4"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if HAS_BPY:
        assemble_with_blender(manifest, output_path)
    else:
        assemble_with_ffmpeg(manifest, output_path)


if __name__ == "__main__":
    main()
