# AI-BS ReAct Agent Architecture & Permanent Memory System

## Overview
This document outlines the core architecture of the Autonomous ReAct (Reason + Act) loop and the Living Learning Memory system integrated into the AI-BS Backend.

## The ReAct Loop (Polyglot Execution)
The AI-BS system has moved beyond standard conversational generation. It now possesses the ability to autonomously execute code, read the results, and self-correct.

1. **Trigger**: The LLM generates a tool call using the syntax `[TOOL: POLYGLOT]`.
2. **Interception**: The `AI_BS_Backend.py` stream generator intercepts the stream, pauses the output to the frontend, and extracts the code block.
3. **Execution**: The code is passed to the Polyglot Sandbox daemon for physical execution on the host machine.
4. **Feedback**: The raw `STDOUT` and `STDERR` (terminal output) are captured and injected back into the LLM's context as a hidden system prompt.
5. **Self-Correction**: The LLM analyzes the terminal output. If the code crashed, it automatically rewrites it and tries again. If it succeeded, it explains the results to the user.

## Living Learning Memory (Permanent Injection)
To ensure the LLM learns from its successes rather than forgetting them at the end of a session, a secondary autonomous tool was added.

1. **Trigger**: When the LLM successfully executes a complex task (e.g., math proofs, architectural logic, system scripts), it is instructed to use `[TOOL: MEMORY | "topic" | "knowledge"]`.
2. **Storage**: The backend intercepts this tool and autonomously writes the learned data to the Master Memory DB (`G:\AI-BS_Master_Memory\master_memory_dump.json`).
3. **Retrieval**: During future conversations, the Omni-Context Hybrid Retrieval system scans the Master Memory DB and re-injects this "Known-Good Baseline" into the LLM's context.

## Auto-Ingestion Mechanics
Because this file (`ReAct_Agent_Architecture.md`) exists on the local hard drive, the `Vault_Auto_Scanner` background daemon will automatically discover it. The scanner will sweep the file, chunk the markdown text, vectorize it using local embeddings, and store it into the `vault_index.json`. 

From that point forward, the AI-BS LLM will permanently understand its own backend architecture.

## Cloud UI & Remote Backend Tunneling
To prepare for the eventual release of a standalone APK and public SaaS model, the frontend and backend architectures have been fully decoupled.

1. **Cloud Frontend**: The Vite/React frontend is compiled and hosted publicly on Vercel. This allows the user to access the UI from any device (phone, laptop) without needing local build tools.
2. **Dynamic Routing**: The frontend uses a dynamic connection state stored in the browser's `localStorage`.
3. **Secure Tunneling**: A local daemon (`start_tunnel.bat`) spins up the secure Python FastApi server and automatically launches an `ngrok` TCP/HTTP tunnel. 
4. **Execution**: The user pastes the generated Ngrok URL into the Vercel Settings tab. The public frontend now seamlessly communicates with the private, local hardware to execute complex AI-BS workloads natively on the host GPU/CPU while preserving security.
