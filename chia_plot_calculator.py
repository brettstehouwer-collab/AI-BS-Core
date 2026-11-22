import psutil
import os

PLOT_SIZE_GB = 108.9  # Standard k=32 plot size in gigabytes

print("========================================")
print("     Chia Plot Capacity Calculator      ")
print("========================================")

drives_found = False
for part in psutil.disk_partitions(all=False):
    if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
        continue
    try:
        usage = psutil.disk_usage(part.mountpoint)
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        
        # Calculate how many full plots can fit in the free space
        possible_plots = int(free_gb // PLOT_SIZE_GB)
        
        print(f"\nDrive {part.device} ({part.fstype})")
        print(f"  Total Space: {total_gb:,.2f} GB")
        print(f"  Free Space:  {free_gb:,.2f} GB")
        print(f"  --> Can fit: {possible_plots} new k=32 plots")
        drives_found = True
    except PermissionError:
        continue
    except Exception as e:
        print(f"Could not read {part.device}: {e}")

if not drives_found:
    print("No valid hard drives found to scan.")

print("\n========================================")
print("Note: Plotting requires ~256 GB of TEMPORARY")
print("space on an SSD/NVMe drive during creation.")
print("========================================")
