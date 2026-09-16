import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

const RAPID_CATEGORIES = [
  { id: 'data', label: 'Data', icon: '📈' },
  { id: 'sports', label: 'Sports', icon: '🏀' },
  { id: 'ai', label: 'AI & ML', icon: '🤖' },
  { id: 'finance', label: 'Finance', icon: '💰' },
  { id: 'entertainment', label: 'Entertainment', icon: '🎬' },
  { id: 'travel', label: 'Travel', icon: '✈️' },
  { id: 'location', label: 'Location', icon: '📍' },
  { id: 'science', label: 'Science', icon: '🔬' },
  { id: 'food', label: 'Food', icon: '🍔' },
  { id: 'transportation', label: 'Transportation', icon: '🚌' },
  { id: 'music', label: 'Music', icon: '🎵' },
  { id: 'business', label: 'Business', icon: '💼' },
  { id: 'visual', label: 'Visual Recog.', icon: '👁️' },
  { id: 'tools', label: 'Tools', icon: '🛠️' },
  { id: 'text', label: 'Text Analysis', icon: '📝' },
  { id: 'weather', label: 'Weather', icon: '⛅' },
  { id: 'gaming', label: 'Gaming', icon: '🎮' },
  { id: 'sms', label: 'SMS', icon: '📱' },
  { id: 'events', label: 'Events', icon: '🎫' },
  { id: 'health', label: 'Health', icon: '🏃' }
];

const TASK_MAPPINGS = {
  entertainment: [
    { value: 'facebook_group_videos', label: 'Facebook Group Videos' },
    { value: 'facebook_user_search', label: 'Facebook User Search' },
    { value: 'tiktok_oldest_posts', label: 'TikTok Oldest Posts' },
    { value: 'instagram_followings', label: 'Instagram Followings' }
  ],
  business: [
    { value: 'email_finder', label: 'Email Finder (Hunter/Snovio)' },
    { value: 'phone_lookup', label: 'Phone Number Lookup' },
    { value: 'domain_search', label: 'Domain Search' },
    { value: 'linkedin_profile', label: 'LinkedIn Profile Data' },
    { value: 'linkedin_company', label: 'LinkedIn Company Data' },
    { value: 'linkedin_jobs', label: 'LinkedIn Job Search' }
  ],
  tools: [
    { value: 'google_search', label: 'Google Search' },
    { value: 'subdomain_finder', label: 'Subdomain Finder' },
    { value: 'skip_tracing_email', label: 'Skip Tracing by Email' }
  ],
  finance: [
    { value: 'crypto_account_balance', label: 'Crypto.com Balances (Mock)' },
    { value: 'crypto_market_data', label: 'Crypto Market Ticker' },
    { value: 'yahoo_finance', label: 'Yahoo Finance (YH Finance)' }
  ]
};

export default function BrettDataTab({ backendUrl }) {
  const [activeSubTab, setActiveSubTab] = useState('api_hub');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [rawJson, setRawJson] = useState('');
  const [parsedData, setParsedData] = useState(null);
  const [parseError, setParseError] = useState('');

  // Live Fetch State
  const [apis, setApis] = useState([]);
  const [selectedApiId, setSelectedApiId] = useState('');
  const [manualApiKey, setManualApiKey] = useState('');
  const [taskType, setTaskType] = useState('facebook_group_videos');
  const [targetId, setTargetId] = useState('');
  const [isFetching, setIsFetching] = useState(false);

  // Test & Sort State
  const [testEndpoint, setTestEndpoint] = useState('');
  const [testSelectedApiId, setTestSelectedApiId] = useState('');
  const [testManualApiKey, setTestManualApiKey] = useState('');
  const [testIsFetching, setTestIsFetching] = useState(false);
  const [testRawJson, setTestRawJson] = useState('');
  const [testParsedList, setTestParsedList] = useState(null);
  const [testError, setTestError] = useState('');

  const [vaultItems, setVaultItems] = useState([]);

  // API Manager States
  const [newApi, setNewApi] = useState({ clientName: '', apiName: '', apiKey: '', baseUrl: '', category: '' });
  const [query, setQuery] = useState('');
  const [recommenderResponse, setRecommenderResponse] = useState('');
  const [isLoadingRecommender, setIsLoadingRecommender] = useState(false);
  const [testerApiId, setTesterApiId] = useState('');
  const [testerEndpoint, setTesterEndpoint] = useState('');
  const [testerMethod, setTesterMethod] = useState('GET');
  const [testerAuthType, setTesterAuthType] = useState('Query Parameter');
  const [testerAuthKeyName, setTesterAuthKeyName] = useState('access_token');
  const [testerBody, setTesterBody] = useState('');
  const [testerResponse, setTesterResponse] = useState('');
  const [isTesting, setIsTesting] = useState(false);

  useEffect(() => {
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/keys`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setApis(data.keys);
        }
      })
      .catch(err => console.error("Failed to fetch keys:", err));

    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/data`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setVaultItems(data.vault);
        }
      })
      .catch(err => console.error("Failed to fetch vault data:", err));
  }, [backendUrl]);

  const handleSaveToVault = (item, source) => {
    const payload = {
      id: crypto.randomUUID(),
      timestamp: Date.now(),
      source,
      data: item
    };
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/data`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(() => {
      setVaultItems([payload, ...vaultItems]);
      alert('Saved to Vault!');
    });
  };

  const handleDeleteFromVault = (id) => {
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/data/${id}`, { method: "DELETE" }).then(() => {
      setVaultItems(vaultItems.filter(i => i.id !== id));
    });
  };

  const handleSendToClipboard = (item) => {
    const formatted = JSON.stringify(item.data, null, 2);
    navigator.clipboard.writeText(formatted).then(() => {
      alert('Copied to clipboard! You can now paste this anywhere.');
    }).catch(() => {
      alert('Failed to copy to clipboard.');
    });
  };

  const handleAddApi = (e) => {
    e.preventDefault();
    if (!newApi.apiName || !newApi.apiKey) return;
    const apiObj = { id: Date.now().toString(), clientName: newApi.clientName || 'Custom', ...newApi };
    
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(apiObj)
    }).then(() => {
      setApis([...apis, apiObj]);
      setNewApi({ clientName: '', apiName: '', apiKey: '', baseUrl: '', category: '' });
    });
  };

  const handleDeleteApi = (id) => {
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/keys/${id}`, { method: "DELETE" }).then(() => {
      setApis(apis.filter(api => api.id !== id));
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const handleAskRecommender = async (e) => {
    e.preventDefault();
    if (!query) return;
    setIsLoadingRecommender(true);
    setRecommenderResponse('');
    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `I need an API recommendation. ${query}. Please list 2-3 public or RapidAPI APIs that could solve this, with their general capabilities and where to find them. Format as markdown.`,
          model: 'stehouwer_llm',
          persona: 'Brett Stehouwer (CTO)'
        })
      });
      if (!res.ok) throw new Error("Failed to fetch recommendation");
      const data = await res.json();
      setRecommenderResponse(data.reply);
    } catch (err) {
      setRecommenderResponse("Error contacting AI for recommendation.");
    } finally {
      setIsLoadingRecommender(false);
    }
  };

  const handleRunTest = async (e) => {
    e.preventDefault();
    if (!testerApiId || !testerEndpoint) return;
    const apiToTest = apis.find(a => a.id === testerApiId);
    if (!apiToTest) return;
    setIsTesting(true);
    setTesterResponse('Running test...');
    try {
      let finalUrl = testerEndpoint;
      const headers = { 'Accept': 'application/json' };
      if (testerAuthType === 'Query Parameter') {
        const separator = finalUrl.includes('?') ? '&' : '?';
        finalUrl = `${finalUrl}${separator}${testerAuthKeyName}=${encodeURIComponent(apiToTest.apiKey)}`;
      } else if (testerAuthType === 'Bearer Token') {
        headers['Authorization'] = `Bearer ${apiToTest.apiKey}`;
      } else if (testerAuthType === 'Custom Header') {
        headers[testerAuthKeyName] = apiToTest.apiKey;
      }
      try {
        const urlObj = new URL(finalUrl);
        if (urlObj.hostname.includes('rapidapi.com')) {
          headers['x-rapidapi-host'] = urlObj.hostname;
          headers['x-rapidapi-key'] = apiToTest.apiKey;
        }
      } catch (e) {}
      const options = { method: testerMethod, headers };
      if (testerMethod !== 'GET' && testerMethod !== 'HEAD' && testerBody) {
        options.body = testerBody;
        headers['Content-Type'] = 'application/json';
      }
      const res = await fetch(finalUrl, options);
      const data = await res.json().catch(() => null);
      const responsePayload = {
        status: res.status,
        statusText: res.statusText,
        headers: Object.fromEntries(res.headers.entries()),
        data: data || "No JSON returned or failed to parse JSON"
      };
      setTesterResponse(JSON.stringify(responsePayload, null, 2));
    } catch (err) {
      setTesterResponse(JSON.stringify({ error: err.message }, null, 2));
    } finally {
      setIsTesting(false);
    }
  };

  const handleFetchLive = async () => {
    let finalApiKey = '';
    if (selectedApiId) {
      const api = apis.find(a => a.id === selectedApiId);
      if (api) finalApiKey = api.apiKey;
    } else if (manualApiKey) {
      finalApiKey = manualApiKey;
    }

    if (!finalApiKey || !taskType || !targetId) return;

    setIsFetching(true);
    setParseError('');
    setParsedData(null);

    try {
      const res = await fetch(`${backendUrl}/api/proxy/3001/api/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          taskType,
          targetId,
          apiKey: finalApiKey
        })
      });
      
      const backendData = await res.json();
      
      if (!res.ok) {
        throw new Error(backendData.error || 'Backend failed');
      }

      setRawJson(JSON.stringify(backendData, null, 2));
      const data = backendData.data;

      if (data && data.data && data.data.videos) {
        setParsedData(data.data.videos);
      } else if (Array.isArray(data)) {
        setParsedData(data);
      } else if (data && data.videos) {
        setParsedData(data.videos);
      } else {
        setParseError('Fetched successfully, but could not find a recognized list to render. File saved to: ' + backendData.savedPath);
        setParsedData(null);
      }
    } catch (err) {
      setParseError('Failed to fetch data: ' + err.message);
      setParsedData(null);
    } finally {
      setIsFetching(false);
    }
  };

  const getTaskHelperText = (type) => {
    switch (type) {
      case 'facebook_group_videos': return "Fetches videos from a Facebook group. Target ID: The numerical ID of the group (e.g., 1571965316444595).";
      case 'facebook_user_search': return "Searches for a user on Facebook. Target ID: The user's name or search term.";
      case 'tiktok_oldest_posts': return "Fetches the oldest posts from a TikTok user. Target ID: The 'secUid' of the TikTok user.";
      case 'instagram_followings': return "Fetches the list of people an Instagram user follows. Target ID: The exact Instagram username.";
      case 'google_search': return "Performs a Google Search. Target ID: Your search query (e.g., 'plumbers in NY').";
      case 'subdomain_finder': return "Finds subdomains for a given website. Target ID: The domain name (e.g., 'example.com').";
      case 'skip_tracing_email': return "Performs a skip trace lookup based on an email. Target ID: The email address to look up.";
      default: return "";
    }
  };

  const extractArrayFromJSON = (obj) => {
    if (Array.isArray(obj)) return obj;
    if (obj && typeof obj === 'object') {
      for (const key of Object.keys(obj)) {
        if (Array.isArray(obj[key])) return obj[key];
        const nested = extractArrayFromJSON(obj[key]);
        if (nested) return nested;
      }
    }
    return null;
  };

  const handleTestFetchLive = async () => {
    let finalApiKey = '';
    if (testSelectedApiId) {
      const api = apis.find(a => a.id === testSelectedApiId);
      if (api) finalApiKey = api.apiKey;
    } else if (testManualApiKey) {
      finalApiKey = testManualApiKey;
    }

    if (!finalApiKey || !testEndpoint) return;

    setTestIsFetching(true);
    setTestError('');
    setTestParsedList(null);

    try {
      const headers = { 'Accept': 'application/json' };
      const urlObj = new URL(testEndpoint);
      if (urlObj.hostname.includes('rapidapi.com')) {
        headers['x-rapidapi-host'] = urlObj.hostname;
        headers['x-rapidapi-key'] = finalApiKey;
      }

      const res = await fetch(testEndpoint, { headers });
      const data = await res.json();
      setTestRawJson(JSON.stringify(data, null, 2));

      const foundArray = extractArrayFromJSON(data);
      if (foundArray && foundArray.length > 0) {
        setTestParsedList(foundArray);
      } else {
        setTestError('Fetched successfully, but could not automatically detect an array of items in the JSON to render.');
        setTestParsedList(null);
      }
    } catch (err) {
      setTestError('Failed to fetch data: ' + err.message);
      setTestParsedList(null);
    } finally {
      setTestIsFetching(false);
    }
  };

  const handleParseJson = () => {
    setParseError('');
    try {
      const data = JSON.parse(rawJson);
      
      // Handle the specific facebook scraper payload we saw
      if (data && data.data && data.data.videos) {
        setParsedData(data.data.videos);
      } else if (data && data.videos) {
        setParsedData(data.videos);
      } else if (Array.isArray(data)) {
        setParsedData(data); // Generic array
      } else {
        setParseError('Parsed successfully, but could not find a "videos" array or a standard list of items in the JSON.');
        setParsedData(null);
      }
    } catch (err) {
      setParseError('Invalid JSON format. Please paste valid JSON output from the API Tester.');
      setParsedData(null);
    }
  };

  return (
    <div className="tab-container" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <h2 className="tab-header" style={{ color: 'var(--accent)' }}>Brett Stehouwer Data Hub</h2>
      <p style={{ color: 'var(--text-muted)' }}>Skim, organize, and visualize data gathered from your APIs.</p>

      {/* Sub-Navigation */}
      <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '16px' }}>
        <button 
          onClick={() => setActiveSubTab('api_hub')}
          style={{ 
            background: activeSubTab === 'api_hub' ? 'rgba(255,255,255,0.1)' : 'transparent',
            border: activeSubTab === 'api_hub' ? '1px solid var(--accent)' : '1px solid transparent',
            color: activeSubTab === 'api_hub' ? 'white' : 'var(--text-muted)',
            padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s'
          }}>
          🌐 API Catalog
        </button>
        <button 
          onClick={() => setActiveSubTab('test_sort')}
          style={{ 
            background: activeSubTab === 'test_sort' ? 'rgba(255,255,255,0.1)' : 'transparent',
            border: activeSubTab === 'test_sort' ? '1px solid var(--accent)' : '1px solid transparent',
            color: activeSubTab === 'test_sort' ? 'white' : 'var(--text-muted)',
            padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s'
          }}>
          🧪 Test & Sort
        </button>
        <button 
          onClick={() => setActiveSubTab('api_manager')}
          style={{ 
            background: activeSubTab === 'api_manager' ? 'rgba(255,255,255,0.1)' : 'transparent',
            border: activeSubTab === 'api_manager' ? '1px solid var(--accent)' : '1px solid transparent',
            color: activeSubTab === 'api_manager' ? 'white' : 'var(--text-muted)',
            padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s'
          }}>
          🔑 API Vault & Discovery
        </button>
        <button 
          onClick={() => setActiveSubTab('vault')}
          style={{ 
            background: activeSubTab === 'vault' ? 'rgba(255,255,255,0.1)' : 'transparent',
            border: activeSubTab === 'vault' ? '1px solid var(--accent)' : '1px solid transparent',
            color: activeSubTab === 'vault' ? 'white' : 'var(--text-muted)',
            padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s',
            marginLeft: 'auto'
          }}>
          🗄️ Data Vault ({vaultItems.length})
        </button>
      </div>

      {activeSubTab === 'api_hub' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {!selectedCategory ? (
            <div className="glass-card">
              <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>API Catalog</h3>
              <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '24px' }}>
                Select a category to view and run live API connections.
              </p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '16px' }}>
                {RAPID_CATEGORIES.map(cat => (
                  <button 
                    key={cat.id}
                    onClick={() => { setSelectedCategory(cat.id); setTaskType(TASK_MAPPINGS[cat.id]?.[0]?.value || ''); }}
                    style={{
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '12px',
                      padding: '24px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '12px',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.borderColor = 'var(--accent)'; }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.3)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}
                  >
                    <span style={{ fontSize: '2.5rem' }}>{cat.icon}</span>
                    <span style={{ color: '#e2e8f0', fontSize: '0.95rem', fontWeight: '500', textAlign: 'center' }}>{cat.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              <button 
                onClick={() => setSelectedCategory(null)}
                style={{ alignSelf: 'flex-start', background: 'transparent', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                ← Back to Categories
              </button>
              
              <div className="glass-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '1.5rem' }}>{RAPID_CATEGORIES.find(c => c.id === selectedCategory)?.icon}</span>
                  <h3 className="glass-card-title" style={{color: 'white', margin: 0}}>
                    {RAPID_CATEGORIES.find(c => c.id === selectedCategory)?.label} Data Connection
                  </h3>
                </div>
                <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px' }}>
                  Connect directly to your API and pull data automatically.
                </p>
                
                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '16px' }}>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>API Key to Use</label>
                    <select 
                      className="chat-input"
                      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white', marginBottom: '8px' }}
                      value={selectedApiId} onChange={e => setSelectedApiId(e.target.value)}
                    >
                      <option value="" style={{color: 'black'}}>-- Select API Key --</option>
                      {apis.map(api => (
                        <option key={api.id} value={api.id} style={{color: 'black'}}>{api.apiName}</option>
                      ))}
                    </select>
                    <input 
                      type="text" placeholder="Or paste API key manually..." className="chat-input"
                      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                      value={manualApiKey} onChange={e => setManualApiKey(e.target.value)}
                      disabled={!!selectedApiId}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: '150px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Task Type</label>
                    <select 
                      className="chat-input"
                      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white' }}
                      value={taskType} onChange={e => setTaskType(e.target.value)}
                    >
                      {TASK_MAPPINGS[selectedCategory] ? (
                        TASK_MAPPINGS[selectedCategory].map(t => (
                          <option key={t.value} value={t.value} style={{color: 'black'}}>{t.label}</option>
                        ))
                      ) : (
                        <option value="" style={{color: 'black'}}>No specific tasks configured yet</option>
                      )}
                    </select>
                  </div>
                  <div style={{ flex: 2, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Target ID / Search Query</label>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input 
                        type="text" placeholder="e.g. 1571965316444595 or full URL" className="chat-input"
                        style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', flex: 1, width: '100%' }}
                        value={targetId} onChange={e => setTargetId(e.target.value)}
                      />
                      {taskType === 'facebook_group_videos' && (
                        <button 
                          onClick={async () => {
                             if (!targetId.includes('facebook.com')) { alert('Please paste a full Facebook URL to extract the ID'); return; }
                             try {
                               const res = await fetch(`${backendUrl}/api/proxy/3001/api/utils/fb-group-id`, {
                                 method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: targetId })
                               });
                               const data = await res.json();
                               if (data.success) {
                                  setTargetId(data.groupId);
                               } else {
                                  alert(data.error);
                               }
                             } catch (err) { alert('Failed: ' + err.message); }
                          }}
                          style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid var(--accent)', color: 'white', borderRadius: '8px', padding: '0 12px', cursor: 'pointer', whiteSpace: 'nowrap' }}
                          title="Extract Group ID from URL"
                        >
                          🔍 Extract ID
                        </button>
                      )}
                    </div>
                  </div>
                </div>
    
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', marginBottom: '16px', borderLeft: '4px solid var(--accent)' }}>
                  <strong style={{color: 'white'}}>💡 Tip:</strong> <span style={{ color: '#94a3b8', fontSize: '0.9rem', marginLeft: '8px' }}>{getTaskHelperText(taskType)}</span>
                </div>
    
                <button onClick={handleFetchLive} className="send-button" style={{ padding: '8px 24px' }} disabled={isFetching || (!selectedApiId && !manualApiKey) || !targetId || !taskType}>
                  {isFetching ? 'Fetching...' : '⚡ Fetch & Organize Live Data'}
                </button>
              </div>
    
              <div className="glass-card">
                <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>Manual Data Input (Fallback)</h3>
                <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px' }}>
                  Or, you can paste the raw JSON response manually here.
                </p>
                <textarea 
                  className="chat-input"
                  placeholder='Paste JSON here...'
                  value={rawJson}
                  onChange={(e) => setRawJson(e.target.value)}
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', minHeight: '120px', fontFamily: 'monospace', color: '#c9d1d9', marginBottom: '16px' }}
                />
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <button onClick={handleParseJson} className="send-button" style={{ padding: '8px 24px' }}>
                    Parse Data
                  </button>
                  {parseError && <span style={{ color: '#ef4444', fontSize: '0.9rem' }}>{parseError}</span>}
                </div>
              </div>
    
              {parsedData && (
                <div className="glass-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                    <h3 className="glass-card-title" style={{color: 'white', margin: 0}}>Organized Feed</h3>
                    <span className="status-pill active">{parsedData.length} items found</span>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px' }}>
                    {parsedData.map((item, idx) => (
                      <div key={item.id || idx} style={{ 
                        background: 'rgba(0,0,0,0.4)', 
                        borderRadius: '12px', 
                        border: '1px solid rgba(255,255,255,0.05)',
                        overflow: 'hidden',
                        display: 'flex',
                        flexDirection: 'column'
                      }}>
                        {item.image && item.image.uri ? (
                          <div style={{ width: '100%', height: '200px', backgroundImage: `url(${item.image.uri})`, backgroundSize: 'cover', backgroundPosition: 'center' }} />
                        ) : (
                          <div style={{ width: '100%', height: '200px', background: 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
                            No Image
                          </div>
                        )}
                        
                        <div style={{ padding: '16px', flex: 1, display: 'flex', flexDirection: 'column' }}>
                          <p style={{ color: '#e2e8f0', fontSize: '0.95rem', marginBottom: '16px', flex: 1, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                            {item.message || "No caption provided."}
                          </p>
                          
                          {item.url && (
                            <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ 
                              display: 'inline-block', 
                              background: 'rgba(255,255,255,0.1)', 
                              color: 'var(--accent)', 
                              padding: '8px 16px', 
                              borderRadius: '6px', 
                              textDecoration: 'none', 
                              textAlign: 'center',
                              fontSize: '0.9rem',
                              fontWeight: 'bold',
                              transition: 'background 0.2s',
                              marginBottom: '8px'
                            }}
                            onMouseOver={(e) => e.target.style.background = 'rgba(255,255,255,0.2)'}
                            onMouseOut={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                            >
                              Watch on Source
                            </a>
                          )}
                          <button onClick={() => handleSaveToVault(item, 'Extracted Data')} style={{
                            background: 'transparent',
                            border: '1px solid rgba(255,255,255,0.2)',
                            color: 'white',
                            padding: '8px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.9rem'
                          }}
                          onMouseOver={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                          onMouseOut={(e) => e.target.style.background = 'transparent'}>
                            💾 Save to Vault
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeSubTab === 'test_sort' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-card">
            <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>API Test Sandbox</h3>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px' }}>
              Test any API endpoint here. The system will attempt to automatically find and render any list of items it returns.
            </p>
            
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '16px' }}>
              <div style={{ flex: 1, minWidth: '200px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>API Key to Use</label>
                <select 
                  className="chat-input"
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white', marginBottom: '8px' }}
                  value={testSelectedApiId} onChange={e => setTestSelectedApiId(e.target.value)}
                >
                  <option value="" style={{color: 'black'}}>-- Select API Key --</option>
                  {apis.map(api => (
                    <option key={api.id} value={api.id} style={{color: 'black'}}>{api.apiName}</option>
                  ))}
                </select>
                <input 
                  type="text" placeholder="Or paste API key manually..." className="chat-input"
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                  value={testManualApiKey} onChange={e => setTestManualApiKey(e.target.value)}
                  disabled={!!testSelectedApiId}
                />
              </div>
              <div style={{ flex: 2, minWidth: '300px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Endpoint URL</label>
                <input 
                  type="url" placeholder="Paste any RapidAPI endpoint here..." className="chat-input"
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                  value={testEndpoint} onChange={e => setTestEndpoint(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <button onClick={handleTestFetchLive} className="send-button" style={{ padding: '8px 24px' }} disabled={testIsFetching || (!testSelectedApiId && !testManualApiKey) || !testEndpoint}>
                {testIsFetching ? 'Fetching...' : '🧪 Fetch & Auto-Sort'}
              </button>
              {testError && <span style={{ color: '#ef4444', fontSize: '0.9rem' }}>{testError}</span>}
            </div>
          </div>

          {testRawJson && !testParsedList && (
            <div className="glass-card">
               <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>Raw JSON Response</h3>
               <textarea 
                  className="chat-input"
                  readOnly
                  value={testRawJson}
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', minHeight: '300px', fontFamily: 'monospace', color: '#c9d1d9', marginBottom: '16px' }}
                />
            </div>
          )}

          {testParsedList && (
            <div className="glass-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h3 className="glass-card-title" style={{color: 'white', margin: 0}}>Auto-Discovered Data Cards</h3>
                <span className="status-pill active">{testParsedList.length} items found</span>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px' }}>
                {testParsedList.map((item, idx) => (
                  <div key={item.id || idx} style={{ 
                    background: 'rgba(0,0,0,0.4)', 
                    borderRadius: '12px', 
                    border: '1px solid rgba(255,255,255,0.05)',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column'
                  }}>
                    <div style={{ flex: 1, marginBottom: '16px', overflow: 'hidden', fontSize: '0.85rem', color: '#e2e8f0' }}>
                      {Object.keys(item).slice(0, 5).map(key => (
                        <div key={key} style={{ marginBottom: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          <strong style={{ color: 'var(--accent)' }}>{key}:</strong> {typeof item[key] === 'object' ? JSON.stringify(item[key]).substring(0, 50) + '...' : String(item[key])}
                        </div>
                      ))}
                      {Object.keys(item).length > 5 && <div style={{ color: '#94a3b8', fontStyle: 'italic', marginTop: '4px' }}>+ {Object.keys(item).length - 5} more fields...</div>}
                    </div>
                    
                    <button onClick={() => handleSaveToVault(item, 'Auto-Sorted Data API')} style={{
                      background: 'transparent',
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: 'white',
                      padding: '8px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.9rem'
                    }}
                    onMouseOver={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                    onMouseOut={(e) => e.target.style.background = 'transparent'}>
                      💾 Save to Vault
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'api_manager' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px', marginBottom: '8px', borderLeft: '4px solid var(--accent)' }}>
            <h4 style={{ color: 'white', marginTop: 0, marginBottom: '8px' }}>📖 How to use this tab:</h4>
            <ul style={{ color: '#94a3b8', fontSize: '0.9rem', margin: 0, paddingLeft: '20px', lineHeight: '1.5' }}>
              <li><strong>Add New API Key:</strong> Store your RapidAPI or custom API keys securely here. They will be saved locally.</li>
              <li><strong>AI API Recommender:</strong> Not sure which API to use? Ask the AI to suggest one based on your goal.</li>
              <li><strong>API Tester Workbench:</strong> Test an endpoint directly from the dashboard to see what raw JSON data it returns before building a full integration for it.</li>
            </ul>
          </div>

          <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
            {/* Left Column: Vault & Form */}
            <div style={{ flex: '2', minWidth: '350px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              <div className="glass-card">
                <h3 className="glass-card-title" style={{color: 'white', marginBottom: '16px'}}>Add New API Key</h3>
                <form onSubmit={handleAddApi} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <input type="text" placeholder="Client Name (e.g. Action Glass)" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.clientName} onChange={e => setNewApi({...newApi, clientName: e.target.value})} />
                  <input type="text" placeholder="API Name (e.g. Facebook Graph API) *" className="chat-input" required
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.apiName} onChange={e => setNewApi({...newApi, apiName: e.target.value})} />
                  <input type="text" placeholder="Category (e.g. Social, SEO, Weather)" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.category} onChange={e => setNewApi({...newApi, category: e.target.value})} />
                  <input type="text" placeholder="Base URL (optional)" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.baseUrl} onChange={e => setNewApi({...newApi, baseUrl: e.target.value})} />
                  <input type="password" placeholder="API Key / Token *" className="chat-input" required
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.apiKey} onChange={e => setNewApi({...newApi, apiKey: e.target.value})} />
                  <button type="submit" className="send-button" style={{ marginTop: '8px', alignSelf: 'flex-start' }}>Save API Config</button>
                </form>
              </div>

              <div className="glass-card" style={{ flex: 1 }}>
                <h3 className="glass-card-title" style={{color: 'white', marginBottom: '16px'}}>Saved APIs</h3>
                {apis.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)' }}>No APIs saved yet.</p>
                ) : (
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {apis.map(api => (
                      <div key={api.id} style={{ 
                        background: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: '8px',
                        border: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: '8px'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <strong style={{ fontSize: '1.1rem', color: 'var(--accent-neon)' }}>{api.apiName}</strong>
                          {api.id !== 'system-rapidapi' && (
                            <button onClick={() => handleDeleteApi(api.id)} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '1.2rem' }} title="Delete API">×</button>
                          )}
                        </div>
                        {api.clientName && <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Client: {api.clientName}</div>}
                        {api.category && <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Category: <span className="status-pill new">{api.category}</span></div>}
                        {api.baseUrl && <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Base URL: {api.baseUrl}</div>}
                        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                          <input type="password" value={api.apiKey} readOnly className="chat-input" style={{ background: 'rgba(255,255,255,0.05)', border: 'none', flex: 1, padding: '8px', borderRadius: '4px' }} />
                          <button onClick={() => copyToClipboard(api.apiKey)} className="tool-toggle-btn" title="Copy API Key">📋 Copy</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: AI Recommender */}
            <div style={{ flex: '1', minWidth: '300px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>AI API Recommender</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                  Describe what kind of data or functionality you need, and the AI will suggest the best APIs for the job.
                </p>
                <form onSubmit={handleAskRecommender} style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                  <input type="text" placeholder="E.g. I need an API for real estate listings" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', flex: 1 }}
                    value={query} onChange={e => setQuery(e.target.value)} />
                  <button type="submit" className="send-button" disabled={isLoadingRecommender}>
                    {isLoadingRecommender ? '...' : 'Ask'}
                  </button>
                </form>
                <div style={{ flex: 1, background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '16px', border: '1px solid rgba(255,255,255,0.05)', overflowY: 'auto', minHeight: '200px' }} className="artifact-markdown-container">
                  {isLoadingRecommender ? (
                    <div style={{ color: 'var(--accent)', fontStyle: 'italic' }}>Searching API directories...</div>
                  ) : recommenderResponse ? (
                    <ReactMarkdown>{recommenderResponse}</ReactMarkdown>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', marginTop: '40px' }}>
                      Ask me for API recommendations!
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* API Tester Workbench */}
          <div className="glass-card" style={{ marginTop: '0px' }}>
            <h3 className="glass-card-title" style={{color: 'white', marginBottom: '16px'}}>API Tester Workbench</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Select a saved API key and enter an endpoint to test the connection.
            </p>
            <form onSubmit={handleRunTest} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Saved API</label>
                  <select className="chat-input" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white' }}
                    value={testerApiId} onChange={e => setTesterApiId(e.target.value)} required>
                    <option value="" style={{color: 'black'}}>-- Select API --</option>
                    {apis.map(api => (
                      <option key={api.id} value={api.id} style={{color: 'black'}}>{api.apiName} ({api.clientName || 'No Client'})</option>
                    ))}
                  </select>
                </div>
                <div style={{ flex: 2, minWidth: '300px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Endpoint URL</label>
                  <input type="url" placeholder="https://graph.facebook.com/v19.0/me" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                    value={testerEndpoint} onChange={e => setTesterEndpoint(e.target.value)} required />
                </div>
                <div style={{ flex: '0 1 120px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Method</label>
                  <select className="chat-input" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white' }}
                    value={testerMethod} onChange={e => setTesterMethod(e.target.value)}>
                    <option value="GET" style={{color: 'black'}}>GET</option>
                    <option value="POST" style={{color: 'black'}}>POST</option>
                    <option value="PUT" style={{color: 'black'}}>PUT</option>
                    <option value="DELETE" style={{color: 'black'}}>DELETE</option>
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Auth Type</label>
                  <select className="chat-input" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white' }}
                    value={testerAuthType} onChange={e => setTesterAuthType(e.target.value)}>
                    <option value="Query Parameter" style={{color: 'black'}}>Query Parameter</option>
                    <option value="Bearer Token" style={{color: 'black'}}>Bearer Token</option>
                    <option value="Custom Header" style={{color: 'black'}}>Custom Header</option>
                  </select>
                </div>
                {(testerAuthType === 'Query Parameter' || testerAuthType === 'Custom Header') && (
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Key Name</label>
                    <input type="text" placeholder={testerAuthType === 'Query Parameter' ? 'access_token' : 'x-api-key'} className="chat-input"
                      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                      value={testerAuthKeyName} onChange={e => setTesterAuthKeyName(e.target.value)} />
                  </div>
                )}
              </div>
              {testerMethod !== 'GET' && testerMethod !== 'DELETE' && (
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>JSON Body (Optional)</label>
                  <textarea className="chat-input" placeholder='{"key": "value"}'
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', minHeight: '80px', fontFamily: 'monospace' }}
                    value={testerBody} onChange={e => setTesterBody(e.target.value)} />
                </div>
              )}
              <button type="submit" className="send-button" style={{ alignSelf: 'flex-start', padding: '10px 24px' }} disabled={isTesting || !testerApiId}>
                {isTesting ? 'Testing...' : '▶ Run Test'}
              </button>
            </form>
            {testerResponse && (
              <div style={{ marginTop: '24px' }}>
                <h4 style={{ color: '#94a3b8', marginBottom: '8px' }}>Response Output</h4>
                <pre style={{ background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #30363d', overflowX: 'auto', color: '#c9d1d9', fontFamily: 'monospace', fontSize: '0.85rem', maxHeight: '400px', overflowY: 'auto' }}>
                  {testerResponse}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {activeSubTab === 'vault' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-card">
            <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>Data Vault</h3>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px' }}>
              Saved items are stored here. Use the "Send To" button to copy them to your clipboard and paste them into any form or prompt.
            </p>
            {vaultItems.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
                Your vault is empty. Save items from the live feeds to see them here!
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px' }}>
                {vaultItems.map(item => (
                  <div key={item.id} style={{ 
                    background: 'rgba(0,0,0,0.4)', 
                    borderRadius: '12px', 
                    border: '1px solid rgba(255,255,255,0.05)',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '1px' }}>{item.source}</span>
                      <button onClick={() => handleDeleteFromVault(item.id)} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer' }} title="Delete">🗑️</button>
                    </div>
                    
                    <div style={{ flex: 1, background: 'rgba(0,0,0,0.3)', borderRadius: '6px', padding: '8px', overflow: 'hidden', marginBottom: '16px', fontSize: '0.8rem', color: '#e2e8f0', fontFamily: 'monospace' }}>
                      {item.source === 'Facebook Video' && item.data.message ? (
                        <div style={{ display: '-webkit-box', WebkitLineClamp: 4, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          {item.data.message}
                        </div>
                      ) : (
                        <div style={{ display: '-webkit-box', WebkitLineClamp: 4, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          {JSON.stringify(item.data).substring(0, 150)}...
                        </div>
                      )}
                    </div>
                    
                    <button onClick={() => handleSendToClipboard(item)} style={{
                      background: 'var(--accent)',
                      border: 'none',
                      color: 'white',
                      padding: '10px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.9rem',
                      fontWeight: 'bold',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px'
                    }}>
                      📤 Send To Clipboard
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
