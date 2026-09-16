import os
import sys
import time
import sqlite3
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "sandbox_scratch", "ipc_benchmark"
    )
)

try:
    from shm_bridge import ShmBridge, TOPIC_ZERO_COPY_VECTOR_TENSORS, FLAG_HIGH_PRIORITY
except ImportError:
    TOPIC_ZERO_COPY_VECTOR_TENSORS = 0x0005
    FLAG_HIGH_PRIORITY = 0x02

    class ShmBridge:
        def init_shm_bridge(self):
            return 0

        def push_topic_event(self, topic, flags, data):
            return 0

        def close_shm_bridge(self):
            pass


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [OmniDriveWatcher] - %(message)s"
)

DB_PATH = os.path.join(os.path.dirname(__file__), "state.db")


class OmniDriveWatchHandler(FileSystemEventHandler):
    def __init__(self, bridge):
        self.bridge = bridge

    def on_created(self, event):
        if not event.is_directory and not any(
            x in event.src_path
            for x in ["node_modules", ".git", "__pycache__", ".venv", "dist"]
        ):
            self.index_file(event.src_path, "CREATE")

    def on_modified(self, event):
        if not event.is_directory and not any(
            x in event.src_path
            for x in ["node_modules", ".git", "__pycache__", ".venv", "dist"]
        ):
            self.index_file(event.src_path, "MODIFY")

    def on_deleted(self, event):
        if not event.is_directory and not any(
            x in event.src_path
            for x in ["node_modules", ".git", "__pycache__", ".venv", "dist"]
        ):
            self.remove_index(event.src_path)

    def index_file(self, filepath, action):
        try:
            filename = os.path.basename(filepath)
            ext = os.path.splitext(filename)[1]
            size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            mtime = (
                os.path.getmtime(filepath) if os.path.exists(filepath) else time.time()
            )

            conn = sqlite3.connect(DB_PATH)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO omnidrive_index (filepath, filename, extension, size_bytes, last_modified)
                VALUES (?, ?, ?, ?, ?)
            """,
                (filepath, filename, ext, size, mtime),
            )
            conn.commit()
            conn.close()

            payload = f"OMNI_DELTA|ACT:{action}|FILE:{filename[:15]}|SIZE:{size}"
            self.bridge.push_topic_event(
                TOPIC_ZERO_COPY_VECTOR_TENSORS, FLAG_HIGH_PRIORITY, payload
            )
        except Exception as e:
            pass

    def remove_index(self, filepath):
        try:
            filename = os.path.basename(filepath)
            conn = sqlite3.connect(DB_PATH)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM omnidrive_index WHERE filepath = ?", (filepath,)
            )
            conn.commit()
            conn.close()

            payload = f"OMNI_DELTA|ACT:DELETE|FILE:{filename[:15]}"
            self.bridge.push_topic_event(
                TOPIC_ZERO_COPY_VECTOR_TENSORS, FLAG_HIGH_PRIORITY, payload
            )
        except Exception as e:
            pass


def start_watcher(path_to_watch):
    bridge = ShmBridge()
    bridge.init_shm_bridge()
    event_handler = OmniDriveWatchHandler(bridge)
    observer = Observer()
    observer.schedule(event_handler, path=path_to_watch, recursive=True)
    observer.start()
    logging.info(f"👁️ OmniDrive Watchdog active on '{path_to_watch}'")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    bridge.close_shm_bridge()


if __name__ == "__main__":
    target = os.path.dirname(os.path.dirname(__file__))
    start_watcher(target)
