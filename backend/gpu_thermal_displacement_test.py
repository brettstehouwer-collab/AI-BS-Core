"""
AI-BS Sovereign Intelligence - GPU Thermal & Emergency Heat Displacement Test
=============================================================================
Safely benchmarks thermal dissipation, maximum fan duty cycle (100% PWM),
and thermal recovery velocity on NVIDIA GeForce RTX 4090.
"""

import sys
import time
import pynvml

# Reconfigure stdout for utf-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def print_telemetry_header(h):
    name = pynvml.nvmlDeviceGetName(h)
    temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
    pwr = pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0
    pwr_cur = pynvml.nvmlDeviceGetPowerManagementLimit(h) / 1000.0
    pwr_min, pwr_max = pynvml.nvmlDeviceGetPowerManagementLimitConstraints(h)
    pwr_min /= 1000.0
    pwr_max /= 1000.0
    num_fans = pynvml.nvmlDeviceGetNumFans(h)
    speeds = [pynvml.nvmlDeviceGetFanSpeed_v2(h, i) for i in range(num_fans)]
    
    print("\n" + "="*70)
    print(" [NVIDIA RTX 4090 TELEMETRY & HARDWARE LIMITS]")
    print("="*70)
    print(f" • GPU Model         : {name}")
    print(f" • Current Core Temp : {temp} deg C")
    print(f" • Current Power     : {pwr:.1f} W (Active Draw)")
    print(f" • Power Limit       : {pwr_cur:.1f} W (Default: 450W, Max vBIOS: {pwr_max:.1f}W / {pwr_max/450*100:.1f}%)")
    print(f" • Hardware Fans     : {num_fans} Fans Detected")
    print(f" • Current Speeds    : Fan 0: {speeds[0]}% | Fan 1: {speeds[1]}%")
    print(f" • Physical PWM Cap  : 100% (Maximum Electronic Duty Cycle)")
    print("="*70 + "\n")
    return temp

def restore_fans(h, num_fans):
    print(">> Restoring fans to factory automatic curve...")
    for i in range(num_fans):
        try:
            pynvml.nvmlDeviceSetDefaultFanSpeed_v2(h, i)
        except Exception as e:
            print(f"  Warning restoring fan {i}: {e}")
    print(">> Fan curve successfully reverted to vBIOS Auto Management.\n")

def run_fan_blast_test(h, duration_sec=10):
    num_fans = pynvml.nvmlDeviceGetNumFans(h)
    start_temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
    print(f"\n[TEST A: 100% EMERGENCY FAN BLAST - {duration_sec} SECONDS]")
    print("Engaging maximum fan duty cycle (100% PWM)...")
    
    try:
        for i in range(num_fans):
            pynvml.nvmlDeviceSetFanSpeed_v2(h, i, 100)
        
        for elapsed in range(1, duration_sec + 1):
            time.sleep(1)
            temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            speeds = [pynvml.nvmlDeviceGetFanSpeed_v2(h, i) for i in range(num_fans)]
            pwr = pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0
            print(f"  [{elapsed:02d}s] Core Temp: {temp} deg C | Fans: {speeds[0]}% / {speeds[1]}% | Power: {pwr:.1f}W")
            
        final_temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
        delta_t = final_temp - start_temp
        print(f"\nResult: Baseline {start_temp} deg C -> Final {final_temp} deg C (Delta: {delta_t:+d} deg C)")
    finally:
        restore_fans(h, num_fans)

def run_thermal_displacement_recovery_test(h, heat_duration_sec=6, cool_duration_sec=10):
    import torch
    if not torch.cuda.is_available():
        print("PyTorch CUDA is not available for compute burst.")
        return

    num_fans = pynvml.nvmlDeviceGetNumFans(h)
    start_temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
    print(f"\n[TEST B: CONTROLLED HEAT SPIKE & EMERGENCY DISPLACEMENT RECOVERY]")
    print(f"Starting Baseline Temperature: {start_temp} deg C")
    print(f"Phase 1: Generating brief thermal load (~{heat_duration_sec}s CUDA tensor stress)...")
    
    try:
        # Phase 1: Controlled Compute Burst
        device = torch.device("cuda:0")
        t_end = time.time() + heat_duration_sec
        a = torch.randn(8192, 8192, device=device, dtype=torch.float16)
        b = torch.randn(8192, 8192, device=device, dtype=torch.float16)
        
        step = 0
        peak_temp = start_temp
        while time.time() < t_end:
            c = torch.matmul(a, b)
            torch.cuda.synchronize()
            step += 1
            if step % 20 == 0:
                cur_t = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
                cur_pwr = pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0
                if cur_t > peak_temp:
                    peak_temp = cur_t
                print(f"  [Heating] Temp: {cur_t} deg C | Draw: {cur_pwr:.1f}W")
                if cur_t >= 75:  # Hard safety ceiling
                    print("  Safety limit reached (75 deg C), cutting heat early!")
                    break

        peak_temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
        print(f"\nThermal Peak Reached: {peak_temp} deg C (+{peak_temp - start_temp} deg C above baseline)")
        
        del a, b, c
        torch.cuda.empty_cache()
        
        # Phase 2: Instant Heat Displacement via 100% Emergency Fan Blast
        print(f"\nPhase 2: Triggering 100% Emergency Fan Blast to Displace Heat...")
        for i in range(num_fans):
            pynvml.nvmlDeviceSetFanSpeed_v2(h, i, 100)
            
        t_cool_start = time.time()
        for elapsed in range(1, cool_duration_sec + 1):
            time.sleep(1)
            t_now = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            speeds = [pynvml.nvmlDeviceGetFanSpeed_v2(h, i) for i in range(num_fans)]
            pwr = pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0
            print(f"  [Cooling {elapsed:02d}s] Core Temp: {t_now} deg C | Fans: {speeds[0]}% / {speeds[1]}% | Draw: {pwr:.1f}W")
            
        recovered_temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
        cooling_delta = peak_temp - recovered_temp
        velocity = cooling_delta / cool_duration_sec
        print(f"\nTHERMAL DISPLACEMENT METRICS:")
        print(f" • Peak Heat Spike    : {peak_temp} deg C")
        print(f" • Recovered Temp     : {recovered_temp} deg C")
        print(f" • Heat Displaced     : -{cooling_delta} deg C in {cool_duration_sec}s")
        print(f" • Displacement Speed : {velocity:.2f} deg C/second")
        print("="*70)
        
    finally:
        restore_fans(h, num_fans)

if __name__ == "__main__":
    pynvml.nvmlInit()
    h = pynvml.nvmlDeviceGetHandleByIndex(0)
    print_telemetry_header(h)
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "info"
    if mode == "blast":
        run_fan_blast_test(h, duration_sec=10)
    elif mode == "recovery":
        run_thermal_displacement_recovery_test(h, heat_duration_sec=6, cool_duration_sec=10)
    else:
        print("Usage:")
        print("  python gpu_thermal_displacement_test.py blast     # Test 100% fan blast for 10s")
        print("  python gpu_thermal_displacement_test.py recovery  # Test thermal spike & heat displacement")
