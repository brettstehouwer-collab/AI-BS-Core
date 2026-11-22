import subprocess
import json
import time
import os
import sys

def test_go_trainer_daemon_ipc():
    exe_path = os.path.join(os.path.dirname(__file__), "..", "trainer_frontend", "resources", "btd6_trainer_daemon.exe")
    assert os.path.exists(exe_path), f"Go daemon binary not found at {exe_path}"

    proc = subprocess.Popen(
        [exe_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # 1. Verify initialization log and state update
        received_state = False
        features = {}

        start_time = time.time()
        while time.time() - start_time < 5.0:
            line = proc.stdout.readline()
            if not line:
                continue
            data = json.loads(line.strip())
            if data.get("type") == "state_update":
                received_state = True
                assert data["status"] in ["SEARCHING", "ATTACHED"]
                assert "Unlimited Match Cash" in data["features"]
                assert "Unlimited Lives" in data["features"]
                assert "Unlimited Monkey Money" in data["features"]
                features = data["features"]
                break

        assert received_state, "Did not receive state_update from Go daemon"

        # 2. Test sending a scan command
        scan_cmd = {"action": "first_scan_cash", "value": 650.0}
        proc.stdin.write(json.dumps(scan_cmd) + "\n")
        proc.stdin.flush()

        received_scan_log = False
        start_time = time.time()
        while time.time() - start_time < 5.0:
            line = proc.stdout.readline()
            if not line:
                continue
            data = json.loads(line.strip())
            if data.get("type") == "log" and "First Scan Cash" in data.get("message", ""):
                received_scan_log = True
                break

        assert received_scan_log, "Did not receive scan confirmation log from Go daemon"

        # 3. Test feature toggle
        toggle_cmd = {"action": "toggle_feature", "feature": "Unlimited Match Cash"}
        proc.stdin.write(json.dumps(toggle_cmd) + "\n")
        proc.stdin.flush()

        toggled = False
        start_time = time.time()
        while time.time() - start_time < 5.0:
            line = proc.stdout.readline()
            if not line:
                continue
            data = json.loads(line.strip())
            if data.get("type") == "state_update":
                if data["features"].get("Unlimited Match Cash") is True:
                    toggled = True
                    break

        assert toggled, "Unlimited Match Cash did not toggle to True in state_update"

        # 4. Test clean shutdown
        proc.stdin.write(json.dumps({"action": "quit"}) + "\n")
        proc.stdin.flush()

        exit_code = proc.wait(timeout=3.0)
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
        print("PASS: Go daemon IPC test succeeded completely!")

    finally:
        if proc.poll() is None:
            proc.kill()

if __name__ == "__main__":
    test_go_trainer_daemon_ipc()
