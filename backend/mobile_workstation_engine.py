import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import time
from pathlib import Path

WORKSPACE_ROOT = Path(r"C:\AI-BS")
CONFIG_DIR = WORKSPACE_ROOT / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_STATE_FILE = CONFIG_DIR / "mobile_workstation_profile.json"


class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmPositionX", ctypes.c_long),
        ("dmPositionY", ctypes.c_long),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]


ENUM_CURRENT_SETTINGS = -1
DM_PELSWIDTH = 0x00080000
DM_PELSHEIGHT = 0x00100000
CDS_UPDATEREGISTRY = 0x00000001
DISP_CHANGE_SUCCESSFUL = 0


MOBILE_PROFILES = {
    "mobile_1080p_150": {
        "id": "mobile_1080p_150",
        "label": "1080p Mobile Touch & High-Contrast (150% DPI)",
        "width": 1920,
        "height": 1080,
        "dpi_percent": 150,
        "ui_zoom": 1.22,
        "code_font_size": "0.98rem",
        "button_padding": "6px 12px",
        "recommended_for": "Phone Screens (Parsec / RustDesk High-Contrast Mode)"
    },
    "mobile_1440p_125": {
        "id": "mobile_1440p_125",
        "label": "1440p Mobile Pro & Bluetooth Trackpad (125% DPI)",
        "width": 2560,
        "height": 1440,
        "dpi_percent": 125,
        "ui_zoom": 1.12,
        "code_font_size": "0.92rem",
        "button_padding": "5px 10px",
        "recommended_for": "Large Phones / Foldables + Bluetooth Keyboard & Mouse"
    },
    "desktop_native": {
        "id": "desktop_native",
        "label": "Desktop Native Resolution (100% Standard DPI)",
        "width": 0,  # Preserves or restores native
        "height": 0,
        "dpi_percent": 100,
        "ui_zoom": 1.0,
        "code_font_size": "0.85rem",
        "button_padding": "3px 8px",
        "recommended_for": "Local Desktop Monitors (RTX 4090 Direct)"
    }
}


def get_current_display_settings() -> dict:
    """Queries Win32 User32 EnumDisplaySettingsW for current resolution, refresh rate, and DPI."""
    try:
        user32 = ctypes.windll.user32
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        if user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm)):
            # Also query available modes to see if 1920x1080 and 2560x1440 are supported
            supported_res = set()
            idx = 0
            mode_dm = DEVMODEW()
            mode_dm.dmSize = ctypes.sizeof(DEVMODEW)
            while user32.EnumDisplaySettingsW(None, idx, ctypes.byref(mode_dm)):
                if mode_dm.dmPelsWidth in (1920, 2560, 3840) and mode_dm.dmPelsHeight in (1080, 1440, 2160):
                    supported_res.add(f"{mode_dm.dmPelsWidth}x{mode_dm.dmPelsHeight}")
                idx += 1

            return {
                "width": int(dm.dmPelsWidth),
                "height": int(dm.dmPelsHeight),
                "refresh_rate_hz": int(dm.dmDisplayFrequency),
                "bits_per_pixel": int(dm.dmBitsPerPel),
                "log_pixels_dpi": int(dm.dmLogPixels) if dm.dmLogPixels else 96,
                "estimated_dpi_scale_percent": round((int(dm.dmLogPixels or 96) / 96.0) * 100),
                "supported_standard_modes": sorted(list(supported_res))
            }
    except Exception as e:
        return {"error": str(e), "width": 1920, "height": 1080, "refresh_rate_hz": 60}
    return {"width": 1920, "height": 1080, "refresh_rate_hz": 60}


def get_remote_and_input_telemetry() -> dict:
    """Checks Parsec, Tailscale, RustDesk, and connected Keyboard/Mouse/Trackpad HID devices."""
    telemetry = {
        "parsec_running": False,
        "tailscale_running": False,
        "tailscale_ip": None,
        "rustdesk_running": False,
        "hid_keyboards_detected": 0,
        "hid_pointing_devices_detected": 0
    }
    try:
        proc = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace"
        )
        out_lower = proc.stdout.lower()
        telemetry["parsec_running"] = "parsecd.exe" in out_lower or "pservice.exe" in out_lower
        telemetry["tailscale_running"] = "tailscaled.exe" in out_lower or "tailscale-ipn.exe" in out_lower
        telemetry["rustdesk_running"] = "rustdesk.exe" in out_lower
    except Exception:
        pass

    if telemetry["tailscale_running"]:
        try:
            ts_proc = subprocess.run(
                ["tailscale", "ip", "-4"],
                capture_output=True, text=True, timeout=3, encoding="utf-8", errors="replace"
            )
            if ts_proc.returncode == 0 and ts_proc.stdout.strip():
                telemetry["tailscale_ip"] = ts_proc.stdout.strip().splitlines()[0]
        except Exception:
            pass

    # Fast check for Keyboard / Mouse / Trackpad count via GetSystemMetrics
    try:
        user32 = ctypes.windll.user32
        mouse_present = bool(user32.GetSystemMetrics(19))  # SM_MOUSEPRESENT
        mouse_buttons = int(user32.GetSystemMetrics(43))   # SM_CMOUSEBUTTONS
        telemetry["hid_pointing_devices_detected"] = 1 if mouse_present else 0
        telemetry["mouse_buttons"] = mouse_buttons
        telemetry["hid_keyboards_detected"] = 1
    except Exception:
        pass

    return telemetry


def load_saved_profile() -> dict:
    if PROFILE_STATE_FILE.exists():
        try:
            return json.loads(PROFILE_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "active_profile_id": "desktop_native",
        "profile": MOBILE_PROFILES["desktop_native"],
        "os_resolution_applied": False
    }


def get_mobile_workstation_status() -> dict:
    t0 = time.perf_counter()
    display = get_current_display_settings()
    remote_hid = get_remote_and_input_telemetry()
    saved = load_saved_profile()

    # Save initial native resolution if not yet recorded
    if "native_width" not in saved and display.get("width"):
        saved["native_width"] = display["width"]
        saved["native_height"] = display["height"]
        try:
            PROFILE_STATE_FILE.write_text(json.dumps(saved, indent=2), encoding="utf-8")
        except Exception:
            pass

    return {
        "status": "success",
        "display": display,
        "remote_and_input": remote_hid,
        "active_profile_id": saved.get("active_profile_id", "desktop_native"),
        "active_profile": saved.get("profile", MOBILE_PROFILES["desktop_native"]),
        "available_profiles": MOBILE_PROFILES,
        "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2)
    }


def apply_mobile_workstation_profile(profile_id: str, apply_os_resolution: bool = False) -> dict:
    """
    Applies a Mobile Workstation & DPI Scaling Profile.
    - Updates BS-Chat & IDE UI scaling parameters immediately (100%, 125%, 150% DPI + High-Contrast).
    - If apply_os_resolution=True, invokes Win32 ChangeDisplaySettingsW to switch primary display resolution.
    """
    t0 = time.perf_counter()
    norm_id = (profile_id or "").strip().lower()
    if norm_id in ("1080p", "150%", "150", "mobile_1080p", "mobile_1080p_150"):
        norm_id = "mobile_1080p_150"
    elif norm_id in ("1440p", "125%", "125", "mobile_1440p", "mobile_1440p_125"):
        norm_id = "mobile_1440p_125"
    elif norm_id in ("reset", "native", "100%", "100", "desktop", "desktop_native"):
        norm_id = "desktop_native"

    if norm_id not in MOBILE_PROFILES:
        return {
            "status": "error",
            "message": f"Unknown profile '{profile_id}'. Valid profiles: {list(MOBILE_PROFILES.keys())}"
        }

    saved = load_saved_profile()
    current_disp = get_current_display_settings()
    if "native_width" not in saved and current_disp.get("width"):
        saved["native_width"] = current_disp["width"]
        saved["native_height"] = current_disp["height"]

    target_profile = dict(MOBILE_PROFILES[norm_id])
    os_change_result = "skipped (UI/IDE virtual DPI scaling active)"

    if apply_os_resolution:
        target_w = target_profile["width"] or saved.get("native_width", current_disp.get("width", 1920))
        target_h = target_profile["height"] or saved.get("native_height", current_disp.get("height", 1080))
        try:
            user32 = ctypes.windll.user32
            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(DEVMODEW)
            if user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm)):
                dm.dmPelsWidth = int(target_w)
                dm.dmPelsHeight = int(target_h)
                dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT
                res_code = user32.ChangeDisplaySettingsW(ctypes.byref(dm), 0)
                if res_code == DISP_CHANGE_SUCCESSFUL:
                    os_change_result = f"applied_win32_{target_w}x{target_h}"
                else:
                    os_change_result = f"win32_code_{res_code}_fallback_virtual_dpi"
        except Exception as e:
            os_change_result = f"error: {e}"

    new_state = {
        "active_profile_id": norm_id,
        "profile": target_profile,
        "os_resolution_applied": apply_os_resolution,
        "os_change_result": os_change_result,
        "native_width": saved.get("native_width", current_disp.get("width", 1920)),
        "native_height": saved.get("native_height", current_disp.get("height", 1080)),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    PROFILE_STATE_FILE.write_text(json.dumps(new_state, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "active_profile_id": norm_id,
        "profile": target_profile,
        "os_change_result": os_change_result,
        "display": get_current_display_settings(),
        "remote_and_input": get_remote_and_input_telemetry(),
        "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2)
    }


# ---------------------------------------------------------------------------
# 3-WAY WIRELESS SCREEN MIRROR & DISPLAY CAST ENGINE
# (1) PC -> Wireless Display (Miracast Win+K, DisplaySwitch Clone/Extend)
# (2) PC -> Phone (Live LAN/Tailscale IDE URL + Live Web Screen Caster)
# (3) Phone -> PC (Wireless ADB + Scrcpy v4.1 Hardware-Accelerated Mirror)
# ---------------------------------------------------------------------------

_LATEST_CAST_FRAME = {
    "data_url": None,
    "updated_at": 0.0,
    "frame_index": 0,
    "width": 0,
    "height": 0,
}


def _find_adb_exe() -> str:
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\adb.exe"),
        r"C:\AI-BS\tools\scrcpy\adb.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "adb"


def _find_scrcpy_exe() -> str:
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\scrcpy.exe"),
        r"C:\AI-BS\tools\scrcpy\scrcpy.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # Search WinGet packages folder
    winget_pkgs = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"))
    if winget_pkgs.is_dir():
        for p in winget_pkgs.glob("*scrcpy*/*/scrcpy.exe"):
            return str(p)
    return "scrcpy"


def get_lan_ipv4_addresses() -> list:
    """Returns active non-loopback IPv4 addresses (prioritizing Wi-Fi 192.168.x.x)."""
    import socket
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and not ip.startswith("169.254.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    # Sort so 192.168.4.x or 192.168.1.x comes before 192.168.137.1 (hotspot)
    ips.sort(key=lambda x: (0 if (x.startswith("192.168.") and not x.startswith("192.168.137.")) else 1, x))
    return ips or ["127.0.0.1"]


def get_adb_connected_devices() -> list:
    """Queries `adb devices -l` for connected USB or Wireless Android phones/tablets."""
    adb_exe = _find_adb_exe()
    devices = []
    try:
        proc = subprocess.run(
            [adb_exe, "devices", "-l"],
            capture_output=True, text=True, timeout=4, encoding="utf-8", errors="replace"
        )
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]
                model = ""
                for tok in parts[2:]:
                    if tok.startswith("model:"):
                        model = tok.split(":", 1)[1]
                devices.append({
                    "serial": serial,
                    "state": state,
                    "model": model or "Android Device",
                    "transport": "wireless" if ":" in serial else "usb"
                })
    except Exception:
        pass
    return devices


def scan_nearby_wireless_and_lan_devices() -> dict:
    """Scans Windows PnP wireless displays/monitors and active Wi-Fi subnet peers."""
    wireless_displays = []
    lan_peers = []

    # 1. Check connected/paired Miracast & Monitors via PowerShell Get-PnpDevice
    try:
        ps_cmd = (
            "Get-PnpDevice -Class 'Monitor','Miracast','Bluetooth','AudioEndpoint' -Status OK -ErrorAction SilentlyContinue | "
            "Select-Object Class, FriendlyName | ConvertTo-Json -Compress"
        )
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=4, encoding="utf-8", errors="replace"
        )
        raw = proc.stdout.strip()
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                parsed = [parsed]
            for item in parsed[:25]:
                fname = (item.get("FriendlyName") or "").strip()
                cls = (item.get("Class") or "").strip()
                if fname:
                    wireless_displays.append({"class": cls, "name": fname})
    except Exception:
        pass

    # 2. Check ARP table on primary Wi-Fi subnet for nearby phones/TVs/devices
    try:
        proc = subprocess.run(
            ["arp", "-a"],
            capture_output=True, text=True, timeout=3, encoding="utf-8", errors="replace"
        )
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[2].lower() == "dynamic":
                ip = parts[0]
                mac = parts[1]
                if ip.startswith("192.168.") and not ip.endswith(".255") and not ip.endswith(".1"):
                    lan_peers.append({"ip": ip, "mac": mac})
    except Exception:
        pass

    return {
        "pnp_displays_and_endpoints": wireless_displays,
        "wifi_lan_peers": lan_peers[:20]
    }


def get_wireless_cast_status() -> dict:
    t0 = time.perf_counter()
    lan_ips = get_lan_ipv4_addresses()
    primary_ip = lan_ips[0] if lan_ips else "127.0.0.1"
    remote_hid = get_remote_and_input_telemetry()
    adb_devices = get_adb_connected_devices()
    scrcpy_exe = _find_scrcpy_exe()
    adb_exe = _find_adb_exe()

    scrcpy_running = False
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq scrcpy.exe", "/NH"],
            capture_output=True, text=True, timeout=2, encoding="utf-8", errors="replace"
        )
        scrcpy_running = "scrcpy.exe" in proc.stdout.lower()
    except Exception:
        pass

    cast_active = (time.time() - _LATEST_CAST_FRAME["updated_at"]) < 10.0

    return {
        "status": "success",
        "primary_lan_ip": primary_ip,
        "all_lan_ips": lan_ips,
        "tailscale_ip": remote_hid.get("tailscale_ip"),
        "urls": {
            "pc_to_phone_workspace_lan": f"http://{primary_ip}:5173/?tab=ide",
            "pc_to_phone_live_screen_viewer": f"http://{primary_ip}:8000/api/executive/wireless-cast/viewer",
            "tailscale_workspace": f"http://{remote_hid['tailscale_ip']}:5173/?tab=ide" if remote_hid.get("tailscale_ip") else None,
            "tailscale_live_viewer": f"http://{remote_hid['tailscale_ip']}:8000/api/executive/wireless-cast/viewer" if remote_hid.get("tailscale_ip") else None,
        },
        "phone_to_pc": {
            "adb_exe": adb_exe,
            "scrcpy_exe": scrcpy_exe,
            "scrcpy_installed": os.path.isfile(scrcpy_exe),
            "scrcpy_running": scrcpy_running,
            "adb_devices": adb_devices,
        },
        "pc_to_wireless_display": {
            "miracast_shortcut": "Win + K",
            "display_modes": ["clone", "extend", "external", "internal"],
        },
        "live_browser_cast": {
            "active": cast_active,
            "frame_index": _LATEST_CAST_FRAME["frame_index"],
            "last_frame_age_sec": round(time.time() - _LATEST_CAST_FRAME["updated_at"], 1) if _LATEST_CAST_FRAME["updated_at"] else None,
        },
        "display": get_current_display_settings(),
        "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2)
    }


def execute_wireless_cast_action(
    action: str,
    mode: str = "extend",
    phone_ip: str = "",
    pair_port: str = "",
    pair_code: str = "",
    bitrate: str = "8M",
    max_fps: int = 60,
    stay_awake: bool = True,
) -> dict:
    """
    Executes a 3-Way Wireless Screen Mirror / Cast action on the Windows 11 Host:
      - 'win_k'                  : Opens the Windows 11 Wireless Display Cast flyout (Win + K) to connect to nearby TVs/monitors.
      - 'display_mode'           : Switches Windows projection mode via DisplaySwitch.exe (/clone, /extend, /external, /internal).
      - 'project_to_pc_settings' : Opens Windows 'Projecting to this PC' settings (Miracast receiver for Phone->PC).
      - 'connected_devices'      : Opens Windows Bluetooth & Wireless Displays settings (ms-settings:connecteddevices).
      - 'phone_to_pc_scrcpy'     : Connects to Android phone via USB or Wireless ADB and launches Scrcpy v4.1 mirror window on PC.
      - 'adb_tcpip_auto'         : Switches USB-connected Android phone to Wireless TCP/IP mode (:5555) and connects over Wi-Fi.
      - 'scan_nearby'            : Scans nearby wireless displays and Wi-Fi LAN devices.
    """
    act = (action or "").strip().lower()

    if act == "win_k":
        try:
            # Synthesize Win + K via Win32 user32.keybd_event (VK_LWIN = 0x5B, VK_K = 0x4B)
            user32 = ctypes.windll.user32
            KEYEVENTF_KEYUP = 0x0002
            user32.keybd_event(0x5B, 0, 0, 0)
            user32.keybd_event(0x4B, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(0x4B, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(0x5B, 0, KEYEVENTF_KEYUP, 0)
            return {
                "status": "success",
                "action": "win_k",
                "message": "Opened Windows 11 Wireless Display Cast flyout (Win + K) on host desktop. Select your nearby Wireless TV, Monitor, or Tablet to mirror or extend!"
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to trigger Win+K: {e}"}

    if act == "display_mode":
        flag_map = {
            "clone": "/clone",
            "duplicate": "/clone",
            "mirror": "/clone",
            "extend": "/extend",
            "external": "/external",
            "second": "/external",
            "internal": "/internal",
            "pc": "/internal",
        }
        flag = flag_map.get((mode or "extend").lower(), "/extend")
        try:
            subprocess.Popen(["DisplaySwitch.exe", flag])
            return {
                "status": "success",
                "action": "display_mode",
                "mode": flag,
                "message": f"Executed Windows DisplaySwitch.exe {flag} ({mode.upper()} projection mode)."
            }
        except Exception as e:
            return {"status": "error", "message": f"DisplaySwitch error: {e}"}

    if act == "project_to_pc_settings":
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "ms-settings:project"], shell=True)
            return {
                "status": "success",
                "action": "project_to_pc_settings",
                "message": "Opened Windows 'Projecting to this PC' settings (ms-settings:project)."
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if act == "connected_devices":
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "ms-settings:connecteddevices"], shell=True)
            return {
                "status": "success",
                "action": "connected_devices",
                "message": "Opened Windows Bluetooth & Wireless Displays settings (ms-settings:connecteddevices)."
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if act == "scan_nearby":
        scan_res = scan_nearby_wireless_and_lan_devices()
        return {
            "status": "success",
            "action": "scan_nearby",
            "scan": scan_res,
            "adb_devices": get_adb_connected_devices(),
            "message": f"Found {len(scan_res['pnp_displays_and_endpoints'])} display/audio endpoints and {len(scan_res['wifi_lan_peers'])} Wi-Fi LAN peers."
        }

    if act == "adb_tcpip_auto":
        adb_exe = _find_adb_exe()
        try:
            # 1. Switch USB device to port 5555
            subprocess.run([adb_exe, "tcpip", "5555"], capture_output=True, text=True, timeout=5)
            time.sleep(1.0)
            # 2. Try to discover phone's wlan0 IP via adb shell ip route
            ip_proc = subprocess.run(
                [adb_exe, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"],
                capture_output=True, text=True, timeout=4, encoding="utf-8", errors="replace"
            )
            import re
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", ip_proc.stdout)
            discovered_ip = m.group(1) if m else phone_ip.strip()
            if discovered_ip:
                conn_proc = subprocess.run(
                    [adb_exe, "connect", f"{discovered_ip}:5555"],
                    capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace"
                )
                return {
                    "status": "success",
                    "action": "adb_tcpip_auto",
                    "phone_ip": discovered_ip,
                    "adb_output": conn_proc.stdout.strip(),
                    "adb_devices": get_adb_connected_devices(),
                    "message": f"Enabled Wireless ADB on {discovered_ip}:5555 ({conn_proc.stdout.strip()}). You can now unplug USB and mirror wirelessly!"
                }
            return {
                "status": "warning",
                "message": "Executed `adb tcpip 5555`. Plug in your phone via USB once or enter your Phone's Wi-Fi IP address to connect wirelessly."
            }
        except Exception as e:
            return {"status": "error", "message": f"ADB TCP/IP setup failed: {e}"}

    if act == "phone_to_pc_scrcpy":
        adb_exe = _find_adb_exe()
        scrcpy_exe = _find_scrcpy_exe()
        logs = []

        # Optional Wireless Debugging Pairing (Android 11+ Developer Options -> Wireless debugging -> Pair device with pairing code)
        if phone_ip and pair_port and pair_code:
            try:
                pair_target = f"{phone_ip.strip()}:{pair_port.strip()}"
                p_res = subprocess.run(
                    [adb_exe, "pair", pair_target, pair_code.strip()],
                    capture_output=True, text=True, timeout=8, encoding="utf-8", errors="replace"
                )
                logs.append(f"ADB Pair ({pair_target}): {(p_res.stdout or p_res.stderr).strip()}")
            except Exception as e:
                logs.append(f"ADB Pair error: {e}")

        # Optional Wireless ADB Connect
        if phone_ip:
            target_addr = phone_ip.strip() if ":" in phone_ip.strip() else f"{phone_ip.strip()}:5555"
            try:
                c_res = subprocess.run(
                    [adb_exe, "connect", target_addr],
                    capture_output=True, text=True, timeout=6, encoding="utf-8", errors="replace"
                )
                logs.append(f"ADB Connect ({target_addr}): {(c_res.stdout or c_res.stderr).strip()}")
            except Exception as e:
                logs.append(f"ADB Connect error: {e}")

        devices = get_adb_connected_devices()
        online_devs = [d for d in devices if d.get("state") == "device"]
        if not online_devs:
            return {
                "status": "warning",
                "logs": logs,
                "adb_devices": devices,
                "message": (
                    "No authorized Android device detected yet. "
                    "To mirror Phone ➔ PC wirelessly:\n"
                    "1. On your phone, enable Developer Options ➔ Wireless Debugging (or plug in via USB once and click 'Enable Wireless ADB').\n"
                    "2. Enter your Phone Wi-Fi IP (e.g. 192.168.4.x:5555) and click 'Mirror Phone to PC (Scrcpy)'."
                )
            }

        # Launch Scrcpy v4.1 window on the PC desktop
        cmd = [
            scrcpy_exe,
            "--window-title", f"AI-BS Wireless Phone Mirror ({online_devs[0]['model']})",
            "--video-bit-rate", bitrate or "8M",
            "--max-fps", str(max_fps or 60),
        ]
        if stay_awake:
            cmd.append("--stay-awake")
        if phone_ip:
            target_serial = phone_ip.strip() if ":" in phone_ip.strip() else f"{phone_ip.strip()}:5555"
            if any(d["serial"] == target_serial for d in online_devs):
                cmd.extend(["-s", target_serial])

        try:
            subprocess.Popen(cmd, cwd=r"C:\AI-BS")
            return {
                "status": "success",
                "action": "phone_to_pc_scrcpy",
                "device": online_devs[0],
                "logs": logs,
                "message": f"Launched Scrcpy v4.1 60FPS Phone-to-PC Mirror for {online_devs[0]['model']} ({online_devs[0]['serial']})!"
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to launch scrcpy: {e}", "logs": logs}

    return {"status": "error", "message": f"Unknown wireless cast action: {action}"}


def store_cast_frame(data_url: str, width: int = 1920, height: int = 1080) -> dict:
    """Stores the latest JPEG data_url frame captured from the PC screen/workspace for low-latency phone/TV viewing."""
    _LATEST_CAST_FRAME["data_url"] = data_url
    _LATEST_CAST_FRAME["updated_at"] = time.time()
    _LATEST_CAST_FRAME["frame_index"] += 1
    _LATEST_CAST_FRAME["width"] = width
    _LATEST_CAST_FRAME["height"] = height
    return {
        "status": "success",
        "frame_index": _LATEST_CAST_FRAME["frame_index"],
        "updated_at": _LATEST_CAST_FRAME["updated_at"],
    }


def get_latest_cast_frame() -> dict:
    age = time.time() - _LATEST_CAST_FRAME["updated_at"] if _LATEST_CAST_FRAME["updated_at"] else 9999.0
    return {
        "status": "success",
        "active": age < 10.0 and bool(_LATEST_CAST_FRAME["data_url"]),
        "frame_index": _LATEST_CAST_FRAME["frame_index"],
        "age_seconds": round(age, 2),
        "width": _LATEST_CAST_FRAME["width"],
        "height": _LATEST_CAST_FRAME["height"],
        "data_url": _LATEST_CAST_FRAME["data_url"],
    }


def get_cast_viewer_html() -> str:
    """Returns a zero-install, mobile- & Smart-TV-optimized HTML5 Live Screen Mirror Receiver page."""
    lan_ips = get_lan_ipv4_addresses()
    primary_ip = lan_ips[0] if lan_ips else "127.0.0.1"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes" />
  <title>AI-BS Wireless Screen Mirror Receiver ({primary_ip})</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #05070d;
      color: #e2e8f0;
      font-family: system-ui, -apple-system, sans-serif;
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}
    header {{
      background: rgba(15, 23, 42, 0.95);
      border-bottom: 1px solid rgba(56, 189, 248, 0.3);
      padding: 8px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      z-index: 10;
    }}
    .badge {{
      font-size: 12px;
      padding: 3px 9px;
      border-radius: 999px;
      font-weight: 700;
      background: rgba(16, 185, 129, 0.18);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.4);
    }}
    .btn {{
      background: #2563eb;
      color: #fff;
      border: 1px solid #60a5fa;
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
    }}
    #stage {{
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      background: #000;
      overflow: auto;
    }}
    #mirrorImg {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      display: none;
    }}
    #emptyState {{
      text-align: center;
      padding: 24px;
      max-width: 480px;
    }}
  </style>
</head>
<body>
  <header>
    <div style="display:flex;align-items:center;gap:8px;">
      <span>📡</span>
      <strong style="color:#38bdf8;font-size:14px;">AI-BS Wireless Screen Mirror</strong>
      <span id="statusBadge" class="badge">Connecting...</span>
    </div>
    <div style="display:flex;gap:8px;align-items:center;">
      <a class="btn" href="http://{primary_ip}:5173/?tab=ide">⚡ Open Interactive BS-Chat IDE</a>
      <button class="btn" onclick="document.documentElement.requestFullscreen && document.documentElement.requestFullscreen()">⛶ Fullscreen</button>
    </div>
  </header>
  <div id="stage">
    <img id="mirrorImg" alt="Live PC Screen Stream" />
    <div id="emptyState">
      <h2 style="color:#60a5fa;margin-bottom:10px;">Ready to Receive PC Screen Stream</h2>
      <p style="color:#94a3b8;font-size:14px;line-height:1.5;margin-bottom:16px;">
        In BS-Chat on your PC, open <strong>📡 Wireless Cast & Mirror</strong> and click
        <strong>"Start Live PC Screen Cast to Phone/TV"</strong>, or click below to use the full interactive IDE directly on this device:
      </p>
      <a class="btn" style="padding:10px 18px;font-size:14px;display:inline-block;" href="http://{primary_ip}:5173/?tab=ide">
        🚀 Launch Full Interactive AI-BS Workspace ({primary_ip}:5173)
      </a>
    </div>
  </div>
  <script>
    let lastFrame = -1;
    const imgEl = document.getElementById('mirrorImg');
    const emptyEl = document.getElementById('emptyState');
    const badgeEl = document.getElementById('statusBadge');

    async function pollFrame() {{
      try {{
        const res = await fetch('/api/executive/wireless-cast/frame?t=' + Date.now());
        const data = await res.json();
        if (data.active && data.data_url) {{
          if (data.frame_index !== lastFrame) {{
            imgEl.src = data.data_url;
            lastFrame = data.frame_index;
          }}
          imgEl.style.display = 'block';
          emptyEl.style.display = 'none';
          badgeEl.textContent = '🟢 LIVE STREAM (Frame #' + data.frame_index + ')';
        }} else {{
          badgeEl.textContent = '⏳ Standby (Click Start Cast on PC)';
        }}
      }} catch (e) {{
        badgeEl.textContent = '⚠️ Reconnecting...';
      }}
      setTimeout(pollFrame, 180);
    }}
    pollFrame();
  </script>
</body>
</html>"""


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    hw_flag = "--apply-os" in sys.argv
    if cmd == "status":
        print(json.dumps(get_mobile_workstation_status(), indent=2))
    elif cmd == "cast-status":
        print(json.dumps(get_wireless_cast_status(), indent=2))
    else:
        print(json.dumps(apply_mobile_workstation_profile(cmd, apply_os_resolution=hw_flag), indent=2))

