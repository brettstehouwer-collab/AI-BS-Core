from fastapi.testclient import TestClient
from AI_BS_Backend import app
import traceback

client = TestClient(app)
try:
    response = client.post(
        "/api/chat",
        json={"model": "test", "messages": [{"role": "user", "content": "hello"}]},
    )
    print("STATUS:", response.status_code)
    print("TEXT:", response.text)
except Exception as e:
    traceback.print_exc()
