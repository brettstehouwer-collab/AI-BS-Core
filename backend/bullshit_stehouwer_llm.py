import time


def main():
    print("[StehouwerLLM] Local Fallback System initialized.")
    print("[StehouwerLLM] Awaiting connection from Antigravity daemon.")

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("[StehouwerLLM] Shutting down.")


if __name__ == "__main__":
    main()
