# AI-BS (Autonomous Intelligence & Build System)
### High-Performance Sovereign AI Ecosystem & Autonomous Workstation Core
**Architect & Copyright Holder:** Brett Stehouwer / Stehouwer Publishing  
**Official Inquiries & Licensing:** [brettstehouwer@gmail.com](mailto:brettstehouwer@gmail.com)  
**License:** Source-Available Non-Commercial & Peer-Review Evaluation License (All Commercial Rights Reserved)

---

## ⚠️ Proprietary Notice & Legal Terms of Viewing

> [!IMPORTANT]
> **PLEASE READ CAREFULLY BEFORE INSPECTING OR CLONING THIS REPOSITORY.**  
> This repository contains proprietary architecture, custom IPC bridges, novel daemon orchestration, and software designs developed by **Brett Stehouwer**. 
>
> Viewing or accessing this repository **does NOT grant any commercial license or right to copy, replicate, or monetize** these systems.

### 1. Permitted Uses (Inspection, Peer Review & Auditing)
Fellow software engineers, systems architects, and security researchers are expressly granted permission to:
- **Inspect & Study:** Read and examine the source code, scripts, configuration files, and documentation for educational purposes and architectural evaluation.
- **Audit & Identify Discrepancies:** Evaluate system mechanics, identify race conditions, spot discrepancies in logic or data flows, and review hardware integration.
- **Submit Feedback & Discrepancies:** Open [GitHub Issues](https://github.com/brettstehouwer-collab/AI-BS-Core/issues) or submit pull requests to document discrepancies, bug reports, or performance optimizations for review.

### 2. Strict Commercial & Proprietary Prohibitions
Without an explicit, executed written commercial license agreement signed by Brett Stehouwer, you may **NOT**:
- **Commercial Deployment:** Deploy, execute, host, or integrate any part of this software for business, commercial, enterprise, or revenue-generating purposes.
- **Idea & Architectural Replication:** Extract, copy, re-implement, or adapt proprietary workflows, the 18-port collision matrix, or autonomous agent algorithms to produce competing software or commercial services.
- **Redistribution & Reselling:** Sell, sub-license, repackage, distribute, or publish this codebase or its derivatives under another name, organization, or open-source license.
- **Automated AI Scraping & Training:** Scrape, ingest, crawl, or process this repository to train, fine-tune, or validate machine learning models or commercial AI systems.

### 3. Commercial Licensing, Fees & Statutory Enforcement
- **Enterprise & Commercial Inquiries:** If your organization wishes to deploy, license, or integrate AI-BS technology, contact: **[brettstehouwer@gmail.com](mailto:brettstehouwer@gmail.com)**.
- **Statutory Infringement Warning:** Any unauthorized commercial exploitation, distribution, or intellectual property theft is subject to civil and criminal liability, including statutory damages of up to **$150,000 per willful infringement** under 17 U.S.C. § 504(c), injunctive relief, and recovery of legal fees.

---

## 🔍 Purpose: Open Architecture for Human-Eye Auditing

AI-BS is made source-available so that seasoned engineers can inspect how the entire ecosystem connects from end to end. We value precision and encourage technical reviewers to inspect our pipelines with a human eye:
- **Architectural Cohesion:** How our Windows 11 host orchestration coordinates with WSL2 Ubuntu environments.
- **Concurrency & IPC:** How the high-speed shared memory (SHM) ring buffers, telemetry daemons, and WebSocket channels avoid contention.
- **Discrepancy Reporting:** If you notice a mismatch between frontend state and backend routers, an unhandled error state, or a redundant call pattern, please report it via GitHub Issues.

---

## 🗺️ System Architecture & How Everything Functions

AI-BS bridges desktop UI engineering, local sovereign AI, hardware-accelerated media rendering, and cross-platform daemons into a unified workstation:

```
                                 ┌─────────────────────────────────┐
                                 │    Vite Desktop Studio (:5173)   │
                                 │     React 19 + Glassmorphism    │
                                 └────────────────┬────────────────┘
                                                  │ WebSocket / REST
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │   FastAPI Core Engine (:8080)   │
                                 │    Router, Auth, State Vault    │
                                 └───────┬───────────────┬─────────┘
                                         │               │
                      ┌──────────────────┴──┐         ┌──┴──────────────────┐
                      │                     │         │                     │
                      ▼                     ▼         ▼                     ▼
          ┌───────────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │ Sovereign Reasoning   │ │ NVENC Studio │ │ ChromaDB     │ │ WSL2 Linux   │
          │ Local Ollama / VLM    │ │ Media Vault  │ │ Vector Store │ │ GPU Mining & │
          │ (:11434 / :11435)     │ │ (:8088)      │ │ (:8002)      │ │ Daemons      │
          └───────────────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### Core Subsystems

#### 1. Desktop Studio (`frontend/`)
- **Technology:** React 19, Vite, Vanilla CSS design tokens with custom glassmorphic styling.
- **4-Pillar Navigation:** Categorizes operations into **Creation Studio**, **Intelligence & Agents**, **System & Hardware Operations**, and **Vault & Media Records**.
- **Media & Screenwriting:** Includes the Fountain screenplay script adapter, dynamic Character Vault modals, and BV-Media Audio/Video creator with real-time waveform inspection.

#### 2. FastAPI Core Engine (`backend/`)
- **Technology:** Python 3.10+ ASGI backend powered by FastAPI and Uvicorn on port `8080`.
- **Capabilities:** Manages system telemetry, token tracking, character profile vaults, automated prompt enhancement, and session persistence.

#### 3. Sovereign AI & Local LLM Cluster
- **Local Inference:** Fully local, privacy-preserving LLM execution running on dedicated ports `11434` (Ollama Host) and `11435` (Ollama Extended Drive).
- **Zero-Cost Mandate:** Operates entirely without paid commercial third-party APIs, running quantized open weights locally on RTX 4090 hardware.

#### 4. The 18-Port Collision Matrix
To eliminate dynamic socket race conditions across background daemons, ports are statically mapped:
- `80`: Nginx Gateway
- `3001`: Node Backend Service
- `4455`: OBS Studio WebSocket
- `5173`: Vite Development Studio
- `8000`: Go Telemetry Gateway
- `8002`: ChromaDB Vector Store
- `8005`: Broadcast Kernel Daemon
- `8006`: Social Hub & IRC Dispatcher
- `8007`: Crypto Swarm & Scalp Daemon
- `8010`: Shared Memory (SHM) Telemetry Bridge
- `8013`: VST3 Audio Bridge
- `8080`: FastAPI Core Engine
- `8085`: Ubuntu-Bio Bridge
- `8088`: NVENC Hardware Streamer & Video Kernel
- `8089`: WSL HLS Ingest Stream
- `8099`: Gemini Protocol Bridge
- `8189`: ComfyUI Screenplay / Secondary Pipeline
- `8888`: Unreal Engine WebRTC Signaling Server
- `11434`: Primary Ollama LLM Host
- `11435`: Secondary / Extended Drive Ollama Instance

#### 5. Cross-Platform Windows 11 & WSL2 Integration
- Orchestrates Windows 11 PowerShell execution (`-ExecutionPolicy Bypass`) with dual Ubuntu distributions in WSL2 (`Ubuntu` and `Ubuntu-24.04`) for distributed workload acceleration.

---

## 🛠️ Local Inspection & Setup (For Peer Reviewers)

To run and inspect the ecosystem locally for non-commercial evaluation:

### Prerequisites
- **Operating System:** Windows 11 Pro with WSL2 enabled.
- **Hardware Recommended:** NVIDIA RTX 40-series GPU (RTX 4090 optimal).
- **Runtimes:** Python 3.10+, Node.js 20+, Git.

### Quick Inspection Launch
1. Clone the repository for inspection:
   ```powershell
   git clone https://github.com/brettstehouwer-collab/AI-BS-Core.git
   cd AI-BS-Core
   ```
2. Launch the dev ecosystem:
   ```powershell
   .\Launch_AI_BS_Dev.bat
   ```
3. Open your browser to the local studio:
   ```
   http://localhost:5173
   ```

---

## 📬 Reporting Discrepancies & Contact

If you inspect the code and discover discrepancies, bugs, or architectural improvements:
- **Bug Reports & Feedback:** Open an issue at [GitHub Issues](https://github.com/brettstehouwer-collab/AI-BS-Core/issues).
- **Commercial & Enterprise Inquiries:** Contact Brett Stehouwer directly at **[brettstehouwer@gmail.com](mailto:brettstehouwer@gmail.com)**.

---
*Copyright © 2026 Brett Stehouwer / Stehouwer Publishing. All Rights Reserved. No commercial use or unauthorized reproduction permitted.*
