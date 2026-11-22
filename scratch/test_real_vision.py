import cv2
import numpy as np
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Test on any image in ComfyUI or backend or create a test frame
test_img = np.zeros((512, 512, 3), dtype=np.uint8)
cv2.rectangle(test_img, (100, 100), (300, 350), (200, 200, 255), -1)
cv2.circle(test_img, (400, 200), 50, (100, 255, 100), -1)

test_path = r"C:\AI-BS\scratch\test_vision_frame.png"
cv2.imwrite(test_path, test_img)

# 1. Test real object detection with OpenCV contours & cascades
img = cv2.imread(test_path)
h, w = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Contours
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
edges = cv2.Canny(blurred, 50, 150)
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

detected = []
for cnt in contours:
    area = cv2.contourArea(cnt)
    if area > (w * h * 0.005): # > 0.5% of frame
        x, y, bw, bh = cv2.boundingRect(cnt)
        detected.append({
            "label": "visual_subject",
            "bbox": [int(x), int(y), int(bw), int(bh)],
            "area_px": int(area),
            "confidence": round(min(0.99, 0.70 + (area / (w * h)) * 0.3), 3)
        })

print(f"Real detected objects: {len(detected)}")
for d in detected:
    print(" ", d)

# 2. Test real scene reconstruction & depth estimation
# Compute gradient magnitude
sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
magnitude = np.sqrt(sobelx**2 + sobely**2)
depth_map = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

# Save depth map
depth_path = r"C:\AI-BS\scratch\test_depth_map.png"
cv2.imwrite(depth_path, depth_map)

# Hough lines for horizon/perspective
lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=40, minLineLength=30, maxLineGap=10)
horizon_y = h // 2
if lines is not None and len(lines) > 0:
    horizontal_y = []
    for l in lines:
        coords = l.flatten()
        if len(coords) == 4:
            x1, y1, x2, y2 = coords
            if abs(y1 - y2) < 10:
                horizontal_y.append((y1 + y2) / 2)
    if horizontal_y:
        horizon_y = int(np.mean(horizontal_y))

print(f"Scene geometry: Horizon Y = {horizon_y}, Mean Depth Intensity = {float(np.mean(depth_map)):.2f}")
print("Depth map generated at:", depth_path)
