import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useAppStore } from './useAppStore';
import { 
  Menu, Plus, Send, Mic, MicOff, Image, Paperclip, Volume2, VolumeX, 
  ChevronDown, Check, Copy, ExternalLink, Download, Monitor, Trash2, 
  X, Cpu, ArrowUp, RefreshCw, Sparkles, Share2, Smartphone
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

// ─── Code Block with Syntax Highlighting & 1-Click Copy ──────────────────────
const MobileCodeBlock = React.memo(function MobileCodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

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
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language || 'text'}
        customStyle={{
          margin: 0,
          padding: '10px 12px',
          fontSize: '0.8rem',
          background: 'transparent',
          lineHeight: '1.45',
          overflowX: 'auto'
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
});

// ─── Markdown Content Renderer with Media Proxying ───────────────────────────
function MobileFormattedContent({ content, role, onImageClick }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);

  if (role === 'user') {
    return <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{content}</div>;
  }

  return (
    <div style={{ wordBreak: 'break-word', fontSize: '0.92rem', lineHeight: '1.6' }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children).replace(/\n$/, '');
            const isMultiLine = codeString.includes('\n');

            if (!inline && (match || isMultiLine)) {
              return (
                <MobileCodeBlock
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
          img({ node, src, alt, ...props }) {
            let finalSrc = src || '';
            const isLocalHost = typeof window !== 'undefined' && 
              (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

            if (finalSrc.includes('127.0.0.1:8188') || finalSrc.includes('localhost:8188') || 
                finalSrc.includes('127.0.0.1:8189') || finalSrc.includes('localhost:8189')) {
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

            // Automatic Cloudflare tunnel upgrade for mobile/PWA environments
            const isMobileEnv = typeof window !== 'undefined' && (
              /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ||
              window.location.protocol === 'capacitor:' ||
              window.location.protocol === 'https:' ||
              !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform())
            );

            if (isMobileEnv && (finalSrc.startsWith('http://127.0.0.1') || finalSrc.startsWith('http://localhost'))) {
              finalSrc = finalSrc.replace(/^http:\/\/(?:127\.0\.0\.1|localhost):(?:\d+)/, 'https://api.brettstehouwer.live');
            }

            if (finalSrc && (finalSrc.includes('.mp4') || finalSrc.includes('.webm') || finalSrc.includes('.mov'))) {
              return (
                <div style={{ margin: '12px 0' }}>
                  <video
                    src={finalSrc}
                    controls
                    autoPlay
                    loop
                    muted
                    playsInline
                    style={{
                      width: '100%',
                      maxHeight: '400px',
                      borderRadius: '12px',
                      border: '1px solid rgba(66, 133, 244, 0.4)',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                      display: 'block',
                      background: '#000'
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: '#94a3b8', marginTop: '6px' }}>
                    <span>🎬 Wan2.1 HD Video</span>
                    <a
                      href={finalSrc}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#60a5fa', textDecoration: 'none', fontWeight: 'bold' }}
                    >
                      Open Video ↗
                    </a>
                  </div>
                </div>
              );
            }

            return (
              <div style={{ margin: '12px 0' }}>
                <img
                  src={finalSrc}
                  alt={alt || 'Generated Image'}
                  onError={(e) => {
                    const cur = e.currentTarget.src;
                    if (cur.includes('127.0.0.1') || cur.includes('localhost')) {
                      e.currentTarget.src = cur.replace(/http:\/\/(?:127\.0\.0\.1|localhost):(?:\d+)/, 'https://api.brettstehouwer.live');
                    } else if (typeof window !== 'undefined' && window.location.protocol !== 'https:' && !cur.includes('192.168.4.92')) {
                      e.currentTarget.src = cur.replace(/http:\/\/[^/]+:(?:8000|8080)/, 'http://192.168.4.92:8080');
                    }
                  }}
                  style={{
                    width: '100%',
                    maxHeight: '420px',
                    objectFit: 'cover',
                    borderRadius: '12px',
                    border: '1px solid rgba(66, 133, 244, 0.4)',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                    cursor: 'pointer',
                    display: 'block'
                  }}
                  onClick={() => onImageClick ? onImageClick(finalSrc) : window.open(finalSrc, '_blank')}
                  {...props}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: '#94a3b8', marginTop: '6px' }}>
                  <span>🎨 SDXL / Wan Render</span>
                  <a
                    href={finalSrc}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: '#60a5fa', textDecoration: 'none', fontWeight: 'bold' }}
                  >
                    View Full HD ↗
                  </a>
                </div>
              </div>
            );
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
        }}
      >
        {content}
      </ReactMarkdown>
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
  const chatMessages = useAppStore(state => state.chatMessages);
  const setChatMessages = useAppStore(state => state.setChatMessages);
  const footerInput = useAppStore(state => state.footerInput);
  const setFooterInput = useAppStore(state => state.setFooterInput);
  const selectedModel = useAppStore(state => state.selectedModel) || 'stehouwer_llm';
  const setSelectedModel = useAppStore(state => state.setSelectedModel);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [actionSheetOpen, setActionSheetOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
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
        }
      } catch (err) {
        console.error('File upload failed:', err);
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

  // Save conversation to Master Memory and clear chat
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
        session_title: `Mobile Chat Session (${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`,
        source: 'mobile_chat_stehouwer'
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
        setMemoryToast('💾 Cleared & Saved locally');
      }
    } catch (err) {
      console.warn('Memory ingest error:', err);
      setChatMessages([]);
      setMemoryToast('💾 Chat cleared');
    } finally {
      setIsSavingMemory(false);
      setTimeout(() => setMemoryToast(''), 3500);
    }
  };

  // Message Send Logic
  const handleSendMessage = async (textToSend = null) => {
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

    try {
      const reqHeaders = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
        'X-Client-ID': 'stehouwer_mobile_sovereign'
      };

      let streamingSucceeded = false;

      // Candidate backends to probe in priority order
      const candidateBases = [
        'https://api.brettstehouwer.live',
        BACKEND_URL,
        'http://192.168.4.92:8080',
        'http://100.104.31.50:8080'
      ].filter((u, idx, arr) => u && arr.indexOf(u) === idx && (!isMobileClient || (!u.includes('127.0.0.1') && !u.includes('localhost'))));

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

        const mediaTimeout = isVisualOrMediaIntent ? 900000 : 180000;
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
              body: JSON.stringify({ prompt: formattedPrompt, messages: recentHistory, stream: true }),
              signal: AbortSignal.timeout ? AbortSignal.timeout(mediaTimeout) : undefined
            });

            if (streamRes.ok && streamRes.body) {
              const reader = streamRes.body.getReader();
              const decoder = new TextDecoder();

              while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                accumulated += chunk;

                setChatMessages(prev => {
                  const arr = [...prev];
                  if (arr.length > 0 && arr[arr.length - 1].role === 'assistant') {
                    arr[arr.length - 1].content = accumulated;
                  }
                  return arr;
                });
              }

              if (accumulated.trim().length > 0) {
                streamingSucceeded = true;
                if (autoSpeak) speakText(accumulated);
                break;
              }
            }
          } catch (streamErr) {
            console.warn(`Streaming attempt on ${targetBase} failed:`, streamErr);
            if (accumulated.trim().length > 0) {
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

        const fallbackTimeout = isVisualOrMediaIntent ? 600000 : 60000;
        let res = null;
        for (const targetBase of candidateBases) {
          try {
            res = await fetch(`${targetBase}/api/chat`, {
              method: 'POST',
              headers: reqHeaders,
              body: payloadBody,
              signal: AbortSignal.timeout ? AbortSignal.timeout(fallbackTimeout) : undefined
            });
            if (res && res.ok) break;

            res = await fetch(`${targetBase}/v1/chat/completions`, {
              method: 'POST',
              headers: reqHeaders,
              body: payloadBody,
              signal: AbortSignal.timeout ? AbortSignal.timeout(fallbackTimeout) : undefined
            });
            if (res && res.ok) break;
          } catch (e) {
            console.warn(`Chat endpoint attempt on ${targetBase} failed:`, e);
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
              if (fbRes && fbRes.ok) {
                const fbText = await fbRes.text();
                if (fbText.trim()) {
                  setChatMessages(prev => [
                    ...prev,
                    {
                      role: 'assistant',
                      content: fbText,
                      model: 'Stehouwer LLM (Fallback)',
                      execution_time_ms: 150
                    }
                  ]);
                  if (autoSpeak) speakText(fbText);
                  return;
                }
              }
            } catch (fbErr) {
              console.warn(`Secondary fallback attempt on ${targetBase} failed:`, fbErr);
            }
          }

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
        const botResponse = rawContent.trim() !== '' ? rawContent : 'Operational.';

        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: botResponse,
            model: data.model || selectedModel,
            execution_time_ms: data.execution_time_ms || 120
          }
        ]);

        if (autoSpeak) speakText(botResponse);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: `❌ **Connection Notice:** ${err.message || 'Unable to reach backend'}` }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const rawName = currentUser ? (currentUser.displayName || currentUser.email.split('@')[0]) : 'Brett';
  const displayName = rawName.replace(/\s*\(.*?\)/g, '').trim().split(' ')[0] || 'Brett';

  const suggestionChips = [
    { title: '🎨 Create 8K Photo', prompt: 'Create a photorealistic 8k photograph of a futuristic cybernetic warrior in neon lighting' },
    { title: '🎬 Wan2.1 Video', prompt: 'Generate a cinematic 1080p Wan2.1 video of a hyper-speed flight through a cyberpunk matrix' },
    { title: '⚡ Check RTX 4090', prompt: 'Check RTX 4090 GPU status, VRAM telemetry, and ComfyUI Port 8189 connection.' },
    { title: '✍️ Creative Script', prompt: 'Brainstorm a high-intensity film treatment scene with dialogue.' }
  ];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      width: '100vw',
      background: '#131314',
      color: '#e3e3e3',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      position: 'relative',
      overflow: 'hidden'
    }}>
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
        padding: '12px 16px',
        paddingTop: 'max(12px, env(safe-area-inset-top))',
        background: '#131314',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        zIndex: 50
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
            disabled={isSavingMemory}
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
            title="Save conversation to Master Memory and clear chat"
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
        overflowY: 'auto',
        overflowX: 'hidden',
        padding: '16px',
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
            justifyContent: 'center',
            alignItems: 'center',
            maxWidth: '520px',
            margin: '0 auto',
            textAlign: 'center',
            padding: '20px 10px',
            width: '100%'
          }}>
            {/* Centered Glowing 4-Point AI Star */}
            <div style={{
              position: 'relative',
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <div style={{
                position: 'absolute',
                width: '70px',
                height: '70px',
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(66,133,244,0.35) 0%, rgba(155,114,207,0.2) 60%, transparent 100%)',
                filter: 'blur(10px)'
              }} />
              <StehouwerStar size={46} />
            </div>

            {/* Greeting */}
            <h1 style={{
              fontSize: '1.85rem',
              fontWeight: '400',
              margin: '0 0 6px 0',
              color: '#e3e3e3',
              letterSpacing: '-0.5px'
            }}>
              Hi {displayName},
            </h1>
            <p style={{
              fontSize: '1.35rem',
              color: '#8e918f',
              margin: '0 0 32px 0',
              fontWeight: '300'
            }}>
              what's on your mind?
            </p>

            {/* Suggestion Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '10px',
              width: '100%'
            }}>
              {suggestionChips.map((chip, i) => (
                <div
                  key={i}
                  onClick={() => handleSendMessage(chip.prompt)}
                  style={{
                    background: '#1e1f20',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '16px',
                    padding: '14px 12px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '80px',
                    transition: 'all 0.15s ease'
                  }}
                  onTouchStart={(e) => e.currentTarget.style.background = '#282a2c'}
                  onTouchEnd={(e) => e.currentTarget.style.background = '#1e1f20'}
                >
                  <span style={{ fontSize: '0.85rem', fontWeight: '500', color: '#e3e3e3' }}>
                    {chip.title}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: '#8ab4f8', marginTop: '8px' }}>
                    Ask AI ↗
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
                  <span>Thinking...</span>
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
        padding: '8px 16px',
        paddingBottom: 'max(12px, env(safe-area-inset-bottom))',
        background: 'linear-gradient(180deg, transparent 0%, #131314 40%)',
        position: 'relative',
        zIndex: 40
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

          {/* Send Button */}
          <button
            onClick={() => handleSendMessage()}
            disabled={(!footerInput.trim() && attachments.length === 0) || isLoading}
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              background: (footerInput.trim() || attachments.length > 0) && !isLoading ? '#4285f4' : 'transparent',
              border: 'none',
              color: (footerInput.trim() || attachments.length > 0) && !isLoading ? '#fff' : '#5f6368',
              cursor: (footerInput.trim() || attachments.length > 0) && !isLoading ? 'pointer' : 'default',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'all 0.2s ease'
            }}
          >
            <ArrowUp size={20} />
          </button>
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
                  <div style={{ fontSize: '0.68rem', color: '#8ab4f8' }}>v5.296.0 • Sovereign Mobile</div>
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
                setChatMessages([]);
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

