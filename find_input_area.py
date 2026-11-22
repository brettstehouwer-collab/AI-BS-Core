with open('C:/AI-BS/frontend/src/components/ChatTab.jsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('C:/AI-BS/scratch_input_area.txt', 'w', encoding='utf-8') as out:
    out.write("=== INPUT AREA & CONTROLS ===\n")
    for i, line in enumerate(lines):
        if 'footerInput' in line or 'ChatToolControlBar' in line or 'handleSendMessage' in line:
            if i > 2500:
                out.write(f"Line {i+1}: {line.strip()[:120]}\n")
                for j in range(max(0, i-5), min(len(lines), i+30)):
                    out.write(f"  {j+1}: {lines[j]}")
                out.write("\n" + "="*50 + "\n")

print("Wrote input area to scratch_input_area.txt")
