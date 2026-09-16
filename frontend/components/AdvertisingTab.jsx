import React, { useState, useEffect, useRef, useCallback } from 'react';

// ─── Canonical lead shape ────────────────────────────────────────────────────
// { id, business_name, contact, url, email, status, value, heuristic_match, date_acquired }
// This matches what BullshitLeadMatrix reads from the backend. Both components
// now share the same store: GET/POST /api/advertising/leads.
// ─────────────────────────────────────────────────────────────────────────────

const LEADS_LS_KEY = 'advertising_leads_v2';   // v2 to avoid conflict with old shape
const BUDGETS_LS_KEY = 'advertising_budgets';
const SAVE_DEBOUNCE_MS = 800;

const AdvertisingTab = ({ backendUrl, selectedModel = 'stehouwer_llm' }) => {
  const [activeSubTab, setActiveSubTab] = useState('leads');
  const [leads, setLeads] = useState([]);
  const [leadsLoaded, setLeadsLoaded] = useState(false);
  const [saveStatus, setSaveStatus] = useState('');       // 'saving' | 'saved' | 'offline'
  const saveTimerRef = useRef(null);
  const isFirstLeadLoad = useRef(true);

  // AI Campaign Generator
  const [businessName, setBusinessName] = useState('');
  const [campaignGoal, setCampaignGoal] = useState('');
  const [generatedCopy, setGeneratedCopy] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [genError, setGenError] = useState('');

  // Platform Post Generator
  const [postBizName, setPostBizName] = useState('Stehouwer Advertising');
  const [postIndustry, setPostIndustry] = useState('Marketing / Advertising Agency');
  const [postCounty, setPostCounty] = useState('Ottawa County');
  const [postPromo, setPostPromo] = useState('We help West Michigan local businesses dominate Google, Facebook, Instagram, and TikTok with AI-powered ad campaigns. First month FREE for new clients — call us today and get a custom strategy built for your neighborhood.');
  const [generatedPosts, setGeneratedPosts] = useState(null);
  const [isGeneratingPosts, setIsGeneratingPosts] = useState(false);
  const [copiedPlatform, setCopiedPlatform] = useState('');


  // Budget Tracker
  const [budgets, setBudgets] = useState(() => {
    const saved = localStorage.getItem(BUDGETS_LS_KEY);
    return saved ? JSON.parse(saved) : [{ id: 1, event: 'Summer SEO Push', spent: 1500, roi: 4500 }];
  });

  // ── Load leads from backend on mount, fall back to localStorage ─────────────
  const fetchLeads = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/advertising/leads`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.status === 'success') {
        const fetched = data.leads;
        setLeads(fetched);
        localStorage.setItem(LEADS_LS_KEY, JSON.stringify(fetched));   // warm the fallback
        setLeadsLoaded(true);
        return;
      }
    } catch (_) {
      // Backend unreachable — use localStorage fallback
    }
    const cached = localStorage.getItem(LEADS_LS_KEY);
    setLeads(cached ? JSON.parse(cached) : []);
    setLeadsLoaded(true);
    setSaveStatus('offline');
  }, [backendUrl]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  // ── Debounced save to backend (skip the very first load-triggered effect) ───
  useEffect(() => {
    if (!leadsLoaded) return;
    if (isFirstLeadLoad.current) { isFirstLeadLoad.current = false; return; }

    clearTimeout(saveTimerRef.current);
    setSaveStatus('saving');
    saveTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/advertising/leads`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(leads),
        });
        if (!res.ok) throw new Error();
        localStorage.setItem(LEADS_LS_KEY, JSON.stringify(leads));
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus(''), 2000);
      } catch (_) {
        localStorage.setItem(LEADS_LS_KEY, JSON.stringify(leads));
        setSaveStatus('offline');
      }
    }, SAVE_DEBOUNCE_MS);

    return () => clearTimeout(saveTimerRef.current);
  }, [leads, leadsLoaded, backendUrl]);

  // Budgets stay localStorage-only (no backend endpoint yet)
  useEffect(() => {
    localStorage.setItem(BUDGETS_LS_KEY, JSON.stringify(budgets));
  }, [budgets]);

  // ── Lead CRUD ────────────────────────────────────────────────────────────────
  const addLead = () => {
    const newLead = {
      id: `manual-${Date.now()}`,
      business_name: 'New Business',
      contact: '',
      url: '',
      email: '',
      status: 'New',
      value: '$0',
      heuristic_match: 'Manual Entry',
      date_acquired: new Date().toISOString(),
    };
    setLeads(prev => [newLead, ...prev]);
  };

  const updateLead = (id, field, value) =>
    setLeads(prev => prev.map(l => l.id === id ? { ...l, [field]: value } : l));

  const deleteLead = (id) =>
    setLeads(prev => prev.filter(l => l.id !== id));

  // ── Campaign generator ───────────────────────────────────────────────────────
  const generateCampaign = async () => {
    if (!businessName.trim()) { setGenError('Enter a business name first.'); return; }
    setIsGenerating(true);
    setGenError('');
    setGeneratedCopy('Generating...');
    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: `Write a high-converting Facebook ad and 5 Google SEO keywords for a business named "${businessName}" whose goal is "${campaignGoal}". Keep it highly professional and punchy.` }],
          use_rag: false,
          use_web_search: false,
          model: 'stehouwer_llm',
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const content = (typeof data.message === 'string' ? data.message : data.message?.content) || data.response || data.choices?.[0]?.message?.content || (typeof data === 'string' ? data : '');
      setGeneratedCopy(content || 'No response received. Check backend logs.');
    } catch (err) {
      setGenError('Backend unreachable. Ensure uvicorn and Ollama are running.');
      setGeneratedCopy('');
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Platform Post Generator ──────────────────────────────────────────────────
  const handleGeneratePlatformPosts = async () => {
    setIsGeneratingPosts(true);
    setGeneratedPosts(null);
    const systemPrompt = `You are an expert platform-native content strategist and local SEO specialist for West Michigan businesses. Your posts must be engineered to be indexed and ranked FAST by each platform's algorithm — not generic, not templated, algorithmically precise.

Business: "${postBizName}" | Industry: "${postIndustry}" | County: "${postCounty}"
Promotion: "${postPromo}"

CRITICAL ALGORITHM RULES PER PLATFORM (follow exactly):

ALL PLATFORMS: You MUST include the specific Promotion/Offer provided above in every single post naturally. Do not ignore the promo.

GOOGLE: Front-load geo-intent keywords (people search "near me" or "[city] [service]"). NAP-consistent phrasing. schema_title must be under 60 chars and include the county name. meta_description must be under 155 chars, include a local intent phrase, and end with a micro-CTA. local_keywords must be long-tail geo-modified phrases someone in ${postCounty} would actually type (not brand names).

FACEBOOK: The entire headline + first sentence of body must be under 90 characters (this is what shows before "See More" — the algo rewards early engagement on visible text). Body is 2-3 sentences, conversational, no jargon. CTA drives a comment or message (comments boost reach 3x). Include 3-5 highly targeted, algorithmically optimized hashtags (mix of local, industry, and niche tags) to maximize organic outreach.

INSTAGRAM: caption_hook must be under 125 characters (this is the preview before "more" tap — the algo scores retention here). Body is 2-4 lines max. hashtags: use EXACTLY 3-5 highly targeted hashtags (2024 Instagram algo penalizes hashtag spam; 3-5 niche tags outperform 20+ generic ones). Mix one local tag, one industry tag, one niche tag.

TIKTOK: hook_text is the FIRST 1-3 SECONDS spoken aloud — TikTok transcribes audio and indexes it for search, so include the primary keyword in the spoken hook. script is a 30-45 second natural spoken script (TikTok rewards watch time and loop completion). caption_keywords: write 3-5 words as a search-optimized caption — TikTok's search engine indexes captions exactly like Google, so use phrases people search for (e.g. "Ottawa County marketing tips").

TWITTER / X: tweet must be under 220 characters. Zero external links (the X algorithm heavily suppresses tweets with external links). Use reply-bait wording to drive 30-min engagement velocity. card_title under 50 chars, card_description under 100 chars.

PINTEREST: pin_title must be keyword front-loaded. pin_description 2-3 sentences, search-intent driven, zero fluff.

YELP: Category-exact language. Business description 100-150 words. Mention the county name 2-3x naturally. Highlight special offer in Check-In Offer format.

Respond ONLY with a single, raw, valid JSON object with NO markdown, NO code block ticks, NO intro text, matching this exact shape:
{
  "_thought_process": "Verify promo inclusion, Facebook <90 chars, Instagram exactly 3-5 tags, Yelp 100+ words...",
  "google": { "schema_title": "...", "meta_description": "...", "local_keywords": ["...", "...", "..."] },
  "facebook": { "headline": "...", "body": "...", "cta": "...", "hashtags": "..." },
  "instagram": { "caption_hook": "...", "body": "...", "hashtags": "..." },
  "tiktok": { "hook_text": "...", "script": "...", "caption_keywords": "..." },
  "twitter": { "tweet": "..." , "card_title": "...", "card_description": "..." },
  "pinterest": { "pin_title": "...", "pin_description": "..." },
  "yelp": { "business_description": "...", "category_tags": ["...", "..."], "special_offer": "..." }
}`;

    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: systemPrompt }],
          use_rag: false,
          use_web_search: false,
          model: selectedModel || 'stehouwer_llm',
          format: 'json'
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const raw = data.message?.content || data.response || data.content || data.choices?.[0]?.message?.content || '{}';
      const jsonMatch = raw.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try { setGeneratedPosts(JSON.parse(jsonMatch[0])); }
        catch { setGeneratedPosts({ error: 'AI returned malformed JSON — try again.' }); }
      } else {
        setGeneratedPosts({ error: 'No JSON in AI response — try again.' });
      }
    } catch (e) {
      setGeneratedPosts({ error: `Backend error: ${e.message}` });
    }
    setIsGeneratingPosts(false);
  };


  const handleCopyPost = (key, text) => {
    navigator.clipboard.writeText(text);
    setCopiedPlatform(key);
    setTimeout(() => setCopiedPlatform(''), 2000);
  };

  const statusColor = saveStatus === 'saved' ? '#10b981'
    : saveStatus === 'offline' ? '#ef4444'
    : saveStatus === 'saving' ? '#f59e0b'
    : 'transparent';

  const statusLabel = saveStatus === 'saved' ? '✓ Saved'
    : saveStatus === 'offline' ? '⚠ Offline (local only)'
    : saveStatus === 'saving' ? '↑ Saving...'
    : '';

  return (
    <div className="advertising-workspace" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div className="adv-header glass-panel" style={{ flexShrink: 0 }}>
        <div className="adv-title-area">
          <h3>📈 Stehouwer Advertising Dashboard</h3>
          <p className="subtitle">
            Manage local business leads, generate ad copy, and track ROI.
            {statusLabel && (
              <span style={{ marginLeft: '16px', color: statusColor, fontSize: '0.8em', fontWeight: 600 }}>
                {statusLabel}
              </span>
            )}
          </p>
        </div>
        <div className="adv-tabs">
          <button className={`adv-tab-btn ${activeSubTab === 'leads' ? 'active' : ''}`} onClick={() => setActiveSubTab('leads')}>🏢 Lead Manager</button>
          <button className={`adv-tab-btn ${activeSubTab === 'campaign' ? 'active' : ''}`} onClick={() => setActiveSubTab('campaign')}>🤖 AI Campaign Generator</button>
          <button className={`adv-tab-btn ${activeSubTab === 'posts' ? 'active' : ''}`} onClick={() => setActiveSubTab('posts')} style={{ background: activeSubTab === 'posts' ? 'linear-gradient(135deg, #7c3aed, #4f46e5)' : '' }}>🌐 Platform Post Generator</button>
          <button className={`adv-tab-btn ${activeSubTab === 'budget' ? 'active' : ''}`} onClick={() => setActiveSubTab('budget')}>💰 Budget Tracker</button>
        </div>
      </div>

      <div className="adv-content-area" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '20px 0 0 0' }}>


        {/* ── LEADS TAB ─────────────────────────────────────────────────────── */}
        {activeSubTab === 'leads' && (
          <div className="adv-panel glass-panel">
            <div className="panel-header">
              <h4>Secure Leads Vault <span style={{ fontSize: '0.75em', fontWeight: 400, color: '#888' }}>(synced with Lead Matrix)</span></h4>
              <button className="action-btn" onClick={addLead}>+ Add Lead</button>
            </div>
            <div className="table-container">
              {!leadsLoaded ? (
                <p className="empty-state">Loading leads from backend...</p>
              ) : (
                <table className="adv-table">
                  <thead>
                    <tr>
                      <th>Business Name</th>
                      <th>Contact</th>
                      <th>Email</th>
                      <th>Website</th>
                      <th>Status</th>
                      <th>Est. Value</th>
                      <th>Heuristic</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map(lead => (
                      <tr key={lead.id}>
                        <td><input type="text" aria-label="Business Name" placeholder="Business Name" value={lead.business_name || ''} onChange={e => updateLead(lead.id, 'business_name', e.target.value)} /></td>
                        <td><input type="text" aria-label="Contact Name" placeholder="Contact Name" value={lead.contact || ''} onChange={e => updateLead(lead.id, 'contact', e.target.value)} /></td>
                        <td><input type="email" aria-label="Contact Email" placeholder="Contact Email" value={lead.email || ''} onChange={e => updateLead(lead.id, 'email', e.target.value)} /></td>
                        <td><input type="text" aria-label="Website Domain Vector" placeholder="Website URL" value={lead.url || ''} onChange={e => updateLead(lead.id, 'url', e.target.value)} /></td>
                        <td>
                          <select aria-label="CRM Lead Status" value={lead.status || 'New'} onChange={e => updateLead(lead.id, 'status', e.target.value)}>
                            <option value="New">New</option>
                            <option value="Contacted">Contacted</option>
                            <option value="In Negotiations">In Negotiations</option>
                            <option value="Closed (Won)">Closed (Won)</option>
                            <option value="Closed (Lost)">Closed (Lost)</option>
                          </select>
                        </td>
                        <td><input type="text" aria-label="Estimated Value" placeholder="$0" value={lead.value || '$0'} onChange={e => updateLead(lead.id, 'value', e.target.value)} /></td>
                        <td><input type="text" aria-label="Heuristic Match Profile" placeholder="Heuristic" value={lead.heuristic_match || ''} onChange={e => updateLead(lead.id, 'heuristic_match', e.target.value)} /></td>
                        <td><button className="del-btn" aria-label={`Delete Lead ${lead.business_name || lead.id}`} onClick={() => deleteLead(lead.id)}>🗑️</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {leadsLoaded && leads.length === 0 && (
                <p className="empty-state">No leads found. Click "+ Add Lead" or trigger a sweep in the Lead Matrix tab.</p>
              )}
            </div>
          </div>
        )}

        {/* ── CAMPAIGN TAB ──────────────────────────────────────────────────── */}
        {activeSubTab === 'campaign' && (
          <div className="adv-grid-2">
            <div className="adv-panel glass-panel">
              <h4>AI Copywriter Setup</h4>
              <p className="field-desc">Powered by Local Llama 3 Engine</p>

              <div className="form-group">
                <label>Business Name</label>
                <input type="text" placeholder="e.g. Grandville Plumbing" value={businessName} onChange={e => setBusinessName(e.target.value)} />
              </div>

              <div className="form-group">
                <label>Campaign Goal / Key Selling Point</label>
                <textarea rows="4" placeholder="e.g. We offer 24/7 emergency pipe repair with 0 callout fees." value={campaignGoal} onChange={e => setCampaignGoal(e.target.value)} />
              </div>

              {genError && <p style={{ color: '#ef4444', fontSize: '0.85em', margin: '8px 0' }}>{genError}</p>}

              <button className="action-btn full-width" onClick={generateCampaign} disabled={isGenerating || !businessName.trim()}>
                {isGenerating ? 'Generating Copy...' : '⚡ Generate Advertising Copy'}
              </button>
            </div>

            <div className="adv-panel glass-panel">
              <h4>Generated Ad Copy &amp; SEO</h4>
              <div className="generated-output-box">
                {generatedCopy ? (
                  <pre>{generatedCopy}</pre>
                ) : (
                  <p className="empty-state">Your generated Facebook Ads and SEO keywords will appear here.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── BUDGET TAB ────────────────────────────────────────────────────── */}
        {activeSubTab === 'budget' && (
          <div className="adv-panel glass-panel">
            <div className="panel-header">
              <h4>Marketing Event Budgets</h4>
              <button className="action-btn" onClick={() => setBudgets(prev => [...prev, { id: Date.now(), event: 'New Event', spent: 0, roi: 0 }])}>
                + Add Event
              </button>
            </div>

            <div className="budget-cards">
              {budgets.map(budget => (
                <div key={budget.id} className="budget-card">
                  <input className="budget-title-input" type="text" value={budget.event}
                    onChange={e => setBudgets(prev => prev.map(b => b.id === budget.id ? { ...b, event: e.target.value } : b))} />

                  <div className="budget-metrics">
                    <div className="metric">
                      <span>Amount Spent</span>
                      <input type="number" value={budget.spent}
                        onChange={e => setBudgets(prev => prev.map(b => b.id === budget.id ? { ...b, spent: parseFloat(e.target.value) || 0 } : b))} />
                    </div>
                    <div className="metric">
                      <span>Estimated ROI</span>
                      <input type="number" value={budget.roi}
                        onChange={e => setBudgets(prev => prev.map(b => b.id === budget.id ? { ...b, roi: parseFloat(e.target.value) || 0 } : b))} />
                    </div>
                  </div>

                  <div className="roi-indicator" style={{ color: budget.roi >= budget.spent ? '#10b981' : '#ef4444' }}>
                    {budget.roi >= budget.spent ? '▲ Profitable' : '▼ Loss'}
                    <span style={{ marginLeft: '10px' }}>${(budget.roi - budget.spent).toFixed(2)}</span>
                  </div>

                  <button className="del-btn-card" onClick={() => setBudgets(prev => prev.filter(b => b.id !== budget.id))}>Remove</button>
                </div>
              ))}
              {budgets.length === 0 && <p className="empty-state">No budgets tracked yet.</p>}
            </div>
          </div>
        )}

        {/* ── PLATFORM POST GENERATOR TAB ──────────────────────────────────── */}
        {activeSubTab === 'posts' && (
          <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20, height: '100%', minHeight: 0 }}>
            {/* LEFT: Form */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: 20, background: 'rgba(0,0,0,0.35)', borderRadius: 16, border: '1px solid rgba(124,58,237,0.3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, #7c3aed, #4f46e5)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>🌐</div>
                <div>
                  <h4 style={{ margin: 0, color: '#00f0ff' }}>Platform Post Generator</h4>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8' }}>One promo → 7 platforms</p>
                </div>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontSize: '0.82rem', color: '#94a3b8' }}>Business Name</label>
                <input type="text" value={postBizName} onChange={e => setPostBizName(e.target.value)} placeholder="e.g. Holland Hardware & Supply" style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: 'white', outline: 'none' }} />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontSize: '0.82rem', color: '#94a3b8' }}>Industry</label>
                <select value={postIndustry} onChange={e => setPostIndustry(e.target.value)} style={{ width: '100%', padding: '9px 12px', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: 'white', outline: 'none' }}>
                  <option>Local Business</option><option>Restaurant / Food</option><option>Auto Repair</option><option>Real Estate</option><option>Health & Wellness</option><option>Retail / Shop</option><option>Home Services</option><option>Legal / Financial</option><option>Beauty & Salon</option><option>Event Venue</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontSize: '0.82rem', color: '#94a3b8' }}>Target County</label>
                <select value={postCounty} onChange={e => setPostCounty(e.target.value)} style={{ width: '100%', padding: '9px 12px', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: 'white', outline: 'none' }}>
                  <option>Ottawa County</option><option>Kent County</option><option>Muskegon County</option><option>Allegan County</option><option>Kalamazoo County</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontSize: '0.82rem', color: '#94a3b8' }}>Promotion / Offer</label>
                <textarea value={postPromo} onChange={e => setPostPromo(e.target.value)} placeholder="e.g. First month FREE for new clients. AI-powered campaigns built for your neighborhood." rows={5} style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: 'white', outline: 'none', resize: 'vertical' }} />
              </div>
              <button onClick={handleGeneratePlatformPosts} disabled={isGeneratingPosts || !postBizName.trim() || !postPromo.trim()} style={{ marginTop: 'auto', padding: '13px', background: isGeneratingPosts ? 'rgba(124,58,237,0.3)' : 'linear-gradient(135deg, #7c3aed, #4f46e5)', border: 'none', borderRadius: 10, color: 'white', fontWeight: 700, cursor: isGeneratingPosts ? 'not-allowed' : 'pointer', fontSize: '1rem' }}>
                {isGeneratingPosts ? '⚙️ Generating...' : '⚡ Generate All 7 Platforms'}
              </button>
            </div>

            {/* RIGHT: 2-column card grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, alignContent: 'start', overflowY: 'auto' }}>
              {[
                {
                  key: 'google',
                  label: 'Google Business Profile',
                  url: 'https://business.google.com/',
                  icon: '🔍',
                  color: '#4285F4',
                  algoTip: 'Geo-intent keywords · NAP-consistent · <60 char title · <155 char meta',
                  content: g => {
                    const title = g.schema_title || g.title || '';
                    const desc = g.meta_description || g.description || '';
                    const kws = (g.local_keywords || g.keywords || []).join(' · ');
                    return [title, desc, kws ? `📍 ${kws}` : ''].filter(Boolean).join('\n\n');
                  }
                },

                {
                  key: 'facebook',
                  label: 'Facebook',
                  url: 'https://business.facebook.com/',
                  icon: '📘',
                  color: '#1877F2',
                  algoTip: '90-char hook visible · 3-5 targeted hashtags · comment-bait CTA for 3x reach',
                  content: f => [f.headline, f.body || f.text, f.cta, f.hashtags].filter(Boolean).join('\n\n')
                },
                {
                  key: 'instagram',
                  label: 'Instagram',
                  url: 'https://business.instagram.com/',
                  icon: '📸',
                  color: '#E1306C',
                  algoTip: '125-char preview · 3-5 niche hashtags (2024 algo) · hook drives retention',
                  content: i => [
                    i.caption_hook || i.hook,
                    i.body || i.caption,
                    i.hashtags
                  ].filter(Boolean).join('\n\n')
                },
                {
                  key: 'tiktok',
                  label: 'TikTok',
                  url: 'https://www.tiktok.com/business/en',
                  icon: '🎵',
                  color: '#69C9D0',
                  algoTip: 'Spoken keywords indexed by audio · search-phrase caption · loop-completion hook',
                  content: t => [
                    t.hook_text || t.hook,
                    t.script,
                    t.caption_keywords || t.caption
                  ].filter(Boolean).join('\n\n')
                },
                {
                  key: 'twitter',
                  label: 'X / Twitter',
                  url: 'https://ads.x.com/',
                  icon: '𝕏',
                  color: '#e7e9ea',
                  algoTip: '<220 chars · no external links · reply-bait for 30-min velocity',
                  content: t => t.tweet || t.text || ''
                },
                {
                  key: 'pinterest',
                  label: 'Pinterest',
                  url: 'https://business.pinterest.com/',
                  icon: '📌',
                  color: '#E60023',
                  algoTip: 'Keyword front-loaded in title · used 2-3x in description · search-intent driven',
                  content: p => [p.pin_title || p.title, p.pin_description || p.description].filter(Boolean).join('\n\n')
                },
                {
                  key: 'yelp',
                  label: 'Yelp',
                  url: 'https://biz.yelp.com/',
                  icon: '⭐',
                  color: '#d32323',
                  algoTip: 'Category-exact language · county mentioned 2-3x · Check-In Offer format',
                  content: y => {
                    const desc = y.business_description || y.description || '';
                    const offer = y.special_offer || y.offer || '';
                    return [desc, offer ? `🎁 ${offer}` : ''].filter(Boolean).join('\n\n');
                  }
                },
              ].map(({ key, label, url, icon, color, algoTip, content }) => {

                const data = generatedPosts?.[key];
                const text = data && !generatedPosts?.error ? content(data) : '';
                return (
                  <div key={key} style={{ padding: 16, background: 'rgba(0,0,0,0.35)', borderRadius: 14, border: `1px solid ${data ? color + '55' : 'rgba(255,255,255,0.06)'}`, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <span style={{ fontWeight: 700, color: data ? color : '#555', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {icon} <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none', transition: 'opacity 0.2s' }} onMouseOver={e => e.currentTarget.style.opacity = '0.8'} onMouseOut={e => e.currentTarget.style.opacity = '1'}>{label}</a>
                        </span>
                        <div style={{ fontSize: '0.68rem', color: '#4a6070', marginTop: 3, lineHeight: 1.4 }}>⚡ {algoTip}</div>
                      </div>
                      {data && !generatedPosts?.error && (
                        <button onClick={() => handleCopyPost(key, text)} style={{ flexShrink: 0, marginLeft: 8, padding: '4px 10px', background: copiedPlatform === key ? '#10b981' : `${color}22`, border: `1px solid ${color}66`, borderRadius: 6, color: copiedPlatform === key ? 'white' : color, cursor: 'pointer', fontSize: '0.73rem', fontWeight: 600 }}>
                          {copiedPlatform === key ? '✅ Copied!' : '📋 Copy'}
                        </button>
                      )}
                    </div>
                    {!generatedPosts && !isGeneratingPosts && <p style={{ margin: 0, fontSize: '0.78rem', color: '#444' }}>Awaiting generation...</p>}
                    {isGeneratingPosts && <p style={{ margin: 0, fontSize: '0.78rem', color: '#7c3aed', animation: 'pulse 1s infinite' }}>Generating...</p>}
                    {generatedPosts?.error && key === 'google' && <p style={{ margin: 0, fontSize: '0.78rem', color: '#ef4444' }}>{generatedPosts.error}</p>}
                    {text && <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.6, flex: 1 }}>{text}</pre>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default AdvertisingTab;

