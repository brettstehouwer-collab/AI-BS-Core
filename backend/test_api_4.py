import requests

try:
    res = requests.post(
        'http://127.0.0.1:8000/api/chat',
        json={'model': 'stehouwer_llm', 'messages': [{'role': 'user', 'content': 'hello'}]}
    )
    print("Status for hello:", res.status_code)
    print("Text for hello:", res.text)
except Exception as e:
    print(e)

try:
    res = requests.post(
        'http://127.0.0.1:8000/api/chat',
        json={'model': 'stehouwer_llm', 'messages': [{'role': 'user', 'content': 'sex'}]}
    )
    print("Status for sex:", res.status_code)
    print("Text for sex:", res.text)
except Exception as e:
    print(e)
