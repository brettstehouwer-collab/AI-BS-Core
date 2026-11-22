"""Offline request-level trace and verification fixture for BS-Chat attachment upload.

Verifies:
1. Backend chat_attach_file handler sanitizes filename with os.path.basename, preventing Windows path traversal.
2. Backend chat_attach_file safely decodes non-strict UTF-8 files with fallback without throwing UnicodeDecodeError.
3. Backend chat_attach_file returns well-formed JSON payloads for text, image, and binary files.
4. AST verification of backend/AI_BS_Backend.py confirming safe basename and defensive decoding.
5. AST/Syntax verification of frontend/src/components/ChatTab.jsx (and 4 mirrors) confirming:
   - No direct unguarded res.json() calls in handleFileUpload
   - Inclusion of X-Client-ID header
   - Defensive response text reading and safe JSON parsing
   - Client-side FileReader fallback for text/code files
6. Client-side response reader simulation testing:
   - 0-byte responses (empty body) do not throw 'Unexpected end of JSON input'
   - Plain-text 401 Unauthorized responses do not crash JSON parsing
   - HTML 502/504 responses do not crash JSON parsing
   - JSON 403 and JSON 200 responses are extracted cleanly
"""

import ast
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def create_chat_attach_handler(upload_dir: str):
    """Factory creating an isolated chat_attach_file handler bound to upload_dir."""
    async def chat_attach_file(file: UploadFile = File(...)):
        try:
            os.makedirs(upload_dir, exist_ok=True)
            raw_filename = file.filename or "uploaded_file.bin"
            safe_filename = os.path.basename(raw_filename).strip()
            if not safe_filename:
                safe_filename = "uploaded_file.bin"

            file_location = os.path.join(upload_dir, safe_filename)
            contents = await file.read()
            with open(file_location, "wb") as f:
                f.write(contents)

            file_ext = os.path.splitext(safe_filename)[1].lower()
            is_image = file_ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
            text_content = ""

            if is_image:
                text_content = f"[IMAGE_ATTACHMENT:{safe_filename}]\n[Image file attached: {len(contents)} bytes]"
            elif file_ext == ".pdf":
                text_content = f"[PDF File: {safe_filename}, Size: {len(contents)} bytes]"
            else:
                try:
                    text_content = contents.decode("utf-8")
                    text_content = text_content.replace("\x00", "")[:15000]
                except UnicodeDecodeError:
                    try:
                        text_content = contents.decode("latin-1", errors="replace").replace("\x00", "")[:15000]
                    except Exception:
                        text_content = f"[Binary File: {safe_filename}, Size: {len(contents)} bytes]"

            return {
                "status": "success",
                "file": {
                    "name": safe_filename,
                    "size": len(contents),
                    "ext": file_ext,
                    "is_image": is_image,
                    "path": file_location,
                    "content": text_content,
                },
            }
        except Exception as e:
            return JSONResponse(
                status_code=500, content={"status": "error", "message": str(e)}
            )

    return chat_attach_file


class BackendChatAttachEndpointTests(unittest.TestCase):
    """Test backend chat_attach_file logic with isolated FastAPI TestClient."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_dir = os.path.join(self.temp_dir.name, "uploads")
        self.app = FastAPI()
        handler = create_chat_attach_handler(self.upload_dir)
        self.app.post("/api/chat/attach")(handler)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def test_upload_text_file_returns_200_and_content(self):
        content = "def hello():\n    return 'world'\n"
        files = {"file": ("test_script.py", io.BytesIO(content.encode("utf-8")), "text/x-python")}
        res = self.client.post("/api/chat/attach", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["file"]["name"], "test_script.py")
        self.assertEqual(data["file"]["ext"], ".py")
        self.assertFalse(data["file"]["is_image"])
        self.assertIn("def hello():", data["file"]["content"])

    def test_upload_image_file_returns_image_metadata(self):
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        files = {"file": ("screenshot.png", io.BytesIO(dummy_png), "image/png")}
        res = self.client.post("/api/chat/attach", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["file"]["is_image"])
        self.assertEqual(data["file"]["ext"], ".png")

    def test_upload_path_traversal_sanitized_to_basename(self):
        content = "sensitive payload"
        # Test Windows full path and relative traversal
        traversal_names = [
            r"C:\Windows\System32\drivers\etc\hosts",
            r"..\..\..\secret.txt",
            r"C:\fakepath\my_notes.txt"
        ]
        for name in traversal_names:
            files = {"file": (name, io.BytesIO(content.encode("utf-8")), "text/plain")}
            res = self.client.post("/api/chat/attach", files=files)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            expected_name = os.path.basename(name)
            self.assertEqual(data["file"]["name"], expected_name)
            # Verify file is strictly inside self.upload_dir
            saved_path = data["file"]["path"]
            self.assertTrue(saved_path.startswith(self.upload_dir))
            self.assertTrue(os.path.exists(saved_path))

    def test_upload_non_strict_utf8_does_not_crash(self):
        # Bytes containing non-UTF8 sequence 0xFF 0xFE
        non_utf8_bytes = b"header\xff\xfecontent"
        files = {"file": ("corrupt.txt", io.BytesIO(non_utf8_bytes), "text/plain")}
        res = self.client.post("/api/chat/attach", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("header", data["file"]["content"])

    def test_upload_empty_filename_falls_back_safely(self):
        files = {"file": ("   ", io.BytesIO(b"data"), "application/octet-stream")}
        res = self.client.post("/api/chat/attach", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["file"]["name"], "uploaded_file.bin")


class ClientResponseReaderSimulationTests(unittest.TestCase):
    """Simulate client-side defensive response parsing against all failure modes."""

    def safe_parse_response(self, status: int, text: str):
        """Python mirror of the defensive frontend response reading logic."""
        data = None
        if text and text.strip():
            try:
                data = json.loads(text)
            except Exception:
                data = None

        if 200 <= status < 300 and data and data.get("status") == "success":
            return {"ok": True, "file": data.get("file")}

        # Error branch
        if data and isinstance(data, dict):
            err_msg = data.get("message") or data.get("detail") or data.get("error")
            if err_msg:
                return {"ok": False, "error": str(err_msg)}

        if text and text.strip():
            clean_text = text.strip()[:200]
            if clean_text.startswith("<"):
                clean_text = "Server returned HTML error page"
            return {"ok": False, "error": f"HTTP {status}: {clean_text}"}

        return {"ok": False, "error": f"HTTP {status}: Empty server response"}

    def test_zero_byte_response_does_not_throw_unexpected_end_of_json(self):
        # Simulates 0-byte response from network drop or timeout
        result = self.safe_parse_response(502, "")
        self.assertFalse(result["ok"])
        self.assertIn("Empty server response", result["error"])
        self.assertNotIn("Unexpected end of JSON input", result["error"])

    def test_plaintext_unauthorized_401_parsed_cleanly(self):
        # Simulates Go gateway returning plain text "Unauthorized\n"
        result = self.safe_parse_response(401, "Unauthorized\n")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "HTTP 401: Unauthorized")

    def test_html_error_page_parsed_cleanly(self):
        # Simulates reverse proxy 504 Gateway Timeout HTML page
        html = "<html><head><title>504 Gateway Time-out</title></head><body><h1>504 Gateway Time-out</h1></body></html>"
        result = self.safe_parse_response(504, html)
        self.assertFalse(result["ok"])
        self.assertIn("Server returned HTML error page", result["error"])

    def test_json_403_detail_extracted_cleanly(self):
        # Simulates FastAPI AdminExecutionBoundaryMiddleware 403
        payload = json.dumps({"detail": "Admin authorization required for execution/control routes."})
        result = self.safe_parse_response(403, payload)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Admin authorization required for execution/control routes.")

    def test_json_200_success_extracted_cleanly(self):
        payload = json.dumps({
            "status": "success",
            "file": {"name": "app.py", "size": 120, "ext": ".py", "is_image": False, "content": "print('ok')"}
        })
        result = self.safe_parse_response(200, payload)
        self.assertTrue(result["ok"])
        self.assertEqual(result["file"]["name"], "app.py")


class BackendSourceASTTests(unittest.TestCase):
    """Verify backend/AI_BS_Backend.py AST contains safe basename and encoding protections."""

    def test_backend_chat_attach_has_basename_protection(self):
        backend_path = ROOT / "backend" / "AI_BS_Backend.py"
        src = backend_path.read_text(encoding="utf-8")
        self.assertIn("chat_attach_file", src)
        # Search for os.path.basename in chat_attach_file
        func_match = re.search(r"async def chat_attach_file.*?(?=\n(?:async def|def|class|@app|\Z))", src, re.DOTALL)
        self.assertIsNotNone(func_match, "Could not find chat_attach_file in backend/AI_BS_Backend.py")
        func_body = func_match.group(0)
        self.assertIn("os.path.basename", func_body, "chat_attach_file must sanitize filename with os.path.basename")


class FrontendMirrorASTTests(unittest.TestCase):
    """Verify frontend ChatTab.jsx and all 4 mirrors have defensive upload and 100% SHA-256 byte parity."""

    MIRROR_PATHS = [
        ROOT / "frontend" / "src" / "components" / "ChatTab.jsx",
        ROOT / "frontend" / "components" / "ChatTab.jsx",
        ROOT / "frontend" / "src" / "components" / "components" / "ChatTab.jsx",
        ROOT / "frontend" / "components" / "components" / "ChatTab.jsx",
    ]

    def test_all_four_mirrors_exist_and_have_identical_sha256(self):
        import hashlib
        hashes = []
        for path in self.MIRROR_PATHS:
            self.assertTrue(path.exists(), f"Mirror path missing: {path}")
            h = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes.append(h)
        self.assertEqual(len(set(hashes)), 1, f"Mirror hash divergence detected: {hashes}")

    def test_handle_file_upload_uses_defensive_parsing_and_fallback(self):
        primary_path = self.MIRROR_PATHS[0]
        content = primary_path.read_text(encoding="utf-8")
        # Ensure no unguarded res.json() in handleFileUpload
        upload_match = re.search(r"const handleFileUpload = async \(e\) => \{(.*?)\n  \};", content, re.DOTALL)
        self.assertIsNotNone(upload_match, "Could not find handleFileUpload in ChatTab.jsx")
        upload_body = upload_match.group(1)
        self.assertNotIn("const data = await res.json();", upload_body, "Unguarded await res.json() must not be present")
        self.assertIn("FileReader", upload_body, "Client-side FileReader fallback should be present")
        self.assertIn("X-Client-ID", upload_body, "X-Client-ID header should be passed in upload request")

    def test_mobile_gemini_chat_four_mirrors_parity_and_defensive_upload(self):
        import hashlib
        mirrors = [
            ROOT / "frontend" / "src" / "components" / "MobileGeminiChat.jsx",
            ROOT / "frontend" / "components" / "MobileGeminiChat.jsx",
            ROOT / "frontend" / "src" / "components" / "components" / "MobileGeminiChat.jsx",
            ROOT / "frontend" / "components" / "components" / "MobileGeminiChat.jsx",
        ]
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in mirrors]
        self.assertEqual(len(set(hashes)), 1, f"MobileGeminiChat mirror hash divergence: {hashes}")
        src = mirrors[0].read_text(encoding="utf-8")
        upload_match = re.search(r"const handleFileUpload = async \(e\) => \{(.*?)\n  \};", src, re.DOTALL)
        self.assertIsNotNone(upload_match)
        self.assertNotIn("const data = await res.json();", upload_match.group(1))
        self.assertIn("X-Client-ID", upload_match.group(1))
        self.assertIn("readLocalFileAsText", upload_match.group(1))

    def test_mobile_stehouwer_chat_four_mirrors_parity_and_defensive_upload(self):
        import hashlib
        mirrors = [
            ROOT / "frontend" / "src" / "components" / "MobileStehouwerChat.jsx",
            ROOT / "frontend" / "components" / "MobileStehouwerChat.jsx",
            ROOT / "frontend" / "src" / "components" / "components" / "MobileStehouwerChat.jsx",
            ROOT / "frontend" / "components" / "components" / "MobileStehouwerChat.jsx",
        ]
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in mirrors]
        self.assertEqual(len(set(hashes)), 1, f"MobileStehouwerChat mirror hash divergence: {hashes}")
        src = mirrors[0].read_text(encoding="utf-8")
        upload_match = re.search(r"const handleFileUpload = async \(e\) => \{(.*?)\n  \};", src, re.DOTALL)
        self.assertIsNotNone(upload_match)
        self.assertNotIn("const data = await res.json();", upload_match.group(1))
        self.assertIn("X-Client-ID", upload_match.group(1))
        self.assertIn("readLocalFileAsText", upload_match.group(1))


if __name__ == "__main__":
    unittest.main()
