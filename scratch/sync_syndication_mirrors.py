import os
from pathlib import Path

SYNDICATION_MIRRORS = [
    r"C:\AI-BS\frontend\src\components\SyndicationTab.jsx",
    r"C:\AI-BS\frontend\components\SyndicationTab.jsx",
    r"C:\AI-BS\frontend\src\components\components\SyndicationTab.jsx",
    r"C:\AI-BS\frontend\components\components\SyndicationTab.jsx",
]

TARGET_SNIPPET = """      {/* Fleet Telemetry HUD */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',"""

REPLACEMENT_SNIPPET = """      {/* 🏀 Recreational Debut & Dennis Bell Sports Outreach Syndication Bridge */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(7, 16, 30, 0.95), rgba(10, 23, 42, 0.95))',
        border: '2px solid #F58426',
        borderRadius: '10px',
        padding: '16px 20px',
        marginBottom: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px',
        boxShadow: '0 4px 16px rgba(245, 132, 38, 0.2)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '46px',
            height: '46px',
            borderRadius: '10px',
            background: '#ffffff',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
          }}>
            <img 
              src="https://recdebut.com/wp-content/uploads/2025/08/Screenshot__8_-removebg-preview.png" 
              alt="RD" 
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              onError={(e) => { e.target.parentNode.innerHTML = '<span style="font-size:22px">🏀</span>'; }}
            />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '800', color: '#ffffff' }}>
                Recreational Debut • Mass SMS & College Athletic Outreach Syndication
              </h3>
              <span style={{ backgroundColor: '#F58426', color: '#ffffff', fontSize: '11px', fontWeight: '800', padding: '2px 8px', borderRadius: '4px' }}>
                Dennis Bell • Former New York Knick #4
              </span>
              <span style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#10b981', border: '1px solid #10b981', fontSize: '11px', fontWeight: '700', padding: '2px 6px', borderRadius: '4px' }}>
                MMS Direct Gateway (Full Text Delivery)
              </span>
            </div>
            <div style={{ color: '#94a3b8', fontSize: '12px', marginTop: '4px' }}>
              2,173+ Student-Athletes • 3,116+ Excluded Coaches Blocked • Verified Caller ID: <strong style={{ color: '#10b981' }}>BrettStehouwer@gmail.com</strong>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <a
            href="/?portal=recdebut&tab=syndication"
            style={{
              backgroundColor: '#F58426',
              color: '#ffffff',
              textDecoration: 'none',
              padding: '9px 18px',
              borderRadius: '6px',
              fontWeight: '800',
              fontSize: '13px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 12px rgba(245, 132, 38, 0.3)'
            }}
          >
            <span>🏀 Launch RecDebut Syndication Suite ↗</span>
          </a>
        </div>
      </div>

      {/* Fleet Telemetry HUD */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',"""

for p in SYNDICATION_MIRRORS:
    path = Path(p)
    if not path.exists():
        print("Missing path:", path)
        continue
    content = path.read_text(encoding="utf-8")
    if "Recreational Debut • Mass SMS & College Athletic Outreach Syndication" in content:
        print("Already patched:", path)
        continue
    if TARGET_SNIPPET in content:
        content = content.replace(TARGET_SNIPPET, REPLACEMENT_SNIPPET)
        path.write_text(content, encoding="utf-8")
        print("Patched:", path)
    else:
        print("Could not find TARGET_SNIPPET in:", path)

print("SYNDICATION TAB MIRRORS SYNCHRONIZED!")
