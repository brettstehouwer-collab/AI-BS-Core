import time
import requests
import os

PORT_FILE = r"C:\AI-BS\backend\.writer_daemon_port"


def get_writer_port():
    try:
        with open(PORT_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "8111"


def main():
    # Wait for daemon to boot and write the port file
    time.sleep(2)
    port = get_writer_port()
    print(f"[Test] Using Daemon Port: {port}")

    # 1. Queue a massive batch of 10,000 files with LOW priority (10)
    low_priority_data = [
        (
            "C:\\",
            f"C:\\dummy\\low_priority_file_{i}.txt",
            f"low_priority_file_{i}.txt",
            ".txt",
            100,
            time.time(),
        )
        for i in range(1000)
    ]
    print("[Test] Sending 1000 low-priority insert rows...")
    requests.post(
        f"http://127.0.0.1:{port}/write_batch",
        json={"priority": 10, "rows": low_priority_data},
    )

    # 2. Queue another batch of 10,000 files with LOW priority (10)
    low_priority_data_2 = [
        (
            "C:\\",
            f"C:\\dummy\\low_priority_file_B_{i}.txt",
            f"low_priority_file_B_{i}.txt",
            ".txt",
            100,
            time.time(),
        )
        for i in range(1000)
    ]
    print("[Test] Sending another 1000 low-priority insert rows...")
    requests.post(
        f"http://127.0.0.1:{port}/write_batch",
        json={"priority": 10, "rows": low_priority_data_2},
    )

    # 3. Queue a CRITICAL path deletion with HIGH priority (1)
    # Because it is in a PriorityQueue, the daemon will process this BEFORE it processes the second low-priority batch
    # if it hasn't already pulled it from the queue.
    print("[Test] Sending HIGH-PRIORITY delete request...")
    requests.post(
        f"http://127.0.0.1:{port}/delete_path",
        json={"priority": 1, "filepath": "C:\\critical_path\\delete_me.txt"},
    )

    print(
        "[Test] All requests queued. Check the daemon output to see the high-priority task jump the queue."
    )


if __name__ == "__main__":
    main()
