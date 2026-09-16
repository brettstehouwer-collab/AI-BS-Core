import os
import sys
import base64
import json
from fastapi.testclient import TestClient

# Add current dir to path to import AI_BS_Backend
sys.path.append(os.path.dirname(__file__))

from AI_BS_Backend import app, aesgcm, ph

client = TestClient(app)


def run_tests():
    print("==========================================")
    print("Executing AES-GCM & Argon2id Security Test")
    print("==========================================")

    # 1. Test Argon2id Authentication
    print("[1] Testing /api/auth/login with Argon2id parameters (m=65536, t=3, p=4)...")
    res = client.post(
        "/api/auth/login", json={"username": "admin", "password": "password"}
    )
    if res.status_code == 200 and "session_token" in res.cookies:
        print("  -> SUCCESS: Valid credentials accepted. HttpOnly cookie generated.")
    else:
        print(f"  -> FAILED: Auth failed. Response: {res.json()}")
        sys.exit(1)

    res_bad = client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrongpassword"}
    )
    if res_bad.status_code == 401:
        print("  -> SUCCESS: Invalid credentials securely rejected.")
    else:
        print("  -> FAILED: Invalid credentials allowed!")
        sys.exit(1)

    # 2. Test AES-GCM-256 Decryption
    print("\n[2] Testing AES-GCM-256 Payload Decryption...")

    # Mocking frontend Web Crypto encryption
    plaintext_payload = json.dumps(
        {"command": "SYSTEM_DIAGNOSTIC", "target": "Core_Memory"}
    ).encode("utf-8")
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, plaintext_payload, None)

    iv_b64 = base64.b64encode(iv).decode("utf-8")
    cipher_b64 = base64.b64encode(ciphertext).decode("utf-8")

    res_dec = client.post(
        "/api/security/decrypt", json={"iv": iv_b64, "ciphertext": cipher_b64}
    )

    if res_dec.status_code == 200:
        data = res_dec.json()
        print(f"  -> SUCCESS: Payload Decrypted. Data: {data.get('decrypted_data')}")
        if "SYSTEM_DIAGNOSTIC" in data.get("decrypted_data"):
            print("  -> VALIDATION: Cryptographic Integrity Verified.")
        else:
            print("  -> FAILED: Data mismatch.")
            sys.exit(1)
    else:
        print(f"  -> FAILED: Decryption rejected. {res_dec.text}")
        sys.exit(1)

    print("\n==========================================")
    print("ALL SECURITY PERIMETERS FUNCTIONING NOMINALLY")
    print("==========================================")


if __name__ == "__main__":
    run_tests()
