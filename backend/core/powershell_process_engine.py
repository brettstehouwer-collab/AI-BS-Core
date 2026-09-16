import os
import sys
import time
import subprocess
import json
import logging
import psutil
from typing import Dict, Any, Optional, List

logger = logging.getLogger("PowerShellProcessEngine")

CHROME_USER_DATA_PATH = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")


class PowerShellProcessEngine:
    """
    Elevated PowerShell Script Runner, Chrome Profile Sync Manager, and Directory State Inspector for AI-BS.
    """

    @staticmethod
    def execute_powershell(
        command_or_script: str,
        execution_policy: str = "Bypass",
        timeout_seconds: int = 5400,
        working_directory: str = r"C:\AI-BS"
    ) -> Dict[str, Any]:
        """
        Executes a script block via powershell -ExecutionPolicy Bypass with real-time capture.
        """
        start_time = time.time()
        cwd = working_directory if os.path.exists(working_directory) else r"C:\AI-BS"

        ps_args = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", execution_policy,
            "-Command", command_or_script
        ]

        try:
            res = subprocess.run(
                ps_args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "success" if res.returncode == 0 else "error",
                "returncode": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "elapsed_ms": elapsed_ms,
                "execution_policy": execution_policy
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "returncode": -1,
                "error": f"Execution timed out after {timeout_seconds} seconds."
            }
        except Exception as e:
            return {
                "status": "error",
                "returncode": -1,
                "error": str(e)
            }

    @staticmethod
    def manage_chrome_profiles(action: str = "status", profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Inspects and manages background Google Chrome profiles, locks, and sync states.
        """
        if not os.path.exists(CHROME_USER_DATA_PATH):
            return {"status": "error", "message": f"Chrome User Data path not found: {CHROME_USER_DATA_PATH}"}

        # Find profiles in Chrome User Data
        profiles_found = []
        for item in os.listdir(CHROME_USER_DATA_PATH):
            full_path = os.path.join(CHROME_USER_DATA_PATH, item)
            if os.path.isdir(full_path):
                if item == "Default" or item.startswith("Profile "):
                    pref_path = os.path.join(full_path, "Preferences")
                    has_prefs = os.path.exists(pref_path)
                    lock_file = os.path.join(full_path, "lockfile")
                    has_lock = os.path.exists(lock_file)
                    
                    prof_info = {
                        "name": item,
                        "path": full_path,
                        "has_preferences": has_prefs,
                        "is_locked": has_lock,
                        "size_mb": 0.0
                    }
                    try:
                        # Estimate profile size
                        total_size = sum(
                            os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, dirnames, filenames in os.walk(full_path)
                            for filename in filenames
                        )
                        prof_info["size_mb"] = round(total_size / (1024 * 1024), 2)
                    except Exception:
                        pass
                    profiles_found.append(prof_info)

        # Check running chrome processes
        chrome_pids = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    chrome_pids.append({
                        "pid": proc.info['pid'],
                        "cmdline": " ".join(proc.info['cmdline'] or [])[:150]
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if action == "unlock" and profile_name:
            target = os.path.join(CHROME_USER_DATA_PATH, profile_name)
            unlocked_files = []
            for lock_name in ["lockfile", "SingletonLock", "SingletonCookie", "SingletonSocket"]:
                lock_p = os.path.join(target, lock_name)
                if os.path.exists(lock_p):
                    try:
                        os.remove(lock_p)
                        unlocked_files.append(lock_name)
                    except Exception as e:
                        logger.warning(f"Could not remove {lock_p}: {e}")
            return {
                "status": "success",
                "action": "unlock",
                "profile": profile_name,
                "unlocked_files": unlocked_files
            }

        return {
            "status": "success",
            "action": action,
            "chrome_user_data_path": CHROME_USER_DATA_PATH,
            "profiles_count": len(profiles_found),
            "profiles": profiles_found,
            "running_chrome_processes": len(chrome_pids),
            "active_pids": chrome_pids[:10]
        }

    @staticmethod
    def inspect_directory_state(target_dir: str = r"C:\AI-BS") -> Dict[str, Any]:
        """
        Inspects directory health, file counts, disk footprints, and 4-mirror parity.
        """
        if not os.path.exists(target_dir):
            return {"status": "error", "message": f"Directory not found: {target_dir}"}

        start_time = time.time()
        file_count = 0
        dir_count = 0
        total_size = 0
        file_types = {}

        for root, dirs, files in os.walk(target_dir):
            if "node_modules" in root or ".git" in root or "__pycache__" in root:
                continue
            dir_count += len(dirs)
            for f in files:
                file_count += 1
                fp = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fp)
                    total_size += sz
                    ext = os.path.splitext(f)[1].lower() or "no_ext"
                    file_types[ext] = file_types.get(ext, 0) + 1
                except Exception:
                    pass

        # 4-mirror check
        mirror_paths = [
            r"C:\AI-BS\frontend\src\components",
            r"C:\AI-BS\frontend\components",
            r"C:\AI-BS\frontend\src\components\components",
            r"C:\AI-BS\frontend\components\components"
        ]
        mirrors_status = {}
        for mp in mirror_paths:
            if os.path.exists(mp):
                mirrors_status[mp] = len([f for f in os.listdir(mp) if f.endswith(('.jsx', '.js', '.tsx'))])
            else:
                mirrors_status[mp] = "MISSING"

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "success",
            "target_dir": target_dir,
            "total_files": file_count,
            "total_dirs": dir_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types,
            "frontend_4_mirror_parity_counts": mirrors_status,
            "elapsed_ms": elapsed_ms
        }

    @staticmethod
    def list_ecosystem_processes() -> Dict[str, Any]:
        """
        Reports processes running across the 18-port collision matrix and background daemons.
        """
        tracked_ports = [80, 3001, 4455, 5173, 5174, 8000, 8001, 8002, 8005, 8006, 8007, 8010, 8013, 8055, 8080, 8088, 8089, 8099, 8189, 8888, 11434, 11435]
        active_ports = {}
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr:
                port = conn.laddr.port
                if port in tracked_ports:
                    pid = conn.pid
                    proc_name = "Unknown"
                    if pid:
                        try:
                            proc_name = psutil.Process(pid).name()
                        except Exception:
                            pass
                    active_ports[port] = {
                        "port": port,
                        "pid": pid,
                        "process": proc_name,
                        "ip": conn.laddr.ip
                    }

        return {
            "status": "success",
            "active_listening_ports_count": len(active_ports),
            "tracked_ports_total": len(tracked_ports),
            "ports_map": active_ports
        }
