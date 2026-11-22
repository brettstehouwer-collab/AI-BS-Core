#!/usr/bin/env python3
"""Measured GPU/host observations and explicit fan-control acknowledgements.

Imports and reads never initialize a database. Legacy thermal rows are retained
as unverified; new hardware observations have separate, additive provenance.
"""
import ctypes
import json
import logging
import math
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aibs_gpu_telemetry")
_db_path = Path(__file__).resolve().parent.parent / "aibs_master.db"


class SovereignGpuTelemetry:
    GPU_FIELDS = ("gpu_name", "core_temp_c", "fan_speed_pct", "memory_used_mb",
                  "memory_total_mb", "power_usage_w", "gpu_util_pct",
                  "core_clock_mhz", "memory_clock_mhz")
    HOST_FIELDS = ("cpu_util_pct", "ram_used_gb", "ram_total_gb")

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or _db_path)

    def _get_db_connection(self, write=False):
        if not write and not self.db_path.is_file():
            return None
        conn = sqlite3.connect(str(self.db_path) if write else self.db_path.resolve().as_uri() + "?mode=ro",
                               uri=not write, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite_vault(self) -> bool:
        """Initialize only the additive measured-observation table on a real write."""
        conn = self._get_db_connection(write=True)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS gpu_thermal_observations_v1(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL, sample_json TEXT NOT NULL)""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gpu_thermal_timestamp ON gpu_thermal_observations_v1(timestamp);")
            conn.commit()
            return True
        finally:
            conn.close()

    def query_nvml_telemetry(self) -> Dict[str, Any]:
        """Keep independent failed/unsupported readings null, never substitute sensors."""
        fields = self.GPU_FIELDS + self.HOST_FIELDS
        data = dict.fromkeys(fields)
        data.update(timestamp=time.strftime("%Y-%m-%d %H:%M:%S"), nvml_online=False,
                    field_status=dict.fromkeys(fields, "unavailable"),
                    verification="unavailable", status_flag="UNAVAILABLE",
                    fan_enforcement_verified=False, default_fan_target_pct=100,
                    history_recorded=False)
        nvml = None
        initialized = False
        device_available = False

        def measured(name, value):
            data[name] = value
            data["field_status"][name] = "measured"

        try:
            nvml = ctypes.CDLL("nvml.dll")
            initialized = nvml.nvmlInit_v2() == 0
            handle = ctypes.c_void_p()
            if initialized and nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) == 0:
                device_available = True
                try:
                    buffer = ctypes.create_string_buffer(64)
                    if nvml.nvmlDeviceGetName(handle, buffer, 64) == 0 and buffer.value:
                        measured("gpu_name", buffer.value.decode("utf-8", errors="replace"))
                except Exception:
                    pass

                def number(name, method, *args, scale=1, maximum=None):
                    try:
                        output = ctypes.c_uint()
                        if getattr(nvml, method)(handle, *args, ctypes.byref(output)) == 0:
                            value = output.value / scale if scale != 1 else output.value
                            if maximum is None or value <= maximum:
                                measured(name, round(value, 1) if scale != 1 else value)
                    except Exception:
                        pass

                number("core_temp_c", "nvmlDeviceGetTemperature", 0, maximum=150)
                number("fan_speed_pct", "nvmlDeviceGetFanSpeed", maximum=100)
                number("power_usage_w", "nvmlDeviceGetPowerUsage", scale=1000)
                try:
                    class Memory(ctypes.Structure):
                        _fields_ = [("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong),
                                    ("used", ctypes.c_ulonglong)]
                    memory = Memory()
                    if (nvml.nvmlDeviceGetMemoryInfo(handle, ctypes.byref(memory)) == 0
                            and memory.total > 0 and memory.used <= memory.total):
                        measured("memory_total_mb", int(memory.total // (1024 * 1024)))
                        measured("memory_used_mb", int(memory.used // (1024 * 1024)))
                except Exception:
                    pass
                try:
                    class Utilization(ctypes.Structure):
                        _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]
                    utilization = Utilization()
                    if nvml.nvmlDeviceGetUtilizationRates(handle, ctypes.byref(utilization)) == 0 and utilization.gpu <= 100:
                        measured("gpu_util_pct", utilization.gpu)
                except Exception:
                    pass
        except Exception:
            logger.warning("NVML hardware evidence is unavailable.")
        finally:
            if initialized:
                try:
                    nvml.nvmlShutdown()
                except Exception:
                    logger.warning("NVML shutdown acknowledgement is unavailable.")

        gpu_measured = [key for key in self.GPU_FIELDS[1:] if data["field_status"][key] == "measured"]
        data["nvml_online"] = device_available and bool(gpu_measured)
        if data["nvml_online"]:
            data["verification"] = "measured" if all(data["field_status"][key] == "measured" for key in self.GPU_FIELDS[:7]) else "partial"
        temperature = data["core_temp_c"]
        if temperature is not None:
            data["status_flag"] = "CRITICAL_WARM" if temperature >= 75 else ("WARM" if temperature >= 60 else "MEASURED_NORMAL")

        try:
            import psutil
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                if isinstance(cpu, (int, float)) and not isinstance(cpu, bool) and math.isfinite(cpu) and 0 <= cpu <= 100:
                    measured("cpu_util_pct", round(cpu, 1))
            except Exception:
                pass
            try:
                memory = psutil.virtual_memory()
                if 0 <= memory.used <= memory.total and memory.total > 0:
                    measured("ram_used_gb", round(memory.used / (1024 ** 3), 1))
                    measured("ram_total_gb", round(memory.total / (1024 ** 3), 1))
            except Exception:
                pass
        except Exception:
            pass
        if data["nvml_online"]:
            data["history_recorded"] = self.log_telemetry(data)
        return data

    def log_telemetry(self, data: Dict[str, Any]) -> bool:
        """Only admit observations with explicit successful GPU field evidence."""
        status = data.get("field_status", {})
        measured_fields = [key for key in self.GPU_FIELDS[1:] if status.get(key) == "measured"
                           and type(data.get(key)) in (int, float) and math.isfinite(data[key])]
        if data.get("nvml_online") is not True or not measured_fields:
            return False
        conn = None
        try:
            payload = json.dumps(data, allow_nan=False, separators=(",", ":"))
            self._init_sqlite_vault()
            conn = self._get_db_connection(write=True)
            conn.execute("INSERT INTO gpu_thermal_observations_v1(timestamp,sample_json) VALUES(?,?)",
                         (data["timestamp"], payload))
            conn.commit()
            return True
        except Exception:
            logger.warning("GPU observation persistence is unavailable.")
            return False
        finally:
            if conn is not None:
                conn.close()

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return measured history and clearly unverified legacy rows without repair."""
        if type(limit) is not int or not 1 <= limit <= 500:
            return []
        conn = None
        try:
            conn = self._get_db_connection()
            if conn is None:
                return []
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            rows = []
            if "gpu_thermal_observations_v1" in tables:
                for row in conn.execute("SELECT * FROM gpu_thermal_observations_v1 ORDER BY id DESC LIMIT ?", (limit,)):
                    try:
                        data = json.loads(row["sample_json"])
                        if not isinstance(data, dict) or data.get("nvml_online") is not True or not isinstance(data.get("field_status"), dict):
                            continue
                        data.update(id=row["id"], verification="recorded_measurement", live_verified=False,
                                    history_source="gpu_thermal_observations_v1", history_recorded=True)
                        rows.append(data)
                    except (TypeError, ValueError):
                        continue
            if "gpu_thermal_logs" in tables:
                for row in conn.execute("SELECT * FROM gpu_thermal_logs ORDER BY id DESC LIMIT ?", (limit,)):
                    data = dict(row)
                    data.update(verification="legacy_unverified", live_verified=False, nvml_online=False,
                                history_source="gpu_thermal_logs",
                                field_status=dict.fromkeys(self.GPU_FIELDS + self.HOST_FIELDS, "unavailable"))
                    rows.append(data)
            rows.sort(key=lambda row: str(row.get("timestamp", "")), reverse=True)
            return rows[:limit]
        except Exception:
            logger.warning("GPU observation history is unavailable.")
            return []
        finally:
            if conn is not None:
                conn.close()

    def set_fan_speed(self, speed: int = 100, auto: bool = False) -> Dict[str, Any]:
        """Request a driver policy; acceptance alone is never verified enforcement."""
        result = dict(success=False, target_speed=speed, auto_mode=auto, message="",
                      enforcement_verified=False, observed_speed_pct=None,
                      enforcement_scope="unverified", default_fan_target_pct=100)
        if (type(speed) is not int or type(auto) is not bool or not 0 <= speed <= 100
                or (not auto and speed < 30)):
            result["message"] = "Invalid fan request; use an integer 30–100 or an automatic driver policy."
            return result
        nvml = None
        initialized = False
        try:
            nvml = ctypes.CDLL("nvml.dll")
            initialized = nvml.nvmlInit_v2() == 0
            if not initialized:
                result["message"] = "NVML initialization unavailable."
                return result
            handle = ctypes.c_void_p()
            if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) != 0:
                result["message"] = "GPU device is unavailable."
                return result
            count = ctypes.c_uint(1)
            count_verified = (hasattr(nvml, "nvmlDeviceGetNumFans")
                              and nvml.nvmlDeviceGetNumFans(handle, ctypes.byref(count)) == 0
                              and 1 <= count.value <= 64)
            fan_count = count.value if count_verified else 1
            method = getattr(nvml, "nvmlDeviceDefaultFanSpeed" if auto else "nvmlDeviceSetFanSpeed_v2", None)
            accepted = 0
            if method is not None:
                for fan in range(fan_count):
                    code = method(handle, fan) if auto else method(handle, fan, speed)
                    accepted += int(code == 0)
            result.update(success=accepted == fan_count, requested_fans=fan_count, accepted_fans=accepted)
            if not auto and result["success"]:
                observed = ctypes.c_uint()
                if hasattr(nvml, "nvmlDeviceGetFanSpeed") and nvml.nvmlDeviceGetFanSpeed(handle, ctypes.byref(observed)) == 0 and observed.value <= 100:
                    result["observed_speed_pct"] = observed.value
                    # Aggregate readback is insufficient evidence for multiple fans.
                    result["enforcement_verified"] = count_verified and fan_count == 1 and observed.value == speed
                    if result["enforcement_verified"]:
                        result["enforcement_scope"] = "single_fan_readback_at_request"
            result["message"] = ("Driver request accepted; policy enforcement requires separate evidence."
                                 if result["success"] else "Driver did not accept the complete fan request.")
            return result
        except Exception:
            result["message"] = "Fan control evidence is unavailable."
            return result
        finally:
            if initialized:
                try:
                    nvml.nvmlShutdown()
                except Exception:
                    logger.warning("NVML shutdown acknowledgement is unavailable.")


# Construction has no database, device, fan-control or background side effects.
gpu_telemetry_engine = SovereignGpuTelemetry()
