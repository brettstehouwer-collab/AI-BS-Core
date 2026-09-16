import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Ensure the backend directory is in the path so we can import Vault_Auto_Scanner
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Vault_Auto_Scanner import scan_and_ingest, ALLOWED_EXTENSIONS


class VaultIngestionHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.cooldowns = {}

    def on_created(self, event):
        if not event.is_directory:
            self.handle_file_event(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.handle_file_event(event.src_path)

    def handle_file_event(self, filepath):
        # Debounce to prevent multiple fires for the same file save operation
        current_time = time.time()
        if filepath in self.cooldowns and current_time - self.cooldowns[filepath] < 5:
            return

        ext = os.path.splitext(filepath)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            print(f"[Watchdog] Triggered on {filepath}")
            self.cooldowns[filepath] = current_time

            # Use the existing scan_and_ingest logic, but give it a single file path
            # To do this safely with scan_and_ingest (which expects a directory),
            # we need to pass the directory of the file and ensure it only scans that dir...
            # Actually, we can just pass the parent directory, but that might rescan everything.
            # Instead, let's call the logic directly:
            from Vault_Auto_Scanner import (
                classify_content,
                VAULTS_DIR,
                MAX_FILE_SIZE_BYTES,
            )
            import shutil

            try:
                if not os.path.exists(filepath):
                    return
                if os.path.getsize(filepath) > MAX_FILE_SIZE_BYTES:
                    return

                # We add a small delay to ensure the file handle is released by the writer
                time.sleep(1)

                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    snippet = f.read(2000)

                target_vault = classify_content(snippet)
                if target_vault:
                    vault_path = os.path.join(VAULTS_DIR, target_vault)
                    os.makedirs(vault_path, exist_ok=True)
                    filename = os.path.basename(filepath)
                    dest_file = os.path.join(vault_path, filename)

                    if os.path.exists(dest_file):
                        base, extension = os.path.splitext(filename)
                        dest_file = os.path.join(
                            vault_path, f"{base}_{int(time.time())}{extension}"
                        )

                    shutil.copy2(filepath, dest_file)
                    print(
                        f"[Watchdog INGESTED] Auto-ingested {filename} -> {target_vault}/"
                    )
            except Exception as e:
                print(f"[Watchdog ERROR] Failed to auto-ingest {filepath}: {e}")


def start_watchdog():
    documents_folder = os.path.join(os.path.expanduser("~"), "Documents")
    paths_to_watch = [documents_folder]

    event_handler = VaultIngestionHandler()
    observer = Observer()

    for path in paths_to_watch:
        if os.path.exists(path):
            print(f"[Watchdog] Starting continuous monitoring on: {path}")
            observer.schedule(event_handler, path, recursive=True)

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    start_watchdog()
