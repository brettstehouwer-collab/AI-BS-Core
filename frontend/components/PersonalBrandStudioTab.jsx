import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Share2, Sparkles, Copy, Check, ExternalLink, Hash, AlertTriangle, 
  CheckCircle2, Layers, RefreshCw, MessageSquare, Zap, ShieldCheck, Flame,
  FileCode, Database, Terminal, Cpu, BookOpen, Film
} from 'lucide-react';
import { getApiBase } from '../config/api';

const PersonalBrandStudioTab = ({ backendUrl, selectedModel = 'stehouwer_llm' }) => {
  const apiBase = backendUrl || getApiBase() || 'http://127.0.0.1:8080';

  // Input State
  const [inputText, setInputText] = useState('');
  const [customUrl, setCustomUrl] = useState('');
  const [platform, setPlatform] = useState('facebook'); // 'facebook' | 'instagram' | 'linkedin' | 'x'
  
  // Format Selection: 'auto' | 'long' | 'short' | 'fire'
  const [formatMode, setFormatMode] = useState('auto');
  const [activeOutputTab, setActiveOutputTab] = useState('long'); // 'long' | 'short' | 'fire'

  // Processing & Results State
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  const [resultData, setResultData] = useState(null);

  // Clipboard Feedback State
  const [copiedKey, setCopiedKey] = useState(null);

  const handleCopy = (text, key) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2200);
  };

  const handleOptimize = async () => {
    if (!inputText.trim()) {
      setError('Please provide post text, thoughts, or an excerpt to analyze.');
      return;
    }

    setIsGenerating(true);
    setError('');
    setResultData(null);

    const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
    const isLocal = typeof window !== 'undefined' && (
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1'
    );

    const candidateBases = [];
    if (backendUrl) candidateBases.push(backendUrl);
    if (getApiBase()) candidateBases.push(getApiBase());
    if (isHttps) {
      candidateBases.push('https://api.brettstehouwer.live');
      candidateBases.push('https://ai-bs.brettstehouwer.live');
    }
    if (isLocal || !isHttps) {
      candidateBases.push('http://127.0.0.1:8000');
      candidateBases.push('http://127.0.0.1:8080');
      candidateBases.push('');
    }
    const uniqueBases = Array.from(new Set(candidateBases));

    let lastError = null;
    let successData = null;

    for (const base of uniqueBases) {
      try {
        const url = base ? `${base}/api/social/optimize` : '/api/social/optimize';
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Client-ID': 'stehouwer_publishing'
          },
          body: JSON.stringify({
            text: inputText,
            custom_url: customUrl.trim() || undefined,
            target_platform: platform,
            fire_writing_mode: formatMode === 'fire'
          }),
          signal: AbortSignal.timeout(8000)
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        if (data && (data.status === 'success' || data.topic)) {
          successData = data;
          break;
        } else {
          throw new Error(data?.detail || 'Invalid response');
        }
      } catch (err) {
        lastError = err;
        console.warn(`[SocialOptimizer] Candidate ${base} failed:`, err);
      }
    }

    if (successData) {
      setResultData(successData);
      if (formatMode === 'short') {
        setActiveOutputTab('short');
      } else if (formatMode === 'long') {
        setActiveOutputTab('long');
      } else if (formatMode === 'fire') {
        setActiveOutputTab('fire');
      } else {
        setActiveOutputTab(inputText.length < 220 ? 'short' : 'long');
      }
    } else {
      setError(lastError ? `Connection failed: ${lastError.message}. Ensure the backend daemon is running.` : 'Could not connect to Social Optimizer Engine.');
    }
    setIsGenerating(false);
  };

  // Preset 1: Creative / Film & Friend Appreciation (Anna Stadler IMDb)
  const loadFilmStageSample = () => {
    setInputText(`No matter the role.
Always, Bad-Ass'. Support my 🎸☕️🎬
Click the link below.
Thank you for always finding time. 16 hour days on set or 20 hour days stage+ memorizing lines.
You always find the time to catch up. Please never give up being the beautiful lady you are.
Always stay true to you. If you forgot, being you, is the best part of you, the you, that was kind to me, became someone special, a friend to me.`);
    setCustomUrl('https://www.imdb.com/name/nm11231767/?ref_=nv_sr_srsg_0_tt_0_nm_8_in_0_q_anna%20stadler');
  };

  // Preset 2: Personal Memoir & Resilience (Authenticity & C-PTSD)
  const loadBookMemoirSample = () => {
    setInputText(`Are you, or have you ever had a moment where you wonder why I stand out in a cringe way, or a little over the top goofy, or over passionate about things I post at times?

Or when you do meet me, then you see what many people have said: "different in person."

Well, quick response:
I am the person who you see posted. I am that person.

I'm a very introverted dude who also can come across quiet, or talk way more than expected.
I often show the professional side of me on first interactions.
Then I'll go into observation mode for a period of time.
Then, when my hyper vigilance goes away and the sense of hyper awareness dissolves a bit, I'm able to breathe deep and relax the distraction from trauma...

I'm finally at the point where I thrive and become extremely good at anything I do.

Now that the C-PTSD subconscious mind begin telling my concise mind that everything is okay, and I can continue forward, and finally get to business / open up / be what seems a bit normal...
Then the side that you see will come out more: the side of me that posts awkward and sometimes cringe strange videos.

But it takes a long time to get to that point.
Just be patient with me, because I am genuine.
I tell the truth.

Even a little lie—whether it's just telling someone it's 6 and when it's 5:54 am—for whatever reason, my brain latches onto and bugs me and eats at me.
This is why I'm the first to let anyone know when I screw up, because that hangs on me when I know the moral ethical value I have to first be honest with myself.
And I can't be honest with myself if I let myself be dishonest and say something that's not true.

That's why I tend to consciously be truthful and to the point in any conversation.

Will my mind pause and get stuck in a loop from past traumas over certain words, or other actions, or objects as simple as a spoon, or wire, or a door shutting?
Yes to all.

Yet I am aware, and I accept it.
This at times may be confusing or misunderstood externally, yet even that thought could invertedly be in my mind.

So this is where I say: if you want to understand more, read my book and learn about how I came this far and still have a long road ahead of me.

On the positive:
I am here no matter what.
I will make Adam proud. As well as Tyler Patrick.`);
    setCustomUrl('https://stehouwer-publishing.com/library');
  };

  // Preset 3: Sovereign Tech & Software Engineering (RTX 4090 / Local LLMs)
  const loadTechSoftwareSample = () => {
    setInputText(`Scaling local LLM architectures on consumer silicon.
Running 100% sovereign inference with RTX 4090 24GB VRAM and Ryzen 9 9950X on Windows 11 with WSL2 daemons.
Zero vendor lock-in. Zero cloud dependency. High throughput token streaming with quantized models.
Building sovereign operating infrastructure from the ground up.`);
    setCustomUrl('https://github.com/example/sovereign-ai');
  };

  const getFullPostWithBuffer = () => {
    if (!resultData) return '';
    const body = activeOutputTab === 'long' 
      ? resultData.posts.long_form 
      : activeOutputTab === 'short' 
        ? resultData.posts.short_form 
        : (resultData.posts.fire_writing || resultData.fire_writing?.social_post || '');
    
    const tags = `${resultData.hashtag_boxes.box1.tag_string} ${resultData.hashtag_boxes.box2.tag_string}`;
    return `${body}\n\n.\n.\n.\n\n${tags}`;
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
      height: '100%',
      padding: '24px',
      color: '#c9d1d9',
      boxSizing: 'border-box',
      overflowY: 'auto'
    }}>
      {/* Header Deck */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        background: 'linear-gradient(135deg, rgba(22,27,34,0.7) 0%, rgba(13,17,23,0.9) 100%)',
        border: '1px solid rgba(56,189,248,0.2)',
        borderRadius: '12px',
        padding: '18px 24px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.35)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1 style={{ margin: 0, fontSize: '1.45rem', fontWeight: 800, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Flame size={24} color="#38bdf8" />
              Personal Brand Studio & Social Outreach Optimizer
            </h1>
            <span style={{
              background: 'rgba(56,189,248,0.15)',
              border: '1px solid #38bdf8',
              color: '#38bdf8',
              fontSize: '0.72rem',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: '6px'
            }}>
              v5.296.0 ACTIVE
            </span>
          </div>
          <p style={{ margin: '6px 0 0 0', color: '#94a3b8', fontSize: '0.88rem' }}>
            Context-driven Facebook generator (Long Narrative vs Short Hook vs Fire Writing) with intelligent topic detection, 3-tier mixed hashtag matrices, and zero-penalty comment-drop URL architecture.
          </p>
        </div>

        {/* 3 Diverse Sample Loaders */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={loadFilmStageSample}
            title="Load Anna Stadler IMDb Acting / Shoutout Sample"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(56,189,248,0.12)',
              border: '1px solid rgba(56,189,248,0.35)',
              color: '#38bdf8',
              padding: '8px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: 600
            }}
          >
            <Film size={13} color="#38bdf8" />
            1: Film & Friend
          </button>
          <button
            onClick={loadBookMemoirSample}
            title="Load C-PTSD & Personal Resilience Book Excerpt"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.15)',
              color: '#e2e8f0',
              padding: '8px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: 600
            }}
          >
            <BookOpen size={13} color="#f59e0b" />
            2: Memoir & Resilience
          </button>
          <button
            onClick={loadTechSoftwareSample}
            title="Load RTX 4090 / Local LLM Software Engineering Sample"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(16,185,129,0.1)',
              border: '1px solid rgba(16,185,129,0.3)',
              color: '#34d399',
              padding: '8px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: 600
            }}
          >
            <Cpu size={13} color="#10b981" />
            3: Sovereign Tech
          </button>
        </div>
      </div>

      {/* Main Workspace: 2-Column Split */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(380px, 1fr) minmax(420px, 1.25fr)', gap: '20px', flex: 1, minHeight: 0 }}>
        
        {/* Left Column: Input, Parameters & Controls */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          background: 'rgba(15,23,42,0.6)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '12px',
          padding: '20px'
        }}>
          {/* Format Mode Selector */}
          <div>
            <label style={{ fontSize: '0.82rem', color: '#94a3b8', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
              Formatting Strategy:
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1.2fr', gap: '8px' }}>
              {[
                { key: 'auto', label: '⚡ Auto-Detect' },
                { key: 'long', label: '📖 Long Story' },
                { key: 'short', label: '🎯 Short Punch' },
                { key: 'fire', label: '🔥 Fire Writing' }
              ].map(mode => (
                <button
                  key={mode.key}
                  onClick={() => setFormatMode(mode.key)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: formatMode === mode.key ? '#0284c7' : 'rgba(255,255,255,0.05)',
                    border: formatMode === mode.key ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                    color: formatMode === mode.key ? '#ffffff' : '#94a3b8',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {mode.label}
                </button>
              ))}
            </div>
            {formatMode === 'fire' && (
              <span style={{ fontSize: '0.74rem', color: '#f59e0b', marginTop: '6px', display: 'block', fontWeight: 600 }}>
                🛡️ Fidelitas Mandate Active: Zero word substitutions or vocabulary smoothing.
              </span>
            )}
          </div>

          {/* Raw Text Input */}
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
            <label style={{ fontSize: '0.82rem', color: '#94a3b8', fontWeight: 600, marginBottom: '6px' }}>
              Source Thought, Brain Dump, Fire Writing or Excerpt:
            </label>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste raw text, book excerpts, voice notes, or unfiltered cognitive stream here..."
              style={{
                flex: 1,
                minHeight: '220px',
                background: 'rgba(2,6,23,0.7)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                padding: '14px',
                color: '#f8fafc',
                fontSize: '0.88rem',
                lineHeight: '1.5',
                resize: 'vertical',
                outline: 'none',
                fontFamily: 'inherit'
              }}
            />
          </div>

          {/* Comment Drop URL Field */}
          <div>
            <label style={{ fontSize: '0.82rem', color: '#94a3b8', fontWeight: 600, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ExternalLink size={14} color="#38bdf8" />
              Target Outbound URL (Protected Comment Drop):
            </label>
            <input
              type="text"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              placeholder="e.g. https://www.imdb.com/name/nm... or https://github.com/..."
              style={{
                width: '100%',
                background: 'rgba(2,6,23,0.7)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '6px',
                padding: '10px 12px',
                color: '#f8fafc',
                fontSize: '0.86rem',
                boxSizing: 'border-box',
                outline: 'none'
              }}
            />
            <span style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '4px', display: 'block' }}>
              🛡️ Stripped from body automatically to prevent Meta algorithm reach throttling.
            </span>
          </div>

          {/* Action Button */}
          <button
            onClick={handleOptimize}
            disabled={isGenerating}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '12px 18px',
              background: isGenerating ? '#0369a1' : 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
              color: '#ffffff',
              border: '1px solid #38bdf8',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '0.95rem',
              cursor: isGenerating ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 14px rgba(2,132,199,0.35)',
              transition: 'all 0.15s ease'
            }}
          >
            {isGenerating ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                Analyzing Topic & Optimizing...
              </>
            ) : (
              <>
                <Zap size={16} />
                Generate Optimized Facebook Post & Tag Mix
              </>
            )}
          </button>
          {error && <div style={{ color: '#ef4444', fontSize: '0.85rem' }}>{error}</div>}
        </div>

        {/* Right Column: Output & Optimization Suite */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          background: 'rgba(15,23,42,0.6)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '12px',
          padding: '20px',
          minHeight: '520px'
        }}>
          {resultData ? (
            <>
              {/* Output Sub-Tabs (Long vs Short vs Fire Writing) */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => setActiveOutputTab('long')}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '0.82rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      background: activeOutputTab === 'long' ? 'rgba(56,189,248,0.2)' : 'transparent',
                      border: activeOutputTab === 'long' ? '1px solid #38bdf8' : '1px solid transparent',
                      color: activeOutputTab === 'long' ? '#38bdf8' : '#94a3b8'
                    }}
                  >
                    📖 Long-Form Narrative
                  </button>
                  <button
                    onClick={() => setActiveOutputTab('short')}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '0.82rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      background: activeOutputTab === 'short' ? 'rgba(56,189,248,0.2)' : 'transparent',
                      border: activeOutputTab === 'short' ? '1px solid #38bdf8' : '1px solid transparent',
                      color: activeOutputTab === 'short' ? '#38bdf8' : '#94a3b8'
                    }}
                  >
                    🎯 Short-Form Hook
                  </button>
                  <button
                    onClick={() => setActiveOutputTab('fire')}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '0.82rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      background: activeOutputTab === 'fire' ? 'rgba(245,158,11,0.2)' : 'transparent',
                      border: activeOutputTab === 'fire' ? '1px solid #f59e0b' : '1px solid transparent',
                      color: activeOutputTab === 'fire' ? '#f59e0b' : '#94a3b8'
                    }}
                  >
                    🔥 Fire Writing (Immutable)
                  </button>
                </div>

                <span style={{ fontSize: '0.78rem', color: '#10b981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <CheckCircle2 size={14} />
                  Topic: {resultData.topic}
                </span>
              </div>

              {/* Formatted Post Viewer */}
              <div style={{
                position: 'relative',
                background: 'rgba(2,6,23,0.85)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '8px',
                padding: '16px',
                flex: 1,
                overflowY: 'auto',
                fontSize: '0.9rem',
                lineHeight: '1.6',
                color: '#e2e8f0',
                whiteSpace: 'pre-wrap'
              }}>
                <div style={{ position: 'absolute', top: '12px', right: '12px', display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => handleCopy(
                      activeOutputTab === 'long' 
                        ? resultData.posts.long_form 
                        : activeOutputTab === 'short' 
                          ? resultData.posts.short_form 
                          : (resultData.posts.fire_writing || resultData.fire_writing?.social_post || ''),
                      'post_body'
                    )}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      background: copiedKey === 'post_body' ? '#10b981' : 'rgba(255,255,255,0.1)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      color: '#ffffff',
                      borderRadius: '6px',
                      fontSize: '0.76rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    {copiedKey === 'post_body' ? <Check size={14} /> : <Copy size={14} />}
                    {copiedKey === 'post_body' ? 'Copied!' : 'Copy Text'}
                  </button>

                  <button
                    onClick={() => handleCopy(getFullPostWithBuffer(), 'full_buffered')}
                    title="Copy post body with triple period buffer (. \n . \n .) and hashtag block"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      background: copiedKey === 'full_buffered' ? '#10b981' : 'rgba(56,189,248,0.15)',
                      border: '1px solid rgba(56,189,248,0.3)',
                      color: '#38bdf8',
                      borderRadius: '6px',
                      fontSize: '0.76rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    {copiedKey === 'full_buffered' ? <Check size={14} /> : <Share2 size={14} />}
                    {copiedKey === 'full_buffered' ? 'Copied Full!' : 'Copy with . Buffers + Tags'}
                  </button>
                </div>

                {activeOutputTab === 'long' && resultData.posts.long_form}
                {activeOutputTab === 'short' && resultData.posts.short_form}
                {activeOutputTab === 'fire' && (resultData.posts.fire_writing || resultData.fire_writing?.social_post)}
              </div>

              {/* Fire Writing Bifurcation & Archival Block (When in Fire Mode or Available) */}
              {activeOutputTab === 'fire' && resultData.fire_writing && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {resultData.fire_writing.raw_source_payload && (
                    <div style={{
                      background: 'rgba(2,6,23,0.9)',
                      border: '1px solid rgba(245,158,11,0.25)',
                      borderRadius: '6px',
                      padding: '10px 14px'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <FileCode size={13} />
                          Bifurcation Protocol: Sequestered Raw Source Payload (&gt;400 chars)
                        </span>
                        <button
                          onClick={() => handleCopy(resultData.fire_writing.raw_source_payload, 'raw_code')}
                          style={{
                            background: copiedKey === 'raw_code' ? '#10b981' : 'rgba(255,255,255,0.08)',
                            border: 'none',
                            color: '#ffffff',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            fontSize: '0.7rem',
                            cursor: 'pointer'
                          }}
                        >
                          {copiedKey === 'raw_code' ? 'Copied' : 'Copy Code Block'}
                        </button>
                      </div>
                      <pre style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8', overflowX: 'auto', fontFamily: 'monospace' }}>
                        {resultData.fire_writing.raw_source_payload}
                      </pre>
                    </div>
                  )}

                  {/* Archival Block & Decoupled Scaffolding Metadata */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '10px',
                    fontSize: '0.76rem',
                    background: 'rgba(15,23,42,0.7)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '6px',
                    padding: '10px 14px'
                  }}>
                    <div>
                      <span style={{ fontWeight: 700, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <Database size={12} />
                        stehouwer_reality_archival_block:
                      </span>
                      <div style={{ color: '#cbd5e1', marginTop: '4px' }}>
                        Fidelity Score: <strong style={{ color: '#10b981' }}>1.0 (Zero Alterations)</strong><br />
                        Word Substitutions: <strong>0</strong> | Grammar Smoothing: <strong>False</strong><br />
                        Protocol: <strong>Fidelitas Mandate v1.0</strong>
                      </div>
                    </div>

                    <div>
                      <span style={{ fontWeight: 700, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <Layers size={12} />
                        Decoupled Analytical Scaffolding:
                      </span>
                      <div style={{ color: '#cbd5e1', marginTop: '4px' }}>
                        Cadence: <strong>Internal Cadence Invariance</strong><br />
                        Buffer: <strong>Triple Period Line-Split (. \n . \n .)</strong><br />
                        Link Isolation: <strong style={{ color: '#10b981' }}>Comment #1 Protected</strong>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 3-Tier Mixed Hashtag Boxes (3 to 6 Target Limit) */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label style={{ fontSize: '0.82rem', color: '#94a3b8', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Hash size={14} color="#38bdf8" />
                    3-Tier Mixed Hashtag Boxes (Target Limit 3–6):
                  </label>
                  <span style={{ fontSize: '0.72rem', color: '#10b981', fontWeight: 600 }}>
                    🛡️ Anti-Stuffing Compliant
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px' }}>
                  {Object.entries(resultData.hashtag_boxes).map(([boxKey, box]) => (
                    <div 
                      key={boxKey}
                      style={{
                        background: 'rgba(2,6,23,0.7)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '6px',
                        padding: '10px 14px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#38bdf8' }}>
                          {box.title} <span style={{ color: '#64748b', fontWeight: 400 }}>• {box.audience}</span>
                        </div>
                        <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '2px', fontFamily: 'monospace' }}>
                          {box.tag_string}
                        </div>
                      </div>

                      <button
                        onClick={() => handleCopy(box.tag_string, boxKey)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '6px 10px',
                          background: copiedKey === boxKey ? '#10b981' : 'rgba(255,255,255,0.08)',
                          border: '1px solid rgba(255,255,255,0.15)',
                          color: '#ffffff',
                          borderRadius: '4px',
                          fontSize: '0.72rem',
                          fontWeight: 600,
                          cursor: 'pointer'
                        }}
                      >
                        {copiedKey === boxKey ? <Check size={12} /> : <Copy size={12} />}
                        {copiedKey === boxKey ? 'Copied' : 'Copy Box'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Comment Drop Link Helper */}
              {resultData.comment_drop && (
                <div style={{
                  background: 'rgba(16,185,129,0.1)',
                  border: '1px solid rgba(16,185,129,0.3)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#34d399', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <MessageSquare size={14} />
                      First Comment Link Drop (Post Immediately After Publishing):
                    </div>
                    <div style={{ fontSize: '0.84rem', color: '#e2e8f0', marginTop: '3px', fontFamily: 'monospace' }}>
                      {resultData.comment_drop}
                    </div>
                  </div>

                  <button
                    onClick={() => handleCopy(resultData.comment_drop, 'comment_drop')}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '6px 12px',
                      background: copiedKey === 'comment_drop' ? '#10b981' : '#059669',
                      border: 'none',
                      color: '#ffffff',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    {copiedKey === 'comment_drop' ? <Check size={12} /> : <Copy size={12} />}
                    {copiedKey === 'comment_drop' ? 'Copied' : 'Copy Comment #1'}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#64748b',
              textAlign: 'center',
              padding: '30px'
            }}>
              <Share2 size={44} style={{ opacity: 0.4, marginBottom: '12px' }} />
              <h3 style={{ margin: '0 0 6px 0', color: '#94a3b8', fontSize: '1.05rem' }}>Ready to Generate</h3>
              <p style={{ margin: 0, fontSize: '0.85rem', maxWidth: '400px', lineHeight: '1.5' }}>
                Select a sample preset or paste your raw stream. Choose formatting strategy (Auto-Detect, Long Story, Short Punch, or Fire Writing), then click Generate.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PersonalBrandStudioTab;


