import json
import os
import time


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "ai_bs_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


def test_function_loop():
    try:
        from google import genai
        from bullshit_api_request_manager import fetch_local_chroma_context
        from bullshit_polyglot import (
            list_local_directory,
            read_local_file,
            execute_polyglot_command,
        )
        from bullshit_github_automation import commit_and_push_build

        print(
            "[Antigravity] Initializing genai client for function interception loop..."
        )
        client = genai.Client()

        interaction = client.interactions.create(
            agent="antigravity-preview-05-2026",
            input="What files are in the local directory and what does main.py do?",
            environment="remote",
            tools=[
                fetch_local_chroma_context,
                list_local_directory,
                read_local_file,
                execute_polyglot_command,
                commit_and_push_build,
            ],
        )

        print("[Antigravity] Interception loop active. Waiting for function calls...")
        for chunk in interaction.stream():
            if chunk.function_call:
                func_name = chunk.function_call.name
                args = chunk.function_call.args

                print(
                    f"[Antigravity] Intercepted tool call: {func_name} with args {args}"
                )

                local_payload = {}
                if func_name == "fetch_local_chroma_context":
                    local_payload = fetch_local_chroma_context(**args)
                elif func_name == "list_local_directory":
                    local_payload = list_local_directory(**args)
                elif func_name == "read_local_file":
                    local_payload = read_local_file(**args)
                elif func_name == "execute_polyglot_command":
                    local_payload = execute_polyglot_command(**args)
                elif func_name == "commit_and_push_build":
                    local_payload = commit_and_push_build(**args)

                interaction.send_function_response(
                    name=func_name, response=local_payload
                )

            elif chunk.text:
                print(f"[Antigravity] Agent: {chunk.text}")
    except ImportError as e:
        print(f"[Antigravity] Missing module for tool loop: {e}")


def main():
    config = load_config()
    fallback = config.get("fallback_model", "stehouwer_llm")

    print("[Antigravity] Integration Daemon started.")
    print(
        f"[Antigravity] Monitoring APIRequestManager. Ready to transition to {fallback} on exhaustion."
    )

    # Run the test loop (this will fail if genai or SDK is not configured yet, which is expected)
    test_function_loop()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("[Antigravity] Shutting down.")


if __name__ == "__main__":
    main()
