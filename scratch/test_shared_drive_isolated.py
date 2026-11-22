import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

_backend_dir = r"C:\AI-BS\backend"
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.shared_drive_router import router as shared_drive_router, DRIVE_ROOT

app = FastAPI()
app.include_router(shared_drive_router)

client = TestClient(app)

def run_tests():
    print(f"Drive Root: {DRIVE_ROOT}")
    
    # 1. Test GET /api/drive/files
    res = client.get("/api/drive/files?path=/")
    print(f"1. GET /api/drive/files: status {res.status_code}")
    data = res.json()
    print(f"   Items found: {data['item_count']}")
    for item in data['items'][:3]:
        print(f"   - {item['icon']} {item['name']} ({item['category']})")
    assert res.status_code == 200

    # 2. Test GET /api/drive/storage_stats
    res2 = client.get("/api/drive/storage_stats")
    print(f"\n2. GET /api/drive/storage_stats: status {res2.status_code}")
    stats = res2.json()
    print(f"   Disk Total: {stats['disk_total_formatted']}")
    print(f"   Disk Free: {stats['disk_free_formatted']}")
    print(f"   Categories breakdown count: {len(stats['categories_breakdown'])}")
    assert res2.status_code == 200

    # 3. Test POST /api/drive/create_folder
    res3 = client.post("/api/drive/create_folder", json={
        "current_path": "/",
        "folder_name": "Test_Suite_Folder"
    })
    print(f"\n3. POST /api/drive/create_folder: status {res3.status_code}, response: {res3.json()}")
    assert res3.status_code in [200, 409]

    # 4. Test POST /api/drive/create_document (Fountain Screenplay)
    res4 = client.post("/api/drive/create_document", json={
        "current_path": "/01_Screenplays_and_Scripts",
        "file_name": "Brett_Feature_Draft.fountain",
        "content": "Title: ECHOES OF THE MATRIX\nAuthor: Brett Stehouwer\n\nEXT. CITY STREET - DAY\n\nBrett walks into the Stehouwer Publishing headquarters.\n\nBRETT\nThe system is live.\n",
        "doc_type": "fountain"
    })
    print(f"\n4. POST /api/drive/create_document: status {res4.status_code}, response: {res4.json()}")
    assert res4.status_code in [200, 409]

    # 5. Test GET /api/drive/read_document
    res5 = client.get("/api/drive/read_document?path=/01_Screenplays_and_Scripts/Brett_Feature_Draft.fountain")
    print(f"\n5. GET /api/drive/read_document: status {res5.status_code}")
    doc = res5.json()
    print(f"   Filename: {doc['filename']}")
    print(f"   Category: {doc['category']}")
    print(f"   Content Length: {len(doc['content'])} chars")
    assert res5.status_code == 200
    assert "ECHOES OF THE MATRIX" in doc['content']

    # 6. Test POST /api/drive/save_document
    res6 = client.post("/api/drive/save_document", json={
        "file_path": "/01_Screenplays_and_Scripts/Brett_Feature_Draft.fountain",
        "content": doc['content'] + "\nBRETT\n(smiling)\nEverything is saved to disk.\n"
    })
    print(f"\n6. POST /api/drive/save_document: status {res6.status_code}, response: {res6.json()}")
    assert res6.status_code == 200

    # 7. Test POST /api/drive/zip_download
    res7 = client.post("/api/drive/zip_download", json={
        "paths": ["/01_Screenplays_and_Scripts"],
        "archive_name": "scripts_bundle.zip"
    })
    print(f"\n7. POST /api/drive/zip_download: status {res7.status_code}, bytes length: {len(res7.content)}")
    assert res7.status_code == 200
    assert len(res7.content) > 0

    print("\n✅ ALL SHARED DRIVE ROUTER TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_tests()
