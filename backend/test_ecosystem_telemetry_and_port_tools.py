import os
import sys
import asyncio
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ecosystem_telemetry_engine import EcosystemTelemetryEngine
from tools.tool_registry import ToolRegistry


def test_telemetry_engine():
    print("--- 1. Testing EcosystemTelemetryEngine Snapshot ---")
    data = EcosystemTelemetryEngine.get_full_ecosystem_telemetry()
    assert data["status"] == "success"
    assert "summary" in data
    assert "core_matrix" in data
    assert len(data["core_matrix"]) == 25
    print(f"  [PASS] Ecosystem snapshot retrieved: {data['summary']['total_listening_ports']} ports, CPU: {data['summary']['host_cpu_pct']}%")


def test_port_discovery():
    print("--- 2. Testing Port Tool Discovery ---")
    res = asyncio.run(EcosystemTelemetryEngine.discover_port_tools(ports=[8080], timeout=1.5))
    assert res["status"] == "success"
    assert "discovered_services" in res
    print(f"  [PASS] Discovered services on port 8080: {res['discovered_services'].get(8080, {}).get('tools_count')} tools")


def test_tool_registry_matrix():
    print("--- 3. Testing ToolRegistry Declarations and Port Tools ---")
    decls = ToolRegistry.get_tool_declarations()
    assert len(decls) == 78, f"Expected 78 tools, got {len(decls)}"
    
    # Test get_port_telemetry_report
    r1 = ToolRegistry.execute_tool("get_port_telemetry_report", {"port": 8080})
    assert r1.get("status") == "success"
    assert r1.get("is_active") is True
    print("  [PASS] get_port_telemetry_report passed")

    # Test discover_ecosystem_port_tools
    r2 = ToolRegistry.execute_tool("discover_ecosystem_port_tools", {"ports": [8080], "timeout_seconds": 1.0})
    assert r2.get("status") == "success"
    print("  [PASS] discover_ecosystem_port_tools passed")

    # Test dispatch_port_tool_call
    r3 = ToolRegistry.execute_tool("dispatch_port_tool_call", {
        "port": 8080,
        "endpoint": "/api/v1/system/ecosystem/telemetry",
        "method": "GET"
    })
    assert r3.get("status") == "success" or r3.get("http_status") == 200
    print(f"  [PASS] dispatch_port_tool_call passed (HTTP {r3.get('http_status')})")


if __name__ == "__main__":
    test_telemetry_engine()
    test_port_discovery()
    test_tool_registry_matrix()
    print("\nALL ECOSYSTEM TELEMETRY & PORT TOOL TESTS PASSED! (3/3)")
