import os
import sys
import time
import subprocess
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("TunnelManager")
logger.setLevel(logging.INFO)


class TunnelManager:
    """Manages Cloudflare Zero-Trust Tunnels for public exposure without opening ports."""

    @staticmethod
    def is_cloudflared_installed() -> bool:
        """Check if cloudflared CLI is installed in PATH."""
        try:
            res = subprocess.run(
                ["cloudflared", "--version"], capture_output=True, text=True
            )
            return res.returncode == 0
        except FileNotFoundError:
            return False

    @classmethod
    def get_status(cls, port: int = 8000) -> Dict[str, Any]:
        """Return status of local cloudflared tunnel service."""
        installed = cls.is_cloudflared_installed()
        return {
            "installed": installed,
            "target_port": port,
            "target_url": f"http://localhost:{port}",
            "recommended_command": f"cloudflared tunnel --url http://localhost:{port}",
        }
