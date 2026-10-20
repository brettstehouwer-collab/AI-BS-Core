import os
import sys

models_to_test = [
    # 1. Wan2.1
    ("Wan2.1 T2V 1.3B", r"C:\AI-BS\AI-BS-Models\diffusion_models\wan2.1_t2v_1.3b.safetensors"),
    ("Wan2.1 VAE (PTH)", r"C:\AI-BS\AI-BS-Models\vae\Wan2.1_VAE.pth"),
    ("Wan2.1 VAE (BF16)", r"C:\AI-BS\ComfyUI\models\vae\Wan2_1_VAE_bf16.safetensors"),
    
    # 2. LTX-Video
    ("LTX-Video 2B v0.9.1", r"C:\AI-BS-Models\checkpoints\ltx-video-2b-v0.9.1.safetensors"),
    ("LTX-Video 2B GGUF", r"C:\AI-BS\AI-BS-Models\unet\ltx-video-2b-v0.9.1-q8_0.gguf"),
    
    # 3. CogVideoX-2B
    ("CogVideoX-2B Transformer", r"D:\huggingface_cache\hub\models--THUDM--CogVideoX-2b\snapshots\1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01\transformer\diffusion_pytorch_model.safetensors"),
    ("CogVideoX-2B VAE", r"D:\huggingface_cache\hub\models--THUDM--CogVideoX-2b\snapshots\1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01\vae\diffusion_pytorch_model.safetensors"),
    
    # 4. Encoders & Vision
    ("SigLIP Vision Patch14", r"C:\AI-BS\AI-BS-Models\clip_vision\sigclip_vision_patch14_384.safetensors"),
    ("Qwen3-VL 4B Vision LLM", r"C:\AI-BS\ComfyUI\models\LLM\qwen3vl_4b_fp8_scaled.safetensors"),
    ("T5-XXL FP16", r"C:\AI-BS\AI-BS-Models\clip\t5xxl_fp16.safetensors"),
    ("UMT5-XXL BF16", r"C:\AI-BS\AI-BS-Models\clip\umt5-xxl-enc-bf16.pth"),
    
    # 5. Motion & ControlNet
    ("AnimateDiff v3 Motion", r"C:\AI-BS\AI-BS-Models\animatediff_models\v3_sd15_mm.ckpt"),
    ("ControlNet Tile SD15", r"C:\AI-BS-Models\controlnet\control_v11f1e_sd15_tile.pth"),
]

results = []

for name, path in models_to_test:
    if not os.path.exists(path):
        results.append({"name": name, "path": path, "status": "MISSING", "error": "Path does not exist"})
        continue
    
    size_mb = os.path.getsize(path) / (1024 * 1024)
    status = "UNKNOWN"
    err_msg = ""
    
    try:
        if path.endswith(".safetensors"):
            import safetensors
            with safetensors.safe_open(path, framework="pt", device="cpu") as f:
                keys = f.keys()
                status = f"VALID ({len(keys)} tensors, {size_mb:.1f} MB)"
        elif path.endswith(".pth") or path.endswith(".ckpt") or path.endswith(".pt"):
            import torch
            try:
                # Load header/state dict with map_location cpu
                data = torch.load(path, map_location="cpu", weights_only=False)
                if isinstance(data, dict):
                    status = f"VALID (PyTorch Dict with {len(data)} keys, {size_mb:.1f} MB)"
                else:
                    status = f"VALID (PyTorch object {type(data).__name__}, {size_mb:.1f} MB)"
            except Exception as e:
                # Some weights are pure state dicts or need weights_only=False
                status = f"LOAD_ERROR: {str(e)[:100]}"
        elif path.endswith(".gguf"):
            # Verify GGUF magic header 'GGUF'
            with open(path, "rb") as gf:
                header = gf.read(4)
                if header == b"GGUF":
                    status = f"VALID (GGUF magic verified, {size_mb:.1f} MB)"
                else:
                    status = f"CORRUPT (Bad magic header: {header})"
        else:
            status = f"CHECKED ({size_mb:.1f} MB)"
    except Exception as ex:
        status = f"CORRUPT: {str(ex)[:120]}"
    
    results.append({"name": name, "path": path, "status": status})

print("\n" + "="*80)
print(" AI-BS VIDEO & AI MODEL CORRUPTION / INTEGRITY AUDIT")
print("="*80)
for r in results:
    print(f"[{r['name']}] -> {r['status']}")
print("="*80)
