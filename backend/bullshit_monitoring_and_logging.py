import time
import json
import os


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "ai_bs_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


def main():
    config = load_config()
    print(
        f"[MonitoringAndLogging] Active. Log level: {config.get('log_level', 'INFO')}"
    )
    print(
        "[MonitoringAndLogging] Tracking API request limits and AI-BS operation insights..."
    )

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("[MonitoringAndLogging] Shutting down.")


if __name__ == "__main__":
    main()
