import os
import sys

tracker_path = r"C:\AI-BS\frontend\src\components\NocoPropertiesTracker.jsx"
with open(tracker_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """            {/* Export & External Spreadsheet Links */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                onClick={exportAuditJSON}"""

replacement = """            {/* Export & External Spreadsheet Links */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <a
                href="/NoCo_Executive_Due_Diligence_Dossier_2026.pdf"
                target="_blank"
                rel="noreferrer"
                download="NoCo_Executive_Due_Diligence_Dossier_2026.pdf"
                style={{
                  background: 'rgba(239, 68, 68, 0.2)',
                  border: '1px solid #ef4444',
                  color: '#f87171',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 800,
                  textDecoration: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 0 10px rgba(239, 68, 68, 0.25)'
                }}
              >
                📄 Download Executive Dossier (PDF)
              </a>
              <button
                onClick={exportAuditJSON}"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open(tracker_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS LF")
elif target.replace('\n', '\r\n') in content:
    content = content.replace(target.replace('\n', '\r\n'), replacement.replace('\n', '\r\n'), 1)
    with open(tracker_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS CRLF")
else:
    print("TARGET NOT FOUND")
