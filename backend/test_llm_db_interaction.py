import urllib.request
import json
import sys
import os

from tools.tool_registry import ToolRegistry

def test_llm_tool_calling():
    print("Testing Stehouwer LLM Tool Calling with 70 Vertical DBs...\n")
    
    tools = ToolRegistry.get_tool_declarations()
    
    # Format tools for Ollama API (OpenAI format for tools)
    ollama_tools = []
    for t in tools:
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("parameters", {})
            }
        })
        
    messages = [
        {"role": "system", "content": "You are the Stehouwer LLM. You must use tools to answer questions."},
        {"role": "user", "content": "Please query the aerospace_telemetry.db database for the latest 2 records in the system_telemetry table."}
    ]
    
    payload = {
        "model": "stehouwer_llm",
        "messages": messages,
        "tools": ollama_tools,
        "stream": False
    }
    
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            response = json.loads(resp.read().decode('utf-8'))
            
            message = response.get("message", {})
            print(f"LLM Response Role: {message.get('role')}")
            
            if "tool_calls" in message and message["tool_calls"]:
                print("\n[SUCCESS] LLM decided to use a tool!")
                for tc in message["tool_calls"]:
                    func_name = tc["function"]["name"]
                    args = tc["function"]["arguments"]
                    print(f"Tool Call: {func_name}")
                    print(f"Arguments: {args}")
                    
                    print("\nExecuting tool via ToolRegistry...")
                    result = ToolRegistry.execute_tool(func_name, args)
                    print(f"Result: {json.dumps(result, indent=2)}")
            else:
                print("\n[FAILURE] LLM did not use a tool. Content output:")
                print(message.get("content", ""))
                
    except Exception as e:
        print(f"Error testing LLM: {e}")

if __name__ == "__main__":
    test_llm_tool_calling()
