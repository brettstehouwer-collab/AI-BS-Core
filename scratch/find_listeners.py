import subprocess
import re

res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
lines = res.stdout.splitlines()

target_ports = ["47984", "47989", "47990", "48010", "48000"]

found = []
for l in lines:
    for p in target_ports:
        if f":{p}" in l:
            found.append(l.strip())

print(f"Total matching socket lines: {len(found)}")
for l in found:
    print("  ", l)

pids = set()
for l in found:
    parts = l.split()
    if parts:
        pids.add(parts[-1])

print("\nPIDs owning these sockets:", pids)
for pid in pids:
    try:
        proc = subprocess.run(["tasklist", "/fi", f"PID eq {pid}"], capture_output=True, text=True)
        print(f"\nPID {pid} info:\n" + proc.stdout.strip())
    except Exception as e:
        print(f"Error checking PID {pid}: {e}")
