# Task: Local Hybrid Background Matting & Vision Processing Architecture

## Current Status
- [ ] Inspect Python environment dependencies and verify PyTorch / CUDA compatibility <!-- id: 0 -->
- [ ] Draft interactive implementation plan with Lifespan Singleton and ComfyUI Graph Schema <!-- id: 1 -->
- [ ] Await user explicit manual review and typed approval <!-- id: 2 -->
- [ ] Resolve OpenCV Haar Cascades missing data XMLs in `cv2/data/` and `backend/models/haarcascades/` <!-- id: 3 -->
- [ ] Safely install vision dependencies (`pillow`, `numpy`, `scikit-image`, `onnxruntime-gpu`, `rembg`, `timm`) without breaking CUDA / Torch <!-- id: 4 -->
- [ ] Implement `C:\AI-BS\backend\modules\vision_matting.py` with `LocalMattingEngine` and CUDA validation <!-- id: 5 -->
- [ ] Implement `C:\AI-BS\backend\routers\photo_studio.py` with FastAPI Lifespan Singleton and concrete ComfyUI graph injection <!-- id: 6 -->
- [ ] Register `photo_studio` router and lifespan singleton in `C:\AI-BS\backend\AI_BS_Backend.py` <!-- id: 7 -->
- [ ] Configure ComfyUI custom nodes (`ComfyUI-BiRefNet-ll`, `ComfyUI_UltimateSDUpscale`) and upscale models in `C:\AI-BS\ComfyUI` <!-- id: 8 -->
- [ ] Execute automated verification tests (`test_vision_matting.py` and direct FastAPI route tests) <!-- id: 9 -->
- [ ] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, bump version, and sync historical ledgers <!-- id: 10 -->
