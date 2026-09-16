# Gemini MCP Server Integration Plan

You are trying to connect your live Firebase web app (`https://ai-bs-dashboard.web.app/`) to Gemini as a "Custom Connected App." 

**Why it failed:** 
Gemini expects the URL you provide to be a live, running **MCP (Model Context Protocol) Server** that speaks a specific real-time streaming language called SSE (Server-Sent Events). 
Firebase Hosting (`.web.app`) is a static Content Delivery Network (CDN) for your frontend React/HTML files. It cannot run a live backend server to communicate with Gemini.

To fix this, we need to expose your actual local `AI-BS` Python backend to the internet so Gemini can talk directly to your RTX 4090 architecture and local tools.

## User Review Required
> [!WARNING]
> By completing this phase, you are granting the external Google Gemini cloud model direct API access to your local AI-BS tools. We will only expose specific, safe tools through the MCP protocol to prevent external models from running destructive local commands.

## Open Questions
> [!IMPORTANT]
> 1. To give Gemini a valid URL, we need to expose your local Python backend to the internet. Do you already have a static Cloudflare Tunnel / Ngrok domain you prefer to use, or should I install and launch a free temporary `cloudflared` Quick Tunnel for this?
> 2. Which specific AI-BS tools do you want to expose to Gemini? (e.g., Should Gemini be able to query your 200GB SQLite RAG database, or do you just want it to be able to execute Python sandbox scripts?)

## Proposed Changes

### 1. The MCP Server Bridge (`backend/mcp_server.py`)
I will build a dedicated Python FastAPIServer endpoint using the official `mcp` SDK. 
- It will expose `/sse` and `/messages` endpoints.
- It will securely bind to your existing `ToolRegistry` so Gemini can see and execute the exact same tools that your local `stehouwer_llm` uses.

### 2. Network Tunneling
Because Gemini is in the cloud and your AI-BS backend is on your local Windows PC, I will set up a secure Cloudflare Tunnel.
- The tunnel will route `https://your-custom-tunnel.trycloudflare.com/sse` directly to your local Python MCP server.
- You will paste *this* tunnel URL into Gemini, and the connection will instantly succeed.

## Verification Plan
1. I will write and launch the Python MCP server.
2. I will launch the Cloudflare Tunnel.
3. I will provide you with the exact secure URL to paste into the Gemini "Add a custom app link" settings.
4. We will verify that Gemini successfully reads your local AI-BS tool declarations.
