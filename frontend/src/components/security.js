// Web Crypto API utility for AES-GCM-256 payload encryption & dynamic PBKDF2/HKDF key derivation
// Sovereign Stehouwer Publishing AI-BS Ecosystem Cryptographic Standard (Parity with backend/core/cryptographic_vault.py)

export const DEFAULT_AES_PASSPHRASE = "Stehouwer_AIBS_Master_Sovereign_Key_2026";
export const DEFAULT_AES_SALT = "Stehouwer_AIBS_Salt_v5";
export const DEFAULT_PBKDF2_ITERATIONS = 100000;

// Legacy key for backward compatibility (bytes 1..32)
export const LEGACY_RAW_KEY = new Uint8Array(Array.from({ length: 32 }, (_, i) => i + 1));

const bufferToBase64 = (buffer) => {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
};

const base64ToBuffer = (base64) => {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
};

/**
 * Derives an AES-GCM-256 CryptoKey from passphrase and salt using PBKDF2-HMAC-SHA256
 * Matching backend/core/cryptographic_vault.py
 * @param {string} passphrase
 * @param {string|Uint8Array} salt
 * @param {number} iterations
 * @returns {Promise<CryptoKey>}
 */
export async function deriveKeyFromPassphrase(
    passphrase = DEFAULT_AES_PASSPHRASE,
    salt = DEFAULT_AES_SALT,
    iterations = DEFAULT_PBKDF2_ITERATIONS
) {
    const encoder = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
        "raw",
        encoder.encode(passphrase),
        { name: "PBKDF2" },
        false,
        ["deriveKey", "deriveBits"]
    );

    const saltBuffer = typeof salt === "string" ? encoder.encode(salt) : salt;

    return await crypto.subtle.deriveKey(
        {
            name: "PBKDF2",
            salt: saltBuffer,
            iterations: iterations,
            hash: "SHA-256"
        },
        keyMaterial,
        { name: "AES-GCM", length: 256 },
        true,
        ["encrypt", "decrypt"]
    );
}

/**
 * Imports a raw 32-byte Uint8Array into an AES-GCM CryptoKey (Legacy Fallback)
 * @param {Uint8Array} rawKeyBytes
 * @returns {Promise<CryptoKey>}
 */
export async function importRawKey(rawKeyBytes = LEGACY_RAW_KEY) {
    return await crypto.subtle.importKey(
        "raw",
        rawKeyBytes,
        { name: "AES-GCM" },
        false,
        ["encrypt", "decrypt"]
    );
}

/**
 * Encrypts a plaintext payload using AES-GCM-256
 * @param {string} plaintext - The raw string/JSON to encrypt
 * @param {CryptoKey} key - The imported or derived AES-GCM Web Crypto key
 * @returns {Promise<{iv: string, ciphertext: string}>}
 */
export async function encryptPayload(plaintext, key) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoder = new TextEncoder();
    const encodedData = encoder.encode(plaintext);

    const ciphertextBuffer = await crypto.subtle.encrypt(
        {
            name: "AES-GCM",
            iv: iv
        },
        key,
        encodedData
    );

    return {
        iv: bufferToBase64(iv),
        ciphertext: bufferToBase64(ciphertextBuffer)
    };
}

/**
 * Decrypts an AES-GCM-256 payload
 * @param {string} ciphertextB64
 * @param {string} ivB64
 * @param {CryptoKey} key
 * @returns {Promise<string>}
 */
export async function decryptPayload(ciphertextB64, ivB64, key) {
    const iv = base64ToBuffer(ivB64);
    const ciphertext = base64ToBuffer(ciphertextB64);

    const decryptedBuffer = await crypto.subtle.decrypt(
        {
            name: "AES-GCM",
            iv: new Uint8Array(iv)
        },
        key,
        ciphertext
    );

    const decoder = new TextDecoder();
    return decoder.decode(decryptedBuffer);
}
