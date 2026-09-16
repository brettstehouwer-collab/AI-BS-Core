"""
Model Domain Taxonomy & Semantic Keyword Matrix (17-Model Fleet)
Ecosystem: AI-BS Sovereign Intelligence Matrix

Defines exhaustive domain taxonomies, keyword weights, specialized roles,
and multi-model scoring heuristics across all 17 local Ollama models.
"""

import re
from typing import Dict, List, Any, Tuple, Optional

# ==============================================================================
# MASTER 17-MODEL TAXONOMY & KEYWORD DICTIONARIES
# ==============================================================================

MODEL_FLEET_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "qwen2.5-coder:latest": {
        "title": "Technical Architecture & Code Engineering Model",
        "role": "code_architecture_engineering",
        "weight": 0.98,
        "description": "Specialized in Python AST parsing, JSX/TSX validation, Rust, Go, C++, SQL/DuckDB, algorithms, refactoring, and full-stack debugging.",
        "keywords": [
            "python", "javascript", "typescript", "react", "vite", "fastapi", "node", "sql", "sqlite",
            "duckdb", "c++", "cpp", "rust", "golang", "go", "powershell", "bash", "html", "css",
            "jsx", "tsx", "ast", "regex", "api", "endpoint", "json", "yaml", "toml", "git",
            "docker", "refactor", "patch", "bug", "debug", "syntax", "function", "class", "async",
            "await", "promise", "loop", "compiler", "parser", "dependency", "npm", "pip", "venv",
            "unit test", "mock", "pytest", "lint", "webpack", "tailwind", "database schema", "migration",
            "query optimization", "backend", "frontend", "fullstack", "script", "algorithm",
            "data structure", "recursion", "socket", "websocket", "http", "rest", "crud",
            "middleware", "jwt", "import", "package.json", "requirements.txt", "traceback",
            "exception", "nullpointer", "segfault", "type error", "undefined", "variable", "scope"
        ],
        "regex_patterns": [
            r"\bdef\s+[a-zA-Z_]\w*\(", r"\bfunction\s+[a-zA-Z_]\w*\(", r"\bconst\s+[a-zA-Z_]\w*\s*=",
            r"\bimport\s+[\w\s,{}]+from", r"\bclass\s+[a-zA-Z_]\w*", r"\bSELECT\s+.+\s+FROM\b",
            r"\b<\w+(?:\s+[^>]+)?>", r"\b(?:npm|pip|cargo|go\s+run|git\s+commit)\b"
        ]
    },

    "qwen3.6:latest": {
        "title": "Macro-System Reasoning & High-Order Architecture",
        "role": "macro_system_reasoning",
        "weight": 0.96,
        "description": "Specialized in distributed architectures, system decomposition, multi-step strategic roadmaps, concurrency models, and high-level decision matrices.",
        "keywords": [
            "architecture", "system design", "macro reasoning", "roadmap", "distributed system",
            "scalability", "decomposition", "tradeoff", "trade-off", "decision matrix", "concurrency model",
            "fault tolerance", "disaster recovery", "state machine", "pipeline architecture", "topology",
            "load balancing", "caching strategy", "microservices", "event driven", "workflow design",
            "multi-stage", "strategic plan", "system integration", "bottleneck analysis", "capacity planning",
            "high availability", "failover", "protocol design", "scalability plan", "architectural blueprint",
            "flowchart", "sequence diagram", "consensus protocol", "sharding", "consistency model", "cap theorem"
        ],
        "regex_patterns": [
            r"\barchitecture\b", r"\bsystem\s+design\b", r"\btrade[- ]?offs?\b", r"\broadmap\b",
            r"\bmacro[- ]reasoning\b", r"\bhigh[- ]level\s+plan\b"
        ]
    },

    "nemotron-3.5-lightning:latest": {
        "title": "NVIDIA Silicon, CUDA & Hardware Accelerator",
        "role": "nvidia_silicon_cuda_acceleration",
        "weight": 0.94,
        "description": "Specialized in NVIDIA RTX 4090 / CUDA optimization, TensorRT, VRAM bandwidth, NVENC encoding, flash attention, and low-latency parallel compute.",
        "keywords": [
            "nvidia", "cuda", "gpu", "rtx 4090", "vram", "tensorrt", "flash attention", "nvenc",
            "tensor core", "compute shader", "cuda kernel", "cuda stream", "pcie", "bandwidth",
            "memory bandwidth", "tflops", "fp16", "fp32", "int8", "quantization", "awq", "gptq",
            "gguf", "cuda out of memory", "oom", "hardware acceleration", "nvlink", "cudnn",
            "driver", "vram offload", "kernel compilation", "nsight", "latency optimization",
            "throughput", "multithreading", "gpu temperature", "power limit", "tensor cores",
            "directx", "vulkan", "opengl", "shading rate", "nvml", "smi", "nvidia-smi"
        ],
        "regex_patterns": [
            r"\b(?:cuda|tensorrt|nvenc|rtx\s*4090|gpu|vram|nvidia-smi)\b",
            r"\b(?:fp16|fp32|int8|quantization|tensor\s+cores?)\b"
        ]
    },

    "stehouwer_qwen:latest": {
        "title": "Station 13 Hardware & Boardview Diagnostician",
        "role": "hardware_schematics_boardview",
        "weight": 0.95,
        "description": "Specialized in motherboard schematics, diode mode readings, IC pinouts, SPI/EEPROM firmware flashing, iPhone/MacBook micro-soldering, and power rails.",
        "keywords": [
            "hardware", "schematic", "boardview", "diode mode", "short circuit", "power rail",
            "pp_vcc", "vcore", "ic pinout", "flashrom", "ch341a", "spi flash", "eeprom", "bios",
            "firmware dump", "soldering", "hot air", "bga", "flux", "multimeter", "oscilloscope",
            "station 13", "iphone repair", "macbook repair", "logic board", "tristar", "pmic",
            "smc", "t2 chip", "capacitance", "resistor", "mosfet", "buck converter", "voltage regulator",
            "bench power supply", "amperage draw", "thermal camera", "micro soldering", "pad",
            "trace", "vcc_main", "ground short", "inject voltage", "solder wick", "reball"
        ],
        "regex_patterns": [
            r"\b(?:diode\s+mode|power\s+rail|boardview|schematic|station\s*13)\b",
            r"\b(?:pp_[\w\d]+|vcore|pmic|ch341a|flashrom|eeprom|spi\s+flash)\b"
        ]
    },

    "stehouwer_dolphin:latest": {
        "title": "Wave Studio Audio DSP, Stems & Lyric Prosody",
        "role": "audio_dsp_prosody_engineering",
        "weight": 0.92,
        "description": "Specialized in Demucs audio stem separation, SoX filtergraphs, EBU R128 (-14 LUFS) mastering, pitch/tempo stretching, and lyric cadence meter mapping.",
        "keywords": [
            "audio", "dsp", "stem", "demucs", "vocal", "instrumental", "bass", "drums", "equalizer",
            "eq", "compressor", "limiter", "reverb", "delay", "lufs", "ebu r128", "normalization",
            "mastering", "mixing", "pitch shift", "tempo stretch", "rubber band", "sox", "ffmpeg audio",
            "wav", "flac", "mp3", "prosody", "rhyme", "meter", "syllable", "cadence", "4/4 time",
            "bpm", "tempo", "daw", "vst3", "wave studio", "suno", "sound design", "frequency",
            "sample rate", "bit depth", "phase inversion", "noise gate", "multiband", "sidechain",
            "acoustics", "reverberation", "rt60", "lyric alignment", "vocal tuning", "autotune"
        ],
        "regex_patterns": [
            r"\b(?:demucs|stems?|lufs|ebu\s*r128|prosody|rubber\s*band|sox|vst3)\b",
            r"\b(?:equalizer|compressor|reverb|bpm|tempo\s+stretch|pitch\s+shift)\b"
        ]
    },

    "unrestricted-llama3.1:latest": {
        "title": "Unrestricted Creative Stream & Raw Manuscript Engine",
        "role": "unrestricted_creative_manuscript",
        "weight": 0.92,
        "description": "Specialized in unfiltered creative exploration, fiction worldbuilding, uncensored manuscripts, stream-of-consciousness writing, and raw authorial drafts.",
        "keywords": [
            "unrestricted", "unfiltered", "raw manuscript", "uncensored", "stream of consciousness",
            "fire writing", "fiction", "novel", "screenplay", "dialogue", "creative writing",
            "worldbuilding", "character arc", "scene description", "creative exploration",
            "brainstorming", "philosophical stream", "narrative draft", "prose", "storytelling",
            "lore", "creative draft", "dark fiction", "uncensored narrative", "raw creative",
            "author manuscript", "literary stream", "uninhibited exploration", "creative writing prompt"
        ],
        "regex_patterns": [
            r"\b(?:unrestricted|unfiltered|raw\s+manuscript|fire\s+writing|uncensored)\b",
            r"\b(?:stream\s+of\s+consciousness|worldbuilding|novel\s+chapter)\b"
        ]
    },

    "dolphin-llama3:latest": {
        "title": "Dynamic Scenario Ideation & Creative Dialogue",
        "role": "scenario_dialogue_ideation",
        "weight": 0.90,
        "description": "Specialized in character dialogue, what-if simulations, roleplay dynamics, creative improvisation, and cinematic scene scriptwriting.",
        "keywords": [
            "creative dialogue", "roleplay", "character interaction", "brainstorm", "what-if",
            "scenario simulation", "dynamic script", "story prompt", "creative ideation",
            "narrative concept", "dramatic scene", "character development", "improvisation",
            "story arc", "creative pitch", "dialogue exchange", "play script", "scriptwriting",
            "character voice", "conversation simulation", "dramatic tension"
        ],
        "regex_patterns": [
            r"\b(?:what[- ]if|dialogue\s+between|scenario\s+simulation|roleplay)\b",
            r"\b(?:character\s+voice|dramatic\s+scene|scriptwriting)\b"
        ]
    },

    "stehouwer_llm_dolphin:latest": {
        "title": "Stehouwer Narrative Fidelitas & Autobiographical Archivist",
        "role": "stehouwer_fidelitas_archival",
        "weight": 0.91,
        "description": "Specialized in Stehouwer family lore, verbatim reality archival blocks, personal memoir stream preservation, and biographical fidelitas mandate transcription.",
        "keywords": [
            "stehouwer narrative", "reality archival block", "verbatim stream", "autobiography",
            "memoir", "stehouwer lore", "chronicle", "verbatim transcription", "fidelitas mandate",
            "raw source payload", "personal history", "sovereign narrative", "life story",
            "family archive", "stehouwer publishing history", "bretts history", "biographical record"
        ],
        "regex_patterns": [
            r"\b(?:stehouwer\s+reality|archival\s+block|fidelitas\s+mandate|verbatim\s+stream)\b",
            r"\b(?:stehouwer\s+lore|family\s+archive|personal\s+memoir)\b"
        ]
    },

    "stehouwer_hermes:latest": {
        "title": "Autonomous Agentic Orchestrator & Tool Supervisor",
        "role": "agentic_tool_supervision",
        "weight": 0.90,
        "description": "Specialized in multi-agent crew orchestration, function/tool parameter selection, execution tree dispatching, and autonomous workflow coordination.",
        "keywords": [
            "agentic", "tool calling", "function call", "autonomous agent", "agent crew",
            "supervisor", "decision tree", "action execution", "task decomposition", "multi-agent",
            "tool selection", "workflow orchestration", "dispatch action", "subagent", "agent loop",
            "tool parameter", "execution plan", "hierarchical planning", "tool schema", "agent roster",
            "crew routing", "autonomous loop", "orchestration plan"
        ],
        "regex_patterns": [
            r"\b(?:tool\s+calling|function\s+call|agentic\s+loop|agent\s+crew)\b",
            r"\b(?:orchestrate|subagent|decision\s+tree|dispatch\s+action)\b"
        ]
    },

    "gemma4:12b": {
        "title": "Factual Grounding, Logic Auditor & Bias Validator",
        "role": "factual_grounding_logic_auditor",
        "weight": 0.91,
        "description": "Specialized in factual verification, logical fallacy detection, hallucination audits, counterarguments, citation cross-checking, and empirical truthfulness.",
        "keywords": [
            "fact check", "verify", "audit", "grounding", "accuracy", "fallacy", "logical fallacy",
            "bias check", "citation check", "truthfulness", "hallucination", "evidence",
            "counterargument", "scientific validity", "sanity check", "premise check",
            "consistency audit", "mathematical proof", "empirical check", "verify facts",
            "cross-examine", "validate claims", "check errors", "truth verification", "factual audit"
        ],
        "regex_patterns": [
            r"\b(?:fact[- ]check|verify\s+claims?|logical\s+fallac(?:y|ies)|audit\s+for\s+bias)\b",
            r"\b(?:hallucination\s+check|cross[- ]examine|empirical\s+evidence)\b"
        ]
    },

    "command-r:latest": {
        "title": "Long-Context Document Factoring & Enterprise RAG",
        "role": "document_factoring_rag_publishing",
        "weight": 0.93,
        "description": "Specialized in massive document ingestion, Typst/Pandoc PDF compilation, Calibre eBook conversions, citations, multi-chapter books, and KDP publishing.",
        "keywords": [
            "document", "pdf", "epub", "kdp", "publishing", "typst", "pandoc", "calibre",
            "long context", "rag", "retrieval", "chapter", "manuscript", "citation", "index",
            "table of contents", "ebook formatting", "margin", "bleed", "trim size", "running header",
            "document stream", "vector retrieval", "corpus search", "cross-reference", "mobi",
            "azw3", "kindle formatting", "book design", "page numbering", "frontmatter", "backmatter"
        ],
        "regex_patterns": [
            r"\b(?:typst|pandoc|calibre|kdp|epub|mobi|azw3|pdf\s+optimization)\b",
            r"\b(?:trim\s+size|bleed|running\s+headers?|table\s+of\s+contents)\b"
        ]
    },

    "mixtral:latest": {
        "title": "Mixture-of-Experts Consensus & Cross-Domain Synthesis",
        "role": "mixture_of_experts_synthesis",
        "weight": 0.95,
        "description": "Specialized in multi-perspective consensus, cross-disciplinary synthesis, polymath evaluations, and comprehensive trade-off summaries.",
        "keywords": [
            "synthesis", "cross discipline", "interdisciplinary", "consensus", "expert review",
            "comprehensive analysis", "multi-perspective", "holistic overview", "comparative evaluation",
            "trade-off analysis", "polymath", "macro analysis", "broad synthesis", "unified summary",
            "multi-expert", "cross-cutting", "comprehensive review", "meta analysis", "unified perspective"
        ],
        "regex_patterns": [
            r"\b(?:cross[- ]disciplinary|interdisciplinary|consensus\s+review)\b",
            r"\b(?:holistic\s+overview|multi[- ]perspective|polymath\s+analysis)\b"
        ]
    },

    "llama3.1:8b-instruct-q5_K_M": {
        "title": "Rapid Instruction Execution & Low-Overhead Parsing",
        "role": "rapid_instruction_parsing",
        "weight": 0.88,
        "description": "Specialized in sub-100ms command parsing, short summaries, bullet extractions, regex extraction, format conversions, and rapid low-latency answering.",
        "keywords": [
            "fast command", "quick answer", "short summary", "quick parse", "extract json",
            "simple query", "rapid response", "low latency", "instant lookup", "brief answer",
            "regex extract", "bullet points", "convert format", "fast reply", "one-liner",
            "quick check", "summarize in 3 bullets", "fast classification"
        ],
        "regex_patterns": [
            r"\b(?:quick\s+answer|in\s+one\s+sentence|in\s+3\s+bullets|fast\s+reply)\b",
            r"\b(?:parse\s+this\s+json|extract\s+data|quick\s+summary)\b"
        ]
    },

    "llama3.1:latest": {
        "title": "Context Coherence & Structured Technical Manuals",
        "role": "context_coherence_technical_reports",
        "weight": 0.89,
        "description": "Specialized in cohesive long-form exposition, formal standard operating procedures (SOPs), whitepapers, user manuals, and structured operational guides.",
        "keywords": [
            "technical report", "structured report", "formal documentation", "user manual",
            "operational guide", "whitepaper", "system manual", "deep exposition", "coherence",
            "standard operating procedure", "sop", "ecosystem manual", "step by step guide",
            "procedural document", "system specification"
        ],
        "regex_patterns": [
            r"\b(?:user\s+manual|technical\s+report|standard\s+operating\s+procedure|sop)\b",
            r"\b(?:whitepaper|operational\s+guide|system\s+specification)\b"
        ]
    },

    "llama3:latest": {
        "title": "Baseline Benchmark & Sanity Verification",
        "role": "baseline_benchmark_sanity",
        "weight": 0.88,
        "description": "Specialized in baseline comparative testing, sanity evaluation, standard answer formatting, and benchmark regression auditing.",
        "keywords": [
            "baseline test", "benchmark", "standard response", "sanity test", "reference comparison",
            "standard evaluation", "baseline comparison", "control test", "benchmark audit"
        ],
        "regex_patterns": [
            r"\b(?:baseline\s+test|benchmark\s+comparison|sanity\s+check)\b"
        ]
    },

    "nomic-embed-text:latest": {
        "title": "ChromaDB Vector Embedding & HNSW Indexing",
        "role": "vector_embedding_indexing",
        "weight": 0.95,
        "description": "Specialized in vector embeddings, cosine similarity search, ChromaDB partitions, HNSW semantic index generation, and dense vector retrieval.",
        "keywords": [
            "embed", "vectorize", "semantic search", "similarity search", "chromadb", "vector store",
            "cosine similarity", "hnsw index", "semantic chunking", "dense retrieval", "embedding model",
            "vector space", "k-nearest neighbors", "knn", "vector partition", "embedding distance"
        ],
        "regex_patterns": [
            r"\b(?:chromadb|vector\s+store|semantic\s+search|cosine\s+similarity)\b",
            r"\b(?:hnsw|embedding\s+model|vectorize)\b"
        ]
    },

    "stehouwer_llm:latest": {
        "title": "Sovereign Executive Core & Master Persona",
        "role": "sovereign_executive_core",
        "weight": 1.00,
        "description": "The default sovereign intelligence core of Brett Stehouwer / Stehouwer Publishing. Master decision maker, executive synthesizer, personal memory recall, and full-authority orchestrator.",
        "keywords": [
            "stehouwer", "ai-bs", "sovereign", "master directive", "brotherly banter",
            "executive decision", "unified dashboard", "all systems", "final answer", "general chat",
            "default core", "personal memory", "brett", "stehouwer publishing", "master manual",
            "checkpoint", "ledger", "sovereign authority", "18-port matrix", "full privilege"
        ],
        "regex_patterns": [
            r"\b(?:stehouwer|ai-bs|sovereign|executive\s+core)\b",
            r"\b(?:brett|master\s+directive|18-port\s+matrix)\b"
        ]
    }
}

# ==============================================================================
# MODEL CLASSIFICATION & DOMAIN SCORING ENGINE
# ==============================================================================

class ModelDomainMatrix:
    """Master Semantic Classifier & Multi-Model Allocator."""

    @classmethod
    def score_prompt_against_fleet(cls, prompt: str) -> List[Dict[str, Any]]:
        """
        Calculates domain relevance scores for all 17 models based on keyword matches,
        regex pattern hits, and base cognitive weights.
        Returns a sorted list of ranked models with reasoning metadata.
        """
        prompt_lower = prompt.lower()
        scored_fleet = []

        for model_name, meta in MODEL_FLEET_TAXONOMY.items():
            # Skip pure embedding model from conversational text generation ranking
            if model_name.startswith("nomic-embed"):
                continue

            score = 0.0
            matched_keywords = []
            matched_patterns = []

            # 1. Exact Keyword Matches (weighted by keyword length and specificity)
            for kw in meta.get("keywords", []):
                # Word boundary search for accurate match
                pattern = r"\b" + re.escape(kw) + r"\b"
                matches = len(re.findall(pattern, prompt_lower))
                if matches > 0:
                    kw_score = (1.5 if len(kw.split()) > 1 else 1.0) * matches
                    score += kw_score
                    matched_keywords.append(kw)

            # 2. Structural Regex Matches
            for pat in meta.get("regex_patterns", []):
                if re.search(pat, prompt, re.IGNORECASE):
                    score += 3.0
                    matched_patterns.append(pat)

            # 3. Apply Base Model Weight
            base_weight = meta.get("weight", 0.90)
            final_composite_score = score * base_weight

            # Always give default stehouwer_llm a slight base affinity for sovereign voice
            if model_name in ["stehouwer_llm:latest", "stehouwer_llm"]:
                final_composite_score += 0.5

            scored_fleet.append({
                "model": model_name,
                "title": meta.get("title"),
                "role": meta.get("role"),
                "score": round(final_composite_score, 3),
                "raw_match_count": len(matched_keywords) + len(matched_patterns),
                "matched_keywords": matched_keywords[:8],
                "matched_patterns": len(matched_patterns),
                "base_weight": base_weight
            })

        # Sort descending by composite score
        scored_fleet.sort(key=lambda x: x["score"], reverse=True)
        return scored_fleet

    @classmethod
    def get_optimal_cross_communication_crew(cls, prompt: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Selects a lead specialist, logic auditor, and sovereign synthesizer for cross-model communication.
        """
        ranked = cls.score_prompt_against_fleet(prompt)
        lead_model = ranked[0]["model"]
        
        # Select secondary specialist / auditor
        secondary_model = "gemma4:12b"  # Default logic & fact auditor
        for cand in ranked[1:]:
            if cand["model"] != lead_model and cand["model"] not in ["stehouwer_llm:latest", "stehouwer_llm"]:
                secondary_model = cand["model"]
                break

        synthesizer_model = "stehouwer_llm:latest"

        return {
            "lead_specialist": lead_model,
            "lead_role": MODEL_FLEET_TAXONOMY.get(lead_model, {}).get("title"),
            "logic_auditor": secondary_model,
            "auditor_role": MODEL_FLEET_TAXONOMY.get(secondary_model, {}).get("title"),
            "sovereign_synthesizer": synthesizer_model,
            "top_ranked": ranked[:top_k],
            "multi_model_needed": ranked[0]["raw_match_count"] > 0 or len(prompt.split()) > 30
        }
