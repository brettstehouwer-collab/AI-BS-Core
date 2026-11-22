"""AI-BS Granian (Rust ASGI) High-Performance Server Launcher.

Replaces standard Uvicorn with Granian (Rust/Tokio) for maximum request-per-second throughput,
zero-overhead concurrent WebSocket telemetry broadcasting, and multi-threaded Tokio event loops.
Automatically falls back to Uvicorn if Granian is not installed or encounters environment issues.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(r"C:\AI-BS\backend")
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("AIBS_Granian_Launcher")

PORT = int(os.environ.get("AIBS_CORE_PORT", 8080))
HOST = os.environ.get("AIBS_CORE_HOST", "127.0.0.1")


def launch_server() -> None:
    """Launches FastAPI Core using Granian (Rust ASGI) with transparent Uvicorn fallback."""
    logger.info("==================================================")
    logger.info(f"AI-BS FastAPI Core Engine Launcher (Port {PORT})")
    logger.info("Target: Rust/Tokio ASGI Server (Granian)")
    logger.info("==================================================")

    # 1. Try Granian
    try:
        from granian import Granian
        from granian.constants import Interfaces, HTTPModes

        logger.info(f"⚡ Booting Granian (Rust/Tokio) on {HOST}:{PORT}...")
        server = Granian(
            target="AI_BS_Backend:app",
            address=HOST,
            port=PORT,
            interface=Interfaces.ASGI,
            http=HTTPModes.auto,
            websockets=True,
            workers=1,
            threads=4,
            log_enabled=True,
        )
        server.serve()
        return
    except ImportError:
        logger.info("Granian (Rust ASGI) package not found in active environment.")
    except Exception as e:
        logger.warning(f"Granian encountered an error during initialization: {e}")

    # 2. Seamless Fallback to Uvicorn
    logger.info(f"🔄 Seamlessly falling back to Uvicorn ASGI on {HOST}:{PORT}...")
    try:
        import uvicorn
        from AI_BS_Backend import app

        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    except Exception as ex:
        logger.error(f"Failed to start ASGI core server: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    launch_server()
