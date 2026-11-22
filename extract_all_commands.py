with open('C:/AI-BS/frontend/src/components/ChatTab.jsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('C:/AI-BS/scratch_all_commands.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if 'if (command ===' in line or 'else if (command ===' in line or 'command ===' in line:
            out.write(f"Line {i+1}: {line.strip()}\n")
            # print next 3 lines
            for j in range(i+1, min(len(lines), i+5)):
                out.write(f"    {lines[j].strip()[:80]}\n")

print("Saved to scratch_all_commands.txt")
