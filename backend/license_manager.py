import os
import json
import base64
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Sourced from environment or fallback default for Stehouwer Publishing licensing signatures.
LICENSE_SECRET = os.getenv("AIBS_LICENSE_SECRET", "Stehouwer_Publishing_Secret_2026").encode("utf-8")[:32].ljust(32, b"0")


class LicenseManager:
    def __init__(self, license_file: str = None):
        if license_file is None:
            license_file = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "AI-BS_Knowledge_Vaults",
                    "license.key",
                )
            )
        self.license_file = license_file

        self.aesgcm = AESGCM(LICENSE_SECRET)

    def generate_key(self, email: str, tier: str, expires_days: int = 365) -> str:
        """Generates a cryptographically signed license key."""
        expiry_date = (datetime.now() + timedelta(days=expires_days)).isoformat()
        payload = {
            "email": email,
            "tier": tier,
            "expires": expiry_date,
            "publisher": "Stehouwer Publishing",
        }

        serialized = json.dumps(payload).encode("utf-8")
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, serialized, None)

        # Combine nonce and ciphertext and encode to base64
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("utf-8")

    def verify_key(self, key_str: str) -> dict:
        """Decrypts and validates the license key payload."""
        try:
            combined = base64.b64decode(key_str.encode("utf-8"))
            if len(combined) < 13:
                return {"status": "invalid", "message": "Key is too short."}

            nonce = combined[:12]
            ciphertext = combined[12:]

            decrypted = self.aesgcm.decrypt(nonce, ciphertext, None)
            payload = json.loads(decrypted.decode("utf-8"))

            # Verify expiration
            expires = datetime.fromisoformat(payload["expires"])
            if expires < datetime.now():
                return {
                    "status": "expired",
                    "payload": payload,
                    "message": "License key has expired.",
                }

            return {"status": "valid", "payload": payload}
        except Exception as e:
            return {"status": "invalid", "message": f"Verification failed: {str(e)}"}

    def install_license(self, key_str: str) -> dict:
        """Verifies and physically saves the license key to disk."""
        result = self.verify_key(key_str)
        if result["status"] == "valid":
            try:
                os.makedirs(os.path.dirname(self.license_file), exist_ok=True)
                with open(self.license_file, "w", encoding="utf-8") as f:
                    f.write(key_str.strip())
                return {"status": "success", "payload": result["payload"]}
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to write license file: {str(e)}",
                }
        return result

    def get_installed_license(self) -> dict:
        """Reads and verifies the locally installed license key."""
        if not os.path.exists(self.license_file):
            return {"status": "missing", "message": "No license key installed."}

        try:
            with open(self.license_file, "r", encoding="utf-8") as f:
                key_str = f.read().strip()
            return self.verify_key(key_str)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read license file: {str(e)}",
            }
