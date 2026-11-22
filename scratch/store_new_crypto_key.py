"""Store a Crypto.com API key/secret in the DPAPI vault WITHOUT pasting into chat.
Run locally:  python C:\\AI-BS\\scratch\\store_new_crypto_key.py
Input is hidden. The old blob is kept as a timestamped backup. Nothing is written unless the new key authenticates.
"""
import ctypes, ctypes.wintypes, getpass, importlib.util, json, time
from pathlib import Path

class BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

def protect(data: bytes) -> bytes:
    buf = ctypes.create_string_buffer(data, len(data))
    i = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))); o = BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(i), "Crypto API Key Pair", None, None, None, 1, ctypes.byref(o)):
        raise ctypes.WinError()
    try: return ctypes.string_at(o.pbData, o.cbData)
    finally: ctypes.windll.kernel32.LocalFree(o.pbData)

spec = importlib.util.spec_from_file_location("t", r"C:\AI-BS\scratch\live_cro_usdt_trader.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

key = getpass.getpass("New API KEY (hidden): ").strip()
sec = getpass.getpass("New API SECRET (hidden): ").strip()
try:
    m.CryptoComClient(key, sec).private_post("private/user-balance", {})
except Exception as e:
    raise SystemExit(f"Authentication FAILED, nothing saved: {e}")

loc = json.loads(Path(m.LOCATOR_PATH).read_text(encoding="utf-8"))
pair = Path(loc["pair"])
if pair.exists():
    pair.with_name(pair.name + f".bak-{time.strftime('%Y%m%d-%H%M%S')}").write_bytes(pair.read_bytes())
pair.write_bytes(protect(json.dumps({"api_key": key, "secret": sec}).encode()))
print("Saved and verified. Restart the engine so it loads the new key.")
