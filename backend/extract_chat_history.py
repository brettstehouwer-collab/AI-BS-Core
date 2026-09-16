import json

log_path = r"C:\Users\footb\.gemini\antigravity-ide\brain\7147b90f-f551-4fea-87b8-95ddf84a2b2d\.system_generated\logs\transcript.jsonl"
output_path = r"G:\Stehouwer_Server\AI-BS\Chat_History.txt"

history = []

try:
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)

            source = data.get("source", "")
            type_ = data.get("type", "")
            content = data.get("content", "")

            # Extract User Messages
            if source == "USER_EXPLICIT" and type_ == "USER_INPUT":
                if "<USER_REQUEST>" in content:
                    text = (
                        content.split("<USER_REQUEST>")[1]
                        .split("</USER_REQUEST>")[0]
                        .strip()
                    )
                    if text:
                        history.append(f"USER:\n{text}\n")

            # Extract AI Messages
            elif source == "MODEL" and type_ == "PLANNER_RESPONSE":
                if content and not content.startswith("<USER_REQUEST>"):
                    history.append(f"AI:\n{content.strip()}\n")

    with open(output_path, "w", encoding="utf-8") as out_f:
        out_f.write("=== AI-BS Development Chat History ===\n\n")
        out_f.write(
            "\n--------------------------------------------------\n".join(history)
        )

    print(f"Successfully extracted {len(history)} messages to {output_path}")

except Exception as e:
    print(f"Error extracting history: {e}")
