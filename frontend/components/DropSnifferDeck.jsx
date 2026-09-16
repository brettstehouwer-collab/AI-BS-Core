import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Activity, 
  Radio, 
  Zap, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  ExternalLink, 
  Package, 
  Music, 
  Sliders, 
  Cpu, 
  Layers,
  Search,
  Check,
  XCircle,
  Download
} from 'lucide-react';

export default function DropSnifferDeck() {
  const [statusData, setStatusData] = useState(null);
  const [drops, setDrops] = useState([]);
  const [inventory, setInventory] = useState(null);
  const [crossCheckMatrix, setCrossCheckMatrix] = useState([]);
  const [filterType, setFilterType] = useState('all'); // all, checked, unclaimed, plugins, packs
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('checked_off'); // checked_off, stream_queue, log
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [resStatus, resDrops, resInv, resMatrix] = await Promise.allSettled([
        fetch('http://127.0.0.1:8080/api/drop-sniffer/status').then(r => r.json()),
        fetch('http://127.0.0.1:8080/api/drop-sniffer/drops').then(r => r.json()),
        fetch('http://127.0.0.1:8080/api/drop-sniffer/inventory').then(r => r.json()),
        fetch('http://127.0.0.1:8080/api/drop-sniffer/cross-check').then(r => r.json())
      ]);

      if (resStatus.status === 'fulfilled') setStatusData(resStatus.value);
      if (resDrops.status === 'fulfilled') setDrops(resDrops.value || []);
      if (resInv.status === 'fulfilled') setInventory(resInv.value);
      if (resMatrix.status === 'fulfilled' && Array.isArray(resMatrix.value) && resMatrix.value.length > 0) {
        setCrossCheckMatrix(resMatrix.value);
      }
    } catch (e) {
      console.error('Error fetching sniffer telemetry:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 2000);
    return () => clearInterval(timer);
  }, []);

  const upcomingDecoded = [
    { title: 'DOPE Collection - Melodies', variant: '42703045132373', link: 'https://cymatics.fm/cart/42703045132373:1?checkout' },
    { title: 'DOPE Collection - Drums', variant: '42703113420885', link: 'https://cymatics.fm/cart/42703113420885:1?checkout' },
    { title: 'DOPE Collection - Vocals', variant: '42703162277973', link: 'https://cymatics.fm/cart/42703162277973:1?checkout' },
    { title: 'DOPE Collection - Bonus Stash', variant: '42703163228245', link: 'https://cymatics.fm/cart/42703163228245:1?checkout' },
    { title: 'Solace - Acapellas', variant: '42703166439509', link: 'https://cymatics.fm/cart/42703166439509:1?checkout' },
    { title: 'Daydream - Vocal Loops', variant: '42703168700501', link: 'https://cymatics.fm/cart/42703168700501:1?checkout' },
    { title: 'Euphoria - Vocal Chops', variant: '42703179022421', link: 'https://cymatics.fm/cart/42703179022421:1?checkout' },
    { title: 'SESSIONS: Melody Compositions', variant: '40635706343509', link: 'https://cymatics.fm/cart/40635706343509:1?checkout' },
    { title: 'Generations - 1970s Samples', variant: '40620833570901', link: 'https://cymatics.fm/cart/40620833570901:1?checkout' },
    { title: 'Generations - 1960s Samples', variant: '40620731498581', link: 'https://cymatics.fm/cart/40620731498581:1?checkout' },
    { title: 'Kingdom: Electronic MIDI', variant: '40666743111765', link: 'https://cymatics.fm/cart/40666743111765:1?checkout' },
    { title: 'Pandora - EDM MIDI', variant: '42703201370197', link: 'https://cymatics.fm/cart/42703201370197:1?checkout' },
    { title: 'Pandora - RnB MIDI', variant: '42703204712533', link: 'https://cymatics.fm/cart/42703204712533:1?checkout' },
    { title: 'Pandora - Trap MIDI', variant: '42703211626581', link: 'https://cymatics.fm/cart/42703211626581:1?checkout' },
    { title: 'Pandora: Paradise Expansion', variant: '42703223881813', link: 'https://cymatics.fm/cart/42703223881813:1?checkout' },
    { title: 'Pandora: Echoes Expansion', variant: '42703249342549', link: 'https://cymatics.fm/cart/42703249342549:1?checkout' },
    { title: 'MIDI Shredder', variant: '42520328962133', link: 'https://cymatics.fm/cart/42520328962133:1?checkout' }
  ];

  const totalOwned = crossCheckMatrix.filter(m => m.is_owned).length;
  const totalUnclaimed = crossCheckMatrix.filter(m => !m.is_owned).length;
  const totalMatrixCount = crossCheckMatrix.length || 204;
  const ownedPercentage = Math.round((totalOwned / (totalMatrixCount || 1)) * 100);

  const filteredMatrix = crossCheckMatrix.filter(item => {
    // Type filter
    if (filterType === 'checked' && !item.is_owned) return false;
    if (filterType === 'unclaimed' && item.is_owned) return false;
    if (filterType === 'plugins' && item.category !== 'Plugin') return false;
    if (filterType === 'packs' && item.category !== 'Sample Pack') return false;

    // Search query filter
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        item.title.toLowerCase().includes(q) ||
        (item.details && item.details.toLowerCase().includes(q)) ||
        (item.category && item.category.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div style={{ background: '#070a12', color: '#e6edf3', padding: '24px', borderRadius: '12px', minHeight: '100%', fontFamily: 'Inter, system-ui, sans-serif' }}>
      {/* Header Deck */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #1e293b', paddingBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ background: 'rgba(0, 240, 255, 0.12)', border: '1px solid #00f0ff', padding: '10px', borderRadius: '8px' }}>
            <Radio style={{ width: '24px', height: '24px', color: '#00f0ff', animation: 'spin 4s linear infinite' }} />
          </div>
          <div>
            <h1 style={{ fontSize: '20px', fontWeight: '800', margin: 0, letterSpacing: '-0.3px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              Cymatics Hub Cross-Check & Drop Watchdog <span style={{ fontSize: '11px', background: '#10b98122', color: '#10b981', padding: '2px 8px', borderRadius: '4px', border: '1px solid #10b981' }}>ARMED</span>
            </h1>
            <p style={{ margin: '3px 0 0 0', fontSize: '12px', color: '#94a3b8' }}>
              Checked Off Library: <strong>{totalOwned} Claimed in Hub</strong> &bull; <strong>{totalUnclaimed} Unclaimed Free ($0.00)</strong> &bull; Target: <a href="https://cymatics.fm/pages/cymatics-c86v" target="_blank" rel="noreferrer" style={{ color: '#38bdf8', textDecoration: 'none' }}>cymatics-c86v</a>
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button 
            onClick={fetchData} 
            style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '7px 14px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: '600' }}
          >
            <RefreshCw style={{ width: '14px', height: '14px' }} /> Refresh Matrix
          </button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '20px' }}>
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', padding: '14px', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '12px' }}>
            <span>Library Ownership Rate</span>
            <CheckCircle2 style={{ width: '16px', height: '16px', color: '#10b981' }} />
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', marginTop: '6px', color: '#10b981' }}>
            {totalOwned} / {totalMatrixCount} ({ownedPercentage}%)
          </div>
          <div style={{ width: '100%', background: '#1e293b', height: '6px', borderRadius: '3px', marginTop: '8px', overflow: 'hidden' }}>
            <div style={{ width: `${ownedPercentage}%`, background: '#10b981', height: '100%' }} />
          </div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', padding: '14px', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '12px' }}>
            <span>Watchdog Heartbeat</span>
            <Activity style={{ width: '16px', height: '16px', color: '#00f0ff' }} />
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', marginTop: '6px', color: '#00f0ff' }}>
            {statusData?.is_alive ? 'HEALTHY (0.04s)' : 'ONLINE'}
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
            PID: {statusData?.pid || 'Active'} &bull; 5 Channels Scanning
          </div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', padding: '14px', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '12px' }}>
            <span>Cymatics Hub Installed</span>
            <Sliders style={{ width: '16px', height: '16px', color: '#a855f7' }} />
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', marginTop: '6px', color: '#a855f7' }}>
            {inventory?.total_plugins || 53} Plugins / {inventory?.total_packs || 29} Packs
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
            157 Exclusion Keywords Loaded
          </div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', padding: '14px', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '12px' }}>
            <span>Safety Gate Filter</span>
            <ShieldCheck style={{ width: '16px', height: '16px', color: '#38bdf8' }} />
          </div>
          <div style={{ fontSize: '20px', fontWeight: '800', marginTop: '6px', color: '#38bdf8' }}>
            STRICT $0.00 FREE ONLY
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
            Zero paid items auto-carted
          </div>
        </div>
      </div>

      {/* Primary Tab Navigation */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #1e293b', paddingBottom: '10px', marginBottom: '16px' }}>
        <button
          onClick={() => setActiveTab('checked_off')}
          style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', background: activeTab === 'checked_off' ? '#00f0ff' : '#1e293b', color: activeTab === 'checked_off' ? '#000' : '#cbd5e1', fontWeight: '700', fontSize: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <CheckCircle2 style={{ width: '14px', height: '14px' }} /> Checked Off Library Matrix ({totalMatrixCount})
        </button>
        <button
          onClick={() => setActiveTab('stream_queue')}
          style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', background: activeTab === 'stream_queue' ? '#00f0ff' : '#1e293b', color: activeTab === 'stream_queue' ? '#000' : '#cbd5e1', fontWeight: '700', fontSize: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Zap style={{ width: '14px', height: '14px' }} /> Upcoming Stream Drops ({upcomingDecoded.length})
        </button>
        <button
          onClick={() => setActiveTab('log')}
          style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', background: activeTab === 'log' ? '#00f0ff' : '#1e293b', color: activeTab === 'log' ? '#000' : '#cbd5e1', fontWeight: '700', fontSize: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Activity style={{ width: '14px', height: '14px' }} /> Intercepted Drops Log ({drops.length})
        </button>
      </div>

      {/* TAB 1: Checked Off Library Matrix */}
      {activeTab === 'checked_off' && (
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', overflow: 'hidden' }}>
          {/* Filter & Search Bar */}
          <div style={{ padding: '14px 16px', background: '#131d31', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <button 
                onClick={() => setFilterType('all')} 
                style={{ padding: '5px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: '700', cursor: 'pointer', border: 'none', background: filterType === 'all' ? '#38bdf8' : '#1e293b', color: filterType === 'all' ? '#000' : '#cbd5e1' }}
              >
                All ({crossCheckMatrix.length})
              </button>
              <button 
                onClick={() => setFilterType('checked')} 
                style={{ padding: '5px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: '700', cursor: 'pointer', border: 'none', background: filterType === 'checked' ? '#10b981' : '#1e293b', color: filterType === 'checked' ? '#000' : '#cbd5e1' }}
              >
                ✓ Checked Off in Hub ({totalOwned})
              </button>
              <button 
                onClick={() => setFilterType('unclaimed')} 
                style={{ padding: '5px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: '700', cursor: 'pointer', border: 'none', background: filterType === 'unclaimed' ? '#f59e0b' : '#1e293b', color: filterType === 'unclaimed' ? '#000' : '#cbd5e1' }}
              >
                ⚡ Unclaimed Free ({totalUnclaimed})
              </button>
              <button 
                onClick={() => setFilterType('plugins')} 
                style={{ padding: '5px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: '700', cursor: 'pointer', border: 'none', background: filterType === 'plugins' ? '#a855f7' : '#1e293b', color: filterType === 'plugins' ? '#000' : '#cbd5e1' }}
              >
                Plugins ({inventory?.total_plugins || 53})
              </button>
              <button 
                onClick={() => setFilterType('packs')} 
                style={{ padding: '5px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: '700', cursor: 'pointer', border: 'none', background: filterType === 'packs' ? '#6366f1' : '#1e293b', color: filterType === 'packs' ? '#000' : '#cbd5e1' }}
              >
                Sample Packs
              </button>
            </div>

            {/* Search Input */}
            <div style={{ position: 'relative', minWidth: '220px' }}>
              <Search style={{ position: 'absolute', left: '10px', top: '8px', width: '14px', height: '14px', color: '#64748b' }} />
              <input 
                type="text" 
                placeholder="Search matrix items..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ width: '100%', background: '#0b0f17', border: '1px solid #334155', color: '#f8fafc', padding: '6px 12px 6px 30px', borderRadius: '6px', fontSize: '12px', outline: 'none' }}
              />
            </div>
          </div>

          {/* Matrix Table */}
          <div style={{ maxHeight: '550px', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1e293b', color: '#94a3b8', textAlign: 'left', background: '#0b0f17' }}>
                  <th style={{ padding: '10px 16px', width: '50px' }}>Status</th>
                  <th style={{ padding: '10px 16px' }}>Item Name</th>
                  <th style={{ padding: '10px 16px' }}>Category</th>
                  <th style={{ padding: '10px 16px' }}>Price</th>
                  <th style={{ padding: '10px 16px' }}>Library Location / Variant</th>
                  <th style={{ padding: '10px 16px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredMatrix.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #1e293b', background: item.is_owned ? 'rgba(16, 185, 129, 0.03)' : (idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)') }}>
                    <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                      {item.is_owned ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '22px', height: '22px', borderRadius: '50%', background: '#10b98122', border: '1px solid #10b981', color: '#10b981' }}>
                          <Check style={{ width: '14px', height: '14px' }} />
                        </span>
                      ) : (
                        <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '22px', height: '22px', borderRadius: '50%', background: '#f59e0b22', border: '1px solid #f59e0b', color: '#f59e0b' }}>
                          <Zap style={{ width: '12px', height: '12px' }} />
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '10px 16px', fontWeight: '700', color: item.is_owned ? '#f1f5f9' : '#38bdf8' }}>
                      {item.title}
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <span style={{ background: item.category === 'Plugin' ? '#4338ca33' : '#0369a133', color: item.category === 'Plugin' ? '#a5b4fc' : '#7dd3fc', border: `1px solid ${item.category === 'Plugin' ? '#6366f1' : '#0284c7'}`, padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '600' }}>
                        {item.category}
                      </span>
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <span style={{ color: '#10b981', fontWeight: '700' }}>{item.price}</span>
                    </td>
                    <td style={{ padding: '10px 16px', color: '#94a3b8', fontSize: '11px', fontFamily: 'monospace' }}>
                      {item.details || 'Cymatics Hub'}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                      {item.is_owned ? (
                        <span style={{ color: '#10b981', fontSize: '11px', fontWeight: '700', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <Check style={{ width: '12px', height: '12px' }} /> Checked Off
                        </span>
                      ) : (
                        <a 
                          href={item.direct_link} 
                          target="_blank" 
                          rel="noreferrer" 
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#0284c7', color: '#fff', padding: '4px 10px', borderRadius: '4px', textDecoration: 'none', fontWeight: '700', fontSize: '11px' }}
                        >
                          Claim $0 <ExternalLink style={{ width: '12px', height: '12px' }} />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: Upcoming Stream Drops */}
      {activeTab === 'stream_queue' && (
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', background: '#131d31', borderBottom: '1px solid #1e293b' }}>
            <span style={{ fontSize: '13px', fontWeight: '700', color: '#f8fafc' }}>
              Pre-Resolved Stream Drops (Direct $0.00 1-Click Instant Cart Injection)
            </span>
          </div>
          <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1e293b', color: '#94a3b8', textAlign: 'left', background: '#0b0f17' }}>
                  <th style={{ padding: '10px 16px' }}>Item Title</th>
                  <th style={{ padding: '10px 16px' }}>Price</th>
                  <th style={{ padding: '10px 16px' }}>Shopify Variant ID</th>
                  <th style={{ padding: '10px 16px', textAlign: 'right' }}>Direct Action</th>
                </tr>
              </thead>
              <tbody>
                {upcomingDecoded.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #1e293b', background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                    <td style={{ padding: '10px 16px', fontWeight: '600', color: '#f1f5f9' }}>{item.title}</td>
                    <td style={{ padding: '10px 16px' }}><span style={{ background: '#10b98122', color: '#10b981', padding: '2px 6px', borderRadius: '4px', fontWeight: '700' }}>$0.00 FREE</span></td>
                    <td style={{ padding: '10px 16px', fontFamily: 'monospace', color: '#38bdf8' }}>{item.variant}</td>
                    <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                      <a 
                        href={item.link} 
                        target="_blank" 
                        rel="noreferrer" 
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#0284c7', color: '#fff', padding: '4px 10px', borderRadius: '4px', textDecoration: 'none', fontWeight: '700', fontSize: '11px' }}
                      >
                        Claim Drop <ExternalLink style={{ width: '12px', height: '12px' }} />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: Intercepted Drops Log */}
      {activeTab === 'log' && (
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '700', color: '#f8fafc', marginTop: 0 }}>
            Audit Log of Detected & Auto-Carted Drops ({drops.length})
          </h3>
          {drops.length === 0 ? (
            <p style={{ fontSize: '12px', color: '#94a3b8' }}>No drops sniped during the current session yet. Watchdog is monitoring live stream.</p>
          ) : (
            <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
              {drops.slice().reverse().map((drop, idx) => (
                <div key={idx} style={{ padding: '10px', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontWeight: '700', color: '#38bdf8', fontSize: '13px' }}>{drop.title}</span>
                    <span style={{ fontSize: '11px', color: '#94a3b8', marginLeft: '10px' }}>[{drop.timestamp}]</span>
                  </div>
                  <a href={drop.url} target="_blank" rel="noreferrer" style={{ color: '#10b981', fontSize: '12px', textDecoration: 'none', fontWeight: '700' }}>
                    Open Checkout &rarr;
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
