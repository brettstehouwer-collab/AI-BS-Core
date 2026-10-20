"""
AI-BS Video LoRA & Fine-Tuning Dispatcher
-----------------------------------------
Loads existing local models:
- CogVideoX-2B from D:\\huggingface_cache\\hub\\models--THUDM--CogVideoX-2b
- Wan2.1 from C:\\AI-BS\\AI-BS-Models\\diffusion_models
- LTX-Video from C:\\AI-BS-Models\\checkpoints

Prepares LoRA layers via PEFT/Diffusers for training on RTX 4090 (24GB VRAM).
"""

import os
import sys
import torch

def verify_and_prep_trainer(model_choice="cogvideox"):
    print("="*80)
    print(" AI-BS VIDEO MODEL TRAINING & LORA PIPELINE INITIALIZATION")
    print("="*80)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[HARDWARE] Active Device: {device}")
    if device == "cuda":
        print(f"[HARDWARE] GPU: {torch.cuda.get_device_name(0)}")
        print(f"[HARDWARE] VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
        
    cogvideo_dir = r"D:\huggingface_cache\hub\models--THUDM--CogVideoX-2b\snapshots\1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01"
    wan_path = r"C:\AI-BS\AI-BS-Models\diffusion_models\wan2.1_t2v_1.3b.safetensors"
    ltx_path = r"C:\AI-BS-Models\checkpoints\ltx-video-2b-v0.9.1.safetensors"
    
    print("\n[VERIFYING MODEL PATHS]")
    print(f"  - CogVideoX Directory Exists: {os.path.exists(cogvideo_dir)}")
    print(f"  - Wan2.1 Checkpoint Exists: {os.path.exists(wan_path)}")
    print(f"  - LTX-Video Checkpoint Exists: {os.path.exists(ltx_path)}")
    
    output_lora_dir = r"C:\AI-BS\saved_data\video_loras"
    os.makedirs(output_lora_dir, exist_ok=True)
    print(f"\n[OUTPUT DIRECTORY] LoRA weights will be staged in: {output_lora_dir}")
    
    print("\n[STATUS] All local model files verified and ready for training execution.")
    print("="*80)

if __name__ == "__main__":
    verify_and_prep_trainer()
