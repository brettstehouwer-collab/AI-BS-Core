"""WASAPI Exclusive audio kernel entry point (backend/native).

The implementation lives in ``native_studio/audio_kernel.py`` so it ships inside
the PyInstaller bundle. This module re-exports it and offers a CLI latency test:

    python backend/native/wasapi_audio_kernel.py [blocksize]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from native_studio.audio_kernel import (  # noqa: E402,F401
    AudioEngine,
    EngineStats,
    SpscRing,
    measure_roundtrip,
    register_mmcss,
)

if __name__ == "__main__":
    bs = int(sys.argv[1]) if len(sys.argv) > 1 else 64
    print(json.dumps(measure_roundtrip(blocksize=bs), indent=2))
