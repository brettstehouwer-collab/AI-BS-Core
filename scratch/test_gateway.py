import urllib.request, json, sys

try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/comfyui/generate',
        data=json.dumps({'prompt_text': 'A test prompt', 'workflow_filename': 'ltx_video_generation.json'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    urllib.request.urlopen(req)
    print("SUCCESS")
except Exception as e:
    print(getattr(e, 'read', lambda: b'')().decode() or str(e))
