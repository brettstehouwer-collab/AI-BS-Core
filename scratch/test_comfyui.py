import urllib.request, json, sys

try:
    data = json.load(open('C:/AI-BS/backend/comfyui_workflows/ltx_video_generation.json'))
    req = urllib.request.Request(
        'http://127.0.0.1:8080/comfyui/generate',
        data=json.dumps({'prompt': data}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    urllib.request.urlopen(req)
except Exception as e:
    print(getattr(e, 'read', lambda: b'')().decode() or str(e))
