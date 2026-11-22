import sqlite3
import os
import time
import threading
import unittest

class TestSandboxSQLiteWAL(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sandbox", "db")
        os.makedirs(self.test_dir, exist_ok=True)
        self.db_path = os.path.join(self.test_dir, f"test_wal_{int(time.time() * 1000)}.db")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER,
                topic TEXT,
                payload TEXT,
                created_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        for ext in ["", "-wal", "-shm"]:
            path = self.db_path + ext
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA mmap_size = 1073741824;") # 1GB test mmap
        conn.execute("PRAGMA cache_size = -16000;")     # 16MB cache
        conn.execute("PRAGMA busy_timeout = 10000;")
        return conn

    def test_concurrent_wal_writes(self):
        num_workers = 32
        rows_per_worker = 100
        errors = []

        def worker_task(worker_id):
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                for i in range(rows_per_worker):
                    cursor.execute(
                        "INSERT INTO test_telemetry (worker_id, topic, payload, created_at) VALUES (?, ?, ?, ?)",
                        (worker_id, f"topic_{worker_id}", f"data_payload_{i}", time.time())
                    )
                conn.commit()
                conn.close()
            except Exception as e:
                errors.append(f"Worker {worker_id} failed: {e}")

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(num_workers)]
        
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start_time

        self.assertEqual(len(errors), 0, f"Errors occurred during concurrent writes: {errors}")

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_telemetry")
        total_rows = cursor.fetchone()[0]
        conn.close()

        expected_rows = num_workers * rows_per_worker
        self.assertEqual(total_rows, expected_rows)
        print(f"\n[PASS] Concurrent WAL Benchmark: {total_rows} rows inserted in {elapsed:.3f}s ({total_rows/elapsed:.1f} writes/sec across {num_workers} threads)")

if __name__ == "__main__":
    unittest.main()
