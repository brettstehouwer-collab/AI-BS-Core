"""Read-only persisted-index inspection without loading Chroma/native clients.

Usage: python scripts/inspect_chroma_store.py --store C:\\AI-BS\\chroma_db
Exit0: known static checks pass; exit2: corrupt; exit3: unverified/unsupported.
Static checks do not establish SQLite integrity, native health or full recovery.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def _inspect_store(path):
    # Load only the inert inspector, without importing the application package.
    module_path = Path(__file__).resolve().parents[1] / "backend/core/chroma_native_integrity.py"
    spec = importlib.util.spec_from_file_location("aibs_chroma_native_inspector", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inspect_chroma_store(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, help="Existing store directory; never created or repaired")
    args = parser.parse_args(argv)
    # Importing this diagnostic must not create bytecode in the source tree.
    previous_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        result = _inspect_store(args.store)
    except Exception as error:
        result = {
            "status": "UNVERIFIED",
            "reason": "INSPECTOR_FAILURE",
            "error_type": type(error).__name__,
            "native_runtime_tested": False,
            "sqlite_opened": False,
            "data_recovery_complete": False,
        }
    finally:
        sys.dont_write_bytecode = previous_bytecode
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["status"] == "STATIC_CHECKS_PASS" else 2 if result["status"] == "CORRUPT" else 3


if __name__ == "__main__":
    raise SystemExit(main())
