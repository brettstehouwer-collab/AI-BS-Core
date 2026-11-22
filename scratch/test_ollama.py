"""Test ollama API root."""

import requests

PROMPT = """You are an expert Hollywood screenwriter and script formatting \
engine. Adapt the following prose segment from a book into a proper \
screenplay format for a TV Pilot.
Rules:
1. ABSOLUTELY NO PREAMBLE, introductions, title pages, or conversational \
text. Start directly with the first Scene Heading.
2. ABSOLUTELY NO MARKDOWN formatting (Do NOT use ** or * for bold/italics).
3. Transitions (e.g., CUT TO:, FADE IN:) must be UPPERCASE, on their own \
line, without any markdown asterisks.
4. SPACING AND ALIGNMENT (Mandatory for Layout Engine):
   - Character Names: Must be indented exactly 22 spaces before the name.
   - Parentheticals: Must be indented exactly 16 spaces before the opening \
parenthesis.
   - Dialogue: Must be indented exactly 10 spaces before the text.
   - Scene Headings and Action Lines: 0 spaces (flush left).

CRITICAL INSTRUCTION:
At the very end of your response, you MUST provide a brief 2-sentence \
narrative summary of the current plot state, active characters, and current \
location. You must wrap this summary exactly in <SUMMARY> and </SUMMARY> \
tags. This is crucial for narrative continuity in the next chunk.

Previous Plot Context:
none

New Segment to Adapt:
The dog ran fast."""

try:
    response = requests.post(
        "http://127.0.0.1:11434/api/chat",
        json={
            "model": "llama3:latest",
            "messages": [{"role": "user", "content": PROMPT}],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 2500,
                "num_ctx": 8192
            }
        },
        timeout=60.0
    )
    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)
except requests.RequestException as e:
    print("ERROR:", e)
