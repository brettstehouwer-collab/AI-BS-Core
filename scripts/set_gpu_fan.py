"""
AI-BS Sovereign Hardware Controller: NVIDIA GPU Fan Speed Manager
------------------------------------------------------------------
Usage:
  python set_gpu_fan.py --speed 100       # Set all fans to 100% max speed
  python set_gpu_fan.py --speed 80        # Set all fans to 80%
  python set_gpu_fan.py --auto            # Restore factory automatic curve
  python set_gpu_fan.py --status          # Query current temperatures & fan RPM %
"""

import sys
import argparse
import ctypes
from ctypes import byref, c_uint, c_void_p

def get_nvml():
    try:
        nvml = ctypes.CDLL('nvml.dll')
    except Exception:
        nvml = ctypes.CDLL(r'C:\Windows\System32\nvml.dll')
    nvml.nvmlInit_v2()
    handle = c_void_p()
    nvml.nvmlDeviceGetHandleByIndex_v2(c_uint(0), byref(handle))
    return nvml, handle

def set_fan_speed(speed_pct):
    nvml, handle = get_nvml()
    num_fans = c_uint(0)
    nvml.nvmlDeviceGetNumFans(handle, byref(num_fans))
    
    print(f"Detected {num_fans.value} fan zones on NVIDIA GeForce RTX 4090.")
    print(f"Applying fan target: {speed_pct}%...")
    
    for i in range(num_fans.value):
        res = nvml.nvmlDeviceSetFanSpeed_v2(handle, c_uint(i), c_uint(speed_pct))
        status = "OK" if res == 0 else f"Err ({res})"
        print(f"  • Fan {i} -> {speed_pct}%: {status}")

def restore_auto_curve():
    nvml, handle = get_nvml()
    num_fans = c_uint(0)
    nvml.nvmlDeviceGetNumFans(handle, byref(num_fans))
    print(f"Restoring factory automatic fan curve on {num_fans.value} fans...")
    for i in range(num_fans.value):
        if hasattr(nvml, 'nvmlDeviceSetDefaultFanSpeed_v2'):
            res = nvml.nvmlDeviceSetDefaultFanSpeed_v2(handle, c_uint(i))
        else:
            # Fallback
            res = nvml.nvmlDeviceSetFanSpeed_v2(handle, c_uint(i), c_uint(0))
        print(f"  • Fan {i} restored to AUTO: code {res}")

def query_status():
    nvml, handle = get_nvml()
    temp = c_uint(0)
    nvml.nvmlDeviceGetTemperature(handle, c_uint(0), byref(temp))
    num_fans = c_uint(0)
    nvml.nvmlDeviceGetNumFans(handle, byref(num_fans))
    print(f"GPU Core Temp: {temp.value}°C")
    for i in range(num_fans.value):
        speed = c_uint(0)
        nvml.nvmlDeviceGetFanSpeed_v2(handle, c_uint(i), byref(speed))
        print(f"  • Fan {i}: {speed.value}%")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="NVIDIA GPU Fan Controller")
    parser.add_argument('--speed', type=int, help="Target fan speed (0-100%)")
    parser.add_argument('--auto', action='store_true', help="Restore automatic fan curve")
    parser.add_argument('--status', action='store_true', help="Show current temp and fan speeds")
    args = parser.parse_args()

    if args.auto:
        restore_auto_curve()
    elif args.speed is not None:
        val = max(0, min(100, args.speed))
        set_fan_speed(val)
    else:
        query_status()
