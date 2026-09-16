import subprocess
import time
import asyncio
import sys
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
import logging
import json
import os
import threading
import re
import socket
import csv
import io
import numpy as np
import pyvirtualcam
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
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] BroadcastDaemon: %(message)s")

app = FastAPI(title="AI-BS Resilient Broadcast & NVENC Daemon")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def detect_microphone() -> str:
    cmd = ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
    for line in res.stderr.split('\n'):
        if '"' in line and "(audio)" in line and "Alternative name" not in line:
            match = re.search(r'"([^"]+)"', line)
            if match:
                dev_name = match.group(1)
                if any(k in dev_name.lower() for k in ["mic", "focusrite", "realtek", "usb", "audio", "headset"]):
                    logging.info(f"Dynamically detected Audio Input: {dev_name}")
                    return dev_name
    return "Microphone (Realtek(R) Audio)"


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
        res = subprocess.run(["tasklist", "/v", "/fo", "csv"], capture_output=True, text=True, errors='ignore')
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

class BroadcastDaemon:

    def __init__(self):
        self.process = None
        if hasattr(self, 'overlay_workers'):
            for w in self.overlay_workers:
                try:
                    w.kill()
                except:
                    pass
            self.overlay_workers = []

        self.is_streaming = False
        self.encoder_config = detect_optimal_encoder()
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
        
        # Start game detection loop
        threading.Thread(target=self._game_detector, daemon=True).start()

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
            time.sleep(2.0)

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
        if self.is_streaming:
            logging.warning("Stream is already running.")
            return False

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

        clean_game_name = "".join(x for x in game_name if x.isalnum() or x in " _-") or "General"
        base_record_dir = "E:/Recordings" if os.path.exists("E:/") else "C:/AI-BS/recordings"
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
        ffmpeg_cmd = ["ffmpeg", "-y"]
        video_inputs = []
        audio_inputs = []
        input_idx = 0

        if not sources:
            sources = [
                {"type": "screen", "enabled": True},
                {"type": "mic", "deviceId": "default", "enabled": True}
            ]

        # Separate and prioritize sources: Primary Game/Desktop first, Cam second, Audio third
        active_sources = [s for s in sources if s.get("enabled", True)]
        game_sources = [s for s in active_sources if s.get("type") in ["game", "window", "screen", "desktop"]]
        cam_sources = [s for s in active_sources if s.get("type") == "cam"]
        audio_sources = [s for s in active_sources if s.get("type") in ["mic", "daw", "guest", "desktop_audio"]]

        # 1. Ingest Primary Game / Desktop Source (Always video_inputs[0])
        target_prog = game_name if game_name not in ["General", "AI-BS Broadcast", ""] else self.active_game
        if game_sources:
            src_prog = game_sources[0].get("deviceId") or game_sources[0].get("name")
            if src_prog and src_prog not in ["🎮 Game Capture (DirectX/DXGI)", "Desktop Screen 1", "default", ""]:
                target_prog = src_prog

        # Check if user requested locking to a specific window / game program
        locked_rect = None
        is_true_game_capture = False

        if target_prog and target_prog not in ["Desktop Screen 1", "Entire Screen", "Auto-Detect Foreground Window", "None Detected"]:
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

            # FALLBACK GDIGRAB (If OBS not running or failed)
            if not is_true_game_capture:
                try:
                    title_hint = re.sub(r'\s*\([\w\-\.]+\.exe\)', '', clean_target, flags=re.I).strip().lower()

                    # Step 1: Match by process name / PID
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            pname = (proc.info['name'] or '').lower()
                            is_cod = 'cod.exe' in pname or 'call of duty' in clean_target.lower() or 'cod' in clean_target.lower()
                            matches_exe = exe_hint and (exe_hint == pname or exe_hint in pname or pname in exe_hint)
                            matches_title = title_hint and (title_hint in pname or pname in title_hint)

                            if is_cod or matches_exe or matches_title:
                                pid = proc.info['pid']
                                def _enum_win(hwnd, ctx):
                                    if win32gui.IsWindowVisible(hwnd):
                                        _, p = win32process.GetWindowThreadProcessId(hwnd)
                                        if p == pid:
                                            rect = win32gui.GetWindowRect(hwnd)
                                            w = rect[2] - rect[0]
                                            h = rect[3] - rect[1]
                                            if w > 100 and h > 100:
                                                ctx.append((max(0, rect[0]), max(0, rect[1]), w, h))
                                rects = []
                                win32gui.EnumWindows(_enum_win, rects)
                                if rects:
                                    locked_rect = rects[0]
                                    logging.info(f"BroadcastDaemon: Resolved process PID {pid} ({pname}) window rect {locked_rect}")
                                    break
                        except Exception:
                            pass

                    # Step 2: Fallback to partial window title match via EnumWindows
                    if not locked_rect and title_hint:
                        def _enum_win_title(hwnd, ctx):
                            if win32gui.IsWindowVisible(hwnd):
                                t = (win32gui.GetWindowText(hwnd) or '').lower()
                                if t and (title_hint in t or t in title_hint):
                                    rect = win32gui.GetWindowRect(hwnd)
                                    w = rect[2] - rect[0]
                                    h = rect[3] - rect[1]
                                    if w > 100 and h > 100:
                                        ctx.append((max(0, rect[0]), max(0, rect[1]), w, h))
                        rects = []
                        win32gui.EnumWindows(_enum_win_title, rects)
                        if rects:
                            locked_rect = rects[0]
                            logging.info(f"BroadcastDaemon: Resolved HWND title substring match ({title_hint}) window rect {locked_rect}")

                    if not locked_rect:
                        hwnd = win32gui.FindWindow(None, target_prog) or win32gui.FindWindow(None, clean_target)
                        if hwnd and win32gui.IsWindowVisible(hwnd):
                            rect = win32gui.GetWindowRect(hwnd)
                            w = rect[2] - rect[0]
                            h = rect[3] - rect[1]
                            if w > 100 and h > 100:
                                locked_rect = (max(0, rect[0]), max(0, rect[1]), w, h)
                except Exception as e:
                    logging.debug(f"Window lock error: {e}")

        if not is_true_game_capture:
            if locked_rect:
                x, y, w, h = locked_rect
                logging.info(f"BroadcastDaemon: Locked video feed to program window ({target_prog}) at offset ({x}, {y}) size ({w}x{h})")
                ffmpeg_cmd.extend(["-thread_queue_size", "2048", "-rtbufsize", "512M", "-probesize", "32M", "-f", "gdigrab", "-framerate", str(fps), "-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{w}x{h}", "-draw_mouse", "1", "-i", "desktop"])
            else:
                logging.info(f"BroadcastDaemon: Full desktop display capture (Optimized Realtime GDI)")
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
        if audio_sources:
            for src in audio_sources:
                if not src.get("enabled", True):
                    continue
                audio_dev = src.get("deviceId", "")
                if not audio_dev or audio_dev in ["default", "anullsrc"]:
                    audio_dev = detect_microphone()
                if audio_dev in ingested_audio_devs:
                    continue
                ingested_audio_devs.add(audio_dev)
                ffmpeg_cmd.extend(["-thread_queue_size", "2048", "-f", "dshow", "-i", f"audio={audio_dev}"])
                audio_inputs.append(input_idx)
                input_idx += 1

        if not audio_inputs:
            mic_name = detect_microphone()
            ffmpeg_cmd.extend(["-thread_queue_size", "2048", "-f", "dshow", "-i", f"audio={mic_name}"])
            audio_inputs.append(input_idx)
            input_idx += 1

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
                    self.telemetry["endpoints"]["Virtual Camera"] = "STREAMING"
                    continue
                    
                if url:
                    escaped_url = escape_tee_url(url)
                    if url.startswith("https://"):
                        outputs.append(f"[f=hls:hls_time=2:hls_list_size=5:method=POST:select=\\'v:0,a:0\\']{escaped_url}")
                    else:
                        outputs.append(f"[f=flv:onfail=ignore:select=\\'v:0,a:0\\']{escaped_url}")
                    self.telemetry["endpoints"][ep_name] = "STREAMING"
            else:
                self.telemetry["endpoints"][ep_name] = "DISABLED"

        # Add recording output with multi-track mapping
        archive_escaped = escape_tee_url(archive_file)
        num_audio_streams = len(audio_inputs) + 1 if len(audio_inputs) > 1 else 1
        select_streams = "\\'v:0," + ",".join([f"a:{i}" for i in range(num_audio_streams)]) + "\\'"
        outputs.append(f"[{rec_mux_flags}:select={select_streams}]{archive_escaped}")
        self.telemetry["endpoints"]["Local Recording"] = "RECORDING"
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
            if len(audio_inputs) > 1:
                a_filters.append(f"[{a_idx}:a]aresample=async=1:first_pts=0,asplit=2[a_stem_mix{i}][a_stem_iso{i}]")
                a_outs_mix.append(f"[a_stem_mix{i}]")
                a_outs_iso.append(f"[a_stem_iso{i}]")
            else:
                a_filters.append(f"[{a_idx}:a]aresample=async=1:first_pts=0[a_master]")

        # Mix all audio stems for Track 1 (Master Output)
        if len(audio_inputs) > 1:
            a_mix_in = "".join(a_outs_mix)
            a_filters.append(f"{a_mix_in}amix=inputs={len(audio_inputs)}:duration=longest[a_master]")

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
            self.is_streaming = True
            logging.info(f"Spawning Hardware FFmpeg Broadcast Pipeline ({encoder_choice.upper()} @ {resolution} {fps}FPS)...")
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            threading.Thread(target=self._telemetry_reader, daemon=True).start()
            return True
        except Exception as e:
            logging.error(f"Failed to start FFmpeg process: {e}")
            self.is_streaming = False
            return False

    def _telemetry_reader(self):
        fps_pattern = re.compile(r"fps=\s*([\d\.]+)")
        bitrate_pattern = re.compile(r"bitrate=\s*([\d\.]+kbits/s)")
        speed_pattern = re.compile(r"speed=\s*([\d\.]+x)")
        drop_pattern = re.compile(r"drop=\s*(\d+)")
        
        with open("C:/AI-BS/backend/ffmpeg.log", "w", encoding="utf-8") as log_f:
            while self.is_streaming and self.process:
                line = self.process.stdout.readline()
                if not line:
                    break
                log_f.write(line)
                log_f.flush()
                if "frame=" in line:
                    fps_match = fps_pattern.search(line)
                    bitrate_match = bitrate_pattern.search(line)
                    speed_match = speed_pattern.search(line)
                    drop_match = drop_pattern.search(line)
                    if fps_match: self.telemetry["fps"] = fps_match.group(1)
                    if bitrate_match: 
                        self.telemetry["bitrate"] = bitrate_match.group(1)
                    elif hasattr(self, 'configured_bitrate') and self.configured_bitrate:
                        self.telemetry["bitrate"] = self.configured_bitrate
                    if speed_match: self.telemetry["speed"] = speed_match.group(1)
                    if drop_match: self.telemetry["dropped"] = drop_match.group(1)
        self.is_streaming = False

    def stop_stream(self):
        if not self.is_streaming or not self.process:
            return {"status": "stopped", "message": "Stream already offline"}
        logging.info("Stopping stream gracefully...")
        try:
            self.process.stdin.write("q\n")
            self.process.stdin.flush()
            self.process.wait(timeout=5)
        except Exception:
            self.process.kill()
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
        return {"status": "stopped", "message": "Stream stopped and archive saved"}

daemon = BroadcastDaemon()

@app.on_event("startup")
async def on_broadcast_daemon_startup():
    asyncio.create_task(daemon.run_telemetry_loop_async())

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
    sources: Optional[List[Dict[str, Any]]] = []

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
        sources=req.sources or []
    )
    return {"status": "streaming" if success else "error"}

@app.post("/stream/stop")
async def stop_stream_endpoint():
    return daemon.stop_stream()

@app.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket):
    await websocket.accept()
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
    logging.info("Starting Resilient AI-BS Broadcast Daemon on port 8005...")
    uvicorn.run(app, host="127.0.0.1", port=8005)
