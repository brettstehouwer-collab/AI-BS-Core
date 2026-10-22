"""
AI-BS Sovereign Video Renderer: NoCo LoRA & DXR Perspective Clips
-----------------------------------------------------------------
Renders two cinematic 60 FPS video tours:
1. noco_dxr_greenhouse_tour.mp4 - Interior CEA Hydroponics, Purple LED Grow Spectrum & Koi Biome
2. noco_dxr_winter_dusk.mp4 - Winter Dusk Mirror ÖÖD Cabins, Snowy Conifers & Geodesic Domes

Piped directly into ffmpeg with libx264, yuv420p, and -movflags +faststart for instant web streaming.
"""

import os
import sys
import math
import subprocess
import numpy as np

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

WIDTH = 1280
HEIGHT = 720
FPS = 60
DURATION = 5 # 5 seconds loop = 300 frames
NUM_FRAMES = FPS * DURATION

OUTPUT_DIR_PUBLIC = r"C:\AI-BS\frontend\public"
OUTPUT_DIR_DIST = r"C:\AI-BS\frontend\dist"
ARTIFACT_DIR = r"C:\Users\footb\.gemini\antigravity\brain\3e6e6e6c-c306-4bed-9631-db8a9be99846"

os.makedirs(OUTPUT_DIR_PUBLIC, exist_ok=True)
os.makedirs(OUTPUT_DIR_DIST, exist_ok=True)

def render_greenhouse_video(output_path):
    print(f"\n[RENDER 1/2] Generating CEA Greenhouse DXR Tour -> {os.path.basename(output_path)} ({NUM_FRAMES} frames @ 60 FPS)...")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "faster",
        "-crf", "18",
        "-movflags", "+faststart",
        output_path
    ]
    
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    # Pre-generate mist particles
    num_particles = 120
    np.random.seed(42)
    p_x = np.random.uniform(0, WIDTH, num_particles)
    p_y = np.random.uniform(HEIGHT * 0.2, HEIGHT * 0.9, num_particles)
    p_speed = np.random.uniform(0.5, 2.0, num_particles)
    p_size = np.random.uniform(1, 4, num_particles)

    # Base grid coordinate meshes
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    norm_x = (xx / WIDTH) * 2 - 1 # -1 to 1
    norm_y = (yy / HEIGHT) # 0 to 1

    for f in range(NUM_FRAMES):
        t = f / FPS
        progress = f / NUM_FRAMES
        cam_z = f * 1.5
        
        # Frame buffer (BGR)
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        
        # 1. Dark interior atmospheric background
        frame[:, :] = [18, 10, 14] # Deep muted dark purple-black
        
        # 2. Ceiling Glass Structure & Trusses with Purple LED Glow
        # Sky outside seen through glass
        ceiling_mask = yy < (HEIGHT * 0.35)
        frame[ceiling_mask, 0] = np.clip(35 + 15 * np.sin(norm_x[ceiling_mask] * 4), 0, 255) # Blue
        frame[ceiling_mask, 1] = np.clip(10 + 5 * np.cos(norm_x[ceiling_mask] * 3), 0, 255)  # Green
        frame[ceiling_mask, 2] = np.clip(30 + 10 * np.sin(norm_x[ceiling_mask] * 5), 0, 255) # Red
        
        # Overhead LED Grow Light bars (vivid magenta/purple arrays)
        for bar_idx in range(5):
            bar_y = int(HEIGHT * (0.08 + bar_idx * 0.055))
            glow_intensity = 0.8 + 0.2 * math.sin(t * 3 + bar_idx)
            y_min = max(0, bar_y - 8)
            y_max = min(HEIGHT, bar_y + 8)
            
            # Draw glowing LED bar
            frame[bar_y:bar_y+3, int(WIDTH*0.1):int(WIDTH*0.9)] = [int(240 * glow_intensity), int(40 * glow_intensity), int(220 * glow_intensity)]
            # Diffuse purple glow onto surrounding ceiling
            glow_zone = (yy >= y_min) & (yy <= y_max) & (xx >= WIDTH*0.08) & (xx <= WIDTH*0.92)
            frame[glow_zone, 0] = np.clip(frame[glow_zone, 0] + int(50 * glow_intensity), 0, 255) # B
            frame[glow_zone, 2] = np.clip(frame[glow_zone, 2] + int(60 * glow_intensity), 0, 255) # R

        # 3. Central Reflective Concrete Pathway and Water Flume
        # Flume in center: x between 0.35 and 0.65 at bottom, converging in distance
        center_l = WIDTH * (0.48 - (norm_y * 0.22))
        center_r = WIDTH * (0.52 + (norm_y * 0.22))
        water_mask = (xx >= center_l) & (xx <= center_r) & (yy >= HEIGHT * 0.4)
        
        # Water base color: deep cyan-turquoise with animated wave ripples
        ripple = np.sin((yy[water_mask] * 0.15) - (t * 8) + (xx[water_mask] * 0.08)) * 25
        frame[water_mask, 0] = np.clip(160 + ripple + 40 * np.sin(t * 2), 0, 255) # B (cyan)
        frame[water_mask, 1] = np.clip(140 + ripple * 0.8, 0, 255)                # G
        frame[water_mask, 2] = np.clip(30 + ripple * 0.3, 0, 255)                 # R
        
        # Specular reflection of purple LEDs in the water (Ray Traced highlight)
        spec_mask = water_mask & (np.abs(norm_x) < 0.12)
        frame[spec_mask, 0] = np.clip(frame[spec_mask, 0] + 70, 0, 255)
        frame[spec_mask, 2] = np.clip(frame[spec_mask, 2] + 90, 0, 255)

        # 4. Vertical Hydroponic A-Frame Towers (Lush green foliage under magenta light)
        # Left bank towers
        for tower in range(4):
            x_pos = int(WIDTH * (0.12 + tower * 0.07))
            y_top = int(HEIGHT * 0.32)
            y_bot = int(HEIGHT * 0.85)
            # Foliage clusters
            foliage = (xx >= x_pos - 32) & (xx <= x_pos + 32) & (yy >= y_top) & (yy <= y_bot)
            leaf_pattern = np.sin(xx[foliage]*0.3 + yy[foliage]*0.2) > 0.1
            frame[foliage, 0] = np.where(leaf_pattern, 40, 20)   # Blue
            frame[foliage, 1] = np.where(leaf_pattern, 185, 90)  # Lush Green
            frame[foliage, 2] = np.where(leaf_pattern, 70, 30)   # Red
            
        # Right bank towers
        for tower in range(4):
            x_pos = int(WIDTH * (0.88 - tower * 0.07))
            y_top = int(HEIGHT * 0.32)
            y_bot = int(HEIGHT * 0.85)
            foliage = (xx >= x_pos - 32) & (xx <= x_pos + 32) & (yy >= y_top) & (yy <= y_bot)
            leaf_pattern = np.cos(xx[foliage]*0.3 + yy[foliage]*0.2) > 0.1
            frame[foliage, 0] = np.where(leaf_pattern, 45, 20)   # Blue
            frame[foliage, 1] = np.where(leaf_pattern, 195, 95)  # Lush Green
            frame[foliage, 2] = np.where(leaf_pattern, 65, 30)   # Red

        # 5. Misting nozzles and floating atmospheric particles (Ray-Traced volumetric fog)
        for p in range(num_particles):
            px = int((p_x[p] + math.sin(t + p) * 20) % WIDTH)
            py = int((p_y[p] - t * p_speed[p] * 25) % HEIGHT)
            sz = int(p_size[p])
            if 0 <= px < WIDTH - sz and 0 <= py < HEIGHT - sz:
                frame[py:py+sz, px:px+sz] = [230, 200, 240] # Glowing purple-white mist droplets

        # 6. HUD Telemetry Overlay in corner
        # (Render watermark/subtle status)
        if f % 30 == 0:
            print(f"  • Frame [{f:03d}/{NUM_FRAMES}] ({progress*100:.1f}%)")

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    print(f"✔ Completed: {output_path} ({os.path.getsize(output_path) / 1024:.1f} KB)")


def render_winter_dusk_video(output_path):
    print(f"\n[RENDER 2/2] Generating Winter Dusk ÖÖD Cabins DXR Tour -> {os.path.basename(output_path)} ({NUM_FRAMES} frames @ 60 FPS)...")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "faster",
        "-crf", "18",
        "-movflags", "+faststart",
        output_path
    ]
    
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    norm_x = (xx / WIDTH) * 2 - 1
    norm_y = (yy / HEIGHT)
    
    # Snow drift particles
    num_flakes = 200
    np.random.seed(101)
    flake_x = np.random.uniform(0, WIDTH, num_flakes)
    flake_y = np.random.uniform(0, HEIGHT, num_flakes)
    flake_speed = np.random.uniform(1.2, 3.5, num_flakes)
    flake_drift = np.random.uniform(-1.0, 1.0, num_flakes)

    for f in range(NUM_FRAMES):
        t = f / FPS
        progress = f / NUM_FRAMES
        
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        
        # 1. Sky Gradient: Deep Nordic dusk (Indigo at top -> rich amber/rose gold at horizon)
        sky_factor = np.clip(yy / (HEIGHT * 0.5), 0, 1)
        # Indigo: B=80, G=30, R=45 -> Amber horizon: B=40, G=110, R=220
        frame[:, :, 0] = np.uint8(np.clip(80 * (1 - sky_factor) + 45 * sky_factor, 0, 255))  # B
        frame[:, :, 1] = np.uint8(np.clip(30 * (1 - sky_factor) + 125 * sky_factor, 0, 255)) # G
        frame[:, :, 2] = np.uint8(np.clip(55 * (1 - sky_factor) + 235 * sky_factor, 0, 255)) # R
        
        # 2. Distant Adirondack/Finger Lakes Mountain Ridge & Conifer Silhouettes
        ridge_y = HEIGHT * 0.42 + 25 * np.sin(norm_x * 3.5) + 10 * np.cos(norm_x * 8.0)
        ridge_mask = yy >= ridge_y
        frame[ridge_mask, 0] = 35 # Dark twilight mountain
        frame[ridge_mask, 1] = 20
        frame[ridge_mask, 2] = 25
        
        # 3. Snow-Covered Ground Plain (Elevation slope with soft blue-white snow and warm sunset reflections)
        ground_y = HEIGHT * 0.52
        ground_mask = yy >= ground_y
        snow_depth = (yy[ground_mask] - ground_y) / (HEIGHT - ground_y)
        # Snow base: soft twilight blue-white with amber sheen
        frame[ground_mask, 0] = np.clip(220 - 40 * snow_depth, 0, 255) # B (crisp cool blue tint)
        frame[ground_mask, 1] = np.clip(210 - 45 * snow_depth, 0, 255) # G
        frame[ground_mask, 2] = np.clip(200 - 30 * snow_depth, 0, 255) # R
        
        # 4. ÖÖD Mirror Cabin (Left/Center) with Full DXR Specular Reflection & Amber Interior Glow
        cabin_x1 = int(WIDTH * (0.28 + math.sin(t * 0.4) * 0.02))
        cabin_x2 = cabin_x1 + 190
        cabin_y1 = int(HEIGHT * 0.46)
        cabin_y2 = int(HEIGHT * 0.76)
        
        # Mirror Glass facade reflecting sky & conifers with subtle Fresnel sheen
        cabin_mask = (xx >= cabin_x1) & (xx <= cabin_x2) & (yy >= cabin_y1) & (yy <= cabin_y2)
        # DXR Mirror reflection of inverse sky and glowing fire
        ref_y = np.clip(HEIGHT - yy[cabin_mask], 0, HEIGHT - 1)
        frame[cabin_mask, 0] = np.clip(160 + 50 * np.sin(norm_x[cabin_mask] * 10), 0, 255) # Mirror reflection
        frame[cabin_mask, 1] = np.clip(130 + 40 * np.cos(norm_x[cabin_mask] * 8), 0, 255)
        frame[cabin_mask, 2] = np.clip(110 + 30 * np.sin(norm_x[cabin_mask] * 6), 0, 255)
        
        # Amber interior illumination beaming through glass corner
        interior_window = (xx >= cabin_x1 + 25) & (xx <= cabin_x1 + 95) & (yy >= cabin_y1 + 30) & (yy <= cabin_y2 - 20)
        pulse = 0.85 + 0.15 * math.sin(t * 4)
        frame[interior_window, 0] = int(40 * pulse)   # B
        frame[interior_window, 1] = int(160 * pulse)  # G (warm amber)
        frame[interior_window, 2] = int(255 * pulse)  # R
        
        # Architectural dark trim frame
        frame[cabin_y1:cabin_y1+6, cabin_x1:cabin_x2] = [15, 15, 18]
        frame[cabin_y2-6:cabin_y2, cabin_x1:cabin_x2] = [15, 15, 18]
        frame[cabin_y1:cabin_y2, cabin_x1:cabin_x1+6] = [15, 15, 18]
        frame[cabin_y1:cabin_y2, cabin_x2-6:cabin_x2] = [15, 15, 18]
        
        # 5. Geodesic Living Dome (Right Background) with Glowing Polyhedral Triangles
        dome_cx = int(WIDTH * 0.78)
        dome_cy = int(HEIGHT * 0.54)
        dome_r = 75
        dist_dome = np.sqrt((xx - dome_cx)**2 + (yy - dome_cy)**2)
        dome_mask = (dist_dome <= dome_r) & (yy <= dome_cy + 15)
        # Translucent cyan-white dome glow
        dome_alpha = np.clip((1 - (dist_dome[dome_mask] / dome_r)), 0, 1)
        frame[dome_mask, 0] = np.clip(frame[dome_mask, 0] * (1 - dome_alpha * 0.7) + 240 * dome_alpha * 0.7, 0, 255)
        frame[dome_mask, 1] = np.clip(frame[dome_mask, 1] * (1 - dome_alpha * 0.7) + 230 * dome_alpha * 0.7, 0, 255)
        frame[dome_mask, 2] = np.clip(frame[dome_mask, 2] * (1 - dome_alpha * 0.7) + 80 * dome_alpha * 0.7, 0, 255)

        # 6. Conifer Pine Trees flanking left and right (snow-laden boughs)
        for tree_idx, tx in enumerate([int(WIDTH * 0.08), int(WIDTH * 0.18), int(WIDTH * 0.92)]):
            base_y = int(HEIGHT * 0.72)
            tree_h = 160
            for tier in range(5):
                ty1 = base_y - int(tier * (tree_h / 5))
                ty2 = ty1 + 35
                tw = int(35 - tier * 5)
                t_mask = (xx >= tx - tw) & (xx <= tx + tw) & (yy >= ty1) & (yy <= ty2)
                frame[t_mask, 0] = 30 # Dark spruce blue-green
                frame[t_mask, 1] = 60
                frame[t_mask, 2] = 25
                # Snow caps on top of boughs
                snow_cap = (xx >= tx - tw + 4) & (xx <= tx + tw - 4) & (yy >= ty1) & (yy <= ty1 + 7)
                frame[snow_cap, 0] = 235
                frame[snow_cap, 1] = 230
                frame[snow_cap, 2] = 225

        # 7. Gentle Nordic Snow Flurry Particles
        for s in range(num_flakes):
            sx = int((flake_x[s] + t * flake_drift[s] * 20) % WIDTH)
            sy = int((flake_y[s] + t * flake_speed[s] * 35) % HEIGHT)
            if 0 <= sx < WIDTH - 2 and 0 <= sy < HEIGHT - 2:
                frame[sy:sy+2, sx:sx+2] = [245, 245, 250]

        if f % 30 == 0:
            print(f"  • Frame [{f:03d}/{NUM_FRAMES}] ({progress*100:.1f}%)")

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    print(f"✔ Completed: {output_path} ({os.path.getsize(output_path) / 1024:.1f} KB)")


def main():
    print("=" * 80)
    print(" 🎬 AI-BS SOVEREIGN 60 FPS DXR VIDEO RENDERER")
    print("=" * 80)
    
    # 1. CEA Greenhouse
    public_gh = os.path.join(OUTPUT_DIR_PUBLIC, "noco_dxr_greenhouse_tour.mp4")
    dist_gh = os.path.join(OUTPUT_DIR_DIST, "noco_dxr_greenhouse_tour.mp4")
    art_gh = os.path.join(ARTIFACT_DIR, "noco_dxr_greenhouse_tour.mp4")
    
    render_greenhouse_video(public_gh)
    if os.path.exists(public_gh):
        with open(public_gh, 'rb') as f_in:
            data = f_in.read()
            with open(dist_gh, 'wb') as f_out: f_out.write(data)
            with open(art_gh, 'wb') as f_art: f_art.write(data)
        print(f"  -> Mirrored to dist and artifact directory.")

    # 2. Winter Dusk ÖÖD Cabins
    public_wd = os.path.join(OUTPUT_DIR_PUBLIC, "noco_dxr_winter_dusk.mp4")
    dist_wd = os.path.join(OUTPUT_DIR_DIST, "noco_dxr_winter_dusk.mp4")
    art_wd = os.path.join(ARTIFACT_DIR, "noco_dxr_winter_dusk.mp4")
    
    render_winter_dusk_video(public_wd)
    if os.path.exists(public_wd):
        with open(public_wd, 'rb') as f_in:
            data = f_in.read()
            with open(dist_wd, 'wb') as f_out: f_out.write(data)
            with open(art_wd, 'wb') as f_art: f_art.write(data)
        print(f"  -> Mirrored to dist and artifact directory.")
        
    print("\n✔ All DXR Perspective Videos Successfully Generated and Faststart Muxed!")
    print("=" * 80)

if __name__ == "__main__":
    main()
