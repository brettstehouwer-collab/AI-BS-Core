import requests

token = "cfut_yhe6w3OJ4xbAL9sIPaS5V8entYRfK47xs3NIK5Lo15afb231"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

try:
    r = requests.get("https://api.cloudflare.com/client/v4/zones", headers=headers, timeout=10)
    print("Status:", r.status_code)
    data = r.json()
    print("Full Cloudflare result:", data)

except Exception as e:
    print("Exception:", e)
