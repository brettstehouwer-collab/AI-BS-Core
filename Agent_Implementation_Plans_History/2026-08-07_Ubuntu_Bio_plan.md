# Offline AI-BS Subsystem: Bioinformatics & Cloud Emulation Architecture

This document outlines the architectural plan to integrate bioinformatics (PyMOL, Foldseek, MMseqs2, Clustal) and local cloud/mobile emulators (Firebase, Wrangler, Android CLI) into the AI-BS ecosystem for 100% offline, disaster-resilient operation.

## User Review Required

> [!IMPORTANT]
> **WSL2 Distribution Creation:** Since you strictly requested a dedicated WSL2 distribution (`Ubuntu-Bio`), I will provide the commands to clone or create this distribution. You may need to run the initial `wsl --import Ubuntu-Bio ...` command manually in PowerShell if you have a specific Ubuntu base image you prefer to use.

> [!CAUTION]
> **Drive Mounting:** The plan involves mounting `E:\WLS2BKUP` into WSL2. This requires the drive to be properly initialized in Windows and accessible to WSL. We will configure the `/etc/wsl.conf` in `Ubuntu-Bio` to auto-mount this.

## Open Questions

- What specific port would you like the `Ubuntu-Bio` FastAPI bridge daemon to run on? (Currently proposing `8085` to avoid conflicts with existing ports 8080, 8000, 8010, etc.)
- Do you have an existing Ubuntu `.tar` export you want to use as the base for `Ubuntu-Bio`, or should we pull a fresh Ubuntu 24.04 image from the Microsoft Store / Windows CLI?

## Proposed Changes

---

### Orchestration & Setup Scripts

#### [NEW] setup_ubuntu_bio.sh
This bash script will live in `C:\AI-BS\` (or a subfolder) and will automate the installation of all dependencies inside the `Ubuntu-Bio` container.
- Update `apt` and install base build essentials.
- Install Python, Node.js, and Java (required for Android CLI/Firebase).
- Download and extract binaries for MMseqs2, Foldseek, and Clustal Omega.
- Install Firebase CLI, Wrangler, and `uv` globally.
- Set up the Python virtual environment for the FastAPI bridge.

#### [MODIFY] Launch_AI_BS.bat
Inject a startup sequence to boot the new offline subsystem automatically.
```diff
  powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%vnc_bridge.exe' -WindowStyle Hidden"
  powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- systemctl start clore-hosting.service' -WindowStyle Hidden"
+ powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu-Bio -u root -- /opt/bio_bridge/start_fastapi.sh' -WindowStyle Hidden"
```
*And add a `WaitForPort 8085 "Ubuntu-Bio Bridge" 15` in the monitoring section.*

---

### Communication Layer (FastAPI Bridge)

#### [NEW] backend/ubuntu_bio_bridge/main.py
A lightweight FastAPI daemon running **inside** `Ubuntu-Bio`.
- Exposes REST endpoints to trigger offline executions of Foldseek, MMseqs2, and Wrangler commands.
- Returns JSON results to the primary Windows AI-BS backend.
- Will be configured to start automatically on boot via a bash script (`start_fastapi.sh`).

---

### Storage Configuration

#### [MODIFY] Ubuntu-Bio `/etc/wsl.conf`
We will configure the `Ubuntu-Bio` instance to automatically mount the `E:\WLS2BKUP` drive so that the massive bioinformatics databases are accessible at `/mnt/e/WLS2BKUP`.
```ini
[automount]
enabled = true
options = "metadata,uid=1000,gid=1000,umask=22"
```

---

## Verification Plan

### Automated Tests
- The FastAPI Bridge will include a `/ping` endpoint to verify the daemon is running and the `E:` drive is successfully mounted.

### Manual Verification
- We will execute `wsl -d Ubuntu-Bio -- Foldseek --help` from Windows to verify binary availability.
- Verify `E:\WLS2BKUP` is visible inside `Ubuntu-Bio` at `/mnt/e/WLS2BKUP`.
- Review the AI-BS startup logs to confirm the `Ubuntu-Bio Bridge (8085)` comes online successfully.
