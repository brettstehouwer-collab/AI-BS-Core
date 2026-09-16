"""
AI-BS Sovereign Runtime Customizer.
Automatically loaded by Python when executed in C:\\AI-BS.
Injects core sovereign helper functions into builtins for seamless script and REPL execution.
"""

import builtins
import sys
import os

def _lazy_generate_comfy_image(prompt: str, *args, **kwargs):
    ai_bs_root = os.path.dirname(os.path.abspath(__file__))
    if ai_bs_root not in sys.path:
        sys.path.insert(0, ai_bs_root)
    from backend.tools.tool_registry import generate_comfy_image
    return generate_comfy_image(prompt, *args, **kwargs)

# Inject into builtins so `generate_comfy_image(...)` never throws NameError in any Python process
if not hasattr(builtins, "generate_comfy_image"):
    setattr(builtins, "generate_comfy_image", _lazy_generate_comfy_image)
