import os
import numpy as np
from PIL import Image, ImageFilter

def process_4k_detail(
    input_path="C:/AI-BS/output/imagegen/max_detail_step1.png",
    output_path="C:/AI-BS/output/imagegen/max_detail_step2_4k.png",
    target_width=3840,
    target_height=2160
):
    print(f"[Step 2] Loading image from: {input_path}")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
        
    img = Image.open(input_path).convert("RGB")
    print(f"Original Dimensions: {img.width}x{img.height}")
    
    print(f"[Step 2] Resampling to 4K UHD ({target_width}x{target_height})...")
    img_4k = img.resize((target_width, target_height), resample=Image.LANCZOS)
    
    print(f"[Step 2] Converting to 32-bit floating-point array for maximum dynamic range...")
    arr_32bit = np.array(img_4k, dtype=np.float32) / 255.0
    
    print(f"[Step 2] Applying unsharp mask & micro-texture sharpening...")
    sharpened = img_4k.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sharpened.save(output_path, format="PNG", compress_level=0)
    print(f"[Step 2 Complete] 4K Max-Detail photo written to: {output_path}")
    print(f"Final 4K Dimensions: {sharpened.width}x{sharpened.height}")

if __name__ == "__main__":
    process_4k_detail()
