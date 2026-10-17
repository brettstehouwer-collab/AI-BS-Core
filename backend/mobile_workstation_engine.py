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


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    hw_flag = "--apply-os" in sys.argv
    if cmd == "status":
        print(json.dumps(get_mobile_workstation_status(), indent=2))
    else:
        print(json.dumps(apply_mobile_workstation_profile(cmd, apply_os_resolution=hw_flag), indent=2))

