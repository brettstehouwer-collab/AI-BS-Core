import os
from PIL import Image
import numpy as np

frames_dir = r"C:\AI-BS\saved_data\video_inspect\latency_timing\detailed"
frames = sorted(os.listdir(frames_dir))

for idx in range(0, len(frames), 2): # every 4 seconds
    f = frames[idx]
    t = idx * 2
    img = Image.open(os.path.join(frames_dir, f))
    # Sample center pixel color and top-left pixel color
    top_color = img.getpixel((20, 20))
    center_color = img.getpixel((img.width // 2, img.height // 2))
    
    # Check if there is red banner at (500, 20)
    banner_color = img.getpixel((500, 20))
    print(f"[{t:3d}s] {f}: banner_color={banner_color}, center_color={center_color}")
