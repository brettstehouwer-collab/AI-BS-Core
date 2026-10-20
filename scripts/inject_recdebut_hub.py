import json
from pathlib import Path

target = Path("C:/AI-BS/frontend/src/components/clients/DennisBellPortal.jsx")
content = target.read_text(encoding="utf-8")

# 1. Update activeTab URL param check
old_tab_check = "if (tab && ['telemetry', 'syndication', 'emails', 'replies', 'campaigns', 'roster', 'submit', 'network'].includes(tab))"
new_tab_check = "if (tab && ['telemetry', 'syndication', 'emails', 'replies', 'campaigns', 'roster', 'submit', 'network', 'cloudflared', 'recdebut_hub'].includes(tab))"
if old_tab_check in content:
    content = content.replace(old_tab_check, new_tab_check, 1)

# 2. Add state
old_state = "const [cfResult, setCfResult] = useState(null);"
new_state = """const [cfResult, setCfResult] = useState(null);

  // RecDebut.com Site Hub State
  const [siteData, setSiteData] = useState(null);
  const [hubSection, setHubSection] = useState('sports'); // 'sports' | 'coaches' | 'nominees' | 'packages' | 'faq' | 'directory'
  const [hubSportSearch, setHubSportSearch] = useState('');
  const [hubNomineeSearch, setHubNomineeSearch] = useState('');
  const [hubNomineeState, setHubNomineeState] = useState('ALL');
  const [hubCustomAthlete, setHubCustomAthlete] = useState('');
  const [hubCustomSport, setHubCustomSport] = useState('Basketball');
  const [hubGeneratedLink, setHubGeneratedLink] = useState(null);
  const [hubGeneratingLink, setHubGeneratingLink] = useState(false);
  const [copiedSiteLink, setCopiedSiteLink] = useState(false);"""
if old_state in content and "setSiteData" not in content:
    content = content.replace(old_state, new_state, 1)

# 3. Add fetch
old_fetch = "fetch(`${BACKEND_URL}/api/v1/recdebut/cloudflared/status`).then(r => r.json()).catch(() => null)"
new_fetch = """fetch(`${BACKEND_URL}/api/v1/recdebut/cloudflared/status`).then(r => r.json()).catch(() => null),
        fetch(`${BACKEND_URL}/api/v1/recdebut/site-data`).then(r => r.json()).catch(() => null)"""
if old_fetch in content and "site-data" not in content:
    content = content.replace(old_fetch, new_fetch, 1)

old_fetch_assign = """      const [athRes, campRes, coachRes, quotaRes, smtpRes, emailSumRes, repliesRes, analyticsRes, cfRes] = await Promise.all(["""
new_fetch_assign = """      const [athRes, campRes, coachRes, quotaRes, smtpRes, emailSumRes, repliesRes, analyticsRes, cfRes, siteRes] = await Promise.all(["""
if old_fetch_assign in content:
    content = content.replace(old_fetch_assign, new_fetch_assign, 1)

old_cf_set = """      if (cfRes && cfRes.success) {
        setCfStatus(cfRes);
      }"""
new_cf_set = """      if (cfRes && cfRes.success) {
        setCfStatus(cfRes);
      }
      if (siteRes && siteRes.success) {
        setSiteData(siteRes);
      }"""
if old_cf_set in content and "setSiteData(siteRes)" not in content:
    content = content.replace(old_cf_set, new_cf_set, 1)

# 4. Add link generation handler
old_ping_handler = "setCfSending(false);\n    }\n  };"
new_ping_handler = """setCfSending(false);
    }
  };

  // RecDebut.com Link Generator Handler
  const handleGenerateRegistrationLink = async (sportName, athleteName) => {
    setHubGeneratingLink(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/generate-registration-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sport: sportName || hubCustomSport,
          athlete_name: athleteName || hubCustomAthlete || undefined
        })
      });
      const data = await res.json();
      if (data.success) {
        setHubGeneratedLink(data);
      }
    } catch (e) {
      console.error('Failed to generate registration link:', e);
    } finally {
      setHubGeneratingLink(false);
    }
  };"""
if old_ping_handler in content and "handleGenerateRegistrationLink" not in content:
    content = content.replace(old_ping_handler, new_ping_handler, 1)

# 5. Add Tab button
old_tab_btn = "{ id: 'cloudflared', label: '☁️ Cloudflared Edge Dispatcher', badge: 'api.brettstehouwer.live' },"
new_tab_btn = """{ id: 'cloudflared', label: '☁️ Cloudflared Edge Dispatcher', badge: 'api.brettstehouwer.live' },
            { id: 'recdebut_hub', label: '🌐 RecDebut.com Site Hub', badge: '14 Sports • Leadership • 28 Pages' },"""
if old_tab_btn in content and "recdebut_hub" not in content:
    content = content.replace(old_tab_btn, new_tab_btn, 1)

# 6. Tab Markup
hub_jsx = """
        {/* ── TAB: RECDEBUT.COM SITE HUB ────────────────────────────────────── */}
        {activeTab === 'recdebut_hub' && (
          <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Header Banner */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(245, 132, 38, 0.15) 0%, rgba(16, 185, 129, 0.10) 100%)',
              border: '1px solid rgba(245, 132, 38, 0.35)',
              borderRadius: '16px',
              padding: '28px 32px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '20px'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '32px' }}>🌐</span>
                  <h2 style={{ fontSize: '26px', fontWeight: '900', color: '#fff', margin: 0, letterSpacing: '-0.5px' }}>
                    RECDEBUT.COM OFFICIAL PLATFORM ECOSYSTEM
                  </h2>
                </div>
                <p style={{ color: '#94a3b8', fontSize: '14px', margin: 0, maxWidth: '820px', lineHeight: 1.6 }}>
                  Direct portal integration with RecDebut.com • A 501(c)(3) Nonprofit Organization helping student-athletes turn dreams into collegiate opportunities since 1984. Founded & presided by Dennis Bell (Former NY Knicks).
                </p>
                <div style={{ display: 'flex', gap: '10px', marginTop: '16px', flexWrap: 'wrap' }}>
                  <span style={{ background: 'rgba(245, 132, 38, 0.2)', color: '#F58426', border: '1px solid rgba(245, 132, 38, 0.4)', borderRadius: '20px', padding: '4px 12px', fontSize: '12px', fontWeight: '700' }}>
                    ✓ 28 Pages Ingested
                  </span>
                  <span style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.4)', borderRadius: '20px', padding: '4px 12px', fontSize: '12px', fontWeight: '700' }}>
                    ✓ 14 Sport Portals
                  </span>
                  <span style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.4)', borderRadius: '20px', padding: '4px 12px', fontSize: '12px', fontWeight: '700' }}>
                    ✓ 4 Executive Leaders
                  </span>
                  <span style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#fbbf24', border: '1px solid rgba(234, 179, 8, 0.4)', borderRadius: '20px', padding: '4px 12px', fontSize: '12px', fontWeight: '700' }}>
                    ✓ 15 All-American Nominees
                  </span>
                  <span style={{ background: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.4)', borderRadius: '20px', padding: '4px 12px', fontSize: '12px', fontWeight: '700' }}>
                    ✓ 501(c)(3) Tax Deductible
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <a
                  href="https://recdebut.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    background: '#F58426',
                    color: '#fff',
                    padding: '12px 24px',
                    borderRadius: '10px',
                    fontWeight: '800',
                    fontSize: '14px',
                    textDecoration: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: '0 4px 16px rgba(245, 132, 38, 0.4)'
                  }}
                >
                  <span>🌐</span> Launch RecDebut.com ↗
                </a>
                <a
                  href="https://recdebut.com/all-registration/"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: '#fff',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    padding: '12px 20px',
                    borderRadius: '10px',
                    fontWeight: '700',
                    fontSize: '14px',
                    textDecoration: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <span>📋</span> Master Registration Hub ↗
                </a>
              </div>
            </div>

            {/* Sub-Section Navigation Pills */}
            <div style={{ display: 'flex', gap: '8px', background: 'rgba(15, 23, 42, 0.6)', padding: '6px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)', overflowX: 'auto' }}>
              {[
                { id: 'sports', label: '🏅 14 Sport Portals & Intake Links', count: siteData?.sports?.length || 14 },
                { id: 'coaches', label: '👔 Coaching Staff & Leadership', count: siteData?.coaches?.length || 4 },
                { id: 'nominees', label: '⭐ Pre-Season All-Americans', count: siteData?.nominees?.length || 15 },
                { id: 'packages', label: '📦 Programs, Packages & 501(c)(3)' },
                { id: 'faq', label: '❓ Official RecDebut FAQ' },
                { id: 'directory', label: '🗺️ Full 28-Page Directory', count: 28 }
              ].map(sec => (
                <button
                  key={sec.id}
                  onClick={() => setHubSection(sec.id)}
                  style={{
                    padding: '10px 18px',
                    borderRadius: '8px',
                    border: 'none',
                    cursor: 'pointer',
                    fontWeight: '700',
                    fontSize: '13px',
                    whiteSpace: 'nowrap',
                    background: hubSection === sec.id ? '#F58426' : 'transparent',
                    color: hubSection === sec.id ? '#fff' : '#94a3b8',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  {sec.label}
                  {sec.count !== undefined && (
                    <span style={{
                      background: hubSection === sec.id ? 'rgba(0,0,0,0.25)' : 'rgba(255,255,255,0.1)',
                      color: hubSection === sec.id ? '#fff' : '#cbd5e1',
                      borderRadius: '10px',
                      padding: '2px 8px',
                      fontSize: '11px',
                      fontWeight: '800'
                    }}>
                      {sec.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* SECTION 1: 14 SPORT PORTALS & INTAKE LINK GENERATOR */}
            {hubSection === 'sports' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                
                {/* Dynamic Intake Link Generator Card */}
                <div style={{
                  background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)',
                  border: '1px solid rgba(245, 132, 38, 0.3)',
                  borderRadius: '14px',
                  padding: '24px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                    <span style={{ fontSize: '24px' }}>⚡</span>
                    <div>
                      <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#fff' }}>
                        Custom Athlete Registration Link Generator
                      </h3>
                      <p style={{ margin: '2px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                        Create a direct, trackable RecDebut.com intake link pre-populated with any athlete's name to text or email them directly.
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', alignItems: 'end' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                        Select Target Sport:
                      </label>
                      <select
                        value={hubCustomSport}
                        onChange={(e) => setHubCustomSport(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '10px 14px',
                          background: 'rgba(15, 23, 42, 0.8)',
                          border: '1px solid rgba(255, 255, 255, 0.15)',
                          borderRadius: '8px',
                          color: '#fff',
                          fontSize: '14px',
                          fontWeight: '600'
                        }}
                      >
                        {(siteData?.sports || []).map(s => (
                          <option key={s.name} value={s.name}>{s.icon} {s.name}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                        Candidate Athlete Name (Optional):
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Marcus Johnson or pick from Roster"
                        value={hubCustomAthlete}
                        onChange={(e) => setHubCustomAthlete(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '10px 14px',
                          background: 'rgba(15, 23, 42, 0.8)',
                          border: '1px solid rgba(255, 255, 255, 0.15)',
                          borderRadius: '8px',
                          color: '#fff',
                          fontSize: '14px'
                        }}
                      />
                    </div>

                    <div>
                      <button
                        onClick={() => handleGenerateRegistrationLink(hubCustomSport, hubCustomAthlete)}
                        disabled={hubGeneratingLink}
                        style={{
                          width: '100%',
                          padding: '11px 20px',
                          background: '#F58426',
                          color: '#fff',
                          border: 'none',
                          borderRadius: '8px',
                          fontWeight: '800',
                          fontSize: '14px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px'
                        }}
                      >
                        {hubGeneratingLink ? '⚡ Generating...' : '🔗 Generate Intake Link'}
                      </button>
                    </div>
                  </div>

                  {hubGeneratedLink && (
                    <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        <span style={{ fontSize: '11px', textTransform: 'uppercase', color: '#10b981', fontWeight: '800', letterSpacing: '0.5px' }}>
                          ✓ Live Sport Intake Link Ready:
                        </span>
                        <div style={{ fontSize: '14px', color: '#fff', fontWeight: '700', marginTop: '2px', wordBreak: 'break-all' }}>
                          {hubGeneratedLink.direct_url}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(hubGeneratedLink.direct_url);
                            setCopiedSiteLink(true);
                            setTimeout(() => setCopiedSiteLink(false), 2000);
                          }}
                          style={{
                            padding: '8px 16px',
                            background: copiedSiteLink ? '#10b981' : '#334155',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '6px',
                            fontWeight: '700',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }}
                        >
                          {copiedSiteLink ? '✓ Copied!' : '📋 Copy Link'}
                        </button>
                        <a
                          href={hubGeneratedLink.direct_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '8px 16px',
                            background: '#F58426',
                            color: '#fff',
                            borderRadius: '6px',
                            fontWeight: '700',
                            fontSize: '12px',
                            textDecoration: 'none'
                          }}
                        >
                          Launch ↗
                        </a>
                      </div>
                    </div>
                  )}
                </div>

                {/* 14 Sport Portals Grid */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                    <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#fff' }}>
                      Official RecDebut.com Sport Registration Hubs ({siteData?.sports?.length || 14})
                    </h3>
                    <input
                      type="text"
                      placeholder="Search sport (e.g. Football, Basketball)..."
                      value={hubSportSearch}
                      onChange={(e) => setHubSportSearch(e.target.value)}
                      style={{
                        padding: '8px 14px',
                        background: 'rgba(15, 23, 42, 0.8)',
                        border: '1px solid rgba(255, 255, 255, 0.15)',
                        borderRadius: '8px',
                        color: '#fff',
                        fontSize: '13px',
                        width: '260px'
                      }}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
                    {(siteData?.sports || [])
                      .filter(s => !hubSportSearch || s.name.toLowerCase().includes(hubSportSearch.toLowerCase()))
                      .map(sport => (
                        <div
                          key={sport.name}
                          style={{
                            background: 'rgba(30, 41, 59, 0.5)',
                            border: '1px solid rgba(255, 255, 255, 0.08)',
                            borderRadius: '12px',
                            padding: '20px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            transition: 'transform 0.2s, border-color 0.2s',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                              <span style={{ fontSize: '32px' }}>{sport.icon}</span>
                              <span style={{ background: 'rgba(245, 132, 38, 0.15)', color: '#F58426', padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: '800' }}>
                                {sport.category}
                              </span>
                            </div>
                            <h4 style={{ margin: '0 0 6px 0', fontSize: '18px', fontWeight: '800', color: '#fff' }}>
                              {sport.name}
                            </h4>
                            <p style={{ margin: '0 0 12px 0', fontSize: '12px', color: '#94a3b8' }}>
                              Official intake portal for prospective collegiate {sport.name.toLowerCase()} student-athletes.
                            </p>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '16px' }}>
                              {(sport.fields || []).slice(0, 4).map(f => (
                                <span key={f} style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#cbd5e1', padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: '600' }}>
                                  ✓ {f}
                                </span>
                              ))}
                              {(sport.fields || []).length > 4 && (
                                <span style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#94a3b8', padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: '600' }}>
                                  +{sport.fields.length - 4} more
                                </span>
                              )}
                            </div>
                          </div>

                          <div style={{ display: 'flex', gap: '8px' }}>
                            <a
                              href={sport.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                flex: 1,
                                textAlign: 'center',
                                padding: '8px 12px',
                                background: '#F58426',
                                color: '#fff',
                                borderRadius: '6px',
                                fontWeight: '700',
                                fontSize: '12px',
                                textDecoration: 'none'
                              }}
                            >
                              Open Portal ↗
                            </a>
                            <button
                              onClick={() => {
                                handleGenerateRegistrationLink(sport.name, '');
                                window.scrollTo({ top: 300, behavior: 'smooth' });
                              }}
                              style={{
                                padding: '8px 12px',
                                background: '#334155',
                                color: '#fff',
                                border: 'none',
                                borderRadius: '6px',
                                fontWeight: '700',
                                fontSize: '12px',
                                cursor: 'pointer'
                              }}
                            >
                              Create Link
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>

              </div>
            )}

            {/* SECTION 2: COACHING STAFF & LEADERSHIP */}
            {hubSection === 'coaches' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#fff' }}>
                    Executive Leadership & Collegiate Recruiting Staff
                  </h3>
                  <span style={{ fontSize: '13px', color: '#94a3b8' }}>
                    All staff have played or coached at the professional / NCAA collegiate level.
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
                  {(siteData?.coaches || []).map(coach => (
                    <div
                      key={coach.name}
                      style={{
                        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '16px',
                        padding: '24px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.3)'
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '16px' }}>
                          <div style={{
                            width: '56px',
                            height: '56px',
                            borderRadius: '50%',
                            background: 'rgba(245, 132, 38, 0.2)',
                            border: '2px solid #F58426',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '28px'
                          }}>
                            {coach.avatar}
                          </div>
                          <div>
                            <h4 style={{ margin: 0, fontSize: '20px', fontWeight: '900', color: '#fff' }}>
                              {coach.name}
                            </h4>
                            <div style={{ fontSize: '13px', fontWeight: '700', color: '#F58426', marginTop: '2px' }}>
                              {coach.role}
                            </div>
                          </div>
                        </div>

                        <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: '10px', padding: '12px', marginBottom: '14px', fontSize: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <span style={{ color: '#94a3b8' }}>Alma Mater:</span>
                            <span style={{ color: '#fff', fontWeight: '700' }}>{coach.college}</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <span style={{ color: '#94a3b8' }}>Pro / Coaching:</span>
                            <span style={{ color: '#10b981', fontWeight: '700' }}>{coach.pro_career}</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ color: '#94a3b8' }}>Credentials:</span>
                            <span style={{ color: '#cbd5e1', fontWeight: '600' }}>{coach.qualification}</span>
                          </div>
                        </div>

                        <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>
                          {coach.bio}
                        </p>
                      </div>

                      <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                          <div>📞 {coach.phone}</div>
                          <div>✉️ {coach.email}</div>
                        </div>
                        <a
                          href={coach.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '8px 14px',
                            background: '#F58426',
                            color: '#fff',
                            borderRadius: '6px',
                            fontWeight: '700',
                            fontSize: '12px',
                            textDecoration: 'none'
                          }}
                        >
                          Full Profile ↗
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* SECTION 3: PRE-SEASON ALL-AMERICANS & NOMINEES */}
            {hubSection === 'nominees' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#fff' }}>
                      Pre-Season All-American Nominees & Alumni
                    </h3>
                    <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                      Official RecDebut nominees and showcase standouts placed into collegiate programs nationwide.
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', gap: '4px', background: 'rgba(0,0,0,0.3)', padding: '4px', borderRadius: '8px' }}>
                      {['ALL', 'MI', 'IN', 'OH'].map(st => (
                        <button
                          key={st}
                          onClick={() => setHubNomineeState(st)}
                          style={{
                            padding: '4px 10px',
                            border: 'none',
                            borderRadius: '6px',
                            background: hubNomineeState === st ? '#F58426' : 'transparent',
                            color: hubNomineeState === st ? '#fff' : '#94a3b8',
                            fontSize: '12px',
                            fontWeight: '700',
                            cursor: 'pointer'
                          }}
                        >
                          {st}
                        </button>
                      ))}
                    </div>

                    <input
                      type="text"
                      placeholder="Search player, school, or awards..."
                      value={hubNomineeSearch}
                      onChange={(e) => setHubNomineeSearch(e.target.value)}
                      style={{
                        padding: '8px 14px',
                        background: 'rgba(15, 23, 42, 0.8)',
                        border: '1px solid rgba(255, 255, 255, 0.15)',
                        borderRadius: '8px',
                        color: '#fff',
                        fontSize: '13px',
                        width: '240px'
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
                  {(siteData?.nominees || [])
                    .filter(n => {
                      if (hubNomineeState !== 'ALL' && !n.city_state.includes(hubNomineeState)) return false;
                      if (hubNomineeSearch) {
                        const q = hubNomineeSearch.toLowerCase();
                        return n.name.toLowerCase().includes(q) || n.school.toLowerCase().includes(q) || n.awards.toLowerCase().includes(q);
                      }
                      return true;
                    })
                    .map(nominee => (
                      <div
                        key={nominee.name}
                        style={{
                          background: 'rgba(30, 41, 59, 0.6)',
                          border: '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: '12px',
                          padding: '18px',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between'
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                            <div>
                              <h4 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#fff' }}>
                                {nominee.name}
                              </h4>
                              <div style={{ fontSize: '13px', color: '#F58426', fontWeight: '700' }}>
                                📏 {nominee.height} • {nominee.school}
                              </div>
                            </div>
                            <span style={{ background: 'rgba(234, 179, 8, 0.15)', color: '#fbbf24', border: '1px solid rgba(234, 179, 8, 0.3)', padding: '2px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: '800' }}>
                              ⭐ Nominee
                            </span>
                          </div>

                          <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '10px' }}>
                            📍 {nominee.city_state} {nominee.coach ? `• Coach ${nominee.coach}` : ''}
                          </div>

                          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', fontSize: '12px', color: '#cbd5e1', lineHeight: 1.5 }}>
                            🏆 <span style={{ fontWeight: '700', color: '#fff' }}>Accolades:</span> {nominee.awards}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* SECTION 4: PACKAGES & 501(c)(3) TAX BENEFITS */}
            {hubSection === 'packages' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                <div style={{
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: '12px',
                  padding: '20px 24px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px'
                }}>
                  <span style={{ fontSize: '32px' }}>🏛️</span>
                  <div>
                    <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '800', color: '#10b981' }}>
                      100% Tax-Deductible Non-Profit 501(c)(3) Organization
                    </h4>
                    <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#cbd5e1', lineHeight: 1.5 }}>
                      Because Recreational Debut is a registered 501(c)(3) non-profit, all family contributions and enrollment fees are classified as charitable donations and are 100% tax-deductible under IRS guidelines.
                    </p>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
                  {(siteData?.packages || []).map(pkg => (
                    <div
                      key={pkg.name}
                      style={{
                        background: pkg.name.includes('Gold') 
                          ? 'linear-gradient(135deg, rgba(245, 132, 38, 0.15) 0%, rgba(30, 41, 59, 0.9) 100%)' 
                          : 'rgba(30, 41, 59, 0.6)',
                        border: pkg.name.includes('Gold') 
                          ? '2px solid rgba(245, 132, 38, 0.5)' 
                          : '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '16px',
                        padding: '28px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.25)'
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                          <h3 style={{ margin: 0, fontSize: '24px', fontWeight: '900', color: '#fff' }}>
                            {pkg.name}
                          </h3>
                          <span style={{
                            background: pkg.name.includes('Gold') ? 'rgba(245, 132, 38, 0.2)' : 'rgba(255,255,255,0.1)',
                            color: pkg.name.includes('Gold') ? '#F58426' : '#cbd5e1',
                            border: pkg.name.includes('Gold') ? '1px solid #F58426' : 'none',
                            padding: '4px 10px',
                            borderRadius: '12px',
                            fontSize: '11px',
                            fontWeight: '800'
                          }}>
                            {pkg.badge}
                          </span>
                        </div>

                        <div style={{ fontSize: '13px', color: '#10b981', fontWeight: '700', marginBottom: '20px' }}>
                          ✓ {pkg.price_note}
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
                          {(pkg.features || []).map(feat => (
                            <div key={feat} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '13px', color: '#cbd5e1', lineHeight: 1.5 }}>
                              <span style={{ color: '#F58426', fontWeight: '900' }}>✓</span>
                              <span>{feat}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <a
                        href="https://recdebut.com/program/"
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          textAlign: 'center',
                          padding: '12px',
                          background: pkg.name.includes('Gold') ? '#F58426' : '#334155',
                          color: '#fff',
                          borderRadius: '8px',
                          fontWeight: '800',
                          fontSize: '14px',
                          textDecoration: 'none'
                        }}
                      >
                        Enroll Candidate via RecDebut.com ↗
                      </a>
                    </div>
                  ))}
                </div>

                {/* Statistical Value Callout */}
                <div style={{
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.7) 100%)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '14px',
                  padding: '24px',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                  gap: '20px',
                  textAlign: 'center'
                }}>
                  <div>
                    <div style={{ fontSize: '32px', fontWeight: '900', color: '#F58426' }}>7,000,000</div>
                    <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>High School Athletes in USA Each Year</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '32px', fontWeight: '900', color: '#ef4444' }}>Only 6%</div>
                    <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>Advance to Compete in NCAA College Sports</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '32px', fontWeight: '900', color: '#10b981' }}>2,000+</div>
                    <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>College Coaches in RecDebut Network</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '32px', fontWeight: '900', color: '#60a5fa' }}>34+ Years</div>
                    <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>Helping Athletes Secure Full Scholarships</div>
                  </div>
                </div>
              </div>
            )}

            {/* SECTION 5: OFFICIAL FAQ ACCORDION */}
            {hubSection === 'faq' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#fff' }}>
                  Frequently Asked Questions (Official RecDebut.com Knowledge Base)
                </h3>
                <p style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#94a3b8' }}>
                  Quick reference answers for phone calls with student-athletes, parents, and high school coaches.
                </p>

                {(siteData?.faq || []).map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(30, 41, 59, 0.5)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '12px',
                      padding: '20px'
                    }}
                  >
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '16px', fontWeight: '800', color: '#F58426', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>Q:</span> {item.q}
                    </h4>
                    <p style={{ margin: 0, fontSize: '14px', color: '#cbd5e1', lineHeight: 1.6 }}>
                      {item.a}
                    </p>
                  </div>
                ))}
              </div>
            )}

            {/* SECTION 6: FULL 28-PAGE SITE DIRECTORY */}
            {hubSection === 'directory' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#fff' }}>
                    Complete 28-Page Site Directory (recdebut.com Full Export)
                  </h3>
                  <a
                    href="https://recdebut.com/contact/"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      padding: '8px 16px',
                      background: '#F58426',
                      color: '#fff',
                      borderRadius: '6px',
                      fontWeight: '700',
                      fontSize: '12px',
                      textDecoration: 'none'
                    }}
                  >
                    Contact Portal ↗
                  </a>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '12px' }}>
                  {(siteData?.sports || []).map(s => (
                    <a
                      key={s.url}
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        background: 'rgba(30, 41, 59, 0.4)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        textDecoration: 'none',
                        color: '#fff'
                      }}
                    >
                      <span style={{ fontSize: '13px', fontWeight: '700' }}>{s.icon} {s.name} Registration</span>
                      <span style={{ color: '#F58426', fontSize: '12px' }}>Open ↗</span>
                    </a>
                  ))}
                  {(siteData?.coaches || []).map(c => (
                    <a
                      key={c.url}
                      href={c.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        background: 'rgba(30, 41, 59, 0.4)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        textDecoration: 'none',
                        color: '#fff'
                      }}
                    >
                      <span style={{ fontSize: '13px', fontWeight: '700' }}>{c.avatar} {c.name} Profile</span>
                      <span style={{ color: '#60a5fa', fontSize: '12px' }}>Open ↗</span>
                    </a>
                  ))}
                  {[
                    { label: '🏠 Homepage', url: 'https://recdebut.com/' },
                    { label: 'ℹ️ About Us', url: 'https://recdebut.com/about-us/' },
                    { label: '👔 Coaches Directory', url: 'https://recdebut.com/coachs/' },
                    { label: '📦 Programs & Packages', url: 'https://recdebut.com/program/' },
                    { label: '🎥 Videos & Showcases', url: 'https://recdebut.com/vidoes/' },
                    { label: '❓ FAQ Page', url: 'https://recdebut.com/faq/' },
                    { label: '⭐ Awards & Nominees', url: 'https://recdebut.com/awards/' },
                    { label: '📞 Contact Us', url: 'https://recdebut.com/contact/' },
                    { label: '📋 All Registration Hub', url: 'https://recdebut.com/all-registration/' }
                  ].map(p => (
                    <a
                      key={p.url}
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid rgba(245, 132, 38, 0.2)',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        textDecoration: 'none',
                        color: '#fff'
                      }}
                    >
                      <span style={{ fontSize: '13px', fontWeight: '700' }}>{p.label}</span>
                      <span style={{ color: '#10b981', fontSize: '12px' }}>Open ↗</span>
                    </a>
                  ))}
                </div>
              </div>
            )}

          </div>
        )}
"""

# Insert hub_jsx right before the closing of main ({/* ── FOOTER ── */})
target_marker = "</main>"
assert target_marker in content, "target_marker </main> not found!"
content = content.replace(target_marker, hub_jsx + "\n      " + target_marker, 1)

target.write_text(content, encoding="utf-8")
print("DennisBellPortal.jsx updated successfully!")
