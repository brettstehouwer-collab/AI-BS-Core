"""Explicit lifecycle permissions for the native client.

The gateway supervisor owns services by default. Opening or closing a client
must not start every daemon or terminate unrelated processes.
"""
import os
from pathlib import Path
import sys


def configure_frozen_dependencies() -> None:
    """Expose only packaged pywin32 subdirectories to the frozen interpreter.

    PyInstaller preserves these extension directories. Ordinary Python finds
    them through pywin32.pth, which is not processed by the frozen interpreter.
    No installed Python or repository directory is added here.
    """
    if not getattr(sys, 'frozen', False):
        return
    root = Path(sys._MEIPASS)
    if not root.is_absolute() or not root.is_dir():
        raise RuntimeError('The packaged dependency directory is unavailable.')
    paths = []
    for child in [root, *(root / name for name in ('win32', 'pythonwin', 'pywin32_system32'))]:
        if any(p.is_symlink() or p.is_junction() for p in [child, *child.parents]):
            raise RuntimeError('A packaged dependency directory is redirected.')
        if child.is_dir():
            resolved = child.resolve(strict=True)
            if not resolved.is_relative_to(root.resolve(strict=True)):
                raise RuntimeError('A packaged dependency directory escaped its root.')
            if child != root:
                paths.append(str(child))
    for path in paths:
        if path not in sys.path:
            sys.path.append(path)


def allow_background_daemon_management() -> bool:
    return os.environ.get('AI_BS_NATIVE_MANAGE_DAEMONS', '').strip().lower() == 'true'


def allow_exit_process_cleanup() -> bool:
    return os.environ.get('AI_BS_NATIVE_EXIT_PROCESS_CLEANUP', '').strip().lower() == 'true'


def allow_background_update_checks() -> bool:
    return os.environ.get('AI_BS_NATIVE_BACKGROUND_UPDATES', '').strip().lower() == 'true'
