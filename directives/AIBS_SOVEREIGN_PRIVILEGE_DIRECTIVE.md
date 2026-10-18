# AI-BS SOVEREIGN EXECUTION & PRIVILEGE DIRECTIVE
**Directive ID:** AIBS-DIR-000-ROOT-AUTHORITY  
**Target Environment:** Windows 11 x86_64 | AMD Ryzen 9 9950X (16-Core / 32-Thread) | NVIDIA GeForce RTX 4090 (24GB VRAM) | ASUS TUF GAMING X870-PLUS WIFI  
**Core Executables:** `C:\AI-BS\native_studio\dist\AI_BS_Studio\AI_BS_Studio.exe` | `C:\AI-BS\backend\dist\brain_backend.exe` | `C:\AI-BS\go_gateway\aibs_engine.exe` | `C:\AI-BS\.temp_executor` (`G:\Stehouwer_Server\Projects\.temp_executor` auto-mapped)  
**Enforcement Status:** MANDATORY / PRE-APPROVED AUTONOMOUS EXECUTION

---

## 1. PRIVILEGE STRATIFICATION & EXECUTION MATRIX

AI-BS enforces a strict five-tier privilege routing model across User Mode (Ring 3), Kernel Mode (Ring 0), and Hypervisor partitions (Ring -1) to maximize hardware throughput without sacrificing system stability.

| AI-BS Subsystem | Target Execution Tier | Security Context / Ring | Assigned Authority & Scope |
| :--- | :--- | :--- | :--- |
| **UI & Workspace Orchestrator** (`AI_BS_Studio.exe`) | Tier 1: Elevated User Mode | Ring 3 (`High` Integrity Admin) | PyQt6/Win32 native windowing, zero-copy shared memory (`shm`) IPC host, local filesystem read/write across `C:\AI-BS` and `G:\Stehouwer_Server`. |
| **Multi-Agent CLI & Service Dispatcher** (`brain_backend.exe` / `AI_BS_Backend.py`) | Tier 2: Local System | Ring 3 (`NT AUTHORITY\SYSTEM` / Admin) | Unrestricted background daemon management, socket/port binding across the 25-port matrix, process spawning, and token impersonation. |
| **OS Provisioning & Registry Engine** | Tier 3: TrustedInstaller | Ring 3 (`SYSTEM` + `TrustedInstaller`) | Full DACL write authority over `System32`, Windows services, Defender exclusions, and system-level dependency installation. |
| **Hardware Telemetry, MSR & VRAM Clamping** | Tier 4: Kernel Mode Driver | Ring 0 (`.sys` / VTL 0) | Direct CPU Model-Specific Register (MSR) read/write, PCIe BAR / GPU VRAM aperture telemetry, and hardware power-state clamping. |
| **Linux Subsystem Bridge & Sandbox** (`wsl.exe`) | Tier 5: Hypervisor Partition | Ring -1 (`hvax64.exe` / AMD-V) | Co-execution of Linux toolchains via WSL2 with HVCI (VTL 1 Memory Integrity) disabled to prevent hypervisor page locks from blocking Ring 0 MSR/telemetry drivers. |

---

## 2. AUTONOMOUS EXECUTION & TERMINAL GOVERNANCE

1. **Pre-Approved Action Mandate:** All build scripts, file synchronizations, code refactorings, and process orchestrations initiated within the AI-BS ecosystem are pre-approved. Agents must execute tasks to completion without gating prompts or confirmation dialogs.
2. **Shell Routing Standard:**
   * **Windows Native:** Execute via `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass`.
   * **Linux / POSIX Targets:** Execute via `wsl.exe -e bash -c "<command>"` (or `wsl.exe -d <distro> -- bash -lc "<command>"`).
3. **The Two-Strike Diagnostic Halt Rule:** If any shell command, compilation pass, or IPC call fails **twice consecutively**, the executing agent must immediately halt the retry loop, capture `stderr` and exit codes, log the fault vector to SQLite/ChromaDB (`ai_bs_error_heuristics`), and run Stage 1 root-cause diagnostics (`qwen2.5-coder` grammar-locked JSON auto-heal) before attempting an alternative path.
4. **ReAct Sandbox Isolation:** Unverified generated code and automated error-feedback loops execute inside `C:\AI-BS\.temp_executor` (with automatic path resolution for `G:\Stehouwer_Server\Projects\.temp_executor` whether `G:\` is mounted or unmounted) prior to merging into production directories.

---

## 3. TOKEN ELEVATION & TIER 3 (`TrustedInstaller`) ESCALATION PROTOCOL

When an AI-BS agent requires modification of OS-protected binaries, service ACLs, or locked registry hives that reject standard `Administrator` access, `brain_backend.exe` escalates via parent-process token inheritance:

```powershell
# AI-BS Tier 3 Escalation Payload (SYSTEM + TrustedInstaller Token Inheritance)
sc.exe config TrustedInstaller start= demand | Out-Null
sc.exe start TrustedInstaller | Out-Null

if (Get-Module -ListAvailable -Name NtObjectManager) {
    Import-Module NtObjectManager -ErrorAction Stop
    $tiProcess = Get-NtProcess -Name "TrustedInstaller.exe"
    $cmdArgs   = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File C:\AI-BS\scripts\elevated_task.ps1"
    New-Win32Process -CommandLine $cmdArgs -CreationFlags NewConsole -ParentProcess $tiProcess
}
```

---

## 4. RING 0 HARDWARE ACCESS & VTL 1 DE-CLAMPING STANDARD

To allow AI-BS hardware controllers to read/write AMD Ryzen 9 9950X MSRs, poll RTX 4090 PCIe BAR telemetry, and load custom signed `.sys` drivers while keeping WSL2 active:
1. **Hypervisor Coexistence (`hypervisorlaunchtype auto`):** Keep the AMD-V hypervisor active strictly for WSL2 containerization.
2. **Disable VTL 1 Memory Integrity (HVCI):** Prevent `securekernel.exe` from locking Ring 0 physical memory pages or blocking hardware telemetry drivers:
```powershell
reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity" /v "Enabled" /t REG_DWORD /d 0 /f
```
3. **Local Cryptographic Signing Chain:** All compiled AI-BS executables (`AI_BS_Studio.exe`, `brain_backend.exe`, `aibs_engine.exe`) and custom `.sys` drivers are signed using the local **AI-BS Sovereign Root Authority** 4096-bit RSA SHA-256 X.509 certificate enrolled in `Cert:\LocalMachine\Root` and `Cert:\LocalMachine\TrustedPublisher`.

---

## 5. DATA INTEGRITY, TELEMETRY & ETHICAL ARCHITECTURE

1. **Zero Cloud Leakage:** All vector embeddings (ChromaDB Port 8001), LLM weights (Ollama Ports 11434/11435), and IPC shared memory buffers remain strictly local.
2. **Real-Time Hardware Telemetry:** GPU VRAM allocation, PCIe bandwidth, CPU thread saturation, and IPC latency metrics stream in real time without quantitative masking.
3. **Immutable Transcription (Fire Writing Enforcement):** Any personal creative prose or manuscript payload ingested by AI-BS retains 100% of its original vocabulary and spelling. Automated passes are restricted strictly to periods, capitalization, and paragraph breaks.
4. **Pagination & Deterministic Feeds:** Internal dashboard tables and log viewers enforce deterministic chronological or categorical sorting with a 10-item page boundary and manual pagination.
