import requests

url = "https://cymatics.fm/cart/26872525127744:1,26872799887424:1,29519321432129:1,26872724783168:1,30568026898497:1,31776639516757:1,40912744874069:1,40858166329429:1?checkout"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

r = requests.get(url, headers=headers, allow_redirects=False)
print("Status:", r.status_code)
print("Location:", r.headers.get("Location"))
