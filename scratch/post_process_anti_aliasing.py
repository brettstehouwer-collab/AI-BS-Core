import os
import cv2
import numpy as np

def apply_max_antialiasing(
    input_path="C:/AI-BS/output/imagegen/max_detail_step3_hdr4k.png",
    output_path="C:/AI-BS/output/imagegen/max_detail_step4_aa4k.png",
    supersample_factor=2.0
):
    print(f"[Step 4: Anti-Aliasing] Loading input image from: {input_path}")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    img_bgr = cv2.imread(input_path)
    if img_bgr is None:
        raise ValueError("Failed to read image with OpenCV")

    orig_h, orig_w = img_bgr.shape[:2]
    ss_w = int(orig_w * supersample_factor)
    ss_h = int(orig_h * supersample_factor)

    print(f"[Step 4: Anti-Aliasing] 1. Supersampling (SSAA {supersample_factor}x) to 8K resolution ({ss_w}x{ss_h})...")
    # Supersample to 8K using Lanczos interpolation to generate sub-pixel positions
    ss_img = cv2.resize(img_bgr, (ss_w, ss_h), interpolation=cv2.INTER_CUBIC)

    print(f"[Step 4: Anti-Aliasing] 2. Applying Sub-Pixel Gaussian Anti-Aliasing Edge Filter...")
    # Apply sub-pixel Gaussian anti-aliasing kernel to smooth pixel staircases
    aa_filtered = cv2.GaussianBlur(ss_img, (3, 3), sigmaX=0.6, sigmaY=0.6)

    print(f"[Step 4: Anti-Aliasing] 3. Downsampling back to 4K target with Area Anti-Aliasing integration...")
    # Downsample with INTER_AREA (box-average anti-aliasing filter)
    aa_final = cv2.resize(aa_filtered, (orig_w, orig_h), interpolation=cv2.INTER_AREA)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, aa_final, [int(cv2.IMWRITE_PNG_COMPRESSION), 0])
    
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[Step 4 Complete] Maximum Anti-Aliased 4K photo written to: {output_path}")
    print(f"Dimensions: {orig_w}x{orig_h} | Output Size: {file_size_mb:.2f} MB")

if __name__ == "__main__":
    apply_max_antialiasing()
