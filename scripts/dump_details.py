import json

with open(r'c:\AI-BS\saved_data\recdebut_extracted_summary.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== COACH PROFILES DETAILS ===")
for url, p in data.items():
    if 'coach-profile' in url:
        print(f"\n--- {p['title']} ({url}) ---")
        print("Images:", p['images'])
        print("Content:")
        print(p['content'])

print("\n=== AWARDS DETAILS ===")
for url, p in data.items():
    if 'awards' in url:
        print(f"\n--- {p['title']} ---")
        print(p['content'])

print("\n=== FAQ DETAILS ===")
for url, p in data.items():
    if 'faq' in url:
        print(f"\n--- {p['title']} ---")
        print(p['content'])

print("\n=== PROGRAM DETAILS ===")
for url, p in data.items():
    if 'program' in url and 'all-registration' not in url:
        print(f"\n--- {p['title']} ---")
        print(p['content'])

print("\n=== SPORTS REGISTRATIONS ===")
for url, p in data.items():
    if 'registration' in url:
        print(f"Sport/Page: {p['title']} -> {url}")
