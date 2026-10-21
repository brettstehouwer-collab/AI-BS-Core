import ast
from pathlib import Path

# Verify that our code block parses cleanly with Python AST
sample_code = '''
import os
import sys
import json
import time
import sqlite3
import re
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Set

BASE_DIR = Path(r"C:\\AI-BS")
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"
SECONDARY_DB_PATH = Path(r"C:\\Recreational-Debut\\saved_data\\rec_debut.db")
ROSTER_CSV_PATH = Path(r"C:\\Users\\footb\\OneDrive\\Desktop\\TextBee_RecDebut_Class_of_2027.csv")

DENNIS_PHONE = "+1-616-291-5227"
DENNIS_EMAIL = "dbell002@sbcglobal.net"

def dispatch_sms_message(recipient_phone: str, message_text: str, caller_id_name: str = "RecDebut Lead Sentinel") -> Dict[str, Any]:
    digits = "".join(filter(str.isdigit, recipient_phone))
    if len(digits) < 10:
        return {"success": False, "error": f"Invalid phone: {recipient_phone}"}
    e164_phone = f"+1{digits[-10:]}"

    textbee_key = os.environ.get("TEXTBEE_API_KEY", "txb_rAZOZNMuTEKtlxQ30hfcJd05dL2KlVRu").strip()
    textbee_device = os.environ.get("TEXTBEE_DEVICE_ID", "6ad7b28560b1138230badd0a").strip()
    if textbee_key and textbee_device:
        try:
            tb_endpoint = "https://api.textbee.dev/api/v1/gateway/devices/" + textbee_device + "/send-sms"
            resp = requests.post(
                tb_endpoint,
                headers={"x-api-key": textbee_key, "Content-Type": "application/json"},
                json={"recipients": [e164_phone], "message": message_text},
                timeout=10.0
            )
            if resp.status_code in (200, 201):
                return {"success": True, "provider": "textbee_sim", "phone": e164_phone}
        except Exception as e:
            print(f"[TEXTBEE ERROR] {e}")

    telnyx_key = os.environ.get("TELNYX_API_KEY", "").strip()
    telnyx_from = os.environ.get("TELNYX_FROM_PHONE", "").strip()
    if telnyx_key and telnyx_from:
        try:
            resp = requests.post(
                "https://api.telnyx.com/v2/messages",
                headers={"Authorization": f"Bearer {telnyx_key}", "Content-Type": "application/json"},
                json={"from": telnyx_from, "to": e164_phone, "text": message_text},
                timeout=10.0
            )
            if resp.status_code in (200, 201, 202):
                return {"success": True, "provider": "telnyx", "phone": e164_phone}
        except Exception as e:
            print(f"[TELNYX ERROR] {e}")

    return {"success": False, "error": "No SMS provider available"}
'''

try:
    ast.parse(sample_code)
    print("Syntax verification: Clean!")
except SyntaxError as e:
    print("Syntax error:", e)
