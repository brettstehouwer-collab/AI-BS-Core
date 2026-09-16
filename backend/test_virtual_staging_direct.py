import asyncio
import base64
from io import BytesIO
from PIL import Image
import sys
import os

# Ensure modules are in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import virtual_staging_engine


async def test_virtual_staging_direct():
    print("Generating a test blank image (512x512) for staging...")
    img = Image.new("RGB", (512, 512), color=(200, 200, 200))
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    print("\n--- TEST 1: STILL IMAGE GENERATION ---")
    try:
        res_img = await virtual_staging_engine.generate_virtual_staging(
            image_base64=img_str,
            style="Modern Farmhouse",
            room_type="Living Room",
            custom_prompt="A modern farmhouse living room with bright lighting.",
        )
        print(f"Result: {res_img}")
    except Exception as e:
        print(f"Error testing image generation: {e}")

    print("\n--- TEST 2: VIDEO TOUR GENERATION ---")
    try:
        res_vid = await virtual_staging_engine.generate_video_tour(
            image_base64=img_str, custom_prompt="Cinematic pan around the room"
        )
        print(f"Result: {res_vid}")
    except Exception as e:
        print(f"Error testing video generation: {e}")


if __name__ == "__main__":
    asyncio.run(test_virtual_staging_direct())
