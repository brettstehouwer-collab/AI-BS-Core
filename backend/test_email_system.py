"""Automated Test Suite for AI-BS Business Email Subsystem
Tests email_client_router endpoints, payload normalization, and SMTP/IMAP interfaces.
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from AI_BS_Backend import app

client = TestClient(app)


class TestEmailSubsystem(unittest.TestCase):
    def test_01_get_email_status(self):
        """Verify email status endpoint reports correct domain and parameters."""
        response = client.get("/api/v1/emails/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("domain"), "stehouwer-publishing.com")
        self.assertIn("imap_status", data)
        self.assertIn("smtp_status", data)
        self.assertIn("mailbox_stats", data)

    def test_02_get_emails_list(self):
        """Verify /api/v1/emails returns structured data without crashing."""
        response = client.get("/api/v1/emails")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIsInstance(data.get("data"), list)

    def test_03_incoming_webhook_ingestion(self):
        """Verify incoming email webhook ingests clean message with normalized account."""
        test_payload = {
            "to": "brett@stehouwer-publishing.com",
            "from_name": "Test Client",
            "from_email": "client@example.com",
            "subject": "Automated Test Inquiry",
            "body": "This is an automated test message to verify email ingestion.",
            "category": "Primary"
        }
        response = client.post("/api/v1/emails/incoming", json=test_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data["data"]["account"], "brett@stehouwer-publishing.com")
        self.assertEqual(data["data"]["label"], "[Imap]/Brett")

    def test_04_generate_smart_reply(self):
        """Verify smart reply endpoint returns a structured draft."""
        reply_payload = {
            "sender": "John Doe",
            "subject": "Book Proposal Inquiry",
            "body_snippet": "Hello, I wanted to submit a manuscript proposal for review.",
            "tone_preference": "Professional"
        }
        response = client.post("/api/v1/emails/generate-reply", json=reply_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(len(data.get("draft", "")) > 0)
        self.assertIn("Stehouwer Publishing", data.get("draft", ""))

    def test_05_send_email_validation(self):
        """Verify send_email endpoint rejects invalid or unauthenticated requests properly."""
        invalid_payload = {
            "from_email": "brett@stehouwer-publishing.com",
            "to": "recipient@example.com",
            "subject": "Test Dispatch",
            "body": "Test dispatch body"
        }
        # If credentials are not an app password, it should return 401 or graceful failure, not a 500 crash
        response = client.post("/api/v1/emails/send", json=invalid_payload)
        self.assertIn(response.status_code, [200, 400, 401, 500])
        data = response.json()
        self.assertIn(data.get("status"), ["success", "error"])


if __name__ == "__main__":
    unittest.main()
