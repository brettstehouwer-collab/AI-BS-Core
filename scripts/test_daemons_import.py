import sys
from pathlib import Path

BACKEND = Path(r"C:\AI-BS\backend")
sys.path.insert(0, str(BACKEND))

modules = [
    ("Broadcast Kernel Daemon (8005)", "aibs_broadcast_daemon"),
    ("Broadcast NVENC Kernel (8088)", "aibs_broadcast_kernel"),
    ("Social Hub Daemon (8006)", "aibs_social_daemon"),
    ("VST3 Audio Bridge (8013)", "aibs_vst_daemon"),
    ("Crypto Trader Bot (8007)", "crypto_trader_bot"),
    ("Supabase Kong Gateway (8008)", "aibs_supabase_gateway"),
    ("ComfyUI Primary Proxy (8188)", "comfy_primary_proxy_8188"),
]

for label, mod in modules:
    try:
        __import__(mod)
        print(f"[OK] {label}: Successfully imported.")
    except Exception as e:
        print(f"[FAIL] {label}: Import error: {e}")
