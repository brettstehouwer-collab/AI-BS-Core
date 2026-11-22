path = '/var/lib/vastai_kaalia/latest/ktxt_tojson.py'
with open(path) as f:
    content = f.read()

target = 'minor_no = int(gpu.find("minor_number").text)'
replacement = 'minor_elem = gpu.find("minor_number")\n        minor_no = int(minor_elem.text) if minor_elem is not None and minor_elem.text and minor_elem.text.isdigit() else cidx'

if target in content:
    content = content.replace(target, replacement, 1)
    with open(path, 'w') as f:
        f.write(content)
    print('Successfully patched ktxt_tojson.py!')
else:
    print('Target string not found!')
