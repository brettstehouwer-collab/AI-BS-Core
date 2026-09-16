import json
import os
import re

LOG_PATH = r"C:\Users\footb\.gemini\antigravity-ide\brain\86c3414e-094b-4332-831e-507b50037507\.system_generated\logs\transcript_full.jsonl"
OUTPUT_PATH = r"C:\AI-BS\Full_Chat_Transcript_2026-07-22.md"


def extract_user_request(text):
    if not text:
        return ""
    match = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback if no tags
    clean = re.sub(
        r"<ADDITIONAL_METADATA>.*?</ADDITIONAL_METADATA>", "", text, flags=re.DOTALL
    )
    clean = re.sub(
        r"<USER_SETTINGS_CHANGE>.*?</USER_SETTINGS_CHANGE>", "", clean, flags=re.DOTALL
    )
    return clean.strip()


def export_transcript():
    if not os.path.exists(LOG_PATH):
        print("Transcript log file not found.")
        return

    md_lines = [
        "# Complete AI-BS Session Chat Transcript",
        "**Date:** July 22, 2026  ",
        "**Conversation ID:** `86c3414e-094b-4332-831e-507b50037507`  ",
        "**System:** AI-BS (Stehouwer LLM & Antigravity IDE)  ",
        "\n---\n",
    ]

    message_count = 0
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line)
                entry_type = entry.get("type", "")
                content = entry.get("content", "")

                if entry_type == "USER_INPUT":
                    user_text = extract_user_request(content)
                    if user_text:
                        message_count += 1
                        md_lines.append(f"## 👤 User (Request #{message_count})")
                        md_lines.append(f"{user_text}\n")

                elif entry_type == "PLANNER_RESPONSE":
                    if isinstance(content, str) and content.strip():
                        # Clean internal thought tags if present
                        assistant_text = re.sub(
                            r"<thought>.*?</thought>", "", content, flags=re.DOTALL
                        ).strip()
                        if assistant_text:
                            md_lines.append(
                                "## 🤖 Assistant (Stehouwer LLM / Antigravity)"
                            )
                            md_lines.append(f"{assistant_text}\n")
                            md_lines.append("---\n")

            except Exception as e:
                continue

    output_text = "\n".join(md_lines)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(
        f"Successfully exported full transcript with {message_count} user turns to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    export_transcript()
