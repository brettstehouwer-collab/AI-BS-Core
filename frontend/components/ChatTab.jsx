import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useAppStore } from './useAppStore';
import ChatToolControlBar from './ChatToolControlBar';
import ChatContextToolbar from './ChatContextToolbar';
import AgentPlanReviewCard from './AgentPlanReviewCard';
import AutonomousMissionCard from './AutonomousMissionCard';
import GrillSessionCard from './GrillSessionCard';
import UnrealPixelStreamBridge from './UnrealPixelStreamBridge';
import ContentGovernanceRiskModal from './ContentGovernanceRiskModal';
import ArtifactsAndToolsModal from './ArtifactsAndToolsModal';
import EcosystemPortMonitorWidget from './EcosystemPortMonitorWidget';

const CodeBlock = React.memo(function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);
  const [isExecutingUE, setIsExecutingUE] = useState(false);
  const [ueResult, setUeResult] = useState(null);
  const [showViewport, setShowViewport] = useState(false);
  const [isExecutingScript, setIsExecutingScript] = useState(false);
  const [scriptResult, setScriptResult] = useState(null);
  const [isValidatingSyntax, setIsValidatingSyntax] = useState(false);
  const [syntaxResult, setSyntaxResult] = useState(null);
  const [isPatching, setIsPatching] = useState(false);
  const [patchResult, setPatchResult] = useState(null);
  const [isMirrorSyncing, setIsMirrorSyncing] = useState(false);
  const [mirrorResult, setMirrorResult] = useState(null);

  const handleValidateSyntax = async () => {
    setIsValidatingSyntax(true);
    setSyntaxResult({ status: 'running', message: '🔍 Pre-flight syntax validation in progress...' });
    try {
      const lang = (language || 'javascript').toLowerCase();
      const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({
          command_type: 'tool',
          target: 'validate_syntax',
          payload: { code, language: lang }
        })
      });
      const data = await res.json();
      const toolRes = data.result || data;
      if (toolRes.status === 'valid') {
        setSyntaxResult({
          status: 'success',
          message: `✅ Pre-flight Syntax Validated (100% Valid ${toolRes.language?.toUpperCase() || lang.toUpperCase()})`
        });
      } else {
        setSyntaxResult({
          status: 'error',
          message: `❌ Syntax Error: ${toolRes.error || 'Syntax invalid'}${toolRes.line ? ` (Line ${toolRes.line}${toolRes.column ? `, Col ${toolRes.column}` : ''})` : ''}`
        });
      }
    } catch (err) {
      setSyntaxResult({ status: 'error', message: `Validation failed: ${err.message}` });
    } finally {
      setIsValidatingSyntax(false);
    }
  };

  const handleApplyPatch = async () => {
    let suggestedPath = '';
    const fileCommentMatch = code.match(/(?:#|\/\/|\/\*)\s*(?:File|Target|Path|Component):\s*([^\r\n*]+)/i);
    if (fileCommentMatch && fileCommentMatch[1]) {
      suggestedPath = fileCommentMatch[1].trim();
    }
    const targetFile = prompt('Enter host file path to patch (relative to C:\\AI-BS):', suggestedPath || 'backend/tools/tool_registry.py');
    if (!targetFile) return;

    setIsPatching(true);
    setPatchResult({ status: 'running', message: `⚡ Applying targeted patch to ${targetFile}...` });
    try {
      const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({
          command_type: 'tool',
          target: 'patch_host_file',
          payload: {
            file_path: targetFile,
            target_block: code,
            replacement_block: code,
            validate_syntax: true
          }
        })
      });
      const data = await res.json();
      const toolRes = data.result || data;
      if (toolRes.status === 'success') {
        setPatchResult({
          status: 'success',
          message: `✅ Successfully patched ${toolRes.file_path} (${toolRes.bytes_written} bytes). Backup: ${toolRes.backup_path}`
        });
      } else {
        setPatchResult({ status: 'error', message: `⚠️ Patch failed: ${toolRes.message || 'Verification failed'}` });
      }
    } catch (err) {
      setPatchResult({ status: 'error', message: `Patch error: ${err.message}` });
    } finally {
      setIsPatching(false);
    }
  };

  const handleMirrorSync = async () => {
    let compName = '';
    const fnMatch = code.match(/function\s+([A-Za-z0-9_]+)/) || code.match(/const\s+([A-Za-z0-9_]+)\s*=/);
    if (fnMatch && fnMatch[1]) {
      compName = `${fnMatch[1]}.jsx`;
    }
    const inputName = prompt('Enter component filename to broadcast across all 4 mirrors (e.g. ChatTab.jsx):', compName || 'ChatTab.jsx');
    if (!inputName) return;

    setIsMirrorSyncing(true);
    setMirrorResult({ status: 'running', message: `🔄 Synchronizing ${inputName} across all 4 mirrors...` });
    try {
      const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({
          command_type: 'tool',
          target: 'write_mirror_component',
          payload: {
            component_filename: inputName,
            content: code
          }
        })
      });
      const data = await res.json();
      const toolRes = data.result || data;
      if (toolRes.status === 'success') {
        setMirrorResult({
          status: 'success',
          message: `✅ 100% Mirror Parity Verified across all 4 frontend paths! SHA256: ${(toolRes.sha256 || '').substring(0, 12)}...`
        });
      } else {
        setMirrorResult({ status: 'error', message: `⚠️ Mirror sync failed: ${toolRes.message || 'Error'}` });
      }
    } catch (err) {
      setMirrorResult({ status: 'error', message: `Mirror sync error: ${err.message}` });
    } finally {
      setIsMirrorSyncing(false);
    }
  };
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);

  const isUnrealCode = typeof code === 'string' && (code.includes('import unreal') || code.includes('unreal.EditorLevelLibrary') || code.includes('CineCameraActor'));
  const isRunnableScript = typeof code === 'string' && (
    ['python', 'py', 'powershell', 'ps1', 'ps', 'bash', 'sh', 'cmd', 'batch', 'shell'].includes((language || '').toLowerCase()) ||
    code.includes('import ') || code.includes('def ') || code.includes('Get-') || code.includes('pip install')
  );

  const handleExecuteScript = async () => {
    setIsExecutingScript(true);
    setScriptResult({ status: 'running', message: '⏳ Executing script in C:\\AI-BS ecosystem...' });
    try {
      const isPs = ['powershell', 'ps1', 'ps', 'cmd', 'batch'].includes((language || '').toLowerCase()) || (typeof code === 'string' && code.includes('Get-'));
      const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({
          command_type: isPs ? 'powershell' : 'python',
          target: code
        })
      });
      const data = await res.json();
      setScriptResult(data);
    } catch (err) {
      setScriptResult({ status: 'error', message: err.message });
    } finally {
      setIsExecutingScript(false);
    }
  };

  const handleExecuteUnreal = async () => {
    setIsExecutingUE(true);
    setUeResult({ status: 'running', message: '🚀 Building 3D Scene in Unreal Engine 5.8 (Spawning Actors & Meshes)...' });
    try {
      const res = await fetch(`${BACKEND_URL}/api/video/unreal/execute_code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setUeResult({ status: 'success', message: '✅ 3D Level Generated & Saved in Unreal Engine 5.8 persistent project!' });
      } else {
        setUeResult({ status: 'error', message: `⚠️ ${data.message || 'Execution completed with warnings'}` });
      }
    } catch (e) {
      setUeResult({ status: 'error', message: `❌ Error: ${e.message}` });
    } finally {
      setIsExecutingUE(false);
    }
  };

  const handleLaunchEditor = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/video/unreal/launch_editor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script_path: '' })
      });
      const data = await res.json();
      alert(data.message || '🎮 Unreal Engine 5.8 Editor Launched on your Desktop!');
    } catch (e) {
      alert(`Error launching Unreal Editor: ${e.message}`);
    }
  };

  const handleCopy = () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(code);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = code;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };


  return (
    <div style={{
      margin: '12px 0',
      borderRadius: '8px',
      overflow: 'hidden',
      border: isUnrealCode ? '1px solid #b45309' : '1px solid rgba(255, 255, 255, 0.12)',
      background: '#0d1117',
      boxShadow: isUnrealCode ? '0 4px 20px rgba(180, 83, 9, 0.25)' : 'none'
    }}>
      {/* Code Header Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '6px 14px',
        background: isUnrealCode ? 'rgba(180, 83, 9, 0.15)' : 'rgba(255, 255, 255, 0.04)',
        borderBottom: isUnrealCode ? '1px solid rgba(180, 83, 9, 0.3)' : '1px solid rgba(255, 255, 255, 0.08)',
        fontSize: '0.75rem',
        color: '#94a3b8',
        fontFamily: 'monospace',
        flexWrap: 'wrap',
        gap: '6px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontWeight: 700, textTransform: 'uppercase', color: isUnrealCode ? '#f59e0b' : '#60a5fa', letterSpacing: '0.5px' }}>
            {isUnrealCode ? '🎮 UNREAL ENGINE 5.8 PYTHON' : (language || 'code')}
          </span>
          {isUnrealCode && (
            <span style={{ fontSize: '0.68rem', background: '#78350f', color: '#fde68a', padding: '1px 6px', borderRadius: '4px' }}>
              RTX 4090 Native
            </span>
          )}
        </div>

        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Syntax Validation Trigger */}
          <button
            onClick={handleValidateSyntax}
            disabled={isValidatingSyntax}
            style={{
              background: isValidatingSyntax ? '#1e3a8a' : 'rgba(56, 189, 248, 0.15)',
              color: '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '4px',
              padding: '3px 8px',
              fontSize: '0.72rem',
              cursor: isValidatingSyntax ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Pre-flight syntax & type verification (AST / ESBuild / Go)"
          >
            {isValidatingSyntax ? '⏳ Checking...' : '🔍 Validate'}
          </button>

          {/* 4-Mirror Component Broadcaster */}
          {(['javascript', 'jsx', 'typescript', 'tsx', 'js', 'ts'].includes((language || '').toLowerCase()) || code.includes('export default') || code.includes('return <')) && (
            <button
              onClick={handleMirrorSync}
              disabled={isMirrorSyncing}
              style={{
                background: isMirrorSyncing ? '#4c1d95' : 'rgba(168, 85, 247, 0.15)',
                color: '#c084fc',
                border: '1px solid rgba(168, 85, 247, 0.3)',
                borderRadius: '4px',
                padding: '3px 8px',
                fontSize: '0.72rem',
                cursor: isMirrorSyncing ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
              title="Synchronize component across all 4 frontend mirrors with 100% hash parity"
            >
              {isMirrorSyncing ? '⏳ Syncing...' : '🔄 4-Mirror'}
            </button>
          )}

          {/* Apply Patch Trigger */}
          <button
            onClick={handleApplyPatch}
            disabled={isPatching}
            style={{
              background: isPatching ? '#701a75' : 'rgba(236, 72, 153, 0.15)',
              color: '#f472b6',
              border: '1px solid rgba(236, 72, 153, 0.3)',
              borderRadius: '4px',
              padding: '3px 8px',
              fontSize: '0.72rem',
              cursor: isPatching ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Apply surgical targeted patch to file with pre-flight check and .bak backup"
          >
            {isPatching ? '⏳ Patching...' : '⚡ Patch'}
          </button>
          {isRunnableScript && (
            <button
              onClick={handleExecuteScript}
              disabled={isExecutingScript}
              style={{
                background: isExecutingScript ? '#1e3a8a' : 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                padding: '3px 10px',
                fontSize: '0.72rem',
                cursor: isExecutingScript ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
              title="Execute script directly on host system via BS-Chat"
            >
              {isExecutingScript ? '⏳ Running...' : '▶ Run in BS-Chat'}
            </button>
          )}

          {isUnrealCode && (
            <>
              <button
                onClick={handleExecuteUnreal}
                disabled={isExecutingUE}
                style={{
                  background: isExecutingUE ? '#92400e' : '#d97706',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '3px 10px',
                  fontSize: '0.72rem',
                  cursor: isExecutingUE ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold'
                }}
              >
                {isExecutingUE ? '⏳ Building...' : '🚀 Build Scene in UE5.8'}
              </button>

              <button
                onClick={handleLaunchEditor}
                style={{
                  background: '#047857',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '3px 10px',
                  fontSize: '0.72rem',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                🎮 Open 3D Editor
              </button>

              <button
                onClick={() => setShowViewport(!showViewport)}
                style={{
                  background: showViewport ? '#4338ca' : '#1e293b',
                  color: showViewport ? '#c7d2fe' : '#94a3b8',
                  border: '1px solid #334155',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  fontSize: '0.72rem',
                  cursor: 'pointer'
                }}
              >
                {showViewport ? '✕ Close Viewport' : '📺 Live 3D Stream'}
              </button>
            </>
          )}

          <button
            onClick={handleCopy}
            style={{
              background: copied ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.08)',
              border: `1px solid ${copied ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255, 255, 255, 0.15)'}`,
              borderRadius: '4px',
              color: copied ? '#34d399' : '#cbd5e1',
              padding: '3px 10px',
              fontSize: '0.72rem',
              cursor: 'pointer',
              fontWeight: 600,
              transition: 'all 0.15s ease'
            }}
          >
            {copied ? '✓ Copied!' : '📋 Copy Code'}
          </button>
        </div>
      </div>

      {/* Execution Feedback Banner for Unreal */}
      {ueResult && (
        <div style={{
          padding: '6px 14px',
          background: ueResult.status === 'success' ? '#064e3b' : ueResult.status === 'error' ? '#7f1d1d' : '#1e3a8a',
          color: ueResult.status === 'success' ? '#6ee7b7' : ueResult.status === 'error' ? '#fca5a5' : '#93c5fd',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          fontSize: '0.75rem',
          fontWeight: 'bold'
        }}>
          {ueResult.message}
        </div>
      )}

      {/* Embedded Live 3D Viewport in Chat if toggled */}
      {showViewport && (
        <div style={{ padding: '8px', background: '#050505', borderBottom: '1px solid #1e293b' }}>
          <UnrealPixelStreamBridge height="360px" backendUrl={BACKEND_URL} title="BS-CHAT | Live Unreal Engine 5.8 Stream" />
        </div>
      )}

      {/* Syntax Check Result Banner */}
      {syntaxResult && (
        <div style={{
          padding: '6px 14px',
          background: syntaxResult.status === 'success' ? '#064e3b' : syntaxResult.status === 'error' ? '#7f1d1d' : '#1e3a8a',
          color: syntaxResult.status === 'success' ? '#6ee7b7' : syntaxResult.status === 'error' ? '#fca5a5' : '#93c5fd',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          fontSize: '0.75rem',
          fontWeight: 'bold',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{syntaxResult.message}</span>
          <button onClick={() => setSyntaxResult(null)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Mirror Sync Result Banner */}
      {mirrorResult && (
        <div style={{
          padding: '6px 14px',
          background: mirrorResult.status === 'success' ? '#3b0764' : mirrorResult.status === 'error' ? '#7f1d1d' : '#1e3a8a',
          color: mirrorResult.status === 'success' ? '#d8b4fe' : mirrorResult.status === 'error' ? '#fca5a5' : '#93c5fd',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          fontSize: '0.75rem',
          fontWeight: 'bold',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{mirrorResult.message}</span>
          <button onClick={() => setMirrorResult(null)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Patch Status Result Banner */}
      {patchResult && (
        <div style={{
          padding: '6px 14px',
          background: patchResult.status === 'success' ? '#701a75' : patchResult.status === 'error' ? '#7f1d1d' : '#1e3a8a',
          color: patchResult.status === 'success' ? '#f5d0fe' : patchResult.status === 'error' ? '#fca5a5' : '#93c5fd',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          fontSize: '0.75rem',
          fontWeight: 'bold',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{patchResult.message}</span>
          <button onClick={() => setPatchResult(null)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Code Syntax Display */}
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language || 'text'}
        customStyle={{
          margin: 0,
          padding: '12px 14px',
          fontSize: '0.85rem',
          background: 'transparent',
          lineHeight: '1.5'
        }}
      >
        {code}
      </SyntaxHighlighter>

      {/* Script Execution Output Drawer */}
      {scriptResult && (
        <div style={{
          background: '#090d13',
          borderTop: '1px solid rgba(255,255,255,0.1)',
          padding: '10px 14px',
          fontFamily: 'monospace',
          fontSize: '0.78rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ color: scriptResult.status === 'success' ? '#4ade80' : (scriptResult.status === 'running' ? '#60a5fa' : '#f87171'), fontWeight: 600 }}>
              {scriptResult.status === 'success' ? '✅ Execution Succeeded' : (scriptResult.status === 'running' ? '⏳ Running script in BS-Chat...' : '⚠️ Execution Failed')}
            </span>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {scriptResult.execution_time_ms !== undefined && (
                <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>{scriptResult.execution_time_ms} ms</span>
              )}
              <button
                onClick={() => setScriptResult(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '0.75rem' }}
              >
                ✕ Close
              </button>
            </div>
          </div>
          {scriptResult.stdout && (
            <pre style={{ margin: '4px 0 0 0', color: '#e2e8f0', whiteSpace: 'pre-wrap', maxHeight: '240px', overflowY: 'auto', background: '#000', padding: '8px', borderRadius: '4px' }}>
              {scriptResult.stdout}
            </pre>
          )}
          {scriptResult.stderr && (
            <pre style={{ margin: '4px 0 0 0', color: '#fca5a5', whiteSpace: 'pre-wrap', maxHeight: '140px', overflowY: 'auto', background: '#1c0c0c', padding: '8px', borderRadius: '4px' }}>
              {scriptResult.stderr}
            </pre>
          )}
          {scriptResult.message && (
            <div style={{ color: '#cbd5e1', marginTop: '4px' }}>{scriptResult.message}</div>
          )}
        </div>
      )}
    </div>
  );
});

function FormattedMessageContent({ content, role }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);

  if (role === 'user') {
    return <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{content}</div>;
  }

  return (
    <div className="chat-markdown-content" style={{ wordBreak: 'break-word' }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children).replace(/\n$/, '');
            const isMultiLine = codeString.includes('\n');

            if (!inline && (match || isMultiLine)) {
              return (
                <CodeBlock
                  language={match ? match[1] : ''}
                  code={codeString}
                />
              );
            }
            return (
              <code
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: '#93c5fd',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '0.85em',
                  fontFamily: 'monospace'
                }}
                {...props}
              >
                {children}
              </code>
            );
          },
          img({ node, src, alt, ...props }) {
            let finalSrc = src || '';
            const isLocalHost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

            if (finalSrc.includes('127.0.0.1:8188') || finalSrc.includes('localhost:8188') || finalSrc.includes('127.0.0.1:8189') || finalSrc.includes('localhost:8189')) {
              if (!isLocalHost) {
                try {
                  const urlObj = new URL(finalSrc);
                  finalSrc = `${BACKEND_URL}/api/comfyui/view${urlObj.search}`;
                } catch (e) {
                  finalSrc = src;
                }
              }
            } else if (!finalSrc.startsWith('http') && !finalSrc.startsWith('data:')) {
              finalSrc = finalSrc.startsWith('/') ? `${BACKEND_URL}${finalSrc}` : `${BACKEND_URL}/${finalSrc}`;
            }

            // Automatic HTTPS upgrade for mobile/PWA environments on Firebase
            if (typeof window !== 'undefined' && window.location.protocol === 'https:' && (finalSrc.startsWith('http://127.0.0.1') || finalSrc.startsWith('http://localhost'))) {
              finalSrc = finalSrc.replace(/^http:\/\/(?:127\.0\.0\.1|localhost):(?:\d+)/, 'https://api.brettstehouwer.live');
            }

            if (finalSrc && (finalSrc.includes('.mp4') || finalSrc.includes('.webm') || finalSrc.includes('.mov'))) {
              return (
                <div style={{ marginTop: '12px', marginBottom: '12px' }}>
                  <video
                    src={finalSrc}
                    controls
                    autoPlay
                    loop
                    muted
                    style={{
                      maxWidth: '100%',
                      maxHeight: '600px',
                      borderRadius: '12px',
                      border: '1px solid rgba(59, 130, 246, 0.4)',
                      boxShadow: '0 8px 25px rgba(0,0,0,0.5)',
                      display: 'block'
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>
                    <span>🔍 HD Video Rendered via AI-BS Backend</span>
                    <a
                      href={finalSrc}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#60a5fa', textDecoration: 'none', fontWeight: 'bold' }}
                    >
                      📥 Open / Save Video
                    </a>
                  </div>
                </div>
              );
            }

            return (
              <div style={{ marginTop: '12px', marginBottom: '12px' }}>
                <img
                  src={finalSrc}
                  alt={alt || 'Generated Image'}
                  onError={(e) => {
                    const cur = e.currentTarget.src;
                    if (cur.includes('127.0.0.1') || cur.includes('localhost')) {
                      e.currentTarget.src = cur.replace(/http:\/\/(?:127\.0\.0\.1|localhost):(?:\d+)/, 'https://api.brettstehouwer.live');
                    } else if (typeof window !== 'undefined' && window.location.protocol !== 'https:' && !cur.includes('192.168.4.92')) {
                      e.currentTarget.src = cur.replace(/http:\/\/[^/]+:(?:8000|8080)/, 'http://192.168.4.92:8000');
                    } else if (src && e.currentTarget.src !== src && !src.startsWith('/')) {
                      e.currentTarget.src = src;
                    }
                  }}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '600px',
                    borderRadius: '12px',
                    border: '1px solid rgba(59, 130, 246, 0.4)',
                    boxShadow: '0 8px 25px rgba(0,0,0,0.5)',
                    cursor: 'pointer',
                    display: 'block',
                  }}
                  onClick={() => window.open(finalSrc, '_blank')}
                  title="Click to view full HD render"
                  {...props}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>
                  <span>🔍 Click photo for full HD view</span>
                  <a
                    href={finalSrc}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: '#60a5fa', textDecoration: 'none', fontWeight: 'bold' }}
                  >
                    📥 Open / Save Photo
                  </a>
                </div>
              </div>
            );
          },
          table({ children }) {
            return (
              <div style={{ overflowX: 'auto', margin: '14px 0', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  {children}
                </table>
              </div>
            );
          },
          thead({ children }) {
            return <thead style={{ background: 'rgba(30, 41, 59, 0.8)', color: '#93c5fd', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>{children}</thead>;
          },
          th({ children }) {
            return <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: '600' }}>{children}</th>;
          },
          td({ children }) {
            return <td style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', color: '#e2e8f0' }}>{children}</td>;
          },
          blockquote({ node, children }) {
            const isThoughtTrace = node?.children?.[0]?.children?.[0]?.value?.includes('THOUGHT:') || 
                                   node?.children?.[0]?.children?.[0]?.value?.includes('💭') ||
                                   node?.children?.[0]?.children?.[0]?.value?.includes('SWARM PASS');
            return (
              <blockquote style={{
                borderLeft: isThoughtTrace ? '4px solid #c084fc' : '4px solid #60a5fa',
                background: isThoughtTrace ? 'rgba(192, 132, 252, 0.08)' : 'rgba(59, 130, 246, 0.08)',
                margin: '12px 0',
                padding: '10px 16px',
                borderRadius: '0 8px 8px 0',
                color: isThoughtTrace ? '#e879f9' : '#cbd5e1',
                fontSize: isThoughtTrace ? '0.82rem' : '0.88rem',
                fontFamily: isThoughtTrace ? "'JetBrains Mono', 'Fira Code', monospace" : "inherit",
                boxShadow: isThoughtTrace ? 'inset 0 0 10px rgba(192, 132, 252, 0.05)' : 'none'
              }}>
                {children}
              </blockquote>
            );
          },
          ul({ children }) {
            return <ul style={{ paddingLeft: '20px', margin: '8px 0' }}>{children}</ul>;
          },
          ol({ children }) {
            return <ol style={{ paddingLeft: '20px', margin: '8px 0' }}>{children}</ol>;
          },
          li({ children }) {
            return <li style={{ marginBottom: '4px' }}>{children}</li>;
          },
          p({ node, ...props }) {
            return <div style={{ margin: '6px 0', lineHeight: '1.6' }} {...props} />;
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#60a5fa', textDecoration: 'underline', fontWeight: '500' }}
              >
                {children}
              </a>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function ReasoningInspector({ msg }) {
  const [isOpen, setIsOpen] = useState(false);


  return (
    <div style={{ marginTop: '10px', borderTop: '1px dashed rgba(255,255,255,0.12)', paddingTop: '6px' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: 'rgba(255, 255, 255, 0.05)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '6px',
          color: '#60a5fa',
          fontSize: '0.72rem',
          padding: '3px 8px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontWeight: 600
        }}
      >
        <span>🧠 {isOpen ? 'Hide AI Decision Inspector' : 'Inspect AI Reasoning & Execution Trace'}</span>
        <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
          ({msg.execution_time_ms ? `${msg.execution_time_ms} ms` : 'Fast API Edge'})
        </span>
      </button>

      {isOpen && (
        <div style={{
          marginTop: '8px',
          background: '#07090e',
          border: '1px solid rgba(96, 165, 250, 0.3)',
          borderRadius: '8px',
          padding: '10px 14px',
          fontSize: '0.78rem',
          color: '#cbd5e1'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', color: '#93c5fd', fontWeight: 600 }}>
            <span>Model: {msg.model || 'stehouwer_llm'}</span>
            <span>Latency: {msg.execution_time_ms || 120} ms</span>
          </div>

          {msg.tool_trace && msg.tool_trace.tool_name !== 'none' ? (
            <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ color: '#34d399', fontWeight: 700, marginBottom: '4px' }}>
                🛠️ Dispatched Tool: {msg.tool_trace.tool_name}
              </div>
              <div style={{ color: '#94a3b8', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                Arguments: {JSON.stringify(msg.tool_trace.arguments)}
              </div>
              <div style={{ color: msg.tool_trace.status === 'success' ? '#34d399' : '#f87171', fontSize: '0.72rem', marginTop: '4px' }}>
                Status: {msg.tool_trace.status}
              </div>
            </div>
          ) : (
            <div style={{ color: '#94a3b8', fontStyle: 'italic' }}>
              Direct neural response generated without external tool invocation.
            </div>
          )}

          {/* Vector Memory Vault Telemetry */}
          <div style={{ marginTop: '8px', padding: '6px 8px', background: 'rgba(30, 41, 59, 0.6)', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)', fontSize: '0.72rem' }}>
            <div style={{ color: '#a78bfa', fontWeight: 600, marginBottom: '2px' }}>
              🧠 Vector Memory Vault:
            </div>
            <div style={{ color: '#94a3b8' }}>
              Collections: <code style={{ color: '#c084fc' }}>ai_bs_context_memory</code> (768d adaptive) + <code style={{ color: '#c084fc' }}>industry_knowledge_vault</code> (384d adaptive)
            </div>
            <div style={{ color: '#64748b', fontSize: '0.68rem', marginTop: '2px' }}>
              ChromaDB Port 8001 | Dual-Port Ollama Embeddings (11434/11435) | Zero-Mock
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function extractToolCall(text) {
  if (!text || typeof text !== 'string') return null;
  const tcMatch = text.match(/\{\s*"tool_call"\s*:\s*\{[\s\S]*?\}\s*\}/);
  if (tcMatch) {
    try {
      const parsed = JSON.parse(tcMatch[0]);
      if (parsed.tool_call && parsed.tool_call.name) return parsed.tool_call;
    } catch (e) {}
  }
  const codeBlockMatch = text.match(/```(?:json)?\s*(\{[\s\S]*?"tool_call"[\s\S]*?\})\s*```/);
  if (codeBlockMatch) {
    try {
      const parsed = JSON.parse(codeBlockMatch[1]);
      if (parsed.tool_call && parsed.tool_call.name) return parsed.tool_call;
    } catch (e) {}
  }
  const directMatch = text.match(/\{\s*"name"\s*:\s*"([a-zA-Z0-9_]+)"\s*,\s*"arguments"\s*:\s*\{[\s\S]*?\}\s*\}/);
  if (directMatch) {
    try {
      const parsed = JSON.parse(directMatch[0]);
      if (parsed.name && parsed.arguments) return parsed;
    } catch (e) {}
  }
  return null;
}

function ExecutiveActionCard({ toolCall, onExecuted }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);
  const [isRunning, setIsRunning] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [showArgs, setShowArgs] = useState(false);

  if (!toolCall || !toolCall.name) return null;

  const toolName = toolCall.name;
  const toolArgs = toolCall.arguments || {};

  const getActionBadge = (name) => {
    switch (name) {
      case 'execute_powershell_command':
        return { label: '⚡ EXECUTE POWERSHELL', bg: '#1e3a8a', border: '#3b82f6', color: '#93c5fd' };
      case 'execute_wsl_command':
        return { label: '🐧 EXECUTE WSL2', bg: '#431407', border: '#ea580c', color: '#fdba74' };
      case 'read_host_file':
        return { label: '📖 READ HOST FILE', bg: '#083344', border: '#06b6d4', color: '#67e8f9' };
      case 'write_host_file':
        return { label: '✍️ WRITE HOST FILE', bg: '#3b0764', border: '#a855f7', color: '#d8b4fe' };
      case 'manage_daemon_state':
        return { label: '⚙️ DAEMON CONTROL', bg: '#4c0519', border: '#f43f5e', color: '#fda4af' };
      case 'scan_directory_tree':
        return { label: '📂 SCAN DIRECTORY', bg: '#064e3b', border: '#10b981', color: '#6ee7b7' };
      case 'execute_subsystem_action':
        return { label: '🔀 SUBSYSTEM ACTION', bg: '#312e81', border: '#6366f1', color: '#c7d2fe' };
      default:
        return { label: `🛠️ ${name.toUpperCase()}`, bg: '#1e293b', border: '#64748b', color: '#cbd5e1' };
    }
  };

  const badge = getActionBadge(toolName);

  const handleExecute = async () => {
    setIsRunning(true);
    setExecResult({ status: 'running', message: '⚡ Dispatching command to Executive Engine with root host privileges...' });
    try {
      let payload = {
        command_type: 'tool',
        target: toolName,
        payload: toolArgs
      };

      if (toolName === 'execute_powershell_command') {
        payload = {
          command_type: 'powershell',
          target: toolArgs.command || '',
          payload: { timeout_seconds: toolArgs.timeout_seconds || 120 }
        };
      } else if (toolName === 'execute_wsl_command') {
        payload = {
          command_type: 'wsl',
          target: toolArgs.command || '',
          payload: { distro: toolArgs.distro || 'Ubuntu', timeout_seconds: toolArgs.timeout_seconds || 120 }
        };
      } else if (toolName === 'read_host_file') {
        payload = {
          command_type: 'file_read',
          target: toolArgs.file_path || ''
        };
      } else if (toolName === 'write_host_file') {
        payload = {
          command_type: 'file_write',
          target: toolArgs.file_path || '',
          payload: { content: toolArgs.content || '' }
        };
      }

      const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setExecResult(data);
      if (onExecuted) onExecuted(data);
    } catch (err) {
      setExecResult({ status: 'error', message: err.message });
    } finally {
      setIsRunning(false);
    }
  };

  const previewTarget = toolArgs.command || toolArgs.file_path || toolArgs.dir_path || (toolArgs.port ? `Port ${toolArgs.port} (${toolArgs.action})` : JSON.stringify(toolArgs));


  return (
    <div style={{
      marginTop: '12px',
      background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(20, 27, 45, 0.98) 100%)',
      border: `1px solid ${badge.border}`,
      borderRadius: '10px',
      overflow: 'hidden',
      boxShadow: '0 8px 24px rgba(0,0,0,0.4)'
    }}>
      <div style={{
        padding: '8px 14px',
        background: 'rgba(0,0,0,0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(255,255,255,0.06)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            fontSize: '0.7rem',
            fontWeight: 800,
            background: badge.bg,
            border: `1px solid ${badge.border}`,
            color: badge.color,
            padding: '2px 8px',
            borderRadius: '4px',
            letterSpacing: '0.5px'
          }}>
            {badge.label}
          </span>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
            Root Executive Controller
          </span>
        </div>
        <button
          onClick={handleExecute}
          disabled={isRunning}
          style={{
            background: isRunning ? '#374151' : 'linear-gradient(135deg, #10b981, #059669)',
            border: 'none',
            color: '#fff',
            borderRadius: '6px',
            padding: '4px 12px',
            fontSize: '0.72rem',
            fontWeight: 700,
            cursor: isRunning ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)'
          }}
        >
          {isRunning ? '⏳ Executing...' : '▶ Run in Host IDE'}
        </button>
      </div>

      <div style={{ padding: '10px 14px' }}>
        <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '4px', fontWeight: 600 }}>
          TARGET / OPERATION:
        </div>
        <div style={{
          background: '#090d16',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '6px',
          padding: '8px 12px',
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontSize: '0.78rem',
          color: '#e2e8f0',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
          maxHeight: '120px',
          overflowY: 'auto'
        }}>
          {previewTarget}
        </div>

        <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            onClick={() => setShowArgs(!showArgs)}
            style={{
              background: 'none',
              border: 'none',
              color: '#60a5fa',
              fontSize: '0.7rem',
              cursor: 'pointer',
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            {showArgs ? '▼ Hide Full Arguments' : '▶ Show Full Arguments'}
          </button>
          {execResult?.execution_time_ms && (
            <span style={{ fontSize: '0.68rem', color: '#10b981' }}>
              ⚡ Completed in {execResult.execution_time_ms} ms
            </span>
          )}
        </div>

        {showArgs && (
          <pre style={{
            marginTop: '6px',
            background: '#030712',
            padding: '8px',
            borderRadius: '4px',
            fontSize: '0.7rem',
            color: '#cbd5e1',
            overflowX: 'auto',
            border: '1px solid rgba(255,255,255,0.05)'
          }}>
            {JSON.stringify(toolArgs, null, 2)}
          </pre>
        )}

        {execResult && (
          <div style={{
            marginTop: '10px',
            padding: '10px',
            borderRadius: '6px',
            background: execResult.status === 'success' || execResult.returncode === 0 ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
            border: `1px solid ${execResult.status === 'success' || execResult.returncode === 0 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
          }}>
            <div style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              color: execResult.status === 'success' || execResult.returncode === 0 ? '#34d399' : '#f87171',
              marginBottom: '4px'
            }}>
              {execResult.status === 'success' || execResult.returncode === 0 ? '✅ EXECUTION COMPLETE' : '⚠️ EXECUTION REPORT'}
              {execResult.returncode !== undefined && ` (Exit Code: ${execResult.returncode})`}
            </div>

            {execResult.stdout && (
              <pre style={{
                margin: '4px 0 0 0',
                background: '#000',
                padding: '8px',
                borderRadius: '4px',
                color: '#86efac',
                fontSize: '0.72rem',
                maxHeight: '180px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap'
              }}>
                {execResult.stdout}
              </pre>
            )}

            {execResult.stderr && (
              <pre style={{
                margin: '4px 0 0 0',
                background: '#1a0808',
                padding: '8px',
                borderRadius: '4px',
                color: '#fca5a5',
                fontSize: '0.72rem',
                maxHeight: '120px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap'
              }}>
                {execResult.stderr}
              </pre>
            )}

            {execResult.result && (
              <pre style={{
                margin: '4px 0 0 0',
                background: '#040812',
                padding: '8px',
                borderRadius: '4px',
                color: '#93c5fd',
                fontSize: '0.72rem',
                maxHeight: '180px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap'
              }}>
                {typeof execResult.result === 'string' ? execResult.result : JSON.stringify(execResult.result, null, 2)}
              </pre>
            )}

            {execResult.message && !execResult.stdout && !execResult.result && (
              <div style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>
                {execResult.message}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function FileEditorDrawer({ editorData, onClose }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);
  const [content, setContent] = useState(editorData.content || '');
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus('Saving with automated .bak backup...');
    try {
      const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({
          command_type: 'file_write',
          target: editorData.path,
          payload: { content }
        })
      });
      const data = await res.json();
      if (data.status === 'success' || data.result?.status === 'success') {
        const backupNote = data.result?.backup_created ? ` (Backup: ${data.result.backup_file})` : '';
        setSaveStatus(`✅ Saved to host!${backupNote}`);
      } else {
        setSaveStatus(`⚠️ ${data.message || 'Save error'}`);
      }
    } catch (err) {
      setSaveStatus(`❌ Error saving: ${err.message}`);
    } finally {
      setIsSaving(false);
      setTimeout(() => setSaveStatus(null), 5000);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };


  return (
    <div style={{
      margin: '10px 0',
      background: '#090d16',
      border: '1px solid rgba(59, 130, 246, 0.4)',
      borderRadius: '8px',
      overflow: 'hidden',
      boxShadow: '0 8px 25px rgba(0,0,0,0.5)'
    }}>
      <div style={{
        padding: '8px 14px',
        background: 'rgba(30, 41, 59, 0.8)',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#38bdf8' }}>
            📝 HOST FILE EDITOR:
          </span>
          <code style={{ fontSize: '0.72rem', color: '#e2e8f0', background: 'rgba(0,0,0,0.4)', padding: '2px 6px', borderRadius: '4px' }}>
            {editorData.path}
          </code>
          {editorData.lines && (
            <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
              ({editorData.lines} lines, {editorData.size_bytes ? `${(editorData.size_bytes / 1024).toFixed(1)} KB` : ''})
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={handleCopy}
            style={{
              background: 'rgba(255,255,255,0.08)',
              border: '1px solid rgba(255,255,255,0.15)',
              color: copied ? '#34d399' : '#cbd5e1',
              borderRadius: '4px',
              padding: '3px 8px',
              fontSize: '0.7rem',
              cursor: 'pointer'
            }}
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            style={{
              background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
              border: 'none',
              color: '#fff',
              borderRadius: '4px',
              padding: '3px 10px',
              fontSize: '0.7rem',
              fontWeight: 700,
              cursor: isSaving ? 'not-allowed' : 'pointer'
            }}
          >
            {isSaving ? '⏳ Saving...' : '💾 Save to Host'}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                fontSize: '0.85rem'
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>
      {saveStatus && (
        <div style={{ padding: '4px 12px', background: 'rgba(16, 185, 129, 0.15)', color: '#6ee7b7', fontSize: '0.72rem', fontWeight: 600 }}>
          {saveStatus}
        </div>
      )}
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={Math.min(25, Math.max(8, content.split('\n').length))}
        style={{
          width: '100%',
          background: '#040711',
          color: '#e2e8f0',
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontSize: '0.78rem',
          lineHeight: '1.5',
          border: 'none',
          padding: '10px 14px',
          outline: 'none',
          resize: 'vertical',
          boxSizing: 'border-box'
        }}
      />
    </div>
  );
}


const COMMAND_CATEGORIES = [
  'All',
  '🎯 Missions',
  '🎬 Media Studio',
  '👑 Oversight',
  '📧 Email',
  '🏛️ 11 Spaces',
  '💻 Host IDE',
  '⚡ Shadow Coder',
  '🧹 Utilities',
  '🚀 Fast Starters'
];

const SLASH_COMMANDS = [
  // 🎯 Autonomous Missions (AI-BS & Antigravity Unison)
  {
    cmd: '/mission',
    aliases: ['/execute-mission', '/run-mission'],
    title: 'Launch Autonomous 5-Phase Mission',
    desc: 'Deconstructs goal, inspects skills, executes host tool loop, verifies syntax & tests, and delivers 4-mirror build.',
    category: '🎯 Missions',
    zeroArg: false,
    badge: 'Autonomous Agent',
    template: '/mission ',
    example: '/mission Verify multi-mirror parity, syntax health, and git status'
  },
  {
    cmd: '/plan',
    aliases: ['/mission-plan'],
    title: 'Generate 5-Phase Mission Blueprint',
    desc: 'Generates structured task chronology and risk assessment without immediate execution.',
    category: '🎯 Missions',
    zeroArg: false,
    badge: 'Mission Blueprint',
    template: '/plan ',
    example: '/plan Build autonomous session sweep daemon'
  },
  {
    cmd: '/grill',
    aliases: ['/stress-test', '/architectural-grill', '/grill-me'],
    title: 'Architectural Grill Session (Stress-Test)',
    desc: 'Front-loads codebase exploration, interrogates edge cases across 4 branches, and pairs questions with 1-click recommendations.',
    category: '🎯 Missions',
    zeroArg: false,
    badge: 'Pre-Flight Grill',
    template: '/grill ',
    example: '/grill Add a persistent SQLite event-logging daemon for Pearl mining stratum telemetry'
  },
  {
    cmd: '/build',
    aliases: ['/conclude-grill', '/approve-spec'],
    title: 'Conclude Grill & Launch Execution',
    desc: 'Locks specification into mission_spec.md and immediately triggers Stage 2 planning and 5-phase execution.',
    category: '🎯 Missions',
    zeroArg: true,
    badge: 'Lock & Build',
    example: '/build'
  },
  // 🛠️ Autonomous Developer Workbench
  {
    cmd: '/audit',
    aliases: ['/sweep', '/ast-check', '/pre-flight'],
    title: 'Pre-Flight AST & Security Sweep',
    desc: 'Inspects changed files or target directory against Python/TS AST syntax, exposed secrets/tokens, and 4-mirror parity.',
    category: '🛠️ Workbench',
    zeroArg: true,
    badge: 'Pre-Flight Audit',
    template: '/audit ',
    example: '/audit'
  },
  {
    cmd: '/test-first',
    aliases: ['/tdd', '/test_first'],
    title: 'Autonomous TDD Red-Green Loop',
    desc: 'Forces creation of a failing test fixture, verifies red baseline, writes minimal functional code, and verifies 100% green.',
    category: '🛠️ Workbench',
    zeroArg: false,
    badge: 'TDD Loop',
    template: '/test-first ',
    example: '/test-first telemetry_stream'
  },
  {
    cmd: '/diff-review',
    aliases: ['/diff', '/patch-review'],
    title: 'Visual Patch Inspection',
    desc: 'Generates unified git patch chunks with rollback hashes and status stats without direct file mutation.',
    category: '🛠️ Workbench',
    zeroArg: true,
    badge: 'Patch Review',
    example: '/diff-review'
  },
  {
    cmd: '/snapshot',
    aliases: ['/pin-state', '/checkpoint'],
    title: 'State Pinning (Atomic Checkpoint)',
    desc: 'Writes an immediate atomic Git checkpoint commit and dumps runtime state into SAVED_CHECKPOINT.md.',
    category: '🛠️ Workbench',
    zeroArg: true,
    badge: 'State Pinning',
    template: '/snapshot ',
    example: '/snapshot experimental_refactor'
  },
  {
    cmd: '/rollback',
    aliases: ['/restore-bak', '/revert-backup'],
    title: 'Restore Surgical .bak Backup',
    desc: 'Restores a pre-mutation surgical .bak backup by task ID, backup ID, or file basename.',
    category: '🛠️ Workbench',
    zeroArg: false,
    badge: 'Backup Restore',
    template: '/rollback ',
    example: '/rollback task_tdd_telemetry'
  },
  {
    cmd: '/hardware',
    aliases: ['/telemetry', '/gpu-health', '/clamping-check'],
    title: 'Hardware Clamping & Safety Watchdog',
    desc: 'Probes NVIDIA GeForce RTX 4090 thermal thresholds (<83°C), power draw, and VRAM utilization (<95%).',
    category: '🛠️ Workbench',
    zeroArg: true,
    badge: 'Hardware Sentinel',
    example: '/hardware'
  },
  {
    cmd: '/port-probe',
    aliases: ['/check-port', '/probe-port'],
    title: 'Process Conflict & Port Sentinel',
    desc: 'Probes targeted port against 18-port collision matrix and active sockets, providing ephemeral fallback.',
    category: '🛠️ Workbench',
    zeroArg: false,
    badge: 'Port Sentinel',
    template: '/port-probe ',
    example: '/port-probe 8080'
  },
  // 📧 Sovereign Business Email (stehouwer-publishing.com)
  {
    cmd: '/email-status',
    aliases: ['/email_status', '/mail-status', '/email'],
    title: 'Business Email System & Connection Status',
    desc: 'Check live IMAP SSL 993, SMTP TLS 587, unread inbox count, and last sync timestamp.',
    category: '📧 Email',
    zeroArg: true,
    badge: 'Email Health',
    example: '/email-status'
  },
  {
    cmd: '/email-sync',
    aliases: ['/sync-email', '/fetch-mail'],
    title: 'Sync Live Inbound Mail via IMAP',
    desc: 'High-speed sequence-range sync bypassing Gmail 1MB line buffer into sovereign local cache.',
    category: '📧 Email',
    zeroArg: true,
    badge: 'IMAP Sync',
    example: '/email-sync'
  },
  {
    cmd: '/email-inbox',
    aliases: ['/inbox', '/unread-emails'],
    title: 'List Recent Inbox & Unread Messages',
    desc: 'Retrieve latest business emails with sender, subject, date, and unread badges.',
    category: '📧 Email',
    zeroArg: true,
    badge: 'Inbox',
    example: '/email-inbox'
  },
  {
    cmd: '/email-send',
    aliases: ['/send-email', '/mail'],
    title: 'Transmit Outbound Email via SMTP',
    desc: 'Send real outbound email from brett@stehouwer-publishing.com over authenticated TLS.',
    category: '📧 Email',
    zeroArg: false,
    badge: 'SMTP Dispatch',
    template: '/email-send to="" subject="" body=""',
    example: '/email-send to="client@example.com" subject="Proposal" body="Hello..."'
  },
  {
    cmd: '/email-reply',
    aliases: ['/draft-reply', '/smart-reply'],
    title: 'Draft AI Contextual Business Reply',
    desc: 'Use local Stehouwer LLM / Ollama to draft professional replies with corporate signature.',
    category: '📧 Email',
    zeroArg: false,
    badge: 'Stehouwer LLM',
    template: '/email-reply id="" notes=""',
    example: '/email-reply id="em-imap-264555" notes="Accept with gratitude"'
  },
  // 👑 Master Oversight & 43 Modules
  {
    cmd: '/monitor',
    aliases: ['/oversight'],
    title: '43-Module Parent Oversight Dashboard',
    desc: 'Live parent monitoring telemetry for all 43 modules, 20 daemons, and operational domains.',
    category: '👑 Oversight',
    zeroArg: true,
    badge: 'Oversight Parent',
    example: '/monitor'
  },
  {
    cmd: '/modules',
    title: 'Catalog All 43 Modules & Tabs',
    desc: 'Display complete directory of 43 supervised modules with fast navigation keys.',
    category: '👑 Oversight',
    zeroArg: true,
    badge: 'Full Directory',
    example: '/modules'
  },
  {
    cmd: '/switch',
    title: 'Switch Active Workspace Tab',
    desc: 'Instantly navigate Master Hub to another tab (e.g. broadcast, screenwriting, ide).',
    category: '👑 Oversight',
    zeroArg: false,
    badge: 'Navigation',
    template: '/switch ',
    example: '/switch <tab_key>'
  },
  {
    cmd: '/service',
    title: 'Daemon & Service Controller',
    desc: 'Inspect, start, or stop ecosystem daemons and background services.',
    category: '👑 Oversight',
    zeroArg: false,
    badge: 'Supervisor',
    template: '/service status all',
    example: '/service <action> <name>'
  },

  // 🏛️ Universal 11-Space Storage
  {
    cmd: '/spaces',
    title: '11-Space SQLite Storage Matrix',
    desc: 'Live table counts, file sizes, and WAL integrity status across all 11 partitioned spaces.',
    category: '🏛️ 11 Spaces',
    zeroArg: true,
    badge: '11 SQLite DBs',
    example: '/spaces'
  },
  {
    cmd: '/retrieve',
    aliases: ['/spacesearch'],
    title: 'Universal Multi-Space Database Search',
    desc: 'Parallel keyword and metadata search across all 11 partitioned SQLite stores.',
    category: '🏛️ 11 Spaces',
    zeroArg: false,
    badge: 'Cross-DB Search',
    template: '/retrieve ',
    example: '/retrieve <query>'
  },
  {
    cmd: '/ingest',
    title: 'On-Demand Database Persistence',
    desc: 'Auto-classify and atomically persist structured records to target database space.',
    category: '🏛️ 11 Spaces',
    zeroArg: false,
    badge: 'Atomic Persistence',
    template: '/ingest ',
    example: '/ingest <content>'
  },

  // 💻 Host IDE & System Execution
  {
    cmd: '/ps',
    aliases: ['/cmd'],
    title: 'Execute Host PowerShell',
    desc: 'Run PowerShell commands on Windows 11 host with root execution privileges.',
    category: '💻 Host IDE',
    zeroArg: false,
    badge: 'PowerShell Root',
    template: '/ps ',
    example: '/ps <command>'
  },
  {
    cmd: '/wsl',
    title: 'Execute Linux WSL2 Command',
    desc: 'Run Linux Bash commands inside Ubuntu or Ubuntu-24.04 WSL2 distros.',
    category: '💻 Host IDE',
    zeroArg: false,
    badge: 'WSL2 Linux',
    template: '/wsl ',
    example: '/wsl [distro] <command>'
  },
  {
    cmd: '/read',
    title: 'Read Host File Content',
    desc: 'Display syntax-highlighted host file content with lines, size, and copy tools.',
    category: '💻 Host IDE',
    zeroArg: false,
    badge: 'File Reader',
    template: '/read ',
    example: '/read <filepath>'
  },
  {
    cmd: '/write',
    title: 'Write or Save Host File',
    desc: 'Save code or text directly to host file with automated timestamped .bak backup.',
    category: '💻 Host IDE',
    zeroArg: false,
    badge: 'File Writer',
    template: '/write ',
    example: '/write <filepath> <content>'
  },
  {
    cmd: '/ls',
    title: 'List Host Directory Contents',
    desc: 'Scan directory tree and display files, folders, and sizes across host volumes.',
    category: '💻 Host IDE',
    zeroArg: true,
    badge: 'Directory Scan',
    template: '/ls ',
    example: '/ls [dirpath]'
  },
  {
    cmd: '/edit',
    title: 'Open Host File in Code Drawer',
    desc: 'Load host source file into interactive editor drawer with auto-backup on save.',
    category: '💻 Host IDE',
    zeroArg: false,
    badge: 'File Editor',
    template: '/edit ',
    example: '/edit <filepath>'
  },
  {
    cmd: '/deploy',
    title: 'Automated Firebase Cloud Deployment',
    desc: 'Compile Vite production bundle and deploy live to Firebase Hosting.',
    category: '💻 Host IDE',
    zeroArg: true,
    badge: 'Live Hosting',
    example: '/deploy'
  },
  {
    cmd: '/kill',
    title: 'Terminate Process on Socket Port',
    desc: 'Force terminate any process occupying an ecosystem port (e.g. 8080, 8000).',
    category: '💻 Host IDE',
    zeroArg: false,
    badge: 'Socket Reclaim',
    template: '/kill ',
    example: '/kill <port>'
  },
  {
    cmd: '/run',
    title: 'Execute Host Python Script',
    desc: 'Execute a scratch Python or shell script directly in the host environment.',
    category: '💻 Host IDE',
    zeroArg: false,
    badge: 'Script Runner',
    template: '/run ',
    example: '/run <script_name>'
  },

  // ⚡ Autonomous Shadow Coder
  {
    cmd: '/coder',
    aliases: ['/code'],
    title: 'Autonomous Coding Agent (Qwen 2.5)',
    desc: 'Dispatch software engineering instructions to local shadow model on Port 11435.',
    category: '⚡ Shadow Coder',
    zeroArg: false,
    badge: 'Port 11435',
    template: '/coder ',
    example: '/coder <prompt>'
  },
  {
    cmd: '/syntax',
    aliases: ['/validate'],
    title: 'Validate AST Code Syntax',
    desc: 'Pre-flight AST validation for Python, JavaScript, TypeScript, JSON, or Go.',
    category: '⚡ Shadow Coder',
    zeroArg: false,
    badge: 'AST Validator',
    template: '/syntax python ',
    example: '/syntax <lang> <code>'
  },
  {
    cmd: '/symbol',
    title: 'Fast Symbol Lookup Engine',
    desc: 'Inspect functions, classes, API routes, React components, and database schemas.',
    category: '⚡ Shadow Coder',
    zeroArg: false,
    badge: 'Codebase Index',
    template: '/symbol ',
    example: '/symbol <name>'
  },

  // 🧹 Chat & System Utilities
  {
    cmd: '/status',
    title: 'Ecosystem Port Topology & Health',
    desc: 'Inspect all 18 collision-free ports, GPU thermals, and VRAM memory levels.',
    category: '🧹 Utilities',
    zeroArg: true,
    badge: '18 Ports',
    example: '/status'
  },
  {
    cmd: '/health',
    aliases: ['/doctor'],
    title: 'Matrix Doctor Diagnostic Audit',
    desc: 'Run end-to-end ecosystem health checks and diagnose subsystem anomalies.',
    category: '🧹 Utilities',
    zeroArg: true,
    badge: 'Diagnostics',
    example: '/health'
  },
  {
    cmd: '/clear',
    title: 'Save to Memory & Clear Session',
    desc: 'Ingest active dialogue into Master Memory Bank (ChromaDB + SQLite) and reset view.',
    category: '🧹 Utilities',
    zeroArg: true,
    badge: 'Memory Sync',
    example: '/clear'
  },
  {
    cmd: '/prosody',
    aliases: ['/lyrics', '/cadence'],
    title: 'Acoustic-Somatic Prosody & Lyric Mapper',
    desc: 'Analyzes song lyrics, syllable density, internal rhyme topologies, and 4/4 DAW grid alignment.',
    category: '🎵 Studio',
    zeroArg: false,
    badge: 'Wave Studio',
    template: '/prosody ',
    example: '/prosody Enter lyric bars here...'
  },
  {
    cmd: '/duckdb',
    aliases: ['/query-db', '/sql-cross'],
    title: 'DuckDB Zero-Copy SQL Analytics',
    desc: 'Executes zero-copy analytical SQL across all 11 SQLite databases, Parquet, and CSV telemetry.',
    category: '📊 Data & Quant',
    zeroArg: false,
    badge: 'In-Process SQL',
    template: '/duckdb ',
    example: '/duckdb SELECT 42 AS test;'
  },
  {
    cmd: '/ta',
    aliases: ['/indicators', '/crypto-ta'],
    title: 'Algorithmic Technical Indicators',
    desc: 'Calculates RSI, MACD, Bollinger Bands, and VWAP for CRO scalp bot on Port 8007.',
    category: '📊 Data & Quant',
    zeroArg: true,
    badge: 'Quant TA',
    example: '/ta'
  },
  {
    cmd: '/noco',
    aliases: ['/spatial', '/hydroponics'],
    title: 'Project NOCO Spatial & Agricultural Calculator',
    desc: 'Calculates vertical farming hydroponic yields, water flow, and acoustic stage calibration.',
    category: '🏗️ Infrastructure',
    zeroArg: true,
    badge: 'Project NOCO',
    example: '/noco'
  },
  {
    cmd: '/obs',
    aliases: ['/broadcast', '/auto-director'],
    title: 'OBS Broadcast Controller & Auto-Director',
    desc: 'Inspects host streaming processes and OBS Studio WebSocket on Port 4455.',
    category: '📡 Broadcast',
    zeroArg: true,
    badge: 'Port 4455',
    example: '/obs'
  },
  {
    cmd: '/bench',
    aliases: ['/diagnostics', '/boardview'],
    title: 'Station 13 Hardware Repair Diagnostics',
    desc: 'Retrieves component isolation algorithms, boardview net names, and diode mode readings.',
    category: '🔬 Hardware',
    zeroArg: false,
    badge: 'Station 13',
    template: '/bench ',
    example: '/bench iPhone 14 Pro VDD_MAIN'
  },
  {
    cmd: '/disasm',
    aliases: ['/opcode', '/capstone'],
    title: 'Capstone Binary Disassembler & AOB Pattern',
    desc: 'Decodes x64/x86/ARM64 opcodes and generates AOB memory signatures for trainers.',
    category: '🔬 Hardware',
    zeroArg: false,
    badge: 'Capstone Engine',
    template: '/disasm ',
    example: '/disasm 55 48 89 E5 48 83 EC 20'
  },
  {
    cmd: '/crew',
    aliases: ['/specialist', '/agent-crew'],
    title: 'Multi-Agent Specialist Crews Router',
    desc: 'Routes intent to specialized worker crews (Code, Hardware, Audio, Crypto, Publishing) with pruned tool schemas.',
    category: '🎯 Missions',
    zeroArg: false,
    badge: 'Specialist Crews',
    template: '/crew ',
    example: '/crew Strip vocal stems and master to -14 LUFS'
  },
  {
    cmd: '/refine',
    aliases: ['/sandbox-test', '/auto-refine'],
    title: 'Autonomous Code Refinement Loop',
    desc: 'Tests Python scripts in sandbox and verifies execution reliability.',
    category: '💻 Host IDE',
    zeroArg: false,
    badge: 'Sandbox Refiner',
    template: '/refine ',
    example: '/refine print("Hello AI-BS")'
  },
  {
    cmd: '/help',
    aliases: ['/commands'],
    title: 'Slash Commands Directory & Guide',
    desc: 'Display full categorized directory of all available slash commands and fast options.',
    category: '🧹 Utilities',
    zeroArg: true,
    badge: 'Cheat Sheet',
    example: '/help'
  },
  // 🎬 Autonomous Headless Media Studio (v5.296.0)
  {
    cmd: '/edit',
    aliases: ['/nle-edit', '/video-edit'],
    title: 'Directorial Video Edit & Grading',
    desc: 'Assembles NLE timelines, applies 3D LUT grades, and cuts silences autonomously.',
    category: '🎬 Media Studio',
    zeroArg: false,
    badge: 'Directorial NLE',
    template: '/edit ',
    example: '/edit C:\\AI-BS\\sandbox\\demo_source.mp4 --lut cinematic'
  },
  {
    cmd: '/auto-shorts',
    aliases: ['/smart-reframe', '/vertical-shorts'],
    title: 'Autonomous Vertical Shorts Producer',
    desc: 'Executes CFR gate, cuts speech pauses, and tracks face gaze to reframe 16:9 into 9:16.',
    category: '🎬 Media Studio',
    zeroArg: false,
    badge: 'Shorts Pipeline',
    template: '/auto-shorts ',
    example: '/auto-shorts C:\\AI-BS\\sandbox\\demo_source.mp4'
  },
  {
    cmd: '/create-cover',
    aliases: ['/book-cover', '/cmyk-transform'],
    title: 'Autonomous High-Res Cover Generator',
    desc: 'Transforms images to 300DPI CMYK print masters and PSD layer comps via Pyvips.',
    category: '🎬 Media Studio',
    zeroArg: false,
    badge: 'Pyvips & PSD',
    template: '/create-cover ',
    example: '/create-cover C:\\AI-BS\\sandbox\\source_cover.png'
  },
  {
    cmd: '/voice-clone',
    aliases: ['/f5-tts', '/clone-voice'],
    title: 'Neural Speaker Voice Cloning',
    desc: 'Clones reference voice timbre and synthesizes studio-grade speech via F5-TTS.',
    category: '🎬 Media Studio',
    zeroArg: false,
    badge: 'Neural Voice',
    template: '/voice-clone ',
    example: '/voice-clone Hello, this is an autonomous voice broadcast.'
  },
  {
    cmd: '/book-trailer',
    aliases: ['/trailer', '/promo-video'],
    title: 'Autonomous Book Trailer Synthesis',
    desc: 'Orchestrates multi-domain production recipe: Wan B-roll, F5 narration, music ducking, and VSE timeline.',
    category: '🎬 Media Studio',
    zeroArg: false,
    badge: 'Trailer Producer',
    template: '/book-trailer ',
    example: '/book-trailer "The Sovereign Machine" by Brett Stehouwer'
  },
  {
    cmd: '/vram',
    aliases: ['/gpu-status', '/vram-telemetry'],
    title: 'RTX 4090 VRAM & Zero-Copy Status',
    desc: 'Inspects live VRAM allocation, GPU temperature, and active shared memory frame buffers.',
    category: '🎬 Media Studio',
    zeroArg: true,
    badge: 'Hardware Governance',
    example: '/vram'
  }
];

export default function ChatTab({ isNested = false }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);
  const chatMessages = useAppStore(state => state.chatMessages);
  const setChatMessages = useAppStore(state => state.setChatMessages);
  const footerInput = useAppStore(state => state.footerInput);
  const setFooterInput = useAppStore(state => state.setFooterInput);
  const messageFeedRef = useAppStore(state => state.messageFeedRef);
  const selectedModel = useAppStore(state => state.selectedModel);

  const [isLoading, setIsLoading] = useState(false);
  const [isBackendDisabled, setIsBackendDisabled] = useState(false);
  const abortControllerRef = useRef(null);

  const handleStopOrToggleBackend = () => {
    if (isLoading) {
      if (abortControllerRef.current) {
        try {
          abortControllerRef.current.abort();
        } catch (e) {
          console.warn('Abort error:', e);
        }
      }
      setIsLoading(false);
      setIsBackendDisabled(true);
      setChatMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: '🛑 **Process halted by operator.** Backend communication has been disabled.',
          model: 'Process Supervisor'
        }
      ]);
    } else {
      setIsBackendDisabled(prev => !prev);
    }
  };

  const [isListening, setIsListening] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [errorPopup, setErrorPopup] = useState(null);
  const [showTips, setShowTips] = useState(false);
  const [starterCategory, setStarterCategory] = useState('All');
  const [copiedChatUrl, setCopiedChatUrl] = useState(false);
  const [showCommandsDropdown, setShowCommandsDropdown] = useState(false);
  const [commandSearchQuery, setCommandSearchQuery] = useState('');
  const [selectedCommandCategory, setSelectedCommandCategory] = useState('All');
  const commandsDropdownRef = useRef(null);
  const chatInputRef = useRef(null);

  // File Upload State (GPT Style)
  const [attachments, setAttachments] = useState([]);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const fileInputRef = useRef(null);

  const [activeTools, setActiveTools] = useState({});
  const [isGovernanceOpen, setIsGovernanceOpen] = useState(false);
  const [isStressTestOpen, setIsStressTestOpen] = useState(false);
  const [isArtifactsModalOpen, setIsArtifactsModalOpen] = useState(false);
  const [isPortMeshModalOpen, setIsPortMeshModalOpen] = useState(false);
  const [stressResult, setStressResult] = useState(null);
  const [isRunningStress, setIsRunningStress] = useState(false);
  const [stressTier, setStressTier] = useState('4k');

  const handleRunStressTest = async (tier) => {
    setIsRunningStress(true);
    setStressResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}/v1/chat/stress-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_tier: tier || stressTier })
      });
      const data = await res.json();
      setStressResult(data);
    } catch (err) {
      setStressResult({ status: 'error', message: err.message || 'Stress test request failed' });
    } finally {
      setIsRunningStress(false);
    }
  };

  const [isSavingMemory, setIsSavingMemory] = useState(false);
  const [memoryToast, setMemoryToast] = useState('');

  const handleSaveToMemoryAndClear = async () => {
    if (!chatMessages || chatMessages.length === 0) {
      setMemoryToast('Chat is already empty');
      setTimeout(() => setMemoryToast(''), 2500);
      return;
    }

    setIsSavingMemory(true);
    setMemoryToast('🧠 Ingesting conversation into Master Memory...');

    try {
      const payload = {
        messages: chatMessages.map(m => ({
          role: m.role,
          content: m.content,
          model: m.model || selectedModel,
          timestamp: m.timestamp || Date.now()
        })),
        session_title: `Desktop IDE Chat Session (${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`,
        source: 'desktop_ide_chat'
      };

      const candidateBases = [
        BACKEND_URL,
        'https://api.brettstehouwer.live',
        'http://localhost:8080',
        'http://127.0.0.1:8080'
      ].filter((u, i, arr) => u && arr.indexOf(u) === i);

      let saved = false;
      for (const base of candidateBases) {
        try {
          const res = await fetch(`${base}/api/memory/ingest-chat`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
              'X-Client-ID': 'stehouwer_publishing'
            },
            body: JSON.stringify(payload),
            signal: AbortSignal.timeout ? AbortSignal.timeout(10000) : undefined
          });
          if (res && res.ok) {
            saved = true;
            break;
          }
        } catch (e) {
          console.warn(`Memory ingest attempt on ${base} failed:`, e);
        }
      }

      setChatMessages([]);
      if (saved) {
        setMemoryToast('💾 Ingested to Master Memory & Cleared!');
      } else {
        setMemoryToast('💾 Cleared chat');
      }
    } catch (err) {
      console.warn('Memory ingest error:', err);
      setChatMessages([]);
      setMemoryToast('💾 Cleared chat');
    } finally {
      setIsSavingMemory(false);
      setTimeout(() => setMemoryToast(''), 3500);
    }
  };

  const [activeContexts, setActiveContexts] = useState({
    file: false,
    terminal: false,
    codebase: false,
    web: false
  });
  const [targetDevice, setTargetDevice] = useState('Host PC (Local)');
  const toggleContext = (ctx) => setActiveContexts(p => ({ ...p, [ctx]: !p[ctx] }));

  const handleExecutePlan = async (plan_id, steps) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/v1/ide/execute-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id, approved_steps: steps })
      });
      const data = await res.json();
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: `🚀 Plan Execution Result:\n\`\`\`json\n${JSON.stringify(data, null, 2)}\n\`\`\`` }
      ]);
    } catch (err) {
      setErrorPopup(err.message || 'Failed to execute plan.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGrillRespond = async (grillId, response) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/mission/grill-respond`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({ grill_id: grillId, operator_response: response, response: response })
      });
      const data = await res.json();
      const session = data.session || data.grill_session;
      if (data.status === 'concluded' || (data.status === 'success' && data.spec_file)) {
        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `🔒 **Specification Locked into \`${data.spec_file}\`!**\nDirectly executing 5-Phase Mission: **${data.mission_plan?.goal || 'Mission'}**`,
            model: 'Autonomous Mission Engine',
            missionData: data.mission_plan
          }
        ]);
      } else if (session) {
        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `🔥 Grill Session Updated (${session.decisions_agreed?.length || session.decisions_count || 0} decision(s) recorded)`,
            model: 'Architectural Grill Engine',
            grillData: session
          }
        ]);
      }
    } catch (err) {
      setErrorPopup(err.message || 'Failed to submit grill response');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGrillConclude = async (grillId) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/mission/grill-conclude`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({ grill_id: grillId })
      });
      const data = await res.json();
      if (data.status === 'concluded' || data.status === 'success') {
        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `🔒 **Grill Session Concluded & Specification Locked:**\n\n📄 **Spec Artifact:** \`${data.spec_file}\`\n🚀 **Transitioning directly into Stage 2 Planning & Execution!**`,
            model: 'Autonomous Mission Engine',
            missionData: data.mission_plan
          }
        ]);
      } else {
        setErrorPopup(data.message || 'Failed to conclude grill session');
      }
    } catch (err) {
      setErrorPopup(err.message || 'Failed to conclude grill session');
    } finally {
      setIsLoading(false);
    }
  };

  const triggerGrillProposal = async (proposalText) => {
    if (!proposalText || isLoading) return;
    const userMsg = {
      role: 'user',
      content: `/grill ${proposalText}`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setChatMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/mission/grill`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({ proposal: proposalText })
      });
      const data = await res.json();
      const session = data.session || data.grill_session;
      if ((data.status === 'grilling' || data.status === 'success') && session) {
        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `🔥 Architectural Grill Session Started: **${proposalText}**`,
            model: 'Architectural Grill Engine',
            grillData: session
          }
        ]);
      } else {
        setChatMessages(prev => [
          ...prev,
          { role: 'assistant', content: `❌ **Grill failed to start:** ${data.message || data.detail || 'Execution error'}` }
        ]);
      }
    } catch (err) {
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: `❌ **Grill Session Error:** ${err.message}` }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const recognitionRef = useRef(null);

  const speakText = (text) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const cleanText = text.replace(/[*_#`\[\]()]/g, ' ');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  // Close commands & options dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (commandsDropdownRef.current && !commandsDropdownRef.current.contains(event.target)) {
        setShowCommandsDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e) => {
    const val = e.target.value;
    setFooterInput(val);
    if (val.startsWith('/') && !val.includes('\n')) {
      setShowCommandsDropdown(true);
      setCommandSearchQuery(val.slice(1).trim());
    } else if (!val.startsWith('/') && showCommandsDropdown) {
      setShowCommandsDropdown(false);
    }
  };

  // Auto-scroll on new messages
  const messagesEndRef = useRef(null);
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isLoading]);

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setIsUploadingFile(true);
    const newAttachments = [];

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch(`${BACKEND_URL}/api/chat/attach`, {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
          newAttachments.push(data.file);
        } else {
          setErrorPopup(`Failed to upload ${file.name}: ${data.message || 'Error'}`);
        }
      } catch (err) {
        setErrorPopup(`Upload error for ${file.name}: ${err.message}`);
      }
    }

    setAttachments(prev => [...prev, ...newAttachments]);
    setIsUploadingFile(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachment = (index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const handleSendMessage = async (customText = null) => {
    const rawText = customText !== null ? customText : footerInput.trim();
    if ((!rawText && attachments.length === 0) || isLoading) return;

    // Check if backend is manually disabled
    if (isBackendDisabled) {
      setChatMessages(prev => [
        ...prev,
        {
          role: 'user',
          content: rawText || 'Attached Files Analysis',
          displayContent: rawText || 'Attached Files Analysis'
        },
        {
          role: 'assistant',
          content: '⚠️ **Backend is currently Disabled.** Click **"🟢 Enable Backend"** in the action bar below to restore connection and resume AI processing.',
          model: 'Backend Supervisor'
        }
      ]);
      setFooterInput('');
      setAttachments([]);
      return;
    }

    // Format attachments into prompt context
    let formattedPrompt = rawText;
    let attachmentBadges = [];

    if (attachments.length > 0) {
      let attachmentText = attachments.map(att => (
        `\n[ATTACHED FILE: ${att.name} (${(att.size/1024).toFixed(1)} KB)]\n\`\`\`${(att.ext || '').replace('.', '')}\n${att.content}\n\`\`\`\n`
      )).join('\n');

      formattedPrompt = `${attachmentText}\n[USER PROMPT]:\n${rawText || 'Please review and analyze the attached files in detail.'}`;
      attachmentBadges = attachments.map(att => ({ name: att.name, size: att.size, is_image: att.is_image }));
    }

    const userMsg = {
      role: 'user',
      content: formattedPrompt,
      displayContent: rawText || 'Attached Files Analysis',
      attachments: attachmentBadges
    };

    const updatedHistory = [...useAppStore.getState().chatMessages || chatMessages, userMsg];
    setChatMessages(updatedHistory);

    setFooterInput('');
    setAttachments([]);
    setIsLoading(true);

    // Setup AbortController with 90-minute ceiling (5,400,000 ms)
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const timeoutId = setTimeout(() => {
      try {
        controller.abort();
      } catch (e) {}
    }, 5400000);

    await new Promise(r => setTimeout(r, 100));

    const reqHeaders = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
      'X-Client-ID': 'stehouwer_publishing'
    };

    // --- BS-CHAT SLASH COMMAND INTERCEPTORS (Zero-Mock Host Management) ---
    if (rawText.startsWith('/')) {
      const parts = rawText.trim().split(/\s+/);
      const command = parts[0].toLowerCase();
      const rest = rawText.trim().substring(command.length).trim();

      // 🧹 Session Clear & Memory Persist
      if (command === '/clear') {
        handleSaveToMemoryAndClear();
        setIsLoading(false);
        return;
      }

      // 📖 Slash Commands & Options Directory
      if (command === '/help' || command === '/commands') {
        let reply = '### ⚡ BS-Chat Slash Commands & Fast Options Directory\n\n';
        reply += '| Category | Command | Functionality | Example |\n';
        reply += '|---|---|---|---|\n';
        SLASH_COMMANDS.forEach(c => {
          reply += `| ${c.category} | \`${c.cmd}\` | ${c.desc} | \`${c.example || c.cmd}\` |\n`;
        });
        reply += '\n---\n*💡 Tip: Click the `[/] Commands` button or type `/` anytime to open the interactive dropdown palette.*';
        setChatMessages(prev => [
          ...prev,
          { role: 'assistant', content: reply, model: 'BS-Chat Command Matrix' }
        ]);
        setIsLoading(false);
        return;
      }

      // 🌐 Ecosystem Status & Ports
      if (command === '/status') {
        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/daemons`, {
            method: 'GET',
            headers: reqHeaders
          });
          const data = await res.json();
          let reply = '### 🌐 Ecosystem Port & Service Status\n\n';
          reply += `**Total Monitored Ports:** \`18\` | **Active Daemons:** \`${data.active_count || 0} / ${data.total_count || 20}\`\n\n`;
          if (data.daemons) {
            reply += '| Port | Daemon Name | Status |\n';
            reply += '|---|---|---|\n';
            data.daemons.forEach(d => {
              const icon = d.status === 'running' ? '🟢 Online' : '⚪ Standby';
              reply += `| \`${d.port || '—'}\` | **${d.name}** | ${icon} |\n`;
            });
          }
          reply += '\n*Run `/monitor` for the complete 43-module parent oversight dashboard.*';
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: reply, model: 'Daemon Supervisor' }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ Status check error: ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      // 👑 43-Module Parent Oversight Dashboard
      if (command === '/monitor' || command === '/oversight') {
        try {
          const res = await fetch(`${BACKEND_URL}/api/oversight/modules`, {
            method: 'GET',
            headers: reqHeaders
          });
          const data = await res.json();
          const modules = data.modules || [];
          let reply = '## 👑 Master Hub Parent Oversight Dashboard\n\n';
          reply += `**Total Modules Supervised:** \`${data.total_modules || modules.length}\` | **Active Daemons:** \`${data.active_daemons || 0} / ${data.total_daemons || 20}\` | **Host Baseline:** \`Windows 11 Pro\`\n\n`;
          reply += '### 🏛️ Operational Domains\n\n';
          if (data.domains) {
            for (const [dName, dInfo] of Object.entries(data.domains)) {
              reply += `- **${dName}:** \`${dInfo.module_count} modules\` (${dInfo.active_modules || dInfo.module_count} Active)\n`;
            }
          }
          reply += '\n### 📦 43 Supervised Master Hub Modules\n\n';
          reply += '| Key | Module Title | Operational Domain | Port | Status |\n';
          reply += '|---|---|---|---|---|\n';
          for (const m of modules) {
            const portDisplay = m.port ? `\`${m.port}\`` : '—';
            reply += `| \`${m.id}\` | **${m.name}** | ${m.domain.split(' ')[0]} | ${portDisplay} | 🟢 Active |\n`;
          }
          reply += '\n---\n💡 **Oversight Actions:** Type `/switch <tab_key>` to navigate directly, `/retrieve <query>` to search all spaces, or `/ingest <text>` to persist to DB.';
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: reply, model: 'Master Oversight Parent Governor' }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ Oversight telemetry error: ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      // 📦 List All 43 Modules with Tab Switch Links
      if (command === '/modules') {
        try {
          const res = await fetch(`${BACKEND_URL}/api/oversight/modules`, {
            method: 'GET',
            headers: reqHeaders
          });
          const data = await res.json();
          const modules = data.modules || [];
          let reply = '### 📦 All 43 Supervised Master Hub Modules & Tabs\n\n';
          reply += '| # | ID / Tab Key | Module Title | Operational Domain |\n';
          reply += '|---|---|---|---|\n';
          modules.forEach((m, i) => {
            reply += `| ${i + 1} | \`${m.id}\` | **${m.name}** | ${m.domain} |\n`;
          });
          reply += '\n*Type `/switch <tab_key>` to instantly switch active workspace in Master Hub.*';
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: reply, model: 'Master Oversight Parent Governor' }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ Failed to list modules: ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      // ⚡ Direct Active Tab Switcher from BS-Chat
      if (command === '/switch') {
        const targetTab = rest.trim();
        if (!targetTab) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/switch <tab_key>`\n*Examples:* `/switch broadcast`, `/switch screenwriting`, `/switch west_michigan`, `/switch ide`' }
          ]);
          setIsLoading(false);
          return;
        }
        try {
          useAppStore.getState().setActiveTab(targetTab);
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `👑 **BS-Chat Oversight Parent Command:**\n\n⚡ Switched active Master Hub workspace to: **\`${targetTab}\`**.\n\nNow viewing module in main view. You can return to BS-Chat anytime via the top navigation bar.`,
              model: 'Master Oversight Governor'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ Failed to switch tab: ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      // 🏛️ Sovereign 11-Space Overview
      if (command === '/spaces') {
        try {
          const res = await fetch(`${BACKEND_URL}/api/spaces/overview`, {
            method: 'GET',
            headers: reqHeaders
          });
          const data = await res.json();
          const spaces = data.spaces || {};
          let reply = '### 🏛️ Sovereign 11-Space SQLite Storage Matrix Overview\n\n';
          reply += '| Space ID | Database Name | File Size | Tables | Status |\n';
          reply += '|---|---|---|---|---|\n';
          for (const [spaceId, s] of Object.entries(spaces)) {
            const statusIcon = s.integrity === 'ok' ? '🟢 Verified' : '⚠️ Disconnected';
            reply += `| \`${spaceId}\` | \`${s.name || spaceId}\` | \`${s.size_kb || 0} KB\` | \`${s.tables_count || 0}\` | ${statusIcon} |\n`;
          }
          reply += '\n---\n*Universal retrieval and on-demand ingestion active across all 11 partitioned spaces.*';
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: reply, model: 'OmniSpace 11-DB Engine' }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ Spaces overview error: ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      // 🔍 Universal 11-Space Database Retrieval
      if (command === '/retrieve' || command === '/spacesearch') {
        if (!rest) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/retrieve <search_query>`\n*Example:* `/retrieve Grand Rapids` or `/retrieve bitcoin`' }
          ]);
          setIsLoading(false);
          return;
        }
        try {
          const res = await fetch(`${BACKEND_URL}/api/spaces/retrieve`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ query: rest, limit_per_space: 5 })
          });
          const data = await res.json();
          let reply = `### 🔍 Universal Space Search Results for "${rest}"\n\n`;
          reply += `**Total Matches:** \`${data.total_matches || 0}\` across \`${data.spaces_searched || 11}\` spaces (${data.execution_time_ms || 0} ms)\n\n`;
          if (data.matches_by_space && Object.keys(data.matches_by_space).length > 0) {
            for (const [space, matches] of Object.entries(data.matches_by_space)) {
              reply += `#### 🏛️ Space: \`${space}\` (${matches.length} matches)\n\n`;
              for (const m of matches) {
                reply += `- **Table:** \`${m.table}\` | **Preview:** \`${JSON.stringify(m.preview || m.match_preview || {}).substring(0, 150)}\`\n`;
              }
              reply += '\n';
            }
          } else {
            reply += '*No direct matches found in priority tables for this keyword.*';
          }
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: reply, model: 'OmniSpace 11-DB Engine' }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ Space retrieval error: ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      // 💾 On-Demand Structured Database Ingestion
      if (command === '/ingest') {
        if (!rest) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/ingest <text_to_persist>`\n*Example:* `/ingest Strategic client contact: Acme Corp interested in West Michigan AI deployment`' }
          ]);
          setIsLoading(false);
          return;
        }
        try {
          const res = await fetch(`${BACKEND_URL}/api/spaces/ingest`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ content: rest })
          });
          const data = await res.json();
          const statusIcon = data.status === 'success' ? '💾' : '⚠️';
          const reply = `${statusIcon} **On-Demand Space Ingestion Result:**\n\n` +
            `- **Status:** \`${data.status}\`\n` +
            `- **Target Space:** \`${data.target_space || 'stehouwer_vault'}\`\n` +
            `- **Target Table:** \`${data.target_table || 'vault_items'}\`\n` +
            `- **Record ID:** \`${data.record_id || 'N/A'}\`\n` +
            `- **Integrity Check:** \`${data.integrity_check || 'verified'}\`\n` +
            `- **Timestamp:** \`${data.timestamp || new Date().toISOString()}\`\n\n` +
            `*Live record persisted to disk with WAL synchronization.*`;
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: reply, model: 'OmniSpace Ingestion Engine' }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ Space ingestion error: ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/email' || command === '/email-status' || command === '/email_status' || command === '/mail-status' || command === '/email-sync' || command === '/sync-email' || command === '/email-inbox' || command === '/inbox') {
        const subAction = command.includes('sync') ? 'sync' : (command.includes('inbox') ? 'inbox' : (parts[1] || 'status'));
        try {
          if (subAction === 'sync') {
            const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
              method: 'POST',
              headers: reqHeaders,
              body: JSON.stringify({ command_type: 'tool', target: 'email_sync_inbox', payload: {} })
            });
            const data = await res.json();
            const toolRes = data.result || data;
            const reply = `📬 **Live IMAP Email Synchronization:**\n\`\`\`json\n${JSON.stringify(toolRes, null, 2)}\n\`\`\``;
            setChatMessages(prev => [...prev, { role: 'assistant', content: reply, model: 'Sovereign Business Email Engine' }]);
          } else if (subAction === 'list' || subAction === 'inbox') {
            const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
              method: 'POST',
              headers: reqHeaders,
              body: JSON.stringify({ command_type: 'tool', target: 'email_list_messages', payload: { folder: 'Inbox', limit: 10 } })
            });
            const data = await res.json();
            const toolRes = data.result || data;
            const reply = `📨 **Latest Inbox Messages (${toolRes.total_matches || 0} total, showing ${toolRes.count || 0}):**\n\`\`\`json\n${JSON.stringify(toolRes.messages || [], null, 2)}\n\`\`\``;
            setChatMessages(prev => [...prev, { role: 'assistant', content: reply, model: 'Sovereign Business Email Engine' }]);
          } else {
            const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
              method: 'POST',
              headers: reqHeaders,
              body: JSON.stringify({ command_type: 'tool', target: 'email_get_status', payload: {} })
            });
            const data = await res.json();
            const toolRes = data.result || data;
            const statusIcon = toolRes.imap_status?.connected ? '✅' : '⚠️';
            const reply = `${statusIcon} **Sovereign Business Email Infrastructure Status (stehouwer-publishing.com):**\n\`\`\`json\n${JSON.stringify(toolRes, null, 2)}\n\`\`\``;
            setChatMessages(prev => [...prev, { role: 'assistant', content: reply, model: 'Sovereign Business Email Engine' }]);
          }
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ Email command failed: ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/coder' || command === '/code') {
        const coderPrompt = rest.trim() || 'Please write a production-ready script or component for the AI-BS ecosystem.';
        handleSendMessage(`/coder ${coderPrompt}`);
        return;
      }


      if (command === '/syntax' || command === '/validate') {
        if (!rest) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/syntax <language> <code>`\n*Example:* `/syntax python def test(): return 1`' }
          ]);
          setIsLoading(false);
          return;
        }
        const spaceIdx = rest.indexOf(' ');
        const lang = spaceIdx > -1 ? rest.substring(0, spaceIdx) : 'python';
        const codeSnippet = spaceIdx > -1 ? rest.substring(spaceIdx + 1).trim() : rest;
        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({
              command_type: 'tool',
              target: 'validate_syntax',
              payload: { code: codeSnippet, language: lang }
            })
          });
          const data = await res.json();
          const toolRes = data.result || data;
          const statusIcon = toolRes.status === 'valid' ? '✅' : '❌';
          const reply = statusIcon + ' **Pre-Flight Syntax Validation (' + lang.toUpperCase() + '):**\n```json\n' + JSON.stringify(toolRes, null, 2) + '\n```';
          setChatMessages(prev => [...prev, { role: 'assistant', content: reply, model: 'Autonomous Coding Agent' }]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ Syntax validation failed: ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/symbol') {
        if (!rest) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/symbol <query>`\n*Example:* `/symbol telemetry` or `/symbol /api/`' }
          ]);
          setIsLoading(false);
          return;
        }
        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({
              command_type: 'tool',
              target: 'lookup_symbol',
              payload: { query: rest.trim(), scope: 'all' }
            })
          });
          const data = await res.json();
          const toolRes = data.result || data;
          const reply = '🔍 **Symbol Index Lookup Results for "' + rest.trim() + '" (' + (toolRes.match_count || 0) + ' matches, ' + (toolRes.execution_time_ms || 0) + ' ms):**\n```json\n' + JSON.stringify(toolRes.matches || [], null, 2) + '\n```';
          setChatMessages(prev => [...prev, { role: 'assistant', content: reply, model: 'Fast Codebase Symbol Indexer' }]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ Symbol lookup failed: ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/run') {
        const scriptName = parts[1] || '';
        if (!scriptName) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/run <script_path> [args]`\n*Example:* `/run run_full_scan.py` or `/run backend/AI_BS_Universal_Data_Ingestor.py --once`' }
          ]);
          setIsLoading(false);
          return;
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/chat/execute-script`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ script_path: scriptName, language: 'python' })
          });
          const data = await res.json();
          const out = data.stdout || data.message || 'Script completed without stdout.';
          const errText = data.stderr ? `\n\n**Stderr:**\n\`\`\`\n${data.stderr}\n\`\`\`` : '';
          const statusIcon = data.status === 'success' ? '✅' : '⚠️';
          const reply = `${statusIcon} **Script Execution Output** (\`${scriptName}\`, Exit Code: \`${data.returncode ?? 0}\`, \`${data.execution_time_ms || 0} ms\`):\n\n\`\`\`\n${out}\n\`\`\`${errText}`;
          
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: reply,
              model: 'BS-Chat Ecosystem Engine',
              execution_time_ms: data.execution_time_ms
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `❌ **Failed to execute script:** ${err.message}`,
              model: 'BS-Chat Ecosystem Engine'
            }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/mission', '/plan', '/execute-mission', '/run-mission'].includes(command)) {
        const goal = rest.trim();
        if (!goal) {
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: '🚀 **Autonomous Mission Engine (AI-BS & Antigravity Unison)**\n\n**Usage:** `/mission <goal>` or `/plan <goal>`\n*Examples:*\n- `/mission Verify multi-mirror parity, syntax health, and git status`\n- `/mission Inspect active trading bots on Port 8007 and report status`\n- `/plan Build an autonomous cron task to sweep expired sessions`\n\n---\n*Executes the 5-Phase Mission Lifecycle: Intent, Planning, Tool Execution, Self-Healing Verification, and Production Delivery.*'
            }
          ]);
          setIsLoading(false);
          return;
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/plan`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ goal, mode: command === '/plan' ? 'plan_only' : 'auto' })
          });
          const data = await res.json();
          if (data.status === 'success' && data.plan) {
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `🚀 Initialized Autonomous Mission: **${goal}**`,
                model: 'Autonomous Mission Engine',
                missionData: data.plan
              }
            ]);
          } else {
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: `❌ **Mission failed to initialize:** ${data.message || data.detail || 'Execution error'}` }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Mission Execution Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/grill', '/stress-test', '/architectural-grill', '/grill-me'].includes(command)) {
        const proposal = rest.trim();
        if (!proposal) {
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: '🔥 **Architectural Grill Engine (/grill)**\n\n**Usage:** `/grill <mission proposal>`\n\n*Click an example proposal below to immediately launch an interactive architectural stress-test:*',
              grillHelpExamples: [
                'Add a persistent SQLite event-logging daemon for Pearl mining stratum telemetry',
                'Integrate WebSocket real-time market orderbook stream on Port 8007',
                'Implement auto-recovering background session watcher'
              ]
            }
          ]);
          setIsLoading(false);
          return;
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/grill`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ proposal })
          });
          const data = await res.json();
          const session = data.session || data.grill_session;
          if ((data.status === 'grilling' || data.status === 'success') && session) {
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `🔥 Architectural Grill Session Started: **${proposal}**`,
                model: 'Architectural Grill Engine',
                grillData: session
              }
            ]);
          } else {
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: `❌ **Grill failed to start:** ${data.message || data.detail || 'Execution error'}` }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Grill Session Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/build', '/conclude-grill', '/approve-spec'].includes(command)) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/grill-conclude`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ grill_id: rest.trim() || undefined })
          });
          const data = await res.json();
          if (data.status === 'concluded') {
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `🔒 **Grill Session Concluded & Specification Locked:**\n\n📄 **Spec Artifact:** \`${data.spec_file}\`\n🚀 **Transitioning directly into Stage 2 Planning & Execution!**`,
                model: 'Autonomous Mission Engine',
                missionData: data.mission_plan
              }
            ]);
          } else {
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: `⚠️ **Notice:** ${data.message || 'No active grill session found to conclude.'}` }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Grill Conclude Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/audit', '/sweep', '/ast-check', '/pre-flight'].includes(command)) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/audit`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ scope: rest.trim() || undefined })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: data.markdown_summary || `Audit Result: ${data.status}`,
              model: 'Pre-Flight Security Auditor'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Audit Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/test-first', '/tdd', '/test_first'].includes(command)) {
        const feature = rest.trim() || 'core_feature';
        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/test-first`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ feature })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: data.markdown_summary || `TDD Result: ${data.status}`,
              model: 'Autonomous TDD Engine'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **TDD Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/diff-review', '/diff', '/patch-review'].includes(command)) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/diff-review`, {
            method: 'POST',
            headers: reqHeaders
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: data.markdown_summary || 'No unstaged modifications detected.',
              model: 'Visual Patch Reviewer'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Diff Review Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/snapshot', '/pin-state', '/checkpoint'].includes(command)) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/snapshot`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ label: rest.trim() || undefined })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: data.markdown_summary || `Snapshot pinned: ${data.commit_hash}`,
              model: 'Atomic State Manager'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Snapshot Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/rollback', '/restore-bak', '/revert-backup'].includes(command)) {
        const target = rest.trim();
        if (!target) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/rollback <backup_id|filename>`\n*Example:* `/rollback task_tdd_core` or `/rollback ChatTab.jsx`' }
          ]);
          setIsLoading(false);
          return;
        }
        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/rollback`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ target })
          });
          const data = await res.json();
          if (data.status === 'success') {
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `✅ **Rollback Completed Successfully!**\n- **Restored File:** \`${data.restored_file}\`\n- **Source Backup:** \`${data.backup_source}\`\n- **Pre-Rollback Backup:** \`${data.pre_rollback_backup}\`\n- **Message:** ${data.message}`,
                model: 'Surgical Backup Engine'
              }
            ]);
          } else {
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: `❌ **Rollback Failed:** ${data.message || 'Unknown error'}` }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Rollback Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/typst', '/compile-typst', '/kdp-pdf'].includes(command)) {
        const textToCompile = rest.trim() || '= Stehouwer Publishing\nSovereign Print Document.\n\n#set text(size: 11pt)\nGenerated via AI-BS Typst Engine.';
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/publishing/typst/compile`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ markup_text: textToCompile, title: 'Stehouwer Publishing Print Edition' })
          });
          const data = await res.json();
          if (data.status === 'success') {
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `📖 **Typst Print-Ready PDF Compiled Successfully!**\n- **Trim Size:** \`${data.trim_size}\`\n- **Compilation Speed:** \`${data.elapsed_ms} ms\`\n- **PDF Size:** \`${data.file_size_bytes} bytes\`\n- **PDF Path:** \`${data.pdf_path}\`\n- 📥 [Download PDF](${BACKEND_URL}${data.download_url})`,
                model: 'Typst & Pandoc Engine'
              }
            ]);
          } else {
            setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Typst Compilation Error:** ${data.detail || data.message || 'Error'}` }]);
          }
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Typst Request Failed:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/demucs', '/stems', '/audio-split'].includes(command)) {
        const audioPath = rest.trim();
        if (!audioPath) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '🎵 **Demucs PyTorch/CUDA Stem Separator**\n\n**Usage:** `/demucs <audio_file_path>`\n*Example:* `/demucs C:\\AI-BS\\saved_data\\test_audio_sample.wav`' }
          ]);
          setIsLoading(false);
          return;
        }
        try {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `⏳ **Demucs:** Running PyTorch CUDA stem separation on RTX 4090 for \`${audioPath}\`...` }]);
          const res = await fetch(`${BACKEND_URL}/api/v1/audio/demucs/separate`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ audio_file_path: audioPath })
          });
          const data = await res.json();
          if (data.status === 'success') {
            const stemList = Object.keys(data.stems || {}).map(k => `  - **${k.toUpperCase()}:** \`${data.stems[k].filename}\` (${data.stems[k].size_bytes} bytes)`).join('\n');
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `✅ **Demucs Stem Separation Complete!** (${data.elapsed_seconds}s on ${data.device.toUpperCase()})\n- **Destination:** \`${data.target_folder}\`\n- **Extracted Stems:**\n${stemList}`,
                model: 'Demucs Audio Separator'
              }
            ]);
          } else {
            setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Demucs Separation Error:** ${data.detail || data.message || 'Error'}` }]);
          }
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Demucs Request Failed:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/psmgr', '/process-manager', '/chrome-sync'].includes(command)) {
        const subAction = parts[1] || 'ports';
        try {
          if (subAction === 'chrome' || subAction === 'chrome_sync') {
            const res = await fetch(`${BACKEND_URL}/api/v1/system/powershell/chrome/profiles`, {
              method: 'POST',
              headers: reqHeaders,
              body: JSON.stringify({ action: 'status' })
            });
            const data = await res.json();
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `🌐 **Chrome Profile Sync Status:**\n- **Profiles Found:** ${data.profiles_count}\n- **Active Chrome PIDs:** ${data.running_chrome_processes}\n\`\`\`json\n${JSON.stringify(data.profiles || [], null, 2)}\n\`\`\``,
                model: 'PowerShell Process Manager'
              }
            ]);
          } else {
            const res = await fetch(`${BACKEND_URL}/api/v1/system/powershell/ecosystem/ports`, {
              method: 'GET',
              headers: reqHeaders
            });
            const data = await res.json();
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `⚡ **18-Port Ecosystem Process Monitor:**\n- **Active Listening Ports:** ${data.active_listening_ports_count} / ${data.tracked_ports_total}\n\`\`\`json\n${JSON.stringify(data.ports_map || {}, null, 2)}\n\`\`\``,
                model: 'PowerShell Process Manager'
              }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **PowerShell Manager Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/tshark', '/packet-sniff', '/mining-audit'].includes(command)) {
        try {
          if (rest.includes('mining') || command === '/mining-audit') {
            const res = await fetch(`${BACKEND_URL}/api/v1/diagnostics/tshark/mining-audit?port=8335`, {
              method: 'GET',
              headers: reqHeaders
            });
            const data = await res.json();
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `🦪 **Pearl Mining Stratum Telemetry Audit:**\n- **Local Port 8335 Open:** ${data.stratum_listening ? '🟢 YES' : '🔴 NO'} (${data.latency_ms} ms)\n- **HeroMiners Pool Reachable:** ${data.herominers_pool_reachable ? '🟢 YES' : '🔴 NO'} (${data.pool_host})\n- **Response:** \`${data.response_banner}\``,
                model: 'TShark Telemetry Monitor'
              }
            ]);
          } else {
            const res = await fetch(`${BACKEND_URL}/api/v1/diagnostics/tshark/capture`, {
              method: 'POST',
              headers: reqHeaders,
              body: JSON.stringify({ ports: [8001, 8080, 8335, 11434], duration_seconds: 2 })
            });
            const data = await res.json();
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `📡 **TShark Telemetry Capture (${data.packets_captured} packets in ${data.duration_seconds}s):**\n\`\`\`json\n${JSON.stringify(data.port_diagnostics || data.packets || [], null, 2)}\n\`\`\``,
                model: 'TShark Telemetry Monitor'
              }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **TShark Telemetry Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/matting', '/remove-bg', '/bg-remove'].includes(command)) {
        const imgPath = rest.trim();
        if (!imgPath) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '🖼️ **ComfyUI Background Matting**\n\n**Usage:** `/matting <image_path>`\n*Example:* `/matting C:\\AI-BS\\saved_data\\product.jpg`' }
          ]);
          setIsLoading(false);
          return;
        }
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/comfy/process/matting`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ image_path: imgPath })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `🎨 **Background Matting Complete!** (${data.elapsed_seconds}s via \`${data.method}\`)\n- **Output:** \`${data.output_path || data.filename}\``,
              model: 'ComfyUI Image Processor'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Matting Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/upscale', '/super-res'].includes(command)) {
        const imgPath = rest.trim();
        if (!imgPath) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '🔍 **ComfyUI 4x Super-Resolution Upscaler**\n\n**Usage:** `/upscale <image_path>`\n*Example:* `/upscale C:\\AI-BS\\saved_data\\sample.png`' }
          ]);
          setIsLoading(false);
          return;
        }
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/comfy/process/upscale`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ image_path: imgPath, scale_factor: 4 })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `✨ **4x Super-Resolution Upscaling Complete!** (${data.elapsed_seconds}s via \`${data.method}\`)\n- **Resolution:** ${data.original_dimensions || 'Original'} ➔ **${data.upscaled_dimensions || '4x Upscaled'}**\n- **Output:** \`${data.output_path || data.filename}\``,
              model: 'ComfyUI Image Processor'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Upscaling Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/prosody', '/lyrics', '/cadence'].includes(command)) {
        const lyricText = rest.trim() || 'I got the master plan running on the local host\nRTX forty ninety making records coast to coast\nNever pay a fee when we execute the code\nZero cost engine on the sovereign road';
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/audio/prosody/map`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ raw_lyrics: lyricText, bpm: 140 })
          });
          const data = await res.json();
          const barRows = (data.mapped_bars || []).map(b => `  - **Bar ${b.bar_number}:** \`${b.text}\` (${b.syllable_count} syl, [${b.rhyme_scheme_tag}], ${b.cadence_status})`).join('\n');
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `🎤 **Acoustic-Somatic Prosody Mapping Complete!** (${data.process_time_ms} ms)\n- **Bars:** ${data.total_bars} | **Total Syllables:** ${data.total_syllables} | **Avg Syllables/Bar:** ${data.avg_syllables_per_bar}\n- **Rhyme Scheme:** \`${data.rhyme_scheme}\` | **Est Duration:** \`${data.estimated_duration_seconds}s\` @ 140 BPM\n\n**DAW Bar Grid Alignment:**\n${barRows}`,
              model: 'Prosody Mapper Engine'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Prosody Mapping Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/duckdb', '/query-db', '/sql-cross'].includes(command)) {
        const queryStr = rest.trim() || 'SELECT 42 AS solution, "AI-BS Ecosystem" AS name;';
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/analytics/duckdb/query`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ sql_query: queryStr, max_rows: 20 })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `🦆 **DuckDB Zero-Copy Analytics Result (${data.execution_time_ms} ms):**\n- **Mounted DBs:** \`${(data.mounted_databases || []).join(', ')}\`\n- **Rows Returned:** ${data.row_count}\n\`\`\`json\n${JSON.stringify(data.results || [], null, 2)}\n\`\`\``,
              model: 'DuckDB Analytics Engine'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **DuckDB Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/ta', '/indicators', '/crypto-ta'].includes(command)) {
        try {
          const testPrices = [0.0570, 0.0572, 0.0571, 0.0574, 0.0575, 0.0573, 0.0576, 0.0578, 0.0577, 0.0580, 0.0582, 0.0581, 0.0584, 0.0585, 0.0583, 0.0586, 0.0588, 0.0587, 0.0590, 0.0592];
          const res = await fetch(`${BACKEND_URL}/api/v1/crypto/indicators/calculate`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ prices: testPrices })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `📈 **CRO Algorithmic Technical Indicators (${data.calculation_time_ms} ms):**\n- **Current Price:** \`$${data.current_price}\`\n- **RSI (14):** \`${data.rsi}\`\n- **MACD:** \`${data.macd?.macd}\` | **Signal:** \`${data.macd?.signal}\` | **Hist:** \`${data.macd?.histogram}\`\n- **Bollinger Bands:** Upper \`$${data.bollinger_bands?.upper}\` | Mid \`$${data.bollinger_bands?.middle}\` | Lower \`$${data.bollinger_bands?.lower}\`\n- **Strategy Recommendation:** **${data.recommended_signal}**`,
              model: 'Quantitative Indicators Engine'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **TA Indicators Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/noco', '/spatial', '/hydroponics'].includes(command)) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/infrastructure/noco/spatial`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ facility_sq_ft: 2400, growing_tiers: 4, stage_sq_ft: 600 })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `🌱 **Project NOCO Spatial & Agricultural Blueprint (${data.calculation_time_ms} ms):**\n- **Effective Canopy:** \`${data.agricultural_metrics?.effective_canopy_sq_ft} sq ft\` (${data.agricultural_metrics?.growing_tiers} tiers)\n- **Plant Capacity:** \`${data.agricultural_metrics?.total_plant_sites} sites\`\n- **Est Harvest:** \`${data.agricultural_metrics?.est_weekly_harvest_lbs} lbs/wk\` ($${data.agricultural_metrics?.est_annual_gross_revenue_usd?.toLocaleString()}/yr gross)\n- **Stage Capacity:** \`${data.performance_stage_acoustics?.safe_patron_capacity} patrons\` | **RT60 Reverb:** \`${data.performance_stage_acoustics?.estimated_rt60_reverb_seconds}s\` (${data.performance_stage_acoustics?.acoustic_status})`,
              model: 'Project NOCO Spatial Calculator'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **NOCO Spatial Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/obs', '/broadcast', '/auto-director'].includes(command)) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/broadcast/obs/state`, {
            method: 'GET',
            headers: reqHeaders
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `📡 **OBS Studio Broadcast State (${data.scan_time_ms} ms):**\n- **OBS Socket:** \`${data.obs_socket}\` (Active: ${data.is_obs_running ? '🟢 YES' : '🟡 STANDBY'})\n- **Suggested Scene:** **${data.suggested_scene}**\n- **Detected Studio Apps:**\n\`\`\`json\n${JSON.stringify(data.detected_studio_processes || {}, null, 2)}\n\`\`\``,
              model: 'OBS Broadcast Controller'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **OBS Controller Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/bench', '/diagnostics', '/boardview'].includes(command)) {
        const query = rest.trim() || 'iPhone 14 Pro VDD_MAIN';
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/hardware/bench/diagnostics`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ device_model: 'iPhone 14 Pro', symptom_or_rail: query })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `🔬 **Station 13 Bench Hardware Diagnostics (${data.query_time_ms} ms):**\n- **Matches:** ${data.matches_found}\n\`\`\`json\n${JSON.stringify(data.diagnostics || [], null, 2)}\n\`\`\``,
              model: 'Bench Diagnostics Engine'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Bench Diagnostics Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/ports', '/ecosystem-ports', '/sockets'].includes(command)) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/system/ecosystem/telemetry`, {
            method: 'GET',
            headers: reqHeaders
          });
          const data = await res.json();
          const s = data.summary || {};
          const onlineCore = (data.core_matrix || []).filter(m => m.status === 'ONLINE');
          const tableRows = onlineCore.map(m => `| \`${m.port}\` | **${m.service}** | \`${m.process_name || 'Daemon'}\` | ${m.cpu_pct}% | ${m.mem_mb} MB | \`${m.type}\` |`).join('\n');
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `⚡ **Unified Ecosystem Port Telemetry Snapshot**\n\n- **Core Collision Matrix Online:** **${s.core_matrix_online || 0} / ${s.core_matrix_total || 25}**\n- **Total Listening Sockets:** \`${s.total_listening_ports || 0}\` (Host + WSL2)\n- **Host Compute:** CPU **${s.host_cpu_pct}%** | RAM **${s.host_mem_used_gb} / ${s.host_mem_total_gb} GB** (${s.host_mem_pct}%)\n- **RTX 4090 VRAM:** **${Math.round((s.rtx_4090_vram_used_mb || 0) / 1024)} GB / 24 GB** (${s.rtx_4090_util_pct}% GPU, ${s.rtx_4090_temp_c}°C)\n\n### 🟢 Active Core Sockets:\n| Port | Service | Process | CPU | RAM | Type |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n${tableRows}`,
              model: 'Ecosystem Telemetry Mesh'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Port Telemetry Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/port-tools', '/discover-ports', '/tools-matrix'].includes(command)) {
        try {
          setChatMessages(prev => [...prev, { role: 'assistant', content: '🔍 **Probing active ports for OpenAPI schemas and tool signatures...**' }]);
          const res = await fetch(`${BACKEND_URL}/api/v1/system/ecosystem/ports/discover`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ timeout_seconds: 2.0 })
          });
          const data = await res.json();
          const services = Object.values(data.discovered_services || {});
          const totalTools = services.reduce((acc, s) => acc + (s.tools_count || 0), 0);
          const srvDetails = services.map(s => `* **Port ${s.port} (${s.service_title}):** \`${s.tools_count}\` tools [${s.protocol}]\n  ${(s.tools || []).slice(0, 3).map(t => `  - \`${t.method} ${t.endpoint}\`: ${t.summary}`).join('\n')}`).join('\n\n');
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `🛠️ **Dynamic Port Tool Discovery Complete!**\n- **Scanned Ports:** \`${data.scanned_ports_count}\`\n- **Total Discovered Tool Call Endpoints:** **${totalTools}**\n\n${srvDetails}`,
              model: 'Port Tool Dispatcher'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Tool Discovery Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/call-port', '/dispatch-port'].includes(command)) {
        const portArg = parseInt(parts[1], 10);
        const endpointArg = parts[2] || '/api/health';
        const methodArg = (parts[3] || 'GET').toUpperCase();
        if (!portArg) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚡ **Dynamic Port Tool Caller**\n\n**Usage:** `/call-port <port> [endpoint] [method]`\n*Example:* `/call-port 8080 /api/health GET`\n*Example:* `/call-port 11434 /api/tags GET`' }
          ]);
          setIsLoading(false);
          return;
        }
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/system/ecosystem/ports/dispatch`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ port: portArg, endpoint: endpointArg, method: methodArg, timeout_seconds: 15.0 })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `⚡ **Port Tool Execution Result:**\n- **Target:** \`${data.target_url}\` (Port ${portArg})\n- **Status:** **${data.status}** (HTTP ${data.http_status})\n- **Latency:** \`${data.execution_time_ms} ms\`\n\`\`\`json\n${JSON.stringify(data.response || data, null, 2)}\n\`\`\``,
              model: 'Dynamic Port Dispatcher'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Port Dispatch Failed:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/crew', '/specialist', '/agent-crew'].includes(command)) {
        const promptText = rest.trim() || 'Strip vocal stems and master track to -14 LUFS';
        try {
          const res = await fetch(`${BACKEND_URL}/api/v1/agents/route`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ prompt: promptText })
          });
          const data = await res.json();
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `🤖 **Specialist Crew Routed Successfully!**\n- **Assigned Specialist:** **${data.crew_title}** (\`${data.assigned_crew_id}\`)\n- **Scoped Tools:** \`${(data.scoped_tools || []).join(', ')}\`\n- **Context Overhead Reduction:** **${data.token_overhead_reduction}**\n- **System Directive:** *"${data.system_prompt}"*`,
              model: 'Multi-Agent Specialist Router'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [...prev, { role: 'assistant', content: `❌ **Specialist Crew Error:** ${err.message}` }]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/hardware', '/telemetry', '/gpu-health', '/clamping-check'].includes(command)) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/hardware-health`, {
            method: 'GET',
            headers: reqHeaders
          });
          const data = await res.json();
          const statusIcon = data.safe_to_execute ? '🟢' : '🔴';
          const tempStr = data.temperature_celsius !== null && data.temperature_celsius !== undefined ? `${data.temperature_celsius}°C` : 'N/A';
          const pwrStr = data.power_draw_watts !== null && data.power_draw_watts !== undefined ? `${data.power_draw_watts}W` : 'N/A';
          const vramStr = `${data.vram_used_mb || 'N/A'} MB / ${data.vram_total_mb || 'N/A'} MB (${data.vram_pct || 'N/A'}%)`;
          const warnText = data.warnings && data.warnings.length > 0 ? `\n\n⚠️ **Warnings:**\n${data.warnings.map(w => `- ${w}`).join('\n')}` : '';
          const md = `### ${statusIcon} Host Hardware Clamping & Watchdog Status\n- **Device:** \`${data.gpu_name || 'NVIDIA GPU'}\`\n- **State:** **${(data.status || 'unknown').toUpperCase()}** (Safe: \`${data.safe_to_execute}\`)\n- **Temperature:** \`${tempStr}\` *(Threshold: <83°C)*\n- **Power Draw:** \`${pwrStr}\`\n- **VRAM Utilized:** \`${vramStr}\` *(Threshold: <95%)*${warnText}`;
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: md,
              model: 'Hardware Clamping Sentinel'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Hardware Probe Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/port-probe', '/check-port', '/probe-port'].includes(command)) {
        const portVal = parseInt(rest.trim() || '8080', 10);
        try {
          const res = await fetch(`${BACKEND_URL}/api/mission/port-probe/${portVal}`, {
            method: 'GET',
            headers: reqHeaders
          });
          const data = await res.json();
          const conflictIcon = data.is_conflict ? '🚨' : '✅';
          const md = `### ${conflictIcon} Port Collision Probe: Port ${data.port}\n- **Conflict Detected:** **${data.is_conflict ? 'YES (Occupied / Collision)' : 'NO (Clear)'}**\n- **Static Matrix Owner:** \`${data.registered_daemon || 'None (Unreserved)'}\`\n- **Active Socket Binding:** \`${data.socket_busy ? 'Bound (Active)' : 'Unbound'}\`\n- **Fallback Port:** \`${data.fallback_port}\`\n- **Recommendation:** *${data.recommendation}*`;
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: md,
              model: 'Process Conflict Sentinel'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Port Probe Error:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/read', '/cat', '/view', '/file'].includes(command)) {
        const targetPath = rest.trim();
        if (!targetPath) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/read <file_path>`\n*Example:* `/read version.txt` or `/read backend/crypto_trader_bot.py`' }
          ]);
          setIsLoading(false);
          return;
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ command_type: 'file_read', target: targetPath })
          });
          const data = await res.json();
          if (data.status === 'success' && data.result) {
            const rawContent = data.result.content || '';
            const lines = data.result.lines || 0;
            const sizeKb = (data.result.size_bytes ? (data.result.size_bytes / 1024).toFixed(1) : '0.0');
            const ext = targetPath.split('.').pop().toLowerCase();
            const preview = rawContent.length > 30000 ? rawContent.substring(0, 30000) + `\n\n... [Truncated: showing 30,000 of ${rawContent.length} characters]` : rawContent;
            
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `📖 **Host File Read:** \`${targetPath}\` *(${lines} lines, ${sizeKb} KB)*\n\n\`\`\`${ext}\n${preview}\n\`\`\`\n\n---\n💡 *Use \`/edit ${targetPath}\` to open in the interactive drawer, or \`/write ${targetPath} <content>\` to overwrite.*`,
                model: 'Executive File Engine'
              }
            ]);
          } else {
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: `❌ **Failed to read file:** ${data.message || data.result?.message || 'File not found'}` }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Error reading file:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/write', '/save'].includes(command)) {
        let targetPath = '';
        let fileContent = '';
        
        const codeBlockMatch = rest.match(/```(?:[a-zA-Z0-9_\-]+)?\r?\n([\s\S]*?)\r?\n```/);
        if (codeBlockMatch) {
          targetPath = rest.substring(0, rest.indexOf('```')).trim().replace(/:$/, '').trim();
          fileContent = codeBlockMatch[1];
        } else {
          const parts = rest.trim().split(/\s+(.+)/s);
          targetPath = (parts[0] || '').trim();
          fileContent = (parts[1] || '').trim();
        }

        if (!targetPath) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/write <file_path> <content>` or `/write <file_path>\\n\\`\\`\\`<code>\\`\\`\\``\n*Example:* `/write scratch/test.txt Hello world`\n*Tip:* Use `/write <file_path>` with no content to open directly in the Host File Editor.' }
          ]);
          setIsLoading(false);
          return;
        }

        if (!fileContent) {
          try {
            const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
              method: 'POST',
              headers: reqHeaders,
              body: JSON.stringify({ command_type: 'file_read', target: targetPath })
            });
            const data = await res.json();
            const existingContent = (data.status === 'success' && data.result) ? (data.result.content || '') : '';
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `📝 Opened \`${targetPath}\` in Host Editor Drawer:`,
                editorData: {
                  path: targetPath,
                  content: existingContent,
                  lines: existingContent ? existingContent.split('\n').length : 0,
                  size_bytes: existingContent ? existingContent.length : 0
                },
                model: 'Executive File Engine'
              }
            ]);
          } catch (err) {
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: `❌ **Error opening editor drawer:** ${err.message}` }
            ]);
          } finally {
            setIsLoading(false);
          }
          return;
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({
              command_type: 'file_write',
              target: targetPath,
              payload: { content: fileContent }
            })
          });
          const data = await res.json();
          if (data.status === 'success' || data.result?.status === 'success') {
            const backupNote = data.result?.backup_created ? `\n📦 **Auto-Backup Created:** \`${data.result.backup_file}\`` : '';
            const bytesWritten = data.result?.bytes_written || fileContent.length;
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `✅ **File Written Successfully!**\n\n- **Target:** \`${targetPath}\`\n- **Size:** ${bytesWritten} bytes (${(bytesWritten / 1024).toFixed(1)} KB)\n- **Lines:** ${fileContent.split('\n').length}${backupNote}\n\n---\n💡 *File saved to host disk with automated .bak backup protection.*`,
                model: 'Executive File Engine'
              }
            ]);
          } else {
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: `❌ **Failed to write file:** ${data.message || data.result?.message || 'Write error'}` }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Error writing file:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (['/ls', '/dir', '/tree'].includes(command)) {
        const targetDir = rest.trim() || 'C:\\AI-BS';
        try {
          const res = await fetch(`${BACKEND_URL}/api/tools/execute`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({
              tool_name: 'scan_directory_tree',
              arguments: { dir_path: targetDir, depth: 2 }
            })
          });
          const data = await res.json();
          const r = data.result || data;
          if (r.status === 'success') {
            const treeItems = r.tree || [];
            let md = `### 📁 Host Directory: \`${r.root || targetDir}\`\n\n| Type | Name | Size |\n|---|---|---|\n`;
            treeItems.slice(0, 40).forEach(item => {
              const itype = item.type === 'directory' ? '📁 DIR' : '📄 FILE';
              const isize = item.type !== 'directory' && item.size_bytes >= 0 ? `${(item.size_bytes / 1024).toFixed(1)} KB` : '-';
              md += `| ${itype} | \`${item.name}\` | ${isize} |\n`;
            });
            if (treeItems.length > 40) {
              md += `\n*... and ${treeItems.length - 40} additional items.*`;
            }
            md += `\n\n---\n💡 *Use \`/read <filepath>\` to view a file or \`/edit <filepath>\` to open in the drawer.*`;
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: md, model: 'Host Directory Engine' }
            ]);
          } else {
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: `❌ **Directory scan failed:** ${r.message || 'Directory not found'}` }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Error scanning directory:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/edit') {
        const targetPath = rest.trim();
        if (!targetPath) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/edit <file_path>`\n*Example:* `/edit backend/tools/tool_registry.py` or `/edit C:\\AI-BS\\package.json`' }
          ]);
          setIsLoading(false);
          return;
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ command_type: 'file_read', target: targetPath })
          });
          const data = await res.json();
          if (data.status === 'success' && data.result) {
            setChatMessages(prev => [
              ...prev,
              {
                role: 'assistant',
                content: `📖 Opened file \`${targetPath}\` in Host Editor Drawer (${data.result.lines || 0} lines):`,
                editorData: {
                  path: targetPath,
                  content: data.result.content || '',
                  lines: data.result.lines,
                  size_bytes: data.result.size_bytes
                },
                model: 'Executive File Engine'
              }
            ]);
          } else {
            setChatMessages(prev => [
              ...prev,
              { role: 'assistant', content: `❌ **Failed to read file:** ${data.message || data.result?.message || 'File not found'}` }
            ]);
          }
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: `❌ **Error reading file:** ${err.message}` }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/ps' || command === '/cmd') {
        if (!rest) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/ps <powershell_command>`\n*Example:* `/ps Get-Process | Select-Object -First 5`' }
          ]);
          setIsLoading(false);
          return;
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ command_type: 'powershell', target: rest })
          });
          const data = await res.json();
          const out = data.stdout || data.message || 'Command executed without stdout.';
          const errText = data.stderr ? `\n\n**Stderr:**\n\`\`\`\n${data.stderr}\n\`\`\`` : '';
          const statusIcon = data.status === 'success' ? '✅' : '⚠️';
          const reply = `${statusIcon} **PowerShell Output** (Exit Code: \`${data.returncode ?? 0}\`, \`${data.execution_time_ms || 0} ms\`):\n\n\`\`\`\n${out}\n\`\`\`${errText}`;

          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: reply,
              model: 'Executive PowerShell Engine',
              execution_time_ms: data.execution_time_ms
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `❌ **Command error:** ${err.message}`,
              model: 'Executive PowerShell Engine'
            }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/wsl') {
        if (!rest) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/wsl [distro] <bash_command>`\n*Examples:* `/wsl ls -la` or `/wsl Ubuntu-24.04 nvidia-smi`' }
          ]);
          setIsLoading(false);
          return;
        }

        let distro = 'Ubuntu';
        let bashCmd = rest;
        const wslTokens = rest.split(/\s+/);
        if (['ubuntu', 'ubuntu-24.04', 'ubuntu-22.04', 'debian'].includes(wslTokens[0].toLowerCase())) {
          distro = wslTokens[0];
          bashCmd = rest.substring(wslTokens[0].length).trim();
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({
              command_type: 'wsl',
              target: bashCmd,
              payload: { distro }
            })
          });
          const data = await res.json();
          const out = data.stdout || data.message || 'WSL command executed without stdout.';
          const errText = data.stderr ? `\n\n**Stderr:**\n\`\`\`\n${data.stderr}\n\`\`\`` : '';
          const statusIcon = data.status === 'success' ? '🐧' : '⚠️';
          const reply = `${statusIcon} **WSL (${distro}) Output** (Exit Code: \`${data.returncode ?? 0}\`, \`${data.execution_time_ms || 0} ms\`):\n\n\`\`\`\n${out}\n\`\`\`${errText}`;

          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: reply,
              model: `WSL2 Executive Engine (${distro})`,
              execution_time_ms: data.execution_time_ms
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `❌ **WSL command error:** ${err.message}`,
              model: 'WSL2 Executive Engine'
            }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/deploy') {
        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: '🚀 **Triggering Production Build & Firebase Cloud Sync...**\n*Executing:* `powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"`',
            model: 'Executive Deployment Daemon'
          }
        ]);

        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({
              command_type: 'powershell',
              target: 'powershell.exe -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"',
              payload: { timeout_seconds: 300 }
            })
          });
          const data = await res.json();
          const out = data.stdout || data.message || 'Deployment finished.';
          const errText = data.stderr ? `\n\n**Stderr:**\n\`\`\`\n${data.stderr}\n\`\`\`` : '';
          const statusIcon = data.status === 'success' ? '🎉' : '⚠️';
          const reply = `${statusIcon} **Deployment Pipeline Output** (Exit Code: \`${data.returncode ?? 0}\`, \`${data.execution_time_ms || 0} ms\`):\n\n\`\`\`\n${out}\n\`\`\`${errText}`;

          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: reply,
              model: 'Executive Deployment Daemon',
              execution_time_ms: data.execution_time_ms
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `❌ **Deployment failed:** ${err.message}`,
              model: 'Executive Deployment Daemon'
            }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/kill') {
        const portNum = parseInt(parts[1], 10);
        if (isNaN(portNum)) {
          setChatMessages(prev => [
            ...prev,
            { role: 'assistant', content: '⚠️ **Usage:** `/kill <port>`\n*Example:* `/kill 8080` or `/kill 3001`' }
          ]);
          setIsLoading(false);
          return;
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({
              command_type: 'tool',
              target: 'manage_daemon_state',
              payload: { port: portNum, action: 'kill' }
            })
          });
          const data = await res.json();
          const resultObj = data.result || {};
          const statusIcon = resultObj.status === 'success' ? '🛑' : '⚠️';
          const reply = `${statusIcon} **Daemon Port Killer** (\`Port ${portNum}\`):\n\`\`\`json\n${JSON.stringify(resultObj, null, 2)}\n\`\`\``;

          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: reply,
              model: 'Executive Process Engine'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `❌ **Process termination error:** ${err.message}`,
              model: 'Executive Process Engine'
            }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/health' || command === '/doctor') {
        try {
          const res = await fetch(`${BACKEND_URL}/api/tools/execute`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ tool_name: 'get_ecosystem_health', arguments: { component: 'all' } })
          });
          const data = await res.json();
          const rep = data.result?.diagnostics || data.result?.hardware || JSON.stringify(data.result, null, 2);
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: rep,
              model: 'Matrix Doctor'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `❌ **Diagnostic scan error:** ${err.message}`,
              model: 'Matrix Doctor'
            }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      if (command === '/service') {
        const action = parts[1] || 'status';
        const serviceName = parts[2] || 'all';

        try {
          const res = await fetch(`${BACKEND_URL}/api/tools/execute`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ tool_name: 'manage_ecosystem_service', arguments: { action, service_name: serviceName } })
          });
          const data = await res.json();
          const reply = `### ⚙️ Ecosystem Service Status (\`${action}\` on \`${serviceName}\`)\n\`\`\`json\n${JSON.stringify(data.result, null, 2)}\n\`\`\``;
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: reply,
              model: 'BS-Chat Ecosystem Engine'
            }
          ]);
        } catch (err) {
          setChatMessages(prev => [
            ...prev,
            {
              role: 'assistant',
              content: `❌ **Service manager error:** ${err.message}`,
              model: 'BS-Chat Ecosystem Engine'
            }
          ]);
        } finally {
          setIsLoading(false);
        }
        return;
      }
    }

    try {
      const isPlanMode = activeTools?.plan_and_review;
      const targetModel = selectedModel || 'stehouwer_llm';
      const useHybridStream = !isPlanMode && targetModel === 'stehouwer_llm';

      const reqHeaders = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
        'X-Client-ID': 'stehouwer_publishing'
      };

      let streamingSucceeded = false;

      if (useHybridStream) {
        // --- HYBRID REASONING ENGINE (STREAMING) ---
        // Push an empty assistant message first
        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: '',
            model: 'stehouwer_llm (Hybrid)',
            execution_time_ms: 0
          }
        ]);

        let assistantMessage = '';
        try {
          const recentHistory = (updatedHistory || []).slice(-8).map(m => ({
            role: m.role,
            content: m.content || m.displayContent || ''
          }));

          const streamRes = await fetch(`${BACKEND_URL}/api/v1/hybrid-chat/stream`, {
            method: 'POST',
            headers: reqHeaders,
            body: JSON.stringify({ prompt: formattedPrompt, messages: recentHistory, stream: true }),
            signal: controller.signal,
          });

          if (streamRes.ok && streamRes.body) {
            const reader = streamRes.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              
              const chunk = decoder.decode(value);
              assistantMessage += chunk;
              
              setChatMessages(prev => {
                const newArr = [...prev];
                if (newArr.length > 0 && newArr[newArr.length - 1].role === 'assistant') {
                  newArr[newArr.length - 1].content = assistantMessage;
                }
                return newArr;
              });
            }

            if (assistantMessage.trim().length > 0) {
              streamingSucceeded = true;
              if (autoSpeak) {
                speakText(assistantMessage);
              }
            }
          }
        } catch (streamErr) {
          console.warn('Streaming failed, engaging fallback endpoint...', streamErr);
          if (assistantMessage.trim().length > 0) {
            streamingSucceeded = true;
          } else {
            // Pop the empty placeholder if no tokens received
            setChatMessages(prev => {
              if (prev.length > 0 && prev[prev.length - 1].content === '') {
                return prev.slice(0, -1);
              }
              return prev;
            });
          }
        }
      }

      if (!streamingSucceeded) {
        // --- NON-STREAMING ENGINE OR FAILOVER RECOVERY ---
        const endpoint = isPlanMode ? '/v1/ide/plan' : '/api/chat';
        
        const payloadBody = JSON.stringify({
          messages: updatedHistory.map(m => ({ role: m.role, content: m.content })),
          model: targetModel,
          prompt: isPlanMode ? rawText : undefined,
          active_file: isPlanMode ? 'C:\\AI-BS\\backend\\AI_BS_Backend.py' : undefined,
          context_flags: isPlanMode ? activeContexts : undefined,
          target_device: targetDevice,
          stream: false
        });

        let res = await fetch(`${BACKEND_URL}${endpoint}`, {
          method: 'POST',
          headers: reqHeaders,
          body: payloadBody,
          signal: controller.signal,
        }).catch(() => null);

        if (!res || !res.ok) {
          res = await fetch(`${BACKEND_URL}/v1/chat/completions`, {
            method: 'POST',
            headers: reqHeaders,
            body: payloadBody,
            signal: controller.signal,
          }).catch(() => null);
        }

        // Secondary fallback to FastAPI directly on 8080 if Go Gateway on 8000 dropped
        if (!res || !res.ok) {
          const directFastApiUrl = BACKEND_URL.includes(':8000') ? BACKEND_URL.replace(':8000', ':8080') : 'http://127.0.0.1:8080';
          res = await fetch(`${directFastApiUrl}${endpoint}`, {
            method: 'POST',
            headers: reqHeaders,
            body: payloadBody,
            signal: controller.signal,
          }).catch(() => null);
        }

        if (!res || !res.ok) {
          throw new Error(`Server returned HTTP ${res ? res.status : 'Connection Offline'}`);
        }

        let data = {};
        const rawTextRes = await res.text();
        if (rawTextRes.trim().startsWith('data:')) {
          let sseContent = '';
          for (const line of rawTextRes.split('\n')) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data:')) {
              const jsonPart = trimmed.replace(/^data:\s*/, '');
              if (jsonPart === '[DONE]') continue;
              try {
                const parsed = JSON.parse(jsonPart);
                if (parsed.content) sseContent += parsed.content;
                else if (parsed.response) sseContent += parsed.response;
                else if (parsed.error) sseContent = `⚠️ ${parsed.error}`;
              } catch (_) {
                if (jsonPart) sseContent += jsonPart;
              }
            }
          }
          data = { response: sseContent };
        } else {
          try {
            data = JSON.parse(rawTextRes);
          } catch (_) {
            data = { response: rawTextRes };
          }
        }

        const rawContent = data.choices?.[0]?.message?.content || data.message || (typeof data.response === 'string' ? data.response : '');
        const botResponse = rawContent.trim() !== '' ? rawContent : (isPlanMode ? 'Plan generated.' : `Online and operational (${targetModel}).`);
        const planData = isPlanMode ? (data.plan_id ? data : (data.planData || null)) : null;

        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: botResponse,
            model: data.model || targetModel,
            execution_time_ms: data.execution_time_ms || 120,
            tool_trace: data.tool_trace || null,
            planData: planData
          }
        ]);

        if (autoSpeak) {
          speakText(botResponse);
        }
      }
    } catch (err) {
      console.error('Chat error:', err);
      setErrorPopup(err.message || 'Failed to reach AI-BS backend.');
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: `❌ **Error:** ${err.message}` }
      ]);
    } finally {
      clearTimeout(timeoutId);
      setIsLoading(false);
    }
  };

  const toggleListening = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      setErrorPopup('Speech recognition is not supported in this browser.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setFooterInput(prev => (prev ? `${prev} ${transcript}` : transcript));
      setIsListening(false);
    };
    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setErrorPopup(`Speech error: ${event.error}`);
      setIsListening(false);
    };
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
  };

  const starterCategories = ['All', '🎯 Missions', '💻 Host IDE', '👑 Oversight', '📧 Email', '⚔️ Swarm', '🎨 Creative', '🎹 Studio', '🗄️ Intelligence'];

  const starterCards = [
    // 🎯 Autonomous Missions (AI-BS & Antigravity Unison)
    {
      category: "🎯 Missions",
      title: "🚀 Launch Autonomous Mission",
      desc: "Run 5-Phase agentic mission: workspace telemetry, task blueprint, tool execution, tests, and 4-mirror delivery.",
      prompt: "/mission Verify multi-mirror parity, syntax health, and git status"
    },
    {
      category: "🎯 Missions",
      title: "📋 Generate Mission Blueprint",
      desc: "Deconstruct an operational goal into an atomic execution plan without touching host files.",
      prompt: "/plan Audit ecosystem port topology and verify daemon health"
    },
    {
      category: "🎯 Missions",
      title: "🔥 Pre-Flight Architectural Grill",
      desc: "Stress-test proposals against local schemas, concurrency locks, recovery rollbacks, and security policies.",
      prompt: "/grill Add a persistent SQLite event-logging daemon for Pearl mining stratum telemetry"
    },
    // 🛠️ Autonomous Developer Workbench
    {
      category: "🛠️ Workbench",
      title: "🔍 Static AST & Security Sweep",
      desc: "Scan changed files for AST syntax errors, exposed API keys/tokens, and 4-mirror parity violations.",
      prompt: "/audit"
    },
    {
      category: "🛠️ Workbench",
      title: "🔴 Autonomous TDD Red-Green Loop",
      desc: "Enforce test-driven development: author failing test fixture first, then build minimal functional code.",
      prompt: "/test-first telemetry_stream"
    },
    {
      category: "🛠️ Workbench",
      title: "📄 Visual Patch & Diff Review",
      desc: "Inspect pending git diff patches with rollback hashes without direct mutation.",
      prompt: "/diff-review"
    },
    {
      category: "🛠️ Workbench",
      title: "📌 Atomic State Snapshot",
      desc: "Write an atomic checkpoint commit to Git and dump state to SAVED_CHECKPOINT.md.",
      prompt: "/snapshot dev_checkpoint"
    },
    {
      category: "🛠️ Workbench",
      title: "⚡ Hardware & Clamping Watchdog",
      desc: "Check NVIDIA GeForce RTX 4090 GPU thermals, power draw, and VRAM utilization.",
      prompt: "/hardware"
    },
    // 💻 Host IDE & File Engine
    {
      category: "💻 Host IDE",
      title: "📖 Read Host System File",
      desc: "Inspect file contents on host disk with syntax highlighting, byte size, and line count.",
      prompt: "/read version.txt"
    },
    {
      category: "💻 Host IDE",
      title: "📝 Host File Editor Drawer",
      desc: "Open source file in the interactive editor drawer with live editing and automated .bak backup.",
      prompt: "/edit version.txt"
    },
    {
      category: "💻 Host IDE",
      title: "📁 Host Directory Scan",
      desc: "Scan and display directory tree, file sizes, and folder counts across host storage volumes.",
      prompt: "/ls"
    },
    {
      category: "💻 Host IDE",
      title: "💾 Write Host File",
      desc: "Write or create a file on host disk with automated backup and validation.",
      prompt: "/write scratch/test_chat.txt Autonomous chat file engine verified!"
    },
    // 📧 Sovereign Business Email
    {
      category: "📧 Email",
      title: "📧 Sovereign Business Email Sync & Status",
      desc: "Poll Google IMAP SSL 993, inspect mailbox stats, and display latest unread business messages.",
      prompt: "/email-status"
    },
    {
      category: "📧 Email",
      title: "✍️ AI Business Reply Generator",
      desc: "Draft a polished Stehouwer Publishing response to the latest received business inquiry.",
      prompt: "Draft a polished business reply to the latest received inquiry in my inbox."
    },
    // 👑 Master Hub Oversight Parent & Storage Matrix
    {
      category: "👑 Oversight",
      title: "👑 Master Hub 43-Module Oversight",
      desc: "Live parent governor supervising all 43 modules, 20 daemons, and 6 operational domains.",
      prompt: "/monitor"
    },
    {
      category: "👑 Oversight",
      title: "📦 Catalog All 43 Ecosystem Modules",
      desc: "List all 43 Master Hub modules with domain groupings and 1-click tab switching keys.",
      prompt: "/modules"
    },
    {
      category: "🗄️ Intelligence",
      title: "🏛️ Universal 11-Space Retrieval",
      desc: "Query across all 11 memory-mapped SQLite databases and knowledge vaults simultaneously.",
      prompt: "/retrieve Grand Rapids"
    },
    {
      category: "🗄️ Intelligence",
      title: "💾 On-Demand Database Ingestion",
      desc: "Persist incoming intelligence, notes, client data, or transactions to verified SQLite spaces.",
      prompt: "/ingest Priority executive memo: BS-Chat is now the master oversight parent supervising all 43 ecosystem modules."
    },
    {
      category: "🗄️ Intelligence",
      title: "🏛️ 11 Database Spaces Overview",
      desc: "Inspect storage sizes, table counts, and WAL integrity across all 11 local database spaces.",
      prompt: "/spaces"
    },
    // ⚔️ Reasoning & Swarm
    {
      category: "⚔️ Swarm",
      title: "⚔️ Run 12-Stage Swarm Gauntlet",
      desc: "Audit strategic logic across 11 local models (Dolphin, Qwen, Nemotron, Mixtral, Gemma, Llama).",
      prompt: "run deep gauntlet What is the mathematical and architectural advantage of local NVMe memory-mapped multi-model consensus over cloud APIs?"
    },
    {
      category: "🗄️ Intelligence",
      title: "🏛️ Query Master Ledger & Origins",
      desc: "Retrieve founding dates, Vercel genesis, 90-Day Accumulation Matrix, and hardware baselines in <2ms.",
      prompt: "Search your master memory and chronology for our founding dates, first Vercel upload, and the 90-Day Accumulation Matrix."
    },
    // 🎨 Creative & 3D
    {
      category: "🎨 Creative",
      title: "🎨 Render 4K SDXL Concept Art",
      desc: "Dispatch instant high-res visual prompt to local ComfyUI RTX 4090 pipeline.",
      prompt: "Use your generate_comfy_image tool to create a futuristic neon cyberpunk penthouse overlooking a glowing server matrix."
    },
    {
      category: "🎨 Creative",
      title: "🎬 Generate Wan2.1 Cinematic Video",
      desc: "Render photorealistic 1080p/4K motion clip locally via Wan2.1 & ComfyUI on Port 8189.",
      prompt: "Use your generate_comfy_video tool to create an epic camera drone sweep over a sovereign mountain data fortress."
    },
    {
      category: "🎨 Creative",
      title: "🎮 Unreal Engine 5 Theatrical Stage",
      desc: "Spawn 3D lighting cues, DMX mood triggers, and virtual camera tracks on Port 8080.",
      prompt: "Trigger Unreal Engine 5 theatrical stage cue with blue cyber neon lighting and dynamic cinematic camera choreography."
    },
    // 🎹 Studio & Broadcast
    {
      category: "🎹 Studio",
      title: "🎹 Compose Neural DAW Soundtrack",
      desc: "Generate Tone.js 16-step sequencer rhythm and 808 sub-bass track in BS-Studio.",
      prompt: "Generate a hard-hitting 140 BPM synthwave drum groove and 808 sub-bass chord progression for the DAW Channel Rack."
    },
    {
      category: "🎹 Studio",
      title: "🎥 Zero-Copy OBS Broadcast Switcher",
      desc: "Engage D3D11-CUDA zero-copy capture, NVENC rate control & live game hooks on Port 8088.",
      prompt: "Check the DirectX 11 zero-copy broadcast kernel status, active game detection hooks, and NVENC rate control on Port 8088."
    },
    {
      category: "🎹 Studio",
      title: "📡 30-Node Ultra-Syndication Broadcast",
      desc: "Simultaneously ping IndexNow, Microsoft Bing, Google WebSub, and XML-RPC clusters.",
      prompt: "Dispatch a live global syndication broadcast across all 30 IndexNow, WebSub, and XML-RPC ping nodes."
    },
    // 🗄️ Data & OSINT
    {
      category: "🗄️ Intelligence",
      title: "🔍 Query 70+ Knowledge & Blockchain DBs",
      desc: "Run sub-2ms WAL-mode queries across 272K+ telemetry records and financial ledgers.",
      prompt: "Query the blockchain telemetry and industry intelligence database and show me the latest records."
    },
    {
      category: "🗄️ Intelligence",
      title: "🌐 OSINT & Live Market Intelligence",
      desc: "Scan live corporate data, lead matrices, and market intelligence across 12 API endpoints.",
      prompt: "Run an OSINT reconnaissance scan on commercial business directories in West Michigan for high-probability B2B leads."
    },
    {
      category: "🎨 Creative",
      title: "📖 Hollywood Screenplay & Fountain Format",
      desc: "Draft and format screenplay scenes with automatic AST node breakdown and FDX export.",
      prompt: "Draft a gritty Hollywood-standard screenplay scene formatted in Fountain syntax with character action nodes and dialogue."
    },
    {
      category: "⚔️ Swarm",
      title: "🛡️ Matrix Doctor 20-Port System Diagnostic",
      desc: "Benchmark socket latency and database health across all 20 background service ports.",
      prompt: "Run a full Matrix Doctor diagnostic scan across all 20 service ports and verify database health."
    },
    {
      category: "🏠 Automation",
      title: "🏠 Activate Command Center Protocol",
      desc: "Dim studio lights, initialize security dashboard, and boot primary workstation monitors.",
      prompt: "Run the command center boot sequence: activate smart lighting, wake local dashboard, and initialize proxy network."
    },
    {
      category: "🏠 Automation",
      title: "🕸️ Test Go-Matrix Proxy Multiplex",
      desc: "Stress-test Port 8000 reverse-proxy socket multiplexing to prevent starvation.",
      prompt: "Ping the Go API Gateway at Port 8000 to verify reverse-proxy socket multiplexing and memory mapping integrity."
    },
    {
      category: "💻 Developer",
      title: "🚀 Trigger Vercel Edge Deploy",
      desc: "Run Vite build pipeline, execute ESLint, and deploy to Vercel/Firebase edge network.",
      prompt: "Initialize the production build pipeline, verify React boundary state, and deploy the latest artifact to Firebase Hosting."
    },
    {
      category: "💻 Developer",
      title: "🕷️ Deep Cyber-Scrape Analysis",
      desc: "Launch headless Chromium to scrape top cybersecurity architectures and parse with Lexicon.",
      prompt: "Use your web scraping tools to pull the latest front-end architecture trends and cross-reference them with our Lexicon Vault."
    },
    {
      category: "🎙️ Studio",
      title: "🎙️ Generate TTS Podcast Host Track",
      desc: "Synthesize a 30-second intro using Kokoro TTS and load into the local buffer.",
      prompt: "Generate a dynamic AI podcast host introduction script and synthesize it into the local audio buffer."
    },
    {
      category: "📈 Finance",
      title: "📈 Quantitative Market Ledger",
      desc: "Query financial intelligence DB and compute standard deviation on the latest asset vectors.",
      prompt: "Query the financial intelligence database for historical asset vectors and run a quantitative market analysis."
    }
  ];

  // Filtered Slash Commands and Starters for Dropdown
  const filteredCommands = SLASH_COMMANDS.filter(c => {
    const matchesCategory = selectedCommandCategory === 'All' || c.category === selectedCommandCategory;
    if (!matchesCategory) return false;
    if (!commandSearchQuery) return true;
    const q = commandSearchQuery.toLowerCase();
    const cmdMatch = c.cmd.toLowerCase().includes(q) || (c.aliases && c.aliases.some(a => a.toLowerCase().includes(q)));
    const titleMatch = c.title.toLowerCase().includes(q);
    const descMatch = c.desc.toLowerCase().includes(q);
    return cmdMatch || titleMatch || descMatch;
  });

  const filteredStarters = starterCards.filter(s => {
    const matchesCat = selectedCommandCategory === 'All' || selectedCommandCategory === '🚀 Fast Starters' || s.category === selectedCommandCategory;
    if (!matchesCat) return false;
    if (!commandSearchQuery) return true;
    const q = commandSearchQuery.toLowerCase();
    return s.title.toLowerCase().includes(q) || s.desc.toLowerCase().includes(q) || s.prompt.toLowerCase().includes(q);
  });

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 170px)',
      minHeight: '600px',
      background: 'linear-gradient(180deg, #0d0f14 0%, #07090e 100%)',
      borderRadius: '12px',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
      overflow: 'hidden',
      color: '#e2e8f0',
      fontFamily: 'Inter, system-ui, sans-serif',
    }}>
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        multiple
        style={{ display: 'none' }}
      />

      {/* System Status Dashboard Bar */}
      <div style={{
        padding: '12px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(15, 19, 28, 0.95)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '10px', height: '10px', borderRadius: '50%',
            background: isLoading ? '#f59e0b' : '#10b981',
            boxShadow: isLoading ? '0 0 10px #f59e0b' : '0 0 10px #10b981',
          }} />
          <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc', letterSpacing: '0.5px' }}>
            STEHOUWER LLM CENTRAL HUB
          </span>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 600 }}>Active Model:</span>
            <select
              value={selectedModel || 'stehouwer_llm'}
              onChange={(e) => useAppStore.getState().setSelectedModel(e.target.value)}
              style={{
                fontSize: '0.75rem',
                background: 'rgba(59, 130, 246, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                color: '#60a5fa',
                padding: '4px 12px',
                borderRadius: '8px',
                fontWeight: 700,
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value="stehouwer_llm" style={{ background: '#0d1117', color: '#60a5fa' }}>⚡ Stehouwer LLM (Unified Swarm System)</option>
              <option value="gemini-1.5-pro" style={{ background: '#0d1117', color: '#60a5fa' }}>✨ Google Gemini 1.5 Pro (Cloud Backup)</option>
              <option value="gemini-1.5-flash" style={{ background: '#0d1117', color: '#38bdf8' }}>⚡ Google Gemini 1.5 Flash (Fast Backup)</option>
              <option value="gemini-2.0-flash" style={{ background: '#0d1117', color: '#a855f7' }}>🚀 Google Gemini 2.0 Flash (Next-Gen)</option>
              <option value="stehouwer_qwen:latest" style={{ background: '#0d1117', color: '#a855f7' }}>🚀 Stehouwer Qwen 23B (High Capacity)</option>
              <option value="stehouwer_dolphin:latest" style={{ background: '#0d1117', color: '#f43f5e' }}>🐬 Stehouwer Dolphin 8.5B (Uncensored)</option>
              <option value="stehouwer_hermes:latest" style={{ background: '#0d1117', color: '#38bdf8' }}>🔮 Stehouwer Hermes 8.5B (Reasoning)</option>
              <option value="qwen2.5-coder:latest" style={{ background: '#0d1117', color: '#34d399' }}>💻 Qwen 2.5 Coder (Polyglot Engineer)</option>
              <option value="gemma4:12b" style={{ background: '#0d1117', color: '#fbbf24' }}>💎 Google Gemma 4 12B</option>
              <option value="qwen3.6:latest" style={{ background: '#0d1117', color: '#c084fc' }}>🧠 Qwen 3.6 23B (Heavy Reasoning)</option>
              <option value="command-r:latest" style={{ background: '#0d1117', color: '#818cf8' }}>📚 Cohere Command-R (RAG Specialist)</option>
              <option value="mixtral:latest" style={{ background: '#0d1117', color: '#f472b6' }}>🧩 Mixtral 8x7B (MoE Architecture)</option>
              <option value="llama3.1:latest" style={{ background: '#0d1117', color: '#cbd5e1' }}>🦙 Llama 3.1 8B (Base Model)</option>
            </select>
          </div>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 600 }}>Target:</span>
            <select
              value={targetDevice}
              onChange={(e) => setTargetDevice(e.target.value)}
              style={{
                fontSize: '0.75rem',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                color: '#34d399',
                padding: '4px 12px',
                borderRadius: '8px',
                fontWeight: 700,
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value="Host PC (Local)" style={{ background: '#0d1117', color: '#34d399' }}>🖥️ Host PC (Local)</option>
              <option value="Mobile Phone (ADB)" style={{ background: '#0d1117', color: '#f59e0b' }}>📱 Mobile Phone (ADB)</option>
            </select>
          </div>
        </div>

        {/* Feature Badges & Quick Action Controls */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '0.72rem', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', color: '#34d399', padding: '3px 8px', borderRadius: '6px' }}>
            ⚡ 70+ DBs Ready (2ms)
          </span>
          <span style={{ fontSize: '0.72rem', background: 'rgba(168,85,247,0.12)', border: '1px solid rgba(168,85,247,0.3)', color: '#c084fc', padding: '3px 8px', borderRadius: '6px' }}>
            🛠️ 8 Master Tools
          </span>
          <span style={{ fontSize: '0.72rem', background: 'rgba(236,72,153,0.12)', border: '1px solid rgba(236,72,153,0.3)', color: '#f472b6', padding: '3px 8px', borderRadius: '6px' }}>
            🎨 ComfyUI Port 8189
          </span>

          <button
            onClick={() => {
              const url = `${window.location.origin}${window.location.pathname}?tab=chat`;
              navigator.clipboard.writeText(url).then(() => {
                setCopiedChatUrl(true);
                setTimeout(() => setCopiedChatUrl(false), 2500);
              });
            }}
            style={{
              background: copiedChatUrl ? '#10b981' : 'rgba(56, 189, 248, 0.12)',
              color: copiedChatUrl ? '#ffffff' : '#38bdf8',
              border: '1px solid #38bdf8',
              padding: '4px 10px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: '700'
            }}
          >
            🔗 {copiedChatUrl ? 'Copied!' : 'Share IDE'}
          </button>

          <button
            onClick={handleSaveToMemoryAndClear}
            disabled={isSavingMemory}
            title="Ingest entire conversation history into ChromaDB, SQLite Vault, and Master Memory, then clear chat"
            style={{
              background: 'linear-gradient(135deg, rgba(147, 51, 234, 0.25), rgba(99, 102, 241, 0.25))',
              color: '#c084fc',
              border: '1px solid rgba(168, 85, 247, 0.5)',
              padding: '4px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              boxShadow: '0 2px 8px rgba(147, 51, 234, 0.3)'
            }}
          >
            <span>💾</span>
            <span>{isSavingMemory ? 'Ingesting...' : 'Save to Memory & Clear'}</span>
          </button>

          <button
            onClick={handleSaveToMemoryAndClear}
            title="Reset Chat & View 18 Quick Starter Showcase Cards"
            style={{
              background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
              color: '#ffffff',
              border: '1px solid #60a5fa',
              padding: '4px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: '700',
              boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)'
            }}
          >
            ⚡ 18 Quick Starters
          </button>

          <button
            onClick={() => {
              setFooterInput('/mission ');
              document.querySelector('textarea')?.focus();
            }}
            title="Launch an Autonomous 5-Phase Mission (AI-BS & Antigravity Unison)"
            style={{
              background: 'linear-gradient(135deg, rgba(236, 72, 153, 0.25), rgba(168, 85, 247, 0.25))',
              color: '#f472b6',
              border: '1px solid rgba(236, 72, 153, 0.5)',
              padding: '4px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              boxShadow: '0 2px 8px rgba(236, 72, 153, 0.25)'
            }}
          >
            <span>🎯</span>
            <span>Mission Control</span>
          </button>

          <button
            onClick={() => {
              setFooterInput('/grill ');
              document.querySelector('textarea')?.focus();
            }}
            title="Pre-Flight Architectural Grill: stress-test proposals across 4 branches with 1-click recommendations"
            style={{
              background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.25), rgba(245, 158, 11, 0.25))',
              color: '#fb923c',
              border: '1px solid rgba(245, 158, 11, 0.5)',
              padding: '4px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              boxShadow: '0 2px 8px rgba(245, 158, 11, 0.25)'
            }}
          >
            <span>🔥</span>
            <span>Grill Architecture</span>
          </button>

          <button
            onClick={() => setShowTips(!showTips)}
            style={{
              background: '#21262d',
              color: '#c9d1d9',
              border: '1px solid #30363d',
              padding: '4px 10px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: '600'
            }}
          >
            💡 {showTips ? 'Hide Tips' : 'IDE Guide'}
          </button>
        </div>
      </div>

      {/* Memory Ingest Toast Notification */}
      {memoryToast && (
        <div style={{
          background: '#1e1b4b',
          borderBottom: '1px solid #818cf8',
          color: '#e0e7ff',
          padding: '8px 20px',
          fontSize: '0.82rem',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span>{memoryToast}</span>
        </div>
      )}

      {/* In-Tab Guidance Accordion */}
      {showTips && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.95) 100%)',
          borderBottom: '1px solid rgba(56, 189, 248, 0.35)',
          borderLeft: '4px solid #38bdf8',
          padding: '10px 20px',
          color: '#cbd5e1',
          fontSize: '0.8rem',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '12px'
        }}>
          <div style={{ background: '#0f172a', padding: '8px 12px', borderRadius: '6px', border: '1px solid #334155' }}>
            <strong style={{ color: '#38bdf8', display: 'block', marginBottom: '3px' }}>🧠 Multi-LLM Provider Engine:</strong>
            <span style={{ color: '#94a3b8' }}>Select between Local Ollama RTX 4090 models, Gemini 1.5/2.0, Claude 3.5, or Qwen 23B in real-time.</span>
          </div>
          <div style={{ background: '#0f172a', padding: '8px 12px', borderRadius: '6px', border: '1px solid #334155' }}>
            <strong style={{ color: '#38bdf8', display: 'block', marginBottom: '3px' }}>⚡ Efficiency Mode:</strong>
            <span style={{ color: '#94a3b8' }}>Toggle Efficiency Mode in the top navbar to unload local GPU weights for crypto mining or cloud GPU renting.</span>
          </div>
          <div style={{ background: '#0f172a', padding: '8px 12px', borderRadius: '6px', border: '1px solid #334155' }}>
            <strong style={{ color: '#38bdf8', display: 'block', marginBottom: '3px' }}>🎮 Unreal & ComfyUI Tools:</strong>
            <span style={{ color: '#94a3b8' }}>AI responses can generate runnable Unreal Engine 5.8 Python scripts and direct ComfyUI image render tasks.</span>
          </div>
        </div>
      )}

      {/* Error Popup */}
      {errorPopup && (
        <div style={{
          padding: '10px 20px', background: 'rgba(239,68,68,0.15)',
          borderBottom: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5',
          fontSize: '0.82rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span>⚠️ {errorPopup}</span>
          <button onClick={() => setErrorPopup(null)} style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Main Chat Feed */}
      <div
        ref={messageFeedRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
        }}
      >
        {chatMessages.length === 0 ? (
          <div style={{
            maxWidth: '900px', margin: 'auto', width: '100%', padding: '20px 0',
          }}>
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
              <div style={{
                fontSize: '2.5rem', marginBottom: '12px',
                background: 'linear-gradient(135deg, #60a5fa, #c084fc)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                fontWeight: 800
              }}>
                Stehouwer LLM Assistant
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.95rem', maxWidth: '600px', margin: '0 auto' }}>
                Your unified cognitive AI system. Select a quick starter action below, upload files/code for instant review, or type a custom prompt.
              </p>

              {/* Category Filter Pills */}
              <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '14px', flexWrap: 'wrap' }}>
                {starterCategories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setStarterCategory(cat)}
                    style={{
                      background: starterCategory === cat ? 'linear-gradient(135deg, #3b82f6, #6366f1)' : 'rgba(255, 255, 255, 0.05)',
                      border: starterCategory === cat ? '1px solid #60a5fa' : '1px solid rgba(255, 255, 255, 0.1)',
                      color: starterCategory === cat ? '#ffffff' : '#94a3b8',
                      padding: '4px 12px',
                      borderRadius: '20px',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Quick Action Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '12px',
              maxHeight: '440px',
              overflowY: 'auto',
              paddingRight: '4px'
            }}>
              {starterCards
                .filter(c => starterCategory === 'All' || c.category === starterCategory)
                .map((card, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleSendMessage(card.prompt)}
                    style={{
                      background: 'rgba(22, 27, 38, 0.75)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '10px',
                      padding: '14px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease-in-out',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(96, 165, 250, 0.6)';
                      e.currentTarget.style.background = 'rgba(30, 41, 59, 0.95)';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = '0 8px 20px rgba(59, 130, 246, 0.15)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                      e.currentTarget.style.background = 'rgba(22, 27, 38, 0.75)';
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.88rem', color: '#f1f5f9', marginBottom: '4px' }}>
                        {card.title}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: '1.4' }}>
                        {card.desc}
                      </div>
                    </div>
                    <div style={{ marginTop: '8px', fontSize: '0.7rem', color: '#60a5fa', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                      ⚡ Click to Launch →
                    </div>
                  </div>
                ))}
            </div>
          </div>
        ) : (
          chatMessages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '82%',
              }}
            >
              {/* Role Header */}
              <div style={{
                fontSize: '0.75rem', color: '#64748b', marginBottom: '4px', fontWeight: 500,
                textAlign: msg.role === 'user' ? 'right' : 'left',
              }}>
                {msg.role === 'user' ? '👤 You' : '🤖 Stehouwer LLM'}
              </div>

              {/* Message Bubble */}
              <div style={{
                padding: '14px 18px',
                borderRadius: msg.role === 'user' ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                background: msg.role === 'user' ? 'linear-gradient(135deg, #2563eb, #1d4ed8)' : 'rgba(26, 33, 48, 0.95)',
                border: msg.role === 'user' ? 'none' : '1px solid rgba(255,255,255,0.08)',
                boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
                color: '#f8fafc', fontSize: '0.92rem', lineHeight: '1.6',
              }}>
                {/* Attachment Badges */}
                {msg.attachments && msg.attachments.length > 0 && (
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
                    {msg.attachments.map((att, i) => (
                      <div key={i} style={{
                        fontSize: '0.75rem', background: 'rgba(255,255,255,0.15)',
                        padding: '4px 10px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '6px',
                      }}>
                        {att.is_image ? '🖼️' : '📎'} {att.name} ({(att.size/1024).toFixed(1)} KB)
                      </div>
                    ))}
                  </div>
                )}

                {/* Formatted Content */}
                {msg.editorData ? (
                  <FileEditorDrawer editorData={msg.editorData} />
                ) : msg.missionData ? (
                  <AutonomousMissionCard missionData={msg.missionData} />
                ) : msg.grillData ? (
                  <GrillSessionCard 
                    grillData={msg.grillData} 
                    onRespond={(grillId, response) => handleGrillRespond(grillId, response)}
                    onConclude={(grillId) => handleGrillConclude(grillId)}
                    onAcceptRecommendations={(grillId) => handleGrillRespond(grillId, 'yes')}
                    onBuildSpec={(grillId) => handleGrillConclude(grillId)}
                  />
                ) : msg.planData && Object.keys(msg.planData).length > 0 && msg.planData.plan_id ? (
                  <AgentPlanReviewCard 
                    planData={msg.planData} 
                    onExecutePlan={(plan_id, steps) => handleExecutePlan(plan_id, steps)}
                    onRequestRevisions={() => { setFooterInput(`@Developer revise plan ${msg.planData.plan_id}: `); document.querySelector('textarea')?.focus(); }}
                  />
                ) : (
                  <>
                    <FormattedMessageContent
                      content={msg.displayContent || msg.content || ''}
                      role={msg.role}
                    />
                    {msg.grillHelpExamples && (
                      <div className="mt-3 p-3.5 rounded-xl border border-amber-500/40 bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-black/60 shadow-lg flex flex-col gap-2.5">
                        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-300">
                          <span className="text-sm">⚡</span>
                          <span>Launch Architectural Grill with Preset Proposal:</span>
                        </div>
                        <div className="flex flex-col gap-2">
                          {msg.grillHelpExamples.map((ex, exIdx) => (
                            <button
                              key={exIdx}
                              onClick={() => triggerGrillProposal(ex)}
                              className="px-3 py-2.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/25 border border-amber-500/30 hover:border-amber-400 text-xs font-mono text-amber-200 hover:text-white transition-all text-left flex items-start gap-2.5 shadow-sm group"
                            >
                              <span className="text-sm text-amber-400 group-hover:scale-110 transition-transform">🔥</span>
                              <span className="flex-1 leading-snug">{ex}</span>
                              <span className="text-[10px] uppercase font-bold text-amber-400/80 group-hover:text-amber-300 ml-1">Run ➜</span>
                            </button>
                          ))}
                        </div>
                        <div className="text-[11px] text-zinc-400 flex items-center gap-2 pt-1 border-t border-amber-500/20">
                          <span>Or type any custom proposal:</span>
                          <code className="bg-black/60 text-amber-300 px-1.5 py-0.5 rounded border border-amber-500/30 text-[11px]">/grill &lt;proposal&gt;</code>
                        </div>
                      </div>
                    )}
                    {msg.role === 'assistant' && extractToolCall(msg.content) && (
                      <ExecutiveActionCard toolCall={extractToolCall(msg.content)} />
                    )}
                  </>
                )}

                {/* Reasoning Inspector for Assistant Messages */}
                {msg.role === 'assistant' && (
                  <ReasoningInspector msg={msg} />
                )}
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div style={{ alignSelf: 'flex-start', color: '#60a5fa', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 41, 59, 0.5)', padding: '8px 14px', borderRadius: '12px' }}>
            <span style={{ animation: 'spin 1s linear infinite' }}>⚙️</span> Stehouwer LLM is reasoning & executing tools...
          </div>
        )}
        
        {/* Invisible element to scroll into view */}
        <div ref={messagesEndRef} />
      </div>

      {/* Footer Input Controls */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(12, 15, 22, 0.98)',
      }}>
        {/* Attached Files Preview Bar (GPT Style) */}
        {attachments.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {attachments.map((att, index) => (
              <div key={index} style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                background: 'rgba(30, 41, 59, 0.95)',
                border: '1px solid rgba(59,130,246,0.5)',
                borderRadius: '8px', padding: '6px 12px', fontSize: '0.82rem', color: '#93c5fd',
              }}>
                <span>{att.is_image ? '🖼️' : '📄'}</span>
                <span style={{ fontWeight: 600 }}>{att.name}</span>
                <span style={{ color: '#64748b', fontSize: '0.72rem' }}>({(att.size / 1024).toFixed(1)} KB)</span>
                <button
                  onClick={() => removeAttachment(index)}
                  style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer', marginLeft: '4px', fontSize: '0.9rem' }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        {/* @Tag Quick Actions */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
          {['@Developer', '@Ecosystem', '@Calendar', '@Documents', '@Email'].map(tag => (
            <button
              key={tag}
              onClick={() => setFooterInput(prev => (prev ? prev + ' ' + tag + ' ' : tag + ' '))}
              style={{
                background: 'rgba(59, 130, 246, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                color: '#93c5fd',
                borderRadius: '12px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600,
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.3)'}
              onMouseOut={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)'}
            >
              {tag}
            </button>
          ))}
        </div>

        {/* Live Context Token Budget Gauge */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', fontSize: '0.72rem', color: '#94a3b8', padding: '0 2px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: '600', color: Math.floor(footerInput.length / 4) > 8192 ? '#f87171' : '#38bdf8' }}>
              📊 Context Budget: {footerInput.length.toLocaleString()} chars • ~{Math.floor(footerInput.length / 4).toLocaleString()} tokens
            </span>
            <span style={{ color: '#64748b' }}>({Math.min(100, Math.round((Math.floor(footerInput.length / 4) / 8192) * 100))}% of 8,192 max window)</span>
          </div>
          <div style={{ width: '120px', height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
            <div style={{
              width: `${Math.min(100, Math.round((Math.floor(footerInput.length / 4) / 8192) * 100))}%`,
              height: '100%',
              background: Math.floor(footerInput.length / 4) > 8192 ? '#ef4444' : 'linear-gradient(90deg, #38bdf8, #818cf8)'
            }} />
          </div>
        </div>

        {/* Phase 7.1 Control Bar Injected Above Input */}
        <ChatToolControlBar onToolToggle={setActiveTools} />
        <ChatContextToolbar activeContexts={activeContexts} onToggleContext={toggleContext} />

        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
          {/* Artifacts & Tools Hub Button */}
          <button
            onClick={() => setIsArtifactsModalOpen(true)}
            title="Open Live Artifacts & Autonomous Program Builder Hub"
            style={{
              height: '42px',
              padding: '0 12px',
              background: isArtifactsModalOpen ? 'linear-gradient(135deg, #059669, #10b981)' : 'rgba(16, 185, 129, 0.12)',
              border: `1px solid ${isArtifactsModalOpen ? '#34d399' : 'rgba(16, 185, 129, 0.35)'}`,
              borderRadius: '10px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: isArtifactsModalOpen ? '#ffffff' : '#34d399',
              transition: 'all 0.2s ease',
              whiteSpace: 'nowrap',
              flexShrink: 0
            }}
          >
            <span>📦 Artifacts & Tools</span>
          </button>

          {/* Ecosystem Ports & Tool Devices Mesh Button */}
          <button
            onClick={() => setIsPortMeshModalOpen(true)}
            title="Open Live Ecosystem Port Telemetry & Dynamic Tool Caller Mesh"
            style={{
              height: '42px',
              padding: '0 12px',
              background: isPortMeshModalOpen ? 'linear-gradient(135deg, #0284c7, #38bdf8)' : 'rgba(56, 189, 248, 0.12)',
              border: `1px solid ${isPortMeshModalOpen ? '#38bdf8' : 'rgba(56, 189, 248, 0.35)'}`,
              borderRadius: '10px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: isPortMeshModalOpen ? '#ffffff' : '#38bdf8',
              transition: 'all 0.2s ease',
              whiteSpace: 'nowrap',
              flexShrink: 0
            }}
          >
            <span>⚡ Ecosystem Ports</span>
          </button>

          {/* Unified Slash Commands & Fast Options Dropdown Button */}
          <div style={{ position: 'relative', flexShrink: 0 }} ref={commandsDropdownRef}>
            <button
              onClick={() => setShowCommandsDropdown(!showCommandsDropdown)}
              title="Open Slash Commands & Fast Options Palette (or type / in chat)"
              style={{
                height: '42px',
                padding: '0 13px',
                background: showCommandsDropdown 
                  ? 'linear-gradient(135deg, #0284c7, #4f46e5)' 
                  : 'rgba(56, 189, 248, 0.14)',
                border: `1px solid ${showCommandsDropdown ? '#38bdf8' : 'rgba(56, 189, 248, 0.4)'}`,
                borderRadius: '10px',
                cursor: 'pointer',
                fontSize: '0.82rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: showCommandsDropdown ? '#ffffff' : '#38bdf8',
                transition: 'all 0.2s ease',
                whiteSpace: 'nowrap',
                boxShadow: showCommandsDropdown ? '0 0 16px rgba(56, 189, 248, 0.4)' : 'none'
              }}
            >
              <span style={{ fontFamily: 'monospace', fontSize: '0.92rem', fontWeight: 800 }}>[/]</span>
              <span>Commands</span>
              <span style={{ fontSize: '0.65rem' }}>{showCommandsDropdown ? '▲' : '▼'}</span>
            </button>

            {/* Dropdown Menu Popup (Anchored Above the Button) */}
            {showCommandsDropdown && (
              <div style={{
                position: 'absolute',
                bottom: '50px',
                left: '0',
                width: 'min(580px, 92vw)',
                maxHeight: '480px',
                background: 'linear-gradient(180deg, #0d131f 0%, #060911 100%)',
                border: '1px solid rgba(56, 189, 248, 0.45)',
                borderRadius: '14px',
                boxShadow: '0 20px 50px rgba(0,0,0,0.9), 0 0 25px rgba(56, 189, 248, 0.2)',
                zIndex: 1100,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
              }}>
                {/* Header */}
                <div style={{
                  padding: '10px 14px',
                  background: 'rgba(15, 23, 42, 0.9)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.9rem' }}>⚡</span>
                    <span style={{ fontSize: '0.84rem', fontWeight: 800, color: '#38bdf8', letterSpacing: '0.3px' }}>
                      BS-Chat Commands & Fast Options
                    </span>
                    <span style={{
                      fontSize: '0.68rem',
                      background: 'rgba(56, 189, 248, 0.12)',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                      color: '#7dd3fc',
                      padding: '1px 7px',
                      borderRadius: '10px'
                    }}>
                      {filteredCommands.length + (selectedCommandCategory === 'All' || selectedCommandCategory === '🚀 Fast Starters' ? filteredStarters.length : 0)} options
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.68rem', color: '#64748b' }}>[Esc] to close</span>
                    <button
                      onClick={() => setShowCommandsDropdown(false)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#94a3b8',
                        fontSize: '1rem',
                        cursor: 'pointer',
                        padding: '0 4px',
                        lineHeight: 1
                      }}
                      title="Close Command Palette"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                {/* Search Input Bar */}
                <div style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255, 255, 255, 0.06)', background: 'rgba(0,0,0,0.4)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '8px', padding: '6px 10px' }}>
                    <span style={{ fontSize: '0.82rem', color: '#38bdf8' }}>🔍</span>
                    <input
                      type="text"
                      value={commandSearchQuery}
                      onChange={(e) => setCommandSearchQuery(e.target.value)}
                      placeholder="Filter commands or starters... (e.g. /read, /write, /ls, /edit, /monitor, /ps)"
                      style={{
                        flex: 1,
                        background: 'transparent',
                        border: 'none',
                        color: '#f8fafc',
                        fontSize: '0.8rem',
                        outline: 'none'
                      }}
                      autoFocus
                    />
                    {commandSearchQuery && (
                      <button
                        onClick={() => setCommandSearchQuery('')}
                        style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '0.75rem' }}
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>

                {/* Category Filter Tabs */}
                <div style={{
                  display: 'flex',
                  gap: '6px',
                  padding: '7px 12px',
                  background: 'rgba(11, 15, 25, 0.95)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                  overflowX: 'auto',
                  whiteSpace: 'nowrap'
                }}>
                  {COMMAND_CATEGORIES.map(cat => (
                    <button
                      key={cat}
                      onClick={() => setSelectedCommandCategory(cat)}
                      style={{
                        padding: '3px 9px',
                        borderRadius: '6px',
                        fontSize: '0.72rem',
                        fontWeight: selectedCommandCategory === cat ? 700 : 500,
                        background: selectedCommandCategory === cat ? 'linear-gradient(135deg, #0284c7, #4f46e5)' : 'rgba(255, 255, 255, 0.04)',
                        color: selectedCommandCategory === cat ? '#ffffff' : '#94a3b8',
                        border: `1px solid ${selectedCommandCategory === cat ? '#38bdf8' : 'rgba(255, 255, 255, 0.08)'}`,
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      {cat}
                    </button>
                  ))}
                </div>

                {/* Scrollable Command List */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {/* Render matching slash commands */}
                  {selectedCommandCategory !== '🚀 Fast Starters' && filteredCommands.map(c => (
                    <div
                      key={c.cmd}
                      style={{
                        padding: '8px 10px',
                        borderRadius: '8px',
                        background: 'rgba(255, 255, 255, 0.025)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '10px',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(56, 189, 248, 0.1)';
                        e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.35)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.025)';
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)';
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '2px', flexWrap: 'wrap' }}>
                          <span style={{
                            fontFamily: 'monospace',
                            fontSize: '0.82rem',
                            fontWeight: 800,
                            color: '#38bdf8',
                            background: 'rgba(56, 189, 248, 0.14)',
                            padding: '1px 6px',
                            borderRadius: '5px'
                          }}>
                            {c.example || c.cmd}
                          </span>
                          <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f1f5f9' }}>{c.title}</span>
                          <span style={{
                            fontSize: '0.62rem',
                            color: '#a78bfa',
                            background: 'rgba(167, 139, 250, 0.12)',
                            padding: '1px 5px',
                            borderRadius: '4px'
                          }}>
                            {c.badge}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.71rem', color: '#94a3b8', lineHeight: '1.3' }}>
                          {c.desc}
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '5px', flexShrink: 0 }}>
                        {c.zeroArg ? (
                          <button
                            onClick={() => {
                              setShowCommandsDropdown(false);
                              setFooterInput('');
                              handleSendMessage(c.cmd);
                            }}
                            style={{
                              background: 'linear-gradient(135deg, #10b981, #059669)',
                              color: '#ffffff',
                              border: 'none',
                              padding: '4px 10px',
                              borderRadius: '6px',
                              fontSize: '0.72rem',
                              fontWeight: 700,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)'
                            }}
                            title={`Execute ${c.cmd} immediately`}
                          >
                            <span>▶</span>
                            <span>Run</span>
                          </button>
                        ) : null}

                        <button
                          onClick={() => {
                            setShowCommandsDropdown(false);
                            const fillText = c.template || (c.cmd + ' ');
                            setFooterInput(fillText);
                            setTimeout(() => {
                              chatInputRef.current?.focus();
                              if (chatInputRef.current) {
                                chatInputRef.current.selectionStart = chatInputRef.current.selectionEnd = fillText.length;
                              }
                            }, 50);
                          }}
                          style={{
                            background: 'rgba(56, 189, 248, 0.12)',
                            color: '#38bdf8',
                            border: '1px solid rgba(56, 189, 248, 0.3)',
                            padding: '4px 8px',
                            borderRadius: '6px',
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            cursor: 'pointer'
                          }}
                          title="Insert template into chat bar"
                        >
                          ⚡ Use
                        </button>
                      </div>
                    </div>
                  ))}

                  {/* Render matching fast starter cards */}
                  {(selectedCommandCategory === 'All' || selectedCommandCategory === '🚀 Fast Starters') && (
                    <>
                      {selectedCommandCategory === 'All' && filteredStarters.length > 0 && (
                        <div style={{
                          padding: '6px 4px 2px 4px',
                          fontSize: '0.7rem',
                          fontWeight: 800,
                          color: '#818cf8',
                          letterSpacing: '0.5px',
                          borderTop: '1px solid rgba(255,255,255,0.06)',
                          marginTop: '4px'
                        }}>
                          🚀 FAST STARTER PRESETS
                        </div>
                      )}
                      {filteredStarters.map((card, idx) => (
                        <div
                          key={`starter-${idx}`}
                          onClick={() => {
                            setShowCommandsDropdown(false);
                            handleSendMessage(card.prompt);
                          }}
                          style={{
                            padding: '8px 10px',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            background: 'rgba(255, 255, 255, 0.025)',
                            border: '1px solid rgba(255, 255, 255, 0.06)',
                            transition: 'all 0.15s ease',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'rgba(99, 102, 241, 0.15)';
                            e.currentTarget.style.borderColor = 'rgba(129, 140, 248, 0.4)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.025)';
                            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)';
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f1f5f9' }}>{card.title}</span>
                              <span style={{ fontSize: '0.62rem', background: 'rgba(255,255,255,0.06)', padding: '1px 5px', borderRadius: '4px', color: '#94a3b8' }}>
                                {card.category}
                              </span>
                            </div>
                            <div style={{ fontSize: '0.7rem', color: '#94a3b8', lineHeight: '1.3' }}>{card.desc}</div>
                          </div>
                          <span style={{ fontSize: '0.72rem', color: '#818cf8', fontWeight: 700, flexShrink: 0, paddingLeft: '8px' }}>
                            Launch ▶
                          </span>
                        </div>
                      ))}
                    </>
                  )}

                  {/* Empty State */}
                  {filteredCommands.length === 0 && (selectedCommandCategory !== '🚀 Fast Starters' || filteredStarters.length === 0) && (
                    <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.78rem' }}>
                      No commands or starters matching "{commandSearchQuery}". Try /monitor, /spaces, or /ps.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Attachment Button 📎 */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploadingFile || isLoading}
            title="Attach code or document for LLM analysis"
            style={{
              width: '42px', height: '42px',
              background: isUploadingFile ? 'rgba(59,130,246,0.3)' : 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '10px', cursor: 'pointer', fontSize: '1.2rem',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8',
              transition: 'background 0.2s',
            }}
          >
            📎
          </button>

          <textarea
            ref={chatInputRef}
            value={footerInput}
            onChange={handleInputChange}
            onKeyDown={(e) => {
              if (e.key === 'Escape' && showCommandsDropdown) {
                e.preventDefault();
                setShowCommandsDropdown(false);
                return;
              }
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                setShowCommandsDropdown(false);
                handleSendMessage();
              }
            }}
            placeholder={attachments.length > 0 ? "Add instructions for attached files..." : "Message Stehouwer LLM or run /read, /write, /ls, /edit, /ps, /wsl... (Enter to send)"}
            rows={2}
            style={{
              flex: 1,
              background: 'rgba(0,0,0,0.5)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '10px',
              color: '#f8fafc',
              padding: '10px 14px',
              fontSize: '0.9rem',
              resize: 'none',
              outline: 'none',
              fontFamily: 'inherit',
              lineHeight: '1.5',
            }}
          />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                onClick={toggleListening}
                title="Toggle Voice Input (STT)"
                style={{
                  width: '42px', height: '40px',
                  background: isListening ? 'rgba(239,68,68,0.25)' : 'rgba(255,255,255,0.06)',
                  border: `1px solid ${isListening ? 'rgba(239,68,68,0.5)' : 'rgba(255,255,255,0.12)'}`,
                  borderRadius: '10px', cursor: 'pointer', fontSize: '1.1rem',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                🎙️
              </button>
              <button
                onClick={() => setAutoSpeak(!autoSpeak)}
                title={autoSpeak ? "Auto Readout (TTS) Enabled" : "Enable Auto Readout (TTS)"}
                style={{
                  width: '42px', height: '40px',
                  background: autoSpeak ? 'rgba(16,185,129,0.25)' : 'rgba(255,255,255,0.06)',
                  border: `1px solid ${autoSpeak ? 'rgba(16,185,129,0.5)' : 'rgba(255,255,255,0.12)'}`,
                  borderRadius: '10px', cursor: 'pointer', fontSize: '1.1rem',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                🔊
              </button>
            </div>
            <button
              onClick={() => handleSendMessage()}
              disabled={(!footerInput.trim() && attachments.length === 0) || isLoading}
              style={{
                width: '42px', height: '40px',
                background: (footerInput.trim() || attachments.length > 0) && !isLoading ? '#2563eb' : 'rgba(255,255,255,0.06)',
                border: 'none',
                borderRadius: '10px',
                cursor: (footerInput.trim() || attachments.length > 0) && !isLoading ? 'pointer' : 'not-allowed',
                fontSize: '1.1rem',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: (footerInput.trim() || attachments.length > 0) && !isLoading ? '#fff' : '#475569',
                transition: 'background 0.2s',
              }}
            >
              ➤
            </button>
          </div>
        </div>

        {/* Clear screen & Action Toolbar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {/* Disable / Enable Backend & Stop Process Button */}
            <button
              onClick={handleStopOrToggleBackend}
              style={{
                background: isLoading 
                  ? 'rgba(239, 68, 68, 0.22)' 
                  : isBackendDisabled 
                    ? 'rgba(239, 68, 68, 0.15)' 
                    : 'rgba(16, 185, 129, 0.12)',
                color: isLoading 
                  ? '#f87171' 
                  : isBackendDisabled 
                    ? '#f87171' 
                    : '#34d399',
                border: isLoading 
                  ? '1px solid rgba(239, 68, 68, 0.55)' 
                  : isBackendDisabled 
                    ? '1px solid rgba(239, 68, 68, 0.4)' 
                    : '1px solid rgba(16, 185, 129, 0.35)',
                borderRadius: '6px',
                padding: '3px 10px',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: '700',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                transition: 'all 0.2s',
                boxShadow: isBackendDisabled ? '0 0 10px rgba(239, 68, 68, 0.25)' : (isLoading ? '0 0 10px rgba(239, 68, 68, 0.35)' : 'none')
              }}
              title={isLoading ? "Abort active process and pause backend" : (isBackendDisabled ? "Click to enable backend communication" : "Click to disable backend communication")}
            >
              {isLoading ? (
                <>🛑 <span>Stop Process</span></>
              ) : isBackendDisabled ? (
                <>⏸️ <span>Enable Backend (Disabled)</span></>
              ) : (
                <>⚡ <span>Disable Backend</span></>
              )}
            </button>

            {chatMessages.length > 0 && (
              <button
                onClick={() => setChatMessages([])}
                style={{
                  background: 'none', border: 'none', color: '#64748b', fontSize: '0.75rem', cursor: 'pointer',
                }}
              >
                Clear Screen (Retains Memory)
              </button>
            )}

            <button
              onClick={() => handleSendMessage('/monitor')}
              style={{
                background: 'rgba(245, 158, 11, 0.12)',
                color: '#fbbf24',
                border: '1px solid rgba(245, 158, 11, 0.35)',
                borderRadius: '6px',
                padding: '3px 8px',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: '600'
              }}
              title="Monitor all 43 Master Hub modules, 20 daemons, and storage matrix"
            >
              👑 43-Module Oversight
            </button>

            <button
              onClick={() => handleSendMessage('/spaces')}
              style={{
                background: 'rgba(99, 102, 241, 0.12)',
                color: '#a5b4fc',
                border: '1px solid rgba(99, 102, 241, 0.35)',
                borderRadius: '6px',
                padding: '3px 8px',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: '600'
              }}
              title="Inspect all 11 memory-mapped SQLite database spaces"
            >
              🔍 11 Spaces
            </button>

            <button
              onClick={() => {
                const text = window.prompt("Enter data or note to persist into SQLite database space:");
                if (text && text.trim()) handleSendMessage('/ingest ' + text.trim());
              }}
              style={{
                background: 'rgba(16, 185, 129, 0.12)',
                color: '#34d399',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                borderRadius: '6px',
                padding: '3px 8px',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: '600'
              }}
              title="On-demand structured data ingestion to database"
            >
              💾 Ingest to DB
            </button>

            <button
              onClick={() => setIsGovernanceOpen(true)}
              style={{
                background: 'rgba(56, 189, 248, 0.1)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                borderRadius: '6px',
                padding: '3px 8px',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              🛡️ Risk & Governance Review
            </button>

            <button
              onClick={() => setIsStressTestOpen(true)}
              style={{
                background: 'rgba(129, 140, 248, 0.1)',
                color: '#818cf8',
                border: '1px solid rgba(129, 140, 248, 0.3)',
                borderRadius: '6px',
                padding: '3px 8px',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              📊 Context Stress Test
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.7rem',
              color: isBackendDisabled ? '#f87171' : '#34d399',
              background: isBackendDisabled ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.1)',
              border: isBackendDisabled ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(16, 185, 129, 0.25)',
              padding: '2px 7px',
              borderRadius: '6px',
              fontWeight: 600
            }}>
              <span style={{ fontSize: '0.65rem' }}>{isBackendDisabled ? '🔴' : '🟢'}</span> {isBackendDisabled ? 'Backend Offline' : 'Auto-Save Active'}
            </span>
            <span style={{ color: '#475569', fontSize: '0.72rem' }}>
              Stehouwer LLM v5.296.0 • RTX 4090 GPU Accelerated
            </span>
          </div>
        </div>
      </div>

      {/* Live Workspace Artifacts & Autonomous Program Builder Hub Modal */}
      <ArtifactsAndToolsModal
        isOpen={isArtifactsModalOpen}
        onClose={() => setIsArtifactsModalOpen(false)}
        onInsertText={(text) => setFooterInput(prev => (prev ? prev + text : text))}
        backendUrl={BACKEND_URL}
      />

      {/* Unified Ecosystem Port Telemetry & Dynamic Tool Caller Modal */}
      {isPortMeshModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.85)', backdropFilter: 'blur(8px)',
          zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px'
        }}>
          <div style={{
            background: '#0f172a', border: '1px solid rgba(56, 189, 248, 0.4)',
            borderRadius: '20px', width: '100%', maxWidth: '1100px', maxHeight: '90vh', overflowY: 'auto', padding: '20px',
            boxShadow: '0 25px 60px rgba(0,0,0,0.8)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '1.4rem' }}>⚡</span>
                <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: '800', color: '#38bdf8' }}>
                  Ecosystem Port Telemetry & Dynamic Tool Mesh
                </h3>
              </div>
              <button onClick={() => setIsPortMeshModalOpen(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.4rem', cursor: 'pointer' }}>✕</button>
            </div>
            <EcosystemPortMonitorWidget backendUrl={BACKEND_URL} />
          </div>
        </div>
      )}

      {/* Content Governance & Risk Assessment Modal */}
      <ContentGovernanceRiskModal 
        isOpen={isGovernanceOpen} 
        onClose={() => setIsGovernanceOpen(false)}
        initialText={footerInput}
        onApplyRefinement={(newText) => setFooterInput(newText)}
      />

      {/* Context Window Stress Test Benchmark Modal */}
      {isStressTestOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.85)', backdropFilter: 'blur(8px)',
          zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px'
        }}>
          <div style={{
            background: '#0f172a', border: '1px solid rgba(129, 140, 248, 0.4)',
            borderRadius: '16px', width: '100%', maxWidth: '640px', padding: '24px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.6)', color: '#f8fafc'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '1.3rem' }}>📊</span>
                <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#818cf8' }}>BS-Chat Context Window Capacity Benchmark</h3>
              </div>
              <button onClick={() => setIsStressTestOpen(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.2rem', cursor: 'pointer' }}>✕</button>
            </div>

            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: 0, marginBottom: '18px' }}>
              Test BS-Chat context limits and needle-in-a-haystack accuracy across local RTX 4090 hardware context windows.
            </p>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ fontSize: '0.78rem', color: '#cbd5e1', fontWeight: '600', display: 'block', marginBottom: '8px' }}>
                Select Context Payload Tier:
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                {['1k', '2k', '4k', '8k', '16k'].map(t => (
                  <button
                    key={t}
                    onClick={() => setStressTier(t)}
                    style={{
                      background: stressTier === t ? '#4f46e5' : 'rgba(255,255,255,0.05)',
                      color: stressTier === t ? '#ffffff' : '#cbd5e1',
                      border: `1px solid ${stressTier === t ? '#6366f1' : 'rgba(255,255,255,0.1)'}`,
                      borderRadius: '8px', padding: '8px 0', fontSize: '0.82rem', fontWeight: '700', cursor: 'pointer'
                    }}
                  >
                    {t.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={() => handleRunStressTest(stressTier)}
              disabled={isRunningStress}
              style={{
                width: '100%', background: isRunningStress ? '#312e81' : 'linear-gradient(135deg, #4f46e5, #3b82f6)',
                color: '#fff', border: 'none', borderRadius: '10px', padding: '12px',
                fontSize: '0.9rem', fontWeight: '700', cursor: isRunningStress ? 'wait' : 'pointer',
                boxShadow: '0 4px 14px rgba(79,70,229,0.4)', marginBottom: '18px'
              }}
            >
              {isRunningStress ? '⚡ Executing Context Benchmark...' : `Run ${stressTier.toUpperCase()} Token Stress Test`}
            </button>

            {stressResult && (
              <div style={{
                background: 'rgba(255,255,255,0.03)', border: `1px solid ${stressResult.accuracy_score === 100 ? 'rgba(52, 211, 153, 0.4)' : 'rgba(248, 113, 113, 0.4)'}`,
                borderRadius: '12px', padding: '16px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: '700', color: stressResult.accuracy_score === 100 ? '#34d399' : '#f87171' }}>
                    {stressResult.accuracy_score === 100 ? '✅ 100% NEEDLE RETENTION (PASSED)' : '❌ BENCHMARK FAILED'}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Latency: {stressResult.latency_ms}ms</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', fontSize: '0.78rem', marginBottom: '12px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}>
                    <div style={{ color: '#64748b' }}>Allocated num_ctx</div>
                    <div style={{ fontWeight: '700', color: '#f8fafc' }}>{stressResult.num_ctx_allocated || 'N/A'} tokens</div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}>
                    <div style={{ color: '#64748b' }}>Input Characters</div>
                    <div style={{ fontWeight: '700', color: '#f8fafc' }}>{stressResult.character_count?.toLocaleString() || 'N/A'}</div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}>
                    <div style={{ color: '#64748b' }}>Throughput</div>
                    <div style={{ fontWeight: '700', color: '#f8fafc' }}>{stressResult.tokens_per_sec || 'N/A'} tok/s</div>
                  </div>
                </div>

                <div style={{ fontSize: '0.78rem', background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '6px', color: '#cbd5e1', fontFamily: 'monospace' }}>
                  <strong>Model Response:</strong> {stressResult.model_response || stressResult.message}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}






