# =========================================================================
# AI-BS Sovereign Intelligence Ecosystem - Tap-To-Run Canvas Test Suite
# File: C:\AI-BS\backend\test_tap_to_run_canvas.py
# Description: Automated regression verification for click-gated execution,
#              sprite synthesis, display flip monkey-patch, and process lifecycle
# =========================================================================

import os
import sys
import time
import pytest
import asyncio
from pathlib import Path

# Add backend directory to path
backend_dir = r"C:\AI-BS\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import canvas_daemon
from canvas_daemon import (
    CanvasExecRequest,
    ensure_neon_chess_assets,
    execute_on_tap,
    stop_canvas,
    get_canvas_status,
    get_canvas_frame,
    DEFAULT_TARGET_DIR
)


def test_canvas_exec_request_model():
    """Verify CanvasExecRequest model fields and defaults."""
    req = CanvasExecRequest(
        label="Animated Chess Game",
        target_dir=DEFAULT_TARGET_DIR,
        bash_commands=["mkdir C:\\AI-BS\\backend\\chess\\animated_chess"],
        python_scripts=["import pygame\nprint('staged')"]
    )
    assert req.label == "Animated Chess Game"
    assert req.target_dir == DEFAULT_TARGET_DIR
    assert len(req.bash_commands) == 1
    assert len(req.python_scripts) == 1


def test_ensure_neon_chess_assets():
    """Verify automated sprite synthesizer creates piece PNGs without FileNotFoundError."""
    test_dir = os.path.join(DEFAULT_TARGET_DIR, "test_sprites")
    os.makedirs(test_dir, exist_ok=True)
    count = ensure_neon_chess_assets(test_dir)
    assert count >= 16

    img_dir = os.path.join(test_dir, "images")
    assert os.path.isdir(img_dir)
    for piece in ["wK.png", "wQ.png", "bK.png", "bQ.png", "bP.png", "wP.png"]:
        piece_path = os.path.join(img_dir, piece)
        assert os.path.exists(piece_path), f"Missing piece sprite: {piece}"
        assert os.path.getsize(piece_path) > 100


def test_execute_on_tap_lifecycle():
    """
    Verify complete click-gated execution lifecycle:
    1. Passive until execute_on_tap is called.
    2. Provisions assets and injects _stream_flip hook.
    3. Spawns headless SDL2 process and returns live PID.
    4. Generates _frame.bmp.
    5. Stops cleanly upon stop_canvas call.
    """
    async def _run():
        test_script = """
import os
import time
import pygame

pygame.init()
screen = pygame.display.set_mode((400, 400))
for i in range(15):
    screen.fill((0, 255, 255))
    pygame.draw.circle(screen, (255, 0, 128), (200, 200), 50)
    pygame.display.flip()
    time.sleep(0.05)
pygame.quit()
"""

        req = CanvasExecRequest(
            label="Test Tap Canvas",
            target_dir=DEFAULT_TARGET_DIR,
            bash_commands=[],
            python_scripts=[test_script]
        )

        # 1. Execute on tap
        res = await execute_on_tap(req)
        assert res["status"] == "running"
        assert res["pid"] is not None
        assert os.path.exists(res["script"])

        # 2. Check status while running
        status = await get_canvas_status()
        assert status["status"] == "running"
        assert status["pid"] == res["pid"]

        # 3. Wait briefly for _stream_flip to write _frame.bmp
        frame_path = os.path.join(DEFAULT_TARGET_DIR, "_frame.bmp")
        for _ in range(25):
            if os.path.exists(frame_path):
                break
            await asyncio.sleep(0.1)

        assert os.path.exists(frame_path), "Expected _frame.bmp to be written by _stream_flip hook"

        # 4. Check fallback frame HTTP response
        frame_resp = await get_canvas_frame()
        assert frame_resp.media_type == "image/jpeg"
        assert len(frame_resp.body) > 500

        # 5. Stop process
        stop_res = await stop_canvas()
        assert stop_res["status"] == "terminated"

        # 6. Verify status is idle after stop
        post_status = await get_canvas_status()
        assert post_status["status"] == "idle"
        assert post_status["pid"] is None

    asyncio.run(_run())


def test_token_extraction_regex():
    """Verify that [Run <Label>] tokens are correctly captured."""
    import re
    msg = (
        "Here is the animated chess game:\n\n"
        "```python\nimport pygame\nprint('chess')\n```\n\n"
        "[Run Animated Chess Game]\n\n"
        "Tap the button above to launch."
    )
    match = re.search(r"\[Run\s+([^\]]+)\]", msg)
    assert match is not None
    assert match.group(1).strip() == "Animated Chess Game"

    # Verify segmentation
    parts = re.split(r"(\[Run\s+[^\]]+\])", msg)
    assert len(parts) == 3
    assert parts[1] == "[Run Animated Chess Game]"
