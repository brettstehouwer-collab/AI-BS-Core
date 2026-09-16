import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';

export default function DeepLearningStudioTab({ backendUrl }) {
  const apiHost = backendUrl || getApiBase() || `${backendUrl}`;

  // Autograd DAG State
  const [x1Val, setX1Val] = useState(2.0);
  const [x2Val, setX2Val] = useState(3.0);
  const [dagResult, setDagResult] = useState(null);
  const [isBuildingDag, setIsBuildingDag] = useState(false);

  // DL Domain Benchmarking State
  const [selectedDomain, setSelectedDomain] = useState('nlp');
  const [batchSize, setBatchSize] = useState(32);
  const [benchmarkResult, setBenchmarkResult] = useState(null);
  const [isBenchmarking, setIsBenchmarking] = useState(false);

  const fetchAutogradDag = async () => {
    setIsBuildingDag(true);
    try {
      const res = await fetch(`${apiHost}/v1/dl/build-dag`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x1: parseFloat(x1Val), x2: parseFloat(x2Val) })
      });
      if (res.ok) {
        const json = await res.json();
        setDagResult(json);
      }
    } catch (e) {
      console.warn('Failed to fetch Autograd DAG:', e);
    } finally {
      setIsBuildingDag(false);
    }
  };

  const fetchDomainBenchmark = async (domain = selectedDomain) => {
    setIsBenchmarking(true);
    try {
      const res = await fetch(`${apiHost}/v1/dl/benchmark`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain, batch_size: parseInt(batchSize) })
      });
      if (res.ok) {
        const json = await res.json();
        if (json.benchmark) setBenchmarkResult(json.benchmark);
      }
    } catch (e) {
      console.warn('Failed to fetch DL benchmark:', e);
    } finally {
      setIsBenchmarking(false);
    }
  };

  useEffect(() => {
    fetchAutogradDag();
    fetchDomainBenchmark(selectedDomain);
  }, [selectedDomain, batchSize, x1Val, x2Val]);

  return (
    <div style={{ padding: '24px', color: '#e6edf3', height: '100%', overflowY: 'auto', background: '#090d16', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Studio Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #30363d', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: '800', margin: 0, color: '#38bdf8' }}>
            🧠 Deep Learning Architecture & Autograd Computation Graph Studio
          </h1>
          <p style={{ fontSize: '13px', color: '#8b949e', margin: '4px 0 0 0' }}>
            Define-by-Run Dynamic DAGs, Reverse-Mode Automatic Differentiation, and CUDA Parallel Execution Acceleration
          </p>
        </div>

        <button
          onClick={fetchAutogradDag}
          style={{ padding: '8px 16px', background: '#1f6feb', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '600', fontSize: '13px', cursor: 'pointer' }}
        >
          ⚡ Re-evaluate Dynamic DAG
        </button>
      </div>

      {/* SECTION 1: ARCHITECTURAL PILLARS OVERVIEW */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '12px', fontWeight: '700', color: '#38bdf8', marginBottom: '6px' }}>1. NEURAL ARCHITECTURES</div>
          <div style={{ fontSize: '12px', color: '#8b949e', lineHeight: '1.4' }}>
            Spatial CNNs (2D/3D Kernels), Recurrent LSTMs/GRUs, and Multi-Head Self-Attention Transformers.
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '12px', fontWeight: '700', color: '#a78bfa', marginBottom: '6px' }}>2. DYNAMIC COMPUTATION GRAPH</div>
          <div style={{ fontSize: '12px', color: '#8b949e', lineHeight: '1.4' }}>
            Define-by-Run Directed Acyclic Graphs (DAG) built dynamically on every forward pass execution.
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '12px', fontWeight: '700', color: '#4ade80', marginBottom: '6px' }}>3. AUTOGRAD & OPTIMIZERS</div>
          <div style={{ fontSize: '12px', color: '#8b949e', lineHeight: '1.4' }}>
            Reverse-Mode Automatic Differentiation with Adam, AdamW, SGD, and RMSprop optimization routines.
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '12px', fontWeight: '700', color: '#f59e0b', marginBottom: '6px' }}>4. HARDWARE ACCELERATION</div>
          <div style={{ fontSize: '12px', color: '#8b949e', lineHeight: '1.4' }}>
            NVIDIA CUDA GPGPU & TensorRT asynchronous memory pipelines on local RTX 4090 hardware.
          </div>
        </div>
      </div>

      {/* SECTION 2: INTERACTIVE REVERSE-MODE AUTOGRAD COMPUTATIONAL DAG VISUALIZER */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '16px', margin: '0 0 4px 0', color: '#f0f6fc' }}>
              📐 Dynamic Autograd Computation DAG (Reverse-Mode Differentiation)
            </h2>
            <p style={{ fontSize: '12px', color: '#8b949e', margin: 0 }}>
              Live forward graph construction & reverse-mode partial derivative backpropagation.
            </p>
          </div>

          {/* Interactive Input Sliders */}
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', background: '#0d1117', padding: '10px 16px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <div>
              <label style={{ fontSize: '11px', color: '#38bdf8', fontWeight: '700', marginRight: '8px' }}>
                x1 = {x1Val}
              </label>
              <input
                type="range"
                min="0.5"
                max="10.0"
                step="0.5"
                value={x1Val}
                onChange={(e) => setX1Val(parseFloat(e.target.value))}
                style={{ width: '90px' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '11px', color: '#38bdf8', fontWeight: '700', marginRight: '8px' }}>
                x2 = {x2Val}
              </label>
              <input
                type="range"
                min="0.5"
                max="10.0"
                step="0.5"
                value={x2Val}
                onChange={(e) => setX2Val(parseFloat(e.target.value))}
                style={{ width: '90px' }}
              />
            </div>
          </div>
        </div>

        {/* Dual Column Visualizer: Forward (Blue) vs. Backward (Green) */}
        {!dagResult ? (
          <div style={{ padding: '30px', textAlign: 'center', color: '#8b949e' }}>Building Computation DAG...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', background: '#0d1117', padding: '20px', borderRadius: '8px', border: '1px solid #30363d' }}>
            
            {/* COLUMN 1: FORWARD PASS (BLUE) */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px', borderBottom: '1px solid #1f6feb', paddingBottom: '8px' }}>
                <span style={{ fontSize: '14px', fontWeight: '800', color: '#38bdf8' }}>⬆️ FORWARD PASS (Values)</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {dagResult.dag_nodes.filter(n => n.col === 'left').map(node => (
                  <div key={node.id} style={{ background: '#161b22', border: '1px solid #1f6feb', borderRadius: '6px', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: '#38bdf8' }}>{node.label}</div>
                      <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Node Type: {node.type}</div>
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: '800', color: '#ffffff', background: '#0d1117', padding: '4px 10px', borderRadius: '4px', border: '1px solid #30363d' }}>
                      {node.val}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* COLUMN 2: BACKWARD AUTOGRAD PASS (GREEN) */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px', borderBottom: '1px solid #238636', paddingBottom: '8px' }}>
                <span style={{ fontSize: '14px', fontWeight: '800', color: '#4ade80' }}>⬇️ BACKWARD AUTOGRAD (Gradients)</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {dagResult.dag_nodes.filter(n => n.col === 'right').map(node => (
                  <div key={node.id} style={{
                    background: '#161b22',
                    border: node.id === 'dz_dx2' ? '2px solid #238636' : '1px solid #238636',
                    borderRadius: '6px',
                    padding: '12px',
                    display: 'flex',
                    justify: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: '#4ade80' }}>{node.label}</div>
                      <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Op: {node.backward_op}</div>
                      {node.id === 'dz_dx2' && (
                        <div style={{ fontSize: '10px', color: '#4ade80', fontWeight: '700', marginTop: '4px' }}>
                          ⚡ Grads from different paths are added together!
                        </div>
                      )}
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: '800', color: '#4ade80', background: 'rgba(35, 134, 54, 0.2)', padding: '4px 10px', borderRadius: '4px', border: '1px solid #238636' }}>
                      {node.val}
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}
      </div>

      {/* SECTION 3: DOMAIN BENCHMARKS & HARDWARE ACCELERATION */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '16px', margin: '0 0 4px 0', color: '#a78bfa' }}>
              🚀 Deep Learning Domain Performance & VRAM Benchmark
            </h2>
            <p style={{ fontSize: '12px', color: '#8b949e', margin: 0 }}>
              Hardware acceleration metrics across Transformer, CNN, Audio, Robotics, and Latent Diffusion models.
            </p>
          </div>

          {/* Domain Selector */}
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
              style={{ padding: '8px 16px', background: '#0d1117', border: '1px solid #a78bfa', borderRadius: '6px', color: '#a78bfa', fontWeight: '700', fontSize: '13px' }}
            >
              <option value="nlp">🔤 Natural Language Processing (Transformers)</option>
              <option value="vision">👁️ Computer Vision (CNNs & ViT)</option>
              <option value="speech">🎙️ Speech Recognition (1D Audio-CNNs)</option>
              <option value="robotics">🤖 Robotics & RL (Visuomotor / State-Space)</option>
              <option value="generative">🎨 Generative AI (Latent Diffusion Models)</option>
            </select>
          </div>
        </div>

        {/* Benchmark Results Display */}
        {benchmarkResult && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <div style={{ background: '#161b22', padding: '14px', borderRadius: '6px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e' }}>EXECUTION LATENCY</div>
              <div style={{ fontSize: '20px', fontWeight: '800', color: '#38bdf8', marginTop: '4px' }}>{benchmarkResult.latency_ms} ms</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Per forward/backward step</div>
            </div>

            <div style={{ background: '#161b22', padding: '14px', borderRadius: '6px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e' }}>GPU VRAM ALLOCATION</div>
              <div style={{ fontSize: '20px', fontWeight: '800', color: '#a78bfa', marginTop: '4px' }}>{benchmarkResult.vram_usage_mb} MB</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Unified CUDA VRAM memory</div>
            </div>

            <div style={{ background: '#161b22', padding: '14px', borderRadius: '6px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e' }}>HARDWARE BACKEND</div>
              <div style={{ fontSize: '13px', fontWeight: '700', color: '#4ade80', marginTop: '4px' }}>{benchmarkResult.hardware_backend}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Batch Size: {benchmarkResult.batch_size}</div>
            </div>

            <div style={{ gridColumn: '1 / -1', background: '#161b22', padding: '14px', borderRadius: '6px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '12px', fontWeight: '700', color: '#f0f6fc', marginBottom: '4px' }}>Architecture Specification:</div>
              <div style={{ fontSize: '12px', color: '#8b949e' }}>{benchmarkResult.architecture_description}</div>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
