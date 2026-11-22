import socket

ECOSYSTEM_PORTS = {
    80: "Nginx Gateway",
    3001: "Node Backend",
    4455: "OBS WebSocket",
    5173: "Vite Dev & Desktop Studio",
    8000: "Go Gateway",
    8002: "ChromaDB Store",
    8005: "Broadcast Daemon",
    8006: "Social Hub (Twitch/IRC)",
    8007: "Crypto Swarm & Scalp Bot",
    8010: "SHM Telemetry",
    8013: "VST3 Audio Bridge",
    8080: "FastAPI Core Engine",
    8085: "Ubuntu-Bio Bridge",
    8088: "Broadcast Kernel & NVENC",
    8089: "WSL HLS Ingest",
    8099: "Gemini MCP",
    8189: "ComfyUI Secondary / Screenplay",
    8888: "Unreal Engine Signaling (On-Demand)",
    11434: "Ollama Host (GPU Node)",
    11435: "Ollama E-Drive (CPU Node)",
}

print(f"{'PORT':<6} | {'STATUS':<10} | {'SERVICE NAME'}")
print("-" * 55)

online_count = 0
for p, name in ECOSYSTEM_PORTS.items():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    res = s.connect_ex(('127.0.0.1', p))
    s.close()
    is_online = (res == 0)
    if is_online:
        online_count += 1
    status = "ONLINE" if is_online else "OFFLINE"
    print(f"{p:<6} | {status:<10} | {name}")

print("-" * 55)
print(f"Summary: {online_count} / {len(ECOSYSTEM_PORTS)} services listening.")
