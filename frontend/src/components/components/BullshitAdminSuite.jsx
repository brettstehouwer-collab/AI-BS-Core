import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import TerminalPanel from './TerminalPanel';

function TrainerLogViewer({ BACKEND_URL }) {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState("Checking...");

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/trainer/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data.status);
        setLogs(data.logs || []);
      } else {
        setStatus("Offline/Error");
      }
    } catch (err) {
      setStatus("Disconnected");
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [BACKEND_URL]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ marginBottom: '10px', color: status === 'running' ? '#4ade80' : '#ff6b6b', fontWeight: 'bold' }}>
        Daemon Status: {status.toUpperCase()}
      </div>
      <div style={{ flex: 1, background: '#111', border: '1px solid #333', borderRadius: '6px', overflowY: 'auto', padding: '12px', fontFamily: 'monospace', fontSize: '0.85rem' }}>
        {logs.length > 0 ? (
          logs.map((log, i) => (
            <div key={i} style={{ color: log.includes('SUCCESS') ? '#4ade80' : log.includes('FAILED') || log.includes('Error') ? '#ff6b6b' : '#d4d4d4' }}>
              {log}
            </div>
          ))
        ) : (
          <div style={{ color: '#888' }}>Waiting for trainer logs... Make sure start_trainer.vbs is running.</div>
        )}
      </div>
      <div style={{ marginTop: '10px' }}>
        <button onClick={fetchLogs} style={{ background: 'rgba(255,255,255,0.1)', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer' }}>
          Refresh Logs
        </button>
      </div>
    </div>
  );
}

export default function BullshitAdminSuite(props) {
  const { 
    activeTab, BACKEND_URL, ORCHESTRATOR_COMMANDS, chatInput, setChatInput, setActiveTab, setWorkflowMode,
    activeAgents, pullingStatus, pullModelInput, telegramToken, safetySkipPermissions, customLoopTime, customLoopTask,
    handleLaunchAgent, handleKillAgent, handlePullModel, setPullModelInput, setTelegramToken, setSafetySkipPermissions,
    setCustomLoopTime, setCustomLoopTask, ssdRamPath, ssdRamSize, ssdRamCount, isSsdLoading, updateSsdSettings, wipeSsdRam,
    devLeftTab, setDevLeftTab, devChatMessages, messageFeedRef, isDevChatLoading, devChatInput, setDevChatInput, handleDevChatSubmit,
    systemGitStatus, setSystemGitStatus, gitStatus, setGitStatus, devCodeInput, setDevCodeInput, devMode, setDevMode,
    devCodeType, setDevCodeType, devFileName, setDevFileName, handleSaveFile, isSavingFile, saveMessage, handleEditorDidMount,
    handleExecuteCode, isExecutingCode, devBottomTab, setDevBottomTab, devCodeOutput, itTimer, formatTime, isItActive,
    handleStartItInterview, handleGradeItInterview, isGrading, itScorecard, messages, handleSendMessage, toggleListening,
    isListening, renderDevChatMessage
  } = props;

  const [localSsdPath, setLocalSsdPath] = useState('');
  const [config, setConfig] = useState({ theme: 'matrix', backendIp: '127.0.0.1', activeModel: 'stehouwer_llm' });
  const [selectedVault, setSelectedVault] = useState("Medical");
  const [epochs, setEpochs] = useState(3);
  const [loraRank, setLoraRank] = useState(16);
  const [learningRate, setLearningRate] = useState("2e-4");
  const [isTraining, setIsTraining] = useState(false);
  const [ftLogs, setFtLogs] = useState([]);

  if (activeTab === 'dev') {
    return (
      <div className="dev-workspace-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', height: '100%' }}>
        <div className="dev-chat-panel glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-glow)' }}>
            <button style={{ flex: 1, padding: '16px', background: devLeftTab === 'chat' ? 'rgba(0,255,0,0.1)' : 'transparent', color: devLeftTab === 'chat' ? 'var(--accent-neon)' : '#888', border: 'none', cursor: 'pointer', fontWeight: 'bold' }} onClick={() => setDevLeftTab('chat')}>🤖 Assistant</button>
            <button style={{ flex: 1, padding: '16px', background: devLeftTab === 'git' ? 'rgba(0,255,0,0.1)' : 'transparent', color: devLeftTab === 'git' ? 'var(--accent-neon)' : '#888', border: 'none', cursor: 'pointer', fontWeight: 'bold' }} onClick={() => { setDevLeftTab('git'); fetch(`${BACKEND_URL}/api/git/status`).then(r => r.json()).then(d => setGitStatus(d.status || d.error || 'Clean working tree.')); fetch(`${BACKEND_URL}/api/git/system/status`).then(r => r.json()).then(d => setSystemGitStatus(d.status || d.error || 'Clean working tree.')); }}>🌿 Source Control</button>
            <button style={{ flex: 1, padding: '16px', background: devLeftTab === 'trainer' ? 'rgba(0,255,0,0.1)' : 'transparent', color: devLeftTab === 'trainer' ? 'var(--accent-neon)' : '#888', border: 'none', cursor: 'pointer', fontWeight: 'bold' }} onClick={() => setDevLeftTab('trainer')}>🧠 Trainer</button>
          </div>
          {devLeftTab === 'chat' ? (
            <>
              <div className="message-feed" ref={messageFeedRef} style={{ flex: 1, padding: '16px', overflowY: 'auto' }}>
                {devChatMessages?.map((msg, idx) => (
                  <div key={idx} className={`chat-message ${msg.role}`}>
                    <div className={`avatar ${msg.role === 'user' ? 'user-avatar' : 'ai-avatar'}`}>{msg.role === 'user' ? 'B' : 'AI'}</div>
                    <div className="message-bubble">
                      <div className="message-text" style={{ whiteSpace: 'pre-wrap' }}>{renderDevChatMessage ? renderDevChatMessage(msg.content) : msg.content}</div>
                    </div>
                  </div>
                ))}
                {isDevChatLoading && <div className="chat-message agent"><div className="avatar ai-avatar">AI</div><div className="message-bubble"><div className="message-text" style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>Working...</div></div></div>}
              </div>
              <div className="chat-input-area" style={{ padding: '16px', borderTop: '1px solid var(--border-glow)' }}>
                <div className="chat-input-row">
                  <textarea className="chat-input" placeholder="Ask the Dev Assistant..." value={devChatInput} onChange={(e) => setDevChatInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleDevChatSubmit(); } }} style={{ height: '60px' }} />
                  <button className="send-button" onClick={handleDevChatSubmit} disabled={isDevChatLoading || !devChatInput?.trim()}>Send</button>
                </div>
              </div>
            </>
          ) : devLeftTab === 'git' ? (
            <div style={{ flex: 1, padding: '16px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
              <h4 style={{ margin: '0 0 8px 0', color: 'var(--accent-neon)' }}>AI-BS System Updates</h4>
              <pre style={{ minHeight: '100px', background: '#111', padding: '12px', borderRadius: '6px', overflow: 'auto', border: '1px solid #333' }}>{systemGitStatus}</pre>
              <div style={{ marginTop: '8px', marginBottom: '24px', display: 'flex', gap: '8px' }}>
                <button className="dev-btn dev-btn-run" onClick={() => { setSystemGitStatus('Pulling...'); fetch(`${BACKEND_URL}/api/git/system/pull`, {method: 'POST'}).then(r => r.json()).then(d => setSystemGitStatus(d.stdout || d.stderr || d.error || 'Done.')); }}>⬇️ Pull</button>
                <button className="dev-btn dev-btn-run" onClick={() => { setSystemGitStatus('Pushing...'); fetch(`${BACKEND_URL}/api/git/system/push`, {method: 'POST'}).then(r => r.json()).then(d => setSystemGitStatus(d.stdout || d.stderr || d.error || 'Done.')); }}>⬆️ Push</button>
              </div>
              <h4 style={{ margin: '0 0 8px 0' }}>Projects Workspace</h4>
              <pre style={{ flex: 1, minHeight: '100px', background: '#111', padding: '12px', borderRadius: '6px', overflow: 'auto', border: '1px solid #333' }}>{gitStatus}</pre>
            </div>
          ) : (
            <div style={{ flex: 1, padding: '16px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
              <h4 style={{ margin: '0 0 8px 0', color: 'var(--accent-neon)' }}>Background Trainer Status</h4>
              <TrainerLogViewer BACKEND_URL={BACKEND_URL} />
            </div>
          )}
        </div>
        <div className="dev-code-panel glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="dev-header-row">
            <h3>Code Editor</h3>
            <div className="dev-controls">
              <select value={devCodeType} onChange={(e) => { setDevCodeType(e.target.value); }} className="dev-select">
                <option value="python">Python</option><option value="javascript">JavaScript (Node)</option>
                <option value="cpp">C++</option><option value="lua">Lua</option>
                <option value="go">Go</option><option value="html">HTML</option><option value="css">CSS</option>
              </select>
            </div>
          </div>
          <div className="dev-file-save-row">
            <input type="text" className="dev-filename-input" value={devFileName} onChange={(e) => setDevFileName(e.target.value)} placeholder="Filename (e.g. app.py)" />
            <button className="dev-btn dev-btn-save" onClick={handleSaveFile} disabled={isSavingFile || !devFileName?.trim()}>{isSavingFile ? 'Saving...' : '💾 Save File'}</button>
            {saveMessage && <span className="dev-save-msg">{saveMessage}</span>}
          </div>
          <div style={{ flex: 1, minHeight: '400px', border: '1px solid var(--border-glow)', borderRadius: '6px', overflow: 'hidden' }}>
            <Editor height="100%" language={devCodeType === 'cpp' ? 'cpp' : devCodeType} theme="vs-dark" value={devCodeInput} onChange={(value) => setDevCodeInput(value || '')} onMount={handleEditorDidMount} options={{ minimap: { enabled: false } }} />
          </div>
          <div className="dev-action-row">
            {devCodeType !== 'css' && devCodeType !== 'html' && <button className="dev-btn dev-btn-run" onClick={handleExecuteCode} disabled={isExecutingCode}>{isExecutingCode ? 'Running...' : '▶️ Run'}</button>}
          </div>
          <div className="dev-bottom-panel" style={{ display: 'flex', flexDirection: 'column', height: '250px', border: '1px solid var(--border-glow)', borderRadius: '6px', overflow: 'hidden' }}>
            <div className="dev-bottom-tabs" style={{ display: 'flex', background: 'rgba(0,0,0,0.5)', borderBottom: '1px solid var(--border-glow)' }}>
              <button style={{ padding: '8px 16px', background: devBottomTab === 'output' ? 'var(--accent-neon)' : 'transparent', color: devBottomTab === 'output' ? '#fff' : '#888', border: 'none', cursor: 'pointer' }} onClick={() => setDevBottomTab('output')}>Console Output</button>
              <button style={{ padding: '8px 16px', background: devBottomTab === 'terminal' ? 'var(--accent-neon)' : 'transparent', color: devBottomTab === 'terminal' ? '#fff' : '#888', border: 'none', cursor: 'pointer' }} onClick={() => setDevBottomTab('terminal')}>Terminal</button>
            </div>
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
              {devBottomTab === 'output' && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '8px', overflow: 'auto' }}>
                  {devCodeType === 'html' ? <iframe srcDoc={devCodeInput} sandbox="allow-scripts allow-modals" style={{ flex: 1, backgroundColor: '#fff', border: '1px solid var(--border-glow)', borderRadius: '6px' }} /> : <pre className="dev-output-terminal" style={{ margin: 0 }}>{devCodeOutput || 'Ready.'}</pre>}
                </div>
              )}
              {devBottomTab === 'terminal' && <TerminalPanel backendUrl={BACKEND_URL} />}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (activeTab === 'commands') {
    return (
      <div className="command-center-container" style={{ padding: '32px', height: '100%', overflowY: 'auto' }}>
        <h2 style={{ marginBottom: '8px', color: '#fff' }}>Orchestrator Command Library & Agentic Manager</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px', marginBottom: '40px' }}>
          <div className="glass-panel" style={{ padding: '24px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', background: 'rgba(25, 28, 36, 0.4)' }}>
            <h3 style={{ margin: '0 0 20px 0', color: '#4ade80' }}>⚡ Local Agent Launcher</h3>
            <button className="generate-btn" onClick={() => handleLaunchAgent('vscode')} style={{ padding: '10px 16px', background: '#38bdf8', color: '#000', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>Launch VS Code Sync</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div className="glass-panel" style={{ padding: '24px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', background: 'rgba(25, 28, 36, 0.4)' }}>
              <h3 style={{ margin: '0 0 16px 0', color: '#f87171' }}>🤖 Active Background Sessions</h3>
              {activeAgents?.filter(a => a.is_running).length === 0 ? <div style={{ color: '#666', fontSize: '0.9rem', textAlign: 'center', padding: '24px' }}>No active background agent sessions running.</div> : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {activeAgents?.filter(a => a.is_running).map(agent => (
                    <div key={agent.agent} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(0,0,0,0.3)', padding: '14px 18px', borderRadius: '8px' }}>
                      <div><div style={{ color: '#fff', fontWeight: 'bold' }}>{agent.agent.toUpperCase()} Sync Daemon</div></div>
                      <button onClick={() => handleKillAgent(agent.agent)} style={{ padding: '6px 12px', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '4px' }}>Terminate</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="glass-panel" style={{ padding: '28px', borderRadius: '12px', border: '1px solid rgba(139, 92, 246, 0.2)', background: 'rgba(20, 15, 40, 0.5)', marginBottom: '40px' }}>
          <h3 style={{ margin: '0 0 8px 0', color: '#a78bfa' }}>💾 SSD Virtual RAM — Context Memory</h3>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <input type="text" value={localSsdPath} onChange={(e) => setLocalSsdPath(e.target.value)} placeholder={ssdRamPath || 'Enter SSD path...'} style={{ flexGrow: 1, background: '#000', color: '#c4b5fd', padding: '10px 14px' }} />
            <button onClick={() => { updateSsdSettings(localSsdPath); setLocalSsdPath(''); }} style={{ padding: '10px 20px', background: '#7c3aed', color: '#fff', border: 'none' }}>💾 Set Path</button>
          </div>
        </div>
        <h3 style={{ color: '#fff', marginBottom: '20px' }}>🧠 Orchestrator Command Library</h3>
        <div className="commands-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
          {ORCHESTRATOR_COMMANDS?.map((cmd, idx) => (
            <div key={idx} className="command-card glass-panel" style={{ padding: '24px', borderRadius: '12px', background: 'rgba(25, 28, 36, 0.4)' }}>
              <h4 style={{ margin: '0 0 12px 0', color: '#4ade80' }}>{cmd.title}</h4>
              <button className="generate-btn" onClick={() => { handleLaunchAgent('coder', cmd.prompt); }} style={{ padding: '12px', background: '#fbbf24', color: '#000', border: 'none', borderRadius: '8px' }}>Execute</button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (activeTab === 'settings') {
    return (
      <div style={{ padding: '20px', color: '#fff', maxWidth: '800px', margin: '0 auto' }}>
        <h2 style={{ color: '#f43f5e' }}>⚙️ AI-BS Core Settings</h2>
        
        <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px', marginTop: '20px', background: 'rgba(25, 28, 36, 0.4)' }}>
          <h3 style={{ margin: '0 0 10px 0', color: '#38bdf8' }}>Remote Connection Tunnel</h3>
          <p style={{ color: '#aaa', fontSize: '0.9rem', marginBottom: '15px' }}>
            If you are accessing this UI from outside your local network (e.g. via Vercel on your phone), paste your Ngrok or Cloudflare tunnel URL here to sync the UI with your home desktop's Python backend.
          </p>
          <label style={{ display: 'block', color: '#fff', marginBottom: '8px' }}>Master Backend URL</label>
          <input 
            type="text" 
            value={BACKEND_URL} 
            onChange={e => props.setBackendUrl(e.target.value)} 
            placeholder="https://ai-bs.brettstehouwer.live"
            style={{ width: '100%', padding: '12px', background: '#111', color: '#4ade80', border: '1px solid #333', borderRadius: '6px', fontFamily: 'monospace' }} 
          />
        </div>

        <button 
          onClick={() => {
            localStorage.setItem('bullshitBackendUrl', BACKEND_URL);
            alert("Backend URL saved successfully! The swarm is now re-routing to " + BACKEND_URL);
          }}
          style={{ marginTop: '30px', padding: '12px 24px', background: '#f43f5e', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}
        >
          Save & Re-Connect
        </button>
      </div>
    );
  }

  if (activeTab === 'it_helpdesk') {
    return (
      <div className="it-simulator-grid" style={{ display: 'flex', height: '100%' }}>
        <div className="it-control-card glass-panel" style={{ width: '300px', padding: '20px' }}>
          <h3>Interview Controls</h3>
          <button className="it-btn-primary" onClick={handleStartItInterview}>🔄 Start</button>
          <button className="it-btn-success" onClick={handleGradeItInterview} disabled={!isItActive || isGrading}>{isGrading ? 'Grading...' : '🎓 Finish & Grade'}</button>
          {itScorecard && <div className="it-scorecard animate-slide-in">Score: {itScorecard.score}</div>}
        </div>
        <div className="chat-container" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div className="message-feed" style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
            {messages?.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.role}`}>{msg.content}</div>
            ))}
          </div>
          <div className="chat-input-area" style={{ padding: '20px' }}>
            <textarea className="chat-input" value={chatInput} onChange={(e) => setChatInput(e.target.value)} disabled={!isItActive} />
            <button className="send-button" onClick={handleSendMessage} disabled={!isItActive}>Reply</button>
          </div>
        </div>
      </div>
    );
  }

  if (activeTab === 'finetune') {
    const handleStartTraining = async () => {
      setIsTraining(true);
      setFtLogs(prev => [...prev, `[System] Initiating Dataset Compiler for Vault: ${selectedVault}...`]);
      try {
        const res = await fetch("http://127.0.0.1:8004/finetune/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ vault: selectedVault, epochs, rank: loraRank, lr: learningRate }) });
        const data = await res.json();
        if (data.status === "success") {
          setFtLogs(prev => [...prev, `[Trainer] ${data.message}`]);
        } else {
          setFtLogs(prev => [...prev, `[Error] ${data.message}`]);
          setIsTraining(false);
        }
      } catch (e) {
        setFtLogs(prev => [...prev, `[Network Error] Could not connect.`]);
        setIsTraining(false);
      }
    };

    return (
      <div className="finetuning-container glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '20px' }}>
        <h2>LoRA Model Fine-Tuning Studio</h2>
        <div style={{ display: 'flex', gap: '20px' }}>
          <div className="config-panel glass-panel" style={{ flex: 1, padding: '15px' }}>
            <h3>Training Configuration</h3>
            <select value={selectedVault} onChange={e => setSelectedVault(e.target.value)} style={{ width: '100%', marginBottom: '15px' }}><option value="Medical">Medical</option></select>
            <button onClick={handleStartTraining} disabled={isTraining} style={{ width: '100%', padding: '15px', background: isTraining ? '#555' : '#8A2BE2', color: 'white', border: 'none', borderRadius: '5px' }}>{isTraining ? 'Training...' : 'Start QLoRA Training'}</button>
          </div>
          <div className="logs-panel glass-panel" style={{ flex: 2, padding: '15px', background: '#0a0a0a', color: '#00ff00', fontFamily: 'monospace', overflowY: 'auto', minHeight: '300px' }}>
            <h3>Training Matrix Matrix</h3>
            {ftLogs.map((log, i) => <div key={i}>{log}</div>)}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
