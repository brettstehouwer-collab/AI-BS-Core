import React, { useState, useRef } from 'react';
import TerminalPanel from './TerminalPanel';
import { useAppStore } from './useAppStore';

// ─── Real AI-BS Commands ─────────────────────────────────────────────────────
const COMMAND_GROUPS = [
  {
    group: '🖥️ System',
    commands: [
      { label: 'GPU Status (nvidia-smi)',           cmd: 'nvidia-smi' },
      { label: 'GPU Clocks & Power',                cmd: 'nvidia-smi --query-gpu=name,clocks.gr,clocks.mem,power.draw,temperature.gpu,utilization.gpu --format=csv' },
      { label: 'Lock GPU to Max Performance',       cmd: 'nvidia-smi -i 0 --lock-gpu-clocks=2550,2700; nvidia-smi -i 0 --lock-memory-clocks=10501,10501; Write-Host "GPU clocks locked to max."' },
      { label: 'Reset GPU Clocks (Auto)',            cmd: 'nvidia-smi -i 0 --reset-gpu-clocks; nvidia-smi -i 0 --reset-memory-clocks; Write-Host "GPU clocks reset to auto."' },
      { label: 'CPU & RAM Usage',                   cmd: 'Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name, CPU, WorkingSet | Format-Table -AutoSize' },
      { label: 'Disk Usage (All Drives)',            cmd: 'Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N="Used(GB)";E={[math]::Round($_.Used/1GB,2)}}, @{N="Free(GB)";E={[math]::Round($_.Free/1GB,2)}} | Format-Table -AutoSize' },
      { label: 'Network Interfaces',                cmd: 'Get-NetIPAddress | Where-Object AddressFamily -eq IPv4 | Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize' },
      { label: 'Open Ports Snapshot',               cmd: 'netstat -an | findstr LISTENING' },
      { label: 'System Uptime',                     cmd: '(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime | Select-Object Days, Hours, Minutes | Format-List' },
    ]
  },
  {
    group: '⛏️ Mining',
    commands: [
      { label: 'Start Pearl Miner',                 cmd: 'Start-Process cmd.exe -ArgumentList "/c C:\\AI-BS\\miners\\Mine_Pearl.bat" -WindowStyle Hidden; Write-Host "Pearl miner started."' },
      { label: 'Stop Pearl Miner (WSL2)',            cmd: 'wsl.exe -d Ubuntu -u root -- sh -c "pkill -f peakminer && echo Miner stopped || echo Miner was not running"' },
      { label: 'Pearl Miner Status (WSL2)',          cmd: 'wsl.exe -d Ubuntu -u root -- sh -c "ps aux | grep -v grep | grep peakminer || echo Not running"' },
      { label: 'View Pearl Miner Log (last 40)',     cmd: 'Get-Content "C:\\AI-BS\\miners\\logs\\pearl_payout_watcher.log" -Tail 40' },
      { label: 'View Watchdog Status',              cmd: 'Get-Content "C:\\AI-BS\\state\\unified_watchdog_status.json" | ConvertFrom-Json | ConvertTo-Json -Depth 5' },
      { label: 'Pearl Pool Stats (curl)',            cmd: 'curl -s "https://pearl.herominers.com/api/miner_info?address=prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5" | ConvertFrom-Json | ConvertTo-Json -Depth 4' },
    ]
  },
  {
    group: '🔌 Services',
    commands: [
      { label: 'Backend Health Check (port 8080)', cmd: 'curl -s http://127.0.0.1:8080/health | ConvertFrom-Json | ConvertTo-Json' },
      { label: 'List All AI-BS Ports Listening',   cmd: 'netstat -an | findstr "8080 8000 3001 5173 8007 8099 11434 11435 4455"' },
      { label: 'Restart Backend Service',          cmd: 'Get-Process python | Where-Object {$_.CommandLine -like "*AI_BS_Backend*"} | Stop-Process -Force; Start-Sleep 1; Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File C:\\AI-BS\\scripts\\start_backend.ps1" -WindowStyle Hidden; Write-Host "Backend restarting..."' },
      { label: 'Ollama Models Loaded',             cmd: 'curl -s http://127.0.0.1:11434/api/tags | ConvertFrom-Json | Select-Object -ExpandProperty models | Select-Object name, size | Format-Table -AutoSize' },
      { label: 'WSL2 Ubuntu Status',               cmd: 'wsl.exe -d Ubuntu -u root -- sh -c "uname -a && free -h && df -h /"' },
      { label: 'WSL2 Ubuntu-24.04 Status',         cmd: 'wsl.exe -d Ubuntu-24.04 -u root -- sh -c "uname -a && free -h && df -h /"' },
    ]
  },
  {
    group: '📁 Workspace',
    commands: [
      { label: 'List AI-BS Root',                  cmd: 'Get-ChildItem C:\\AI-BS | Select-Object Name, LastWriteTime, @{N="Size";E={if($_.PSIsContainer){"[DIR]"} else {"$([math]::Round($_.Length/1KB,1)) KB"}}} | Format-Table -AutoSize' },
      { label: 'List Backend Scripts',             cmd: 'Get-ChildItem C:\\AI-BS\\scripts | Format-Table Name, LastWriteTime -AutoSize' },
      { label: 'AI-BS Version',                    cmd: 'Get-Content C:\\AI-BS\\version.txt' },
      { label: 'Git Log (last 10 commits)',         cmd: 'git -C C:\\AI-BS log --oneline -10' },
      { label: 'Git Status',                       cmd: 'git -C C:\\AI-BS status' },
      { label: 'Show SAVED_CHECKPOINT.md',         cmd: 'Get-Content C:\\AI-BS\\SAVED_CHECKPOINT.md | Select-Object -First 60' },
    ]
  },
];

export default function TerminalPanelWrapper() {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);
  const terminalRef = useRef(null);
  const [selectedCmd, setSelectedCmd] = useState('');
  const [injecting, setInjecting] = useState(false);

  // Inject the selected command into the xterm terminal via the shared ref
  const injectCommand = () => {
    if (!selectedCmd || !terminalRef.current) return;
    terminalRef.current(selectedCmd);
    setSelectedCmd('');
  };

  return (
    <div className="powershell-container" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        background: 'rgba(255,255,255,0.04)',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        flexWrap: 'wrap'
      }}>
        <div style={{ flex: '0 0 auto' }}>
          <h3 style={{ margin: 0, color: '#fff', fontSize: '14px', fontWeight: 700 }}>
            🖥️ Windows Administrative PowerShell
          </h3>
          <p style={{ margin: '2px 0 0 0', color: '#666', fontSize: '11px' }}>
            Wired to <strong style={{ color: '#4ade80' }}>{BACKEND_URL || 'http://127.0.0.1:8080'}/api/terminal/run</strong> — commands execute on the host machine.
          </p>
        </div>

        {/* Command Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto', flexWrap: 'wrap' }}>
          <select
            value={selectedCmd}
            onChange={e => setSelectedCmd(e.target.value)}
            style={{
              background: '#0d1117',
              color: '#c9d1d9',
              border: '1px solid #30363d',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '12px',
              minWidth: '280px',
              maxWidth: '400px',
              cursor: 'pointer',
              outline: 'none'
            }}
          >
            <option value="">── Quick Commands ──</option>
            {COMMAND_GROUPS.map(group => (
              <optgroup key={group.group} label={group.group}>
                {group.commands.map(c => (
                  <option key={c.cmd} value={c.cmd}>{c.label}</option>
                ))}
              </optgroup>
            ))}
          </select>

          <button
            onClick={injectCommand}
            disabled={!selectedCmd}
            style={{
              padding: '6px 14px',
              background: selectedCmd
                ? 'linear-gradient(135deg, rgba(74,222,128,0.2), rgba(34,197,94,0.1))'
                : 'rgba(255,255,255,0.04)',
              color: selectedCmd ? '#4ade80' : '#555',
              border: `1px solid ${selectedCmd ? 'rgba(74,222,128,0.4)' : '#30363d'}`,
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 700,
              cursor: selectedCmd ? 'pointer' : 'not-allowed',
              transition: 'all 0.15s',
              whiteSpace: 'nowrap'
            }}
          >
            ▶ Run
          </button>
        </div>
      </div>

      {/* Terminal */}
      <TerminalPanel backendUrl={BACKEND_URL} injectRef={terminalRef} />
    </div>
  );
}
