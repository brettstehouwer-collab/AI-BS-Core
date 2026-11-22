import os
import re

filepath = r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the flex container for master_plan_23acres with a simple block
pattern = r"(activeSubTab === 'master_plan_23acres' && \(\s*)<div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>"
replacement = r"\1<div style={{ display: 'block' }}>"
content = re.sub(pattern, replacement, content)

# Add margin-bottom to the first block inside it
pattern2 = r"(<div style={{ background: theme\.cardBg, border: theme\.border, borderRadius: '12px', padding: '20px' }}>\s*<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>\s*<h3 style={{ color: theme\.accentCyan, margin: 0 }}>MAP: MASTER PLAN)"
replacement2 = r"<div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>\n            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>\n              <h3 style={{ color: theme.accentCyan, margin: 0 }}>MAP: MASTER PLAN"
content = re.sub(pattern2, replacement2, content)

# Add margin-bottom to the second block
pattern3 = r"(<div style={{ background: theme\.cardBg, border: theme\.border, borderRadius: '12px', padding: '20px' }}>\s*<h3 style={{ color: theme\.accentGreen, marginTop: 0 }}>)"
replacement3 = r"<div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>\n            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>"
content = re.sub(pattern3, replacement3, content)

# Fix images
content = content.replace("style={{ width: '100%', borderRadius: '8px', border: '1px solid rgba(0, 255, 255, 0.3)', boxShadow: '0 0 20px rgba(0, 255, 255, 0.2)' }}", "style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '8px', border: '1px solid rgba(0, 255, 255, 0.3)', boxShadow: '0 0 20px rgba(0, 255, 255, 0.2)' }}")
content = content.replace("style={{ width: '100%', borderRadius: '8px', border: '1px solid rgba(122, 40, 138, 0.4)', boxShadow: '0 0 20px rgba(122, 40, 138, 0.2)' }}", "style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '8px', border: '1px solid rgba(122, 40, 138, 0.4)', boxShadow: '0 0 20px rgba(122, 40, 138, 0.2)' }}")
content = content.replace("style={{ width: '100%', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.4)', boxShadow: '0 0 20px rgba(16, 185, 129, 0.2)' }}", "style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.4)', boxShadow: '0 0 20px rgba(16, 185, 129, 0.2)' }}")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated CSS to use block layout instead of flex column for the master plan tab.")
