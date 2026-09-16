# Phase 1 Tool Prioritization Matrix: Sovereign Architectural Implementation Plan

Implementation of the **Phase 1 Tool Prioritization Matrix** expanding AI-BS with 5 core backend tool modules, native REST routers on Port 8080, tool declarations in `ToolRegistry`, and frontend IDE integration across all 4 mirrors.

---

## 1. Scope & Tool Architecture Overview

| Tool Module | Target Workflow | Core Capabilities & Technical Architecture |
|---|---|---|
| **Pandoc & Typst Engine** | Stehouwer Publishing LLC | • Map raw text/markdown/contract payloads to KDP-compliant print-ready PDFs.<br>• Sub-50ms Typst C-binding & `typst.exe` compiler.<br>• KDP trim size templates (6x9, 8.5x11), running headers, and interior margins.<br>• Pandoc multi-format converter. |
| **Demucs Audio Separator** | Local Audio Processing / Suno AI | • Local PyTorch/CUDA stem separation (`htdemucs`) on NVIDIA RTX 4090.<br>• Discrete stem extraction: `vocals`, `drums`, `bass`, `other` (accompaniment).<br>• Direct export into DAW project folders (`saved_data/audio_stems/<session>/`).<br>• Instrumental-only and Acapella-only strip pipelines. |
| **PowerShell Process Manager** | Developer Environment Maintenance | • Elevated PowerShell runner targeting `-ExecutionPolicy Bypass`.<br>• Background Google Chrome profile sync manager (locks, profiles, reconciliation).<br>• Directory state inspector (SHA256 integrity, 4-mirror parity, disk sizing).<br>• Daemon process lifecycle monitor with PID/resource tracking. |
| **TShark Telemetry Monitor** | Hardware Diagnostics & Mining | • Local packet extraction tool using `tshark.exe` (v4.6.8) and Scapy sniffer.<br>• Live API traffic probe for ChromaDB (`8001/8002`) and vLLM/Ollama (`11434/11435`).<br>• Pearl mining Stratum telemetry auditor (Port `8335` / HeroMiners hash/share packets).<br>• Network health, packet drops, and local-first architecture stability metrics. |
| **ComfyUI API Trigger** | Image Processing & Matting | • Dynamic ComfyUI workflow JSON mapping onto high-level REST endpoints.<br>• Pass system image paths directly to background matting nodes (`RMBG-1.4`, `BiRefNet`).<br>• Super-resolution upscaling nodes (`RealESRGAN_x4plus`, `4x-UltraSharp`).<br>• Asynchronous execution, polling, and media extraction on Port `8189`. |
