import ctypes
from ctypes import wintypes
import tempfile
import sqlite3
import os

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80

kernel32 = ctypes.windll.kernel32

def copy_locked_file(src_path, dst_path):
    handle = kernel32.CreateFileW(
        src_path,
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None
    )
    if handle == -1 or handle == 0xFFFFFFFFFFFFFFFF:
        error = kernel32.GetLastError()
        raise OSError(f"CreateFileW failed with error code {error}")

    try:
        chunk_size = 64 * 1024
        buf = ctypes.create_string_buffer(chunk_size)
        bytes_read = wintypes.DWORD()
        with open(dst_path, 'wb') as out_f:
            while True:
                success = kernel32.ReadFile(handle, buf, chunk_size, ctypes.byref(bytes_read), None)
                if not success or bytes_read.value == 0:
                    break
                out_f.write(buf.raw[:bytes_read.value])
    finally:
        kernel32.CloseHandle(handle)

src_cookie = r'C:\Users\footb\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies'
with tempfile.NamedTemporaryFile(delete=False) as tf:
    tmp_path = tf.name

try:
    copy_locked_file(src_cookie, tmp_path)
    print(f"Successfully copied locked source Cookies! Size: {os.path.getsize(tmp_path)} bytes")
    con = sqlite3.connect(tmp_path)
    cur = con.cursor()
    cur.execute("SELECT count(*) FROM cookies")
    print("Total cookies in source DB:", cur.fetchone()[0])
    cur.execute("SELECT host_key, name FROM cookies WHERE host_key LIKE '%google%' AND name IN ('SID', 'SSID', 'SAPISID', 'HSID', '__Secure-1PSID')")
    rows = cur.fetchall()
    print("Google Auth cookies found in source:", len(rows))
    for r in rows:
        print(" ", r)
    con.close()
except Exception as e:
    print(f"Error copying locked file: {e}")
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
