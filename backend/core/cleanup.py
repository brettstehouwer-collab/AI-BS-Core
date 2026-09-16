import os
import shutil
from pathlib import Path
import argparse


def cleanup_project(project_path: Path, dry_run: bool):
    """
    Removes build artifacts, logs, and caches from a project directory.
    """
    if not project_path.exists():
        print(f"[INFO] Directory not found, skipping: {project_path}")
        return

    print(f"\n--- Scanning: {project_path} ---")

    # Patterns to delete recursively
    patterns_to_delete = [
        "build",
        "dist",
        "release",
        "build-output",
        "win-unpacked",
        "*.egg-info",
        "__pycache__",
        ".vite",
        "matrix_installer",
    ]

    # Specific files to delete from the root
    files_to_delete_in_root = [
        "*.spec",
        "*.pid",
    ]

    # Log files in the logs directory
    logs_to_delete = ["logs/*.log"]

    # Sandbox content
    sandboxes_to_clean = ["sandbox", "sandbox_scratch"]

    # Deleting patterns
    for pattern in patterns_to_delete:
        for path in project_path.rglob(pattern):
            if path.exists() and path.is_dir():
                print(f"Removing directory: {path}")
                if not dry_run:
                    shutil.rmtree(path, ignore_errors=True)

    # Deleting specific files
    for pattern in files_to_delete_in_root:
        for path in project_path.glob(pattern):
            if path.exists() and path.is_file():
                print(f"Removing file: {path}")
                if not dry_run:
                    os.remove(path)

    # Deleting logs
    log_dir = project_path / "logs"
    if log_dir.exists():
        for path in log_dir.glob("*.log"):
            if path.exists() and path.is_file():
                print(f"Removing log file: {path}")
                if not dry_run:
                    os.remove(path)

    # Cleaning sandboxes
    for sandbox_name in sandboxes_to_clean:
        sandbox_path = project_path / sandbox_name
        if sandbox_path.exists():
            print(f"Cleaning sandbox directory: {sandbox_path}")
            if not dry_run:
                for item in sandbox_path.iterdir():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            os.remove(item)
                    except Exception as e:
                        print(f"  [ERROR] Could not remove {item} from sandbox: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Clean AI-BS project directories for a fresh build."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting anything.",
    )
    args = parser.parse_args()

    print("==================================================")
    print("    AI-BS Matrix - Fresh Build Cleanup Tool")
    print("==================================================")
    if args.dry_run:
        print("\n*** DRY RUN MODE: No files will be deleted. ***")

    cleanup_project(Path("C:/Users/footb/AI-BS"), args.dry_run)
    cleanup_project(Path("C:/Users/footb/AI-BS_Matrix"), args.dry_run)

    print("\n--- Cleanup Complete ---")


if __name__ == "__main__":
    main()
