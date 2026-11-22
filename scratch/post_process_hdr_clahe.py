import os
import cv2
import numpy as np
from PIL import Image

def apply_hdr_clahe_pass(
    input_path="C:/AI-BS/output/imagegen/max_detail_step2_4k.png",
    output_path="C:/AI-BS/output/imagegen/max_detail_step3_hdr4k.png"
):
    print(f"[Step 3] Loading 4K image from: {input_path}")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Read image using OpenCV (BGR format)
    img_bgr = cv2.imread(input_path)
    if img_bgr is None:
        raise ValueError("Failed to load image with OpenCV")

    print(f"Dimensions: {img_bgr.shape[1]}x{img_bgr.shape[0]}")

    print(f"[Step 3] Converting RGB to LAB color space for luminance isolation...")
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    print(f"[Step 3] Applying Contrast Limited Adaptive Histogram Equalization (CLAHE)...")
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)

    print(f"[Step 3] Merging enhanced LAB channels and converting back to BGR...")
    limg = cv2.merge((cl, a_channel, b_channel))
    enhanced_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    print(f"[Step 3] Applying Edge-Preserving Bilateral Denoising Filter...")
    denoised_bgr = cv2.bilateralFilter(enhanced_bgr, d=5, sigmaColor=25, sigmaSpace=25)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, denoised_bgr, [int(cv2.IMWRITE_PNG_COMPRESSION), 0])
    
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[Step 3 Complete] HDR 4K Max-Detail photo written to: {output_path}")
    print(f"Final Size: {file_size_mb:.2f} MB")

if __name__ == "__main__":
    apply_hdr_clahe_pass()
