import 'react';

// No current owned evidence contract exists for these provider and host metrics.
// Missing records remain unavailable; this view performs no financial or daemon actions.
const MoneyTrackTab = () => {
  const exchangeMetrics = { totalBalance: 'Unavailable', dayPnL: 'Unavailable', activeTrades: 'Unavailable', freeMargin: 'Unavailable' };
  const chiaMetrics = { totalPlots: 'Unavailable', farmSize: 'Unavailable', xchBalance: 'Unavailable', estTimeToWin: 'Unavailable', status: 'Unavailable' };
  const saladMetrics = { dayEarnings: 'Unavailable', totalBalance: 'Unavailable', workload: 'Unavailable', gpuTemp: 'Unavailable' };
  const minerMetrics = { hashrate: 'Unavailable', algo: 'Unavailable', targetWallet: 'Unavailable', gpuTemp: 'Unavailable', status: 'Unavailable' };
  /** @type {{id:string,date:string,bot:string,pair:string,action:string,amount:string,status:string}[]} */
  const recentBots = [];

  return (
    <div style={{ padding: '20px', color: '#c9d1d9', fontFamily: 'monospace' }}>
      
      <p role="status" style={{ color: '#fbbf24', marginTop: 0 }}>
        Unavailable: no verified owned records are connected. Trading and daemon actions are disabled.
      </p>
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
          <h3 style={{ margin: 0, color: '#3fb950' }}>⛏️ GPU Mining</h3>
          <span style={{ 
            fontSize: '0.85rem', 
            padding: '4px 12px', 
            borderRadius: '12px', 
            background: '#854d0e',
            color: '#fff',
            fontWeight: 'bold'
          }}>
            {minerMetrics.status}
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
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#e6edf3' }}>Order Activity</h3>
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
            {recentBots.length === 0 && <tr><td colSpan={7} style={{ padding: '16px', color: '#94a3b8' }}>
              Unavailable: no verified owned order records. Missing history does not mean there were no trades.
            </td></tr>}
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

/** @param {{title:string,value:import("react").ReactNode,color:string}} props */
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

/** @param {{title:string,value:import("react").ReactNode,color?:string}} props */
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
