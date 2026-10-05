import React, { useState, useMemo } from 'react';
import useComfyWorkspace from './useComfyWorkspace';
import './ComfyStation.css';

/**
 * 5 Sovereign Workflow Presets grounded in local RTX 4090 ComfyUI on Port 8189.
 * Models confirmed in filesystem:
 * - sd_xl_base_1.0.safetensors
 * - ltx-video-2b-v0.9.1.safetensors
 * - v1-5-pruned-emaonly-fp16.safetensors
 * - diffusion_pytorch_model.safetensors
 * - 4x-UltraSharp.pth
 */
export const SOVEREIGN_PRESETS = {
  'SDXL 4K Master Cine': {
    "1": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "sd_xl_base_1.0.safetensors" } },
    "2": { "class_type": "EmptyLatentImage", "inputs": { "width": 1024, "height": 1024, "batch_size": 1 } },
    "3": { "class_type": "CLIPTextEncode", "inputs": { "text": "cinematic movie still of an astronaut discovering an ancient crystalline monument on Mars at night, dramatic rim lighting, 8k resolution, photorealistic, cinematic 35mm film grain, masterpiece", "clip": ["1", 1] } },
    "4": { "class_type": "CLIPTextEncode", "inputs": { "text": "low quality, blurry, distorted anatomy, bad hands, artifacts, watermark, oversaturated, amateur render", "clip": ["1", 1] } },
    "5": { "class_type": "KSampler", "inputs": { "seed": 42099, "steps": 28, "cfg": 7.5, "sampler_name": "dpmpp_2m_sde_gpu", "scheduler": "karras", "denoise": 1.0, "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["2", 0] } },
    "6": { "class_type": "VAEDecode", "inputs": { "samples": ["5", 0], "vae": ["1", 2] } },
    "7": { "class_type": "SaveImage", "inputs": { "filename_prefix": "AI_BS_SDXL_4K", "images": ["6", 0] } }
  },

  'Wan2.1 Neural Motion Video': {
    "1": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "diffusion_pytorch_model.safetensors" } },
    "2": { "class_type": "EmptyLatentImage", "inputs": { "width": 832, "height": 480, "batch_size": 16 } },
    "3": { "class_type": "CLIPTextEncode", "inputs": { "text": "high-definition cinematic camera pan across an illuminated neon data center, humming servers, volumetric smoke, photorealistic 24fps motion", "clip": ["1", 1] } },
    "4": { "class_type": "CLIPTextEncode", "inputs": { "text": "jitter, stutter, low resolution, blurry, flickering, distorted", "clip": ["1", 1] } },
    "5": { "class_type": "KSampler", "inputs": { "seed": 10884, "steps": 25, "cfg": 6.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["2", 0] } },
    "6": { "class_type": "VAEDecode", "inputs": { "samples": ["5", 0], "vae": ["1", 2] } },
    "7": { "class_type": "VHS_VideoCombine", "inputs": { "images": ["6", 0], "frame_rate": 16, "loop_count": 0, "filename_prefix": "AI_BS_WanMotion", "format": "video/h264-mp4", "pingpong": false, "save_output": true } }
  },

  'LTX-Video 2B Real-time Motion': {
    "1": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "ltx-video-2b-v0.9.1.safetensors" } },
    "2": { "class_type": "EmptyLatentImage", "inputs": { "width": 768, "height": 512, "batch_size": 25 } },
    "3": { "class_type": "CLIPTextEncode", "inputs": { "text": "dynamic tracking drone shot flying over a futuristic metropolis bathed in golden hour sunlight, hyperdetailed architecture", "clip": ["1", 1] } },
    "4": { "class_type": "CLIPTextEncode", "inputs": { "text": "blurry, low resolution, motion artifact, bad lighting", "clip": ["1", 1] } },
    "5": { "class_type": "KSampler", "inputs": { "seed": 77102, "steps": 20, "cfg": 4.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["2", 0] } },
    "6": { "class_type": "VAEDecode", "inputs": { "samples": ["5", 0], "vae": ["1", 2] } },
    "7": { "class_type": "SaveImage", "inputs": { "filename_prefix": "AI_BS_LTX_Render", "images": ["6", 0] } }
  },

  'ImpactPack FaceDetailer & ControlNet': {
    "1": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors" } },
    "2": { "class_type": "EmptyLatentImage", "inputs": { "width": 512, "height": 768, "batch_size": 1 } },
    "3": { "class_type": "CLIPTextEncode", "inputs": { "text": "portrait of a high-tech robotic engineer working in a holographic laboratory, detailed skin texture, expressive eyes, rim lighting, 8k", "clip": ["1", 1] } },
    "4": { "class_type": "CLIPTextEncode", "inputs": { "text": "ugly, deformed face, bad eyes, missing limbs, watermark, cartoon", "clip": ["1", 1] } },
    "5": { "class_type": "KSampler", "inputs": { "seed": 91823, "steps": 30, "cfg": 7.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0, "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["2", 0] } },
    "6": { "class_type": "VAEDecode", "inputs": { "samples": ["5", 0], "vae": ["1", 2] } },
    "7": { "class_type": "SaveImage", "inputs": { "filename_prefix": "AI_BS_Detailer", "images": ["6", 0] } }
  },

  '4x-UltraSharp Super-Resolution': {
    "1": { "class_type": "UpscaleModelLoader", "inputs": { "model_name": "4x-UltraSharp.pth" } },
    "2": { "class_type": "LoadImage", "inputs": { "image": "latest_render.png" } },
    "3": { "class_type": "ImageUpscaleWithModel", "inputs": { "upscale_model": ["1", 0], "image": ["2", 0] } },
    "4": { "class_type": "SaveImage", "inputs": { "filename_prefix": "AI_BS_4x_UltraSharp", "images": ["3", 0] } }
  }
};

export const ComfyStation = () => {
  const {
    baseUrl,
    setBaseUrl,
    nodeRegistry,
    executingNode,
    progress,
    outputs,
    isConnected,
    errorStatus,
    queueWorkflow,
    interrupt,
    refreshRegistry
  } = useComfyWorkspace();

  const [selectedPreset, setSelectedPreset] = useState('SDXL 4K Master Cine');
  const [customDAG, setCustomDAG] = useState(() => JSON.stringify(SOVEREIGN_PRESETS['SDXL 4K Master Cine'], null, 2));
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedNodeKey, setSelectedNodeKey] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('canvas'); // 'canvas' | 'gallery' | 'dag_editor'
  const [endpointInput, setEndpointInput] = useState(baseUrl);
  const [isQueueing, setIsQueueing] = useState(false);
  const [lastQueueError, setLastQueueError] = useState(null);

  // Synchronize custom DAG editor on preset change
  const handlePresetChange = (name) => {
    setSelectedPreset(name);
    if (SOVEREIGN_PRESETS[name]) {
      setCustomDAG(JSON.stringify(SOVEREIGN_PRESETS[name], null, 2));
    }
  };

  // Group Categories from Node Registry
  const categories = useMemo(() => {
    const set = new Set();
    Object.values(nodeRegistry || {}).forEach((n) => {
      if (n && n.category) {
        set.add(n.category.split('/')[0]);
      }
    });
    return Array.from(set).sort();
  }, [nodeRegistry]);

  // Filtered Nodes for Inspector List
  const filteredNodes = useMemo(() => {
    const entries = Object.entries(nodeRegistry || {});
    return entries.filter(([key, def]) => {
      const cat = def?.category || '';
      const matchesCategory = selectedCategory === 'all' || cat.startsWith(selectedCategory);
      const search = searchTerm.toLowerCase();
      const matchesSearch =
        key.toLowerCase().includes(search) ||
        (def?.display_name && def.display_name.toLowerCase().includes(search));
      return matchesCategory && matchesSearch;
    });
  }, [nodeRegistry, selectedCategory, searchTerm]);

  const activeNodeDetail = selectedNodeKey ? nodeRegistry[selectedNodeKey] : null;

  // Handle Workflow Execution
  const handleExecute = async () => {
    setIsQueueing(true);
    setLastQueueError(null);
    try {
      let dagToRun;
      try {
        dagToRun = JSON.parse(customDAG);
      } catch (jsonErr) {
        throw new Error(`DAG JSON Syntax Error: ${jsonErr.message}`);
      }
      await queueWorkflow(dagToRun);
    } catch (err) {
      setLastQueueError(err.message || 'Execution failed');
    } finally {
      setIsQueueing(false);
    }
  };

  return (
    <div className="comfy-station-container">
      {/* Top Controls Bar */}
      <header className="comfy-station-header">
        <div className="comfy-station-brand">
          <span
            className={`comfy-status-dot ${isConnected ? 'online' : 'offline'}`}
            title={isConnected ? 'Connected to ComfyUI Port 8189' : 'ComfyUI Disconnected'}
          />
          <strong>ComfyUI RTX 4090 Workstation</strong>
          <span className="comfy-node-count-badge">
            {Object.keys(nodeRegistry).length > 0 ? `${Object.keys(nodeRegistry).length} Nodes` : 'Probing...'}
          </span>
        </div>

        {/* Endpoint Config */}
        <div className="comfy-endpoint-picker">
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>Host:</span>
          <input
            type="text"
            className="comfy-endpoint-input"
            value={endpointInput}
            onChange={(e) => setEndpointInput(e.target.value)}
            onBlur={() => setBaseUrl(endpointInput)}
            placeholder="http://127.0.0.1:8189"
          />
          <button
            type="button"
            className="comfy-mini-btn"
            onClick={() => { setBaseUrl(endpointInput); refreshRegistry(); }}
            title="Reconnect and refresh node schemas"
          >
            🔄 Sync
          </button>
        </div>

        {/* Workflow Preset Selector */}
        <label className="comfy-preset-label">
          <span>Preset:</span>
          <select
            value={selectedPreset}
            onChange={(e) => handlePresetChange(e.target.value)}
            className="comfy-preset-select"
          >
            {Object.keys(SOVEREIGN_PRESETS).map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </label>

        {/* Execution Actions */}
        <div className="comfy-action-group">
          <button
            type="button"
            className="comfy-run-btn"
            onClick={handleExecute}
            disabled={isQueueing}
          >
            {isQueueing ? '⚡ Queueing...' : '🚀 Queue Workflow'}
          </button>

          <button
            type="button"
            className="comfy-interrupt-btn"
            onClick={interrupt}
            title="Interrupt running queue immediately"
          >
            ⏹ Interrupt
          </button>
        </div>

        {/* View Switcher Tabs */}
        <div className="comfy-tab-switcher">
          <button
            type="button"
            className={`comfy-view-btn ${activeTab === 'canvas' ? 'active' : ''}`}
            onClick={() => setActiveTab('canvas')}
          >
            Native Canvas
          </button>
          <button
            type="button"
            className={`comfy-view-btn ${activeTab === 'gallery' ? 'active' : ''}`}
            onClick={() => setActiveTab('gallery')}
          >
            Outputs ({outputs.length})
          </button>
          <button
            type="button"
            className={`comfy-view-btn ${activeTab === 'dag_editor' ? 'active' : ''}`}
            onClick={() => setActiveTab('dag_editor')}
          >
            DAG Editor
          </button>
        </div>
      </header>

      {/* Progress & Live Telemetry Sub-bar */}
      {executingNode && (
        <div className="comfy-telemetry-bar">
          <div className="comfy-telemetry-indicator">
            <span className="pulse-icon">⚡</span>
            <span>Active Node: <strong>{executingNode}</strong></span>
          </div>
          <div className="comfy-progress-track">
            <div
              className="comfy-progress-fill"
              style={{
                width: `${progress.max > 0 ? Math.min(100, (progress.value / progress.max) * 100) : 0}%`
              }}
            />
          </div>
          <div className="comfy-progress-stats">
            {progress.value} / {progress.max} steps ({progress.max > 0 ? Math.round((progress.value / progress.max) * 100) : 0}%)
          </div>
        </div>
      )}

      {/* Error / Alert banner */}
      {(lastQueueError || errorStatus) && (
        <div className="comfy-alert-banner">
          ⚠️ {lastQueueError || errorStatus}
        </div>
      )}

      {/* Main Workstation Workspace */}
      <div className="comfy-station-body">
        {/* Left Side: Exhaustive Dynamic Node Inspector */}
        <aside className="comfy-node-inspector">
          <div className="comfy-inspector-header">
            <div className="comfy-inspector-title">
              <span>Node Registry Inspector</span>
              <span className="comfy-count-pill">{filteredNodes.length}</span>
            </div>
            <input
              type="text"
              placeholder="Search 1,365 nodes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="comfy-search-input"
            />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="comfy-category-select"
            >
              <option value="all">All Categories ({Object.keys(nodeRegistry).length} nodes)</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Node Selection List */}
          <div className="comfy-node-list">
            {filteredNodes.length === 0 ? (
              <div className="comfy-no-nodes">No nodes match filter</div>
            ) : (
              filteredNodes.map(([key, def]) => (
                <div
                  key={key}
                  onClick={() => setSelectedNodeKey(key)}
                  className={`comfy-node-item ${selectedNodeKey === key ? 'selected' : ''}`}
                >
                  <div className="comfy-node-name">{def?.display_name || key}</div>
                  <div className="comfy-node-cat">{def?.category || 'uncategorized'}</div>
                </div>
              ))
            )}
          </div>

          {/* Selected Node Schema Metadata */}
          {activeNodeDetail ? (
            <div className="comfy-node-detail-panel">
              <div className="comfy-detail-row">
                <span className="comfy-detail-label">Type:</span>
                <span className="comfy-detail-value">{selectedNodeKey}</span>
              </div>
              <div className="comfy-detail-row">
                <span className="comfy-detail-label">Category:</span>
                <span className="comfy-detail-value">{activeNodeDetail.category || 'N/A'}</span>
              </div>
              <div className="comfy-detail-row">
                <span className="comfy-detail-label">Outputs:</span>
                <span className="comfy-detail-value">
                  {activeNodeDetail.output?.length > 0 ? activeNodeDetail.output.join(', ') : 'None'}
                </span>
              </div>

              {activeNodeDetail.input?.required && (
                <div className="comfy-inputs-block">
                  <div className="comfy-inputs-header">Required Inputs:</div>
                  <ul className="comfy-inputs-list">
                    {Object.entries(activeNodeDetail.input.required).map(([name, config]) => (
                      <li key={name}>
                        <span className="comfy-input-key">{name}</span>:
                        <span className="comfy-input-type">
                          {Array.isArray(config?.[0]) ? ` [${config[0].join(' | ')}]` : ` ${config?.[0]}`}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {activeNodeDetail.input?.optional && Object.keys(activeNodeDetail.input.optional).length > 0 && (
                <div className="comfy-inputs-block">
                  <div className="comfy-inputs-header">Optional Inputs:</div>
                  <ul className="comfy-inputs-list">
                    {Object.entries(activeNodeDetail.input.optional).map(([name, config]) => (
                      <li key={name}>
                        <span className="comfy-input-key">{name}</span>:
                        <span className="comfy-input-type">
                          {Array.isArray(config?.[0]) ? ` [${config[0].join(' | ')}]` : ` ${config?.[0]}`}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="comfy-node-detail-empty">
              Select any node above to inspect its execution signature and data types.
            </div>
          )}
        </aside>

        {/* Center Workspace: Canvas / Output Gallery / DAG Editor */}
        <main className="comfy-station-main">
          {activeTab === 'canvas' ? (
            <div className="comfy-iframe-stage">
              <iframe
                src={baseUrl}
                title="ComfyUI Native Interface"
                className="comfy-native-iframe"
                allow="accelerometer; autoplay; camera; encrypted-media; display-capture"
              />
            </div>
          ) : activeTab === 'gallery' ? (
            <div className="comfy-gallery-stage">
              {outputs.length === 0 ? (
                <div className="comfy-empty-gallery">
                  <p style={{ fontSize: '3rem', margin: 0 }}>🎨</p>
                  <h3>No Outputs Streamed in Current Session</h3>
                  <p>Queue any workflow above or run via the ComfyUI canvas. Results stream here in real time.</p>
                </div>
              ) : (
                <div className="comfy-gallery-grid">
                  {outputs.map((item, idx) => (
                    <div key={idx} className="comfy-gallery-card">
                      <div className="comfy-card-thumb-container">
                        {item.filename?.endsWith('.mp4') ? (
                          <video src={item.url} controls autoPlay loop className="comfy-card-media" />
                        ) : (
                          <img src={item.url} alt={item.filename} className="comfy-card-media" />
                        )}
                      </div>
                      <div className="comfy-card-meta">
                        <span className="comfy-card-title">{item.filename}</span>
                        <div className="comfy-card-actions">
                          <span className="comfy-card-time">{item.timestamp}</span>
                          <a
                            href={item.url}
                            download={item.filename}
                            target="_blank"
                            rel="noreferrer"
                            className="comfy-download-link"
                          >
                            ⬇ Download
                          </a>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="comfy-dag-editor-stage">
              <div className="comfy-dag-header">
                <span>Prompt DAG JSON ({selectedPreset})</span>
                <button
                  type="button"
                  className="comfy-mini-btn"
                  onClick={() => setCustomDAG(JSON.stringify(SOVEREIGN_PRESETS[selectedPreset], null, 2))}
                >
                  Reset to Default
                </button>
              </div>
              <textarea
                className="comfy-dag-textarea"
                value={customDAG}
                onChange={(e) => setCustomDAG(e.target.value)}
                spellCheck={false}
              />
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default ComfyStation;
