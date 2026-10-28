import AuthenticatedChatMedia from '/src/components/AuthenticatedChatMedia.jsx';
import { useConversationMemory, ConversationMemoryStatus } from '/src/hooks/useConversationMemory.jsx';
import { archiveChatAndClear } from '/src/utils/chatArchive.js';
import CodingPreparationPanel from './CodingPreparationPanel';
import React, { useState, useRef, useEffect } from 'react';
import { readChatHttpResponse, chatResponseText } from '/src/utils/chatHttpResponse.js';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useAppStore } from './useAppStore';
import TapToRunCanvas, { extractStagedPayloads } from './TapToRunCanvas';
import { 
  Menu, Plus, Send, Mic, MicOff, Image, Paperclip, Volume2, VolumeX, 
  ChevronDown, Check, Copy, ExternalLink, Download, Monitor, Trash2, 
  X, Cpu, ArrowUp, RefreshCw, Sparkles, Share2, Smartphone,
  Play, Square, Terminal, WrapText,
  Brain, Info, Layers
} from 'lucide-react';

// ─── Sovereign 4-Point AI Star SVG ──────────────────────────────────────────
function StehouwerStar({ size = 28, className = '' }) {
  return (
    <svg 
      viewBox="0 0 24 24" 
      width={size} 
      height={size} 
      fill="none" 
      className={className}
      style={{ flexShrink: 0 }}
    >
      <path 
        d="M12 0C12 6.627 6.627 12 0 12C6.627 12 12 17.373 12 24C12 17.373 17.373 12 24 12C17.373 12 12 6.627 12 0Z" 
        fill="url(#stehouwerGradMobile)" 
      />
      <defs>
        <linearGradient id="stehouwerGradMobile" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#4285f4" />
          <stop offset="50%" stopColor="#9b72cf" />
          <stop offset="100%" stopColor="#d96570" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// ─── Code Block with Syntax Highlighting, 1-Click Copy & Inline Execution ─────
const MobileCodeBlock = React.memo(function MobileCodeBlock({ language, code, backendUrl }) {
  const [copied, setCopied] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [showOutput, setShowOutput] = useState(false);
  const [wordWrap, setWordWrap] = useState(false);

  const langLower = (language || '').toLowerCase().trim();
  const isExecutable = [
    'python', 'py', 'javascript', 'js', 'node',
    'bash', 'sh', 'shell', 'powershell', 'ps', 'ps1',
    'go', 'golang', 'rust', 'rs', 'cpp', 'c'
  ].includes(langLower);

  const handleCopy = () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(code);
      } else {
        const ta = document.createElement('textarea');
        ta.value = code;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  const handleRun = async () => {
    if (isExecuting) return;
    setIsExecuting(true);
    setShowOutput(true);
    setExecResult(null);

    const candidateBases = [
      backendUrl,
      'https://api.brettstehouwer.live',
      'http://127.0.0.1:8080',
      'http://localhost:8080',
      'http://192.168.4.92:8080'
    ].filter(Boolean);

    let executed = false;
    for (const base of candidateBases) {
      try {
        const cmdType = langLower === 'js' || langLower === 'javascript'
          ? 'node'
          : (langLower === 'sh' || langLower === 'shell' ? 'bash' : (langLower === 'ps' ? 'powershell' : langLower));

        const res = await fetch(`${base}/api/executive/run`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            command_type: cmdType,
            target: code,
            payload: { timeout_seconds: 30 }
          }),
          signal: AbortSignal.timeout ? AbortSignal.timeout(35000) : undefined
        });

        if (res.ok) {
          const data = await res.json();
          setExecResult(data);
          executed = true;
          break;
        }
      } catch (e) {
        console.warn(`Execution attempt on ${base} failed:`, e);
      }
    }

    if (!executed) {
      setExecResult({
        status: 'error',
        stderr: 'Unable to reach local workstation execution daemon on Port 8080.'
      });
    }
    setIsExecuting(false);
  };

  return (
    <div style={{
      margin: '10px 0',
      borderRadius: '10px',
      overflow: 'hidden',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      background: '#0d1117'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '6px 12px',
        background: 'rgba(255, 255, 255, 0.04)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        fontSize: '0.72rem',
        color: '#94a3b8'
      }}>
        <span style={{ fontWeight: 600, textTransform: 'uppercase', color: '#60a5fa' }}>
          {language || 'code'}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* Word Wrap Toggle */}
          <button
            onClick={() => setWordWrap(w => !w)}
            style={{
              background: wordWrap ? 'rgba(96, 165, 250, 0.2)' : 'rgba(255, 255, 255, 0.06)',
              border: `1px solid ${wordWrap ? 'rgba(96, 165, 250, 0.4)' : 'rgba(255, 255, 255, 0.12)'}`,
              borderRadius: '4px',
              color: wordWrap ? '#60a5fa' : '#94a3b8',
              padding: '3px 7px',
              fontSize: '0.68rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px'
            }}
            title="Toggle Word Wrap"
          >
            <WrapText size={11} />
            <span>{wordWrap ? 'Wrap' : 'Scroll'}</span>
          </button>

          {/* Run Code Button */}
          {isExecutable && (
            <button
              onClick={handleRun}
              disabled={isExecuting}
              style={{
                background: isExecuting ? 'rgba(245, 158, 11, 0.2)' : 'rgba(52, 211, 153, 0.15)',
                border: `1px solid ${isExecuting ? 'rgba(245, 158, 11, 0.4)' : 'rgba(52, 211, 153, 0.3)'}`,
                borderRadius: '4px',
                color: isExecuting ? '#fbbf24' : '#34d399',
                padding: '3px 8px',
                fontSize: '0.7rem',
                cursor: isExecuting ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: 600
              }}
              title="Execute on host workstation"
            >
              <Play size={11} fill={isExecuting ? '#fbbf24' : '#34d399'} />
              <span>{isExecuting ? 'Running...' : 'Run'}</span>
            </button>
          )}

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            style={{
              background: copied ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.08)',
              border: `1px solid ${copied ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255, 255, 255, 0.15)'}`,
              borderRadius: '4px',
              color: copied ? '#34d399' : '#cbd5e1',
              padding: '3px 8px',
              fontSize: '0.7rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language || 'text'}
        wrapLines={wordWrap}
        wrapLongLines={wordWrap}
        customStyle={{
          margin: 0,
          padding: '10px 12px',
          fontSize: '0.8rem',
          background: 'transparent',
          lineHeight: '1.45',
          overflowX: wordWrap ? 'hidden' : 'auto',
          whiteSpace: wordWrap ? 'pre-wrap' : 'pre',
          wordBreak: wordWrap ? 'break-word' : 'normal'
        }}
      >
        {code}
      </SyntaxHighlighter>

      {/* Terminal Output Drawer */}
      {showOutput && (
        <div style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.12)',
          background: '#040711',
          padding: '8px 12px',
          fontSize: '0.75rem',
          fontFamily: 'Consolas, monospace'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '6px',
            color: '#64748b',
            fontSize: '0.7rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Terminal size={12} color="#60a5fa" />
              <span style={{ color: '#93c5fd', fontWeight: 600 }}>Host Terminal Output</span>
              {execResult && (
                <span style={{
                  padding: '1px 6px',
                  borderRadius: '10px',
                  fontSize: '0.65rem',
                  background: (execResult.returncode === 0 || execResult.status === 'success') ? 'rgba(52, 211, 153, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: (execResult.returncode === 0 || execResult.status === 'success') ? '#34d399' : '#f87171'
                }}>
                  exit {execResult.returncode ?? (execResult.status === 'success' ? 0 : 1)}
                  {execResult.execution_time_ms ? ` · ${execResult.execution_time_ms}ms` : ''}
                </span>
              )}
            </div>
            <button
              onClick={() => setShowOutput(false)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#64748b',
                cursor: 'pointer',
                padding: '2px'
              }}
              title="Close Output"
            >
              <X size={13} />
            </button>
          </div>
          {isExecuting && (
            <div style={{ color: '#fbbf24', fontStyle: 'italic', padding: '4px 0' }}>
              Executing on root workstation...
            </div>
          )}
          {execResult && (
            <div style={{
              maxHeight: '180px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              lineHeight: '1.4'
            }}>
              {execResult.stdout && <div style={{ color: '#34d399' }}>{execResult.stdout}</div>}
              {execResult.stderr && <div style={{ color: '#f87171' }}>{execResult.stderr}</div>}
              {!execResult.stdout && !execResult.stderr && (
                <div style={{ color: '#94a3b8', fontStyle: 'italic' }}>(Process completed with no console output)</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
});

// ─── Cognitive Parser & Interactive Architecture Components ──────────────────
function parseCognitiveContent(rawContent) {
  if (typeof rawContent !== 'string') {
    return { meta: null, thought: null, body: rawContent, isThinking: false };
  }

  let text = rawContent;
  let meta = null;

  // 1. Extract metadata comment <!--AI-BS-METADATA:...-->
  const metaMatch = /<!--AI-BS-METADATA:([\s\S]*?)-->/.exec(text);
  if (metaMatch) {
    try {
      meta = JSON.parse(metaMatch[1]);
    } catch (e) {
      console.warn("Failed to parse AI-BS cognitive metadata", e);
    }
    text = text.replace(/<!--AI-BS-METADATA:[\s\S]*?-->/, '').trimStart();
  }

  // 2. Extract <think>...</think> block (complete or in-progress stream)
  let thought = null;
  let body = text;
  let isThinking = false;

  const completeThinkMatch = /<think>([\s\S]*?)<\/think>/.exec(text);
  if (completeThinkMatch) {
    thought = completeThinkMatch[1].trim();
    body = text.replace(/<think>[\s\S]*?<\/think>/, '').trim();
    isThinking = false;
  } else {
    const inProgressThinkMatch = /<think>([\s\S]*)$/.exec(text);
    if (inProgressThinkMatch) {
      thought = inProgressThinkMatch[1].trim();
      body = text.split('<think>')[0].trim();
      isThinking = true;
    }
  }

  return { meta, thought, body, isThinking };
}

function MobileCognitiveMetaHeader({ meta }) {
  const [showWhy, setShowWhy] = useState(false);
  const [showStepper, setShowStepper] = useState(false);

  if (!meta) return null;

  const t = meta.live_telemetry;
  const steps = meta.steps || [
    { id: 1, name: "Ingestion & Intent", status: "done", detail: "Intent Classified" },
    { id: 2, name: "Model Route", status: "done", detail: `${meta.display_name || meta.model}` },
    { id: 3, name: "Memory Vault", status: "done", detail: "Vault Verified" },
    { id: 4, name: "Reasoning Trace (Point A ➔ ∞)", status: "done", detail: "CoT Synthesized" },
    { id: 5, name: "Token Generation", status: "done", detail: "NVML Streaming" },
    { id: 6, name: "Sandbox Ready", status: "done", detail: "Host Verified" }
  ];

  return (
    <div style={{ marginBottom: '8px', fontSize: '0.74rem' }}>
      {/* Attribution & Inspector Pill Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '6px' }}>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          background: 'rgba(96, 165, 250, 0.12)',
          color: '#93c5fd',
          border: '1px solid rgba(96, 165, 250, 0.25)',
          padding: '2px 8px',
          borderRadius: '12px',
          fontWeight: 600
        }}>
          🤖 {meta.display_name || meta.model}
        </span>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          background: 'rgba(52, 211, 153, 0.12)',
          color: '#6ee7b7',
          border: '1px solid rgba(52, 211, 153, 0.25)',
          padding: '2px 8px',
          borderRadius: '12px',
          fontWeight: 500
        }}>
          ⚡ {meta.device || 'RTX 4090'}
        </span>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          background: 'rgba(168, 85, 247, 0.15)',
          color: '#d8b4fe',
          border: '1px solid rgba(168, 85, 247, 0.3)',
          padding: '2px 8px',
          borderRadius: '12px',
          fontWeight: 600
        }}>
          ♾️ Point A ➔ ∞
        </span>
        <button
          onClick={() => setShowWhy(!showWhy)}
          style={{
            background: showWhy ? 'rgba(245, 158, 11, 0.2)' : 'rgba(255, 255, 255, 0.05)',
            color: showWhy ? '#fbbf24' : '#cbd5e1',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '12px',
            padding: '2px 8px',
            fontSize: '0.7rem',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            transition: 'all 0.15s ease'
          }}
        >
          <span>ℹ️ Why this LLM?</span>
        </button>
        <button
          onClick={() => setShowStepper(!showStepper)}
          style={{
            background: showStepper ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255, 255, 255, 0.05)',
            color: showStepper ? '#c084fc' : '#cbd5e1',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '12px',
            padding: '2px 8px',
            fontSize: '0.7rem',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            transition: 'all 0.15s ease'
          }}
        >
          <span>🪜 Pipeline ({steps.length}/{steps.length}) {showStepper ? '▲' : '▼'}</span>
        </button>
      </div>

      {/* Live Hardware Telemetry Strip */}
      {t && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          flexWrap: 'wrap',
          marginBottom: '6px',
          padding: '4px 8px',
          borderRadius: '8px',
          background: 'rgba(15, 23, 42, 0.8)',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          fontSize: '0.67rem',
          color: '#94a3b8'
        }}>
          <span style={{ color: '#38bdf8', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
            🗄️ VRAM: <strong style={{ color: '#f1f5f9' }}>{t.vram_used_gb != null ? `${t.vram_used_gb} / ${t.vram_total_gb || 24} GB` : 'Active'}</strong>
          </span>
          <span style={{ color: '#475569' }}>•</span>
          <span style={{ color: '#f59e0b', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
            🌡️ <strong style={{ color: '#f1f5f9' }}>{t.core_temp_c != null ? `${t.core_temp_c}°C` : '38°C'}</strong>
          </span>
          <span style={{ color: '#475569' }}>•</span>
          <span style={{ color: '#ef4444', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
            ⚡ <strong style={{ color: '#f1f5f9' }}>{t.power_usage_w != null ? `${t.power_usage_w}W` : '--'}</strong>
          </span>
          <span style={{ color: '#475569' }}>•</span>
          <span style={{ color: '#10b981', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
            📊 <strong style={{ color: '#f1f5f9' }}>{t.gpu_util_pct != null ? `${t.gpu_util_pct}% GPU` : '0%'}</strong>
          </span>
          {t.sys_ram_used_gb != null && (
            <>
              <span style={{ color: '#475569' }}>•</span>
              <span style={{ color: '#a78bfa', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                💾 <strong style={{ color: '#f1f5f9' }}>{t.sys_ram_used_gb} / {t.sys_ram_total_gb || 62} GB RAM</strong>
              </span>
            </>
          )}
        </div>
      )}

      {/* Why This Model Rationale Drawer */}
      {showWhy && (
        <div style={{
          background: '#0d1117',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          borderRadius: '8px',
          padding: '8px 12px',
          marginBottom: '8px',
          color: '#e2e8f0',
          lineHeight: '1.45',
          boxShadow: '0 4px 12px rgba(0,0,0,0.4)'
        }}>
          <div style={{ color: '#fbbf24', fontWeight: 600, marginBottom: '3px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>💡 Cognitive Model Routing & Execution Rationale:</span>
          </div>
          <div style={{ color: '#cbd5e1', fontSize: '0.72rem' }}>
            {meta.reason || 'Sovereign local inference with zero cloud dependency.'}
          </div>
          <div style={{ marginTop: '6px', fontSize: '0.68rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <span>Scope: <strong style={{ color: '#c084fc' }}>{meta.thinking_scope || 'Point A to Point Infinity (Full Exhaustive Chain-of-Thought)'}</strong></span>
              <span>Allocated Context: <strong style={{ color: '#93c5fd' }}>{meta.context_tokens ? `${meta.context_tokens.toLocaleString()} tokens` : 'Adaptive'}</strong></span>
              <span>VRAM Mode: <strong style={{ color: '#34d399' }}>Locked Hot in 24GB (keep_alive: -1)</strong></span>
            </div>
            {t && (
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', color: '#64748b', fontSize: '0.65rem', marginTop: '2px' }}>
                <span>Driver: <strong style={{ color: '#38bdf8' }}>Direct nvml.dll</strong></span>
                <span>Core Clock: <strong style={{ color: '#f1f5f9' }}>{t.core_clock_mhz || 2520} MHz</strong></span>
                <span>Fan: <strong style={{ color: '#f1f5f9' }}>{t.fan_speed_pct || 30}%</strong></span>
                <span>Timestamp: <strong style={{ color: '#cbd5e1' }}>{t.timestamp || 'Live'}</strong></span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Pipeline Stepper Drawer */}
      {showStepper && (
        <div style={{
          background: '#070a10',
          border: '1px solid rgba(168, 85, 247, 0.3)',
          borderRadius: '8px',
          padding: '8px 12px',
          marginBottom: '8px',
          color: '#cbd5e1',
          boxShadow: '0 4px 12px rgba(0,0,0,0.4)'
        }}>
          <div style={{ color: '#c084fc', fontWeight: 600, marginBottom: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>✦ Sovereign Execution Journey (Step-by-Step)</span>
            <span style={{ fontSize: '0.68rem', color: '#34d399' }}>✓ {steps.length} / {steps.length} Complete</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
            {steps.map(step => (
              <div key={step.id || step.name} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.71rem' }}>
                <span style={{ color: step.status === 'done' ? '#34d399' : step.status === 'active' ? '#60a5fa' : '#94a3b8' }}>
                  {step.status === 'done' ? '✓' : step.status === 'active' ? '⟳' : '○'}
                </span>
                <span style={{ fontWeight: 600, color: step.status === 'done' ? '#f1f5f9' : '#cbd5e1' }}>
                  {step.name}
                </span>
                {step.detail && (
                  <span style={{ color: '#94a3b8', fontSize: '0.68rem', marginLeft: 'auto' }}>
                    {step.detail}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MobileCognitiveThoughtDrawer({ thought, isThinking }) {
  const [isOpen, setIsOpen] = useState(isThinking);

  useEffect(() => {
    if (isThinking) {
      setIsOpen(true);
    }
  }, [isThinking]);

  if (!thought) return null;

  const wordCount = thought.split(/\s+/).filter(Boolean).length;

  return (
    <div style={{
      marginBottom: '10px',
      borderRadius: '8px',
      background: 'rgba(168, 85, 247, 0.05)',
      border: isThinking ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
      overflow: 'hidden',
      transition: 'all 0.2s ease'
    }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 10px',
          background: isThinking ? 'rgba(168, 85, 247, 0.12)' : 'rgba(255, 255, 255, 0.03)',
          border: 'none',
          color: isThinking ? '#d8b4fe' : '#94a3b8',
          fontSize: '0.72rem',
          fontWeight: 600,
          cursor: 'pointer',
          textAlign: 'left'
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span>{isThinking ? '✦ Exhaustive CoT Trace (Point A ➔ Point ∞)...' : '🧠 Complete Thought Process (Point A ➔ Point ∞)'}</span>
          <span style={{
            background: 'rgba(168, 85, 247, 0.2)',
            color: '#c084fc',
            padding: '1px 6px',
            borderRadius: '10px',
            fontSize: '0.65rem',
            fontWeight: 700
          }}>
            Point A ➔ ∞
          </span>
          {!isThinking && (
            <span style={{ color: '#64748b', fontWeight: 400, fontSize: '0.68rem' }}>
              ({wordCount} words)
            </span>
          )}
        </span>
        <span style={{ fontSize: '0.68rem', color: isThinking ? '#c084fc' : '#64748b' }}>
          {isOpen ? '▲ Collapse' : '▼ Expand'}
        </span>
      </button>

      {isOpen && (
        <div style={{
          padding: '8px 12px',
          fontSize: '0.74rem',
          color: '#cbd5e1',
          fontFamily: "'JetBrains Mono', Consolas, monospace",
          lineHeight: '1.5',
          whiteSpace: 'pre-wrap',
          maxHeight: '360px',
          overflowY: 'auto',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          background: '#080a0f'
        }}>
          <div style={{
            fontSize: '0.65rem',
            color: '#c084fc',
            marginBottom: '6px',
            borderBottom: '1px solid rgba(168, 85, 247, 0.15)',
            paddingBottom: '4px',
            display: 'flex',
            justifyContent: 'space-between',
            fontWeight: 700,
            letterSpacing: '0.5px'
          }}>
            <span>⚡ EXHAUSTIVE CHAIN-OF-THOUGHT · POINT A TO POINT INFINITY</span>
            <span style={{ color: isThinking ? '#38bdf8' : '#34d399' }}>
              {isThinking ? '● ACTIVE STREAM' : '✓ VERIFIED COMPLETE'}
            </span>
          </div>
          {thought}
        </div>
      )}
    </div>
  );
}

// ─── Markdown Content Renderer with Media Proxying ───────────────────────────
export function MobileFormattedContent({ content, role, onImageClick }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);

  // ReactMarkdown uses renderer functions as component types. Keep them stable
  // across telemetry/parent renders so previews retain their blob URL/playback.
  const markdownComponents = React.useMemo(() => ({
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const codeString = String(children).replace(/\n$/, '');
          const isMultiLine = codeString.includes('\n');

          if (!inline && (match || isMultiLine)) {
            return (
              <MobileCodeBlock
                language={match ? match[1] : ''}
                code={codeString}
                backendUrl={BACKEND_URL}
              />
            );
          }
          return (
            <code
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                color: '#93c5fd',
                padding: '2px 5px',
                borderRadius: '4px',
                fontSize: '0.82em',
                fontFamily: 'monospace'
              }}
              {...props}
            >
              {children}
            </code>
          );
        },
        img({ src, alt }) {
          return <AuthenticatedChatMedia src={src} backendUrl={BACKEND_URL} alt={alt} />;
        },
        table({ children }) {
          return (
            <div style={{ overflowX: 'auto', margin: '10px 0', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                {children}
              </table>
            </div>
          );
        },
        th({ children }) {
          return <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: '600', background: 'rgba(255,255,255,0.05)', color: '#93c5fd' }}>{children}</th>;
        },
        td({ children }) {
          return <td style={{ padding: '6px 10px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', color: '#e2e8f0' }}>{children}</td>;
        },
        p({ children }) {
          return <p style={{ margin: '6px 0', lineHeight: '1.55' }}>{children}</p>;
        },
        a({ href, children }) {
          if (typeof href === 'string' && (/\/api\/(?:comfy(?:ui)?\/(?:media|view)|music\/|audio\/|video\/|media\/)/.test(href) || /\/media\//.test(href))) {
            return <AuthenticatedChatMedia src={href} backendUrl={BACKEND_URL} linkOnly>{children}</AuthenticatedChatMedia>;
          }
          let finalHref = href;
          if (finalHref && finalHref.startsWith('/')) {
            finalHref = `${BACKEND_URL}${finalHref}`;
          }
          if (finalHref && (finalHref.startsWith('http://127.0.0.1') || finalHref.startsWith('http://localhost'))) {
            finalHref = finalHref.replace(/^http:\/\/(?:127\.0\.0\.1|localhost):(?:\d+)/, 'https://api.brettstehouwer.live');
          }
          return (
            <a href={finalHref} target="_blank" rel="noreferrer" style={{ color: '#60a5fa', textDecoration: 'underline' }}>
              {children}
            </a>
          );
        }
  }), [BACKEND_URL]);

  if (role === 'user') {
    return <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{content}</div>;
  }

  const { meta, thought, body, isThinking } = parseCognitiveContent(content);
  const hasRunToken = typeof body === 'string' && /\[Run\s+([^\]]+)\]/.test(body);
  const stagedPayloads = hasRunToken ? extractStagedPayloads(body) : null;

  const renderMarkdownBlock = (markdownText, key) => (
    <ReactMarkdown
      key={key}
      remarkPlugins={[remarkGfm]}
      components={markdownComponents}
    >
      {markdownText}
    </ReactMarkdown>
  );

  const renderMainBody = () => {
    if (hasRunToken) {
      const parts = body.split(/(\[Run\s+[^\]]+\])/g);
      return parts.map((part, idx) => {
        const runMatch = /\[Run\s+([^\]]+)\]/.exec(part);
        if (runMatch) {
          const label = runMatch[1] || 'Interactive Canvas';
          return (
            <TapToRunCanvas
              key={`canvas-${idx}`}
              label={label}
              stagedPayloads={stagedPayloads}
              backendUrl={BACKEND_URL}
            />
          );
        }
        if (!part || !part.trim()) return null;
        return renderMarkdownBlock(part, `md-${idx}`);
      });
    }

    if (body) {
      return renderMarkdownBlock(body, 'single-md');
    }

    if (isThinking) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#c084fc', fontSize: '0.78rem', fontStyle: 'italic', padding: '4px 0' }}>
          <span style={{ animation: 'spin 1.5s linear infinite' }}>✦</span> Formulating synthesized response...
        </div>
      );
    }

    return null;
  };

  return (
    <div style={{ wordBreak: 'break-word', fontSize: '0.92rem', lineHeight: '1.6' }}>
      {meta && <MobileCognitiveMetaHeader meta={meta} />}
      {thought && <MobileCognitiveThoughtDrawer thought={thought} isThinking={isThinking} />}
      {renderMainBody()}
    </div>
  );
}

// ─── Main MobileStehouwerChat Component ───────────────────────────────────────
export default function MobileStehouwerChat({ onSwitchToDesktop, currentUser, backendUrl }) {
  const storeBackendUrl = useAppStore(state => state.BACKEND_URL);
  const isMobileClient = typeof window !== 'undefined' && (
    /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ||
    window.location.protocol === 'capacitor:' ||
    window.location.protocol === 'https:' ||
    !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) ||
    (window.location.origin && window.location.origin.includes('localhost') && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent))
  );

  const rawUrl = backendUrl || storeBackendUrl;
  const BACKEND_URL = (isMobileClient && (!rawUrl || rawUrl.includes('127.0.0.1') || rawUrl.includes('localhost')))
    ? 'https://api.brettstehouwer.live'
    : (rawUrl || 'https://api.brettstehouwer.live');
  const storedChatMessages = useAppStore(state => state.chatMessages);
  const storedFooterInput = useAppStore(state => state.footerInput);
  const selectedModel = useAppStore(state => state.selectedModel) || 'stehouwer_llm';
  const setSelectedModel = useAppStore(state => state.setSelectedModel);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [actionSheetOpen, setActionSheetOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);

  const abortControllerRef = useRef(null);
  const conversationMemory = useConversationMemory(useAppStore, BACKEND_URL, () => abortControllerRef.current?.abort());
  const chatMessages = conversationMemory.viewReady ? storedChatMessages : [];
  const footerInput = conversationMemory.viewReady ? storedFooterInput : '';
  const setChatMessages = conversationMemory.setMessages;
  const setFooterInput = conversationMemory.setDraft;
  const [genStartTime, setGenStartTime] = useState(null);
  const [elapsedTime, setElapsedTime] = useState('0.0');

  useEffect(() => {
    if (!isLoading) {
      setGenStartTime(null);
      return;
    }
    const start = Date.now();
    setGenStartTime(start);
    const interval = setInterval(() => {
      setElapsedTime(((Date.now() - start) / 1000).toFixed(1));
    }, 100);
    return () => clearInterval(interval);
  }, [isLoading]);

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      try {
        abortControllerRef.current.abort();
      } catch (e) {}
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  };

  // God-Mode Telemetry Hook (Live Hardware NVML & Port 8080 Bridge)
  const [gpuTelemetry, setGpuTelemetry] = useState(null);
  useEffect(() => {
    const fetchTelemetry = async () => {
      const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
      const candidateBases = [
        BACKEND_URL,
        'https://api.brettstehouwer.live',
        !isHttps ? 'http://127.0.0.1:8080' : null,
        !isHttps ? 'http://localhost:8080' : null,
        !isHttps ? 'http://192.168.4.92:8080' : null
      ].filter(Boolean);

      let fetched = false;
      for (const base of candidateBases) {
        try {
          const res = await fetch(`${base}/api/v1/hardware/gpu/telemetry`, {
            headers: {  },
            signal: AbortSignal.timeout ? AbortSignal.timeout(2000) : undefined
          });
          if (res.ok) {
            const json = await res.json();
            const t = json.telemetry || json;
            setGpuTelemetry({
              is_active: t.gpu_util_pct > 0 || t.status_flag === 'OPTIMAL' || !!t.nvml_online,
              vram_used_mb: t.memory_used_mb ?? t.vram_used_mb ?? 0,
              gpu_power_w: Math.round(t.power_usage_w ?? t.gpu_power_w ?? 0),
              gpu_temp_c: t.core_temp_c ?? t.gpu_temp_c ?? 32,
              sys_ram_gb: t.ram_used_gb ?? t.sys_ram_gb ?? 0,
              payout_bridge: json.payout_bridge || null
            });
            fetched = true;
            break;
          }
        } catch (e) {}

        if (!fetched) {
          try {
            const res2 = await fetch(`${base}/api/system/health`, {
              signal: AbortSignal.timeout ? AbortSignal.timeout(2000) : undefined
            });
            if (res2.ok) {
              const h = await res2.json();
              setGpuTelemetry({
                is_active: h.status === 'healthy',
                vram_used_mb: h.gpu?.allocated_gb ? h.gpu.allocated_gb * 1024 : 3500,
                gpu_power_w: 38,
                gpu_temp_c: 32,
                sys_ram_gb: h.ram?.used_gb ?? 16.4,
                payout_bridge: null
              });
              fetched = true;
              break;
            }
          } catch (e2) {}
        }
      }

      if (!fetched) {
        try {
          const res = await fetch('/telemetry.json?t=' + Date.now());
          if (res.ok) {
            const data = await res.json();
            setGpuTelemetry(data);
          }
        } catch (err) {}
      }
    };
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 3000);
    return () => clearInterval(interval);
  }, [BACKEND_URL]);
  const [previewImage, setPreviewImage] = useState(null);
  const [attachments, setAttachments] = useState([]);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [copiedShareToast, setCopiedShareToast] = useState(false);
  const [dismissedIOSBanner, setDismissedIOSBanner] = useState(() => {
    try {
      return localStorage.getItem('aibs_dismiss_ios_banner') === 'true';
    } catch {
      return false;
    }
  });

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const recognitionRef = useRef(null);

  // Check if running on iOS inside Safari (not yet added to Home Screen)
  const isIOS = typeof window !== 'undefined' && /iPhone|iPad|iPod/i.test(navigator.userAgent);
  const isStandalone = typeof window !== 'undefined' && (
    window.navigator.standalone === true || 
    window.matchMedia('(display-mode: standalone)').matches
  );
  const showIOSPrompt = isIOS && !isStandalone && !dismissedIOSBanner;

  // Available models for picker
  const models = [
    { id: 'stehouwer_llm', name: 'Stehouwer LLM', tag: 'Hybrid Sovereign' },
    { id: 'deepseek-r1:14b', name: 'DeepSeek R1 (14B)', tag: 'Local GPU 4090' },
    { id: 'qwen2.5-coder:32b', name: 'Qwen 2.5 Coder', tag: 'Local GPU 4090' },
    { id: 'llama3.3:70b', name: 'Llama 3.3 (70B)', tag: 'Distributed' },
    { id: 'gpt-4o', name: 'GPT-4o Omniscient', tag: 'Cloud API' },
    { id: 'claude-3-7-sonnet', name: 'Claude 3.7 Sonnet', tag: 'Cloud API' }
  ];

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isLoading]);

  // Auto-adjust textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [footerInput]);

  // Text-To-Speech
  const speakText = (text) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const clean = text.replace(/[*_#`\[\]()]/g, ' ');
    const u = new SpeechSynthesisUtterance(clean);
    u.rate = 1.0;
    window.speechSynthesis.speak(u);
  };

  // Speech-To-Text
  const toggleListening = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Speech recognition is not supported on this browser/device.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = 'en-US';

    rec.onstart = () => setIsListening(true);
    rec.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setFooterInput(prev => (prev ? `${prev} ${transcript}` : transcript));
      setIsListening(false);
    };
    rec.onerror = (e) => {
      console.warn('Speech error:', e.error);
      setIsListening(false);
    };
    rec.onend = () => setIsListening(false);

    recognitionRef.current = rec;
    rec.start();
  };

  // File Upload Handler
  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setIsUploadingFile(true);
    const newAttachments = [];

    // Helper: read text/code file client-side via FileReader
    const readLocalFileAsText = (targetFile) => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result || '');
        reader.onerror = () => reject(reader.error || new Error('Failed to read file client-side'));
        reader.readAsText(targetFile);
      });
    };

    // Helper: read image file client-side as data URL
    const readLocalFileAsDataUrl = (targetFile) => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result || '');
        reader.onerror = () => reject(reader.error || new Error('Failed to read image client-side'));
        reader.readAsDataURL(targetFile);
      });
    };

    for (const file of files) {
      const ext = (file.name.includes('.') ? `.${file.name.split('.').pop().toLowerCase()}` : '').trim();
      const isImage = file.type?.startsWith('image/') || ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'].includes(ext);
      const isTextOrCode = file.type?.startsWith('text/') ||
        ['.txt', '.md', '.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.html', '.css', '.scss',
         '.c', '.cpp', '.h', '.hpp', '.rs', '.go', '.sql', '.sh', '.bat', '.ps1', '.yaml',
         '.yml', '.toml', '.xml', '.csv', '.tsv', '.env', '.log', '.diff', '.patch'].includes(ext);

      let uploadSucceeded = false;

      try {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch(`${BACKEND_URL}/api/chat/attach`, {
          method: 'POST',
          headers: {
            'X-Client-ID': 'stehouwer_publishing'
          },
          body: formData
        });

        const rawText = await res.text();
        let data = null;
        if (rawText && rawText.trim()) {
          try {
            data = JSON.parse(rawText);
          } catch {
            data = null;
          }
        }

        if (res.ok && data && data.status === 'success' && data.file) {
          newAttachments.push(data.file);
          uploadSucceeded = true;
        }
      } catch (err) {
        console.error('File upload failed:', err);
      }

      if (!uploadSucceeded) {
        if (isTextOrCode) {
          try {
            const rawContent = await readLocalFileAsText(file);
            const sanitized = (rawContent || '').replace(/\x00/g, '');
            newAttachments.push({
              name: file.name,
              size: file.size,
              ext: ext,
              is_image: false,
              path: '',
              content: sanitized
            });
          } catch (readErr) {
            console.error('Local file read failed:', readErr);
          }
        } else if (isImage) {
          try {
            const dataUrl = await readLocalFileAsDataUrl(file);
            newAttachments.push({
              name: file.name,
              size: file.size,
              ext: ext,
              is_image: true,
              path: '',
              content: `[IMAGE_ATTACHMENT:${file.name}]\n[Client-Staged Data URL: ${dataUrl.slice(0, 100)}...]`
            });
          } catch (readErr) {
            console.error('Local image read failed:', readErr);
          }
        }
      }
    }

    setAttachments(prev => [...prev, ...newAttachments]);
    setIsUploadingFile(false);
    setActionSheetOpen(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Share with Friend
  const handleShareWithFriend = () => {
    const shareData = {
      title: 'Stehouwer AI • Sovereign Intelligence Studio',
      text: 'Check out Stehouwer AI — local RTX 4090 neural models, ComfyUI image creation & full studio!',
      url: 'https://ai-bs-dashboard.web.app'
    };

    if (navigator.share) {
      navigator.share(shareData).catch(() => {});
    } else {
      if (navigator.clipboard) {
        navigator.clipboard.writeText('https://ai-bs-dashboard.web.app');
      }
      setCopiedShareToast(true);
      setTimeout(() => setCopiedShareToast(false), 3000);
    }
  };

  const [isSavingMemory, setIsSavingMemory] = useState(false);
  const [memoryToast, setMemoryToast] = useState('');

  // Archive conversation to SQLite; clear only after confirmation
  const memoryArchiveRef = useRef({ busy:false, pending:null });
  const handleSaveToMemoryAndClear = async () => {
    if (!conversationMemory.viewReady) return;
    if (memoryArchiveRef.current.busy) return;
    if (!useAppStore.getState().chatMessages?.length) {
      setMemoryToast('Chat is already empty');
      return;
    }
    if (isLoading) {
      setMemoryToast('Wait for the response to finish before archiving.');
      return;
    }
    setIsSavingMemory(true);
    setMemoryToast('Archiving conversation to the local SQLite vault...');
    try {
      const saved = await archiveChatAndClear({
        state:memoryArchiveRef.current, backendUrl:BACKEND_URL,
        getMessages:() => useAppStore.getState().chatMessages,
        setMessages:setChatMessages,
        isCurrentBackend:conversationMemory.isCurrent,
        beforeClear:conversationMemory.beforeClear,
        sessionTitle:'Mobile Chat Session', source:'mobile_chat_stehouwer',
      });
      setMemoryToast(saved.cleared ? 'Archived to SQLite & cleared.' : 'Archived snapshot; current chat kept.');
    } catch (err) {
      setMemoryToast('Archive not confirmed; chat kept. ' + err.message);
    } finally {
      setIsSavingMemory(false);
      setTimeout(() => setMemoryToast(''), 5000);
    }
  };

  // Message Send Logic
  const handleSendMessage = async (textToSend = null) => {
    if (!conversationMemory.viewReady) return;
    const rawText = textToSend !== null ? textToSend : footerInput.trim();
    if ((!rawText && attachments.length === 0) || isLoading) return;

    let formattedPrompt = rawText;
    let attachmentBadges = [];

    if (attachments.length > 0) {
      const attText = attachments.map(att => (
        `\n[ATTACHED FILE: ${att.name} (${(att.size/1024).toFixed(1)} KB)]\n\`\`\`${(att.ext || '').replace('.', '')}\n${att.content}\n\`\`\`\n`
      )).join('\n');
      formattedPrompt = `${attText}\n[USER PROMPT]:\n${rawText || 'Please review and analyze the attached files.'}`;
      attachmentBadges = attachments.map(att => ({ name: att.name, size: att.size, is_image: att.is_image }));
    }

    const userMsg = {
      role: 'user',
      content: formattedPrompt,
      displayContent: rawText || 'Attached Files Analysis',
      attachments: attachmentBadges
    };

    const currentList = useAppStore.getState().chatMessages || chatMessages;
    const updatedHistory = [...currentList, userMsg];
    setChatMessages(updatedHistory);

    setFooterInput('');
    setAttachments([]);
    setIsLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const reqHeaders = {
        'Content-Type': 'application/json',
        
        'X-Client-ID': 'stehouwer_mobile_sovereign'
      };

      let streamingSucceeded = false;

      // Candidate backends to probe in priority order
      const candidateBases = [
        'https://api.brettstehouwer.live',
        BACKEND_URL,
        'http://192.168.4.92:8080',
        'http://100.104.31.50:8080'
      ].filter((u, idx, arr) => u && arr.indexOf(u) === idx && (!isMobileClient || (!u.includes('127.0.0.1') && !u.includes('localhost') && !u.includes('192.168.'))));

      const pLower = (formattedPrompt || '').toLowerCase().trim();
      const isVisualOrMediaIntent = (
        pLower.startsWith('/imagine') || pLower.startsWith('/render') || pLower.startsWith('/image') ||
        pLower.startsWith('/draw') || pLower.startsWith('/paint') || pLower.startsWith('/generate') ||
        pLower.startsWith('t2i:') || pLower.startsWith('txt2img:') ||
        /\b(create|generate|make|render|draw|paint|sketch|produce|design)\b.*?\b(photo|photos|photograph|photographs|image|images|picture|pictures|pic|pics|drawing|drawings|painting|paintings|artwork|art|render|renders|video|videos|avatar|logo|banner)\b/i.test(pLower) ||
        /^(?:photo of|photograph of|picture of|image of|portrait of|painting of|render of|photorealistic|hyperrealistic|cinematic shot|macro shot)/i.test(pLower)
      );

      // Prefer streaming hybrid-chat if stehouwer_llm OR any visual/image creation request
      if (selectedModel === 'stehouwer_llm' || isVisualOrMediaIntent) {
        setChatMessages(prev => [
          ...prev,
          { role: 'assistant', content: '', model: isVisualOrMediaIntent ? 'Stehouwer Vision • ComfyUI' : 'Stehouwer LLM' }
        ]);

        let accumulated = '';
        const recentHistory = (updatedHistory || []).slice(-8).map(m => ({
          role: m.role,
          content: m.content || m.displayContent || ''
        }));
        for (const targetBase of candidateBases) {
          try {
            const streamRes = await fetch(`${targetBase}/api/v1/hybrid-chat/stream`, {
              method: 'POST',
              headers: reqHeaders,
              body: JSON.stringify({ prompt: formattedPrompt, messages: recentHistory, stream: true, enable_rag: true }),
              signal: controller.signal
            });

            if ([401, 403].includes(streamRes.status)) {
              const error = Object.assign(new Error(`AI-BS backend returned HTTP ${streamRes.status}. Sign in with an authorized administrator account.`), { chatAuthorizationFailure: true });
              throw error;
            }

            if (streamRes.ok && streamRes.body) {
              const reader = streamRes.body.getReader();
              const decoder = new TextDecoder();

              while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                accumulated += chunk;

                const displayAccumulated = accumulated.replace(/^[\u200B\s]+/, '');
                setChatMessages(prev => {
                  const arr = [...prev];
                  if (arr.length > 0 && arr[arr.length - 1].role === 'assistant') {
                    arr[arr.length - 1].content = displayAccumulated;
                    const metaMatch = /<!--AI-BS-METADATA:([\s\S]*?)-->/.exec(displayAccumulated);
                    if (metaMatch) {
                      try {
                        const parsedMeta = JSON.parse(metaMatch[1]);
                        if (parsedMeta.display_name) {
                          arr[arr.length - 1].model = parsedMeta.display_name;
                        }
                      } catch (e) {}
                    }
                  }
                  return arr;
                });
              }

              const finalTrimmed = accumulated.replace(/^[\u200B\s]+/, '').trim();
              if (finalTrimmed.length > 0) {
                streamingSucceeded = true;
                if (autoSpeak) speakText(finalTrimmed);
                break;
              }
            }
          } catch (streamErr) {
            if (streamErr && typeof streamErr === 'object' && 'chatAuthorizationFailure' in streamErr && streamErr.chatAuthorizationFailure) throw streamErr;
            if (streamErr.name === 'AbortError') {
              console.log('Stream generation aborted by user.');
              const partialTrimmed = accumulated.replace(/^[\u200B\s]+/, '').trim();
              if (partialTrimmed.length > 0) {
                streamingSucceeded = true;
              }
              break;
            }
            console.warn(`Streaming attempt on ${targetBase} failed:`, streamErr);
            const partialTrimmed = accumulated.replace(/^[\u200B\s]+/, '').trim();
            if (partialTrimmed.length > 0) {
              streamingSucceeded = true;
              break;
            }
          }
        }

        if (!streamingSucceeded) {
          setChatMessages(prev => {
            if (prev.length > 0 && prev[prev.length - 1].content === '') {
              return prev.slice(0, -1);
            }
            return prev;
          });
        }
      }

      if (!streamingSucceeded) {
        const payloadBody = JSON.stringify({
          messages: updatedHistory.map(m => ({ role: m.role, content: m.content })),
          model: selectedModel
        });

        const responseStartedAt = Date.now();
        const fallbackTimeout = isVisualOrMediaIntent ? 600000 : 300000;
        let res = null;
        candidateLoop: for (const targetBase of candidateBases) {
          for (const endpoint of ['/api/chat', '/v1/chat/completions']) {
            try {
              res = await fetch(`${targetBase}${endpoint}`, {
                method: 'POST', headers: reqHeaders, body: payloadBody, signal: controller.signal
              });
            } catch (error) {
              if (error && typeof error === 'object' && 'name' in error && error.name === 'AbortError') throw error;
              throw new Error('The chat request was not acknowledged. It may have reached the host; no automatic retry was sent. Your prompt is retained.');
            }
            if (res?.ok) break candidateLoop;
            if (!res || ![404, 405].includes(res.status)) {
              await readChatHttpResponse(res);
            }
          }
        }

        if (!res || !res.ok) {
          // Secondary fallback to Stehouwer LLM hybrid stream before giving up
          console.warn('Dedicated model endpoints unready. Falling back to Stehouwer sovereign stream...');
          for (const targetBase of candidateBases) {
            try {
              const fbRes = await fetch(`${targetBase}/api/v1/hybrid-chat/stream`, {
                method: 'POST',
                headers: reqHeaders,
                body: JSON.stringify({ prompt: formattedPrompt, stream: false }),
                signal: AbortSignal.timeout ? AbortSignal.timeout(fallbackTimeout) : undefined
              });
              if ([401, 403].includes(fbRes?.status)) {
                const error = Object.assign(new Error(`AI-BS backend returned HTTP ${fbRes.status}. Sign in with an authorized administrator account.`), { chatAuthorizationFailure: true });
                throw error;
              }
              if (fbRes && fbRes.ok) {
                const fbData = await readChatHttpResponse(fbRes);
                const fbText = chatResponseText(fbData);
                if (fbText.trim()) {
                  setChatMessages(prev => [
                    ...prev,
                    {
                      role: 'assistant',
                      content: fbText,
                      model: 'Stehouwer LLM (Fallback)',
                      execution_time_ms: typeof fbData.execution_time_ms === 'number' ? fbData.execution_time_ms : Date.now() - responseStartedAt
                    }
                  ]);
                  if (autoSpeak) speakText(fbText);
                  return;
                }
              }
            } catch (fbErr) {
              if (fbErr && typeof fbErr === 'object' && 'chatAuthorizationFailure' in fbErr && fbErr.chatAuthorizationFailure) throw fbErr;
              console.warn(`Secondary fallback attempt on ${targetBase} failed:`, fbErr);
            }
          }

          throw new Error(`Server returned HTTP ${res ? res.status : 'Connection Offline'}`);
        }

        const data = await readChatHttpResponse(res);
        const botResponse = chatResponseText(data);

        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: botResponse,
            model: data.model || selectedModel,
            execution_time_ms: typeof data.execution_time_ms === 'number' ? data.execution_time_ms : Date.now() - responseStartedAt
          }
        ]);

        if (autoSpeak) speakText(botResponse);
      }
    } catch (err) {
      // Keep the submitted prompt available without replacing newer text typed during the request.
      if (!(useAppStore.getState().footerInput || '').trim()) setFooterInput(rawText);
      setAttachments(prev => prev.length ? prev : attachments);
      setChatMessages(/** @param {typeof chatMessages} prev */ prev => prev.length && prev[prev.length - 1].role === 'assistant' && prev[prev.length - 1].content === '' ? prev.slice(0, -1) : prev);
      if (err.name === 'AbortError') {
        console.log('Stream generation aborted by user.');
      } else {
        console.error('Chat error:', err);
        setChatMessages(prev => [
          ...prev,
          { role: 'assistant', content: `❌ **Connection Notice:** ${err.message || 'Unable to reach backend'}` }
        ]);
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const rawName = currentUser ? (currentUser.displayName || currentUser.email.split('@')[0]) : 'Brett';
  const displayName = rawName.replace(/\s*\(.*?\)/g, '').trim().split(' ')[0] || 'Brett';

  const suggestionChips = [
    { title: '🧠 1M+ RAG Search', prompt: 'search rag for sovereign intelligence and cognitive architecture' },
    { title: '📑 1M Map-Reduce', prompt: 'summarize 1m file C:\\AI-BS\\workspace\\pasted_1m_buffer.txt' },
    { title: '🧹 Reclaim RAM', prompt: 'Run the Zombie Node Cleaner to sweep orphaned background processes and reclaim host DDR5 RAM.' },
    { title: '⚡ Check RTX 4090', prompt: 'Check RTX 4090 GPU status, VRAM telemetry, and ComfyUI Port 8189 connection.' },
    { title: '🎨 Create 8K Photo', prompt: 'Create a photorealistic 8k photograph of a futuristic cybernetic warrior in neon lighting' },
    { title: '🎬 Wan2.1 Video', prompt: 'Generate a cinematic 1080p Wan2.1 video of a hyper-speed flight through a cyberpunk matrix' }
  ];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      width: '100%',
      flex: 1,
      minHeight: 0,
      background: '#131314',
      color: '#e3e3e3',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      position: 'relative',
      overflow: 'hidden'
    }}>
      <ConversationMemoryStatus memory={conversationMemory} />
      <CodingPreparationPanel memory={conversationMemory} />
      {/* ── Hidden File Input ── */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={handleFileUpload}
      />

      {/* ── Top App Bar ── */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        background: '#131314',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        zIndex: 50,
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Menu Drawer Button */}
          <button
            onClick={() => setDrawerOpen(true)}
            style={{
              background: 'none',
              border: 'none',
              color: '#c4c7c5',
              padding: '6px',
              borderRadius: '50%',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Open Menu"
          >
            <Menu size={22} />
          </button>

          {/* Model Selector Dropdown Pill */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '18px',
                padding: '6px 12px',
                color: '#e3e3e3',
                fontSize: '0.88rem',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer'
              }}
            >
              <span>{models.find(m => m.id === selectedModel)?.name || 'Stehouwer LLM'}</span>
              <ChevronDown size={14} color="#9ca3af" />
            </button>

            {/* Dropdown Menu */}
            {modelDropdownOpen && (
              <div style={{
                position: 'absolute',
                top: '40px',
                left: '0',
                background: '#1e1f20',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '14px',
                padding: '6px',
                width: '240px',
                boxShadow: '0 12px 30px rgba(0,0,0,0.7)',
                zIndex: 100
              }}>
                <div style={{ padding: '6px 10px', fontSize: '0.72rem', color: '#9ca3af', fontWeight: '700', textTransform: 'uppercase' }}>
                  Select Neural Engine
                </div>
                {models.map(m => (
                  <div
                    key={m.id}
                    onClick={() => {
                      setSelectedModel(m.id);
                      setModelDropdownOpen(false);
                    }}
                    style={{
                      padding: '8px 10px',
                      borderRadius: '8px',
                      background: selectedModel === m.id ? 'rgba(66, 133, 244, 0.15)' : 'transparent',
                      color: selectedModel === m.id ? '#8ab4f8' : '#e3e3e3',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '0.82rem'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>{m.name}</div>
                      <div style={{ fontSize: '0.68rem', color: '#8e918f' }}>{m.tag}</div>
                    </div>
                    {selectedModel === m.id && <Check size={14} color="#8ab4f8" />}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Header Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Save to Memory & Clear Button */}
          <button
            onClick={handleSaveToMemoryAndClear}
            disabled={isSavingMemory || isLoading}
            style={{
              background: 'linear-gradient(135deg, rgba(147, 51, 234, 0.25), rgba(99, 102, 241, 0.25))',
              border: '1px solid rgba(168, 85, 247, 0.45)',
              color: '#c084fc',
              padding: '5px 9px',
              borderRadius: '14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.74rem',
              fontWeight: '700'
            }}
            title="Archive conversation to SQLite; clear only after confirmation"
          >
            <Sparkles size={13} color="#c084fc" />
            <span>{isSavingMemory ? 'Saving...' : 'Save & Clear'}</span>
          </button>

          {/* Share Button (Top) */}
          <button
            onClick={handleShareWithFriend}
            style={{
              background: 'none',
              border: 'none',
              color: '#c4c7c5',
              padding: '6px',
              borderRadius: '50%',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Share with Friend"
          >
            <Share2 size={20} />
          </button>

          {/* New Chat Button */}
          <button
            onClick={handleSaveToMemoryAndClear}
            style={{
              background: 'none',
              border: 'none',
              color: '#c4c7c5',
              padding: '6px',
              borderRadius: '50%',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="New Chat (Saves to Memory)"
          >
            <Plus size={22} />
          </button>

          {/* User Avatar */}
          <div 
            onClick={() => setDrawerOpen(true)}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #4285f4, #9b72cf)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '0.8rem',
              fontWeight: '700',
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(66, 133, 244, 0.4)'
            }}
          >
            {displayName.substring(0, 2).toUpperCase()}
          </div>
        </div>
      </header>

      {/* Memory Ingest Toast Notification */}
      {memoryToast && (
        <div style={{
          position: 'absolute',
          top: '64px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: '#1e1b4b',
          border: '1px solid #818cf8',
          color: '#e0e7ff',
          padding: '8px 16px',
          borderRadius: '20px',
          fontSize: '0.82rem',
          fontWeight: 600,
          boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          whiteSpace: 'nowrap'
        }}>
          {memoryToast}
        </div>
      )}

      {/* ── Main Chat Stream / Empty State ── */}
      <main style={{
        flex: 1,
        minHeight: 0,
        overflowY: 'auto',
        overflowX: 'hidden',
        padding: '12px 14px 6px',
        display: 'flex',
        flexDirection: 'column',
        WebkitOverflowScrolling: 'touch'
      }}>
        {/* iOS Install on Home Screen Helper Card (Safari iPhone only) */}
        {showIOSPrompt && (
          <div style={{
            background: 'linear-gradient(135deg, rgba(66, 133, 244, 0.12), rgba(155, 114, 207, 0.12))',
            border: '1px solid rgba(66, 133, 244, 0.35)',
            borderRadius: '16px',
            padding: '12px 14px',
            marginBottom: '16px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.3)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, fontSize: '0.86rem', color: '#8ab4f8' }}>
                <Smartphone size={16} />
                <span>Install on your iPhone Home Screen</span>
              </div>
              <button 
                onClick={() => {
                  setDismissedIOSBanner(true);
                  try { localStorage.setItem('aibs_dismiss_ios_banner', 'true'); } catch {}
                }} 
                style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '0.9rem' }}
              >
                ✕
              </button>
            </div>
            <p style={{ fontSize: '0.76rem', color: '#cbd5e1', margin: '0 0 8px 0', lineHeight: 1.45 }}>
              Launch Stehouwer AI in full-screen native mode without Safari browser bars:
            </p>
            <div style={{ fontSize: '0.74rem', color: '#93c5fd', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div>1. Tap the <strong>Share</strong> button <span style={{ background: 'rgba(255,255,255,0.12)', padding: '1px 6px', borderRadius: '4px' }}>[↑]</span> at the bottom of Safari</div>
              <div>2. Scroll down & tap <strong>Add to Home Screen</strong> <span style={{ background: 'rgba(255,255,255,0.12)', padding: '1px 6px', borderRadius: '4px' }}>[+]</span></div>
              <div>3. Tap <strong>Add</strong> in the top-right corner to finish</div>
            </div>
          </div>
        )}

        {chatMessages.length === 0 ? (
          /* Empty Welcome View */
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            alignItems: 'center',
            maxWidth: '520px',
            margin: '0 auto',
            textAlign: 'center',
            padding: '10px 10px 16px',
            width: '100%'
          }}>
            {/* God-Mode GPU Telemetry Banner */}
            <div style={{
              width: '100%',
              minHeight: '76px',
              contain: 'layout',
              marginBottom: '24px',
              padding: '12px 16px',
              background: 'rgba(20, 20, 20, 0.8)',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Monitor size={14} /> RTX 4090 Core
                </span>
                <span style={{ 
                  fontSize: '0.75rem', 
                  color: gpuTelemetry?.is_active ? '#34d399' : '#94a3b8',
                  background: gpuTelemetry?.is_active ? 'rgba(52, 211, 153, 0.1)' : 'transparent',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontWeight: '600'
                }}>
                  {gpuTelemetry?.is_active ? '● CONTAINER ACTIVE' : '○ IDLE QUEUE'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase' }}>VRAM</span>
                  <span style={{ fontSize: '0.9rem', color: '#e2e8f0', fontWeight: '600' }}>
                    {gpuTelemetry ? `${(gpuTelemetry.vram_used_mb / 1024).toFixed(1)} GB` : '--'}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase' }}>Power</span>
                  <span style={{ fontSize: '0.9rem', color: '#fbbf24', fontWeight: '600' }}>
                    {gpuTelemetry ? `${gpuTelemetry.gpu_power_w} W` : '--'}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase' }}>Temp</span>
                  <span style={{ fontSize: '0.9rem', color: '#ef4444', fontWeight: '600' }}>
                    {gpuTelemetry ? `${gpuTelemetry.gpu_temp_c}°C` : '--'}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase' }}>Sys RAM</span>
                  <span style={{ fontSize: '0.9rem', color: '#60a5fa', fontWeight: '600' }}>
                    {gpuTelemetry ? `${gpuTelemetry.sys_ram_gb.toFixed(1)} GB` : '--'}
                  </span>
                </div>
              </div>
              {gpuTelemetry?.payout_bridge && (
                <div style={{
                  borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                  paddingTop: '8px',
                  marginTop: '4px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '0.72rem'
                }}>
                  <span style={{ color: '#94a3b8' }}>
                    Clore: <strong style={{ color: '#38bdf8' }}>{gpuTelemetry.payout_bridge.clore_balance} CLORE</strong>
                  </span>
                  <button
                    onClick={() => {
                      if (navigator.clipboard) {
                        navigator.clipboard.writeText(gpuTelemetry.payout_bridge.treasury_wallet);
                        alert('AI-BS Treasury Address Copied!\n' + gpuTelemetry.payout_bridge.treasury_wallet);
                      }
                    }}
                    style={{
                      background: 'rgba(56, 189, 248, 0.15)',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                      color: '#38bdf8',
                      borderRadius: '8px',
                      padding: '3px 8px',
                      fontSize: '0.7rem',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    📋 Copy Hot Wallet
                  </button>
                </div>
              )}
            </div>

            {/* Suggestion Cards - Compressed 2x2 Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '12px',
              width: '100%'
            }}>
              {suggestionChips.map((chip, i) => (
                <div
                  key={i}
                  onClick={() => handleSendMessage(chip.prompt)}
                  style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '12px',
                    padding: '12px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    minHeight: '60px',
                    transition: 'transform 0.15s ease, opacity 0.15s ease, background-color 0.15s ease'
                  }}
                  onTouchStart={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'}
                  onTouchEnd={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'}
                >
                  <span style={{ fontSize: '0.8rem', fontWeight: '500', color: '#e3e3e3' }}>
                    {chip.title}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Chat Message Stream */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', width: '100%', maxWidth: '800px', margin: '0 auto' }}>
            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: msg.role === 'user' ? '88%' : '100%',
                  width: msg.role === 'user' ? 'auto' : '100%'
                }}
              >
                {/* User Message Bubble */}
                {msg.role === 'user' ? (
                  <div style={{
                    background: '#282a2c',
                    color: '#e3e3e3',
                    padding: '12px 16px',
                    borderRadius: '20px 20px 4px 20px',
                    fontSize: '0.94rem',
                    lineHeight: '1.5',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                    wordBreak: 'break-word'
                  }}>
                    {msg.attachments && msg.attachments.length > 0 && (
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
                        {msg.attachments.map((att, i) => (
                          <div key={i} style={{
                            fontSize: '0.7rem',
                            background: 'rgba(255,255,255,0.1)',
                            padding: '3px 8px',
                            borderRadius: '6px'
                          }}>
                            {att.is_image ? '🖼️' : '📎'} {att.name}
                          </div>
                        ))}
                      </div>
                    )}
                    <MobileFormattedContent content={msg.displayContent || msg.content} role="user" />
                  </div>
                ) : (
                  /* Assistant Message Layout */
                  <div style={{
                    display: 'flex',
                    gap: '12px',
                    alignItems: 'flex-start',
                    width: '100%'
                  }}>
                    <div style={{ marginTop: '2px', flexShrink: 0 }}>
                      <StehouwerStar size={20} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.75rem', color: '#8e918f', marginBottom: '4px', fontWeight: '500' }}>
                        {msg.model || 'Stehouwer LLM'}
                      </div>
                      <MobileFormattedContent 
                        content={msg.content} 
                        role="assistant" 
                        onImageClick={(src) => setPreviewImage(src)}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}

            {/* Loading / Generating Indicator */}
            {isLoading && (
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', alignSelf: 'flex-start' }}>
                <StehouwerStar size={20} />
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: '#8ab4f8',
                  fontSize: '0.85rem'
                }}>
                  <div style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: '#8ab4f8',
                    animation: 'pulse 1s infinite'
                  }} />
                  <span>
                    {chatMessages.length > 0 && chatMessages[chatMessages.length - 1]?.role === 'assistant' && chatMessages[chatMessages.length - 1]?.content
                      ? `Streaming... (${elapsedTime}s · RTX 4090)`
                      : `Thinking... (${elapsedTime}s)`}
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} style={{ height: '80px' }} />
          </div>
        )}
      </main>

      {/* ── Attached Files Preview Bar ── */}
      {attachments.length > 0 && (
        <div style={{
          padding: '8px 16px',
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          background: '#1e1f20',
          borderTop: '1px solid rgba(255,255,255,0.08)'
        }}>
          {attachments.map((att, index) => (
            <div key={index} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: '#282a2c',
              borderRadius: '12px',
              padding: '4px 10px',
              fontSize: '0.75rem',
              color: '#8ab4f8',
              flexShrink: 0
            }}>
              <span>{att.is_image ? '🖼️' : '📄'}</span>
              <span>{att.name}</span>
              <button
                onClick={() => setAttachments(prev => prev.filter((_, i) => i !== index))}
                style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── Floating Capsule Bottom Input Bar ── */}
      <footer style={{
        padding: '6px 12px',
        paddingBottom: 'calc(var(--mobile-bottom-nav-height, 60px) + max(8px, env(safe-area-inset-bottom)))',
        background: 'linear-gradient(180deg, transparent 0%, #131314 40%)',
        position: 'relative',
        zIndex: 40,
        flexShrink: 0
      }}>
        <div style={{
          maxWidth: '740px',
          margin: '0 auto',
          background: '#1e1f20',
          borderRadius: '28px',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          display: 'flex',
          alignItems: 'flex-end',
          padding: '6px 10px',
          gap: '8px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
        }}>
          {/* Action Sheet (+) Button */}
          <button
            onClick={() => setActionSheetOpen(!actionSheetOpen)}
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.08)',
              border: 'none',
              color: '#c4c7c5',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'background 0.2s'
            }}
            title="Tools & Attachments"
          >
            <Plus size={20} />
          </button>

          {/* Text Input Area */}
          <textarea
            ref={textareaRef}
            disabled={!conversationMemory.viewReady}
            value={footerInput}
            onChange={(e) => setFooterInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder="Ask Stehouwer..."
            rows={1}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#e3e3e3',
              fontSize: '0.94rem',
              padding: '8px 4px',
              fontFamily: 'inherit',
              lineHeight: '1.4',
              resize: 'none',
              maxHeight: '120px'
            }}
          />

          {/* Voice Input Mic Button */}
          <button
            onClick={toggleListening}
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              background: isListening ? '#ef4444' : 'transparent',
              border: 'none',
              color: isListening ? '#fff' : '#c4c7c5',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
            title="Speech-To-Text"
          >
            {isListening ? <MicOff size={18} /> : <Mic size={20} />}
          </button>

          {/* Send or Stop Button */}
          {isLoading ? (
            <button
              onClick={handleStopGeneration}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                background: '#ef4444',
                border: 'none',
                color: '#fff',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                boxShadow: '0 0 14px rgba(239, 68, 68, 0.45)',
                transition: 'all 0.2s ease'
              }}
              title="Stop Generation"
            >
              <Square size={15} fill="#ffffff" />
            </button>
          ) : (
            <button
              onClick={() => handleSendMessage()}
              disabled={!footerInput.trim() && attachments.length === 0}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                background: (footerInput.trim() || attachments.length > 0) ? '#4285f4' : 'transparent',
                border: 'none',
                color: (footerInput.trim() || attachments.length > 0) ? '#fff' : '#5f6368',
                cursor: (footerInput.trim() || attachments.length > 0) ? 'pointer' : 'default',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                transition: 'all 0.2s ease'
              }}
            >
              <ArrowUp size={20} />
            </button>
          )}
        </div>
      </footer>

      {/* ── Slide-Out Left Navigation Drawer ── */}
      {drawerOpen && (
        <div 
          onClick={() => setDrawerOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            zIndex: 1000,
            display: 'flex',
            backdropFilter: 'blur(4px)'
          }}
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '82%',
              maxWidth: '310px',
              height: '100%',
              background: '#1e1f20',
              borderRight: '1px solid rgba(255, 255, 255, 0.1)',
              display: 'flex',
              flexDirection: 'column',
              padding: '16px',
              boxSizing: 'border-box'
            }}
          >
            {/* Drawer Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <StehouwerStar size={24} />
                <div>
                  <div style={{ fontSize: '0.92rem', fontWeight: '700', color: '#e3e3e3' }}>Stehouwer AI</div>
                  <div style={{ fontSize: '0.68rem', color: '#8ab4f8' }}>v5.327.0 • Sovereign Mobile</div>
                </div>
              </div>
              <button 
                onClick={() => setDrawerOpen(false)}
                style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* New Chat Action */}
            <button
              onClick={() => {
                handleSaveToMemoryAndClear();
                setDrawerOpen(false);
              }}
              style={{
                width: '100%',
                background: 'linear-gradient(135deg, #4285f4, #1a73e8)',
                color: '#fff',
                border: 'none',
                borderRadius: '12px',
                padding: '12px 14px',
                fontSize: '0.88rem',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                marginBottom: '10px'
              }}
            >
              <Plus size={18} />
              <span>New Conversation</span>
            </button>

            {/* Share with Friend Button */}
            <button
              onClick={handleShareWithFriend}
              style={{
                width: '100%',
                background: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                color: '#34d399',
                borderRadius: '12px',
                padding: '11px 14px',
                fontSize: '0.82rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                marginBottom: '16px'
              }}
            >
              <Share2 size={16} />
              <span>{copiedShareToast ? '✓ Link Copied!' : 'Share App with Friend'}</span>
            </button>

            {/* Switch to Full Desktop IDE View */}
            <div style={{
              background: 'rgba(66, 133, 244, 0.1)',
              border: '1px solid rgba(66, 133, 244, 0.3)',
              borderRadius: '12px',
              padding: '12px',
              marginBottom: '20px'
            }}>
              <div style={{ fontSize: '0.78rem', fontWeight: '600', color: '#8ab4f8', marginBottom: '4px' }}>
                🖥️ Need Workstation Tabs?
              </div>
              <p style={{ fontSize: '0.72rem', color: '#9ca3af', margin: '0 0 8px 0', lineHeight: '1.4' }}>
                Switch to the full multi-panel IDE, 3D Unreal Viewport, Studio DAW, and Command Center.
              </p>
              <button
                onClick={() => {
                  setDrawerOpen(false);
                  if (onSwitchToDesktop) onSwitchToDesktop();
                }}
                style={{
                  width: '100%',
                  background: '#282a2c',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#e3e3e3',
                  borderRadius: '8px',
                  padding: '8px',
                  fontSize: '0.78rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <Monitor size={14} />
                <span>Switch to Desktop View</span>
              </button>
            </div>

            {/* Hardware Status */}
            <div style={{
              background: '#131314',
              borderRadius: '10px',
              padding: '10px 12px',
              fontSize: '0.74rem',
              color: '#9ca3af',
              marginBottom: '16px',
              border: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#34d399', fontWeight: '600', marginBottom: '4px' }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#34d399' }} />
                <span>RTX 4090 GPU Active</span>
              </div>
              <div>Port 8080 FastAPI • Port 8189 ComfyUI</div>
              <div style={{ color: '#60a5fa', marginTop: '4px' }}>Cloudflare Sovereign Tunnel OK</div>
            </div>

            {/* Quick Settings */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
              <div style={{ fontSize: '0.72rem', fontWeight: '700', color: '#8e918f', textTransform: 'uppercase', marginBottom: '8px' }}>
                Voice & Audio
              </div>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 0',
                borderBottom: '1px solid rgba(255,255,255,0.06)'
              }}>
                <span style={{ fontSize: '0.82rem', color: '#e3e3e3' }}>Auto-Readout (TTS)</span>
                <button
                  onClick={() => setAutoSpeak(!autoSpeak)}
                  style={{
                    background: autoSpeak ? '#4285f4' : '#282a2c',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '12px',
                    padding: '4px 10px',
                    fontSize: '0.72rem',
                    cursor: 'pointer'
                  }}
                >
                  {autoSpeak ? 'ON' : 'OFF'}
                </button>
              </div>
            </div>

            {/* User Profile Badge */}
            <div style={{
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              paddingTop: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #4285f4, #9b72cf)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: '0.85rem',
                fontWeight: '700'
              }}>
                {displayName.substring(0, 2).toUpperCase()}
              </div>
              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: '600', color: '#e3e3e3' }}>{displayName}</div>
                <div style={{ fontSize: '0.7rem', color: '#8e918f' }}>Master Administrator</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Action Sheet Modal (Bottom Popup for Tools & Media) ── */}
      {actionSheetOpen && (
        <div
          onClick={() => setActionSheetOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.6)',
            zIndex: 900,
            display: 'flex',
            alignItems: 'flex-end',
            backdropFilter: 'blur(4px)'
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              background: '#1e1f20',
              borderTop: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '24px 24px 0 0',
              padding: '20px 16px',
              paddingBottom: 'max(24px, env(safe-area-inset-bottom))',
              boxSizing: 'border-box'
            }}
          >
            <div style={{
              width: '36px',
              height: '4px',
              borderRadius: '2px',
              background: 'rgba(255, 255, 255, 0.2)',
              margin: '0 auto 16px auto'
            }} />

            <div style={{ fontSize: '0.9rem', fontWeight: '700', color: '#e3e3e3', marginBottom: '14px' }}>
              Create & Attach
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
              {/* Upload File */}
              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer'
                }}
              >
                <div style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '16px',
                  background: '#282a2c',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#8ab4f8'
                }}>
                  <Paperclip size={22} />
                </div>
                <span style={{ fontSize: '0.72rem', color: '#c4c7c5' }}>Attach</span>
              </div>

              {/* SDXL Image Generator */}
              <div
                onClick={() => {
                  setFooterInput('Create a photorealistic 8k image of ');
                  setActionSheetOpen(false);
                  textareaRef.current?.focus();
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer'
                }}
              >
                <div style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '16px',
                  background: '#282a2c',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#a78bfa'
                }}>
                  <Image size={22} />
                </div>
                <span style={{ fontSize: '0.72rem', color: '#c4c7c5' }}>Image</span>
              </div>

              {/* Wan2.1 Video Generator */}
              <div
                onClick={() => {
                  setFooterInput('Create a cinematic Wan2.1 video of ');
                  setActionSheetOpen(false);
                  textareaRef.current?.focus();
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer'
                }}
              >
                <div style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '16px',
                  background: '#282a2c',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#f472b6'
                }}>
                  <Sparkles size={22} />
                </div>
                <span style={{ fontSize: '0.72rem', color: '#c4c7c5' }}>Video</span>
              </div>

              {/* 1M+ RAG Search Action */}
              <div
                onClick={() => {
                  handleSendMessage('search rag for key system parameters and memory');
                  setActionSheetOpen(false);
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer'
                }}
              >
                <div style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '16px',
                  background: '#282a2c',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#60a5fa'
                }}>
                  <Sparkles size={22} />
                </div>
                <span style={{ fontSize: '0.72rem', color: '#c4c7c5' }}>1M+ RAG</span>
              </div>

              {/* Zombie Node RAM Sweep */}
              <div
                onClick={() => {
                  handleSendMessage('Run the Zombie Node Cleaner to sweep orphaned background processes and reclaim host DDR5 RAM.');
                  setActionSheetOpen(false);
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer'
                }}
              >
                <div style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '16px',
                  background: '#282a2c',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fbbf24'
                }}>
                  <Cpu size={22} />
                </div>
                <span style={{ fontSize: '0.72rem', color: '#c4c7c5' }}>Sweep RAM</span>
              </div>

              {/* Hardware GPU Check */}
              <div
                onClick={() => {
                  handleSendMessage('Check local RTX 4090 GPU status, temperature, VRAM usage, and active models.');
                  setActionSheetOpen(false);
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer'
                }}
              >
                <div style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '16px',
                  background: '#282a2c',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#34d399'
                }}>
                  <Cpu size={22} />
                </div>
                <span style={{ fontSize: '0.72rem', color: '#c4c7c5' }}>GPU Info</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── High-Res Image Preview Modal ── */}
      {previewImage && (
        <div
          onClick={() => setPreviewImage(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.92)',
            zIndex: 2000,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '20px'
          }}
        >
          <div style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            display: 'flex',
            gap: '12px'
          }}>
            <a
              href={previewImage}
              download="ai-bs-render.png"
              target="_blank"
              rel="noreferrer"
              style={{
                background: '#282a2c',
                color: '#fff',
                padding: '8px 12px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Download size={14} />
              <span>Save HD</span>
            </a>
            <button
              onClick={() => setPreviewImage(null)}
              style={{
                background: '#282a2c',
                border: 'none',
                color: '#fff',
                borderRadius: '8px',
                padding: '8px 12px',
                cursor: 'pointer'
              }}
            >
              <X size={16} />
            </button>
          </div>
          <img
            src={previewImage?.startsWith('http') || previewImage?.startsWith('data:') || previewImage?.startsWith('blob:') ? previewImage : `${BACKEND_URL}${previewImage?.startsWith('/') ? '' : '/'}${previewImage}`}
            alt="Enlarged render"
            style={{
              maxWidth: '100%',
              maxHeight: '85vh',
              objectFit: 'contain',
              borderRadius: '12px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.8)'
            }}
          />
        </div>
      )}
    </div>
  );
}

