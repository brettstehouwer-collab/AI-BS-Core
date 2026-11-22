import os
import shutil

base_dest = r"C:\Users\footb\AI-BS\ComfyUI\ComfyUI\models"
base_src = r"C:\Users\footb\AI-BS"

moves = {
    "RealESRGAN_x4plus.safetensors": r"upscale_models\RealESRGAN_x4plus.safetensors",
    "Wan2_1_VAE_bf16.safetensors": r"vae\Wan2_1_VAE_bf16.safetensors",
    "clip_vision_h.safetensors": r"clip_vision\clip_vision_h.safetensors",
    "umt5_xxl_fp16.safetensors": r"clip\umt5_xxl_fp16.safetensors",
    "ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors": r"loras\ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors",
    "gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors": r"loras\gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors",
    "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors": r"unet\lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors",
    "seedvr2_3b_int8_convrot.safetensors": r"unet\seedvr2_3b_int8_convrot.safetensors",
    "gemma_3_12B_it_fp4_mixed.safetensors": r"unet\gemma_3_12B_it_fp4_mixed.safetensors",
    "wan2.2_dancer_14b_global_fp8_scaled.safetensors": r"unet\wan2.2_dancer_14b_global_fp8_scaled.safetensors",
    "wan2.2_dancer_14b_local_fp8_scaled.safetensors": r"unet\wan2.2_dancer_14b_local_fp8_scaled.safetensors",
    "ltx-2.3-22b-distilled-fp8.safetensors": r"unet\ltx-2.3-22b-distilled-fp8.safetensors",
}

for src_name, dest_rel in moves.items():
    src_path = os.path.join(base_src, src_name)
    dest_path = os.path.join(base_dest, dest_rel)
    if os.path.exists(src_path):
        print(f"Moving {src_name} to {dest_rel}")
        shutil.move(src_path, dest_path)

dup_path = os.path.join(base_src, "RealESRGAN_x4plus (1).safetensors")
if os.path.exists(dup_path):
    print("Removing duplicate")
    os.remove(dup_path)
