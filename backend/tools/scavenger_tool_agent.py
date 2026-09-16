import os
import glob
import time
from .tool_registry import ToolRegistry, SANDBOX_DIR


class ScavengerToolAgent:
    def __init__(self):
        self.sandbox_path = SANDBOX_DIR

    def run_sweep_and_repair(self):
        """Scans sandbox for broken files/error logs and attempts repair using ToolRegistry."""
        print("[ScavengerToolAgent] Sweep disabled per user request to prevent infinite loops.")
        return {"status": "success", "message": "Scavenger Engine disabled. No repairs attempted."}
