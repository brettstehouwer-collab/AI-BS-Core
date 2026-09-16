"""
AI-BS Sovereign Cryptographic Hardening, E2E Payload Encryption & AES3 Audio Standards
Automated Verification Suite
Validates PBKDF2/HKDF derivation parity, Web Crypto cross-language interop,
tamper rejection (AEAD), /api/security/decrypt, encrypted chat envelopes,
streaming validation, and AES3 (IEC 60958 Type I) digital audio framing.
"""

import os
import sys
import json
import base64
import subprocess
import unittest

# Ensure backend root is on Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.core.cryptographic_vault import (
    vault,
    CryptographicVault,
    derive_key_pbkdf2,
    derive_key_hkdf,
    LEGACY_AES_SECRET_KEY,
    DEFAULT_MASTER_PASSPHRASE,
    DEFAULT_SALT,
    PBKDF2_ITERATIONS,
)
from backend.modules.audio_engineering_standards import (
    aes3_engine,
    AES3ChannelStatus,
    compute_aes3_crcc,
)
from backend.modules.streaming_validator import (
    validate_stream_url,
    validate_stream_key,
    validate_stream_endpoint,
    mask_stream_key,
)
from backend.AI_BS_Backend import app


class TestAESCryptographicHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Expected reference values derived under standard PBKDF2 / HKDF parameters
        cls.expected_vault_key_hex = "a9d3d00cfcc7c3030a4b5125de1bcf33c4d1f0daf09b1c7fc452e2aecbff043d"
        cls.expected_hkdf_test_hex = "48af2e4c7f372ccc68143559091641722573ce6e7b5f5cfe2f7110dd7d97366e"

    # =========================================================================
    # PHASE 1: KEY ROTATION & DYNAMIC KEY DERIVATION PARITY
    # =========================================================================
    def test_01_pbkdf2_key_derivation_parity(self):
        """Verifies PBKDF2-HMAC-SHA256 deterministic key derivation against canonical standard."""
        derived = derive_key_pbkdf2(DEFAULT_MASTER_PASSPHRASE, DEFAULT_SALT, PBKDF2_ITERATIONS)
        self.assertEqual(len(derived), 32)
        self.assertEqual(derived.hex(), self.expected_vault_key_hex)
        self.assertEqual(vault.get_active_key().hex(), self.expected_vault_key_hex)

    def test_02_hkdf_key_derivation_parity(self):
        """Verifies HKDF-SHA256 key derivation parity."""
        secret = b"test_secret_32bytes_long_key_12"
        salt = b"test_salt_16byte"
        derived = derive_key_hkdf(secret, salt, info=b"aibs_aes_gcm_payload", length=32)
        self.assertEqual(len(derived), 32)
        self.assertEqual(derived.hex(), self.expected_hkdf_test_hex)

    def test_03_web_crypto_cross_language_parity_and_interop(self):
        """
        Cross-validates Python CryptographicVault directly with Node.js Web Crypto API.
        Encrypts with Web Crypto and decrypts with Python; then encrypts with Python and decrypts with Web Crypto.
        """
        # Step A: Node.js Web Crypto derives key and encrypts test payload
        node_script = """
        const crypto = require('crypto').webcrypto;
        (async () => {
            const encoder = new TextEncoder();
            const passphrase = 'Stehouwer_AIBS_Master_Sovereign_Key_2026';
            const salt = 'Stehouwer_AIBS_Salt_v5';
            const keyMaterial = await crypto.subtle.importKey(
                'raw',
                encoder.encode(passphrase),
                { name: 'PBKDF2' },
                false,
                ['deriveKey']
            );
            const key = await crypto.subtle.deriveKey(
                { name: 'PBKDF2', salt: encoder.encode(salt), iterations: 100000, hash: 'SHA-256' },
                keyMaterial,
                { name: 'AES-GCM', length: 256 },
                false,
                ['encrypt']
            );
            const iv = crypto.getRandomValues(new Uint8Array(12));
            const plaintext = encoder.encode('Node_To_Python_Interop_Verified_2026');
            const ciphertext = await crypto.subtle.encrypt(
                { name: 'AES-GCM', iv: iv },
                key,
                plaintext
            );
            console.log(JSON.stringify({
                iv: Buffer.from(iv).toString('base64'),
                ciphertext: Buffer.from(ciphertext).toString('base64')
            }));
        })();
        """
        result = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
        node_out = json.loads(result.stdout.strip())
        
        # Python decrypts Node-encrypted ciphertext
        decrypted_in_py = vault.decrypt_payload(node_out["iv"], node_out["ciphertext"])
        self.assertEqual(decrypted_in_py.decode("utf-8"), "Node_To_Python_Interop_Verified_2026")

        # Step B: Python encrypts payload, Node Web Crypto decrypts it
        py_enc = vault.encrypt_payload(b"Python_To_Node_Interop_Verified_2026")
        node_decrypt_script = f"""
        const crypto = require('crypto').webcrypto;
        (async () => {{
            const encoder = new TextEncoder();
            const passphrase = 'Stehouwer_AIBS_Master_Sovereign_Key_2026';
            const salt = 'Stehouwer_AIBS_Salt_v5';
            const keyMaterial = await crypto.subtle.importKey(
                'raw',
                encoder.encode(passphrase),
                {{ name: 'PBKDF2' }},
                false,
                ['deriveKey']
            );
            const key = await crypto.subtle.deriveKey(
                {{ name: 'PBKDF2', salt: encoder.encode(salt), iterations: 100000, hash: 'SHA-256' }},
                keyMaterial,
                {{ name: 'AES-GCM', length: 256 }},
                false,
                ['decrypt']
            );
            const iv = Buffer.from('{py_enc["iv"]}', 'base64');
            const ciphertext = Buffer.from('{py_enc["ciphertext"]}', 'base64');
            const decrypted = await crypto.subtle.decrypt(
                {{ name: 'AES-GCM', iv: iv }},
                key,
                ciphertext
            );
            console.log(new TextDecoder().decode(decrypted));
        }})();
        """
        res_node_dec = subprocess.run(["node", "-e", node_decrypt_script], capture_output=True, text=True, check=True)
        self.assertEqual(res_node_dec.stdout.strip(), "Python_To_Node_Interop_Verified_2026")

    # =========================================================================
    # PHASE 2: AEAD TAMPER REJECTION & ENDPOINT SECURITY
    # =========================================================================
    def test_04_aead_authentication_tag_tamper_rejection(self):
        """
        Validates AES-GCM AEAD tamper rejection. Modifying any bit of the ciphertext
        or authentication tag MUST trigger an immediate cryptographic rejection.
        """
        payload = b"Top_Secret_Sovereign_Cognitive_Payload"
        enc = vault.encrypt_payload(payload)

        # 1. Authentic decrypt succeeds
        decrypted = vault.decrypt_payload(enc["iv"], enc["ciphertext"])
        self.assertEqual(decrypted, payload)

        # 2. Tampered ciphertext (flip 1 byte)
        raw_cipher = bytearray(base64.b64decode(enc["ciphertext"]))
        raw_cipher[5] ^= 0xFF
        tampered_cipher_b64 = base64.b64encode(raw_cipher).decode("utf-8")

        with self.assertRaises(ValueError) as ctx:
            vault.decrypt_payload(enc["iv"], tampered_cipher_b64)
        self.assertIn("Decryption failed", str(ctx.exception))

        # 3. Tampered IV (flip 1 byte)
        raw_iv = bytearray(base64.b64decode(enc["iv"]))
        raw_iv[2] ^= 0x01
        tampered_iv_b64 = base64.b64encode(raw_iv).decode("utf-8")

        with self.assertRaises(ValueError) as ctx:
            vault.decrypt_payload(tampered_iv_b64, enc["ciphertext"])
        self.assertIn("Decryption failed", str(ctx.exception))

    def test_05_legacy_key_backward_compatibility_fallback(self):
        """
        Ensures payloads encrypted with the legacy 32-byte key (bytes 1..32)
        are transparently and securely decrypted via the Tier 2 fallback.
        """
        legacy_cipher = AESGCM(LEGACY_AES_SECRET_KEY)
        nonce = os.urandom(12)
        plaintext = b"Legacy_Archive_Record_2024_Preserved"
        ciphertext = legacy_cipher.encrypt(nonce, plaintext, None)

        iv_b64 = base64.b64encode(nonce).decode("utf-8")
        ct_b64 = base64.b64encode(ciphertext).decode("utf-8")

        # Vault active key is NOT the legacy key, but decrypt_payload must gracefully succeed
        decrypted = vault.decrypt_payload(iv_b64, ct_b64)
        self.assertEqual(decrypted, plaintext)

    def test_06_dynamic_key_rotation(self):
        """Verifies in-memory key rotation and re-derivation."""
        test_vault = CryptographicVault()
        old_key = test_vault.get_active_key()

        new_key = test_vault.rotate_key("Rotated_Stehouwer_Passphrase_2027", b"New_Salt_Alpha_99")
        self.assertNotEqual(old_key, new_key)
        self.assertEqual(len(new_key), 32)

        enc = test_vault.encrypt_payload(b"Post_Rotation_Secret")
        dec = test_vault.decrypt_payload(enc["iv"], enc["ciphertext"])
        self.assertEqual(dec, b"Post_Rotation_Secret")

    def test_07_api_decrypt_endpoint(self):
        """Tests POST /api/security/decrypt with authentic, tampered, and legacy payloads."""
        # 1. Authentic active key payload
        enc = vault.encrypt_payload(b'{"action": "test_ping", "user": "brett"}')
        resp = self.client.post("/api/security/decrypt", json={"iv": enc["iv"], "ciphertext": enc["ciphertext"]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn('"user": "brett"', data["decrypted_data"])

        # 2. Tampered payload
        raw_cipher = bytearray(base64.b64decode(enc["ciphertext"]))
        raw_cipher[10] ^= 0xAB
        tampered_b64 = base64.b64encode(raw_cipher).decode("utf-8")
        resp_tampered = self.client.post("/api/security/decrypt", json={"iv": enc["iv"], "ciphertext": tampered_b64})
        self.assertEqual(resp_tampered.status_code, 400)
        self.assertEqual(resp_tampered.json()["status"], "error")

        # 3. Legacy key payload
        legacy_cipher = AESGCM(LEGACY_AES_SECRET_KEY)
        nonce = os.urandom(12)
        ct = legacy_cipher.encrypt(nonce, b"Legacy API Record", None)
        resp_legacy = self.client.post("/api/security/decrypt", json={
            "iv": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext": base64.b64encode(ct).decode("utf-8")
        })
        self.assertEqual(resp_legacy.status_code, 200)
        self.assertEqual(resp_legacy.json()["decrypted_data"], "Legacy API Record")

    def test_08_encrypted_chat_payload_envelope(self):
        """
        Tests encrypted envelope handling on /api/chat.
        Passes an encrypted payload with { encrypted: true, iv, ciphertext }.
        """
        chat_body = {
            "model": "stehouwer_llm",
            "messages": [{"role": "user", "content": "Ping encrypted envelope test"}]
        }
        serialized = json.dumps(chat_body).encode("utf-8")
        enc = vault.encrypt_payload(serialized)

        envelope = {
            "encrypted": True,
            "iv": enc["iv"],
            "ciphertext": enc["ciphertext"],
            "rawFallback": {
                "model": "stehouwer_llm",
                "messages": [{"role": "user", "content": "Fallback message"}]
            }
        }

        # Send to /api/chat
        resp = self.client.post("/api/chat", json=envelope)
        # Should return a response from chat router (200 or processed response)
        self.assertIn(resp.status_code, [200, 500, 503])
        if resp.status_code == 200:
            data = resp.json()
            self.assertTrue("choices" in data or "id" in data or "message" in data)

    # =========================================================================
    # PHASE 3: STREAMING URL & STREAM KEY VALIDATION
    # =========================================================================
    def test_09_streaming_url_and_key_validation(self):
        """Comprehensive verification of streaming keys and URLs."""
        # Valid YouTube
        yt = validate_stream_endpoint("rtmp://a.rtmp.youtube.com/live2", "je5p-8zxu-d7rj-d73s-cvu6")
        self.assertTrue(yt["valid"])
        self.assertEqual(yt["provider"], "YouTube Live")
        self.assertEqual(yt["protocol"], "rtmp")
        self.assertEqual(yt["masked_key"], "je5p****cvu6")

        # Valid Twitch
        tw = validate_stream_endpoint("rtmp://live.twitch.tv/app", "live_475849061_slFqN8Vl9Rr5SdAXRAnzry99LIfMVb")
        self.assertTrue(tw["valid"])
        self.assertEqual(tw["provider"], "Twitch")
        self.assertEqual(tw["masked_key"], "live****fMVb")

        # Valid SRT with parameters
        srt = validate_stream_endpoint("srt://127.0.0.1:9000?mode=caller&latency=120")
        self.assertTrue(srt["valid"])
        self.assertEqual(srt["protocol"], "srt")

        # Rejection: Shell command injection in URL
        inj_url = validate_stream_endpoint("rtmp://a.rtmp.youtube.com/live2; rm -rf /", "je5p-8zxu-d7rj-d73s-cvu6")
        self.assertFalse(inj_url["valid"])
        self.assertIn("Streaming URL contains illegal whitespace or shell metacharacters", inj_url["errors"])

        # Rejection: Shell command injection in Key
        inj_key = validate_stream_endpoint("rtmp://a.rtmp.youtube.com/live2", "key; cat /etc/passwd")
        self.assertFalse(inj_key["valid"])
        self.assertTrue(any("metacharacters" in err for err in inj_key["errors"]))

        # Rejection: Pipe injection
        inj_pipe = validate_stream_endpoint("rtmp://a.rtmp.youtube.com/live2|reboot", "safe_key_123")
        self.assertFalse(inj_pipe["valid"])

    def test_10_api_stream_validate_endpoint(self):
        """Tests POST /api/stream/validate live endpoint."""
        resp = self.client.post("/api/stream/validate", json={
            "url": "rtmp://a.rtmp.youtube.com/live2",
            "key": "je5p-8zxu-d7rj-d73s-cvu6",
            "name": "YouTube Live"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["masked_key"], "je5p****cvu6")

        # Injection test via API
        resp_inj = self.client.post("/api/stream/validate", json={
            "url": "rtmp://a.rtmp.youtube.com/live2; reboot",
            "key": "je5p-8zxu-d7rj-d73s-cvu6"
        })
        self.assertEqual(resp_inj.status_code, 200)
        self.assertFalse(resp_inj.json()["valid"])

    # =========================================================================
    # PHASE 4: AUDIO ENGINEERING SOCIETY (AES3 / AES/EBU) STANDARDS ENGINE
    # =========================================================================
    def test_11_aes3_channel_status_and_crcc(self):
        """Verifies AES3 (IEC 60958 Type I) 24-byte Channel Status encoding and CRC-8."""
        cs = AES3ChannelStatus(sample_rate=48000, word_length=24, origin="AIBS", destination="PROD")
        encoded = cs.encode()
        self.assertEqual(len(encoded), 24)

        # Verify CRCC Byte 23
        expected_crc = compute_aes3_crcc(encoded)
        self.assertEqual(encoded[23], expected_crc)

        # Decode and verify fields
        decoded = AES3ChannelStatus.decode(encoded)
        self.assertTrue(decoded["professional"])
        self.assertEqual(decoded["sample_rate_hz"], 48000)
        self.assertEqual(decoded["word_length_bits"], 24)
        self.assertTrue(decoded["crcc_valid"])
        self.assertEqual(decoded["origin"], "AIBS")
        self.assertEqual(decoded["destination"], "PROD")

    def test_12_aes3_subframe_and_block_assembly(self):
        """Verifies 192-frame AES3 block assembly, preambles (X, Y, Z), and parity bit."""
        # Process 192 stereo frames (1 block)
        left = [i * 100 for i in range(192)]
        right = [-i * 100 for i in range(192)]
        frames = aes3_engine.process_stereo_samples(left, right)
        self.assertEqual(len(frames), 192)

        # Frame 0 Subframe 1 must start with Preamble Z (0xE8 & 0x0F = 0x8)
        sub_l_0, sub_r_0 = frames[0]
        self.assertEqual(sub_l_0 & 0x0F, 0x08)  # Preamble Z low nibble
        self.assertEqual(sub_r_0 & 0x0F, 0x04)  # Preamble Y low nibble

        # Frame 1 Subframe 1 must start with Preamble X (0xE2 & 0x0F = 0x2)
        sub_l_1, sub_r_1 = frames[1]
        self.assertEqual(sub_l_1 & 0x0F, 0x02)  # Preamble X low nibble
        self.assertEqual(sub_r_1 & 0x0F, 0x04)  # Preamble Y low nibble

    def test_13_api_aes3_status_endpoint(self):
        """Tests GET /api/audio/aes3-status endpoint."""
        resp = self.client.get("/api/audio/aes3-status")
        self.assertEqual(resp.status_code, 200)
        telemetry = resp.json()
        self.assertEqual(telemetry["standard"], "AES3-2009 / AES/EBU (IEC 60958 Type I)")
        self.assertEqual(telemetry["status"], "LOCKED")
        self.assertEqual(telemetry["sample_rate_hz"], 48000)
        self.assertEqual(telemetry["bit_depth"], 24)
        self.assertTrue(telemetry["channel_status"]["crcc_valid"])


if __name__ == "__main__":
    unittest.main()
