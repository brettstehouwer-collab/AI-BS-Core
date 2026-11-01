import subprocess
import time
import asyncio
import sys
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

    # Ensure all subprocess calls on Windows are completely silent (no flashing console/terminal windows)
    _orig_run = subprocess.run
    _orig_popen = subprocess.Popen
    _orig_check_output = subprocess.check_output

    _hidden_startupinfo = subprocess.STARTUPINFO()
    _hidden_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _hidden_startupinfo.wShowWindow = 0

    def _silent_run(*args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        if "startupinfo" not in kwargs:
            kwargs["startupinfo"] = _hidden_startupinfo
        return _orig_run(*args, **kwargs)

    class _SilentPopen(_orig_popen):
        def __init__(self, *args, **kwargs):
            if "creationflags" not in kwargs:
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            if "startupinfo" not in kwargs:
                kwargs["startupinfo"] = _hidden_startupinfo
            super().__init__(*args, **kwargs)

    def _silent_check_output(*args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        if "startupinfo" not in kwargs:
            kwargs["startupinfo"] = _hidden_startupinfo
        return _orig_check_output(*args, **kwargs)

    subprocess.run = _silent_run
    subprocess.Popen = _SilentPopen
    subprocess.check_output = _silent_check_output
import logging
import json
import os
import threading
import re
import socket
import csv
import io
import win32gui
import win32process
import psutil
try:
    from aibs_obs_orchestrator import OBSOrchestrator
except ImportError:
    OBSOrchestrator = None
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from pydantic import BaseModel
import uvicorn
from typing import List, Dict, Any, Optional
try:
    from backend.core.native_window_capture import NativeWindowCapture
    from backend.core.window_capture_pipe import WindowCapturePipe
except ImportError:
    try:
        from core.native_window_capture import NativeWindowCapture
        from core.window_capture_pipe import WindowCapturePipe
    except ImportError:
        NativeWindowCapture = None
        WindowCapturePipe = None
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] BroadcastDaemon: %(message)s")

app = FastAPI(title="AI-BS Resilient Broadcast & NVENC Daemon")

BROADCAST_ALLOWED_ORIGINS = (
    "http://localhost:5173", "http://localhost:5174",
    "http://127.0.0.1:5173", "http://127.0.0.1:5174",
    "https://ai-bs-dashboard.web.app", "https://ai-bs-dashboard.firebaseapp.com",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(BROADCAST_ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_broadcast_origin(request: Request, call_next):
    """Reject browser-origin dispatch before side effects, including simple POSTs.

    CORS response headers alone do not prevent cross-site form submissions.
    Native local clients without browser Origin headers remain compatible. This
    is an origin boundary, not authentication against hostile local processes.
    """
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if (origin is not None and origin not in BROADCAST_ALLOWED_ORIGINS) or (
            origin is None and request.headers.get("sec-fetch-site") == "cross-site"
        ):
            return JSONResponse({"detail": "Broadcast dispatch origin is not allowed."}, status_code=403)
    return await call_next(request)

def build_encoder_flags(encoder_name: str, preset: str = "p1", tune: str = "ull") -> List[str]:
    enc = encoder_name.lower()
    if "av1" in enc and "nvenc" in enc:
        return ["-c:v", "av1_nvenc", "-preset", "p1", "-tune", "ull", "-rc", "cbr", "-zerolatency", "1", "-delay", "0", "-bf", "0", "-no-scenecut", "1", "-forced-idr", "1"]
    elif "hevc" in enc or "h265" in enc:
        if "nvenc" in enc:
            return ["-c:v", "hevc_nvenc", "-preset", "p1", "-tune", "ull", "-rc", "cbr", "-zerolatency", "1", "-delay", "0", "-bf", "0", "-no-scenecut", "1", "-forced-idr", "1"]
        elif "qsv" in enc:
            return ["-c:v", "hevc_qsv", "-preset", "veryfast", "-bf", "0"]
        elif "amf" in enc:
            return ["-c:v", "hevc_amf", "-quality", "speed", "-rc", "cbr", "-bf", "0"]
        else:
            return ["-c:v", "libx265", "-preset", "veryfast", "-bf", "0"]
    elif "nvenc" in enc:
        return ["-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ull", "-rc", "cbr", "-zerolatency", "1", "-delay", "0", "-bf", "0", "-no-scenecut", "1", "-forced-idr", "1", "-profile:v", "high", "-level", "4.2"]
    elif "qsv" in enc:
        return ["-c:v", "h264_qsv", "-preset", "veryfast", "-global_quality", "23", "-bf", "0", "-profile:v", "high", "-level", "4.2"]
    elif "amf" in enc:
        return ["-c:v", "h264_amf", "-quality", "speed", "-rc", "cbr", "-bf", "0", "-profile:v", "high", "-level", "4.2"]
    elif "svtav1" in enc:
        return ["-c:v", "libsvtav1", "-preset", "8"]
    else:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-bf", "0", "-profile:v", "high", "-level", "4.2"]

def detect_optimal_encoder() -> dict:
    encoders_to_test = [
        {"name": "av1_nvenc",  "extra_args": ["-preset", "p5", "-tune", "ll", "-rc", "cbr"]},
        {"name": "h264_nvenc", "extra_args": ["-preset", "p5", "-tune", "ll", "-rc", "cbr"]},
        {"name": "hevc_nvenc", "extra_args": ["-preset", "p5", "-tune", "ll", "-rc", "cbr"]},
        {"name": "h264_qsv",   "extra_args": ["-preset", "veryfast", "-global_quality", "23"]},
        {"name": "h264_amf",   "extra_args": ["-quality", "speed", "-rc", "cbr"]},
        {"name": "libx264",    "extra_args": ["-preset", "veryfast", "-tune", "zerolatency"]}
    ]
    
    for enc in encoders_to_test:
        test_cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1",
            "-c:v", enc["name"], "-f", "null", "-"
        ]
        try:
            res = subprocess.run(test_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            if res.returncode == 0:
                logging.info(f"Dynamic Hardware Probe selected encoder: {enc['name']}")
                return enc
        except Exception:
            pass
            
    logging.warning("Hardware encoders probe fallback to libx264.")
    return {"name": "libx264", "extra_args": ["-preset", "veryfast"]}

def detect_microphone() -> Optional[str]:
    """Return an enumerated device only; missing hardware must not become a fake name."""
    cmd = ["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding='utf-8', errors='replace', timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        logging.warning("Audio device enumeration unavailable; no microphone selected.")
        return None
    devices = []
    for line in (res.stderr or '')[:65536].split('\n'):
        if '"' in line and "(audio)" in line and "Alternative name" not in line:
            match = re.search(r'"([^"]+)"', line)
            if match:
                dev_name = match.group(1)
                devices.append(dev_name)
                if any(k in dev_name.lower() for k in ["mic", "focusrite", "realtek", "usb", "audio", "headset"]):
                    logging.info(f"Dynamically detected Audio Input: {dev_name}")
                    return dev_name
    return devices[0] if devices else None


def probe_single_endpoint(ep: Dict[str, Any]) -> Dict[str, Any]:
    name = ep.get("name", "Unknown")
    url = ep.get("url", "")
    key = ep.get("key", "")
    enabled = ep.get("enabled", True)

    if not enabled:
        return {"name": name, "status": "DISABLED", "reachable": True, "message": "Disabled in settings", "latency_ms": 0}

    if name == "Virtual Camera":
        return {"name": name, "status": "READY", "reachable": True, "message": "DirectShow Virtual Camera driver ready", "latency_ms": 0}

    if not key and name != "Custom RTMP":
        return {"name": name, "status": "KEY_MISSING", "reachable": False, "message": "Stream key is empty", "latency_ms": 0}

    from modules.streaming_validator import validate_stream_endpoint, mask_stream_key

    # Validate streaming URL and stream key formatting
    val = validate_stream_endpoint(url, key, name)
    if not val["valid"]:
        return {
            "name": name,
            "status": "VALIDATION_FAILED",
            "reachable": False,
            "host": val.get("host"),
            "port": val.get("port"),
            "latency_ms": 0,
            "masked_key": val.get("masked_key"),
            "provider": val.get("provider"),
            "message": f"Validation failed: {'; '.join(val['errors'])}",
            "validation": val
        }

    host = val.get("host")
    port = val.get("port") or 1935

    t0 = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=2.5)
        sock.close()
        latency = round((time.time() - t0) * 1000, 1)
        return {
            "name": name,
            "status": "ONLINE",
            "reachable": True,
            "host": host,
            "port": port,
            "latency_ms": latency,
            "message": f"Connected ({latency}ms)"
        }
    except socket.gaierror:
        return {"name": name, "status": "DNS_ERROR", "reachable": False, "host": host, "port": port, "latency_ms": 0, "message": "DNS resolution failed"}
    except (socket.timeout, TimeoutError):
        return {"name": name, "status": "TIMEOUT", "reachable": False, "host": host, "port": port, "latency_ms": 0, "message": "Connection timed out"}
    except ConnectionRefusedError:
        return {"name": name, "status": "REFUSED", "reachable": False, "host": host, "port": port, "latency_ms": 0, "message": "Connection refused by host"}
    except Exception as e:
        return {"name": name, "status": "ERROR", "reachable": False, "host": host, "port": port, "latency_ms": 0, "message": str(e)}


def escape_tee_url(url: str) -> str:
    for char in ['\\', ':', '|', '[', ']', '=', ',', '%']:
        url = url.replace(char, '\\' + char)
    return url


def redact_broadcast_log(line: str, secrets=()) -> str:
    """Keep diagnostics while withholding destination URLs and stream credentials."""
    value = str(line)
    for secret in sorted({str(item) for item in secrets if item}, key=len, reverse=True):
        value = value.replace(secret, "[REDACTED]")
        value = value.replace(escape_tee_url(secret), "[REDACTED]")
    return re.sub(r"(?i)(?:rtmps?|https?|srt)(?:\\)?:\/\/[^\s\"'<>]+", "[REDACTED_STREAM_URL]", value)

def resolve_game_window_title(target_name: str = "") -> Optional[str]:
    """Resolve process name (e.g. cod.exe) or game title to exact HWND visible title, handling unicode zero-width characters."""
    try:
        clean_target = re.sub(r'^[🎮🪟🎯\s]+', '', target_name or '').strip()
        exe_matches = re.findall(r'[\w\-\.]+\.exe', clean_target, re.I)
        exe_hint = exe_matches[0].lower() if exe_matches else ""
        title_hint = re.sub(r'\s*\([\w\-\.]+\.exe\)', '', clean_target, flags=re.I).strip().lower()

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = (proc.info['name'] or '').lower()
                is_cod = 'cod.exe' in pname or 'call of duty' in clean_target.lower() or 'cod' in clean_target.lower()
                matches_exe = exe_hint and (exe_hint == pname or exe_hint in pname or pname in exe_hint)
                matches_title = title_hint and (title_hint in pname or pname in title_hint)
                if is_cod or matches_exe or matches_title:
                    pid = proc.info['pid']
                    windows = []
                    def _enum_cb(hwnd, extra):
                        if win32gui.IsWindowVisible(hwnd):
                            _, p = win32process.GetWindowThreadProcessId(hwnd)
                            if p == pid:
                                title = win32gui.GetWindowText(hwnd)
                                rect = win32gui.GetClientRect(hwnd)
                                w = rect[2] - rect[0]
                                h = rect[3] - rect[1]
                                if w > 100 and h > 100 and title:
                                    windows.append(title)
                    win32gui.EnumWindows(_enum_cb, None)
                    if windows:
                        return windows[0]
            except Exception:
                pass
    except Exception:
        pass
    return None

KNOWN_GAME_MAP = {
    "fortniteclient-win64-shipping.exe": "Fortnite",
    "fortnitelauncher.exe": "Fortnite Launcher",
    "fortniteclient-win64-shipping_eac_eos.exe": "Fortnite (EAC)",
    "cod.exe": "Call of Duty",
    "bootcamp.exe": "Call of Duty: Warzone",
    "r5apex.exe": "Apex Legends",
    "valorant-win64-shipping.exe": "Valorant",
    "cs2.exe": "Counter-Strike 2",
    "csgo.exe": "Counter-Strike: Global Offensive",
    "overwatch.exe": "Overwatch 2",
    "robloxplayerbeta.exe": "Roblox",
    "javaw.exe": "Minecraft",
    "minecraft.exe": "Minecraft",
    "gta5.exe": "Grand Theft Auto V",
    "fivem.exe": "FiveM (GTA V)",
    "rocketleague.exe": "Rocket League",
    "leagueclientux.exe": "League of Legends",
    "league of legends.exe": "League of Legends",
    "dota2.exe": "Dota 2",
    "cyberpunk2077.exe": "Cyberpunk 2077",
    "eldenring.exe": "Elden Ring",
    "starfield.exe": "Starfield",
    "genshinimpact.exe": "Genshin Impact",
    "tarkov.exe": "Escape from Tarkov",
    "escapefromtarkov.exe": "Escape from Tarkov",
    "pubg.exe": "PUBG: BATTLEGROUNDS",
    "tslgame.exe": "PUBG: BATTLEGROUNDS",
    "helldivers2.exe": "HELLDIVERS 2",
    "destiny2.exe": "Destiny 2",
    "halo_infinite.exe": "Halo Infinite",
    "haloinfinite.exe": "Halo Infinite"
}

IGNORE_TITLES = {
    "N/A", "OleMainThreadWndName", "Default IME", "MSCTFIME UI",
    "Program Manager", "Settings", "Windows Input Experience",
    "DWM Notification Window", "NvSvc", "UxdService", "BroadcastListenerWindow",
    "Flyout window", "Windows Push Notifications Platform", "Task Host Window",
    "CrossDeviceResumeWindow", "Search", "Start", "Player Location Check",
    "OLEChannelWnd", "GDI+ Window", "Logi Plugin Service", "Logi_Devio_MainWindow",
    "RealtekAudioBackgroundProcessClass", "Temp Window", "WingetMessageOnlyWindow",
    "CRC Message Loop Wnd", "Quick Settings"
}

def scan_system_windows_and_games() -> Dict[str, Any]:
    windows = []
    active_game = None

    try:
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        res = subprocess.run(
            ["tasklist", "/v", "/fo", "csv"],
            capture_output=True,
            text=True,
            errors='ignore',
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        reader = csv.DictReader(io.StringIO(res.stdout))
        for row in reader:
            title = (row.get("Window Title") or "").strip()
            pname = (row.get("Image Name") or "").strip()
            pname_lower = pname.lower()
            pid_str = row.get("PID", "0")
            try:
                pid = int(pid_str)
            except ValueError:
                pid = 0
                
            if not title or title in IGNORE_TITLES or title.startswith("GDI+ Window") or title.startswith(".NET-Broadcast"):
                continue
                
            if any(studio_name in title for studio_name in ["AI-BS Broadcast Studio", "Antigravity IDE", "cmd.exe", "powershell.exe"]):
                continue

            is_game = False
            friendly_game_name = None
            if pname_lower in KNOWN_GAME_MAP:
                is_game = True
                friendly_game_name = KNOWN_GAME_MAP[pname_lower]
            elif any(g in pname_lower or g in title.lower() for g in ["game", "shipping", "unreal", "unity"]):
                if "steam" not in pname_lower and "service" not in pname_lower:
                    is_game = True
                    friendly_game_name = title or pname

            display_name = f"🎮 {friendly_game_name or title} ({pname})" if is_game else f"🪟 {title} ({pname})"
            
            entry = {
                "title": title,
                "process_name": pname,
                "pid": pid,
                "is_game": is_game,
                "game_name": friendly_game_name or title,
                "display_name": display_name
            }
            windows.append(entry)
            
            if is_game and not active_game:
                active_game = entry
    except Exception as e:
        logging.error(f"Window scan error: {e}")

    try:
        fg_hwnd = win32gui.GetForegroundWindow()
        if fg_hwnd:
            fg_title = win32gui.GetWindowText(fg_hwnd).strip()
            _, fg_pid = win32process.GetWindowThreadProcessId(fg_hwnd)
            for w in windows:
                if w["pid"] == fg_pid or w["title"] == fg_title:
                    w["is_foreground"] = True
                    if w["is_game"]:
                        active_game = w
    except Exception:
        pass

    windows.sort(key=lambda x: (not x.get("is_foreground", False), not x["is_game"], x["title"]))
    return {"windows": windows, "open_windows": windows, "active_game": active_game}

def legacy_coordinator_guard():
    """Probe an existing modern lease without touching capture or credentials."""
    try:
        import win32event
        import win32api
    except Exception:
        return "OWNER_UNVERIFIED"
    try:
        handle = win32event.OpenMutex(0x00100001, False, r"Local\AI_BS_Secondary_Broadcast206")
    except Exception as exc:
        return None if getattr(exc, "winerror", None) == 2 else "OWNER_UNVERIFIED"
    acquired = False
    result = "OWNER_UNVERIFIED"
    try:
        status = win32event.WaitForSingleObject(handle, 0)
        acquired = status in (0, 0x80)
        if status == 0:
            result = None
        elif status == 258:
            result = "COORDINATOR_ACTIVE"
    except Exception:
        result = "OWNER_UNVERIFIED"
    finally:
        if acquired:
            try:win32event.ReleaseMutex(handle)
            except Exception:result = "OWNER_UNVERIFIED"
        try:win32api.CloseHandle(handle)
        except Exception:result = "OWNER_UNVERIFIED"
    return result


class BroadcastDaemon:

    def __init__(self, *, secondary_outputs=False):
        if type(secondary_outputs) is not bool:
            raise ValueError("Secondary output mode must be explicit")
        # A separate controller can opt into fixed C-backed outputs. The
        # original service instance keeps its existing configuration and PID.
        self._secondary_outputs = secondary_outputs
        self._archive_root_override = "C:/AI-BS/recordings/secondary" if secondary_outputs else None
        self._telemetry_log_override = "C:/AI-BS/logs/secondary_ffmpeg.log" if secondary_outputs else None
        self._secondary_hls_dir = "C:/AI-BS/saved_data/broadcast_hls/secondary" if secondary_outputs else None
        self.process = None
        if hasattr(self, 'overlay_workers'):
            for w in self.overlay_workers:
                try:
                    w.kill()
                except:
                    pass
            self.overlay_workers = []

        self.is_streaming = False
        self._stream_secrets = ()
        # Control-service availability is not an encoder test. Real capture and
        # encoding start only after an explicit, validated /stream/start request.
        self.encoder_config = None
        self.active_game = "Desktop Screen 1"
        
        # Telemetry State
        self.overlay_worker = None
        self.telemetry = {
            "fps": "0.0",
            "bitrate": "0.0kbits/s",
            "speed": "0.0x",
            "dropped": "0",
            "game_name": "None Detected",
            "endpoints": {}
        }
        self.telemetry_clients: List[WebSocket] = []
        
        # Virtual Camera State
        self.vcam_running = True
        self.vcam_active = False
        self.vcam_thread = None
        
        self._game_detector_thread = None

    def ensure_game_detection(self):
        """A telemetry subscription may request discovery; import/startup do not."""
        if self._game_detector_thread is None or not self._game_detector_thread.is_alive():
            self._game_detector_thread = threading.Thread(target=self._game_detector, daemon=True)
            self._game_detector_thread.start()

    async def run_telemetry_loop_async(self):
        while True:
            try:
                if self.telemetry_clients:
                    dead = []
                    msg = json.dumps(self.telemetry)
                    for client in list(self.telemetry_clients):
                        try:
                            await client.send_text(msg)
                        except Exception:
                            dead.append(client)
                    for d in dead:
                        if d in self.telemetry_clients:
                            self.telemetry_clients.remove(d)
            except Exception:
                pass
            await asyncio.sleep(1.0)

    def _game_detector(self):
        while True:
            try:
                # Only scan processes if actively streaming or clients are connected
                if self.is_streaming or getattr(self, "telemetry_clients", None):
                    res = scan_system_windows_and_games()
                    self.open_windows = res["windows"]
                    self.active_game_info = res["active_game"]
                    if self.active_game_info:
                        self.telemetry["game_name"] = self.active_game_info.get("game_name") or self.active_game_info.get("title")
                        self.active_game = self.telemetry["game_name"]
                    else:
                        self.telemetry["game_name"] = "Desktop"
                        self.active_game = "Desktop"
            except Exception as e:
                logging.debug(f"Game detector error: {e}")
            time.sleep(5.0 if self.is_streaming else 20.0)

    def start_stream(
        self,
        endpoints: List[Dict[str, Any]],
        game_name: str = "General",
        fps: int = 60,
        resolution: str = "1920x1080",
        video_bitrate: str = "6000k",
        audio_bitrate: str = "160k",
        encoder_choice: str = "h264_nvenc",
        encoder_preset: str = "p5",
        keyframe_interval: int = 2,
        format_choice: str = "hybrid_mp4",
        sources: Optional[List[Dict[str, Any]]] = None,
        overlays: Optional[List[Dict[str, Any]]] = None,
        enable_6_track: bool = True
    ):
        if getattr(self, "_secondary_outputs", False) is not True:
            guard_code = legacy_coordinator_guard()
            if guard_code is not None:
                self.telemetry["capture_error_code"] = guard_code
                return False
        if self.is_streaming or (getattr(self, "_owns_process", False) and self.process is not None and self.process.poll() is None):
            logging.warning("Stream is already running.")
            return False
        if getattr(self, "_window_pipe", None) is not None or getattr(self, "_window_capture", None) is not None:
            self.telemetry["capture_error_code"] = "window_capture_stop_unconfirmed"
            return False
        self._window_capture = None
        self._rawvideo_input = False
        self.telemetry.pop("capture_error_code", None)
        self.telemetry.pop("capture_error", None)

        # Older clients omitted their preview selection entirely. This cannot
        # authorize desktop/microphone capture; require an explicit selection.
        if sources is None:
            self.telemetry["capture_error"] = "Explicit capture selection is required; update the client and choose a source."
            self.telemetry["capture_error_code"] = "capture_selection_required"
            return False
        active_sources = [s for s in sources if s.get("enabled", True)]
        game_sources = [s for s in active_sources if s.get("type") in ["game", "window", "screen", "desktop"]]
        cam_sources = [s for s in active_sources if s.get("type") == "cam"]
        audio_sources = [s for s in active_sources if s.get("type") in ["mic", "daw", "guest", "desktop_audio"]]
        if not game_sources and not cam_sources:
            self.telemetry["capture_error"] = "No enabled video input is selected."
            self.telemetry["capture_error_code"] = "capture_selection_required"
            return False

        self._stream_secrets = tuple(
            str(value) for ep in endpoints for value in (ep.get("key"), ep.get("url")) if value
        )

        # Facebook Live Strict Enforcement
        has_facebook = any("facebook.com" in ep.get("url", "").lower() for ep in endpoints)
        if has_facebook:
            if "hevc" in encoder_choice.lower() or "av1" in encoder_choice.lower():
                logging.warning("Facebook Live detected: Forcing fallback to H.264 encoder.")
                encoder_choice = "h264_nvenc" if "nvenc" in encoder_choice.lower() else "libx264"
        
        # Clamp Keyframe Interval (FB requires 2s)
        keyframe_interval = 2
        
        # Clamp Audio Bitrate (FB requires max 256k)
        try:
            a_b_val = int(''.join(filter(str.isdigit, str(audio_bitrate))))
            if a_b_val > 256:
                audio_bitrate = "256k"
        except Exception:
            pass

        self.configured_bitrate = video_bitrate

        clean_game_name = "".join(x for x in game_name if x.isalnum() or x in " _-").strip(" .") or "General"
        base_record_dir = getattr(self, "_archive_root_override", None) or ("E:/Recordings" if os.path.exists("E:/") else "C:/AI-BS/recordings")
        archive_dir = f"{base_record_dir}/{clean_game_name}"
        os.makedirs(archive_dir, exist_ok=True)
        
        timestamp = int(time.time())
        archive_file = f"{archive_dir}/stream_{timestamp}.mp4"
        rec_mux_flags = "f=mp4:onfail=ignore:movflags=+faststart+frag_keyframe+empty_moov+default_base_moof"

        # Parse target resolution
        try:
            target_w, target_h = map(int, resolution.split("x"))
        except Exception:
            target_w, target_h = 1920, 1080
            resolution = "1920x1080"
            
        is_vertical = (target_w == 1080 and target_h == 1920)

        # Build FFmpeg Command (We need inputs before building tee outputs)
        ffmpeg_executable = "C:/Users/footb/AppData/Local/Microsoft/WinGet/Links/ffmpeg.EXE" if getattr(self, "_secondary_outputs", False) else "ffmpeg"
        ffmpeg_cmd = [ffmpeg_executable, "-y", "-nostats", "-stats_period", "1", "-progress", "pipe:2"]
        video_inputs = []
        audio_inputs = []
        input_idx = 0

        # 1. Ingest Primary Game / Desktop Source (Always video_inputs[0])
        target_prog = game_name if game_name not in ["General", "AI-BS Broadcast", ""] else self.active_game
        if game_sources:
            src_prog = game_sources[0].get("deviceId") or game_sources[0].get("name")
            if src_prog and src_prog not in ["🎮 Game Capture (DirectX/DXGI)", "Desktop Screen 1", "default", ""]:
                target_prog = src_prog
            if game_sources[0].get("type") in {"screen", "desktop"} and not game_sources[0].get("hwnd"):
                target_prog = "Desktop Screen 1"

        # Check if user requested locking to a specific window / game program
        is_true_game_capture = False
        primary_input_configured = False

        # The preview's selected HWND is authoritative. A vanished/minimized
        # window is a held start, not permission to broadcast the whole desktop.
        selected_source = game_sources[0] if game_sources else {}
        selected_hwnd = selected_source.get("hwnd")
        # Native clients historically send the exact title as "name". An
        # explicitly supplied "title" stays authoritative, including invalid
        # empty values, and still must match the selected HWND's current title.
        expected_title = selected_source.get("title", selected_source.get("name"))
        expected_pid = selected_source.get("pid")

        internal_follow = selected_source.get("capture_policy") == "verified_game_follow"
        if internal_follow:
            # This object exists only inside the isolated coordinator. HTTP
            # payloads cannot supply providers or authorize a desktop fallback.
            capture = getattr(self, "_capture_provider_override", None)
            if (getattr(self, "_secondary_outputs", False) is not True or capture is None
                    or len(game_sources) != 1 or len(active_sources) != 1 + len(audio_sources) or selected_source.get("type") != "game"
                    or selected_hwnd is not None):
                self.telemetry["capture_error_code"] = "internal_follow_provider_unavailable"
                return False
            try:
                if (capture.width != target_w or capture.height != target_h or capture.fps != fps):
                    raise ValueError("Follow provider format differs from encoder input")
                self._window_capture = capture
                capture.start(timeout=3)
                frame = capture.read_frame(timeout=0.5)
                if type(frame) is not bytes or len(frame) != target_w * target_h * 4:
                    raise ValueError("Invalid follow provider frame")
                ffmpeg_cmd.extend(["-thread_queue_size", "2", "-f", "rawvideo", "-pixel_format", "bgra",
                                   "-video_size", f"{target_w}x{target_h}", "-framerate", str(fps), "-i", "pipe:0"])
                primary_input_configured = True
                self._rawvideo_input = True
                self.telemetry["capture_mode"] = "verified_game_follow_or_explicit_holding"
            except Exception:
                self.telemetry["capture_error_code"] = "internal_follow_provider_unavailable"
                try:
                    if capture.stop(timeout=1) is True:self._window_capture = None
                except Exception:pass
                return False

        def require_selected_window():
            if type(selected_hwnd) is not int or not 0 < selected_hwnd < 2**64:
                raise ValueError("Invalid capture window handle")
            if not win32gui.IsWindow(selected_hwnd) or not win32gui.IsWindowVisible(selected_hwnd) or win32gui.IsIconic(selected_hwnd):
                raise ValueError("Selected capture window is unavailable")
            if not isinstance(expected_title, str) or not expected_title or win32gui.GetWindowText(selected_hwnd) != expected_title:
                raise ValueError("Selected capture window identity changed")
            if expected_pid is not None:
                if type(expected_pid) is not int or expected_pid <= 0 or win32process.GetWindowThreadProcessId(selected_hwnd)[1] != expected_pid:
                    raise ValueError("Selected capture process identity changed")

        if selected_source.get("type") == "window" and selected_hwnd in (None, 0):
            self.telemetry["capture_error"] = "Choose a valid window handle before starting."
            return False
        if not internal_follow and selected_hwnd not in (None, 0):
            try:
                require_selected_window()
                if NativeWindowCapture is None or WindowCapturePipe is None:
                    raise RuntimeError("Verified window capture provider unavailable")
                capture = NativeWindowCapture(selected_hwnd, expected_pid, expected_title,
                                              fps=fps, width=target_w, height=target_h)
                self._window_capture = capture
                capture.start(timeout=3)
                frame = capture.read_frame(timeout=0.5)
                if type(capture.width) is not int or type(capture.height) is not int or len(frame) != capture.width*capture.height*4:
                    raise ValueError("Invalid window capture frame")
                ffmpeg_cmd.extend(["-thread_queue_size", "2", "-f", "rawvideo", "-pixel_format", "bgra",
                                   "-video_size", f"{capture.width}x{capture.height}", "-framerate", str(fps), "-i", "pipe:0"])
                primary_input_configured = True
                self._rawvideo_input = True
                self.telemetry["capture_mode"] = "windows_graphics_capture_hwnd"
            except Exception:
                if self._window_capture is not None:
                    try:
                        if self._window_capture.stop(timeout=1) is True:self._window_capture = None
                    except Exception:pass
                self.telemetry["capture_error"] = "Verified window capture is unavailable; choose the window again."
                self.telemetry["capture_error_code"] = "window_capture_unavailable"
                return False

        if not game_sources:
            primary_camera = cam_sources[0].get("deviceId")
            if not isinstance(primary_camera, str) or primary_camera in {"", "default", "none"}:
                self.telemetry["capture_error"] = "Select a camera device before starting."
                return False
            ffmpeg_cmd.extend(["-thread_queue_size", "2048", "-f", "dshow", "-framerate", str(fps), "-i", f"video={primary_camera}"])
            cam_sources = cam_sources[1:]
            primary_input_configured = True
            self.telemetry["capture_mode"] = "camera"

        if not primary_input_configured and target_prog and target_prog not in ["Desktop Screen 1", "Entire Screen", "Auto-Detect Foreground Window", "None Detected"]:
            clean_target = re.sub(r'^[🎮🪟🎯\s]+', '', target_prog or '').strip()
            exe_matches = re.findall(r'[\w\-\.]+\.exe', clean_target, re.I)
            exe_hint = exe_matches[0].lower() if exe_matches else ""
            
            # TRUE GAME CAPTURE (OBS DXGI INJECTION)
            if OBSOrchestrator:
                obs_orch = OBSOrchestrator()
                if obs_orch.connect():
                    obs_orch.start_virtual_camera()
                    if "🎮 Game Capture" in target_prog:
                        obs_orch.set_game_capture_target("Game Capture", "", any_fullscreen=True)
                    else:
                        match_str = f"{exe_hint}:" if exe_hint else f":{clean_target}:"
                        obs_orch.set_game_capture_target("Game Capture", match_str, any_fullscreen=False)
                    is_true_game_capture = True
                    logging.info(f"BroadcastDaemon: True Game Capture (OBS DXGI Hook) activated for {target_prog}")
                    ffmpeg_cmd.extend(["-thread_queue_size", "1024", "-probesize", "32M", "-f", "dshow", "-framerate", str(fps), "-i", "video=OBS Virtual Camera"])

        if not is_true_game_capture and not primary_input_configured:
            if selected_source.get("type") not in {"screen", "desktop"}:
                self.telemetry["capture_error"] = "Window/game capture needs a valid window handle or available OBS capture."
                return False
            self.telemetry["capture_mode"] = "explicit_desktop"
            logging.info("BroadcastDaemon: Explicit desktop capture selected.")
            ffmpeg_cmd.extend(["-thread_queue_size", "2048", "-rtbufsize", "512M", "-probesize", "32M", "-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "1", "-i", "desktop"])

        video_inputs.append(input_idx)
        input_idx += 1

        # 2. Ingest Hardware Webcam / Capture Card (Secondary video_inputs[1])
        for src in cam_sources:
            cam_name = src.get("deviceId", "")
            if cam_name and cam_name not in ["default", "none", ""]:
                ffmpeg_cmd.extend(["-thread_queue_size", "2048", "-f", "dshow", "-framerate", str(fps), "-i", f"video={cam_name}"])
                video_inputs.append(input_idx)
                input_idx += 1

        # 3. Ingest Audio Sources (Microphone, DAW, WASAPI) - Deduplicated
        ingested_audio_devs = set()
        audio_gains = {}
        default_mic_resolved = False
        default_mic = None
        if audio_sources:
            for src in audio_sources:
                if not src.get("enabled", True):
                    continue
                audio_dev = src.get("deviceId", "")
                gain = src.get('gain', 1.0)
                if type(gain) not in (int, float) or not 0 <= gain <= 2:
                    self.telemetry['capture_error_code'] = 'invalid_audio_gain'
                    return False
                if audio_dev == '__wasapi_pcm__' and getattr(self, '_secondary_outputs', False):
                    provider = getattr(self, '_audio_provider_overrides', {}).get(src.get('type'))
                    if provider is None:
                        self.telemetry['capture_error_code'] = 'audio_capture_unavailable'
                        return False
                    ffmpeg_cmd.extend(['-thread_queue_size', '8', '-f', 'f32le', '-ar', str(provider.rate),
                                       '-ac', str(provider.channels), '-i', provider.path])
                    audio_gains[input_idx] = float(gain)
                    audio_inputs.append(input_idx)
                    input_idx += 1
                    continue
                if audio_dev == "anullsrc":
                    continue
                if not audio_dev or audio_dev == "default":
                    if src.get("type") != "mic":
                        continue  # A DAW/guest route is not permission to open a microphone.
                    if not default_mic_resolved:
                        default_mic = detect_microphone()
                        default_mic_resolved = True
                    audio_dev = default_mic
                if not isinstance(audio_dev, str) or not audio_dev.strip():
                    continue
                if audio_dev in ingested_audio_devs:
                    continue
                ingested_audio_devs.add(audio_dev)
                audio_gains[input_idx] = float(gain)
                ffmpeg_cmd.extend(["-thread_queue_size", "2048", "-f", "dshow", "-i", f"audio={audio_dev}"])
                audio_inputs.append(input_idx)
                input_idx += 1

        if not audio_inputs:
            # RTMP/FLV still gets a valid AAC track when no audio is requested or
            # available. This is explicit silence, never invented hardware.
            ffmpeg_cmd.extend(["-thread_queue_size", "2", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"])
            audio_inputs.append(input_idx)
            input_idx += 1
            self.telemetry["audio_input_status"] = "silent_no_requested_or_available_audio"
        else:
            self.telemetry["audio_input_status"] = "device_input_requested_unverified"

        # Ingest Browser Overlays
        overlay_inputs = []
        if overlays:
            for i, ov in enumerate(overlays):
                if not ov.get("enabled", True):
                    continue
                mode = ov.get("mode", "")
                if mode == "obs_passthrough":
                    continue  # handled in OBS
                elif mode == "window_capture":
                    title = ov.get("title", "")
                    if title:
                        ffmpeg_cmd.extend(["-thread_queue_size", "1024", "-f", "gdigrab", "-framerate", str(fps), "-i", f"title={title}"])
                        overlay_inputs.append(input_idx)
                        input_idx += 1
                elif mode == "headless_engine":
                    url = ov.get("url", "")
                    if url:
                        title = f"AI-BS-Overlay-{i}"
                        # Spawn worker process
                        worker = subprocess.Popen(["python", "C:/AI-BS/backend/aibs_browser_overlay_worker.py", "--url", url, "--title", title])
                        if not hasattr(self, 'overlay_workers'):
                            self.overlay_workers = []
                        self.overlay_workers.append(worker)
                        # Wait a bit for the window to appear
                        time.sleep(3)
                        ffmpeg_cmd.extend(["-thread_queue_size", "1024", "-f", "gdigrab", "-framerate", str(fps), "-i", f"title={title}"])
                        overlay_inputs.append(input_idx)
                        input_idx += 1


        # Build Tee Muxer Destinations
        outputs = []
        self.telemetry["endpoints"] = {}
        for ep in endpoints:
            ep_name = ep.get("name", "Unknown")
            if ep.get("enabled", True):
                base_url = ep.get('url', '').rstrip('/')
                key = ep.get('key', '').lstrip('/')
                url = f"{base_url}/{key}" if key else base_url
                
                if ep.get("name") == "Virtual Camera":
                    vcam_url = escape_tee_url('video=OBS Virtual Camera')
                    outputs.append(f"[f=dshow:select=\'v:0\']{vcam_url}")
                    self.telemetry["endpoints"]["Virtual Camera"] = "PENDING_UNVERIFIED"
                    continue
                    
                if url:
                    escaped_url = escape_tee_url(url)
                    if url.startswith("https://"):
                        outputs.append(f"[f=hls:hls_time=2:hls_list_size=5:method=POST:select=\\'v:0,a:0\\']{escaped_url}")
                    else:
                        transport = ":rw_timeout=8000000:tls_verify=1" if getattr(self, "_secondary_outputs", False) else ""
                        outputs.append(f"[f=flv:onfail=ignore{transport}:select=\\'v:0,a:0\\']{escaped_url}")
                    self.telemetry["endpoints"][ep_name] = "PENDING_UNVERIFIED"
            else:
                self.telemetry["endpoints"][ep_name] = "DISABLED"

        # Add recording output with multi-track mapping
        archive_escaped = escape_tee_url(archive_file)
        num_audio_streams = len(audio_inputs) + 1 if len(audio_inputs) > 1 else 1
        select_streams = "\\'v:0," + ",".join([f"a:{i}" for i in range(num_audio_streams)]) + "\\'"
        outputs.append(f"[{rec_mux_flags}:select={select_streams}]{archive_escaped}")
        self.telemetry["endpoints"]["Local Recording"] = "PENDING_UNVERIFIED"
        hls_dir = getattr(self, "_secondary_hls_dir", None)
        if hls_dir:
            os.makedirs(hls_dir, exist_ok=True)
            # The drive colon is nested in tee options and needs two parsing
            # layers of escaping. No credential or destination URL enters HLS.
            segment_path = f"{hls_dir}/segment_%09d.ts".replace(":", "\\\\\\:")
            playlist = escape_tee_url(f"{hls_dir}/index.m3u8")
            outputs.append("[f=hls:onfail=ignore:hls_time=2:hls_list_size=6:"
                           "hls_flags=delete_segments+independent_segments+temp_file:"
                           f"hls_segment_filename={segment_path}:select=\\'v:0,a:0\\']{playlist}")
            self.telemetry["endpoints"]["Local HLS"] = "PENDING_UNVERIFIED"
        self.telemetry["ingest_verified"] = False
        self.telemetry["archive_verified"] = False
        tee_outputs = "|".join(outputs)

        # Build Filter Complex (Video Scaling & Audio Mixing)
        if is_vertical:
            v_filters = [f"[{video_inputs[0]}:v]scale=-1:1920:flags=bicubic,crop=1080:1920:(in_w-1080)/2:0[bg]"]
        else:
            v_filters = [f"[{video_inputs[0]}:v]scale={resolution}:flags=bicubic[bg]"]
            
        last_v_out = "bg"
        
        # Apply Browser Overlays
        for i, ov_idx in enumerate(overlay_inputs):
            # Chrome uses #0000FF for pure blue, chromakey out blue with 0.1 similarity and 0.1 blend
            v_filters.append(f"[{ov_idx}:v]colorkey=0x0000FF:0.1:0.1[ov{i}]")
            v_filters.append(f"[{last_v_out}][ov{i}]overlay=0:0[bg_ov{i}]")
            last_v_out = f"bg_ov{i}"

        
        # Picture in picture for secondary video inputs (Cam/Window)
        pip_w, pip_h = target_w // 4, target_h // 4
        pip_x, pip_y = target_w - pip_w - 20, target_h - pip_h - 20
        for i, v_idx in enumerate(video_inputs[1:]):
            v_filters.append(f"[{v_idx}:v]scale={pip_w}:{pip_h}:flags=bicubic[pip{i}]")
            v_filters.append(f"[{last_v_out}][pip{i}]overlay={pip_x}:{pip_y}[bg{i+1}]")
            last_v_out = f"bg{i+1}"
        v_filters.append(f"[{last_v_out}]copy[vout_main]")

        # Multi-Track Audio Stem Filters
        a_filters = []
        a_outs_mix = []
        a_outs_iso = []
        for i, a_idx in enumerate(audio_inputs):
            audio_filter = f'aresample=async=1:first_pts=0,aformat=sample_rates=48000:channel_layouts=stereo,volume={audio_gains.get(a_idx, 1.0)}'
            if len(audio_inputs) > 1:
                a_filters.append(f"[{a_idx}:a]{audio_filter},asplit=2[a_stem_mix{i}][a_stem_iso{i}]")
                a_outs_mix.append(f"[a_stem_mix{i}]")
                a_outs_iso.append(f"[a_stem_iso{i}]")
            else:
                a_filters.append(f"[{a_idx}:a]{audio_filter},alimiter=limit=0.95[a_master]")

        # Mix all audio stems for Track 1 (Master Output)
        if len(audio_inputs) > 1:
            a_mix_in = "".join(a_outs_mix)
            a_filters.append(f"{a_mix_in}amix=inputs={len(audio_inputs)}:duration=longest:normalize=0,alimiter=limit=0.95[a_master]")

        filter_complex = ";".join(v_filters + a_filters)

        # Build Hardware Encoder Arguments (NVENC AV1/H.264/HEVC)
        enc_args = build_encoder_flags(encoder_choice, preset=encoder_preset)

        ffmpeg_cmd.extend([
            "-filter_complex", filter_complex,
            "-fps_mode", "cfr",
            "-map", "[vout_main]",
            "-map", "[a_master]"
        ])
        
        if len(audio_inputs) > 1:
            for out in a_outs_iso:
                ffmpeg_cmd.extend(["-map", out])

        ffmpeg_cmd.extend([
            *enc_args,
            "-flags", "+global_header",
            "-pix_fmt", "yuv420p",
            "-g", str(fps * keyframe_interval),
            "-b:v", video_bitrate,
            "-maxrate", video_bitrate,
            "-bufsize", str(int(video_bitrate.replace("k", "").replace("M", "000")) * 2) + "k",
            "-c:a", "aac",
            "-profile:a", "aac_low",
            "-ac", "2",
            "-b:a", audio_bitrate,
            "-ar", "48000",
            "-f", "tee",
            tee_outputs
        ])

        try:
            if selected_hwnd not in (None, 0):
                require_selected_window()
            logging.info(f"Spawning Hardware FFmpeg Broadcast Pipeline ({encoder_choice.upper()} @ {resolution} {fps}FPS)...")
            process_options = {}
            if getattr(self, "_secondary_outputs", False):
                permitted_env = {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA"}
                child_env = {name: value for name, value in os.environ.items() if name.upper() in permitted_env}
                child_env.update(DRY_RUN="true", HOLD_DISPATCH="true", LIVE_TRADING_ENABLED="false",
                                 RECDEBUT_SENDING_ENABLED="false", AI_BS_BACKEND_MANAGE_DAEMONS="false",
                                 AI_BS_BACKEND_BACKGROUND_ENABLED="false", AIBS_PAYMENT_MODE="disabled")
                process_options["env"] = child_env
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=not self._rawvideo_input,
                bufsize=0 if self._rawvideo_input else 1,
                universal_newlines=not self._rawvideo_input,
                **process_options
            )
            self._owns_process = True
            process = self.process
            process_pid = getattr(process, "pid", None)
            if type(process_pid) is not int:process_pid = None
            session = (process_pid, float(time.time()))
            self._stream_session = session
            self.telemetry.update(session_pid=process_pid, session_epoch=session[1],
                                  frames_encoded=None, out_time_us=None, last_progress_epoch=None,
                                  fps=None, bitrate=None, speed=None, dropped=None)
            # Popen success proves creation only. Catch an immediate encoder exit;
            # a running process still does not prove remote ingest or archive validity.
            time.sleep(0.1)
            if self.process.poll() is not None:
                self.is_streaming = False
                self.telemetry["process_running"] = False
                self.telemetry["endpoints"] = {name: "START_FAILED" if state != "DISABLED" else state
                                                for name, state in self.telemetry["endpoints"].items()}
                if self._window_capture is not None:
                    try:
                        if self._window_capture.stop(timeout=1) is True:self._window_capture = None
                    except Exception:pass
                return False
            self.is_streaming = True
            self.telemetry["process_running"] = True
            if self._rawvideo_input:
                process = self.process
                def capture_failed(code):
                    if self.process is process:
                        self.telemetry["capture_error_code"] = code
                        self.telemetry["process_running"] = process.poll() is None
                        self.is_streaming = False
                self._window_pipe = WindowCapturePipe(self._window_capture, process, on_failure=capture_failed)
                self._window_pipe.start()
            threading.Thread(target=self._telemetry_reader,
                             args=(process, session, tuple(self._stream_secrets)), daemon=True).start()
            return self.is_streaming and self.process.poll() is None
        except Exception as e:
            logging.error("Failed to start FFmpeg process (%s)", type(e).__name__)
            self.is_streaming = False
            pipe = getattr(self, "_window_pipe", None)
            if pipe is not None:
                if pipe.stop(timeout=2) is True:self._window_pipe = None;self._window_capture = None
            elif self._window_capture is not None:
                if getattr(self, "_owns_process", False) and self.process is not None and self.process.poll() is None:
                    try:
                        self.process.terminate();self.process.wait(timeout=1)
                    except Exception:
                        try:self.process.kill();self.process.wait(timeout=1)
                        except Exception:pass
                try:
                    if self._window_capture.stop(timeout=1) is True:self._window_capture = None
                except Exception:pass
            return False

    def _telemetry_reader(self, process=None, session=None, secrets=None):
        fps_pattern = re.compile(r"fps=\s*([\d\.]+)")
        bitrate_pattern = re.compile(r"bitrate=\s*([\d\.]+kbits/s)")
        speed_pattern = re.compile(r"speed=\s*([\d\.]+x)")
        drop_pattern = re.compile(r"drop=\s*(\d+)")
        
        process = self.process if process is None else process
        session = getattr(self, "_stream_session", None) if session is None else session
        secrets = tuple(getattr(self, "_stream_secrets", ())) if secrets is None else secrets
        def current():
            return self.process is process and getattr(self, "_stream_session", None) == session
        if not process or not current():return
        pending = {}
        log_path = getattr(self, "_telemetry_log_override", None) or "C:/AI-BS/backend/ffmpeg.log"
        with open(log_path, "a", encoding="utf-8") as log_f:
            if session is not None:
                log_f.write(f"[SESSION pid={session[0]} epoch={session[1]}]\n")
                log_f.flush()
            while self.is_streaming and current():
                line = process.stdout.readline()
                if not line or not current():
                    break
                if isinstance(line, bytes):
                    line = line.decode('utf-8', errors='replace')
                log_f.write(redact_broadcast_log(line, secrets))
                log_f.flush()
                key, separator, value = line.strip().partition('=')
                if separator and key in {'frame', 'out_time_us', 'drop_frames'} and value.isdigit():
                    pending[{'frame':'frames_encoded','out_time_us':'out_time_us','drop_frames':'dropped'}[key]] = str(int(value)) if key == 'drop_frames' else int(value)
                elif separator and key in {'fps', 'bitrate', 'speed'}:
                    pattern = {'fps':r'\d+(?:\.\d+)?','bitrate':r'\d+(?:\.\d+)?kbits/s','speed':r'\d+(?:\.\d+)?x'}[key]
                    if re.fullmatch(pattern,value):pending[key] = value
                elif key == 'progress' and value in {'continue','end'} and current():
                    self.telemetry.update(pending)
                    self.telemetry['last_progress_epoch'] = float(time.time())
                    pending = {}
                # Compatibility for earlier daemon/tests emitting one human
                # stats line; production uses newline-delimited -progress.
                if "frame=" in line and "fps=" in line and current():
                    fps_match = fps_pattern.search(line)
                    bitrate_match = bitrate_pattern.search(line)
                    speed_match = speed_pattern.search(line)
                    drop_match = drop_pattern.search(line)
                    if fps_match: self.telemetry["fps"] = fps_match.group(1)
                    if bitrate_match: 
                        self.telemetry["bitrate"] = bitrate_match.group(1)
                    if speed_match: self.telemetry["speed"] = speed_match.group(1)
                    if drop_match: self.telemetry["dropped"] = drop_match.group(1)
        if current():
            self.is_streaming = False
            self.telemetry["process_running"] = process.poll() is None if process else False

    def stop_stream(self):
        pipe = getattr(self, "_window_pipe", None)
        if pipe is not None:
            self.is_streaming = False
            if pipe.stop(timeout=3) is not True:
                return {"status": "error", "message": "Window capture/encoder stop could not be confirmed.",
                        "process_running": self.process is not None and self.process.poll() is None,
                        "archive_verified": False}
            self._window_pipe = None
            self._window_capture = None
            self._owns_process = False
            self.process = None
            self.telemetry["process_running"] = False
            return {"status": "stopped", "message": "Window capture and owned encoder stopped; archive validity unverified.",
                    "process_running": False, "archive_verified": False}
        if getattr(self, "_rawvideo_input", False) and self.process is not None:
            process = self.process
            if process.poll() is None:
                try:process.terminate();process.wait(timeout=2)
                except Exception:
                    try:process.kill();process.wait(timeout=1)
                    except Exception:pass
            if process.poll() is None:
                return {"status":"error","message":"Raw-video encoder termination is unconfirmed.",
                        "process_running":True,"archive_verified":False}
            try:process.stdin.close()
            except Exception:pass
            self.process = None
            self._owns_process = False
            self.is_streaming = False
        capture = getattr(self, "_window_capture", None)
        if capture is not None:
            try:
                if capture.stop(timeout=1) is not True:
                    return {"status":"error","message":"Window capture shutdown is unconfirmed.","archive_verified":False}
                self._window_capture = None
            except Exception:
                return {"status":"error","message":"Window capture shutdown is unconfirmed.","archive_verified":False}
        if not self.process:
            return {"status": "stopped", "message": "No encoder process is owned.", "archive_verified": False}
        process = self.process
        logging.info("Stopping stream gracefully...")
        try:
            if process.poll() is None:
                process.stdin.write("q\n")
                process.stdin.flush()
                process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
                process.wait(timeout=2)
            except Exception:
                if process.poll() is None:
                    return {"status": "error", "message": "Encoder termination could not be confirmed.",
                            "process_running": True, "archive_verified": False}
        if process.poll() is None:
            return {"status": "error", "message": "Encoder process is still running.",
                    "process_running": True, "archive_verified": False}
        self.process = None
        if hasattr(self, 'overlay_workers'):
            for w in self.overlay_workers:
                try:
                    w.kill()
                except:
                    pass
            self.overlay_workers = []

        self.is_streaming = False
        self.overlay_worker = None
        self.telemetry = {
            "fps": "0.0",
            "bitrate": "0.0kbits/s",
            "speed": "0.0x",
            "dropped": "0",
            "game_name": self.active_game,
            "endpoints": {}
        }
        return {"status": "stopped", "message": "Encoder stopped; archive validity has not been verified.",
                "process_running": False, "archive_verified": False}

daemon = BroadcastDaemon()

@app.on_event("startup")
async def on_broadcast_daemon_startup():
    asyncio.create_task(daemon.run_telemetry_loop_async())


@app.get("/health")
def broadcast_service_health():
    """Read-only control identity; never probes hardware or starts a workload."""
    process = daemon.process
    running = process is not None and process.poll() is None
    return {"service_id": "ai-bs.broadcast-daemon", "protocol_version": 1,
            "pid": os.getpid(), "port": 8005, "status": "ok",
            "process_running": running, "is_streaming": bool(daemon.is_streaming and running),
            "ingest_verified": False, "archive_verified": False}

class ProbeRequest(BaseModel):
    endpoints: Optional[List[Dict[str, Any]]] = []

@app.post("/stream/probe")
async def probe_endpoints_endpoint(req: ProbeRequest):
    results = []
    for ep in (req.endpoints or []):
        res = probe_single_endpoint(ep)
        results.append(res)
    return {"status": "ok", "results": results}

class StreamStartRequest(BaseModel):
    game_name: Optional[str] = "General"
    fps: Optional[int] = 60
    resolution: Optional[str] = "1920x1080"
    video_bitrate: Optional[str] = "6000k"
    audio_bitrate: Optional[str] = "160k"
    encoder: Optional[str] = "h264_nvenc"
    preset: Optional[str] = "p5"
    format: Optional[str] = "hybrid_mp4"
    endpoints: Optional[List[Dict[str, Any]]] = []
    sources: Optional[List[Dict[str, Any]]] = None

@app.post("/stream/start")
async def start_stream_endpoint(req: StreamStartRequest):
    success = daemon.start_stream(
        endpoints=req.endpoints or [],
        game_name=req.game_name or "General",
        fps=req.fps or 60,
        resolution=req.resolution or "1920x1080",
        video_bitrate=req.video_bitrate or "6000k",
        audio_bitrate=req.audio_bitrate or "160k",
        encoder_choice=req.encoder or "h264_nvenc",
        encoder_preset=req.preset or "p5",
        format_choice=req.format or "hybrid_mp4",
        sources=req.sources
    )
    error_code = None if success else getattr(daemon, "telemetry", {}).get("capture_error_code")
    status = "streaming" if success else "held" if error_code in {"COORDINATOR_ACTIVE", "OWNER_UNVERIFIED"} else "error"
    return {"status": status, "process_running": bool(success),
            "error_code": error_code,
            "ingest_verified": False, "archive_verified": False,
            "verification_scope": "ffmpeg_process_running_only"}

@app.post("/stream/stop")
async def stop_stream_endpoint():
    return daemon.stop_stream()

@app.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket):
    await websocket.accept()
    daemon.ensure_game_detection()
    daemon.telemetry_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in daemon.telemetry_clients:
            daemon.telemetry_clients.remove(websocket)

@app.get("/api/windows")
def list_windows():
    res = scan_system_windows_and_games()
    # Support both list of strings and rich objects
    return {
        "windows": res["windows"],
        "open_windows": res["windows"],
        "active_game": res["active_game"]
    }

@app.get("/api/active_game")
@app.get("/api/game/active")
def get_active_game_daemon():
    res = scan_system_windows_and_games()
    return {
        "status": "OK",
        "is_game_running": bool(res["active_game"]),
        "active_game": res["active_game"]
    }

class StreamShoutoutRequest(BaseModel):
    stream_url: str
    message: str
    author: Optional[str] = "Brett Stehouwer / AI-BS"
    overlay_duration_sec: Optional[int] = 10

@app.post("/api/broadcast/stream/shoutout")
async def broadcast_stream_shoutout(req: StreamShoutoutRequest):
    logging.info(f"[STREAM SHOUTOUT] Dispatching lower-third: '{req.message}' for stream {req.stream_url}")
    # Forward telemetry to active websocket clients
    payload = {
        "type": "STREAM_SHOUTOUT",
        "stream_url": req.stream_url,
        "message": req.message,
        "author": req.author,
        "duration": req.overlay_duration_sec,
        "timestamp": time.time()
    }
    for client in list(daemon.telemetry_clients):
        try:
            asyncio.create_task(client.send_text(json.dumps(payload)))
        except Exception:
            pass

    # If OBS orchestrator is connected, trigger lower third overlay asynchronously in background
    if OBSOrchestrator:
        def async_obs_trigger():
            try:
                orch = OBSOrchestrator()
                if orch.connect(retry_launch=False):
                    orch.trigger_lexicon_theme("neon_cyber")
            except Exception:
                pass
        threading.Thread(target=async_obs_trigger, daemon=True).start()

    return {
        "status": "success",
        "broadcast_event": payload
    }

class ThemeTriggerRequest(BaseModel):
    theme: str

@app.post("/obs/trigger-theme")
async def trigger_obs_theme(req: ThemeTriggerRequest):
    if OBSOrchestrator:
        orch = OBSOrchestrator()
        if orch.connect(retry_launch=False):
            orch.trigger_lexicon_theme(req.theme)
            return {"status": "triggered", "theme": req.theme}
        return {"status": "error", "message": "OBS not connected"}
    return {"status": "error", "message": "OBSOrchestrator not available"}

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    def _serve_obs_ws_bridge_4455():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex(("127.0.0.1", 4455)) == 0:
                    return
            logging.info("Starting Native Broadcast WebSocket Bridge on port 4455...")
            uvicorn.run(app, host="127.0.0.1", port=4455, log_level="warning")
        except Exception as e:
            logging.warning(f"Port 4455 bridge notice: {e}")

    threading.Thread(target=_serve_obs_ws_bridge_4455, daemon=True).start()
    logging.info("Starting Resilient AI-BS Broadcast Daemon on port 8005...")
    uvicorn.run(app, host="127.0.0.1", port=8005)

