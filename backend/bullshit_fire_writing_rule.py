import threading
import time


def formatting_daemon():
    while True:
        try:
            # Perform any necessary formatting or monitoring tasks here
            print(
                "[FireWritingRule] Monitoring Brett's creative output for structural correctness."
            )
            time.sleep(3600)
        except KeyboardInterrupt:
            print("[FireWritingRule] Shutting down.")


if __name__ == "__main__":
    daemon = threading.Thread(target=formatting_daemon)
    daemon.daemon = True  # Allow the daemon to exit when the main program ends
    daemon.start()
