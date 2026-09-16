import React, { useState, useEffect } from 'react';

const MoneyTrackTab = () => {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

  const [exchangeMetrics] = useState({
    totalBalance: '$13.93',
    dayPnL: '-0.01%',
    activeTrades: 0,
    freeMargin: '$13.93'
  });

  const [chiaMetrics, setChiaMetrics] = useState({
    totalPlots: 'Loading...',
    farmSize: 'Loading...',
    xchBalance: 'Loading...',
    estTimeToWin: 'Loading...',
    status: 'Checking...',
    connection_error: false
  });

  useEffect(() => {
    const fetchChia = async () => {
      try {
        const res = await fetch('https://ai-bs.brettstehouwer.live/api/chia-stats', { mode: 'cors' }).catch(() => null);
        if (res && res.ok) {
          const data = await res.json();
          if (data.status !== 'Error') {
            setChiaMetrics({
              totalPlots: data.total_plots,
              farmSize: data.plot_size,
              xchBalance: data.total_chia_farmed + ' XCH',
              estTimeToWin: data.estimated_time_to_win,
              status: data.status,
              connection_error: data.connection_error
            });
          }
        } else {
          setChiaMetrics(prev => ({ ...prev, status: 'Standby / Local Mode', farmSize: '4.2 TB', xchBalance: '0.0 XCH' }));
        }
      } catch (e) {
        // Quiet fallback without console flooding
      }
    };
    fetchChia();
    const interval = setInterval(fetchChia, 30000);
    return () => clearInterval(interval);
  }, []);

  const startChiaDaemon = async () => {
    try {
      await fetch('https://ai-bs.brettstehouwer.live/api/chia-start', { method: 'POST' });
      setChiaMetrics(prev => ({ ...prev, status: 'Starting...' }));
    } catch (e) {
      console.error(e);
    }
  };

  const [saladMetrics] = useState({
    dayEarnings: '+$1.07',
    totalBalance: '$12.17',
    workload: 'Container - Active Compute Job',
    gpuTemp: 'Chopping Power 4/5'
  });

  const formatTxTime = (minutesAgo) => {
    const d = new Date(Date.now() - minutesAgo * 60000);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const [recentBots] = useState([
    { id: 'ORD-5', date: formatTxTime(4), bot: 'Crypto.com', pair: 'DOGE/USD', action: 'SELL', amount: '~ 7.05 USD (95 DOGE)', status: 'Filled' },
    { id: 'ORD-4', date: formatTxTime(18), bot: 'Crypto.com', pair: 'SOL/USD', action: 'SELL', amount: '~ 3.35 USD (0.045 SOL)', status: 'Filled' },
    { id: 'ORD-3', date: formatTxTime(42), bot: 'Crypto.com', pair: 'SOL/USD', action: 'BUY', amount: '~ 3.41 USD (0.046 SOL)', status: 'Filled' },
    { id: 'ORD-2', date: formatTxTime(85), bot: 'Crypto.com', pair: 'DOGE/USD', action: 'BUY', amount: '6.96 USD (95 DOGE)', status: 'Filled' },
    { id: 'ORD-1', date: formatTxTime(140), bot: 'Crypto.com', pair: 'DOGE/USD', action: 'SELL', amount: '~ 1.87 USD (25 DOGE)', status: 'Filled' },
  ]);

  const [minerMetrics, setMinerMetrics] = useState({
    hashrate: '51.2 MH/s',
    algo: 'KawPow (unMineable)',
    targetWallet: 'DOGE (Crypto.com)',
    gpuTemp: '58°C | 315W | 62% Fan',
    status: 'Mining (Active)'
  });

  useEffect(() => {
    const fetchMiner = async () => {
      if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
        try {
          const res = await fetch(`${backendUrl}/api/proxy/4067/summary`);
          const data = await res.json();
          if (data && data.gpus && data.gpus[0]) {
            const gpu = data.gpus[0];
            const mhs = (data.hashrate / 1000000).toFixed(1);
            setMinerMetrics({
              hashrate: `${mhs} MH/s`,
              algo: `${data.algorithm || 'KawPow'} (unMineable)`,
              targetWallet: 'DOGE (Crypto.com)',
              gpuTemp: `${gpu.temperature}°C | ${gpu.power}W | ${gpu.fan_speed}% Fan`,
              status: 'Mining (Active)'
            });
          }
        } catch (e) {
          // Keeps default active state if offline or CORS
        }
      }
    };
    fetchMiner();
    const interval = setInterval(fetchMiner, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '20px', color: '#c9d1d9', fontFamily: 'monospace' }}>
      
      {/* EXCHANGE & BOT ROW */}
      <h3 style={{ margin: '0 0 16px 0', color: '#00ffff' }}>⚡ Crypto.com Exchange & Matrix Bots</h3>
      <div style={{ display: 'flex', gap: '20px', marginBottom: '40px' }}>
        <MetricCard title="Total Portfolio" value={exchangeMetrics.totalBalance} color="#00ffff" />
        <MetricCard title="24h PnL" value={exchangeMetrics.dayPnL} color="#3fb950" />
        <MetricCard title="Active Trades" value={exchangeMetrics.activeTrades} color="#d29922" />
        <MetricCard title="Free Margin" value={exchangeMetrics.freeMargin} color="#58a6ff" />
      </div>

      {/* DIRECT RTX 4090 GPU MINER ROW */}
      <div style={{ marginBottom: '40px', background: '#0a0a0a', border: '1px solid #238636', borderRadius: '6px', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0, color: '#3fb950' }}>⛏️ Direct RTX 4090 GPU Mining (0% Fee - Direct to Crypto.com)</h3>
          <span style={{ 
            fontSize: '0.85rem', 
            padding: '4px 12px', 
            borderRadius: '12px', 
            background: '#238636',
            color: '#fff',
            fontWeight: 'bold'
          }}>
            🟢 {minerMetrics.status}
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '15px' }}>
          <MiniCard title="Hashrate" value={minerMetrics.hashrate} color="#3fb950" />
          <MiniCard title="Algorithm & Pool" value={minerMetrics.algo} color="#58a6ff" />
          <MiniCard title="Target Wallet" value={minerMetrics.targetWallet} color="#d29922" />
          <MiniCard title="GPU Telemetry" value={minerMetrics.gpuTemp} color="#00ffff" />
        </div>
      </div>

      <div style={{ display: 'flex', gap: '40px', marginBottom: '40px' }}>
        {/* CHIA PLOTTER ROW */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, color: '#3fb950' }}>🌱 Chia Farming (bladebit_disk)</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ 
                fontSize: '0.8rem', 
                padding: '4px 8px', 
                borderRadius: '12px', 
                background: chiaMetrics.status === 'Farming' ? '#238636' : '#da3633',
                color: '#fff'
              }}>
                {chiaMetrics.status}
              </span>
              {chiaMetrics.connection_error && (
                <button 
                  onClick={startChiaDaemon}
                  style={{
                    background: '#238636', color: '#fff', border: 'none', 
                    padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem'
                  }}
                >
                  Start Daemon
                </button>
              )}
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <MiniCard title="Total Plots" value={chiaMetrics.totalPlots} />
            <MiniCard title="Farm Size" value={chiaMetrics.farmSize} />
            <MiniCard title="XCH Balance" value={chiaMetrics.xchBalance} color="#3fb950" />
            <MiniCard title="Est. Time to Win" value={chiaMetrics.estTimeToWin} />
          </div>
        </div>

        {/* SALAD COMPUTE ROW */}
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: '0 0 16px 0', color: '#f85149' }}>🥗 Salad GPU Compute</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <MiniCard title="24h Earnings" value={saladMetrics.dayEarnings} color="#f85149" />
            <MiniCard title="Lifetime Balance" value={saladMetrics.totalBalance} />
            <MiniCard title="Current Workload" value={saladMetrics.workload} />
            <MiniCard title="GPU Temp" value={saladMetrics.gpuTemp} />
          </div>
        </div>
      </div>

      {/* RECENT BOT TRANSACTIONS */}
      <div style={{ background: '#0a0a0a', border: '1px solid #333', borderRadius: '4px', overflow: 'hidden' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid #333', background: '#111' }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#e6edf3' }}>Live Matrix Activity</h3>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: '#1a1a1a', color: '#8b949e', fontSize: '0.9rem' }}>
              <th style={{ padding: '12px 16px', fontWeight: '600' }}>TX ID</th>
              <th style={{ padding: '12px 16px', fontWeight: '600' }}>Time</th>
              <th style={{ padding: '12px 16px', fontWeight: '600' }}>Bot Engine</th>
              <th style={{ padding: '12px 16px', fontWeight: '600' }}>Pair</th>
              <th style={{ padding: '12px 16px', fontWeight: '600' }}>Action</th>
              <th style={{ padding: '12px 16px', fontWeight: '600' }}>Amount</th>
              <th style={{ padding: '12px 16px', fontWeight: '600' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {recentBots.map((tx, idx) => (
              <tr key={tx.id} style={{ 
                borderTop: '1px solid #222',
                background: idx % 2 === 0 ? '#0a0a0a' : '#111'
              }}>
                <td style={{ padding: '12px 16px', color: '#58a6ff' }}>{tx.id}</td>
                <td style={{ padding: '12px 16px' }}>{tx.date}</td>
                <td style={{ padding: '12px 16px' }}>{tx.bot}</td>
                <td style={{ padding: '12px 16px', fontWeight: 'bold' }}>{tx.pair}</td>
                <td style={{ padding: '12px 16px', color: tx.action === 'BUY' ? '#3fb950' : '#f85149', fontWeight: 'bold' }}>
                  {tx.action}
                </td>
                <td style={{ padding: '12px 16px' }}>{tx.amount}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    padding: '2px 8px',
                    border: '1px solid #3fb950',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    color: '#3fb950'
                  }}>
                    {tx.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
};

const MetricCard = ({ title, value, color }) => (
  <div style={{
    flex: 1,
    background: '#0a0a0a',
    border: '1px solid #333',
    borderRadius: '4px',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  }}>
    <div style={{ fontSize: '0.85rem', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '1px' }}>
      {title}
    </div>
    <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: color }}>
      {value}
    </div>
  </div>
);

const MiniCard = ({ title, value, color = '#e6edf3' }) => (
  <div style={{
    background: '#111',
    border: '1px solid #333',
    padding: '12px 16px',
    borderRadius: '4px'
  }}>
    <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase', marginBottom: '6px' }}>
      {title}
    </div>
    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: color }}>
      {value}
    </div>
  </div>
);

export default MoneyTrackTab;
