import re
with open("src/App.jsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace any "http://127.0.0.1:8000/some/path" or 'http://127.0.0.1:8000/some/path'
content = re.sub(r'[\'"]http://127\.0\.0\.1:8000(.*?)[\'"]', r'`${backendUrl}\1`', content)
# Replace `http://127.0.0.1:8000/some/path`
content = re.sub(r'`http://127\.0\.0\.1:8000(.*?)`', r'`${backendUrl}\1`', content)
# Replace {`http://127.0.0.1:8000`} specifically (it's covered by the above, but just in case)
content = content.replace("`${backendUrl}`", "backendUrl")

with open("src/App.jsx", "w", encoding="utf-8") as f:
    f.write(content)
