import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.vertex_mcp_client import VertexMCPClient


def test_client():
    try:
        print("Testing Vertex MCP Client Initialization (ADC Check)...")
        client = VertexMCPClient("https://aiplatform.googleapis.com/mcp/retrieval")
        print("Successfully loaded ADC credentials.")

        print("Fetching /mcp/retrieval tools/list...")
        tools = client.list_tools()
        print(f"Found {len(tools)} tools:")
        for t in tools:
            print(f"  - {t.get('name')}: {t.get('description', '')[:60]}...")

    except Exception as e:
        print(f"Error during test: {e}")


if __name__ == "__main__":
    test_client()
