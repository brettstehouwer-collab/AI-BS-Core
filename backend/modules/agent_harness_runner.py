#!/usr/bin/env python3
"""
Sovereign Agent Harness Runner Subsystem
AI-BS Antigravity Sovereign Unison Architecture
Manages sessions and execution adapters for the 14-tool sovereign agent suite:
Claude Code, Codex CLI, OpenClaw, OpenCode, Hermes Agent/Desktop, Droid, Pi,
Cline, Copilot CLI, Oh My Pi, DeepSeek Harness, Qwen Code, and Terminal.
"""

import os
import sys
import json
import time
import uuid
import asyncio
import sqlite3
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime, timezone

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logger = logging.getLogger("agent_harness_runner")

_backend_dir = Path(__file__).resolve().parent.parent
_root_dir = _backend_dir.parent
DB_PATH = _root_dir / "saved_data" / "agent_harness_sessions.db"

# 14 Sovereign Agent Applications Definition Catalog
AGENT_APPS_CATALOG: Dict[str, Dict[str, Any]] = {
    "claude_code": {
        "id": "claude_code",
        "name": "Claude Code",
        "tagline": "Terminal Pair Programmer",
        "category": "Code Synthesis & Git",
        "specialist_domain": "code",
        "default_model": "qwen2.5-coder:latest",
        "icon": "Terminal",
        "color": "#d97706", # amber
        "description": "Autonomous CLI coding agent inspired by Claude Code / Aider. Synthesizes multi-file edits, checks ASTs, and executes Git commits.",
        "capabilities": ["multi_file_edit", "git_commit", "terminal_exec", "diff_generation"],
        "version": "1.0.0"
    },
    "codex_cli": {
        "id": "codex_cli",
        "name": "Codex CLI",
        "tagline": "One-Shot Code Generator",
        "category": "Code Synthesis",
        "specialist_domain": "code",
        "default_model": "qwen2.5-coder:latest",
        "icon": "Code",
        "color": "#10b981", # emerald
        "description": "Deterministic snippet generator and algorithmic code optimizer powered by local 32.8B Qwen coder weights.",
        "capabilities": ["snippet_synthesis", "type_checking", "algorithm_design"],
        "version": "1.0.0"
    },
    "openclaw": {
        "id": "openclaw",
        "name": "OpenClaw",
        "tagline": "Autonomous Web Scraper & Crawler",
        "category": "Web & Reconnaissance",
        "specialist_domain": "function_calling",
        "default_model": "stehouwer-hermes:latest",
        "icon": "Globe",
        "color": "#06b6d4", # cyan
        "description": "Headless browser crawler and DOM extractor. Inspects web endpoints, extracts structured JSON, and generates sitemaps.",
        "capabilities": ["dom_scraping", "curl_extraction", "json_parsing", "link_traversal"],
        "version": "1.0.0"
    },
    "opencode": {
        "id": "opencode",
        "name": "OpenCode",
        "tagline": "Sandboxed Interpreter & REPL",
        "category": "Execution Sandbox",
        "specialist_domain": "code",
        "default_model": "qwen2.5-coder:latest",
        "icon": "Play",
        "color": "#8b5cf6", # purple
        "description": "Interactive Python / JavaScript code interpreter executing inside local sandboxed runtimes with zero external leaks.",
        "capabilities": ["repl_execution", "sandbox_isolation", "data_visualization", "math_eval"],
        "version": "1.0.0"
    },
    "hermes_agent": {
        "id": "hermes_agent",
        "name": "Hermes Agent",
        "tagline": "Function Calling & Tool Dispatcher",
        "category": "Agentic Orchestration",
        "specialist_domain": "function_calling",
        "default_model": "stehouwer-hermes:latest",
        "icon": "Cpu",
        "color": "#f59e0b", # amber-orange
        "description": "Multi-turn tool-calling loop utilizing Stehouwer Hermes 8B weights. Converts natural language directives into validated JSON function calls.",
        "capabilities": ["tool_dispatch", "json_schema_validation", "multi_turn_loop", "task_planning"],
        "version": "1.0.0"
    },
    "hermes_desktop": {
        "id": "hermes_desktop",
        "name": "Hermes Desktop",
        "tagline": "Host OS & Workspace Monitor",
        "category": "System Control",
        "specialist_domain": "function_calling",
        "default_model": "stehouwer-hermes:latest",
        "icon": "Monitor",
        "color": "#3b82f6", # blue
        "description": "Desktop workspace inspector for drives C:, D:, and E:. Watches directory changes, audits file permissions, and automates workspace syncing.",
        "capabilities": ["drive_audit", "file_watcher", "directory_sync", "registry_check"],
        "version": "1.0.0"
    },
    "droid": {
        "id": "droid",
        "name": "Droid",
        "tagline": "Mobile Device Automation Bridge",
        "category": "Mobile & Hardware",
        "specialist_domain": "function_calling",
        "default_model": "stehouwer-hermes:latest",
        "icon": "Smartphone",
        "color": "#22c55e", # green
        "description": "ADB bridge harness and Android emulator controller for cross-platform app diagnostics and UI hierarchy inspection.",
        "capabilities": ["adb_control", "ui_hierarchy", "apk_inspection", "screenshot_capture"],
        "version": "1.0.0"
    },
    "pi": {
        "id": "pi",
        "name": "Pi",
        "tagline": "Personal Intelligence & Empathy",
        "category": "Cognitive Dialogue",
        "specialist_domain": "creative",
        "default_model": "stehouwer_dolphin:latest",
        "icon": "Heart",
        "color": "#ec4899", # pink
        "description": "Warm, conversational cognitive partner with long-term episodic memory recall and philosophical reflection.",
        "capabilities": ["conversational_memory", "philosophical_dialogue", "empathic_synthesis"],
        "version": "1.0.0"
    },
    "cline": {
        "id": "cline",
        "name": "Cline",
        "tagline": "Autonomous IDE Pair Programmer",
        "category": "Code Synthesis & Refactor",
        "specialist_domain": "code",
        "default_model": "qwen2.5-coder:latest",
        "icon": "Layers",
        "color": "#6366f1", # indigo
        "description": "Multi-step architectural refactoring assistant that reads AST trees, plans file replacements, and validates syntax.",
        "capabilities": ["ast_refactor", "lint_repair", "test_generation", "patch_synthesis"],
        "version": "1.0.0"
    },
    "copilot_cli": {
        "id": "copilot_cli",
        "name": "Copilot CLI",
        "tagline": "Command-Line Shell Assistant",
        "category": "Host Terminal",
        "specialist_domain": "code",
        "default_model": "qwen2.5-coder:latest",
        "icon": "HelpCircle",
        "color": "#0ea5e9", # light blue
        "description": "Explains complex PowerShell / WSL2 Linux commands, suggests syntax flags, and generates one-liner terminal snippets.",
        "capabilities": ["command_explanation", "powershell_synthesis", "wsl_bridge", "flag_lookup"],
        "version": "1.0.0"
    },
    "oh_my_pi": {
        "id": "oh_my_pi",
        "name": "Oh My Pi",
        "tagline": "Creative Prompting & Muse Engine",
        "category": "Creative Ideation",
        "specialist_domain": "creative",
        "default_model": "stehouwer_dolphin:latest",
        "icon": "Sparkles",
        "color": "#a855f7", # purple-violet
        "description": "Uninhibited narrative generator for storytelling, character development, world-building, and Fire Writing manuscripts.",
        "capabilities": ["fire_writing", "narrative_arcs", "lyricism", "character_bibles"],
        "version": "1.0.0"
    },
    "deepseek_harness": {
        "id": "deepseek_harness",
        "name": "DeepSeek Harness",
        "tagline": "Deep Chain-of-Thought Reasoning",
        "category": "Symbolic Reasoning",
        "specialist_domain": "reasoning",
        "default_model": "llama3.3:70b",
        "icon": "Compass",
        "color": "#f43f5e", # rose
        "description": "Multi-step symbolic logic, formal proofs, and mathematical derivation harness running local 70.6B Q4_K_M weights.",
        "capabilities": ["chain_of_thought", "mathematical_proof", "causal_reasoning", "game_theory"],
        "version": "1.0.0"
    },
    "qwen_code": {
        "id": "qwen_code",
        "name": "Qwen Code",
        "tagline": "Polyglot Language Engine",
        "category": "Code Synthesis",
        "specialist_domain": "code",
        "default_model": "qwen2.5-coder:latest",
        "icon": "Box",
        "color": "#14b8a6", # teal
        "description": "Full-context 32k window polyglot coder supporting 92 programming languages, SQL, regex, and compiler intermediate representations.",
        "capabilities": ["polyglot_codegen", "sql_dialect_translation", "regex_construction", "cross_compilation"],
        "version": "1.0.0"
    },
    "terminal": {
        "id": "terminal",
        "name": "Terminal",
        "tagline": "Sovereign PowerShell Bypass Shell",
        "category": "System Terminal",
        "specialist_domain": "code",
        "default_model": "qwen2.5-coder:latest",
        "icon": "Square",
        "color": "#64748b", # slate
        "description": "Direct, authenticated host terminal bridge running Windows 11 PowerShell with ExecutionPolicy Bypass and WSL2 dispatch.",
        "capabilities": ["powershell_bypass", "wsl_dispatch", "process_monitoring", "environment_inspection"],
        "version": "1.0.0"
    }
}


class AgentHarnessRunner:
    """Orchestrates agent sessions, command execution, and prompt routing for the 14 agent apps."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_sqlite()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def _init_sqlite(self):
        """Initializes SQLite session registry."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_sessions (
                        session_id TEXT PRIMARY KEY,
                        app_id TEXT NOT NULL,
                        app_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        model TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        workspace_path TEXT,
                        turn_count INTEGER DEFAULT 0,
                        last_prompt TEXT,
                        last_output TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS session_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (session_id) REFERENCES agent_sessions(session_id)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing agent harness database: {e}")

    def list_apps(self) -> List[Dict[str, Any]]:
        """Returns catalog of all 14 sovereign agent applications with live session counts."""
        apps = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for app_id, app_info in AGENT_APPS_CATALOG.items():
                cursor.execute("SELECT COUNT(*) FROM agent_sessions WHERE app_id = ? AND status = 'active'", (app_id,))
                active_count = cursor.fetchone()[0]
                
                info = dict(app_info)
                info["active_sessions"] = active_count
                apps.append(info)
        return apps

    def create_session(self, app_id: str, workspace_path: Optional[str] = None) -> Dict[str, Any]:
        """Creates a new agent session for the specified app."""
        if app_id not in AGENT_APPS_CATALOG:
            raise ValueError(f"Unknown agent application ID: {app_id}")

        app_info = AGENT_APPS_CATALOG[app_id]
        session_id = f"session_{app_id}_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        ws = workspace_path or str(_root_dir)

        session_record = {
            "session_id": session_id,
            "app_id": app_id,
            "app_name": app_info["name"],
            "status": "active",
            "model": app_info["default_model"],
            "created_at": now,
            "updated_at": now,
            "workspace_path": ws,
            "turn_count": 0,
            "last_prompt": None,
            "last_output": None
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO agent_sessions 
                (session_id, app_id, app_name, status, model, created_at, updated_at, workspace_path, turn_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                session_id, app_id, app_info["name"], "active",
                app_info["default_model"], now, now, ws
            ))
            conn.commit()

        self.active_sessions[session_id] = session_record
        return session_record

    def list_sessions(self, app_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recorded agent sessions with optional filtering by app ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if app_id:
                cursor.execute("""
                    SELECT * FROM agent_sessions 
                    WHERE app_id = ? 
                    ORDER BY updated_at DESC LIMIT ?
                """, (app_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM agent_sessions 
                    ORDER BY updated_at DESC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves session metadata and conversation history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,))
            session_row = cursor.fetchone()
            if not session_row:
                return None

            cursor.execute("""
                SELECT id, role, content, timestamp, metadata 
                FROM session_messages 
                WHERE session_id = ? 
                ORDER BY id ASC
            """, (session_id,))
            messages = [dict(m) for m in cursor.fetchall()]

            data = dict(session_row)
            data["messages"] = messages
            return data

    async def execute_turn(
        self,
        session_id: str,
        prompt: str,
        system_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes a turn within an agent session, querying the MoE router and recording messages."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        app_id = session["app_id"]
        app_info = AGENT_APPS_CATALOG.get(app_id, {})
        domain = app_info.get("specialist_domain", "code")

        now = datetime.now(timezone.utc).isoformat()

        # Record user message
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO session_messages (session_id, role, content, timestamp, metadata)
                VALUES (?, 'user', ?, ?, ?)
            """, (session_id, prompt, now, json.dumps({"turn": session["turn_count"] + 1})))
            conn.commit()

        # Connect to MoE Router
        try:
            from core.sovereign_reasoning.moe_specialist_router import moe_router
            
            system_prompt = system_override or f"You are {app_info.get('name')}, an autonomous sovereign agent in AI-BS. Capabilities: {', '.join(app_info.get('capabilities', []))}."
            
            start_t = time.perf_counter()
            response = await moe_router.dispatch(
                prompt=prompt,
                system_prompt=system_prompt,
                domain_hint=domain
            )
            elapsed_ms = (time.perf_counter() - start_t) * 1000
            content = response.get("response", "")
            model_used = response.get("model", app_info.get("default_model"))
        except Exception as e:
            logger.error(f"Error querying specialist router: {e}")
            content = f"Execution error: {str(e)}"
            elapsed_ms = 0
            model_used = "error"

        reply_now = datetime.now(timezone.utc).isoformat()
        new_turn_count = session["turn_count"] + 1

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO session_messages (session_id, role, content, timestamp, metadata)
                VALUES (?, 'assistant', ?, ?, ?)
            """, (session_id, content, reply_now, json.dumps({
                "model": model_used,
                "domain": domain,
                "elapsed_ms": elapsed_ms
            })))
            conn.execute("""
                UPDATE agent_sessions 
                SET updated_at = ?, turn_count = ?, last_prompt = ?, last_output = ?, model = ?
                WHERE session_id = ?
            """, (reply_now, new_turn_count, prompt[:200], content[:200], model_used, session_id))
            conn.commit()

        return {
            "session_id": session_id,
            "turn_count": new_turn_count,
            "model_used": model_used,
            "domain": domain,
            "elapsed_ms": elapsed_ms,
            "response": content
        }

    def _record_audit_action(self, action: str, details: str, result: str, elapsed_ms: float):
        """Records terminal and agent actions into the master executive audit vault."""
        vault_db = _root_dir / "backend" / "stehouwer_vault.db"
        try:
            if vault_db.exists():
                with sqlite3.connect(vault_db) as conn:
                    conn.execute("""
                        INSERT INTO executive_action_audit
                        (action_type, action_details, executed_by, status, duration_ms, created_at)
                        VALUES (?, ?, 'sovereign_agent_harness', ?, ?, CURRENT_TIMESTAMP)
                    """, (action, details[:500], result[:200], elapsed_ms))
                    conn.commit()
        except Exception as e:
            logger.debug(f"Audit log write failed: {e}")

    async def execute_host_command(self, command: str, cwd: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes an unrestricted terminal command on the host (PowerShell bypass),
        streaming stdout and stderr line-by-line, and recording to executive action audit.
        """
        work_dir = cwd or str(_root_dir)
        start_t = time.perf_counter()
        yield {"type": "log", "line": f"[AI-BS Host Terminal] Executing: {command}"}
        
        try:
            process = await asyncio.create_subprocess_shell(
                f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "{command}"',
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            async def stream_reader(stream, stream_name):
                lines = []
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace').rstrip('\r\n')
                    lines.append(decoded)
                    yield {"type": "log", "stream": stream_name, "line": decoded}

            async for item in stream_reader(process.stdout, "stdout"):
                yield item

            async for item in stream_reader(process.stderr, "stderr"):
                yield item

            await process.wait()
            elapsed_ms = (time.perf_counter() - start_t) * 1000
            exit_code = process.returncode
            yield {"type": "command_done", "exit_code": exit_code, "elapsed_ms": elapsed_ms}
            self._record_audit_action("host_terminal_exec", command, f"Exit: {exit_code}", elapsed_ms)
        except Exception as e:
            yield {"type": "log", "stream": "stderr", "line": f"Execution error: {str(e)}"}
            yield {"type": "command_done", "exit_code": -1, "elapsed_ms": 0}

    async def stream_turn(
        self,
        session_id: str,
        prompt: str,
        system_override: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes a turn within an agent session, streaming real-time tokens and live subprocess outputs.
        Supports direct host commands prefixed with '!' or '$'.
        """
        session = self.get_session(session_id)
        if not session:
            yield {"type": "error", "message": f"Session {session_id} not found."}
            return

        app_id = session["app_id"]
        app_info = AGENT_APPS_CATALOG.get(app_id, {})
        domain = app_info.get("specialist_domain", "code")
        now = datetime.now(timezone.utc).isoformat()

        # Record user message in SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO session_messages (session_id, role, content, timestamp, metadata)
                VALUES (?, 'user', ?, ?, ?)
            """, (session_id, prompt, now, json.dumps({"turn": session["turn_count"] + 1})))
            conn.commit()

        yield {"type": "turn_start", "session_id": session_id, "app_id": app_id, "prompt": prompt}

        # Check for direct terminal command execution (e.g. !pytest, $git status, !dir)
        stripped = prompt.strip()
        if stripped.startswith("!") or stripped.startswith("$"):
            raw_cmd = stripped[1:].strip()
            full_output = []
            async for log_event in self.execute_host_command(raw_cmd, session.get("workspace_path")):
                if log_event.get("type") == "log":
                    full_output.append(log_event["line"])
                yield log_event
            
            terminal_response = "\n".join(full_output) if full_output else f"Command '{raw_cmd}' executed."
            reply_now = datetime.now(timezone.utc).isoformat()
            new_turn = session["turn_count"] + 1
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO session_messages (session_id, role, content, timestamp, metadata)
                    VALUES (?, 'assistant', ?, ?, ?)
                """, (session_id, terminal_response, reply_now, json.dumps({"model": "host_terminal", "domain": "system"})))
                conn.execute("""
                    UPDATE agent_sessions
                    SET updated_at = ?, turn_count = ?, last_prompt = ?, last_output = ?, model = 'host_terminal'
                    WHERE session_id = ?
                """, (reply_now, new_turn, prompt[:200], terminal_response[:200], session_id))
                conn.commit()
                
            yield {
                "type": "turn_complete",
                "session_id": session_id,
                "turn_count": new_turn,
                "model_used": "host_terminal",
                "response": terminal_response
            }
            return

        # Query MoE router with real-time token streaming
        from core.sovereign_reasoning.moe_specialist_router import moe_router
        system_prompt = system_override or f"You are {app_info.get('name')}, an autonomous sovereign agent in AI-BS. Capabilities: {', '.join(app_info.get('capabilities', []))}."
        
        full_tokens = []
        start_t = time.perf_counter()
        model_used = app_info.get("default_model", "qwen2.5-coder:latest")
        
        try:
            async for event_str in moe_router.stream_specialist_response(
                prompt=prompt,
                system_prompt=system_prompt,
                domain_override=domain
            ):
                if event_str.startswith("data: "):
                    raw_data = event_str[6:].strip()
                    try:
                        parsed = json.loads(raw_data)
                        if parsed.get("type") == "META_CLASSIFICATION":
                            model_used = parsed.get("model", model_used)
                            yield {"type": "meta", "model": model_used, "domain": parsed.get("domain")}
                        elif "token" in parsed:
                            token_val = parsed["token"]
                            full_tokens.append(token_val)
                            yield {"type": "token", "token": token_val}
                    except Exception:
                        pass
        except Exception as e:
            err_msg = f"Streaming error: {str(e)}"
            yield {"type": "log", "line": err_msg}
            full_tokens.append(err_msg)

        elapsed_ms = (time.perf_counter() - start_t) * 1000
        combined_response = "".join(full_tokens) if full_tokens else "Execution complete."
        reply_now = datetime.now(timezone.utc).isoformat()
        new_turn = session["turn_count"] + 1

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO session_messages (session_id, role, content, timestamp, metadata)
                VALUES (?, 'assistant', ?, ?, ?)
            """, (session_id, combined_response, reply_now, json.dumps({
                "model": model_used,
                "domain": domain,
                "elapsed_ms": elapsed_ms
            })))
            conn.execute("""
                UPDATE agent_sessions
                SET updated_at = ?, turn_count = ?, last_prompt = ?, last_output = ?, model = ?
                WHERE session_id = ?
            """, (reply_now, new_turn, prompt[:200], combined_response[:200], model_used, session_id))
            conn.commit()

        yield {
            "type": "turn_complete",
            "session_id": session_id,
            "turn_count": new_turn,
            "model_used": model_used,
            "domain": domain,
            "elapsed_ms": elapsed_ms,
            "response": combined_response
        }

    def terminate_session(self, session_id: str) -> bool:
        """Marks an active session as archived/terminated."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_sessions 
                SET status = 'archived', updated_at = ? 
                WHERE session_id = ?
            """, (now, session_id))
            conn.commit()
            return cursor.rowcount > 0


agent_harness_runner = AgentHarnessRunner()

if __name__ == "__main__":
    print("Testing Agent Harness Runner...")
    apps = agent_harness_runner.list_apps()
    print(f"Catalog contains {len(apps)} apps.")
    sess = agent_harness_runner.create_session("claude_code")
    print(f"Created session: {sess['session_id']}")
    ret = asyncio.run(agent_harness_runner.execute_turn(sess['session_id'], "What is your architecture?"))
    print(f"Response: {ret['response'][:100]}...")
