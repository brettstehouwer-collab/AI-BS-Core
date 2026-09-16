import requests

try:
    res = requests.post(
        'http://127.0.0.1:8000/v1/chat/completions',
        json={'model': 'stehouwer_qwen', 'messages': [{'role': 'user', 'content': 'hello'}]}
    )
    print("Status:", res.status_code)
    print("Text:", res.text)
except Exception as e:
    print(e)
