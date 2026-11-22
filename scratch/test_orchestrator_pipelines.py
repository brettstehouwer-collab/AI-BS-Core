import sys
import os
import asyncio

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure backend directory is in sys.path
backend_dir = r"C:\AI-BS\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from bullshit_orchestrator import SwarmOrchestrator

async def main():
    print("[TEST] Initializing SwarmOrchestrator test...")
    orchestrator = SwarmOrchestrator()

    # 1. Test Audio Routing
    print("\n--- TEST 1: Audio Generation Routing ---")
    audio_res = await orchestrator.delegate_task("Synthesize an edm synth track with energetic beats", "Core_Architect")
    print(f"Audio Result: {audio_res}")

    # 2. Test Video Routing
    print("\n--- TEST 2: Video Generation Routing ---")
    video_res = await orchestrator.delegate_task("Render a video clip showing dynamic motion in a neon city", "Core_Architect")
    print(f"Video Result: {video_res}")

    # 3. Test Code_Debugger Self-Healing Routing
    print("\n--- TEST 3: Code_Debugger Self-Healing Routing ---")
    code_res = await orchestrator.delegate_task("Fix syntax error and debug exception in python script", "Core_Architect")
    print(f"Code Debugger Result: {code_res}")

if __name__ == "__main__":
    asyncio.run(main())
