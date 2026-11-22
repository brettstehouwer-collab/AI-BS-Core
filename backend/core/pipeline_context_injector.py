"""AI-BS Pipeline (6/6) Stage 1: Sovereign System Identity & Term Disambiguator

File: C:/AI-BS/backend/core/pipeline_context_injector.py
Fixes the bug in Build v5.329.127 where gpt-4.1-mini misinterprets 'AI-BS' as 'AI bullshit'
and provides Stage 1 context & shorthand disambiguation across both OpenAI API and local RTX 4090 Ollama routes.
"""

from pathlib import Path
import re
from typing import Dict, List, Optional

VERSION_FILE = Path("C:/AI-BS/version.txt")


def get_current_build_version(default: str = "v5.329.127") -> str:
    try:
        if VERSION_FILE.exists():
            raw = VERSION_FILE.read_text(encoding="utf-8").strip()
            if raw:
                return raw if raw.startswith("v") else f"v{raw}"
    except Exception:
        pass
    return default


AIBS_SOVEREIGN_SYSTEM_PROMPT = """You are the core intelligence engine of AI-BS (Autonomous Intelligence & Build System), version v5.329.127+.
CRITICAL IDENTITY LOCK:
- "AI-BS" (or "AI bs" / "AIBS") ALWAYS refers to this software platform: the sovereign, local-first multi-agent AI operating system and developer studio located at C:\\AI-BS, built by Brett Adam Stehouwer.
- NEVER interpret "AI-BS" as "AI bullshit", "myth-busting", or generic AI jargon.
- Platform Architecture: Python/FastAPI backend, SQLite WAL persistence (aibs_master.db), ChromaDB vector memory, PyQt6 desktop GUI (AI_BS_Studio.exe), and Mobile Web UI connected via persistent bridge.
- Core Navigation Modules:
  1. Chat: Multi-agent coding workflow ("Prepare code change"), local Ollama (RTX 4090) + API router ("Point A -> ∞", "Pipeline (6/6)").
  2. NoCo (3D): Project NoCo off-grid greenhouse campus, hydroponics, microgrid, and Living Stage 3D simulation.
  3. VLC / Media: FFmpeg transcoding, local media playback, and October 7 Vocal Studio audio processing.
  4. Cockpit: Hardware telemetry (Ryzen 9 9950X, RTX 4090), process watchdog, and Android bridge controls.
  5. All Tools: 64-specialist subagent registry, BS-Game custom engine + Unreal Engine 5 adapters, KDP publishing (Immutable Transcription), and FE Express logistics tools.
- Communication Protocol: Direct, clinical, objective engineering tone. Zero conversational fluff, zero cheerleading ("Absolutely!", "Sure!"), and zero unverified claims."""

SHORTHAND_DISAMBIGUATION_MAP: Dict[str, str] = {
    r"\bai[\s\-]?bs\b": (
        "AI-BS (Autonomous Intelligence & Build System platform at C:\\AI-BS)"
    ),
    r"\bnoco\b": (
        "Project NoCo (NoCo 3D Campus & off-grid biosystem module in AI-BS)"
    ),
    r"\bimplication plan\b": (
        "architectural implementation plan for the C:\\AI-BS codebase"
    ),
    r"\bcockpit\b": (
        "Executive Cockpit (hardware telemetry, RTX 4090 / Ryzen 9 9950X watchdog & Android bridge module in AI-BS)"
    ),
    r"\bprepare code change\b": (
        "AI-BS reviewed coding workflow (repo_diff_architect unified diff & verification gate in C:\\AI-BS)"
    ),
}


def disambiguate_prompt_text(content: str) -> str:
    """Appends an explicit System Context Note when shorthand terms ('AI bs', 'NoCo', 'implication plan') appear."""
    if not isinstance(content, str) or not content.strip():
        return content
    if "[System Context Note:" in content:
        return content
    matched_expansions: List[str] = []
    for pattern, expansion in SHORTHAND_DISAMBIGUATION_MAP.items():
        if re.search(pattern, content, flags=re.IGNORECASE):
            matched_expansions.append(expansion)
    if not matched_expansions:
        return content
    joined = "; ".join(matched_expansions)
    return (
        f"{content}\n\n[System Context Note: References to 'AI-BS' or"
        f" shorthand refer strictly to {joined}.]"
    )


def build_sovereign_system_prompt(
    base_system_prompt: Optional[str] = None,
    active_tab: str = "Chat",
    build_version: Optional[str] = None,
) -> str:
    """Combines the immutable AI-BS Sovereign System Prompt with any caller-supplied system prompt."""
    resolved_version = build_version or get_current_build_version()
    header = (
        f"{AIBS_SOVEREIGN_SYSTEM_PROMPT}\n"
        f"Active UI Tab: {active_tab} | Build: {resolved_version}"
    )
    if not base_system_prompt or not isinstance(base_system_prompt, str):
        return header
    if "Autonomous Intelligence & Build System" in base_system_prompt:
        return base_system_prompt
    return f"{header}\n\n{base_system_prompt.strip()}"


def inject_aibs_pipeline_context(
    messages: List[Dict[str, str]],
    active_tab: str = "Chat",
    build_version: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Stage 1 of Pipeline (6/6): Prepends the immutable AI-BS identity manifest
    and normalizes ambiguous shorthand in the latest user prompt.
    """
    resolved_version = build_version or get_current_build_version()
    enriched: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                f"{AIBS_SOVEREIGN_SYSTEM_PROMPT}\nActive UI Tab:"
                f" {active_tab} | Build: {resolved_version}"
            ),
        }
    ]

    for idx, msg in enumerate(messages or []):
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Identity is additive: retain caller project context and tool limits.

        # Disambiguate shorthand in the most recent user message
        if idx == len(messages) - 1 and role == "user":
            normalized_content = disambiguate_prompt_text(content)
            enriched.append({**msg, "role": role, "content": normalized_content})
        else:
            enriched.append({**msg, "role": role, "content": content})

    return enriched
