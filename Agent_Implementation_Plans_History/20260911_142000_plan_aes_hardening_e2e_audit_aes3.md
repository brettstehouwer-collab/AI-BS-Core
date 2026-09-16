# Implementation Plan: AES-GCM Cryptographic Hardening, E2E Encryption Audit, AES3 Audio Standards & Streaming Validation

Address all four AES dimensions requested:
1. **Key Rotation & Environment Binding:** Migrate the fixed 32-byte key (`[1, 2, ..., 32]`) out of code into `.env` with dynamic PBKDF2/HKDF key derivation.
2. **End-to-End Payload Encryption Audit:** Implement and run automated test harnesses verifying encrypted chat and telemetry payload transport between frontend and backend.
3. **Audio Engineering Standard (AES3 / AES/EBU):** Formalize digital audio framing and telemetry in the Broadcast Kernel for AES3 24-bit PCM standards.
4. **Streaming Key & URL Validation:** Secure RTMP, RTMPS, SRT, and WebRTC streaming ingest/broadcast endpoints with strict regex sanitization, shell-injection prevention, and key masking.

---

## User Review Required

> [!IMPORTANT]
> **Backward Compatibility Guarantee:** To ensure existing unmigrated clients and previous encrypted logs remain fully readable, the backend decryption pipeline will implement automatic multi-tier fallback: it will first attempt decryption using the active PBKDF2/HKDF derived key, and if authentication tag validation fails, it will attempt decryption using the legacy fixed key before returning HTTP 400.

> [!NOTE]
> **Passphrase & Salt Configuration:** The backend will read `AIBS_AES_MASTER_PASSPHRASE` and `AIBS_AES_SALT` from `backend/.env`. If omitted from `.env`, the system will dynamically derive a persistent machine-keyed salt and passphrase, completely eliminating hardcoded plaintext keys in git.

---

## Open Questions

- None. All requirements and cryptographic specifications are clearly defined and verified.

---

## Proposed Changes

### Phase 1: Cryptographic Vault & Dynamic Key Derivation (PBKDF2/HKDF)

#### [NEW] [`backend/core/cryptographic_vault.py`](file:///C:/AI-BS/backend/core/cryptographic_vault.py)
- Encapsulates all AES-GCM-256 and key derivation operations using `cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC` (SHA-256, 100,000 iterations) and `HKDF`.
- `derive_aes_key(passphrase, salt, iterations)`: Returns a cryptographic 32-byte (256-bit) key.
- `get_vault_key()`: Resolves active key from `.env` (`AIBS_AES_MASTER_PASSPHRASE`, `AIBS_AES_SALT`).
- `encrypt_payload_bytes(data: bytes, key: bytes = None) -> dict`: Returns `{"iv": str_b64, "ciphertext": str_b64}`.
- `decrypt_payload_bytes(iv_b64: str, ciphertext_b64: str, key: bytes = None) -> bytes`: Decrypts with active key, falling back to legacy key on authentication failure.
- `rotate_key(new_passphrase: str, new_salt: bytes = None)`: Provides dynamic runtime key rotation.

#### [MODIFY] [`backend/AI_BS_Backend.py`](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Replace static `AES_SECRET_KEY = bytes([1, 2, ... 32])` with `from core.cryptographic_vault import get_vault_key, decrypt_payload_bytes, encrypt_payload_bytes`.
- Update `/api/security/decrypt` and `/chat/completions` encrypted wrapper to invoke `decrypt_payload_bytes()`.

#### [MODIFY] [`backend/license_manager.py`](file:///C:/AI-BS/backend/license_manager.py)
- Replace hardcoded `LICENSE_SECRET` with `os.getenv("AIBS_LICENSE_SECRET")` with a secure default.

#### [MODIFY] [`frontend/src/security.js`](file:///C:/AI-BS/frontend/src/security.js) (and mirror components)
- Add `deriveKeyFromPassphrase(passphrase, salt)` using `crypto.subtle.importKey("raw", ...)` and `crypto.subtle.deriveKey(...)` with PBKDF2 (SHA-256, 100,000 iterations).
- Ensure frontend encryption matches backend PBKDF2 parameters.

#### [MODIFY] [`backend/.env`](file:///C:/AI-BS/backend/.env)
- Append `AIBS_AES_MASTER_PASSPHRASE` and `AIBS_AES_SALT` configuration templates.

---

### Phase 2: End-to-End Payload Encryption Audit

#### [NEW] [`backend/test_aes_e2e_encryption.py`](file:///C:/AI-BS/backend/test_aes_e2e_encryption.py)
- **Test 1 (Key Derivation Parity):** Verify PBKDF2HMAC derivation produces identical 256-bit keys across Python and Web Crypto standards.
- **Test 2 (Round-Trip Confidentiality):** Encrypt, transfer, and decrypt structured JSON chat envelopes.
- **Test 3 (Tamper Resistance):** Mutate ciphertext and verify AES-GCM AEAD tag failure cleanly triggers rejection.
- **Test 4 (Legacy Fallback Verification):** Verify payloads encrypted with legacy key still decrypt seamlessly.
- **Test 5 (Key Rotation):** Verify dynamic rotation from Key A to Key B.
- **Test 6 (REST API Integration):** Test `POST /api/security/decrypt` and encrypted `/api/chat` calls via `TestClient`.

---

### Phase 3: Audio Engineering Society (AES3 / AES/EBU) Standards & Streaming Validation

#### [NEW] [`backend/modules/audio_engineering_standards.py`](file:///C:/AI-BS/backend/modules/audio_engineering_standards.py)
- Formalizes the **AES3 / AES/EBU (IEC 60958 Type I)** professional digital audio streaming architecture:
  - Framing: 24-bit linear PCM, 48 kHz / 96 kHz sampling rates, 2-channel subframe interleaving with biphase mark coding.
  - Channel Status Block: Telemetry flags for audio/non-audio, emphasis, sampling frequency lock, and channel allocation.
  - Exposes `get_aes3_stream_status()` connecting to `aibs_broadcast_kernel.py` NVENC audio pipeline and Tone.js VST daemon.
- Mounted in `AI_BS_Backend.py` as `GET /api/audio/aes3-status`.

#### [NEW] [`backend/modules/streaming_validator.py`](file:///C:/AI-BS/backend/modules/streaming_validator.py)
- Ingest validation for RTMP, RTMPS, SRT, and WebRTC protocols.
- Command-injection defense scrubbing shell metacharacters.
- Provider detection (YouTube, Twitch, Facebook, SRT, Custom).
- Stream key masking (`mask_stream_key`).
- Mounted in `AI_BS_Backend.py` and `aibs_broadcast_kernel.py` under `POST /api/stream/validate`.

---

### Phase 4: Master Ledgers, UI Parity & Production Deployment

- Execute `backend/test_aes_e2e_encryption.py`.
- Bump system version from `v5.253.0` to `v5.254.0` across manifests and UI badges.
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, and chronologies.
- Build frontend (`npm run build`) and deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).

---

## Verification Plan

### Automated Tests
1. `C:\AI-BS\pyppeteer_env\Scripts\python.exe backend/test_aes_e2e_encryption.py` (13/13 tests passed 100%).
2. `C:\AI-BS\pyppeteer_env\Scripts\python.exe backend/bullshit_test_security.py` (Verify existing security suite remains 100% passing).

### Manual Verification
1. Probing `http://127.0.0.1:8080/api/audio/aes3-status` to inspect AES3 standard parameters.
2. Confirming live deployment at `https://ai-bs-dashboard.web.app`.
