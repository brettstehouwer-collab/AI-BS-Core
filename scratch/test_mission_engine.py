import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend is on sys.path
backend_dir = Path(r"C:\AI-BS\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(backend_dir.parent) not in sys.path:
    sys.path.insert(0, str(backend_dir.parent))

from core.mission_control_engine import mission_engine

goal = "Verify multi-mirror parity, syntax health, and git status"
print(f"Testing Mission Engine with goal: {goal}")
plan = mission_engine.run_full_mission(goal)

print(f"Mission Status: {plan.get('status')}")
print(f"Total Duration: {plan.get('total_duration_ms')} ms")
print(f"Total Tasks: {len(plan.get('tasks', []))}")

for t in plan.get('tasks', []):
    print(f"  [{t.get('status').upper()}] Phase: {t.get('phase')} - {t.get('title')}")
    res = t.get('result', {})
    if res.get('output'):
        print(f"      Output: {res.get('output')[:100]}...")

assert plan.get('status') == 'completed', "Mission did not complete successfully"
print("\n>>> ALL MISSION ENGINE TESTS PASSED SUCCESSFULLY! <<<")
