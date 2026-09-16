import os
import sys
import json
import secrets
from datetime import datetime, timedelta

COMMERCIAL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(COMMERCIAL_DIR, "authorized_testers_config.json")


def generate_tester_passkey(
    email: str, allowed_ips: list = None, duration_days: int = 30
):
    """Generate a high-entropy Tester Passkey and secret auth header for an authorized penetration tester."""
    raw_passkey = "sk_aibs_test_" + secrets.token_hex(20)
    secret_header_val = "sec_token_aibs_" + secrets.token_hex(16)

    start_dt = datetime.now()
    end_dt = start_dt + timedelta(days=duration_days)

    new_tester = {
        "tester_id": f"auditor_{secrets.token_hex(4)}",
        "tester_email": email,
        "allowed_ips": allowed_ips or ["127.0.0.1"],
        "tester_api_passkey": raw_passkey,
        "secret_header_name": "X-AI-BS-Test-Auth",
        "secret_header_value": secret_header_val,
        "window_start": start_dt.isoformat() + "Z",
        "window_end": end_dt.isoformat() + "Z",
        "suppress_auto_ban": True,
        "log_findings_only": True,
    }

    cfg = {"pen_testing_enabled": True, "authorized_testers": []}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    cfg["pen_testing_enabled"] = True
    testers = cfg.get("authorized_testers", [])
    # Replace or append tester by email
    testers = [t for t in testers if t.get("tester_email") != email]
    testers.append(new_tester)
    cfg["authorized_testers"] = testers

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    return new_tester


if __name__ == "__main__":
    if len(sys.argv) > 1:
        auditor_email = sys.argv[1]
    else:
        auditor_email = "security_auditor@example.com"

    res = generate_tester_passkey(auditor_email)
    print("==========================================================")
    print("🛡️ AUTHORIZED SECURITY TESTER PASSKEY GENERATED")
    print("==========================================================")
    print(f"Tester Email:        {res['tester_email']}")
    print(f"Tester API Passkey:  {res['tester_api_passkey']}")
    print(f"Secret Header Name:  {res['secret_header_name']}")
    print(f"Secret Header Value: {res['secret_header_value']}")
    print(f"Testing Time Window: {res['window_start']} -> {res['window_end']}")
    print("==========================================================")
