import os

path = "C:/AI-BS/frontend/components/ChatTab.jsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the missing comma
bad_syntax = """    {
      category: "⚔️ Swarm",
      title: "🛡️ Matrix Doctor 20-Port System Diagnostic",
      desc: "Benchmark socket latency and database health across all 20 background service ports.",
      prompt: "Run a full Matrix Doctor diagnostic scan across all 20 service ports and verify database health."
    }
    {
      category: "🏠 Automation","""

good_syntax = """    {
      category: "⚔️ Swarm",
      title: "🛡️ Matrix Doctor 20-Port System Diagnostic",
      desc: "Benchmark socket latency and database health across all 20 background service ports.",
      prompt: "Run a full Matrix Doctor diagnostic scan across all 20 service ports and verify database health."
    },
    {
      category: "🏠 Automation","""

if bad_syntax in content:
    content = content.replace(bad_syntax, good_syntax)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Fixed missing comma syntax error!")
else:
    print("Could not find the exact syntax to fix! Investigating...")

import shutil
shutil.copy2(path, "C:/AI-BS/frontend/src/components/ChatTab.jsx")
