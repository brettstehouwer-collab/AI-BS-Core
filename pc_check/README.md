# Mom's PC Diagnostic & Health Check Guide

## 1. Target Hardware Specifications & Baseline

- **Processor (CPU):** AMD Ryzen 5000 Series (Quad-Core / 8-Thread, e.g., 5400U / 5300G).
- **Storage:** Samsung 980 NVMe SSD (PCIe 3.0 x4, ~3,500 MB/s sequential read).
- **System Memory (RAM):** 8.0 GB DDR4/LPDDR4x.
  - *Usable Memory:* ~6.5 GB – 7.2 GB (512 MB – 1.5 GB is dynamically hardware-reserved by the AMD Radeon Vega integrated graphics).
- **Graphics (GPU):** Integrated AMD Radeon Graphics (Shared VRAM).

---

## 2. Hardware Capabilities & Operational Boundaries

### What the PC CAN Do
1. **Run Antigravity Google IDE for Diagnostics & Code:**
   - The Samsung 980 NVMe ensures fast application launch times.
   - All AI reasoning and agent intelligence run on Google Cloud servers; zero local VRAM or GPU compute is required.
2. **Execute Full System Triage & OS Repairs:**
   - Automated health scans (PowerShell WMI/CIM queries, driver verification, event log auditing).
   - Windows file system repair (`sfc /scannow`, `DISM.exe /Online /Cleanup-Image /RestoreHealth`).
   - Startup item pruning and telemetry/bloatware cleanup.
3. **Hardware Health Verification:**
   - NVMe SMART status, drive wear percentage, and temperature checks.
   - Memory integrity testing via Windows Memory Diagnostic (`mdsched.exe`).
   - Brief CPU thermal checks (observing fan and temperature curves under short load).

### What the PC CANNOT (or Should Not) Do
1. **No Local LLM / Neural Network Inference:**
   - **Do not run Ollama or local open-weights models (e.g., Llama 3 8B, Mistral, DeepSeek)**. 8 GB of shared system RAM cannot hold model weights and context without extreme swap thrashing or system lockups.
2. **No Heavy Multitasking with the IDE Open:**
   - Do not run Antigravity IDE (~1.0–1.2 GB) concurrently with Chrome/Edge holding 15+ tabs (~2.0 GB) and background apps (Spotify, Discord, etc.).
3. **No Heavy Virtualization or Containers:**
   - Do not launch heavy Docker Desktop containers, multi-GB WSL2 instances, or VirtualBox/VMware virtual machines (a 4 GB VM will immediately exhaust available RAM).
4. **No Extended Power-Virus Stress Tests:**
   - Avoid sustained Prime95 Small FFTs or FurMark loops if the PC is a compact desktop or thin-and-light laptop, to prevent unnecessary thermal throttling on modest OEM coolers.

---

## 3. Preparation Checklist Before Installing / Running Antigravity IDE

1. **Verify Windows Pagefile on the Samsung 980 NVMe:**
   - Ensure the Windows virtual memory paging file is located on the Samsung 980 NVMe (Fast NVMe paging prevents hard application crashes when physical RAM crosses 90%).
   - Setting: `SystemPropertiesAdvanced.exe` > Performance Settings > Advanced > Virtual Memory > Ensure "Automatically manage paging file size for all drives" is checked, or set a custom 8192 MB – 16384 MB size on the C: drive.
2. **Close Background Applications:**
   - Exit web browsers, cloud sync clients (OneDrive, Google Drive), and game launchers before launching deep diagnostic scans.
3. **Free Storage Space:**
   - Maintain at least 15–20 GB of free space on the Samsung 980 NVMe to ensure TRIM and wear leveling operate efficiently.

---

## 4. Diagnostic Scripts Included in this Directory

- **`run_pc_health_check.ps1`**: Lightweight, zero-dependency PowerShell script that audits CPU, RAM, NVMe health, top resource processes, and recent system crash logs. Generates `pc_health_report.txt`.
- **`Run_Health_Check.bat`**: One-click launcher to run the PowerShell check as Administrator without typing commands.

---

## 5. Quick Command Reference for Manual Triage

Run these in an elevated PowerShell/Terminal window:

```powershell
# 1. System File Checker (Verify & repair corrupted Windows files)
sfc /scannow

# 2. DISM Component Store Health (Fix Windows system image)
DISM.exe /Online /Cleanup-Image /RestoreHealth

# 3. Check NVMe Drive Health via Windows Storage Management
Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, OperationalStatus, HealthStatus

# 4. Check Motherboard & BIOS Version
Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, Version
Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, ReleaseDate

# 5. Check System Memory Distribution
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory, TotalVirtualMemorySize, FreeVirtualMemory
```
