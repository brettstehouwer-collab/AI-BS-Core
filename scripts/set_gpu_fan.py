#!/usr/bin/env python3
"""
Sovereign GPU Fan Control Utility
Controls NVIDIA GeForce RTX 4090 fan speeds via direct NVML hardware bindings.
Usage:
    python set_gpu_fan.py --speed 100       # Force 100% fan speed
    python set_gpu_fan.py --speed 80        # Set 80% fan speed
    python set_gpu_fan.py --status          # Query current fan speed and thermals
    python set_gpu_fan.py --auto            # Restore automatic driver curve
"""

import sys
import ctypes
import argparse

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def get_nvml():
    try:
        nvml = ctypes.CDLL("nvml.dll")
        ret = nvml.nvmlInit_v2()
        if ret != 0:
            raise RuntimeError(f"nvmlInit_v2 failed with error code: {ret}")
        return nvml
    except Exception as e:
        print(f"Error loading NVML: {e}")
        sys.exit(1)

def set_fan_speed(speed: int):
    nvml = get_nvml()
    handle = ctypes.c_void_p()
    ret = nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle))
    if ret != 0:
        print(f"Failed to get GPU 0 handle (code: {ret})")
        nvml.nvmlShutdown()
        sys.exit(1)

    num_fans = ctypes.c_uint(1)
    if hasattr(nvml, "nvmlDeviceGetNumFans"):
        nvml.nvmlDeviceGetNumFans(handle, ctypes.byref(num_fans))

    print(f"[GPU Fan Control] Target Speed: {speed}% across {num_fans.value} fan(s)...")
    for f in range(num_fans.value):
        if hasattr(nvml, "nvmlDeviceSetFanSpeed_v2"):
            res = nvml.nvmlDeviceSetFanSpeed_v2(handle, f, int(speed))
            if res == 0:
                print(f"  ✓ Fan {f}: Locked to {speed}%")
            else:
                print(f"  ✗ Fan {f}: Failed to set speed (code: {res})")

    # Read back current
    cur_speed = ctypes.c_uint()
    nvml.nvmlDeviceGetFanSpeed(handle, ctypes.byref(cur_speed))
    print(f"[GPU Fan Control] Current Sensor Readout: {cur_speed.value}%")
    nvml.nvmlShutdown()

def restore_auto():
    nvml = get_nvml()
    handle = ctypes.c_void_p()
    nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle))
    num_fans = ctypes.c_uint(1)
    if hasattr(nvml, "nvmlDeviceGetNumFans"):
        nvml.nvmlDeviceGetNumFans(handle, ctypes.byref(num_fans))

    print(f"[GPU Fan Control] Restoring automatic thermal curve...")
    for f in range(num_fans.value):
        if hasattr(nvml, "nvmlDeviceSetDefaultFanSpeed_v2"):
            res = nvml.nvmlDeviceSetDefaultFanSpeed_v2(handle, f)
            print(f"  Fan {f} reset to default: {res == 0}")
        elif hasattr(nvml, "nvmlDeviceSetFanControlPolicy"):
            res = nvml.nvmlDeviceSetFanControlPolicy(handle, f, 0)
            print(f"  Fan {f} policy set to AUTO: {res == 0}")
    nvml.nvmlShutdown()

def show_status():
    nvml = get_nvml()
    handle = ctypes.c_void_p()
    nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle))
    cur_speed = ctypes.c_uint()
    temp = ctypes.c_uint()
    nvml.nvmlDeviceGetFanSpeed(handle, ctypes.byref(cur_speed))
    if hasattr(nvml, "nvmlDeviceGetTemperature"):
        nvml.nvmlDeviceGetTemperature(handle, 0, ctypes.byref(temp))
    print(f"GPU Fan Speed: {cur_speed.value}% | Temp: {temp.value}°C")
    nvml.nvmlShutdown()

def main():
    parser = argparse.ArgumentParser(description="NVIDIA GPU Fan Control Utility")
    parser.add_argument("--speed", type=int, default=100, help="Fan speed percentage (0-100)")
    parser.add_argument("--auto", action="store_true", help="Restore automatic fan curve")
    parser.add_argument("--status", action="store_true", help="Display current fan speed and temperature")
    args = parser.parse_args()

    if args.auto:
        restore_auto()
    elif args.status:
        show_status()
    else:
        set_fan_speed(args.speed)

if __name__ == "__main__":
    main()
