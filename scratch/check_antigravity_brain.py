import os

antigravity_brain = r'C:\Users\footb\.gemini\antigravity\brain'
if os.path.exists(antigravity_brain):
    subdirs = [d for d in os.listdir(antigravity_brain) if os.path.isdir(os.path.join(antigravity_brain, d))]
    print(f"Total dirs in {antigravity_brain}: {len(subdirs)}")
    sample_sub = subdirs[:5]
    print("Sample dirs:", sample_sub)
    for s in sample_sub:
        p = os.path.join(antigravity_brain, s)
        print(s, os.listdir(p)[:6])
else:
    print("Does not exist!")
