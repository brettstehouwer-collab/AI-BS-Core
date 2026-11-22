import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8080"

def test_endpoints():
    print("Testing Shared Cloud Drive Endpoints...")
    
    # 1. Test /api/drive/files
    r1 = requests.get(f"{BASE_URL}/api/drive/files?path=/")
    print(f"1. /api/drive/files status: {r1.status_code}")
    if r1.status_code == 200:
        data = r1.json()
        print(f"   Items in root: {data.get('item_count', 0)}")
        for item in data.get('items', [])[:4]:
            print(f"   - {item.get('icon')} {item.get('name')} ({item.get('category')})")
    
    # 2. Test /api/drive/storage_stats
    r2 = requests.get(f"{BASE_URL}/api/drive/storage_stats")
    print(f"\n2. /api/drive/storage_stats status: {r2.status_code}")
    if r2.status_code == 200:
        sdata = r2.json()
        print(f"   Disk Total: {sdata.get('disk_total_formatted')}")
        print(f"   Disk Free: {sdata.get('disk_free_formatted')}")
        print(f"   Drive Total Files: {sdata.get('drive_total_files')}")
        print(f"   Drive Total Folders: {sdata.get('drive_total_folders')}")

    # 3. Test /api/drive/create_document
    r3 = requests.post(f"{BASE_URL}/api/drive/create_document", json={
        "current_path": "/01_Screenplays_and_Scripts",
        "file_name": "Test_Scene_Draft.fountain",
        "content": "Title: TEST SCENE DRAFT\nAuthor: Brett Stehouwer\n\nINT. STEHOUWER LAB - DAY\n\nBrett inspects the AI-BS Shared Cloud Drive system.\n\nBRETT\nIt is alive and fully operational.\n",
        "doc_type": "fountain"
    })
    print(f"\n3. /api/drive/create_document status: {r3.status_code}")
    if r3.status_code == 200:
        print(f"   Created document: {r3.json().get('path')}")

    # 4. Test /api/drive/read_document
    r4 = requests.get(f"{BASE_URL}/api/drive/read_document?path=/01_Screenplays_and_Scripts/Test_Scene_Draft.fountain")
    print(f"\n4. /api/drive/read_document status: {r4.status_code}")
    if r4.status_code == 200:
        print(f"   Document content preview: {r4.json().get('content')[:60]}...")

if __name__ == "__main__":
    test_endpoints()
