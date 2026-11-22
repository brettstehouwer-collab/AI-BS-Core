import os

version = "5.269.5"
v_version = "v5.269.5"

# 1. version.txt
with open(r"C:\AI-BS\version.txt", "w", encoding="utf-8") as f:
    f.write(f"{v_version}\n")
print(f"Updated C:\\AI-BS\\version.txt -> {v_version}")

# 2. frontend/package.json
pkg_path = r"C:\AI-BS\frontend\package.json"
with open(pkg_path, "r", encoding="utf-8") as f:
    content = f.read()
new_content = content.replace('"version": "5.269.4"', f'"version": "{version}"')
with open(pkg_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print(f"Updated {pkg_path} -> {version}")

# 3. frontend/public/version.json
vjson_path = r"C:\AI-BS\frontend\public\version.json"
with open(vjson_path, "r", encoding="utf-8") as f:
    content = f.read()
new_content = content.replace('"version": "5.269.4"', f'"version": "{version}"')
new_content = new_content.replace('v5.269.4-gemini-mcp-email-automation-catalog', f'{v_version}-stehouwer-llm-coder-backbone-upgrade')
with open(vjson_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print(f"Updated {vjson_path} -> {version}")

# 4. frontend/public/sw.js
sw_path = r"C:\AI-BS\frontend\public\sw.js"
with open(sw_path, "r", encoding="utf-8") as f:
    content = f.read()
new_content = content.replace('v5.269.4', v_version)
with open(sw_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print(f"Updated {sw_path} -> {v_version}")

# 5. UI Mirrors
mirrors = [
    r"C:\AI-BS\frontend\src\components",
    r"C:\AI-BS\frontend\components",
    r"C:\AI-BS\frontend\src\components\components",
    r"C:\AI-BS\frontend\components\components"
]

for m in mirrors:
    # ChatTab.jsx
    ct = os.path.join(m, "ChatTab.jsx")
    if os.path.exists(ct):
        with open(ct, "r", encoding="utf-8") as f:
            c = f.read()
        c = c.replace("Stehouwer LLM v5.269.4", f"Stehouwer LLM {v_version}")
        with open(ct, "w", encoding="utf-8") as f:
            f.write(c)
        print(f"Updated {ct} -> {v_version}")

    # TopNavbar.jsx
    tn = os.path.join(m, "TopNavbar.jsx")
    if os.path.exists(tn):
        with open(tn, "r", encoding="utf-8") as f:
            c = f.read()
        c = c.replace(">v5.269.4<", f">{v_version}<")
        with open(tn, "w", encoding="utf-8") as f:
            f.write(c)
        print(f"Updated {tn} -> {v_version}")

    # Sidebar.jsx
    sb = os.path.join(m, "Sidebar.jsx")
    if os.path.exists(sb):
        with open(sb, "r", encoding="utf-8") as f:
            c = f.read()
        c = c.replace(">v5.269.4<", f">{v_version}<")
        with open(sb, "w", encoding="utf-8") as f:
            f.write(c)
        print(f"Updated {sb} -> {v_version}")

print("Version sweep to v5.269.5 complete across all mirrors!")
