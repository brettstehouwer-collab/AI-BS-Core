import json
import httpx
import google.auth
from google.auth.transport.requests import Request
import uuid


class VertexMCPClient:
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url
        self.credentials, self.project_id = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

    def _get_headers(self):
        self.credentials.refresh(Request())
        token = self.credentials.token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    def _call_jsonrpc(self, method: str, params: dict = None):
        payload = {"jsonrpc": "2.0", "method": method, "id": str(uuid.uuid4())}
        if params is not None:
            payload["params"] = params

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self.endpoint_url, headers=self._get_headers(), json=payload
            )
            response.raise_for_status()
            return response.json()

    def list_tools(self):
        """Fetch available tools from the MCP endpoint."""
        response = self._call_jsonrpc("tools/list")
        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")
        return response.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict):
        """Execute a specific tool on the MCP endpoint."""
        params = {"name": name, "arguments": arguments}
        response = self._call_jsonrpc("tools/call", params)
        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")
        return response.get("result", {})


if __name__ == "__main__":
    # Simple test logic if run directly
    try:
        client = VertexMCPClient("https://aiplatform.googleapis.com/mcp/retrieval")
        tools = client.list_tools()
        print("Successfully authenticated. Available tools:")
        for t in tools:
            print(f"- {t.get('name')}")
    except Exception as e:
        print(f"Failed to connect to Vertex MCP: {e}")
