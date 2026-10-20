import os

frontend_components = []
frontend_dir = r"C:\AI-BS\frontend\src"
for root, dirs, files in os.walk(frontend_dir):
    for f in files:
        if f.endswith(('.jsx', '.tsx')):
            frontend_components.append(os.path.relpath(os.path.join(root, f), frontend_dir))

backend_routers = []
backend_routers_dir = r"C:\AI-BS\backend\routers"
if os.path.exists(backend_routers_dir):
    for f in os.listdir(backend_routers_dir):
        if f.endswith('.py'):
            backend_routers.append(f)

print("FRONTEND JSX/TSX COMPONENTS (" + str(len(frontend_components)) + "):")
for c in sorted(frontend_components):
    print(f"  - {c}")

print("\nBACKEND ROUTERS (" + str(len(backend_routers)) + "):")
for r in sorted(backend_routers):
    print(f"  - {r}")