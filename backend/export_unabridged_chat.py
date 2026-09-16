import json
import os
import re

LOG_PATH = r"C:\Users\footb\.gemini\antigravity-ide\brain\86c3414e-094b-4332-831e-507b50037507\.system_generated\logs\transcript_full.jsonl"
OUTPUT_PATH = r"C:\AI-BS\Full_Chat_Transcript_2026-07-22.md"


def export_unabridged():
    if not os.path.exists(LOG_PATH):
        print("Log path not found.")
        return

    md_lines = [
        "# Unabridged AI-BS Session Transcript — Full Thinking, Commands & Outputs",
        "**Date:** July 22, 2026  ",
        "**Conversation ID:** `86c3414e-094b-4332-831e-507b50037507`  ",
        "**System:** AI-BS (Stehouwer LLM & Antigravity IDE)  ",
        "**Includes:** User Prompts, Agent Thinking, Terminal Commands Executed, Code Edits & Command Outputs  ",
        "\n---\n",
    ]

    user_count = 0
    step_count = 0

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                entry_type = entry.get("type", "")
                content = entry.get("content", "")
                tool_calls = entry.get("tool_calls", [])

                step_count += 1

                # 1. User Inputs
                if entry_type == "USER_INPUT":
                    user_count += 1
                    md_lines.append(f"\n# 👤 USER REQUEST #{user_count}\n")
                    md_lines.append(f"```text\n{content}\n```\n")
                    md_lines.append("---\n")

                # 2. Model Responses (including thinking)
                elif entry_type == "PLANNER_RESPONSE":
                    md_lines.append(
                        f"\n## 🧠 AGENT REASONING & RESPONSE (Step {step_count})\n"
                    )
                    if isinstance(content, str) and content.strip():
                        md_lines.append(content.strip() + "\n")

                    # If tool calls were made in this turn
                    if tool_calls and isinstance(tool_calls, list):
                        md_lines.append("\n### 🛠️ COMMANDS & TOOL CALLS EXECUTED:\n")
                        for tc in tool_calls:
                            t_name = tc.get("name", tc.get("tool_name", "tool"))
                            args = tc.get("args", tc.get("arguments", {}))

                            md_lines.append(f"#### Tool Executed: `{t_name}`")
                            if t_name == "run_command":
                                cmd_line = args.get("CommandLine", "")
                                cwd = args.get("Cwd", "")
                                md_lines.append(f"**Working Directory:** `{cwd}`")
                                md_lines.append(f"```powershell\n{cmd_line}\n```")
                            elif t_name in ["write_to_file", "replace_file_content"]:
                                target = args.get("TargetFile", "")
                                desc = args.get("Description", "")
                                md_lines.append(
                                    f"**Target File:** `{target}`  \n**Description:** {desc}"
                                )
                                code = args.get(
                                    "CodeContent", args.get("ReplacementContent", "")
                                )
                                if code:
                                    md_lines.append(f"```python\n{code[:1000]}\n```")
                            else:
                                md_lines.append(
                                    f"```json\n{json.dumps(args, indent=2)}\n```"
                                )
                        md_lines.append("\n")

                # 3. Command Execution Outputs / Tool Results
                elif entry_type == "RUN_COMMAND":
                    md_lines.append(
                        f"\n#### 💻 TERMINAL COMMAND OUTPUT (Step {step_count})\n"
                    )
                    md_lines.append(f"```text\n{str(content)[:2000]}\n```\n")

            except Exception as ex:
                continue

    output_text = "\n".join(md_lines)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"Exported unabridged transcript to: {OUTPUT_PATH}")


if __name__ == "__main__":
    export_unabridged()
