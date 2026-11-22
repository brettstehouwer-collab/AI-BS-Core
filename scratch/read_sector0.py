import ctypes

kernel32 = ctypes.windll.kernel32
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3

hDevice = kernel32.CreateFileW(
    r"\\.\PhysicalDrive3",
    GENERIC_READ,
    FILE_SHARE_READ | FILE_SHARE_WRITE,
    None,
    OPEN_EXISTING,
    0,
    None
)

buf = ctypes.create_string_buffer(512)
bytes_read = ctypes.c_ulong(0)
res = kernel32.ReadFile(hDevice, buf, 512, ctypes.byref(bytes_read), None)
err = kernel32.GetLastError()
print(f"ReadFile on Sector 0: res={res}, bytes_read={bytes_read.value}, err={err}")
if err == 21:
    print("Error 21 = ERROR_NOT_READY (The device is not ready / No Media)")
elif err == 1117:
    print("Error 1117 = ERROR_IO_DEVICE (The request could not be performed because of an I/O device error)")

kernel32.CloseHandle(hDevice)
