with open('C:/AI-BS/frontend/src/components/ChatTab.jsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('C:/AI-BS/scratch_sections.txt', 'w', encoding='utf-8') as out:
    out.write("=== SLASH COMMANDS (1570-1750) ===\n")
    for i in range(1570, min(1750, len(lines))):
        out.write(f"{i+1}: {lines[i]}")
    
    out.write("\n=== QUICK ACTION CONTROLS & INPUT AREA (2670-2820) ===\n")
    for i in range(2670, min(2820, len(lines))):
        out.write(f"{i+1}: {lines[i]}")

print("Extracted to scratch_sections.txt")
