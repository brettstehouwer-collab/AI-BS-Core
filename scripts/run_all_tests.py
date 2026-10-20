import os
import sys
import unittest
import sqlite3
import py_compile

tests_dir = r"C:\AI-BS\tests"
test_files = [f for f in os.listdir(tests_dir) if f.startswith("test_") and f.endswith(".py")]

print("=" * 70)
print("             AI-BS UNIT & SANDBOX TEST SUITE AUDIT")
print("=" * 70)

# Check test_state.db
db_path = os.path.join(tests_dir, "test_state.db")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    res = conn.execute("PRAGMA quick_check;").fetchone()[0]
    mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    print(f"Database 'test_state.db': Status = {res} | Mode = {mode} | Tables = {tables}")
    conn.close()

print("\n--- Compiling Test Files with Python 3.12 ---")
for tf in test_files:
    fpath = os.path.join(tests_dir, tf)
    py_compile.compile(fpath, doraise=True)
    print(f"  [OK] Compiled {tf}")

print("\n--- Running Unit Test Suite ---")
loader = unittest.TestLoader()
suite = loader.discover(tests_dir, pattern="test_*.py")
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

print("\n" + "=" * 70)
print(f"Tests Run     : {result.testsRun}")
print(f"Failures      : {len(result.failures)}")
print(f"Errors        : {len(result.errors)}")
if result.wasSuccessful():
    print("[SUCCESS] All AI-BS Unit & Sandbox Tests Passed with 100% Success!")
print("=" * 70)