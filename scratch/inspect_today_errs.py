import os

log_dir = r'C:\AI-BS\logs'
today_errs = [
    'broadcast_daemon.log',
    'aibs_broadcast_daemon.err',
    'broadcast_kernel_8088.err',
    'unreal_signaling_8888.err',
    'shm_websocket_gateway.err',
    'comfy_proxy_8188.err',
    'crypto_trader_8007.err',
    'AI_BS_Backend.err',
    'gemini_mcp_server.err'
]

for f in today_errs:
    p = os.path.join(log_dir, f)
    if os.path.exists(p):
        print(f"=== {f} ===")
        with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
            lines = fp.readlines()
            for l in lines[-8:]:
                print("  ", l.strip())
        print()
