import cv2
import os
import numpy as np

video_path = r"C:\Users\footb\Videos\NativefFuntionVsWebFunction.mp4"
out_dir = r"C:\Users\footb\.gemini\antigravity\brain\3e6e6e6c-c306-4bed-9631-db8a9be99846\video_frames"
os.makedirs(out_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps

print(f"Total duration: {duration:.1f}s, fps: {fps}, total frames: {total_frames}")

# Sample every 15 seconds
sample_interval_sec = 15
timestamps = list(range(5, int(duration), sample_interval_sec))
print(f"Sampling {len(timestamps)} frames at intervals of {sample_interval_sec}s...")

extracted = []
for sec in timestamps:
    frame_idx = int(sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if ret:
        m, s = divmod(sec, 60)
        time_str = f"{m:02d}m{s:02d}s"
        out_name = f"frame_{sec:04d}s_{time_str}.jpg"
        out_path = os.path.join(out_dir, out_name)
        # Resize slightly to keep under limit and fast viewing, e.g., width 1280
        h, w = frame.shape[:2]
        new_w = 1280
        new_h = int(h * (new_w / w))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(out_path, resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        extracted.append((sec, time_str, out_path))

cap.release()
print(f"Successfully extracted {len(extracted)} frames into {out_dir}")
