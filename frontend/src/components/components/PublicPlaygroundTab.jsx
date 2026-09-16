import React, { useState, useEffect, useRef } from 'react';
import { getApiBase } from '../config/api.js';

export default function PublicPlaygroundTab({ backendUrl }) {
  const apiHost = backendUrl || getApiBase() || `${backendUrl}`;
  const [passKey, setPassKey] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('aibs_active_pass_key') || '';
      // Sanitize stored key if it contains private key string
      if (stored.includes('a2f7c2b0') || stored.length > 50) {
        localStorage.removeItem('aibs_active_pass_key');
        return '';
      }
      return stored;
    }
    return '';
  });


  const [activeSubTab, setActiveSubTab] = useState('image'); // 'image', 'video', 'chat'

  // Image Gen State
  const [imagePrompt, setImagePrompt] = useState('A futuristic glowing crystal synthwave city in Michigan');
  const [imageSize, setImageSize] = useState('1024x1024');
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [generatedImage, setGeneratedImage] = useState(null);

  // Video Gen State
  const [videoPrompt, setVideoPrompt] = useState('Cinematic drone flight through neon clouds, 4k');
  const [videoDuration, setVideoDuration] = useState(300); // 4s to 300s (5 Minutes)
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [generatedVideo, setGeneratedVideo] = useState(null);

  // Audio Gen State
  const [audioPrompt, setAudioPrompt] = useState('Relaxing retro synthwave background track with soft chill pads');
  const [audioLyrics, setAudioLyrics] = useState('');
  const [audioGenre, setAudioGenre] = useState('synthwave');
  const [audioDuration, setAudioDuration] = useState(0); // 0 = Dynamic Auto-Timing
  const [audioTempo, setAudioTempo] = useState(110); // 70 to 160 BPM
  const [audioVocalStyle, setAudioVocalStyle] = useState('lead'); // 'lead', 'harmonies', 'whispered', 'vocoder', 'instrumental'
  const [audioArrangement, setAudioArrangement] = useState('verse_chorus'); // 'verse_chorus', 'build_drop', 'continuous_loop'
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const [generatedAudio, setGeneratedAudio] = useState(null);


  // Chat State
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI-BS Studio Assistant. How can I help you generate audio, video, images, or code today?' }
  ]);
  
  const chatEndRef = useRef(null);
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);
  const [isChatting, setIsChatting] = useState(false);

  // Developer Portal State
  const [devClientName, setDevClientName] = useState('My Creative App');
  const [devTier, setDevTier] = useState('starter');
  const [newGeneratedPasskey, setNewGeneratedPasskey] = useState(null);
  const [passkeyUsageInfo, setPasskeyUsageInfo] = useState(null);
  const [isGeneratingPasskey, setIsGeneratingPasskey] = useState(false);

  // Speculative VRAM Pre-loader trigger
  useEffect(() => {
    fetch(`${apiHost}/v1/media/warmup`, { method: 'POST' }).catch(() => {});
  }, [apiHost]);

  const handleRequestPasskey = async () => {
    if (!devClientName.trim()) return alert('Please enter a Client or Company Name!');
    setIsGeneratingPasskey(true);
    try {
      const res = await fetch(`${apiHost}/v1/auth/request-passkey`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: devClientName, tier: devTier })
      });
      const data = await res.json();
      if (data.passkey) {
        setNewGeneratedPasskey(data);
        setPassKey(data.passkey);
        if (typeof window !== 'undefined') localStorage.setItem('aibs_active_pass_key', data.passkey);
      } else {
        alert('Error generating passkey: ' + (data.message || JSON.stringify(data)));
      }
    } catch (e) {
      alert('Passkey Request Failed: ' + e.message);
    } finally {
      setIsGeneratingPasskey(false);
    }
  };

  const handleCheckPasskeyUsage = async () => {
    if (!passKey.trim()) return alert('Please enter a Pass Key to check usage!');
    try {
      const res = await fetch(`${apiHost}/v1/user/usage`, {
        headers: { 'Authorization': `Bearer ${passKey}` }
      });
      const data = await res.json();
      setPasskeyUsageInfo(data);
    } catch (e) {
      alert('Usage check error: ' + e.message);
    }
  };


  // Saved Media Vault State
  const [mediaVault, setMediaVault] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('aibs_created_media_vault');
        return stored ? JSON.parse(stored) : [];
      } catch (e) {
        return [];
      }
    }
    return [];
  });
  const [vaultFilter, setVaultFilter] = useState('all'); // 'all', 'image', 'video', 'audio'

  const saveToMediaVault = (type, prompt, url, metadata = {}) => {
    const newItem = {
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString() + ' ' + new Date().toLocaleDateString(),
      type,
      prompt,
      url,
      metadata
    };
    const updated = [newItem, ...mediaVault];
    setMediaVault(updated);
    if (typeof window !== 'undefined') {
      localStorage.setItem('aibs_created_media_vault', JSON.stringify(updated));
    }
  };

  const deleteFromVault = (id) => {
    const updated = mediaVault.filter(item => item.id !== id);
    setMediaVault(updated);
    if (typeof window !== 'undefined') {
      localStorage.setItem('aibs_created_media_vault', JSON.stringify(updated));
    }
  };

  const clearVault = () => {
    if (confirm('Are you sure you want to clear your Created Media Vault?')) {
      setMediaVault([]);
      if (typeof window !== 'undefined') {
        localStorage.removeItem('aibs_created_media_vault');
      }
    }
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('aibs_active_pass_key');
      if (stored) setPassKey(stored);
    }
  }, []);

  const handleGenerateImage = async () => {
    if (!passKey) return alert('Please enter or purchase an active Pass Key first!');
    setIsGeneratingImage(true);
    setGeneratedImage(null);

    try {
      const res = await fetch(`${apiHost}/v1/images/generations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${passKey}`
        },
        body: JSON.stringify({ prompt: imagePrompt, size: imageSize })
      });

      const data = await res.json();
      let rawUrl = null;

      if (data.data && Array.isArray(data.data) && data.data.length > 0) {
        const item = data.data[0];
        if (typeof item === 'string') {
          rawUrl = item;
        } else if (item.url) {
          rawUrl = item.url;
        } else if (item.b64_json) {
          rawUrl = `data:image/png;base64,${item.b64_json}`;
        }
      } else if (data.url) {
        rawUrl = data.url;
      } else if (data.image_url) {
        rawUrl = data.image_url;
      } else if (data.image) {
        rawUrl = data.image;
      } else if (data.output) {
        rawUrl = typeof data.output === 'string' ? data.output : (Array.isArray(data.output) ? data.output[0] : null);
      }

      if (rawUrl) {
        const fullUrl = (rawUrl.startsWith('http') || rawUrl.startsWith('data:')) ? rawUrl : `${apiHost}${rawUrl}`;
        setGeneratedImage(fullUrl);
        saveToMediaVault('image', imagePrompt, fullUrl, { size: imageSize });
      } else if (data.error) {
        alert('Generation Error: ' + (data.error.message || JSON.stringify(data.error)));
      } else {
        alert('Image generation completed, but no media URL could be extracted from server response: ' + JSON.stringify(data));
      }
    } catch (e) {
      alert('Network Error: ' + e.message);
    } finally {
      setIsGeneratingImage(false);
    }
  };

  const handleSendChat = async () => {
    if (!chatInput.trim() || isChatting) return;
    if (!passKey) return alert('Please enter or purchase an active Pass Key first!');

    const userMsg = { role: 'user', content: chatInput };
    const updatedMessages = [...chatMessages, userMsg];
    setChatMessages(updatedMessages);
    setChatInput('');
    setIsChatting(true);

    try {
      const res = await fetch(`${apiHost}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${passKey}`
        },
        body: JSON.stringify({
          model: 'stehouwer_llm',
          messages: updatedMessages
        })
      });

      const data = await res.json();
      if (data.choices && data.choices[0] && data.choices[0].message) {
        setChatMessages(prev => [...prev, data.choices[0].message]);
      } else if (data.error) {
        alert('Chat Error: ' + data.error.message);
      }
    } catch (e) {
      alert('Chat fault: ' + e.message);
    } finally {
      setIsChatting(false);
    }
  };

  const handleGenerateVideo = async () => {
    if (!passKey) return alert('Please enter or purchase an active Pass Key first!');
    setIsGeneratingVideo(true);
    setGeneratedVideo(null);

    try {
      const res = await fetch(`${apiHost}/v1/videos/generations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${passKey}`
        },
        body: JSON.stringify({ prompt: videoPrompt, duration_sec: videoDuration, fps: 24 })
      });

      const data = await res.json();
      let rawUrl = null;

      if (data.data && Array.isArray(data.data) && data.data.length > 0) {
        const item = data.data[0];
        if (typeof item === 'string') rawUrl = item;
        else if (item.url) rawUrl = item.url;
      } else if (data.url) rawUrl = data.url;
      else if (data.video) rawUrl = data.video;
      else if (data.output) rawUrl = typeof data.output === 'string' ? data.output : (Array.isArray(data.output) ? data.output[0] : null);

      if (rawUrl) {
        const fullUrl = (rawUrl.startsWith('http') || rawUrl.startsWith('data:')) ? rawUrl : `${apiHost}${rawUrl}`;
        setGeneratedVideo(fullUrl);
        saveToMediaVault('video', videoPrompt, fullUrl, { duration_sec: videoDuration, fps: 24 });
      } else if (data.error) {
        alert('Video Generation Error: ' + (data.error.message || JSON.stringify(data.error)));
      } else {
        alert('Video generation completed!');
      }
    } catch (e) {
      alert('Network Error: ' + e.message);
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  const handleGenerateAudio = async () => {
    if (!passKey) return alert('Please enter or purchase an active Pass Key first!');
    setIsGeneratingAudio(true);
    setGeneratedAudio(null);

    try {
      const res = await fetch(`${apiHost}/v1/audio/generations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${passKey}`
        },
        body: JSON.stringify({
          prompt: audioPrompt,
          genre: audioGenre,
          duration_sec: audioDuration,
          lyrics: audioLyrics,
          tempo_bpm: audioTempo,
          vocal_style: audioVocalStyle,
          arrangement: audioArrangement
        })
      });

      const data = await res.json();
      let rawUrl = null;

      if (data.data && Array.isArray(data.data) && data.data.length > 0) {
        const item = data.data[0];
        if (typeof item === 'string') rawUrl = item;
        else if (item.url) rawUrl = item.url;
      } else if (data.url) rawUrl = data.url;
      else if (data.audio) rawUrl = data.audio;
      else if (data.output) rawUrl = typeof data.output === 'string' ? data.output : (Array.isArray(data.output) ? data.output[0] : null);

      if (rawUrl) {
        const fullUrl = (rawUrl.startsWith('http') || rawUrl.startsWith('data:')) 
          ? rawUrl 
          : `${apiHost}${rawUrl}`;
        const actualDur = (data.data && data.data[0] && data.data[0].duration_sec) ? data.data[0].duration_sec : audioDuration;
        setGeneratedAudio(fullUrl);
        saveToMediaVault('audio', audioPrompt, fullUrl, { genre: audioGenre, duration_sec: actualDur, tempo_bpm: audioTempo, vocal_style: audioVocalStyle });

      } else if (data.error) {
        alert('Audio Generation Error: ' + (data.error.message || JSON.stringify(data.error)));
      } else {
        alert('Audio synthesis completed!');
      }
    } catch (e) {
      alert('Network Error: ' + e.message);
    } finally {
      setIsGeneratingAudio(false);
    }
  };

  return (

    <main id="main-content" style={{ padding: '24px', background: '#090d16', color: '#e6edf3', minHeight: '100vh', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Brand Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #30363d', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: '800', margin: 0, color: '#38bdf8' }}>🎨 Stehouwer AI Studio & Playground</h1>
          <p style={{ fontSize: '13px', color: '#8b949e', margin: '4px 0 0 0' }}>Isolated Creator Studio — Powered by NVIDIA GeForce RTX 4090 GPU Compute</p>
        </div>

        {/* Pass Key Header Bar */}
        <form onSubmit={(e) => e.preventDefault()} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input type="text" name="username" value="aibs_passkey_user" readOnly autoComplete="username" style={{ display: 'none' }} />
          <label htmlFor="pass-key-input" style={{ fontSize: '12px', color: '#8b949e' }}>Pass Key:</label>
          <input
            id="pass-key-input"
            aria-label="Pass Key Input"
            type="password"
            autoComplete="current-password"
            value={passKey}
            onChange={(e) => {
              setPassKey(e.target.value);
              if (typeof window !== 'undefined') localStorage.setItem('aibs_active_pass_key', e.target.value);
            }}
            placeholder="sk_aibs_live_..."
            style={{
              padding: '6px 12px',
              background: '#161b22',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#38bdf8',
              fontSize: '12px',
              width: '180px',
              fontFamily: 'monospace'
            }}
          />
        </form>
      </div>

      {/* Paid API Key Security Gate Banner if Key is Missing */}
      {!passKey.trim() && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(137, 87, 229, 0.15), rgba(56, 189, 248, 0.15))',
          border: '1px solid #8957e5',
          borderRadius: '12px',
          padding: '24px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px'
        }}>
          <div style={{ maxWidth: '600px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ fontSize: '18px' }}>🔑</span>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#e6edf3' }}>Paid API Key Required for Web Studio Access</h3>
            </div>
            <p style={{ margin: 0, fontSize: '13px', color: '#8b949e', lineHeight: '1.5' }}>
              Web Studio GPU rendering requires an active Stehouwer AI Pass Key (<code style={{ color: '#38bdf8' }}>sk_aibs_...</code>). Enter your paid key above to unlock rendering or purchase a 1-click flexibility pass.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <a
              href="/checkout"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                background: 'linear-gradient(90deg, #8957e5, #38bdf8)',
                color: '#ffffff',
                padding: '10px 20px',
                borderRadius: '6px',
                fontWeight: '700',
                fontSize: '13px',
                textDecoration: 'none',
                boxShadow: '0 4px 12px rgba(137, 87, 229, 0.3)'
              }}
            >
              💳 Get Pass Key (From $4.99)
            </a>
          </div>
        </div>
      )}


      {/* Sub Navigation Bar */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        {[
          { id: 'image', label: '🎨 Image Studio (SDXL)', desc: '2-Sec Render' },
          { id: 'video', label: '🎬 Video Studio (WanVideo)', desc: '4s Render' },
          { id: 'audio', label: '🎵 Audio & Music Studio', desc: '13 Genres' },
          { id: 'chat', label: '💬 AI Assistant Chat', desc: 'Fast LLM' },
          { id: 'developer', label: '🚀 API Developer & Passkey Portal', desc: 'Commercial Gateway' },
          { id: 'vault', label: `📁 My Created Media Vault (${mediaVault.length})`, desc: 'History' }

        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              padding: '10px 18px',
              background: activeSubTab === tab.id ? '#1f6feb' : '#161b22',
              color: '#ffffff',
              border: activeSubTab === tab.id ? '1px solid #38bdf8' : '1px solid #30363d',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '13px'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* SUB-TAB 1: IMAGE STUDIO */}
      {activeSubTab === 'image' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 16px 0', color: '#f0f6fc' }}>High-Resolution SDXL Image Generation</h2>
          
          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="image-prompt-input" style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>Image Prompt:</label>
            <textarea
              id="image-prompt-input"
              aria-label="Image Prompt Input"
              value={imagePrompt}
              onChange={(e) => setImagePrompt(e.target.value)}
              rows={3}
              style={{ width: '100%', padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '14px', resize: 'vertical' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <label htmlFor="image-size-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Aspect Ratio:</label>
              <select
                id="image-size-select"
                aria-label="Aspect Ratio Select"
                value={imageSize}
                onChange={(e) => setImageSize(e.target.value)}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3' }}
              >
                <option value="1024x1024">Square (1024x1024)</option>
                <option value="1280x720">Landscape (1280x720)</option>
                <option value="720x1280">Portrait (720x1280)</option>
              </select>
            </div>

            <button
              onClick={handleGenerateImage}
              disabled={isGeneratingImage}
              style={{
                padding: '12px 24px',
                background: 'linear-gradient(90deg, #238636, #2ea043)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '700',
                cursor: isGeneratingImage ? 'wait' : 'pointer',
                marginTop: '16px'
              }}
            >
              {isGeneratingImage ? '⚡ RTX 4090 Rendering Image...' : '✨ Generate Image'}
            </button>
          </div>

          {/* Rendered Result Output */}
          {generatedImage && (
            <div style={{ marginTop: '24px', textAlign: 'center', background: '#0d1117', padding: '16px', borderRadius: '12px', border: '1px solid #30363d' }}>
              <img src={generatedImage?.startsWith('http') || generatedImage?.startsWith('data:') || generatedImage?.startsWith('blob:') ? generatedImage : `${apiHost}${generatedImage?.startsWith('/') ? '' : '/'}${generatedImage}`} alt="Generated AI" style={{ maxWidth: '100%', maxHeight: '500px', borderRadius: '8px' }} />
              <div style={{ marginTop: '12px' }}>
                <a href={generatedImage} download="stehouwer_ai_image.png" style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: '600', fontSize: '13px' }}>
                  📥 Download High-Res Image
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 2: VIDEO STUDIO */}
      {activeSubTab === 'video' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 16px 0', color: '#f0f6fc' }}>WanVideo / AnimateDiff Motion Studio</h2>
          
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>Video Motion Prompt:</label>
            <textarea
              value={videoPrompt}
              onChange={(e) => setVideoPrompt(e.target.value)}
              rows={3}
              style={{ width: '100%', padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '14px', resize: 'vertical' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap' }}>
            <div>
              <label htmlFor="video-duration-select" style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>Video Clip Duration:</label>
              <select
                id="video-duration-select"
                aria-label="Video Clip Duration"
                value={videoDuration}
                onChange={(e) => setVideoDuration(Number(e.target.value))}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value={4}>⚡ 4-Second Quick Clip</option>
                <option value={15}>🎬 15-Second Motion Scene</option>
                <option value={30}>📺 30-Second Commercial Spot</option>
                <option value={60}>🎥 60-Second Short Film</option>
                <option value={180}>🍿 3-Minute Epic Scene (180s)</option>
                <option value={300}>🌟 5-Minute Master Production (300s)</option>
              </select>
            </div>

            <button
              onClick={handleGenerateVideo}
              disabled={isGeneratingVideo}
              style={{
                padding: '10px 24px',
                background: 'linear-gradient(90deg, #8957e5, #6e40c9)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '700',
                cursor: isGeneratingVideo ? 'wait' : 'pointer',
                marginTop: '16px'
              }}
            >
              {isGeneratingVideo ? `⚡ RTX 4090 Rendering ${videoDuration}s Video...` : `🎬 Generate ${videoDuration}s AI Video`}
            </button>
          </div>


          {/* Rendered Video Result Output */}
          {generatedVideo && (
            <div style={{ marginTop: '24px', textAlign: 'center', background: '#0d1117', padding: '16px', borderRadius: '12px', border: '1px solid #30363d' }}>
              <video controls autoPlay loop src={generatedVideo?.startsWith('http') || generatedVideo?.startsWith('data:') || generatedVideo?.startsWith('blob:') ? generatedVideo : `${apiHost}${generatedVideo?.startsWith('/') ? '' : '/'}${generatedVideo}`} style={{ maxWidth: '100%', maxHeight: '450px', borderRadius: '8px' }} />
              <div style={{ marginTop: '12px' }}>
                <a href={generatedVideo} download="wanvideo_ai_clip.mp4" style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: '600', fontSize: '13px' }}>
                  📥 Download WanVideo MP4 Clip
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 3: AUDIO STUDIO */}
      {activeSubTab === 'audio' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 4px 0', color: '#f0f6fc' }}>AI Multi-Genre Music & Audio Texture Studio</h2>
          <p style={{ fontSize: '12px', color: '#8b949e', marginBottom: '16px' }}>
            Combine primary subgenres, niche hybrid blends, acoustic texture modifiers, vocal timbres, and rhythm descriptors into a custom tag stack.
          </p>

          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="audio-prompt-input" style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>Custom Tag-Stacked Audio Prompt:</label>
            <textarea
              id="audio-prompt-input"
              aria-label="Custom Tag-Stacked Audio Prompt"
              value={audioPrompt}
              onChange={(e) => setAudioPrompt(e.target.value)}
              rows={3}
              style={{ width: '100%', padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '14px', resize: 'vertical' }}
            />
          </div>

          {/* Custom Song Lyrics & Vocal Verses Input */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label htmlFor="audio-lyrics-input" style={{ fontSize: '12px', color: '#38bdf8', fontWeight: '600' }}>🎤 Custom Song Lyrics & Vocal Verses (Optional):</label>
              <button
                onClick={() => setAudioLyrics('[Verse 1]\nNeon lights in the midnight rain\nDriving fast down memory lane\n\n[Chorus]\nWe are the dreamers of the night\nElectric hearts burning bright\n\n[Bridge]\nFade away into the sound\nNo looking back, we own this town')}
                style={{ background: 'transparent', border: 'none', color: '#a855f7', fontSize: '11px', cursor: 'pointer', textDecoration: 'underline' }}
              >
                + Insert Sample Verse & Chorus Lyrics
              </button>
            </div>
            <textarea
              id="audio-lyrics-input"
              aria-label="Custom Song Lyrics & Vocal Verses"
              value={audioLyrics}
              onChange={(e) => setAudioLyrics(e.target.value)}
              rows={4}
              placeholder="[Verse 1]&#10;Type or paste your custom song lyrics here...&#10;&#10;[Chorus]&#10;Add your chorus lyrics here..."
              style={{ width: '100%', padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '13px', fontFamily: 'monospace', resize: 'vertical' }}
            />
          </div>

          {/* Quick Tag-Stacking Helper Chips */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '8px' }}>⚡ Quick Tag-Stacking Helper Chips (Click to append to prompt):</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {[
                "boom bap 808 sub-bass", "darksynth cyberpunk", "bluegrass trap hybrid", "epic dark orchestral",
                "1970s analog vinyl", "1980s cassette saturation", "90s lo-fi tape", "sidechain compression",
                "raspy gritty vocal", "silky whispered vocal", "vocoder effect", "gang vocals background",
                "syncopated beat", "half-time bounce", "relentless momentum", "explosive crescendo"
              ].map(tag => (
                <button
                  key={tag}
                  onClick={() => setAudioPrompt(prev => prev ? `${prev}, ${tag}` : tag)}
                  style={{
                    padding: '4px 10px',
                    background: '#21262d',
                    border: '1px solid #30363d',
                    borderRadius: '12px',
                    color: '#38bdf8',
                    fontSize: '11px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  + {tag}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap' }}>
            <div>
              <label htmlFor="audio-genre-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Primary Genre Category:</label>
              <select
                id="audio-genre-select"
                aria-label="Primary Genre Category"
                value={audioGenre}
                onChange={(e) => setAudioGenre(e.target.value)}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value="hip_hop">🎤 Hip Hop & Rap (Boom Bap, Trap, Drill, Phonk, 808s)</option>
                <option value="rock_metal">🎸 Rock & Metal (Alt Rock, Grunge, Heavy Metal, Metalcore)</option>
                <option value="electronic_edm">⚡ Electronic & EDM (Synthwave, Techno, DnB, Dubstep)</option>
                <option value="pop_dance">💃 Pop & Dance (Synth-Pop, K-Pop, Electropop)</option>
                <option value="rb_soul">🎷 R&B & Soul (Neo-Soul, Funk, Disco, Smooth Soul)</option>
                <option value="folk_country">🌿 Folk & Country (Americana, Bluegrass, Celtic Folk)</option>
                <option value="jazz_blues">🎺 Jazz & Blues (Smooth Jazz, Bebop, Bossa Nova, Blues)</option>
                <option value="global_rhythms">🌍 Global Rhythms (Afrobeats, Reggaeton, Dancehall, Amapiano)</option>
                <option value="cyberpunk_synthmetal">🔥 Hybrid: Cyberpunk / Synth-Metal (Industrial, Darksynth)</option>
                <option value="acoustic_hybrid">🪕 Hybrid: Acoustic / Hybrid (Bluegrass Trap, Folk-Pop)</option>
                <option value="atmospheric_ambient">🌌 Hybrid: Atmospheric / Ambient (Downtempo, Trip-Hop)</option>
                <option value="cinematic_orchestral">🎬 Hybrid: Cinematic / Orchestral (Epic Film Score, Trailer Music)</option>
                <option value="heavy_distorted">💥 Hybrid: Heavy / Distorted (Sludge Metal, Deathcore, Nu-Metal)</option>
              </select>
            </div>

            <div>
              <label htmlFor="audio-duration-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Song Length / Duration:</label>
              <select
                id="audio-duration-select"
                aria-label="Song Length / Duration"
                value={audioDuration}
                onChange={(e) => setAudioDuration(Number(e.target.value))}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value={0}>✨ Dynamic Auto-Timing (Calculated from Lyrics & BPM)</option>
                <option value={10}>10 Seconds Quick Clip</option>

                <option value={30}>30 Seconds Short Track</option>
                <option value={60}>60 Seconds Full Verse</option>
                <option value={180}>3 Minutes Full Song (180s)</option>
                <option value={300}>5 Minutes Extended Master (300s)</option>
                <option value={600}>10 Minutes Epic Suite (600s)</option>
                <option value={1200}>♾️ Unlimited Continuous Stream (1200s / 20 Mins)</option>
              </select>
            </div>

            <div>
              <label htmlFor="audio-vocal-style-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Vocal Mix Style:</label>
              <select
                id="audio-vocal-style-select"
                aria-label="Vocal Mix Style"
                value={audioVocalStyle}
                onChange={(e) => setAudioVocalStyle(e.target.value)}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value="lead">🎙️ Lead Vocals (Clean & Clear)</option>
                <option value="harmonies">🎶 Layered Harmonies & Backing</option>
                <option value="whispered">🤫 Whispered & Soft Vocal</option>
                <option value="vocoder">🤖 Vocoder & Auto-Tune Synth</option>
                <option value="instrumental">🎻 Instrumental Only (No Vocals)</option>
              </select>
            </div>

            <div>
              <label htmlFor="audio-arrangement-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Song Arrangement:</label>
              <select
                id="audio-arrangement-select"
                aria-label="Song Arrangement"
                value={audioArrangement}
                onChange={(e) => setAudioArrangement(e.target.value)}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value="verse_chorus">🎼 Verse - Chorus - Bridge - Outro</option>
                <option value="build_drop">🔥 Intro - Build-Up - Explosive Drop</option>
                <option value="continuous_loop">🔁 Continuous Ambient Soundscape</option>
              </select>
            </div>

            <div>
              <label htmlFor="audio-tempo-range" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Tempo / Speed: <strong style={{ color: '#38bdf8' }}>{audioTempo} BPM</strong></label>
              <input
                id="audio-tempo-range"
                aria-label="Tempo Speed BPM"
                type="range"
                min="70"
                max="160"
                value={audioTempo}
                onChange={(e) => setAudioTempo(Number(e.target.value))}
                style={{ width: '160px', accentColor: '#38bdf8', cursor: 'pointer' }}
              />
            </div>

            <button
              onClick={handleGenerateAudio}
              disabled={isGeneratingAudio}
              style={{
                padding: '12px 24px',
                background: 'linear-gradient(90deg, #d97706, #b45309)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '700',
                cursor: isGeneratingAudio ? 'wait' : 'pointer',
                marginTop: '16px'
              }}
            >
              {isGeneratingAudio 
                ? `⚡ Synthesizing ${audioDuration === 0 ? 'Auto-Timed' : audioDuration + 's'} Song (${audioTempo} BPM)...` 
                : `🎵 Synthesize ${audioDuration === 0 ? 'Auto-Timed' : audioDuration + 's'} Track (${audioTempo} BPM)`
              }
            </button>
          </div>





          {/* Rendered Audio Result Output */}
          {generatedAudio && (
            <div style={{ marginTop: '24px', textAlign: 'center', background: '#0d1117', padding: '20px', borderRadius: '12px', border: '1px solid #30363d' }}>
              <audio controls autoPlay src={generatedAudio ? (generatedAudio.startsWith('http') ? generatedAudio : `${apiHost}${generatedAudio.startsWith('/') ? '' : '/'}${generatedAudio}`) : undefined} style={{ width: '100%', maxWidth: '500px', marginBottom: '12px' }} />
              <div>
                <a href={generatedAudio} download={`stehouwer_ai_${audioGenre}.wav`} style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: '600', fontSize: '13px' }}>
                  📥 Download Tag-Stacked High-Quality WAV Audio
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 3: CHAT STUDIO */}
      {activeSubTab === 'chat' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', height: '600px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 16px 0', color: '#f0f6fc' }}>Stehouwer AI Chat Assistant</h2>
          
          {/* Chat Messages */}
          <div style={{ flex: 1, overflowY: 'auto', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            {chatMessages.map((msg, idx) => (
              <div key={idx} style={{ marginBottom: '12px', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                <div style={{
                  display: 'inline-block',
                  maxWidth: '80%',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  background: msg.role === 'user' ? '#1f6feb' : '#21262d',
                  color: '#ffffff',
                  fontSize: '14px',
                  lineHeight: '1.5'
                }}>
                  {msg.content}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
              placeholder="Ask anything or request creative assistance..."
              style={{ flex: 1, padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '14px' }}
            />
            <button
              onClick={handleSendChat}
              disabled={isChatting}
              style={{ padding: '12px 20px', background: '#238636', color: '#ffffff', border: 'none', borderRadius: '8px', fontWeight: '700', cursor: 'pointer' }}
            >
              Send
            </button>
          </div>
        </div>
      )}

      {/* SUB-TAB 6: COMMERCIAL API DEVELOPER & PASSKEY PORTAL */}
      {activeSubTab === 'developer' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <div style={{ marginBottom: '24px', borderBottom: '1px solid #21262d', paddingBottom: '16px' }}>
            <h2 style={{ fontSize: '20px', margin: '0 0 6px 0', color: '#38bdf8', fontWeight: '800' }}>
              🚀 Commercial API Developer & Passkey Portal
            </h2>
            <p style={{ fontSize: '13px', color: '#8b949e', margin: 0, lineHeight: '1.5' }}>
              Integrate AI-BS 44.1kHz RVQ Neural Audio, SDXL Visual Generation, WanVideo 5-Min Clips, and LLM Chat directly into your applications via sovereign API endpoints.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', marginBottom: '24px' }}>
            {/* Card 1: Request Passkey */}
            <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
              <h3 style={{ fontSize: '16px', color: '#f0f6fc', marginTop: 0 }}>🔑 Self-Service Passkey Generator</h3>
              <p style={{ fontSize: '12px', color: '#8b949e', marginBottom: '16px' }}>
                Instantly provision a sovereign API key to access live endpoints over HTTPS.
              </p>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Client / Company Name:</label>
                <input
                  type="text"
                  value={devClientName}
                  onChange={(e) => setDevClientName(e.target.value)}
                  placeholder="e.g. Grand Rapids Creative Studio"
                  style={{ width: '100%', padding: '10px', background: '#161b22', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Target Usage Tier:</label>
                <select
                  value={devTier}
                  onChange={(e) => setDevTier(e.target.value)}
                  style={{ width: '100%', padding: '10px', background: '#161b22', border: '1px solid #30363d', borderRadius: '6px', color: '#38bdf8', fontSize: '13px' }}
                >
                  <option value="starter">Starter Tier (1,000 requests/day - $19/mo)</option>
                  <option value="pro">Pro Tier (10,000 requests/day - $49/mo)</option>
                  <option value="enterprise">Enterprise Tier (100,000 requests/day - $199/mo)</option>
                </select>
              </div>

              <button
                onClick={handleRequestPasskey}
                disabled={isGeneratingPasskey}
                style={{ width: '100%', padding: '12px', background: 'linear-gradient(90deg, #1f6feb, #38bdf8)', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '700', fontSize: '13px', cursor: 'pointer' }}
              >
                {isGeneratingPasskey ? 'Provisioning Passkey...' : '⚡ Generate Developer Passkey'}
              </button>

              {newGeneratedPasskey && (
                <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid #38bdf8', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: '#8b949e', marginBottom: '4px' }}>YOUR NEW PASSKEY:</div>
                  <code style={{ fontSize: '12px', color: '#38bdf8', wordBreak: 'break-all', fontWeight: 'bold' }}>{newGeneratedPasskey.passkey}</code>
                  <div style={{ fontSize: '11px', color: '#238636', marginTop: '6px' }}>✓ Key automatically active and saved to your studio browser context!</div>
                </div>
              )}
            </div>

            {/* Card 2: Quota & Usage Monitor */}
            <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
              <h3 style={{ fontSize: '16px', color: '#f0f6fc', marginTop: 0 }}>📊 Live Quota & Usage Inspector</h3>
              <p style={{ fontSize: '12px', color: '#8b949e', marginBottom: '16px' }}>
                Check daily unit usage, remaining request balance, and active rate limits.
              </p>

              <button
                onClick={handleCheckPasskeyUsage}
                style={{ width: '100%', padding: '12px', background: '#238636', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '700', fontSize: '13px', cursor: 'pointer', marginBottom: '16px' }}
              >
                🔍 Inspect Active Passkey Usage
              </button>

              {passkeyUsageInfo ? (
                <div style={{ background: '#161b22', padding: '12px', borderRadius: '6px', fontSize: '12px', border: '1px solid #30363d' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ color: '#8b949e' }}>Client Name:</span>
                    <strong style={{ color: '#f0f6fc' }}>{passkeyUsageInfo.client_name}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ color: '#8b949e' }}>Active Tier:</span>
                    <span style={{ color: '#38bdf8', fontWeight: 'bold', textTransform: 'uppercase' }}>{passkeyUsageInfo.tier}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ color: '#8b949e' }}>Total Requests Recorded:</span>
                    <span style={{ color: '#e6edf3' }}>{passkeyUsageInfo.total_requests_recorded}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#8b949e' }}>Daily Quota Remaining:</span>
                    <span style={{ color: '#238636', fontWeight: 'bold' }}>{passkeyUsageInfo.remaining_units_today} / {passkeyUsageInfo.tier_daily_quota}</span>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: '12px', color: '#8b949e', fontStyle: 'italic', textAlign: 'center', padding: '20px 0' }}>
                  Click inspect button to view current passkey telemetry.
                </div>
              )}
            </div>
          </div>

          {/* Quickstart Code Snippets */}
          <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ fontSize: '16px', color: '#f0f6fc', marginTop: 0, marginBottom: '8px' }}>💻 Developer Quickstart cURL Snippet</h3>
            <p style={{ fontSize: '12px', color: '#8b949e', margin: '0 0 12px 0' }}>
              Execute requests directly against our live production proxy endpoint (<code style={{ color: '#38bdf8' }}>https://stehouwer-publishing.com/v1/</code>):
            </p>

            <pre style={{ background: '#161b22', padding: '16px', borderRadius: '8px', color: '#38bdf8', fontSize: '12px', fontFamily: 'monospace', overflowX: 'auto', border: '1px solid #30363d', margin: 0 }}>
{`curl -X POST https://stehouwer-publishing.com/v1/audio/generations \\
  -H "Authorization: Bearer ${newGeneratedPasskey?.passkey || 'sk_aibs_live_YOUR_PASSKEY_HERE'}" \\
  -H "Content-Type: application/json" \\

  -d '{
    "prompt": "Retro acoustic guitar and cellos",
    "genre": "acoustic",
    "duration_sec": 0,
    "tempo_bpm": 95,
    "lyrics": "[Verse 1]\\nGolden sunlight on the trees"
  }'`}
            </pre>
          </div>
        </div>
      )}

      {/* SUB-TAB 5: CREATED MEDIA VAULT */}

      {activeSubTab === 'vault' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '18px', margin: '0 0 4px 0', color: '#f0f6fc' }}>📁 My Created Media Vault</h2>
              <p style={{ fontSize: '12px', color: '#8b949e', margin: 0 }}>
                Persistent local gallery of all your rendered images, motion video clips, and synthesized audio tracks.
              </p>
            </div>

            {mediaVault.length > 0 && (
              <button
                onClick={clearVault}
                style={{ padding: '6px 14px', background: '#da3633', color: '#ffffff', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
              >
                🗑️ Clear Entire Vault
              </button>
            )}
          </div>

          {/* Filter Pills */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
            {[
              { id: 'all', label: 'All Media' },
              { id: 'image', label: '🎨 Images' },
              { id: 'video', label: '🎬 Videos' },
              { id: 'audio', label: '🎵 Audio Tracks' }
            ].map(filter => (
              <button
                key={filter.id}
                onClick={() => setVaultFilter(filter.id)}
                style={{
                  padding: '6px 14px',
                  background: vaultFilter === filter.id ? '#1f6feb' : '#0d1117',
                  color: '#ffffff',
                  border: vaultFilter === filter.id ? '1px solid #38bdf8' : '1px solid #30363d',
                  borderRadius: '20px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                {filter.label}
              </button>
            ))}
          </div>

          {/* Media Items Grid */}
          {mediaVault.filter(item => vaultFilter === 'all' || item.type === vaultFilter).length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 24px', background: '#0d1117', borderRadius: '12px', border: '1px solid #30363d', color: '#8b949e' }}>
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>📁</div>
              <h3 style={{ fontSize: '16px', margin: '0 0 8px 0', color: '#e6edf3' }}>No Media Items Saved Yet</h3>
              <p style={{ fontSize: '13px', margin: 0 }}>
                Generate images, videos, or audio tracks in the playground to automatically save them into your vault!
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
              {mediaVault
                .filter(item => vaultFilter === 'all' || item.type === vaultFilter)
                .map(item => (
                  <div
                    key={item.id}
                    style={{
                      background: '#0d1117',
                      border: '1px solid #30363d',
                      borderRadius: '12px',
                      padding: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      justify: 'space-between'
                    }}
                  >
                    <div>
                      {/* Header Badge & Date */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: '700',
                          background: item.type === 'image' ? '#1f6feb' : item.type === 'video' ? '#8957e5' : '#d97706',
                          color: '#ffffff'
                        }}>
                          {item.type === 'image' ? '🎨 IMAGE' : item.type === 'video' ? '🎬 VIDEO' : '🎵 AUDIO'}
                        </span>
                        <span style={{ fontSize: '11px', color: '#8b949e' }}>{item.timestamp}</span>
                      </div>

                      {/* Prompt */}
                      <p style={{ fontSize: '13px', color: '#e6edf3', margin: '0 0 14px 0', lineHeight: '1.4', fontWeight: '500' }}>
                        "{item.prompt}"
                      </p>

                      {/* Media Display */}
                      {(() => {
                        const mediaSrc = (item.url && !item.url.startsWith('http') && !item.url.startsWith('data:')) ? `${apiHost}${item.url}` : item.url;
                        return (
                          <div style={{ marginBottom: '14px', textAlign: 'center', background: '#161b22', borderRadius: '8px', padding: '8px', overflow: 'hidden' }}>
                            {item.type === 'image' && (
                              <img src={mediaSrc ? (mediaSrc.startsWith('http') || mediaSrc.startsWith('data:') ? mediaSrc : `${apiHost}${mediaSrc.startsWith('/') ? '' : '/'}${mediaSrc}`) : ''} alt={item.prompt} style={{ maxWidth: '100%', maxHeight: '250px', borderRadius: '6px', objectFit: 'contain' }} />
                            )}
                            {item.type === 'video' && (
                              <video controls autoPlay loop src={mediaSrc ? (mediaSrc.startsWith('http') ? mediaSrc : `${apiHost}${mediaSrc.startsWith('/') ? '' : '/'}${mediaSrc}`) : undefined} style={{ maxWidth: '100%', maxHeight: '250px', borderRadius: '6px' }} />
                            )}
                            {item.type === 'audio' && (
                              <audio controls src={mediaSrc ? (mediaSrc.startsWith('http') ? mediaSrc : `${apiHost}${mediaSrc.startsWith('/') ? '' : '/'}${mediaSrc}`) : undefined} style={{ width: '100%' }} />
                            )}
                          </div>
                        );
                      })()}
                    </div>

                    {/* Footer Actions */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #21262d', paddingTop: '12px' }}>
                      <a
                        href={(item.url && !item.url.startsWith('http') && !item.url.startsWith('data:')) ? `${apiHost}${item.url}` : item.url}
                        download={`stehouwer_${item.type}_${item.id}.${item.type === 'image' ? 'png' : item.type === 'video' ? 'mp4' : 'wav'}`}
                        style={{ color: '#38bdf8', textDecoration: 'none', fontSize: '12px', fontWeight: '600' }}
                      >
                        📥 Download File
                      </a>
                      <button
                        onClick={() => deleteFromVault(item.id)}
                        style={{ background: 'none', border: 'none', color: '#f85149', cursor: 'pointer', fontSize: '12px', fontWeight: '600' }}
                      >
                        ❌ Remove
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

    </main>
  );
}
