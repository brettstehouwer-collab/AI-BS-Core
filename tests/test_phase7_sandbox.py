import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [Phase7SandboxTest] - %(message)s")

# Ensure backend is in sys.path
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from omnidrive_service import OmniDriveService
from node_ast_compiler import NodeASTCompiler
from jit_daemon_manager import JITDaemonManager

async def run_dry_run_tests():
    logging.info("🚀 Starting Phase 7 Sandbox Dry-Run Verification Suite...")
    
    # 1. Test OmniDrive Hybrid Search & AST Check
    logging.info("--- Testing OmniDriveService ---")
    db_test_path = os.path.join(os.path.dirname(__file__), "test_state.db")
    omnidrive = OmniDriveService(db_path=db_test_path)
    search_res = await omnidrive.hybrid_search("telemetry", limit=5)
    logging.info(f"✅ Hybrid Search Latency: {search_res['latency_us']} us | Hits: {len(search_res['results'])}")
    assert "results" in search_res and search_res["latency_us"] >= 0, "OmniDrive hybrid_search test failed"
    
    # 2. Test NodeASTCompiler
    logging.info("--- Testing NodeASTCompiler ---")
    compiler = NodeASTCompiler()
    sample_graph = {
        "nodes": [
            {"id": "node_1", "type": "telemetry", "data": {"label": "Hardware Telemetry Node"}},
            {"id": "node_2", "type": "render", "data": {"label": "3D Canvas Render Node"}}
        ],
        "edges": [{"source": "node_1", "target": "node_2"}]
    }
    compiled_ast_code = compiler.compile_graph_to_ast(sample_graph)
    logging.info(f"✅ Node AST Code Compiled ({len(compiled_ast_code.splitlines())} lines)")
    assert "def execute_node_1" in compiled_ast_code and "def execute_node_2" in compiled_ast_code, "NodeASTCompiler test failed"

    # 3. Test JITDaemonManager
    logging.info("--- Testing JITDaemonManager ---")
    jit_mgr = JITDaemonManager()
    jit_mgr.thermal_threshold_celsius = 82.0
    thermal_flag = jit_mgr.check_hardware_thermal_throttle()
    logging.info(f"✅ Thermal Limit Check (82.0°C limit): Thermal Throttle Active = {thermal_flag}")
    assert isinstance(thermal_flag, bool), "JITDaemonManager thermal check failed"

    logging.info("==========================================================")
    logging.info("🎉 ALL PHASE 7 SANDBOX TESTS PASSED SUCCESSFULLY! (100% OK)")
    logging.info("==========================================================")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(run_dry_run_tests())
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        logging.error(f"❌ Phase 7 Sandbox Dry-Run Failed: {e}", exc_info=True)
        sys.exit(1)
