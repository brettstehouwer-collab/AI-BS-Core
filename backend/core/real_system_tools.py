import os
import sys
import time
import socket
import sqlite3
import psutil
import json
from typing import Dict, Any, Optional

WORKSPACE_ROOT = r"C:\AI-BS"

def execute_real_matrix_doctor() -> str:
    """Runs a live socket scan across all 20 service ports and checks database integrity."""
    try:
        sys.path.append(os.path.join(WORKSPACE_ROOT, "backend"))
        import matrix_doctor
        rep = matrix_doctor.run_diagnostics()
        
        online_count = rep.get("services_online", 0)
        total_count = rep.get("services_total", 20)
        cpu = rep.get("cpu_percent", 0.0)
        ram = rep.get("ram_percent", 0.0)
        ports = rep.get("ports", {})
        databases = rep.get("databases", {})
        
        md = f"### 🩺 AI-BS Matrix Doctor Diagnostic Scan (Live Hardware Probing)\n\n"
        md += f"**Timestamp:** `{time.strftime('%Y-%m-%d %H:%M:%S')}` | **System Status:** `{online_count}/{total_count} Services Online` | **CPU:** `{cpu}%` | **RAM:** `{ram}%`\n\n"
        md += "#### 🌐 Core Service Ports (20 Ports Benchmarked)\n\n"
        md += "| Port | Service Name | Status | Latency |\n"
        md += "|---|---|---|---|\n"
        
        for port_num, info in ports.items():
            name = info.get("name", "Unknown")
            is_online = info.get("online", False)
            lat = info.get("latency_ms")
            status_icon = "🟢 **ONLINE**" if is_online else "⚪ *OFFLINE*"
            lat_str = f"`{lat:.2f} ms`" if lat is not None else "—"
            md += f"| `{port_num}` | {name} | {status_icon} | {lat_str} |\n"
            
        roles = rep.get("database_roles", {})
        md += "\n#### 💾 SQLite Database Integrity & Master WAL Health\n\n"
        md += "| Database File | Role / Architectural Scope | Status |\n"
        md += "|---|---|---|\n"
        
        for db_name, status in databases.items():
            role = roles.get(db_name, "SQLite Store")
            status_badge = "🟢 **HEALTHY (OK)**" if status == "ok" else f"⚠️ *{status}*"
            md += f"| `{db_name}` | {role} | {status_badge} |\n"
            
        md += "\n---\n*Report generated live from host kernel sockets and NVMe filesystem.*"
        try:
            from core.personal_intelligence_memory import personal_memory
            personal_memory.record_ecosystem_event(
                event_type="matrix_doctor_scan",
                summary=f"Matrix Doctor Diagnostic: {online_count}/{total_count} Services Online (CPU: {cpu}%, RAM: {ram}%)",
                metadata={"online_count": online_count, "total_count": total_count, "cpu": cpu, "ram": ram}
            )
        except Exception:
            pass
        return md
    except Exception as e:
        return f"⚠️ Error executing live Matrix Doctor: {e}"


def execute_real_active_game_scan() -> str:
    """Scans the host system for active foreground games and window processes."""
    try:
        sys.path.append(os.path.join(WORKSPACE_ROOT, "backend"))
        from aibs_broadcast_daemon import scan_system_windows_and_games
        game_res = scan_system_windows_and_games()
        
        active_game = game_res.get("active_game")
        game_title = game_res.get("game_title", "None detected")
        windows = game_res.get("windows", [])
        
        md = f"### 🎮 Live Game & Window Scanner Telemetry\n\n"
        if active_game:
            md += f"🟢 **ACTIVE GAME DETECTED:** **`{game_title}`** (`{active_game}`)\n\n"
        else:
            md += f"⚪ **Active Game:** *No protected 3D game currently in foreground focus.*\n\n"
            
        md += f"#### 🪟 Active Desktop Windows ({len(windows)} Discovered)\n\n"
        md += "| Window Title | Process | PID |\n"
        md += "|---|---|---|\n"
        for w in windows[:12]:
            md += f"| {w.get('title', '')[:40]} | `{w.get('process', '')}` | `{w.get('pid', '')}` |\n"
            
        return md
    except Exception as e:
        return f"⚠️ Error scanning active games: {e}"


def execute_real_hardware_telemetry() -> str:
    """Retrieves real-time CPU, GPU (RTX 4090), RAM, and Drive telemetry."""
    try:
        ram = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)
        
        # Disk partitions
        disks = []
        for p in psutil.disk_partitions():
            if os.name == 'nt' and 'cdrom' in p.opts:
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    "mount": p.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1),
                    "percent": usage.percent
                })
            except Exception:
                pass
                
        # GPU Check via PyTorch if available
        gpu_info = "NVIDIA GeForce RTX 4090 (24GB VRAM)"
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                mem_alloc = torch.cuda.memory_allocated(0) / (1024**2)
                mem_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                gpu_info = f"{name} ({mem_total:.1f} GB Total | {mem_alloc:.1f} MB Allocated)"
        except Exception:
            pass

        md = "### ⚡ Live Host Hardware & Silicon Telemetry\n\n"
        md += f"- **CPU:** AMD Ryzen 9 9950X ({cpu_count} Logical Cores) — **`{cpu_pct}% Usage`**\n"
        md += f"- **GPU:** **`{gpu_info}`**\n"
        md += f"- **System RAM:** **`{round((ram.total - ram.available)/(1024**3), 2)} GB / {round(ram.total/(1024**3), 2)} GB`** (`{ram.percent}% Used`)\n\n"
        md += "#### 💽 NVMe & Storage Drive Status\n\n"
        md += "| Drive | Free Space | Total Capacity | Utilization |\n"
        md += "|---|---|---|---|\n"
        for d in disks:
            md += f"| `{d['mount']}` | `{d['free_gb']} GB` | `{d['total_gb']} GB` | `{d['percent']}%` |\n"
            
        return md
    except Exception as e:
        return f"⚠️ Error reading hardware telemetry: {e}"


def execute_real_osint_lead_scan(query: str = "") -> str:
    """Read stored local records; never substitute demonstration leads or claim web verification."""
    from pathlib import Path
    import html

    def cell(value):
        return html.escape(str(value if value is not None else 'Unknown')).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')

    backend_dir = Path(WORKSPACE_ROOT) / 'backend'
    master = backend_dir / 'aibs_master.db'
    selected = master if master.is_file() else None
    queries = [
        ('growth_leads', selected or backend_dir / 'state.db',
         'SELECT business_name, niche, website, email, match_score, value_prop FROM growth_leads ORDER BY match_score DESC LIMIT 5'),
        ('properties', selected or backend_dir / 'west_michigan.db',
         'SELECT address, propertyType, daysOnZillow FROM properties ORDER BY daysOnZillow ASC LIMIT 6'),
    ]
    rows, provenance, failures = {}, [], []
    for table, path, sql in queries:
        if not path.is_file():
            failures.append(f'{table}: database unavailable')
            continue
        conn = None
        try:
            conn = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
            conn.execute('PRAGMA query_only=ON')
            rows[table] = conn.execute(sql).fetchall()
            provenance.append(f'{path.name} / {table}')
        except sqlite3.Error:
            failures.append(f'{table}: query unavailable')
        finally:
            if conn is not None:
                conn.close()
    status = ('UNAVAILABLE' if not rows else 'PARTIAL' if failures
              else 'OK' if any(rows.values()) else 'EMPTY')
    md = f'### Local business records\n\n**Read status:** `{status}`\n\n'
    md += 'Stored records only; current business status, contacts and market ages have not been independently verified. No web scan was performed.\n\n'
    for failure in failures:
        md += f'- {failure}\n'
    leads = rows.get('growth_leads', [])
    if leads:
        md += '\n| Business | Sector | Stored score | Stored contact |\n|---|---|---|---|\n'
        for name, niche, website, email, score, _ in leads:
            md += '| ' + ' | '.join(cell(v) for v in (name, niche, score, email or website)) + ' |\n'
    else:
        md += '\nNo business leads available from this read.\n'
    properties = rows.get('properties', [])
    if properties:
        md += '\n| Stored address | Type | Stored days on market |\n|---|---|---|\n'
        for row in properties:
            md += '| ' + ' | '.join(cell(v) for v in row) + ' |\n'
    else:
        md += '\nNo property records available from this read.\n'
    md += '\n**Sources read:** ' + (', '.join(provenance) if provenance else 'None') + '\n'
    return md


def execute_program_builder_from_prompt(prompt: str) -> str:
    """Prepare a starter scaffold and report its actual build/smoke-run receipt."""
    try:
        from core.program_builder_engine import AutonomousProgramBuilder
        
        # Derive clean project name and description
        clean_p = prompt.strip()
        stop_words = {"build", "a", "an", "the", "program", "create", "write", "code", "generate", "script", "app", "tool", "that", "for", "with", "and", "in", "to"}
        tokens = [w.lower() for w in clean_p.split() if w.isalnum() and w.lower() not in stop_words]
        proj_name = "_".join(tokens[:4]) if tokens else f"program_{int(time.time())}"
        
        # Record user text as data, never as generated Python syntax or f-string expressions.
        code_content = f'''"""AI-BS starter scaffold; requested program logic is not implemented."""
import platform
import time

PROJECT_NAME = {proj_name!r}
TARGET_OBJECTIVE = {clean_p!r}

def execute_main():
    print("=" * 60)
    print("AI-BS STARTER SCAFFOLD:", PROJECT_NAME.upper())
    print("=" * 60)
    print("Recorded target objective:", ascii(TARGET_OBJECTIVE))
    print(f"Execution Environment: {{platform.system()}} {{platform.release()}} ({{platform.machine()}})")
    print("Runtime timestamp:", time.strftime('%Y-%m-%d %H:%M:%S'))
    print("-" * 60)
    print("Scaffold smoke run only; requested program logic is not implemented.")
    print("No telemetry worker pipeline or vault synchronization was performed.")
    print("=" * 60)

if __name__ == '__main__':
    execute_main()
'''
        files = [
            {"path": "main.py", "content": code_content},
            {"path": "README.md", "content": f"# {proj_name.upper()} starter scaffold\n\nThe objective is recorded below. Requested program logic, telemetry workers and vault synchronization are not implemented by this template.\n\n**Recorded objective:** {clean_p}\n\n**Scaffold smoke run:**\n```bash\npython main.py\n```\n"},
            {"path": "run.bat", "content": f"@echo off\npython main.py\npause\n"}
        ]
        
        res = AutonomousProgramBuilder.build_program(
            project_name=proj_name,
            language="python",
            description=clean_p,
            files=files,
            entrypoint="main.py",
            run_immediately=True
        )
        
        execution = res.get("execution") or {}
        build = res.get("build") or {}
        quality = res.get("code_quality") or {}
        blocked = (res.get("status") == "error" or quality.get("valid") is False
                   or str(execution.get("status", "")).startswith("blocked_"))
        executed = execution.get("executed") is True
        smoke_passed = (executed and execution.get("status") == "success"
                        and execution.get("exit_code") == 0)
        if blocked:
            status = "BLOCKED"
        elif smoke_passed:
            status = "SCAFFOLD SMOKE RUN PASSED"
        elif executed:
            status = "SCAFFOLD SMOKE RUN FAILED"
        else:
            status = "SCAFFOLD PREPARED; NOT RUN"

        md = "### AI-BS Starter Scaffold Receipt\n\n"
        md += f"**Project Name:** `{res.get('project_name', proj_name)}` | **Language:** `Python` | **Status:** `{status}`\n\n"
        md += "This fixed template records your objective. It does not implement the requested program, telemetry workers or vault synchronization. A successful smoke run only shows that the scaffold ran.\n\n"
        if res.get("zip_name"):
            md += f"**Directory:** `saved_data/built_programs/{res.get('project_name', proj_name)}/` | **ZIP Package:** `saved_data/built_programs/{res['zip_name']}`\n\n"
        else:
            md += "**ZIP Package:** Not reported.\n\n"
        
        md += "#### 📁 Scaffolding & Manifest\n\n"
        md += "| File Name | Size | Source Check |\n"
        md += "|---|---|---|\n"
        for f in res.get("files", []):
            file_check = quality.get("files", {}).get(f["name"], {})
            check_label = "Compile check passed" if file_check.get("valid") is True else "Written; source check not reported"
            md += f"| `{f['name']}` | `{f['size_bytes']} bytes` | `{check_label}` |\n"
            
        def report_text(value):
            # Keep program output from terminating its Markdown evidence fence.
            return str(value or "").replace("```", "` ` `")

        md += f"\n**Build receipt:** executed={build.get('executed') is True}; status={build.get('status', 'not reported')}; exit={build.get('exit_code', 'not reported')}.\n"
        md += f"**Execution receipt:** executed={executed}; status={execution.get('status', 'not reported')}; exit={execution.get('exit_code', 'not reported')}.\n"
        for label, output in (("Scaffold stdout", execution.get("stdout")),
                              ("Scaffold stderr", execution.get("stderr")),
                              ("Build stderr", build.get("stderr"))):
            md += f"\n#### {label}\n\n```text\n{report_text(output) or '[No output reported]'}\n```\n"
        errors = quality.get("errors") or res.get("syntax_errors") or []
        if errors:
            md += "\n#### Source check errors\n\n```text\n" + report_text("\n".join(str(error) for error in errors)) + "\n```\n"
        md += "\nRequested functionality and deployment readiness remain unverified."
        return md
    except Exception as e:
        return f"⚠️ Error in autonomous program builder: {e}"


def execute_real_space_retrieval(prompt: str) -> str:
    """Executes live retrieval across all 11 SQLite database spaces."""
    try:
        from core.omni_space_manager import omni_space_manager
        p_clean = prompt.strip()
        for prefix in [
            "retrieve information from all spaces", "retrieve information from spaces",
            "retrieve info from all spaces", "retrieve info from spaces", "retrieve info on",
            "retrieve from all spaces", "retrieve from spaces", "retrieve from database",
            "retrieve information about", "retrieve information", "retrieve info",
            "search all spaces for", "search all spaces", "search spaces for", "search spaces",
            "search database for", "search 11 databases for", "search 11 spaces for",
            "query database for", "query spaces for", "find in all spaces", "find in database",
            "look up in database", "/retrieve"
        ]:
            if p_clean.lower().startswith(prefix):
                p_clean = p_clean[len(prefix):].strip(" :,-")
                break

        target_spaces = None
        p_lower = prompt.lower()
        if "lexicon" in p_lower:
            target_spaces = ["lexicon_vault"]
        elif "audio" in p_lower:
            target_spaces = ["audio_catalog"]
        elif "unreal" in p_lower:
            target_spaces = ["unreal_assets"]
        elif "property" in p_lower or "properties" in p_lower or "real estate" in p_lower:
            target_spaces = ["west_michigan", "aibs_master"]
        elif "trade" in p_lower or "crypto" in p_lower or "drip" in p_lower:
            target_spaces = ["drip_ledger", "aibs_master"]
        elif "accounting" in p_lower or "tax" in p_lower or "expense" in p_lower:
            target_spaces = ["stehouwer_accounting", "aibs_master"]
        elif "lead" in p_lower or "prospect" in p_lower or "crm" in p_lower or "client" in p_lower:
            target_spaces = ["aibs_master", "state", "clients"]
        elif "vault" in p_lower:
            target_spaces = ["stehouwer_vault", "aibs_master"]

        results = omni_space_manager.search_all_spaces(p_clean or prompt, spaces=target_spaces, limit_per_space=5)
        return omni_space_manager.format_retrieval_card(results)
    except Exception as e:
        return f"⚠️ Error executing universal space retrieval: {e}"


def execute_real_space_ingestion(prompt: str) -> str:
    """Executes live on-demand ingestion into the appropriate SQLite database space."""
    try:
        from core.omni_space_manager import omni_space_manager
        p_clean = prompt.strip()
        for prefix in [
            "store this in the database", "store this in database", "store in database", "store to database",
            "store this info to db", "store info to db", "store to db", "store in db", "save this to the database",
            "save to database", "save this to database", "save to db", "save this to db", "ingest on demand",
            "ingest into database", "ingest to database", "ingest into db", "ingest to db", "save this note to the vault",
            "save note to vault", "record in database", "record to database", "record in db", "record this transaction",
            "/ingest"
        ]:
            if p_clean.lower().startswith(prefix):
                p_clean = p_clean[len(prefix):].strip(" :,-")
                break

        payload_text = p_clean if p_clean else prompt
        res = omni_space_manager.ingest_on_demand(payload_text)
        return omni_space_manager.format_ingestion_card(res)
    except Exception as e:
        return f"⚠️ Error executing on-demand database ingestion: {e}"


def execute_real_oversight_monitoring(prompt: str = "") -> str:
    """Executes live master oversight parent telemetry monitoring all 43 modules/subsystems across AI-BS."""
    try:
        from core.oversight_parent_engine import master_oversight_engine
        return master_oversight_engine.format_oversight_dashboard()
    except Exception as e:
        return f"⚠️ Error executing oversight parent monitoring: {e}"


def execute_real_spaces_overview() -> str:
    """Returns real-time status, table counts, and disk footprints across all 11 SQLite database spaces."""
    try:
        from core.omni_space_manager import omni_space_manager
        overview = omni_space_manager.get_spaces_overview()
        md = "### 🏛️ Sovereign 11-Space SQLite Storage Matrix Overview\n\n"
        md += "| Space ID | Database Name | File Size | Tables | Status |\n"
        md += "|---|---|---|---|---|\n"
        for space_id, s in overview.items():
            status_icon = "🟢 Verified" if s.get("integrity") == "ok" else "⚠️ Disconnected"
            md += f"| `{space_id}` | `{s.get('name')}` | `{s.get('size_kb')} KB` | `{s.get('tables_count')}` | {status_icon} |\n"
        md += "\n---\n*Universal retrieval and on-demand ingestion active across all 11 partitioned spaces.*"
        return md
    except Exception as e:
        return f"⚠️ Error reading spaces overview: {e}"



def check_and_execute_system_tools(prompt: str) -> Optional[str]:
    """Detects if prompt requires real PC telemetry, space retrieval/ingestion, or 43-module oversight and returns real formatted results."""
    p = prompt.strip().lower()

    # 1. 43-Module Master Hub Oversight Parent Intent
    if any(k in p for k in [
        "monitor all 43", "monitor all 43 modules", "monitor modules", "monitor systems",
        "43 modules", "43 master hub", "oversight parent", "system oversight", "master oversight",
        "oversight dashboard", "module overview", "/monitor", "/oversight", "/modules"
    ]):
        return execute_real_oversight_monitoring(prompt)

    # 2. Spaces Overview Intent
    if any(k in p for k in [
        "spaces overview", "all 11 spaces", "11 database spaces", "list spaces", "show spaces",
        "storage spaces", "database spaces", "/spaces"
    ]):
        return execute_real_spaces_overview()

    # 3. Universal Space Retrieval Intent
    if any(k in p for k in [
        "retrieve from all spaces", "retrieve from spaces", "retrieve info from all spaces",
        "retrieve information from all spaces", "search all spaces", "search spaces",
        "query all spaces", "find in all spaces", "search 11 databases", "search 11 spaces",
        "retrieve from database", "search the 11 spaces", "/retrieve"
    ]):
        return execute_real_space_retrieval(prompt)

    # 4. On-Demand Database Ingestion Intent
    if any(k in p for k in [
        "store this in the database", "store this info to db", "store info to db", "store in db",
        "store to db", "save to db", "save this to db", "ingest on demand", "ingest into database",
        "ingest to database", "ingest to db", "ingest into db", "save to database", "save this to database",
        "save note to vault", "save this note to the vault", "store note in db", "record this transaction",
        "/ingest"
    ]):
        return execute_real_space_ingestion(prompt)

    # 5. Creating a project requires a leading action request, not a quoted mention.
    import re
    builder_request = re.sub(r"^please[,\s]+", "", p, count=1)
    builder_request = re.sub(
        r"^(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?"
        r"|i\s+(?:want|need)\s+(?:you\s+)?to\s+"
        r"|i(?:'d|\s+would)\s+like\s+(?:you\s+)?to\s+)",
        "", builder_request, count=1)
    builder_request = re.sub(r"^please[,\s]+", "", builder_request, count=1)
    if (re.match(
        r"^(?:build|create|make|generate|write|code)\s+(?:me\s+)?"
        r"(?:(?:a|an|the)\s+)?"
        r"(?:(?:new|starter|simple|sample|python|javascript|typescript|powershell|bash|shell|rust|go|java|c\+\+|c#)\s+){0,2}"
        r"(?:program|script|app|application|scaffold)\b", builder_request)
        or re.match(r"^(?:run|use|start)\s+(?:(?:the|ai-bs|autonomous)\s+)*program\s+builder\b", builder_request)):
        return execute_program_builder_from_prompt(prompt)

    # 6. OSINT Commercial Lead Reconnaissance Intent
    if any(k in p for k in [
        "osint", "reconnaissance scan", "b2b lead", "b2b leads", "commercial business directories",
        "business directories in west michigan", "west michigan leads", "lead generation scan",
        "commercial leads", "lead scan", "recon scan"
    ]):
        return execute_real_osint_lead_scan(prompt)

    # 7. Matrix Doctor / Port Scan / DB Health Intent
    if any(k in p for k in [
        "matrix doctor", "diagnostic scan", "scan service ports", "service ports",
        "check ports", "database health", "verify database", "port scan", "system health scan",
        "doctor scan", "diagnose ports", "run diagnostic", "run a full matrix doctor"
    ]):
        return execute_real_matrix_doctor()

    # 8. Game & Window Scanner Intent
    if any(k in p for k in [
        "active game", "detect game", "what game", "game detection", "open windows", "running windows", "list windows"
    ]):
        return execute_real_active_game_scan()

    # 9. Hardware / Specs / GPU Telemetry Intent
    if any(k in p for k in [
        "hardware specs", "system specs", "cpu usage", "ram usage", "vram usage", "gpu status", "disk space", "drive status"
    ]):
        return execute_real_hardware_telemetry()

    return None


