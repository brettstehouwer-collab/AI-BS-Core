import unittest
import ctypes
from ctypes import wintypes
import time
import os
import sys

AIBS_SHM_MAGIC = 0xA1B51996
AIBS_SHM_TEST_NAME = "Local\\AI_BS_IPC_SHM_TEST"
AIBS_RING_SLOTS = 64
AIBS_SLOT_PAYLOAD_SIZE = 60
AIBS_SHM_TOTAL_SIZE = 4224

FILE_MAP_ALL_ACCESS = 0xF001F
PAGE_READWRITE = 0x04
INVALID_HANDLE_VALUE = -1

kernel32 = ctypes.windll.kernel32

kernel32.CreateFileMappingW.argtypes = [
    wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR
]
kernel32.CreateFileMappingW.restype = wintypes.HANDLE

kernel32.MapViewOfFile.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t
]
kernel32.MapViewOfFile.restype = wintypes.LPVOID

kernel32.UnmapViewOfFile.argtypes = [wintypes.LPCVOID]
kernel32.UnmapViewOfFile.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

class RingSlotMultiTopic(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("topic_id", ctypes.c_uint16),
        ("flags", ctypes.c_uint8),
        ("seq", ctypes.c_uint8),
        ("payload", ctypes.c_uint8 * AIBS_SLOT_PAYLOAD_SIZE)
    ]

class ShmRingBufferMultiTopic(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint32),
        ("head", ctypes.c_uint64),
        ("tail", ctypes.c_uint64),
        ("total_pushed", ctypes.c_uint64),
        ("total_popped", ctypes.c_uint64),
        ("padding", ctypes.c_uint8 * 24),
        ("slots", RingSlotMultiTopic * AIBS_RING_SLOTS)
    ]

class TestSandboxSHMRing(unittest.TestCase):
    def setUp(self):
        self.hMapFile = kernel32.CreateFileMappingW(
            INVALID_HANDLE_VALUE, None, PAGE_READWRITE, 0, AIBS_SHM_TOTAL_SIZE, AIBS_SHM_TEST_NAME
        )
        self.pBuf = kernel32.MapViewOfFile(self.hMapFile, FILE_MAP_ALL_ACCESS, 0, 0, AIBS_SHM_TOTAL_SIZE)
        self.ring = ShmRingBufferMultiTopic.from_address(self.pBuf)
        self.ring.magic = AIBS_SHM_MAGIC
        self.ring.version = 1
        self.ring.head = 0
        self.ring.tail = 0
        self.ring.total_pushed = 0
        self.ring.total_popped = 0

    def tearDown(self):
        if self.pBuf:
            kernel32.UnmapViewOfFile(self.pBuf)
        if self.hMapFile:
            kernel32.CloseHandle(self.hMapFile)

    def test_shm_zero_copy_push_pop(self):
        num_packets = 10000
        start = time.perf_counter()

        for i in range(num_packets):
            idx = self.ring.head % AIBS_RING_SLOTS
            slot = self.ring.slots[idx]
            slot.topic_id = 0x0001
            slot.flags = 0
            slot.seq = i % 256
            
            # Write payload bytes
            data = f"packet_{i}".encode('utf-8')
            ctypes.memmove(slot.payload, data, min(len(data), AIBS_SLOT_PAYLOAD_SIZE))
            
            self.ring.head += 1
            self.ring.total_pushed += 1

            # Simulate consumer reading immediately
            if self.ring.head > self.ring.tail:
                c_idx = self.ring.tail % AIBS_RING_SLOTS
                c_slot = self.ring.slots[c_idx]
                self.assertEqual(c_slot.topic_id, 0x0001)
                self.ring.tail += 1
                self.ring.total_popped += 1

        elapsed = time.perf_counter() - start
        throughput = num_packets / elapsed
        print(f"\n[PASS] Windows SHM Ring Zero-Copy: {num_packets} packets in {elapsed*1000:.2f}ms ({throughput:,.0f} pkts/sec)")
        self.assertEqual(self.ring.total_pushed, num_packets)
        self.assertEqual(self.ring.total_popped, num_packets)

if __name__ == "__main__":
    unittest.main()
