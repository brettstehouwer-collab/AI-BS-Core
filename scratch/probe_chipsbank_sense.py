import ctypes
from ctypes import wintypes

IOCTL_SCSI_PASS_THROUGH_DIRECT = 0x04D014
IOCTL_SCSI_PASS_THROUGH = 0x04D004
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

class SCSI_PASS_THROUGH_WITH_BUFFERS(ctypes.Structure):
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
        ("SenseBuf", ctypes.c_ubyte * 64),
        ("DataBuf", ctypes.c_ubyte * 512)
    ]

def send_scsi(cdb, data_in=True, transfer_len=0):
    spt = SCSI_PASS_THROUGH_WITH_BUFFERS()
    spt.Length = ctypes.sizeof(spt)
    spt.CdbLength = len(cdb)
    for i, b in enumerate(cdb):
        spt.Cdb[i] = b
    spt.DataIn = 1 if data_in else 0
    spt.DataTransferLength = transfer_len
    spt.TimeOutValue = 5
    spt.DataBufferOffset = SCSI_PASS_THROUGH_WITH_BUFFERS.DataBuf.offset
    spt.SenseInfoOffset = SCSI_PASS_THROUGH_WITH_BUFFERS.SenseBuf.offset
    spt.SenseInfoLength = 64

    bytes_ret = wintypes.DWORD(0)
    res = kernel32.DeviceIoControl(
        hDevice,
        IOCTL_SCSI_PASS_THROUGH,
        ctypes.byref(spt),
        ctypes.sizeof(spt),
        ctypes.byref(spt),
        ctypes.sizeof(spt),
        ctypes.byref(bytes_ret),
        None
    )
    return res, spt

# Test Unit Ready
res, spt = send_scsi([0x00, 0, 0, 0, 0, 0], data_in=False, transfer_len=0)
print(f"TEST UNIT READY: Result={res}, ScsiStatus={spt.ScsiStatus:#x}")
if spt.ScsiStatus != 0:
    sense = bytes(spt.SenseBuf[:spt.SenseInfoLength])
    print(f"Sense Data (len={spt.SenseInfoLength}): {sense.hex()}")
    if len(sense) >= 14:
        sense_key = sense[2] & 0x0F
        asc = sense[12]
        ascq = sense[13]
        print(f"Sense Key: {sense_key:#04x}, ASC: {asc:#04x}, ASCQ: {ascq:#04x}")
        # ASC 0x3A = MEDIUM NOT PRESENT

# Read Capacity (10)
res, spt = send_scsi([0x25, 0, 0, 0, 0, 0, 0, 0, 0, 0], data_in=True, transfer_len=8)
print(f"READ CAPACITY (10): Result={res}, ScsiStatus={spt.ScsiStatus:#x}")
if spt.ScsiStatus == 0 and res:
    data = bytes(spt.DataBuf[:8])
    print(f"Capacity Data: {data.hex()}")
else:
    sense = bytes(spt.SenseBuf[:spt.SenseInfoLength])
    print(f"Sense Data: {sense.hex()}")

# Chipsbank Vendor Specific Command to query Controller & Flash ID
# Chipsbank typically uses 0xF0 or 0xF1 or 0x06 for Flash ID / Controller identification
print("\n--- Probing Chipsbank Vendor Commands ---")
for cmd_byte in [0xF0, 0xF1, 0x06, 0xC6, 0xCC, 0xD6]:
    res, spt = send_scsi([cmd_byte, 0, 0, 0, 0, 0, 0, 0, 0, 0], data_in=True, transfer_len=64)
    if res and spt.ScsiStatus == 0:
        data = bytes(spt.DataBuf[:32])
        print(f"Command {cmd_byte:#04x} SUCCESS! Data: {data.hex()} | ASCII: {data.decode('latin1', errors='replace')}")
    else:
        # print(f"Command {cmd_byte:#04x} failed (status={spt.ScsiStatus:#x})")
        pass

kernel32.CloseHandle(hDevice)
