import React, { useState, useEffect } from 'react';
import { Play, Gamepad2, HardDrive, RefreshCw, Cpu, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function SteamGamingHubTab({ backendUrl = 'http://127.0.0.1:8080' }) {
  const [games, setGames] = useState([]);
  const [runningGames, setRunningGames] = useState([]);
  const [gameModeActive, setGameModeActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [launchingAppId, setLaunchingAppId] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');

  const fetchLibrary = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${backendUrl}/api/v1/steam/library`);
      if (res.ok) {
        const data = await res.json();
        setGames(data.games || []);
        setRunningGames(data.running_games || []);
        setGameModeActive(data.game_mode_active || false);
      }
    } catch (e) {
      console.error('Failed to load Steam library:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLibrary();
    const interval = setInterval(fetchLibrary, 15000);
    return () => clearInterval(interval);
  }, [backendUrl]);

  const handleLaunchGame = async (game) => {
    setLaunchingAppId(game.appid);
    setStatusMessage(`Activating Game Mode & Launching ${game.name}...`);
    try {
      const res = await fetch(`${backendUrl}/api/v1/steam/launch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          appid: game.appid,
          game_name: game.name,
          enable_game_mode: true
        })
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(`🎮 ${game.name} launched! Ollama VRAM yielded for 100% RTX 4090 GPU execution.`);
        setTimeout(fetchLibrary, 3000);
      } else {
        setStatusMessage(`Failed to launch: ${res.statusText}`);
      }
    } catch (e) {
      setStatusMessage(`Launch error: ${e.message}`);
    } finally {
      setLaunchingAppId(null);
    }
  };

  const totalDiskGb = games.reduce((acc, g) => acc + (g.size_gb || 0), 0).toFixed(1);

  return (
    <div style={{
      padding: '24px',
      background: 'radial-gradient(circle at top right, #171c26 0%, #0d1117 100%)',
      minHeight: '100%',
      color: '#e6edf3',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* Header Banner */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px',
        background: 'rgba(22, 27, 34, 0.8)',
        border: '1px solid #30363d',
        borderRadius: '12px',
        marginBottom: '24px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
        backdropFilter: 'blur(8px)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #1b2838 0%, #2a475e 100%)',
            padding: '14px',
            borderRadius: '10px',
            border: '1px solid #66c0f4',
            boxShadow: '0 0 15px rgba(102, 192, 244, 0.3)'
          }}>
            <Gamepad2 size={32} color="#66c0f4" />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 800, letterSpacing: '0.5px', color: '#ffffff' }}>
              Steam Gaming Hub & Native Launcher
            </h1>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#8b949e' }}>
              Autonomous Hardware Governor • Direct ACF Manifest Bridge • Zero-Cost Native Gaming
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={fetchLibrary}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: '#21262d',
              border: '1px solid #30363d',
              color: '#c9d1d9',
              padding: '8px 14px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.82rem'
            }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase', fontWeight: 700 }}>Installed Titles</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#58a6ff', marginTop: '4px' }}>{games.length}</div>
          <div style={{ fontSize: '0.75rem', color: '#6e7681', marginTop: '4px' }}>Detected across C:, D:, E:</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase', fontWeight: 700 }}>Library Footprint</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#3fb950', marginTop: '4px' }}>{totalDiskGb} GB</div>
          <div style={{ fontSize: '0.75rem', color: '#6e7681', marginTop: '4px' }}>High-Speed NVMe Storage</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase', fontWeight: 700 }}>Game-Mode Governor</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: gameModeActive ? '#f59e0b' : '#34d399', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            {gameModeActive ? <AlertTriangle size={18} /> : <ShieldCheck size={18} />}
            {gameModeActive ? 'ACTIVE (VRAM Yielded)' : 'STANDBY (Full AI Swarm)'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6e7681', marginTop: '4px' }}>NVIDIA RTX 4090 Allocation</div>
        </div>
      </div>

      {statusMessage && (
        <div style={{
          background: 'rgba(56, 189, 248, 0.12)',
          border: '1px solid rgba(56, 189, 248, 0.4)',
          color: '#38bdf8',
          padding: '12px 18px',
          borderRadius: '8px',
          marginBottom: '24px',
          fontSize: '0.9rem',
          fontWeight: 600
        }}>
          {statusMessage}
        </div>
      )}

      {/* Game Grid */}
      <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '16px', color: '#f0f6fc' }}>Installed Game Library</h2>
      
      {loading && games.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#8b949e' }}>
          <RefreshCw size={32} className="animate-spin" style={{ margin: '0 auto 12px' }} />
          <div>Scanning drive manifests...</div>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
          gap: '20px'
        }}>
          {games.map((game) => (
            <div
              key={game.appid}
              style={{
                background: '#161b22',
                border: '1px solid #30363d',
                borderRadius: '12px',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 4px 14px rgba(0,0,0,0.3)',
                transition: 'transform 0.2s ease, border-color 0.2s ease'
              }}
            >
              {/* Header Image */}
              <div style={{ width: '100%', height: '150px', background: '#0d1117', position: 'relative' }}>
                <img
                  src={game.header_image}
                  alt={game.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
                <div style={{
                  position: 'absolute',
                  top: '10px',
                  right: '10px',
                  background: 'rgba(0,0,0,0.7)',
                  backdropFilter: 'blur(4px)',
                  padding: '4px 8px',
                  borderRadius: '6px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: '#66c0f4',
                  border: '1px solid rgba(102, 192, 244, 0.4)'
                }}>
                  {game.library} DRIVE
                </div>
              </div>

              {/* Game Metadata */}
              <div style={{ padding: '16px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <h3 style={{ margin: '0 0 8px 0', fontSize: '1.1rem', fontWeight: 700, color: '#ffffff' }}>
                    {game.name}
                  </h3>
                  <div style={{ display: 'flex', gap: '10px', fontSize: '0.78rem', color: '#8b949e', marginBottom: '12px' }}>
                    <span>📦 <strong>{game.size_gb} GB</strong></span>
                    <span>•</span>
                    <span>AppID: <code>{game.appid}</code></span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#6e7681', wordBreak: 'break-all', marginBottom: '16px' }}>
                    📂 {game.full_path}
                  </div>
                </div>

                {/* Actions */}
                <button
                  onClick={() => handleLaunchGame(game)}
                  disabled={launchingAppId === game.appid}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    width: '100%',
                    padding: '10px',
                    borderRadius: '8px',
                    border: 'none',
                    background: game.is_running ? '#238636' : 'linear-gradient(135deg, #1b2838 0%, #2a475e 100%)',
                    border: '1px solid #66c0f4',
                    color: '#ffffff',
                    fontWeight: 700,
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    boxShadow: '0 0 10px rgba(102, 192, 244, 0.2)'
                  }}
                >
                  <Play size={16} fill="white" />
                  {launchingAppId === game.appid ? 'Yielding VRAM & Booting...' : (game.is_running ? 'Running in Windows' : 'Play Game')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
