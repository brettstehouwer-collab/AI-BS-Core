import asyncio
import httpx
import base64

async def test_features():
    base_url = "http://127.0.0.1:8000/api/clients/joey_hamilton"
    
    print("Testing 1. Telecom Call Whisper...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{base_url}/telecom/lead-capture", json={
                "lead_name": "Test User",
                "lead_phone": "555-123-4567",
                "property_interest": "123 Main St"
            })
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.json()}\n")
    except Exception as e:
        print(f"Failed: {e}\n")

    print("Testing 2. Past Client Reactivation...")
    try:
        csv_data = "Name,Phone,Last Purchase\nJohn Doe,555-111-2222,2021\nJane Smith,555-333-4444,2022"
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{base_url}/reactivation/upload", json={
                "csv_content": csv_data
            })
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.json()}\n")
    except Exception as e:
        print(f"Failed: {e}\n")

    print("Testing 3. AI Virtual Staging...")
    try:
        # Create a tiny 1x1 dummy base64 image just to test the endpoint
        dummy_b64 = base64.b64encode(b"dummy image data").decode('utf-8')
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{base_url}/virtual-staging/generate", json={
                "image_base64": dummy_b64,
                "style": "Modern",
                "room_type": "Living Room"
            })
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.json()}\n")
    except Exception as e:
        print(f"Failed: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_features())
