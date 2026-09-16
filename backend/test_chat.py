from fastapi.testclient import TestClient
from AI_BS_Backend import app

client = TestClient(app)
response = client.post(
    "/api/chat",
    json={"model": "test", "messages": [{"role": "user", "content": "hello"}]},
)
print(response.status_code)
print(response.text)
