"""
AI-BS Vision Matting & Photo Studio Automated Verification Suite
----------------------------------------------------------------
Tests:
1. OpenCV Haar Cascade classifier resolution and eye/face detection.
2. LocalMattingEngine initialization and CUDA execution provider verification.
3. Synthetic image foreground extraction and alpha mask generation.
4. FastAPI Photo Studio router endpoints (/health, /models, /process-matte).
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from PIL import Image, ImageDraw

def test_haar_cascades():
    print("\n--- [TEST 1: OpenCV Haar Cascades Resolution] ---")
    import cv2
    from aibs_opencv_tracker import AIBSIOpenCVTracker
    
    tracker = AIBSIOpenCVTracker()
    assert tracker.face_cascade is not None, "Face cascade is None!"
    assert not tracker.face_cascade.empty(), "Face cascade classifier is empty!"
    assert tracker.eye_cascade is not None, "Eye cascade is None!"
    assert not tracker.eye_cascade.empty(), "Eye cascade classifier is empty!"
    
    print("SUCCESS: Face and Eye cascades loaded and verified not empty.")


def test_direct_matting_engine():
    print("\n--- [TEST 2: LocalMattingEngine Direct CUDA Execution] ---")
    from modules.vision_matting import get_matting_engine
    
    engine = get_matting_engine("birefnet-general")
    telemetry = engine.get_runtime_telemetry()
    print("Engine Telemetry:", telemetry)
    
    assert telemetry["status"] == "READY", f"Engine status is {telemetry['status']}"
    assert telemetry["active_provider"] == "CUDAExecutionProvider", f"Expected CUDAExecutionProvider, got {telemetry['active_provider']}"
    
    # Create test image (300x300 canvas with a distinct red circle on yellow background)
    test_dir = r"C:\AI-BS\models\rembg"
    test_in = os.path.join(test_dir, "verify_input.png")
    test_out_matte = os.path.join(test_dir, "verify_out_matte.png")
    test_out_mask = os.path.join(test_dir, "verify_out_mask.png")
    
    img = Image.new("RGB", (300, 300), color=(255, 215, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((50, 50, 250, 250), fill=(220, 20, 60))
    img.save(test_in)
    
    # 1. Test foreground extraction
    t0 = time.time()
    out1 = engine.extract_foreground(test_in, test_out_matte, alpha_matting=True)
    matte_ms = (time.time() - t0) * 1000.0
    print(f"Foreground extracted in {matte_ms:.1f}ms -> {out1}")
    
    assert os.path.exists(out1), "Matte output file does not exist!"
    with Image.open(out1) as res:
        assert res.mode == "RGBA", f"Expected RGBA mode, got {res.mode}"
        assert res.size == (300, 300), f"Expected (300, 300), got {res.size}"
    
    # 2. Test mask only generation
    t1 = time.time()
    out2 = engine.generate_mask_only(test_in, test_out_mask)
    mask_ms = (time.time() - t1) * 1000.0
    print(f"Mask generated in {mask_ms:.1f}ms -> {out2}")
    
    assert os.path.exists(out2), "Mask output file does not exist!"
    
    # Cleanup temp files
    for p in [test_in, test_out_matte, test_out_mask]:
        if os.path.exists(p):
            os.remove(p)
            
    print("SUCCESS: Direct CUDA matting and alpha masking verified.")


async def test_fastapi_photo_studio_router():
    print("\n--- [TEST 3: FastAPI Photo Studio Router Integration] ---")
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from routers.photo_studio import router as photo_studio_router
    from modules.vision_matting import get_matting_engine
    
    app = FastAPI()
    app.include_router(photo_studio_router)
    # Attach lifespan singleton
    app.state.matting_engine = get_matting_engine("birefnet-general")
    
    client = TestClient(app)
    
    # 1. Health check
    res = client.get("/api/photo-studio/health", headers={"X-Client-ID": "stehouwer_publishing"})
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health_data = res.json()
    print("Health Data:", health_data)
    assert health_data["status"] == "HEALTHY"
    assert health_data["cuda_accelerated"] is True
    assert health_data["client_id"] == "stehouwer_publishing"
    
    # 2. List models
    res_models = client.get("/api/photo-studio/models")
    assert res_models.status_code == 200
    models_data = res_models.json()
    assert len(models_data["models"]) >= 3
    print(f"Models endpoint OK: {len(models_data['models'])} models listed.")
    
    # 3. Direct GPU matting via HTTP POST
    test_dir = r"C:\AI-BS\models\rembg"
    test_in = os.path.join(test_dir, "router_test_in.png")
    test_out = os.path.join(test_dir, "router_test_out.png")
    
    img = Image.new("RGB", (200, 200), color=(0, 128, 128))
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, 160, 160), fill=(255, 255, 255))
    img.save(test_in)
    
    req_payload = {
        "input_path": test_in,
        "output_path": test_out,
        "mode": "direct_gpu",
        "alpha_matting": True
    }
    
    post_res = client.post("/api/photo-studio/process-matte", json=req_payload, headers={"X-Client-ID": "stehouwer_publishing"})
    assert post_res.status_code == 200, f"Process matte failed: {post_res.text}"
    post_data = post_res.json()
    print("Process Matte Response:", post_data)
    assert post_data["status"] == "SUCCESS"
    assert post_data["engine"] == "Direct-CUDA"
    assert "CUDA" in post_data["active_provider"]
    assert os.path.exists(test_out)
    
    # Cleanup
    for p in [test_in, test_out]:
        if os.path.exists(p):
            os.remove(p)
            
    print("SUCCESS: FastAPI Photo Studio Router integration fully verified.")


if __name__ == "__main__":
    print("======================================================================")
    print("AI-BS LOCAL HYBRID VISION & MATTING AUTOMATED VERIFICATION SUITE")
    print("======================================================================")
    
    test_haar_cascades()
    test_direct_matting_engine()
    asyncio.run(test_fastapi_photo_studio_router())
    
    print("\n======================================================================")
    print("ALL TESTS PASSED: 100% OPERATIONAL WITH CUDA ACCELERATION")
    print("======================================================================")
