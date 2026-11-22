import os
import urllib.request
import subprocess

downloads = [
    ("https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", r"C:\Users\footb\AI-BS\ComfyUI\ComfyUI\models\clip\umt5_xxl_fp8_e4m3fn_scaled.safetensors"),
    ("https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", r"C:\Users\footb\AI-BS\ComfyUI\ComfyUI\models\loras\wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"),
    ("https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", r"C:\Users\footb\AI-BS\ComfyUI\ComfyUI\models\loras\wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"),
    ("https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", r"C:\Users\footb\AI-BS\ComfyUI\ComfyUI\models\diffusion_models\wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"),
    ("https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", r"C:\Users\footb\AI-BS\ComfyUI\ComfyUI\models\diffusion_models\wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"),
]

sizes = []
for url, dest in downloads:
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req) as response:
            size = int(response.headers.get('Content-Length', 0))
            sizes.append((size, url, dest))
    except Exception as e:
        print(f"Error fetching header for {url}: {e}")
        sizes.append((0, url, dest))

# Sort largest to smallest
sizes.sort(key=lambda x: x[0], reverse=True)

print("Starting Sequential Download via CURL...")
for size, url, dest in sizes:
    size_gb = size / (1024 * 1024 * 1024)
    print(f"\n======================================")
    print(f"Downloading: {os.path.basename(dest)} ({size_gb:.2f} GB)")
    print(f"======================================")
    subprocess.run(["curl.exe", "-L", "-o", dest, url])

print("\nAll downloads completed sequentially!")
