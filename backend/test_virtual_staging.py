import httpx
import asyncio
import base64
from io import BytesIO
from PIL import Image


async def test_virtual_staging():
    print("Generating a test blank image (512x512) for staging...")
    img = Image.new("RGB", (512, 512), color=(200, 200, 200))
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    base_url = "http://127.0.0.1:8000/api/clients/joey_hamilton/virtual-staging"

    print("\n--- TEST 1: STILL IMAGE GENERATION ---")
    payload_image = {
        "image_base64": img_str,
        "style": "Modern Farmhouse",
        "room_type": "Living Room",
        "custom_prompt": "A modern farmhouse living room with bright lighting.",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("Sending POST request to /generate ...")
            res_img = await client.post(f"{base_url}/generate", json=payload_image)
            print(f"Status Code: {res_img.status_code}")
            print(f"Response: {res_img.text}")
        except Exception as e:
            print(f"Error testing image generation: {e}")

    print("\n--- TEST 2: VIDEO TOUR GENERATION ---")
    payload_video = {
        "image_base64": img_str,
        "custom_prompt": "Cinematic pan around the room",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("Sending POST request to /video-tour ...")
            res_vid = await client.post(f"{base_url}/video-tour", json=payload_video)
            print(f"Status Code: {res_vid.status_code}")
            print(f"Response: {res_vid.text}")
        except Exception as e:
            print(f"Error testing video generation: {e}")


if __name__ == "__main__":
    asyncio.run(test_virtual_staging())
