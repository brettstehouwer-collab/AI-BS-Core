import ctypes
from ctypes import wintypes
import struct

# IOCTL_SCSI_PASS_THROUGH constants
IOCTL_SCSI_PASS_THROUGH = 0x04D004
IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400

# Open physical drive 3
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3

kernel32 = ctypes.windll.kernel32

hDevice = kernel32.CreateFileW(
    r"\\.\PhysicalDrive3",
    GENERIC_READ | GENERIC_WRITE,
    FILE_SHARE_READ | FILE_SHARE_WRITE,
    None,
    OPEN_EXISTING,
    0,
    None
)

if hDevice == -1 or hDevice == 0xFFFFFFFFFFFFFFFF:
    print(f"Failed to open PhysicalDrive3 with R/W. Error: {kernel32.GetLastError()}")
    # Try Read Only
    hDevice = kernel32.CreateFileW(
        r"\\.\PhysicalDrive3",
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None
    )
    if hDevice == -1 or hDevice == 0xFFFFFFFFFFFFFFFF:
        print(f"Failed to open PhysicalDrive3 with Read. Error: {kernel32.GetLastError()}")
        exit(1)

print(f"Successfully opened PhysicalDrive3 handle: {hDevice}")

# Structure for SCSI_PASS_THROUGH
class SCSI_PASS_THROUGH(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.USHORT),
        ("ScsiStatus", ctypes.c_ubyte),
        ("PathId", ctypes.c_ubyte),
        ("TargetId", ctypes.c_ubyte),
        ("Lun", ctypes.c_ubyte),
        ("CdbLength", ctypes.c_ubyte),
        ("SenseInfoLength", ctypes.c_ubyte),
        ("DataIn", ctypes.c_ubyte),
        ("DataTransferLength", wintypes.ULONG),
        ("TimeOutValue", wintypes.ULONG),
        ("DataBufferOffset", ctypes.c_size_t),
        ("SenseInfoOffset", wintypes.ULONG),
        ("Cdb", ctypes.c_ubyte * 16),
    ]

# Execute standard SCSI INQUIRY (0x12)
buffer_size = 512
total_size = ctypes.sizeof(SCSI_PASS_THROUGH) + buffer_size
raw_buf = ctypes.create_string_buffer(total_size)

spt = SCSI_PASS_THROUGH.from_buffer(raw_buf)
spt.Length = ctypes.sizeof(SCSI_PASS_THROUGH)
spt.CdbLength = 6
spt.DataIn = 1 # SCSI_IOCTL_DATA_IN
spt.DataTransferLength = 96
spt.TimeOutValue = 5
spt.DataBufferOffset = ctypes.sizeof(SCSI_PASS_THROUGH)
spt.SenseInfoOffset = 0
spt.SenseInfoLength = 0
spt.Cdb[0] = 0x12 # INQUIRY
spt.Cdb[4] = 96

bytes_returned = wintypes.DWORD(0)
res = kernel32.DeviceIoControl(
    hDevice,
    IOCTL_SCSI_PASS_THROUGH,
    raw_buf,
    total_size,
    raw_buf,
    total_size,
    ctypes.byref(bytes_returned),
    None
)

if res:
    inq_data = raw_buf.raw[ctypes.sizeof(SCSI_PASS_THROUGH):ctypes.sizeof(SCSI_PASS_THROUGH) + 96]
    vid = inq_data[8:16].decode('ascii', errors='replace').strip()
    pid = inq_data[16:32].decode('ascii', errors='replace').strip()
    rev = inq_data[32:36].decode('ascii', errors='replace').strip()
    print(f"SCSI INQUIRY -> VID: '{vid}', PID: '{pid}', Rev: '{rev}'")
    print(f"Raw Inquiry Hex: {inq_data[:36].hex()}")
else:
    print(f"SCSI INQUIRY failed: {kernel32.GetLastError()}")

kernel32.CloseHandle(hDevice)
