"""
AI-BS Broadcast Studio Advanced Stream Engine & Platform Ingest Telemetry
Provides comprehensive platform specifications, real-time socket ping diagnostics,
hardware NVENC encoding profiles, and native streaming configuration.
"""

from __future__ import annotations

import json
import base64
import copy
import tempfile
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ══════════════════════════════════════════════════════════════════════════
# 1. PLATFORM INGEST SPECIFICATIONS REGISTRY
# ══════════════════════════════════════════════════════════════════════════

STREAM_PLATFORM_SPECS: Dict[str, Dict[str, Any]] = {
    "twitch": {
        "id": "twitch",
        "name": "Twitch (Amazon IVS)",
        "icon": "🟣",
        "default_url": "rtmp://iad05.contribute.live-video.net/app/",
        "alt_urls": [
            ("US East (Ashburn)", "rtmp://iad05.contribute.live-video.net/app/"),
            ("US Central (Chicago)", "rtmp://ord02.contribute.live-video.net/app/"),
            ("US West (San Jose)", "rtmp://sjc01.contribute.live-video.net/app/"),
            ("Europe (Frankfurt)", "rtmp://fra02.contribute.live-video.net/app/"),
        ],
        "protocol": "RTMP",
        "port": 1935,
        "max_video_bitrate_kbps": 8000,
        "recommended_bitrate_kbps": 6000,
        "supported_codecs": ["H.264 (NVENC AVC)", "AV1 (Enhanced Broadcasting Beta)"],
        "rate_control": "CBR (Constant Bitrate Required)",
        "keyframe_interval_sec": 2.0,
        "bframes": 2,
        "max_audio_bitrate_kbps": 160,
        "audio_samplerate": "48.0 kHz",
        "max_resolution": "1920x1080 (1080p60)",
        "aspect_ratio": "16:9",
        "vod_track_support": True,
        "color_format": "NV12 / Rec. 709",
        "notes": (
            "Strict CBR required. Max 8,000 kbps for Affiliates/Partners, 6,000 kbps standard. "
            "Twitch VOD Track supported for copyright-safe music streaming."
        ),
    },
    "youtube_4k": {
        "id": "youtube_4k",
        "name": "YouTube Live (4K UHD HDR)",
        "icon": "🔴",
        "default_url": "rtmp://a.rtmp.youtube.com/live2",
        "alt_urls": [
            ("Primary RTMP Ingest", "rtmp://a.rtmp.youtube.com/live2"),
            ("Backup RTMP Ingest", "rtmp://b.rtmp.youtube.com/live2"),
            ("Encrypted RTMPS Ingest (Port 443)", "rtmps://a.rtmp.youtube.com:443/live2"),
        ],
        "protocol": "RTMP / RTMPS",
        "port": 1935,
        "max_video_bitrate_kbps": 51000,
        "recommended_bitrate_kbps": 25000,
        "supported_codecs": ["AV1 (Dual NVENC 8th Gen)", "HEVC / H.265 (HDR10)", "H.264"],
        "rate_control": "CBR",
        "keyframe_interval_sec": 2.0,
        "bframes": 3,
        "max_audio_bitrate_kbps": 320,
        "audio_samplerate": "48.0 kHz",
        "max_resolution": "3840x2160 (4K UHD 60fps)",
        "aspect_ratio": "16:9",
        "vod_track_support": False,
        "color_format": "P010 / Rec. 2100 (HDR) or NV12 / Rec. 709",
        "notes": (
            "Dual 8th Gen NVENC AV1 on RTX 4090 delivers cinematic 4K 60fps at 25-35 Mbps. "
            "10-bit HDR10 color space supported via HEVC/AV1."
        ),
    },
    "youtube_1080p": {
        "id": "youtube_1080p",
        "name": "YouTube Live (1080p60 FHD)",
        "icon": "🔴",
        "default_url": "rtmp://a.rtmp.youtube.com/live2",
        "alt_urls": [
            ("Primary RTMP Ingest", "rtmp://a.rtmp.youtube.com/live2"),
            ("Backup RTMP Ingest", "rtmp://b.rtmp.youtube.com/live2"),
        ],
        "protocol": "RTMP",
        "port": 1935,
        "max_video_bitrate_kbps": 9000,
        "recommended_bitrate_kbps": 6800,
        "supported_codecs": ["AV1", "HEVC / H.265", "H.264"],
        "rate_control": "CBR",
        "keyframe_interval_sec": 2.0,
        "bframes": 2,
        "max_audio_bitrate_kbps": 256,
        "audio_samplerate": "48.0 kHz",
        "max_resolution": "1920x1080 (1080p60)",
        "aspect_ratio": "16:9",
        "vod_track_support": False,
        "color_format": "NV12 / Rec. 709",
        "notes": "Standard high-definition 60 FPS YouTube broadcast profile.",
    },
    "kick": {
        "id": "kick",
        "name": "Kick.com (Ultra-Low Latency)",
        "icon": "🟢",
        "default_url": "rtmp://fa723fc1b171.global-contribute.live-video.net/app/",
        "alt_urls": [
            ("Global Contribute (Anycast)", "rtmp://fa723fc1b171.global-contribute.live-video.net/app/"),
        ],
        "protocol": "RTMP",
        "port": 1935,
        "max_video_bitrate_kbps": 8000,
        "recommended_bitrate_kbps": 8000,
        "supported_codecs": ["H.264 (NVENC AVC)"],
        "rate_control": "CBR",
        "keyframe_interval_sec": 2.0,
        "bframes": 2,
        "max_audio_bitrate_kbps": 160,
        "audio_samplerate": "48.0 kHz",
        "max_resolution": "1920x1080 (1080p60)",
        "aspect_ratio": "16:9",
        "vod_track_support": False,
        "color_format": "NV12 / Rec. 709",
        "notes": "Full 8,000 kbps 1080p 60fps CBR supported for all creators with 2s keyframes.",
    },
    "tiktok": {
        "id": "tiktok",
        "name": "TikTok Live (Vertical Shorts / Reels)",
        "icon": "📱",
        "default_url": "rtmp://live.tiktok.com/live/",
        "alt_urls": [
            ("Global Live Ingest", "rtmp://live.tiktok.com/live/"),
        ],
        "protocol": "RTMP",
        "port": 1935,
        "max_video_bitrate_kbps": 6000,
        "recommended_bitrate_kbps": 4500,
        "supported_codecs": ["H.264 (AVC)"],
        "rate_control": "CBR",
        "keyframe_interval_sec": 2.0,
        "bframes": 2,
        "max_audio_bitrate_kbps": 128,
        "audio_samplerate": "44.1 / 48.0 kHz",
        "max_resolution": "1080x1920 (Vertical 9:16)",
        "aspect_ratio": "9:16",
        "vod_track_support": False,
        "color_format": "NV12 / Rec. 709",
        "notes": (
            "Requires 9:16 Vertical canvas. Stream key is generated dynamically via "
            "TikTok Live Studio / Creator Center."
        ),
    },
    "facebook": {
        "id": "facebook",
        "name": "Facebook Live (Meta Gaming)",
        "icon": "🔵",
        "default_url": "rtmps://live-api-s.facebook.com:443/rtmp/",
        "alt_urls": [
            ("Secure RTMPS (Port 443)", "rtmps://live-api-s.facebook.com:443/rtmp/"),
        ],
        "protocol": "RTMPS (SSL Required)",
        "port": 443,
        "max_video_bitrate_kbps": 8000,
        "recommended_bitrate_kbps": 6000,
        "supported_codecs": ["H.264 (AVC)"],
        "rate_control": "CBR",
        "keyframe_interval_sec": 2.0,
        "bframes": 2,
        "max_audio_bitrate_kbps": 128,
        "audio_samplerate": "48.0 kHz",
        "max_resolution": "1920x1080 (1080p60)",
        "aspect_ratio": "16:9",
        "vod_track_support": False,
        "color_format": "NV12 / Rec. 709",
        "notes": "Strictly requires TLS/SSL RTMPS on Port 443. Keyframe interval must be 2 seconds.",
    },
    "sovereign_srt": {
        "id": "sovereign_srt",
        "name": "Sovereign SRT / Broadcast Link (Ultra-Low Latency)",
        "icon": "⚡",
        "default_url": "srt://127.0.0.1:8089?mode=caller&latency=120",
        "alt_urls": [
            ("Local HLS/SRT Master (Port 8089)", "srt://127.0.0.1:8089?mode=caller&latency=120"),
            ("Local Broadcast Kernel (Port 8088)", "rtmp://127.0.0.1:8088/live"),
        ],
        "protocol": "SRT / Custom RTMP",
        "port": 8089,
        "max_video_bitrate_kbps": 60000,
        "recommended_bitrate_kbps": 20000,
        "supported_codecs": ["AV1 (Dual NVENC)", "HEVC / H.265", "H.264 (Lossless / Intra)"],
        "rate_control": "CBR / VBR / CQP",
        "keyframe_interval_sec": 1.0,
        "bframes": 0,
        "max_audio_bitrate_kbps": 320,
        "audio_samplerate": "48.0 kHz",
        "max_resolution": "7680x4320 (8K Master)",
        "aspect_ratio": "16:9 / 21:9",
        "vod_track_support": True,
        "color_format": "NV12 / P010 / RGB24",
        "notes": (
            "Professional point-to-point Secure Reliable Transport (SRT) link with sub-150ms buffer. "
            "Zero cloud lock-in sovereign broadcasting."
        ),
    },
}

# Aliases for lookup by human display name
STREAM_PLATFORM_SPECS["Twitch"] = STREAM_PLATFORM_SPECS["twitch"]
STREAM_PLATFORM_SPECS["YouTube Live"] = STREAM_PLATFORM_SPECS["youtube_4k"]
STREAM_PLATFORM_SPECS["YouTube Live 4K"] = STREAM_PLATFORM_SPECS["youtube_4k"]
STREAM_PLATFORM_SPECS["YouTube Live 1080p"] = STREAM_PLATFORM_SPECS["youtube_1080p"]
STREAM_PLATFORM_SPECS["Kick"] = STREAM_PLATFORM_SPECS["kick"]
STREAM_PLATFORM_SPECS["TikTok Live"] = STREAM_PLATFORM_SPECS["tiktok"]
STREAM_PLATFORM_SPECS["Facebook Live"] = STREAM_PLATFORM_SPECS["facebook"]
STREAM_PLATFORM_SPECS["Sovereign Broadcast"] = STREAM_PLATFORM_SPECS["sovereign_srt"]

# Ingest endpoints probed for live ping & TCP roundtrip latency
PING_TEST_TARGETS: Dict[str, Tuple[str, int, str]] = {
    "Twitch (US East - Ashburn)": ("iad05.contribute.live-video.net", 1935, "twitch"),
    "Twitch (US Central - Chicago)": ("ord02.contribute.live-video.net", 1935, "twitch"),
    "Twitch (US West - San Jose)": ("sjc01.contribute.live-video.net", 1935, "twitch"),
    "Twitch (Europe - Frankfurt)": ("fra02.contribute.live-video.net", 1935, "twitch"),
    "YouTube Live (Primary RTMP)": ("a.rtmp.youtube.com", 1935, "youtube_4k"),
    "YouTube Live (Backup RTMP)": ("b.rtmp.youtube.com", 1935, "youtube_1080p"),
    "YouTube Live (Secure RTMPS)": ("a.rtmp.youtube.com", 443, "youtube_4k"),
    "Kick (Global Anycast)": ("fa723fc1b171.global-contribute.live-video.net", 1935, "kick"),
    "TikTok Live (Global Ingest)": ("live.tiktok.com", 443, "tiktok"),
    "Facebook Live (RTMPS 443)": ("live-api-s.facebook.com", 443, "facebook"),
    "Sovereign Local Link (Port 8089)": ("127.0.0.1", 8089, "sovereign_srt"),
    "FastAPI Master Core (Port 8080)": ("127.0.0.1", 8080, "sovereign_srt"),
}

OUTPUT_RESOLUTION_PRESETS = [
    ("1920x1080 (1080p 60fps - Standard 16:9)", 1920, 1080, "16:9", 60),
    ("3840x2160 (4K UHD 60fps - Master 16:9)", 3840, 2160, "16:9", 60),
    ("2560x1440 (1440p QHD 60fps - 16:9)", 2560, 1440, "16:9", 60),
    ("1080x1920 (Shorts / TikTok / Reels - 9:16)", 1080, 1920, "9:16", 60),
    ("1080x1080 (1:1 Square Feed)", 1080, 1080, "1:1", 60),
    ("1440x1080 (4:3 Retro / Gaming CRT)", 1440, 1080, "4:3", 60),
    ("2560x1080 (21:9 Ultra-Wide Gaming)", 2560, 1080, "21:9", 60),
    ("1280x720 (720p 60fps - High Performance)", 1280, 720, "16:9", 60),
]


# ══════════════════════════════════════════════════════════════════════════
# 2. MULTI-THREADED REAL-TIME INGEST PING PROBE
# ══════════════════════════════════════════════════════════════════════════

class PlatformPingProbeThread(QThread):
    """Asynchronously measures TCP round-trip latency to all streaming service ingest servers.

    Zero UI thread blocking; emits per-server latency updates and final summary.
    """

    ping_updated = pyqtSignal(str, float, str, str)  # name, ping_ms, status_label, platform_id
    probe_finished = pyqtSignal(dict)                # name -> result dict
    all_finished = pyqtSignal(dict)                  # alias for audit & backward compatibility

    def __init__(self, targets: Optional[Dict[str, Tuple[str, int, str]]] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.targets = targets or PING_TEST_TARGETS
        self._running = True

    def stop(self) -> None:
        self._running = False
        self.wait(1200)

    def run(self) -> None:
        results: Dict[str, Dict[str, Any]] = {}

        for name, (host, port, plat_id) in self.targets.items():
            if not self._running:
                break

            t0 = time.perf_counter()
            ping_ms = -1.0
            status = "Offline"

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.2)
                res = sock.connect_ex((host, port))
                latency = (time.perf_counter() - t0) * 1000.0
                sock.close()

                if res == 0:
                    ping_ms = round(latency, 1)
                    if ping_ms < 35.0:
                        status = "Ultra-Low Latency"
                    elif ping_ms < 80.0:
                        status = "Optimal"
                    elif ping_ms < 140.0:
                        status = "Fair"
                    else:
                        status = "High Latency"
                else:
                    # Fallback DNS probe
                    try:
                        socket.gethostbyname(host)
                        ping_ms = round(latency, 1)
                        status = "Reachable"
                    except Exception:
                        status = "Unreachable"
            except Exception:
                status = "Timeout"

            item = {
                "name": name,
                "host": host,
                "port": port,
                "platform_id": plat_id,
                "ping_ms": ping_ms,
                "status": status,
            }
            results[name] = item
            self.ping_updated.emit(name, ping_ms, status, plat_id)
            time.sleep(0.04)

        self.probe_finished.emit(results)
        self.all_finished.emit(results)


# ══════════════════════════════════════════════════════════════════════════
# 3. STREAM PROFILE PERSISTENCE MANAGER
# ══════════════════════════════════════════════════════════════════════════

class StreamProfileManager:
    r"""Manages persistent saving and loading of stream credentials, encoder profiles,

    and platform requirements to C:\AI-BS\stream_profiles.json.
    """

    PROFILE_FILE = Path(r"C:\AI-BS\stream_profiles.json")

    @classmethod
    def load(cls) -> Dict[str, Any]:
        defaults = cls.get_defaults()
        if not cls.PROFILE_FILE.exists():
            return defaults
        try:
            data = json.loads(cls.PROFILE_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return defaults
            for section, value in defaults.items():
                if isinstance(value, dict):
                    saved=data.get(section,{})
                    if not isinstance(saved,dict): saved={}
                    data[section]={**value,**saved}
            for name, destination in data['destinations'].items():
                if not isinstance(destination,dict):
                    raise ValueError('Invalid destination')
                if destination.get('key_dpapi'):
                    try:
                        import win32crypt
                        destination['key']=win32crypt.CryptUnprotectData(base64.b64decode(destination['key_dpapi'],validate=True),None,None,None,1)[1].decode('utf-8')
                    except Exception:
                        destination['key']=''
                        destination['enabled']=False
                        destination['_credential_unavailable']=True
            return data
        except Exception:
            # Preserve unreadable original bytes. No automatic rewrite/migration.
            return defaults

    @classmethod
    def save(cls, data: Dict[str, Any]) -> bool:
        temporary=None
        try:
            if cls.PROFILE_FILE.exists():
                existing=json.loads(cls.PROFILE_FILE.read_text(encoding='utf-8'))
                if not isinstance(existing,dict):
                    return False
            stored=copy.deepcopy(data)
            for destination in stored.get('destinations',{}).values():
                key=destination.pop('key','')
                if destination.pop('_credential_unavailable',False) and not key:
                    return False
                destination.pop('key_dpapi',None)
                if key:
                    import win32crypt
                    blob=win32crypt.CryptProtectData(key.encode('utf-8'),'AI-BS stream credential',None,None,None,1)
                    destination['key_dpapi']=base64.b64encode(blob).decode('ascii')
            raw=json.dumps(stored,indent=2,allow_nan=False).encode('utf-8')
            with tempfile.NamedTemporaryFile(mode='wb',dir=cls.PROFILE_FILE.parent,prefix='.stream-profile-',suffix='.tmp',delete=False) as output:
                temporary=Path(output.name)
                output.write(raw);output.flush();os.fsync(output.fileno())
            os.replace(temporary,cls.PROFILE_FILE)
            return True
        except Exception:
            return False
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        return {
            "version": "5.327.0",
            "active_platform": "twitch",
            "destinations": {
                "twitch": {
                    "enabled": False,
                    "url": STREAM_PLATFORM_SPECS["twitch"]["default_url"],
                    "key": "",
                    "vod_track": 2,
                },
                "youtube": {
                    "enabled": False,
                    "url": STREAM_PLATFORM_SPECS["youtube_4k"]["default_url"],
                    "key": "",
                },
                "kick": {
                    "enabled": False,
                    "url": STREAM_PLATFORM_SPECS["kick"]["default_url"],
                    "key": "",
                },
                "tiktok": {
                    "enabled": False,
                    "url": STREAM_PLATFORM_SPECS["tiktok"]["default_url"],
                    "key": "",
                },
                "facebook": {
                    "enabled": False,
                    "url": STREAM_PLATFORM_SPECS["facebook"]["default_url"],
                    "key": "",
                },
                "sovereign_srt": {
                    "enabled": False,
                    "url": STREAM_PLATFORM_SPECS["sovereign_srt"]["default_url"],
                    "key": "",
                },
            },
            "profiles": {
                "twitch_standard": {
                    "platform": "twitch",
                    "resolution": "1920x1080",
                    "codec": "H.264 (NVENC AVC)",
                    "bitrate_kbps": 6000,
                },
                "youtube_4k_av1": {
                    "platform": "youtube_4k",
                    "resolution": "3840x2160",
                    "codec": "AV1 (Dual NVENC 8th Gen)",
                    "bitrate_kbps": 25000,
                },
                "kick_pro": {
                    "platform": "kick",
                    "resolution": "1920x1080",
                    "codec": "H.264 (CBR)",
                    "bitrate_kbps": 8000,
                },
                "tiktok_vertical": {
                    "platform": "tiktok",
                    "resolution": "1080x1920",
                    "codec": "H.264",
                    "bitrate_kbps": 6000,
                },
            },
            "encoder": {
                "codec": "AV1 (Dual NVENC 8th Gen)",
                "resolution": "1920x1080",
                "fps": 60,
                "bitrate_kbps": 6000,
                "rate_control": "CBR",
                "keyframe_sec": 2.0,
                "preset": "P5 (Medium - Balanced)",
                "tuning": "High Quality",
                "bframes": 2,
                "lookahead": True,
                "spatial_aq": True,
                "temporal_aq": True,
                "audio_bitrate_kbps": 160,
                "audio_sample_rate": 48000,
            },
            "network": {
                "stream_delay_sec": 0,
                "auto_reconnect": True,
                "retry_delay_sec": 2,
                "max_retries": 10,
                "low_latency_pacing": True,
            },
            "preview": {
                "studio_mode": False,
                "safe_areas": False,
                "scale_filter": "Lanczos",
                "aspect_preset": "16:9 (1080p 60fps)",
            },
        }

    def get_profiles(self) -> Dict[str, Any]:
        data = self.load()
        if "profiles" in data:
            return data["profiles"]
        return self.get_defaults().get("profiles", {})



# ══════════════════════════════════════════════════════════════════════════
# 4. COMPREHENSIVE STREAM REQUIREMENTS & PING DIAGNOSTICS DIALOG
# ══════════════════════════════════════════════════════════════════════════

class StreamRequirementsDialog(QDialog):
    """Native broadcast configuration, platform requirements, and ingest probes.

    Includes live ping probes, platform compliance checks, hardware NVENC controls, and stream keys.
    """

    profile_applied = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Stehouwer Broadcast Studio — Platform Requirements & Ingest Health")
        self.resize(880, 620)
        self.setStyleSheet("""
            QDialog { background: #070b14; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QTabWidget::pane { border: 1px solid #1e293b; background: #0c1220; border-radius: 6px; }
            QTabBar::tab { background: #0f172a; color: #94a3b8; padding: 8px 16px; font-weight: bold; font-size: 8.5pt; border: 1px solid #1e293b; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #1e293b; color: #00f0ff; border-top: 2px solid #00f0ff; }
            QTabBar::tab:hover { color: #f8fafc; background: #162032; }
            QGroupBox { border: 1px solid #1e293b; border-radius: 6px; margin-top: 12px; padding: 12px; font-weight: bold; font-size: 8pt; color: #38bdf8; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QPushButton { background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 5px; padding: 6px 12px; font-weight: bold; font-size: 8pt; }
            QPushButton:hover { background: #22d3ee; color: #000000; border-color: #22d3ee; }
            QLineEdit, QComboBox, QSpinBox { background: #060911; color: #f8fafc; border: 1px solid #1e293b; border-radius: 4px; padding: 5px 8px; font-size: 8pt; }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #00f0ff; }
            QTableWidget { background: #080d1a; color: #cbd5e1; gridline-color: #1e293b; border: 1px solid #1e293b; border-radius: 4px; font-size: 8pt; }
            QHeaderView::section { background: #0f172a; color: #94a3b8; font-weight: bold; font-size: 7.5pt; border: 1px solid #1e293b; padding: 4px; }
        """)

        self.cfg = StreamProfileManager.load()
        self.ping_thread: Optional[PlatformPingProbeThread] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(14, 14, 14, 14)
        root_lay.setSpacing(10)

        # ── HEADER ROW ──
        hdr = QHBoxLayout()
        icon_lbl = QLabel("📡")
        icon_lbl.setStyleSheet("font-size: 16pt;")
        hdr.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_lbl = QLabel("STEHOUWER PUBLISHING BROADCAST ENGINE")
        title_lbl.setStyleSheet("font-size: 11pt; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;")
        sub_lbl = QLabel("Multi-Platform RTMP/SRT Requirements, Live Ingest Ping Probes & Dual 8th Gen NVENC Profiles")
        sub_lbl.setStyleSheet("font-size: 7.5pt; color: #94a3b8;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        hdr.addLayout(title_box)
        hdr.addStretch()

        self.btn_run_ping = QPushButton("⚡ Run Platform Ping Check")
        self.btn_run_ping.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #06b6d4); color: #ffffff; font-weight: bold; padding: 6px 14px;")
        self.btn_run_ping.clicked.connect(self._start_ping_probe)
        hdr.addWidget(self.btn_run_ping)

        root_lay.addLayout(hdr)

        # ── TAB CONTAINER ──
        self.tabs = QTabWidget()

        # TAB 1: PING & INGEST HEALTH
        self.tab_ping = QWidget()
        self._build_ping_tab()
        self.tabs.addTab(self.tab_ping, "📶 Ingest Ping Checks")

        # TAB 2: PLATFORM REQUIREMENTS & PRESETS
        self.tab_specs = QWidget()
        self._build_specs_tab()
        self.tabs.addTab(self.tab_specs, "📋 Platform Specifications")

        # TAB 3: HARDWARE NVENC ENCODER
        self.tab_encoder = QWidget()
        self._build_encoder_tab()
        self.tabs.addTab(self.tab_encoder, "⚡ NVENC Hardware Encoder")

        # TAB 4: STREAM KEYS & DESTINATIONS
        self.tab_keys = QWidget()
        self._build_keys_tab()
        self.tabs.addTab(self.tab_keys, "🔑 Stream Keys & Multi-RTMP")

        # TAB 5: NETWORK, BUFFER & ANTI-SNIPING
        self.tab_network = QWidget()
        self._build_network_tab()
        self.tabs.addTab(self.tab_network, "🛡️ Network & Anti-Sniping")

        root_lay.addWidget(self.tabs, 1)

        # Aliases for testing & programmatic access
        self.tab_widget = self.tabs
        self.ping_table = self.tbl_ping
        self.platform_table = self.spec_card

        # ── FOOTER ACTION BUTTONS ──
        ft_lay = QHBoxLayout()
        self.lbl_status = QLabel("Settings draft. Service readiness not checked.")
        self.lbl_status.setStyleSheet("color: #10b981; font-size: 8pt; font-weight: bold;")
        ft_lay.addWidget(self.lbl_status)
        ft_lay.addStretch()

        btn_save = QPushButton("💾 Save Configuration")
        btn_save.clicked.connect(self._save_and_apply)
        ft_lay.addWidget(btn_save)

        btn_apply = QPushButton("Use Saved Settings")
        btn_apply.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669); color: #ffffff; font-weight: bold; padding: 6px 16px;")
        btn_apply.clicked.connect(self._apply_and_close)
        ft_lay.addWidget(btn_apply)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        ft_lay.addWidget(btn_close)

        root_lay.addLayout(ft_lay)

    def get_selected_platform_profile(self) -> str:
        """Returns the currently selected streaming platform ID."""
        if hasattr(self, "combo_plat_select"):
            data = self.combo_plat_select.currentData()
            if data:
                return str(data)
            text = self.combo_plat_select.currentText().lower()
            for k in STREAM_PLATFORM_SPECS:
                if k.lower() in text:
                    return k
        return "twitch"

    # ── TAB 1: INGEST PING DIAGNOSTICS ──
    def _build_ping_tab(self) -> None:
        lay = QVBoxLayout(self.tab_ping)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        info_lbl = QLabel(
            "<b>Real-Time Streaming Service Latency & Route Quality:</b><br>"
            "<span style='color: #94a3b8; font-size: 7.5pt;'>Direct TCP socket handshakes to regional RTMP/RTMPS ingests. "
            "Lower latency guarantees buffer-free streaming and instantaneous chat interaction.</span>"
        )
        lay.addWidget(info_lbl)

        # Table of servers
        self.tbl_ping = QTableWidget(len(PING_TEST_TARGETS), 5)
        self.tbl_ping.setHorizontalHeaderLabels(["Server / Ingest Location", "Host Address", "Port", "Ping (Latency)", "Route Quality"])
        self.tbl_ping.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_ping.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_ping.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_ping.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_ping.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_ping.verticalHeader().setVisible(False)

        for row, (name, (host, port, plat_id)) in enumerate(PING_TEST_TARGETS.items()):
            self.tbl_ping.setItem(row, 0, QTableWidgetItem(name))
            self.tbl_ping.setItem(row, 1, QTableWidgetItem(host))
            self.tbl_ping.setItem(row, 2, QTableWidgetItem(str(port)))
            self.tbl_ping.setItem(row, 3, QTableWidgetItem("Untested"))
            self.tbl_ping.setItem(row, 4, QTableWidgetItem("—"))

        lay.addWidget(self.tbl_ping, 1)

        bot_row = QHBoxLayout()
        self.ping_progress = QProgressBar()
        self.ping_progress.setFixedHeight(12)
        self.ping_progress.setTextVisible(False)
        self.ping_progress.setStyleSheet("QProgressBar { background: #080d1a; border: 1px solid #1e293b; border-radius: 4px; } QProgressBar::chunk { background: #00f0ff; border-radius: 3px; }")
        self.ping_progress.setValue(0)
        bot_row.addWidget(self.ping_progress, 1)

        btn_auto_select = QPushButton("🎯 Auto-Select Lowest Latency Ingest")
        btn_auto_select.clicked.connect(self._auto_select_best_ingest)
        bot_row.addWidget(btn_auto_select)
        lay.addLayout(bot_row)

    def _start_ping_probe(self) -> None:
        self.btn_run_ping.setEnabled(False)
        self.btn_run_ping.setText("⏳ Testing Latency...")
        self.ping_progress.setValue(0)
        self.ping_progress.setMaximum(len(PING_TEST_TARGETS))
        self._ping_count = 0

        self.ping_thread = PlatformPingProbeThread(PING_TEST_TARGETS, self)
        self.ping_thread.ping_updated.connect(self._on_ping_result)
        self.ping_thread.probe_finished.connect(self._on_ping_all_done)
        self.ping_thread.start()

    def _on_ping_result(self, name: str, ping_ms: float, status: str, plat_id: str) -> None:
        self._ping_count += 1
        self.ping_progress.setValue(self._ping_count)

        # Locate row in table
        for row in range(self.tbl_ping.rowCount()):
            if self.tbl_ping.item(row, 0).text() == name:
                # Latency item
                lat_str = f"{ping_ms} ms" if ping_ms >= 0 else "Timeout"
                lat_item = QTableWidgetItem(lat_str)
                lat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Quality item
                qual_item = QTableWidgetItem(status)
                qual_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if ping_ms >= 0 and ping_ms < 40:
                    lat_item.setForeground(QColor("#10b981"))
                    qual_item.setForeground(QColor("#10b981"))
                elif ping_ms >= 40 and ping_ms < 85:
                    lat_item.setForeground(QColor("#00f0ff"))
                    qual_item.setForeground(QColor("#00f0ff"))
                elif ping_ms >= 85 and ping_ms < 140:
                    lat_item.setForeground(QColor("#fbbf24"))
                    qual_item.setForeground(QColor("#fbbf24"))
                else:
                    lat_item.setForeground(QColor("#f87171"))
                    qual_item.setForeground(QColor("#f87171"))

                self.tbl_ping.setItem(row, 3, lat_item)
                self.tbl_ping.setItem(row, 4, qual_item)
                break

    def _on_ping_all_done(self, results: dict) -> None:
        self.btn_run_ping.setEnabled(True)
        self.btn_run_ping.setText("⚡ Run Platform Ping Check")
        self.lbl_status.setText(f"Ping scan complete. Tested {len(results)} ingest endpoints.")

    def _auto_select_best_ingest(self) -> None:
        best_name = None
        best_ping = 999999.0
        for row in range(self.tbl_ping.rowCount()):
            lat_item = self.tbl_ping.item(row, 3)
            if lat_item and "ms" in lat_item.text():
                try:
                    val = float(lat_item.text().replace("ms", "").strip())
                    if val > 0 and val < best_ping:
                        best_ping = val
                        best_name = self.tbl_ping.item(row, 0).text()
                except Exception:
                    pass

        if best_name:
            QMessageBox.information(
                self,
                "Optimal Ingest Selected",
                f"Selected optimal streaming ingest:\n\n{best_name} with {best_ping} ms latency.\n"
                "No live target was changed; select a platform profile to edit settings.",
            )
            self.lbl_status.setText(f"Optimal Ingest Selected: {best_name} ({best_ping}ms)")
        else:
            QMessageBox.warning(self, "No Test Results", "Please run '⚡ Run Platform Ping Check' first.")

    # ── TAB 2: PLATFORM SPECIFICATIONS & PROFILES ──
    def _build_specs_tab(self) -> None:
        lay = QVBoxLayout(self.tab_specs)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("<b>Select Platform Profile:</b>"))
        self.combo_plat_select = QComboBox()
        for k, v in STREAM_PLATFORM_SPECS.items():
            self.combo_plat_select.addItem(f"{v['icon']} {v['name']}", k)
        self.combo_plat_select.currentIndexChanged.connect(self._on_platform_selection_changed)
        top_row.addWidget(self.combo_plat_select, 1)

        self.btn_apply_profile = QPushButton("⚡ Apply Platform Profile to Encoder")
        self.btn_apply_profile.setStyleSheet("background: #0284c7; color: #ffffff; font-weight: bold;")
        self.btn_apply_profile.clicked.connect(self._apply_platform_profile_to_encoder)
        top_row.addWidget(self.btn_apply_profile)
        lay.addLayout(top_row)

        # Specifications Details Card
        self.spec_card = QGroupBox("Platform Ingest Standards & Requirements")
        sc_lay = QGridLayout(self.spec_card)
        sc_lay.setSpacing(8)

        self.lbl_spec_res = QLabel()
        self.lbl_spec_bitrate = QLabel()
        self.lbl_spec_rate_ctrl = QLabel()
        self.lbl_spec_keyframe = QLabel()
        self.lbl_spec_codecs = QLabel()
        self.lbl_spec_audio = QLabel()
        self.lbl_spec_notes = QLabel()
        self.lbl_spec_notes.setWordWrap(True)

        sc_lay.addWidget(QLabel("<span style='color: #94a3b8;'>Resolution & Aspect:</span>"), 0, 0)
        sc_lay.addWidget(self.lbl_spec_res, 0, 1)

        sc_lay.addWidget(QLabel("<span style='color: #94a3b8;'>Video Bitrate:</span>"), 1, 0)
        sc_lay.addWidget(self.lbl_spec_bitrate, 1, 1)

        sc_lay.addWidget(QLabel("<span style='color: #94a3b8;'>Rate Control:</span>"), 2, 0)
        sc_lay.addWidget(self.lbl_spec_rate_ctrl, 2, 1)

        sc_lay.addWidget(QLabel("<span style='color: #94a3b8;'>Keyframe (GOP):</span>"), 3, 0)
        sc_lay.addWidget(self.lbl_spec_keyframe, 3, 1)

        sc_lay.addWidget(QLabel("<span style='color: #94a3b8;'>Supported Codecs:</span>"), 4, 0)
        sc_lay.addWidget(self.lbl_spec_codecs, 4, 1)

        sc_lay.addWidget(QLabel("<span style='color: #94a3b8;'>Audio Ingest Spec:</span>"), 5, 0)
        sc_lay.addWidget(self.lbl_spec_audio, 5, 1)

        sc_lay.addWidget(QLabel("<span style='color: #94a3b8;'>Platform Rules:</span>"), 6, 0)
        sc_lay.addWidget(self.lbl_spec_notes, 6, 1)

        lay.addWidget(self.spec_card, 1)

        self._on_platform_selection_changed(0)

    def _on_platform_selection_changed(self, idx: int) -> None:
        plat_key = self.combo_plat_select.currentData()
        spec = STREAM_PLATFORM_SPECS.get(plat_key)
        if not spec:
            return

        self.lbl_spec_res.setText(f"<b>{spec['max_resolution']}</b> ({spec['aspect_ratio']})")
        self.lbl_spec_bitrate.setText(
            f"<b>{spec['recommended_bitrate_kbps']:,} kbps</b> (Max: {spec['max_video_bitrate_kbps']:,} kbps)"
        )
        self.lbl_spec_rate_ctrl.setText(f"<b>{spec['rate_control']}</b>")
        self.lbl_spec_keyframe.setText(f"<b>{spec['keyframe_interval_sec']} seconds</b> (B-Frames: {spec['bframes']})")
        self.lbl_spec_codecs.setText(f"<b>{', '.join(spec['supported_codecs'])}</b>")
        self.lbl_spec_audio.setText(
            f"<b>AAC {spec['audio_samplerate']}</b> @ {spec['max_audio_bitrate_kbps']} kbps max"
        )
        self.lbl_spec_notes.setText(spec["notes"])

    def _apply_platform_profile_to_encoder(self) -> None:
        plat_key = self.combo_plat_select.currentData()
        spec = STREAM_PLATFORM_SPECS.get(plat_key)
        if not spec:
            return

        # Reconfigure Encoder widgets to match
        # 1. Bitrate
        rec_kbps = spec["recommended_bitrate_kbps"]
        self.spin_bitrate.setValue(rec_kbps)

        # 2. Keyframe
        kf = spec["keyframe_interval_sec"]
        self.spin_keyframe.setCurrentIndex(1 if kf == 1 else 2 if kf == 3 else 0)

        # 3. Audio Bitrate
        self.spin_audio_bitrate.setValue(spec["max_audio_bitrate_kbps"])

        # 4. Codec
        if "AV1" in spec["supported_codecs"][0]:
            self.combo_codec.setCurrentText("AV1 (Dual NVENC 8th Gen)")
        elif "HEVC" in spec["supported_codecs"][0]:
            self.combo_codec.setCurrentText("HEVC / H.265")
        else:
            self.combo_codec.setCurrentText("H.264 (NVENC Studio CBR)")

        self.lbl_status.setText(f"Selected profile '{spec['name']}' for the settings draft.")
        QMessageBox.information(
            self,
            "Profile Applied",
            f"Draft encoder settings selected for {spec['name']}:\n\n"
            f"• Bitrate: {rec_kbps} kbps CBR\n"
            f"• Keyframe: {kf}s GOP\n"
            f"• Audio: {spec['max_audio_bitrate_kbps']} kbps AAC 48kHz\n"
            f"• Codec: {self.combo_codec.currentText()}",
        )

    # ── TAB 3: HARDWARE NVENC ENCODER ──
    def _build_encoder_tab(self) -> None:
        lay = QVBoxLayout(self.tab_encoder)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(10)

        # Codec
        grid.addWidget(QLabel("<b>Video Codec:</b>"), 0, 0)
        self.combo_codec = QComboBox()
        self.combo_codec.addItems([
            "AV1 (Dual NVENC 8th Gen)",
            "HEVC / H.265",
            "H.264 (NVENC Studio CBR)",
            "CPU x264 (Ryzen 9 9950X AVX-512)",
        ])
        self.combo_codec.setCurrentText(self.cfg["encoder"].get("codec", self.combo_codec.currentText()))
        grid.addWidget(self.combo_codec, 0, 1)

        # Rate Control
        grid.addWidget(QLabel("<b>Rate Control:</b>"), 0, 2)
        self.combo_rate_ctrl = QComboBox()
        self.combo_rate_ctrl.addItems(["CBR (Constant Bitrate)", "VBR (Variable Bitrate)", "CQP (Constant Quality)"])
        for i in range(self.combo_rate_ctrl.count()):
            if self.combo_rate_ctrl.itemText(i).startswith(str(self.cfg["encoder"].get("rate_control", "CBR"))):
                self.combo_rate_ctrl.setCurrentIndex(i); break
        grid.addWidget(self.combo_rate_ctrl, 0, 3)

        # Bitrate
        grid.addWidget(QLabel("<b>Video Bitrate (kbps):</b>"), 1, 0)
        self.spin_bitrate = QSpinBox()
        self.spin_bitrate.setRange(1000, 80000)
        self.spin_bitrate.setSingleStep(500)
        self.spin_bitrate.setValue(self.cfg["encoder"].get("bitrate_kbps", 6000))
        grid.addWidget(self.spin_bitrate, 1, 1)

        # Keyframe Interval
        grid.addWidget(QLabel("<b>Keyframe Interval (sec):</b>"), 1, 2)
        self.spin_keyframe = QComboBox()
        self.spin_keyframe.addItems(["2.0s (Twitch/YouTube/Kick Standard)", "1.0s (Ultra Low Latency)", "3.0s", "Auto"])
        self.spin_keyframe.setCurrentIndex({1.0:1,3.0:2}.get(self.cfg["encoder"].get("keyframe_sec",2.0),0))
        grid.addWidget(self.spin_keyframe, 1, 3)

        # NVENC Preset P1-P7
        grid.addWidget(QLabel("<b>NVENC Preset:</b>"), 2, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItems([
            "P7: Slowest (Best Quality - Dual NVENC)",
            "P6: Slower (High Quality)",
            "P5: Medium (Balanced - Default)",
            "P4: Fast (Standard)",
            "P3: Faster (Low Latency)",
            "P1: Fastest (Ultra Low Latency)",
        ])
        self.combo_preset.setCurrentIndex(2)  # P5
        self.combo_preset.setCurrentText(self.cfg["encoder"].get("preset", self.combo_preset.currentText()))
        grid.addWidget(self.combo_preset, 2, 1)

        # Tuning
        grid.addWidget(QLabel("<b>Tuning:</b>"), 2, 2)
        self.combo_tuning = QComboBox()
        self.combo_tuning.addItems(["High Quality", "Low Latency", "Ultra Low Latency", "Lossless"])
        self.combo_tuning.setCurrentText(self.cfg["encoder"].get("tuning", self.combo_tuning.currentText()))
        grid.addWidget(self.combo_tuning, 2, 3)

        # Audio Bitrate
        grid.addWidget(QLabel("<b>Audio Bitrate:</b>"), 3, 0)
        self.spin_audio_bitrate = QSpinBox()
        self.spin_audio_bitrate.setRange(96, 320)
        self.spin_audio_bitrate.setSingleStep(32)
        self.spin_audio_bitrate.setValue(self.cfg["encoder"].get("audio_bitrate_kbps", 160))
        grid.addWidget(self.spin_audio_bitrate, 3, 1)

        # Audio Sample Rate
        grid.addWidget(QLabel("<b>Audio Sample Rate:</b>"), 3, 2)
        self.combo_sample_rate = QComboBox()
        self.combo_sample_rate.addItems(["48.0 kHz (Standard Broadcast)", "44.1 kHz"])
        self.combo_sample_rate.setCurrentIndex(1 if self.cfg["encoder"].get("audio_sample_rate")==44100 else 0)
        grid.addWidget(self.combo_sample_rate, 3, 3)

        lay.addLayout(grid)

        # Advanced GPU Optimization Checkboxes
        opt_box = QGroupBox("NVIDIA Ada Lovelace Architectural Optimizations (RTX 4090)")
        ob_lay = QVBoxLayout(opt_box)
        ob_lay.setSpacing(6)

        self.chk_lookahead = QCheckBox("Lookahead (Dynamic B-Frame Insertion & Multi-Frame Scene Analysis)")
        self.chk_lookahead.setChecked(True)
        ob_lay.addWidget(self.chk_lookahead)

        self.chk_spatial_aq = QCheckBox("Spatial Adaptive Quantization (Distributes bits to complex edges and high detail)")
        self.chk_spatial_aq.setChecked(True)
        ob_lay.addWidget(self.chk_spatial_aq)

        self.chk_temporal_aq = QCheckBox("Temporal Adaptive Quantization (Reduces artifacting across moving camera frames)")
        self.chk_temporal_aq.setChecked(True)
        ob_lay.addWidget(self.chk_temporal_aq)

        self.chk_multipass = QCheckBox("Two-Pass Encoding (Quarter Resolution 2-Pass for maximum bitrate efficiency)")
        self.chk_multipass.setChecked(True)
        ob_lay.addWidget(self.chk_multipass)

        lay.addWidget(opt_box)
        lay.addStretch()

    # ── TAB 4: STREAM KEYS & MULTI-RTMP ──
    def _build_keys_tab(self) -> None:
        lay = QVBoxLayout(self.tab_keys)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        lay.addWidget(QLabel("<b>Multi-Destination RTMP Credentials & Keys:</b>"))

        dests = self.cfg.get("destinations", {})

        # Form
        form = QFormLayout()
        form.setSpacing(8)

        # 1. Twitch
        self.chk_en_tw = QCheckBox("Enable Twitch Ingest")
        self.chk_en_tw.setChecked(dests.get("twitch", {}).get("enabled", True))
        self.edit_tw_url = QLineEdit(dests.get("twitch", {}).get("url", STREAM_PLATFORM_SPECS["twitch"]["default_url"]))
        self.edit_tw_key = QLineEdit(dests.get("twitch", {}).get("key", ""))
        self.edit_tw_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_tw_key.setPlaceholderText("live_xxxxxxxxxxxxxxxxxxxx")

        tw_box = QHBoxLayout()
        tw_box.addWidget(self.edit_tw_key, 1)
        btn_tw_show = QPushButton("👁")
        btn_tw_show.setFixedSize(26, 26)
        btn_tw_show.clicked.connect(lambda: self._toggle_echo(self.edit_tw_key, btn_tw_show))
        tw_box.addWidget(btn_tw_show)

        form.addRow("<b>🟣 Twitch:</b>", self.chk_en_tw)
        form.addRow("Twitch Ingest URL:", self.edit_tw_url)
        form.addRow("Twitch Stream Key:", tw_box)

        # 2. YouTube
        self.chk_en_yt = QCheckBox("Enable YouTube Live Ingest")
        self.chk_en_yt.setChecked(dests.get("youtube", {}).get("enabled", True))
        self.edit_yt_url = QLineEdit(dests.get("youtube", {}).get("url", STREAM_PLATFORM_SPECS["youtube_4k"]["default_url"]))
        self.edit_yt_key = QLineEdit(dests.get("youtube", {}).get("key", ""))
        self.edit_yt_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_yt_key.setPlaceholderText("xxxx-xxxx-xxxx-xxxx-xxxx")

        yt_box = QHBoxLayout()
        yt_box.addWidget(self.edit_yt_key, 1)
        btn_yt_show = QPushButton("👁")
        btn_yt_show.setFixedSize(26, 26)
        btn_yt_show.clicked.connect(lambda: self._toggle_echo(self.edit_yt_key, btn_yt_show))
        yt_box.addWidget(btn_yt_show)

        form.addRow("<b>🔴 YouTube Live:</b>", self.chk_en_yt)
        form.addRow("YouTube Ingest URL:", self.edit_yt_url)
        form.addRow("YouTube Stream Key:", yt_box)

        # 3. Kick
        self.chk_en_kick = QCheckBox("Enable Kick Ingest")
        self.chk_en_kick.setChecked(dests.get("kick", {}).get("enabled", False))
        self.edit_kick_url = QLineEdit(dests.get("kick", {}).get("url", STREAM_PLATFORM_SPECS["kick"]["default_url"]))
        self.edit_kick_key = QLineEdit(dests.get("kick", {}).get("key", ""))
        self.edit_kick_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_kick_key.setPlaceholderText("sk_us-east_xxxxxxxx")

        kick_box = QHBoxLayout()
        kick_box.addWidget(self.edit_kick_key, 1)
        btn_kick_show = QPushButton("👁")
        btn_kick_show.setFixedSize(26, 26)
        btn_kick_show.clicked.connect(lambda: self._toggle_echo(self.edit_kick_key, btn_kick_show))
        kick_box.addWidget(btn_kick_show)

        form.addRow("<b>🟢 Kick.com:</b>", self.chk_en_kick)
        form.addRow("Kick Ingest URL:", self.edit_kick_url)
        form.addRow("Kick Stream Key:", kick_box)

        # 4. TikTok
        self.chk_en_tiktok = QCheckBox("Enable TikTok Live (Vertical)")
        self.chk_en_tiktok.setChecked(dests.get("tiktok", {}).get("enabled", False))
        self.edit_tiktok_url = QLineEdit(dests.get("tiktok", {}).get("url", STREAM_PLATFORM_SPECS["tiktok"]["default_url"]))
        self.edit_tiktok_key = QLineEdit(dests.get("tiktok", {}).get("key", ""))
        self.edit_tiktok_key.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("<b>📱 TikTok Live:</b>", self.chk_en_tiktok)
        form.addRow("TikTok Server URL:", self.edit_tiktok_url)
        form.addRow("TikTok Stream Key:", self.edit_tiktok_key)

        # Facebook supports both standard and session-specific RTMPS ingest URLs.
        self.chk_en_fb = QCheckBox("Enable Facebook Live Ingest")
        self.chk_en_fb.setChecked(dests.get("facebook", {}).get("enabled", False))
        self.edit_fb_url = QLineEdit(dests.get("facebook", {}).get("url", STREAM_PLATFORM_SPECS["facebook"]["default_url"]))
        self.edit_fb_key = QLineEdit(dests.get("facebook", {}).get("key", ""))
        self.edit_fb_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Facebook Live:", self.chk_en_fb)
        form.addRow("Facebook Server URL:", self.edit_fb_url)
        form.addRow("Facebook Stream Key:", self.edit_fb_key)

        # 5. Sovereign HLS / SRT Local
        self.chk_en_srt = QCheckBox("Enable Local Sovereign Ingest (Port 8089)")
        self.chk_en_srt.setChecked(dests.get("sovereign_srt", {}).get("enabled", True))
        self.edit_srt_url = QLineEdit(dests.get("sovereign_srt", {}).get("url", STREAM_PLATFORM_SPECS["sovereign_srt"]["default_url"]))

        form.addRow("<b>⚡ Sovereign Link:</b>", self.chk_en_srt)
        form.addRow("Local SRT Ingest URL:", self.edit_srt_url)

        lay.addLayout(form)
        lay.addStretch()

    def _toggle_echo(self, edit: QLineEdit, btn: QPushButton) -> None:
        if edit.echoMode() == QLineEdit.EchoMode.Password:
            edit.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("🔒")
        else:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("👁")

    # ── TAB 5: NETWORK, BUFFER & ANTI-SNIPING ──
    def _build_network_tab(self) -> None:
        lay = QVBoxLayout(self.tab_network)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # Anti-Stream Sniping Delay Buffer
        snip_box = QGroupBox("Anti-Stream Sniping & Broadcast Delay Buffer")
        sb_lay = QVBoxLayout(snip_box)

        d_row = QHBoxLayout()
        d_row.addWidget(QLabel("<b>Stream Delay:</b>"))
        self.combo_delay = QComboBox()
        self.combo_delay.addItems([
            "0 Seconds (No additional delay)",
            "15 Seconds (Competitive Quick Delay)",
            "30 Seconds (Standard Anti-Sniping)",
            "60 Seconds (Tournament Grade)",
            "120 Seconds (High Stakes)",
            "300 Seconds (5 Minutes)",
        ])
        delays=[0,15,30,60,120,300]
        delay=self.cfg['network'].get('stream_delay_sec',0)
        self.combo_delay.setCurrentIndex(delays.index(delay) if delay in delays else 0)
        d_row.addWidget(self.combo_delay, 1)
        sb_lay.addLayout(d_row)

        sb_lay.addWidget(QLabel(
            "<span style='color: #94a3b8; font-size: 7.5pt;'>Saved delay preference; the connected daemon does not enforce this buffer. "
            "Starting with a nonzero delay is held until supported.</span>"
        ))
        lay.addWidget(snip_box)

        # Reconnect Engine
        rec_box = QGroupBox("Network Fault Tolerance & Automatic Reconnect")
        rb_lay = QGridLayout(rec_box)

        self.chk_auto_rec = QCheckBox("Enable Automatic Stream Reconnect")
        self.chk_auto_rec.setChecked(self.cfg['network'].get('auto_reconnect',True))
        rb_lay.addWidget(self.chk_auto_rec, 0, 0, 1, 2)

        rb_lay.addWidget(QLabel("Retry Interval (sec):"), 1, 0)
        self.spin_rec_interval = QSpinBox()
        self.spin_rec_interval.setRange(1, 30)
        self.spin_rec_interval.setValue(self.cfg['network'].get('retry_delay_sec',2))
        rb_lay.addWidget(self.spin_rec_interval, 1, 1)

        rb_lay.addWidget(QLabel("Maximum Retry Attempts:"), 2, 0)
        self.spin_max_retries = QSpinBox()
        self.spin_max_retries.setRange(1, 100)
        self.spin_max_retries.setValue(self.cfg['network'].get('max_retries',10))
        rb_lay.addWidget(self.spin_max_retries, 2, 1)

        lay.addWidget(rec_box)

        # Low-Latency Pacing
        pace_box = QGroupBox("Network Throughput & Congestion Protocol")
        pb_lay = QVBoxLayout(pace_box)

        self.chk_pacing = QCheckBox("Request low-latency pacing (not verified or applied)")
        self.chk_pacing.setChecked(True)
        self.chk_pacing.setChecked(self.cfg["network"].get("low_latency_pacing",False))
        pb_lay.addWidget(self.chk_pacing)

        self.chk_mmcss = QCheckBox("Request MMCSS audio priority (not verified or applied)")
        self.chk_mmcss.setChecked(True)
        self.chk_mmcss.setChecked(self.cfg["network"].get("mmcss_priority_requested",False))
        pb_lay.addWidget(self.chk_mmcss)

        lay.addWidget(pace_box)
        lay.addStretch()

    # ── PERSISTENCE & ACTIONS ──
    def _save_and_apply(self) -> None:
        self.cfg["destinations"]["twitch"]["enabled"] = self.chk_en_tw.isChecked()
        self.cfg["destinations"]["twitch"]["url"] = self.edit_tw_url.text()
        self.cfg["destinations"]["twitch"]["key"] = self.edit_tw_key.text()

        self.cfg["destinations"]["youtube"]["enabled"] = self.chk_en_yt.isChecked()
        self.cfg["destinations"]["youtube"]["url"] = self.edit_yt_url.text()
        self.cfg["destinations"]["youtube"]["key"] = self.edit_yt_key.text()

        self.cfg["destinations"]["kick"]["enabled"] = self.chk_en_kick.isChecked()
        self.cfg["destinations"]["kick"]["url"] = self.edit_kick_url.text()
        self.cfg["destinations"]["kick"]["key"] = self.edit_kick_key.text()

        self.cfg["destinations"]["tiktok"]["enabled"] = self.chk_en_tiktok.isChecked()
        self.cfg["destinations"]["tiktok"]["url"] = self.edit_tiktok_url.text()
        self.cfg["destinations"]["tiktok"]["key"] = self.edit_tiktok_key.text()

        self.cfg["destinations"]["sovereign_srt"]["enabled"] = self.chk_en_srt.isChecked()
        self.cfg["destinations"]["sovereign_srt"]["url"] = self.edit_srt_url.text()

        self.cfg["encoder"]["codec"] = self.combo_codec.currentText()
        self.cfg["encoder"]["bitrate_kbps"] = self.spin_bitrate.value()
        self.cfg["encoder"]["rate_control"] = self.combo_rate_ctrl.currentText()
        self.cfg["encoder"]["preset"] = self.combo_preset.currentText()
        self.cfg["encoder"]["tuning"] = self.combo_tuning.currentText()
        self.cfg["encoder"]["audio_bitrate_kbps"] = self.spin_audio_bitrate.value()

        self.cfg['destinations']['facebook'].update(enabled=self.chk_en_fb.isChecked(),url=self.edit_fb_url.text(),key=self.edit_fb_key.text())
        self.cfg['network'].update(stream_delay_sec=[0,15,30,60,120,300][self.combo_delay.currentIndex()],
            auto_reconnect=self.chk_auto_rec.isChecked(),retry_delay_sec=self.spin_rec_interval.value(),
            max_retries=self.spin_max_retries.value(),low_latency_pacing=self.chk_pacing.isChecked(),
            mmcss_priority_requested=self.chk_mmcss.isChecked())
        self.cfg['encoder']['audio_sample_rate']=44100 if self.combo_sample_rate.currentIndex()==1 else 48000
        self.cfg['encoder']['keyframe_sec']=[2.0,1.0,3.0,2.0][self.spin_keyframe.currentIndex()]
        if not StreamProfileManager.save(self.cfg):
            self.lbl_status.setText('Save failed. Existing profiles preserved; settings not applied.')
            return False
        self.lbl_status.setText('Settings saved locally; not applied to a live stream. Reconnect/pacing preferences require backend support.')
        self.profile_applied.emit(self.cfg)
        return True

    def _apply_and_close(self) -> None:
        if self._save_and_apply():
            self.accept()
