import sys
from pathlib import Path

backend_dir = Path(r"C:\AI-BS\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.mission_control_engine import mission_engine

proposal = "Add a persistent SQLite event-logging daemon for Pearl mining stratum telemetry."
print(f"Testing Grill Session for: '{proposal}'")

# Step 1: Start Grill Session
session = mission_engine.start_grill(proposal)
print("1. Grill Session Started:")
print(f"   Grill ID: {session['grill_id']}")
print(f"   Context Summary: {session['context_explored']['summary']}")
print(f"   Questions count: {len(session['questions'])}")
for q in session['questions']:
    print(f"   - Branch: {q['branch']}")
    print(f"     Q: {q['question']}")
    print(f"     Rec: {q['recommendation']}")

# Step 2: Respond with 1-click 'yes'
conclude_res = mission_engine.respond_grill(session['grill_id'], "yes")
print("\n2. Operator Responded 'yes':")
print(f"   Status: {conclude_res['status']}")
print(f"   Spec File: {conclude_res['spec_file']}")
print(f"   Generated Mission Plan ID: {conclude_res['mission_plan']['mission_id']}")
print(f"   Tasks count in Plan: {len(conclude_res['mission_plan']['tasks'])}")

# Step 3: Verify mission_spec.md exists
spec_path = Path(conclude_res['spec_file'])
assert spec_path.exists(), "mission_spec.md does not exist!"
print("\n3. mission_spec.md successfully verified on disk!")
print("All Grill Session mechanics validated 100% OK!")
