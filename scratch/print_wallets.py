import json

with open(r'C:\AI-BS\scratch\wallet_audit_results.json', 'r') as f:
    data = json.load(f)

print(f"Total addresses cataloged: {len(data)}\n")
for item in data:
    if not item['is_contract']:
        print(f"[{item['type']}] {item['address']}")
        print(f"  Files: {item['file_count']}")
        print(f"  Labels: {item['context_labels']}")
        print("-" * 65)
