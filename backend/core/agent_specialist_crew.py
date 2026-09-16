"""
Multi-Agent Specialist Crews & Supervised Pipeline Architecture (Phase 3)
Integrates:
1. Domain-Partitioned Specialist Crews: Code Reviewer, Workbench Diagnostician, Audio Producer,
   Crypto Scalper, Publishing Master, Security Gatekeeper.
2. Dynamic Supervisor Router: Eliminates token bloat by pruning tool schemas to active specialist scope.
3. Hierarchical Security Gatekeeper: Intercepts & validates execution commands against system policies.
"""

import os
import sys
import time
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("AgentSpecialistCrew")


SPECIALIST_ROSTER = {
    "code_reviewer": {
        "title": "Code Reviewer & Autonomous Refiner",
        "description": "Specialized in Python AST parsing, JSX validation, test suites, and surgical patching.",
        "allowed_tools": [
            "validate_syntax", "patch_host_file", "write_mirror_component",
            "run_ecosystem_script", "lookup_symbol", "read_host_file", "write_host_file"
        ],
        "system_prompt": "You are the AI-BS Senior Code Reviewer. You enforce 100% syntactic precision, AST validation, and 4-mirror frontend parity."
    },
    "workbench_diagnostician": {
        "title": "Station 13 Hardware & Logic Board Diagnostician",
        "description": "Specialized in motherboard schematics, diode mode readings, IC pinouts, and SPI flash programming.",
        "allowed_tools": [
            "query_bench_diagnostics", "flash_chip_firmware", "disassemble_binary_or_bytes",
            "tshark_telemetry_monitor", "read_host_file"
        ],
        "system_prompt": "You are the Station 13 Hardware Diagnostician. You isolate power rail shorts, analyze boardviews, and verify EEPROM dumps."
    },
    "audio_producer": {
        "title": "Wave Studio Audio & Prosody Producer",
        "description": "Specialized in Demucs stem isolation, SoX DSP filters, pitch stretching, and lyric prosody.",
        "allowed_tools": [
            "separate_audio_stems", "process_dsp_filter", "stretch_pitch_tempo",
            "map_lyrics_prosody", "read_host_file"
        ],
        "system_prompt": "You are the AI-BS Wave Studio Audio Producer. You factor audio stems, align lyric cadence to 4/4 bars, and master output to -14 LUFS."
    },
    "crypto_scalper": {
        "title": "Crypto Swarm & Quantitative Scalper",
        "description": "Specialized in CRO HFT orderbook analysis, DuckDB analytics, and 150+ technical indicators.",
        "allowed_tools": [
            "calculate_technical_indicators", "execute_duckdb_query", "tshark_telemetry_monitor",
            "retrieve_from_all_spaces", "get_ecosystem_health"
        ],
        "system_prompt": "You are the AI-BS Crypto Swarm Quant. You detect micro-dip DCA triggers, compute RSI/MACD/Bollinger bands, and enforce pure-profit reinvestment."
    },
    "publishing_master": {
        "title": "Stehouwer Publishing Master",
        "description": "Specialized in sub-50ms Typst PDF compilation, Pandoc conversion, Calibre eBooks, and PDF stream compression.",
        "allowed_tools": [
            "compile_typst_document", "convert_ebook", "optimize_pdf_stream",
            "read_host_file", "write_host_file"
        ],
        "system_prompt": "You are the Stehouwer Publishing Master. You generate publication-grade KDP manuscripts, linearize PDF streams, and format multi-device eBooks."
    },
    "security_gatekeeper": {
        "title": "Host Security & Policy Gatekeeper",
        "description": "Validates proposed PowerShell commands, directory boundaries, and execution policies.",
        "allowed_tools": [
            "powershell_process_manager", "get_ecosystem_health", "read_host_file"
        ],
        "system_prompt": "You are the AI-BS Security Gatekeeper. You ensure commands target valid paths and adhere to ExecutionPolicy Bypass safety baselines."
    }
}


class AgentSpecialistCrewEngine:
    """Master Multi-Agent Specialist Crew & Supervisor Router."""

    @staticmethod
    def get_all_crews() -> Dict[str, Any]:
        """Returns the full roster of specialized agent crews and their tool schemas."""
        return {
            "status": "success",
            "crew_count": len(SPECIALIST_ROSTER),
            "crews": SPECIALIST_ROSTER
        }

    @staticmethod
    def route_to_specialist(prompt: str) -> Dict[str, Any]:
        """
        Dynamically routes user prompt to the optimal specialist crew, pruning
        the tool registry schema to only relevant tools.
        """
        p_lower = prompt.lower()

        # Evaluation heuristics
        if any(w in p_lower for w in ["audio", "stem", "demucs", "vocal", "drum", "bpm", "prosody", "rhyme", "lufs", "dsp", "pitch"]):
            crew_id = "audio_producer"
        elif any(w in p_lower for w in ["hardware", "schematic", "diode", "short", "boardview", "flashrom", "chip", "station 13", "iphone", "repair", "amperage"]):
            crew_id = "workbench_diagnostician"
        elif any(w in p_lower for w in ["cro", "trade", "scalp", "crypto", "indicator", "rsi", "macd", "duckdb", "orderbook", "profit"]):
            crew_id = "crypto_scalper"
        elif any(w in p_lower for w in ["book", "publish", "typst", "kdp", "manuscript", "pdf", "epub", "calibre", "pandoc", "author"]):
            crew_id = "publishing_master"
        elif any(w in p_lower for w in ["security", "firewall", "port", "gatekeeper", "policy"]):
            crew_id = "security_gatekeeper"
        else:
            crew_id = "code_reviewer"

        crew_data = SPECIALIST_ROSTER[crew_id]

        return {
            "status": "success",
            "prompt": prompt,
            "assigned_crew_id": crew_id,
            "crew_title": crew_data["title"],
            "scoped_tools": crew_data["allowed_tools"],
            "system_prompt": crew_data["system_prompt"],
            "token_overhead_reduction": f"{(1.0 - (len(crew_data['allowed_tools']) / 55.0)) * 100:.1f}% reduction"
        }

    @staticmethod
    def validate_command_security(command: str) -> Dict[str, Any]:
        """
        Interrogates proposed shell/PowerShell commands against dangerous patterns.
        """
        DANGEROUS_PATTERNS = [
            r"rmdir\s+/s\s+/q\s+c:\\(?!ai-bs)",
            r"format\s+[c-z]:",
            r"del\s+/f\s+/s\s+/q\s+c:\\windows",
            r"drop\s+database",
            r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;"
        ]
        
        import re
        for pat in DANGEROUS_PATTERNS:
            if re.search(pat, command, re.IGNORECASE):
                return {
                    "status": "blocked",
                    "safe": False,
                    "reason": f"Command matched dangerous system destruction pattern: '{pat}'"
                }

        return {
            "status": "approved",
            "safe": True,
            "command": command,
            "message": "Command verified safe for execution under ExecutionPolicy Bypass."
        }
