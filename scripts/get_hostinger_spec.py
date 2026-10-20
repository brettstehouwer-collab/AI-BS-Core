import requests

urls = [
    "https://developers.hostinger.com/openapi.json",
    "https://developers.hostinger.com/api/openapi.json",
    "https://developers.hostinger.com/swagger.json",
    "https://developers.hostinger.com/api/swagger.json",
    "https://developers.hostinger.com/api-docs",
    "https://developers.hostinger.com/api/v1/openapi.json"
]

for u in urls:
    try:
        r = requests.get(u, timeout=5)
        print(u, "->", r.status_code, len(r.text))
        if r.status_code == 200 and ("paths" in r.text or "openapi" in r.text):
            print("Found openapi spec at:", u)
            with open("C:/AI-BS/saved_data/hostinger_openapi.json", "w", encoding="utf-8") as f:
                f.write(r.text)
            break
    except Exception as e:
        print(u, "error:", e)
