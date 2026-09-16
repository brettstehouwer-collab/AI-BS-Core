function TelemetryWidget({ data }) {
  if (!data) {
    return <div className="glass-panel"><h2>Telemetry</h2><p>Loading telemetry...</p></div>
  }

  const { wallet, compute, general } = data
  const computeEarned = compute?.earnings?.all_time_usd?.toFixed(4) || "0.0000"
  const activeJob = compute?.current_job || "Idle"
  const computeStatus = compute?.status || "Unknown"

  return (
    <div className="glass-panel">
      <h2>Swarm Telemetry</h2>
      
      <div className="telemetry-grid">
        {/* Wallet Stat */}
        <div className="widget-stat">
          <span className="label">Wallet Balance (DOGE)</span>
          <span className="value highlight">{wallet?.balance_doge || "0.0000"}</span>
        </div>

        {/* Compute Stat */}
        <div className="widget-stat">
          <span className="label">Compute Earnings (USD)</span>
          <span className="value success">${computeEarned}</span>
        </div>

        {/* Compute Job */}
        <div className="widget-stat" style={{ gridColumn: '1 / -1' }}>
          <span className="label">Active Compute Job ({computeStatus})</span>
          <span className="value" style={{ fontSize: '1.25rem' }}>{activeJob}</span>
        </div>

        {/* GPU Temp */}
        <div className="widget-stat">
          <span className="label">GPU Temp</span>
          <span className="value">{general?.gpu_status?.temp || "--"}°C</span>
        </div>

        {/* Plot Progress */}
        <div className="widget-stat">
          <span className="label">Chia Plotting</span>
          <span className="value">{general?.storage_status?.plot_progress_pct || "0"}%</span>
        </div>
      </div>

      {compute?.alerts?.length > 0 && (
        <div className="alerts">
          <strong>Compute Alerts:</strong>
          <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.2rem' }}>
            {compute.alerts.map((alert, i) => <li key={i}>{alert}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

export default TelemetryWidget
