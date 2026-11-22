"""
AI-BS Cryptographic Vault
Sovereign AES-GCM-256 authenticated encryption, PBKDF2/HKDF dynamic key derivation,
and multi-tier key rotation engine.
"""

import os
import sys
import base64
import json
from typing import Optional, Dict, Any, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

# Legacy fixed 32-byte key (bytes 1 through 32) retained strictly for backward compatibility
LEGACY_AES_SECRET_KEY = bytes(range(1, 33))

# Standard canonical defaults for deterministic derivation when environment is unconfigured
DEFAULT_MASTER_PASSPHRASE = "Stehouwer_AIBS_Master_Sovereign_Key_2026"
DEFAULT_SALT = b"Stehouwer_AIBS_Salt_v5"
PBKDF2_ITERATIONS = 100_000


def derive_key_pbkdf2(passphrase: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """
    Derives a 256-bit (32-byte) AES key from a passphrase and salt using PBKDF2-HMAC-SHA256.
    Matching standard Web Crypto API PBKDF2 specifications.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def derive_key_hkdf(secret: bytes, salt: bytes, info: bytes = b"aibs_aes_gcm_payload", length: int = 32) -> bytes:
    """
    Derives a cryptographic key using HKDF-SHA256.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    )
    return hkdf.derive(secret)


class CryptographicVault:
    """
    Centralized cryptographic vault managing AES-GCM-256 keys, dynamic rotation,
    and multi-tier decryption fallbacks.
    """

    def __init__(self):
        self._load_keys()

    def _load_keys(self):
        # 1. Environment-driven passphrase & salt
        passphrase = os.getenv("AIBS_AES_MASTER_PASSPHRASE", DEFAULT_MASTER_PASSPHRASE)
        raw_salt = os.getenv("AIBS_AES_SALT")
        if raw_salt:
            self.salt = raw_salt.encode("utf-8")
        else:
            self.salt = DEFAULT_SALT

        self.passphrase = passphrase
        self.active_key = derive_key_pbkdf2(self.passphrase, self.salt, PBKDF2_ITERATIONS)
        self.active_aesgcm = AESGCM(self.active_key)
        self.legacy_aesgcm = AESGCM(LEGACY_AES_SECRET_KEY)

    def rotate_key(self, new_passphrase: str, new_salt: Optional[bytes] = None) -> bytes:
        """
        Dynamically rotates the active AES key in-memory.
        """
        self.passphrase = new_passphrase
        if new_salt:
            self.salt = new_salt
        self.active_key = derive_key_pbkdf2(self.passphrase, self.salt, PBKDF2_ITERATIONS)
        self.active_aesgcm = AESGCM(self.active_key)
        return self.active_key

    def get_active_key(self) -> bytes:
        return self.active_key

    def get_active_aesgcm(self) -> AESGCM:
        return self.active_aesgcm

    def encrypt_payload(self, data: bytes, key: Optional[bytes] = None) -> Dict[str, str]:
        """
        Encrypts plaintext bytes using AES-GCM with a fresh random 12-byte IV.
        Returns base64-encoded IV and ciphertext (including 16-byte authentication tag).
        """
        cipher = AESGCM(key) if key else self.active_aesgcm
        iv = os.urandom(12)
        ciphertext = cipher.encrypt(iv, data, None)
        return {
            "iv": base64.b64encode(iv).decode("utf-8"),
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
        }

    def decrypt_payload(self, iv_b64: str, ciphertext_b64: str, key: Optional[bytes] = None) -> bytes:
        """
        Decrypts base64-encoded IV and ciphertext.
        Implements multi-tier fallback: attempts with provided/active key first,
        and falls back to legacy key on InvalidTag authentication failure.
        """
        iv = base64.b64decode(iv_b64)
        ciphertext = base64.b64decode(ciphertext_b64)

        target_cipher = AESGCM(key) if key else self.active_aesgcm

        # Tier 1: Try target / active derived key
        try:
            return target_cipher.decrypt(iv, ciphertext, None)
        except InvalidTag:
            # Tier 2: Fall back to legacy fixed key for backward compatibility
            try:
                return self.legacy_aesgcm.decrypt(iv, ciphertext, None)
            except InvalidTag:
                raise ValueError("Decryption failed: cryptographic signature/tag mismatch or invalid key")


# Singleton instance for ecosystem-wide consumption
vault = CryptographicVault()
aesgcm = vault.get_active_aesgcm()
AES_SECRET_KEY = vault.get_active_key()


def encrypt_payload(data: bytes, key: Optional[bytes] = None) -> Dict[str, str]:
    return vault.encrypt_payload(data, key)


def decrypt_payload(iv_b64: str, ciphertext_b64: str, key: Optional[bytes] = None) -> bytes:
    return vault.decrypt_payload(iv_b64, ciphertext_b64, key)
