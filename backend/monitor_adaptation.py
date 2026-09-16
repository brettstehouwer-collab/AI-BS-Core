"""Monitor adaptation status."""

import sys
import time

import httpx


def monitor():
    """Monitor loop."""
    print("[Monitor] Waiting for an active adaptation task to appear...")
    active_project = None
    
    # 1. Wait for a project to start processing
    for _ in range(60):  # Poll for 60 seconds looking for a job
        try:
            # Check all projects for active job
            r = httpx.get("http://127.0.0.1:8000/api/screenwriting/projects")
            projects = r.json().get("projects", [])
            
            for p in projects:
                status_url = (
                    f"http://127.0.0.1:8000/api/screenplay/adapt/status"
                    f"?project_name={p}"
                )
                status_r = httpx.get(status_url)
                if status_r.status_code == 200:
                    data = status_r.json()
                    if data.get("status") == "processing":
                        active_project = p
                        print(f"\n[Monitor] Detected Adaptation: {p}")
                        break

            if active_project:
                break
        except httpx.RequestError:
            pass
        time.sleep(2)
    if not active_project:
        print("[Monitor] No adaptation task was started within 60 seconds.")
        sys.exit(0)
        
    # 2. Track it until completion
    last_chunk = -1
    while True:
        try:
            status_url = (
                f"http://127.0.0.1:8000/api/screenplay/adapt/status"
                f"?project_name={active_project}"
            )
            status_r = httpx.get(status_url)
            if status_r.status_code == 200:
                data = status_r.json()
                status = data.get("status")

                if status == "processing":
                    curr = data.get("current_chunk", 0)
                    if curr != last_chunk:
                        print(
                            f"[Monitor] Processing Chunk {curr} of "
                            f"{data.get('total_chunks', 0)}..."
                        )
                        last_chunk = curr
                elif status == "complete":
                    print(
                        f"\n[Monitor] Adaptation COMPLETE! Successfully "
                        f"parsed {data.get('total_chunks', 0)} chunks."
                    )
                    break
                elif status == "error":
                    print(
                        f"\n[Monitor] Adaptation FAILED! "
                        f"Error: {data.get('error')}"
                    )
                    break
        except httpx.RequestError as e:
            print(f"[Monitor] Connection error: {e}")
        time.sleep(1)


if __name__ == "__main__":
    monitor()
