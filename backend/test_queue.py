import urllib.request
import urllib.error
import json
import uuid

with open("comfyui_workflows/lora_model_generation.json", "r") as f:
    workflow = json.load(f)

# Mock what inject_prompt_into_workflow does
# For lora_model_generation, it just uses it as is.
p = {"prompt": workflow, "client_id": str(uuid.uuid4())}
data = json.dumps(p).encode('utf-8')

req = urllib.request.Request("http://127.0.0.1:8189/prompt", data=data)
req.add_header('Content-Type', 'application/json')
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(e)
