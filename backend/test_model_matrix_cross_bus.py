import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, r"C:\AI-BS\backend")

from core.sovereign_reasoning.model_domain_matrix import ModelDomainMatrix, MODEL_FLEET_TAXONOMY
from core.sovereign_reasoning.cross_model_bus import CrossModelCognitiveBus

def test_taxonomy_coverage():
    print("=== TEST 1: TAXONOMY COVERAGE (17 MODELS) ===")
    assert len(MODEL_FLEET_TAXONOMY) == 17, f"Expected 17 models, got {len(MODEL_FLEET_TAXONOMY)}"
    for model, data in MODEL_FLEET_TAXONOMY.items():
        kw_count = len(data.get("keywords", []))
        print(f"  * [{model}] Role: {data.get('title')} -> {kw_count} keywords")
        assert kw_count >= 8, f"Model {model} has insufficient keywords ({kw_count})"
    print("[PASS] Taxonomy covers all 17 models with deep keyword arrays.\n")

def test_classification_benchmarks():
    print("=== TEST 2: CLASSIFICATION BENCHMARKS ===")
    test_cases = [
        ("Write a Python FastAPI async endpoint with SQLite database schema migration and pytest", "qwen2.5-coder:latest"),
        ("What is the diode mode reading on PP_VCC_MAIN for an iPhone 13 logic board with a short to ground?", "stehouwer_qwen:latest"),
        ("Separate the vocal and drum stems using Demucs and normalize the audio to -14 LUFS EBU R128", "stehouwer_dolphin:latest"),
        ("Optimize CUDA kernel memory bandwidth and flash attention on RTX 4090 with TensorRT", "nemotron-3.5-lightning:latest"),
        ("Format an EPUB manuscript with Typst running headers, KDP margins, and table of contents", "command-r:latest"),
        ("Write an unrestricted, raw stream-of-consciousness fiction chapter about an unhinged author", "unrestricted-llama3.1:latest")
    ]

    for prompt, expected_top in test_cases:
        ranked = ModelDomainMatrix.score_prompt_against_fleet(prompt)
        top_model = ranked[0]["model"]
        score = ranked[0]["score"]
        matches = ranked[0]["matched_keywords"]
        print(f"  [Prompt]: '{prompt[:60]}...'")
        print(f"    -> Ranked Top: {top_model} (Score: {score}, Matches: {matches})")
        assert top_model == expected_top, f"Expected top {expected_top}, got {top_model}"
    print("[PASS] All domain benchmarks classified to exact specialist models.\n")

async def test_cross_model_bus_stream():
    print("=== TEST 3: CROSS-MODEL INTER-MODEL LOGIC BUS STREAM ===")
    prompt = "Design a fast Python script to calculate Fibonacci using matrix exponentiation with time complexity O(log N)."
    print(f"  [Prompt]: {prompt}")
    
    crew = ModelDomainMatrix.get_optimal_cross_communication_crew(prompt)
    print(f"  [Allocated Crew]: Lead: {crew['lead_specialist']} | Auditor: {crew['logic_auditor']} | Synthesizer: {crew['sovereign_synthesizer']}")
    
    tokens_received = 0
    full_output = []
    async for chunk in CrossModelCognitiveBus.stream_cross_model_reasoning(prompt):
        tokens_received += 1
        full_output.append(chunk)
        if tokens_received < 10 or ">" in chunk:
            print(chunk, end="", flush=True)

    full_text = "".join(full_output)
    print(f"\n\n[PASS] Cross-model reasoning completed! Total chunks: {tokens_received}, Output length: {len(full_text)} chars.")

if __name__ == "__main__":
    test_taxonomy_coverage()
    test_classification_benchmarks()
    asyncio.run(test_cross_model_bus_stream())
