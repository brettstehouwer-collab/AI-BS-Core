import httpx
import base64
import sys

OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"
VISION_MODEL = "llava"


def test_llava(image_path):
    try:
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        print("Sending request to Ollama...")
        with httpx.Client(timeout=120.0) as client:
            payload = {
                "model": VISION_MODEL,
                "prompt": "Describe this image.",
                "images": [b64_img],
                "stream": False
            }
            r = client.post(OLLAMA_GENERATE_URL, json=payload)
            r.raise_for_status()
            print("Response:", r.json().get("response"))
            return True
    except Exception as e:
        print(f"Error testing llava: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_vision.py <path_to_image>")
        sys.exit(1)
    test_llava(sys.argv[1])
