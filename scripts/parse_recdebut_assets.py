import json

with open(r'C:\Users\footb\OneDrive\Desktop\recdebut.com_full_export.json', 'r', encoding='utf-8') as f:
    pages = json.load(f)

all_images = set()
for p in pages:
    for img in p.get('images', []):
        all_images.add(img)

print("=== ALL UNIQUE IMAGES ===")
for img in sorted(all_images):
    print(img)

print("\n=== COACH PROFILES ===")
for p in pages:
    if 'coach-profile' in p.get('url', '') or 'coach' in p.get('url', ''):
        print(f"TITLE: {p.get('title')}")
        print(f"URL: {p.get('url')}")
        print(f"IMAGES: {p.get('images')}")
        lines = [l.strip() for l in p.get('content', '').split('\n') if l.strip()]
        clean = [l for l in lines if l not in ['Skip to content', 'Recreational Debut Is A Nonprofit Organization That Helps Student Athletes', 'home', 'about us', 'Coachs', 'program', 'Awards', 'faq', 'contact', 'vidoes']]
        print("CONTENT:")
        print('\n'.join(clean[:15]))
        print("-" * 50)

print("\n=== PROGRAM / ABOUT / AWARDS / FAQS ===")
for p in pages:
    if any(k in p.get('url', '') for k in ['program', 'about-us', 'awards', 'faq', 'vidoes']):
        print(f"TITLE: {p.get('title')}")
        print(f"URL: {p.get('url')}")
        print(f"IMAGES: {p.get('images')}")
        lines = [l.strip() for l in p.get('content', '').split('\n') if l.strip()]
        clean = [l for l in lines if l not in ['Skip to content', 'Recreational Debut Is A Nonprofit Organization That Helps Student Athletes', 'home', 'about us', 'Coachs', 'program', 'Awards', 'faq', 'contact', 'vidoes']]
        print("SAMPLE CONTENT:")
        print('\n'.join(clean[:10]))
        print("-" * 50)
