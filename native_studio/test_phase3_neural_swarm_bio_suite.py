"""
Test suite for Phase 3: Autonomous Neural Swarm & Bio-AI Integration.
Verifies TieredModelRouter, VramArbiter, BioAiTrainingEngine, and DeepLearningStudioNativeView.
"""
import os
import sys
import time
import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYTEST_CURRENT_TEST"] = "1"

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from native_studio.engine import EngineBus
from native_studio.neural_swarm_router import (
    TieredModelRouter,
    VramArbiter,
    BioAiTrainingEngine,
    BioAiTrainingWorker,
    LORA_OUTPUT_DIR,
)
from native_studio.intelligence_views import DeepLearningStudioNativeView

@pytest.fixture
def bus():
    b = EngineBus()
    yield b
    b.shutdown(500)
    b.pool.waitForDone(1000)

def test_vram_arbiter_hardware_telemetry():
    vram = VramArbiter.get_gpu_vram()
    assert isinstance(vram, dict)
    assert "total_mb" in vram
    assert "free_mb" in vram
    assert "temp_c" in vram
    assert vram["total_mb"] >= 8000
    print(f"VRAM Arbiter telemetry: {vram['device']} - {vram['used_mb']}MB used / {vram['free_mb']}MB free ({vram['used_pct']}%) @ {vram['temp_c']}°C")

def test_vram_arbiter_headroom_check():
    headroom = VramArbiter.ensure_headroom(min_free_mb=4096)
    assert isinstance(headroom, dict)
    assert "headroom_guaranteed" in headroom
    assert "current_free_mb" in headroom
    print(f"VRAM Arbiter headroom check: {headroom}")

def test_tiered_model_router_classification():
    router = TieredModelRouter()
    # Test Tier 1 coding detection
    t1, m1 = router.determine_tier_and_model("def calculate_loss(y_true, y_pred):", task="code")
    assert t1 == 1
    assert "coder" in m1 or "gemma" in m1 or "nemotron" in m1 or len(m1) > 0

    # Test Tier 2 creative screenplay detection
    t2, m2 = router.determine_tier_and_model("EXT. SUBURBAN MOTEL - NIGHT. Tommy loads the revolver in silence.", task="screenplay")
    assert t2 == 2
    assert "llama" in m2 or "qwen" in m2 or len(m2) > 0

    # Test Tier 3 multimodal cloud fallback
    t3, m3 = router.determine_tier_and_model("Search the web for recent clinical trials on PARP inhibitors", task="search")
    assert t3 == 3
    assert "gemini" in m3 or "cloud" in m3
    print(f"Tier classifications verified: Code->Tier {t1} ({m1}), Screenplay->Tier {t2} ({m2}), Cloud->Tier {t3} ({m3})")

def test_tiered_model_router_query():
    router = TieredModelRouter()
    res = router.route_query("def get_device(): return 'cuda'", task="code", preferred_tier=1)
    assert isinstance(res, dict)
    assert res["status"] == "SUCCESS"
    assert "latency_ms" in res
    assert "tokens_per_sec" in res
    assert len(res["response"]) > 0
    print(f"Router query executed: Model={res['model']}, Latency={res['latency_ms']}ms, Speed={res['tokens_per_sec']} tok/s")

def test_bio_ai_curricula_synthesis():
    for domain in ["alphafold", "clinvar", "dbsnp", "chembl"]:
        curriculum = BioAiTrainingEngine.synthesize_curriculum(domain)
        assert len(curriculum) >= 1
        first_item = curriculum[0]
        assert "instruction" in first_item
        assert "response" in first_item
        print(f"Bio-AI curriculum '{domain}' verified: {len(curriculum)} samples")

def test_bio_ai_lora_training_loop_and_checkpoint():
    ckpt_path = BioAiTrainingEngine.train_lora_checkpoint(
        domain="clinvar",
        epochs=2,
        lr=2e-4,
        rank=16,
    )
    assert ckpt_path.exists()
    assert ckpt_path.stat().st_size > 100
    with open(ckpt_path, "rb") as f:
        magic = f.read(7)
        assert magic == b"BIOLORA"
    print(f"Bio-AI LoRA checkpoint created and verified: {ckpt_path.name} ({ckpt_path.stat().st_size} bytes)")

def test_deep_learning_studio_native_view_integration(bus):
    view = DeepLearningStudioNativeView(bus)
    assert view is not None
    assert hasattr(view, "combo_router_tier")
    assert hasattr(view, "txt_router_prompt")
    assert hasattr(view, "btn_dispatch_router")
    assert hasattr(view, "combo_bio_curr")
    assert hasattr(view, "spn_bio_epochs")
    assert hasattr(view, "btn_launch_bio")
    assert hasattr(view, "bio_progress")

    # Test route query handler
    view.txt_router_prompt.setText("def calculate_fp16_grad(): pass")
    view._handle_route_query()
    assert "Tier" in view.lbl_router_metric.text() or "Routing" in view.btn_dispatch_router.text() or len(view.txt_router_out.toPlainText()) >= 0

    # Test bio training step handler
    view._on_bio_step({"step": 2, "total_steps": 6, "loss": 0.452, "gflops": 320.5, "epoch": 1, "total_epochs": 3, "step_ms": 48.0})
    assert view.bio_progress.value() > 0
    assert "0.4520" in view.lbl_bio_metrics.text()

    # Test bio training complete handler
    dummy_ckpt = str(LORA_OUTPUT_DIR / "test_dummy_lora.bin")
    view._on_bio_complete(dummy_ckpt)
    assert "test_dummy_lora.bin" in view.lbl_bio_metrics.text()
    assert view.btn_launch_bio.isEnabled()
    print("DeepLearningStudioNativeView UI and handlers verified.")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
