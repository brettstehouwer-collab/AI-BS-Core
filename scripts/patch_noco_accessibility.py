#!/usr/bin/env python3
"""
Precision Accessibility & Performance Patch for Project NoCo Dashboard
Resolves all issues identified in Lighthouse Audit Report (NoCo page review.pdf):
1. Accessible labels & IDs for Range Sliders and Select Elements
2. Sequential Heading Hierarchy (h1 -> h2 -> h3)
3. Accessible labels for all search, filter, and audit inputs in NocoPropertiesTracker
4. Layout shift containment for MobileStehouwerChat
5. Transition cleanup for non-composited animations
"""

from pathlib import Path

# --- 1. Patch ProjectNoCoStudioTab.jsx ---
noco_studio_path = Path("C:/AI-BS/frontend/src/components/ProjectNoCoStudioTab.jsx")
content = noco_studio_path.read_text(encoding="utf-8")

# Add H2 header before acoustic simulators and add label/id/aria-label to Glazing Tilt
old_acoustic_top = """      {activeSubTab === 'acoustic_engineering' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
          {/* SIMULATOR 1: GLAZING TILT & REFLECTION RAY TRACING */}
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🪟 Smart Glass Glazing Tilt Angle Simulator</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              Standard smart-tinting glass has high specular reflectivity. Angling floor-to-ceiling glass panes <strong>5°–7° off vertical</strong> directs reflections toward ceiling acoustic absorbers rather than performance microphones.
            </p>

            <div style={{ margin: '16px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: theme.textMuted, marginBottom: '6px' }}>
                <span>Glass Tilt Angle: <strong style={{ color: '#00FFFF' }}>{glazingTiltAngle}° off vertical</strong></span>
                <span>{glazingTiltAngle >= 5 && glazingTiltAngle <= 7 ? '✅ OPTIMAL ACOUSTIC TILT (5°-7°)' : '⚠️ NON-OPTIMAL TILT'}</span>
              </div>
              <input
                type="range" min="0" max="15" step="0.5" value={glazingTiltAngle}
                onChange={(e) => setGlazingTiltAngle(parseFloat(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>"""

new_acoustic_top = """      {activeSubTab === 'acoustic_engineering' && (
        <div>
          <div style={{ marginBottom: '18px' }}>
            <h2 style={{ color: '#ffffff', fontSize: '1.3rem', fontWeight: 700, margin: '0 0 6px 0' }}>
              Acoustic Engineering & Sound Shell Simulators
            </h2>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', margin: 0 }}>
              Specular reflection ray tracing, bio-acoustic soil absorption coefficients, and cardioid sub-stage mechanical isolation.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
            {/* SIMULATOR 1: GLAZING TILT & REFLECTION RAY TRACING */}
            <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🪟 Smart Glass Glazing Tilt Angle Simulator</h3>
              <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
                Standard smart-tinting glass has high specular reflectivity. Angling floor-to-ceiling glass panes <strong>5°–7° off vertical</strong> directs reflections toward ceiling acoustic absorbers rather than performance microphones.
              </p>

              <div style={{ margin: '16px 0' }}>
                <label
                  htmlFor="glazing-tilt-range"
                  style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: theme.textMuted, marginBottom: '6px', cursor: 'pointer' }}
                >
                  <span>Glass Tilt Angle: <strong style={{ color: '#00FFFF' }}>{glazingTiltAngle}° off vertical</strong></span>
                  <span>{glazingTiltAngle >= 5 && glazingTiltAngle <= 7 ? '✅ OPTIMAL ACOUSTIC TILT (5°-7°)' : '⚠️ NON-OPTIMAL TILT'}</span>
                </label>
                <input
                  id="glazing-tilt-range"
                  name="glazingTiltAngle"
                  aria-label="Smart Glass Glazing Tilt Angle in degrees off vertical"
                  type="range" min="0" max="15" step="0.5" value={glazingTiltAngle}
                  onChange={(e) => setGlazingTiltAngle(parseFloat(e.target.value))}
                  style={{ width: '100%', cursor: 'pointer' }}
                />
              </div>"""

# Subwoofer array accessibility label & ID
old_subwoofer = """            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block', marginBottom: '6px' }}>Select Subwoofer Dispersion Mode over Concrete Floor:</label>
              <select
                value={subwooferArrayMode}
                onChange={(e) => setSubwooferArrayMode(e.target.value)}
                style={{ width: '100%', background: '#0d1117', color: '#c084fc', border: '1px solid #7A288A', padding: '8px', borderRadius: '6px' }}
              >
                <option value="cardioid">🔊 Cardioid Array (Recommended: Rejection at Rear Stage)</option>
                <option value="end_fire">🔊 End-Fire Array (High Directional Throw)</option>
              </select>
            </div>"""

new_subwoofer = """            <div style={{ marginBottom: '14px' }}>
              <label htmlFor="subwoofer-array-select" style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block', marginBottom: '6px' }}>
                Select Subwoofer Dispersion Mode over Concrete Floor:
              </label>
              <select
                id="subwoofer-array-select"
                name="subwooferArrayMode"
                aria-label="Subwoofer Acoustic Array Configuration"
                value={subwooferArrayMode}
                onChange={(e) => setSubwooferArrayMode(e.target.value)}
                style={{ width: '100%', background: '#0d1117', color: '#c084fc', border: '1px solid #7A288A', padding: '8px', borderRadius: '6px' }}
              >
                <option value="cardioid">🔊 Cardioid Array (Recommended: Rejection at Rear Stage)</option>
                <option value="end_fire">🔊 End-Fire Array (High Directional Throw)</option>
              </select>
            </div>"""

old_acoustic_close = """          </div>
        </div>
      )}"""

new_acoustic_close = """          </div>
        </div>
        </div>
      )}"""

if old_acoustic_top in content:
    content = content.replace(old_acoustic_top, new_acoustic_top)
    content = content.replace(old_subwoofer, new_subwoofer)
    content = content.replace(old_acoustic_close, new_acoustic_close, 1)
    noco_studio_path.write_text(content, encoding="utf-8")
    print("[OK] ProjectNoCoStudioTab.jsx patched with H2 heading and accessible form labels.")
else:
    print("! Notice: old_acoustic_top not matched in ProjectNoCoStudioTab.jsx")

# --- 2. Patch NocoPropertiesTracker.jsx ---
tracker_path = Path("C:/AI-BS/frontend/src/components/NocoPropertiesTracker.jsx")
t_content = tracker_path.read_text(encoding="utf-8")

# Candidates search input
t_content = t_content.replace(
    """            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Search address, county, criteria...\"""",
    """            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                id="noco-candidate-search"
                name="nocoCandidateSearch"
                aria-label="Search candidate properties by address, county, or criteria"
                type="text"
                placeholder="Search address, county, criteria...\""""
)

# Active Audit Parcel select
t_content = t_content.replace(
    """              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Active Audit Parcel:
              </div>
              <select
                value={selectedAuditPropertyId}
                onChange={e => setSelectedAuditPropertyId(e.target.value)}""",
    """              <label htmlFor="noco-audit-parcel-select" style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block' }}>
                Active Audit Parcel:
              </label>
              <select
                id="noco-audit-parcel-select"
                name="nocoAuditParcelSelect"
                aria-label="Select Active Audit Parcel"
                value={selectedAuditPropertyId}
                onChange={e => setSelectedAuditPropertyId(e.target.value)}"""
)

# Due Diligence search input
t_content = t_content.replace(
    """            <input
              type="text"
              placeholder="Search due diligence questions, benchmark criteria, sources..."
              value={auditSearchQuery}""",
    """            <input
              id="noco-dd-search"
              name="nocoDdSearch"
              aria-label="Search due diligence questions, benchmark criteria, and sources"
              type="text"
              placeholder="Search due diligence questions, benchmark criteria, sources..."
              value={auditSearchQuery}"""
)

# Realtor / Seller response input
t_content = t_content.replace(
    """                        <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: '4px', fontWeight: 600 }}>
                          Realtor / Seller Response:
                        </div>
                        <input
                          type="text"
                          placeholder="Enter verified seller disclosure or realtor feedback..."
                          value={audit.realtorResponse || ''}""",
    """                        <label htmlFor={`realtor-resp-${item.id}`} style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: '4px', fontWeight: 600, display: 'block' }}>
                          Realtor / Seller Response:
                        </label>
                        <input
                          id={`realtor-resp-${item.id}`}
                          aria-label={`Realtor or seller response for question ${item.id}`}
                          type="text"
                          placeholder="Enter verified seller disclosure or realtor feedback..."
                          value={audit.realtorResponse || ''}"""
)

# Notes / Action items input
t_content = t_content.replace(
    """                        <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: '4px', fontWeight: 600 }}>
                          Action Items & Due Diligence Notes:
                        </div>
                        <input
                          type="text"
                          placeholder="e.g. Schedule perc test, pull GIS deed plat..."
                          value={audit.notes || ''}""",
    """                        <label htmlFor={`notes-${item.id}`} style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: '4px', fontWeight: 600, display: 'block' }}>
                          Action Items & Due Diligence Notes:
                        </label>
                        <input
                          id={`notes-${item.id}`}
                          aria-label={`Action items and due diligence notes for question ${item.id}`}
                          type="text"
                          placeholder="e.g. Schedule perc test, pull GIS deed plat..."
                          value={audit.notes || ''}"""
)

# Condition evaluation inputs & range sliders
t_content = t_content.replace(
    """              <div>
                <label style={{ fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 600 }}>Parcel Address / Nickname:</label>
                <input
                  type="text"
                  value={evalAddress}""",
    """              <div>
                <label htmlFor="eval-address-input" style={{ fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 600 }}>Parcel Address / Nickname:</label>
                <input
                  id="eval-address-input"
                  name="evalAddress"
                  aria-label="Parcel Address or Nickname for Condition Evaluation"
                  type="text"
                  value={evalAddress}"""
)

t_content = t_content.replace(
    """              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Acreage (Target: 10–25 ac):</span>
                  <span style={{ color: '#00FFFF', fontWeight: 800 }}>{evalAcres} acres</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="80"
                  step="0.5"
                  value={evalAcres}""",
    """              <div>
                <label htmlFor="eval-acres-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1', cursor: 'pointer' }}>
                  <span>Acreage (Target: 10–25 ac):</span>
                  <span style={{ color: '#00FFFF', fontWeight: 800 }}>{evalAcres} acres</span>
                </label>
                <input
                  id="eval-acres-slider"
                  name="evalAcres"
                  aria-label="Parcel Acreage Slider"
                  type="range"
                  min="1"
                  max="80"
                  step="0.5"
                  value={evalAcres}"""
)

t_content = t_content.replace(
    """              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Asking Price:</span>
                  <span style={{ color: '#10b981', fontWeight: 800 }}>${evalPrice.toLocaleString()} (${Math.round(evalPrice / (evalAcres || 1)).toLocaleString()}/ac)</span>
                </div>
                <input
                  type="range"
                  min="30000"
                  max="1200000"
                  step="10000"
                  value={evalPrice}""",
    """              <div>
                <label htmlFor="eval-price-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1', cursor: 'pointer' }}>
                  <span>Asking Price:</span>
                  <span style={{ color: '#10b981', fontWeight: 800 }}>${evalPrice.toLocaleString()} (${Math.round(evalPrice / (evalAcres || 1)).toLocaleString()}/ac)</span>
                </label>
                <input
                  id="eval-price-slider"
                  name="evalPrice"
                  aria-label="Asking Price Slider"
                  type="range"
                  min="30000"
                  max="1200000"
                  step="10000"
                  value={evalPrice}"""
)

t_content = t_content.replace(
    """              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Acoustic Topography & Bowl Rake (25% Weight):</span>
                  <span style={{ color: '#c084fc', fontWeight: 800 }}>{evalAcoustic} / 100</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalAcoustic}""",
    """              <div>
                <label htmlFor="eval-acoustic-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1', cursor: 'pointer' }}>
                  <span>Acoustic Topography & Bowl Rake (25% Weight):</span>
                  <span style={{ color: '#c084fc', fontWeight: 800 }}>{evalAcoustic} / 100</span>
                </label>
                <input
                  id="eval-acoustic-slider"
                  name="evalAcoustic"
                  aria-label="Acoustic Topography Score Slider"
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalAcoustic}"""
)

t_content = t_content.replace(
    """              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Water Rights, Springs & Hydrology (20% Weight):</span>
                  <span style={{ color: '#38bdf8', fontWeight: 800 }}>{evalWater} / 100</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalWater}""",
    """              <div>
                <label htmlFor="eval-water-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1', cursor: 'pointer' }}>
                  <span>Water Rights, Springs & Hydrology (20% Weight):</span>
                  <span style={{ color: '#38bdf8', fontWeight: 800 }}>{evalWater} / 100</span>
                </label>
                <input
                  id="eval-water-slider"
                  name="evalWater"
                  aria-label="Water Rights and Hydrology Score Slider"
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalWater}"""
)

t_content = t_content.replace(
    """              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>CEA & Agritourism Zoning Flexibility (15% Weight):</span>
                  <span style={{ color: '#10b981', fontWeight: 800 }}>{evalZoning} / 100</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalZoning}""",
    """              <div>
                <label htmlFor="eval-zoning-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1', cursor: 'pointer' }}>
                  <span>CEA & Agritourism Zoning Flexibility (15% Weight):</span>
                  <span style={{ color: '#10b981', fontWeight: 800 }}>{evalZoning} / 100</span>
                </label>
                <input
                  id="eval-zoning-slider"
                  name="evalZoning"
                  aria-label="CEA and Agritourism Zoning Score Slider"
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalZoning}"""
)

t_content = t_content.replace(
    """              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Industrial / Sprawl / Data Center Shield (15% Weight):</span>
                  <span style={{ color: '#ef4444', fontWeight: 800 }}>{evalShield} / 100</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalShield}""",
    """              <div>
                <label htmlFor="eval-shield-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1', cursor: 'pointer' }}>
                  <span>Industrial / Sprawl / Data Center Shield (15% Weight):</span>
                  <span style={{ color: '#ef4444', fontWeight: 800 }}>{evalShield} / 100</span>
                </label>
                <input
                  id="eval-shield-slider"
                  name="evalShield"
                  aria-label="Industrial and Sprawl Shield Score Slider"
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalShield}"""
)

tracker_path.write_text(t_content, encoding="utf-8")
print("[OK] NocoPropertiesTracker.jsx patched with accessible labels, ids, and aria-labels across all controls.")

# --- 3. Patch MobileStehouwerChat.jsx ---
mobile_chat_path = Path("C:/AI-BS/frontend/src/components/MobileStehouwerChat.jsx")
m_content = mobile_chat_path.read_text(encoding="utf-8")

# Fix candidateBases to not call unsecure HTTP on HTTPS
old_cand = """      const candidateBases = [
        BACKEND_URL,
        'https://api.brettstehouwer.live',
        'http://127.0.0.1:8080',
        'http://localhost:8080',
        'http://192.168.4.92:8080'
      ].filter(Boolean);"""

new_cand = """      const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
      const candidateBases = [
        BACKEND_URL,
        'https://api.brettstehouwer.live',
        !isHttps ? 'http://127.0.0.1:8080' : null,
        !isHttps ? 'http://localhost:8080' : null,
        !isHttps ? 'http://192.168.4.92:8080' : null
      ].filter(Boolean);"""

if old_cand in m_content:
    m_content = m_content.replace(old_cand, new_cand)

# Containment for GPU banner to prevent CLS
old_banner_style = """            {/* God-Mode GPU Telemetry Banner */}
            <div style={{
              width: '100%',
              marginBottom: '24px',
              padding: '12px 16px',"""

new_banner_style = """            {/* God-Mode GPU Telemetry Banner */}
            <div style={{
              width: '100%',
              minHeight: '76px',
              contain: 'layout',
              marginBottom: '24px',
              padding: '12px 16px',"""

if old_banner_style in m_content:
    m_content = m_content.replace(old_banner_style, new_banner_style)

# Composited transitions for suggestion chips
old_chip_trans = """                    minHeight: '60px',
                    transition: 'all 0.15s ease'"""

new_chip_trans = """                    minHeight: '60px',
                    transition: 'transform 0.15s ease, opacity 0.15s ease, background-color 0.15s ease'"""

if old_chip_trans in m_content:
    m_content = m_content.replace(old_chip_trans, new_chip_trans)

mobile_chat_path.write_text(m_content, encoding="utf-8")
print("[OK] MobileStehouwerChat.jsx patched with HTTPS filtering, banner layout containment, and composited transitions.")

# --- 4. Patch style.css (Remove continuous backgroundShift on body) ---
style_css_path = Path("C:/AI-BS/frontend/style.css")
s_content = style_css_path.read_text(encoding="utf-8")

old_body_bg = """body {
  margin: 0;
  color: #d7ffd8;
  background: radial-gradient(circle at 15% 10%, rgba(120, 20, 190, 0.35), transparent 30%),
              radial-gradient(circle at 85% 20%, rgba(63, 0, 255, 0.28), transparent 25%),
              radial-gradient(circle at 50% 80%, rgba(0, 209, 166, 0.24), transparent 35%),
              #0b0717;
  background-size: 200% 200%;
  animation: backgroundShift 20s ease infinite;
}"""

new_body_bg = """body {
  margin: 0;
  color: #d7ffd8;
  background: radial-gradient(circle at 15% 10%, rgba(120, 20, 190, 0.35), transparent 30%),
              radial-gradient(circle at 85% 20%, rgba(63, 0, 255, 0.28), transparent 25%),
              radial-gradient(circle at 50% 80%, rgba(0, 209, 166, 0.24), transparent 35%),
              #0b0717;
  background-attachment: fixed;
}"""

if old_body_bg in s_content:
    s_content = s_content.replace(old_body_bg, new_body_bg)
    style_css_path.write_text(s_content, encoding="utf-8")
    print("[OK] style.css body backgroundShift animation replaced with fixed high-performance gradient.")
