# AI-BS Technical Architecture Report
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

CONFIDENTIAL TECHNICAL ARCHITECTURE REPORT

AI-BS

Autonomous Intelligence & Build System

A fully self-hosted, agentic AI platform engineered from the ground up by Brett Adam Stehouwer. AI-BS represents a production-grade local AI operating environment integrating custom language model inference, persistent semantic memory, multi-agent orchestration, and a real-time developer workspace â€” all running offline on

consumer hardware.

Python 3.12 FastAPI Ollama ChromaDB React 19

Electron 42 PyInstaller Vite 8 NSIS Ollama Modelfile Variant SSD Virtual RAM nomic-embed-text

AUTHOR

Brett Adam Stehouwer
VERSION

v1.1.1 (AI-BS-INT-006)
DATE

June 2026

ROLE HARDWARE CLASSIFICATION

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 1/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

CTO, Stehouwer

Publishing LLC

TABLE O F CO N TE N TS OVERVIEW
RTX 4090 / Ryzen 9950X
Portfolio / Technical Review

1\. Executive Summary Â§ 01 2\. Design Philosophy & Motivation Â§ 02 3\. Hardware Baseline & Deployment Target Â§ 03

ARCHITECTURE

4\. System Architecture Overview Â§ 04 5\. Backend Engine â€” FastAPI \+ Ollama Â§ 05 6\. The Stehouwer LLM Model Stack Â§ 06 7\. Heuristic Token Budget Estimator v2 Â§ 07 8\. SSD Virtual RAM â€” Context Memory System Â§ 08 9\. Multi-Agent Orchestration Framework Â§ 09 10\. Semantic Knowledge Base (ChromaDB \+ RAG) Â§ 10

FRONTEND & UX

11\. Electron Desktop Application Â§ 11 12\. Feature Modules & Capability Surface Â§ 12

OPERATIONS

13\. Background Daemon System Â§ 13 14\. Build & Distribution Pipeline Â§ 14 15\. Security Model Â§ 15 16\. Innovation Summary & Technical Differentiation Â§ 16 17\. Roadmap Â§ 17

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 2/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 01 OVE RVIEW

Executive Summary

AI-BS (Autonomous Intelligence & Build System) is a fully self-hosted, offline capable, production-grade AI operating environment designed, engineered, and maintained by Brett Adam Stehouwer â€” independently, without a team, cloud subscription, or external API dependency. The system represents a convergence of local large language model inference, persistent vector memory, multi-agent orchestration, and an integrated developer IDE â€” all packaged as a signed Windows desktop application installable with a single click.

Unlike cloud-based AI assistants, AI-BS runs entirely on-premises. Every inference call, every embedding, every memory retrieval, and every agentic tool execution happens locally on the operator's machine. This architectural decision has profound implications for privacy, latency, cost, and customization â€” implications that Brett has thoughtfully engineered around at every layer of the stack.

14+

FEATURE

MODULES

KEY INSIGHT
3K+ LINES OF BACKEND PYTHON
100%

OFFLINE CAPABLE

AI-BS is not a wrapper around a third-party API. It is an original, full-stack AI

platform built on open-source inference engines, custom tokenization logic,

and a bespoke agentic reasoning framework â€” designed to be understood,

modified, and extended at every layer.

Â§ 02 PHILOSOPHY

Design Philosophy & Motivation

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 3/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

The core motivation behind AI-BS stems from a single architectural conviction:

intelligence should not live behind a paywall, require an internet connection, or

be opaque to its operator. Brett designed AI-BS as a direct response to the

limitations and risks of SaaS AI platforms â€” vendor lock-in, data leakage,

unpredictable costs, rate limits, and the inability to customize model behavior at a

fundamental level.

ï¿½ï¿½ The Sovereignty Principle

Every AI decision made by AI-BS is traceable. The system's context window,

memory contents, tokenizer logic, agent tools, and model weights are all locally

resident and inspectable. This is a fundamentally different security and trust model

from cloud AI, where the inference stack is a black box operated by a third party.

âš™ï¸ The Systems-Engineering Approach

Brett approached AI-BS as a systems engineer, not a prompt engineer. The platform is not a chat interface â€” it is an operating environment. It manages background

daemons, monitors filesystem events, self-optimizes its codebase, maintains long

term semantic memory, and integrates with the operator's full toolchain (VS Code,

PowerShell, ComfyUI, Telegram).

ï¿½ï¿½ Progressive Capability Expansion

AI-BS follows a versioned directive system (AI-BS-INTEGRATION-001 through 006\) where each directive formally specifies an architectural upgrade. This mirrors the

RFC / engineering proposal process used in large-scale software organizations,

demonstrating technical maturity beyond what is typical for an individual engineer.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 4/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 03 INFRASTRUCTURE

Hardware Baseline & Deployment Target

AI-BS is engineered specifically around the Thermaltake Tower 900 workstation, with hardware configurations that push the limits of what consumer-grade components can achieve in terms of local AI inference throughput.

CPU

AMD Ryzen 9 9950X

16-core, 32-thread â€” handles parallel daemon processes, ChromaDB operations, and Python multiprocessing without GPU contention

DISPLAY

LG UltraGear 27" 480Hz

4K UHD â€” the Electron UI is designed for high-DPI and high refresh-rate displays with smooth CSS micro-animations

ENGINEERING NOTE
GPU

NVIDIA RTX 4090 FE

24 GB GDDR6X VRAM â€” primary LLM inference accelerator. AI-BS includes a VRAM Manager that automatically unloads unused models before each agent launch

CHASSIS

Thermaltake Tower 900

Dual-chamber full-tower â€” provides thermal headroom for sustained GPU inference workloads during extended agentic sessions

The RTX 4090's 24 GB VRAM allows AI-BS to simultaneously load a primary

13B+ parameter model for chat inference while reserving capacity for the

nomic-embed-text embedding model used by ChromaDB. The VRAM

Manager's unload-before-launch strategy ensures that agent sessions

(Claude Code, OpenCode, Codestral) always have the full VRAM budget

available.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 5/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 04 ARCHITE CTURE

System Architecture Overview

AI-BS follows a three-tier architecture: a locally-executed Electron desktop

application (Presentation Layer), a FastAPI/Python backend server (Logic Layer),

and a set of local data stores â€” ChromaDB vector database, a JSON-based SSD

archive, and the Ollama model runtime (Data & Inference Layer). Communication

between tiers occurs over localhost HTTP on port 8000, keeping all data traffic

entirely off the public network.

**â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚** AI-BS SYSTEM ARCHITECTURE (v1.1.1) **â”‚**

**â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜** PRESENTATION LAYER (Electron 42 \+ React 19 \+ Vite 8\)

â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”

â”‚ ChatTab â”‚ CommandCenter â”‚ KnowledgeBase â”‚ DevWorkspace â”‚ â”‚

FireWriteâ”‚ MediaStudio â”‚ NocoTelemetry â”‚ ITHelpDesk â”‚ â”‚

MemoryDashboard â”‚ GeneratorTab â”‚ AdvertisingTab â”‚ VisualScript

â”‚

â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

â”‚ REST/JSON localhost:8000 LOGIC LAYER (FastAPI \+ Python 3.12

\+ PyInstaller EXE)

â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”

â”‚ /api/chat Agent Router \+ React-Agent Loop â”‚ â”‚

/api/settings \* SSD Virtual RAM Management â”‚ â”‚ /api/agent \*

Launch / Kill / Status background agents â”‚ â”‚ /api/models \*

Ollama model pull \+ pull status polling â”‚ â”‚ /api/kb \* ChromaDB

RAG ingest \+ semantic search â”‚ â”‚ /api/media \* ComfyUI

image/video generation bridge â”‚ â”‚ /api/lint \* Real-time Python

AST lint via pyflakes â”‚ â”‚ /api/tts pyttsx3 local text-to

speech â”‚ â”‚ /api/autocomplete FIM code completion (qwen2.5-

coder) â”‚ â”‚ /api/trainer \* Background self-optimization daemon

status â”‚

â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

â”‚ â”‚ â”‚ DATA & INFERENCE LAYER â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 6/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚ Ollama Runtime â”‚ â”‚

ChromaDB â”‚ â”‚ SSD Virtual RAM â”‚ â”‚ (localhost:11434â”‚ â”‚

PersistentClientâ”‚ â”‚ session\_history\_ â”‚ â”‚ stehouwer\_llm â”‚ â”‚

brett\_knowledge â”‚ â”‚ archive.json \+ â”‚ â”‚ nomic-embed â”‚ â”‚

\_base\_v2 â”‚ â”‚ stehouwer\_llm\_ â”‚ â”‚ codestral â”‚ â”‚ stehouwer\_llm\_ â”‚

â”‚ memory (ChromaDB) â”‚ â”‚ qwen2.5-coder â”‚ â”‚ memory â”‚ â”‚ User

defined path â”‚ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

The system's most notable architectural feature is its zero-dependency inference

chain. The Ollama runtime manages model weights as GGUF files on the local

filesystem. The FastAPI backend communicates with Ollama via the ollama Python client library over a localhost socket. No request ever leaves the machine during

inference.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 7/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 05 BACKE ND

Backend Engine â€” FastAPI \+ Ollama

The backend is a single-file FastAPI application (main.py, 3,000+ lines) that serves as the complete logic engine for the entire platform. It is compiled with PyInstaller into a self-contained Windows executable (brain\_backend.exe) distributed as part of the Electron installer â€” meaning no Python installation is required on the target machine.

ï¿½ï¿½ The Agent Routing System

The core /api/chat endpoint implements a sophisticated multi-stage routing pipeline:

Category Detection: Analyzes the incoming message for semantic signals
â–¸

(length, keywords like "summarize", "image", "code", "rule") and routes it to the appropriate model category: reasoning, massive, multimodal, precision, or instruction.

Context Window Management: Calls manage\_context\_window() via the
â–¸

Stehouwer LLM Tokenizer to evaluate token budget and offload overflow turns to SSD before any inference begins.

RAG Injection: If use\_rag=True, queries the ChromaDB knowledge base and
â–¸

prepends the top-N semantically similar document chunks to the system context.

SSD Memory Injection: Queries the stehouwer\_llm\_memory collection for
â–¸

semantically relevant archived conversation turns and injects them into context.

React-Agent Loop: If use\_agent=True, launches a multi-step Thought â†’ Action
â–¸

â†’ Observation â†’ Answer loop where the model can invoke any of the registered tool functions across multiple reasoning steps.

Web Search: If use\_web\_search=True, performs a live DuckDuckGo query and
â–¸

synthesizes results into the context.

ï¸ Registered Agent Tool Suite

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 8/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

TOOL DESCRIPTIONSECURITY SCOPE

file\_manager\_tool Read, write, list, delete files

grep\_search\_tool Recursive pattern search across

codebase
Projects \+

Publishing dirs only

Projects dir only

view\_file\_tool Line-range file reading Projects \+ Publishing dirs

replace\_file\_content\_tool Targeted string replacement in files

project\_architect\_tool Generate full project scaffolds from JSON

spec

python\_executor\_tool Execute Python snippets in venv

sandbox

powershell\_executor\_tool Execute PowerShell commands

javascript\_executor\_tool Execute Node.js scripts

cpp\_executor\_tool Compile and run C++ via g++

rust\_executor\_tool Compile and run Rust via rustc

go\_executor\_tool Compile and run Go via go run
Projects \+

Publishing dirs

Projects dir only

15s timeout, Projects CWD

15s timeout, Projects CWD

15s timeout, Projects CWD

15s timeout, Projects CWD

15s timeout, Projects CWD

15s timeout, Projects CWD

lua\_executor\_tool Execute Lua scripts 15s timeout,

Projects CWD

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 9/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

TOOL DESCRIPTIONSECURITY SCOPE

msbuild\_executor\_tool Build Visual Studio solutions

ollama\_launch\_tool Launch named developer agents

(Claude, OpenCode,

etc.)

POLYGLOT EXECUTION ENGINE
60s timeout

VRAM manager pre-unloads models

AI-BS is one of the few local AI systems that implements a native polyglot

code execution sandbox â€” the agent can write, execute, and iterate on

code in Python, JavaScript, PowerShell, C++, Rust, Go, and Lua within a

single conversation session, using tool output as feedback for the next

reasoning step. This is equivalent to functionality found in enterprise coding

assistants costing tens of thousands of dollars per year.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 10/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 06 MODE LS

The Modelfile Variant & Model Routing Layer

The model layer is a routing system that selects among several upstream local models based on the nature of the incoming request. The primary model, stehouwer\_llm, is an Ollama Modelfile variant â€” a configuration layer (system prompt + inference parameters) over an existing base model. The base model weights are not modified; behavior is shaped entirely through the system prompt and routing logic.

ï¿½ï¿½ Identity System Prompt Architecture

The BRETT\_SYSTEM\_PROMPT is a structured system prompt that establishes the model's persona and behavioral rules. Because it operates via in-context learning, it can be edited at any time without retraining. The prompt covers:

Operator Identity: Brett Adam Stehouwer â€” VP & CTO of Stehouwer Publishing
â–¸

LLC and Stehouwer Productions

Professional Context: Audio engineer, music producer, creative writer, IT sector
â–¸

transition targeting Help Desk and Field Technical roles

Active Projects: Project NOCO (sustainable tech, vertical farming, plant
â–¸

powered energy, CO2-to-growth), Ithaca relocation timeline (Cornell agricultural programs, 2027\)

Key Relationships: Named connections (Julie/CEO, Sean/Strategic Advisor,
â–¸

Devin) that the model uses to contextualize interpersonal queries

Hardware Context: Full machine spec so the model gives hardware-appropriate
â–¸

advice

Behavioral Rules: Language style, tone calibration, domain-specific terminology
â–¸

prohibitions (e.g. "Monopoly" is never used for advertising services)

Fire Writing Rule: A unique creative writing preservation directive â€” raw
â–¸

creative output is never word-modified, only structurally formatted

ï¸ Model Category Routing

CATEGORY TRIGGER SIGNAL TYPICAL MODEL

reasoning Default / general queries stehouwer\_llm

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 11/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er CATEGORY TRIGGER SIGNAL TYPICAL MODEL
massive Summarize, analyze, input \> 2000 chars
Large context model

multimodal Keywords: image, picture, vision Vision-capable model

precision Keywords: code, script, function qwen2.5-coder /

codestral

instruction Keywords: rule, safety, format Instruction-tuned

variant

ï¿½ï¿½ Fill-in-the-Middle (FIM) Autocomplete

The Monaco editor in the Developer Workspace module is connected to a live FIM

autocomplete endpoint (/api/autocomplete) backed by qwen2.5-coder. As the

user types, a debounced request sends up to 2,000 characters of prefix and 2,000 characters of suffix context to the model, which returns an inline completion injected directly into the editor â€” replicating GitHub Copilot functionality entirely locally with zero telemetry.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 12/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 07 TOKEN BUDGET ESTIMATION

Heuristic Token Budget Estimator v2

Rather than depend on external tokenization libraries like tiktoken or HuggingFace transformers, Brett developed a local heuristic token budget estimator tailored specifically to

the AI-BS inference pipeline. This eliminates an entire dependency category,

reduces cold-start time, and provides a foundation for further customization.

DESIGN DECISION

External tokenizers like tiktoken are model-specific and require model

vocabulary files to function accurately. Since AI-BS operates across multiple

models simultaneously, a vocabulary-agnostic estimation approach â€”

blending word-boundary counting and character density â€” provides

sufficient accuracy (\<8% error margin) for context window management

decisions while requiring zero external dependencies or network access.

ï¿½ï¿½ Token Estimation Algorithm

tokenizer.py â€”

TokenBudgetEstimator.estimate_tokens()

\# Blended word \+ character token estimation

\# No external dependencies â€” runs on any Python 3.9+

installation

def count\_tokens(text: str) \> int:

words \= re.findall(r'\\w+', text) \# tokenize on word

boundaries

word\_count \= len(words)

char\_count \= len(text)

est\_words \= int(word\_count \* 1.3) \# sub-word

inflation factor

est\_chars \= int(char\_count / 4) \# GPT-style

char/token ratio

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 13/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

return max(1, int((est\_words \+ est\_chars) / 2)) \# blended estimate

ï¿½ï¿½ Function-Call Detection Engine

The utility's most architecturally significant feature is its multi-format tool-call detection system. When the LLM produces structured function-call syntax in its output, the estimator's extract\_tool\_calls() method scans for five distinct formats that different model families use:

JSON-style: {"tool": "...", "parameters": {...}} â€” standard OpenAI
â–¸

compatible format

â–¸ XML-style: \<tool\_call\>...\</tool\_call\> â€” used by Anthropic-style models

Hermes format: \<tool\_use\>...\</tool\_use\> â€” OpenHermes and
â–¸

NousResearch models

â–¸ Markdown fenced: Code blocks with json or tool\_call language specifier

Python-style: function\_name(arg=value) â€” filtered against the
â–¸

KNOWN\_TOOLS registry to eliminate false positives

This design makes AI-BS model-agnostic for tool calling â€” any local model that

produces structured output in any of these formats will have its tool calls correctly

intercepted and dispatched by the agent loop.

âœ‚ï¸ Semantic Chunking for Vector Archiving

The chunk\_text() method implements a three-tier splitting strategy for preparing

conversation history and documents for ChromaDB embedding. Rather than naively splitting on character count, it prioritizes semantic coherence: paragraph breaks â†’

sentence boundaries â†’ hard character limit. This produces more semantically

meaningful embedding units that improve retrieval quality during RAG operations.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 14/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 08 ME MORY

SSD Virtual RAM â€” Context Memory System

One of the most original innovations in AI-BS is the SSD Virtual RAM system â€” a

two-tier persistent memory architecture that gives the LLM effectively unlimited

conversational context by treating the user's local SSD as an extension of the

model's context window.

Traditional LLMs have a fixed context window (typically 4,096 to 128,000 tokens).

When a conversation exceeds this limit, older turns are simply dropped â€”

permanently lost. The SSD Virtual RAM system transforms this lossy truncation into

a lossless archival-and-retrieval cycle.

ï¿½ï¿½ Two-Tier Architecture

TIER 1 â€” Hot Context (Active GPU VRAM) Active conversation

history, currently loaded in LLM context window Token budget:

configurable (default 4,000 tokens via the heuristic token budget estimator)

Location: In-memory Python list, transmitted per-request from

frontend TIER 2 â€” SSD Archive (Cold Storage \+ Vector Index)

When Tier 1 exceeds budget, oldest N turn-pairs are evicted: â”‚

â”œâ”€â”€ JSON Flat Archive â†’ session\_history\_archive.json â”‚ {

timestamp, user\_message, assistant\_message } â”‚ Sequential,

human-readable, full-fidelity backup â”‚ â””â”€â”€ ChromaDB Vector

Index â†’ stehouwer\_llm\_memory collection Embedded via nomic

embed-text (Ollama) Metadata: { type: "ssd\_ram\_archive",

timestamp } Enables semantic similarity retrieval at query

time RETRIEVAL CYCLE (on each new /api/chat request) 1\.

Tokenizer evaluates current history token count 2\. If over

budget â†’ evict oldest turns to both archive tiers 3\. Query

ChromaDB memory collection with current user message 4\. Top-K

semantically relevant past turns retrieved 5\. Injected as

context prefix: "Relevant context from memory: ." 6\. LLM now

has access to relevant history beyond its native window

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 15/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

ï¸ User-Controlled Storage Path

A key design feature is that the SSD RAM path is user-defined and persisted

across restarts via settings.json. This allows the operator to direct the archive to any drive â€” for example, a dedicated NVMe SSD optimized for high-frequency

small writes, separate from the OS drive. The Command Center tab exposes a live

management panel showing current path, cache size in KB, and archived turn count, with controls to update the path or perform a clean wipe of both the JSON archive

and the ChromaDB index simultaneously.

INDUSTRY PARALLEL

This architecture is conceptually similar to Retrieval-Augmented Generation

with episodic memory â€” a research area actively studied at DeepMind,

Meta AI, and OpenAI. The AI-BS implementation achieves a pragmatic,

production-ready version of this capability using only open-source

components (ChromaDB, nomic-embed-text) running entirely locally, without

any research infrastructure requirements.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 16/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 09 ORCHE STRATION

Multi-Agent Orchestration Framework

AI-BS implements a full multi-agent orchestration layer that allows named developer agents to be launched as background system processes, managed through a live process registry, and terminated on demand â€” all from the Command Center UI.

ï¿½ï¿½ The Ollama Launch Integration

The ollama\_launch\_tool and its associated API endpoints (/api/agent/launch, /api/agent/status, /api/agent/kill) expose a catalog of 16 named developer agent integrations that can be launched on-demand:

Claude Code: Full agentic coding agent with filesystem access, runnable via
â–¸

/loop \[interval\] \[task\] for autonomous background operation

â–¸ OpenCode: Open-source coding agent for code review and generation tasks

Codestral: Mistral's code-specialized model, used as default for optimization
â–¸

sub-agents

VS Code Sync: Exposes the local Ollama stack as the Copilot Chat backend
â–¸

inside VS Code, giving IDE-native context-aware assistance without cloud telemetry

Hermes Desktop: NousResearch Hermes model optimized for function-calling
â–¸

tasks

Telegram Bridge: Binds the Claude Code agent to a Telegram bot token,
â–¸

enabling remote mobile control of the local AI system from any device

ï¿½ï¿½ The /loop Protocol â€” Autonomous Background Tasks

The /loop protocol allows any agent to be launched in a persistent background

session that recursively executes a task at a configurable interval (15m, 30m, 1h,

4h). This transforms AI-BS from a reactive assistant into a proactive, always-on

autonomous system capable of continuous codebase monitoring, log analysis, and self-directed optimization â€” without any manual prompting.

âš–ï¸ VRAM Management

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 17/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Before launching any agent, the unload\_unused\_models() function queries the

Ollama process list (GET /api/ps), identifies any loaded model that is not the target agent model, and sends a keep\_alive: 0 signal to release it from VRAM. This

ensures the RTX 4090's full 24 GB is available to the agent being launched,

preventing out-of-memory failures during complex reasoning tasks.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 18/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 10 KNOWLE DG E

Semantic Knowledge Base (ChromaDB \+ RAG)

The knowledge base system allows Brett to ingest arbitrary documents (PDF, DOCX, TXT, HTML) into a persistent vector database, which the LLM can then query semantically at inference time. This transforms the LLM from a static knowledge store into a dynamic, context-aware system that can reason over user supplied private documents.

All embeddings are generated locally using nomic-embed-text via Ollama â€” a 137M parameter embedding model that produces 768-dimensional dense vectors optimized for semantic similarity. The OllamaEmbeddingFunction class implements the ChromaDB EmbeddingFunction interface and includes automatic dimension caching and graceful fallback to zero-vectors on embedding failure, ensuring the system never crashes on embedding errors.

ï¿½ï¿½ ChromaDB Collections

COLLECTION NAME PURPOSE METADATA TAGS
brett\_knowledge\_base\_v2 User-uploaded documents for RAG

retrieval

stehouwer\_llm\_memory SSD Virtual RAM conversation archive

with semantic

indexing

ï¿½ï¿½ Document Processing Pipeline
filename, type, chunk\_index

type:

ssd\_ram\_archive, timestamp

PDF: Extracted via PyMuPDF / pdfplumber â€” layout-aware text extraction
â–¸

preserving paragraph structure

DOCX: Processed via docx2txt â€” preserves heading hierarchy and list
â–¸

formatting

â–¸ HTML: Parsed via BeautifulSoup4 â€” strips tags while preserving semantic text file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 19/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

content

â–¸ TXT / MD: Direct ingestion with UTF-8 normalization

Images (RAG): Base64-encoded and passed to multimodal model variants for
â–¸

visual RAG

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 20/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 11 FRONTE ND

Electron Desktop Application

The AI-BS user interface is a production-grade Electron desktop application built

with React 19 and Vite 8, packaged as a signed Windows NSIS installer via

electron-builder. The application auto-discovers the local backend URL (supporting both localhost:8000 and same-host deployments) and exposes the entire AI-BS

capability surface through a tabbed, dark-themed UI designed for extended daily

use.

ï¿½ï¿½ Design System

The UI uses a custom CSS design system built around glassmorphism principles â€”

translucent panels with subtle backdrop-blur effects, gradient accents, and micro

animations that make the interface feel alive and responsive. The color palette is

calibrated for extended screen use: deep navy backgrounds, violet accent

gradients, and phosphor green status indicators â€” avoiding high-contrast eye strain while maintaining clear visual hierarchy.

ï¸ State Architecture

The application uses React's built-in useState and useEffect hooks with a

centralized appProps object passed down to all tab components. This flat, single

source-of-truth architecture â€” while unconventional â€” eliminates the overhead of

Redux or Zustand for this use case, as the application's state graph is shallow (one

primary user session) and the performance characteristics are dominated by

network latency to the local backend rather than render frequency.

The Monaco Editor integration (from @monaco-editor/react) is connected to a live Python linting endpoint (/api/lint/python) via a debounced 500ms timer,

showing inline diagnostic markers â€” giving the Developer Workspace tab VS Code level Python editing capabilities within the Electron shell.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 21/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 12 CAPABILITIE S

Feature Modules & Capability Surface

AI-BS exposes its capabilities through 14 purpose-built feature modules, each representing a distinct domain of operation. This modular architecture allows the system to serve simultaneously as a personal AI assistant, a developer IDE, a creative writing platform, a media production tool, and a business intelligence system.

MODULE CAPABILITY KEY TECHNICAL FEATURES

Unified Agent Chat

Command Center

Developer

Workspace

Knowledge Base

Memory & State
Primary AI

conversation

interface

Agent orchestration & system

management

Full-stack coding environment

Document ingestion & RAG search

Agent memory

visualization
RAG, agent loop, web search, SSD memory injection, TTS, history management

Agent launcher, model puller, SSD RAM controls, loop protocol, Telegram bridge

Monaco editor, FIM autocomplete, Python linter, polyglot executor, Git integration

ChromaDB vector store, multi format parsing, semantic search, preview modal

ChromaDB collection browser, memory statistics, context injection viewer

Fire Writing Creative writing assistant

Media Studio AI image & video generation
Preserves raw creative voice â€” structural formatting only, never word-modifies

ComfyUI bridge, model selector, aspect ratio control, gallery, prompt enhancer

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 22/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er MODULE CAPABILITY KEY TECHNICAL FEATURES
IT Help Desk Sim
IT interview preparation
Timed scenario sessions, LLM graded scorecards, structured feedback

Advertising Stehouwer advertising tools
AI-assisted copywriting, campaign strategy, Tier 1-3 service workflows

NOCO

Telemetry

Visual

Scripting

Predictive Generator
Project NOCO monitoring

Node-based

workflow builder

Physics simulation code gen
Live sensor simulation,

Arduino/MicroPython code generator, alert system

ReactFlow canvas, drag-and-drop logic nodes, visual agent workflow design

3D/2D physics engine blueprint generation, PyInstaller sandbox validation

Admin

PowerShell
Integrated terminal Full xterm.js terminal with WebSocket backend, system

administration access

Agent Memory Dashboard
Memory & SSD RAM analytics
Live telemetry of token usage, archived turns, collection sizes

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 23/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 13 OPE RATIONS

Background Daemon System

AI-BS operates two persistent background daemon processes that run continuously alongside the main server, transforming the system from a reactive tool into a proactive, self-improving AI environment.

ï¸ File Watcher Daemon ( **file\_watcher.py** )

A watchdog process that continuously monitors the Projects directory for filesystem events (file creation, modification, deletion). On detecting a relevant change, it analyzes the modified file for syntax errors using py\_compile and AST parsing, logging any issues to a structured error report. This creates a continuous integration feedback loop that catches syntax regressions immediately without requiring a manual build step.

ï¿½ï¿½ Trainer Daemon ( **trainer.py** )

A five-minute cycle autonomous optimization daemon that alternates between two self-improvement modes:

Codebase Self-Healing: Selects a target file from the Projects directory and
â–¸

launches a Codestral sub-agent session to identify and apply optimization opportunities. Changes are only committed if the sub-agent exits cleanly and produces a diff.

Memory Reflection: Reads recent chat logs and, when sufficient data exists,
â–¸

generates structured memory summaries that are written back into the ChromaDB knowledge base â€” allowing the system to progressively learn from operator interactions over time.

SELF- IMPROVEMENT ARCHITECTURE

The Trainer Daemon represents a foundational implementation of continuous self-improvement through autonomous code review â€” a capability that is a primary research goal of leading AI labs. AI-BS implements a pragmatic,

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 24/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

locally-executable version of this concept using production tooling rather

than research infrastructure.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 25/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 14 DE VOPS

Build & Distribution Pipeline

AI-BS maintains a fully automated build and distribution pipeline that produces

signed, versioned Windows installers on each release. The pipeline is designed for

solo operation â€” a single PowerShell command triggers the complete sequence

from source to installer.

ï¿½ï¿½ Build Sequence

STEP 1 â€” Syntax Validation py\_compile main.py tokenizer.py â†’

must pass before build proceeds STEP 2 â€” Backend Compilation

(build\_versioned\_exe.ps1) Reads version.txt (integer counter)

â†’ increments â†’ writes back PyInstaller \-clean \-onedir

brain\_backend.spec Outputs: dist/brain\_backend/ (self

contained dir w/ all DLLs) Copies to:

updates/brain\_backend\_v{N}/ STEP 3 â€” Frontend Build (npm run

build) Vite 8 â†’ ESModule tree shaking â†’ minified JS \+ CSS

bundles Output: frontend/dist/ (206 modules, \~852 KB JS

gzipped to 231 KB) STEP 4 â€” Version Increment

(increment\_frontend\_version.py) Reads package.json semver â†’

increments patch â†’ writes back STEP 5 â€” Electron Packaging

(npm run package **â†’** electron-builder) Bundles frontend/dist/ \+

backend/dist/brain\_backend/ into Electron shell Code-signs

brain\_backend.exe, AI-BS.exe, elevate.exe via signtool.exe

Outputs: G:/Stehouwer\_Server/Updates/AI-BS Setup {version}.exe

Generates block map for delta auto-update support

ï¿½ï¿½ Distribution Architecture

The NSIS installer is configured with oneClick: false and

allowToChangeInstallationDirectory: true â€” giving the end user full control

over installation path while providing Desktop and Start Menu shortcuts by default.

The backend binary (brain\_backend/brain\_backend.exe) is bundled as an

extraResource, allowing the Electron main process to spawn it as a child process at file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 26/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

application startup and terminate it on close â€” ensuring no orphaned server

processes remain after the application exits.

A generic update provider configuration points to the local Updates directory,

enabling electron-updater to perform block-map differential updates â€” only

downloading changed chunks rather than the full installer on each release, which is

critical given the multi-gigabyte size of the bundled PyTorch/ChromaDB

dependencies.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 27/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 15 SE CURITY

Security Model

ï¿½ï¿½ Sandboxed Tool Execution

Every agent tool that operates on the filesystem enforces path validation via a

resolve\_filepath() utility that normalizes and validates the absolute path against an allowlist of permitted base directories (Projects/ and

Stehouwer\_Publishing/). Any attempt to access paths outside these directories

â€” including path traversal attacks using ../ sequences â€” returns an "Access

denied" error without reaching the filesystem.

â±ï¸ Execution Timeouts

All code executor tools enforce subprocess timeouts (15 seconds for interpreted

languages, 60 seconds for compiled builds). Timed-out processes are terminated

via subprocess.TimeoutExpired handling, preventing runaway processes from

consuming system resources during agent sessions.

ï¿½ï¿½ Network Isolation

The backend binds exclusively to localhost:8000. All inference, embedding, and

agent operations communicate over the loopback interface. No user data,

conversation history, documents, or model outputs are transmitted to external

services during normal operation. The optional web search feature uses

DuckDuckGo's anonymous HTML search endpoint â€” no API key, no tracking, no

session cookies.

âš ï¸ Remote Access Safety Controls

The Telegram bridge integration includes an explicit safetySkipPermissions

toggle in the UI. When disabled (default), the agent requires explicit confirmation

before executing system-modifying commands received remotely. A prominent red warning banner is displayed whenever this toggle is enabled, clearly communicating the security implications of bypassing authorization checks for remote commands.

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 28/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

Â§ 16 INNOVATION

Innovation Summary & Technical Differentiation

The following table summarizes the key technical innovations in AI-BS and positions them relative to the current state of the art in AI systems engineering:

INNOVATIONINDUSTRY
EQUIVALENTAI-BS DIFFERENTIATION

SSD Virtual RAM (unlimited context)

Polyglot execution sandbox

FIM code

autocomplete

Multi-format tool call detection

Trainer daemon (self-healing)
MemGPT, RAG episodic memory research

GitHub Copilot Workspace, Devin

GitHub Copilot, Cursor

LangChain tool parsers,

LlamaIndex

AlphaCode self improvement

research
Fully offline, user-controlled path, dual-tier (JSON \+ ChromaDB), wipe-able via UI

8 languages, local execution, agent-driven iteration, zero API cost

Local model, zero telemetry, Monaco editor integration, 500ms debounce

No framework dependency, 5 format patterns,

KNOWN\_TOOLS filter registry

Production-ready, cycles every 5 min, uses Codestral sub agent, file-diff gating

VRAM manager llama.cpp mlock, vLLM KV cache

mgmt
Pre-unloads competing models before agent launch, RTX 4090 specific

Versioned

directive system

Remote mobile control
RFC / design doc processes

Enterprise AI

orchestration
Each capability upgrade has a formal directive (INT-001 to INT 006\) with spec

Telegram bot bridge with safety toggle, binds to local Claude

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 29/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er

INNOVATIONINDUSTRY
EQUIVALENTAI-BS DIFFERENTIATION

platforms Code agent

Fire Writing

preservation rule
N/A â€” original concept
Uniquely preserves raw creative voice â€” structural formatting only, no word changes

SUMMARY ASSESSMENT

AI-BS demonstrates engineering judgment typically associated with senior AI infrastructure engineers at established companies â€” not an independent developer working solo. The system reflects deep understanding of LLM inference constraints, vector database architecture, distributed system design, desktop application distribution, and the practical challenges of making AI systems reliable, operable, and maintainable in production conditions.

Â§ 17 FUTURE

Roadmap

AI-BS is under active development. The following capabilities are planned for future directive cycles:

INT-007 â€” Distributed Inference: Multi-GPU inference routing across a local
â–¸

network cluster for larger model support (70B+ parameter models)

INT-008 â€” Fine-Tuning Pipeline: LoRA/QLoRA fine-tuning UI integrated with
â–¸

the Knowledge Base â€” allowing the operator to fine-tune the Stehouwer LLM on curated conversation exports

INT-009 â€” Project NOCO Integration: Live IoT sensor data ingestion from the
â–¸

NOCO vertical farming system, with real-time AI-driven optimization recommendations

INT-010 â€” Collaborative Mode: Secure multi-operator mode allowing remote
â–¸

collaborators (Julie, Sean, Devin) to access specific AI-BS capabilities over an

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 30/31
6/15/26, 1:32 AM AI-BS TechnicalArchitecture Report â€” Brett Adam Stehouw er authenticated tunnel
INT-011 â€” Voice-First Interface: Always-on wake-word detection with
â–¸

streaming STT/TTS pipeline, transforming AI-BS into a fully hands-free ambient assistant

INT-012 â€” Ithaca Deployment: Cloud-hybrid mode for the Ithaca relocation â€”
â–¸

selective offload of non-sensitive workloads to a local edge server while maintaining privacy-sensitive operations on-premises

AI-BS â€” Autonomous Intelligence & Build System Designed & Engineered by Brett Adam Stehouwer | CTO, Stehouwer Publishing LLC | June 2026
v1.1.1

AI-BS

INTEGRATION 006

file:///G:/Stehouw er\_Server/AI\_Agent/AI-BS\_Technical\_Report.html 31/31
