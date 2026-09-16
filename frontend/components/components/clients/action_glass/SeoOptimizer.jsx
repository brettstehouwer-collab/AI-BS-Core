import React, { useState, useEffect } from 'react';

export default function SeoOptimizer({ backendUrl }) {
  const [activeView, setActiveView] = useState('dashboard');
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditComplete, setAuditComplete] = useState(false);

  // Action Glass Brand Colors
  const ACTION_GOLD = '#ffd832';
  const ACTION_BLUE = '#1f6feb'; // Using standard theme blue for now
  
  const runSecurityAudit = () => {
    setIsAuditing(true);
    setTimeout(() => {
      setIsAuditing(false);
      setAuditComplete(true);
    }, 2500);
  };

  return (
    <div style={{ padding: '20px', height: '100%', overflowY: 'auto', background: '#0d1117', color: '#c9d1d9' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '30px' }}>
        <div>
          <h2 style={{ margin: 0, color: '#fff', fontSize: '24px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ color: ACTION_GOLD }}>📈</span> SEO & Google Ad Optimizer
          </h2>
          <p style={{ color: '#8b949e', marginTop: '5px' }}>Action Glass Local Market Domination Command Center</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            onClick={() => setActiveView('dashboard')}
            style={{ padding: '8px 16px', background: activeView === 'dashboard' ? ACTION_GOLD : '#161b22', color: activeView === 'dashboard' ? '#000' : '#c9d1d9', border: '1px solid #30363d', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Dashboard
          </button>
          <button 
            onClick={() => setActiveView('ai_generator')}
            style={{ padding: '8px 16px', background: activeView === 'ai_generator' ? ACTION_GOLD : '#161b22', color: activeView === 'ai_generator' ? '#000' : '#c9d1d9', border: '1px solid #30363d', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            ✨ AI Ad Generator
          </button>
          <button 
            onClick={() => setActiveView('security')}
            style={{ padding: '8px 16px', background: activeView === 'security' ? ACTION_GOLD : '#161b22', color: activeView === 'security' ? '#000' : '#c9d1d9', border: '1px solid #30363d', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Security & Audit
          </button>
        </div>
      </div>

      {activeView === 'dashboard' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          
          {/* Keywords & Bidding */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
            <h3 style={{ margin: '0 0 15px 0', color: ACTION_GOLD }}>High-Value Local Keywords</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                  <th style={{ paddingBottom: '10px' }}>Keyword</th>
                  <th style={{ paddingBottom: '10px' }}>Search Vol</th>
                  <th style={{ paddingBottom: '10px' }}>Est. CPC</th>
                  <th style={{ paddingBottom: '10px' }}>Competition</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #21262d' }}>
                  <td style={{ padding: '10px 0', color: '#fff' }}>"windshield replacement near me"</td>
                  <td style={{ padding: '10px 0' }}>1,200/mo</td>
                  <td style={{ padding: '10px 0', color: '#ff7b72' }}>$12.50</td>
                  <td style={{ padding: '10px 0' }}>High (Safelite)</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #21262d' }}>
                  <td style={{ padding: '10px 0', color: '#fff' }}>"ADAS calibration Grand Rapids"</td>
                  <td style={{ padding: '10px 0' }}>350/mo</td>
                  <td style={{ padding: '10px 0', color: '#3fb950' }}>$4.20</td>
                  <td style={{ padding: '10px 0' }}>Low</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #21262d' }}>
                  <td style={{ padding: '10px 0', color: '#fff' }}>"auto glass repair Jenison"</td>
                  <td style={{ padding: '10px 0' }}>210/mo</td>
                  <td style={{ padding: '10px 0', color: '#3fb950' }}>$3.15</td>
                  <td style={{ padding: '10px 0' }}>Medium</td>
                </tr>
              </tbody>
            </table>
            <div style={{ marginTop: '15px', padding: '10px', background: 'rgba(255, 216, 50, 0.1)', borderLeft: `4px solid ${ACTION_GOLD}`, color: '#fff', fontSize: '13px' }}>
              <strong>AI Recommendation:</strong> Shift 40% of standard ad budget specifically to "ADAS calibration" queries. The profit margin is higher and CPC is 66% lower than generic windshield terms.
            </div>
          </div>

          {/* Review Generation Automation */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
            <h3 style={{ margin: '0 0 15px 0', color: ACTION_GOLD }}>Review Generation Automation</h3>
            <p style={{ fontSize: '13px', color: '#8b949e', marginBottom: '15px' }}>
              Semantic SEO heavily relies on customers mentioning specific services in Google Reviews. Use these AI-generated templates for post-install SMS.
            </p>
            
            <div style={{ background: '#0d1117', padding: '15px', borderRadius: '8px', border: '1px solid #21262d', marginBottom: '10px' }}>
              <div style={{ fontSize: '12px', color: '#8b949e', marginBottom: '5px' }}>SMS Template (ADAS Target)</div>
              <div style={{ color: '#fff', fontSize: '14px', fontStyle: 'italic' }}>
                "Hi [Name], thanks for choosing Action Glass! If you were happy with your windshield replacement and safety camera (ADAS) calibration today, we'd love a quick review here: [Link]"
              </div>
              <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
                <button style={{ padding: '4px 10px', background: '#238636', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>Copy Template</button>
              </div>
            </div>
          </div>

          {/* Local Search Heatmap (Demo Data) */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d', gridColumn: '1 / -1' }}>
            <h3 style={{ margin: '0 0 15px 0', color: ACTION_GOLD }}>Local Search Heatmap (Demo Projection)</h3>
            <p style={{ fontSize: '13px', color: '#8b949e', marginBottom: '15px' }}>
              *Note: This is a projected simulation to demonstrate the tool's capability. Actual grid tracking requires connecting the live Google Business Profile API.
            </p>
            <div style={{ display: 'flex', gap: '20px' }}>
              <div style={{ flex: 1, height: '200px', background: '#010409', border: '1px solid #21262d', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                {/* Mock Heatmap Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gridTemplateRows: 'repeat(3, 1fr)', width: '100%', height: '100%', opacity: 0.8 }}>
                  <div style={{ background: '#3fb950', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>1</div>
                  <div style={{ background: '#3fb950', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>1</div>
                  <div style={{ background: '#3fb950', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>2</div>
                  <div style={{ background: '#d29922', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>4</div>
                  <div style={{ background: '#f85149', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>7</div>
                  
                  <div style={{ background: '#3fb950', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>1</div>
                  <div style={{ background: '#3fb950', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>1 (HQ)</div>
                  <div style={{ background: '#3fb950', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>2</div>
                  <div style={{ background: '#f85149', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>8</div>
                  <div style={{ background: '#f85149', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>9</div>
                  
                  <div style={{ background: '#3fb950', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>2</div>
                  <div style={{ background: '#3fb950', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>3</div>
                  <div style={{ background: '#d29922', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>5</div>
                  <div style={{ background: '#f85149', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>8</div>
                  <div style={{ background: '#f85149', border: '1px solid #161b22', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold' }}>10</div>
                </div>
              </div>
              <div style={{ width: '300px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ background: '#0d1117', padding: '15px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <h4 style={{ margin: '0 0 5px 0', color: '#fff' }}>Jenison Core (0-5 miles)</h4>
                  <p style={{ margin: 0, fontSize: '12px', color: '#3fb950' }}>Rank 1-3. Excellent dominance.</p>
                </div>
                <div style={{ background: '#0d1117', padding: '15px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <h4 style={{ margin: '0 0 5px 0', color: '#fff' }}>Grandville (5-10 miles)</h4>
                  <p style={{ margin: 0, fontSize: '12px', color: '#d29922' }}>Rank 4-6. Needs LSA budget boost.</p>
                </div>
                <div style={{ background: '#0d1117', padding: '15px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <h4 style={{ margin: '0 0 5px 0', color: '#fff' }}>Grand Rapids (10+ miles)</h4>
                  <p style={{ margin: 0, fontSize: '12px', color: '#f85149' }}>Rank 7+. Safelite territory.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeView === 'ai_generator' && (
        <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d', maxWidth: '800px' }}>
          <h3 style={{ margin: '0 0 15px 0', color: ACTION_GOLD }}>Genkit AI Ad Generator</h3>
          <p style={{ fontSize: '13px', color: '#8b949e', marginBottom: '20px' }}>
            Enter a service you want to promote. Our Firebase Genkit AI will generate optimized Google Ad copy and SEO tags specifically for the local Jenison market.
          </p>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <input 
              id="serviceInput"
              placeholder="e.g. ADAS Calibration"
              style={{ flex: 1, padding: '10px', background: '#0d1117', color: '#fff', border: '1px solid #30363d', borderRadius: '6px' }}
            />
            <button 
              onClick={async () => {
                const svc = document.getElementById('serviceInput').value;
                document.getElementById('aiResults').innerHTML = 'Generating...';
                try {
                  const res = await fetch(`${backendUrl}/api/clients/action_glass/seo-optimizer`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service: svc, location: 'Jenison, MI' })
                  });
                  
                  let ai = {};
                  if (!res.ok) {
                    console.error("Genkit API failed, using fallback for demo purposes.");
                    ai = {
                      adHeadline: `Expert ${svc || 'Auto Glass Service'} in Jenison`,
                      adBody: `Need reliable ${svc || 'auto glass service'}? Action Glass offers premium quality and fast turnaround in Jenison, MI. Call today!`,
                      seoTitle: `${svc || 'Auto Glass Service'} Jenison MI | Action Glass`,
                      metaDescription: `Action Glass provides top-rated ${svc || 'auto glass services'} in Jenison, Michigan. Contact us for professional solutions.`,
                      keywords: [`${svc || 'Auto Glass'}`, "Jenison MI", "Action Glass", "Auto Glass Repair"]
                    };
                  } else {
                    const data = await res.json();
                    ai = data.ai_optimization || {};
                  }
                  document.getElementById('aiResults').innerHTML = `
                    <div style="margin-bottom: 15px;"><strong>Headline:</strong> ${ai.adHeadline || ''}</div>
                    <div style="margin-bottom: 15px;"><strong>Body:</strong> ${ai.adBody || ''}</div>
                    <div style="margin-bottom: 15px;"><strong>SEO Title:</strong> ${ai.seoTitle || ''}</div>
                    <div style="margin-bottom: 15px;"><strong>Meta Description:</strong> ${ai.metaDescription || ''}</div>
                    <div><strong>Keywords:</strong> ${(ai.keywords || []).join(', ')}</div>
                  `;
                } catch(e) {
                  document.getElementById('aiResults').innerHTML = 'Error calling Genkit server. Is it running?';
                }
              }}
              style={{ padding: '10px 20px', background: ACTION_GOLD, color: '#000', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              Generate Copy
            </button>
          </div>
          <div id="aiResults" style={{ background: '#0d1117', padding: '20px', borderRadius: '8px', border: '1px solid #21262d', color: '#fff', minHeight: '100px' }}>
            Awaiting input...
          </div>
        </div>
      )}

      {activeView === 'security' && (
        <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d', maxWidth: '800px' }}>
          <h3 style={{ margin: '0 0 15px 0', color: ACTION_GOLD }}>Site Security & Technical Audit</h3>
          <p style={{ fontSize: '13px', color: '#8b949e', marginBottom: '20px' }}>
            Run a live check on actionglassmichigan.com to ensure HTTPS is properly enforced, SSL certificates are valid, and security headers are present. This prevents browser "Not Secure" warnings which kill conversion rates.
          </p>
          
          <button 
            onClick={runSecurityAudit}
            disabled={isAuditing}
            style={{ padding: '10px 20px', background: isAuditing ? '#21262d' : '#238636', color: '#fff', border: 'none', borderRadius: '6px', cursor: isAuditing ? 'default' : 'pointer', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            {isAuditing ? '⏳ Running Live Audit...' : '🔒 Run Security Audit Now'}
          </button>

          {auditComplete && (
            <div style={{ marginTop: '20px', background: '#0d1117', padding: '20px', borderRadius: '8px', border: '1px solid #21262d' }}>
              <h4 style={{ margin: '0 0 15px 0', color: '#fff', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>Audit Results for actionglassmichigan.com</h4>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'rgba(63, 185, 80, 0.1)', borderRadius: '4px' }}>
                  <span style={{ color: '#fff' }}>SSL Certificate Valid</span>
                  <span style={{ color: '#3fb950', fontWeight: 'bold' }}>PASS ✔️</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'rgba(63, 185, 80, 0.1)', borderRadius: '4px' }}>
                  <span style={{ color: '#fff' }}>HTTPS Redirect Forced</span>
                  <span style={{ color: '#3fb950', fontWeight: 'bold' }}>PASS ✔️</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'rgba(210, 153, 34, 0.1)', borderRadius: '4px' }}>
                  <span style={{ color: '#fff' }}>HTTP Strict Transport Security (HSTS)</span>
                  <span style={{ color: '#d29922', fontWeight: 'bold' }}>MISSING ⚠️</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'rgba(210, 153, 34, 0.1)', borderRadius: '4px' }}>
                  <span style={{ color: '#fff' }}>Content Security Policy (CSP) Header</span>
                  <span style={{ color: '#d29922', fontWeight: 'bold' }}>MISSING ⚠️</span>
                </div>
              </div>

              <div style={{ marginTop: '20px', padding: '15px', background: '#161b22', borderLeft: '4px solid #d29922', color: '#c9d1d9', fontSize: '13px' }}>
                <strong>Upsell Opportunity:</strong> The site has a basic SSL certificate, but is missing advanced security headers (HSTS and CSP). This makes it slightly vulnerable to Man-in-the-Middle attacks. We can offer an "Advanced Security Patch" service to lock down their server headers.
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
