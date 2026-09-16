import React, { useState } from 'react';
import UnrealPixelStreamBridge from './UnrealPixelStreamBridge';
import { Camera, Box, Sparkles, SlidersHorizontal, Download } from 'lucide-react';

export default function BanquetArchitectTab({ backendUrl }) {
  const baseUrl = backendUrl || import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

  const [activeSpace, setActiveSpace] = useState('2d'); // '2d' or '3d'
  const [banquetPrompt, setBanquetPrompt] = useState('');
  const [stylePreset, setStylePreset] = useState('elegant');
  const [errorMsg, setErrorMsg] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [banquetImg, setBanquetImg] = useState('');
  const [showTips, setShowTips] = useState(false);
  const [copiedToolUrl, setCopiedToolUrl] = useState(false);
  const [isGeneratingBeo, setIsGeneratingBeo] = useState(false);
  
  // Media Assistant State
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', text: 'Hello, I am the AI Media Architect. What would you like to design today?' }
  ]);
  const [isChatting, setIsChatting] = useState(false);
  const [isAssistantExpanded, setIsAssistantExpanded] = useState(true);

  // 3D Control States
  const [tableCount, setTableCount] = useState(10);
  const [lightingRig, setLightingRig] = useState('Evening Warm');
  const [floralColor, setFloralColor] = useState('White/Cream');
  const [spawnActors, setSpawnActors] = useState([]);
  const [materialOverride, setMaterialOverride] = useState('Hardwood');
  const [isSyncing3D, setIsSyncing3D] = useState(false);
  const [syncWarning, setSyncWarning] = useState('');
  const [isListening, setIsListening] = useState(false);
  
  // Asset Search State
  const [assetSearchTerm, setAssetSearchTerm] = useState('');
  const [assetSearchResults, setAssetSearchResults] = useState([]);
  const [isSearchingAssets, setIsSearchingAssets] = useState(false);

  const handleAssetSearch = async (term) => {
    setAssetSearchTerm(term);
    if (!term || term.length < 2) {
      setAssetSearchResults([]);
      return;
    }
    setIsSearchingAssets(true);
    try {
      const res = await fetch(`${backendUrl}/api/v1/assets/unreal/search?keyword=${encodeURIComponent(term)}&limit=5`);
      const data = await res.json();
      if (data.status === 'success') {
        setAssetSearchResults(data.results);
      }
    } catch (e) {
      console.error('Asset search failed', e);
    } finally {
      setIsSearchingAssets(false);
    }
  };

  const handleSyncToUnreal = async () => {
    setIsSyncing3D(true);
    setSyncWarning('');
    try {
      const res = await fetch(`${backendUrl}/api/unreal/remote-control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          objectPath: '/Game/Blueprints/BP_BanquetController.Default__BP_BanquetController_C',
          functionName: 'UpdateSceneParams',
          parameters: { tableCount, lightingRig, floralColor, spawnActors, materialOverride }
        })
      });
      const data = await res.json();
      if (data.status === 'warning') {
        setSyncWarning(data.message || 'Unreal Engine is offline.');
      }
    } catch (e) {
      console.error('Failed to sync with Unreal Engine', e);
      setSyncWarning('Failed to connect to backend.');
    } finally {
      setIsSyncing3D(false);
    }
  };

  const handleGenerate2D = async () => {
    if (!banquetPrompt.trim()) return;
    setIsGenerating(true);
    setBanquetImg('');
    setErrorMsg('');
    
    try {
      const res = await fetch(`${backendUrl}/api/v1/demos/noto/banquet-architect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: banquetPrompt, style: stylePreset })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setBanquetImg(data.image_url);
      } else {
        setErrorMsg(data.message || 'Generation failed.');
      }
    } catch (e) {
      setErrorMsg('Failed to connect to backend.');
    } finally {
      setIsGenerating(false);
    }
  };

  const presetStyles = [
    { id: 'elegant', label: 'Classic Elegant' },
    { id: 'tuscan', label: 'Rustic Tuscan' },
    { id: 'modern', label: 'Modern Minimalist' },
    { id: 'corporate', label: 'Corporate Gala' }
  ];



  const toggleActor = (asset) => {
    // Check if it's already in the list by package_path
    const exists = spawnActors.find(a => a.package_path === asset.package_path);
    if (exists) {
      setSpawnActors(prev => prev.filter(a => a.package_path !== asset.package_path));
    } else {
      setSpawnActors(prev => [...prev, {
        id: Math.random().toString(36).substr(2, 9),
        asset_keyword: asset.asset_name,
        asset_name: asset.asset_name,
        package_path: asset.package_path,
        layout_mode: 'engine_procedural' // Default for manual addition
      }]);
    }
  };

  const handleMicClick = () => {
    if (!('webkitSpeechRecognition' in window)) {
      alert("Voice recognition is not supported by your browser.");
      return;
    }
    const recognition = new window.webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsListening(true);
    
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setChatInput(transcript);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error', event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  const handleSendAssistantChat = async () => {
    if (!chatInput.trim() || isChatting) return;
    
    const userText = chatInput.trim();
    setChatInput('');
    setChatHistory(prev => [...prev, { role: 'user', text: userText }]);
    setIsChatting(true);

    try {
      const res = await fetch(`${backendUrl}/api/v1/demos/noto/media-assistant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userText })
      });
      const data = await res.json();
      
      if (data.status === 'success' && data.data) {
        const payload = data.data;
        
        // Add Assistant text
        if (payload.assistant_reply) {
          setChatHistory(prev => [...prev, { role: 'assistant', text: payload.assistant_reply }]);
        }

        // Auto-apply state updates
        if (payload.state_updates) {
          if (payload.state_updates.tableCount !== null) setTableCount(payload.state_updates.tableCount);
          if (payload.state_updates.lightingRig !== null) setLightingRig(payload.state_updates.lightingRig);
          if (payload.state_updates.floralColor !== null) setFloralColor(payload.state_updates.floralColor);
          if (payload.state_updates.stylePreset !== null) setStylePreset(payload.state_updates.stylePreset);
          if (payload.state_updates.spawnActors !== null) setSpawnActors(payload.state_updates.spawnActors);
          if (payload.state_updates.materialOverride !== null) setMaterialOverride(payload.state_updates.materialOverride);
          if (payload.state_updates.prompt2D !== null) setBanquetPrompt(payload.state_updates.prompt2D);
        }

        // Auto-trigger actions
        if (payload.trigger_2d) {
          setActiveSpace('2d');
          // small delay to allow state to settle
          setTimeout(() => handleGenerate2D(), 100);
        }
        
        if (payload.trigger_3d) {
          setActiveSpace('3d');
          setTimeout(() => handleSyncToUnreal(), 100);
        }
      } else {
        setChatHistory(prev => [...prev, { role: 'assistant', text: `Error: ${data.message || 'I encountered an issue processing that.'}` }]);
      }
    } catch (e) {
      setChatHistory(prev => [...prev, { role: 'assistant', text: 'Connection to AI Assistant failed.' }]);
    } finally {
      setIsChatting(false);
    }
  };

  const handleGenerateBeoContract = async () => {
    setIsGeneratingBeo(true);
    try {
      const res = await fetch(`${baseUrl}/api/documents/banquet/generate_beo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_name: 'Noto\'s Grand Wedding & Banquet Celebration',
          client_name: 'Mr. & Mrs. Stehouwer',
          contact_email: 'events@notosoldworld.com',
          contact_phone: '(616) 493-6686',
          event_date: 'Saturday, November 14, 2026',
          event_time: '5:30 PM - 11:30 PM',
          room_name: 'Grand Ballroom & Tuscan Terrace',
          guest_count: tableCount * 10,
          menu_package: 'Plated Prime Filet Mignon & Chilean Sea Bass',
          bar_service: 'Noto\'s Cellar Master Premium Wine Service & Open Bar',
          special_requests: `Custom 3D lighting rig (${lightingRig}), floral design: ${floralColor}.`,
          subtotal: tableCount * 10 * 85.00,
          service_charge: (tableCount * 10 * 85.00) * 0.20,
          tax: (tableCount * 10 * 85.00) * 0.06,
          total: (tableCount * 10 * 85.00) * 1.26,
          deposit_paid: 3500.00,
          balance_due: ((tableCount * 10 * 85.00) * 1.26) - 3500.00
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Notos_Banquet_Event_Order_BEO.docx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        alert('Could not generate Word BEO contract.');
      }
    } catch (e) {
      alert(`BEO generation error: ${e.message}`);
    } finally {
      setIsGeneratingBeo(false);
    }
  };

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#050505',
      color: '#e2e8f0',
      fontFamily: 'sans-serif',
      overflow: 'hidden'
    }}>
      {/* Top Control Bar */}
      <div style={{
        padding: '16px 32px',
        backgroundColor: '#121212',
        borderBottom: '1px solid #333',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        zIndex: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Sparkles color="#d4af37" size={24} />
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f8fafc' }}>
            Banquet Architect <span style={{ color: '#d4af37' }}>Studio</span>
          </h1>
        </div>

        {/* View Toggle & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={handleGenerateBeoContract}
            disabled={isGeneratingBeo}
            style={{
              backgroundColor: '#0d9488',
              color: '#ffffff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 12px rgba(13, 148, 136, 0.3)'
            }}
            title="Download formatted Microsoft Word (.docx) Banquet Event Order & Contract"
          >
            {isGeneratingBeo ? '⏳ Generating BEO...' : '📋 Generate Word BEO (.docx)'}
          </button>

          <div style={{
            display: 'flex',
            backgroundColor: '#1a1a1a',
            borderRadius: '8px',
            padding: '4px',
            border: '1px solid #333'
          }}>
            <button
              onClick={() => setActiveSpace('2d')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 24px',
                backgroundColor: activeSpace === '2d' ? '#2d2d2d' : 'transparent',
                color: activeSpace === '2d' ? '#d4af37' : '#888',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: activeSpace === '2d' ? 'bold' : 'normal',
                transition: 'all 0.2s'
              }}
            >
              <Camera size={18} /> 2D Generative Studio
            </button>
            <button
              onClick={() => setActiveSpace('3d')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 24px',
                backgroundColor: activeSpace === '3d' ? '#2d2d2d' : 'transparent',
                color: activeSpace === '3d' ? '#d4af37' : '#888',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: activeSpace === '3d' ? 'bold' : 'normal',
                transition: 'all 0.2s'
              }}
            >
              <Box size={18} /> 3D Immersive Engine
            </button>
          </div>

          <button
            onClick={() => {
              const url = `${window.location.origin}${window.location.pathname}?tab=banquet_architect`;
              navigator.clipboard.writeText(url).then(() => {
                setCopiedToolUrl(true);
                setTimeout(() => setCopiedToolUrl(false), 2500);
              });
            }}
            style={{
              background: copiedToolUrl ? '#10b981' : 'rgba(212, 175, 55, 0.15)',
              color: copiedToolUrl ? '#ffffff' : '#d4af37',
              border: '1px solid #d4af37',
              padding: '8px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: '700'
            }}
          >
            🔗 {copiedToolUrl ? 'Copied Link!' : 'Share Tool'}
          </button>

          <button
            onClick={() => setShowTips(!showTips)}
            style={{
              background: '#21262d',
              color: '#c9d1d9',
              border: '1px solid #30363d',
              padding: '8px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: '600'
            }}
          >
            💡 {showTips ? 'Hide Tips' : 'Seating Guide'}
          </button>
        </div>
      </div>

      {/* In-Tab Guidance Accordion */}
      {showTips && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.95) 100%)',
          borderBottom: '1px solid rgba(212, 175, 55, 0.35)',
          borderLeft: '4px solid #d4af37',
          padding: '12px 24px',
          color: '#cbd5e1',
          fontSize: '0.82rem',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '12px'
        }}>
          <div style={{ background: '#0f172a', padding: '10px 14px', borderRadius: '8px', border: '1px solid #334155' }}>
            <strong style={{ color: '#d4af37', display: 'block', marginBottom: '4px' }}>🏛️ 60" Aisle Clearance:</strong>
            <span style={{ color: '#94a3b8' }}>Maintain 60 inches between all round table perimeters for fire exit compliance and banquet cart maneuvering.</span>
          </div>
          <div style={{ background: '#0f172a', padding: '10px 14px', borderRadius: '8px', border: '1px solid #334155' }}>
            <strong style={{ color: '#d4af37', display: 'block', marginBottom: '4px' }}>👑 VIP Affinity Solver:</strong>
            <span style={{ color: '#94a3b8' }}>The AI auto-arranges key donors, wedding party, and corporate executives within direct line-of-sight of the podium/head table.</span>
          </div>
          <div style={{ background: '#0f172a', padding: '10px 14px', borderRadius: '8px', border: '1px solid #334155' }}>
            <strong style={{ color: '#d4af37', display: 'block', marginBottom: '4px' }}>🎮 3D Unreal Engine Sync:</strong>
            <span style={{ color: '#94a3b8' }}>Switch to 3D Immersive Engine to spawn dynamic table actors, chandeliers, and floral centerpieces live in Unreal Engine 5.8.</span>
          </div>
        </div>
      )}

      {/* Main Workspace Area */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        
        {/* 2D Generative Studio Workspace */}
        {activeSpace === '2d' && (
          <div style={{ display: 'flex', height: '100%', width: '100%' }}>
            {/* 2D Settings Panel */}
            <div style={{
              width: '350px',
              backgroundColor: '#0a0a0a',
              borderRight: '1px solid #222',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '24px',
              overflowY: 'auto'
            }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', marginBottom: '12px', fontSize: '0.9rem', fontWeight: 'bold' }}>
                  <SlidersHorizontal size={16} /> STYLE PRESET
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  {presetStyles.map(preset => (
                    <button
                      key={preset.id}
                      onClick={() => setStylePreset(preset.id)}
                      style={{
                        padding: '12px 8px',
                        backgroundColor: stylePreset === preset.id ? 'rgba(212, 175, 55, 0.15)' : '#111',
                        border: stylePreset === preset.id ? '1px solid #d4af37' : '1px solid #333',
                        color: stylePreset === preset.id ? '#d4af37' : '#94a3b8',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        transition: 'all 0.2s'
                      }}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ display: 'block', color: '#94a3b8', marginBottom: '12px', fontSize: '0.9rem', fontWeight: 'bold' }}>
                  SCENE DESCRIPTION
                </label>
                <textarea
                  value={banquetPrompt}
                  onChange={(e) => setBanquetPrompt(e.target.value)}
                  placeholder="Describe the banquet layout, floral arrangements, lighting, and table settings..."
                  style={{
                    width: '100%',
                    height: '160px',
                    backgroundColor: '#111',
                    border: '1px solid #333',
                    borderRadius: '8px',
                    padding: '12px',
                    color: '#f8fafc',
                    resize: 'none',
                    outline: 'none',
                    fontFamily: 'inherit',
                    lineHeight: '1.5'
                  }}
                />
              </div>

              <button
                onClick={handleGenerate2D}
                disabled={isGenerating || !banquetPrompt.trim()}
                style={{
                  backgroundColor: isGenerating || !banquetPrompt.trim() ? '#333' : '#d4af37',
                  color: isGenerating || !banquetPrompt.trim() ? '#888' : '#000',
                  padding: '16px',
                  borderRadius: '8px',
                  border: 'none',
                  fontWeight: 'bold',
                  fontSize: '1rem',
                  cursor: isGenerating || !banquetPrompt.trim() ? 'not-allowed' : 'pointer',
                  marginTop: 'auto',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: isGenerating || !banquetPrompt.trim() ? 'none' : '0 4px 12px rgba(212, 175, 55, 0.3)'
                }}
              >
                {isGenerating ? 'RENDERING...' : 'GENERATE 2D RENDER'}
              </button>
            </div>

            {/* 2D Render Canvas */}
            <div style={{
              flex: 1,
              backgroundColor: '#000',
              backgroundImage: 'radial-gradient(#222 1px, transparent 0)',
              backgroundSize: '40px 40px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '48px',
              position: 'relative'
            }}>
              {errorMsg && (
                <div style={{ position: 'absolute', top: '24px', left: '50%', transform: 'translateX(-50%)', backgroundColor: 'rgba(220, 38, 38, 0.9)', color: 'white', padding: '12px 24px', borderRadius: '8px', fontWeight: 'bold' }}>
                  {errorMsg}
                </div>
              )}
              
              {!banquetImg && !isGenerating && (
                <div style={{ color: '#555', textAlign: 'center', fontFamily: 'serif' }}>
                  <Sparkles size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
                  <h2>Studio Canvas Empty</h2>
                  <p>Configure parameters on the left and initialize rendering.</p>
                </div>
              )}

              {isGenerating && (
                <div style={{ color: '#d4af37', textAlign: 'center', fontFamily: 'serif', animation: 'pulse 2s infinite' }}>
                  <div style={{ width: '64px', height: '64px', border: '4px solid #333', borderTop: '4px solid #d4af37', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 24px' }} />
                  <h2>Synthesizing Spatial Geometry...</h2>
                  <p style={{ opacity: 0.7 }}>Awaiting tensor return from ComfyUI Bridge</p>
                </div>
              )}

              {banquetImg && !isGenerating && (
                <div style={{ position: 'relative', maxWidth: '100%', maxHeight: '100%', boxShadow: '0 20px 50px rgba(0,0,0,0.8)', border: '1px solid #333', borderRadius: '4px', overflow: 'hidden' }}>
                  <img src={banquetImg} alt="Render" style={{ display: 'block', maxWidth: '100%', maxHeight: 'calc(100vh - 200px)', objectFit: 'contain' }} />
                  <a href={banquetImg} download="Banquet_Render.png" style={{ position: 'absolute', bottom: '16px', right: '16px', backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', padding: '8px 16px', borderRadius: '6px', color: '#fff', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid rgba(255,255,255,0.2)', transition: 'background 0.2s' }}>
                    <Download size={16} /> Download High-Res
                  </a>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 3D Immersive Environment Workspace */}
        {activeSpace === '3d' && (
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* The Pixel Stream Bridge takes over */}
            <div style={{ flex: 1, padding: '16px', backgroundColor: '#000' }}>
              <div style={{ width: '100%', height: '100%', borderRadius: '12px', overflow: 'hidden', border: '1px solid #333', position: 'relative' }}>
                <UnrealPixelStreamBridge 
                  title="Unreal Engine 5.8 | Live Banquet Interaction" 
                  port="8888" 
                  height="100%" 
                  backendUrl={backendUrl}
                />
                
                {/* Overlay Instructions */}
                <div style={{ position: 'absolute', bottom: '24px', left: '24px', backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', color: '#a3a3a3', fontSize: '0.85rem', maxWidth: '300px' }}>
                  <h4 style={{ color: '#fff', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}><Box size={14}/> Client Navigation</h4>
                  <ul style={{ margin: 0, paddingLeft: '16px' }}>
                    <li><strong>WASD:</strong> Walk</li>
                    <li><strong>Right Click + Drag:</strong> Look</li>
                    <li><strong>Scroll:</strong> Zoom</li>
                  </ul>
                </div>
                
                {syncWarning && (
                  <div style={{ position: 'absolute', top: '24px', left: '50%', transform: 'translateX(-50%)', backgroundColor: 'rgba(212, 175, 55, 0.9)', color: '#000', padding: '12px 24px', borderRadius: '8px', fontWeight: 'bold', zIndex: 50, boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
                    {syncWarning}
                  </div>
                )}

                {/* Interactive Remote Control Panel */}
                <div style={{ position: 'absolute', top: '80px', right: '24px', backgroundColor: 'rgba(10, 10, 10, 0.85)', backdropFilter: 'blur(12px)', padding: '24px', borderRadius: '12px', border: '1px solid rgba(212, 175, 55, 0.3)', width: '300px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <h3 style={{ margin: 0, color: '#d4af37', fontFamily: 'serif', fontSize: '1.25rem', borderBottom: '1px solid #333', paddingBottom: '12px' }}>Scene Controller</h3>
                  
                  <div>
                    <label style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '8px' }}>
                      <span>Table Count</span>
                      <span style={{ color: '#d4af37' }}>{tableCount}</span>
                    </label>
                    <input type="range" min="5" max="30" value={tableCount} onChange={(e) => setTableCount(e.target.value)} style={{ width: '100%', accentColor: '#d4af37' }} />
                  </div>

                  <div>
                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '8px' }}>Lighting Rig</label>
                    <select value={lightingRig} onChange={(e) => setLightingRig(e.target.value)} style={{ width: '100%', backgroundColor: '#111', border: '1px solid #333', color: '#f8fafc', padding: '8px', borderRadius: '4px', outline: 'none' }}>
                      <option>Daylight Bright</option>
                      <option>Evening Warm</option>
                      <option>Intimate Candlelight</option>
                      <option>Corporate Cool</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '8px' }}>Floral Arrangements</label>
                    <select value={floralColor} onChange={(e) => setFloralColor(e.target.value)} style={{ width: '100%', backgroundColor: '#111', border: '1px solid #333', color: '#f8fafc', padding: '8px', borderRadius: '4px', outline: 'none' }}>
                      <option>White/Cream</option>
                      <option>Tuscan Red/Gold</option>
                      <option>Blush Pink</option>
                      <option>Minimalist Greenery</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '8px' }}>Global Asset Search</label>
                    <div style={{ position: 'relative' }}>
                      <input 
                        type="text" 
                        value={assetSearchTerm}
                        onChange={(e) => handleAssetSearch(e.target.value)}
                        placeholder="Search Unreal Registry (e.g. Chair, Marble)"
                        style={{ width: '100%', backgroundColor: '#111', border: '1px solid #333', color: '#f8fafc', padding: '8px', borderRadius: '4px', outline: 'none' }}
                      />
                      {assetSearchResults.length > 0 && (
                        <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, backgroundColor: '#161616', border: '1px solid #333', borderRadius: '4px', zIndex: 200, maxHeight: '200px', overflowY: 'auto', marginTop: '4px' }}>
                          {assetSearchResults.map(asset => (
                            <div key={asset.id} style={{ padding: '8px', borderBottom: '1px solid #222', fontSize: '0.8rem', cursor: 'pointer' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ color: '#d4af37', fontWeight: 'bold' }}>{asset.asset_name}</span>
                                <span style={{ color: '#888', fontSize: '0.7rem' }}>{asset.asset_type}</span>
                              </div>
                              <div style={{ color: '#555', fontSize: '0.7rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{asset.package_path}</div>
                              <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                                <button onClick={() => { setMaterialOverride(asset.asset_name); setAssetSearchResults([]); setAssetSearchTerm(''); }} style={{ flex: 1, backgroundColor: '#222', color: '#ccc', border: '1px solid #444', borderRadius: '4px', padding: '4px', fontSize: '0.7rem', cursor: 'pointer' }}>Use as Material</button>
                                <button onClick={() => { toggleActor(asset); setAssetSearchResults([]); setAssetSearchTerm(''); }} style={{ flex: 1, backgroundColor: 'rgba(212, 175, 55, 0.2)', color: '#d4af37', border: '1px solid #d4af37', borderRadius: '4px', padding: '4px', fontSize: '0.7rem', cursor: 'pointer' }}>Add to Scene</button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '8px' }}>Floor Material Override</label>
                    <input type="text" value={materialOverride} onChange={(e) => setMaterialOverride(e.target.value)} style={{ width: '100%', backgroundColor: '#111', border: '1px solid #333', color: '#f8fafc', padding: '8px', borderRadius: '4px', outline: 'none' }} />
                  </div>

                  <div>
                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '8px' }}>Active Spawn Actors</label>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {spawnActors.length === 0 && <span style={{ color: '#555', fontSize: '0.8rem' }}>None Selected</span>}
                      {spawnActors.map(actor => (
                        <div key={actor.id || actor.package_path || Math.random()} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#000', backgroundColor: '#d4af37', padding: '4px 8px', borderRadius: '12px' }}>
                          <span style={{ fontWeight: 'bold' }}>{actor.asset_name || actor.asset_keyword}</span>
                          <span style={{ fontSize: '0.65rem', backgroundColor: 'rgba(0,0,0,0.2)', padding: '2px 4px', borderRadius: '4px' }}>
                            {actor.layout_mode === 'ai_transform' ? '🤖 AI Layout' : '⚙️ Engine Layout'}
                          </span>
                          <button onClick={() => toggleActor(actor)} style={{ background: 'transparent', border: 'none', color: '#000', cursor: 'pointer', padding: 0, marginLeft: '4px', fontWeight: 'bold' }}>×</button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <button 
                    onClick={handleSyncToUnreal}
                    disabled={isSyncing3D}
                    style={{
                      backgroundColor: isSyncing3D ? '#333' : 'rgba(212, 175, 55, 0.2)',
                      color: isSyncing3D ? '#888' : '#d4af37',
                      border: isSyncing3D ? '1px solid #444' : '1px solid #d4af37',
                      padding: '12px',
                      borderRadius: '6px',
                      cursor: isSyncing3D ? 'not-allowed' : 'pointer',
                      fontWeight: 'bold',
                      transition: 'all 0.2s',
                      marginTop: '8px'
                    }}
                  >
                    {isSyncing3D ? 'SYNCING DATA...' : 'PUSH TO 3D STUDIO'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Floating AI Media Assistant Panel */}
      <div style={{
        position: 'absolute',
        bottom: '24px',
        left: '24px',
        width: '380px',
        backgroundColor: 'rgba(10, 10, 10, 0.9)',
        backdropFilter: 'blur(12px)',
        borderRadius: '12px',
        border: '1px solid rgba(212, 175, 55, 0.4)',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
        zIndex: 100,
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div 
          onClick={() => setIsAssistantExpanded(!isAssistantExpanded)}
          style={{ 
            padding: '12px 16px', 
            backgroundColor: '#161616', 
            borderBottom: isAssistantExpanded ? '1px solid #333' : 'none', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            cursor: 'pointer' 
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="#d4af37" />
            <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontFamily: 'serif' }}>AI Media Assistant</h4>
          </div>
          <div style={{ color: '#888', fontSize: '0.8rem' }}>{isAssistantExpanded ? '▼' : '▲'}</div>
        </div>

        {/* Chat Body */}
        {isAssistantExpanded && (
          <>
            <div style={{ height: '300px', overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {chatHistory.map((msg, i) => (
                <div key={i} style={{ 
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  backgroundColor: msg.role === 'user' ? 'rgba(212, 175, 55, 0.15)' : '#222',
                  border: msg.role === 'user' ? '1px solid rgba(212, 175, 55, 0.3)' : '1px solid #333',
                  padding: '10px 14px',
                  borderRadius: '12px',
                  borderBottomRightRadius: msg.role === 'user' ? '2px' : '12px',
                  borderBottomLeftRadius: msg.role === 'assistant' ? '2px' : '12px',
                  maxWidth: '85%',
                  fontSize: '0.9rem',
                  color: '#e2e8f0',
                  lineHeight: '1.4'
                }}>
                  {msg.text}
                </div>
              ))}
              {isChatting && (
                <div style={{ alignSelf: 'flex-start', color: '#888', fontSize: '0.85rem', fontStyle: 'italic' }}>
                  Architect is thinking...
                </div>
              )}
            </div>

            {/* Chat Input */}
            <div style={{ padding: '12px', backgroundColor: '#111', display: 'flex', gap: '8px' }}>
              <button
                onClick={handleMicClick}
                title="Use Voice Transcription"
                style={{
                  backgroundColor: isListening ? '#ef4444' : 'transparent',
                  color: isListening ? '#fff' : '#888',
                  border: isListening ? 'none' : '1px solid #333',
                  padding: '0 12px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.2s'
                }}
              >
                🎤
              </button>
              <input 
                type="text" 
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendAssistantChat()}
                placeholder={isListening ? "Listening..." : "e.g. Set up a corporate gala with 25 tables..."}
                disabled={isChatting || isListening}
                style={{ 
                  flex: 1, 
                  backgroundColor: '#0a0a0a', 
                  border: '1px solid #333', 
                  color: '#f8fafc', 
                  padding: '10px 12px', 
                  borderRadius: '6px', 
                  outline: 'none',
                  fontSize: '0.9rem'
                }}
              />
              <button 
                onClick={handleSendAssistantChat}
                disabled={isChatting}
                style={{
                  backgroundColor: 'rgba(212, 175, 55, 0.2)',
                  color: '#d4af37',
                  border: '1px solid #d4af37',
                  padding: '0 16px',
                  borderRadius: '6px',
                  cursor: isChatting ? 'not-allowed' : 'pointer'
                }}
              >
                Send
              </button>
            </div>
          </>
        )}
      </div>
      <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
      `}</style>
    </div>
  );
}
