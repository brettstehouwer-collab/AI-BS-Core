import socket

ports = [5174, 8002, 8005, 8006, 8007, 8008, 8013, 8088, 8188]
names = {
    5174: "BroadcastStudioApp Vite",
    8002: "ChromaDB Vector Store",
    8005: "Broadcast Kernel Daemon",
    8006: "Twitch / IRC Social Hub",
    8007: "Crypto Swarm & Scalp Bot",
    8008: "Supabase Kong Gateway",
    8013: "VST3 Audio Bridge",
    8088: "Broadcast NVENC Hardware Encoder",
    8188: "ComfyUI Primary Proxy",
}

online_count = 0
for p in ports:
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=0.6):
            print(f"Port {p:5d} | [ONLINE]  | {names[p]}")
            online_count += 1
    except Exception as e:
        print(f"Port {p:5d} | [OFFLINE] | {names[p]}")

print(f"\nResult: {online_count}/{len(ports)} Online")
