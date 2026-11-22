import os
from PIL import Image

frames_dir = r"C:\AI-BS\saved_data\video_inspect\latency_timing\detailed"

# Let's inspect sec_005 (10s), sec_015 (30s), sec_025 (50s) in AI-BS
# and sec_035 (70s), sec_045 (90s) in Suno
crops_dir = r"C:\AI-BS\saved_data\video_inspect\latency_timing\crops"
os.makedirs(crops_dir, exist_ok=True)

# In AI-BS (Wave Studio & Multimedia):
# Crop transport bar (top left controls) and waveform / playhead
img_aibs = Image.open(os.path.join(frames_dir, "sec_005.jpg"))
# Transport bar: y from 160 to 220
transport = img_aibs.crop((0, 160, 1280, 220))
transport.save(os.path.join(crops_dir, "aibs_transport.jpg"))

# Waveform info: y from 260 to 360
wave_info = img_aibs.crop((0, 260, 1280, 420))
wave_info.save(os.path.join(crops_dir, "aibs_wave_info.jpg"))

# In Suno:
img_suno = Image.open(os.path.join(frames_dir, "sec_040.jpg"))
# Top bar: y from 0 to 80
suno_top = img_suno.crop((0, 0, 1280, 80))
suno_top.save(os.path.join(crops_dir, "suno_top.jpg"))

# Suno timeline: y from 80 to 220
suno_timeline = img_suno.crop((0, 80, 1280, 220))
suno_timeline.save(os.path.join(crops_dir, "suno_timeline.jpg"))

print("Saved crops successfully.")
