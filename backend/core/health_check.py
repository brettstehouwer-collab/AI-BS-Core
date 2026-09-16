import urllib.request
import json
import os

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def check_url(url, name):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2.5) as response:
            if response.status in [200, 204]:
                print(f"[{GREEN}OK{RESET}] {name} is reachable.")
                return True
            else:
                print(f"[{YELLOW}WARN{RESET}] {name} returned HTTP {response.status}.")
                return False
    except urllib.error.URLError as e:
        print(f"[{RED}FAIL{RESET}] {name} is OFFLINE or UNREACHABLE: {e.reason}")
        return False
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] {name} connection error: {e}")
        return False


def check_api_health():
    try:
        url = "http://localhost:8000/api/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2.5) as response:
            data = json.loads(response.read().decode())
            print(f"\n{CYAN}--- AI-BS Daemon Diagnostics ---{RESET}")
            daemons = data.get("daemons", {})
            if not daemons:
                print(f"[{YELLOW}WARN{RESET}] No daemons reported by DaemonManager.")
            for d_name, is_alive in daemons.items():
                if is_alive:
                    print(f"  [{GREEN}ALIVE{RESET}] {d_name}")
                else:
                    print(f"  [{RED}DEAD{RESET}]  {d_name}")
    except Exception as e:
        print(
            f"\n[{RED}FATAL{RESET}] Cannot parse FastAPI Daemon state. Is the backend offline? ({e})"
        )


if __name__ == "__main__":
    print(f"{CYAN}Initializing AI-BS Master Health Check...{RESET}\n")

    # Core Infrastructure
    check_url("http://127.0.0.1:11434/", "Ollama Engine")
    check_url("http://localhost:8001/api/v2/heartbeat", "ChromaDB Vector Store")
    check_url("http://localhost:8000/docs", "FastAPI Backend Core")

    # Frontend Router
    v1 = check_url("http://localhost:4173/", "Vite Frontend (Prod/Docker 4173)")
    if not v1:
        check_url("http://localhost:5173/", "Vite Frontend (Local Dev 5173)")

    # Daemon States
    check_api_health()
    print(f"\n{CYAN}Diagnostics Complete.{RESET}")
