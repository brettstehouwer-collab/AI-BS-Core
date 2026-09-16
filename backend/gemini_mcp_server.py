from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.tool_registry import ToolRegistry

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.sse import SseServerTransport

app = FastAPI(title="AI-BS Gemini MCP Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mcp_server = Server("ai-bs-mcp-server")
mcp_transport = SseServerTransport("/messages")

registry = ToolRegistry()

@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    declarations = registry.get_tool_declarations()
    mcp_tools = []
    for dec in declarations:
        mcp_tools.append(Tool(
            name=dec["name"],
            description=dec.get("description", ""),
            inputSchema=dec.get("parameters", {"type": "object", "properties": {}})
        ))
    return mcp_tools

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if hasattr(registry, "execute_tool"):
            result = registry.execute_tool(name, arguments)
        else:
            # Fallback if execute_tool is named something else, e.g., dispatch
            result = getattr(registry, name)(**arguments)
        
        import json
        text_out = json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
        return [TextContent(type="text", text=text_out)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing tool {name}: {str(e)}")]

async def sse_head(request: Request):
    return Response(status_code=200)

async def sse_post_dummy(request: Request):
    try:
        body_bytes = await request.body()
        if not body_bytes:
            return Response(status_code=200)
        import json
        body = json.loads(body_bytes)
        print(f"Gemini POSTed to /sse: {body.get('method')}")
        
        method = body.get("method")
        msg_id = body.get("id")
        
        if method == "initialize":
            protocol_version = body.get("params", {}).get("protocolVersion", "2024-11-05")
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": protocol_version,
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "ai-bs-mcp-server",
                            "version": "1.0.0"
                        }
                    }
                }),
                media_type="application/json"
            )
            
        elif method == "tools/list":
            declarations = registry.get_tool_declarations()
            tools_list = []
            for dec in declarations:
                tools_list.append({
                    "name": dec["name"],
                    "description": dec.get("description", ""),
                    "inputSchema": dec.get("parameters", {"type": "object", "properties": {}})
                })
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": tools_list
                    }
                }),
                media_type="application/json"
            )
            
        elif method == "tools/call":
            params = body.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            try:
                if hasattr(registry, "execute_tool"):
                    result = registry.execute_tool(tool_name, arguments)
                else:
                    result = getattr(registry, tool_name)(**arguments)
                import json
                text_out = json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
                content = [{"type": "text", "text": text_out}]
                is_error = False
            except Exception as e:
                content = [{"type": "text", "text": f"Error: {str(e)}"}]
                is_error = True
                
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": content,
                        "isError": is_error
                    }
                }),
                media_type="application/json"
            )
            
        elif method == "notifications/initialized":
            return Response(status_code=200)
            
        # Return 200 for any other unknown notifications
        return Response(status_code=200)

    except Exception as e:
        print("Error in POST /sse:", e)
class DummyResponse:
    async def __call__(self, scope, receive, send):
        pass

async def sse_endpoint(request: Request):
    async with mcp_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options()
        )
    return DummyResponse()

async def messages_endpoint(request: Request):
    await mcp_transport.handle_post_message(
        request.scope, request.receive, request._send
    )
    return DummyResponse()

app.add_route("/sse", sse_endpoint, methods=["GET"])
app.add_route("/messages", messages_endpoint, methods=["POST", "OPTIONS"])

app.add_route("/sse", sse_head, methods=["HEAD", "OPTIONS"])
app.add_route("/sse", sse_post_dummy, methods=["POST"])

if __name__ == "__main__":
    print("Starting AI-BS Gemini MCP Bridge on port 8099...")
    uvicorn.run(app, host="0.0.0.0", port=8099)
