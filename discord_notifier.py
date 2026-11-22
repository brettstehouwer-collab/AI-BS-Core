import os

import requests

from backend.core.outbound_messaging_policy import outbound_messaging_enabled


WEBHOOK_FILE = "C:\\AI-BS\\.discord_webhook.txt"


def send_discord_update(message: str):
    """Send only after explicit channel activation; disabled never reads secrets."""
    if not outbound_messaging_enabled("discord"):
        return False
    if not os.path.exists(WEBHOOK_FILE):
        return False

    try:
        with open(WEBHOOK_FILE, "r", encoding="utf-8") as webhook_file:
            webhook_url = webhook_file.read().strip()
        if not webhook_url or not webhook_url.startswith(("https://", "http://")):
            return False

        response = requests.post(
            webhook_url,
            json={"content": f"**[AI-BS OS Update]**: {message}"},
            timeout=(3.05, 10.0),
            allow_redirects=False,
        )
        return response.status_code in (200, 204)
    except Exception as error:
        # Exceptions can contain a webhook credential or message contents.
        print(f"Discord notification failed ({type(error).__name__}).")
        return False


if __name__ == "__main__":
    send_discord_update("AI-BS Notification System Initialized.")
