import React, { useState, useCallback, useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import TerminalPanel from './TerminalPanel';
import VisualScriptingTab from './VisualScriptingTab';
import { useAppStore } from './useAppStore';
import './DeveloperWorkspaceTab.css';

function renderDevChatMessage(content) {
  return content;
}

export default function DeveloperWorkspaceTab() {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);
  const devChatInput = useAppStore(state => state.devChatInput);
  const setDevChatInput = useAppStore(state => state.setDevChatInput);
  const devChatMessages = useAppStore(state => state.devChatMessages);
  const setDevChatMessages = useAppStore(state => state.setDevChatMessages);
  const devLeftTab = useAppStore(state => state.devLeftTab);
  const setDevLeftTab = useAppStore(state => state.setDevLeftTab);
  const devBottomTab = useAppStore(state => state.devBottomTab);
  const setDevBottomTab = useAppStore(state => state.setDevBottomTab);
  const devMode = useAppStore(state => state.devMode);
  const setDevMode = useAppStore(state => state.setDevMode);
  const devFileName = useAppStore(state => state.devFileName);
  const setDevFileName = useAppStore(state => state.setDevFileName);
  const devCodeInput = useAppStore(state => state.devCodeInput);
  const setDevCodeInput = useAppStore(state => state.setDevCodeInput);
  const devCodeOutput = useAppStore(state => state.devCodeOutput);
  const setDevCodeOutput = useAppStore(state => state.setDevCodeOutput);
  const devCodeType = useAppStore(state => state.devCodeType);
  const setDevCodeType = useAppStore(state => state.setDevCodeType);
  const gitStatus = useAppStore(state => state.gitStatus);
  const setGitStatus = useAppStore(state => state.setGitStatus);
  const systemGitStatus = useAppStore(state => state.systemGitStatus);
  const setSystemGitStatus = useAppStore(state => state.setSystemGitStatus);
  const isExecutingCode = useAppStore(state => state.isExecutingCode);
  const setIsExecutingCode = useAppStore(state => state.setIsExecutingCode);
  const monacoRef = useAppStore(state => state.monacoRef);
  const selectedModel = useAppStore(state => state.selectedModel);

  const [isDevChatLoading, setIsDevChatLoading] = useState(false);
  const [isSavingFile, setIsSavingFile] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  const chatEndRef = useRef(null);
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [devChatMessages, isDevChatLoading]);

  const handleEditorDidMount = useCallback((editor) => {
    if (monacoRef) monacoRef.current = editor;
  }, [monacoRef]);

  const handleDevChatSubmit = async () => {
    const text = devChatInput.trim();
    if (!text || isDevChatLoading) return;

    const userMsg = { role: 'user', content: text };
    setDevChatMessages(prev => [...prev, userMsg]);
    setDevChatInput('');
    setIsDevChatLoading(true);

    const contextPrompt = devCodeInput
      ? `You are a coding assistant. The user currently has this code open (${devCodeType}):\n\`\`\`${devCodeType}\n${devCodeInput}\n\`\`\`\n\nUser request: ${text}`
      : text;

    try {
      const res = await fetch(`${BACKEND_URL}/v1/ide/reason-and-code`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026'
        },
        body: JSON.stringify({ 
          user_prompt: text, 
          code_context: devCodeInput,
          file_name: devFileName || 'main.py',
          language: devCodeType || 'python',
          model: selectedModel || 'qwen2.5-coder:latest' 
        }),
      });
      const data = await res.json();
      const responseText = data.response || data.message || 'No response generated.';
      
      let headerText = '';
      if (data.refinement_quality_score) {
        headerText = `🧠 [Self-Solving Verified: ${data.refinement_quality_score}% Quality | Model: ${data.model_used}]\n\n`;
      }
      
      const fullResponse = headerText + responseText;
      setDevChatMessages(prev => [...prev, { role: 'assistant', content: fullResponse }]);
      
      const codeMatch = responseText?.match(/```(?:\w+)?\n([\s\S]+?)```/);
      if (codeMatch) {
        setDevCodeInput(codeMatch[1].trim());
      }
    } catch (err) {
      setDevChatMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Error: ${err.message}` }]);
    } finally {
      setIsDevChatLoading(false);
    }
  };

  const handleSaveFile = async () => {
    if (!devFileName.trim()) return;
    setIsSavingFile(true);
    setSaveMessage('');
    try {
      const res = await fetch(`${BACKEND_URL}/api/save-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: devFileName, content: devCodeInput, language: devCodeType }),
      });
      const data = await res.json();
      setSaveMessage(data.status === 'success' ? `✅ Saved to ${data.path}` : `❌ ${data.detail || 'Save failed'}`);
    } catch (err) {
      setSaveMessage(`❌ ${err.message}`);
    } finally {
      setIsSavingFile(false);
      setTimeout(() => setSaveMessage(''), 4000);
    }
  };

  const handleExecuteCode = async () => {
    if (!devCodeInput.trim() || isExecutingCode) return;
    setIsExecutingCode(true);
    setDevCodeOutput([{ type: 'system', content: `Running ${devCodeType}...` }]);
    try {
      const res = await fetch(`${BACKEND_URL}/api/execute-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: devCodeInput, language: devCodeType }),
      });
      const data = await res.json();
      const steps = [];
      if (data.stdout) steps.push({ type: 'stdout', content: data.stdout });
      if (data.stderr) steps.push({ type: 'error', content: data.stderr });
      if (data.error) steps.push({ type: 'error', content: data.error });
      if (!data.stdout && !data.stderr && !data.error) steps.push({ type: 'complete', content: 'Execution complete — no output.' });
      setDevCodeOutput(steps);
    } catch (err) {
      setDevCodeOutput([{ type: 'error', content: err.message }]);
    } finally {
      setIsExecutingCode(false);
    }
  };

  return (
    <div className="dev-workspace-grid">

      {/* DEV CHAT PANEL (LEFT) */}
      <div className="dev-chat-panel glass-panel">
        <div className="dev-tabs-row">
          <button
            className={`dev-tab-btn ${devLeftTab === 'chat' ? 'dev-tab-btn-active' : 'dev-tab-btn-inactive'}`}
            onClick={() => setDevLeftTab('chat')}
          >🤖 Assistant</button>
          <button
            className={`dev-tab-btn ${devLeftTab === 'git' ? 'dev-tab-btn-active' : 'dev-tab-btn-inactive'}`}
            onClick={() => {
              setDevLeftTab('git');
              fetch(`${BACKEND_URL}/api/git/status`).then(r => r.json()).then(d => setGitStatus(d.status || d.error || 'Clean working tree.'));
              fetch(`${BACKEND_URL}/api/git/system/status`).then(r => r.json()).then(d => setSystemGitStatus(d.status || d.error || 'Clean working tree.'));
            }}
          >🌿 Source Control</button>
          <button
            className={`dev-tab-btn ${devLeftTab === 'trainer' ? 'dev-tab-btn-active' : 'dev-tab-btn-inactive'}`}
            onClick={() => setDevLeftTab('trainer')}
          >🧠 Trainer</button>
        </div>

        {devLeftTab === 'chat' ? (
          <>
            <div className="message-feed">
              {devChatMessages.length === 0 && (
                <div style={{ color: '#555', fontSize: '0.85rem', marginTop: '20px', textAlign: 'center' }}>
                  Ask the Dev Assistant to write, fix, explain, or run code.<br />
                  Your current editor code is sent as context.
                </div>
              )}
              {devChatMessages.map((msg, idx) => (
                <div key={idx} className={`chat-message ${msg.role}`}>
                  <div className={`chat-avatar ${msg.role}`}>
                    {msg.role === 'user' ? 'B' : 'AI'}
                  </div>
                  <div className={`chat-bubble ${msg.role}`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isDevChatLoading && (
                <div style={{ color: '#38bdf8', fontSize: '0.82rem', fontStyle: 'italic', paddingLeft: '40px' }}>Working...</div>
              )}
              <div ref={chatEndRef} />
            </div>
            <div className="chat-input-area">
              <div className="chat-input-row">
                <textarea
                  className="chat-input"
                  placeholder="Ask the Dev Assistant to write, fix, or run code..."
                  value={devChatInput}
                  onChange={(e) => setDevChatInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleDevChatSubmit(); } }}
                />
                <button
                  className="send-button"
                  onClick={handleDevChatSubmit}
                  disabled={isDevChatLoading || !devChatInput.trim()}
                >Send</button>
              </div>
            </div>
          </>
        ) : devLeftTab === 'git' ? (
          <div className="git-panel">
            <h4 className="git-header">AI-BS System</h4>
            <pre className="git-output">{systemGitStatus}</pre>
            <div style={{ marginTop: '8px', marginBottom: '24px', display: 'flex', gap: '8px' }}>
              <button className="dev-btn" onClick={() => fetch(`${BACKEND_URL}/api/git/system/status`).then(r => r.json()).then(d => setSystemGitStatus(d.status || d.error || 'OK'))}>Refresh</button>
              <button className="dev-btn dev-btn-run" onClick={() => { setSystemGitStatus('Pulling...'); fetch(`${BACKEND_URL}/api/git/system/pull`, { method: 'POST' }).then(r => r.json()).then(d => setSystemGitStatus(d.stdout || d.stderr || d.error || 'Done.')); }}>⬇️ Pull</button>
              <button className="dev-btn dev-btn-run" onClick={() => { setSystemGitStatus('Pushing...'); fetch(`${BACKEND_URL}/api/git/system/push`, { method: 'POST' }).then(r => r.json()).then(d => setSystemGitStatus(d.stdout || d.stderr || d.error || 'Done.')); }}>⬆️ Push</button>
            </div>
            <h4 className="git-header" style={{ color: '#fff' }}>Projects Workspace</h4>
            <pre className="git-output" style={{ flex: 1 }}>{gitStatus}</pre>
            <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
              <button className="dev-btn" onClick={() => fetch(`${BACKEND_URL}/api/git/status`).then(r => r.json()).then(d => setGitStatus(d.status || d.error || 'OK'))}>Refresh</button>
              <button className="dev-btn dev-btn-run" onClick={() => setDevCodeInput(`import subprocess\nres = subprocess.run(["git", "add", "."], capture_output=True, text=True)\nprint(res.stdout)\nres2 = subprocess.run(["git", "commit", "-m", "Auto-commit from IDE"], capture_output=True, text=True)\nprint(res2.stdout)`)}>Auto-Commit Script</button>
            </div>
          </div>
        ) : (
          <div className="git-panel">
            {/* Archiving legacy trainer tab component call per Phase 18 */}
          </div>
        )}
      </div>

      {/* CODE EDITOR PANEL (RIGHT) */}
      <div className="dev-code-panel glass-panel">
        <div className="dev-header-row">
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>{devMode === 'visual' ? 'Visual Scripting' : 'Code Editor'}</h3>
            <div className="dev-toggle-group">
              <button className={`dev-toggle-btn ${devMode === 'text' ? 'active' : 'inactive'}`} onClick={() => setDevMode('text')}>Text Editor</button>
              <button className={`dev-toggle-btn ${devMode === 'visual' ? 'active' : 'inactive'}`} onClick={() => setDevMode('visual')}>Visual Scripting</button>
            </div>
          </div>
          {devMode === 'text' && (
            <select
              value={devCodeType}
              onChange={(e) => {
                const t = e.target.value;
                setDevCodeType(t);
                const extMap = { python: '.py', javascript: '.js', css: '.css', cpp: '.cpp', html: '.html', lua: '.lua', go: '.go' };
                const ext = extMap[t] || '.txt';
                if (!devFileName.endsWith(ext)) setDevFileName(`script${ext}`);
              }}
              className="dev-select"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="cpp">C++</option>
              <option value="lua">Lua</option>
              <option value="go">Go</option>
              <option value="html">HTML (WebGL)</option>
              <option value="css">CSS</option>
            </select>
          )}
        </div>

        {devMode === 'visual' ? (
          <div style={{ flex: 1, minHeight: '600px', display: 'flex', flexDirection: 'column' }}>
            <VisualScriptingTab onExportCode={(code, type) => {
              setDevCodeType(type);
              setDevCodeInput(code);
              setDevFileName(type === 'html' ? 'visual_scene.html' : 'visual_script.js');
              setDevMode('text');
            }} />
          </div>
        ) : (
          <>
            {/* File save row */}
            <div className="file-save-row">
              <input
                type="text"
                value={devFileName}
                onChange={(e) => setDevFileName(e.target.value)}
                placeholder="Filename (e.g. app.py)"
                className="file-input"
              />
              <button
                onClick={handleSaveFile}
                disabled={isSavingFile || !devFileName.trim()}
                className="file-save-btn"
                style={{ opacity: isSavingFile ? 0.6 : 1 }}
              >
                {isSavingFile ? 'Saving...' : '💾 Save File'}
              </button>
              {saveMessage && <span style={{ fontSize: '0.8rem', color: saveMessage.startsWith('✅') ? '#4ade80' : '#f87171' }}>{saveMessage}</span>}
            </div>

            {/* Monaco Editor */}
            <div className="editor-wrapper">
              <Editor
                height="100%"
                language={devCodeType === 'cpp' ? 'cpp' : devCodeType}
                theme="vs-dark"
                value={devCodeInput}
                onChange={(value) => setDevCodeInput(value || '')}
                onMount={handleEditorDidMount}
                options={{ minimap: { enabled: false }, fontSize: 14, wordWrap: 'on', scrollBeyondLastLine: false, automaticLayout: true }}
              />
            </div>

            {/* Run button */}
            <div className="run-row">
              {devCodeType !== 'css' && devCodeType !== 'html' && (
                <button
                  onClick={handleExecuteCode}
                  disabled={isExecutingCode}
                  className={`run-btn ${isExecutingCode ? 'running' : 'idle'}`}
                >
                  {isExecutingCode ? 'Running...' : `▶️ Run ${devCodeType}`}
                </button>
              )}
            </div>

            {/* Bottom output/terminal panel */}
            <div className="bottom-panel">
              <div className="bottom-tabs">
                <button
                  className={`bottom-tab-btn ${devBottomTab === 'output' ? 'active' : 'inactive'}`}
                  onClick={() => setDevBottomTab('output')}
                >Console Output</button>
                <button
                  className={`bottom-tab-btn ${devBottomTab === 'terminal' ? 'active' : 'inactive'}`}
                  onClick={() => setDevBottomTab('terminal')}
                >Terminal</button>
              </div>
              <div className="bottom-content">
                {devBottomTab === 'output' && (
                  <div className="console-output">
                    {devCodeType === 'html' ? (
                      <iframe
                        title="HTML Preview"
                        srcDoc={devCodeInput}
                        sandbox="allow-scripts allow-modals"
                        style={{ width: '100%', height: '100%', background: '#fff', border: 'none', borderRadius: '4px' }}
                      />
                    ) : !Array.isArray(devCodeOutput) || devCodeOutput.length === 0 ? (
                      <div style={{ color: '#888' }}>Ready. Click Run to execute.</div>
                    ) : (
                      devCodeOutput.map((step, idx) => (
                        <div key={idx} className={`console-step ${step.type === 'error' ? 'error' : step.type === 'complete' ? 'complete' : 'default'}`}>
                          <div className="console-step-header" style={{ color: step.type === 'error' ? '#ff6b6b' : step.type === 'complete' ? '#4ade80' : '#fff' }}>
                            {step.type === 'error' ? '🐛 Error' : step.type === 'complete' ? '✅ Complete' : step.type === 'stdout' ? '💻 Output' : '⚙️ System'}
                          </div>
                          <pre className="console-step-content">{step.content}</pre>
                        </div>
                      ))
                    )}
                  </div>
                )}
                {devBottomTab === 'terminal' && (
                  <TerminalPanel backendUrl={BACKEND_URL} />
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
