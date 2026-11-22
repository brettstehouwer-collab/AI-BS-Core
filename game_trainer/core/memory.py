"""
AI-BS Game Trainer Suite: Core Memory Engine
Win32 memory primitives, multi-level pointer dereferencing, byte patching,
and AOB (Array of Bytes) signature scanning using native ctypes.
"""

import ctypes
from ctypes import wintypes
import struct
import re
from typing import List, Optional, Tuple, Dict, Any, Union

# Win32 Constants
PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

PAGE_NOACCESS = 0x01
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE = 0x10
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_GUARD = 0x100

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_FREE = 0x10000

# Structures
class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]

class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_char * 256),
        ("szExePath", ctypes.c_char * 260),
    ]

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


class MemoryPatch:
    """Represents a patch applied to memory with automatic restore capability."""
    def __init__(self, memory_manager: "MemoryManager", address: int, original_bytes: bytes, patched_bytes: bytes):
        self.mem = memory_manager
        self.address = address
        self.original_bytes = original_bytes
        self.patched_bytes = patched_bytes
        self.is_applied = True

    def restore(self) -> bool:
        """Restores original instructions/bytes."""
        if not self.is_applied:
            return True
        success = self.mem.write_bytes(self.address, self.original_bytes, unprotect=True)
        if success:
            self.is_applied = False
        return success

    def apply(self) -> bool:
        """Re-applies the patch."""
        if self.is_applied:
            return True
        success = self.mem.write_bytes(self.address, self.patched_bytes, unprotect=True)
        if success:
            self.is_applied = True
        return success

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.restore()


class MemoryManager:
    """
    Win32 external memory manipulation engine.
    Supports 32-bit and 64-bit processes, multi-level pointer resolution,
    instruction patching, and signature scanning.
    """

    def __init__(self, process_name_or_pid: Optional[Union[str, int]] = None):
        self.kernel32 = ctypes.windll.kernel32
        self.pid: Optional[int] = None
        self.process_name: Optional[str] = None
        self.handle: Optional[int] = None
        self.base_address: int = 0
        self.is_64bit: bool = True
        self.active_patches: List[MemoryPatch] = []
        self._scan_buffer: Optional[ctypes.Array] = None
        self._scan_buffer_size: int = 0

        # Set 64-bit safe argtypes for Win32 memory APIs
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE

        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL

        self.kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        self.kernel32.GetExitCodeProcess.restype = wintypes.BOOL

        self.kernel32.ReadProcessMemory.argtypes = [
            wintypes.HANDLE,
            ctypes.c_uint64,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t)
        ]
        self.kernel32.ReadProcessMemory.restype = wintypes.BOOL

        self.kernel32.WriteProcessMemory.argtypes = [
            wintypes.HANDLE,
            ctypes.c_uint64,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t)
        ]
        self.kernel32.WriteProcessMemory.restype = wintypes.BOOL

        self.kernel32.VirtualProtectEx.argtypes = [
            wintypes.HANDLE,
            ctypes.c_uint64,
            ctypes.c_size_t,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD)
        ]
        self.kernel32.VirtualProtectEx.restype = wintypes.BOOL

        if process_name_or_pid is not None:
            self.attach(process_name_or_pid)

    def attach(self, target: Union[str, int]) -> bool:
        """Attaches to a process by executable name (e.g. 'game.exe') or PID."""
        if isinstance(target, int):
            self.pid = target
            self.process_name = f"PID_{target}"
        else:
            self.process_name = target
            self.pid = self.find_process_id(target)
            if not self.pid:
                raise ProcessLookupError(f"Target process '{target}' not found.")

        # Open process handle with full access
        desired_access = PROCESS_ALL_ACCESS
        self.handle = self.kernel32.OpenProcess(desired_access, False, self.pid)
        if not self.handle:
            error_code = self.kernel32.GetLastError()
            raise PermissionError(f"Failed to open process PID {self.pid}. Win32 Error: {error_code}")

        # Check architecture (32-bit vs 64-bit)
        self.is_64bit = self._check_is_64bit()

        # Resolve module base address
        self.base_address = self.get_module_base(self.process_name)
        return True

    def detach(self):
        """Restores all active patches and closes the process handle."""
        for patch in list(self.active_patches):
            patch.restore()
        self.active_patches.clear()

        if self.handle:
            self.kernel32.CloseHandle(self.handle)
            self.handle = None
        self.pid = None
        self.base_address = 0

    def is_alive(self) -> bool:
        """Returns True if the target process is still running."""
        if not self.handle:
            return False
        exit_code = wintypes.DWORD()
        if self.kernel32.GetExitCodeProcess(self.handle, ctypes.byref(exit_code)):
            return exit_code.value == 259  # STILL_ACTIVE
        return False

    def _check_is_64bit(self) -> bool:
        """Determines if the process is 64-bit."""
        # IsWow64Process returns TRUE if running 32-bit on 64-bit Windows
        is_wow64 = wintypes.BOOL()
        if self.kernel32.IsWow64Process(self.handle, ctypes.byref(is_wow64)):
            # If 64-bit OS: Wow64 means 32-bit process. Not Wow64 means 64-bit process.
            # Assuming 64-bit host OS
            return not bool(is_wow64.value)
        return True

    def find_process_id(self, process_name: str) -> Optional[int]:
        """Finds PID of a process by executable filename (supports with or without .exe, case-insensitive)."""
        clean_target = process_name.lower().removesuffix(".exe")

        # Fast and robust discovery via psutil
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pname = (proc.info.get('name') or "").lower().removesuffix(".exe")
                    if pname == clean_target:
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        # Fallback to Toolhelp32Snapshot
        snapshot = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == -1 or not snapshot:
            return None

        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

        try:
            success = self.kernel32.Process32First(snapshot, ctypes.byref(entry))
            while success:
                current_name = entry.szExeFile.decode("utf-8", errors="ignore").lower().removesuffix(".exe")
                if current_name == clean_target:
                    return entry.th32ProcessID
                success = self.kernel32.Process32Next(snapshot, ctypes.byref(entry))
        finally:
            self.kernel32.CloseHandle(snapshot)
        return None

    def get_module_base(self, module_name: Optional[str] = None) -> int:
        """Resolves the base address of a loaded module or main executable."""
        if not self.pid:
            return 0

        flags = TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32
        snapshot = self.kernel32.CreateToolhelp32Snapshot(flags, self.pid)
        if snapshot == -1 or not snapshot:
            return 0

        entry = MODULEENTRY32()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32)

        target_name = (module_name or self.process_name or "").lower()
        base_addr = 0

        try:
            success = self.kernel32.Module32First(snapshot, ctypes.byref(entry))
            while success:
                mod_name = entry.szModule.decode("utf-8", errors="ignore").lower()
                if not target_name or mod_name == target_name:
                    base_addr = entry.modBaseAddr
                    if isinstance(base_addr, int):
                        return base_addr
                    return ctypes.cast(base_addr, ctypes.c_void_p).value or 0
                success = self.kernel32.Module32Next(snapshot, ctypes.byref(entry))
        finally:
            self.kernel32.CloseHandle(snapshot)
        return base_addr

    # -------------------------------------------------------------------------
    # Core Read / Write Primitives
    # -------------------------------------------------------------------------

    def read_bytes(self, address: int, size: int) -> bytes:
        """Reads raw bytes from target process memory."""
        if not self.handle or address == 0:
            return b""
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)
        success = self.kernel32.ReadProcessMemory(
            self.handle,
            address,
            buffer,
            size,
            ctypes.byref(bytes_read)
        )
        if not success:
            err = self.kernel32.GetLastError()
            print(f"DEBUG ReadProcessMemory FAIL: addr={hex(address)}, handle={self.handle}, err={err}, bytes_read={bytes_read.value}")
        if success:
            return buffer.raw[:bytes_read.value]
        return b""

    def read_bytes_into(self, address: int, buffer: ctypes.Array, size: int) -> int:
        """Reads raw bytes into a pre-allocated ctypes buffer. Returns number of bytes read."""
        if not self.handle or address == 0 or size <= 0:
            return 0
        bytes_read = ctypes.c_size_t(0)
        success = self.kernel32.ReadProcessMemory(
            self.handle,
            address,
            buffer,
            size,
            ctypes.byref(bytes_read)
        )
        return bytes_read.value if success else 0

    def write_bytes(self, address: int, data: bytes, unprotect: bool = False) -> bool:
        """Writes raw bytes to target process memory, optionally bypassing page protection."""
        if not self.handle or address == 0:
            return False

        old_protect = wintypes.DWORD()
        if unprotect:
            self.kernel32.VirtualProtectEx(
                self.handle,
                address,
                len(data),
                PAGE_EXECUTE_READWRITE,
                ctypes.byref(old_protect)
            )

        buffer = ctypes.create_string_buffer(data)
        bytes_written = ctypes.c_size_t(0)
        success = self.kernel32.WriteProcessMemory(
            self.handle,
            address,
            buffer,
            len(data),
            ctypes.byref(bytes_written)
        )

        if unprotect and old_protect.value:
            temp = wintypes.DWORD()
            self.kernel32.VirtualProtectEx(
                self.handle,
                address,
                len(data),
                old_protect.value,
                ctypes.byref(temp)
            )

        return bool(success) and bytes_written.value == len(data)

    # -------------------------------------------------------------------------
    # Typed Memory Accessors
    # -------------------------------------------------------------------------

    def read_int32(self, address: int) -> int:
        data = self.read_bytes(address, 4)
        return struct.unpack("<i", data)[0] if len(data) == 4 else 0

    def write_int32(self, address: int, value: int) -> bool:
        return self.write_bytes(address, struct.pack("<i", value))

    def read_uint32(self, address: int) -> int:
        data = self.read_bytes(address, 4)
        return struct.unpack("<I", data)[0] if len(data) == 4 else 0

    def write_uint32(self, address: int, value: int) -> bool:
        return self.write_bytes(address, struct.pack("<I", value))

    def read_int64(self, address: int) -> int:
        data = self.read_bytes(address, 8)
        return struct.unpack("<q", data)[0] if len(data) == 8 else 0

    def write_int64(self, address: int, value: int) -> bool:
        return self.write_bytes(address, struct.pack("<q", value))

    def read_float(self, address: int) -> float:
        data = self.read_bytes(address, 4)
        return struct.unpack("<f", data)[0] if len(data) == 4 else 0.0

    def write_float(self, address: int, value: float) -> bool:
        return self.write_bytes(address, struct.pack("<f", float(value)))

    def read_double(self, address: int) -> float:
        data = self.read_bytes(address, 8)
        return struct.unpack("<d", data)[0] if len(data) == 8 else 0.0

    def write_double(self, address: int, value: float) -> bool:
        return self.write_bytes(address, struct.pack("<d", float(value)))

    def read_bool(self, address: int) -> bool:
        data = self.read_bytes(address, 1)
        return bool(data[0]) if len(data) == 1 else False

    def write_bool(self, address: int, value: bool) -> bool:
        return self.write_bytes(address, b"\x01" if value else b"\x00")

    def read_string(self, address: int, max_length: int = 128, encoding: str = "utf-8") -> str:
        data = self.read_bytes(address, max_length)
        if not data:
            return ""
        null_idx = data.find(b"\x00")
        if null_idx != -1:
            data = data[:null_idx]
        return data.decode(encoding, errors="ignore")

    # -------------------------------------------------------------------------
    # Pointer Resolution Engine
    # -------------------------------------------------------------------------

    def resolve_pointer_chain(self, base_address: int, offsets: List[int]) -> int:
        """
        Traverses dynamic pointer levels to compute the final target memory address.
        e.g., base_address + offsets: [0x10, 0x48, 0x14]
        Computes: [[base_address + 0x10] + 0x48] + 0x14
        """
        if not offsets:
            return base_address

        ptr_size = 8 if self.is_64bit else 4
        current_address = base_address

        for idx, offset in enumerate(offsets[:-1]):
            target = current_address + offset
            if self.is_64bit:
                dereferenced = self.read_int64(target)
            else:
                dereferenced = self.read_uint32(target)

            if dereferenced == 0:
                raise ValueError(f"Null pointer encountered at level {idx} (address: {hex(target)})")
            current_address = dereferenced

        # Final offset
        return current_address + offsets[-1]

    # -------------------------------------------------------------------------
    # Byte Patching & NOPing
    # -------------------------------------------------------------------------

    def patch_bytes(self, address: int, patch_bytes: bytes) -> MemoryPatch:
        """Applies a byte patch and tracks it for clean rollback."""
        original = self.read_bytes(address, len(patch_bytes))
        if len(original) != len(patch_bytes):
            raise MemoryError(f"Cannot read target address {hex(address)} to create patch backup.")

        self.write_bytes(address, patch_bytes, unprotect=True)
        patch = MemoryPatch(self, address, original, patch_bytes)
        self.active_patches.append(patch)
        return patch

    def nop_instruction(self, address: int, count: int) -> MemoryPatch:
        """Overwrites 'count' instruction bytes with x86/x64 NOP (0x90)."""
        return self.patch_bytes(address, b"\x90" * count)

    # -------------------------------------------------------------------------
    # Signature / AOB (Array of Bytes) Scanner
    # -------------------------------------------------------------------------

    def aob_scan(self, pattern: str, module_name: Optional[str] = None) -> List[int]:
        """
        Fast memory signature scanner supporting wildcards (e.g. '48 8B 05 ?? ?? ?? ?? 48 85 C0').
        Scans committed, readable memory pages of the process or specified module.
        """
        # Parse pattern into regex bytes
        # Tokens can be '48', '8B', '?', '??'
        tokens = pattern.strip().split()
        regex_parts = []
        for token in tokens:
            if token in ("?", "??"):
                regex_parts.append(b".")
            else:
                regex_parts.append(re.escape(bytes.fromhex(token)))
        pattern_regex = re.compile(b"".join(regex_parts), re.DOTALL)

        matches: List[int] = []
        mbi = MEMORY_BASIC_INFORMATION()
        current_addr = 0
        max_addr = 0x7FFFFFFFFFFF if self.is_64bit else 0x7FFFFFFF

        # If a module name is given, restrict scan bounds to module size
        if module_name:
            base = self.get_module_base(module_name)
            if base:
                current_addr = base
                # Read page headers
                if self.kernel32.VirtualQueryEx(self.handle, ctypes.c_void_p(current_addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                    max_addr = base + mbi.RegionSize

        while current_addr < max_addr:
            ret = self.kernel32.VirtualQueryEx(
                self.handle,
                ctypes.c_void_p(current_addr),
                ctypes.byref(mbi),
                ctypes.sizeof(mbi)
            )
            if not ret:
                break

            base_addr = mbi.BaseAddress or current_addr
            region_size = mbi.RegionSize

            # Only scan committed memory that is readable (not PAGE_NOACCESS or PAGE_GUARD)
            is_readable = (
                mbi.State == MEM_COMMIT and
                not (mbi.Protect & PAGE_GUARD) and
                not (mbi.Protect & PAGE_NOACCESS) and
                (mbi.Protect in (PAGE_READONLY, PAGE_READWRITE, PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE))
            )

            if is_readable and region_size > 0:
                # Read memory chunk safely (chunked if over 4MB to prevent excessive memory spikes)
                chunk_size = min(region_size, 4 * 1024 * 1024)
                offset = 0
                while offset < region_size:
                    to_read = min(chunk_size, region_size - offset)
                    data = self.read_bytes(base_addr + offset, to_read)
                    if data:
                        for match in pattern_regex.finditer(data):
                            matches.append(base_addr + offset + match.start())
                    offset += to_read

            current_addr = base_addr + region_size
            if module_name and current_addr >= max_addr:
                break

        return matches

    def resolve_rip_relative(self, instruction_address: int, instruction_length: int = 7) -> int:
        """
        Resolves x86_64 RIP-relative addressing:
        e.g., 'mov rax, [rip + 0x123456]' -> target address = (instruction_addr + instruction_len) + displacement
        Displacement is typically a signed 32-bit integer located at (instruction_addr + instruction_length - 4).
        """
        disp_address = instruction_address + instruction_length - 4
        displacement = self.read_int32(disp_address)
        return instruction_address + instruction_length + displacement

    def scan_exact_value(
        self,
        value: Union[int, float],
        value_type: str = "double",
        max_matches: int = 1000,
        alignment: Optional[int] = None
    ) -> List[int]:
        """
        Scans all committed, writable memory regions (PAGE_READWRITE / PAGE_EXECUTE_READWRITE)
        for an exact typed value with boundary overlap and natural memory alignment.
        Supported types: 'double' (8-byte float), 'float' (4-byte float), 'int32' (4-byte int),
        'uint32' (4-byte unsigned), 'int64' (8-byte int).
        Uses a pre-allocated scan buffer to prevent memory churn.
        """
        type_fmts = {
            "double": "<d",
            "float": "<f",
            "int32": "<i",
            "uint32": "<I",
            "int64": "<q"
        }
        fmt = type_fmts.get(value_type.lower(), "<d")
        packed_val = struct.pack(fmt, value)
        val_len = len(packed_val)

        # Default natural alignment: 8 bytes for 64-bit double/int64, 4 bytes for 32-bit int/float
        if alignment is None:
            alignment = 8 if val_len == 8 else 4

        # Pre-allocate or reuse internal scan buffer
        chunk_size = 2 * 1024 * 1024
        buf_needed = chunk_size + 16
        if self._scan_buffer is None or self._scan_buffer_size < buf_needed:
            self._scan_buffer = ctypes.create_string_buffer(buf_needed)
            self._scan_buffer_size = buf_needed
        buf = self._scan_buffer

        matches: List[int] = []
        mbi = MEMORY_BASIC_INFORMATION()
        current_addr = 0
        max_addr = 0x7FFFFFFFFFFF if self.is_64bit else 0x7FFFFFFF

        while current_addr < max_addr and len(matches) < max_matches:
            ret = self.kernel32.VirtualQueryEx(
                self.handle,
                ctypes.c_void_p(current_addr),
                ctypes.byref(mbi),
                ctypes.sizeof(mbi)
            )
            if not ret:
                break

            base_addr = mbi.BaseAddress or current_addr
            region_size = mbi.RegionSize

            # Only scan committed memory that is writable and not guard/noaccess
            is_writable = (
                mbi.State == MEM_COMMIT and
                not (mbi.Protect & PAGE_GUARD) and
                not (mbi.Protect & PAGE_NOACCESS) and
                (mbi.Protect in (PAGE_READWRITE, PAGE_EXECUTE_READWRITE, PAGE_WRITECOPY, PAGE_EXECUTE_WRITECOPY))
            )

            if is_writable and region_size > 0:
                offset = 0
                overlap = val_len - 1
                while offset < region_size and len(matches) < max_matches:
                    to_read = min(chunk_size, region_size - offset)
                    bytes_read = self.read_bytes_into(base_addr + offset, buf, to_read)
                    if bytes_read > 0:
                        raw_data = buf.raw[:bytes_read]
                        idx = 0
                        while True:
                            idx = raw_data.find(packed_val, idx)
                            if idx == -1:
                                break
                            cand_addr = base_addr + offset + idx
                            # Enforce memory alignment
                            if alignment <= 1 or (cand_addr % alignment == 0):
                                if not matches or cand_addr != matches[-1]:
                                    matches.append(cand_addr)
                                    if len(matches) >= max_matches:
                                        break
                            idx += (alignment if alignment > 1 else 1)

                    if to_read < chunk_size or (offset + to_read >= region_size):
                        offset += to_read
                    else:
                        # Overlap chunk by val_len - 1 to capture split values
                        offset += (to_read - overlap)

            current_addr = base_addr + region_size

        return matches

    def filter_scan(
        self,
        candidate_addresses: List[int],
        target_value: Union[int, float],
        value_type: str = "double",
        tolerance: float = 0.001,
        alignment: Optional[int] = None
    ) -> List[int]:
        """
        Narrows down a list of previously found candidate addresses by checking which
        currently match target_value. Executes in <1 millisecond.
        """
        remaining: List[int] = []
        vt = value_type.lower()
        if alignment is None:
            alignment = 8 if vt in ("double", "int64") else 4

        for addr in candidate_addresses:
            if alignment > 1 and (addr % alignment != 0):
                continue
            try:
                if vt == "double":
                    val = self.read_double(addr)
                    if abs(val - float(target_value)) < tolerance:
                        remaining.append(addr)
                elif vt == "float":
                    val = self.read_float(addr)
                    if abs(val - float(target_value)) < tolerance:
                        remaining.append(addr)
                elif vt in ("int32", "uint32"):
                    val = self.read_int32(addr)
                    if val == int(target_value):
                        remaining.append(addr)
                elif vt == "int64":
                    val = self.read_int64(addr)
                    if val == int(target_value):
                        remaining.append(addr)
            except Exception:
                continue

        return remaining

