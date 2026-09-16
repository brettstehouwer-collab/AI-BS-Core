"""
AI-BS User Presence, Session Tracking & Dwell-Time Telemetry Engine
Ecosystem: AI-BS Sovereign Automation
Tracks live online users, login timestamps, dwell time, last seen history,
active tools/tabs, and session open/close audit records in local SQLite.
Dynamically synchronizes with all authorized users from Firebase Firestore.
"""

import os
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "user_sessions.db"

BASE_KNOWN_MEMBERS = [
    {
        "email": "brettstehouwer@gmail.com",
        "name": "Brett Stehouwer",
        "role": "Founder & CTO",
        "avatar": "👑",
        "color": "#38bdf8"
    },
    {
        "uid": "sEq0Yw9wRhZBYOsvgR0J5RjKjMJ3",
        "email": "footballstar0325@gmail.com",
        "name": "Brett Stehouwer (Mobile)",
        "role": "Lead Administrator",
        "avatar": "⚡",
        "color": "#38bdf8"
    },
    {
        "uid": "Kv1rQ1ftcybun9PSHDIX90o3KGl2",
        "email": "footballsyat0325@gmail.com",
        "name": "Brett Stehouwer (Mobile Alt)",
        "role": "Lead Administrator",
        "avatar": "⚡",
        "color": "#38bdf8"
    },
    {
        "email": "stehouwer@gmail.com",
        "name": "Stehouwer Executive",
        "role": "Executive Partner",
        "avatar": "🛡️",
        "color": "#38bdf8"
    },
    {
        "uid": "Kv1rQ1ftcybun9PSHDIX90o3KGl2",
        "email": "keith@evolution6media.com",
        "name": "Keith (Evolution 6 Media)",
        "role": "Media & Production Partner",
        "avatar": "🎥",
        "color": "#f59e0b"
    },
    {
        "email": "stehouwerjulie@gmail.com",
        "name": "Julie Stehouwer (Mom)",
        "role": "Executive Partner",
        "avatar": "🌸",
        "color": "#ec4899"
    },
    {
        "email": "julie.a.stehouwer@gmail.com",
        "name": "Julie Stehouwer",
        "role": "Executive Partner",
        "avatar": "🌸",
        "color": "#ec4899"
    },
    {
        "email": "julieannstehouwer@gmail.com",
        "name": "Julie Stehouwer",
        "role": "Executive Partner",
        "avatar": "🌸",
        "color": "#ec4899"
    },
    {
        "email": "juliestehouwer@gmail.com",
        "name": "Julie Stehouwer",
        "role": "Executive Partner",
        "avatar": "🌸",
        "color": "#ec4899"
    },
    {
        "email": "stehouwer.julie@gmail.com",
        "name": "Julie Stehouwer",
        "role": "Executive Partner",
        "avatar": "🌸",
        "color": "#ec4899"
    },
    {
        "email": "theseandaley@gmail.com",
        "name": "Sean Daley",
        "role": "Production & Creative Partner",
        "avatar": "🎬",
        "color": "#a855f7"
    },
    {
        "email": "rottierannajoy@gmail.com",
        "name": "Anna Joy Rottier",
        "role": "Creative Partner",
        "avatar": "✨",
        "color": "#f59e0b"
    },
    {
        "email": "brett@stehouwerpublishing.com",
        "name": "Brett Stehouwer",
        "role": "Founder & CEO",
        "avatar": "👑",
        "color": "#38bdf8"
    },
    {
        "email": "sean@stehouwerpublishing.com",
        "name": "Sean Stehouwer",
        "role": "Chief Strategy Officer",
        "avatar": "🎬",
        "color": "#a855f7"
    },
    {
        "email": "julie@stehouwerpublishing.com",
        "name": "Julie Stehouwer",
        "role": "Operations Director",
        "avatar": "🌸",
        "color": "#ec4899"
    }
]


class UserSessionTelemetryEngine:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes user session tracking, registered user roster, and event audit tables."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS registered_users (
                    user_email TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    user_avatar TEXT DEFAULT '👤',
                    user_role TEXT DEFAULT 'Authorized Member',
                    user_color TEXT DEFAULT '#38bdf8',
                    is_authorized INTEGER DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    user_avatar TEXT DEFAULT '👤',
                    user_role TEXT DEFAULT 'Operator',
                    started_at INTEGER NOT NULL,
                    last_heartbeat INTEGER NOT NULL,
                    ended_at INTEGER,
                    duration_seconds REAL DEFAULT 0.0,
                    current_tab TEXT DEFAULT 'dashboard',
                    activity_label TEXT DEFAULT 'Browsing Workspace',
                    client_platform TEXT DEFAULT 'Desktop Windows',
                    is_online INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_email ON user_sessions(user_email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_heartbeat ON user_sessions(last_heartbeat)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON user_sessions(status)")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    tab_key TEXT NOT NULL,
                    activity TEXT,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES user_sessions(session_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON session_activity_events(session_id)")

            # Seed base members into registered_users if not present
            now_iso = datetime.now(timezone.utc).isoformat()
            for m in BASE_KNOWN_MEMBERS:
                conn.execute("""
                    INSERT OR IGNORE INTO registered_users (user_email, user_name, user_avatar, user_role, user_color, is_authorized, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, (m["email"].lower(), m["name"], m["avatar"], m["role"], m["color"], now_iso))

            conn.commit()

    def sync_authorized_users(self, users_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingests and synchronizes all authorized users saved in Firebase Firestore into SQLite.
        Accepts list of: [{ email, displayName, photoURL, role, ... }]
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        synced_count = 0

        with self._get_conn() as conn:
            for u in users_list:
                raw_email = u.get("email") or u.get("user_email")
                if not raw_email:
                    continue
                clean_email = raw_email.lower().strip()
                name = u.get("displayName") or u.get("user_name") or u.get("name") or clean_email.split("@")[0].capitalize()
                avatar = u.get("photoURL") or u.get("user_avatar") or u.get("avatar") or "👤"
                role = u.get("role") or u.get("user_role") or "Authorized Partner"
                color = u.get("color") or "#38bdf8"

                # Check if this matches a known member for high-quality badge/role
                known = next((m for m in BASE_KNOWN_MEMBERS if m["email"].lower() == clean_email), None)
                if known:
                    name = known["name"]
                    role = known["role"]
                    avatar = known["avatar"]
                    color = known["color"]

                conn.execute("""
                    INSERT INTO registered_users (user_email, user_name, user_avatar, user_role, user_color, is_authorized, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(user_email) DO UPDATE SET
                        user_name = excluded.user_name,
                        user_avatar = excluded.user_avatar,
                        user_role = excluded.user_role,
                        updated_at = excluded.updated_at
                """, (clean_email, name, avatar, role, color, now_iso))
                synced_count += 1
            conn.commit()

        return {"status": "success", "synced_users_count": synced_count}

    def record_heartbeat(
        self,
        session_id: str,
        user_email: str,
        user_name: Optional[str] = None,
        user_avatar: Optional[str] = None,
        user_role: Optional[str] = None,
        current_tab: str = "dashboard",
        activity_label: Optional[str] = None,
        client_platform: str = "Desktop Windows",
        dwell_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Records or updates a live user session heartbeat.
        Auto-computes duration and transitions status.
        Dynamically registers the user in the SQLite roster if new.
        """
        now_ms = int(time.time() * 1000)
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_email = (user_email or "anonymous@stehouwer.live").lower().strip()

        # Resolve friendly name/avatar if not provided
        known = next((m for m in BASE_KNOWN_MEMBERS if m["email"].lower() == clean_email), None)
        if known:
            user_name = user_name or known["name"]
            user_avatar = user_avatar or known["avatar"]
            user_role = user_role or known["role"]
            user_color = known["color"]
        else:
            user_name = user_name or clean_email.split("@")[0].capitalize()
            user_avatar = user_avatar or "👤"
            user_role = user_role or "Authorized Member"
            user_color = "#38bdf8"

        if not activity_label:
            activity_label = f"Working in {current_tab.replace('_', ' ').title()}"

        with self._get_conn() as conn:
            # Auto-register/update in registered_users roster
            conn.execute("""
                INSERT INTO registered_users (user_email, user_name, user_avatar, user_role, user_color, is_authorized, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(user_email) DO UPDATE SET
                    user_name = excluded.user_name,
                    user_avatar = excluded.user_avatar,
                    user_role = excluded.user_role,
                    updated_at = excluded.updated_at
            """, (clean_email, user_name, user_avatar, user_role, user_color, now_iso))

            cursor = conn.cursor()
            cursor.execute("SELECT started_at, current_tab FROM user_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()

            if row:
                started_at = row["started_at"]
                old_tab = row["current_tab"]
                calc_duration = max(0.0, (now_ms - started_at) / 1000.0)
                if dwell_seconds is not None and dwell_seconds > calc_duration:
                    calc_duration = dwell_seconds

                cursor.execute("""
                    UPDATE user_sessions SET
                        last_heartbeat = ?,
                        duration_seconds = ?,
                        current_tab = ?,
                        activity_label = ?,
                        client_platform = ?,
                        is_online = 1,
                        status = 'ACTIVE',
                        updated_at = ?
                    WHERE session_id = ?
                """, (now_ms, calc_duration, current_tab, activity_label, client_platform, now_iso, session_id))

                # Log activity transition event if tab changed
                if old_tab != current_tab:
                    cursor.execute("""
                        INSERT INTO session_activity_events (session_id, user_email, tab_key, activity, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (session_id, clean_email, current_tab, activity_label, now_ms))
            else:
                calc_duration = dwell_seconds if dwell_seconds else 0.0
                cursor.execute("""
                    INSERT INTO user_sessions (
                        session_id, user_email, user_name, user_avatar, user_role,
                        started_at, last_heartbeat, duration_seconds, current_tab,
                        activity_label, client_platform, is_online, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'ACTIVE', ?, ?)
                """, (
                    session_id, clean_email, user_name, user_avatar, user_role,
                    now_ms, now_ms, calc_duration, current_tab,
                    activity_label, client_platform, now_iso, now_iso
                ))
                cursor.execute("""
                    INSERT INTO session_activity_events (session_id, user_email, tab_key, activity, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, clean_email, current_tab, activity_label, now_ms))

            conn.commit()

        return {
            "status": "success",
            "session_id": session_id,
            "user_email": clean_email,
            "duration_seconds": calc_duration,
            "timestamp": now_ms
        }

    def close_session(
        self,
        session_id: str,
        exit_tab: Optional[str] = None,
        duration_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Marks a session as CLOSED upon unload or explicit logout."""
        now_ms = int(time.time() * 1000)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT started_at FROM user_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                started_at = row["started_at"]
                calc_duration = max(0.0, (now_ms - started_at) / 1000.0)
                if duration_seconds is not None:
                    calc_duration = max(calc_duration, duration_seconds)

                cursor.execute("""
                    UPDATE user_sessions SET
                        ended_at = ?,
                        last_heartbeat = ?,
                        duration_seconds = ?,
                        is_online = 0,
                        status = 'CLOSED',
                        updated_at = ?
                    WHERE session_id = ?
                """, (now_ms, now_ms, calc_duration, now_iso, session_id))
                conn.commit()
                return {"status": "success", "session_id": session_id, "duration_seconds": calc_duration}

        return {"status": "not_found", "session_id": session_id}

    def prune_stale_sessions(self, timeout_seconds: int = 65):
        """
        Finds active sessions whose last heartbeat is older than timeout_seconds
        and transitions them to TIMED_OUT / CLOSED.
        """
        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - (timeout_seconds * 1000)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_conn() as conn:
            conn.execute("""
                UPDATE user_sessions SET
                    is_online = 0,
                    status = 'TIMED_OUT',
                    ended_at = last_heartbeat,
                    duration_seconds = MAX(0.0, (last_heartbeat - started_at) / 1000.0),
                    updated_at = ?
                WHERE is_online = 1 AND last_heartbeat < ?
            """, (now_iso, cutoff_ms))
            conn.commit()

    def get_summary(self) -> Dict[str, Any]:
        """
        Generates unified real-time telemetry summary:
        1. Live Online Users (active now across all registered and connecting users)
        2. Who Was On Last (last seen for all known and registered authorized members)
        3. Recent Sessions History Ledger (open & close times, total duration)
        4. User Aggregated Time Spent
        """
        self.prune_stale_sessions(timeout_seconds=65)
        now_ms = int(time.time() * 1000)

        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 1. Live Users
            cursor.execute("""
                SELECT * FROM user_sessions 
                WHERE is_online = 1
                ORDER BY started_at DESC
            """)
            live_rows = [dict(r) for r in cursor.fetchall()]
            for u in live_rows:
                u["live_duration_seconds"] = max(0.0, (now_ms - u["started_at"]) / 1000.0)
                u["seconds_since_heartbeat"] = round((now_ms - u["last_heartbeat"]) / 1000.0, 1)

            # 2. Recent Sessions Ledger (Chronological Audit)
            cursor.execute("""
                SELECT * FROM user_sessions
                ORDER BY started_at DESC
                LIMIT 100
            """)
            recent_sessions = [dict(r) for r in cursor.fetchall()]

            # 3. Latest session per user
            cursor.execute("""
                SELECT * FROM (
                    SELECT *, ROW_NUMBER() OVER(PARTITION BY user_email ORDER BY started_at DESC) as rn
                    FROM user_sessions
                ) WHERE rn = 1
                ORDER BY last_heartbeat DESC
            """)
            last_seen_db = {r["user_email"].lower(): dict(r) for r in cursor.fetchall()}

            # 4. Fetch all registered authorized users (dynamic roster from Firebase & base list)
            cursor.execute("SELECT * FROM registered_users ORDER BY user_name ASC")
            all_registered = [dict(r) for r in cursor.fetchall()]

            last_seen_users = []
            seen_emails = set()

            for reg in all_registered:
                email = reg["user_email"].lower()
                seen_emails.add(email)

                if email in last_seen_db:
                    rec = last_seen_db[email]
                    rec["seconds_ago"] = max(0, round((now_ms - rec["last_heartbeat"]) / 1000.0))
                    rec["user_role"] = reg["user_role"] or rec.get("user_role")
                    rec["user_avatar"] = reg["user_avatar"] or rec.get("user_avatar")
                    rec["user_name"] = reg["user_name"] or rec.get("user_name")
                    rec["color"] = reg["user_color"] or "#38bdf8"
                    last_seen_users.append(rec)
                else:
                    last_seen_users.append({
                        "user_email": email,
                        "user_name": reg["user_name"],
                        "user_avatar": reg["user_avatar"],
                        "user_role": reg["user_role"],
                        "color": reg["user_color"],
                        "is_online": 0,
                        "status": "OFFLINE",
                        "started_at": None,
                        "last_heartbeat": None,
                        "ended_at": None,
                        "duration_seconds": 0.0,
                        "current_tab": "Offline",
                        "activity_label": "No sessions logged yet today",
                        "seconds_ago": None
                    })

            # Catch any session records whose email wasn't in registered_users
            for email, rec in last_seen_db.items():
                if email not in seen_emails:
                    rec["seconds_ago"] = max(0, round((now_ms - rec["last_heartbeat"]) / 1000.0))
                    last_seen_users.append(rec)

            # Sort: online users first, then by most recent heartbeat
            last_seen_users.sort(key=lambda x: (
                1 if x.get("is_online") else 0,
                x.get("last_heartbeat") or 0
            ), reverse=True)

            # 5. Aggregates: Total duration per user
            cursor.execute("""
                SELECT 
                    user_email, 
                    user_name, 
                    user_avatar, 
                    COUNT(session_id) as session_count,
                    SUM(duration_seconds) as total_seconds
                FROM user_sessions
                GROUP BY user_email
                ORDER BY total_seconds DESC
            """)
            aggregates = [dict(r) for r in cursor.fetchall()]

            # Overall system totals
            cursor.execute("SELECT COUNT(*) as total_sessions, SUM(duration_seconds) as total_duration FROM user_sessions")
            totals_row = cursor.fetchone()
            total_sessions = totals_row["total_sessions"] if totals_row else 0
            total_duration = totals_row["total_duration"] if totals_row and totals_row["total_duration"] else 0.0

        return {
            "status": "success",
            "server_time": now_ms,
            "total_active_now": len(live_rows),
            "total_registered_users": len(last_seen_users),
            "total_sessions_recorded": total_sessions,
            "total_dwell_time_seconds": total_duration,
            "live_users": live_rows,
            "last_seen_users": last_seen_users,
            "recent_sessions": recent_sessions,
            "user_aggregates": aggregates
        }


# Singleton instance
user_telemetry_engine = UserSessionTelemetryEngine()
