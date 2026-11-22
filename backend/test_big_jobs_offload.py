import httpx
import json
import os
import time

def test_streaming_big_job():
    print("=== Testing Big Job Streaming Endpoint & Memory Offload ===")
    url = "http://127.0.0.1:8080/api/v1/hybrid-chat/stream"
    
    # Generate a large test prompt (>4,000 characters)
    scientific_directive = (
        "Directive: Analyze the structural dynamics, variant pathogenicity, and clinical implications of "
        "BRCA1 (UniProt P38398) missense mutation C61G (rs28897672) within the RING finger domain (residues 1-100). "
        "Detail the zinc-coordination disruption, pLDDT confidence alterations, BARD1 heterodimer destabilization, "
        "and therapeutic sensitivity to PARP inhibitors (Olaparib, Talazoparib). Provide comprehensive breakdown."
    )
    large_payload_prompt = scientific_directive + "\n\n" + ("\n- Synthetic verification block with extensive multi-modal bio-intelligence parameters to assert uncapped input context and automatic disk offloading." * 40)
    
    print(f"Prompt character length: {len(large_payload_prompt)} chars (~{int(len(large_payload_prompt)/3.2)} estimated tokens)")
    
    payload = {
        "prompt": large_payload_prompt,
        "model": "stehouwer_llm",
        "stream": True,
        "messages": [
            {"role": "user", "content": large_payload_prompt}
        ]
    }
    
    received_tokens = []
    start_time = time.time()
    
    with httpx.stream("POST", url, json=payload, timeout=httpx.Timeout(120.0, connect=10.0, read=120.0)) as resp:
        print(f"HTTP Status: {resp.status_code}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        for chunk in resp.iter_text():
            if chunk:
                received_tokens.append(chunk)
                # Once we receive 20 chunks or the badge, we know it's flowing and staged
                if len(received_tokens) >= 20:
                    break
                    
    full_received = "".join(received_tokens)
    print(f"Stream initiated successfully! First 350 chars received:\n{full_received[:350]}\n")
    
    # Assert disk staging
    big_jobs_dir = r"C:\AI-BS\saved_data\big_jobs"
    files = sorted(os.listdir(big_jobs_dir), key=lambda f: os.path.getmtime(os.path.join(big_jobs_dir, f)), reverse=True)
    print(f"Recent files in {big_jobs_dir}: {files[:5]}")
    
    json_files = [f for f in files if f.endswith("_prompt.json")]
    assert len(json_files) > 0, "No _prompt.json file found!"
    latest_json = os.path.join(big_jobs_dir, json_files[0])
    
    with open(latest_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print("Latest Job Metadata:")
    print(json.dumps(meta, indent=2)[:500] + "...")
    
    assert meta["allocated_num_ctx"] >= 16384, f"Allocated num_ctx was {meta['allocated_num_ctx']}, expected >= 16384"
    assert meta["total_input_chars"] >= len(large_payload_prompt)
    print("\n✅ Verification PASSED: Input was uncapped, dynamically allocated, and safely offloaded to disk extra save files!")

if __name__ == "__main__":
    test_streaming_big_job()
