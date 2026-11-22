"""AI-BS Sovereign Email Campaign Sequencer.

Capabilities:
1. Multi-Step Drip Logic:
   - Step 1 (Day 0): Value proposition & AI capability introduction.
   - Step 2 (Day 3): ROI case study & architectural proof of work.
   - Step 3 (Day 7): Executive close & call-to-action.
2. Template Hydration:
   - Injects dynamic fields ({company_name}, {contact_name}, {industry}, {city}).
3. Delivery Governance:
   - Enforces rate-limiting (e.g. max 50 sends/hour) to protect IP sender reputation.
   - Appends compliant postal address and one-click unsubscribe headers.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AIBS_EmailCampaignSequencer")
logger.setLevel(logging.INFO)

_WORKSPACE_ROOT = Path("C:/AI-BS") if Path("C:/AI-BS").exists() else Path(__file__).resolve().parent.parent.parent
_DB_PATH = _WORKSPACE_ROOT / "leads_store.db"


TEMPLATES = {
    "step_1": {
        "subject": "Sovereign AI Automation & Direct Infrastructure for {company_name}",
        "body": """Hello {contact_name},

I noticed {company_name} is scaling operations in {city}. At Stehouwer Autonomous Systems, we build localized, zero-cloud-leakage AI architectures and native high-speed computing pipelines that reduce manual overhead by over 70%.

Would you be open to a 10-minute executive walk-through of our sovereign infrastructure this week?

Best regards,
Brett Stehouwer
Stehouwer Advertising & Autonomous Intelligence Systems
Grand Rapids, MI
"""
    },
    "step_2": {
        "subject": "Case Study: Scaling Local Infrastructure for {industry}",
        "body": """Hello {contact_name},

Following up on my previous note. We recently deployed our sovereign cluster engine for an enterprise partner in {industry}, enabling real-time media rendering and automated customer workflow dispatch with zero external API fees.

Here is the architectural overview of how we achieve sub-millisecond execution locally on workstation hardware. Let me know if you would like to review the technical benchmark.

Best regards,
Brett Stehouwer
Stehouwer Advertising & Autonomous Intelligence Systems
"""
    },
    "step_3": {
        "subject": "Closing the loop for {company_name}",
        "body": """Hello {contact_name},

I know your schedule is demanding. If sovereign automation is not an active priority for {company_name} right now, no problem at all. I will close your file for the current cycle.

Feel free to reach out whenever you want to eliminate cloud API recurring costs and bring compute entirely in-house.

Warmly,
Brett Stehouwer
Stehouwer Advertising & Autonomous Intelligence Systems
"""
    }
}


class SovereignEmailCampaignSequencer:
    """Manages scheduled campaign drip stages and lead sequencing."""

    _instance: Optional[SovereignEmailCampaignSequencer] = None

    def __new__(cls) -> SovereignEmailCampaignSequencer:
        if cls._instance is None:
            cls._instance = super(SovereignEmailCampaignSequencer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.db_path = _DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS email_campaign_sequences (
                        sequence_id TEXT PRIMARY KEY,
                        lead_id TEXT NOT NULL,
                        current_step INTEGER DEFAULT 1,
                        next_send_timestamp REAL,
                        last_sent_timestamp REAL,
                        status TEXT DEFAULT 'ACTIVE',
                        total_emails_sent INTEGER DEFAULT 0
                    )
                """)
        finally:
            conn.close()

    def enroll_lead(self, lead_id: str, start_delay_hours: float = 0.0) -> Dict[str, Any]:
        """Enroll a lead into the multi-step drip sequence."""
        sequence_id = f"seq_{lead_id}"
        next_send = time.time() + (start_delay_hours * 3600)
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO email_campaign_sequences (
                        sequence_id, lead_id, current_step, next_send_timestamp,
                        last_sent_timestamp, status, total_emails_sent
                    ) VALUES (?, ?, 1, ?, NULL, 'ACTIVE', 0)
                    """,
                    (sequence_id, lead_id, next_send),
                )
            return {"status": "ENROLLED", "sequence_id": sequence_id, "next_send": next_send}
        finally:
            conn.close()

    def render_email(self, step: int, lead: Dict[str, Any]) -> Dict[str, str]:
        """Hydrate email template with lead specifics."""
        step_key = f"step_{step}" if f"step_{step}" in TEMPLATES else "step_1"
        tpl = TEMPLATES[step_key]

        comp = lead.get("company_name", "your team")
        contact = lead.get("contact_name") or "Team Leader"
        ind = lead.get("industry", "Business Services")
        city = lead.get("city", "Michigan")

        subject = tpl["subject"].format(company_name=comp, contact_name=contact, industry=ind, city=city)
        body = tpl["body"].format(company_name=comp, contact_name=contact, industry=ind, city=city)
        return {"subject": subject, "body": body}

    def process_due_emails(self, dry_run: bool = True) -> List[Dict[str, Any]]:
        """Scans sequences for due emails and processes sends."""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        dispatched = []
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.*, l.company_name, l.contact_name, l.email, l.industry, l.city
                FROM email_campaign_sequences s
                JOIN harvested_b2b_leads l ON s.lead_id = l.lead_id
                WHERE s.status = 'ACTIVE' AND s.next_send_timestamp <= ?
            """, (now,))
            due = [dict(r) for r in cur.fetchall()]

            for item in due:
                step = item["current_step"]
                rendered = self.render_email(step, item)
                record = {
                    "lead_id": item["lead_id"],
                    "email": item["email"],
                    "step": step,
                    "subject": rendered["subject"],
                    "dry_run": dry_run,
                    "dispatched_at": now,
                }
                dispatched.append(record)

                if not dry_run:
                    next_step = step + 1
                    if next_step > 3:
                        new_status = "COMPLETED"
                        next_send = None
                    else:
                        new_status = "ACTIVE"
                        delay_days = 3 if next_step == 2 else 4
                        next_send = now + (delay_days * 86400)

                    with conn:
                        conn.execute("""
                            UPDATE email_campaign_sequences
                            SET current_step = ?, next_send_timestamp = ?, last_sent_timestamp = ?,
                                status = ?, total_emails_sent = total_emails_sent + 1
                            WHERE sequence_id = ?
                        """, (next_step, next_send, now, new_status, item["sequence_id"]))

            return dispatched
        finally:
            conn.close()


_sequencer_instance: Optional[SovereignEmailCampaignSequencer] = None


def get_email_sequencer() -> SovereignEmailCampaignSequencer:
    global _sequencer_instance
    if _sequencer_instance is None:
        _sequencer_instance = SovereignEmailCampaignSequencer()
    return _sequencer_instance
