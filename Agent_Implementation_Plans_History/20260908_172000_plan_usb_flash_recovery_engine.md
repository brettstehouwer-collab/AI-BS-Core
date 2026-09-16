# Implementation Plan: AI-BS USB Hardware Diagnostics & Flash Drive Recovery Engine (v5.222.0)

## Problem Statement
Following the physical connection of a USB flash drive (Drive `F:`, `PhysicalDrive3`), diagnostic discovery revealed the device was completely unmountable by Windows tools:
- Device reports `OperationalStatus: No Media` and `Size: 0 Bytes`.
- Disk Management and `diskpart` report "Virtual Disk Service error: There is no media in the device."
- Physical hardware identification via Win32 device descriptor revealed `Vendor: ChipsBnk`, `Product: Flash Disk`, `Revision: 5.00`, and parent PnP hardware ID `USB\VID_048D&PID_1234`.
- This VID/PID signature confirms the flash memory controller has crashed, lost its firmware microcode mapping, and fallen back into factory BootROM recovery mode.
- The user requested: *"can we just make our own flash tool to add to the AI-BS eco Steyem"*.

## Architecture & Technical Implementation

### Tier 1: Hardware Diagnostic & SCSI Pass-Through Router
- Location: `backend/modules/usb_recovery_router.py` and `backend/routers/usb_recovery_router.py`
- Endpoints:
  1. `GET /api/usb-recovery/devices`: Evaluates connected USB storage media, resolves parent USB VID/PID, checks `BOOTROM_SIGNATURES`, and classifies drive health (`bootrom_recovery`, `corrupted_partition`, `no_media_empty_reader`, `healthy`).
  2. `POST /api/usb-recovery/probe`: Issues `IOCTL_STORAGE_QUERY_PROPERTY` (0x002D1400) to extract hardware vendor, model, and revision strings directly from miniport device descriptors even when media is unmounted. Tests `IOCTL_SCSI_PASS_THROUGH` (opcode 0x12) and executes `ReadFile(Sector 0)` to verify LBA block read readiness.
  3. `POST /api/usb-recovery/rebuild-partition`: Enforces strict physical safety locks (`BusType == 'USB'`, blocks Disk 0, 1, 2 / System boot drives), clears corrupted partition tables, initializes MBR, creates maximum primary partition, and formats to target filesystem (`FAT32`, `exFAT`, `NTFS`).

### Tier 2: Frontend Diagnostics & Flasher Station
- Location: `frontend/src/components/UsbFlashRecoveryStation.jsx`
- Mounted into `frontend/src/components/PhoneRepairGuideTab.jsx` as Station 13 ("USB Flash Diagnostics & Flasher").
- Features:
  - Real-time device discovery cards with status badges and detected controller identification.
  - Low-level SCSI & LBA hardware register viewer with pass-through error reporting.
  - Interactive partition table rebuilder with explicit `confirm_destructive` safety toggle.
  - Mass-production flashing protocols for ChipsBank CBM209X, Phison PS2251, Silicon Motion SMI SM32XX, and Alcor Micro AU698X.
  - Hardware TSOP-48 test-point shorting procedures for reviving unresponsive controllers into BootROM mode.

### Tier 3: Safety Controls & Data Loss Prevention
- Permanent lock preventing any partition or format commands from targeting Disks 0, 1, or 2 (Samsung 980/990 PRO NVMe system drives `C:`, `D:`, `E:`).
- Strict validation that `BusType == 'USB'` and `IsBoot == false` and `IsSystem == false`.
