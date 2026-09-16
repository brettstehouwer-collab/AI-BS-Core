import React, { useState, useEffect } from 'react';

// Lightweight Inline Icons with explicit SVG dimensions
const ZapIcon = ({ color = "#58a6ff", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
  </svg>
);

const BriefcaseIcon = ({ color = "#3fb950", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
    <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
  </svg>
);

const ChartIcon = ({ color = "#a371f7", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"></line>
    <line x1="12" y1="20" x2="12" y2="4"></line>
    <line x1="6" y1="20" x2="6" y2="14"></line>
  </svg>
);

const CreditCardIcon = ({ color = "#d29922", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
    <line x1="1" y1="10" x2="23" y2="10"></line>
  </svg>
);

const CheckIcon = ({ color = "#3fb950", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"></polyline>
  </svg>
);

const CopyIcon = ({ color = "#8b949e", size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
  </svg>
);

const DigitalStorefrontTab = ({ backendUrl, currentUser, selectedModel, subView = 'storefront_hub' }) => {
  const [activeApp, setActiveApp] = useState(subView);
  const [credits, setCredits] = useState(500);
  const [userEmail] = useState(currentUser?.email || "brettstehouwer@gmail.com");

  // AI Content State
  const [prompt, setPrompt] = useState('');
  const [contentType, setContentType] = useState('ad_copy');
  const [generatedContent, setGeneratedContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  // ROI Diagnostic State
  const [hoursPerWeek, setHoursPerWeek] = useState(15);
  const [hourlyRate, setHourlyRate] = useState(45);
  const [numEmployees, setNumEmployees] = useState(3);
  const [isUnlocked, setIsUnlocked] = useState(false);

  // Lead Tracker State
  const [leads, setLeads] = useState([
    { id: 1, name: 'Ottawa Valley Plumbing', contact: 'mike@ottawaplumbing.com', status: 'Active Trial', revenue: '$29/mo' },
    { id: 2, name: 'Lakeshore Landscaping', contact: 'sarah@lakeshoreland.com', status: 'Subscribed', revenue: '$29/mo' },
    { id: 3, name: 'Grand Haven Auto Care', contact: 'steve@ghauto.com', status: 'Pending Intake', revenue: '$0/mo' },
  ]);
  const [newLeadName, setNewLeadName] = useState('');
  const [newLeadContact, setNewLeadContact] = useState('');

  useEffect(() => {
    if (subView) setActiveApp(subView);
  }, [subView]);

  useEffect(() => {
    fetch(`${backendUrl}/api/storefront/balance?user_email=${encodeURIComponent(userEmail)}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && typeof data.credits === 'number') {
          setCredits(data.credits);
        }
      })
      .catch(err => console.error("Error fetching credit balance:", err));
  }, [backendUrl, userEmail]);

  const handleGenerate = async () => {
    if (!prompt) return;
    setIsGenerating(true);
    setGeneratedContent('');
    setCopied(false);
    
    try {
      const fullPrompt = `[Format: ${contentType.toUpperCase().replace('_', ' ')}] ${prompt}`;
      const res = await fetch(`${backendUrl}/api/storefront/generate-content`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_email: userEmail, prompt: fullPrompt, model: selectedModel })
      });
      
      const data = await res.json();
      if (data.status === 'success') {
        setGeneratedContent(data.content);
        if (typeof data.credits_remaining === 'number') {
          setCredits(data.credits_remaining);
        }
      } else {
        setGeneratedContent('Error generating content. Please try again.');
      }
    } catch (err) {
      console.error(err);
      setGeneratedContent('Failed to connect to backend.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!generatedContent) return;
    navigator.clipboard.writeText(generatedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleAddLead = (e) => {
    e.preventDefault();
    if (!newLeadName || !newLeadContact) return;
    setLeads([...leads, {
      id: Date.now(),
      name: newLeadName,
      contact: newLeadContact,
      status: 'Active Trial',
      revenue: '$29/mo'
    }]);
    setNewLeadName('');
    setNewLeadContact('');
  };

  // Calculations for ROI Calculator
  const annualHours = hoursPerWeek * 52 * numEmployees;
  const annualCost = annualHours * hourlyRate;
  const estimatedSavings = Math.round(annualCost * 0.65);
  const paybackDays = Math.max(1, Math.round((19 / (estimatedSavings / 365))));

  // --- RENDERERS ---

  const renderHub = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      {/* Top Banner */}
      <div style={{ 
        background: 'linear-gradient(135deg, rgba(88, 166, 255, 0.1) 0%, rgba(163, 113, 247, 0.15) 100%)',
        border: '1px solid rgba(88, 166, 255, 0.3)',
        borderRadius: '16px',
        padding: '24px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.8rem', color: '#f0f6fc', fontWeight: '800' }}>🚀 Stehouwer Digital Resale & SaaS Marketplace</h1>
          <p style={{ margin: '6px 0 0 0', color: '#8b949e', fontSize: '0.95rem' }}>
            High-margin digital products & micro-SaaS applications running on your home PC compute with zero marginal cost.
          </p>
        </div>
        <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '30px', padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ZapIcon color="#d29922" size={22} />
          <span style={{ color: '#f0f6fc', fontWeight: 'bold', fontSize: '1.2rem' }}>{credits} Credits</span>
        </div>
      </div>

      {/* Product Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        
        {/* App 1: AI Content Engine */}
        <div 
          onClick={() => setActiveApp('ai_content_engine')}
          style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '16px',
            padding: '24px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = '#58a6ff'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = '#30363d'}
        >
          <div>
            <div style={{ background: 'rgba(88, 166, 255, 0.15)', width: '48px', height: '48px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyCenter: 'center', marginBottom: '16px' }}>
              <ZapIcon color="#58a6ff" size={26} />
            </div>
            <h3 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.3rem' }}>AI Content Engine</h3>
            <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem', lineHeight: '1.5' }}>
              Credit-based API wrapper for hyper-niche prompts, ad copy, and blog posts. Wraps local GPU Ollama inference with 100% profit margins.
            </p>
          </div>
          <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', color: '#58a6ff', fontWeight: 'bold', fontSize: '0.9rem' }}>
            Open App Workspace →
          </div>
        </div>

        {/* App 2: Auto Lead Tracker */}
        <div 
          onClick={() => setActiveApp('lead_tracker')}
          style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '16px',
            padding: '24px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = '#3fb950'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = '#30363d'}
        >
          <div>
            <div style={{ background: 'rgba(63, 185, 80, 0.15)', width: '48px', height: '48px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyCenter: 'center', marginBottom: '16px' }}>
              <BriefcaseIcon color="#3fb950" size={26} />
            </div>
            <h3 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.3rem' }}>Auto Lead Tracker</h3>
            <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem', lineHeight: '1.5' }}>
              Single-feature B2B Micro-SaaS CRM for local service businesses. Monitored via $29/mo recurring subscriptions.
            </p>
          </div>
          <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', color: '#3fb950', fontWeight: 'bold', fontSize: '0.9rem' }}>
            Open App Workspace →
          </div>
        </div>

        {/* App 3: AI ROI Diagnostic */}
        <div 
          onClick={() => setActiveApp('roi_diagnostic')}
          style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '16px',
            padding: '24px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = '#a371f7'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = '#30363d'}
        >
          <div>
            <div style={{ background: 'rgba(163, 113, 247, 0.15)', width: '48px', height: '48px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyCenter: 'center', marginBottom: '16px' }}>
              <ChartIcon color="#a371f7" size={26} />
            </div>
            <h3 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.3rem' }}>AI ROI Diagnostic</h3>
            <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem', lineHeight: '1.5' }}>
              Interactive calculator & lead magnet. Generates instant labor cost savings estimates with a $19 one-time paywall for PDF export.
            </p>
          </div>
          <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', color: '#a371f7', fontWeight: 'bold', fontSize: '0.9rem' }}>
            Open App Workspace →
          </div>
        </div>

      </div>

      {/* Metrics Row */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px' }}>
        <h3 style={{ margin: '0 0 16px 0', color: '#f0f6fc' }}>📊 Real-Time Resale Performance</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '16px' }}>
          <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '16px', borderRadius: '12px' }}>
            <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Active Customers</span>
            <div style={{ color: '#f0f6fc', fontSize: '1.5rem', fontWeight: 'bold', marginTop: '4px' }}>14</div>
          </div>
          <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '16px', borderRadius: '12px' }}>
            <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Monthly Recurring (MRR)</span>
            <div style={{ color: '#3fb950', fontSize: '1.5rem', fontWeight: 'bold', marginTop: '4px' }}>$406.00</div>
          </div>
          <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '16px', borderRadius: '12px' }}>
            <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Credits Consumed (24h)</span>
            <div style={{ color: '#58a6ff', fontSize: '1.5rem', fontWeight: 'bold', marginTop: '4px' }}>1,420</div>
          </div>
          <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '16px', borderRadius: '12px' }}>
            <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Margin per Request</span>
            <div style={{ color: '#d29922', fontSize: '1.5rem', fontWeight: 'bold', marginTop: '4px' }}>100% (Local)</div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderAiContentEngine = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexWrap: 'wrap', gap: '20px', boxSizing: 'border-box', overflowY: 'auto' }}>
      {/* Left Pane: Controls */}
      <div style={{ flex: '1 1 320px', maxWidth: '100%', display: 'flex', flexDirection: 'column', gap: '16px', background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', boxSizing: 'border-box' }}>
        <h2 style={{ margin: 0, color: '#f0f6fc', fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ZapIcon color="#58a6ff" size={24} /> AI Content Engine
        </h2>
        <p style={{ margin: 0, color: '#8b949e', fontSize: '0.85rem' }}>
          Generates ad copy, blog posts, and prompts. 10 credits deducted per generation.
        </p>

        <div>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '6px' }}>Content Format</label>
          <select 
            value={contentType} 
            onChange={(e) => setContentType(e.target.value)}
            style={{ width: '100%', background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: '8px', padding: '10px', outline: 'none' }}
          >
            <option value="ad_copy">📢 Facebook & Instagram Ad Copy</option>
            <option value="seo_blog">📝 SEO Blog Outline & Draft</option>
            <option value="cold_email">✉️ Cold Outreach Email</option>
            <option value="social_hook">⚡ Viral Social Media Hooks</option>
          </select>
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '6px' }}>Topic or Business Prompt</label>
          <textarea
            style={{ 
              width: '100%', 
              flex: 1, 
              background: '#0d1117', 
              color: '#f0f6fc', 
              border: '1px solid #30363d', 
              borderRadius: '8px', 
              padding: '12px', 
              outline: 'none', 
              resize: 'none',
              fontFamily: 'inherit',
              boxSizing: 'border-box'
            }}
            placeholder="e.g. Write a high-converting Facebook ad for a Ottawa County plumbing service offering 15% off first service call."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGenerating || !prompt || credits < 10}
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '8px',
            border: 'none',
            background: isGenerating || !prompt || credits < 10 ? '#21262d' : '#238636',
            color: isGenerating || !prompt || credits < 10 ? '#8b949e' : '#ffffff',
            fontWeight: 'bold',
            fontSize: '1rem',
            cursor: isGenerating || !prompt || credits < 10 ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          {isGenerating ? '⏳ Processing on GPU...' : credits < 10 ? 'Insufficient Credits' : 'Generate (10 Credits)'}
        </button>

        <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '12px 16px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#8b949e', fontSize: '0.85rem' }}>Balance:</span>
          <span style={{ color: '#58a6ff', fontWeight: 'bold', fontSize: '1.1rem' }}>{credits} Credits</span>
        </div>
      </div>

      {/* Right Pane: Output */}
      <div style={{ flex: '2 1 400px', maxWidth: '100%', minHeight: '400px', background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ background: '#0d1117', borderBottom: '1px solid #30363d', padding: '14px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#f0f6fc', fontWeight: 'bold' }}>Generated Output ({selectedModel})</span>
          {generatedContent && (
            <button 
              onClick={handleCopy}
              style={{ background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}
            >
              {copied ? <CheckIcon color="#3fb950" size={16} /> : <CopyIcon color="#8b949e" size={16} />}
              {copied ? 'Copied!' : 'Copy Result'}
            </button>
          )}
        </div>
        <div style={{ flex: 1, padding: '24px', overflowY: 'auto', color: '#c9d1d9', lineHeight: '1.7', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.95rem' }}>
          {isGenerating ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyCenter: 'center', color: '#58a6ff' }}>
              <div style={{ fontSize: '2rem', marginBottom: '12px' }}>⚙️</div>
              <div>Processing request via local Ollama engine...</div>
            </div>
          ) : generatedContent ? (
            generatedContent
          ) : (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyCenter: 'center', color: '#484f58' }}>
              <ZapIcon color="#30363d" size={48} />
              <p style={{ marginTop: '16px' }}>Enter a prompt on the left to generate content.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderLeadTracker = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px' }}>
        <h2 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <BriefcaseIcon color="#3fb950" size={24} /> Auto Lead Tracker (Micro-SaaS CRM)
        </h2>
        <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem' }}>
          Automated client intake portal for local service businesses. Retainer price: $29/month per account.
        </p>
      </div>

      {/* Add Lead Form */}
      <form onSubmit={handleAddLead} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '20px', display: 'flex', gap: '16px', alignItems: 'center' }}>
        <input 
          type="text" 
          placeholder="Business Name (e.g. Ottawa Valley Heating)" 
          value={newLeadName}
          onChange={(e) => setNewLeadName(e.target.value)}
          style={{ flex: 1, background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: '8px', padding: '10px', outline: 'none' }}
        />
        <input 
          type="email" 
          placeholder="Contact Email" 
          value={newLeadContact}
          onChange={(e) => setNewLeadContact(e.target.value)}
          style={{ flex: 1, background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: '8px', padding: '10px', outline: 'none' }}
        />
        <button type="submit" style={{ background: '#238636', color: '#fff', border: 'none', borderRadius: '8px', padding: '10px 20px', fontWeight: 'bold', cursor: 'pointer' }}>
          + Add Business
        </button>
      </form>

      {/* Leads Table */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', flex: 1 }}>
        <h3 style={{ margin: '0 0 16px 0', color: '#f0f6fc' }}>Active Managed Accounts</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', color: '#c9d1d9', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', fontSize: '0.85rem', textTransform: 'uppercase' }}>
              <th style={{ padding: '12px' }}>Business Name</th>
              <th style={{ padding: '12px' }}>Contact Email</th>
              <th style={{ padding: '12px' }}>Status</th>
              <th style={{ padding: '12px' }}>Subscription Value</th>
            </tr>
          </thead>
          <tbody>
            {leads.map(lead => (
              <tr key={lead.id} style={{ borderBottom: '1px solid #21262d' }}>
                <td style={{ padding: '14px 12px', fontWeight: 'bold', color: '#f0f6fc' }}>{lead.name}</td>
                <td style={{ padding: '14px 12px', color: '#8b949e' }}>{lead.contact}</td>
                <td style={{ padding: '14px 12px' }}>
                  <span style={{ 
                    padding: '4px 10px', 
                    borderRadius: '12px', 
                    fontSize: '0.75rem', 
                    fontWeight: 'bold',
                    background: lead.status === 'Subscribed' ? 'rgba(63, 185, 80, 0.2)' : 'rgba(210, 153, 34, 0.2)',
                    color: lead.status === 'Subscribed' ? '#3fb950' : '#d29922'
                  }}>
                    ● {lead.status}
                  </span>
                </td>
                <td style={{ padding: '14px 12px', color: '#3fb950', fontWeight: 'bold' }}>{lead.revenue}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderRoiDiagnostic = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexWrap: 'wrap', gap: '20px', boxSizing: 'border-box', overflowY: 'auto' }}>
      {/* Left Pane: Interactive Inputs */}
      <div style={{ flex: '1 1 320px', maxWidth: '100%', background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', boxSizing: 'border-box' }}>
        <div>
          <h2 style={{ margin: '0 0 6px 0', color: '#f0f6fc', fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ChartIcon color="#a371f7" size={24} /> AI ROI Diagnostic Calculator
          </h2>
          <p style={{ margin: 0, color: '#8b949e', fontSize: '0.85rem' }}>
            Calculates estimated manual labor cost savings and outputs a paywalled $19 report.
          </p>
        </div>

        <div>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '8px' }}>
            Manual Task Hours / Week per Employee: <span style={{ color: '#a371f7' }}>{hoursPerWeek} hrs</span>
          </label>
          <input 
            type="range" 
            min="5" 
            max="40" 
            value={hoursPerWeek} 
            onChange={(e) => setHoursPerWeek(parseInt(e.target.value, 10))}
            style={{ width: '100%', accentColor: '#a371f7' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '8px' }}>
            Average Hourly Employee Rate ($): <span style={{ color: '#3fb950' }}>${hourlyRate}/hr</span>
          </label>
          <input 
            type="range" 
            min="20" 
            max="150" 
            value={hourlyRate} 
            onChange={(e) => setHourlyRate(parseInt(e.target.value, 10))}
            style={{ width: '100%', accentColor: '#3fb950' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '8px' }}>
            Number of Team Members: <span style={{ color: '#58a6ff' }}>{numEmployees} employees</span>
          </label>
          <input 
            type="range" 
            min="1" 
            max="25" 
            value={numEmployees} 
            onChange={(e) => setNumEmployees(parseInt(e.target.value, 10))}
            style={{ width: '100%', accentColor: '#58a6ff' }}
          />
        </div>

        <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '12px', padding: '16px' }}>
          <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Estimated Annual AI Savings</span>
          <div style={{ color: '#3fb950', fontSize: '2rem', fontWeight: '800', marginTop: '4px' }}>
            ${estimatedSavings.toLocaleString()} / yr
          </div>
        </div>
      </div>

      {/* Right Pane: Report Preview */}
      <div style={{ flex: '2 1 400px', maxWidth: '100%', minHeight: '500px', background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '32px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxSizing: 'border-box' }}>
        <div style={{ overflowX: 'hidden' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', gap: '12px' }}>
            <h3 style={{ margin: 0, color: '#f0f6fc', fontSize: '1.5rem' }}>📋 Customized Executive AI Audit Report</h3>
            <span style={{ background: 'rgba(163, 113, 247, 0.2)', color: '#a371f7', padding: '4px 12px', borderRadius: '12px', fontWeight: 'bold', fontSize: '0.8rem' }}>
              Generated for Stehouwer Client
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '32px' }}>
            <div style={{ background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #21262d' }}>
              <span style={{ color: '#8b949e', fontSize: '0.8rem' }}>Current Annual Waste</span>
              <p style={{ margin: '4px 0 0 0', color: '#ff7b72', fontSize: '1.2rem', fontWeight: 'bold' }}>${annualCost.toLocaleString()}</p>
            </div>
            <div style={{ background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #21262d' }}>
              <span style={{ color: '#8b949e', fontSize: '0.8rem' }}>Estimated Payback Period</span>
              <p style={{ margin: '4px 0 0 0', color: '#58a6ff', fontSize: '1.2rem', fontWeight: 'bold' }}>{paybackDays} Days</p>
            </div>
          </div>

          <div style={{ color: '#c9d1d9', lineHeight: '1.6', fontSize: '0.95rem' }}>
            <p style={{ fontWeight: 'bold', color: '#f0f6fc' }}>Key Optimization Recommendations:</p>
            <ul style={{ paddingLeft: '20px', color: '#8b949e' }}>
              <li>Automate client intake emails and appointment scheduling via AI-BS daemons.</li>
              <li>Deploy specialized document summarizers for invoice processing.</li>
              <li>Integrate local LLM prompt templates to eliminate repetitive team reporting.</li>
            </ul>
          </div>
        </div>

        {/* Paywall Trigger */}
        <div style={{ background: '#0d1117', border: '1px solid #a371f7', borderRadius: '12px', padding: '20px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <div style={{ flex: '1 1 250px' }}>
            <h4 style={{ margin: 0, color: '#f0f6fc', fontSize: '1.1rem' }}>Unlock Full 12-Page Comprehensive PDF Report</h4>
            <p style={{ margin: '4px 0 0 0', color: '#8b949e', fontSize: '0.85rem' }}>Includes step-by-step implementation guide & software architecture blueprint.</p>
          </div>
          <button 
            onClick={() => setIsUnlocked(true)}
            style={{ background: '#a371f7', color: '#fff', border: 'none', borderRadius: '8px', padding: '12px 24px', fontWeight: 'bold', fontSize: '1rem', cursor: 'pointer', flex: '0 0 auto' }}
          >
            {isUnlocked ? '✓ PDF Unlocked' : 'Unlock Report ($19 via PayPal)'}
          </button>
        </div>
      </div>
    </div>
  );

  const renderResaleLedger = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: '0 0 6px 0', color: '#f0f6fc', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <CreditCardIcon color="#d29922" size={24} /> Credit & Revenue Ledger
          </h2>
          <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem' }}>
            Account holder: <strong style={{ color: '#58a6ff' }}>{userEmail}</strong>
          </p>
        </div>
        <div style={{ background: '#0d1117', border: '1px solid #d29922', borderRadius: '12px', padding: '12px 24px', textAlign: 'right' }}>
          <span style={{ color: '#8b949e', fontSize: '0.75rem', textTransform: 'uppercase' }}>Available Balance</span>
          <div style={{ color: '#d29922', fontSize: '1.8rem', fontWeight: '800' }}>{credits} CRD</div>
        </div>
      </div>

      {/* Credit Purchase Packs */}
      <h3 style={{ margin: '0', color: '#f0f6fc' }}>Refill Credit Packages</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', textCenter: 'center', textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.2rem' }}>Starter Pack</h4>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#58a6ff', margin: '12px 0' }}>100 Credits</div>
          <p style={{ color: '#8b949e', fontSize: '0.85rem', marginBottom: '20px' }}>$5.00 One-time ($0.05 / generation)</p>
          <button style={{ width: '100%', background: '#238636', color: '#fff', border: 'none', borderRadius: '8px', padding: '10px', fontWeight: 'bold', cursor: 'pointer' }}>
            Buy 100 Credits ($5)
          </button>
        </div>

        <div style={{ background: '#161b22', border: '2px solid #58a6ff', borderRadius: '16px', padding: '24px', textCenter: 'center', textAlign: 'center', position: 'relative' }}>
          <span style={{ position: 'absolute', top: '-12px', left: '50%', transform: 'translateX(-50%)', background: '#58a6ff', color: '#0d1117', padding: '2px 12px', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 'bold' }}>MOST POPULAR</span>
          <h4 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.2rem' }}>Pro Pack</h4>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#58a6ff', margin: '12px 0' }}>500 Credits</div>
          <p style={{ color: '#8b949e', fontSize: '0.85rem', marginBottom: '20px' }}>$19.00 One-time ($0.038 / generation)</p>
          <button style={{ width: '100%', background: '#58a6ff', color: '#0d1117', border: 'none', borderRadius: '8px', padding: '10px', fontWeight: 'bold', cursor: 'pointer' }}>
            Buy 500 Credits ($19)
          </button>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', textCenter: 'center', textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.2rem' }}>Agency Pack</h4>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#a371f7', margin: '12px 0' }}>2,000 Credits</div>
          <p style={{ color: '#8b949e', fontSize: '0.85rem', marginBottom: '20px' }}>$49.00 One-time ($0.024 / generation)</p>
          <button style={{ width: '100%', background: '#a371f7', color: '#fff', border: 'none', borderRadius: '8px', padding: '10px', fontWeight: 'bold', cursor: 'pointer' }}>
            Buy 2,000 Credits ($49)
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ width: '100%', height: '100%', background: '#0d1117', color: '#c9d1d9', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif', padding: '20px', boxSizing: 'border-box', overflow: 'hidden' }}>
      {(activeApp === 'hub' || activeApp === 'storefront_hub') && renderHub()}
      {(activeApp === 'ai-content' || activeApp === 'ai_content_engine') && renderAiContentEngine()}
      {(activeApp === 'lead-tracker' || activeApp === 'lead_tracker') && renderLeadTracker()}
      {(activeApp === 'roi-diagnostic' || activeApp === 'roi_diagnostic') && renderRoiDiagnostic()}
      {(activeApp === 'resale-ledger' || activeApp === 'resale_ledger') && renderResaleLedger()}
    </div>
  );
};

export default DigitalStorefrontTab;
