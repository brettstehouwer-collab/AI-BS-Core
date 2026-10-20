import sys
import os
import subprocess

backend_dir = r"C:\AI-BS\backend"
sys.path.insert(0, backend_dir)

try:
    import uvicorn
    print("uvicorn is available")
    import fastapi
    print("fastapi is available")
    import AI_BS_Backend
    print("AI_BS_Backend imported successfully")
except Exception as e:
    import traceback
    traceback.print_exc()
