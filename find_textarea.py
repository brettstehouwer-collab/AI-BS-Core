with open('C:/AI-BS/frontend/src/components/ChatTab.jsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('C:/AI-BS/scratch_textarea.txt', 'w', encoding='utf-8') as out:
    for i in range(3090, min(len(lines), 3240)):
        out.write(f"{i+1}: {lines[i]}")

print("Wrote textarea area")
