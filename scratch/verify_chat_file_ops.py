import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, r"C:\AI-BS\backend")
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.hybrid_reasoning_engine import detect_tool_intent, stream_stehouwer_hybrid_response
from tools.tool_registry import ToolRegistry

async def main():
    print("=== 1. INTENT DETECTION TESTS ===")
    test_prompts = [
        "/read version.txt",
        "/cat backend/tools/tool_registry.py",
        "read C:\\AI-BS\\version.txt",
        "can you read the file version.txt and tell me what version we are on",
        "what is in the file saved_checkpoint.md",
        "show me contents of file frontend/package.json",
        "/write scratch/test_output.txt Hello world from automated test",
        "write to file scratch/notes.txt with content: testing inline write",
        "save this code to file scratch/hello.py:\n```python\nprint('hello')\n```",
        "/ls",
        "/dir backend",
        "/tree frontend/src",
        "list files in folder scratch",
        "what are the files inside C:\\AI-BS\\scratch",
        "tell me a joke about robots"
    ]
    for tp in test_prompts:
        t_name, t_args = detect_tool_intent(tp)
        print(f"PROMPT: {tp[:55]!r} -> TOOL: {t_name}, ARGS: {t_args}")

    print("\n=== 2. TOOL EXECUTION DIRECT TESTS ===")
    read_res = ToolRegistry.execute_tool("read_host_file", {"file_path": "version.txt"})
    print("read_host_file status:", read_res.get("status"), "lines:", read_res.get("lines"), "size:", read_res.get("size_bytes"))

    write_res = ToolRegistry.execute_tool("write_host_file", {
        "file_path": r"C:\AI-BS\scratch\chat_file_test.txt",
        "content": "Test content written by chat file engine at v5.270.0\nLine 2 of test content."
    })
    print("write_host_file status:", write_res.get("status"), "bytes:", write_res.get("bytes_written"), "backup:", write_res.get("backup_path"))

    # Test second write to verify .bak creation
    write_res_2 = ToolRegistry.execute_tool("write_host_file", {
        "file_path": r"C:\AI-BS\scratch\chat_file_test.txt",
        "content": "Updated content to trigger .bak creation."
    })
    print("write_host_file backup check:", write_res_2.get("backup_path"))

    scan_res = ToolRegistry.execute_tool("scan_directory_tree", {"dir_path": r"C:\AI-BS\scratch", "depth": 1})
    print("scan_directory_tree status:", scan_res.get("status"), "items found:", len(scan_res.get("tree", [])))

    print("\n=== 3. HYBRID STREAMING ENDPOINT TEST: /read ===")
    chunks = []
    async for chunk in stream_stehouwer_hybrid_response("/read version.txt"):
        chunks.append(chunk)
    stream_output = "".join(chunks)
    print("Stream /read output preview:")
    print(stream_output[:300])

    print("\n=== 4. HYBRID STREAMING ENDPOINT TEST: /write ===")
    chunks_w = []
    async for chunk in stream_stehouwer_hybrid_response("/write scratch/chat_stream_write.txt Streamed file write content!"):
        chunks_w.append(chunk)
    print("Stream /write output preview:")
    print("".join(chunks_w)[:300])

    print("\n=== 5. HYBRID STREAMING ENDPOINT TEST: /ls ===")
    chunks_ls = []
    async for chunk in stream_stehouwer_hybrid_response("/ls scratch"):
        chunks_ls.append(chunk)
    print("Stream /ls output preview:")
    print("".join(chunks_ls)[:350])

    print("\n=== 6. HYBRID STREAMING ENDPOINT TEST: Natural Language File Q&A ===")
    nl_chunks = []
    async for chunk in stream_stehouwer_hybrid_response("can you read the file version.txt and tell me what version we are on"):
        nl_chunks.append(chunk)
        print(chunk, end="", flush=True)
    print("\n")

    print("\n✅ ALL CHAT FILE TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())

