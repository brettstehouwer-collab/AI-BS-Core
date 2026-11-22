import os

filepath = r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_str = '''      <div style={{
        background: theme.bg,
        color: theme.textLight,
        minHeight: '100vh',
        padding: '20px',
        fontFamily: 'Inter, system-ui, sans-serif'
      }}>'''

new_str = '''      <div style={{
        background: theme.bg,
        color: theme.textLight,
        height: '100%',
        overflowY: 'auto',
        padding: '20px',
        fontFamily: 'Inter, system-ui, sans-serif'
      }}>'''

if old_str in content:
    content = content.replace(old_str, new_str)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Scroll fix applied!")
else:
    print("Could not find the target string. Here is a snippet around minHeight:")
    idx = content.find("minHeight")
    if idx != -1:
        print(content[idx-50:idx+50])
    else:
        print("minHeight not found anywhere")
