import os
import re

path = "C:/AI-BS/backend/aibs_reasoning_engine.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the NameError 'gauntlet' is not defined in solve_and_refine
new_content = content.replace('"total_iterations": len(gauntlet[:max_iterations]),', '"total_iterations": max_iterations,')

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Fixed solve_and_refine NameError!")
