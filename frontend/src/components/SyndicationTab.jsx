import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';

export default function SyndicationTab({ backendUrl, currentUser }) {
  const apiHost = backendUrl || getApiBase() || 'http://127.0.0.1:8000';
  
  // Broadcaster State
  const [siteName, setSiteName] = useState('Stehouwer Publishing L.L.C.');
  const [targetUrl, setTargetUrl] = useState('https://stehouwer-publishing.com');
  const [feedUrl, setFeedUrl] = useState('https://stehouwer-publishing.com/library');
  const [customMsg, setCustomMsg] = useState('Stehouwer-Publishing.com');
  const [selectedBroadcastTier, setSelectedBroadcastTier] = useState('all');
  
  // Campaign Multiplexer Mode
  const [campaignMode, setCampaignMode] = useState('single'); // 'single', 'footprint', 'music', 'literary'
  
  // Social & Community Channels Toggles
  const [channels, setChannels] = useState({
    discord: true,
    telegram: true,
    bluesky: true,
    mastodon: true,
    sitemap: true
  });

  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [broadcastResults, setBroadcastResults] = useState(null);
  const [history, setHistory] = useState([]);
  const [copiedId, setCopiedId] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [resultsFilter, setResultsFilter] = useState('all');
  const [nodeSearchQuery, setNodeSearchQuery] = useState('');
  
  // Node Health State
  const [matrixHealth, setMatrixHealth] = useState(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [smartSkipDeadNodes, setSmartSkipDeadNodes] = useState(true);

  // Campaign Multiplexer Presets
  const CAMPAIGN_PRESETS = {
    single: {
      name: '🎯 Single Target URL',
      description: 'Broadcast a single custom destination URL across the matrix.',
      urls: []
    },
    footprint: {
      name: '🌐 Full Media Footprint (5 Targets)',
      description: 'Simultaneously blasts Website + Amazon Book + IMDb + YouTube + Facebook.',
      urls: [
        'https://stehouwer-publishing.com',
        'https://www.amazon.com/dp/B0H524NPXV',
        'https://www.imdb.com/name/nm12567135/',
        'https://www.youtube.com/@BrettStehouwer',
        'https://www.facebook.com/Bstehouwer/'
      ]
    },
    music: {
      name: '🎵 Music & Sound Fleet (4 Targets)',
      description: 'Multiplexes Storefront + Audio Library + Marketing Hub + YouTube.',
      urls: [
        'https://stehouwer-publishing.com',
        'https://stehouwer-publishing.com/library',
        'https://stehouwer-publishing.com/marketing.html',
        'https://www.youtube.com/@BrettStehouwer'
      ]
    },
    literary: {
      name: '🎬 Literary & Film Suite (3 Targets)',
      description: 'Multiplexes Main Catalog + Amazon Book Edition + IMDb Industry Profile.',
      urls: [
        'https://stehouwer-publishing.com',
        'https://www.amazon.com/dp/B0H524NPXV',
        'https://www.imdb.com/name/nm12567135/'
      ]
    }
  };

  // 37 Node Protocol & Channel Tiers
  const PROTOCOL_TIERS = [
    { id: 'all', label: 'All 37 Channels & Nodes', count: 37, color: '#38bdf8' },
    { id: 'social', label: 'Community & Social', count: 4, color: '#00f0ff' },
    { id: 'indexnow', label: 'IndexNow Fleet', count: 7, color: '#10b981' },
    { id: 'xmlrpc', label: 'XML-RPC Network', count: 12, color: '#f59e0b' },
    { id: 'websub', label: 'WebSub Push Hubs', count: 4, color: '#a855f7' },
    { id: 'decentralized', label: 'Decentralized W3C', count: 2, color: '#ec4899' },
    { id: 'archival', label: 'Archival Gateways', count: 2, color: '#facc15' },
    { id: 'aggregator', label: 'Aggregator Gateways', count: 5, color: '#6366f1' },
    { id: 'local', label: 'Local Sitemap / RSS', count: 1, color: '#22c55e' }
  ];

  // Ad Copy Presets
  const adPresets = [
    {
      id: 'stream_chat_short',
      category: 'stream',
      title: '🔴 YouTube & Twitch Live Chat (Pure Link)',
      target: 'YouTube / Twitch Live Chat',
      text: 'Stehouwer-Publishing.com'
    },
    {
      id: 'stream_chat_value',
      category: 'stream',
      title: '💬 Live Stream Producer Blurb',
      target: 'Stream Chat / Discord Voice',
      text: 'Check out Stehouwer Publishing for sound suites, stems, and audio scoring: https://stehouwer-publishing.com'
    },
    {
      id: 'reddit_producers',
      category: 'music',
      title: '🎹 Reddit Music Communities',
      target: 'r/WeAreTheMusicMakers, r/FL_Studio, Gearspace',
      text: "We've developed an ecosystem uniting high-fidelity audio engineering, sample management, and film/game scoring pipelines. Explore our catalog and sound suites at https://stehouwer-publishing.com"
    },
    {
      id: 'screenwriting_film',
      category: 'film',
      title: '🎬 Stage 32 & Screenwriters Hub',
      target: 'Stage 32, r/Screenwriting, IndieWire',
      text: 'Stehouwer Publishing develops high-concept literary works, narrative screenplays, and bespoke soundtracks for film and interactive media: https://stehouwer-publishing.com'
    },
    {
      id: 'social_x_threads',
      category: 'social',
      title: '📱 Twitter / X & Threads Showcase',
      target: 'Twitter / X, Threads, Bluesky',
      text: 'Elevating modern sound design, audio engineering, and dynamic scoring workflows.\n\nExplore our sound suites, DAW technology, and creative catalog at Stehouwer Publishing:\n👉 https://stehouwer-publishing.com\n\n#MusicProduction #SoundDesign #AudioEngineering #Beatmakers #Producers #DAW #Publishing'
    }
  ];

  // Multi-Endpoint Fallback Host Strategy
  const candidateHosts = [
    backendUrl,
    'http://127.0.0.1:8080',
    'http://localhost:8080',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    getApiBase(),
    ''
  ].filter(Boolean);

  const [activeHost, setActiveHost] = useState(backendUrl || 'http://127.0.0.1:8080');

  const fetchWithFallback = async (endpoint, options = {}) => {
    // 1. Try active host first
    try {
      const res = await fetch(`${activeHost}${endpoint}`, options);
      if (res.ok) return res;
    } catch (e) {}

    // 2. Try candidate hosts in order
    for (const host of candidateHosts) {
      if (host === activeHost) continue;
      try {
        const res = await fetch(`${host}${endpoint}`, options);
        if (res.ok) {
          setActiveHost(host);
          return res;
        }
      } catch (err) {}
    }
    return null;
  };

  const fetchHistory = async () => {
    try {
      const res = await fetchWithFallback('/api/syndication/history?limit=25', {
        headers: { 'X-Client-ID': 'stehouwer_publishing' }
      });
      if (res && res.ok) {
        const data = await res.json();
        setHistory(data.history || []);
      }
    } catch (e) {
      console.warn('Failed to fetch syndication history:', e);
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await fetchWithFallback('/api/syndication/matrix/health', {
        headers: { 'X-Client-ID': 'stehouwer_publishing' }
      });
      if (res && res.ok) {
        const data = await res.json();
        setMatrixHealth(data.data || null);
      }
    } catch (e) {
      console.warn('Failed to fetch matrix health:', e);
    }
  };

  const handleRunAudit = async () => {
    setIsAuditing(true);
    try {
      const res = await fetchWithFallback('/api/syndication/matrix/audit', {
        method: 'POST',
        headers: { 'X-Client-ID': 'stehouwer_publishing' }
      });
      if (res && res.ok) {
        const data = await res.json();
        setMatrixHealth(data.report || null);
        alert('Validation audit completed. Health grades updated.');
      } else {
        alert('Failed to execute matrix audit.');
      }
    } catch (e) {
      alert(`Audit error: ${e.message}`);
    } finally {
      setIsAuditing(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    fetchHealth();
  }, [backendUrl]);

  const handleBroadcast = async () => {
    setIsBroadcasting(true);
    setBroadcastResults(null);
    try {
      const categoriesPayload = selectedBroadcastTier === 'all' ? ['all'] : [selectedBroadcastTier];
      const activeUrls = campaignMode === 'single' 
        ? [targetUrl] 
        : (CAMPAIGN_PRESETS[campaignMode]?.urls || [targetUrl]);

      const res = await fetchWithFallback('/api/syndication/broadcast', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({
          site_name: siteName,
          target_url: targetUrl,
          feed_url: feedUrl,
          custom_message: customMsg,
          categories: categoriesPayload,
          only_active: smartSkipDeadNodes,
          urls: activeUrls,
          channels: channels
        })
      });
      if (res && res.ok) {
        const data = await res.json();
        setBroadcastResults(data);
        fetchHistory();
      } else {
        alert('Broadcast failed or backend is offline. Verify FastAPI is running on Port 8080.');
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    } finally {
      setIsBroadcasting(false);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleChannel = (key) => {
    setChannels(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const filteredPresets = selectedCategory === 'all' 
    ? adPresets 
    : adPresets.filter(p => p.category === selectedCategory);

  const displayResults = broadcastResults?.results?.filter(r => {
    const matchesTier = resultsFilter === 'all' || r.category === resultsFilter;
    const matchesSearch = !nodeSearchQuery || r.target.toLowerCase().includes(nodeSearchQuery.toLowerCase()) || r.type.toLowerCase().includes(nodeSearchQuery.toLowerCase());
    return matchesTier && matchesSearch;
  }) || [];

  return (
    <div style={{
      padding: '24px',
      color: '#e6edf3',
      height: '100%',
      overflowY: 'auto',
      background: '#090d16',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        borderBottom: '1px solid #30363d',
        paddingBottom: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ margin: 0, fontSize: '22px', fontWeight: '800', color: '#38bdf8' }}>
              🌐 Omni-Channel Automated Broadcast & Campaign Matrix
            </h1>
            <span style={{
              background: '#0284c7',
              color: '#fff',
              fontSize: '11px',
              fontWeight: '700',
              padding: '2px 8px',
              borderRadius: '12px'
            }}>
              v5.147.0 SOVEREIGN
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#8b949e' }}>
            Search Engine Fleets, Community Webhooks, Bluesky/Fediverse Open APIs, Local XML Engine & Multi-Channel Copy Hub
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={handleRunAudit}
            disabled={isAuditing}
            style={{
              background: isAuditing ? '#374151' : '#059669',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: isAuditing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {isAuditing ? '🩺 Auditing Fleet...' : '🩺 Run Matrix Audit'}
          </button>

          <button
            onClick={() => { fetchHistory(); fetchHealth(); }}
            style={{
              background: '#21262d',
              color: '#c9d1d9',
              border: '1px solid #30363d',
              borderRadius: '6px',
              padding: '7px 14px',
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            🔄 Refresh Logs
          </button>
        </div>
      </div>

      {/* Fleet Telemetry HUD */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '12px',
        marginBottom: '20px'
      }}>
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Fleet Scope</div>
          <div style={{ fontSize: '20px', fontWeight: '800', color: '#38bdf8', marginTop: '2px' }}>
            35 Targets & Hubs
          </div>
          <div style={{ fontSize: '11px', color: '#10b981', marginTop: '4px' }}>
            ● 18 Active Live • 8 Standby
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Direct Community & Social</div>
          <div style={{ fontSize: '20px', fontWeight: '800', color: '#00f0ff', marginTop: '2px' }}>
            5 Channels
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>
            Discord, Telegram, Bluesky, Mastodon, RSS
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Search Engine Fleet</div>
          <div style={{ fontSize: '20px', fontWeight: '800', color: '#10b981', marginTop: '2px' }}>
            7 IndexNow Nodes
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>
            Bing, Yandex, Naver, Seznam, Yep, Amazon
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Global Weblog Pings</div>
          <div style={{ fontSize: '20px', fontWeight: '800', color: '#f59e0b', marginTop: '2px' }}>
            12 XML-RPC Hubs
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>
            Twingly, Blo.gs, FC2, Ping-O-Matic
          </div>
        </div>
      </div>

      {/* Main Grid: Broadcaster + Ad Copy Hub */}
      <div className="responsive-grid-2col">
        {/* Left Column: Broadcaster Engine */}
        <div style={{
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '20px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: '700', color: '#f0f6fc' }}>
              ⚡ 1-Click Omni-Channel Broadcast Engine
            </h2>
            <span style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '2px 8px', borderRadius: '4px' }}>
              ● 35 Active Endpoints & Hubs
            </span>
          </div>

          {/* Campaign Multiplexer Selector */}
          <div style={{ marginBottom: '16px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', padding: '12px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#38bdf8', marginBottom: '8px' }}>
              🚀 Campaign Scope Multiplexer:
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {Object.entries(CAMPAIGN_PRESETS).map(([key, preset]) => (
                <button
                  key={key}
                  onClick={() => setCampaignMode(key)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: campaignMode === key ? '2px solid #00f0ff' : '1px solid #30363d',
                    background: campaignMode === key ? 'rgba(0, 240, 255, 0.15)' : '#161b22',
                    color: campaignMode === key ? '#00f0ff' : '#c9d1d9',
                    fontSize: '12px',
                    fontWeight: campaignMode === key ? '700' : '500',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  <div style={{ fontWeight: '700' }}>{preset.name}</div>
                  <div style={{ fontSize: '10px', color: '#8b949e', marginTop: '2px' }}>{preset.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Social & Community Channels Toggles */}
          <div style={{ marginBottom: '16px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', padding: '12px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#00f0ff', marginBottom: '8px' }}>
              📢 Automated Outbound Social & Community Channels:
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {[
                { id: 'discord', label: 'Discord Webhook' },
                { id: 'telegram', label: 'Telegram Bot' },
                { id: 'bluesky', label: 'Bluesky (AT Protocol)' },
                { id: 'mastodon', label: 'Mastodon / Fediverse' },
                { id: 'sitemap', label: 'Dynamic Sitemap & RSS' }
              ].map(ch => (
                <button
                  key={ch.id}
                  onClick={() => toggleChannel(ch.id)}
                  style={{
                    padding: '5px 10px',
                    borderRadius: '16px',
                    border: '1px solid',
                    borderColor: channels[ch.id] ? '#10b981' : '#4b5563',
                    background: channels[ch.id] ? 'rgba(16,185,129,0.15)' : 'transparent',
                    color: channels[ch.id] ? '#34d399' : '#9ca3af',
                    fontSize: '11px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  {channels[ch.id] ? '🟢' : '⚪'} {ch.label}
                </button>
              ))}
            </div>
          </div>

          {/* Broadcast Form Inputs */}
          <div style={{ display: 'grid', gap: '12px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>Brand / Entity Name</label>
              <input
                type="text"
                value={siteName}
                onChange={e => setSiteName(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  borderRadius: '6px',
                  color: '#f0f6fc',
                  padding: '8px 12px',
                  fontSize: '13px',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>Target Landing URL</label>
              <input
                type="text"
                value={targetUrl}
                onChange={e => setTargetUrl(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  borderRadius: '6px',
                  color: '#f0f6fc',
                  padding: '8px 12px',
                  fontSize: '13px',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>Advertisement / Custom Message</label>
              <textarea
                value={customMsg}
                onChange={e => setCustomMsg(e.target.value)}
                placeholder="What do you want to advertise? (This text is sent to Discord, Telegram, Bluesky, Mastodon...)"
                rows={3}
                style={{
                  width: '100%',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  borderRadius: '6px',
                  color: '#f0f6fc',
                  padding: '8px 12px',
                  fontSize: '13px',
                  boxSizing: 'border-box',
                  resize: 'vertical'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>Catalog / Feed URL</label>
              <input
                type="text"
                value={feedUrl}
                onChange={e => setFeedUrl(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  borderRadius: '6px',
                  color: '#f0f6fc',
                  padding: '8px 12px',
                  fontSize: '13px',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            {/* Quick Presets */}
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '11px', color: '#8b949e', alignSelf: 'center' }}>Fast Snippet Copy:</span>
              {[
                { label: 'Home Page', url: 'https://stehouwer-publishing.com' },
                { label: 'Library Catalog', url: 'https://stehouwer-publishing.com/library' },
                { label: 'Marketing Hub', url: 'https://stehouwer-publishing.com/marketing.html' },
                { label: 'Amazon Book', url: 'https://www.amazon.com/dp/B0H524NPXV' },
                { label: 'IMDb Profile', url: 'https://www.imdb.com/name/nm12567135/' }
              ].map(snip => (
                <button
                  key={snip.label}
                  onClick={() => {
                    setTargetUrl(snip.url);
                    setCustomMsg(snip.url);
                  }}
                  style={{
                    background: '#21262d',
                    color: '#38bdf8',
                    border: '1px solid #30363d',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    fontSize: '11px',
                    cursor: 'pointer'
                  }}
                >
                  {snip.label}
                </button>
              ))}
            </div>
          </div>

          {/* Smart DNS Filter Switch */}
          <div style={{
            background: 'rgba(56, 189, 248, 0.08)',
            border: '1px solid rgba(56, 189, 248, 0.2)',
            borderRadius: '6px',
            padding: '10px 12px',
            marginBottom: '16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <div style={{ fontSize: '12px', fontWeight: '700', color: '#38bdf8' }}>
                🛡️ Smart Active Routing (Skip 9 Dead/Discontinued DNS Nodes)
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e' }}>
                Prevents slow DNS lookup timeouts on vintage 2000s WordPress directories.
              </div>
            </div>
            <input
              type="checkbox"
              checked={smartSkipDeadNodes}
              onChange={e => setSmartSkipDeadNodes(e.target.checked)}
              style={{ width: '18px', height: '18px', cursor: 'pointer' }}
            />
          </div>

          {/* Fire Broadcast Button */}
          <button
            onClick={handleBroadcast}
            disabled={isBroadcasting}
            style={{
              width: '100%',
              background: isBroadcasting ? '#374151' : 'linear-gradient(135deg, #0284c7, #0369a1)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '12px',
              fontSize: '14px',
              fontWeight: '700',
              cursor: isBroadcasting ? 'not-allowed' : 'pointer',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
            }}
          >
            {isBroadcasting ? '🚀 Multiplexing Omni-Channel Broadcast...' : `🔥 FIRE SEND (${campaignMode === 'single' ? '1 URL' : `${CAMPAIGN_PRESETS[campaignMode]?.urls.length} URLs Multiplexed`} + Channels)`}
          </button>

          {/* Results Console */}
          {broadcastResults && (
            <div style={{
              marginTop: '16px',
              background: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              padding: '14px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '13px', fontWeight: '700', color: '#38bdf8' }}>
                  📊 Broadcast Results ({broadcastResults.successful_targets} / {broadcastResults.total_targets} Succeeded)
                </span>
                <span style={{ fontSize: '11px', color: '#8b949e' }}>
                  {broadcastResults.formatted_time}
                </span>
              </div>

              {/* Protocol Filters */}
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '10px' }}>
                {['all', 'social', 'indexnow', 'xmlrpc', 'websub', 'local'].map(f => (
                  <button
                    key={f}
                    onClick={() => setResultsFilter(f)}
                    style={{
                      padding: '3px 8px',
                      borderRadius: '4px',
                      border: 'none',
                      background: resultsFilter === f ? '#38bdf8' : '#21262d',
                      color: resultsFilter === f ? '#000' : '#8b949e',
                      fontSize: '10px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      textTransform: 'uppercase'
                    }}
                  >
                    {f}
                  </button>
                ))}
              </div>

              <div style={{ maxHeight: '240px', overflowY: 'auto', display: 'grid', gap: '6px' }}>
                {displayResults.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      background: '#161b22',
                      padding: '8px 12px',
                      borderRadius: '4px',
                      borderLeft: `3px solid ${
                        r.status === 'SUCCESS' || r.status === 'POSTED' || r.status === 'SYNCED' ? '#10b981' : 
                        r.status === 'STANDBY' ? '#38bdf8' :
                        r.status.startsWith('HTTP 2') ? '#10b981' :
                        r.status.startsWith('HTTP 4') ? '#f59e0b' : '#ef4444'
                      }`
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: '#f0f6fc' }}>{r.target}</div>
                      <div style={{ fontSize: '10px', color: '#8b949e' }}>
                        ({r.type}) {r.details ? `• ${r.details}` : ''}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: '700',
                        color: r.status === 'SUCCESS' || r.status === 'POSTED' || r.status === 'SYNCED' ? '#10b981' : 
                               r.status === 'STANDBY' ? '#38bdf8' :
                               r.status.startsWith('HTTP 2') ? '#10b981' :
                               r.status.startsWith('HTTP 4') ? '#f59e0b' : '#ef4444'
                      }}>
                        {r.status}
                      </span>
                      <div style={{ fontSize: '10px', color: '#6e7681' }}>{r.latency_ms}ms</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: High-Converting Ad Copy Hub */}
        <div style={{
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '20px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: '700', color: '#f0f6fc' }}>
              📢 High-Converting Ad Copy Hub
            </h2>
            <div style={{ display: 'flex', gap: '4px' }}>
              {['all', 'stream', 'music', 'film', 'social'].map(cat => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  style={{
                    background: selectedCategory === cat ? '#0284c7' : '#21262d',
                    color: selectedCategory === cat ? '#fff' : '#8b949e',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    fontSize: '11px',
                    cursor: 'pointer',
                    textTransform: 'capitalize'
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <p style={{ fontSize: '12px', color: '#8b949e', marginTop: 0, marginBottom: '16px' }}>
            Pre-formatted, platform-tailored ad copy for manual copy-pasting into chat rooms, forums, and social posts.
          </p>

          <div style={{ display: 'grid', gap: '12px' }}>
            {filteredPresets.map(preset => (
              <div
                key={preset.id}
                style={{
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  borderRadius: '6px',
                  padding: '12px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div>
                    <span style={{ fontSize: '12px', fontWeight: '700', color: '#f0f6fc' }}>{preset.title}</span>
                    <div style={{ fontSize: '10px', color: '#8b949e' }}>🎯 Targets: {preset.target}</div>
                  </div>
                  <button
                    onClick={() => copyToClipboard(preset.text, preset.id)}
                    style={{
                      background: copiedId === preset.id ? '#10b981' : '#21262d',
                      color: copiedId === preset.id ? '#fff' : '#c9d1d9',
                      border: '1px solid #30363d',
                      borderRadius: '4px',
                      padding: '4px 10px',
                      fontSize: '11px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    {copiedId === preset.id ? '✓ COPIED' : '📋 COPY'}
                  </button>
                </div>
                <div style={{
                  background: '#161b22',
                  padding: '8px 10px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  color: '#e6edf3',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily: 'monospace'
                }}>
                  {preset.text}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Historical Dispatch Logs */}
      <div style={{
        background: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        padding: '20px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <h2 style={{ margin: 0, fontSize: '16px', fontWeight: '700', color: '#f0f6fc' }}>
            📜 Broadcast Lineage & Telemetry Logs
          </h2>
          <span style={{ fontSize: '12px', color: '#8b949e' }}>
            Showing last {history.length} dispatches
          </span>
        </div>

        {history.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px', color: '#8b949e', fontSize: '13px' }}>
            No broadcasts recorded yet. Click "FIRE SEND" above to launch your first syndication wave.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                  <th style={{ padding: '8px 12px' }}>Time</th>
                  <th style={{ padding: '8px 12px' }}>Target URL</th>
                  <th style={{ padding: '8px 12px' }}>Message / Entity</th>
                  <th style={{ padding: '8px 12px' }}>Success Rate</th>
                  <th style={{ padding: '8px 12px' }}>Endpoints Contacted</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '8px 12px', color: '#c9d1d9', whiteSpace: 'nowrap' }}>{item.formatted_time}</td>
                    <td style={{ padding: '8px 12px', color: '#38bdf8' }}>
                      <a href={item.target_url} target="_blank" rel="noreferrer" style={{ color: '#38bdf8', textDecoration: 'none' }}>
                        {item.target_url}
                      </a>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#e6edf3' }}>{item.custom_message || item.site_name}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{
                        background: item.successful_targets > 0 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: item.successful_targets > 0 ? '#10b981' : '#ef4444',
                        padding: '2px 8px',
                        borderRadius: '10px',
                        fontWeight: '600'
                      }}>
                        {item.successful_targets} / {item.total_targets} Succeeded
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#8b949e', fontSize: '11px' }}>
                      {item.results ? item.results.map(r => r.target).slice(0, 4).join(', ') + (item.results.length > 4 ? '...' : '') : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 1-Click Social Intents */}
      <div style={{
        background: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        padding: '20px',
        marginTop: '20px'
      }}>
        <div style={{ marginBottom: '14px' }}>
          <h2 style={{ margin: 0, fontSize: '16px', fontWeight: '700', color: '#f0f6fc' }}>
            ⚡ 1-Click Social & Community Outreach
          </h2>
          <p style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px', marginBottom: 0 }}>
            Bypass API restrictions. Click to open pre-filled native share intents for the active Target URL.
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '10px' }}>
          {[
            { name: 'Reddit', icon: 'r/', url: `https://www.reddit.com/submit?url=${encodeURIComponent(targetUrl)}&title=${encodeURIComponent(siteName)}`, color: '#ff4500' },
            { name: 'X / Twitter', icon: '𝕏', url: `https://twitter.com/intent/tweet?url=${encodeURIComponent(targetUrl)}&text=${encodeURIComponent(siteName)}`, color: '#1da1f2' },
            { name: 'LinkedIn', icon: 'in', url: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(targetUrl)}`, color: '#0a66c2' },
            { name: 'Facebook', icon: 'f', url: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(targetUrl)}`, color: '#1877f2' },
            { name: 'Hacker News', icon: 'Y', url: `https://news.ycombinator.com/submitlink?u=${encodeURIComponent(targetUrl)}&t=${encodeURIComponent(siteName)}`, color: '#ff6600' },
            { name: 'Pinterest', icon: 'P', url: `https://pinterest.com/pin/create/button/?url=${encodeURIComponent(targetUrl)}&description=${encodeURIComponent(siteName)}`, color: '#bd081c' },
            { name: 'Tumblr', icon: 't', url: `https://www.tumblr.com/widgets/share/tool?canonicalUrl=${encodeURIComponent(targetUrl)}&title=${encodeURIComponent(siteName)}`, color: '#35465c' },
            { name: 'Telegram', icon: '✈', url: `https://t.me/share/url?url=${encodeURIComponent(targetUrl)}&text=${encodeURIComponent(siteName)}`, color: '#0088cc' },
            { name: 'WhatsApp', icon: '💬', url: `https://api.whatsapp.com/send?text=${encodeURIComponent(siteName)}%20${encodeURIComponent(targetUrl)}`, color: '#25d366' }
          ].map(intent => (
            <a
              key={intent.name}
              href={intent.url}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: '#21262d',
                border: '1px solid #30363d',
                borderRadius: '6px',
                padding: '10px 12px',
                color: '#c9d1d9',
                textDecoration: 'none',
                fontSize: '13px',
                fontWeight: '600',
                transition: 'background 0.2s ease'
              }}
              onMouseOver={e => e.currentTarget.style.background = '#30363d'}
              onMouseOut={e => e.currentTarget.style.background = '#21262d'}
            >
              <span style={{ color: intent.color, width: '20px', textAlign: 'center', fontSize: '16px', fontWeight: 'bold' }}>{intent.icon}</span>
              {intent.name}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}






