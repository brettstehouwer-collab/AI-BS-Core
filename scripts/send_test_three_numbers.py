import sqlite3
import json
import time
from pathlib import Path

# Import the send_carrier_sms helper directly or call via API
import sys
sys.path.append(r"C:\AI-BS\backend")
from routers.rec_debut_router import send_carrier_sms

test_numbers = [
    "+1 616 406 7993",
    "+1 616 291 5227",
    "+1 616 402 3628"
]

msg = """Hey, this is Dennis Bell, former New York Knick and President of Recreational Debut.

We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.

📱 Call or text: +1-616-291-5227
✅ Register FREE: RecDebut.com
📧 dbell002@sbcglobal.net

Dennis Bell
Former New York Knicks
President, Recreational Debut"""

print("=== SENDING TO 3 TEST NUMBERS ===")
for phone in test_numbers:
    print(f"\nDispatching MMS to {phone} with Caller ID dbell002@sbcglobal.net...")
    res = send_carrier_sms(
        recipient_phone=phone,
        message_text=msg,
        caller_id_email="dbell002@sbcglobal.net",
        caller_id_name="Dennis Bell (+1-616-291-5227)"
    )
    print("Result:", json.dumps(res, indent=2))
    time.sleep(1)

print("\nAll 3 test numbers dispatched!")
