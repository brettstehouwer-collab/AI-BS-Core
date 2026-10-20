import os
import sys
import time
import ctypes
from ctypes import wintypes

DLL_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "native", "aibs_shm_core.dll")
if not os.path.exists(DLL_PATH):
    DLL_PATH = os.path.abspath(r"C:\AI-BS\backend\native\aibs_shm_core.dll")

print(f"Loading native DLL from: {DLL_PATH}")
shm_dll = ctypes.CDLL(DLL_PATH)

# Signatures
shm_dll.aibs_shm_init.argtypes = [ctypes.c_wchar_p]
shm_dll.aibs_shm_init.restype = ctypes.c_int

shm_dll.aibs_shm_push.argtypes = [ctypes.c_uint16, ctypes.c_uint8, ctypes.c_char_p, ctypes.c_uint32]
shm_dll.aibs_shm_push.restype = ctypes.c_int

shm_dll.aibs_shm_pop.argtypes = [
    ctypes.POINTER(ctypes.c_uint16),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_char_p,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32)
]
shm_dll.aibs_shm_pop.restype = ctypes.c_int

shm_dll.aibs_shm_get_stats.argtypes = [
    ctypes.POINTER(ctypes.c_uint64),
    ctypes.POINTER(ctypes.c_uint64),
    ctypes.POINTER(ctypes.c_uint64),
    ctypes.POINTER(ctypes.c_uint64)
]
shm_dll.aibs_shm_get_stats.restype = None

# 1. Initialize
res = shm_dll.aibs_shm_init("Local\\AI_BS_IPC_SHM_BENCHMARK")
print(f"aibs_shm_init result: {res}")
assert res == 0, "Initialization failed"

# 2. Benchmark Native Throughput
NUM_EVENTS = 100_000
payload = b"RTX4090:TEMP=32C:VRAM=21.2GB:TELEMETRY_LOCK_FREE_TICK"

start = time.perf_counter()
pushed = 0
popped = 0

out_topic = ctypes.c_uint16(0)
out_flags = ctypes.c_uint8(0)
out_seq = ctypes.c_uint8(0)
buf = ctypes.create_string_buffer(64)
actual_len = ctypes.c_uint32(0)

# Simulate burst push / pop loop
for i in range(NUM_EVENTS):
    p_res = shm_dll.aibs_shm_push(1, 0, payload, len(payload))
    if p_res == 0:
        pushed += 1
    
    # Pop immediately to emulate streaming consumer
    pop_res = shm_dll.aibs_shm_pop(
        ctypes.byref(out_topic),
        ctypes.byref(out_flags),
        ctypes.byref(out_seq),
        buf,
        64,
        ctypes.byref(actual_len)
    )
    if pop_res == 0:
        popped += 1

elapsed = time.perf_counter() - start
rate = NUM_EVENTS / elapsed

print(f"\n==========================================")
print(f"   AI-BS NATIVE SHM DLL BENCHMARK")
print(f"==========================================")
print(f"Total Iterations:   {NUM_EVENTS:,}")
print(f"Successfully Pushed:{pushed:,}")
print(f"Successfully Popped:{popped:,}")
print(f"Elapsed Time:       {elapsed:.4f} seconds")
print(f"Throughput Rate:    {rate:,.0f} ops / sec")
print(f"Average Latency:    {(elapsed / NUM_EVENTS) * 1_000_000:.2f} microseconds per IPC round-trip")
print(f"Last Payload Received: {buf.value.decode('utf-8', errors='ignore')}")
print(f"==========================================\n")
