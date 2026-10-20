#!/usr/bin/env python3
"""
Standalone CLI and Script Entrypoint for ComfyUI Image Generation in AI-BS.
Usage:
    python scripts/generate_comfy_image.py "A futuristic neon server room"
    python scripts/generate_comfy_image.py "A medieval castle" --negative "blurry, low quality"
    python scripts/generate_comfy_image.py "A cinematic scene" --open
"""

import os
import sys
import argparse
import json

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure AI-BS root and backend are in Python path
AI_BS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(AI_BS_ROOT, "backend")
for p in [AI_BS_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.tools.tool_registry import generate_comfy_image

def main():
    parser = argparse.ArgumentParser(
        description="Generate images or videos directly via AI-BS ComfyUI (Port 8189)."
    )
    parser.add_argument(
        "prompt",
        type=str,
        nargs="?",
        default="futuristic AI server matrix room with glowing holographic circuitry",
        help="Visual prompt describing the image to generate",
    )
    parser.add_argument(
        "--negative",
        "-n",
        type=str,
        default="",
        help="Negative prompt to suppress undesired attributes",
    )
    parser.add_argument(
        "--video",
        action="store_true",
        help="Generate a short video clip instead of a static image",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open the output image once generated",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON execution payload",
    )

    args = parser.parse_args()

    print(f"🎨 [AI-BS Image Engine] Dispatching generation request to ComfyUI...")
    print(f"   ► Prompt: {args.prompt}")
    if args.negative:
        print(f"   ► Negative: {args.negative}")

    try:
        result = generate_comfy_image(
            prompt=args.prompt,
            negative_prompt=args.negative,
            video=args.video,
        )

        if result.get("status") == "success":
            filename = result.get("filename", "unknown")
            output_dir = os.path.join(AI_BS_ROOT, "ComfyUI", "output")
            local_file_path = os.path.join(output_dir, filename)

            print(f"\n✅ Generation Successful!")
            print(f"   ► File Name: {filename}")
            print(f"   ► Local Path: {local_file_path}")
            print(f"   ► Checkpoint: {result.get('checkpoint_used')}")
            print(f"   ► Prompt ID: {result.get('prompt_id')}")

            if args.open and os.path.exists(local_file_path):
                os.startfile(local_file_path)

            if args.json:
                print(json.dumps(result, indent=2))

            return 0
        else:
            print(f"\n❌ Generation Failed: {result.get('message', 'Unknown error')}")
            if args.json:
                print(json.dumps(result, indent=2))
            return 1

    except Exception as e:
        print(f"\n💥 Execution Exception: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
