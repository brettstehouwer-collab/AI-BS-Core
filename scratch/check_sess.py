import os
import ctypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

sess = kernel32.WTSGetActiveConsoleSessionId()
my_sess = ctypes.c_ulong()
kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(my_sess))
print(f"Active Console Session: {sess}, Current Process Session: {my_sess.value}")

hwinsta = user32.GetProcessWindowStation()
buf = ctypes.create_unicode_buffer(256)
user32.GetUserObjectInformationW(hwinsta, 2, buf, 256, None) # 2 = UOI_NAME
print(f"Window Station: {buf.value}")
