"""AI-BS Native Studio: pure native Windows desktop shell for the AI-BS ecosystem.

Zero browser engines, zero local web servers. PyQt6 widgets on the GUI thread,
all heavy work on QThreadPool workers (see engine.py).
"""

__all__ = ["__version__"]


def _read_version() -> str:
    from pathlib import Path
    import sys

    try:
        if getattr(sys, 'frozen', False):
            # A packaged binary must report the version included when it was built.
            version_path = Path(sys._MEIPASS) / 'version.txt'
        else:
            version_path = Path(r"C:\AI-BS\version.txt")
        return version_path.read_text(encoding="utf-8").strip().lstrip("v") or "0.0.0"
    except OSError:
        return "0.0.0"


__version__ = _read_version()
