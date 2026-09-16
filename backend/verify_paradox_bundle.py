import requests

url = "https://cymatics.fm/cart/42877744808021:1,42877746315349:1,42877743628373:1,40616236908629:1?checkout"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

r = requests.get(url, headers=headers, allow_redirects=False)
print("Status:", r.status_code)
print("Location:", r.headers.get("Location"))
