import React, { useState, useEffect } from 'react';
import './ComfyWorkspaceTab.css';

const STEPS = [
  { id: 1, label: 'Media Type' },
  { id: 2, label: 'Workflow' },
  { id: 3, label: 'Style & Look' },
  { id: 4, label: 'Prompt & DNA' },
  { id: 5, label: 'Parameters' },
  { id: 6, label: 'Review & Render' }
];

const RESOLUTION_PRESETS = {
  '4K': {
    '16:9': { width: 3840, height: 2160, label: '3840 × 2160 (4K UHD Cinema)' },
    '1:1': { width: 4096, height: 4096, label: '4096 × 4096 (4K Square Master)' },
    '9:16': { width: 2160, height: 3840, label: '2160 × 3840 (4K Vertical / Mobile)' },
    '21:9': { width: 5120, height: 2160, label: '5120 × 2160 (4K Ultrawide Scope)' },
    '4:3': { width: 3840, height: 2880, label: '3840 × 2880 (4K Academy)' }
  },
  '8K': {
    '16:9': { width: 7680, height: 4320, label: '7680 × 4320 (8K Cinema Master)' },
    '1:1': { width: 8192, height: 8192, label: '8192 × 8192 (8K Square Master)' },
    '9:16': { width: 4320, height: 7680, label: '4320 × 7680 (8K Vertical Master)' },
    '21:9': { width: 10240, height: 4320, label: '10240 × 4320 (8K Ultrawide Master)' },
    '4:3': { width: 7680, height: 5760, label: '7680 × 5760 (8K Academy)' }
  },
  '16K': {
    '16:9': { width: 15360, height: 8640, label: '15360 × 8640 (16K Sovereign Large-Format)' },
    '1:1': { width: 16384, height: 16384, label: '16384 × 16384 (16K Canvas Peak)' },
    '9:16': { width: 8640, height: 15360, label: '8640 × 15360 (16K Sovereign Vertical)' },
    '21:9': { width: 16384, height: 6880, label: '16384 × 6880 (16K Ultrawide Panavision)' },
    '4:3': { width: 15360, height: 11520, label: '15360 × 11520 (16K Sovereign Print)' }
  }
};

export default function ComfyWorkspaceTab({ backendUrl = 'http://127.0.0.1:8000' }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [capabilities, setCapabilities] = useState(null);
  const [styles, setStyles] = useState([]);
  const [gallery, setGallery] = useState([]);
  
  // Selection State
  const [mediaType, setMediaType] = useState('image'); // image, video, upscale
  const [selectedTemplate, setSelectedTemplate] = useState('sdxl_txt2img');
  const [selectedStyle, setSelectedStyle] = useState('cinematic_hollywood');
  const [prompt, setPrompt] = useState('A cinematic movie still of an astronaut discovering an ancient crystalline monument on Mars at night, dramatic rim lighting');
  const [negativePrompt, setNegativePrompt] = useState('blurry, low quality, bad anatomy, deformed');
  const [sceneDna, setSceneDna] = useState('');
  const [referenceImage, setReferenceImage] = useState('');
  
  // Technical Parameters - Sovereign 4K Default Mandate
  const [targetResolution, setTargetResolution] = useState('4K'); // 4K, 8K, 16K
  const [aspectRatio, setAspectRatio] = useState('16:9'); // 16:9, 1:1, 9:16, 21:9, 4:3
  const [width, setWidth] = useState(3840);
  const [height, setHeight] = useState(2160);
  const [steps, setSteps] = useState(25);
  const [cfg, setCfg] = useState(7.5);
  const [samplerName, setSamplerName] = useState('euler_ancestral');
  const [scheduler, setScheduler] = useState('karras');
  const [seed, setSeed] = useState(-1);
  const [upscaleDenoise, setUpscaleDenoise] = useState(0.15);

  // Execution State
  const [isRendering, setIsRendering] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Ready');
  const [latestOutput, setLatestOutput] = useState(null);

  // Fetch capabilities & styles on mount
  useEffect(() => {
    fetchCapabilities();
    fetchStyles();
    fetchGallery();
    const interval = setInterval(fetchCapabilities, 12000);
    return () => clearInterval(interval);
  }, [backendUrl]);

  const fetchCapabilities = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/comfyui/workspace/capabilities`);
      if (res.ok) {
        const data = await res.json();
        setCapabilities(data);
      }
    } catch (err) {
      console.error('Capabilities error:', err);
    }
  };

  const fetchStyles = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/comfyui/workspace/styles`);
      if (res.ok) {
        const data = await res.json();
        setStyles(data);
      }
    } catch (err) {
      console.error('Styles error:', err);
    }
  };

  const fetchGallery = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/comfyui/workspace/gallery`);
      if (res.ok) {
        const data = await res.json();
        setGallery(data);
        if (data.length > 0 && !latestOutput) {
          setLatestOutput(data[0]);
        }
      }
    } catch (err) {
      console.error('Gallery error:', err);
    }
  };

  const handleFreeVram = async () => {
    try {
      setStatusMessage('Freeing VRAM cache...');
      await fetch(`${backendUrl}/api/comfyui/workspace/free`, { method: 'POST' });
      fetchCapabilities();
      setStatusMessage('VRAM safely cleared');
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectTier = (tier, aspect = aspectRatio) => {
    setTargetResolution(tier);
    setAspectRatio(aspect);
    const preset = RESOLUTION_PRESETS[tier]?.[aspect] || RESOLUTION_PRESETS['4K']['16:9'];
    setWidth(preset.width);
    setHeight(preset.height);
    setStatusMessage(`Target Output Set: ${tier} (${preset.width}×${preset.height}) [${aspect}]`);
  };

  const handleSelectAspect = (aspect) => {
    setAspectRatio(aspect);
    const preset = RESOLUTION_PRESETS[targetResolution]?.[aspect] || RESOLUTION_PRESETS[targetResolution]['16:9'];
    setWidth(preset.width);
    setHeight(preset.height);
    setStatusMessage(`Aspect Ratio: ${aspect} (${preset.width}×${preset.height}) [${targetResolution}]`);
  };

  const handleRun = async () => {
    setIsRendering(true);
    setStatusMessage('Compiling graph and queueing to ComfyUI...');

    let effectiveRefImage = referenceImage;
    if ((mediaType === 'upscale' || (mediaType === 'video' && selectedTemplate === 'ltx_i2v')) && !effectiveRefImage && gallery.length > 0) {
      effectiveRefImage = gallery[0].filename;
      setReferenceImage(effectiveRefImage);
    }

    try {
      const payload = {
        media_type: mediaType,
        template_id: selectedTemplate,
        prompt: prompt,
        negative_prompt: negativePrompt,
        style_id: selectedStyle,
        scene_dna: sceneDna,
        target_resolution: targetResolution,
        aspect_ratio: aspectRatio,
        width: Number(width),
        height: Number(height),
        steps: Number(steps),
        cfg: Number(cfg),
        sampler_name: samplerName,
        scheduler: scheduler,
        seed: Number(seed),
        reference_image: effectiveRefImage,
        upscale_denoise: Number(upscaleDenoise)
      };

      const res = await fetch(`${backendUrl}/api/comfyui/workspace/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to dispatch workflow');
      }

      const data = await res.json();
      setStatusMessage(`Job Queued (Prompt ID: ${data.prompt_id.slice(0, 8)}...). Denoising on GPU...`);

      // Poll history for completion
      pollCompletion(data.prompt_id);
    } catch (err) {
      setStatusMessage(`Error: ${err.message}`);
      setIsRendering(false);
    }
  };

  const pollCompletion = (promptId) => {
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/comfyui/status/${promptId}`);
        if (res.ok) {
          const statusData = await res.json();
          if (statusData.status === 'completed' && statusData.outputs && statusData.outputs.length > 0) {
            clearInterval(timer);
            setIsRendering(false);
            setStatusMessage('Generation completed successfully!');
            fetchGallery();
            setLatestOutput(statusData.outputs[0]);
          }
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  };

  const handleTriggerGridBlueprint = async () => {
    if (gallery.length < 1) {
      setStatusMessage('Error: Need at least 1 image in output/gallery to create 2x2 grid');
      return;
    }
    try {
      setIsRendering(true);
      setStatusMessage('Stitching recent renders into 2x2 Image Grid...');
      const imagesToGrid = gallery.slice(0, 4).map(g => g.filename);
      const res = await fetch(`${backendUrl}/api/comfyui/workspace/blueprints/grid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ images: imagesToGrid, columns: 2, cell_width: 512, cell_height: 512, padding: 4 })
      });
      if (!res.ok) throw new Error('Failed to dispatch 2x2 grid blueprint');
      const data = await res.json();
      setStatusMessage(`Grid Blueprint Queued (ID: ${data.prompt_id.slice(0, 8)}...).`);
      pollCompletion(data.prompt_id);
    } catch (err) {
      setStatusMessage(`Blueprint Error: ${err.message}`);
      setIsRendering(false);
    }
  };

  const handleTriggerFeatherBlueprint = async () => {
    const targetImage = referenceImage || (gallery.length > 0 ? gallery[0].filename : null);
    if (!targetImage) {
      setStatusMessage('Error: Specify an image or generate one first to feather mask');
      return;
    }
    try {
      setIsRendering(true);
      setStatusMessage(`Applying 12px Mask Feathering to ${targetImage}...`);
      const res = await fetch(`${backendUrl}/api/comfyui/workspace/blueprints/feather`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: targetImage, feather_radius: 12 })
      });
      if (!res.ok) throw new Error('Failed to dispatch feather blueprint');
      const data = await res.json();
      setStatusMessage(`Mask Feather Queued (ID: ${data.prompt_id.slice(0, 8)}...).`);
      pollCompletion(data.prompt_id);
    } catch (err) {
      setStatusMessage(`Blueprint Error: ${err.message}`);
      setIsRendering(false);
    }
  };

  const handleToggleSwitchVariant = () => {
    if (prompt.includes('[A/B Switch: Variant B]')) {
      setPrompt(prev => prev.replace(' [A/B Switch: Variant B]', ' [A/B Switch: Variant A]'));
      setCfg(7.5);
      setStatusMessage('Switched to Variant A (Standard CFG 7.5)');
    } else if (prompt.includes('[A/B Switch: Variant A]')) {
      setPrompt(prev => prev.replace(' [A/B Switch: Variant A]', ' [A/B Switch: Variant B]'));
      setCfg(4.0);
      setStatusMessage('Switched to Variant B (Lumina / DiT CFG 4.0)');
    } else {
      setPrompt(prev => prev + ' [A/B Switch: Variant A]');
      setStatusMessage('Activated A/B Switch Logic (Variant A)');
    }
  };

  const getMediaUrl = (filename) => {
    return `${backendUrl}/api/comfyui/view?filename=${encodeURIComponent(filename)}`;
  };

  return (
    <div className="comfy-workspace">
      {/* Header */}
      <div className="comfy-header">
        <div className="comfy-title-group">
          <h2>AI-BS ComfyUI Sovereign Studio</h2>
          <div className="comfy-subtitle">Multi-Modal Media Generation &amp; 2-Stage Ultra-HD Pipeline</div>
        </div>
        
        <div className={`comfy-gpu-badge ${capabilities?.online ? '' : 'offline'}`}>
          <span>{capabilities?.online ? '● RTX 4090 ONLINE (Port 8189)' : '○ ComfyUI Offline'}</span>
          <button className="btn-free-vram" onClick={handleFreeVram} title="Flush GPU VRAM">
            Flush VRAM
          </button>
        </div>
      </div>

      {/* Stepper Bar */}
      <div className="comfy-stepper">
        {STEPS.map((s) => (
          <button
            key={s.id}
            className={`step-btn ${currentStep === s.id ? 'active' : ''} ${currentStep > s.id ? 'completed' : ''}`}
            onClick={() => setCurrentStep(s.id)}
          >
            <span className="step-num">{s.id}</span>
            {s.label}
          </button>
        ))}
      </div>

      {/* Main Body */}
      <div className="comfy-body">
        {/* Wizard Left Side */}
        <div className="comfy-wizard-panel">
          {/* STEP 1: Media Type */}
          {currentStep === 1 && (
            <div>
              <h3>Step 1: Choose Creation Modality</h3>
              <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Select what type of media you are generating.</p>
              
              <div className="cards-grid">
                <div
                  className={`selectable-card ${mediaType === 'image' ? 'selected' : ''}`}
                  onClick={() => { setMediaType('image'); setSelectedTemplate('sdxl_txt2img'); }}
                >
                  <h4>🖼️ Still Image</h4>
                  <p>Text-to-Image high fidelity generation via SDXL or SD 1.5.</p>
                </div>

                <div
                  className={`selectable-card ${mediaType === 'video' ? 'selected' : ''}`}
                  onClick={() => { setMediaType('video'); setSelectedTemplate('wan_video'); }}
                >
                  <h4>🎬 Ultra-HD Video Motion</h4>
                  <p>Cinematic motion synthesis via Wan2.1 (T2V/I2V) & LTX-Video 2B with 4K/8K/16K scaling.</p>
                </div>

                <div
                  className={`selectable-card ${mediaType === 'upscale' ? 'selected' : ''}`}
                  onClick={() => { setMediaType('upscale'); setSelectedTemplate('two_stage_upscale'); }}
                >
                  <h4>🔍 4K / 8K / 16K Ultra-Refinery</h4>
                  <p>2-Stage spatial GAN model upscaling + tiled micro-texture injection scaled to 4K/8K/16K.</p>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Workflow Template */}
          {currentStep === 2 && (
            <div>
              <h3>Step 2: Select Computational Workflow</h3>
              <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                Only verified, fully-executable node topologies for {mediaType} are shown.
              </p>

              <div className="cards-grid">
                {capabilities?.templates
                  ?.filter((t) => t.media_type === mediaType)
                  .map((tmpl) => (
                    <div
                      key={tmpl.id}
                      className={`selectable-card ${selectedTemplate === tmpl.id ? 'selected' : ''}`}
                      onClick={() => {
                        setSelectedTemplate(tmpl.id);
                        if (tmpl.id === 'z_image_lumina2') {
                          setSteps(20);
                          setCfg(4.0);
                          setSamplerName('euler');
                          setScheduler('normal');
                          setStatusMessage('Loaded Z-Image Lumina 2 NextDiT INT8 parameters (CFG 4.0, Euler)');
                        } else if (tmpl.id === 'sdxl_txt2img') {
                          setSteps(25);
                          setCfg(7.5);
                          setSamplerName('euler_ancestral');
                          setScheduler('karras');
                        } else if (tmpl.id === 'wan_video') {
                          setSteps(25);
                          setCfg(6.0);
                          setStatusMessage('Loaded Wan2.1 Unified Studio parameters (81 frames @ 16fps, 4K/8K/16K Ultra-HD scaling)');
                        } else if (tmpl.id === 'ltx_i2v') {
                          setSteps(25);
                          setCfg(3.0);
                          setStatusMessage('Loaded LTX-Video 2B parameters (97 frames @ 24fps, 4K/8K/16K Ultra-HD scaling)');
                        }
                      }}
                    >
                      <h4>{tmpl.name}</h4>
                      <p>{tmpl.description}</p>
                      <div style={{ marginTop: '8px', fontSize: '0.75rem', color: tmpl.ready ? '#34d399' : '#f87171' }}>
                        {tmpl.ready ? '● Hardware Ready' : '○ Weights Missing'}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* STEP 3: Style & Look */}
          {currentStep === 3 && (
            <div>
              <h3>Step 3: Select Visual Style</h3>
              <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                Styles inject tailored camera sensor parameters, lighting behavior, and contrast tuning.
              </p>

              <div className="cards-grid">
                {styles.map((sty) => (
                  <div
                    key={sty.id}
                    className={`selectable-card ${selectedStyle === sty.id ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedStyle(sty.id);
                      if (sty.cfg) setCfg(sty.cfg);
                      if (sty.steps) setSteps(sty.steps);
                    }}
                  >
                    <h4>{sty.name}</h4>
                    <p style={{ fontSize: '0.75rem' }}>Category: {sty.category}</p>
                    <p style={{ marginTop: '6px', fontStyle: 'italic', fontSize: '0.75rem' }}>
                      "{sty.prompt_prefix.slice(0, 45)}..."
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STEP 4: Prompt & DNA */}
          {currentStep === 4 && (
            <div>
              <h3>Step 4: Prompts &amp; Scene DNA Anchors</h3>
              
              <label className="input-label">Core Creative Prompt</label>
              <textarea
                className="comfy-textarea"
                rows={4}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe your subject, action, lighting, and camera angle..."
              />

              <label className="input-label">Negative Prompt (Suppress Undesired Artifacts)</label>
              <input
                className="comfy-input"
                type="text"
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
              />

              <label className="input-label">Scene DNA (Character / Setting Consistency Anchor)</label>
              <textarea
                className="comfy-textarea"
                rows={2}
                value={sceneDna}
                onChange={(e) => setSceneDna(e.target.value)}
                placeholder="Visual anchor injected across all clips (e.g. house number 246 on brick porch, orange jumpsuit, stadium floodlights)..."
              />

              {(mediaType === 'video' || mediaType === 'upscale') && (
                <div style={{ marginTop: '14px', padding: '12px', background: 'rgba(30, 41, 59, 0.5)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <label className="input-label" style={{ margin: 0 }}>Reference Anchor Image (For Upscaling / Video)</label>
                    {gallery.length > 0 && (
                      <button
                        type="button"
                        className="comfy-btn secondary-btn"
                        style={{ fontSize: '0.72rem', padding: '4px 8px' }}
                        onClick={() => {
                          setReferenceImage(gallery[0].filename);
                          setStatusMessage(`Selected latest render: ${gallery[0].filename}`);
                        }}
                      >
                        ✨ Use Latest Render ({gallery[0].filename.slice(0, 18)}...)
                      </button>
                    )}
                  </div>
                  <input
                    className="comfy-input"
                    type="text"
                    value={referenceImage}
                    onChange={(e) => setReferenceImage(e.target.value)}
                    placeholder="e.g. AIBS_Lumina2_Eagle_00001_.png"
                  />
                  {selectedTemplate === 'wan_video' && (
                    <div style={{ marginTop: '6px', fontSize: '0.74rem', padding: '6px 10px', borderRadius: '6px', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(255,255,255,0.06)' }}>
                      {referenceImage ? (
                        <span style={{ color: '#38bdf8' }}>✨ <strong>Anchor Linked:</strong> Wan2.1 will execute 14B FP8 Image-to-Video motion animation.</span>
                      ) : (
                        <span style={{ color: '#34d399' }}>✨ <strong>No Anchor:</strong> Wan2.1 will execute fast 1.3B Text-to-Video generation.</span>
                      )}
                    </div>
                  )}
                  {gallery.length > 0 && (
                    <div style={{ marginTop: '10px' }}>
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Click any render below to use as anchor:</span>
                      <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', marginTop: '6px', paddingBottom: '4px' }}>
                        {gallery.slice(0, 8).map((item) => (
                          <div
                            key={item.filename}
                            onClick={() => {
                              setReferenceImage(item.filename);
                              setStatusMessage(`Selected anchor: ${item.filename}`);
                            }}
                            style={{
                              flex: '0 0 76px',
                              cursor: 'pointer',
                              borderRadius: '6px',
                              overflow: 'hidden',
                              border: referenceImage === item.filename ? '2px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                              opacity: referenceImage === item.filename ? 1 : 0.75,
                              background: '#0f172a'
                            }}
                          >
                            <img
                              src={getMediaUrl(item.filename)}
                              alt={item.filename}
                              style={{ width: '76px', height: '54px', objectFit: 'cover' }}
                            />
                            <div style={{ fontSize: '0.62rem', padding: '2px 4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: '#cbd5e1' }}>
                              {item.filename}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Quick-Action Blueprint Toolbar (Node Basics) */}
              <div className="blueprint-toolbar-box" style={{ marginTop: '16px', padding: '12px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.35)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#60a5fa' }}>⚡ Modular Blueprint Tools (Node Basics)</span>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>1-Click Subgraphs</span>
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="comfy-btn secondary-btn"
                    style={{ fontSize: '0.78rem', padding: '6px 10px' }}
                    onClick={handleTriggerGridBlueprint}
                    disabled={isRendering}
                  >
                    🔲 2×2 Grid Stitch
                  </button>
                  <button
                    type="button"
                    className="comfy-btn secondary-btn"
                    style={{ fontSize: '0.78rem', padding: '6px 10px' }}
                    onClick={handleTriggerFeatherBlueprint}
                    disabled={isRendering}
                  >
                    🎭 Feather Mask
                  </button>
                  <button
                    type="button"
                    className="comfy-btn secondary-btn"
                    style={{ fontSize: '0.78rem', padding: '6px 10px' }}
                    onClick={handleToggleSwitchVariant}
                  >
                    🔀 A/B Switch Variant
                  </button>
                  <button
                    type="button"
                    className="comfy-btn secondary-btn"
                    style={{ fontSize: '0.78rem', padding: '6px 10px' }}
                    onClick={() => {
                      setPrompt(prev => prev + ', vibrant color grading, high dynamic range cinematic exposure, rich film contrast');
                      setStatusMessage('Applied Color Grading Blueprint');
                    }}
                  >
                    🎨 Color Grade Match
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 5: Parameters */}
          {currentStep === 5 && (
            <div>
              <h3>Step 5: Engine Parameters &amp; Latents</h3>

              {/* Sovereign Ultra-Resolution Output Mandate Card */}
              <div style={{
                background: 'linear-gradient(135deg, rgba(30, 58, 138, 0.45), rgba(15, 23, 42, 0.8))',
                padding: '16px',
                borderRadius: '10px',
                border: '1px solid rgba(59, 130, 246, 0.5)',
                marginBottom: '20px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#60a5fa' }}>
                    🛡️ Sovereign Ultra-HD Output Mandate
                  </span>
                  <span style={{
                    fontSize: '0.75rem',
                    background: 'rgba(56, 189, 248, 0.15)',
                    color: '#38bdf8',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    border: '1px solid rgba(56, 189, 248, 0.3)'
                  }}>
                    {targetResolution} Resolution Locked
                  </span>
                </div>

                <div style={{ marginBottom: '12px' }}>
                  <label className="input-label" style={{ marginBottom: '6px', display: 'block' }}>Output Resolution Tier</label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                    {['4K', '8K', '16K'].map((tier) => (
                      <button
                        key={tier}
                        type="button"
                        className={`comfy-btn ${targetResolution === tier ? 'primary-btn' : 'secondary-btn'}`}
                        style={{
                          padding: '10px 8px',
                          fontWeight: targetResolution === tier ? 'bold' : 'normal',
                          background: targetResolution === tier ? 'linear-gradient(135deg, #2563eb, #1d4ed8)' : 'rgba(30, 41, 59, 0.6)',
                          borderColor: targetResolution === tier ? '#60a5fa' : 'rgba(255,255,255,0.1)'
                        }}
                        onClick={() => handleSelectTier(tier)}
                      >
                        {tier === '4K' && '🌟 4K Ultra-HD'}
                        {tier === '8K' && '🔥 8K Cinema Master'}
                        {tier === '16K' && '⚡ 16K Large-Format'}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ marginBottom: '10px' }}>
                  <label className="input-label" style={{ marginBottom: '6px', display: 'block' }}>Aspect Ratio Framing</label>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {['16:9', '1:1', '9:16', '21:9', '4:3'].map((ar) => (
                      <button
                        key={ar}
                        type="button"
                        className={`comfy-btn ${aspectRatio === ar ? 'primary-btn' : 'secondary-btn'}`}
                        style={{
                          padding: '6px 12px',
                          fontSize: '0.8rem',
                          background: aspectRatio === ar ? '#0284c7' : 'rgba(15, 23, 42, 0.6)',
                          borderColor: aspectRatio === ar ? '#38bdf8' : 'rgba(255,255,255,0.1)'
                        }}
                        onClick={() => handleSelectAspect(ar)}
                      >
                        {ar === '16:9' && '16:9 Cinema'}
                        {ar === '1:1' && '1:1 Square'}
                        {ar === '9:16' && '9:16 Vertical / Reels'}
                        {ar === '21:9' && '21:9 Ultrawide'}
                        {ar === '4:3' && '4:3 Academy'}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{
                  padding: '8px 12px',
                  background: 'rgba(0, 0, 0, 0.35)',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  color: '#94a3b8',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span>Target Dimensions: <strong style={{ color: '#f8fafc' }}>{width} × {height} px</strong></span>
                  <span style={{ color: '#34d399' }}>✓ 4x-UltraSharp Detail Pass Active</span>
                </div>
              </div>

              <div className="sliders-row">
                <div>
                  <label className="input-label">Output Width (px)</label>
                  <input className="comfy-input" type="number" value={width} onChange={(e) => setWidth(e.target.value)} />
                </div>
                <div>
                  <label className="input-label">Output Height (px)</label>
                  <input className="comfy-input" type="number" value={height} onChange={(e) => setHeight(e.target.value)} />
                </div>
              </div>

              <div className="sliders-row">
                <div>
                  <label className="input-label">Sampling Steps ({steps})</label>
                  <input type="range" min="10" max="50" value={steps} onChange={(e) => setSteps(e.target.value)} style={{ width: '100%' }} />
                </div>
                <div>
                  <label className="input-label">CFG Scale ({cfg})</label>
                  <input type="range" min="1.0" max="15.0" step="0.5" value={cfg} onChange={(e) => setCfg(e.target.value)} style={{ width: '100%' }} />
                </div>
              </div>

              <div className="sliders-row">
                <div>
                  <label className="input-label">Sampler</label>
                  <select className="comfy-select" value={samplerName} onChange={(e) => setSamplerName(e.target.value)}>
                    <option value="euler_ancestral">euler_ancestral</option>
                    <option value="euler">euler</option>
                    <option value="dpmpp_2m">dpmpp_2m</option>
                  </select>
                </div>
                <div>
                  <label className="input-label">Scheduler</label>
                  <select className="comfy-select" value={scheduler} onChange={(e) => setScheduler(e.target.value)}>
                    <option value="karras">karras</option>
                    <option value="normal">normal</option>
                    <option value="sgm_uniform">sgm_uniform</option>
                  </select>
                </div>
              </div>

              {mediaType === 'upscale' && (
                <div>
                  <label className="input-label">Tiled Denoise Texture Strength ({upscaleDenoise})</label>
                  <input type="range" min="0.05" max="0.35" step="0.01" value={upscaleDenoise} onChange={(e) => setUpscaleDenoise(e.target.value)} style={{ width: '100%' }} />
                  <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    0.10 to 0.15 is the optimal window to inject micro-textures without altering facial or scene geometry.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* STEP 6: Review & Render */}
          {currentStep === 6 && (
            <div>
              <h3>Step 6: Review &amp; Dispatch</h3>
              <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Verify operational directives before committing GPU compute.</p>

              <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                <p><strong>Modality:</strong> {mediaType.toUpperCase()}</p>
                <p><strong>Workflow:</strong> {selectedTemplate}</p>
                <p><strong>Style:</strong> {selectedStyle}</p>
                <p><strong>Target Output:</strong> <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>{targetResolution} Ultra-HD ({width} × {height} px)</span></p>
                <p><strong>Aspect Framing:</strong> {aspectRatio}</p>
                <p><strong>Neural Pipeline:</strong> Base Latent Generation → 4x-UltraSharp Detail Pass → Precision Lanczos Resampling</p>
                <p><strong>Steps / CFG:</strong> {steps} steps | CFG {cfg}</p>
                <p><strong>Effective Prompt:</strong> {sceneDna ? `${sceneDna} ` : ''}{prompt}</p>
                {(mediaType === 'upscale' || mediaType === 'video') && (
                  <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                    <p>
                      <strong>Reference Anchor:</strong>{' '}
                      <span style={{ color: referenceImage ? '#38bdf8' : '#34d399' }}>
                        {referenceImage || (gallery.length > 0 ? `Auto: ${gallery[0].filename}` : 'None specified')}
                      </span>
                    </p>
                    {(!referenceImage && gallery.length > 0) && (
                      <div style={{ marginTop: '8px' }}>
                        <button
                          type="button"
                          className="comfy-btn secondary-btn"
                          style={{ fontSize: '0.75rem', padding: '6px 12px' }}
                          onClick={() => {
                            setReferenceImage(gallery[0].filename);
                            setStatusMessage(`Selected latest render: ${gallery[0].filename}`);
                          }}
                        >
                          ✨ Lock Latest Render as Anchor ({gallery[0].filename})
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div style={{ marginTop: '20px' }}>
                <button
                  className="btn-primary"
                  style={{ width: '100%', padding: '14px', fontSize: '1rem' }}
                  onClick={handleRun}
                  disabled={isRendering}
                >
                  {isRendering ? '⚡ GPU Computing in Progress...' : '🚀 Queue Pipeline on RTX 4090'}
                </button>
                <p style={{ textAlign: 'center', marginTop: '8px', color: '#38bdf8', fontSize: '0.85rem' }}>
                  {statusMessage}
                </p>
              </div>
            </div>
          )}

          {/* Footer Controls */}
          <div className="wizard-footer">
            <button
              className="btn-secondary"
              disabled={currentStep === 1}
              onClick={() => setCurrentStep(currentStep - 1)}
            >
              ← Previous Step
            </button>
            {currentStep < 6 && (
              <button
                className="btn-primary"
                onClick={() => setCurrentStep(currentStep + 1)}
              >
                Next Step →
              </button>
            )}
          </div>
        </div>

        {/* Right Preview & Gallery Panel */}
        <div className="comfy-preview-panel">
          <div>
            <h4 style={{ margin: '0 0 10px 0' }}>Latest Render Output</h4>
            <div className="preview-stage">
              {latestOutput ? (
                latestOutput.type === 'video' || latestOutput.filename?.endsWith('.mp4') ? (
                  <video
                    src={getMediaUrl(latestOutput.filename)}
                    controls
                    autoPlay
                    loop
                    className="media-render"
                  />
                ) : (
                  <img
                    src={getMediaUrl(latestOutput.filename)}
                    alt="Latest Output"
                    className="media-render"
                  />
                )
              ) : (
                <div style={{ color: '#64748b', textAlign: 'center' }}>
                  <p style={{ fontSize: '2rem', margin: 0 }}>🎨</p>
                  <p>No active output. Queue a job to render.</p>
                </div>
              )}
            </div>
          </div>

          <div>
            <h4 style={{ margin: '0 0 10px 0' }}>Vault Media Gallery</h4>
            <div className="gallery-grid">
              {gallery.map((item, idx) => {
                const fn = item.filename?.toUpperCase() || '';
                const is16K = fn.includes('16K') || item.size_bytes > 50000000;
                const is8K = fn.includes('8K') || item.size_bytes > 20000000;
                const is4K = fn.includes('4K') || item.size_bytes > 8000000;
                const badge = is16K ? '16K' : is8K ? '8K' : is4K ? '4K' : null;
                return (
                  <div key={idx} onClick={() => setLatestOutput(item)} style={{ position: 'relative' }}>
                    {badge && (
                      <span style={{
                        position: 'absolute',
                        top: '4px',
                        left: '4px',
                        background: is16K ? '#ea580c' : is8K ? '#dc2626' : '#2563eb',
                        color: '#fff',
                        fontSize: '0.62rem',
                        fontWeight: 'bold',
                        padding: '1px 5px',
                        borderRadius: '3px',
                        zIndex: 2,
                        letterSpacing: '0.5px'
                      }}>
                        {badge}
                      </span>
                    )}
                    {item.filename?.endsWith('.mp4') ? (
                      <video
                        src={getMediaUrl(item.filename)}
                        className="gallery-thumb"
                      />
                    ) : (
                      <img
                        src={getMediaUrl(item.filename)}
                        alt={item.filename}
                        className="gallery-thumb"
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
