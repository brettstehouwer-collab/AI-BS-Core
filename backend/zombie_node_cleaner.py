import os
import sys
import psutil


def get_active_listening_pids():
    """Identify PIDs of processes listening on active network ports."""
    active_pids = set()
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == psutil.CONN_LISTEN and conn.pid:
                active_pids.add(conn.pid)
    except Exception:
        pass
    # Always include current process and parent process
    active_pids.add(os.getpid())
    if hasattr(os, "getppid"):
        active_pids.add(os.getppid())
    return active_pids


def sweep_zombie_nodes():
    """Terminate orphaned python, node, and llama-server processes holding no active listening sockets."""
    active_pids = get_active_listening_pids()
    target_names = [
        "node.exe",
        "node",
        "python.exe",
        "python",
        "llama-server.exe",
        "t-rex.exe",
        "unrealeditor.exe",
        "ai_bs_hub.exe",
    ]

    terminated_count = 0
    freed_bytes = 0

    print("[AI-BS Zombie Node Cleaner] Starting process sweep...")

    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            pname = proc.info["name"]
            pid = proc.info["pid"]

            if pname and pname.lower() in target_names:
                if pid not in active_pids:
                    # Check if process is an orphaned worker
                    mem = (
                        proc.info["memory_info"].rss if proc.info["memory_info"] else 0
                    )
                    print(
                        f"   [TERMINATING ZOMBIE] {pname} (PID: {pid}) - Reclaiming {round(mem / 1024 / 1024, 2)} MB RAM"
                    )
                    proc.kill()
                    terminated_count += 1
                    freed_bytes += mem
                else:
                    print(f"   [PRESERVING SERVICE] {pname} (PID: {pid})")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    freed_mb = round(freed_bytes / 1024 / 1024, 2)
    print("==========================================================")
    print(
        f"[AI-BS Zombie Node Sweep Complete] Terminated {terminated_count} zombie nodes."
    )
    print(f"Total Memory Reclaimed: {freed_mb} MB RAM")
    print("==========================================================")


if __name__ == "__main__":
    sweep_zombie_nodes()
