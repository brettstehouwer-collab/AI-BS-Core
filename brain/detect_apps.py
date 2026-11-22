import os
from PIL import Image
import numpy as np

frames_dir = r"C:\AI-BS\saved_data\video_inspect\latency_timing\detailed"
frames = sorted(os.listdir(frames_dir))

for idx, f in enumerate(frames):
    t_sec = idx * 2
    img_path = os.path.join(frames_dir, f)
    img = Image.open(img_path)
    
    # Check average color of top-left 100x100
    top_left = np.array(img.crop((0, 0, 100, 100)))
    mean_val = np.mean(top_left)
    
    # Check if suno (dark top left with suno logo) or aibs (red banner at top)
    # Red banner in AI-BS has high red channel in top 50 rows
    top_row = np.array(img.crop((100, 10, 300, 40)))
    r_mean = np.mean(top_row[:, :, 0])
    is_aibs = r_mean > 150 # Red banner
    
    app = "AI-BS DAW" if is_aibs else "SUNO Studio"
    print(f"[{t_sec:3d}s] ({f}): {app}")
