function DaemonControl({ daemons, onAction }) {
  // Convert daemons object into an array and sort it alphabetically
  const daemonList = Object.entries(daemons || {}).sort((a, b) => a[0].localeCompare(b[0]))

  return (
    <div className="glass-panel">
      <h2>Swarm Daemons</h2>
      <div className="daemon-list">
        {daemonList.map(([name, info]) => (
          <div key={name} className="daemon-item">
            <div className="daemon-info">
              <h3>{name}</h3>
              <div className="daemon-status">
                <div className={`status-dot ${info.running ? 'running' : 'stopped'}`}></div>
                {info.running ? `Running (PID: ${info.pid})` : 'Stopped'}
                {info.restart_count > 0 && ` • Restarts: ${info.restart_count}`}
              </div>
            </div>
            
            <div className="btn-group">
              <button 
                className="start"
                onClick={() => onAction(name, 'start')}
                disabled={info.running}
              >
                Start
              </button>
              <button 
                className="stop"
                onClick={() => onAction(name, 'stop')}
                disabled={!info.running}
              >
                Stop
              </button>
              <button 
                className="restart"
                onClick={() => onAction(name, 'restart')}
                disabled={!info.running}
              >
                Restart
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default DaemonControl
